import re
import tempfile
from pathlib import Path

from igt.download import Downloader
from igt.errors import NoSpeechError
from igt.models import Transcript
from igt.transcribe import Transcriber
from igt.url import parse_video_url


def generate(
    url: str,
    *,
    downloader: Downloader,
    transcriber: Transcriber,
    language: str = "auto",
) -> Transcript:
    parsed = parse_video_url(url)
    # Audio scratch lives in the system temp dir, never in the repo; always removed.
    with tempfile.TemporaryDirectory(prefix="igt-") as tmp:
        downloaded = downloader.fetch(parsed.canonical, Path(tmp))
        segments, detected = transcriber.transcribe(downloaded.audio_path, language)
    if not any(s.text.strip() for s in segments):
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
    )
