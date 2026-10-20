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


class FakeExtractor:
    def __init__(self, items=(), raises: Exception | None = None):
        from igt.models import OnScreenText

        self.items = tuple(OnScreenText(t, x) for t, x in items)
        self.raises = raises
        self.video: Path | None = None
        self.calls = 0

    def extract(self, video: Path):
        assert video.exists(), "video must exist while extracting"
        self.calls += 1
        self.video = video
        if self.raises:
            raise self.raises
        return self.items

    def extract_images(self, images):
        self.calls += 1
        self.images = tuple(images)
        if self.raises:
            raise self.raises
        return self.items


class FakeImageFetcher:
    def __init__(self, texts=(), creator="", fail: Exception | None = None):
        self.texts, self.creator, self.fail = tuple(texts), creator, fail
        self.shortcode: str | None = None
        self.calls = 0

    def fetch(self, shortcode: str, dest: Path):
        from igt.images import ImagePost

        self.calls += 1
        self.shortcode = shortcode
        if self.fail:
            raise self.fail
        paths = []
        for i, _ in enumerate(self.texts, 1):
            p = dest / f"slide{i:02}.jpg"
            p.write_bytes(b"img")
            paths.append(p)
        return ImagePost(tuple(paths), self.creator)
