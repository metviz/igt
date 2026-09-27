from pathlib import Path
from typing import Any, Callable, Protocol

from igt.errors import TranscribeError
from igt.models import Segment


class Transcriber(Protocol):
    def transcribe(
        self, audio: Path, language: str
    ) -> tuple[tuple[Segment, ...], str]: ...


class FasterWhisperTranscriber:
    def __init__(
        self, model_size: str = "base", model_factory: Callable[..., Any] | None = None
    ):
        self._size = model_size
        self._factory = model_factory
        self._model: Any = None

    def _load(self) -> Any:
        if self._model is None:
            factory = self._factory
            if factory is None:
                from faster_whisper import WhisperModel

                factory = WhisperModel
            # ponytail: CPU+int8 runs everywhere; "auto" device picked a broken CUDA GPU.
            # Expose --device/--compute-type if GPU speed is ever needed.
            self._model = factory(self._size, device="cpu", compute_type="int8")
        return self._model

    def transcribe(self, audio: Path, language: str) -> tuple[tuple[Segment, ...], str]:
        try:
            raw, info = self._load().transcribe(
                str(audio),
                language=None if language == "auto" else language,
                vad_filter=True,
            )
            segments = tuple(
                Segment(s.start, s.end, s.text.strip()) for s in raw
            )  # generator: decode happens here
        except Exception as exc:  # noqa: BLE001 — model/decoder errors are third-party and varied
            raise TranscribeError(f"transcription failed: {exc}") from exc
        return segments, info.language
