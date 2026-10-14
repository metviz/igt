import argparse
import os
import sys
from pathlib import Path
from typing import Mapping, Sequence, TextIO

from igt import __version__
from igt.config import REPO_ROOT, env_path, outside, out_base
from igt.download import Downloader, YtDlpDownloader
from igt.errors import ConfigError, IgtError
from igt.formatters import FORMATS
from igt.ocr import ENGINES, MERGE_MODES, TextExtractor, make_extractor
from igt.idea import to_idea
from igt.llm import PROVIDERS, IdeaWriter, make_writer
from igt.pipeline import generate, save_audio
from igt.transcribe import FasterWhisperTranscriber, Transcriber
from igt.url import parse_video_url


BROWSERS = (
    "chrome",
    "chromium",
    "firefox",
    "edge",
    "brave",
    "opera",
    "vivaldi",
    "safari",
)


def _positive_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        number = 0.0
    if not number > 0:
        raise argparse.ArgumentTypeError(f"must be a positive number: {value!r}")
    return number


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="igt",
        description="Transcribe an Instagram, YouTube, Facebook or TikTok video.",
    )
    p.add_argument(
        "url",
        help=(
            "Instagram reel/post/tv, YouTube watch/shorts, Facebook reel/video, "
            "or TikTok video URL"
        ),
    )
    p.add_argument("--format", choices=sorted(FORMATS), default="txt")
    p.add_argument(
        "--language", default="auto", help="language code or 'auto' (default)"
    )
    p.add_argument(
        "--model", default="base", help="faster-whisper model size (default: base)"
    )
    auth = p.add_mutually_exclusive_group()
    auth.add_argument(
        "--cookies",
        help="Netscape cookies file for login-walled posts (must be outside the repo)",
    )
    auth.add_argument(
        "--cookies-from",
        choices=BROWSERS,
        metavar="BROWSER",
        help=f"read your logged-in session from a browser ({', '.join(BROWSERS)})",
    )
    dest = p.add_mutually_exclusive_group()
    dest.add_argument(
        "--out",
        action="store_true",
        help="write to <shortcode>.<format> in $IGT_OUT_ROOT (default: current directory) instead of stdout",
    )
    dest.add_argument(
        "--out-file",
        metavar="PATH",
        help=(
            "write to PATH instead of stdout; relative to $IGT_OUT_ROOT (default: current directory), or absolute. "
            "Must be outside the repo"
        ),
    )
    p.add_argument(
        "--mp3",
        action="store_true",
        help="save the audio as <shortcode>.mp3 (or --out-file PATH) instead of transcribing; needs ffmpeg",
    )
    p.add_argument(
        "--ocr",
        action="store_true",
        help="also read on-screen text from video frames (md/json output); needs ffmpeg + an OCR engine",
    )
    p.add_argument("--ocr-engine", choices=ENGINES, default="rapidocr")
    p.add_argument(
        "--ocr-every",
        type=_positive_float,
        default=2.0,
        metavar="SECONDS",
        help="seconds between sampled frames (default: 2)",
    )
    p.add_argument(
        "--ocr-merge",
        choices=MERGE_MODES,
        default="fuzzy",
        help=(
            "collapse repeated on-screen text: fuzzy (default, tolerates OCR jitter), "
            "exact (identical text only), off (every sampled frame)"
        ),
    )
    p.add_argument(
        "--idea-llm",
        action="store_true",
        help="with --format idea: add an LLM-written analysis; see --llm-provider (anthropic needs ANTHROPIC_API_KEY and igt[llm] and sends the extracted text to Anthropic)",
    )
    p.add_argument(
        "--llm-provider",
        choices=PROVIDERS,
        default="anthropic",
        help="backend for --idea-llm: anthropic (cloud) or ollama (local, no data leaves the machine)",
    )
    p.add_argument(
        "--llm-model",
        help="model for --idea-llm (default: claude-sonnet-5-5 for anthropic, llama3.2 for ollama)",
    )
    p.add_argument("--version", action="version", version=f"igt {__version__}")
    return p


def _resolve_out(
    args: argparse.Namespace, env: Mapping[str, str], default_name: str
) -> tuple[Path, str]:
    """Split --out/--out-file into (directory, filename); always outside the repo."""
    if args.out_file is None:
        return out_base(env, REPO_ROOT), default_name
    path = Path(args.out_file).expanduser()
    if not path.is_absolute():
        path = out_base(env, REPO_ROOT) / path
    full = outside(path, REPO_ROOT, "--out-file")
    return full.parent, full.name


def _prepare_target(root: Path, name: str) -> Path:
    """Fail fast (before download/transcribe) if the output can't be written safely."""
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ConfigError(f"cannot use output directory {root}: {exc}") from exc
    if not os.access(root, os.W_OK):
        raise ConfigError(f"output directory is not writable: {root}")
    target = root / name
    if target.is_dir():
        raise ConfigError(f"output path is a directory: {target}")
    if target.is_symlink():  # write_text would follow it out of the guarded root
        raise ConfigError(f"refusing to write through symlink: {target}")
    return target


def _run(
    args: argparse.Namespace,
    env: Mapping[str, str],
    downloader: Downloader | None,
    transcriber: Transcriber | None,
    extractor: TextExtractor | None,
    idea_writer: IdeaWriter | None,
    stdout: TextIO,
) -> None:
    parsed = parse_video_url(args.url)
    if args.cookies_from:  # an explicit browser session beats any cookies file
        cookies = None
    elif args.cookies:
        cookies = outside(Path(args.cookies), REPO_ROOT, "cookies")
    else:
        cookies = env_path(env, "IGT_COOKIES_FILE", REPO_ROOT)
    if cookies is not None and not cookies.is_file():
        # yt-dlp would silently skip a missing file and then create it on exit
        raise ConfigError(f"cookies file not found: {cookies}")
    target = None
    if (
        args.out or args.mp3 or args.out_file is not None
    ):  # validate the destination before the expensive work
        ext = "mp3" if args.mp3 else {"idea": "md"}.get(args.format, args.format)
        root, name = _resolve_out(args, env, f"{parsed.shortcode}.{ext}")
        target = _prepare_target(root, name)
    if args.mp3:
        assert target is not None
        save_audio(
            args.url,
            downloader=downloader
            or YtDlpDownloader(
                cookies, cookies_from_browser=args.cookies_from, mp3=True
            ),
            target=target,
        )
        stdout.write(f"{target}\n")
        return
    if args.ocr:
        extractor = extractor or make_extractor(
            args.ocr_engine, args.ocr_every, args.ocr_merge
        )
        if hasattr(extractor, "check"):
            extractor.check()  # fail fast, before the download
    else:
        extractor = None
    if args.idea_llm:
        idea_writer = idea_writer or make_writer(args.llm_provider, args.llm_model, env)
        if hasattr(idea_writer, "check"):
            idea_writer.check()  # fail fast, before the download
    transcript = generate(
        args.url,
        downloader=downloader
        or YtDlpDownloader(
            cookies,
            cookies_from_browser=args.cookies_from,
            **({"video": True} if args.ocr else {}),
        ),
        extractor=extractor,
        transcriber=transcriber or FasterWhisperTranscriber(args.model),
        language=args.language,
    )
    if args.idea_llm:
        rendered = to_idea(transcript, idea_writer.write(transcript))
    else:
        rendered = FORMATS[args.format](transcript).rstrip("\n") + "\n"
    if target is None:
        stdout.write(rendered)
        return
    try:
        target.write_text(rendered, encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"cannot write {target}: {exc}") from exc
    stdout.write(f"{target}\n")


def main(
    argv: Sequence[str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
    downloader: Downloader | None = None,
    transcriber: Transcriber | None = None,
    extractor: TextExtractor | None = None,
    idea_writer: IdeaWriter | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.ocr and args.mp3:
        parser.error("--ocr cannot be combined with --mp3")
    if args.idea_llm and args.format != "idea":
        parser.error("--idea-llm requires --format idea")
    env = os.environ if env is None else env
    stdout, stderr = stdout or sys.stdout, stderr or sys.stderr
    try:
        _run(args, env, downloader, transcriber, extractor, idea_writer, stdout)
        return 0
    except IgtError as exc:
        stderr.write(f"error: {exc}\n")
        return exc.exit_code
    except KeyboardInterrupt:
        stderr.write("interrupted\n")
        return 130


if __name__ == "__main__":
    sys.exit(main())
