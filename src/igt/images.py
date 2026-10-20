import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from igt.errors import DownloadError

_CDN_SUFFIXES = (".cdninstagram.com", ".fbcdn.net")
_MAX_BYTES = 25_000_000  # per image
_SLIDE = re.compile(
    r'is_video\\+":(true|false),\\+"display_url\\+":\\+"(.*?)\\+"', re.DOTALL
)
_OWNER = re.compile(r'\\+"username\\+":\\+"([^\\"]+)')


@dataclass(frozen=True)
class ImagePost:
    paths: tuple[Path, ...]
    creator: str = ""


class ImageFetcher(Protocol):
    def fetch(self, shortcode: str, dest: Path) -> ImagePost: ...


def _unescape(raw: str) -> str:
    """The embed page escapes its JSON two or three levels deep; peel until flat."""
    for _ in range(4):
        if "\\" not in raw:
            break
        raw = json.loads(f'"{raw}"')
    return raw


def parse_embed(page: str) -> tuple[tuple[str, ...], str]:
    """(image URLs of the still slides in order, owner username) from an embed page."""
    # the post's own cover image repeats as slide 1, so drop duplicates (keep order)
    still = (_unescape(url) for video, url in _SLIDE.findall(page) if video == "false")
    urls = tuple(dict.fromkeys(still))
    owner = _OWNER.search(page)
    return urls, owner.group(1) if owner else ""


def _trusted(url: str) -> bool:
    parts = urlparse(url)
    return parts.scheme == "https" and (parts.hostname or "").endswith(_CDN_SUFFIXES)


class EmbedImageFetcher:
    """Reads a public post's slide images from its /embed/captioned/ page (no login)."""

    def __init__(self, opener: Callable = urlopen):
        self._open = opener

    def _get(self, url: str) -> bytes:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with self._open(req, timeout=30) as resp:
            return resp.read(_MAX_BYTES)

    def fetch(self, shortcode: str, dest: Path) -> ImagePost:
        try:
            html = self._get(
                f"https://www.instagram.com/p/{shortcode}/embed/captioned/"
            ).decode("utf-8", "replace")
            urls = [u for u in parse_embed(html)[0] if _trusted(u)]
            if not urls:
                raise DownloadError(
                    "no images found in this post (private or removed?)"
                )
            paths = []
            for i, url in enumerate(urls, 1):
                path = dest / f"slide{i:02}.jpg"
                path.write_bytes(self._get(url))
                paths.append(path)
        except OSError as exc:
            raise DownloadError(f"image download failed: {exc}") from exc
        return ImagePost(tuple(paths), parse_embed(html)[1])
