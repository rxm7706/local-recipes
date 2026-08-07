"""Unit tests for ``pyforge.marshal.adapters.fs_local`` (Story 1.4,
AD-4/AD-11) -- ``LocalFs`` against real ``tmp_path`` I/O.
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

import pytest

from pyforge.marshal.adapters.fs_local import (
    DirectoryAlreadyExistsError,
    FsError,
    LocalFs,
    _tmp_sibling,
)
from pyforge.marshal.core.egress import Redacted
from pyforge.marshal.ports.fs import AdvisoryLock


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


def test_read_text_raises_fs_error_when_path_is_a_directory(fs, tmp_path):
    directory = tmp_path / "a-dir"
    directory.mkdir()
    with pytest.raises(FsError):
        fs.read_text(directory)


def test_read_text_wraps_undecodable_bytes(fs, tmp_path):
    """Review finding: UnicodeDecodeError is a ValueError, not an OSError --
    a corrupt (non-UTF-8) marker previously escaped as a raw traceback."""
    target = tmp_path / "marker"
    target.write_bytes(b"\xff\xfe not utf-8")
    with pytest.raises(FsError):
        fs.read_text(target)


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


def test_write_text_atomic_raises_fs_error_on_unwritable_target(fs, tmp_path):
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("occupied", encoding="utf-8")
    with pytest.raises(FsError):
        fs.write_text_atomic(blocked / "marker", "x")


def test_write_text_atomic_survives_a_stale_temp_file(fs, tmp_path):
    """Review finding: a stale leftover temp file from a crashed,
    pid-recycled run made the O_EXCL open fail on EVERY subsequent attempt
    -- permanent-until-manual-cleanup. Any file at the tmp name cannot
    belong to a live writer, so it is cleared first."""
    target = tmp_path / "marker"
    stale = _tmp_sibling(target)
    stale.write_text("stale leftover", encoding="utf-8")
    fs.write_text_atomic(target, "acme\n")
    assert target.read_text(encoding="utf-8") == "acme\n"
    leftovers = [p for p in tmp_path.iterdir() if p.name != "marker"]
    assert leftovers == []


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
    with pytest.raises(FsError):
        fs.repoint_symlink_atomic(link, Path("projects/acme/planning-artifacts"))
    # the real directory and its content must survive the refusal
    assert (link / "real-content.txt").read_text(encoding="utf-8") == "keep me"


def test_repoint_symlink_atomic_refuses_a_real_file(fs, tmp_path):
    link = tmp_path / "link"
    link.write_text("real content", encoding="utf-8")
    with pytest.raises(FsError):
        fs.repoint_symlink_atomic(link, Path("projects/acme/planning-artifacts"))
    assert link.read_text(encoding="utf-8") == "real content"


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores permission bits")
def test_repoint_symlink_atomic_wraps_an_unsearchable_ancestor(fs, tmp_path):
    """Review finding: the refuse-to-clobber guard ran BEFORE the try
    block, so on Python 3.12 an unsearchable ancestor made its pathlib
    probes escape as a raw PermissionError instead of FsError."""
    parent = tmp_path / "locked"
    link = parent / "link"
    parent.mkdir()
    parent.chmod(0o000)
    try:
        with pytest.raises(FsError):
            fs.repoint_symlink_atomic(link, Path("projects/acme/planning-artifacts"))
    finally:
        parent.chmod(0o755)


# --- remove_symlink (Story 6.2, AD-12/AD-36) --------------------------------------


def test_remove_symlink_removes_an_existing_symlink(fs, tmp_path):
    link = tmp_path / "link"
    os.symlink(Path("projects/acme/planning-artifacts"), link)
    assert fs.remove_symlink(link) is True
    assert not link.is_symlink()
    assert not link.exists()


def test_remove_symlink_is_a_no_op_when_nothing_exists(fs, tmp_path):
    link = tmp_path / "does-not-exist"
    assert fs.remove_symlink(link) is False


def test_remove_symlink_refuses_a_real_directory(fs, tmp_path):
    link = tmp_path / "link"
    link.mkdir()
    (link / "real-content.txt").write_text("keep me", encoding="utf-8")
    with pytest.raises(FsError):
        fs.remove_symlink(link)
    assert (link / "real-content.txt").read_text(encoding="utf-8") == "keep me"


def test_remove_symlink_refuses_a_real_file(fs, tmp_path):
    link = tmp_path / "link"
    link.write_text("real content", encoding="utf-8")
    with pytest.raises(FsError):
        fs.remove_symlink(link)
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


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores permission bits")
def test_is_dir_false_on_unsearchable_ancestor(fs, tmp_path):
    """Review finding: on Python 3.12 (this package's floor) pathlib
    propagates the PermissionError instead of returning False -- the
    adapter must report 'not a usable directory', never crash raw."""
    parent = tmp_path / "locked"
    child = parent / "inner"
    child.mkdir(parents=True)
    parent.chmod(0o000)
    try:
        assert fs.is_dir(child) is False
    finally:
        parent.chmod(0o755)


# --- ensure_dir (Story 1.5) -------------------------------------------------------


def test_ensure_dir_creates_missing_parents(fs, tmp_path):
    target = tmp_path / "nested" / "deeper" / "implementation-artifacts"
    fs.ensure_dir(target)
    assert target.is_dir()


def test_ensure_dir_is_idempotent_on_an_existing_dir(fs, tmp_path):
    target = tmp_path / "implementation-artifacts"
    target.mkdir()
    (target / "keep-me.txt").write_text("x", encoding="utf-8")
    fs.ensure_dir(target)
    assert target.is_dir()
    assert (target / "keep-me.txt").read_text(encoding="utf-8") == "x"


def test_ensure_dir_raises_fs_error_on_unwritable_target(fs, tmp_path):
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("occupied", encoding="utf-8")
    with pytest.raises(FsError):
        fs.ensure_dir(blocked / "implementation-artifacts")


# --- remove_empty_dir (Story 1.5) -------------------------------------------------


def test_remove_empty_dir_removes_a_real_empty_dir(fs, tmp_path):
    target = tmp_path / "implementation-artifacts"
    target.mkdir()
    assert fs.remove_empty_dir(target) is True
    assert not target.exists()


def test_remove_empty_dir_leaves_a_real_nonempty_dir_untouched(fs, tmp_path):
    target = tmp_path / "implementation-artifacts"
    target.mkdir()
    (target / "sprint-status.yaml").write_text("x", encoding="utf-8")
    assert fs.remove_empty_dir(target) is False
    assert target.is_dir()
    assert (target / "sprint-status.yaml").read_text(encoding="utf-8") == "x"


def test_remove_empty_dir_raises_fs_error_when_path_is_missing(fs, tmp_path):
    with pytest.raises(FsError):
        fs.remove_empty_dir(tmp_path / "absent")


def test_remove_empty_dir_raises_fs_error_when_path_is_a_file(fs, tmp_path):
    target = tmp_path / "not-a-directory"
    target.write_text("x", encoding="utf-8")
    with pytest.raises(FsError):
        fs.remove_empty_dir(target)


# --- resolve_path (Story 1.6) -----------------------------------------------------


def test_resolve_path_matches_a_plain_non_symlink_path(fs, tmp_path):
    real = tmp_path / "real-dir"
    real.mkdir()
    assert fs.resolve_path(real) == real.resolve()


def test_resolve_path_resolves_a_real_symlink_chain(fs, tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    middle = tmp_path / "middle"
    middle.symlink_to(target)
    link = tmp_path / "link"
    link.symlink_to(middle)
    assert fs.resolve_path(link) == target.resolve()


def test_resolve_path_tolerates_a_broken_dangling_target(fs, tmp_path):
    """Non-strict (mirrors pathlib.Path.resolve()'s own strict=False
    default): a symlink whose target does not exist still resolves rather
    than raising -- a broken backlink is exactly the violation
    marshal homes' Tier-3 check needs to name, not an error to abort on."""
    link = tmp_path / "dangling-link"
    link.symlink_to(tmp_path / "does-not-exist")
    resolved = fs.resolve_path(link)
    assert resolved == (tmp_path / "does-not-exist").resolve()


def test_resolve_path_tolerates_a_wholly_nonexistent_path(fs, tmp_path):
    absent = tmp_path / "never-created" / "nested"
    resolved = fs.resolve_path(absent)
    assert resolved == absent.resolve()


# --- exists (Story 1.6, review finding) -------------------------------------------


def test_exists_true_for_a_real_directory(fs, tmp_path):
    real = tmp_path / "real-dir"
    real.mkdir()
    assert fs.exists(real) is True


def test_exists_true_for_a_regular_file(fs, tmp_path):
    """The occupancy state is_dir cannot see -- the reason this primitive
    exists (a plain file squatting where a symlink belongs)."""
    target = tmp_path / "plain-file"
    target.write_text("x", encoding="utf-8")
    assert fs.exists(target) is True


def test_exists_false_for_an_absent_path(fs, tmp_path):
    assert fs.exists(tmp_path / "never-created") is False


def test_exists_false_for_a_dangling_symlink(fs, tmp_path):
    """Pathlib semantics (follows the link): a dangling symlink reports
    False -- callers probe read_symlink_target FIRST, so the symlink case
    never reaches this method; see the port docstring."""
    link = tmp_path / "dangling"
    link.symlink_to(tmp_path / "does-not-exist")
    assert fs.exists(link) is False


# --- copy_file (Story 1.7) --------------------------------------------------


def test_copy_file_copies_real_bytes(fs, tmp_path):
    src = tmp_path / "src" / ".mcp.json"
    src.parent.mkdir()
    src.write_text('{"mcpServers": {}}', encoding="utf-8")
    dst = tmp_path / "dst" / ".mcp.json"
    fs.copy_file(src, dst)
    assert dst.read_text(encoding="utf-8") == '{"mcpServers": {}}'
    assert not dst.is_symlink()


def test_copy_file_creates_parent_dirs(fs, tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("x", encoding="utf-8")
    dst = tmp_path / "nested" / "deeper" / "dst.txt"
    fs.copy_file(src, dst)
    assert dst.read_text(encoding="utf-8") == "x"


def test_copy_file_overwrites_an_existing_destination(fs, tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("new", encoding="utf-8")
    dst = tmp_path / "dst.txt"
    dst.write_text("old", encoding="utf-8")
    fs.copy_file(src, dst)
    assert dst.read_text(encoding="utf-8") == "new"


def test_copy_file_raises_fs_error_when_source_is_missing(fs, tmp_path):
    with pytest.raises(FsError):
        fs.copy_file(tmp_path / "absent.txt", tmp_path / "dst.txt")


def test_copy_file_raises_fs_error_when_source_is_a_directory(fs, tmp_path):
    src = tmp_path / "a-dir"
    src.mkdir()
    with pytest.raises(FsError):
        fs.copy_file(src, tmp_path / "dst.txt")


def test_copy_file_raises_fs_error_on_unwritable_destination_parent(fs, tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("x", encoding="utf-8")
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("occupied", encoding="utf-8")
    with pytest.raises(FsError):
        fs.copy_file(src, blocked / "dst.txt")


# --- write_redacted_atomic (Story 2.6, AD-34) ---------------------------------


def test_write_redacted_atomic_writes_the_payloads_text(fs, tmp_path):
    target = tmp_path / "gate-record.json"
    fs.write_redacted_atomic(target, Redacted(text='{"a": 1}'))
    assert target.read_text(encoding="utf-8") == '{"a": 1}'


def test_write_redacted_atomic_creates_parent_dirs(fs, tmp_path):
    target = tmp_path / "nested" / "deeper" / "gate-record.json"
    fs.write_redacted_atomic(target, Redacted(text="{}"))
    assert target.read_text(encoding="utf-8") == "{}"


def test_write_redacted_atomic_overwrites_existing_content(fs, tmp_path):
    target = tmp_path / "gate-record.json"
    target.write_text("old", encoding="utf-8")
    fs.write_redacted_atomic(target, Redacted(text="new"))
    assert target.read_text(encoding="utf-8") == "new"


def test_write_redacted_atomic_leaves_no_temp_file_behind(fs, tmp_path):
    target = tmp_path / "gate-record.json"
    fs.write_redacted_atomic(target, Redacted(text="{}"))
    leftovers = [p for p in tmp_path.iterdir() if p.name != "gate-record.json"]
    assert leftovers == []


def test_write_redacted_atomic_raises_fs_error_on_unwritable_target(fs, tmp_path):
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("occupied", encoding="utf-8")
    with pytest.raises(FsError):
        fs.write_redacted_atomic(blocked / "gate-record.json", Redacted(text="{}"))


@pytest.mark.parametrize("bogus_payload", ["a bare str", None, {"text": "{}"}, 123])
def test_write_redacted_atomic_rejects_a_non_redacted_payload(fs, tmp_path, bogus_payload):
    """Regression (review finding, verified live): without a type check,
    a non-``Redacted`` payload crashed with a raw ``AttributeError`` on
    ``payload.text`` instead of the documented ``TypeError`` contract."""
    with pytest.raises(TypeError, match="Redacted"):
        fs.write_redacted_atomic(tmp_path / "gate-record.json", bogus_payload)


@pytest.mark.parametrize("bogus_path", ["a-bare-str-path", None, 123])
def test_write_redacted_atomic_rejects_a_non_path_path(fs, tmp_path, bogus_path):
    """Regression (follow-up review finding, verified live): the original
    guarded only ``payload``, so a ``str`` path escaped as a raw
    ``AttributeError: 'str' object has no attribute 'parent'`` -- the same
    failure class the ``payload`` guard exists to prevent."""
    with pytest.raises(TypeError, match="path must be a Path"):
        fs.write_redacted_atomic(bogus_path, Redacted(text="{}"))


@pytest.mark.parametrize("path", [Path("/"), Path(".")], ids=["root", "dot"])
def test_write_redacted_atomic_rejects_a_path_with_no_file_name(path):
    """Review finding, verified live: `_tmp_sibling` raised its own
    `ValueError: PosixPath('/') has an empty name`, which
    `write_text_atomic`'s `except OSError` does not catch -- so it escaped
    both failure modes `write_redacted_atomic` and `ports/record.py`
    document (`TypeError` or `FsError`)."""
    with pytest.raises(FsError, match="no file name"):
        LocalFs().write_redacted_atomic(path, Redacted(text="{}"))


def test_write_redacted_atomic_payload_diagnostic_does_not_echo_the_value(tmp_path):
    """Review finding: the diagnostic interpolated the rejected payload, which
    is precisely the unredacted object this port exists to refuse -- and it
    escapes as a raw traceback into the harness log."""
    secret = "ghp_" + "a" * 36
    with pytest.raises(TypeError) as excinfo:
        LocalFs().write_redacted_atomic(tmp_path / "r.json", secret)
    assert secret not in str(excinfo.value)
    assert "Redacted" in str(excinfo.value)


# --- append_line (Story 3.1, AD-30) -------------------------------------------


def test_append_line_creates_the_file_and_writes_one_line(fs, tmp_path):
    target = tmp_path / "journal.jsonl"
    fs.append_line(target, '{"a": 1}', fsync=False)
    assert target.read_text(encoding="utf-8") == '{"a": 1}\n'


def test_append_line_appends_subsequent_lines_without_truncating(fs, tmp_path):
    target = tmp_path / "journal.jsonl"
    fs.append_line(target, '{"a": 1}', fsync=False)
    fs.append_line(target, '{"a": 2}', fsync=False)
    fs.append_line(target, '{"a": 3}', fsync=False)
    assert target.read_text(encoding="utf-8") == '{"a": 1}\n{"a": 2}\n{"a": 3}\n'


def test_append_line_with_fsync_true_still_appends(fs, tmp_path):
    """The AD-30 rule is that fsync=True must not change the WRITE
    behavior -- only whether the data is flushed to disk before returning
    (the actual fsync CALL is verified separately below via monkeypatch)."""
    target = tmp_path / "journal.jsonl"
    fs.append_line(target, '{"a": 1}', fsync=True)
    assert target.read_text(encoding="utf-8") == '{"a": 1}\n'


def test_append_line_calls_os_fsync_only_when_requested(fs, tmp_path, monkeypatch):
    """Review finding: nothing previously proved os.fsync was actually
    called (or skipped) -- a deleted or inverted `if fsync: os.fsync(fd)`
    line would have passed every prior test, since they only checked final
    file content."""
    calls = []
    real_fsync = os.fsync
    monkeypatch.setattr(os, "fsync", lambda fd: (calls.append(fd), real_fsync(fd))[1])

    target = tmp_path / "journal.jsonl"
    fs.append_line(target, '{"a": 1}', fsync=True)
    assert len(calls) == 1

    fs.append_line(target, '{"a": 2}', fsync=False)
    assert len(calls) == 1  # unchanged -- fsync=False must not call it


def test_append_line_raises_fs_error_when_parent_directory_is_missing(fs, tmp_path):
    """Does NOT auto-mkdir, unlike write_text_atomic -- a missing run
    directory is a real precondition failure, not something to create
    around (see create_dir_exclusive)."""
    target = tmp_path / "runs" / "run-1" / "journal.jsonl"
    with pytest.raises(FsError):
        fs.append_line(target, '{"a": 1}', fsync=False)


def test_append_line_leaves_no_temp_file_behind(fs, tmp_path):
    """AD-30: no buffered stream, no temp-file-then-replace -- append_line
    writes directly to the target, so nothing else should ever appear
    beside it."""
    target = tmp_path / "journal.jsonl"
    fs.append_line(target, '{"a": 1}', fsync=False)
    leftovers = [p for p in tmp_path.iterdir() if p.name != "journal.jsonl"]
    assert leftovers == []


def test_append_line_rejects_a_line_with_an_embedded_newline(fs, tmp_path):
    """Review finding: this primitive's entire contract is "one physical
    line per call" -- an unrejected embedded newline would silently split
    into two physical lines with no error raised anywhere."""
    target = tmp_path / "journal.jsonl"
    with pytest.raises(FsError, match="embedded newline"):
        fs.append_line(target, '{"a": 1}\n{"a": 2}', fsync=False)
    assert not target.exists()


def test_append_line_raises_fs_error_on_a_short_write(fs, tmp_path, monkeypatch):
    """Review finding: POSIX permits write() to consume fewer bytes than
    requested even for a regular file; a short write must be surfaced as a
    loud failure, never silently completed (a retry could let a different
    writer's complete line land in the gap) and never silently truncated."""
    target = tmp_path / "journal.jsonl"
    real_write = os.write
    monkeypatch.setattr(os, "write", lambda fd, data: real_write(fd, data[:1]) if data else 0)
    with pytest.raises(FsError, match="short write"):
        fs.append_line(target, '{"a": 1}', fsync=False)


# --- create_dir_exclusive (Story 3.1, AD-25) ----------------------------------


def test_create_dir_exclusive_creates_a_fresh_directory(fs, tmp_path):
    target = tmp_path / "run-1"
    fs.create_dir_exclusive(target)
    assert target.is_dir()


def test_create_dir_exclusive_raises_directory_already_exists_error_on_collision(
    fs, tmp_path
):
    target = tmp_path / "run-1"
    target.mkdir()
    (target / "keep-me.txt").write_text("x", encoding="utf-8")
    with pytest.raises(DirectoryAlreadyExistsError):
        fs.create_dir_exclusive(target)
    # the real directory and its content must survive the collision
    assert (target / "keep-me.txt").read_text(encoding="utf-8") == "x"


def test_directory_already_exists_error_is_an_fs_error(fs, tmp_path):
    target = tmp_path / "run-1"
    target.mkdir()
    with pytest.raises(FsError):
        fs.create_dir_exclusive(target)


def test_create_dir_exclusive_raises_plain_fs_error_when_parent_is_missing(fs, tmp_path):
    """No parents=True -- a missing parent is a different failure than a
    collision, and must NOT be misreported as DirectoryAlreadyExistsError."""
    target = tmp_path / "absent-parent" / "run-1"
    with pytest.raises(FsError) as excinfo:
        fs.create_dir_exclusive(target)
    assert not isinstance(excinfo.value, DirectoryAlreadyExistsError)


def test_create_dir_exclusive_does_not_create_parent_dirs(fs, tmp_path):
    target = tmp_path / "absent-parent" / "run-1"
    with pytest.raises(FsError):
        fs.create_dir_exclusive(target)
    assert not target.exists()


# --- append_line concurrency (Story 3.1, this story's headline AC) -----------


def test_append_line_is_safe_under_concurrent_writers(fs, tmp_path):
    """AD-30's own concurrency proof: one long-lived writer appending many
    lines in a loop, alongside several short-lived writers each appending a
    handful of lines then exiting, ALL targeting the same file concurrently,
    each thread owning its own writer_id and a LOCALLY-owned monotonic
    counter (no lock -- AD-28 requires none). After joining every thread,
    every line must parse as JSON (zero malformed lines -- proves
    atomicity) and the set of (writer_id, counter) pairs across every line
    must have zero duplicates and a size equal to the total append count
    (proves identity -- a malformed-line-only assertion would pass even if
    the id invariant were violated)."""
    target = tmp_path / "journal.jsonl"
    long_lived_line_count = 200
    short_lived_writer_count = 8
    short_lived_line_count = 15

    def write_lines(writer_id: str, count: int) -> None:
        for counter in range(count):
            line = json.dumps({"writer_id": writer_id, "counter": counter})
            fs.append_line(target, line, fsync=False)

    threads = [
        threading.Thread(target=write_lines, args=("long-lived", long_lived_line_count))
    ]
    for index in range(short_lived_writer_count):
        threads.append(
            threading.Thread(
                target=write_lines, args=(f"short-lived-{index}", short_lived_line_count)
            )
        )

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    lines = target.read_text(encoding="utf-8").splitlines()
    total_expected = long_lived_line_count + short_lived_writer_count * short_lived_line_count
    assert len(lines) == total_expected

    pairs = []
    for line in lines:
        document = json.loads(line)  # raises if any line is malformed JSON
        pairs.append((document["writer_id"], document["counter"]))

    assert len(pairs) == len(set(pairs)) == total_expected


def test_append_line_is_safe_under_concurrent_writers_near_the_sidecar_threshold(
    fs, tmp_path
):
    """Review finding: the test above only exercises very short lines --
    nothing proved the same atomicity/identity guarantee holds for lines
    near the 4 KiB sidecar boundary (core.journal.SIDECAR_THRESHOLD_BYTES),
    which is exactly the largest a real inlined journal line is ever meant
    to get and the likeliest place for a short write to actually surface."""
    target = tmp_path / "journal.jsonl"
    writer_count = 6
    lines_per_writer = 20
    padding = "x" * 3900  # each line lands comfortably under ~4 KiB total

    def write_lines(writer_id: str, count: int) -> None:
        for counter in range(count):
            line = json.dumps(
                {"writer_id": writer_id, "counter": counter, "padding": padding}
            )
            fs.append_line(target, line, fsync=False)

    threads = [
        threading.Thread(target=write_lines, args=(f"writer-{index}", lines_per_writer))
        for index in range(writer_count)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    lines = target.read_text(encoding="utf-8").splitlines()
    total_expected = writer_count * lines_per_writer
    assert len(lines) == total_expected

    pairs = []
    for line in lines:
        document = json.loads(line)  # raises if any line is malformed JSON
        assert document["padding"] == padding  # proves no cross-writer truncation/splicing
        pairs.append((document["writer_id"], document["counter"]))

    assert len(pairs) == len(set(pairs)) == total_expected


# --- acquire_advisory_lock / release_advisory_lock (Story 4.9, AD-42) ------


def test_acquire_advisory_lock_returns_a_lock_and_creates_the_sibling_file(fs, tmp_path):
    target = tmp_path / "specs"
    target.mkdir()
    lock = fs.acquire_advisory_lock(target, timeout_s=1.0)
    try:
        assert isinstance(lock, AdvisoryLock)
        assert lock.path == tmp_path / "specs.lock"
        assert lock.path.is_file()
    finally:
        fs.release_advisory_lock(lock)


def test_acquire_advisory_lock_does_not_require_target_path_to_exist(fs, tmp_path):
    """The lock file is a SIBLING of ``path`` -- ``path`` itself is never
    opened, so it need not exist (``specs_dir`` may not exist yet on a
    fresh checkout, and this primitive still works)."""
    target = tmp_path / "does-not-exist"
    lock = fs.acquire_advisory_lock(target, timeout_s=1.0)
    try:
        assert lock.path == tmp_path / "does-not-exist.lock"
    finally:
        fs.release_advisory_lock(lock)


def test_release_advisory_lock_allows_a_subsequent_acquire_to_succeed(fs, tmp_path):
    target = tmp_path / "specs"
    lock = fs.acquire_advisory_lock(target, timeout_s=1.0)
    fs.release_advisory_lock(lock)

    second = fs.acquire_advisory_lock(target, timeout_s=1.0)
    fs.release_advisory_lock(second)


def test_second_acquire_times_out_behind_a_held_lock(fs, tmp_path):
    """Real ``fcntl.flock`` semantics, single process/thread, sequential:
    a SECOND ``LocalFs`` instance's acquire on the same path, while the
    first is still held, must raise ``FsError`` once ``timeout_s`` elapses
    -- proving the bounded-retry-loop timeout path actually blocks rather
    than silently double-granting the lock."""
    target = tmp_path / "specs"
    first_holder = LocalFs()
    lock = first_holder.acquire_advisory_lock(target, timeout_s=1.0)
    try:
        second_holder = LocalFs()
        start = time.monotonic()
        with pytest.raises(FsError):
            second_holder.acquire_advisory_lock(target, timeout_s=0.2)
        elapsed = time.monotonic() - start
        # Genuinely waited (not an immediate raise) but did not hang far
        # past the requested bound.
        assert 0.15 <= elapsed < 2.0
    finally:
        first_holder.release_advisory_lock(lock)


def test_acquire_advisory_lock_succeeds_once_the_holder_releases(fs, tmp_path):
    """Completes the timeout proof above: after the first holder releases,
    a subsequent acquire (even one that previously timed out against it)
    succeeds immediately."""
    target = tmp_path / "specs"
    first_holder = LocalFs()
    lock = first_holder.acquire_advisory_lock(target, timeout_s=1.0)

    second_holder = LocalFs()
    with pytest.raises(FsError):
        second_holder.acquire_advisory_lock(target, timeout_s=0.2)

    first_holder.release_advisory_lock(lock)

    third = second_holder.acquire_advisory_lock(target, timeout_s=1.0)
    second_holder.release_advisory_lock(third)


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores permission bits")
def test_acquire_advisory_lock_raises_fs_error_on_unwritable_parent(fs, tmp_path):
    parent = tmp_path / "readonly"
    parent.mkdir()
    parent.chmod(0o555)
    target = parent / "nested" / "specs"
    try:
        with pytest.raises(FsError):
            fs.acquire_advisory_lock(target, timeout_s=0.2)
    finally:
        parent.chmod(0o755)


def test_release_advisory_lock_never_raises_and_closes_the_descriptor(fs, tmp_path):
    """Idempotent-safe: releasing a lock this same process holds never
    raises (mirrors ``remove_empty_dir``'s own established convention),
    and the descriptor is actually closed -- a double-close would raise
    ``OSError`` from the raw ``os.close`` if the first close were skipped,
    so this also proves the descriptor was closed exactly once by checking
    a subsequent acquire/release cycle still works cleanly."""
    target = tmp_path / "specs"
    lock = fs.acquire_advisory_lock(target, timeout_s=1.0)
    fs.release_advisory_lock(lock)  # must not raise
    # A second acquire/release cycle proves the fd was actually released
    # at the OS level, not merely "didn't crash".
    second = fs.acquire_advisory_lock(target, timeout_s=1.0)
    fs.release_advisory_lock(second)
