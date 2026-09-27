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
