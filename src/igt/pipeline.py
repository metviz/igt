import re
import shutil
import tempfile
from pathlib import Path
from typing import Callable

from igt.download import Downloader
from igt.errors import NoSpeechError, NoVideoError
from igt.images import ImageFetcher
from igt.models import Transcript
from igt.ocr import TextExtractor
from igt.transcribe import Transcriber
from igt.url import parse_video_url


def generate(
    url: str,
    *,
    downloader: Downloader,
    transcriber: Transcriber,
    language: str = "auto",
    extractor: TextExtractor | None = None,
    keep: Callable[[Path], None] | None = None,
    images: ImageFetcher | None = None,
) -> Transcript:
    parsed = parse_video_url(url)
    # Audio scratch lives in the system temp dir, never in the repo; always removed.
    with tempfile.TemporaryDirectory(prefix="igt-") as tmp:
        try:
            downloaded = downloader.fetch(parsed.canonical, Path(tmp))
        except NoVideoError:
            if not (images and extractor and parsed.platform == "instagram"):
                raise
            return _from_images(parsed, url, images, extractor, Path(tmp))
        if keep:  # with video mode the "audio" file is the whole video
            keep(downloaded.audio_path)
        segments, detected = transcriber.transcribe(downloaded.audio_path, language)
        # with --ocr the "audio" file is the whole video, so frames can be read from it
        on_screen = extractor.extract(downloaded.audio_path) if extractor else ()
    if not on_screen and not any(s.text.strip() for s in segments):
        raise NoSpeechError("no speech detected in this video (music-only or silent)")
    return Transcript(
        parsed.platform,
        downloaded.title,
        "local-whisper",
        detected,
        segments,
        url=parsed.canonical,
        creator=downloaded.creator,
        upload_date=downloaded.upload_date,
        duration=downloaded.duration,
        caption=downloaded.caption,
        hashtags=tuple(dict.fromkeys(re.findall(r"#(\w+)", downloaded.caption))),
        on_screen=on_screen,
    )


def save_audio(url: str, *, downloader: Downloader, target: Path) -> None:
    """Download the audio (already mp3 from the downloader) and copy it to target."""
    parsed = parse_video_url(url)
    with tempfile.TemporaryDirectory(prefix="igt-") as tmp:
        downloaded = downloader.fetch(parsed.canonical, Path(tmp))
        shutil.copyfile(downloaded.audio_path, target)


def _from_images(
    parsed, url: str, images: ImageFetcher, extractor, tmp: Path
) -> Transcript:
    """Image post: OCR each slide instead of transcribing."""
    post = images.fetch(parsed.shortcode, tmp)
    on_screen = extractor.extract_images(post.paths)
    if not on_screen:
        raise NoSpeechError("no text found in this post's images")
    by = f" by @{post.creator}" if post.creator else ""
    return Transcript(
        parsed.platform, f"Instagram post{by}", "image-ocr", "", (),
        url=parsed.canonical, creator=post.creator, on_screen=on_screen, slides=True,
    )  # fmt: skip
