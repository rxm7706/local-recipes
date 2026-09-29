"""Unit tests for ``supervisor/intent_gap_preserve.py`` (Story 20.4, FR-189).

Covers the spec's I/O matrix: commits-above-baseline branch park, dirty-only
patch, idempotence when already preserved, selectivity (non-intent-gap), and
clean-tree no-op.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pyforge.marshal.ports.harness import TaskPhaseSnapshot
from pyforge.marshal.supervisor.intent_gap_preserve import (
    AttemptSnapshot,
    append_preserve_notice,
    capture_attempt_snapshot,
    looks_like_intent_gap,
    park_preserve_artifact,
)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("baseline\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "baseline")
    return repo


def _baseline(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


def _task(
    repo: Path,
    *,
    story_key: str = "20-4-intent-gap",
    baseline: str | None = None,
) -> TaskPhaseSnapshot:
    return TaskPhaseSnapshot(
        story_key=story_key,
        phase="dev-running",
        commit_sha=None,
        worktree_path=str(repo),
        baseline_commit=baseline or _baseline(repo),
    )


# --- looks_like_intent_gap -------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Intent gap: spec missing AC", True),
        ("intent_gap halt", True),
        ("intent-gap blocking condition", True),
        ("blocking condition in spec", False),
        ("verify exhausted", False),
        (None, False),
    ],
)
def test_looks_like_intent_gap(text: str | None, expected: bool):
    assert looks_like_intent_gap(text) is expected


def test_looks_like_intent_gap_reads_auto_run_result_body():
    assert looks_like_intent_gap(
        None,
        auto_run_result_text="Status: escalated\n\nintent gap in spec",
    )


# --- capture_attempt_snapshot ----------------------------------------------------


def test_capture_returns_none_for_clean_tree(tmp_path):
    repo = _init_repo(tmp_path)
    assert capture_attempt_snapshot(_task(repo)) is None


def test_capture_dirty_only(tmp_path):
    repo = _init_repo(tmp_path)
    (repo / "dirty.txt").write_text("wip\n", encoding="utf-8")
    snap = capture_attempt_snapshot(_task(repo))
    assert snap is not None
    assert snap.commits_above_baseline == ()
    assert snap.dirty_patch
    assert "dirty.txt" in snap.dirty_patch


def test_capture_commits_above_baseline(tmp_path):
    repo = _init_repo(tmp_path)
    baseline = _baseline(repo)
    (repo / "feature.txt").write_text("feat\n", encoding="utf-8")
    _git(repo, "add", "feature.txt")
    _git(repo, "commit", "-m", "attempt commit")
    snap = capture_attempt_snapshot(_task(repo, baseline=baseline))
    assert snap is not None
    assert len(snap.commits_above_baseline) == 1
    assert snap.head_sha == _git(repo, "rev-parse", "HEAD").stdout.strip()


# --- park_preserve_artifact (I/O matrix) -----------------------------------------


def test_park_creates_attempt_preserve_branch_for_commits(tmp_path):
    repo = _init_repo(tmp_path)
    baseline = _baseline(repo)
    (repo / "feature.txt").write_text("feat\n", encoding="utf-8")
    _git(repo, "add", "feature.txt")
    _git(repo, "commit", "-m", "attempt commit")
    head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    snap = AttemptSnapshot(
        story_key="20-4-intent-gap",
        worktree_path=str(repo),
        baseline_commit=baseline,
        head_sha=head,
        commits_above_baseline=(head,),
    )
    # Simulate intent-gap revert: HEAD back at baseline before park.
    _git(repo, "reset", "--hard", baseline)
    run_dir = tmp_path / "bmad-run"
    ref = park_preserve_artifact(snap, harness_run_id="acme-run-1", bmad_run_dir=run_dir)
    assert ref == f"attempt-preserve/acme-run-1-{head[:8]}"
    branches = _git(repo, "branch", "--list", "attempt-preserve/*").stdout
    assert ref in branches
    tip = _git(repo, "rev-parse", ref).stdout.strip()
    assert tip == head


def test_park_writes_changes_patch_for_dirty_only(tmp_path):
    repo = _init_repo(tmp_path)
    baseline = _baseline(repo)
    head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    patch_body = "diff --git a/dirty.txt b/dirty.txt\n"
    snap = AttemptSnapshot(
        story_key="20-4-intent-gap",
        worktree_path=str(repo),
        baseline_commit=baseline,
        head_sha=head,
        commits_above_baseline=(),
        dirty_patch=patch_body,
    )
    run_dir = tmp_path / "bmad-run"
    ref = park_preserve_artifact(snap, harness_run_id="acme-run-1", bmad_run_dir=run_dir)
    patch_path = run_dir / "failed" / "20-4-intent-gap" / "changes.patch"
    assert ref == patch_path.as_posix()
    assert patch_path.read_text(encoding="utf-8") == patch_body


def test_park_returns_none_for_empty_patch(tmp_path):
    repo = _init_repo(tmp_path)
    baseline = _baseline(repo)
    head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    snap = AttemptSnapshot(
        story_key="20-4-intent-gap",
        worktree_path=str(repo),
        baseline_commit=baseline,
        head_sha=head,
        commits_above_baseline=(),
        dirty_patch="",
    )
    assert park_preserve_artifact(snap, harness_run_id="acme-run-1", bmad_run_dir=tmp_path / "run") is None


# --- append_preserve_notice ------------------------------------------------------


def test_append_preserve_notice_appends_auto_run_result(tmp_path):
    spec = tmp_path / "spec.md"
    spec.write_text("---\nstatus: in-progress\n---\n\n# Spec\n", encoding="utf-8")
    assert append_preserve_notice(spec, "attempt-preserve/run1-deadbeef") is True
    text = spec.read_text(encoding="utf-8")
    assert "## Auto Run Result" in text
    assert "preserve_ref=attempt-preserve/run1-deadbeef" in text
    assert append_preserve_notice(spec, "attempt-preserve/run1-deadbeef") is False


def test_append_preserve_notice_extends_existing_auto_run_result(tmp_path):
    """Intent-gap always wrote ARR already — CAP-2 still needs the named ref."""
    spec = tmp_path / "spec.md"
    spec.write_text(
        "---\nstatus: blocked\n---\n\n# Spec\n\n"
        "## Auto Run Result\n\nStatus: blocked\n\n"
        "Blocking condition: intent gap\n",
        encoding="utf-8",
    )
    assert append_preserve_notice(spec, "failed/20-4/changes.patch") is True
    text = spec.read_text(encoding="utf-8")
    assert text.count("## Auto Run Result") == 1
    assert "preserve_ref=failed/20-4/changes.patch" in text
    # Inserted under ARR, before the original Status body is fine as long as
    # the heading precedes the preserve_ref line.
    arr_idx = text.index("## Auto Run Result")
    ref_idx = text.index("preserve_ref=failed/20-4/changes.patch")
    assert arr_idx < ref_idx
    assert "Blocking condition: intent gap" in text
    assert append_preserve_notice(spec, "failed/20-4/changes.patch") is False


def test_park_also_writes_dirty_overlay_when_commits_exist(tmp_path):
    repo = _init_repo(tmp_path)
    baseline = _baseline(repo)
    (repo / "feature.txt").write_text("feat\n", encoding="utf-8")
    _git(repo, "add", "feature.txt")
    _git(repo, "commit", "-m", "attempt commit")
    head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    snap = AttemptSnapshot(
        story_key="20-4-intent-gap",
        worktree_path=str(repo),
        baseline_commit=baseline,
        head_sha=head,
        commits_above_baseline=(head,),
        dirty_patch="diff --git a/extra.txt b/extra.txt\n",
    )
    _git(repo, "reset", "--hard", baseline)
    run_dir = tmp_path / "bmad-run"
    ref = park_preserve_artifact(snap, harness_run_id="acme-run-1", bmad_run_dir=run_dir)
    assert ref == f"attempt-preserve/acme-run-1-{head[:8]}"
    patch_path = run_dir / "failed" / "20-4-intent-gap" / "changes.patch"
    assert patch_path.read_text(encoding="utf-8").startswith("diff --git")


def test_resolve_spec_path_relative_absolute_and_escape(tmp_path):
    from pyforge.marshal.supervisor.intent_gap_preserve import resolve_spec_path

    home = tmp_path / "home"
    home.mkdir()
    spec = home / "specs" / "story.md"
    spec.parent.mkdir()
    spec.write_text("# s\n", encoding="utf-8")
    assert resolve_spec_path(home, "specs/story.md") == spec.resolve()
    assert resolve_spec_path(home, str(spec)) == spec.resolve()
    assert resolve_spec_path(home, None) is None
    assert resolve_spec_path(home, "missing.md") is None
    outside = tmp_path / "outside.md"
    outside.write_text("x\n", encoding="utf-8")
    assert resolve_spec_path(home, "../outside.md") is None


def test_capture_returns_none_without_worktree_or_baseline(tmp_path):
    repo = _init_repo(tmp_path)
    bare = TaskPhaseSnapshot(
        story_key="20-4",
        phase="dev-running",
        commit_sha=None,
        worktree_path="",
        baseline_commit=_baseline(repo),
    )
    assert capture_attempt_snapshot(bare) is None
    missing = TaskPhaseSnapshot(
        story_key="20-4",
        phase="dev-running",
        commit_sha=None,
        worktree_path=str(tmp_path / "nope"),
        baseline_commit=_baseline(repo),
    )
    assert capture_attempt_snapshot(missing) is None
    no_base = TaskPhaseSnapshot(
        story_key="20-4",
        phase="dev-running",
        commit_sha=None,
        worktree_path=str(repo),
        baseline_commit=None,
    )
    assert capture_attempt_snapshot(no_base) is None


def test_capture_returns_none_on_git_error(tmp_path, monkeypatch):
    import pyforge.marshal.supervisor.intent_gap_preserve as mod

    repo = _init_repo(tmp_path)

    def boom(*a, **k):
        raise mod.GitPreserveError("boom")

    monkeypatch.setattr(mod, "_rev_parse_head", boom)
    assert capture_attempt_snapshot(_task(repo)) is None


def test_park_falls_back_to_patch_when_branch_fails(tmp_path, monkeypatch):
    import pyforge.marshal.supervisor.intent_gap_preserve as mod

    repo = _init_repo(tmp_path)
    baseline = _baseline(repo)
    head = _baseline(repo)
    snap = AttemptSnapshot(
        story_key="20-4-intent-gap",
        worktree_path=str(repo),
        baseline_commit=baseline,
        head_sha=head,
        commits_above_baseline=(head,),
        dirty_patch="diff --git a/x b/x\n",
    )

    def fail_branch(*a, **k):
        raise mod.GitPreserveError("branch failed")

    monkeypatch.setattr(mod, "_preserve_commits", fail_branch)
    run_dir = tmp_path / "run"
    ref = park_preserve_artifact(snap, harness_run_id="run1", bmad_run_dir=run_dir)
    assert ref is not None
    assert ref.endswith("changes.patch")


def test_append_preserve_notice_missing_and_binary(tmp_path):
    missing = tmp_path / "nope.md"
    assert append_preserve_notice(missing, "attempt-preserve/x") is False
    binary = tmp_path / "bin.md"
    binary.write_bytes(b"\xff\xfe## Auto Run Result\n")
    assert append_preserve_notice(binary, "attempt-preserve/x") is False


def test_safe_segment_sanitizes_illegal_chars():
    from pyforge.marshal.supervisor.intent_gap_preserve import (
        _safe_ref_segment,
        _safe_segment,
    )

    assert "/" not in _safe_segment('a/b:c*?"')
    assert _safe_ref_segment("..weird@{ref}") != "..weird@{ref}"
