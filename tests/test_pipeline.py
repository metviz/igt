import pytest

from igt.errors import DownloadError, InvalidUrlError, NoSpeechError, TranscribeError
from igt.models import Segment
from igt.pipeline import generate
from tests.fakes import FakeDownloader, FakeTranscriber

URL = "https://www.instagram.com/reel/ABC123xyz/?igsh=tracking"


def test_builds_transcript_and_sends_canonical_url_to_downloader():
    dl, tr = FakeDownloader(title="My reel"), FakeTranscriber(language="hi")
    t = generate(URL, downloader=dl, transcriber=tr, language="hi")
    assert dl.url == "https://www.instagram.com/reel/ABC123xyz/"
    assert (t.platform, t.source, t.title, t.language) == (
        "instagram",
        "local-whisper",
        "My reel",
        "hi",
    )
    assert [s.text for s in t.segments] == ["hello", "world"]
    assert tr.seen_language == "hi"


def test_invalid_url_fails_before_download():
    dl = FakeDownloader()
    with pytest.raises(InvalidUrlError):
        generate("https://example.com/x", downloader=dl, transcriber=FakeTranscriber())
    assert dl.calls == 0


def test_tempdir_removed_on_success():
    dl = FakeDownloader()
    generate(URL, downloader=dl, transcriber=FakeTranscriber())
    assert not dl.dest.exists()


def test_tempdir_removed_on_download_failure():
    dl = FakeDownloader(fail=DownloadError("nope"))
    with pytest.raises(DownloadError):
        generate(URL, downloader=dl, transcriber=FakeTranscriber())
    assert not dl.dest.exists()


def test_tempdir_removed_on_transcribe_failure():
    dl = FakeDownloader()
    with pytest.raises(TranscribeError):
        generate(
            URL, downloader=dl, transcriber=FakeTranscriber(raises=TranscribeError("x"))
        )
    assert not dl.dest.exists()


@pytest.mark.parametrize("segments", [(), (Segment(0, 1, "  "), Segment(1, 2, ""))])
def test_music_only_video_is_no_speech_error(segments):
    with pytest.raises(NoSpeechError, match="no speech"):
        generate(
            URL,
            downloader=FakeDownloader(),
            transcriber=FakeTranscriber(segments=segments),
        )


def test_metadata_flows_into_transcript_with_deduped_hashtags():
    meta = dict(
        creator="alice",
        upload_date="2026-09-27",
        duration=32.5,
        caption="Hi #Reels #tips #Reels!",
    )
    dl = FakeDownloader(meta=meta)
    t = generate(URL, downloader=dl, transcriber=FakeTranscriber())
    assert t.url == "https://www.instagram.com/reel/ABC123xyz/"
    assert (t.creator, t.upload_date, t.duration, t.caption) == (
        "alice",
        "2026-09-27",
        32.5,
        "Hi #Reels #tips #Reels!",
    )
    assert t.hashtags == ("Reels", "tips")


def test_extractor_sees_downloaded_media_and_result_lands_on_transcript():
    from tests.fakes import FakeExtractor

    ex = FakeExtractor([(1.0, "SALE")])
    dl = FakeDownloader()
    t = generate(URL, downloader=dl, transcriber=FakeTranscriber(), extractor=ex)
    assert [(o.start, o.text) for o in t.on_screen] == [(1.0, "SALE")]
    assert ex.video.name == "a.m4a" and not dl.dest.exists()


def test_no_extractor_means_no_on_screen():
    t = generate(URL, downloader=FakeDownloader(), transcriber=FakeTranscriber())
    assert t.on_screen == ()


def test_silent_video_with_on_screen_text_is_not_an_error():
    from tests.fakes import FakeExtractor

    t = generate(
        URL,
        downloader=FakeDownloader(),
        transcriber=FakeTranscriber(segments=()),
        extractor=FakeExtractor([(0.0, "ONLY TEXT")]),
    )
    assert t.segments == () and t.on_screen[0].text == "ONLY TEXT"


def test_keep_callback_gets_the_downloaded_file_before_cleanup():
    seen = []

    def keep(path):
        seen.append((path.name, path.read_bytes()))

    dl = FakeDownloader()
    generate(URL, downloader=dl, transcriber=FakeTranscriber(), keep=keep)
    assert seen == [("a.m4a", b"audio")]
    assert not dl.dest.exists()


def _no_video_dl():
    from igt.errors import NoVideoError

    return FakeDownloader(fail=NoVideoError("no video"))


def test_image_post_falls_back_to_slide_ocr():
    from tests.fakes import FakeExtractor, FakeImageFetcher

    ex = FakeExtractor([(0, "Prompt one"), (1, "Prompt two")])
    imgs = FakeImageFetcher(["a", "b"], creator="gptprompts.ai")
    tr = FakeTranscriber()
    t = generate(
        URL.replace("reel", "p"), downloader=_no_video_dl(), transcriber=tr,
        extractor=ex, images=imgs,
    )  # fmt: skip
    assert imgs.shortcode == "ABC123xyz"
    assert (t.slides, t.segments, t.creator, t.platform) == (
        True, (), "gptprompts.ai", "instagram",
    )  # fmt: skip
    assert [o.text for o in t.on_screen] == ["Prompt one", "Prompt two"]
    assert tr.seen_language is None  # nothing to transcribe
    assert not imgs.calls == 0 and not ex.images[0].exists()  # temp dir removed


def test_no_video_without_ocr_or_fetcher_still_raises():
    from igt.errors import NoVideoError
    from tests.fakes import FakeExtractor, FakeImageFetcher

    for kw in ({}, {"extractor": FakeExtractor()}, {"images": FakeImageFetcher()}):
        with pytest.raises(NoVideoError):
            generate(
                URL, downloader=_no_video_dl(), transcriber=FakeTranscriber(), **kw
            )


def test_image_post_with_no_text_is_no_speech_error():
    from tests.fakes import FakeExtractor, FakeImageFetcher

    with pytest.raises(NoSpeechError, match="images"):
        generate(
            URL, downloader=_no_video_dl(), transcriber=FakeTranscriber(),
            extractor=FakeExtractor(), images=FakeImageFetcher(["a"]),
        )  # fmt: skip
