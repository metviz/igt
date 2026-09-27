import io
import json
import os

import pytest

from igt.cli import main
from igt.config import REPO_ROOT
from igt.errors import DownloadError, TranscribeError
from igt.models import Segment
from tests.fakes import FakeDownloader, FakeTranscriber

URL = "https://www.instagram.com/reel/ABC123xyz/"


def run(argv, env=None, downloader=None, transcriber=None):
    out, err = io.StringIO(), io.StringIO()
    code = main(
        argv,
        env=env or {},
        downloader=downloader or FakeDownloader(),
        transcriber=transcriber or FakeTranscriber(),
        stdout=out,
        stderr=err,
    )
    return code, out.getvalue(), err.getvalue()


def test_txt_to_stdout_by_default():
    code, out, err = run([URL])
    assert (code, out, err) == (0, "hello\nworld\n", "")


def test_srt_format():
    _, out, _ = run([URL, "--format", "srt"])
    assert out.startswith("1\n00:00:00,000 --> 00:00:01,500\nhello\n")


def test_json_format_parses():
    _, out, _ = run([URL, "--format", "json"])
    assert json.loads(out)["formats"]["txt"] == "hello\nworld"


def test_out_writes_file_named_by_shortcode_and_prints_path(tmp_path):
    code, out, _ = run(
        [URL, "--out", "--format", "srt"], env={"IGT_OUT_ROOT": str(tmp_path)}
    )
    target = tmp_path.resolve() / "ABC123xyz.srt"
    assert code == 0 and out.strip() == str(target)
    assert target.read_text(encoding="utf-8").startswith("1\n")


def test_out_without_root_fails_before_any_download():
    dl = FakeDownloader()
    code, out, err = run([URL, "--out"], downloader=dl)
    assert code == 3 and out == "" and "IGT_OUT_ROOT" in err
    assert dl.calls == 0


def test_out_root_inside_repo_rejected_before_download():
    dl = FakeDownloader()
    code, _, err = run(
        [URL, "--out"], env={"IGT_OUT_ROOT": str(REPO_ROOT / "out")}, downloader=dl
    )
    assert code == 3 and "inside the repository" in err and dl.calls == 0


def test_cookies_inside_repo_rejected():
    dl = FakeDownloader()
    code, _, err = run(
        [URL, "--cookies", str(REPO_ROOT / "cookies.txt")], downloader=dl
    )
    assert code == 3 and "cookies" in err and dl.calls == 0


def test_invalid_url_exit_2():
    code, out, err = run(["https://example.com/x"])
    assert code == 2 and out == "" and err.startswith("error:")


def test_login_walled_reel_exit_4_no_traceback():
    dl = FakeDownloader(
        fail=DownloadError("Instagram requires login ... --cookies FILE")
    )
    code, _, err = run([URL], downloader=dl)
    assert code == 4 and "--cookies" in err and "Traceback" not in err


def test_music_only_video_exit_5_and_no_output_file(tmp_path):
    tr = FakeTranscriber(segments=(Segment(0, 1, ""),))
    code, out, err = run(
        [URL, "--out"], env={"IGT_OUT_ROOT": str(tmp_path)}, transcriber=tr
    )
    assert code == 5 and "no speech" in err and out == ""
    assert list(tmp_path.iterdir()) == []


def test_transcribe_error_exit_5():
    code, _, err = run(
        [URL], transcriber=FakeTranscriber(raises=TranscribeError("boom"))
    )
    assert code == 5 and "boom" in err


def test_keyboard_interrupt_exit_130_and_tempdir_cleaned():
    dl = FakeDownloader()
    code, _, _ = run(
        [URL], downloader=dl, transcriber=FakeTranscriber(raises=KeyboardInterrupt())
    )
    assert code == 130 and not dl.dest.exists()


def test_out_root_is_a_file_fails_before_download(tmp_path):
    f = tmp_path / "file"
    f.write_text("x")
    dl = FakeDownloader()
    code, _, err = run([URL, "--out"], env={"IGT_OUT_ROOT": str(f)}, downloader=dl)
    assert code == 3 and err.startswith("error:") and "Traceback" not in err and dl.calls == 0


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores permission bits")
def test_out_root_read_only_fails_before_download(tmp_path):
    ro = tmp_path / "ro"
    ro.mkdir()
    ro.chmod(0o500)
    dl = FakeDownloader()
    try:
        code, _, err = run([URL, "--out"], env={"IGT_OUT_ROOT": str(ro)}, downloader=dl)
    finally:
        ro.chmod(0o700)
    assert code == 3 and "not writable" in err and dl.calls == 0


def test_symlinked_output_target_is_refused_not_followed(tmp_path):
    victim = tmp_path / "victim.txt"
    victim.write_text("keep")
    root = tmp_path / "root"
    root.mkdir()
    (root / "ABC123xyz.txt").symlink_to(victim)
    dl = FakeDownloader()
    code, _, err = run([URL, "--out"], env={"IGT_OUT_ROOT": str(root)}, downloader=dl)
    assert code == 3 and "symlink" in err and victim.read_text() == "keep" and dl.calls == 0


def test_missing_cookies_flag_file_rejected_and_not_created(tmp_path):
    missing = tmp_path / "typo.txt"
    dl = FakeDownloader()
    code, _, err = run([URL, "--cookies", str(missing)], downloader=dl)
    assert code == 3 and "not found" in err and not missing.exists() and dl.calls == 0


def test_missing_cookies_env_file_rejected(tmp_path):
    dl = FakeDownloader()
    code, _, err = run([URL], env={"IGT_COOKIES_FILE": str(tmp_path / "nope.txt")}, downloader=dl)
    assert code == 3 and "not found" in err and dl.calls == 0


def test_cookies_from_is_wired_to_the_default_downloader(monkeypatch):
    seen = {}

    class Recorder(FakeDownloader):
        def __init__(self, cookies=None, cookies_from_browser=None):
            super().__init__()
            seen.update(cookies=cookies, browser=cookies_from_browser)

    monkeypatch.setattr("igt.cli.YtDlpDownloader", Recorder)
    code = main(
        [URL, "--cookies-from", "firefox"],
        env={},
        transcriber=FakeTranscriber(),
        stdout=io.StringIO(),
        stderr=io.StringIO(),
    )
    assert code == 0 and seen == {"cookies": None, "browser": "firefox"}


def test_cookies_from_ignores_env_cookies_file(monkeypatch, tmp_path):
    seen = {}

    class Recorder(FakeDownloader):
        def __init__(self, cookies=None, cookies_from_browser=None):
            super().__init__()
            seen.update(cookies=cookies)

    monkeypatch.setattr("igt.cli.YtDlpDownloader", Recorder)
    main(
        [URL, "--cookies-from", "chrome"],
        env={"IGT_COOKIES_FILE": str(tmp_path / "gone.txt")},
        transcriber=FakeTranscriber(),
        stdout=io.StringIO(),
        stderr=io.StringIO(),
    )
    assert seen["cookies"] is None


@pytest.mark.parametrize(
    "argv",
    [
        [URL, "--cookies", "x.txt", "--cookies-from", "firefox"],
        [URL, "--cookies-from", "netscape"],
    ],
)
def test_cookies_from_bad_usage_exits_2(argv):
    with pytest.raises(SystemExit) as exc:
        main(argv, env={})
    assert exc.value.code == 2
