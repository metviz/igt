from dataclasses import dataclass


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class Transcript:
    platform: str
    title: str
    source: str
    language: str
    segments: tuple[Segment, ...]
    url: str = ""
    creator: str = ""
    upload_date: str = ""  # ISO 8601 date, e.g. 2026-09-27
    duration: float | None = None  # seconds
    caption: str = ""
    hashtags: tuple[str, ...] = ()
