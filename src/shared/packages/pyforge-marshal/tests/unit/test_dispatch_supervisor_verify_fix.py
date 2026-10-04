"""Supervisor-level tests for the dormant verify-fix turn (Story 85.1, spec-pyforge-marshal:CAP-286).

Story 85.1 lands the fix-turn machinery behind ``pyforge.marshal.verify_fix_loop``, OFF in every
environment. These tests drive ``dispatch_supervisor.__main__`` through its own ports -- the same fakes
``test_dispatch_supervisor_main_loop.py`` uses -- with the flag read for real from a flagd tree seeded under
the fake repo root, never stubbed:

* both flag states (two flagd trees, ``"on"`` and ``"off"``): with the flag off a refusal parks exactly as
  ``main`` does (Story 83.10) -- no fix-turn code runs and the verification OUTCOME keeps ``main``'s five
  keys; with it on the same refusal reaches the fix-turn launch;
* a verification journaled with failed commands while the flag was on, read back with the flag off: still no
  fix turn (forcing the flag on after the read makes this fail);
* an unreadable or invalid flag tree, or an unknown environment: one journaled warning, a park, no crash.

Story 85.2 (flag on unless a test says otherwise) drives one fix turn end to end: the failed commands read
through the sidecar resolver, the INTENT and the session pid journaled before the launch and the wait, the
turn's edits committed (or the story parked) before exactly one re-verification, MRS-DISP-060 on a still-red
re-verify, the one-turn bound across a restart, a restarted supervisor settling the turn it finds in flight
against a real detached session (waited for within the budget left from the INTENT's UTC timestamp, stopped
once that is spent; only stopped with the flag off), and the LIVE reading every CLI reader shares.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import test_dispatch_supervisor_main_loop as loop
from pyforge.testing_kit.flags import flagd_tree

from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core.dispatch_verify_fix import (
    FIX_TURN_START_FAILED_CODE,
    VERIFY_FIX_LOOP_FLAG_KEY,
    fix_intent_ref,
)
from pyforge.marshal.core.egress import Redacted
from pyforge.marshal.core.journal import JournalEntryId, Phase, build_entry, prepare_for_write
from pyforge.marshal.core.model import Finding, Severity, build_envelope
from pyforge.marshal.dispatch_supervisor import __main__ as supervisor_main

_FLAG_KEY = "pyforge.marshal.verify_fix_loop"
_COMMAND = "pixi run --frozen -e pyforge-marshal pyforge-marshal-test"
_SHORT_TAIL = "E501 line too long (101 > 100)\n"
_LONG_TAIL = "x" * 9000  # past the 4 KB output-tail bound and the journal's sidecar threshold
#: ``main``'s verification OUTCOME keys (Story 22.3 + Story 28.15), the flag-off shape.
_MAIN_OUTCOME_KEYS = {"verdict", "ok", "failed_gate", "failed_message", "scope_violation_advisories"}


@pytest.fixture(autouse=True)
def _hermetic_flag_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")


def test_the_flag_key_is_the_one_the_supervisor_reads() -> None:
    assert _FLAG_KEY == VERIFY_FIX_LOOP_FLAG_KEY


def _config_dir(repo_root: Path) -> Path:
    config = repo_root / "src/platform/config"
    config.mkdir(parents=True, exist_ok=True)
    return config


def _seed_flag(repo_root: Path, *, on: bool) -> None:
    """The flagd tree the supervisor reads, holding the fix-turn flag in one state."""
    config = _config_dir(repo_root)
    if on:
        flagd_tree(config, {_FLAG_KEY: "on"})
    else:
        flagd_tree(config, {_FLAG_KEY: "off"})


def _refused_with_output(tail: str):
    """A dispatch-verification refusal naming one failed verify command, with its output."""
    return build_envelope(
        command="dispatch verify",
        verdict="gate-failed",
        data={
            "slug": loop._SLUG,
            "commands": [{"command": _COMMAND, "returncode": 1, "stdout": tail, "stderr": ""}],
        },
        findings=(
            Finding(code="MRS-GATE-001", severity=Severity.ERROR, message=f"verify command {_COMMAND!r} exited 1"),
        ),
    )


def _journaled_refusal_with_failed_commands() -> tuple[str, str]:
    """A refused verification as a flag-on run journals it: ``failed_commands`` inline on the OUTCOME."""
    return loop._outcome_pair(
        kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
        payload={
            "verdict": "refused",
            "ok": False,
            "failed_gate": "MRS-GATE-001",
            "failed_message": f"verify command {_COMMAND!r} exited 1",
            "scope_violation_advisories": [],
            "failed_commands": [{"command": _COMMAND, "exit_code": 1, "output_tail": _SHORT_TAIL}],
        },
        counter=1,
    )


class _NoProfile:
    profile = None
    spec = None
    binary_path = None


def _spy_fix_turn(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record every fix-turn step reached; the launch refuses, so a reached turn journals MRS-DISP-058."""
    calls: list[str] = []

    def _resolve(*_args: object, **_kwargs: object) -> _NoProfile:
        calls.append("binary_present")
        return _NoProfile()

    def _launch(*_args: object, **_kwargs: object) -> None:
        calls.append("dispatch_verify_fix")
        raise supervisor_main.BuildHarnessError("test double: no harness")

    def _wait(*_args: object, **_kwargs: object) -> None:
        calls.append("wait_for_process")
        raise AssertionError("a fix turn must never be waited on in these tests")

    monkeypatch.setattr(supervisor_main.BmadBuildHarness, "binary_present", _resolve)
    monkeypatch.setattr(supervisor_main.BmadBuildHarness, "dispatch_verify_fix", _launch)
    monkeypatch.setattr(supervisor_main, "wait_for_process", _wait)
    return calls


def _entries(fs: loop.FakeFs) -> list[dict]:
    return [json.loads(line) for _path, line, _fsync in fs.appended]


def _verification_outcomes(fs: loop.FakeFs) -> list[dict]:
    return [
        entry["payload"]
        for entry in _entries(fs)
        if entry.get("kind") == dispatch_core.KIND_DISPATCH_VERIFICATION and entry.get("phase") == "outcome"
    ]


def _verify_fix_entries(fs: loop.FakeFs) -> list[dict]:
    return [entry for entry in _entries(fs) if entry.get("kind") == dispatch_core.KIND_DISPATCH_VERIFY_FIX]


def _finalize(
    fs: loop.FakeFs,
    repo_root: Path,
    worktree: Path,
    *,
    journal_lines: tuple[str, ...] = (),
    vcs: loop.FakeVcs | None = None,
):
    branch = dispatch_core.dispatch_worktree_branch(loop._SLUG, loop._STORY_KEY)
    if vcs is None:
        vcs = loop.FakeVcs(branches=frozenset({branch}), head_sha=loop._MOVED)
    return loop._finalize(fs, vcs, repo_root, worktree, journal_lines=journal_lines)


def _assert_parked_unverified(fs: loop.FakeFs, ok: bool) -> None:
    assert ok is True
    last = _entries(fs)[-1]
    assert last["kind"] == dispatch_core.KIND_DISPATCH_FINALIZE
    assert last["payload"]["verified"] is False


# --------------------------------------------------------------------------
# The verification OUTCOME line (narrowed AC 2)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("tail", [_SHORT_TAIL, _LONG_TAIL], ids=["short-tail", "long-tail"])
def test_a_flag_off_refusal_outcome_has_exactly_mains_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tail: str
) -> None:
    repo_root = loop._repo(tmp_path)
    _seed_flag(repo_root, on=False)
    worktree = loop._worktree(repo_root)
    monkeypatch.setattr(supervisor_main, "evaluate_dispatch_verification", lambda **_k: _refused_with_output(tail))
    fs = loop.FakeFs()

    loop._verify(fs, repo_root, worktree)

    outcome = _verification_outcomes(fs)[-1]
    assert set(outcome) == _MAIN_OUTCOME_KEYS
    assert (outcome["verdict"], outcome["failed_gate"]) == ("refused", "MRS-GATE-001")
    assert _COMMAND in outcome["failed_message"]


def test_a_flag_on_refusal_outcome_carries_the_failed_commands(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = loop._repo(tmp_path)
    _seed_flag(repo_root, on=True)
    worktree = loop._worktree(repo_root)
    monkeypatch.setattr(
        supervisor_main, "evaluate_dispatch_verification", lambda **_k: _refused_with_output(_SHORT_TAIL)
    )
    fs = loop.FakeFs()

    loop._verify(fs, repo_root, worktree)

    outcome = _verification_outcomes(fs)[-1]
    assert set(outcome) == _MAIN_OUTCOME_KEYS | {"failed_commands"}
    assert outcome["failed_commands"] == [{"command": _COMMAND, "exit_code": 1, "output_tail": _SHORT_TAIL}]


# --------------------------------------------------------------------------
# The finalize decision, in both flag states (narrowed AC 2; the flag-gate two-state test)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("on", [True, False], ids=["on", "off"])
def test_a_refusal_reaches_the_fix_turn_only_with_the_flag_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, on: bool
) -> None:
    repo_root = loop._repo(tmp_path)
    _seed_flag(repo_root, on=on)
    worktree = loop._worktree(repo_root)
    loop._seed_spec(repo_root, worktree, primary=loop._READY_SPEC_TEXT)
    monkeypatch.setattr(
        supervisor_main, "evaluate_dispatch_verification", lambda **_k: _refused_with_output(_SHORT_TAIL)
    )
    calls = _spy_fix_turn(monkeypatch)
    fs = loop.FakeFs()

    _counter, ok = _finalize(fs, repo_root, worktree)

    _assert_parked_unverified(fs, ok)
    outcome = _verification_outcomes(fs)[-1]
    fix_entries = _verify_fix_entries(fs)
    if on:
        assert calls == ["binary_present", "dispatch_verify_fix"]
        assert "failed_commands" in outcome
        assert [entry["phase"] for entry in fix_entries] == ["intent", "outcome"]
        assert fix_entries[-1]["payload"]["code"] == FIX_TURN_START_FAILED_CODE
    else:
        assert calls == []
        assert set(outcome) == _MAIN_OUTCOME_KEYS
        assert fix_entries == []


@pytest.mark.parametrize("on", [True, False], ids=["on", "off"])
def test_a_journaled_refusal_with_failed_commands_runs_no_fix_turn_once_the_flag_reads_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, on: bool
) -> None:
    """A refusal journaled while the flag was on (``failed_commands`` inline) is re-read at finalize: the flag
    decides there and then. Forcing the flag on right after the supervisor reads it makes the off case fail."""
    repo_root = loop._repo(tmp_path)
    _seed_flag(repo_root, on=on)
    worktree = loop._worktree(repo_root)
    loop._seed_spec(repo_root, worktree, primary=loop._READY_SPEC_TEXT)
    calls = _spy_fix_turn(monkeypatch)
    fs = loop.FakeFs()

    _counter, ok = _finalize(fs, repo_root, worktree, journal_lines=_journaled_refusal_with_failed_commands())

    _assert_parked_unverified(fs, ok)
    if on:
        assert calls == ["binary_present", "dispatch_verify_fix"]
    else:
        assert calls == []
        assert _verify_fix_entries(fs) == []


# --------------------------------------------------------------------------
# A broken flag tree or an unknown environment (narrowed AC 3)
# --------------------------------------------------------------------------


def _break_tree(repo_root: Path, monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    _seed_flag(repo_root, on=False)
    overlays = _config_dir(repo_root) / "flag-overlays.json"
    if case == "unknown-environment":
        monkeypatch.setenv("PYFORGE_ENVIRONMENT", "qa")
    elif case == "overlay-unknown-key":
        overlays.write_text(json.dumps({"dev": {"pyforge.no_such_flag": "on"}}), encoding="utf-8")
    else:
        overlays.write_text("{not json", encoding="utf-8")


@pytest.mark.parametrize("path", ["fresh", "journaled"])
@pytest.mark.parametrize("case", ["unknown-environment", "overlay-unknown-key", "overlay-not-json"])
def test_a_broken_flag_tree_parks_with_one_warning_and_no_fix_turn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str, path: str
) -> None:
    repo_root = loop._repo(tmp_path)
    _break_tree(repo_root, monkeypatch, case)
    worktree = loop._worktree(repo_root)
    loop._seed_spec(repo_root, worktree, primary=loop._READY_SPEC_TEXT)
    monkeypatch.setattr(
        supervisor_main, "evaluate_dispatch_verification", lambda **_k: _refused_with_output(_SHORT_TAIL)
    )
    calls = _spy_fix_turn(monkeypatch)
    journal_lines = _journaled_refusal_with_failed_commands() if path == "journaled" else ()
    fs = loop.FakeFs()

    _counter, ok = _finalize(fs, repo_root, worktree, journal_lines=journal_lines)

    _assert_parked_unverified(fs, ok)
    assert calls == []
    fix_entries = _verify_fix_entries(fs)
    assert [entry["phase"] for entry in fix_entries] == ["observation"]
    assert fix_entries[0]["payload"]["warning"]
    if path == "fresh":
        assert set(_verification_outcomes(fs)[-1]) == _MAIN_OUTCOME_KEYS


# --------------------------------------------------------------------------
# Story 85.2 — one fix turn end to end (flag on; supervisor ports only)
# --------------------------------------------------------------------------


def test_sidecar_failed_commands_still_reach_the_fix_turn(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A long output tail offloads ``failed_commands`` to a sidecar; finalize must still read it."""
    repo_root = loop._repo(tmp_path)
    _seed_flag(repo_root, on=True)
    worktree = loop._worktree(repo_root)
    loop._seed_spec(repo_root, worktree, primary=loop._READY_SPEC_TEXT)
    monkeypatch.setattr(
        supervisor_main, "evaluate_dispatch_verification", lambda **_k: _refused_with_output(_LONG_TAIL)
    )
    calls = _spy_fix_turn(monkeypatch)
    fs = loop.FakeFs()

    _finalize(fs, repo_root, worktree)

    assert calls == ["binary_present", "dispatch_verify_fix"]


def test_fix_turn_intent_is_journaled_before_the_harness_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = loop._repo(tmp_path)
    _seed_flag(repo_root, on=True)
    worktree = loop._worktree(repo_root)
    loop._seed_spec(repo_root, worktree, primary=loop._READY_SPEC_TEXT)
    order: list[str] = []

    def _launch(*_a, **_k):
        order.append("launch")
        raise supervisor_main.BuildHarnessError("stop after intent ordering check")

    monkeypatch.setattr(supervisor_main.BmadBuildHarness, "binary_present", lambda *_a, **_k: _NoProfile())
    monkeypatch.setattr(supervisor_main.BmadBuildHarness, "dispatch_verify_fix", _launch)

    real_append = supervisor_main._append_entry

    def _append(fs, run_dir, entry, **kwargs):
        from pyforge.marshal.core.journal import Phase

        if entry.kind == dispatch_core.KIND_DISPATCH_VERIFY_FIX and entry.phase is Phase.INTENT:
            order.append("intent")
        return real_append(fs, run_dir, entry, **kwargs)

    monkeypatch.setattr(supervisor_main, "_append_entry", _append)
    monkeypatch.setattr(
        supervisor_main, "evaluate_dispatch_verification", lambda **_k: _refused_with_output(_SHORT_TAIL)
    )
    fs = loop.FakeFs()

    _finalize(fs, repo_root, worktree)

    assert order.index("intent") < order.index("launch")


# --------------------------------------------------------------------------
# Story 85.2 — the fix turn's fakes: a tree the fake session dirties and only a commit cleans
# --------------------------------------------------------------------------

_WIP_SUBJECT = "marshal: pre-verify WIP checkpoint"


class _FixTurnVcs(loop.FakeVcs):
    """A worktree that starts clean (review M1): the fake fix session dirties it, and only a commit cleans it."""

    def __init__(self, events: list[tuple], *, commit_cleans: bool = True, **kwargs: object) -> None:
        kwargs.setdefault("dirty", False)
        kwargs.setdefault("changed_vs_head", ("fix.py",))
        kwargs.setdefault("branches", frozenset({dispatch_core.dispatch_worktree_branch(loop._SLUG, loop._STORY_KEY)}))
        kwargs.setdefault("head_sha", loop._MOVED)
        super().__init__(**kwargs)
        self.events = events
        self._commit_cleans = commit_cleans

    def commit_paths(self, repo_root: Path, paths: tuple[Path, ...], message: Redacted) -> str:
        sha = super().commit_paths(repo_root, paths, message)
        self.events.append(("commit", message.text))
        if self._commit_cleans:
            self.dirty = False
        return sha

    def push(self, repo_root: Path, branch: str) -> None:
        self.events.append(("push", self.dirty))
        super().push(repo_root, branch)


class _Launch:
    def __init__(self, pid: int) -> None:
        self.pid = pid


def _fake_fix_session(
    monkeypatch: pytest.MonkeyPatch,
    vcs: _FixTurnVcs,
    *,
    pid: int = 88001,
    returncode: int | None = 0,
) -> list[int]:
    """The harness side of a fix turn: each launch dirties the tree (the session edits, never commits) and the
    wait reports the session's exit. Returns the launched pids, one per launch."""
    from pyforge.marshal.dispatch_verify import ProcessWaitResult

    launches: list[int] = []

    def _launch(*_a: object, **_k: object) -> _Launch:
        launches.append(pid)
        vcs.events.append(("launch",))
        vcs.dirty = True
        return _Launch(pid)

    def _wait(*_a: object, **_k: object) -> ProcessWaitResult:
        vcs.events.append(("wait",))
        return ProcessWaitResult(exited=True, returncode=returncode)

    monkeypatch.setattr(supervisor_main.BmadBuildHarness, "binary_present", lambda *_a, **_k: _NoProfile())
    monkeypatch.setattr(supervisor_main.BmadBuildHarness, "dispatch_verify_fix", _launch)
    monkeypatch.setattr(supervisor_main, "wait_for_process", _wait)
    return launches


def _scripted_verification(monkeypatch: pytest.MonkeyPatch, events: list[tuple], *envelopes) -> None:
    """Each verification returns the next envelope (the last one repeats) and logs itself in ``events``."""
    script = list(envelopes)
    calls = {"n": 0}

    def _evaluate(**_kwargs: object):
        calls["n"] += 1
        events.append(("verify", calls["n"]))
        return script[min(calls["n"], len(script)) - 1]

    monkeypatch.setattr(supervisor_main, "evaluate_dispatch_verification", _evaluate)


def _finalize_outcome(fs: loop.FakeFs) -> dict:
    outcomes = [
        entry["payload"]
        for entry in _entries(fs)
        if entry.get("kind") == dispatch_core.KIND_DISPATCH_FINALIZE and entry.get("phase") == "outcome"
    ]
    assert len(outcomes) == 1
    return outcomes[0]


def _fix_ready_repo(tmp_path: Path, *, on: bool = True) -> tuple[Path, Path]:
    repo_root = loop._repo(tmp_path)
    _seed_flag(repo_root, on=on)
    worktree = loop._worktree(repo_root)
    loop._seed_spec(repo_root, worktree, primary=loop._READY_SPEC_TEXT)
    return repo_root, worktree


def _ts(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def _fix_intent_lines(
    pid: int | None,
    *,
    started_at: datetime,
    budget_s: float = 900.0,
    run_id: str = loop._RUN_ID,
) -> tuple[str, ...]:
    """A fix-turn INTENT a killed supervisor journaled, and -- with ``pid`` -- the pid OBSERVATION naming it."""
    intent = build_entry(
        id=JournalEntryId("dispatch-supervisor-1", 10),
        ts=_ts(started_at),
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_VERIFY_FIX,
        phase=Phase.INTENT,
        payload={
            "launch_mode": "fix_only",
            "prompt_bytes": 12,
            "failed_command_count": 1,
            "wall_clock_budget_s": budget_s,
        },
    )
    lines = [prepare_for_write(intent).line]
    if pid is not None:
        observation = build_entry(
            id=JournalEntryId("dispatch-supervisor-1", 11),
            ts=_ts(started_at),
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_VERIFY_FIX,
            phase=Phase.OBSERVATION,
            payload={"session_pid": pid, "ok": True, "fix_intent_id": fix_intent_ref(intent.id)},
        )
        lines.append(prepare_for_write(observation).line)
    return tuple(lines)


def _finalize_with(
    fs: loop.FakeFs,
    vcs: loop.FakeVcs,
    repo_root: Path,
    worktree: Path,
    *,
    process: object,
    journal_lines: tuple[str, ...],
    publish_heartbeat=None,
):
    """``loop._finalize`` with the process port chosen by the test -- a real one for a real detached session."""
    run_dir = loop._run_dir(repo_root)
    loop._seed_journal(run_dir, (loop._launch_line(), *journal_lines))
    folded = supervisor_main._fold_dispatch_journal(fs, run_dir, fs.journal_text(run_dir))
    return supervisor_main._run_supervisor_finalize_sequence(
        fs=fs,
        vcs=vcs,
        process=process,
        run_dir=run_dir,
        run_id=loop._RUN_ID,
        writer_id="dispatch-supervisor-2",
        counter=0,
        repo_root=repo_root,
        slug=loop._SLUG,
        story_key=loop._STORY_KEY,
        worktree=worktree,
        git_facts=loop._git_facts(),
        session_log="implementation done",
        merge_subject_template=loop._TEMPLATE,
        folded=folded,
        publish_heartbeat=publish_heartbeat,
    )


# --------------------------------------------------------------------------
# Story 85.2 AC1 — a green fix turn commits its edits, re-verifies once and lands
# --------------------------------------------------------------------------


def test_a_green_fix_turn_commits_reverifies_and_lands_through_the_tick_loop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review M6: push -> verify (failed commands offloaded to a sidecar) -> launch -> wait -> commit -> verify ->
    land, driven through ``run_dispatch_supervisor`` itself."""
    monkeypatch.setattr(supervisor_main, "time", loop._FakeClock())
    repo_root, worktree = _fix_ready_repo(tmp_path)
    run_dir = loop._run_dir(repo_root)
    loop._seed_journal(run_dir, (loop._launch_line(),))
    (run_dir / "session.log").write_text("implementation done\n", encoding="utf-8")
    events: list[tuple] = []
    vcs = _FixTurnVcs(events)
    launches = _fake_fix_session(monkeypatch, vcs)
    _scripted_verification(monkeypatch, events, _refused_with_output(_LONG_TAIL), loop._clean_envelope())
    land_calls = loop._patch_landing(monkeypatch)
    real_land = supervisor_main.execute_dispatch_land

    def _land(**kwargs: object):
        events.append(("land", vcs.dirty))
        return real_land(**kwargs)

    monkeypatch.setattr(supervisor_main, "execute_dispatch_land", _land)
    fs = loop.FakeFs()

    code = loop._run(repo_root, fs=fs, vcs=vcs, process=loop.FakeProcess(alive=False), publisher=loop.FakePublisher())

    assert code == 0
    first_outcome = _verification_outcomes(fs)[0]
    assert "failed_commands" not in first_outcome, "the long tail must reach the fix turn through a sidecar"
    assert launches == [88001]
    assert len(land_calls) == 1
    kinds = [event[0] for event in events]
    assert kinds == ["push", "verify", "launch", "wait", "commit", "verify", "land"]
    assert ("commit", _WIP_SUBJECT) in events
    assert ("land", False) in events, "landing must see the fix turn's edits committed"
    assert _finalize_outcome(fs)["verified"] is True


def test_a_fix_turn_commits_its_edits_between_the_launch_and_the_reverification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review M1: the tree starts clean, the session dirties it, and only the pre-verify WIP commit cleans it --
    dropping that commit makes this fail."""
    repo_root, worktree = _fix_ready_repo(tmp_path)
    events: list[tuple] = []
    vcs = _FixTurnVcs(events)
    _fake_fix_session(monkeypatch, vcs)
    _scripted_verification(monkeypatch, events, _refused_with_output(_SHORT_TAIL), loop._clean_envelope())
    fs = loop.FakeFs()

    _counter, ok = _finalize(fs, repo_root, worktree, vcs=vcs)

    assert ok is True
    launch_at = events.index(("launch",))
    commit_at = events.index(("commit", _WIP_SUBJECT))
    reverify_at = events.index(("verify", 2))
    assert launch_at < commit_at < reverify_at
    assert vcs.dirty is False
    outcome = _finalize_outcome(fs)
    assert (outcome["verified"], outcome["committed"], outcome["ok"]) == (True, True, True)


def test_the_launch_journals_the_session_pid_before_the_wait(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Review MI/M3: the pid a restarted supervisor waits for is on disk, naming its INTENT in the journal's own id
    form, before the wait starts."""
    from pyforge.marshal.dispatch_verify import ProcessWaitResult

    repo_root, worktree = _fix_ready_repo(tmp_path)
    events: list[tuple] = []
    vcs = _FixTurnVcs(events)
    _fake_fix_session(monkeypatch, vcs, pid=88123)
    _scripted_verification(monkeypatch, events, _refused_with_output(_SHORT_TAIL), loop._clean_envelope())
    fs = loop.FakeFs()
    seen_at_wait: list[list[dict]] = []

    def _wait(*_a: object, **_k: object) -> ProcessWaitResult:
        seen_at_wait.append(_verify_fix_entries(fs))
        return ProcessWaitResult(exited=True, returncode=0)

    monkeypatch.setattr(supervisor_main, "wait_for_process", _wait)

    _finalize(fs, repo_root, worktree, vcs=vcs)

    assert len(seen_at_wait) == 1
    intent, observation = seen_at_wait[0]
    assert intent["phase"] == "intent"
    assert observation["phase"] == "observation"
    assert observation["payload"] == {"session_pid": 88123, "ok": True, "fix_intent_id": intent["id"]}
    pid_appends = [fsync for _path, line, fsync in fs.appended if '"session_pid": 88123' in line]
    assert pid_appends[0] is True, "the pid observation is fsynced"


def test_a_fix_turn_intent_that_cannot_be_journaled_launches_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review M4: journal every step before it acts -- no INTENT on disk, no launch."""
    repo_root, worktree = _fix_ready_repo(tmp_path)
    events: list[tuple] = []
    vcs = _FixTurnVcs(events)
    launches = _fake_fix_session(monkeypatch, vcs)
    _scripted_verification(monkeypatch, events, _refused_with_output(_SHORT_TAIL))
    real_append = supervisor_main._append_entry

    def _append(fs, run_dir, entry, **kwargs):
        if entry.kind == dispatch_core.KIND_DISPATCH_VERIFY_FIX and entry.phase is Phase.INTENT:
            raise supervisor_main.FsError("disk full (test double)")
        return real_append(fs, run_dir, entry, **kwargs)

    monkeypatch.setattr(supervisor_main, "_append_entry", _append)
    fs = loop.FakeFs()

    _counter, ok = _finalize(fs, repo_root, worktree, vcs=vcs)

    assert launches == []
    assert ok is False
    outcome = _finalize_outcome(fs)
    assert (outcome["ok"], outcome["verified"], outcome["failed_step"]) == (False, False, "verify-fix-intent")
    assert "disk full" in outcome["failed_message"]


# --------------------------------------------------------------------------
# Story 85.2 AC2/AC4 — a still-red re-verify parks with MRS-DISP-060; never a second turn
# --------------------------------------------------------------------------


def test_reverify_still_refused_emits_mrs_disp_060_and_launches_exactly_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pyforge.marshal.core.dispatch_verify_fix import FIX_TURN_REVERIFY_REFUSED_CODE

    repo_root, worktree = _fix_ready_repo(tmp_path)
    events: list[tuple] = []
    vcs = _FixTurnVcs(events)
    launches = _fake_fix_session(monkeypatch, vcs)
    _scripted_verification(monkeypatch, events, _refused_with_output(_SHORT_TAIL))
    fs = loop.FakeFs()

    _counter, ok = _finalize(fs, repo_root, worktree, vcs=vcs)

    assert launches == [88001], "exactly one fix turn for one refusal"
    assert [event for event in events if event[0] == "verify"] == [("verify", 1), ("verify", 2)]
    parks = [
        entry["payload"]
        for entry in _verify_fix_entries(fs)
        if entry["phase"] == "observation" and entry["payload"].get("code") == FIX_TURN_REVERIFY_REFUSED_CODE
    ]
    assert len(parks) == 1
    assert parks[0]["failed_command"] == _COMMAND
    assert parks[0]["finding"]["code"] == FIX_TURN_REVERIFY_REFUSED_CODE
    assert parks[0]["finding"]["message"] == (
        f"verification still refused after one fix turn ({_COMMAND!r}) — story parked for the operator "
        "(Story 85.1 / 83.10)"
    )
    assert ok is True
    assert _finalize_outcome(fs)["verified"] is False


def test_a_finished_fix_turn_with_a_still_red_reverify_never_launches_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review H3: the supervisor was killed after the fix turn's OUTCOME but before its re-verify journaled; the
    next pass re-verifies, still red, and must not launch a second turn (the one-turn bound, both at the call
    site and in ``decide_verify_fix_turn``). Final landing review L1: that park still journals MRS-DISP-060,
    naming the still-failing command and the turn's INTENT."""
    from pyforge.marshal.core.dispatch_verify_fix import FIX_TURN_REVERIFY_REFUSED_CODE

    repo_root, worktree = _fix_ready_repo(tmp_path)
    lines = _finished_fix_turn_lines(ok=True)
    events: list[tuple] = []
    vcs = _FixTurnVcs(events)
    launches = _fake_fix_session(monkeypatch, vcs)
    _scripted_verification(monkeypatch, events, _refused_with_output(_SHORT_TAIL))
    fs = loop.FakeFs()

    _counter, ok = _finalize(fs, repo_root, worktree, journal_lines=lines, vcs=vcs)

    assert launches == [], "a second fix turn was launched for one refusal"
    assert [event for event in events if event[0] == "verify"] == [("verify", 1)]
    parks = [
        entry for entry in _verify_fix_entries(fs) if entry["payload"].get("code") == FIX_TURN_REVERIFY_REFUSED_CODE
    ]
    assert len(parks) == 1, "a red re-verify after a crash-recovered fix turn parks with MRS-DISP-060"
    assert parks[0]["phase"] == "observation"
    assert parks[0]["payload"]["failed_command"] == _COMMAND
    assert parks[0]["payload"]["fix_intent_id"] == {"writer_id": "dispatch-supervisor-1", "counter": 10}
    assert parks[0]["payload"]["finding"]["message"] == (
        f"verification still refused after one fix turn ({_COMMAND!r}) — story parked for the operator "
        "(Story 85.1 / 83.10)"
    )
    assert ok is True
    assert _finalize_outcome(fs)["verified"] is False
    _assert_journal_ids_unique(lines, fs)


def _assert_journal_ids_unique(lines: tuple[str, ...], fs: loop.FakeFs) -> None:
    """Every entry id -- the seeded journal's and each one this pass appended -- names one entry only."""
    ids = [json.dumps(json.loads(line)["id"], sort_keys=True) for line in lines]
    ids += [json.dumps(entry["id"], sort_keys=True) for entry in _entries(fs)]
    assert len(ids) == len(set(ids)), f"duplicate journal entry ids: {sorted(ids)}"


def _finished_fix_turn_lines(
    *, ok: bool, reverified_and_parked: bool = False, park_intent_counter: int = 10
) -> tuple[str, ...]:
    """A refusal, then a fix turn whose OUTCOME a killed supervisor journaled (``ok`` as given); with
    ``reverified_and_parked`` its still-red re-verify and an MRS-DISP-060 were journaled too, the 060 naming the
    INTENT at ``park_intent_counter`` (this turn's is 10)."""
    from pyforge.marshal.core.dispatch_verify_fix import FIX_TURN_REVERIFY_REFUSED_CODE

    started = datetime(2026, 10, 3, 10, 0, tzinfo=timezone.utc)
    intent_line = _fix_intent_lines(None, started_at=started)[0]
    intent_id = JournalEntryId("dispatch-supervisor-1", 10)
    outcome = build_entry(
        id=JournalEntryId("dispatch-supervisor-1", 12),
        ts=_ts(started + timedelta(minutes=5)),
        run_id=loop._RUN_ID,
        kind=dispatch_core.KIND_DISPATCH_VERIFY_FIX,
        phase=Phase.OUTCOME,
        intent_id=intent_id,
        payload={"ok": ok, "session_pid": 88100, "session_returncode": 0 if ok else 1, "elapsed_s": 300.0},
    )
    lines = [*_journaled_refusal_with_failed_commands(), intent_line, prepare_for_write(outcome).line]
    if reverified_and_parked:
        refusal = json.loads(_journaled_refusal_with_failed_commands()[1])["payload"]
        lines.extend(loop._outcome_pair(kind=dispatch_core.KIND_DISPATCH_VERIFICATION, payload=refusal, counter=20))
        park = build_entry(
            id=JournalEntryId("dispatch-supervisor-1", 13),
            ts=_ts(started + timedelta(minutes=6)),
            run_id=loop._RUN_ID,
            kind=dispatch_core.KIND_DISPATCH_VERIFY_FIX,
            phase=Phase.OBSERVATION,
            payload={
                "ok": False,
                "code": FIX_TURN_REVERIFY_REFUSED_CODE,
                "fix_intent_id": fix_intent_ref(JournalEntryId("dispatch-supervisor-1", park_intent_counter)),
            },
        )
        lines.append(prepare_for_write(park).line)
    return tuple(lines)


@pytest.mark.parametrize("case", ["already-parked", "turn-failed"])
def test_mrs_disp_060_is_journaled_once_and_only_for_a_turn_that_finished(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    """Final landing review L1, the edges: a park already journaled for the turn's INTENT is never repeated on a later
    pass, and a turn whose session failed (``ok: false``) is not re-verified and owes no MRS-DISP-060."""
    from pyforge.marshal.core.dispatch_verify_fix import FIX_TURN_REVERIFY_REFUSED_CODE

    repo_root, worktree = _fix_ready_repo(tmp_path)
    if case == "already-parked":
        lines = _finished_fix_turn_lines(ok=True, reverified_and_parked=True)
    else:
        lines = _finished_fix_turn_lines(ok=False)
    events: list[tuple] = []
    vcs = _FixTurnVcs(events)
    launches = _fake_fix_session(monkeypatch, vcs)
    _scripted_verification(monkeypatch, events, _refused_with_output(_SHORT_TAIL))
    fs = loop.FakeFs()

    _counter, ok = _finalize(fs, repo_root, worktree, journal_lines=lines, vcs=vcs)

    assert launches == []
    assert [event for event in events if event[0] == "verify"] == []
    assert [
        entry for entry in _verify_fix_entries(fs) if entry["payload"].get("code") == FIX_TURN_REVERIFY_REFUSED_CODE
    ] == []
    assert ok is True
    assert _finalize_outcome(fs)["verified"] is False
    _assert_journal_ids_unique(lines, fs)


def test_a_park_journaled_for_another_intent_does_not_stand_in_for_this_turns_mrs_disp_060(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Delta review L1: the once-per-INTENT dedupe matches on the turn's own INTENT. An MRS-DISP-060 naming another
    INTENT leaves this turn's park owed -- journaled once, naming INTENT 10, with no second verify or launch."""
    from pyforge.marshal.core.dispatch_verify_fix import FIX_TURN_REVERIFY_REFUSED_CODE

    repo_root, worktree = _fix_ready_repo(tmp_path)
    lines = _finished_fix_turn_lines(ok=True, reverified_and_parked=True, park_intent_counter=99)
    events: list[tuple] = []
    vcs = _FixTurnVcs(events)
    launches = _fake_fix_session(monkeypatch, vcs)
    _scripted_verification(monkeypatch, events, _refused_with_output(_SHORT_TAIL))
    fs = loop.FakeFs()

    _counter, ok = _finalize(fs, repo_root, worktree, journal_lines=lines, vcs=vcs)

    assert launches == []
    assert [event for event in events if event[0] == "verify"] == []
    parks = [
        entry for entry in _verify_fix_entries(fs) if entry["payload"].get("code") == FIX_TURN_REVERIFY_REFUSED_CODE
    ]
    assert len(parks) == 1
    assert parks[0]["payload"]["fix_intent_id"] == {"writer_id": "dispatch-supervisor-1", "counter": 10}
    assert ok is True
    _assert_journal_ids_unique(lines, fs)


# --------------------------------------------------------------------------
# Story 85.2 review H2 — the turn's edits are committed, or the story parks
# --------------------------------------------------------------------------


@pytest.mark.parametrize("failure", ["commit-raises", "still-dirty"])
def test_a_fix_turn_whose_edits_are_not_committed_parks_without_reverifying(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    repo_root, worktree = _fix_ready_repo(tmp_path)
    events: list[tuple] = []
    if failure == "commit-raises":
        vcs = _FixTurnVcs(events, commit_paths_raises=True)
    else:
        vcs = _FixTurnVcs(events, commit_cleans=False)
    _fake_fix_session(monkeypatch, vcs)
    _scripted_verification(monkeypatch, events, _refused_with_output(_SHORT_TAIL), loop._clean_envelope())
    fs = loop.FakeFs()

    _counter, ok = _finalize(fs, repo_root, worktree, vcs=vcs)

    assert [event for event in events if event[0] == "verify"] == [("verify", 1)], "a dirty tree is never re-verified"
    refusals = [entry["payload"] for entry in _verify_fix_entries(fs) if entry["payload"].get("step") == "commit"]
    assert len(refusals) == 1 and refusals[0]["ok"] is False
    assert ok is False
    outcome = _finalize_outcome(fs)
    assert (outcome["ok"], outcome["verified"], outcome["failed_step"]) == (False, False, "commit")
    expected = "git commit failed" if failure == "commit-raises" else "still has uncommitted changes"
    assert expected in outcome["failed_message"]


# --------------------------------------------------------------------------
# Story 85.2 AC3 — a restarted supervisor settles the fix turn it finds in flight
# --------------------------------------------------------------------------


def _spawn_detached(seconds: float) -> int:
    """A real session that is NOT this process's child -- the shape a restarted supervisor finds: started by a
    shell in its own session (so its group holds nothing else), the shell exits, and init reaps it."""
    out = subprocess.run(
        ["sh", "-c", f"sleep {seconds} >/dev/null 2>&1 & echo $!"],
        capture_output=True,
        text=True,
        check=True,
        start_new_session=True,
    )
    return int(out.stdout.strip())


def _running(pid: int) -> bool:
    try:
        state = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except OSError:
        return False
    return state[state.rfind(")") + 2] != "Z"


def _kill(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass


def _record_stops(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Wrap the real ``terminate_process_group``: record each pid the supervisor stops, then really stop it."""
    real = supervisor_main.terminate_process_group
    stops: list[int] = []

    def _stop(pid: int, **kwargs: object):
        stops.append(pid)
        return real(pid, **kwargs)

    monkeypatch.setattr(supervisor_main, "terminate_process_group", _stop)
    return stops


def _gone_within(pid: int, seconds: float = 10.0) -> bool:
    """Whether the signalled session is gone (or a zombie) within ``seconds`` -- generous for a loaded host."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if not _running(pid):
            return True
        time.sleep(0.05)
    return not _running(pid)


def _proc_state(pid: int) -> str:
    try:
        return Path(f"/proc/{pid}/status").read_text(encoding="utf-8").replace("\n", " | ")[:600]
    except OSError:
        return "gone"


def test_a_restarted_supervisor_waits_out_the_remaining_budget_then_stops_a_live_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review H1: the real ``wait_for_process`` (never stubbed) against a live non-child session -- the old wait
    returned at once on ``ChildProcessError``. It waits the ~1.5 s left of the budget, stops the session, journals
    MRS-DISP-059, and commits nothing the session was writing."""
    from pyforge.core.process import PosixProcess

    repo_root, worktree = _fix_ready_repo(tmp_path)
    pid = _spawn_detached(60)
    launches: list[int] = []
    monkeypatch.setattr(supervisor_main.BmadBuildHarness, "dispatch_verify_fix", lambda *_a, **_k: launches.append(1))
    events: list[tuple] = []
    _scripted_verification(monkeypatch, events, loop._clean_envelope())
    budget_s = 3.0
    started = datetime.now(timezone.utc) - timedelta(seconds=budget_s - 1.5)
    lines = (*_journaled_refusal_with_failed_commands(), *_fix_intent_lines(pid, started_at=started, budget_s=budget_s))
    vcs = _FixTurnVcs(events, dirty=True, changed_vs_head=("half-written.py",))
    stops = _record_stops(monkeypatch)
    fs = loop.FakeFs()
    try:
        assert _running(pid)
        t0 = time.monotonic()
        _counter, ok = _finalize_with(fs, vcs, repo_root, worktree, process=PosixProcess(), journal_lines=lines)
        elapsed = time.monotonic() - t0
        journaled = [(entry["phase"], entry["payload"]) for entry in _verify_fix_entries(fs)]
        assert stops == [pid], f"the session must be stopped once the budget is spent: {journaled}"
        assert _gone_within(pid), f"stopped session still running: {_proc_state(pid)}"
    finally:
        _kill(pid)

    assert 1.0 <= elapsed < 10.0, f"waited {elapsed:.2f}s for a ~1.5s remaining budget"
    assert launches == []
    assert vcs.commits == [], "the half-written tree must never be committed"
    assert [event for event in events if event[0] == "verify"] == []
    from pyforge.marshal.core.dispatch_verify_fix import FIX_TURN_TIMEOUT_CODE

    outcome = [entry for entry in _verify_fix_entries(fs) if entry["phase"] == "outcome"]
    assert len(outcome) == 1
    assert outcome[0]["payload"]["code"] == FIX_TURN_TIMEOUT_CODE
    assert outcome[0]["payload"]["session_pid"] == pid
    assert outcome[0]["intent_id"] == {"writer_id": "dispatch-supervisor-1", "counter": 10}
    assert ok is True
    assert _finalize_outcome(fs)["verified"] is False


def test_a_restarted_supervisor_waits_for_a_session_that_exits_in_budget_then_commits_and_reverifies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review H1: the session exits inside the remaining budget; only then are its edits committed and verified,
    once -- its exit code is unknowable to a supervisor that did not launch it, so the re-verify decides."""
    from pyforge.core.process import PosixProcess

    repo_root, worktree = _fix_ready_repo(tmp_path)
    pid = _spawn_detached(1)
    launches: list[int] = []
    monkeypatch.setattr(supervisor_main.BmadBuildHarness, "dispatch_verify_fix", lambda *_a, **_k: launches.append(1))
    events: list[tuple] = []
    _scripted_verification(monkeypatch, events, loop._clean_envelope())
    lines = (
        *_journaled_refusal_with_failed_commands(),
        *_fix_intent_lines(pid, started_at=datetime.now(timezone.utc), budget_s=60.0),
    )

    class _ObservingVcs(_FixTurnVcs):
        def commit_paths(self, repo_root: Path, paths: tuple[Path, ...], message: Redacted) -> str:
            self.events.append(("session-running-at-commit", _running(pid)))
            return super().commit_paths(repo_root, paths, message)

    vcs = _ObservingVcs(events, dirty=True)
    fs = loop.FakeFs()
    try:
        t0 = time.monotonic()
        _counter, ok = _finalize_with(fs, vcs, repo_root, worktree, process=PosixProcess(), journal_lines=lines)
        elapsed = time.monotonic() - t0
    finally:
        _kill(pid)

    assert 0.5 <= elapsed < 30.0, f"waited {elapsed:.2f}s for a session that sleeps 1s"
    assert launches == []
    assert events[0] == ("session-running-at-commit", False)
    assert ("commit", _WIP_SUBJECT) in events
    assert [event for event in events if event[0] == "verify"] == [("verify", 1)]
    outcome = [entry["payload"] for entry in _verify_fix_entries(fs) if entry["phase"] == "outcome"]
    assert len(outcome) == 1
    assert (outcome[0]["ok"], outcome[0]["session_returncode"], outcome[0]["session_pid"]) == (True, None, pid)
    assert ok is True
    assert _finalize_outcome(fs)["verified"] is True


def test_with_the_flag_off_a_pending_fix_turn_is_only_stopped_journaled_and_parked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With the flag off a turn found in flight is stopped at once -- never waited for, committed, re-verified or
    landed. (The flag-on cases are the two tests above.)"""
    from pyforge.core.process import PosixProcess

    repo_root, worktree = _fix_ready_repo(tmp_path, on=False)
    pid = _spawn_detached(60)
    calls = _spy_fix_turn(monkeypatch)
    events: list[tuple] = []
    _scripted_verification(monkeypatch, events, loop._clean_envelope())
    lines = (
        *_journaled_refusal_with_failed_commands(),
        *_fix_intent_lines(pid, started_at=datetime.now(timezone.utc), budget_s=900.0),
    )
    vcs = _FixTurnVcs(events, dirty=True, changed_vs_head=("half-written.py",))
    stops = _record_stops(monkeypatch)
    fs = loop.FakeFs()
    try:
        t0 = time.monotonic()
        _counter, ok = _finalize_with(fs, vcs, repo_root, worktree, process=PosixProcess(), journal_lines=lines)
        elapsed = time.monotonic() - t0
        journaled = [(entry["phase"], entry["payload"]) for entry in _verify_fix_entries(fs)]
        gone = _gone_within(pid)
        state = _proc_state(pid)
    finally:
        _kill(pid)

    assert stops == [pid], f"the in-flight session is stopped: {journaled}"
    assert gone, f"stopped session still running: {state}"
    assert elapsed < 5.0, "never waited for"
    assert calls == []
    assert vcs.commits == []
    assert [event for event in events if event[0] == "verify"] == []
    outcome = [entry["payload"] for entry in _verify_fix_entries(fs) if entry["phase"] == "outcome"]
    assert len(outcome) == 1
    assert (outcome[0]["ok"], outcome[0]["stopped"], outcome[0]["session_pid"]) == (False, True, pid)
    assert "flag off" in outcome[0]["reason"]
    assert ok is True
    assert _finalize_outcome(fs)["verified"] is False


def test_a_restart_with_an_intent_but_no_recorded_pid_closes_it_and_launches_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review M3: nothing to wait for or stop -- the INTENT is closed with MRS-DISP-058 and no turn is relaunched."""
    repo_root, worktree = _fix_ready_repo(tmp_path)
    calls = _spy_fix_turn(monkeypatch)
    lines = (
        *_journaled_refusal_with_failed_commands(),
        *_fix_intent_lines(None, started_at=datetime.now(timezone.utc)),
    )
    fs = loop.FakeFs()

    _counter, ok = _finalize(fs, repo_root, worktree, journal_lines=lines)

    assert calls == []
    outcome = [entry for entry in _verify_fix_entries(fs) if entry["phase"] == "outcome"]
    assert len(outcome) == 1
    assert outcome[0]["payload"]["code"] == FIX_TURN_START_FAILED_CODE
    assert "pid not recorded" in outcome[0]["payload"]["error"]
    assert outcome[0]["intent_id"] == {"writer_id": "dispatch-supervisor-1", "counter": 10}
    run_dir = loop._run_dir(repo_root)
    folded = supervisor_main._fold_dispatch_journal(fs, run_dir, fs.journal_text(run_dir))
    assert supervisor_main.verify_fix_turn_in_flight(folded, loop._RUN_ID) is False
    assert ok is True
    assert _finalize_outcome(fs)["verified"] is False


def test_a_restarted_turn_whose_edits_cannot_be_committed_parks_with_a_failed_commit_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Final landing review L4: the pending-INTENT branch of finalize reports a failed commit the way the finalize
    commit step does -- ``ok: false, failed_step: commit`` -- and returns False; it never re-verifies or lands. The
    session already exited (``loop._finalize``'s process port reads every pid dead), so the turn is settled at once."""
    repo_root, worktree = _fix_ready_repo(tmp_path)
    launches: list[int] = []
    monkeypatch.setattr(supervisor_main.BmadBuildHarness, "dispatch_verify_fix", lambda *_a, **_k: launches.append(1))
    events: list[tuple] = []
    _scripted_verification(monkeypatch, events, loop._clean_envelope())
    lines = (
        *_journaled_refusal_with_failed_commands(),
        *_fix_intent_lines(88004, started_at=datetime.now(timezone.utc) - timedelta(seconds=5)),
    )
    vcs = _FixTurnVcs(events, dirty=True, commit_paths_raises=True)
    fs = loop.FakeFs()

    _counter, ok = _finalize(fs, repo_root, worktree, journal_lines=lines, vcs=vcs)

    assert ok is False
    assert launches == []
    assert [event for event in events if event[0] == "verify"] == []
    assert vcs.pushes == []
    fix_outcomes = [entry["payload"] for entry in _verify_fix_entries(fs) if entry["phase"] == "outcome"]
    assert len(fix_outcomes) == 1
    assert (fix_outcomes[0]["ok"], fix_outcomes[0]["session_returncode"]) == (True, None)
    refusals = [entry["payload"] for entry in _verify_fix_entries(fs) if entry["payload"].get("step") == "commit"]
    assert len(refusals) == 1 and refusals[0]["ok"] is False
    outcome = _finalize_outcome(fs)
    assert (outcome["ok"], outcome["verified"], outcome["failed_step"]) == (False, False, "commit")
    assert "git commit failed" in outcome["failed_message"]


def test_a_restart_resumes_with_the_budget_left_from_the_intents_utc_timestamp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review N7/LOW: the remaining budget is measured from the INTENT's UTC ``ts``, never a monotonic reading
    another process took."""
    from pyforge.marshal.dispatch_verify import ProcessWaitResult

    repo_root, worktree = _fix_ready_repo(tmp_path)
    started = datetime(2026, 10, 3, 10, 0, tzinfo=timezone.utc)
    lines = (*_journaled_refusal_with_failed_commands(), *_fix_intent_lines(88003, started_at=started, budget_s=900.0))
    launches: list[str] = []
    waits: list[tuple[int, float, datetime | None]] = []

    def _wait(_process, pid, *, timeout_s, on_poll=None, launched_at=None):
        waits.append((pid, timeout_s, launched_at))
        return ProcessWaitResult(exited=True, returncode=1)

    monkeypatch.setattr(supervisor_main.BmadBuildHarness, "dispatch_verify_fix", lambda *_a, **_k: launches.append("x"))
    monkeypatch.setattr(supervisor_main, "wait_for_process", _wait)
    monkeypatch.setattr(supervisor_main, "_now_utc", lambda: started + timedelta(seconds=100))
    fs = loop.FakeFs()

    _finalize(fs, repo_root, worktree, journal_lines=lines)

    assert launches == []
    assert waits == [(88003, 800.0, started)]


# --------------------------------------------------------------------------
# Story 85.2 AC3 / review M2, M5 — every CLI reader shares the in-flight reading
# --------------------------------------------------------------------------


class _ProcessAt:
    """A ``ProcessPort`` answering liveness and a start time for one pid (deterministic, no host probe)."""

    def __init__(self, pid: int, *, alive: bool, started: datetime | None) -> None:
        self._pid = pid
        self._alive = alive
        self._started = started

    def is_alive(self, pid: int) -> bool:
        return self._alive and pid == self._pid

    def process_start_time(self, pid: int) -> float | None:
        return self._started.timestamp() if self._started is not None and pid == self._pid else None


def _cli_run(repo_root: Path, worktree: Path, lines: tuple[str, ...]) -> Path:
    from pyforge.marshal.core.journal import JournalEntryId as _Id

    launch = build_entry(
        id=_Id("dispatch-launcher-1", 0),
        ts="2026-10-03T09:00:00.000Z",
        run_id=loop._RUN_ID,
        kind=dispatch_core.KIND_DISPATCH_LAUNCH,
        phase=Phase.INTENT,
        payload={"story_key": loop._STORY_KEY, "worktree_path": str(worktree)},
    )
    run_dir = loop._run_dir(repo_root)
    loop._seed_journal(run_dir, (prepare_for_write(launch).line, *_journaled_refusal_with_failed_commands(), *lines))
    return run_dir


def _cli_verdict(repo_root: Path, run_dir: Path, process: object):
    from pyforge.marshal.adapters.fs_local import LocalFs
    from pyforge.marshal.cli import dispatch as cli

    fs = LocalFs()
    journal = cli.gather_dispatch_journal_facts(fs, run_dir, run_dir.name)
    verdict = cli.resolve_dispatch_session_verdict(
        fs=fs,
        vcs=loop.FakeVcs(),
        process=process,
        repo_root=repo_root,
        slug=loop._SLUG,
        journal=journal,
        effective_policy=cli._compose_policy(loop._SLUG),
        run_dir=run_dir,
    )
    guard = cli._live_dispatch_story_keys(
        fs=fs,
        vcs=loop.FakeVcs(),
        process=process,
        repo_root=repo_root,
        slug=loop._SLUG,
        effective_policy=cli._compose_policy(loop._SLUG),
    )
    return journal, verdict, guard


_FIX_STARTED = datetime(2026, 10, 3, 10, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("case", "alive", "started", "live"),
    [
        ("live", True, _FIX_STARTED + timedelta(seconds=1), True),
        ("dead", False, _FIX_STARTED + timedelta(seconds=1), True),
        ("reused", True, _FIX_STARTED - timedelta(hours=6), True),
    ],
)
def test_an_open_fix_turn_reads_live_to_every_reader_until_a_supervisor_settles_it(
    tmp_path: Path, case: str, alive: bool, started: datetime, live: bool
) -> None:
    """Review M2 + Story 85.3: an open fix-turn INTENT reads LIVE to `dispatch status` and the in-flight guard
    while its session runs, and after it exited (or its pid was reused) -- only a supervisor settles the turn, so
    resume re-spawns one and no second dispatch takes the story meanwhile."""
    from pyforge.marshal.core.dispatch_completion import DispatchSessionVerdict

    repo_root = loop._repo(tmp_path)
    worktree = loop._worktree(repo_root)
    run_dir = _cli_run(repo_root, worktree, _fix_intent_lines(77123, started_at=_FIX_STARTED))

    journal, verdict, guard = _cli_verdict(repo_root, run_dir, _ProcessAt(77123, alive=alive, started=started))

    assert (journal.verify_fix_session_pid, journal.verify_fix_started_at) == (77123, _FIX_STARTED)
    assert (verdict is DispatchSessionVerdict.LIVE) is live, case
    assert bool(guard) is live, case


def test_a_closed_fix_turn_is_no_longer_in_flight(tmp_path: Path) -> None:
    from pyforge.marshal.core.dispatch_completion import DispatchSessionVerdict

    repo_root = loop._repo(tmp_path)
    worktree = loop._worktree(repo_root)
    outcome = build_entry(
        id=JournalEntryId("dispatch-supervisor-1", 12),
        ts=_ts(_FIX_STARTED + timedelta(minutes=1)),
        run_id=loop._RUN_ID,
        kind=dispatch_core.KIND_DISPATCH_VERIFY_FIX,
        phase=Phase.OUTCOME,
        intent_id=JournalEntryId("dispatch-supervisor-1", 10),
        payload={"ok": False, "session_pid": 77123, "session_returncode": 1, "elapsed_s": 60.0},
    )
    lines = (*_fix_intent_lines(77123, started_at=_FIX_STARTED), prepare_for_write(outcome).line)
    run_dir = _cli_run(repo_root, worktree, lines)
    process = _ProcessAt(77123, alive=True, started=_FIX_STARTED)

    journal, verdict, _guard = _cli_verdict(repo_root, run_dir, process)

    assert (journal.verify_fix_session_pid, journal.verify_fix_started_at) == (None, None)
    assert verdict is not DispatchSessionVerdict.LIVE


def test_journal_facts_read_the_latest_verification_outcome(tmp_path: Path) -> None:
    """Review M5: a fix turn's green re-verify follows the refusal it fixed -- the facts read the latest
    OUTCOME, with no gate left over from the earlier refusal."""
    from pyforge.marshal.adapters.fs_local import LocalFs
    from pyforge.marshal.cli import dispatch as cli

    repo_root = loop._repo(tmp_path)
    run_dir = loop._run_dir(repo_root)
    refused = _journaled_refusal_with_failed_commands()
    verified = loop._outcome_pair(
        kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
        payload={"verdict": "verified", "ok": True, "scope_violation_advisories": []},
        counter=5,
    )
    loop._seed_journal(run_dir, (loop._launch_line(), *refused, *verified))

    facts = cli.gather_dispatch_journal_facts(LocalFs(), run_dir, run_dir.name)

    assert facts.verification_verdict == "verified"
    assert facts.verification_failed_gate is None
    assert facts.verification_failed_message is None


def test_without_sidecar_resolver_the_long_tail_fix_turn_never_launches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = loop._repo(tmp_path)
    _seed_flag(repo_root, on=True)
    worktree = loop._worktree(repo_root)
    loop._seed_spec(repo_root, worktree, primary=loop._READY_SPEC_TEXT)
    monkeypatch.setattr(
        supervisor_main, "evaluate_dispatch_verification", lambda **_k: _refused_with_output(_LONG_TAIL)
    )
    calls = _spy_fix_turn(monkeypatch)

    monkeypatch.setattr(
        supervisor_main,
        "resolve_verify_failed_commands_from_payload",
        lambda *_a, **_k: (),
    )
    fs = loop.FakeFs()

    _finalize(fs, repo_root, worktree)

    assert calls == []


# --------------------------------------------------------------------------
# Story 85.3 landing review — the session a fix turn resumes, the publisher heartbeat, redaction at the journal,
# resume after a dead supervisor, `marshal status`, and the tick loop's start-time check
# --------------------------------------------------------------------------


def _launch_outcome(*, profile: str = "claude", session_id: str | None = "sid-85-3") -> str:
    payload: dict[str, object] = {"ok": True, "session_pid": loop._SESSION_PID, "harness_profile": profile}
    if session_id is not None:
        payload["harness_session_id"] = session_id
    return loop._line(
        kind=dispatch_core.KIND_DISPATCH_LAUNCH,
        phase=Phase.OUTCOME,
        payload=payload,
        counter=1,
        intent_id=JournalEntryId("dispatch-launcher-1", 0),
    )


class _ResumableSpec:
    resume_argv = ("--resume", "{session_id}", "{prompt_stdin}")


class _Resolved:
    def __init__(self, profile: str) -> None:
        self.profile = profile
        self.spec = _ResumableSpec()
        self.binary_path = f"/bin/{profile}"


def _record_fix_launches(monkeypatch: pytest.MonkeyPatch, vcs: _FixTurnVcs, *, resolved: str) -> list[dict]:
    from pyforge.marshal.dispatch_verify import ProcessWaitResult

    launches: list[dict] = []

    def _launch(*_a: object, **kwargs: object) -> _Launch:
        launches.append(kwargs)
        vcs.dirty = True
        return _Launch(88001)

    monkeypatch.setattr(supervisor_main.BmadBuildHarness, "binary_present", lambda *_a, **_k: _Resolved(resolved))
    monkeypatch.setattr(supervisor_main.BmadBuildHarness, "dispatch_verify_fix", _launch)
    monkeypatch.setattr(supervisor_main, "wait_for_process", lambda *_a, **_k: ProcessWaitResult(True, 0))
    return launches


@pytest.mark.parametrize(
    ("resolved", "session_id", "mode", "passed_id"),
    [
        ("claude", "sid-85-3", "resume", "sid-85-3"),
        ("cursor", "sid-85-3", "fix_only", "sid-85-3"),
        ("claude", None, "fix_only", ""),
    ],
    ids=["same-profile-resumes", "other-profile-fix-only", "no-recorded-id-fix-only"],
)
def test_a_fix_turn_resumes_the_recorded_session_only_with_the_launch_profiles_own_harness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, resolved: str, session_id: str | None, mode: str, passed_id: str
) -> None:
    """AC6 / review M2 (mutants M13, M18): the launch journaled a session id under `claude`; the fix turn resumes
    it only when the resolved harness is that same profile, and is fix-only otherwise."""
    repo_root, worktree = _fix_ready_repo(tmp_path)
    events: list[tuple] = []
    vcs = _FixTurnVcs(events)
    launches = _record_fix_launches(monkeypatch, vcs, resolved=resolved)
    _scripted_verification(monkeypatch, events, _refused_with_output(_SHORT_TAIL), loop._clean_envelope())
    fs = loop.FakeFs()

    _finalize_with(
        fs,
        vcs,
        repo_root,
        worktree,
        process=loop.FakeProcess(),
        journal_lines=(_launch_outcome(session_id=session_id),),
    )

    assert len(launches) == 1
    assert launches[0]["launch_mode"] == mode
    assert launches[0]["harness_session_id"] == passed_id
    intent = next(entry for entry in _verify_fix_entries(fs) if entry["phase"] == "intent")
    assert intent["payload"]["launch_mode"] == mode


def _publisher_events(events: list[tuple]):
    return lambda: events.append(("publish",))


def test_the_publisher_heartbeat_runs_during_a_new_fix_turns_wait(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC5 / review M2 (mutant M14): the run publisher's heartbeat is called while the fix session is waited on."""
    from pyforge.marshal.dispatch_verify import ProcessWaitResult

    repo_root, worktree = _fix_ready_repo(tmp_path)
    events: list[tuple] = []
    vcs = _FixTurnVcs(events)
    _fake_fix_session(monkeypatch, vcs)
    _scripted_verification(monkeypatch, events, _refused_with_output(_SHORT_TAIL), loop._clean_envelope())

    def _wait(*_a: object, on_poll=None, **_k: object) -> ProcessWaitResult:
        events.append(("wait-start",))
        on_poll()
        events.append(("wait-end",))
        return ProcessWaitResult(exited=True, returncode=0)

    monkeypatch.setattr(supervisor_main, "wait_for_process", _wait)
    fs = loop.FakeFs()

    _finalize_with(
        fs,
        vcs,
        repo_root,
        worktree,
        process=loop.FakeProcess(),
        journal_lines=(),
        publish_heartbeat=_publisher_events(events),
    )

    start, end = events.index(("wait-start",)), events.index(("wait-end",))
    assert ("publish",) in events[start:end]


def test_the_publisher_heartbeat_runs_while_a_restarted_supervisor_settles_an_in_flight_turn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC5 / review M2 (mutant M19): finalize hands the heartbeat to the turn it settles after a restart."""
    from pyforge.marshal.dispatch_verify import ProcessWaitResult

    repo_root, worktree = _fix_ready_repo(tmp_path)
    events: list[tuple] = []
    vcs = _FixTurnVcs(events)
    _scripted_verification(monkeypatch, events, loop._clean_envelope())

    def _wait(*_a: object, on_poll=None, **_k: object) -> ProcessWaitResult:
        events.append(("wait-start",))
        on_poll()
        events.append(("wait-end",))
        return ProcessWaitResult(exited=True, returncode=None)

    monkeypatch.setattr(supervisor_main, "wait_for_process", _wait)
    fs = loop.FakeFs()

    _finalize_with(
        fs,
        vcs,
        repo_root,
        worktree,
        process=loop.FakeProcess(),
        journal_lines=(*_journaled_refusal_with_failed_commands(), *_fix_intent_lines(77123, started_at=_now())),
        publish_heartbeat=_publisher_events(events),
    )

    start, end = events.index(("wait-start",)), events.index(("wait-end",))
    assert ("publish",) in events[start:end]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def test_the_fix_turn_publisher_heartbeat_is_throttled_and_never_overlaps(monkeypatch: pytest.MonkeyPatch) -> None:
    """Review LOW: one publisher call per interval at most, made under one lock."""
    clock = {"now": 100.0}
    monkeypatch.setattr(supervisor_main.time, "monotonic", lambda: clock["now"])
    calls: list[float] = []
    beat = supervisor_main._FixTurnPublisherHeartbeat(lambda: calls.append(clock["now"]))

    for step in (0.0, 1.0, 29.0, 30.5, 31.0, 61.0):
        clock["now"] = 100.0 + step
        beat()

    assert calls == [100.0, 130.5, 161.0]
    assert supervisor_main._FIX_TURN_PUBLISH_INTERVAL_S == 30.0
    assert beat._lock.acquire(blocking=False)
    beat._lock.release()


def test_the_reverification_heartbeats_from_a_progress_thread_while_it_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC5 / review M2 (mutant M15): a long re-verification calls ``on_progress`` while it runs -- asserted on the
    calls themselves -- and the thread is done before the verification returns."""
    import threading

    repo_root = loop._repo(tmp_path)
    worktree = loop._worktree(repo_root)
    loop._seed_spec(repo_root, worktree, primary=loop._READY_SPEC_TEXT)
    monkeypatch.setattr(supervisor_main, "_FIX_TURN_PUBLISH_INTERVAL_S", 0.01)
    beats: list[str] = []

    def _slow_verification(**_k: object):
        deadline = time.monotonic() + 5.0
        while len(beats) < 3 and time.monotonic() < deadline:
            time.sleep(0.01)
        return loop._clean_envelope()

    monkeypatch.setattr(supervisor_main, "evaluate_dispatch_verification", _slow_verification)
    before = threading.active_count()

    supervisor_main._run_and_journal_verification(
        fs=loop.FakeFs(),
        vcs=loop.FakeVcs(),
        process=loop.FakeProcess(),
        run_dir=loop._run_dir(repo_root),
        run_id=loop._RUN_ID,
        writer_id="dispatch-supervisor-1",
        counter=0,
        repo_root=repo_root,
        slug=loop._SLUG,
        story_key=loop._STORY_KEY,
        worktree=worktree,
        on_progress=lambda: beats.append("beat"),
    )

    assert len(beats) >= 3
    assert threading.active_count() == before
    settled = len(beats)
    time.sleep(0.05)
    assert len(beats) == settled, "the progress thread outlived the verification"


def test_the_journaled_output_tail_is_redacted_before_it_is_cut(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC1 / review M2 (mutant M02): the verification OUTCOME's ``output_tail`` -- cut at the policy's byte bound
    inside a URL credential -- carries no fragment of it."""
    from pyforge.marshal.core.dispatch_verify_fix import tail_bytes
    from pyforge.marshal.core.policy import DEFAULT_POLICY

    bound = int(DEFAULT_POLICY["dispatch"]["verify_fix_output_tail_bytes"])
    after_cut = "persecretpw@db/x\n"
    raw = "x" * 300 + " postgres://admin:supersecretpw@db/x\n" + "y" * (bound - len(after_cut))
    assert tail_bytes(raw, max_bytes=bound).startswith("persecretpw"), "the cut must fall inside the credential"
    repo_root = loop._repo(tmp_path)
    _seed_flag(repo_root, on=True)
    worktree = loop._worktree(repo_root)
    monkeypatch.setattr(supervisor_main, "evaluate_dispatch_verification", lambda **_k: _refused_with_output(raw))
    fs = loop.FakeFs()

    loop._verify(fs, repo_root, worktree)

    written = [line for _path, line, _fsync in fs.appended] + [str(text) for text in fs.files.values()]
    assert any("output_tail" in text for text in written)
    assert not any("secretpw" in text for text in written)


class _ResumeVcs(loop.FakeVcs):
    def __init__(self, repo_root: Path, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._repo_root = repo_root

    def repo_common_root(self, _cwd: Path) -> Path:
        return self._repo_root


class _AllDead:
    """No pid is alive -- the story session, its supervisor and the fix session all exited."""

    def __init__(self) -> None:
        self.spawned: list[list[str]] = []

    def is_alive(self, _pid: int) -> bool:
        return False

    def process_start_time(self, _pid: int) -> float | None:
        return None

    def spawn_detached(self, argv, *, cwd: Path, log_path: Path) -> int:
        self.spawned.append(list(argv))
        return 9001


def _dead_supervisor_run(repo_root: Path, worktree: Path) -> Path:
    from pyforge.marshal.core.journal import JournalEntryId as _Id

    launch = build_entry(
        id=_Id("dispatch-launcher-1", 0),
        ts="2026-10-03T09:00:00.000Z",
        run_id=loop._RUN_ID,
        kind=dispatch_core.KIND_DISPATCH_LAUNCH,
        phase=Phase.INTENT,
        payload={"story_key": loop._STORY_KEY, "worktree_path": str(worktree), "baseline_head_sha": loop._BASELINE},
    )
    outcome = build_entry(
        id=_Id("dispatch-launcher-1", 1),
        ts="2026-10-03T09:00:01.000Z",
        run_id=loop._RUN_ID,
        kind=dispatch_core.KIND_DISPATCH_LAUNCH,
        phase=Phase.OUTCOME,
        intent_id=launch.id,
        payload={"ok": True, "session_pid": loop._SESSION_PID, "supervisor_pid": 99},
    )
    run_dir = loop._run_dir(repo_root)
    loop._seed_journal(
        run_dir,
        (
            prepare_for_write(launch).line,
            prepare_for_write(outcome).line,
            *_fix_intent_lines(77123, started_at=_FIX_STARTED),
        ),
    )
    return run_dir


def test_resume_respawns_the_supervisor_for_a_fix_turn_whose_session_exited_unsupervised(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC3 / review M2: the fix session exited while no supervisor was alive. `dispatch resume` does not refuse
    MRS-DISP-023 -- it re-spawns the supervisor, which settles the open INTENT (commit + re-verify)."""
    import argparse

    from pyforge.marshal.adapters.fs_local import LocalFs
    from pyforge.marshal.cli import dispatch as cli
    from pyforge.marshal.core.verdict import EXIT_OK

    repo_root = loop._repo(tmp_path)
    worktree = loop._worktree(repo_root)
    _dead_supervisor_run(repo_root, worktree)
    process = _AllDead()

    code = cli.run_dispatch_resume(
        argparse.Namespace(slug=loop._SLUG, format="json"),
        fs=LocalFs(),
        vcs=_ResumeVcs(repo_root),
        process=process,
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == EXIT_OK, payload
    assert not [f for f in payload["findings"] if f["code"] == "MRS-DISP-023"]
    assert payload["data"]["completion_verdict"] == "live"
    assert len(process.spawned) == 1
    assert "pyforge.marshal.dispatch_supervisor" in process.spawned[0]


def test_marshal_status_and_dispatch_status_agree_on_an_open_fix_turn(tmp_path: Path) -> None:
    """Review M3: `marshal status` resolves the run without a run dir; it reads the open INTENT LIVE all the same."""
    from pyforge.marshal.adapters.fs_local import LocalFs
    from pyforge.marshal.cli import status as status_cli
    from pyforge.marshal.core import status as status_core
    from pyforge.marshal.core.dispatch_completion import DispatchSessionVerdict

    class _Clock:
        def now(self) -> datetime:
            return _FIX_STARTED + timedelta(minutes=5)

    repo_root = loop._repo(tmp_path)
    worktree = loop._worktree(repo_root)
    run_dir = _cli_run(repo_root, worktree, _fix_intent_lines(77123, started_at=_FIX_STARTED))
    process = _ProcessAt(77123, alive=False, started=None)

    _journal, verdict, guard = _cli_verdict(repo_root, run_dir, process)
    facts = status_cli._merge_dispatch_overlay(
        fs=LocalFs(),
        process=process,
        clock=_Clock(),
        vcs=loop.FakeVcs(),
        repo_root=repo_root,
        slug=loop._SLUG,
        facts=status_core.FleetHomeFacts(slug=loop._SLUG, branch=f"loop/{loop._SLUG}", has_run=False),
    )

    assert verdict is DispatchSessionVerdict.LIVE
    assert facts.dispatch_completion_verdict == DispatchSessionVerdict.LIVE.value
    assert guard == (loop._STORY_KEY,)


class _ReusedSessionPid(loop.FakeProcess):
    """The story session's pid is alive -- but its process started hours before the launch: a reused pid."""

    def __init__(self) -> None:
        super().__init__(alive=True)

    def process_start_time(self, _pid: int) -> float | None:
        return datetime(2026, 9, 20, 4, 0, tzinfo=timezone.utc).timestamp()


def test_the_tick_loop_reads_a_reused_session_pid_as_dead(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AC4 / review M2 (mutant M11): a reused pid is not the session -- the loop finalizes and lands instead of
    checkpointing a tree it believes is still being edited."""
    monkeypatch.setattr(supervisor_main, "time", loop._FakeClock(mono_step=float(supervisor_main._TICK_SECONDS)))
    repo_root = loop._repo(tmp_path)
    _seed_flag(repo_root, on=False)
    run_dir = loop._run_dir(repo_root)
    worktree = loop._worktree(repo_root)
    loop._seed_journal(run_dir, (loop._launch_line(),))
    (run_dir / "session.log").write_text("implementation done\n", encoding="utf-8")
    loop._seed_spec(repo_root, worktree, primary=loop._READY_SPEC_TEXT)
    loop._patch_verification(monkeypatch, loop._clean_envelope)
    land_calls = loop._patch_landing(monkeypatch)
    branch = dispatch_core.dispatch_worktree_branch(loop._SLUG, loop._STORY_KEY)
    vcs = loop.FakeVcs(branches=frozenset({branch}), head_sha=loop._MOVED, dirty=True)

    code = loop._run(repo_root, fs=loop.FakeFs(), vcs=vcs, process=_ReusedSessionPid(), publisher=loop.FakePublisher())

    assert code == 0
    assert len(land_calls) == 1
    assert not any("auto-checkpoint" in message for _root, _paths, message in vcs.commits)
