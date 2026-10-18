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
        "## Requirements checklist",
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


def test_analysis_section_placed_after_source_material():
    out = to_idea(make(), analysis="LLM says hi")
    assert "## Generated analysis\n\nLLM says hi" in out
    assert out.index("## Source material") < out.index("## Generated analysis")
    assert out.index("## Generated analysis") < out.index("## Requirements checklist")


def test_no_analysis_section_by_default():
    assert "Generated analysis" not in to_idea(make())


def test_analysis_headings_are_demoted_to_level_3():
    out = to_idea(make(), analysis="# Title\n\n## Summary\ntext\n### Keep\n#hashtag\n```\n# in code\n```")
    block = out.split("## Generated analysis")[1].split("## Requirements checklist")[0]
    assert "\n### Title" in block and "\n### Summary" in block
    assert "\n### Keep" in block and "\n#hashtag" in block
    assert "\n# in code" in block
    assert "\n# Title" not in block and "\n## Summary" not in block


FB_TITLE = (
    "15 reactions | When anyone can copy your software’s features, what becomes "
    "your competitive advantage? 🤔 Tools like REA are changing how software "
    "gets built. | Sathya Sankar"
)


def test_facebook_title_drops_reaction_count_author_and_trailing_sentences():
    first = to_idea(make(title=FB_TITLE)).splitlines()[0]
    assert first == (
        "# Project idea: When anyone can copy your software’s features, "
        "what becomes your competitive advantage?"
    )


def test_long_title_is_cut_at_a_word_boundary():
    first = to_idea(make(title="word " * 40)).splitlines()[0]
    assert first.endswith("…") and len(first) <= len("# Project idea: ") + 101


def test_short_title_is_untouched():
    assert to_idea(make()).startswith("# Project idea: Embedding Gemma\n")


def test_open_questions_grouped_into_four_categories():
    questions = to_idea(make()).split("## Open questions")[1].split("## Brainstorm")[0]
    for heading in (
        "### Core functionality and business logic",
        "### Technical stack and constraints",
        "### Scale, performance and security",
        "### Scope and phasing",
    ):
        assert heading in questions
    assert questions.count("\n- ") >= 8


def test_checklist_asks_for_given_when_then_acceptance_criteria():
    assert "- [ ] Acceptance criteria (Given/When/Then)" in to_idea(make())
