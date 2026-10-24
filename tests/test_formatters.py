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
    assert set(FORMATS) == {"txt", "srt", "vtt", "json", "md", "idea"}


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
    assert to_md(blank).startswith("# Video transcript\n")


def make_ocr():
    from igt.models import OnScreenText

    return Transcript(
        "instagram",
        "T",
        "local-whisper",
        "en",
        (Segment(0, 1, "hi"),),
        on_screen=(OnScreenText(3.0, "SALE 50%"),),
    )


def test_json_includes_on_screen():
    data = json.loads(to_json(make_ocr()))
    assert data["on_screen"] == [{"start": 3.0, "end": None, "text": "SALE 50%"}]
    assert json.loads(to_json(make()))["on_screen"] == []


def test_md_has_on_screen_section_only_when_present():
    assert "## On-screen text\n\n[00:03] SALE 50%" in to_md(make_ocr())
    assert "On-screen" not in to_md(make(Segment(0, 1, "hi")))


def test_txt_and_srt_ignore_on_screen():
    t = make_ocr()
    assert to_txt(t) == "hi" and "SALE" not in to_srt(t)


def test_md_labels_slides_and_skips_empty_transcript():
    from igt.models import OnScreenText, Transcript

    t = Transcript(
        "instagram", "Post", "images", "", (), on_screen=(OnScreenText(1, "Two"),),
        slides=True,
    )  # fmt: skip
    md = to_md(t)
    assert "[slide 2] Two" in md and "## Transcript" not in md


def test_vtt_header_dot_separator_and_skips_blanks():
    from igt.formatters import to_vtt

    t = make(Segment(0, 1.5, "hi"), Segment(1.5, 2, "  "), Segment(3661.25, 3662, "yo"))
    assert to_vtt(t) == (
        "WEBVTT\n\n00:00:00.000 --> 00:00:01.500\nhi\n\n"
        "01:01:01.250 --> 01:01:02.000\nyo\n"
    )


def test_vtt_empty_is_just_header():
    from igt.formatters import to_vtt

    assert to_vtt(make()) == "WEBVTT\n"


def _timed():
    from igt.models import OnScreenText, Transcript

    return Transcript(
        "youtube", "T", "w", "en", (Segment(0, 1, "hi"),), duration=10.0,
        on_screen=(OnScreenText(2.0, "A"), OnScreenText(5.0, "B")),
    )  # fmt: skip


def test_on_screen_end_is_next_start_else_duration():
    data = json.loads(to_json(_timed()))
    assert [(o["start"], o["end"]) for o in data["on_screen"]] == [
        (2.0, 5.0),
        (5.0, 10.0),
    ]


def test_md_on_screen_shows_time_ranges():
    md = to_md(_timed())
    assert "[00:02-00:05] A\n[00:05-00:10] B" in md


def test_json_slides_carry_slide_number_and_no_end():
    from igt.models import OnScreenText, Transcript

    t = Transcript(
        "instagram", "P", "i", "", (), on_screen=(OnScreenText(1, "Two"),), slides=True
    )
    (o,) = json.loads(to_json(t))["on_screen"]
    assert o == {"start": 1, "end": None, "slide": 2, "text": "Two"}


def test_llm_doc_has_title_source_and_demoted_headings():
    from igt.formatters import to_llm_doc

    t = make(Segment(0, 1, "hi"))
    out = to_llm_doc(t, "# Big\n- point")
    assert out.startswith("# T\n") and "### Big\n- point" in out
