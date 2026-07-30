"""Unit tests for ``pyforge.marshal.adapters.fs_local`` (Story 1.4,
AD-4/AD-11) -- ``LocalFs`` against real ``tmp_path`` I/O.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from pyforge.marshal.adapters.fs_local import FsWriteError, LocalFs


@pytest.fixture
def fs() -> LocalFs:
    return LocalFs()


# --- read_text -----------------------------------------------------------------


def test_read_text_returns_none_for_missing_file(fs, tmp_path):
    assert fs.read_text(tmp_path / "absent.txt") is None


def test_read_text_returns_existing_content(fs, tmp_path):
    target = tmp_path / "marker"
    target.write_text("acme\n", encoding="utf-8")
    assert fs.read_text(target) == "acme\n"


def test_read_text_raises_fs_write_error_when_path_is_a_directory(fs, tmp_path):
    directory = tmp_path / "a-dir"
    directory.mkdir()
    with pytest.raises(FsWriteError):
        fs.read_text(directory)


# --- write_text_atomic -----------------------------------------------------------


def test_write_text_atomic_creates_parent_dirs_and_writes(fs, tmp_path):
    target = tmp_path / "nested" / "deeper" / "marker"
    fs.write_text_atomic(target, "acme\n")
    assert target.read_text(encoding="utf-8") == "acme\n"


def test_write_text_atomic_overwrites_existing_content(fs, tmp_path):
    target = tmp_path / "marker"
    target.write_text("old\n", encoding="utf-8")
    fs.write_text_atomic(target, "new\n")
    assert target.read_text(encoding="utf-8") == "new\n"


def test_write_text_atomic_leaves_no_temp_file_behind(fs, tmp_path):
    target = tmp_path / "marker"
    fs.write_text_atomic(target, "acme\n")
    leftovers = [p for p in tmp_path.iterdir() if p.name != "marker"]
    assert leftovers == []


def test_write_text_atomic_raises_fs_write_error_on_unwritable_target(fs, tmp_path):
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("occupied", encoding="utf-8")
    with pytest.raises(FsWriteError):
        fs.write_text_atomic(blocked / "marker", "x")


# --- read_symlink_target -----------------------------------------------------------


def test_read_symlink_target_none_for_missing_path(fs, tmp_path):
    assert fs.read_symlink_target(tmp_path / "absent") is None


def test_read_symlink_target_none_for_a_real_file(fs, tmp_path):
    real = tmp_path / "real.txt"
    real.write_text("x", encoding="utf-8")
    assert fs.read_symlink_target(real) is None


def test_read_symlink_target_returns_raw_relative_target(fs, tmp_path):
    link = tmp_path / "link"
    os.symlink(Path("projects/acme/planning-artifacts"), link)
    assert fs.read_symlink_target(link) == Path("projects/acme/planning-artifacts")


# --- repoint_symlink_atomic -----------------------------------------------------


def test_repoint_symlink_atomic_creates_a_new_symlink(fs, tmp_path):
    link = tmp_path / "link"
    target = Path("projects/acme/planning-artifacts")
    fs.repoint_symlink_atomic(link, target)
    assert link.is_symlink()
    assert Path(os.readlink(link)) == target


def test_repoint_symlink_atomic_repoints_an_existing_symlink(fs, tmp_path):
    link = tmp_path / "link"
    os.symlink(Path("projects/old/planning-artifacts"), link)
    fs.repoint_symlink_atomic(link, Path("projects/new/planning-artifacts"))
    assert Path(os.readlink(link)) == Path("projects/new/planning-artifacts")


def test_repoint_symlink_atomic_creates_parent_dirs(fs, tmp_path):
    link = tmp_path / "nested" / "deeper" / "link"
    fs.repoint_symlink_atomic(link, Path("projects/acme/planning-artifacts"))
    assert link.is_symlink()


def test_repoint_symlink_atomic_leaves_no_temp_symlink_behind(fs, tmp_path):
    link = tmp_path / "link"
    fs.repoint_symlink_atomic(link, Path("projects/acme/planning-artifacts"))
    leftovers = [p for p in tmp_path.iterdir() if p.name != "link"]
    assert leftovers == []


def test_repoint_symlink_atomic_refuses_a_real_directory(fs, tmp_path):
    link = tmp_path / "link"
    link.mkdir()
    (link / "real-content.txt").write_text("keep me", encoding="utf-8")
    with pytest.raises(FsWriteError):
        fs.repoint_symlink_atomic(link, Path("projects/acme/planning-artifacts"))
    # the real directory and its content must survive the refusal
    assert (link / "real-content.txt").read_text(encoding="utf-8") == "keep me"


def test_repoint_symlink_atomic_refuses_a_real_file(fs, tmp_path):
    link = tmp_path / "link"
    link.write_text("real content", encoding="utf-8")
    with pytest.raises(FsWriteError):
        fs.repoint_symlink_atomic(link, Path("projects/acme/planning-artifacts"))
    assert link.read_text(encoding="utf-8") == "real content"


# --- is_dir ----------------------------------------------------------------------


def test_is_dir_true_for_a_directory(fs, tmp_path):
    assert fs.is_dir(tmp_path) is True


def test_is_dir_false_for_a_file(fs, tmp_path):
    target = tmp_path / "file.txt"
    target.write_text("x", encoding="utf-8")
    assert fs.is_dir(target) is False


def test_is_dir_false_for_missing_path(fs, tmp_path):
    assert fs.is_dir(tmp_path / "absent") is False
