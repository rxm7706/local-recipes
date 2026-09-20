"""Unit tests for ``pyforge.core.atomic_write`` (Story 14.2, CAP-2).

Covers the intent contract's I/O & Edge-Case Matrix: happy paths (text /
bytes / callback), missing-parent-dir creation, ``write_fn`` failure
cleanup, ``os.replace`` failure cleanup, the ``mode`` chmod-before-replace
behavior, and -- the review-pass correction this story's re-derivation
exists to prove -- the UMASK-RESPECTING default applied when ``mode`` is
omitted (never a silent narrowing to ``mkstemp``'s private ``0o600``).
"""

from __future__ import annotations

import os
import threading
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


@pytest.mark.skipif(os.name != "posix", reason="umask semantics are POSIX-specific")
def test_atomic_write_no_mode_uses_umask_respecting_default_022(tmp_path):
    """Review-pass correction (Design Notes): ``mode=None`` (the default)
    must NOT leave the file at ``mkstemp``'s private ``0o600`` -- it must
    compute a umask-respecting default internally, exactly as if the temp
    file had been created via ``os.open(..., 0o666)`` in the first place."""
    old_umask = os.umask(0o022)
    try:
        target = tmp_path / "marker.txt"
        atomic_write_text(target, "x")
        assert target.stat().st_mode & 0o777 == 0o666 & ~0o022
        assert target.stat().st_mode & 0o777 != 0o600
    finally:
        os.umask(old_umask)


@pytest.mark.skipif(os.name != "posix", reason="umask semantics are POSIX-specific")
def test_atomic_write_no_mode_uses_umask_respecting_default_077(tmp_path):
    """Same guarantee under a stricter umask -- the default tracks whatever
    the CURRENT process umask is, not a fixed value."""
    old_umask = os.umask(0o077)
    try:
        target = tmp_path / "marker.bin"
        atomic_write_bytes(target, b"\x00")
        assert target.stat().st_mode & 0o777 == 0o666 & ~0o077
    finally:
        os.umask(old_umask)


@pytest.mark.skipif(os.name != "posix", reason="umask semantics are POSIX-specific")
def test_atomic_write_restores_the_process_umask_after_computing_the_default(tmp_path):
    """The umask probe (``os.umask(0)`` then restore) must leave the
    process-global umask exactly as it found it -- a leaked zero umask
    would loosen permissions for every other write in the process."""
    old_umask = os.umask(0o027)
    try:
        atomic_write_text(tmp_path / "marker.txt", "x")
        # Querying the umask is itself only possible via the same
        # set-and-read-back idiom; the probe must have restored 0o027.
        probed = os.umask(0)
        os.umask(probed)
        assert probed == 0o027
    finally:
        os.umask(old_umask)


@pytest.mark.skipif(os.name != "posix", reason="umask semantics are POSIX-specific")
def test_concurrent_atomic_writes_with_no_mode_never_corrupt_the_process_umask(tmp_path):
    """Review-pass-2 correction (Design Notes): the umask probe-and-restore
    pair, once centralized into the one shared primitive, runs on nearly
    every call site that omits ``mode=`` -- an unguarded interleaving of two
    threads' ``os.umask(0)``/restore can leave the PROCESS UMASK PERMANENTLY
    corrupted at ``0``, not just one write affected. Spawns several threads
    hammering ``atomic_write_text`` with ``mode=None`` concurrently and
    confirms the umask reads back the SAME value before and after -- no
    corruption -- and every written file still has the correct
    umask-respecting mode."""
    old_umask = os.umask(0o022)
    try:
        errors: list[Exception] = []

        def _write(i: int) -> None:
            try:
                atomic_write_text(tmp_path / f"marker-{i}.txt", f"payload-{i}")
            except Exception as exc:  # noqa: BLE001 -- captured for the main thread to re-raise
                errors.append(exc)

        threads = [threading.Thread(target=_write, args=(i,)) for i in range(32)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert not errors, f"concurrent atomic_write_text raised: {errors}"

        # The umask must have survived the concurrent run unchanged -- read
        # via the same set-and-restore idiom (there is no other way).
        probed = os.umask(0)
        os.umask(probed)
        assert probed == 0o022

        for i in range(32):
            target = tmp_path / f"marker-{i}.txt"
            assert target.read_text(encoding="utf-8") == f"payload-{i}"
            assert target.stat().st_mode & 0o777 == 0o666 & ~0o022
    finally:
        os.umask(old_umask)


def test_atomic_write_explicit_mode_still_overrides_the_default(tmp_path):
    """An explicit ``mode=`` (e.g. ``herald/registry.py`` preserving a
    pre-existing tracked file's bits) is unaffected by the umask-respecting
    default -- it always wins."""
    if os.name != "posix":
        pytest.skip("permission bits are POSIX-specific")
    old_umask = os.umask(0o022)
    try:
        target = tmp_path / "marker.txt"
        atomic_write_text(target, "x", mode=0o600)
        assert target.stat().st_mode & 0o777 == 0o600
    finally:
        os.umask(old_umask)
