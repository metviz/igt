from pathlib import Path

import pytest
import yt_dlp

from igt.download import Downloaded, YtDlpDownloader
from igt.errors import DownloadError


def factory(info=None, raises=None, seen=None):
    class FakeYDL:
        def __init__(self, opts):
            if seen is not None:
                seen.update(opts)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def extract_info(self, url, download=True):
            if raises:
                raise raises
            return info

    return FakeYDL


def video(path="/x/a.m4a", title="My reel"):
    return {"title": title, "requested_downloads": [{"filepath": path}]}


def test_happy_path_returns_audio_path_and_title(tmp_path):
    d = YtDlpDownloader(ydl_factory=factory(video()))
    assert d.fetch("https://u", tmp_path) == Downloaded(Path("/x/a.m4a"), "My reel")


def test_options_noplaylist_dest_and_cookies(tmp_path):
    seen = {}
    cookies = tmp_path / "c.txt"
    YtDlpDownloader(cookies, factory(video(), seen=seen)).fetch("https://u", tmp_path)
    assert seen["noplaylist"] is True
    assert seen["cookiefile"] == str(cookies)
    assert seen["outtmpl"].startswith(str(tmp_path))
    assert seen["format"] == "bestaudio/best"


def test_no_cookiefile_option_when_unset(tmp_path):
    seen = {}
    YtDlpDownloader(ydl_factory=factory(video(), seen=seen)).fetch(
        "https://u", tmp_path
    )
    assert "cookiefile" not in seen


def test_carousel_picks_first_entry_with_a_download(tmp_path):
    info = {
        "_type": "playlist",
        "entries": [None, {"title": "no dl"}, video("/x/b.mp4", "slide2")],
    }
    got = YtDlpDownloader(ydl_factory=factory(info)).fetch("https://u", tmp_path)
    assert got == Downloaded(Path("/x/b.mp4"), "slide2")


def test_post_without_video_is_download_error(tmp_path):
    info = {"_type": "playlist", "entries": [None]}
    with pytest.raises(DownloadError, match="no video"):
        YtDlpDownloader(ydl_factory=factory(info)).fetch("https://u", tmp_path)


@pytest.mark.parametrize(
    "msg,expect",
    [
        ("ERROR: [Instagram] X: Login required to view this content", "--cookies"),
        (
            "ERROR: [Instagram] X: This content may be inappropriate: use --cookies",
            "--cookies",
        ),
        ("ERROR: There is no video in this post", "no video"),
        ("ERROR: HTTP Error 429: Too Many Requests", "Rate-limited"),
        ("ERROR: something odd\nsecond line", "something odd"),
    ],
)
def test_yt_dlp_errors_are_explained(tmp_path, msg, expect):
    boom = yt_dlp.utils.DownloadError(msg)
    with pytest.raises(DownloadError, match=expect):
        YtDlpDownloader(ydl_factory=factory(raises=boom)).fetch("https://u", tmp_path)


def test_ytdlp_logger_is_silent_so_igt_owns_stderr(tmp_path, capsys):
    seen = {}
    YtDlpDownloader(ydl_factory=factory(video(), seen=seen)).fetch("https://u", tmp_path)
    for level in ("debug", "info", "warning", "error"):
        getattr(seen["logger"], level)("noise")
    assert capsys.readouterr() == ("", "")


def test_cookies_from_browser_option_and_no_cookiefile(tmp_path):
    seen = {}
    YtDlpDownloader(
        cookies_from_browser="firefox", ydl_factory=factory(video(), seen=seen)
    ).fetch("https://u", tmp_path)
    assert seen["cookiesfrombrowser"] == ("firefox",)
    assert "cookiefile" not in seen


def test_login_hint_mentions_cookies_from(tmp_path):
    boom = yt_dlp.utils.DownloadError("ERROR: Login required")
    with pytest.raises(DownloadError, match="--cookies-from"):
        YtDlpDownloader(ydl_factory=factory(raises=boom)).fetch("https://u", tmp_path)


def test_metadata_extracted(tmp_path):
    info = {
        **video(),
        "uploader": "alice",
        "upload_date": "20260927",
        "duration": 32.5,
        "description": "Hi #a #b",
    }
    got = YtDlpDownloader(ydl_factory=factory(info)).fetch("https://u", tmp_path)
    assert (got.creator, got.upload_date, got.duration, got.caption) == (
        "alice",
        "2026-09-27",
        32.5,
        "Hi #a #b",
    )


def test_channel_is_creator_fallback(tmp_path):
    info = {**video(), "channel": "bob"}
    got = YtDlpDownloader(ydl_factory=factory(info)).fetch("https://u", tmp_path)
    assert got.creator == "bob"


def test_missing_or_malformed_metadata_defaults(tmp_path):
    info = {**video(), "upload_date": "bad", "duration": "x", "uploader": None}
    got = YtDlpDownloader(ydl_factory=factory(info)).fetch("https://u", tmp_path)
    assert (got.creator, got.upload_date, got.duration, got.caption) == (
        "",
        "",
        None,
        "",
    )
