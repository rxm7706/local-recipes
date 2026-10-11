"""Story 90.1: dispatch session liveness reads the launch process group."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pyforge.core.process import PosixProcess

from pyforge.marshal import dispatch_verify
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.ports.session_group import SessionGroupMember, SessionGroupPort, SessionGroupReadError


class _FakeSessionGroup:
    def __init__(self, members: tuple[SessionGroupMember, ...]) -> None:
        self._members = members

    def iter_session_group_members(self, _session_leader_pid: int) -> Iterator[SessionGroupMember]:
        yield from self._members


class _RaisingSessionGroup:
    def iter_session_group_members(self, _session_leader_pid: int) -> Iterator[SessionGroupMember]:
        raise SessionGroupReadError("unreadable")
        yield  # pragma: no cover


class _RecordingProcess:
    def is_alive(self, _pid: int) -> bool:
        return False

    def process_start_time(self, pid: int) -> float | None:
        return None


def test_session_group_read_error_counts_as_alive() -> None:
    port = _RaisingSessionGroup()
    launched_at = datetime(2026, 10, 10, 23, 26, 0, tzinfo=timezone.utc)
    assert (
        dispatch_verify.session_group_has_live_member(
            port, 4242, launched_at=launched_at, process=_RecordingProcess()
        )
        is True
    )


def test_zombie_members_do_not_keep_the_group_alive() -> None:
    launched_at = datetime(2026, 10, 10, 23, 26, 0, tzinfo=timezone.utc)
    port = _FakeSessionGroup(
        (SessionGroupMember(pid=99, started_at=launched_at.timestamp(), is_zombie=True),)
    )
    assert (
        dispatch_verify.session_group_has_live_member(
            port, 4242, launched_at=launched_at, process=_RecordingProcess()
        )
        is False
    )


def test_reused_pid_before_launch_does_not_count() -> None:
    launched_at = datetime(2026, 10, 10, 23, 26, 0, tzinfo=timezone.utc)
    old_start = launched_at.timestamp() - dispatch_core.PID_START_TOLERANCE_SECONDS - 60.0
    port = _FakeSessionGroup((SessionGroupMember(pid=99, started_at=old_start, is_zombie=False),))
    assert (
        dispatch_verify.session_group_has_live_member(
            port, 4242, launched_at=launched_at, process=_RecordingProcess()
        )
        is False
    )


@pytest.mark.skipif(sys.platform != "linux", reason="POSIX process-group integration")
def test_parent_exits_while_child_in_session_group_keeps_session_alive(tmp_path: Path) -> None:
    out = tmp_path / "growth.txt"
    out.write_text("", encoding="utf-8")
    shell = (
        f"( while true; do echo x >> {out}; sleep 0.1; done ) & "
        "exit 0"
    )
    proc = subprocess.Popen(
        ["bash", "-c", shell],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    leader_pid = proc.pid
    launched_at = datetime.now(timezone.utc)
    try:
        proc.wait(timeout=5)
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline and out.stat().st_size == 0:
            time.sleep(0.05)
        assert out.stat().st_size > 0
        assert dispatch_verify.dispatch_session_alive(
            PosixProcess(), leader_pid, launched_at=launched_at
        )
        child_deadline = time.monotonic() + 5.0
        while time.monotonic() < child_deadline:
            if not dispatch_verify.dispatch_session_alive(
                PosixProcess(), leader_pid, launched_at=launched_at
            ):
                break
            time.sleep(0.1)
        else:
            pytest.fail("session group did not settle within budget")
    finally:
        try:
            os.killpg(os.getpgid(leader_pid), 9)
        except OSError:
            pass
