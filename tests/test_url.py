import pytest

from igt.errors import InvalidUrlError
from igt.url import parse_instagram_url


@pytest.mark.parametrize(
    "raw,kind,code",
    [
        ("https://www.instagram.com/reel/ABC123xyz/", "reel", "ABC123xyz"),
        ("https://instagram.com/reel/ABC123xyz", "reel", "ABC123xyz"),
        ("https://www.instagram.com/p/Cx_9-aB/?igsh=MXx&utm_source=qr", "p", "Cx_9-aB"),
        ("https://www.instagram.com/tv/ZZ99/", "tv", "ZZ99"),
        ("https://www.instagram.com/some.user/reel/ABC123xyz/", "reel", "ABC123xyz"),
        ("  https://www.instagram.com/reel/ABC123xyz/  ", "reel", "ABC123xyz"),
        ("HTTPS://WWW.INSTAGRAM.COM/reel/ABC123xyz/", "reel", "ABC123xyz"),
        ("https://www.instagram.com/reels/Ddv7x-Yso_r/", "reel", "Ddv7x-Yso_r"),
        ("https://www.instagram.com/some.user/reels/ABC123xyz/", "reel", "ABC123xyz"),
    ],
)
def test_accepts_and_canonicalises(raw, kind, code):
    parsed = parse_instagram_url(raw)
    assert (parsed.kind, parsed.shortcode) == (kind, code)
    assert parsed.canonical == f"https://www.instagram.com/{kind}/{code}/"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "not a url",
        "https://www.instagram.com/",
        "https://www.instagram.com/someuser/",
        "https://www.instagram.com/stories/user/123/",
        "https://www.instagram.com/reel//",
        "https://www.instagram.com/reels/",  # the Reels feed, not a single reel
        "https://www.instagram.com/someuser/reels/",  # a profile's Reels tab
        "https://instagram.com.evil.com/reel/ABC/",
        "https://evilinstagram.com/reel/ABC/",
        "https://www.youtube.com/watch?v=abc",
        "ftp://www.instagram.com/reel/ABC/",
    ],
)
def test_rejects(raw):
    with pytest.raises(InvalidUrlError):
        parse_instagram_url(raw)
