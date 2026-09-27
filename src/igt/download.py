from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from igt.errors import DownloadError


@dataclass(frozen=True)
class Downloaded:
    audio_path: Path
    title: str


class Downloader(Protocol):
    def fetch(self, url: str, dest: Path) -> Downloaded: ...


def _first_download(info: dict | None) -> Downloaded | None:
    if not info:
        return None
    if info.get("_type") == "playlist":  # carousel: take the first entry that has media
        for entry in info.get("entries") or []:
            found = _first_download(entry)
            if found:
                return found
        return None
    downloads = info.get("requested_downloads")
    if downloads:
        return Downloaded(Path(downloads[0]["filepath"]), info.get("title") or "")
    return None


def _explain(message: str) -> str:
    low = message.lower()
    if "login" in low or "log in" in low or "cookies" in low:
        return (
            "Instagram requires login for this post. Pass --cookies-from BROWSER, "
            "or --cookies FILE (Netscape format) / set IGT_COOKIES_FILE."
        )
    if "429" in low or "rate-limit" in low or "rate limit" in low:
        return "Rate-limited by Instagram. Wait and retry."
    if "no video" in low:
        return "This post has no video to transcribe."
    return message.splitlines()[0] if message else "download failed"


class _SilentLogger:
    def debug(self, msg: str) -> None: ...
    def info(self, msg: str) -> None: ...
    def warning(self, msg: str) -> None: ...
    def error(self, msg: str) -> None: ...


class YtDlpDownloader:
    def __init__(
        self,
        cookies_file: Path | None = None,
        ydl_factory: Callable[[dict], Any] | None = None,
        cookies_from_browser: str | None = None,
    ):
        self._cookies = cookies_file
        self._factory = ydl_factory
        self._browser = cookies_from_browser

    def fetch(self, url: str, dest: Path) -> Downloaded:
        import yt_dlp

        opts: dict[str, Any] = {
            "format": "bestaudio/best",
            "outtmpl": str(dest / "%(id)s.%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "no_color": True,
            "logger": _SilentLogger(),  # quiet=True still prints ERROR lines; igt owns stderr
        }
        if self._browser:
            opts["cookiesfrombrowser"] = (self._browser,)
        elif self._cookies:
            opts["cookiefile"] = str(self._cookies)
        try:
            with (self._factory or yt_dlp.YoutubeDL)(opts) as ydl:
                info = ydl.extract_info(url, download=True)
        except yt_dlp.utils.DownloadError as exc:
            raise DownloadError(_explain(str(exc))) from exc
        found = _first_download(info)
        if found is None:
            raise DownloadError("This post has no video to transcribe.")
        return found
