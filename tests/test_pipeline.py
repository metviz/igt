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
