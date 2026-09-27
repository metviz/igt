import re
from dataclasses import dataclass
from urllib.parse import urlparse

from igt.errors import InvalidUrlError

_HOSTS = {"instagram.com", "www.instagram.com"}
_PATH = re.compile(r"^/(?:[A-Za-z0-9._]+/)?(reels?|p|tv)/([A-Za-z0-9_-]+)/?$")


@dataclass(frozen=True)
class ParsedUrl:
    kind: str
    shortcode: str
    canonical: str


def parse_instagram_url(raw: str) -> ParsedUrl:
    parts = urlparse(raw.strip())
    if parts.scheme not in ("http", "https") or (parts.hostname or "") not in _HOSTS:
        raise InvalidUrlError(f"not an Instagram URL: {raw!r}")
    match = _PATH.match(parts.path)
    if not match:
        raise InvalidUrlError(f"not a reel/post/tv URL: {raw!r}")
    kind, code = match.groups()
    kind = "reel" if kind == "reels" else kind
    return ParsedUrl(kind, code, f"https://www.instagram.com/{kind}/{code}/")
