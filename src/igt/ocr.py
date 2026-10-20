import difflib
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Protocol, Sequence

from igt.errors import ConfigError, DownloadError
from igt.models import OnScreenText

ENGINES = ("tesseract", "rapidocr")
MERGE_MODES = ("fuzzy", "exact", "off")


class TextExtractor(Protocol):
    def extract(self, video: Path) -> tuple[OnScreenText, ...]: ...
    def extract_images(self, images: Sequence[Path]) -> tuple[OnScreenText, ...]: ...


def _norm(text: str) -> str:
    return " ".join(text.split())


def _similar(a: str, b: str) -> bool:
    """Same on-screen text seen again: OCR jitter, or the same text partly revealed.

    Overlap is measured against the shorter string, so a caption that grows still matches.
    ponytail: 0.8 overlap / 0.4 length ratio; tune if distinct slides merge.
    """
    a, b = a.casefold(), b.casefold()
    if min(len(a), len(b)) < 0.4 * max(len(a), len(b)):
        return False
    blocks = difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks()
    return sum(m.size for m in blocks) >= 0.8 * min(len(a), len(b))


class _FrameExtractor:
    """Sample a frame every `every` seconds with ffmpeg, read each with an OCR engine."""

    tools: tuple[str, ...] = ("ffmpeg",)

    def __init__(
        self,
        every: float = 2.0,
        merge: str = "fuzzy",
        runner=subprocess.run,
        which=shutil.which,
    ):
        self._every, self._merge, self._run, self._which = every, merge, runner, which

    def _same(self, a: str, b: str) -> bool:
        if self._merge == "off":
            return False
        if self._merge == "exact":
            return a.casefold() == b.casefold()
        return _similar(a, b)

    def check(self) -> None:
        for tool in self.tools:
            if not self._which(tool):
                raise ConfigError(f"--ocr needs {tool} on PATH")

    def _read(self, frame: Path) -> str:
        raise NotImplementedError

    def extract_images(self, images: Sequence[Path]) -> tuple[OnScreenText, ...]:
        """Read still images; `start` is the 0-based slide index. Slides are never merged."""
        found = (
            OnScreenText(float(i), _norm(self._read(p))) for i, p in enumerate(images)
        )
        return tuple(o for o in found if len(re.findall(r"\w", o.text)) >= 3)

    def extract(self, video: Path) -> tuple[OnScreenText, ...]:
        self.check()
        found: list[OnScreenText] = []
        with tempfile.TemporaryDirectory(prefix="igt-ocr-") as tmp:
            cmd = [
                "ffmpeg", "-v", "error", "-i", str(video),
                "-vf", f"fps=1/{self._every}", str(Path(tmp) / "f%05d.png"),
            ]  # fmt: skip
            done = self._run(cmd, capture_output=True, text=True)
            if done.returncode:
                raise DownloadError(
                    f"frame extraction failed: {done.stderr.strip()[:200]}"
                )
            for i, frame in enumerate(sorted(Path(tmp).glob("f*.png"))):
                text = _norm(self._read(frame))
                # ponytail: >=3 alphanumerics drops OCR noise; tune if real captions get lost
                if len(re.findall(r"\w", text)) < 3:
                    continue
                last = found[-1] if found else None
                if last is None or not self._same(text, last.text):
                    found.append(OnScreenText(i * self._every, text))
                elif len(text) > len(
                    last.text
                ):  # text still being revealed: keep fullest
                    found[-1] = OnScreenText(last.start, text)
        return tuple(found)


class TesseractExtractor(_FrameExtractor):
    tools = ("ffmpeg", "tesseract")

    def _read(self, frame: Path) -> str:
        done = self._run(
            ["tesseract", str(frame), "stdout"], capture_output=True, text=True
        )
        return done.stdout if done.returncode == 0 else ""


class RapidOcrExtractor(_FrameExtractor):
    def __init__(self, *args, engine_factory: Callable[[], Any] | None = None, **kw):
        super().__init__(*args, **kw)
        self._factory, self._engine = engine_factory, None

    def check(self) -> None:
        super().check()
        if self._factory is None:
            try:
                import rapidocr_onnxruntime  # noqa: F401
            except ImportError as exc:
                raise ConfigError(
                    "rapidocr engine not installed: pip install 'igt[rapidocr]'"
                ) from exc

    def _read(self, frame: Path) -> str:
        if self._engine is None:
            factory = self._factory
            if factory is None:
                from rapidocr_onnxruntime import RapidOCR as factory
            self._engine = factory()
        result, _ = self._engine(str(frame))
        return " ".join(row[1] for row in result or [])


def make_extractor(engine: str, every: float, merge: str = "fuzzy") -> _FrameExtractor:
    cls = RapidOcrExtractor if engine == "rapidocr" else TesseractExtractor
    return cls(every, merge)
