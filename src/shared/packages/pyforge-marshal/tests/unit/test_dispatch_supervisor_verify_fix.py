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
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import test_dispatch_supervisor_main_loop as loop
from pyforge.testing_kit.flags import flagd_tree

from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core.dispatch_verify_fix import FIX_TURN_START_FAILED_CODE, VERIFY_FIX_LOOP_FLAG_KEY
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


def test_fix_turn_green_reverify_sets_finalize_verified(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from pyforge.marshal.dispatch_verify import ProcessWaitResult

    repo_root = loop._repo(tmp_path)
    _seed_flag(repo_root, on=True)
    worktree = loop._worktree(repo_root)
    loop._seed_spec(repo_root, worktree, primary=loop._READY_SPEC_TEXT)
    branch = dispatch_core.dispatch_worktree_branch(loop._SLUG, loop._STORY_KEY)
    vcs = loop.FakeVcs(dirty=True, changed_vs_head=("fix.py",), branches=frozenset({branch}), head_sha=loop._MOVED)
    verify_pass = {"n": 0}

    def _evaluate(**_kwargs):
        verify_pass["n"] += 1
        if verify_pass["n"] == 1:
            return _refused_with_output(_SHORT_TAIL)
        return loop._clean_envelope()

    monkeypatch.setattr(supervisor_main, "evaluate_dispatch_verification", _evaluate)

    class _Launch:
        pid = 88001

    monkeypatch.setattr(
        supervisor_main.BmadBuildHarness,
        "binary_present",
        lambda *_a, **_k: _NoProfile(),
    )
    monkeypatch.setattr(
        supervisor_main.BmadBuildHarness,
        "dispatch_verify_fix",
        lambda *_a, **_k: _Launch(),
    )
    monkeypatch.setattr(
        supervisor_main,
        "wait_for_process",
        lambda *_a, **_k: ProcessWaitResult(exited=True, returncode=0),
    )
    fs = loop.FakeFs()

    _counter, ok = _finalize(fs, repo_root, worktree, vcs=vcs)

    assert ok is True
    finalize_outcomes = [
        json.loads(line)["payload"]
        for _path, line, _fsync in fs.appended
        if json.loads(line).get("kind") == dispatch_core.KIND_DISPATCH_FINALIZE
        and json.loads(line).get("phase") == "outcome"
    ]
    assert finalize_outcomes[-1]["verified"] is True
    assert vcs.commits, "fix-turn WIP must be committed before re-verify"


def test_reverify_still_refused_emits_mrs_disp_060(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from pyforge.marshal.core.dispatch_verify_fix import FIX_TURN_REVERIFY_REFUSED_CODE
    from pyforge.marshal.dispatch_verify import ProcessWaitResult

    repo_root = loop._repo(tmp_path)
    _seed_flag(repo_root, on=True)
    worktree = loop._worktree(repo_root)
    loop._seed_spec(repo_root, worktree, primary=loop._READY_SPEC_TEXT)
    branch = dispatch_core.dispatch_worktree_branch(loop._SLUG, loop._STORY_KEY)
    vcs = loop.FakeVcs(dirty=True, changed_vs_head=("fix.py",), branches=frozenset({branch}), head_sha=loop._MOVED)
    monkeypatch.setattr(
        supervisor_main, "evaluate_dispatch_verification", lambda **_k: _refused_with_output(_SHORT_TAIL)
    )
    monkeypatch.setattr(
        supervisor_main.BmadBuildHarness,
        "binary_present",
        lambda *_a, **_k: _NoProfile(),
    )
    monkeypatch.setattr(
        supervisor_main.BmadBuildHarness,
        "dispatch_verify_fix",
        lambda *_a, **_k: type("L", (), {"pid": 88002})(),
    )
    monkeypatch.setattr(
        supervisor_main,
        "wait_for_process",
        lambda *_a, **_k: ProcessWaitResult(exited=True, returncode=0),
    )
    fs = loop.FakeFs()

    _finalize(fs, repo_root, worktree, vcs=vcs)

    observations = [
        entry
        for entry in _verify_fix_entries(fs)
        if entry.get("phase") == "observation"
        and entry.get("payload", {}).get("code") == FIX_TURN_REVERIFY_REFUSED_CODE
    ]
    assert observations
    assert observations[-1]["payload"]["failed_command"] == _COMMAND


def test_supervisor_restart_resumes_a_pending_fix_turn_without_launching_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pyforge.marshal.core.journal import JournalEntryId, Phase, build_entry, prepare_for_write
    from pyforge.marshal.dispatch_verify import ProcessWaitResult

    repo_root = loop._repo(tmp_path)
    _seed_flag(repo_root, on=True)
    worktree = loop._worktree(repo_root)
    loop._seed_spec(repo_root, worktree, primary=loop._READY_SPEC_TEXT)
    loop._run_dir(repo_root)
    ver_intent, ver_outcome = _journaled_refusal_with_failed_commands()
    fix_intent = build_entry(
        id=JournalEntryId("dispatch-supervisor-1", 10),
        ts="2026-10-03T10:00:00.000Z",
        run_id=loop._RUN_ID,
        kind=dispatch_core.KIND_DISPATCH_VERIFY_FIX,
        phase=Phase.INTENT,
        payload={
            "launch_mode": "fix_only",
            "prompt_bytes": 12,
            "failed_command_count": 1,
            "wall_clock_budget_s": 900.0,
            "budget_started_monotonic": 1000.0,
        },
    )
    fix_obs = build_entry(
        id=JournalEntryId("dispatch-supervisor-1", 11),
        ts="2026-10-03T10:00:01.000Z",
        run_id=loop._RUN_ID,
        kind=dispatch_core.KIND_DISPATCH_VERIFY_FIX,
        phase=Phase.OBSERVATION,
        payload={"session_pid": 88003, "ok": True, "fix_intent_id": str(fix_intent.id)},
    )
    journal_lines = (
        ver_intent,
        ver_outcome,
        prepare_for_write(fix_intent).line,
        prepare_for_write(fix_obs).line,
    )
    launch_calls: list[str] = []
    wait_calls: list[float] = []

    def _launch(*_a, **_k):
        launch_calls.append("dispatch_verify_fix")
        raise AssertionError("must not launch a second fix turn")

    monkeypatch.setattr(supervisor_main.BmadBuildHarness, "dispatch_verify_fix", _launch)
    monkeypatch.setattr(
        supervisor_main,
        "wait_for_process",
        lambda _p, _pid, *, timeout_s, on_poll=None: (
            wait_calls.append(timeout_s),
            ProcessWaitResult(exited=True, returncode=1),
        )[1],
    )
    monkeypatch.setattr(supervisor_main.time, "monotonic", lambda: 1100.0)
    fs = loop.FakeFs()

    _finalize(fs, repo_root, worktree, journal_lines=journal_lines)

    assert launch_calls == []
    assert wait_calls and wait_calls[0] <= 900.0


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
