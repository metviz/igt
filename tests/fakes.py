from pathlib import Path

from igt.download import Downloaded
from igt.models import Segment

DEFAULT_SEGMENTS = (Segment(0, 1.5, "hello"), Segment(1.5, 3, "world"))


class FakeDownloader:
    def __init__(
        self,
        fail: Exception | None = None,
        title: str = "My reel",
        meta: dict | None = None,
    ):
        self.fail, self.title, self.meta = fail, title, meta or {}
        self.url: str | None = None
        self.dest: Path | None = None
        self.calls = 0

    def fetch(self, url: str, dest: Path) -> Downloaded:
        self.calls += 1
        self.url, self.dest = url, dest
        if self.fail:
            raise self.fail
        path = dest / "a.m4a"
        path.write_bytes(b"audio")
        return Downloaded(path, self.title, **self.meta)


class FakeTranscriber:
    def __init__(
        self,
        segments=DEFAULT_SEGMENTS,
        raises: Exception | None = None,
        language: str = "en",
    ):
        self.segments, self.raises, self.language = tuple(segments), raises, language
        self.seen_language: str | None = None

    def transcribe(self, audio: Path, language: str):
        assert audio.exists(), "audio must exist while transcribing"
        self.seen_language = language
        if self.raises:
            raise self.raises
        return self.segments, self.language
