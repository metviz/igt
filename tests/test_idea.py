from igt.formatters import FORMATS
from igt.idea import to_idea
from igt.models import OnScreenText, Segment, Transcript


def make(**kw):
    base = {
        "platform": "instagram",
        "title": "Embedding Gemma",
        "source": "whisper",
        "language": "en",
        "segments": (Segment(0, 2, "A tiny on-device embedding model."),),
        "url": "https://example.com/r/1",
        "caption": "Try it #ml #embeddings",
        "hashtags": ("ml", "embeddings"),
    }
    return Transcript(**{**base, **kw})


def test_registered_as_format():
    assert FORMATS["idea"] is to_idea


def test_sections_and_source_material():
    out = to_idea(make())
    for heading in (
        "# Project idea: Embedding Gemma",
        "## Source material",
        "## Potential requirements",
        "## Open questions",
        "## Brainstorm prompts",
    ):
        assert heading in out
    assert "Source: https://example.com/r/1" in out
    assert "A tiny on-device embedding model." in out
    assert "Try it #ml #embeddings" in out
    assert out.endswith("\n")


def test_prompts_embed_the_content_for_pasting_into_an_llm():
    out = to_idea(make())
    prompts = out.split("## Brainstorm prompts")[1]
    assert "A tiny on-device embedding model." in prompts


def test_on_screen_text_included_when_present():
    out = to_idea(make(on_screen=(OnScreenText(3, "SALE 50%"),)))
    assert "SALE 50%" in out


def test_no_on_screen_section_when_absent():
    assert "On-screen" not in to_idea(make())


def test_blank_title_falls_back():
    assert to_idea(make(title="  ")).startswith("# Project idea: Untitled")
