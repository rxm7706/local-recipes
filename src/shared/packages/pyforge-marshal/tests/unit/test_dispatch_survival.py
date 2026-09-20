"""Unit tests for dispatch operator survival (Story 22.6, FR-193 CAP-6)."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pyforge.marshal.cli.dispatch import (
    _ensure_dispatch_supervision,
    gather_dispatch_journal_facts,
    run_dispatch_resume,
)
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core.dispatch_completion import (
    DispatchGitFacts,
    DispatchSessionVerdict,
)
from pyforge.marshal.core.dispatch_preserve import failed_patch_path
from pyforge.marshal.core.dispatch_survival import (
    build_timing_record,
    derive_supervision_state,
    reconcile_unsupervised_verdict,
    timing_record_payload,
)
from pyforge.marshal.core.journal import JournalEntryId, Phase, build_entry, prepare_for_write
from pyforge.marshal.core.policy import EffectivePolicy
from pyforge.marshal.core.verdict import EXIT_OK


class FakeFs:
    def __init__(self) -> None:
        self.dirs: set[Path] = set()
        self.files: dict[Path, str] = {}
        self.appended: list[tuple[Path, str, bool]] = []

    def is_dir(self, path: Path) -> bool:
        return path in self.dirs

    def ensure_dir(self, path: Path) -> None:
        self.dirs.add(path)

    def create_dir_exclusive(self, path: Path) -> None:
        self.dirs.add(path)

    def append_line(self, path: Path, line: str, *, fsync: bool) -> None:
        self.appended.append((path, line, fsync))
        prev = self.files.get(path, "")
        self.files[path] = prev + line + "\n"

    def write_text_atomic(self, path: Path, content: str) -> None:
        self.files[path] = content

    def read_text(self, path: Path) -> str | None:
        return self.files.get(path)


class FakeProcess:
    def __init__(self, *, alive_pids: set[int] | None = None) -> None:
        self.alive_pids = alive_pids or set()
        self.spawn_calls: list[list[str]] = []

    def is_alive(self, pid: int) -> bool:
        return pid in self.alive_pids

    def spawn_detached(self, argv, *, cwd: Path, log_path: Path) -> int:
        self.spawn_calls.append(list(argv))
        return 9001


class FakeVcs:
    def repo_common_root(self, _cwd: Path) -> Path:
        return Path("/repo")

    def worktree_unified_patch(self, _worktree: Path, *, baseline_sha: str) -> str:
        return f"diff --git a/x b/x\n+baseline={baseline_sha}\n"


def _minimal_policy(_slug: str | None = None) -> EffectivePolicy:
    from pyforge.marshal.core.policy import compose

    effective, _ = compose(project_slug="pyforge-marshal", project={}, flags={})
    return effective


def test_timing_record_payload_carries_epic23_fields() -> None:
    record = build_timing_record(
        story_key="22-6-test",
        story_started_at="2026-08-23T12:00:00.000Z",
        story_ended_at="2026-08-23T13:00:00.000Z",
        baseline_revision="abc123",
        final_revision="def456",
    )
    payload = timing_record_payload(record)
    assert payload["baseline_revision"] == "abc123"
    assert payload["final_revision"] == "def456"
    assert payload["story_started_at"].endswith("Z")


def test_derive_supervision_state_unsupervised_live() -> None:
    journal = dispatch_core.DispatchJournalFacts(
        story_key="22-6-test",
        session_pid=42,
        model=None,
        launched_at=datetime.now(timezone.utc),
        worktree_path="/wt",
        baseline_head_sha="abc",
        supervisor_pid=99,
    )
    git = DispatchGitFacts(
        baseline_head_sha="abc",
        current_head_sha="def",
        changed_paths=("x",),
        branch_merged=False,
        story_merged_on_main=False,
    )
    state = derive_supervision_state(
        journal=journal,
        session_alive=True,
        supervisor_alive=False,
        git=git,
    )
    assert state.unsupervised_live is True
    assert state.completion_verdict == DispatchSessionVerdict.LIVE


def test_derive_supervision_state_blocked_is_terminal_not_relive() -> None:
    """Story 51.11 (CAP-258): a committed ``blocked`` verdict must not be
    re-derived from fresh git facts -- without the fix, a dead session with
    committed wip (``has_git_progress`` True) would re-derive as LIVE and
    fleet tooling would think the run is still unsupervised-live."""
    journal = dispatch_core.DispatchJournalFacts(
        story_key="51-11-test",
        session_pid=42,
        model=None,
        launched_at=datetime.now(timezone.utc),
        worktree_path="/wt",
        baseline_head_sha="abc",
        supervisor_pid=99,
        completion_verdict="blocked",
    )
    git = DispatchGitFacts(
        baseline_head_sha="abc",
        current_head_sha="def",
        changed_paths=("spec-51-11.md",),
        branch_merged=False,
        story_merged_on_main=False,
    )
    state = derive_supervision_state(
        journal=journal,
        session_alive=False,
        supervisor_alive=False,
        git=git,
    )
    assert state.completion_verdict == DispatchSessionVerdict.BLOCKED
    assert state.unsupervised_live is False


def test_reconcile_unsupervised_verdict_from_git_merge() -> None:
    git = DispatchGitFacts(
        baseline_head_sha="abc",
        current_head_sha="def",
        changed_paths=(),
        branch_merged=True,
        story_merged_on_main=False,
    )
    assert (
        reconcile_unsupervised_verdict(session_alive=False, git=git)
        == DispatchSessionVerdict.COMPLETED
    )


def test_gather_journal_reads_timing_and_preserve() -> None:
    fs = FakeFs()
    run_dir = Path("/repo/_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs/run1")
    fs.dirs.add(run_dir)
    launch = build_entry(
        id=JournalEntryId("w", 0),
        ts="2026-08-23T12:00:00.000Z",
        run_id="run1",
        kind=dispatch_core.KIND_DISPATCH_LAUNCH,
        phase=Phase.INTENT,
        payload={
            "story_key": "22-6-test",
            "worktree_path": "/wt",
            "baseline_head_sha": "abc123",
        },
    )
    launch_out = build_entry(
        id=JournalEntryId("w", 1),
        ts="2026-08-23T12:00:01.000Z",
        run_id="run1",
        kind=dispatch_core.KIND_DISPATCH_LAUNCH,
        phase=Phase.OUTCOME,
        intent_id=JournalEntryId("w", 0),
        payload={"session_pid": 42, "supervisor_pid": 99},
    )
    timing_intent = build_entry(
        id=JournalEntryId("w", 2),
        ts="2026-08-23T13:00:00.000Z",
        run_id="run1",
        kind=dispatch_core.KIND_DISPATCH_TIMING,
        phase=Phase.INTENT,
        payload={
            "story_started_at": "2026-08-23T12:00:00.000Z",
            "story_ended_at": "2026-08-23T13:00:00.000Z",
            "baseline_revision": "abc123",
            "final_revision": "def456",
        },
    )
    timing = build_entry(
        id=JournalEntryId("w", 3),
        ts="2026-08-23T13:00:00.000Z",
        run_id="run1",
        kind=dispatch_core.KIND_DISPATCH_TIMING,
        phase=Phase.OUTCOME,
        intent_id=JournalEntryId("w", 2),
        payload={
            "story_started_at": "2026-08-23T12:00:00.000Z",
            "story_ended_at": "2026-08-23T13:00:00.000Z",
            "baseline_revision": "abc123",
            "final_revision": "def456",
        },
    )
    preserve_intent = build_entry(
        id=JournalEntryId("w", 4),
        ts="2026-08-23T13:00:01.000Z",
        run_id="run1",
        kind=dispatch_core.KIND_DISPATCH_PRESERVE,
        phase=Phase.INTENT,
        payload={"preserve_ref": "failed/22-6-test/changes.patch"},
    )
    preserve = build_entry(
        id=JournalEntryId("w", 5),
        ts="2026-08-23T13:00:01.000Z",
        run_id="run1",
        kind=dispatch_core.KIND_DISPATCH_PRESERVE,
        phase=Phase.OUTCOME,
        intent_id=JournalEntryId("w", 4),
        payload={"preserve_ref": "failed/22-6-test/changes.patch"},
    )
    for entry in (launch, launch_out, timing_intent, timing, preserve_intent, preserve):
        line = prepare_for_write(entry).line
        fs.append_line(run_dir / "journal.jsonl", line, fsync=False)
    facts = gather_dispatch_journal_facts(fs, run_dir, "run1")
    assert facts.final_revision == "def456"
    assert facts.preserve_ref == "failed/22-6-test/changes.patch"


def test_gather_journal_reads_land_findings_regardless_of_ok() -> None:
    """Story 53.2 review (I1): `land_findings` (MRS-DISP-047/048) must be
    readable from a KIND_DISPATCH_LAND OUTCOME entry even when the landing
    was refused (``ok`` False) -- a refused landing is exactly the case
    this must surface, not the one it can afford to drop."""
    fs = FakeFs()
    repo = Path("/repo")
    run_dir = repo / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs/run1"
    fs.dirs.add(run_dir)
    launch = build_entry(
        id=JournalEntryId("w", 0),
        ts="2026-08-23T12:00:00.000Z",
        run_id="run1",
        kind=dispatch_core.KIND_DISPATCH_LAUNCH,
        phase=Phase.INTENT,
        payload={"story_key": "53-2-test", "worktree_path": "/wt", "model": "abc123"},
    )
    launch_out = build_entry(
        id=JournalEntryId("w", 1),
        ts="2026-08-23T12:00:01.000Z",
        run_id="run1",
        kind=dispatch_core.KIND_DISPATCH_LAUNCH,
        phase=Phase.OUTCOME,
        intent_id=JournalEntryId("w", 0),
        payload={"session_pid": 42},
    )
    land_intent = build_entry(
        id=JournalEntryId("w", 2),
        ts="2026-08-23T13:00:00.000Z",
        run_id="run1",
        kind=dispatch_core.KIND_DISPATCH_LAND,
        phase=Phase.INTENT,
        payload={"verdict": "refused"},
    )
    land_out = build_entry(
        id=JournalEntryId("w", 3),
        ts="2026-08-23T13:00:01.000Z",
        run_id="run1",
        kind=dispatch_core.KIND_DISPATCH_LAND,
        phase=Phase.OUTCOME,
        intent_id=JournalEntryId("w", 2),
        payload={
            "verdict": "refused",
            "ok": False,
            "land_findings": [
                {
                    "code": "MRS-DISP-048",
                    "severity": "error",
                    "message": "cannot resolve ref",
                }
            ],
        },
    )
    for entry in (launch, launch_out, land_intent, land_out):
        line = prepare_for_write(entry).line
        fs.append_line(run_dir / "journal.jsonl", line, fsync=False)
    facts = gather_dispatch_journal_facts(fs, run_dir, "run1")
    assert facts.landing_verdict is None
    assert facts.landing_findings == (
        {
            "code": "MRS-DISP-048",
            "severity": "error",
            "message": "cannot resolve ref",
        },
    )


def test_dispatch_resume_respawns_dead_supervisor(monkeypatch: pytest.MonkeyPatch) -> None:
    fs = FakeFs()
    repo = Path("/repo")
    run_dir = repo / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs/run1"
    fs.dirs.add(run_dir)
    launch = build_entry(
        id=JournalEntryId("w", 0),
        ts="2026-08-23T12:00:00.000Z",
        run_id="run1",
        kind=dispatch_core.KIND_DISPATCH_LAUNCH,
        phase=Phase.INTENT,
        payload={
            "story_key": "22-6-test",
            "worktree_path": str(repo / "wt"),
            "baseline_head_sha": "abc123",
        },
    )
    launch_out = build_entry(
        id=JournalEntryId("w", 1),
        ts="2026-08-23T12:00:01.000Z",
        run_id="run1",
        kind=dispatch_core.KIND_DISPATCH_LAUNCH,
        phase=Phase.OUTCOME,
        intent_id=JournalEntryId("w", 0),
        payload={"session_pid": 42, "supervisor_pid": 99},
    )
    for entry in (launch, launch_out):
        line = prepare_for_write(entry).line
        fs.append_line(run_dir / "journal.jsonl", line, fsync=False)

    class Vcs:
        def repo_common_root(self, _cwd: Path) -> Path:
            return repo

    process = FakeProcess(alive_pids={42})
    monkeypatch.setattr(
        "pyforge.marshal.cli.dispatch.latest_dispatch_run_dir",
        lambda _root, _slug: run_dir,
    )
    monkeypatch.setattr(
        "pyforge.marshal.cli.dispatch._compose_policy",
        lambda slug: _minimal_policy(slug),
    )
    monkeypatch.setattr(
        "pyforge.marshal.cli.dispatch.resolve_dispatch_session_verdict",
        lambda **_kwargs: DispatchSessionVerdict.LIVE,
    )
    code = run_dispatch_resume(
        argparse.Namespace(slug="pyforge-marshal", format="text"),
        fs=fs,
        vcs=Vcs(),
        process=process,
    )
    assert code == EXIT_OK
    assert process.spawn_calls
    assert any(
        line for _p, line, _f in fs.appended if "dispatch-operator-resume" in line
    )


def test_failed_patch_path_matches_epic1_discipline() -> None:
    run_dir = Path("/runs/dispatch-1")
    assert failed_patch_path(run_dir, "22-6-test").name == "changes.patch"


def test_ensure_dispatch_supervision_refuses_completed() -> None:
    fs = FakeFs()
    journal = dispatch_core.DispatchJournalFacts(
        story_key="22-6-test",
        session_pid=42,
        model=None,
        launched_at=None,
        worktree_path="/wt",
        baseline_head_sha="abc",
        supervisor_pid=99,
        completion_verdict="completed",
    )
    process = FakeProcess()
    _, findings, _ = _ensure_dispatch_supervision(
        fs=fs,
        vcs=FakeVcs(),
        process=process,
        repo_root=Path("/repo"),
        run_dir=Path("/repo/run"),
        run_id="run1",
        slug="pyforge-marshal",
        journal=journal,
        effective_policy=_minimal_policy(),
        operator_kind="resume",
    )
    assert any(f.code == "MRS-DISP-023" for f in findings)
