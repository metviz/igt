import json
from typing import Callable

from igt.idea import _demote, to_idea
from igt.models import Transcript


def to_txt(t: Transcript) -> str:
    return "\n".join(text for seg in t.segments if (text := seg.text.strip()))


def _ts(seconds: float, sep: str = ",") -> str:
    ms = round(max(seconds, 0) * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02}{sep}{ms:03}"


def to_srt(t: Transcript) -> str:
    blocks: list[str] = []
    for seg in t.segments:
        text = seg.text.strip()
        if text:
            blocks.append(
                f"{len(blocks) + 1}\n{_ts(seg.start)} --> {_ts(seg.end)}\n{text}\n"
            )
    return "\n".join(blocks)


def to_vtt(t: Transcript) -> str:
    cues = [
        f"{_ts(s.start, '.')} --> {_ts(s.end, '.')}\n{text}\n"
        for s in t.segments
        if (text := s.text.strip())
    ]
    return "\n".join(["WEBVTT\n", *cues])


def _spans(t: Transcript) -> list[tuple[float, float | None]]:
    """(start, end) per on-screen item: ends when the next appears, else at the video's end."""
    starts = [o.start for o in t.on_screen]
    ends: list[float | None] = [*starts[1:], t.duration]
    if t.slides:
        return [(s, None) for s in starts]
    return [(s, e if e is not None and e > s else None) for s, e in zip(starts, ends)]


def _on_screen_json(t: Transcript) -> list[dict]:
    rows = []
    for o, (start, end) in zip(t.on_screen, _spans(t)):
        row = {"start": start, "end": end}
        if t.slides:
            row["slide"] = int(start) + 1
        rows.append({**row, "text": o.text})
    return rows


def to_json(t: Transcript) -> str:
    return json.dumps(
        {
            "platform": t.platform,
            "title": t.title,
            "source": t.source,
            "language": t.language,
            "url": t.url,
            "creator": t.creator,
            "upload_date": t.upload_date,
            "duration": t.duration,
            "caption": t.caption,
            "hashtags": list(t.hashtags),
            "segments": [
                {"start": s.start, "end": s.end, "text": s.text} for s in t.segments
            ],
            "on_screen": _on_screen_json(t),
            "formats": {"txt": to_txt(t)},
        },
        ensure_ascii=False,
        indent=2,
    )


def _clock(seconds: float) -> str:
    h, rem = divmod(int(max(seconds, 0)), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02}:{s:02}" if h else f"{m:02}:{s:02}"


def to_md(t: Transcript) -> str:
    title = " ".join(t.title.split()) or "Video transcript"
    parts = [f"# {title}"]
    if t.url:
        parts.append(f"Source: {t.url}")
    facts = [
        ("Creator", t.creator),
        ("Uploaded", t.upload_date),
        ("Duration", _clock(t.duration) if t.duration is not None else ""),
        ("Language", t.language),
        ("Hashtags", " ".join(f"#{h}" for h in t.hashtags)),
    ]
    lines = [f"- {label}: {value}" for label, value in facts if value]
    if lines:
        parts.append("\n".join(lines))
    if t.caption.strip():
        parts.append(f"## Caption\n\n{t.caption.strip()}")
    cues = [
        f"[{_clock(s.start)}] {s.text.strip()}" for s in t.segments if s.text.strip()
    ]
    if not t.slides:
        parts.append("## Transcript\n\n" + "\n".join(cues))
    if t.on_screen:
        shown = [
            f"[slide {int(o.start) + 1}] {o.text}" if t.slides
            else f"[{_clock(a)}{'-' + _clock(b) if b else ''}] {o.text}"
            for o, (a, b) in zip(t.on_screen, _spans(t))
        ]  # fmt: skip
        parts.append("## On-screen text\n\n" + "\n".join(shown))
    return "\n\n".join(parts) + "\n"


def to_llm_doc(t: Transcript, text: str) -> str:
    """Wrap model output (summary/chapters/social) under the video's title and source."""
    title = " ".join(t.title.split()) or "Video"
    head = f"# {title}" + (f"\n\nSource: {t.url}" if t.url else "")
    return f"{head}\n\n{_demote(text)}\n"


FORMATS: dict[str, Callable[[Transcript], str]] = {
    "txt": to_txt,
    "srt": to_srt,
    "vtt": to_vtt,
    "json": to_json,
    "md": to_md,
    "idea": to_idea,
}
