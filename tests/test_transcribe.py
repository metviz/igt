from pathlib import Path
from types import SimpleNamespace

import pytest

from igt.errors import TranscribeError
from igt.models import Segment
from igt.transcribe import FasterWhisperTranscriber


class FakeModel:
    def __init__(self, segs=(), lang="en", raises=None):
        self.segs, self.lang, self.raises, self.calls = segs, lang, raises, []

    def transcribe(self, path, language=None, vad_filter=True):
        self.calls.append((path, language, vad_filter))

        def gen():
            for start, end, text in self.segs:
                yield SimpleNamespace(start=start, end=end, text=text)
            if self.raises:
                raise self.raises

        return gen(), SimpleNamespace(language=self.lang)


def make(model):
    built = []

    def factory(size, **kw):
        built.append((size, kw))
        return model

    return FasterWhisperTranscriber("tiny", factory), built


def test_maps_and_strips_segments_and_returns_language():
    t, _ = make(FakeModel([(0, 1.5, " hello "), (1.5, 2, "world")], lang="hi"))
    segs, lang = t.transcribe(Path("a.m4a"), "auto")
    assert segs == (Segment(0, 1.5, "hello"), Segment(1.5, 2, "world"))
    assert lang == "hi"


def test_auto_maps_to_none_and_explicit_passes_through():
    model = FakeModel()
    t, _ = make(model)
    t.transcribe(Path("a.m4a"), "auto")
    t.transcribe(Path("a.m4a"), "hi")
    assert [c[1] for c in model.calls] == [None, "hi"]
    assert model.calls[0][0] == "a.m4a"  # str, not Path
    assert (
        model.calls[0][2] is True
    )  # vad_filter on: music-only audio yields no phantom text


def test_model_loaded_once_lazily():
    t, built = make(FakeModel())
    assert built == []
    t.transcribe(Path("a"), "auto")
    t.transcribe(Path("b"), "auto")
    assert len(built) == 1 and built[0][0] == "tiny"


def test_decode_error_during_iteration_becomes_transcribe_error():
    t, _ = make(FakeModel([(0, 1, "x")], raises=RuntimeError("bad audio")))
    with pytest.raises(TranscribeError, match="bad audio"):
        t.transcribe(Path("a"), "auto")


def test_model_load_error_becomes_transcribe_error():
    def factory(size, **kw):
        raise OSError("no model")

    with pytest.raises(TranscribeError, match="no model"):
        FasterWhisperTranscriber("tiny", factory).transcribe(Path("a"), "auto")
