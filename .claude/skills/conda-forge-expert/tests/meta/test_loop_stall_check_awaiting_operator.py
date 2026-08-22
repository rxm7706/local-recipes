"""Meta-test: bmad-loop 0.11 `awaiting-operator` parked runs in loop_stall_check.py.

Marshal Story 25.5 (spec-bmad-611-era-alignment CAP-5, absorbing DW-BL011-1):
bmad-loop 0.11 parks a story at `awaiting-operator` when its remaining
acceptance criteria are external human-only actions (completed via `bmad-loop
confirm`). Such a run is deliberately still — before this fix the watchdog's
liveness test exempted only finished/stopped/paused, so a parked run read as a
15-minute stall and misdirected triage toward a wedged-session diagnosis.

The check now classifies a live run's tasks off the same state.json read:

  * parked-ONLY (>=1 `awaiting-operator` task, nothing non-terminal) — reported
    distinctly as `awaiting-operator (run bmad-loop confirm)` with the parked
    story keys, NOT counted stalled, exit 0;
  * parked + still-active — stays a stall (something claims to run and is
    quiet), with the parked keys named alongside, exit 1.

Fixtures are written by the INSTALLED bmad_loop writer
(`bmad_loop.journal.save_state` over a real `RunState`), never a hand-rolled
dict, so the state.json shape is exactly what a real 0.11 run leaves behind —
same harness style as test_fleet_picture_loop_home_staleness.py
(importlib-loaded script under test, real fixtures on tmp_path).
"""
import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
LOOP_STALL_CHECK = REPO_ROOT / "scripts" / "loop_stall_check.py"

AWAITING_LABEL = "awaiting-operator (run bmad-loop confirm)"


def _load_loop_stall_check():
    spec = importlib.util.spec_from_file_location(
        "loop_stall_check_under_test", LOOP_STALL_CHECK
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["loop_stall_check_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def _seed_run(loop_root: Path, slug: str, run_id: str, tasks: dict[str, str],
              *, preserve_ref: str | None = None):
    """One loop-home-shaped dir with a single run whose state.json is written
    by the installed bmad_loop writer. `tasks` maps story_key -> phase."""
    model = pytest.importorskip("bmad_loop.model")
    journal = pytest.importorskip("bmad_loop.journal")

    home = loop_root / f"pyforge-{slug}"
    (home / ".git").mkdir(parents=True)  # the scan's loop-home marker
    run_dir = home / ".bmad-loop" / "runs" / run_id

    state = model.RunState(
        run_id=run_id, project=str(home), started_at="2026-08-22T00:00:00Z"
    )
    for key, phase in tasks.items():
        task = model.StoryTask(story_key=key, epic=25, phase=model.Phase(phase))
        if phase == "awaiting-operator":
            task.operator_actions = ["publish the DNS record"]
            task.commit_sha = "cafe123"  # a park carries a commit
        if preserve_ref is not None:
            task.preserve_ref = preserve_ref
        state.tasks[key] = task
    journal.save_state(run_dir, state)
    # No logs/ and no journal.jsonl are seeded: newest_activity() therefore
    # reads 0.0 and the run counts as quiet past ANY threshold — exactly the
    # matrix's "live quiet run" precondition, with no sleep needed.
    return home, run_dir


def _run_main(mod, loop_root: Path, monkeypatch, *args: str) -> int:
    monkeypatch.setattr(mod, "LOOP_ROOT", loop_root)
    monkeypatch.setattr(sys, "argv", ["loop_stall_check.py", *args])
    return mod.main()


def test_parked_only_quiet_run_is_reported_distinctly_and_exits_zero(
    tmp_path, monkeypatch, capsys
):
    """Matrix row 'Stall-check parked': all tasks terminal, one of them
    parked -> named with the confirm remedy + parked keys, never counted
    stalled, exit 0."""
    _seed_run(
        tmp_path, "teststation", "20260822-000000-abcd",
        {"25-1-done-story": "done", "25-2-parked-story": "awaiting-operator"},
    )
    mod = _load_loop_stall_check()

    rc = _run_main(mod, tmp_path, monkeypatch)
    out = capsys.readouterr().out

    assert rc == 0, out
    assert AWAITING_LABEL in out
    assert "25-2-parked-story" in out
    assert "bmad-loop confirm" in out
    assert "[stalled]" not in out
    for mislabel in ("stalled", "dead", "unsupervised"):
        assert mislabel not in out, (mislabel, out)


def test_parked_plus_active_quiet_run_is_still_a_stall_with_parked_keys_named(
    tmp_path, monkeypatch, capsys
):
    """Matrix row 'Stall-check parked + active': something still claims to
    run and is quiet — a real stall, exit 1, with the parked keys named so
    triage knows which half is deliberate."""
    _seed_run(
        tmp_path, "teststation", "20260822-000000-abcd",
        {"25-2-parked-story": "awaiting-operator", "25-3-active-story": "dev-running"},
    )
    mod = _load_loop_stall_check()

    rc = _run_main(mod, tmp_path, monkeypatch)
    out = capsys.readouterr().out

    assert rc == 1, out
    assert "[stalled]" in out
    assert "25-2-parked-story" in out


def test_a_quiet_run_with_no_parked_tasks_still_stalls_unchanged(
    tmp_path, monkeypatch, capsys
):
    """Regression guard: the park exemption must not soften the ordinary
    stall detection the watchdog exists for."""
    _seed_run(
        tmp_path, "teststation", "20260822-000000-abcd",
        {"25-3-active-story": "dev-running"},
    )
    mod = _load_loop_stall_check()

    rc = _run_main(mod, tmp_path, monkeypatch)
    out = capsys.readouterr().out

    assert rc == 1, out
    assert "[stalled]" in out
    assert AWAITING_LABEL not in out


def test_parked_tasks_helper_mirrors_the_installed_terminal_set():
    """The helper's terminal set mirrors `bmad_loop.model.TERMINAL_PHASES`
    verbatim (marshal's tests/unit/test_bmad_loop_status_vocabulary.py pins
    the same fact from the marshal side); an UNKNOWN phase counts as active
    — the conservative direction (a stall is reported, never hidden)."""
    model = pytest.importorskip("bmad_loop.model")
    mod = _load_loop_stall_check()

    assert mod.TERMINAL_PHASES == {str(p) for p in model.TERMINAL_PHASES}
    assert mod.AWAITING_OPERATOR_LABEL == AWAITING_LABEL

    parked, active = mod.parked_tasks(
        {"tasks": {
            "a": {"phase": "awaiting-operator"},
            "b": {"phase": "done"},
            "c": {"phase": "some-future-phase"},
        }}
    )
    assert parked == ["a"]
    assert active is True

    parked, active = mod.parked_tasks(
        {"tasks": {"a": {"phase": "awaiting-operator"}, "b": {"phase": "escalated"}}}
    )
    assert parked == ["a"]
    assert active is False
