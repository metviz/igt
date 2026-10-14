from igt.models import Transcript

# Deterministic template: no LLM is called. The prompts embed the extracted
# content so they can be pasted into any assistant.
_REQUIREMENT_STUBS = (
    "Problem: who has it, and what do they do today instead?",
    "Core feature: the single thing the first version must do",
    "Inputs and outputs: what goes in, what comes out, in what format",
    "Constraints: platform, budget, privacy, offline use, latency",
    "Success metric: how you will know it works",
    "Out of scope for v1",
)
_QUESTIONS = (
    "What in the source is a claim to verify, and what is a demo to reproduce?",
    "Is there an existing tool or library that already does 80% of this?",
    "What is the smallest experiment that would take under a day?",
    "What breaks first at 10x the scale or data size?",
)
_PROMPTS = (
    "List the explicit and implied requirements in the material above, "
    "grouped as functional, non-functional and data.",
    "Propose three distinct project ideas inspired by the material above. "
    "For each give the user, the core loop and the riskiest assumption.",
    "Act as a sceptical reviewer: what is missing, wrong or unproven in the "
    "material above? Suggest how to check each point.",
    "Draft a one-page spec and a 3-step build plan for the most promising idea.",
)


def to_idea(t: Transcript) -> str:
    title = " ".join(t.title.split()) or "Untitled"
    speech = "\n".join(s.text.strip() for s in t.segments if s.text.strip())
    shown = "\n".join(o.text for o in t.on_screen)
    material = []
    if t.caption.strip():
        material.append(f"### Caption\n\n{t.caption.strip()}")
    material.append(f"### Transcript\n\n{speech}")
    if shown:
        material.append(f"### On-screen text\n\n{shown}")
    body = "\n\n".join(material)
    parts = [f"# Project idea: {title}"]
    if t.url:
        parts.append(f"Source: {t.url}")
    if t.hashtags:
        parts.append("Keywords: " + " ".join(f"#{h}" for h in t.hashtags))
    parts.append(f"## Source material\n\n{body}")
    parts.append(
        "## Potential requirements\n\nFill in or strike out:\n\n"
        + "\n".join(f"- [ ] {s}" for s in _REQUIREMENT_STUBS)
    )
    parts.append("## Open questions\n\n" + "\n".join(f"- {q}" for q in _QUESTIONS))
    prompts = [
        f"### Prompt {i}\n\n{p}\n\n<material>\n{body}\n</material>"
        for i, p in enumerate(_PROMPTS, 1)
    ]
    parts.append(
        "## Brainstorm prompts\n\nPaste into an LLM; the material is included.\n\n"
        + "\n\n".join(prompts)
    )
    return "\n\n".join(parts) + "\n"
