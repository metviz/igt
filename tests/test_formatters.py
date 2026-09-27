import json

from igt.formatters import FORMATS, to_json, to_srt, to_txt
from igt.models import Segment, Transcript


def make(*segs):
    return Transcript("instagram", "T", "local-whisper", "en", tuple(segs))


def test_txt_trims_drops_blanks_joins_with_newline():
    t = make(Segment(0, 1, "  hello "), Segment(1, 2, "   "), Segment(2, 3, "world"))
    assert to_txt(t) == "hello\nworld"


def test_txt_empty():
    assert to_txt(make()) == ""


def test_srt_exact_layout_and_numbering_skips_blanks():
    t = make(Segment(0, 1.5, "hello"), Segment(1.5, 2, " "), Segment(1.5, 3, "world"))
    assert to_srt(t) == (
        "1\n00:00:00,000 --> 00:00:01,500\nhello\n\n"
        "2\n00:00:01,500 --> 00:00:03,000\nworld\n"
    )


def test_srt_hours_and_rounding():
    t = make(Segment(0.9996, 3661.5, "x"))
    assert "00:00:01,000 --> 01:01:01,500" in to_srt(t)


def test_json_shape_mirrors_server_payload_and_keeps_unicode():
    t = make(Segment(0, 1, "héllo 🎬"))
    data = json.loads(to_json(t))
    assert data["platform"] == "instagram"
    assert data["segments"] == [{"start": 0, "end": 1, "text": "héllo 🎬"}]
    assert data["formats"]["txt"] == "héllo 🎬"
    assert "🎬" in to_json(t)  # ensure_ascii=False


def test_registry_keys():
    assert set(FORMATS) == {"txt", "srt", "json"}
