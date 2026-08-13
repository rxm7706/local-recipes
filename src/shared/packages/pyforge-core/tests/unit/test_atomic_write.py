"""Unit tests for ``pyforge.core.atomic_write`` (Story 14.2, CAP-2).

Covers the intent contract's I/O & Edge-Case Matrix: happy paths (text /
bytes / callback), missing-parent-dir creation, ``write_fn`` failure
cleanup, ``os.replace`` failure cleanup, and the ``mode`` chmod-before-
replace behavior.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pyforge.core.atomic_write import (
    atomic_write,
    atomic_write_bytes,
    atomic_write_text,
)


def _leftovers(directory: Path, *keep: str) -> list[Path]:
    return [p for p in directory.iterdir() if p.name not in keep]


def test_atomic_write_text_happy_path_leaves_no_temp_file(tmp_path):
    target = tmp_path / "marker.txt"
    atomic_write_text(target, "hello\n")
    assert target.read_text(encoding="utf-8") == "hello\n"
    assert _leftovers(tmp_path, "marker.txt") == []


def test_atomic_write_bytes_happy_path_with_mode(tmp_path):
    target = tmp_path / "marker.bin"
    atomic_write_bytes(target, b"\x00\x01", mode=0o644)
    assert target.read_bytes() == b"\x00\x01"
    if os.name == "posix":
        assert target.stat().st_mode & 0o777 == 0o644
    assert _leftovers(tmp_path, "marker.bin") == []


def test_atomic_write_callback_happy_path_receives_unopened_path(tmp_path):
    target = tmp_path / "marker.json"
    seen: list[Path] = []

    def write_fn(tmp: Path) -> None:
        seen.append(tmp)
        # The primitive hands back a path that already exists (mkstemp) but
        # is empty -- the callback is free to open/populate it itself.
        assert tmp.exists()
        assert tmp.read_bytes() == b""
        tmp.write_text('{"a": 1}', encoding="utf-8")

    atomic_write(target, write_fn)
    assert seen and seen[0].parent == tmp_path
    assert target.read_text(encoding="utf-8") == '{"a": 1}'


def test_atomic_write_creates_missing_parent_dir(tmp_path):
    target = tmp_path / "nested" / "deeper" / "marker.txt"
    atomic_write_text(target, "x")
    assert target.read_text(encoding="utf-8") == "x"


def test_atomic_write_overwrites_existing_content(tmp_path):
    target = tmp_path / "marker.txt"
    target.write_text("old", encoding="utf-8")
    atomic_write_text(target, "new")
    assert target.read_text(encoding="utf-8") == "new"


def test_write_fn_raises_removes_temp_file_and_reraises_unchanged(tmp_path):
    target = tmp_path / "marker.txt"

    def boom(tmp: Path) -> None:
        raise ValueError("mid-write failure")

    with pytest.raises(ValueError, match="mid-write failure"):
        atomic_write(target, boom)
    assert not target.exists()
    assert _leftovers(tmp_path) == []


def test_os_replace_failure_removes_temp_file_and_reraises_oserror(tmp_path, monkeypatch):
    target = tmp_path / "marker.txt"

    def boom_replace(*_args, **_kwargs):
        raise OSError("simulated cross-device failure")

    monkeypatch.setattr(os, "replace", boom_replace)
    with pytest.raises(OSError, match="simulated cross-device failure"):
        atomic_write_text(target, "x")
    assert not target.exists()
    assert _leftovers(tmp_path) == []


def test_atomic_write_text_custom_encoding(tmp_path):
    target = tmp_path / "marker.txt"
    atomic_write_text(target, "héllo", encoding="utf-8")
    assert target.read_text(encoding="utf-8") == "héllo"


def test_atomic_write_no_mode_leaves_mkstemp_default_permissions(tmp_path):
    """``mode=None`` (the default) never chmods -- the file keeps whatever
    permissions ``os.replace`` carried over from the mkstemp temp file."""
    target = tmp_path / "marker.txt"
    atomic_write_text(target, "x")
    if os.name == "posix":
        assert target.stat().st_mode & 0o777 == 0o600
