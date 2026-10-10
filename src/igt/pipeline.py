import re
import shutil
import tempfile
from pathlib import Path

from igt.download import Downloader
from igt.errors import NoSpeechError
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
) -> Transcript:
    parsed = parse_video_url(url)
    # Audio scratch lives in the system temp dir, never in the repo; always removed.
    with tempfile.TemporaryDirectory(prefix="igt-") as tmp:
        downloaded = downloader.fetch(parsed.canonical, Path(tmp))
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
