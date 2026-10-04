"""Story 85.1 (CAP-286): verification-refusal fix turn."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from pyforge.core.flags import FlagConfigError
from pyforge.core.process import PosixProcess

from pyforge.marshal.core.dispatch_verification import DispatchVerificationVerdict
from pyforge.marshal.core.dispatch_verify_fix import (
    FailedVerifyCommand,
    VerifyFixLaunchMode,
    build_verify_fix_prompt,
    choose_verify_fix_launch_mode,
    decide_verify_fix_turn,
    extract_failed_verify_commands,
    scrub_fix_turn_exposure,
    scrub_then_tail_bytes,
    tail_bytes,
)
from pyforge.marshal.core.harness_profile import parse_profile
from pyforge.marshal.core.harness_profile import render_verify_fix_argv as render_fix
from pyforge.marshal.core.model import Finding, Severity
from pyforge.marshal.core.policy import DEFAULT_POLICY, compose
from pyforge.marshal.dispatch_verify import (
    ProcessWaitResult,
    TerminateProcessGroupResult,
    terminate_process_group,
    verify_fix_loop_enabled,
    wait_for_process,
)


def test_decide_verify_fix_turn_requires_flag_and_refusal():
    assert (
        decide_verify_fix_turn(
            flag_enabled=False,
            verification_verdict=DispatchVerificationVerdict.REFUSED.value,
            has_git_progress=True,
            fix_turn_already_ran=False,
            session_alive=False,
        ).run
        is False
    )
    assert (
        decide_verify_fix_turn(
            flag_enabled=True,
            verification_verdict=DispatchVerificationVerdict.VERIFIED.value,
            has_git_progress=True,
            fix_turn_already_ran=False,
            session_alive=False,
        ).run
        is False
    )
    assert (
        decide_verify_fix_turn(
            flag_enabled=True,
            verification_verdict=DispatchVerificationVerdict.REFUSED.value,
            has_git_progress=True,
            fix_turn_already_ran=False,
            session_alive=False,
        ).run
        is True
    )


def test_build_verify_fix_prompt_uses_tail_only():
    failed = (
        FailedVerifyCommand(
            command="pixi run -e pyforge-guild lint-types",
            stdout="A" * 100,
            stderr="B" * 100,
            exit_code=1,
        ),
    )
    prompt = build_verify_fix_prompt(failed, output_tail_bytes=20)
    assert "bmad-build-auto" not in prompt
    assert "pixi run -e pyforge-guild lint-types" in prompt
    assert "AAAA" not in prompt or len(prompt) < 300


def test_tail_bytes_bounds_output():
    text = "0123456789" * 50
    tailed = tail_bytes(text, max_bytes=15)
    assert len(tailed.encode("utf-8")) <= 15


def test_extract_failed_verify_commands_from_gate_reports():
    reports = (
        {
            "command": "pixi run test",
            "returncode": 1,
            "stdout": "fail",
            "stderr": "",
        },
    )
    findings = (
        Finding(
            code="MRS-GATE-001",
            severity=Severity.ERROR,
            message="verify command 'pixi run test' exited 1",
        ),
    )
    extracted = extract_failed_verify_commands(reports, findings)
    assert len(extracted) == 1
    assert extracted[0].command == "pixi run test"


def test_resume_vs_fix_only_from_profile():
    profile = parse_profile(
        {
            "name": "fake",
            "binary": "fake",
            "argv": ["{prompt}"],
            "resume_argv": ["--continue", "{prompt}"],
        },
        source="t",
    )
    assert (
        choose_verify_fix_launch_mode(
            resume_argv=profile.resume_argv,
            harness_session_id="sid-1",
            launch_profile="fake",
            resolved_profile="fake",
        )
        == VerifyFixLaunchMode.RESUME
    )
    assert choose_verify_fix_launch_mode(resume_argv=profile.resume_argv, harness_session_id=None) == (
        VerifyFixLaunchMode.FIX_ONLY
    )
    assert (
        choose_verify_fix_launch_mode(
            resume_argv=profile.resume_argv,
            harness_session_id="sid-1",
            launch_profile="claude",
            resolved_profile="cursor",
        )
        == VerifyFixLaunchMode.FIX_ONLY
    )
    bare = parse_profile({"name": "bare", "binary": "bare", "argv": ["{prompt}"]}, source="t")
    assert choose_verify_fix_launch_mode(resume_argv=bare.resume_argv) == VerifyFixLaunchMode.FIX_ONLY


def test_render_verify_fix_resume_argv():
    profile = parse_profile(
        {
            "name": "fake",
            "binary": "fake",
            "argv": ["{prompt}"],
            "resume_argv": ["--resume", "{session_id}", "{prompt_file}"],
        },
        source="t",
    )
    argv, _, _ = render_fix(
        profile,
        mode="resume",
        binary_path="/bin/fake",
        worktree=__import__("pathlib").Path("/tmp/wt"),
        prompt="fix it",
        model=None,
        session_id="abc-session",
        prompt_file="/tmp/wt/verify-fix-prompt.txt",
    )
    assert "--resume" in argv
    assert "abc-session" in argv
    assert "/tmp/wt/verify-fix-prompt.txt" in argv
    assert "fix it" not in argv


def test_policy_verify_fix_defaults_compose():
    effective, _ = compose(project_slug="pyforge-marshal", project={}, flags={})
    block = effective.dispatch.value
    assert block["verify_fix_output_tail_bytes"] == DEFAULT_POLICY["dispatch"]["verify_fix_output_tail_bytes"]
    assert block["verify_fix_wall_clock_minutes"] == DEFAULT_POLICY["dispatch"]["verify_fix_wall_clock_minutes"]


def test_scrub_fix_turn_exposure_redacts_common_credential_shapes():
    raw = (
        "postgres://admin:secret@db/x\n"
        "Authorization: Bearer eyJhbGciOi\n"
        "Authorization: Basic dXNlcjpwYXNz\n"
        "password = 'hunter2'\n"
        "DATABASE_PASSWORD=postgres\n"
        "AWS_SECRET_ACCESS_KEY=AKIAEXAMPLE\n"
        "sk-ant-api03-abc12345\n"
        "password: s3cr3t\n"
        "https://user:pa/ss@host.example/path\n"
    )
    scrubbed = scrub_fix_turn_exposure(raw)
    assert "secret" not in scrubbed
    assert "eyJhbGciOi" not in scrubbed
    assert "hunter2" not in scrubbed
    assert "postgres" not in scrubbed or "DATABASE" in scrubbed
    assert "AKIAEXAMPLE" not in scrubbed
    assert "abc12345" not in scrubbed
    assert "s3cr3t" not in scrubbed
    assert "pa/ss" not in scrubbed


def test_scrub_then_tail_bytes_redacts_before_truncating():
    """A credential split by tail truncation must not leak (Story 85.3)."""
    prefix = "A" * 50
    secret = "DATABASE_PASSWORD=leaked"
    raw = prefix + secret
    tailed = scrub_then_tail_bytes(raw, max_bytes=30)
    assert "leaked" not in tailed
    assert "DATABASE_PASSWORD=" not in tailed or "***REDACTED***" in tailed


def test_extract_failed_verify_commands_ignores_gate_018_pseudo_command():
    findings = (
        Finding(
            code="MRS-GATE-018",
            severity=Severity.ERROR,
            message="deferred work intake refused",
        ),
    )
    extracted = extract_failed_verify_commands((), findings)
    assert extracted == ()


def test_wait_for_process_reaps_exited_child_without_zombie_poll():
    import subprocess
    import sys

    proc = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
    result = wait_for_process(PosixProcess(), proc.pid, timeout_s=30.0)
    assert isinstance(result, ProcessWaitResult)
    assert result.exited is True
    assert result.returncode == 0


def test_decide_verify_fix_turn_skips_without_failed_commands():
    assert (
        decide_verify_fix_turn(
            flag_enabled=True,
            verification_verdict=DispatchVerificationVerdict.REFUSED.value,
            has_git_progress=True,
            fix_turn_already_ran=False,
            session_alive=False,
            has_failed_commands=False,
        ).run
        is False
    )


def test_verify_fix_loop_enabled_reads_off_from_shipped_tree(tmp_path):
    repo = tmp_path / "repo"
    flags_dir = repo / "src/platform/config"
    flags_dir.mkdir(parents=True)
    flags_dir.joinpath("flags.json").write_text(
        json.dumps(
            {
                "flags": {
                    "pyforge.marshal.verify_fix_loop": {
                        "state": "ENABLED",
                        "variants": {"on": True, "off": False},
                        "defaultVariant": "off",
                        "metadata": {
                            "owner": "marshal",
                            "story": "85-1-",
                            "created": "2026-10-03",
                            "on_everywhere": "",
                            "cleanup_by": "",
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    enabled, warning = verify_fix_loop_enabled(repo_root=repo)
    assert enabled is False
    assert warning is None


def test_verify_fix_loop_enabled_unset_environment_reads_dev_on(tmp_path, monkeypatch):
    """Story 85.3: unset PYFORGE_ENVIRONMENT follows dev overlay (verify_fix on)."""
    repo = tmp_path / "repo"
    flags_dir = repo / "src/platform/config"
    flags_dir.mkdir(parents=True)
    overlays = flags_dir / "flag-overlays.json"
    overlays.write_text(
        json.dumps({"dev": {"pyforge.marshal.verify_fix_loop": "on"}, "production": {"pyforge.marshal.verify_fix_loop": "off"}}),
        encoding="utf-8",
    )
    flags_dir.joinpath("flags.json").write_text(
        json.dumps(
            {
                "flags": {
                    "pyforge.marshal.verify_fix_loop": {
                        "state": "ENABLED",
                        "defaultVariant": "off",
                        "variants": {"on": True, "off": False},
                        "metadata": {
                            "owner": "marshal",
                            "story": "85-3-x",
                            "created": "2026-10-03",
                            "on_everywhere": "",
                            "cleanup_by": "",
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("PYFORGE_ENVIRONMENT", raising=False)
    enabled, warning = verify_fix_loop_enabled(repo_root=repo)
    assert warning is None
    assert enabled is True


def test_verify_fix_loop_enabled_flag_config_error_returns_warning(monkeypatch, tmp_path):
    def _raise_flag_config(*_args, **_kwargs):
        raise FlagConfigError("unknown environment")

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_verify.read_boolean",
        _raise_flag_config,
    )
    enabled, warning = verify_fix_loop_enabled(repo_root=tmp_path)
    assert enabled is False
    assert warning == "unknown environment"


def test_wait_for_process_invokes_on_poll(monkeypatch):
    ticks = iter([0.0, 0.0, 10.0])
    monkeypatch.setattr(time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(os, "waitpid", lambda _pid, _opts: (0, 0))
    polled: list[str] = []
    wait_for_process(PosixProcess(), 1, timeout_s=5.0, on_poll=lambda: polled.append("x"))
    assert polled


class _NonChild:
    """A ``ProcessPort`` for a pid that is not this process's child: scripted liveness, a fixed start time."""

    def __init__(self, alive, *, started: float | None = None) -> None:
        self._alive = list(alive) if isinstance(alive, list) else None
        self._constant = alive if isinstance(alive, bool) else False
        self._started = started
        self.probes = 0

    def is_alive(self, _pid: int) -> bool:
        self.probes += 1
        if self._alive is None:
            return self._constant
        return self._alive.pop(0) if len(self._alive) > 1 else self._alive[0]

    def process_start_time(self, _pid: int) -> float | None:
        return self._started


def _not_a_child(monkeypatch) -> None:
    def fake_waitpid(_pid: int, _opts: int):
        raise ChildProcessError

    monkeypatch.setattr(os, "waitpid", fake_waitpid)


def test_wait_for_process_child_process_error(monkeypatch):
    """A pid that is not this process's child and is gone: exited, exit code unknowable."""
    _not_a_child(monkeypatch)
    result = wait_for_process(_NonChild(False), 123, timeout_s=1.0)
    assert result == ProcessWaitResult(exited=True, returncode=None)


def test_wait_for_process_polls_a_live_non_child_until_it_exits(monkeypatch):
    """Story 85.2 review H1: ``ChildProcessError`` no longer reads as exited -- the pid's liveness decides."""
    _not_a_child(monkeypatch)
    process = _NonChild([True, True, False])
    polled: list[str] = []
    result = wait_for_process(process, 123, timeout_s=30.0, poll_s=0.01, on_poll=lambda: polled.append("x"))
    assert result == ProcessWaitResult(exited=True, returncode=None)
    assert process.probes == 3
    assert polled == ["x", "x"]


def test_wait_for_process_times_out_on_a_live_non_child(monkeypatch):
    _not_a_child(monkeypatch)
    result = wait_for_process(_NonChild(True), 123, timeout_s=0.2, poll_s=0.05)
    assert result == ProcessWaitResult(exited=False, returncode=None)


def test_wait_for_process_reads_a_reused_non_child_pid_as_exited(monkeypatch):
    """Story 83.1's start-time check: the pid exists, but its process started hours after the launch."""
    from datetime import datetime, timezone

    _not_a_child(monkeypatch)
    launched = datetime(2026, 10, 3, 10, 0, tzinfo=timezone.utc)
    process = _NonChild(True, started=launched.timestamp() + 6 * 3600)
    result = wait_for_process(process, 123, timeout_s=30.0, poll_s=0.01, launched_at=launched)
    assert result == ProcessWaitResult(exited=True, returncode=None)


def test_wait_for_process_waits_for_a_real_detached_non_child():
    """A real session this process did not launch (its shell parent exited): waited for until it exits."""
    out = subprocess.run(
        ["sh", "-c", "sleep 0.5 >/dev/null 2>&1 & echo $!"],
        capture_output=True,
        text=True,
        check=True,
        start_new_session=True,
    )
    pid = int(out.stdout.strip())
    try:
        start = time.monotonic()
        result = wait_for_process(PosixProcess(), pid, timeout_s=20.0, poll_s=0.05)
        elapsed = time.monotonic() - start
    finally:
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    assert result == ProcessWaitResult(exited=True, returncode=None)
    assert 0.2 <= elapsed < 15.0


def test_fix_session_alive_reads_a_zombie_as_exited(monkeypatch, tmp_path):
    """A non-child that exited but awaits its parent's reap is not running (``ProcessPort`` counts it alive)."""
    from pyforge.marshal import dispatch_verify

    stats = {
        4242: "4242 (bash (x) y) Z 1 4242 4242 0 -1\n",
        4343: "4343 (python3) S 1 4343 4343 0 -1\n",
    }
    real_read = Path.read_text

    def fake_read(self, *args, **kwargs):
        for pid, stat in stats.items():
            if str(self) == f"/proc/{pid}/stat":
                return stat
        return real_read(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fake_read)
    assert dispatch_verify.fix_session_alive(_NonChild(True), 4242, launched_at=None) is False
    assert dispatch_verify.fix_session_alive(_NonChild(True), 4343, launched_at=None) is True
    assert dispatch_verify._is_zombie(4242) is True
    assert dispatch_verify._is_zombie(4343) is False


def test_wait_for_process_os_error_in_loop(monkeypatch):
    def fake_waitpid(_pid: int, _opts: int):
        raise OSError

    monkeypatch.setattr(os, "waitpid", fake_waitpid)
    result = wait_for_process(PosixProcess(), 123, timeout_s=1.0)
    assert result == ProcessWaitResult(exited=False, returncode=None)


def test_terminate_process_group_falls_back_to_kill_when_no_pgid(monkeypatch):
    kills: list[tuple[int, int]] = []

    def fake_getpgid(_pid: int) -> int:
        raise OSError

    def fake_kill(pid: int, sig: int) -> None:
        kills.append((pid, sig))

    monkeypatch.setattr(os, "getpgid", fake_getpgid)
    monkeypatch.setattr(os, "kill", fake_kill)
    terminate_process_group(77)
    assert kills == [(77, signal.SIGTERM)]


def test_terminate_process_group_swallows_kill_oserror(monkeypatch):
    monkeypatch.setattr(os, "getpgid", lambda _pid: (_ for _ in ()).throw(OSError))
    monkeypatch.setattr(os, "kill", lambda *_args: (_ for _ in ()).throw(OSError))
    terminate_process_group(1)  # must not raise


def test_terminate_process_group_killpg_failure_falls_back_to_kill(monkeypatch):
    kills: list[tuple[int, int]] = []

    monkeypatch.setattr(os, "getpgid", lambda _pid: 5)

    def fake_killpg(_pgid: int, _sig: int) -> None:
        raise OSError

    def fake_kill(pid: int, sig: int) -> None:
        kills.append((pid, sig))

    monkeypatch.setattr(os, "killpg", fake_killpg)
    monkeypatch.setattr(os, "kill", fake_kill)
    terminate_process_group(88)
    assert kills == [(88, signal.SIGTERM)]


def test_terminate_process_group_killpg_and_kill_both_fail(monkeypatch):
    monkeypatch.setattr(os, "getpgid", lambda _pid: 5)
    monkeypatch.setattr(os, "killpg", lambda *_args: (_ for _ in ()).throw(OSError))
    monkeypatch.setattr(os, "kill", lambda *_args: (_ for _ in ()).throw(OSError))
    terminate_process_group(88)  # must not raise


def test_terminate_process_group_never_signals_a_group_address_or_init(monkeypatch):
    """Story 85.2: a journaled pid of 0 or below is a process-group address to ``kill``, and 1 is init."""
    calls: list[tuple[str, int]] = []
    monkeypatch.setattr(os, "getpgid", lambda pid: calls.append(("getpgid", pid)) or pid)
    monkeypatch.setattr(os, "killpg", lambda pgid, _sig: calls.append(("killpg", pgid)))
    monkeypatch.setattr(os, "kill", lambda pid, _sig: calls.append(("kill", pid)))
    for pid in (1, 0, -1):
        terminate_process_group(pid)
    assert calls == []


def test_terminate_process_group_signals_only_the_pid_when_it_shares_this_process_group(monkeypatch):
    """``killpg`` on this process's own group would stop the supervisor itself."""
    calls: list[tuple[str, int, int]] = []
    monkeypatch.setattr(os, "getpgid", lambda _pid: os.getpgrp())
    monkeypatch.setattr(os, "killpg", lambda pgid, sig: calls.append(("killpg", pgid, sig)))
    monkeypatch.setattr(os, "kill", lambda pid, sig: calls.append(("kill", pid, sig)))
    terminate_process_group(4242)
    assert calls == [("kill", 4242, signal.SIGTERM)]


def test_terminate_process_group_never_passes_a_group_id_of_this_group_or_init_to_killpg(monkeypatch):
    """Final landing review nit: ``killpg(0)`` addresses this process's own group (a kernel thread reports pgid 0)
    and ``killpg(1)`` init's group -- a pid in either is signalled alone, never its group."""
    calls: list[tuple[str, int, int]] = []
    monkeypatch.setattr(os, "getpgrp", lambda: 7777)
    monkeypatch.setattr(os, "killpg", lambda pgid, sig: calls.append(("killpg", pgid, sig)))
    monkeypatch.setattr(os, "kill", lambda pid, sig: calls.append(("kill", pid, sig)))
    for pgid in (0, 1):
        monkeypatch.setattr(os, "getpgid", lambda _pid, pgid=pgid: pgid)
        terminate_process_group(4242)
    assert calls == [("kill", 4242, signal.SIGTERM), ("kill", 4242, signal.SIGTERM)]


def test_terminate_process_group_signals_process_group(monkeypatch):
    calls: list[tuple[int, int]] = []

    def fake_getpgid(pid: int) -> int:
        assert pid == 99
        return 42

    def fake_killpg(pgid: int, sig: int) -> None:
        calls.append((pgid, sig))

    class _DeadProcess:
        def is_alive(self, _pid: int) -> bool:
            return False

    monkeypatch.setattr(os, "getpgid", fake_getpgid)
    monkeypatch.setattr(os, "killpg", fake_killpg)
    monkeypatch.setattr(os, "waitpid", lambda _pid, _opts: (0, 0))
    result = terminate_process_group(99, grace_s=0.0, process=_DeadProcess())
    assert (42, signal.SIGTERM) in calls
    assert isinstance(result, TerminateProcessGroupResult)
    assert result.signalled_term is True


def test_terminate_process_group_sends_sigkill_after_grace(monkeypatch):
    calls: list[tuple[int, int]] = []
    alive = {"v": True}

    class _AliveProcess:
        def is_alive(self, _pid: int) -> bool:
            return alive["v"]

    monkeypatch.setattr(os, "getpgid", lambda _pid: 42)
    monkeypatch.setattr(os, "killpg", lambda pgid, sig: calls.append((pgid, sig)))
    monkeypatch.setattr(os, "waitpid", lambda _pid, _opts: (0, 0))
    result = terminate_process_group(99, grace_s=0.0, process=_AliveProcess())
    assert (42, signal.SIGTERM) in calls
    assert (42, signal.SIGKILL) in calls
    assert result.signalled_kill is True


def test_wait_for_process_times_out_on_slow_child():
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        start_new_session=True,
    )
    try:
        result = wait_for_process(PosixProcess(), proc.pid, timeout_s=0.2, poll_s=0.05)
        assert result.exited is False
        assert result.returncode is None
    finally:
        terminate_process_group(proc.pid)


def test_fix_turn_rule_mutation_flag_off_skips_turn():
    """Removing the flag gate makes this fail (was run=True)."""
    assert (
        decide_verify_fix_turn(
            flag_enabled=True,
            verification_verdict=DispatchVerificationVerdict.REFUSED.value,
            has_git_progress=True,
            fix_turn_already_ran=False,
            session_alive=False,
        ).run
        is True
    )
    assert (
        decide_verify_fix_turn(
            flag_enabled=False,
            verification_verdict=DispatchVerificationVerdict.REFUSED.value,
            has_git_progress=True,
            fix_turn_already_ran=False,
            session_alive=False,
        ).run
        is False
    )


# --------------------------------------------------------------------------
# Story 85.2 (CAP-286): the pure in-flight reading the supervisor and every CLI reader share
# --------------------------------------------------------------------------


def _fix_lines(*entries):
    from pyforge.marshal.core.journal import prepare_for_write

    return [prepare_for_write(entry).line for entry in entries]


def _fix_entry(counter, phase, payload, *, intent_counter=None, run_id="run-1", ts="2026-10-03T10:00:00.000Z"):
    from pyforge.marshal.core import dispatch as dispatch_core
    from pyforge.marshal.core.journal import JournalEntryId, build_entry

    return build_entry(
        id=JournalEntryId("dispatch-supervisor-1", counter),
        ts=ts,
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_VERIFY_FIX,
        phase=phase,
        intent_id=JournalEntryId("dispatch-supervisor-1", intent_counter) if intent_counter is not None else None,
        payload=payload,
    )


def test_in_flight_verify_fix_turn_reads_the_open_intent_and_its_journaled_pid():
    from datetime import datetime, timezone

    from pyforge.marshal.core.dispatch_verify_fix import fix_intent_ref, in_flight_verify_fix_turn
    from pyforge.marshal.core.journal import JournalEntryId, Phase, fold

    ref = fix_intent_ref(JournalEntryId("dispatch-supervisor-1", 1))
    assert ref == {"writer_id": "dispatch-supervisor-1", "counter": 1}
    folded = fold(
        _fix_lines(
            _fix_entry(1, Phase.INTENT, {"launch_mode": "fix_only"}),
            _fix_entry(2, Phase.OBSERVATION, {"session_pid": 4242, "fix_intent_id": ref}),
            # Every decoy sits AFTER the real pid, where the reader's reverse scan meets it first (review L2/L3): an
            # observation naming another INTENT, a bool, a group-address pid, pid 0, and another run's pid are never
            # this turn's pid.
            _fix_entry(3, Phase.OBSERVATION, {"session_pid": 111, "fix_intent_id": {"writer_id": "x", "counter": 9}}),
            _fix_entry(4, Phase.OBSERVATION, {"session_pid": True, "fix_intent_id": ref}),
            _fix_entry(5, Phase.OBSERVATION, {"session_pid": -5, "fix_intent_id": ref}),
            _fix_entry(6, Phase.OBSERVATION, {"session_pid": 0, "fix_intent_id": ref}),
            _fix_entry(7, Phase.OBSERVATION, {"session_pid": 999, "fix_intent_id": ref}, run_id="run-2"),
        )
    )
    in_flight = in_flight_verify_fix_turn(folded, "run-1")
    assert in_flight is not None
    assert in_flight.session_pid == 4242
    assert in_flight.started_at == datetime(2026, 10, 3, 10, 0, tzinfo=timezone.utc)
    assert in_flight.intent.id == JournalEntryId("dispatch-supervisor-1", 1)
    assert in_flight_verify_fix_turn(folded, "run-other") is None


def test_in_flight_verify_fix_turn_prefers_a_pid_on_the_intent_and_reports_none_without_one():
    from pyforge.marshal.core.dispatch_verify_fix import in_flight_verify_fix_turn
    from pyforge.marshal.core.journal import Phase, fold

    on_intent = fold(_fix_lines(_fix_entry(1, Phase.INTENT, {"session_pid": 5151})))
    no_pid = fold(_fix_lines(_fix_entry(1, Phase.INTENT, {"launch_mode": "fix_only"})))
    assert in_flight_verify_fix_turn(on_intent, "run-1").session_pid == 5151
    assert in_flight_verify_fix_turn(no_pid, "run-1").session_pid is None


def test_a_closed_fix_turn_is_not_in_flight():
    from pyforge.marshal.core.dispatch_verify_fix import in_flight_verify_fix_turn, pending_verify_fix_intent
    from pyforge.marshal.core.journal import Phase, fold

    folded = fold(
        _fix_lines(
            _fix_entry(1, Phase.INTENT, {"session_pid": 5151}),
            _fix_entry(2, Phase.OUTCOME, {"ok": False}, intent_counter=1),
        )
    )
    assert pending_verify_fix_intent(folded, "run-1") is None
    assert in_flight_verify_fix_turn(folded, "run-1") is None


def test_fix_turn_remaining_budget_is_measured_from_the_intent_and_never_negative():
    from datetime import datetime, timedelta, timezone

    from pyforge.marshal.core.dispatch_verify_fix import fix_turn_remaining_budget_s

    started = datetime(2026, 10, 3, 10, 0, tzinfo=timezone.utc)
    assert (
        fix_turn_remaining_budget_s(budget_s=900.0, started_at=started, now=started + timedelta(seconds=100)) == 800.0
    )
    assert fix_turn_remaining_budget_s(budget_s=900.0, started_at=started, now=started + timedelta(hours=1)) == 0.0


def test_pid_start_matches_launch_is_story_83_1s_reuse_guard():
    from datetime import datetime, timezone

    from pyforge.marshal.core.dispatch import PID_START_TOLERANCE_SECONDS, pid_start_matches_launch

    launched = datetime(2026, 10, 3, 10, 0, tzinfo=timezone.utc)
    at = launched.timestamp()
    assert pid_start_matches_launch(at + 1.0, launched) is True
    assert pid_start_matches_launch(at - PID_START_TOLERANCE_SECONDS, launched) is True
    assert pid_start_matches_launch(at + PID_START_TOLERANCE_SECONDS + 1.0, launched) is False
    assert pid_start_matches_launch(at - 3600.0, launched) is False
    assert pid_start_matches_launch(None, launched) is True
    assert pid_start_matches_launch(at - 3600.0, None) is True
