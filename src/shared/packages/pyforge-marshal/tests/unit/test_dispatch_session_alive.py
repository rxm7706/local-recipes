"""Story 90.1/92.1: dispatch session liveness reads the launch's whole process group.

Fakes pin the rules (AC2's membership window, AC3's read-error fallback, the pid-reuse rule); the real tests run
the shipped psutil adapter on this host against real process groups (``start_new_session=True``, as the harness
adapter launches a session), and clean up every process they start by its own group id. They never monkeypatch
psutil: the 90.1 outage was a group read that raised on every call while every fake-based test stayed green.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psutil
import pytest
from pyforge.core.process import PosixProcess

from pyforge.marshal import dispatch_verify
from pyforge.marshal.adapters.session_group_psutil import PsutilSessionGroup
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.ports.session_group import SessionGroupMember, SessionGroupReadError

_LAUNCHED_AT = datetime(2026, 10, 10, 23, 26, 0, tzinfo=timezone.utc)
#: Linux never hands out a pid above ``PID_MAX_LIMIT`` (2**22): a fake leader with this pid has no ``/proc`` entry,
#: so the zombie read and the cmdline read can only answer "no such process".
_NO_SUCH_PID = 2**22 + 1234
_REAL_HOST = pytest.mark.skipif(sys.platform != "linux", reason="POSIX process groups, read on a Linux host")


class _FakeSessionGroup:
    def __init__(self, members: tuple[SessionGroupMember, ...]) -> None:
        self._members = members
        self.reads = 0

    def iter_session_group_members(self, _session_leader_pid: int) -> Iterator[SessionGroupMember]:
        self.reads += 1
        yield from self._members


class _RaisingSessionGroup:
    def __init__(self, message: str = "group unreadable") -> None:
        self.message = message
        self.reads = 0

    def iter_session_group_members(self, _session_leader_pid: int) -> Iterator[SessionGroupMember]:
        self.reads += 1
        raise SessionGroupReadError(self.message)
        yield  # pragma: no cover


class _ScriptedSessionGroup:
    def __init__(self, rounds: list[tuple[SessionGroupMember, ...]]) -> None:
        self._rounds = rounds

    def iter_session_group_members(self, _session_leader_pid: int) -> Iterator[SessionGroupMember]:
        if not self._rounds:
            return iter(())
        return iter(self._rounds.pop(0))


class _Leader:
    """``ProcessPort`` stand-in for the launched pid: whether it exists, and its start time (``None`` = unreadable)."""

    def __init__(self, *, alive: bool, start_time: float | None = None) -> None:
        self._alive = alive
        self._start_time = start_time

    def is_alive(self, _pid: int) -> bool:
        return self._alive

    def process_start_time(self, _pid: int) -> float | None:
        return self._start_time if self._alive else None


def _member(*, started_at: float | None, is_zombie: bool = False, pid: int = 99) -> SessionGroupMember:
    return SessionGroupMember(pid=pid, started_at=started_at, is_zombie=is_zombie)


def _assess(process, *, session_group, harness_binary: str | None = None, launched_at=_LAUNCHED_AT):
    return dispatch_verify.assess_dispatch_session_liveness(
        process,
        _NO_SUCH_PID,
        launched_at=launched_at,
        session_group=session_group,
        harness_binary=harness_binary,
    )


# -- AC2, with fakes: membership ---------------------------------------------------------------------------------


def test_a_member_that_started_before_the_launch_less_the_allowance_is_another_process() -> None:
    old_start = _LAUNCHED_AT.timestamp() - dispatch_core.PID_START_TOLERANCE_SECONDS - 60.0
    alive, error = dispatch_verify.session_group_has_live_member(
        _FakeSessionGroup((_member(started_at=old_start),)),
        _NO_SUCH_PID,
        launched_at=_LAUNCHED_AT,
        process=_Leader(alive=False),
    )

    assert (alive, error) == (False, None)


def test_a_member_inside_the_clock_allowance_below_the_launch_counts() -> None:
    """psutil derives ``create_time`` from a boot time kept in whole seconds, so a member can read a little early."""
    early = _LAUNCHED_AT.timestamp() - dispatch_core.PID_START_TOLERANCE_SECONDS + 1.0
    alive, _ = dispatch_verify.session_group_has_live_member(
        _FakeSessionGroup((_member(started_at=early),)),
        _NO_SUCH_PID,
        launched_at=_LAUNCHED_AT,
        process=_Leader(alive=False),
    )

    assert alive is True


def test_a_member_started_long_after_the_launch_keeps_the_session_alive() -> None:
    """No upper bound: a child the session starts five minutes -- or five hours -- in is still the session."""
    late = _LAUNCHED_AT.timestamp() + 5 * 3600
    assert dispatch_verify.dispatch_session_alive(
        _Leader(alive=False),
        _NO_SUCH_PID,
        launched_at=_LAUNCHED_AT,
        session_group=_FakeSessionGroup((_member(started_at=late),)),
    )


def test_zombie_members_do_not_keep_the_group_alive() -> None:
    port = _FakeSessionGroup((_member(started_at=_LAUNCHED_AT.timestamp(), is_zombie=True),))

    alive, _ = dispatch_verify.session_group_has_live_member(
        port, _NO_SUCH_PID, launched_at=_LAUNCHED_AT, process=_Leader(alive=False)
    )

    assert not alive


def test_dispatch_session_alive_turns_false_once_the_group_has_no_live_members() -> None:
    member = _member(started_at=_LAUNCHED_AT.timestamp())
    port = _ScriptedSessionGroup([(member,), ()])
    process = _Leader(alive=False)

    assert dispatch_verify.dispatch_session_alive(process, _NO_SUCH_PID, launched_at=_LAUNCHED_AT, session_group=port)
    assert not dispatch_verify.dispatch_session_alive(
        process, _NO_SUCH_PID, launched_at=_LAUNCHED_AT, session_group=port
    )


# -- the pid-reuse rule (review M4) ------------------------------------------------------------------------------


def test_a_reused_leader_pid_is_not_the_session_and_its_group_is_never_read() -> None:
    """The launched pid exists, is not a zombie, and started an hour after the launch: another process. The pid of a
    live group leader is never reallocated, so the session's own group has ended -- the group under that pid now is
    the new process's, and it is not read (main's Story 83.1 answer, kept)."""
    port = _FakeSessionGroup((_member(started_at=_LAUNCHED_AT.timestamp() + 3600),))

    liveness = _assess(_Leader(alive=True, start_time=_LAUNCHED_AT.timestamp() + 3600), session_group=port)

    assert liveness.alive is False
    assert port.reads == 0


def test_an_existing_leader_inside_its_window_reads_alive_with_an_empty_group() -> None:
    """Story 83.1, unchanged: a leader whose identity checks out is the session."""
    liveness = _assess(
        _Leader(alive=True, start_time=_LAUNCHED_AT.timestamp() + 2), session_group=_FakeSessionGroup(())
    )

    assert liveness == dispatch_verify.DispatchSessionLiveness(alive=True)


def test_an_existing_leader_whose_start_time_cannot_be_read_keeps_story_83_1s_existence_rule() -> None:
    """A working group read that finds no member leaves the leader to Story 83.1: existence decides when the start
    time is unreadable (a host without ``/proc``) -- the identity fallback is for a FAILED read only."""
    liveness = _assess(_Leader(alive=True, start_time=None), session_group=_FakeSessionGroup(()))

    assert liveness == dispatch_verify.DispatchSessionLiveness(alive=True)


# -- AC3: a group read that raises falls back to the identity-checked leader, never to "alive" ----------------------


def test_ac3_a_leader_inside_story_83_1s_window_reads_alive_and_the_error_is_carried() -> None:
    port = _RaisingSessionGroup("psutil: boom")

    liveness = _assess(_Leader(alive=True, start_time=_LAUNCHED_AT.timestamp() + 3), session_group=port)

    assert liveness == dispatch_verify.DispatchSessionLiveness(alive=True, liveness_error="psutil: boom")
    assert port.reads == 1


def test_ac3_a_leader_that_has_exited_reads_not_alive() -> None:
    liveness = _assess(_Leader(alive=False), session_group=_RaisingSessionGroup("psutil: boom"))

    assert liveness == dispatch_verify.DispatchSessionLiveness(alive=False, liveness_error="psutil: boom")


@pytest.mark.parametrize(
    "leader",
    [
        pytest.param(_Leader(alive=True, start_time=_LAUNCHED_AT.timestamp() + 3600), id="start-time-outside-window"),
        pytest.param(_Leader(alive=True, start_time=None), id="start-time-unreadable-cmdline-not-the-binary"),
    ],
)
def test_ac3_a_reused_pid_reads_not_alive(monkeypatch: pytest.MonkeyPatch, leader: _Leader) -> None:
    """Both shapes of a reused pid: a readable start time outside the window, and an unreadable start time whose
    cmdline does not name the profile's ``binary``."""
    monkeypatch.setattr(dispatch_verify, "_process_cmdline", lambda _pid: "/usr/lib/firefox/firefox -contentproc")

    liveness = _assess(leader, session_group=_RaisingSessionGroup(), harness_binary="cursor-agent")

    assert liveness.alive is False


def test_ac3_an_unreadable_start_time_with_no_binary_to_match_reads_not_alive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dispatch_verify, "_process_cmdline", lambda _pid: "cursor-agent --print")

    liveness = _assess(_Leader(alive=True, start_time=None), session_group=_RaisingSessionGroup())

    assert liveness == dispatch_verify.DispatchSessionLiveness(alive=False, liveness_error="group unreadable")


def test_ac3_an_unreadable_start_time_whose_cmdline_names_the_binary_reads_alive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[int] = []

    def _cmdline(pid: int) -> str:
        seen.append(pid)
        return "node /home/op/.local/share/cursor-agent/versions/2026.10/index.js --print"

    monkeypatch.setattr(dispatch_verify, "_process_cmdline", _cmdline)

    liveness = _assess(
        _Leader(alive=True, start_time=None),
        session_group=_RaisingSessionGroup(),
        harness_binary="/home/op/.local/bin/cursor-agent",
    )

    assert liveness == dispatch_verify.DispatchSessionLiveness(alive=True, liveness_error="group unreadable")
    assert seen == [_NO_SUCH_PID]


def test_the_harness_binary_comes_from_the_runs_profile() -> None:
    assert dispatch_verify.harness_binary_for_profile("cursor", repo_root=None) == "cursor-agent"
    assert dispatch_verify.harness_binary_for_profile("claude", repo_root=None) == "claude"
    assert dispatch_verify.harness_binary_for_profile("no-such-profile", repo_root=None) is None
    assert dispatch_verify.harness_binary_for_profile(None, repo_root=None) is None


def test_an_unloadable_profile_overlay_names_no_binary(tmp_path: Path) -> None:
    overlay = tmp_path / "_bmad-output" / "harness-profiles"
    overlay.mkdir(parents=True)
    (overlay / "cursor.toml").write_text("this is not toml = [", encoding="utf-8")

    # The broken overlay is skipped (an overlay error, never a crash); the packaged profile still answers.
    assert dispatch_verify.harness_binary_for_profile("cursor", repo_root=tmp_path) == "cursor-agent"


# -- AC2 on the real host ------------------------------------------------------------------------------------------


def _killpg(pgid: int) -> None:
    try:
        os.killpg(pgid, signal.SIGKILL)
    except OSError:
        pass


@pytest.fixture
def real_group(monkeypatch: pytest.MonkeyPatch) -> None:
    """The shipped psutil adapter -- the unit conftest pins an empty group so no other test reads the host."""
    monkeypatch.setattr(dispatch_verify, "_DEFAULT_SESSION_GROUP", PsutilSessionGroup())


@_REAL_HOST
def test_ac2_a_session_whose_leader_exits_at_once_lives_while_its_child_works_and_ends_within_a_second(
    tmp_path: Path, real_group: None
) -> None:
    """The leader exits (and is reaped) at once; its child appends to a file every 100 ms for about two seconds.
    Alive on every read while the file grows; not alive within one second of the child's exit."""
    grow = tmp_path / "grow.txt"
    grow.write_text("", encoding="utf-8")
    writes = 20
    script = f'( for i in $(seq 1 {writes}); do echo x >> "{grow}"; sleep 0.1; done ) & exit 0'
    launched_at = datetime.now(timezone.utc)
    leader = subprocess.Popen(
        ["bash", "-c", script], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    pgid = leader.pid
    process = PosixProcess()
    try:
        leader.wait(timeout=5)
        full = 2 * writes  # "x\n" per write
        growing: list[bool] = []
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and grow.stat().st_size < full:
            growing.append(dispatch_verify.dispatch_session_alive(process, pgid, launched_at=launched_at))
            time.sleep(0.1)
        last_write_seen = time.monotonic()
        assert grow.stat().st_size == full, "the child never finished writing"
        assert growing and all(growing), f"read not alive while the child was still writing: {growing}"

        # The child exits ~0.1 s after its last write; within one second of that exit the session reads ended.
        first_false: float | None = None
        while time.monotonic() < last_write_seen + 3:
            if not dispatch_verify.dispatch_session_alive(process, pgid, launched_at=launched_at):
                first_false = time.monotonic()
                break
            time.sleep(0.05)
        assert first_false is not None, "the session still read alive three seconds after its child's last write"
        assert first_false - last_write_seen <= 1.1
        assert not dispatch_verify.dispatch_session_alive(process, pgid, launched_at=launched_at)
    finally:
        _killpg(pgid)


@_REAL_HOST
def test_ac2_a_child_started_long_after_the_launch_keeps_the_session_alive(real_group: None) -> None:
    """The launch is moved an hour back rather than sleeping: the child started well past
    ``PID_START_TOLERANCE_SECONDS`` after it, and still counts."""
    leader = subprocess.Popen(
        ["bash", "-c", "( sleep 3 ) & exit 0"],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        leader.wait(timeout=5)
        an_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        an_hour_ahead = datetime.now(timezone.utc) + timedelta(hours=1)

        assert dispatch_verify.dispatch_session_alive(PosixProcess(), leader.pid, launched_at=an_hour_ago)
        # The mirror: a member that predates the launch (less the allowance) is another process.
        assert not dispatch_verify.dispatch_session_alive(PosixProcess(), leader.pid, launched_at=an_hour_ahead)
    finally:
        _killpg(leader.pid)


@_REAL_HOST
def test_ac2_a_pid_that_does_not_exist_reads_not_alive(real_group: None) -> None:
    """The 47.1 stall's shape: 90.1's group read raised on every call and counted the error as alive, so a pid
    that never existed read alive for good."""
    an_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

    liveness = dispatch_verify.assess_dispatch_session_liveness(PosixProcess(), _NO_SUCH_PID, launched_at=an_hour_ago)

    assert liveness == dispatch_verify.DispatchSessionLiveness(alive=False)


@_REAL_HOST
def test_ac2_an_unreaped_zombie_leader_alone_is_not_a_live_session(real_group: None) -> None:
    leader = subprocess.Popen(["bash", "-c", "exit 0"], start_new_session=True)
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and psutil.Process(leader.pid).status() != psutil.STATUS_ZOMBIE:
            time.sleep(0.02)
        assert psutil.Process(leader.pid).status() == psutil.STATUS_ZOMBIE

        assert not dispatch_verify.dispatch_session_alive(
            PosixProcess(), leader.pid, launched_at=datetime.now(timezone.utc)
        )
    finally:
        leader.wait(timeout=5)


@_REAL_HOST
def test_a_reused_pid_that_leads_its_own_group_on_the_real_host_reads_not_alive(real_group: None) -> None:
    """Review M4: an unrelated ``setsid`` process now holds the run's session pid (it started two hours after the
    run's launch). It leads a group of its own, and that group is not the session's."""
    other = subprocess.Popen(["sleep", "5"], start_new_session=True)
    try:
        two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)

        assert not dispatch_verify.fix_session_alive(PosixProcess(), other.pid, launched_at=two_hours_ago)
        assert not dispatch_verify.dispatch_session_alive(PosixProcess(), other.pid, launched_at=two_hours_ago)
    finally:
        _killpg(other.pid)
        other.wait(timeout=5)
