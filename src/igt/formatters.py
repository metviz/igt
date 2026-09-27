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
            "segments": [
                {"start": s.start, "end": s.end, "text": s.text} for s in t.segments
            ],
            "formats": {"txt": to_txt(t)},
        },
        ensure_ascii=False,
        indent=2,
    )


FORMATS: dict[str, Callable[[Transcript], str]] = {
    "txt": to_txt,
    "srt": to_srt,
    "json": to_json,
}
