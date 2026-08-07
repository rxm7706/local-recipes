"""Unit tests for ``core/retire.py`` (pure classification) and
``cli/retire.py`` (``marshal retire``, Story 4.10, FR-63/AD-47).

Fake ``VcsPort``/``HarnessPort`` doubles mirror ``tests/unit/test_land.py``'s
own established convention (hand-written classes implementing the Protocol,
never mocks); filesystem I/O runs against a REAL ``tmp_path`` via the real
``LocalFs``, same as every ``cli/deploy.py``/``cli/land.py`` test.
``cli/retire.py``'s own local import of ``_latest_run_dir``/
``_resolve_harness_run_id_for_resume`` from ``cli/spin.py`` is stubbed at
THAT module's own attribute (the local import re-resolves it at call time,
so patching ``spin_module``'s own names, not ``retire_module``'s, is what
takes effect) -- the per-project journal-directory discovery those two
functions perform is exercised separately by ``test_spin.py``/
``test_deploy.py``; this file only needs a fixed, synthetic
``(run_dir, harness_run_id)`` pair per project.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from pyforge.marshal.adapters.fs_local import LocalFs
from pyforge.marshal.adapters.vcs_git import VcsCommandError
from pyforge.marshal.cli import retire as retire_module
from pyforge.marshal.cli import spin as spin_module
from pyforge.marshal.core import retire as core_retire
from pyforge.marshal.ports.harness import RunStatusSnapshot, TaskPhaseSnapshot
from pyforge.marshal.ports.vcs import WorktreeEntry

# =====================================================================
# core/retire.py -- pure classification, no I/O, no fakes needed.
# =====================================================================


def _candidate(**overrides) -> core_retire.RetirementCandidate:
    fields = {"slug": "acme", "branch": "acme-4-10-story", "story_key": "4.10"}
    fields.update(overrides)
    return core_retire.RetirementCandidate(**fields)


class TestIsStructurallyExcluded:
    def test_loop_prefix_is_excluded(self):
        assert core_retire.is_structurally_excluded("loop/acme") is True

    def test_ordinary_branch_is_not_excluded(self):
        assert core_retire.is_structurally_excluded("acme-4-10-story") is False

    def test_a_branch_merely_containing_loop_is_not_excluded(self):
        assert core_retire.is_structurally_excluded("main-loop/acme") is False


class TestClassifyRetirement:
    def test_all_three_facts_true_proposes(self):
        candidate = _candidate()
        outcome = core_retire.classify_retirement(
            candidate,
            merged_by_patch_id=True,
            run_concluded=True,
            recorded_merge_sha="abc123",
        )
        assert isinstance(outcome, core_retire.RetirementProposal)
        assert outcome.candidate == candidate
        assert outcome.recorded_merge_sha == "abc123"

    def test_not_merged_refuses_naming_the_fact(self):
        outcome = core_retire.classify_retirement(
            _candidate(),
            merged_by_patch_id=False,
            run_concluded=True,
            recorded_merge_sha="abc123",
        )
        assert isinstance(outcome, core_retire.InsufficientEvidence)
        assert outcome.missing == ("merged_by_patch_id",)

    def test_worktree_still_live_refuses_naming_run_concluded(self):
        outcome = core_retire.classify_retirement(
            _candidate(),
            merged_by_patch_id=True,
            run_concluded=False,
            recorded_merge_sha="abc123",
        )
        assert isinstance(outcome, core_retire.InsufficientEvidence)
        assert outcome.missing == ("run_concluded",)

    def test_no_recorded_sha_refuses_naming_story_done_with_sha(self):
        outcome = core_retire.classify_retirement(
            _candidate(),
            merged_by_patch_id=True,
            run_concluded=True,
            recorded_merge_sha=None,
        )
        assert isinstance(outcome, core_retire.InsufficientEvidence)
        assert outcome.missing == ("story_done_with_sha",)

    def test_every_fact_false_names_all_three_in_fixed_order(self):
        outcome = core_retire.classify_retirement(
            _candidate(),
            merged_by_patch_id=False,
            run_concluded=False,
            recorded_merge_sha=None,
        )
        assert isinstance(outcome, core_retire.InsufficientEvidence)
        assert outcome.missing == (
            "merged_by_patch_id",
            "run_concluded",
            "story_done_with_sha",
        )


# =====================================================================
# cli/retire.py -- I/O matrix, fake VcsPort/HarnessPort.
# =====================================================================


class _FakeVcs:
    """A minimal ``VcsPort`` stand-in exposing only what ``cli/retire.py``
    calls -- mirrors ``tests/unit/test_land.py::_FakeVcs``'s own
    configurable-raise shape."""

    def __init__(
        self,
        *,
        repo_root_value: Path = Path("/fake-repo-root"),
        worktrees: tuple[WorktreeEntry, ...] = (),
        worktrees_raise: bool = False,
        merged_map: dict[str, bool] | None = None,
        merged_raises_for: frozenset[str] = frozenset(),
        worktree_path_map: dict[str, Path | None] | None = None,
        worktree_path_raises_for: frozenset[str] = frozenset(),
        delete_raises_for: frozenset[str] = frozenset(),
    ) -> None:
        self.repo_root_value = repo_root_value
        self.worktrees = worktrees
        self.worktrees_raise = worktrees_raise
        self.merged_map = merged_map or {}
        self.merged_raises_for = merged_raises_for
        self.worktree_path_map = worktree_path_map or {}
        self.worktree_path_raises_for = worktree_path_raises_for
        self.delete_raises_for = delete_raises_for
        self.delete_calls: list[tuple[str, bool]] = []
        self.merged_calls: list[str] = []

    def repo_common_root(self, start):
        return self.repo_root_value

    def list_worktrees(self, repo_root):
        if self.worktrees_raise:
            raise VcsCommandError("git worktree list failed")
        return self.worktrees

    def is_branch_merged(self, repo_root, branch, *, into):
        self.merged_calls.append(branch)
        if branch in self.merged_raises_for:
            raise VcsCommandError("git cherry failed")
        return self.merged_map.get(branch, False)

    def worktree_path_for_branch(self, repo_root, branch):
        if branch in self.worktree_path_raises_for:
            raise VcsCommandError("git worktree list --porcelain failed")
        return self.worktree_path_map.get(branch)

    def delete_branch(self, repo_root, branch, *, force=False):
        self.delete_calls.append((branch, force))
        if branch in self.delete_raises_for:
            raise VcsCommandError("git branch -d failed")


class _FakeHarness:
    """A minimal ``HarnessPort`` stand-in: ``run_status_snapshot`` keyed by
    ``str(project)`` (the loop-home path each worktree entry names)."""

    def __init__(self, snapshots: dict[str, RunStatusSnapshot | None] | None = None) -> None:
        self.snapshots = snapshots or {}
        self.calls: list[tuple[str, str]] = []

    def run_status_snapshot(self, project, run_id):
        self.calls.append((str(project), run_id))
        return self.snapshots.get(str(project))


def _snapshot(tasks: tuple[TaskPhaseSnapshot, ...]) -> RunStatusSnapshot:
    return RunStatusSnapshot(
        paused_stage=None,
        paused_story_key=None,
        paused_reason=None,
        escalated_spec_file=None,
        escalated_task_phase=None,
        deferred=(),
        finished=True,
        tasks=tasks,
    )


def _args(*, project: str | None = None, execute: bool = False, format: str = "json"):
    return argparse.Namespace(project=project, execute=execute, format=format)


def _payload(capsys):
    return json.loads(capsys.readouterr().out)


def _stub_run_discovery(monkeypatch, *, run_dir_map: dict[str, Path | None]) -> None:
    """Stubs ``cli/spin.py``'s own ``_latest_run_dir``/
    ``_resolve_harness_run_id_for_resume`` -- ``cli/retire.py`` imports both
    LOCALLY inside ``run_retire`` (mirrors ``_gather_claimed_commits``'s own
    established convention), so the live functions are re-resolved off
    ``spin_module`` at call time; patching that module's own attributes is
    what actually takes effect. ``run_dir_map`` keys by slug: ``None`` means
    "no run found for this slug" (``_latest_run_dir`` returns ``None``)."""

    def _latest_run_dir(home, slug):
        return run_dir_map.get(slug)

    def _resolve_harness_run_id_for_resume(fs, run_dir, run_id):
        return f"harness-{run_id}" if run_dir is not None else None

    monkeypatch.setattr(spin_module, "_latest_run_dir", _latest_run_dir)
    monkeypatch.setattr(
        spin_module, "_resolve_harness_run_id_for_resume", _resolve_harness_run_id_for_resume
    )


@pytest.fixture(autouse=True)
def _no_active_project_env(monkeypatch):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)


def _patch_repo(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(retire_module, "repo_root", lambda: tmp_path)


# --- preconditions -----------------------------------------------------


def test_malformed_project_slug_refuses_before_any_io(tmp_path, capsys, monkeypatch):
    _patch_repo(monkeypatch, tmp_path)
    vcs = _FakeVcs(worktrees_raise=True)  # would raise if ever called

    exit_code = retire_module.run_retire(
        _args(project="../evil"), vcs=vcs, fs=LocalFs(), harness=_FakeHarness()
    )

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-RETIRE-001" in codes
    assert exit_code != 0


def test_no_loop_homes_is_a_clean_noop(tmp_path, capsys, monkeypatch):
    _patch_repo(monkeypatch, tmp_path)
    vcs = _FakeVcs(worktrees=())

    exit_code = retire_module.run_retire(
        _args(), vcs=vcs, fs=LocalFs(), harness=_FakeHarness()
    )

    payload = _payload(capsys)
    assert payload["data"]["proposals"] == []
    assert payload["data"]["insufficient_evidence"] == []
    assert payload["data"]["deleted"] == []
    assert payload["verdict"] == "clean"
    assert exit_code == 0


def test_fleet_worktree_listing_failure_reports_warn(tmp_path, capsys, monkeypatch):
    _patch_repo(monkeypatch, tmp_path)
    vcs = _FakeVcs(worktrees_raise=True)

    exit_code = retire_module.run_retire(
        _args(), vcs=vcs, fs=LocalFs(), harness=_FakeHarness()
    )

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-RETIRE-002" in codes
    assert payload["verdict"] == "warn"
    assert exit_code == 0


# --- discovery edge cases -------------------------------------------------


def test_project_with_no_run_yet_contributes_zero_candidates(tmp_path, capsys, monkeypatch):
    _patch_repo(monkeypatch, tmp_path)
    _stub_run_discovery(monkeypatch, run_dir_map={"acme": None})
    home = tmp_path / "loop-homes" / "acme"
    vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))

    exit_code = retire_module.run_retire(
        _args(), vcs=vcs, fs=LocalFs(), harness=_FakeHarness()
    )

    payload = _payload(capsys)
    assert payload["data"]["proposals"] == []
    assert payload["data"]["insufficient_evidence"] == []
    assert payload["verdict"] == "clean"
    assert exit_code == 0


def test_project_with_no_worktree_isolated_tasks_contributes_zero_candidates(
    tmp_path, capsys, monkeypatch
):
    _patch_repo(monkeypatch, tmp_path)
    _stub_run_discovery(monkeypatch, run_dir_map={"acme": tmp_path / "runs" / "acme-run1"})
    home = tmp_path / "loop-homes" / "acme"
    vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))
    harness = _FakeHarness(
        snapshots={
            str(home): _snapshot(
                (TaskPhaseSnapshot(story_key="4.10", phase="done", commit_sha="sha1", branch=""),)
            )
        }
    )

    exit_code = retire_module.run_retire(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = _payload(capsys)
    assert payload["data"]["proposals"] == []
    assert payload["data"]["insufficient_evidence"] == []
    assert payload["verdict"] == "clean"
    assert exit_code == 0


def test_malformed_story_key_is_skipped_not_a_failure(tmp_path, capsys, monkeypatch):
    _patch_repo(monkeypatch, tmp_path)
    _stub_run_discovery(monkeypatch, run_dir_map={"acme": tmp_path / "runs" / "acme-run1"})
    home = tmp_path / "loop-homes" / "acme"
    vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))
    harness = _FakeHarness(
        snapshots={
            str(home): _snapshot(
                (
                    TaskPhaseSnapshot(
                        story_key="not-a-key", phase="done", commit_sha="sha1", branch="b1"
                    ),
                )
            )
        }
    )

    exit_code = retire_module.run_retire(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = _payload(capsys)
    assert payload["data"]["proposals"] == []
    assert payload["data"]["insufficient_evidence"] == []
    assert payload["verdict"] == "clean"
    assert exit_code == 0


def test_station_branch_named_in_a_task_snapshot_is_excluded_structurally(
    tmp_path, capsys, monkeypatch
):
    """Defense in depth (should never happen per the I/O matrix): a
    malformed harness snapshot naming a `loop/<slug>` branch as a task's own
    branch is excluded BEFORE any evidence-gathering VcsPort call runs."""
    _patch_repo(monkeypatch, tmp_path)
    _stub_run_discovery(monkeypatch, run_dir_map={"acme": tmp_path / "runs" / "acme-run1"})
    home = tmp_path / "loop-homes" / "acme"
    vcs = _FakeVcs(
        worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
        merged_raises_for=frozenset({"loop/acme"}),  # would raise if ever evaluated
    )
    harness = _FakeHarness(
        snapshots={
            str(home): _snapshot(
                (
                    TaskPhaseSnapshot(
                        story_key="4.10", phase="done", commit_sha="sha1", branch="loop/acme"
                    ),
                )
            )
        }
    )

    exit_code = retire_module.run_retire(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = _payload(capsys)
    assert payload["data"]["proposals"] == []
    assert payload["data"]["insufficient_evidence"] == []
    assert exit_code == 0


# --- evidence matrix -------------------------------------------------------


def _one_task_setup(monkeypatch, tmp_path, *, phase="done", commit_sha="sha1"):
    _stub_run_discovery(monkeypatch, run_dir_map={"acme": tmp_path / "runs" / "acme-run1"})
    home = tmp_path / "loop-homes" / "acme"
    harness = _FakeHarness(
        snapshots={
            str(home): _snapshot(
                (
                    TaskPhaseSnapshot(
                        story_key="4.10", phase=phase, commit_sha=commit_sha, branch="acme-4-10"
                    ),
                )
            )
        }
    )
    return home, harness


def test_fully_provable_branch_is_proposed_with_evidence(tmp_path, capsys, monkeypatch):
    _patch_repo(monkeypatch, tmp_path)
    home, harness = _one_task_setup(monkeypatch, tmp_path)
    vcs = _FakeVcs(
        worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
        merged_map={"acme-4-10": True},
        worktree_path_map={"acme-4-10": None},
    )

    exit_code = retire_module.run_retire(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = _payload(capsys)
    assert payload["data"]["proposals"] == [
        {
            "slug": "acme",
            "branch": "acme-4-10",
            "story_key": "4.10",
            "merged_by_patch_id": True,
            "worktree": None,
            "recorded_merge_sha": "sha1",
        }
    ]
    assert payload["data"]["insufficient_evidence"] == []
    assert payload["verdict"] == "clean"
    assert exit_code == 0
    assert vcs.delete_calls == []  # dry-run: never deletes


def test_merged_but_worktree_still_live_is_refused(tmp_path, capsys, monkeypatch):
    _patch_repo(monkeypatch, tmp_path)
    home, harness = _one_task_setup(monkeypatch, tmp_path)
    vcs = _FakeVcs(
        worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
        merged_map={"acme-4-10": True},
        worktree_path_map={"acme-4-10": Path("/live/worktree")},
    )

    exit_code = retire_module.run_retire(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = _payload(capsys)
    assert payload["data"]["proposals"] == []
    assert payload["data"]["insufficient_evidence"] == [
        {
            "slug": "acme",
            "branch": "acme-4-10",
            "story_key": "4.10",
            "missing": ["run_concluded"],
        }
    ]
    assert exit_code == 0


def test_worktree_gone_but_phase_never_done_is_refused(tmp_path, capsys, monkeypatch):
    _patch_repo(monkeypatch, tmp_path)
    home, harness = _one_task_setup(monkeypatch, tmp_path, phase="dev-implement", commit_sha=None)
    vcs = _FakeVcs(
        worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
        merged_map={"acme-4-10": True},
        worktree_path_map={"acme-4-10": None},
    )

    exit_code = retire_module.run_retire(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = _payload(capsys)
    assert payload["data"]["proposals"] == []
    assert payload["data"]["insufficient_evidence"] == [
        {
            "slug": "acme",
            "branch": "acme-4-10",
            "story_key": "4.10",
            "missing": ["story_done_with_sha"],
        }
    ]
    assert exit_code == 0


def test_vcs_command_error_gathering_evidence_refuses_and_warns(tmp_path, capsys, monkeypatch):
    _patch_repo(monkeypatch, tmp_path)
    home, harness = _one_task_setup(monkeypatch, tmp_path)
    vcs = _FakeVcs(
        worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
        merged_raises_for=frozenset({"acme-4-10"}),
        worktree_path_map={"acme-4-10": None},
    )

    exit_code = retire_module.run_retire(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-RETIRE-002" in codes
    assert payload["data"]["proposals"] == []
    assert payload["data"]["insufficient_evidence"] == [
        {
            "slug": "acme",
            "branch": "acme-4-10",
            "story_key": "4.10",
            "missing": ["merged_by_patch_id"],
        }
    ]
    assert payload["verdict"] == "warn"
    assert exit_code == 0


# --- --execute --------------------------------------------------------


def test_dry_run_never_calls_delete_branch(tmp_path, capsys, monkeypatch):
    _patch_repo(monkeypatch, tmp_path)
    home, harness = _one_task_setup(monkeypatch, tmp_path)
    vcs = _FakeVcs(
        worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
        merged_map={"acme-4-10": True},
        worktree_path_map={"acme-4-10": None},
    )

    exit_code = retire_module.run_retire(
        _args(execute=False), vcs=vcs, fs=LocalFs(), harness=harness
    )

    payload = _payload(capsys)
    assert payload["data"]["executed"] is False
    assert payload["data"]["deleted"] == []
    assert vcs.delete_calls == []
    assert exit_code == 0


def test_execute_deletes_every_proposed_branch_and_journals(tmp_path, capsys, monkeypatch):
    _patch_repo(monkeypatch, tmp_path)
    home, harness = _one_task_setup(monkeypatch, tmp_path)
    vcs = _FakeVcs(
        worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
        merged_map={"acme-4-10": True},
        worktree_path_map={"acme-4-10": None},
    )

    exit_code = retire_module.run_retire(
        _args(execute=True), vcs=vcs, fs=LocalFs(), harness=harness
    )

    payload = _payload(capsys)
    assert payload["data"]["executed"] is True
    assert payload["data"]["deleted"] == [
        {
            "slug": "acme",
            "branch": "acme-4-10",
            "story_key": "4.10",
            "recorded_merge_sha": "sha1",
        }
    ]
    # Code review (2026-08-06, both reviewers independently): `force=True`,
    # matching `is_branch_merged`'s own content-based (patch-id) proof and
    # `cli/init.py::run_teardown`'s identical precedent -- `force=False`
    # would let git's own ancestry-based `-d` spuriously refuse exactly the
    # squash-merged branches this command proves safe by content.
    assert vcs.delete_calls == [("acme-4-10", True)]
    assert exit_code == 0

    # Journaled: one run directory under acme's own Tier-3 store carries a
    # branch-retirement observation entry.
    runs_dir = tmp_path / "_bmad-output" / "projects" / "acme" / "implementation-artifacts" / "runs"
    run_dirs = list(runs_dir.iterdir())
    assert len(run_dirs) == 1
    journal_text = (run_dirs[0] / "journal.jsonl").read_text(encoding="utf-8")
    assert "branch-retirement" in journal_text
    assert "acme-4-10" in journal_text


def test_execute_partial_failure_still_attempts_the_rest(tmp_path, capsys, monkeypatch):
    _stub_run_discovery(
        monkeypatch,
        run_dir_map={"acme": tmp_path / "runs" / "acme-run1"},
    )
    _patch_repo(monkeypatch, tmp_path)
    home = tmp_path / "loop-homes" / "acme"
    harness = _FakeHarness(
        snapshots={
            str(home): _snapshot(
                (
                    TaskPhaseSnapshot(
                        story_key="4.10", phase="done", commit_sha="sha1", branch="acme-4-10"
                    ),
                    TaskPhaseSnapshot(
                        story_key="4.11", phase="done", commit_sha="sha2", branch="acme-4-11"
                    ),
                )
            )
        }
    )
    vcs = _FakeVcs(
        worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
        merged_map={"acme-4-10": True, "acme-4-11": True},
        worktree_path_map={"acme-4-10": None, "acme-4-11": None},
        delete_raises_for=frozenset({"acme-4-10"}),
    )

    exit_code = retire_module.run_retire(
        _args(execute=True), vcs=vcs, fs=LocalFs(), harness=harness
    )

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-RETIRE-003" in codes
    deleted_branches = {entry["branch"] for entry in payload["data"]["deleted"]}
    assert deleted_branches == {"acme-4-11"}
    assert {branch for branch, _force in vcs.delete_calls} == {"acme-4-10", "acme-4-11"}
    assert payload["verdict"] == "warn"
    assert exit_code == 0


def test_duplicate_task_branch_in_one_run_is_evaluated_and_deleted_only_once(
    tmp_path, capsys, monkeypatch
):
    """Code review (2026-08-06, Edge Case Hunter): two ``TaskPhaseSnapshot``
    entries naming the SAME branch (a harness anomaly, or a retried story
    reusing a worktree-isolated branch) must not gather evidence twice,
    double-report the branch in ``proposals``, or attempt ``delete_branch``
    twice under ``--execute`` (the second attempt would necessarily fail --
    the branch is already gone -- producing a spurious WARN for a
    deletion that actually succeeded)."""
    _stub_run_discovery(monkeypatch, run_dir_map={"acme": tmp_path / "runs" / "acme-run1"})
    _patch_repo(monkeypatch, tmp_path)
    home = tmp_path / "loop-homes" / "acme"
    harness = _FakeHarness(
        snapshots={
            str(home): _snapshot(
                (
                    TaskPhaseSnapshot(
                        story_key="4.10", phase="done", commit_sha="sha1", branch="acme-4-10"
                    ),
                    # A second task, different story_key, but the SAME
                    # branch -- must be treated as already-classified, not
                    # a fresh candidate.
                    TaskPhaseSnapshot(
                        story_key="4.10a", phase="done", commit_sha="sha1", branch="acme-4-10"
                    ),
                )
            )
        }
    )
    vcs = _FakeVcs(
        worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
        merged_map={"acme-4-10": True},
        worktree_path_map={"acme-4-10": None},
    )

    exit_code = retire_module.run_retire(
        _args(execute=True), vcs=vcs, fs=LocalFs(), harness=harness
    )

    payload = _payload(capsys)
    assert [p["branch"] for p in payload["data"]["proposals"]] == ["acme-4-10"]
    assert vcs.merged_calls.count("acme-4-10") == 1
    assert vcs.delete_calls == [("acme-4-10", True)]
    assert payload["data"]["deleted"] == [
        {
            "slug": "acme",
            "branch": "acme-4-10",
            "story_key": "4.10",
            "recorded_merge_sha": "sha1",
        }
    ]
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-RETIRE-003" not in codes
    assert exit_code == 0


# --- multi-project + --project scoping -------------------------------


def test_two_projects_one_with_proposals_one_without(tmp_path, capsys, monkeypatch):
    _patch_repo(monkeypatch, tmp_path)
    home_a = tmp_path / "loop-homes" / "acme"
    home_b = tmp_path / "loop-homes" / "beta"
    _stub_run_discovery(
        monkeypatch,
        run_dir_map={
            "acme": tmp_path / "runs" / "acme-run1",
            "beta": tmp_path / "runs" / "beta-run1",
        },
    )
    harness = _FakeHarness(
        snapshots={
            str(home_a): _snapshot(
                (
                    TaskPhaseSnapshot(
                        story_key="4.10", phase="done", commit_sha="sha1", branch="acme-4-10"
                    ),
                )
            ),
            str(home_b): _snapshot(()),
        }
    )
    vcs = _FakeVcs(
        worktrees=(
            WorktreeEntry(path=home_a, branch="loop/acme"),
            WorktreeEntry(path=home_b, branch="loop/beta"),
        ),
        merged_map={"acme-4-10": True},
        worktree_path_map={"acme-4-10": None},
    )

    exit_code = retire_module.run_retire(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = _payload(capsys)
    assert len(payload["data"]["proposals"]) == 1
    assert payload["data"]["proposals"][0]["slug"] == "acme"
    assert exit_code == 0


def test_project_flag_scopes_to_one_slug(tmp_path, capsys, monkeypatch):
    _patch_repo(monkeypatch, tmp_path)
    home_a = tmp_path / "loop-homes" / "acme"
    home_b = tmp_path / "loop-homes" / "beta"
    _stub_run_discovery(
        monkeypatch,
        run_dir_map={
            "acme": tmp_path / "runs" / "acme-run1",
            "beta": tmp_path / "runs" / "beta-run1",
        },
    )
    harness = _FakeHarness(
        snapshots={
            str(home_a): _snapshot(
                (
                    TaskPhaseSnapshot(
                        story_key="4.10", phase="done", commit_sha="sha1", branch="acme-4-10"
                    ),
                )
            ),
            str(home_b): _snapshot(
                (
                    TaskPhaseSnapshot(
                        story_key="9.1", phase="done", commit_sha="sha9", branch="beta-9-1"
                    ),
                )
            ),
        }
    )
    vcs = _FakeVcs(
        worktrees=(
            WorktreeEntry(path=home_a, branch="loop/acme"),
            WorktreeEntry(path=home_b, branch="loop/beta"),
        ),
        merged_map={"acme-4-10": True, "beta-9-1": True},
        worktree_path_map={"acme-4-10": None, "beta-9-1": None},
    )

    exit_code = retire_module.run_retire(
        _args(project="beta"), vcs=vcs, fs=LocalFs(), harness=harness
    )

    payload = _payload(capsys)
    assert len(payload["data"]["proposals"]) == 1
    assert payload["data"]["proposals"][0]["slug"] == "beta"
    assert exit_code == 0


# --- main.py wiring smoke test -------------------------------------------


def test_run_retire_with_default_ports_does_not_crash(tmp_path, monkeypatch, capsys):
    """Exercises the real GitVcs/LocalFs/BmadLoopHarness default
    construction path (smoke-level only) -- mirrors
    ``test_land.py::test_run_land_with_default_ports_does_not_crash``.
    Scoped to a slug that names no real project (``--project``, rather than
    a bare sweep): this test runs against the REAL git repo, which -- on a
    developer machine actively running bmad-loop -- may have real
    ``loop/<slug>`` worktrees/fleet state; a bare sweep would read every one
    of them for real. Scoping to a nonexistent slug keeps this test
    deterministic and read-only regardless of the ambient environment."""
    monkeypatch.setattr(retire_module, "repo_root", lambda: tmp_path)

    exit_code = retire_module.run_retire(_args(project="no-such-project-xyz"))

    assert isinstance(exit_code, int)
    payload = _payload(capsys)
    assert payload["data"]["proposals"] == []
