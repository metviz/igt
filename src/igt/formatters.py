import json
from typing import Callable

from igt.models import Transcript


def to_txt(t: Transcript) -> str:
    return "\n".join(text for seg in t.segments if (text := seg.text.strip()))


def _ts(seconds: float) -> str:
    ms = round(max(seconds, 0) * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def to_srt(t: Transcript) -> str:
    blocks: list[str] = []
    for seg in t.segments:
        text = seg.text.strip()
        if text:
            blocks.append(
                f"{len(blocks) + 1}\n{_ts(seg.start)} --> {_ts(seg.end)}\n{text}\n"
            )
    return "\n".join(blocks)


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
    title = " ".join(t.title.split()) or "Instagram transcript"
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
    parts.append("## Transcript\n\n" + "\n".join(cues))
    return "\n\n".join(parts) + "\n"


FORMATS: dict[str, Callable[[Transcript], str]] = {
    "txt": to_txt,
    "srt": to_srt,
    "json": to_json,
    "md": to_md,
}
