import os

import pytest

from igt.config import REPO_ROOT, env_path, outside, out_base
from igt.errors import ConfigError


def test_unset_out_root_falls_back_to_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert out_base({}, REPO_ROOT) == tmp_path.resolve()


def test_empty_out_root_falls_back_to_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert out_base({"IGT_OUT_ROOT": ""}, REPO_ROOT) == tmp_path.resolve()


def test_unset_out_root_with_cwd_inside_repo_rejected(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    with pytest.raises(ConfigError, match="inside the repository"):
        out_base({}, REPO_ROOT)


def test_env_root_wins_over_cwd(tmp_path, monkeypatch):
    other = tmp_path / "cwd"
    other.mkdir()
    monkeypatch.chdir(other)
    assert out_base({"IGT_OUT_ROOT": str(tmp_path)}, REPO_ROOT) == tmp_path.resolve()


def test_out_root_inside_repo_rejected():
    with pytest.raises(ConfigError, match="inside the repository"):
        out_base({"IGT_OUT_ROOT": str(REPO_ROOT / "out")}, REPO_ROOT)


def test_out_root_equal_to_repo_rejected():
    with pytest.raises(ConfigError, match="inside the repository"):
        out_base({"IGT_OUT_ROOT": str(REPO_ROOT)}, REPO_ROOT)


def test_symlink_into_repo_rejected(tmp_path):
    link = tmp_path / "link"
    os.symlink(REPO_ROOT / "out", link)
    with pytest.raises(ConfigError, match="inside the repository"):
        out_base({"IGT_OUT_ROOT": str(link)}, REPO_ROOT)


def test_out_root_outside_repo_ok(tmp_path):
    assert out_base({"IGT_OUT_ROOT": str(tmp_path)}, REPO_ROOT) == tmp_path.resolve()


def test_env_path_unset_is_none():
    assert env_path({}, "IGT_COOKIES_FILE", REPO_ROOT) is None


def test_env_path_expands_tilde(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert env_path({"X": "~/c.txt"}, "X", REPO_ROOT) == tmp_path.resolve() / "c.txt"


def test_outside_names_what_was_rejected():
    with pytest.raises(ConfigError, match="cookies"):
        outside(REPO_ROOT / "c.txt", REPO_ROOT, "cookies")


def test_repo_root_is_the_project_checkout():
    assert (REPO_ROOT / "pyproject.toml").is_file()
    assert (REPO_ROOT / "src" / "igt" / "config.py").is_file()
