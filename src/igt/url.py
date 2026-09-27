import re
from dataclasses import dataclass
from urllib.parse import ParseResult, parse_qs, urlparse

from igt.errors import InvalidUrlError

_INSTAGRAM_HOSTS = {"instagram.com", "www.instagram.com"}
_INSTAGRAM_PATH = re.compile(r"^/(?:[A-Za-z0-9._]+/)?(reels?|p|tv)/([A-Za-z0-9_-]+)/?$")

_YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com"}
_YOUTUBE_SHORT_HOSTS = {"youtu.be"}
_YOUTUBE_WATCH_PATH = re.compile(r"^/watch/?$")
_YOUTUBE_SHORTS_PATH = re.compile(r"^/shorts/([A-Za-z0-9_-]+)/?$")
_YOUTUBE_ID = re.compile(r"[A-Za-z0-9_-]+")

_FACEBOOK_HOSTS = {
    "facebook.com",
    "www.facebook.com",
    "m.facebook.com",
    "web.facebook.com",
}
_FACEBOOK_SHORT_HOSTS = {"fb.watch"}
_FACEBOOK_REEL_PATH = re.compile(r"^/reel/(\d+)/?$")
_FACEBOOK_VIDEOS_PATH = re.compile(r"^/(?:[A-Za-z0-9.]+/)?videos/(\d+)/?$")
_FACEBOOK_WATCH_PATH = re.compile(r"^/watch/?$")
_FACEBOOK_SHORT_ID = re.compile(
    r"[A-Za-z0-9]+"
)  # fb.watch shortcodes are opaque, not video ids


@dataclass(frozen=True)
class ParsedUrl:
    platform: str
    kind: str
    shortcode: str
    canonical: str


def _parse_instagram(parts: ParseResult) -> ParsedUrl | None:
    if (parts.hostname or "") not in _INSTAGRAM_HOSTS:
        return None
    match = _INSTAGRAM_PATH.match(parts.path)
    if not match:
        raise InvalidUrlError(f"not a reel/post/tv URL: {parts.geturl()!r}")
    kind, code = match.groups()
    kind = "reel" if kind == "reels" else kind
    return ParsedUrl(
        "instagram", kind, code, f"https://www.instagram.com/{kind}/{code}/"
    )


def _parse_youtube(parts: ParseResult) -> ParsedUrl | None:
    host = parts.hostname or ""
    if host in _YOUTUBE_SHORT_HOSTS:
        code = parts.path.strip("/")
        if code and _YOUTUBE_ID.fullmatch(code):
            return ParsedUrl(
                "youtube", "video", code, f"https://www.youtube.com/watch?v={code}"
            )
        raise InvalidUrlError(f"not a YouTube video URL: {parts.geturl()!r}")
    if host not in _YOUTUBE_HOSTS:
        return None
    shorts = _YOUTUBE_SHORTS_PATH.match(parts.path)
    if shorts:
        code = shorts.group(1)
        return ParsedUrl(
            "youtube", "shorts", code, f"https://www.youtube.com/shorts/{code}"
        )
    if _YOUTUBE_WATCH_PATH.match(parts.path):
        code = (parse_qs(parts.query).get("v") or [""])[0]
        if code and _YOUTUBE_ID.fullmatch(code):
            return ParsedUrl(
                "youtube", "video", code, f"https://www.youtube.com/watch?v={code}"
            )
    raise InvalidUrlError(f"not a YouTube watch/shorts URL: {parts.geturl()!r}")


def _parse_facebook(parts: ParseResult) -> ParsedUrl | None:
    host = parts.hostname or ""
    if host in _FACEBOOK_SHORT_HOSTS:
        code = parts.path.strip("/")
        if code and _FACEBOOK_SHORT_ID.fullmatch(code):
            return ParsedUrl("facebook", "video", code, f"https://fb.watch/{code}")
        raise InvalidUrlError(f"not a Facebook video URL: {parts.geturl()!r}")
    if host not in _FACEBOOK_HOSTS:
        return None
    reel = _FACEBOOK_REEL_PATH.match(parts.path)
    if reel:
        code = reel.group(1)
        return ParsedUrl(
            "facebook", "reel", code, f"https://www.facebook.com/reel/{code}/"
        )
    videos = _FACEBOOK_VIDEOS_PATH.match(parts.path)
    if videos:
        code = videos.group(1)
        return ParsedUrl(
            "facebook", "video", code, f"https://www.facebook.com/watch/?v={code}"
        )
    if _FACEBOOK_WATCH_PATH.match(parts.path):
        code = (parse_qs(parts.query).get("v") or [""])[0]
        if code.isdigit():
            return ParsedUrl(
                "facebook", "video", code, f"https://www.facebook.com/watch/?v={code}"
            )
    raise InvalidUrlError(f"not a Facebook reel/video URL: {parts.geturl()!r}")


def parse_video_url(raw: str) -> ParsedUrl:
    parts = urlparse(raw.strip())
    if parts.scheme not in ("http", "https"):
        raise InvalidUrlError(f"not an Instagram, YouTube or Facebook URL: {raw!r}")
    for parser in (_parse_instagram, _parse_youtube, _parse_facebook):
        result = parser(parts)
        if result is not None:
            return result
    raise InvalidUrlError(f"not an Instagram, YouTube or Facebook URL: {raw!r}")
