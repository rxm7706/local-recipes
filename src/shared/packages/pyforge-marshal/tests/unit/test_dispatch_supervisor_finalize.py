"""Unit tests for Story 28.24 — supervisor finalizes when harness cannot run shell."""

from __future__ import annotations

from pathlib import Path

from pyforge.marshal.cli.dispatch import (
    _redispatch_blocked_pending_supervisor_finalize,
    gather_fleet_finalize_escalations,
)
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core import status
from pyforge.marshal.core.dispatch_completion import DispatchGitFacts
from pyforge.marshal.core.dispatch_supervisor_finalize import (
    FinalizeTrigger,
    classify_finalize_trigger,
    finalize_attempt_failed,
    finalize_attempt_journaled,
    session_harness_reported_done_or_shell_unavailable,
    supervisor_should_finalize_harness_work,
)
from pyforge.marshal.core.dispatch_verification import DispatchVerificationVerdict
from pyforge.marshal.core.journal import JournalEntryId, Phase, build_entry, fold, prepare_for_write


def _git_facts(**kwargs: object) -> DispatchGitFacts:
    defaults = {
        "baseline_head_sha": "aaa111",
        "current_head_sha": "bbb222",
        "changed_paths": ("src/x.py",),
        "branch_merged": False,
        "story_merged_on_main": False,
    }
    defaults.update(kwargs)
    return DispatchGitFacts(**defaults)  # type: ignore[arg-type]


def test_session_detects_shell_unavailable() -> None:
    log = "Cursor session reported shell unavailable; pixi rejected"
    assert session_harness_reported_done_or_shell_unavailable(log)
    assert classify_finalize_trigger(log) is FinalizeTrigger.SHELL_UNAVAILABLE


def test_session_detects_harness_done() -> None:
    log = "bmad-build-auto: implementation done for story 28.24"
    assert session_harness_reported_done_or_shell_unavailable(log)
    assert classify_finalize_trigger(log) is FinalizeTrigger.HARNESS_DONE


def test_supervisor_should_finalize_dead_session_with_progress() -> None:
    assert supervisor_should_finalize_harness_work(
        session_alive=False,
        git=_git_facts(),
        session_log="shell unavailable",
        verification_verdict=None,
        landing_complete=False,
    )


def test_supervisor_should_not_finalize_when_verified() -> None:
    assert not supervisor_should_finalize_harness_work(
        session_alive=False,
        git=_git_facts(),
        session_log=None,
        verification_verdict=DispatchVerificationVerdict.VERIFIED.value,
        landing_complete=False,
    )


def test_finalize_attempt_journaled_detects_outcome() -> None:
    line = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 1),
            ts="2026-09-01T00:00:00.000Z",
            run_id="run-1",
            kind=dispatch_core.KIND_DISPATCH_FINALIZE,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 0),
            payload={"ok": True},
        )
    ).line
    folded = fold([line])
    assert finalize_attempt_journaled(folded, "run-1")
    assert not finalize_attempt_journaled(folded, "run-2")


def test_finalize_attempt_failed_reads_outcome() -> None:
    line = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 1),
            ts="2026-09-01T00:00:00.000Z",
            run_id="run-fail",
            kind=dispatch_core.KIND_DISPATCH_FINALIZE,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 0),
            payload={"ok": False, "worktree_path": "/tmp/wt"},
        )
    ).line
    folded = fold([line])
    assert finalize_attempt_failed(folded, "run-fail")


class FakeFs:
    def __init__(self, files: dict[Path, str] | None = None) -> None:
        self.files = dict(files or {})

    def read_text(self, path: Path) -> str | None:
        return self.files.get(path)


def _write_launch_journal(
    run_dir: Path,
    *,
    story_key: str = "28.24",
    worktree: Path,
    run_id: str = "run-28-24",
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    intent = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 0),
            ts="2026-09-01T00:00:00.000Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.INTENT,
            payload={
                "story_key": story_key,
                "worktree_path": str(worktree),
                "baseline_head_sha": "aaa111",
            },
        )
    ).line
    (run_dir / "journal.jsonl").write_text(intent + "\n", encoding="utf-8")


def test_redispatch_blocked_until_finalize_attempted(tmp_path: Path) -> None:
    slug = "pyforge-marshal"
    wt = tmp_path / "wt"
    wt.mkdir()
    run_dir = tmp_path / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs/run-28-24"
    _write_launch_journal(run_dir, worktree=wt)
    fs = FakeFs(
        {
            run_dir / "journal.jsonl": (run_dir / "journal.jsonl").read_text(encoding="utf-8"),
        }
    )
    block = _redispatch_blocked_pending_supervisor_finalize(
        fs=fs,
        repo_root=tmp_path,
        slug=slug,
        story_key="28.24",
        worktree=wt,
    )
    assert block is not None
    assert "finalize" in block


def test_redispatch_allowed_after_finalize_journaled(tmp_path: Path) -> None:
    slug = "pyforge-marshal"
    wt = tmp_path / "wt"
    wt.mkdir()
    run_dir = tmp_path / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs/run-done"
    intent = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 0),
            ts="2026-09-01T00:00:00.000Z",
            run_id="run-done",
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.INTENT,
            payload={
                "story_key": "28.24",
                "worktree_path": str(wt),
                "baseline_head_sha": "aaa111",
            },
        )
    ).line
    outcome = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 1),
            ts="2026-09-01T00:00:01.000Z",
            run_id="run-done",
            kind=dispatch_core.KIND_DISPATCH_FINALIZE,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 0),
            payload={"ok": True},
        )
    ).line
    run_dir.mkdir(parents=True, exist_ok=True)
    journal_text = intent + "\n" + outcome + "\n"
    (run_dir / "journal.jsonl").write_text(journal_text, encoding="utf-8")
    fs = FakeFs({run_dir / "journal.jsonl": journal_text})
    block = _redispatch_blocked_pending_supervisor_finalize(
        fs=fs,
        repo_root=tmp_path,
        slug=slug,
        story_key="28.24",
        worktree=wt,
    )
    assert block is None


def test_gather_fleet_finalize_escalations(tmp_path: Path) -> None:
    wt = tmp_path / "wt"
    wt.mkdir()
    run_dir = tmp_path / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs/run-fail"
    intent = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 0),
            ts="2026-09-01T00:00:00.000Z",
            run_id="run-fail",
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.INTENT,
            payload={
                "story_key": "28.24",
                "worktree_path": str(wt),
                "baseline_head_sha": "aaa111",
            },
        )
    ).line
    outcome = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 1),
            ts="2026-09-01T00:00:01.000Z",
            run_id="run-fail",
            kind=dispatch_core.KIND_DISPATCH_FINALIZE,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 0),
            payload={"ok": False, "worktree_path": str(wt), "failed_step": "commit"},
        )
    ).line
    run_dir.mkdir(parents=True, exist_ok=True)
    journal_text = intent + "\n" + outcome + "\n"
    (run_dir / "journal.jsonl").write_text(journal_text, encoding="utf-8")
    (tmp_path / "_bmad-output/projects/pyforge-marshal").mkdir(parents=True, exist_ok=True)
    fs = FakeFs({run_dir / "journal.jsonl": journal_text})
    escalations = gather_fleet_finalize_escalations(fs=fs, repo_root=tmp_path)
    assert "pyforge-marshal" in escalations
    assert escalations["pyforge-marshal"].story == "28.24"
    assert escalations["pyforge-marshal"].worktree_path == str(wt)


def test_gather_fleet_finalize_escalations_superseded_by_success(tmp_path: Path) -> None:
    """Story 28.25: a newer, successfully-finalized run clears an older failure."""
    slug = "pyforge-marshal"
    runs_parent = tmp_path / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs"
    wt_old = tmp_path / "wt-old"
    wt_old.mkdir()
    old_run = runs_parent / "run-1-fail"
    old_intent = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 0),
            ts="2026-09-01T00:00:00.000Z",
            run_id="run-1-fail",
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.INTENT,
            payload={
                "story_key": "28.24",
                "worktree_path": str(wt_old),
                "baseline_head_sha": "aaa111",
            },
        )
    ).line
    old_outcome = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 1),
            ts="2026-09-01T00:00:01.000Z",
            run_id="run-1-fail",
            kind=dispatch_core.KIND_DISPATCH_FINALIZE,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 0),
            payload={"ok": False, "worktree_path": str(wt_old), "failed_step": "commit"},
        )
    ).line
    old_run.mkdir(parents=True, exist_ok=True)
    old_text = old_intent + "\n" + old_outcome + "\n"
    (old_run / "journal.jsonl").write_text(old_text, encoding="utf-8")

    wt_new = tmp_path / "wt-new"
    wt_new.mkdir()
    new_run = runs_parent / "run-2-success"
    new_intent = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 0),
            ts="2026-09-02T00:00:00.000Z",
            run_id="run-2-success",
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.INTENT,
            payload={
                "story_key": "28.10",
                "worktree_path": str(wt_new),
                "baseline_head_sha": "bbb222",
            },
        )
    ).line
    new_outcome = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 1),
            ts="2026-09-02T00:00:01.000Z",
            run_id="run-2-success",
            kind=dispatch_core.KIND_DISPATCH_FINALIZE,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 0),
            payload={"ok": True},
        )
    ).line
    new_run.mkdir(parents=True, exist_ok=True)
    new_text = new_intent + "\n" + new_outcome + "\n"
    (new_run / "journal.jsonl").write_text(new_text, encoding="utf-8")

    (tmp_path / "_bmad-output/projects/pyforge-marshal").mkdir(parents=True, exist_ok=True)
    fs = FakeFs(
        {
            old_run / "journal.jsonl": old_text,
            new_run / "journal.jsonl": new_text,
        }
    )
    escalations = gather_fleet_finalize_escalations(fs=fs, repo_root=tmp_path)
    assert slug not in escalations


def test_gather_fleet_finalize_escalations_worktree_already_gone(tmp_path: Path) -> None:
    """Story 28.25: a failed finalize whose worktree no longer exists is resolved."""
    slug = "pyforge-marshal"
    wt = tmp_path / "wt-removed"
    run_dir = tmp_path / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs/run-fail"
    intent = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 0),
            ts="2026-09-01T00:00:00.000Z",
            run_id="run-fail",
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.INTENT,
            payload={
                "story_key": "28.24",
                "worktree_path": str(wt),
                "baseline_head_sha": "aaa111",
            },
        )
    ).line
    outcome = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 1),
            ts="2026-09-01T00:00:01.000Z",
            run_id="run-fail",
            kind=dispatch_core.KIND_DISPATCH_FINALIZE,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 0),
            payload={"ok": False, "worktree_path": str(wt), "failed_step": "commit"},
        )
    ).line
    run_dir.mkdir(parents=True, exist_ok=True)
    journal_text = intent + "\n" + outcome + "\n"
    (run_dir / "journal.jsonl").write_text(journal_text, encoding="utf-8")
    (tmp_path / "_bmad-output/projects/pyforge-marshal").mkdir(parents=True, exist_ok=True)
    fs = FakeFs({run_dir / "journal.jsonl": journal_text})

    assert not wt.exists()
    escalations = gather_fleet_finalize_escalations(fs=fs, repo_root=tmp_path)
    assert slug not in escalations


def test_finalize_escalation_surfaces_awaiting_operator() -> None:
    facts = status.FleetHomeFacts(
        slug="pyforge-marshal",
        branch="loop/pyforge-marshal",
        has_run=False,
        finalize_escalation_story="28.24",
        finalize_escalation_worktree="/tmp/dispatch-wt",
    )
    row, finding = status.build_fleet_row(facts)
    assert finding is None
    assert row["state"] == "awaiting-operator"
    assert row["current_story"] == "28.24"
    assert "/tmp/dispatch-wt" in row["awaiting_operator_remedy"]
