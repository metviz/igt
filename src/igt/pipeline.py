import tempfile
from pathlib import Path

from igt.download import Downloader
from igt.errors import NoSpeechError
from igt.models import Transcript
from igt.transcribe import Transcriber
from igt.url import parse_instagram_url


def generate(
    url: str,
    *,
    downloader: Downloader,
    transcriber: Transcriber,
    language: str = "auto",
) -> Transcript:
    parsed = parse_instagram_url(url)
    # Audio scratch lives in the system temp dir, never in the repo; always removed.
    with tempfile.TemporaryDirectory(prefix="igt-") as tmp:
        downloaded = downloader.fetch(parsed.canonical, Path(tmp))
        segments, detected = transcriber.transcribe(downloaded.audio_path, language)
    if not any(s.text.strip() for s in segments):
        raise NoSpeechError("no speech detected in this video (music-only or silent)")
    return Transcript(
        "instagram", downloaded.title, "local-whisper", detected, segments
    )
