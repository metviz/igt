import argparse
import os
import sys
from pathlib import Path
from typing import Mapping, Sequence, TextIO

from igt import __version__
from igt.config import REPO_ROOT, env_path, outside, require_out_root
from igt.download import Downloader, YtDlpDownloader
from igt.errors import ConfigError, IgtError
from igt.formatters import FORMATS
from igt.pipeline import generate
from igt.transcribe import FasterWhisperTranscriber, Transcriber
from igt.url import parse_instagram_url


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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="igt", description="Transcribe an Instagram reel/post video."
    )
    p.add_argument("url", help="Instagram reel/post/tv URL")
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
    p.add_argument(
        "--out",
        action="store_true",
        help="write to $IGT_OUT_ROOT/<shortcode>.<format> instead of stdout",
    )
    p.add_argument("--version", action="version", version=f"igt {__version__}")
    return p


def _prepare_target(root: Path, name: str) -> Path:
    """Fail fast (before download/transcribe) if the output can't be written safely."""
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ConfigError(f"cannot use output directory {root}: {exc}") from exc
    if not os.access(root, os.W_OK):
        raise ConfigError(f"output directory is not writable: {root}")
    target = root / name
    if target.is_symlink():  # write_text would follow it out of the guarded root
        raise ConfigError(f"refusing to write through symlink: {target}")
    return target


def _run(
    args: argparse.Namespace,
    env: Mapping[str, str],
    downloader: Downloader | None,
    transcriber: Transcriber | None,
    stdout: TextIO,
) -> None:
    parsed = parse_instagram_url(args.url)
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
    if args.out:  # resolve (and validate) the destination before the expensive work
        target = _prepare_target(
            require_out_root(env, REPO_ROOT), f"{parsed.shortcode}.{args.format}"
        )
    transcript = generate(
        args.url,
        downloader=downloader
        or YtDlpDownloader(cookies, cookies_from_browser=args.cookies_from),
        transcriber=transcriber or FasterWhisperTranscriber(args.model),
        language=args.language,
    )
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
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    env = os.environ if env is None else env
    stdout, stderr = stdout or sys.stdout, stderr or sys.stderr
    try:
        _run(args, env, downloader, transcriber, stdout)
        return 0
    except IgtError as exc:
        stderr.write(f"error: {exc}\n")
        return exc.exit_code
    except KeyboardInterrupt:
        stderr.write("interrupted\n")
        return 130


if __name__ == "__main__":
    sys.exit(main())
