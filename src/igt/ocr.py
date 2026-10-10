import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Protocol

from igt.errors import ConfigError, DownloadError
from igt.models import OnScreenText

ENGINES = ("tesseract", "rapidocr")


class TextExtractor(Protocol):
    def extract(self, video: Path) -> tuple[OnScreenText, ...]: ...


def _norm(text: str) -> str:
    return " ".join(text.split())


class _FrameExtractor:
    """Sample a frame every `every` seconds with ffmpeg, read each with an OCR engine."""

    tools: tuple[str, ...] = ("ffmpeg",)

    def __init__(self, every: float = 2.0, runner=subprocess.run, which=shutil.which):
        self._every, self._run, self._which = every, runner, which

    def check(self) -> None:
        for tool in self.tools:
            if not self._which(tool):
                raise ConfigError(f"--ocr needs {tool} on PATH")

    def _read(self, frame: Path) -> str:
        raise NotImplementedError

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
            prev = ""
            for i, frame in enumerate(sorted(Path(tmp).glob("f*.png"))):
                text = _norm(self._read(frame))
                # ponytail: >=3 alphanumerics drops OCR noise; tune if real captions get lost
                if len(re.findall(r"\w", text)) < 3:
                    continue
                if text.casefold() != prev.casefold():
                    found.append(OnScreenText(i * self._every, text))
                prev = text
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


def make_extractor(engine: str, every: float) -> _FrameExtractor:
    cls = RapidOcrExtractor if engine == "rapidocr" else TesseractExtractor
    return cls(every)
