import json

from igt.formatters import FORMATS, to_json, to_md, to_srt, to_txt
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
    assert set(FORMATS) == {"txt", "srt", "json", "md"}


def test_json_includes_metadata():
    t = Transcript(
        "instagram",
        "T",
        "local-whisper",
        "en",
        (Segment(0, 1, "x"),),
        url="https://www.instagram.com/reel/A/",
        creator="alice",
        upload_date="2026-09-27",
        duration=32.5,
        caption="Hi #a",
        hashtags=("a",),
    )
    data = json.loads(to_json(t))
    assert data["url"] == "https://www.instagram.com/reel/A/"
    assert (data["creator"], data["upload_date"], data["duration"]) == (
        "alice",
        "2026-09-27",
        32.5,
    )
    assert (data["caption"], data["hashtags"]) == ("Hi #a", ["a"])


def test_json_metadata_defaults_when_absent():
    data = json.loads(to_json(make(Segment(0, 1, "x"))))
    assert (data["creator"], data["duration"], data["hashtags"]) == ("", None, [])


def rich():
    return Transcript(
        "instagram",
        "My reel",
        "local-whisper",
        "en",
        (Segment(0, 1.5, "hello"), Segment(61, 63, "  "), Segment(3725, 3726, "world")),
        url="https://www.instagram.com/reel/A/",
        creator="alice",
        upload_date="2026-09-27",
        duration=32.5,
        caption="Hi #a",
        hashtags=("a",),
    )


def test_md_full_document_source_url_first():
    assert to_md(rich()) == (
        "# My reel\n\n"
        "Source: https://www.instagram.com/reel/A/\n\n"
        "- Creator: alice\n- Uploaded: 2026-09-27\n- Duration: 00:32\n"
        "- Language: en\n- Hashtags: #a\n\n"
        "## Caption\n\nHi #a\n\n"
        "## Transcript\n\n[00:00] hello\n[1:02:05] world\n"
    )


def test_md_minimal_omits_empty_sections():
    assert to_md(make(Segment(0, 1, "hello"))) == (
        "# T\n\n- Language: en\n\n## Transcript\n\n[00:00] hello\n"
    )


def test_md_title_is_one_line_and_has_a_fallback():
    t = Transcript("instagram", "Line one\nline two", "s", "", (Segment(0, 1, "x"),))
    assert to_md(t).startswith("# Line one line two\n")
    blank = Transcript("instagram", " ", "s", "", (Segment(0, 1, "x"),))
    assert to_md(blank).startswith("# Instagram transcript\n")
