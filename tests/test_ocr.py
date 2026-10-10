import subprocess
from pathlib import Path

import pytest

from igt.errors import ConfigError, DownloadError
from igt.ocr import TesseractExtractor


class Runner:
    """Fake subprocess.run: ffmpeg writes frames, tesseract returns queued text."""

    def __init__(self, texts, ffmpeg_rc=0):
        self.texts, self.ffmpeg_rc, self.calls = list(texts), ffmpeg_rc, []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        if cmd[0] == "ffmpeg":
            if self.ffmpeg_rc:
                return subprocess.CompletedProcess(cmd, self.ffmpeg_rc, "", "boom")
            pattern = Path(cmd[-1])
            for i in range(1, len(self.texts) + 1):
                (pattern.parent / (pattern.name % i)).write_bytes(b"png")
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return subprocess.CompletedProcess(cmd, 0, self.texts.pop(0), "")


def ex(texts, every=2.0, which=lambda n: f"/usr/bin/{n}", **kw):
    return TesseractExtractor(every=every, runner=Runner(texts, **kw), which=which)


def video(tmp_path):
    v = tmp_path / "v.mp4"
    v.write_bytes(b"v")
    return v


def test_timestamps_follow_sampling_interval(tmp_path):
    out = ex(["Hello world", "", "Second slide"], every=2.5).extract(video(tmp_path))
    assert [(o.start, o.text) for o in out] == [
        (0.0, "Hello world"),
        (5.0, "Second slide"),
    ]


def test_consecutive_duplicates_collapse_but_returning_text_is_kept(tmp_path):
    out = ex(["Sale now", "sale  NOW\n", "Sale now", "Other text", "Sale now"]).extract(
        video(tmp_path)
    )
    assert [o.start for o in out] == [0.0, 6.0, 8.0]


def test_whitespace_normalised_and_noise_dropped(tmp_path):
    out = ex(["  a\n b  ", "|\\ ~", "Real  caption\ntext"]).extract(video(tmp_path))
    assert [o.text for o in out] == ["Real caption text"]


@pytest.mark.parametrize("missing", ["ffmpeg", "tesseract"])
def test_missing_tool_is_config_error(tmp_path, missing):
    e = ex([], which=lambda n: None if n == missing else "/x")
    with pytest.raises(ConfigError, match=missing):
        e.check()
    with pytest.raises(ConfigError, match=missing):
        e.extract(video(tmp_path))


def test_ffmpeg_failure_is_download_error(tmp_path):
    with pytest.raises(DownloadError):
        ex(["x"], ffmpeg_rc=1).extract(video(tmp_path))


def test_rapidocr_joins_boxes_and_dedupes(tmp_path):
    from igt.ocr import RapidOcrExtractor

    answers = iter(
        [[[None, "BIG", 0.9], [None, "SALE", 0.9]], None, [[None, "BIG SALE", 1]]]
    )
    e = RapidOcrExtractor(
        every=1.0,
        runner=Runner(["", "", ""]),
        which=lambda n: "/x",
        engine_factory=lambda: lambda path: (next(answers), None),
    )
    out = e.extract(video(tmp_path))
    assert [(o.start, o.text) for o in out] == [(0.0, "BIG SALE")]


def test_rapidocr_missing_package_is_config_error(monkeypatch):
    import sys

    from igt.ocr import RapidOcrExtractor

    monkeypatch.setitem(sys.modules, "rapidocr_onnxruntime", None)
    with pytest.raises(ConfigError, match="igt\\[rapidocr\\]"):
        RapidOcrExtractor(which=lambda n: "/x").check()
