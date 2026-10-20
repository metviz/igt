import json
from pathlib import Path

import pytest

from igt.errors import DownloadError
from igt.images import EmbedImageFetcher, parse_embed

CDN = "https://scontent-atl3-1.cdninstagram.com/v/t51/{}_n.heic?a=1&b=2%3D%3D"


def page(*children, owner="gptprompts.ai"):
    """Embed HTML: the media JSON is escaped twice, as Instagram serves it."""
    edges = [
        {"node": {"is_video": video, "display_url": CDN.format(name)}}
        for name, video in children
    ]
    media = {"owner": {"username": owner}, "edge_sidecar_to_children": {"edges": edges}}
    inner = json.dumps({"gql_data": {"shortcode_media": media}}, separators=(",", ":"))
    return "<script>x=" + json.dumps(inner) + "</script>"


def test_parse_embed_returns_slide_urls_in_order():
    urls, creator = parse_embed(page(("a", False), ("b", False), ("c", False)))
    assert urls == (CDN.format("a"), CDN.format("b"), CDN.format("c"))
    assert creator == "gptprompts.ai"


def test_parse_embed_skips_video_slides():
    urls, _ = parse_embed(page(("a", False), ("v", True), ("c", False)))
    assert urls == (CDN.format("a"), CDN.format("c"))


def test_parse_embed_without_media_is_empty():
    assert parse_embed("<html>nothing</html>") == ((), "")


class Resp:
    def __init__(self, body: bytes):
        self.body = body

    def read(self, n=-1):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def opener_for(html: str, seen: list):
    def opener(req, timeout=None):
        url = req if isinstance(req, str) else req.full_url
        seen.append(url)
        return Resp(html.encode() if "/embed/" in url else b"\xff\xd8jpeg")

    return opener


def test_fetch_downloads_each_slide(tmp_path):
    seen: list = []
    fetcher = EmbedImageFetcher(
        opener=opener_for(page(("a", False), ("b", False)), seen)
    )
    post = fetcher.fetch("DdvJOwDEw4Q", tmp_path)
    assert seen[0] == "https://www.instagram.com/p/DdvJOwDEw4Q/embed/captioned/"
    assert [p.name for p in post.paths] == ["slide01.jpg", "slide02.jpg"]
    assert all(p.read_bytes() == b"\xff\xd8jpeg" for p in post.paths)
    assert post.creator == "gptprompts.ai"


def test_fetch_no_images_is_download_error(tmp_path):
    fetcher = EmbedImageFetcher(opener=opener_for("<html></html>", []))
    with pytest.raises(DownloadError, match="no images"):
        fetcher.fetch("DdvJOwDEw4Q", tmp_path)


def test_fetch_refuses_non_cdn_hosts(tmp_path):
    evil = page(("a", False)).replace(
        "scontent-atl3-1.cdninstagram.com", "evil.example"
    )
    with pytest.raises(DownloadError, match="no images"):
        EmbedImageFetcher(opener=opener_for(evil, [])).fetch("DdvJOwDEw4Q", tmp_path)


def test_fetch_network_failure_is_download_error(tmp_path):
    def boom(req, timeout=None):
        raise OSError("down")

    with pytest.raises(DownloadError, match="down"):
        EmbedImageFetcher(opener=boom).fetch("DdvJOwDEw4Q", tmp_path)


def test_parse_embed_drops_repeated_cover():
    html = page(("a", False), ("a", False), ("b", False))
    assert parse_embed(html)[0] == (CDN.format("a"), CDN.format("b"))
