"""``PsutilSessionGroup`` (Story 90.1/92.1): shape tests with fakes, and the real adapter on real groups.

The shape tests fake ``psutil`` and ``os.getpgid``; they pin the mapping and the error contract only. The real
tests (POSIX) run the shipped adapter against this host's psutil, the 90.1 failure mode the fakes hid: psutil 7.2.2
has no ``pgid`` attribute, and a read through one raised on every call."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager

import psutil
import pytest

from pyforge.marshal.adapters import session_group_psutil
from pyforge.marshal.adapters.session_group_psutil import PsutilSessionGroup, process_cmdline
from pyforge.marshal.ports.session_group import SessionGroupMember, SessionGroupReadError

#: Linux never hands out a pid above ``PID_MAX_LIMIT`` (2**22), whatever ``pid_max`` is set to.
_NEVER_A_PID = 2**22 + 4321


class _FakePsutilProcess:
    """``psutil.Process`` stand-in keyed by pid: ``rows[pid]`` is ``(create_time, status)`` or an exception."""

    rows: dict[int, object] = {}

    def __init__(self, pid: int) -> None:
        self.pid = pid
        row = self.rows[pid]
        if isinstance(row, BaseException):
            raise row
        self._row = row

    @contextmanager
    def oneshot(self) -> Iterator[None]:
        yield

    def create_time(self) -> float | None:
        value = self._row[0]
        if isinstance(value, BaseException):
            raise value
        return value

    def status(self) -> str:
        return self._row[1]


def _fake_host(monkeypatch: pytest.MonkeyPatch, *, pgids: dict[int, object], rows: dict[int, object]) -> None:
    def _getpgid(pid: int) -> int:
        value = pgids[pid]
        if isinstance(value, BaseException):
            raise value
        return value

    monkeypatch.setattr(psutil, "pids", lambda: list(pgids))
    monkeypatch.setattr(session_group_psutil.os, "getpgid", _getpgid)
    _FakePsutilProcess.rows = rows
    monkeypatch.setattr(session_group_psutil.psutil, "Process", _FakePsutilProcess)


def test_members_are_filtered_by_getpgid_and_mapped(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_host(
        monkeypatch,
        pgids={100: 42, 200: 99, 101: 42},
        rows={100: (1.5, psutil.STATUS_RUNNING), 101: (2.5, psutil.STATUS_ZOMBIE)},
    )

    members = list(PsutilSessionGroup().iter_session_group_members(42))

    assert members == [
        SessionGroupMember(pid=100, started_at=1.5, is_zombie=False),
        SessionGroupMember(pid=101, started_at=2.5, is_zombie=True),
    ]


def test_a_process_that_exits_or_is_not_ours_to_read_is_skipped_never_a_read_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """m5: one exited (``ProcessLookupError``) or unreadable (``PermissionError``) pid never fails the whole read,
    and a member that exits between ``getpgid`` and its read is skipped too."""
    _fake_host(
        monkeypatch,
        pgids={
            100: 42,
            101: ProcessLookupError(3, "No such process"),
            102: PermissionError(1, "Operation not permitted"),
            103: 42,
            104: 42,
        },
        rows={
            100: (1.5, psutil.STATUS_SLEEPING),
            103: psutil.NoSuchProcess(103),
            104: (psutil.AccessDenied(104), psutil.STATUS_RUNNING),
        },
    )

    members = list(PsutilSessionGroup().iter_session_group_members(42))

    assert members == [
        SessionGroupMember(pid=100, started_at=1.5, is_zombie=False),
        SessionGroupMember(pid=104, started_at=None, is_zombie=False),
    ]


def test_an_unreadable_process_table_is_a_read_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _broken() -> list[int]:
        raise OSError("/proc unreadable")

    monkeypatch.setattr(psutil, "pids", _broken)

    with pytest.raises(SessionGroupReadError, match="/proc unreadable") as raised:
        list(PsutilSessionGroup().iter_session_group_members(7))

    assert isinstance(raised.value.__cause__, OSError)


def test_any_other_getpgid_failure_is_a_read_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_host(monkeypatch, pgids={100: OSError(22, "Invalid argument")}, rows={})

    with pytest.raises(SessionGroupReadError, match="getpgid"):
        list(PsutilSessionGroup().iter_session_group_members(42))


def test_any_other_psutil_failure_on_a_member_is_a_read_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_host(monkeypatch, pgids={100: 42}, rows={100: psutil.Error("boom")})

    with pytest.raises(SessionGroupReadError, match="cannot read process 100"):
        list(PsutilSessionGroup().iter_session_group_members(42))


# -- the real adapter on this host (m6) ------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX process groups")
def test_the_real_adapter_on_the_tests_own_group_raises_nothing_and_yields_its_live_members() -> None:
    members = list(PsutilSessionGroup().iter_session_group_members(os.getpgrp()))

    me = next(member for member in members if member.pid == os.getpid())
    assert me.is_zombie is False
    assert me.started_at == pytest.approx(psutil.Process(os.getpid()).create_time())
    assert all(os.getpgid(member.pid) == os.getpgrp() for member in members if psutil.pid_exists(member.pid))


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX process groups")
def test_the_real_adapter_reads_a_launched_session_group_and_nothing_outside_it() -> None:
    """A session launched as the harness adapter launches one (``start_new_session=True``): the adapter yields its
    leader and its child, both live, and none of this test's own processes."""
    leader = subprocess.Popen(
        ["bash", "-c", "sleep 5 & wait"],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 5
        members: list[SessionGroupMember] = []
        while len(members) < 2 and time.monotonic() < deadline:
            members = list(PsutilSessionGroup().iter_session_group_members(leader.pid))
            time.sleep(0.05)
        pids = {member.pid for member in members}
        assert leader.pid in pids
        assert len(pids) >= 2, "the leader's child (sleep) belongs to the same group"
        assert os.getpid() not in pids
        assert all(not member.is_zombie and member.started_at is not None for member in members)
    finally:
        try:
            os.killpg(leader.pid, signal.SIGKILL)
        except OSError:
            pass
        leader.wait(timeout=5)


def test_process_cmdline_reads_a_real_process_and_none_for_a_pid_that_cannot_exist() -> None:
    cmdline = process_cmdline(os.getpid())

    assert cmdline is not None
    assert "python" in cmdline.lower()
    assert process_cmdline(_NEVER_A_PID) is None
