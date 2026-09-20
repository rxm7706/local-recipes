"""Unit tests for ``cli/deploy.py`` (``marshal deploy promote``, Story 4.1,
AD-13/AD-24/AD-29/AD-33). ``VcsPort`` is faked (no real git process needed
to prove the CLI's own orchestration -- real ``git`` behavior is proven by
``test_vcs_git.py``); filesystem I/O runs against a REAL ``tmp_path`` via
the real ``LocalFs`` (matches ``test_vcs_git.py``'s own "real I/O, not
heavy mocking" convention -- directory enumeration in ``cli/deploy.py``
uses plain ``pathlib.glob`` with no ``FsPort`` counterpart, so a fake
filesystem would need to fake glob too).
"""

from __future__ import annotations

import argparse
import json
import threading
from pathlib import Path

import pytest

from pyforge.marshal.adapters.fs_local import FsError, LocalFs
from pyforge.marshal.adapters.vcs_git import VcsCommandError
from pyforge.marshal.cli import deploy as deploy_module

_VALID_SPEC = "---\ntitle: 'x'\nstatus: 'shipped'\n---\n\nbody\n"


class _FakeVcs:
    """A minimal ``VcsPort`` stand-in exposing only ``commit_subjects``/
    ``commit_paths``/``path_has_uncommitted_changes`` -- the methods
    ``cli/deploy.py`` calls (the last added by Story 4.1's own review-fix
    pass, closing the partial-batch-failure gap in "already promoted")."""

    def __init__(
        self,
        *,
        main_subjects: tuple[str, ...] = (),
        origin_subjects: tuple[str, ...] = (),
        origin_raises: bool = False,
        main_raises: bool = False,
        commit_raises: bool = False,
        dirty_paths: frozenset = frozenset(),
        path_status_raises: bool = False,
        existing_branches: frozenset = frozenset(),
        branch_exists_raises: bool = False,
        merge_base_sha: str = "base-sha",
        merge_base_raises: bool = False,
        merge_branch_sha: str = "merge-sha",
        merge_branch_raises: bool = False,
        window_subjects: tuple[str, ...] = (),
        window_subjects_raises: bool = False,
        resolve_ref_sha: str = "branch-tip-sha",
        resolve_ref_raises: bool = False,
        resolve_ref_sequence: list[str] | None = None,
        changed_paths: tuple[str, ...] = (),
        changed_files_raises: bool = False,
        worktree_head_sha: str | None = None,
        worktree_head_sha_raises: bool = False,
    ) -> None:
        self.main_subjects = main_subjects
        self.origin_subjects = origin_subjects
        self.origin_raises = origin_raises
        self.main_raises = main_raises
        self.commit_raises = commit_raises
        self.commit_calls: list[tuple[tuple, str]] = []
        # Every tracked path this fake reports as carrying uncommitted
        # state -- default empty, so a tracked file is "clean" (committed)
        # by default, matching real git's behavior for a file nobody has
        # touched since its own commit.
        self.dirty_paths = dirty_paths
        self.path_status_raises = path_status_raises
        self.path_status_calls: list = []
        self.existing_branches = existing_branches
        self.branch_exists_raises = branch_exists_raises
        self.merge_base_sha = merge_base_sha
        self.merge_base_raises = merge_base_raises
        self.merge_branch_sha = merge_branch_sha
        self.merge_branch_raises = merge_branch_raises
        self.merge_branch_calls: list[tuple[str, str, str]] = []
        self.window_subjects = window_subjects
        self.window_subjects_raises = window_subjects_raises
        self.resolve_ref_sha = resolve_ref_sha
        self.resolve_ref_raises = resolve_ref_raises
        self.resolve_ref_sequence = list(resolve_ref_sequence) if resolve_ref_sequence is not None else None
        self.resolve_ref_calls: list[str] = []
        self.changed_paths = changed_paths
        self.changed_files_raises = changed_files_raises
        # `None` (the default) mirrors `resolve_ref_sha` -- most batch-pr
        # tests don't care about this new P5 precondition, so the fake
        # answers "the worktree IS at the branch tip" by matching whatever
        # `resolve_ref` itself returns, unless a test explicitly wants a
        # mismatch.
        self._worktree_head_sha = worktree_head_sha
        self.worktree_head_sha_raises = worktree_head_sha_raises

    def worktree_head_sha(self, worktree_path):
        if self.worktree_head_sha_raises:
            raise VcsCommandError("git rev-parse HEAD failed")
        if self._worktree_head_sha is not None:
            return self._worktree_head_sha
        return self.resolve_ref_sha

    def changed_files(self, repo_root, worktree_path, *, base):
        if self.changed_files_raises:
            raise VcsCommandError("git diff --name-status failed")
        return self.changed_paths

    def commit_subjects(self, repo_root, ref):
        if ref == "origin/main":
            if self.origin_raises:
                raise VcsCommandError("no origin remote configured")
            return self.origin_subjects
        if ref == "main":
            if self.main_raises:
                raise VcsCommandError("corrupted repo, no main")
            return self.main_subjects
        # Story 4.3's own land-story conformance audit calls with a git
        # revision-range ref ("<since>..<merge_sha>") -- any other ref
        # shape is this fixture's window-subjects case.
        if self.window_subjects_raises:
            raise VcsCommandError("cannot enumerate the conformance window")
        return self.window_subjects

    def commit_paths(self, repo_root, paths, message):
        if self.commit_raises:
            raise VcsCommandError("git commit failed")
        self.commit_calls.append((paths, message))
        return "deadbeef"

    def path_has_uncommitted_changes(self, repo_root, path):
        self.path_status_calls.append(path)
        if self.path_status_raises:
            raise VcsCommandError("git status --porcelain failed")
        return path in self.dirty_paths

    # --- Story 4.3 (`marshal deploy land-story`) additions -----------------

    def repo_common_root(self, start):
        return Path("/fake-repo-root")

    def branch_exists(self, repo_root, branch):
        if self.branch_exists_raises:
            raise VcsCommandError("git rev-parse --verify failed")
        return branch in self.existing_branches

    def merge_base(self, repo_root, a, b):
        if self.merge_base_raises:
            raise VcsCommandError("cannot find a merge base")
        return self.merge_base_sha

    def merge_branch(self, repo_root, branch, *, into, subject):
        self.merge_branch_calls.append((branch, into, subject))
        if self.merge_branch_raises:
            raise VcsCommandError("merge conflict")
        return self.merge_branch_sha

    def resolve_ref(self, repo_root, ref):
        self.resolve_ref_calls.append(ref)
        if self.resolve_ref_raises:
            raise VcsCommandError("git rev-parse --verify failed")
        if self.resolve_ref_sequence is not None:
            index = len(self.resolve_ref_calls) - 1
            if index < len(self.resolve_ref_sequence):
                return self.resolve_ref_sequence[index]
            return self.resolve_ref_sequence[-1]
        return self.resolve_ref_sha


def _args(*, project: str = "acme", format: str = "json") -> argparse.Namespace:
    return argparse.Namespace(project=project, format=format)


def _write_tier3_spec(tmp_path, slug: str, filename_key: str, text: str) -> None:
    tier3_dir = tmp_path / "_bmad-output" / "projects" / slug / "implementation-artifacts"
    tier3_dir.mkdir(parents=True, exist_ok=True)
    (tier3_dir / f"spec-{filename_key}.md").write_text(text, encoding="utf-8")


def _write_tracked_spec(tmp_path, slug: str, filename_key: str, text: str) -> None:
    specs_dir = tmp_path / "_bmad-output" / "projects" / slug / "planning-artifacts" / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / f"spec-{filename_key}.md").write_text(text, encoding="utf-8")


def _tracked_path(tmp_path, slug: str, filename_key: str):
    return tmp_path / "_bmad-output" / "projects" / slug / "planning-artifacts" / "specs" / f"spec-{filename_key}.md"


@pytest.fixture(autouse=True)
def _no_active_project_env(monkeypatch):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)


def test_promote_copies_and_commits_a_durable_unpromoted_spec(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "1-2-title", _VALID_SPEC)
    vcs = _FakeVcs(main_subjects=("Merge acme/1-2 into main",))

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["promoted"] == ["1.2"]
    assert payload["data"]["promoted_count"] == 1
    assert payload["verdict"] == "clean"
    assert exit_code == 0

    # The Tier-3 file's own descriptive filename ("1-2-title") is preserved
    # verbatim into the tracked archive, never collapsed to a bare
    # "spec-1-2.md" -- every prior promotion in this archive used the
    # source's own title slug (live finding, first real run against this
    # repo, 2026-08-06).
    dest = _tracked_path(tmp_path, "acme", "1-2-title")
    assert dest.read_text(encoding="utf-8") == _VALID_SPEC
    assert len(vcs.commit_calls) == 1
    committed_paths, message = vcs.commit_calls[0]
    assert committed_paths == (dest,)
    assert "1 story spec" in message


def test_promote_skips_an_already_promoted_story(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "3-8", _VALID_SPEC)
    _write_tracked_spec(tmp_path, "acme", "3-8", _VALID_SPEC)
    vcs = _FakeVcs(main_subjects=("Merge acme/3-8 into main",))

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["promoted"] == []
    assert payload["data"]["already_promoted"] == ["3.8"]
    assert payload["data"]["gap_count"] == 0
    assert exit_code == 0
    assert vcs.commit_calls == []


def test_promote_reports_a_gap_for_a_merged_story_with_no_tier3_spec(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    (tmp_path / "_bmad-output" / "projects" / "acme" / "implementation-artifacts").mkdir(parents=True, exist_ok=True)
    vcs = _FakeVcs(main_subjects=("Merge acme/4.1 into main",))

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-001" in codes
    assert payload["data"]["gap_count"] == 1
    assert payload["verdict"] == "warn"
    assert exit_code == 0


def test_promote_reports_a_gap_for_an_invalid_tier3_spec_and_does_not_promote_it(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "2-3", "")  # zero-byte
    vcs = _FakeVcs(main_subjects=("Merge acme/2-3 into main",))

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-002" in codes
    assert payload["data"]["promoted"] == []
    assert exit_code == 0
    assert not _tracked_path(tmp_path, "acme", "2-3").exists()


def test_promote_never_overwrites_a_good_tracked_copy_with_a_broken_tier3_one(tmp_path, capsys, monkeypatch):
    """The already-promoted check runs BEFORE validity of the Tier-3 copy is
    even consulted -- a good tracked copy is untouched regardless of the
    Tier-3 source's own state (AD-13's own "never promoted over a GOOD
    copy")."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "1-5", "")  # zero-byte in Tier-3
    _write_tracked_spec(tmp_path, "acme", "1-5", _VALID_SPEC)  # good tracked copy
    vcs = _FakeVcs(main_subjects=("Merge acme/1-5 into main",))

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["gap_count"] == 0
    assert payload["data"]["already_promoted"] == ["1.5"]
    assert exit_code == 0
    assert _tracked_path(tmp_path, "acme", "1-5").read_text(encoding="utf-8") == _VALID_SPEC


def test_promote_treats_a_banner_topped_tracked_copy_as_already_promoted(tmp_path, capsys, monkeypatch):
    """Story 50.5/CAP-248, live incident: herald 23.1's finalize (commit
    `b0b7f3019f`) overwrote the reconciled tracked `spec-1-4` with its stale
    Tier-3 twin because the tracked copy began with a
    `<!-- Promoted from implementation-artifacts/ ... -->` banner ABOVE its
    frontmatter fence, and `is_valid_spec_text` required `text.startswith
    ("---")`. The banner-topped tracked copy must count as already-promoted
    and must never be overwritten by a stale Tier-3 candidate."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    banner_topped = "<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-04 -->\n" + _VALID_SPEC
    stale_tier3 = "---\ntitle: 'x'\nstatus: 'draft'\n---\n\nstale body\n"
    _write_tier3_spec(tmp_path, "acme", "1-4", stale_tier3)
    _write_tracked_spec(tmp_path, "acme", "1-4", banner_topped)
    vcs = _FakeVcs(main_subjects=("Merge acme/1-4 into main",))

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["promoted"] == []
    assert payload["data"]["already_promoted"] == ["1.4"]
    assert payload["data"]["gap_count"] == 0
    assert exit_code == 0
    assert vcs.commit_calls == []
    assert _tracked_path(tmp_path, "acme", "1-4").read_text(encoding="utf-8") == banner_topped


def test_promote_leaves_a_not_yet_merged_story_untouched(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "9-9", _VALID_SPEC)
    vcs = _FakeVcs(main_subjects=())  # nothing merged at all

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["promoted"] == []
    assert payload["data"]["gap_count"] == 0
    assert payload["verdict"] == "clean"
    assert exit_code == 0
    assert not _tracked_path(tmp_path, "acme", "9-9").exists()


def test_promote_falls_back_to_local_main_when_no_origin_remote(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "6-1", _VALID_SPEC)
    vcs = _FakeVcs(main_subjects=("Merge acme/6-1 into main",), origin_raises=True)

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-003" not in codes
    assert payload["data"]["promoted"] == ["6.1"]
    assert exit_code == 0


def test_promote_treats_a_push_only_route_as_durable(tmp_path, capsys, monkeypatch):
    """A story merged only on origin/main (pushed, not yet visible on the
    local main this process has checked out) is still durable per AD-29's
    "pushed to the remote" route."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "7-2", _VALID_SPEC)
    vcs = _FakeVcs(main_subjects=(), origin_subjects=("Merge acme/7-2 into main",))

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["promoted"] == ["7.2"]
    assert exit_code == 0


def test_promote_reports_hard_unevaluable_finding_when_main_read_fails(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "1-1", _VALID_SPEC)
    vcs = _FakeVcs(main_raises=True)

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-003" in codes
    assert payload["verdict"] == "unevaluable"
    assert payload["data"]["promoted"] == []
    assert exit_code == 1


def test_promote_reports_unevaluable_when_commit_paths_fails(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "8-4", _VALID_SPEC)
    vcs = _FakeVcs(main_subjects=("Merge acme/8-4 into main",), commit_raises=True)

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-003" in codes
    assert payload["verdict"] == "unevaluable"
    assert exit_code == 1


def test_promote_zero_candidates_is_a_clean_empty_run(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    (tmp_path / "_bmad-output" / "projects" / "acme" / "implementation-artifacts").mkdir(parents=True, exist_ok=True)
    vcs = _FakeVcs(main_subjects=())

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "clean"
    assert payload["data"]["promoted_count"] == 0
    assert exit_code == 0


def test_promote_with_no_active_project_reports_mrs_policy_005(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    vcs = _FakeVcs()

    exit_code = deploy_module.run_promote(_args(project=""), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-POLICY-005" in codes
    assert payload["data"]["promoted_count"] == 0
    assert exit_code == 0


def test_promote_with_a_malformed_slug_reports_mrs_policy_006_and_touches_nothing(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    vcs = _FakeVcs()

    exit_code = deploy_module.run_promote(_args(project="../escape"), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-POLICY-006" in codes
    assert payload["data"]["promoted_count"] == 0
    assert exit_code == 1
    assert not (tmp_path / "_bmad-output" / "projects").exists()


def test_promote_retries_an_orphaned_uncommitted_tracked_copy(tmp_path, capsys, monkeypatch):
    """Review finding (both reviewers): a partial-batch failure -- a prior
    run's `copy_file` succeeding into the tracked archive immediately
    before its own `commit_paths` call failed -- leaves a VALID, on-disk
    tracked copy that git itself has never actually committed. The old
    "already promoted" check trusted mere on-disk existence and would
    permanently skip re-committing it; the fix asks git via
    `path_has_uncommitted_changes` and, for a still-uncommitted copy,
    treats the candidate as NOT yet promoted so this run retries it."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "9-1", _VALID_SPEC)
    _write_tracked_spec(tmp_path, "acme", "9-1", _VALID_SPEC)  # orphaned copy, uncommitted
    dest = _tracked_path(tmp_path, "acme", "9-1")
    vcs = _FakeVcs(main_subjects=("Merge acme/9-1 into main",), dirty_paths=frozenset({dest}))

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["promoted"] == ["9.1"]
    assert payload["data"]["already_promoted"] == []
    assert exit_code == 0
    assert len(vcs.commit_calls) == 1
    committed_paths, _ = vcs.commit_calls[0]
    assert committed_paths == (dest,)


def test_promote_never_trusts_a_tracked_copy_whose_status_is_unconfirmable(tmp_path, capsys, monkeypatch):
    """When git itself cannot answer whether a tracked copy is committed
    (`path_has_uncommitted_changes` raising), the candidate must not be
    trusted as already-promoted -- fail safe, same shape as an invalid
    Tier-3 source."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "9-2", _VALID_SPEC)
    _write_tracked_spec(tmp_path, "acme", "9-2", _VALID_SPEC)
    vcs = _FakeVcs(main_subjects=("Merge acme/9-2 into main",), path_status_raises=True)

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["already_promoted"] == []
    assert payload["data"]["promoted"] == ["9.2"]
    assert exit_code == 0


def test_promote_reports_subjects_examined_and_matched(tmp_path, capsys, monkeypatch):
    """Diagnostic-only fields (review finding): distinguishes a genuinely
    clean 'nothing merged yet' from 'N commit subjects examined, none
    conformed to either recognized merge-subject pattern.'"""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    (tmp_path / "_bmad-output" / "projects" / "acme" / "implementation-artifacts").mkdir(parents=True, exist_ok=True)
    vcs = _FakeVcs(main_subjects=("fastmcp-v4", "pixi update requires-pixi"))

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["subjects_examined"] == 2
    assert payload["data"]["subjects_matched"] == 0
    assert payload["data"]["promoted_count"] == 0
    assert exit_code == 0


def test_promote_recognizes_a_real_github_merge_subject(tmp_path, capsys, monkeypatch):
    """The spec-amendment's own live regression -- a real GitHub PR-merge
    subject (never the templated form) must be recognized as durable.

    Branch prefix is `acme/`, matching `_args()`'s default `project="acme"`
    slug (2026-08-15 fix: `extract_story_key_from_github_merge_subject` is
    now scoped to `project_slug`, so a subject's branch prefix must
    actually match the project under test -- the original fixture reused
    a real `marshal/` branch against this file's generic `acme` project,
    which the new cross-project scoping correctly rejects)."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "2-3", _VALID_SPEC)
    vcs = _FakeVcs(main_subjects=("Merge pull request #269 from rxm7706/acme/2-3-frozen-surface-scope-check",))

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["promoted"] == ["2.3"]
    assert payload["data"]["subjects_examined"] == 1
    assert payload["data"]["subjects_matched"] == 1
    assert exit_code == 0


def test_promote_text_format_renders_a_summary(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "1-2", _VALID_SPEC)
    vcs = _FakeVcs(main_subjects=("Merge acme/1-2 into main",))

    exit_code = deploy_module.run_promote(_args(format="text"), vcs=vcs, fs=LocalFs())

    output = capsys.readouterr().out
    assert "deploy promote:" in output
    assert "promoted: 1" in output
    assert exit_code == 0


# =====================================================================
# Story 4.6 -- deploy idempotence and reconciliation of open intents
# (AD-6/AD-21/AD-28), ``promote``'s own ``commit_paths`` intent/outcome
# pair and pre-action reconciliation.
# =====================================================================


def test_promote_writes_an_intent_outcome_pair_around_commit_paths(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "1-2-title", _VALID_SPEC)
    vcs = _FakeVcs(main_subjects=("Merge acme/1-2 into main",))

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    assert exit_code == 0
    journal_lines = _find_land_journal_lines(tmp_path, "acme")
    intents = [line for line in journal_lines if line["kind"] == "deploy-promote-commit" and line["phase"] == "intent"]
    outcomes = [
        line for line in journal_lines if line["kind"] == "deploy-promote-commit" and line["phase"] == "outcome"
    ]
    assert len(intents) == 1
    assert intents[0]["payload"]["story_keys"] == ["1.2"]
    assert intents[0]["payload"]["action"] == "commit_paths"
    assert len(outcomes) == 1
    assert outcomes[0]["intent_id"] == intents[0]["id"]


def test_promote_merge_failure_leaves_an_open_intent_with_no_outcome(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "1-2", _VALID_SPEC)
    vcs = _FakeVcs(main_subjects=("Merge acme/1-2 into main",), commit_raises=True)

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    assert exit_code != 0
    journal_lines = _find_land_journal_lines(tmp_path, "acme")
    assert len(journal_lines) == 1
    assert journal_lines[0]["kind"] == "deploy-promote-commit"
    assert journal_lines[0]["phase"] == "intent"
    assert "intent_id" not in journal_lines[0]


def _write_open_intent(
    tmp_path,
    slug: str,
    *,
    run_id: str,
    kind: str,
    story_keys: list[str],
    counter: int = 0,
    writer_id: str = "prior-crashed-run",
) -> dict:
    """Simulate a crashed prior invocation: a lone ``intent`` entry, with no
    matching ``outcome``, in its OWN run directory -- the exact shape a
    process killed between the irreversible action succeeding and this
    process journaling its own outcome would leave behind."""
    run_dir = tmp_path / "_bmad-output" / "projects" / slug / "implementation-artifacts" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "id": {"writer_id": writer_id, "counter": counter},
        "ts": "2026-08-01T00:00:00.000Z",
        "run_id": run_id,
        "kind": kind,
        "phase": "intent",
        "payload": {"action": "prior-attempt", "story_keys": story_keys},
    }
    (run_dir / "journal.jsonl").write_text(json.dumps(entry) + "\n", encoding="utf-8")
    return entry


def test_promote_reconciles_a_prior_open_intent_when_evidence_confirms(tmp_path, capsys, monkeypatch):
    """A crashed prior `promote` left an open intent for "3.8"; THIS run's
    own live evidence (a valid, committed tracked copy already exists)
    confirms it happened -- the intent is closed with a `reconciliation`
    outcome, and "3.8" is never re-committed."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "3-8", _VALID_SPEC)
    _write_tracked_spec(tmp_path, "acme", "3-8", _VALID_SPEC)
    vcs = _FakeVcs(main_subjects=("Merge acme/3-8 into main",))
    prior_intent = _write_open_intent(
        tmp_path,
        "acme",
        run_id="prior-run-1",
        kind="deploy-promote-commit",
        story_keys=["3.8"],
    )

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-021" not in codes
    assert vcs.commit_calls == []

    journal_lines = _find_land_journal_lines(tmp_path, "acme")
    reconciliations = [line for line in journal_lines if line["phase"] == "outcome"]
    assert len(reconciliations) == 1
    assert reconciliations[0]["kind"] == "reconciliation"
    assert reconciliations[0]["intent_id"] == prior_intent["id"]


def test_promote_reports_warn_for_an_open_intent_without_evidence(tmp_path, capsys, monkeypatch):
    """A crashed prior `promote`'s open intent names "9.9" -- nothing this
    run can positively confirm happened. It stays open and is reported via
    MRS-DEPLOY-021, WARN-classified (never ERROR, never blocking, AD-21's
    F-17 amendment)."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    vcs = _FakeVcs()
    _write_open_intent(
        tmp_path,
        "acme",
        run_id="prior-run-1",
        kind="deploy-promote-commit",
        story_keys=["9.9"],
    )

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-021" in codes
    warn_finding = next(f for f in payload["findings"] if f["code"] == "MRS-DEPLOY-021")
    assert warn_finding["severity"] == "warn"
    assert payload["verdict"] == "warn"
    assert exit_code == 0


def test_promote_rerun_against_a_converged_system_is_zero_changes(tmp_path, capsys, monkeypatch):
    """NFR-7: running `promote` twice in a row against the SAME state -- the
    second run finds nothing left to promote, has no open intent to
    reconcile (the first run's own intent/outcome pair already closed
    itself within its own run), and produces zero changes at exit 0."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "1-2", _VALID_SPEC)
    vcs = _FakeVcs(main_subjects=("Merge acme/1-2 into main",))

    first_exit = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())
    capsys.readouterr()
    runs_dir = tmp_path / "_bmad-output" / "projects" / "acme" / "implementation-artifacts" / "runs"
    run_count_after_first = len(list(runs_dir.iterdir()))

    second_exit = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())
    payload = json.loads(capsys.readouterr().out)

    assert first_exit == 0
    assert second_exit == 0
    assert payload["data"]["promoted"] == []
    assert payload["data"]["already_promoted"] == ["1.2"]
    assert payload["findings"] == []
    assert len(vcs.commit_calls) == 1  # unchanged from the first run
    # A fully converged re-run mints no NEW run directory at all -- nothing
    # to reconcile (no open intent survives the first run) and nothing to
    # act on.
    assert len(list(runs_dir.iterdir())) == run_count_after_first


# =====================================================================
# ``run_promote``'s specs_dir advisory lock (Story 4.9, AD-42).
# =====================================================================


class _LockRaisingFs(LocalFs):
    """A ``FsPort`` wrapper (real ``LocalFs`` for everything else) whose
    ``acquire_advisory_lock`` always raises ``FsError`` -- proves
    ``run_promote``'s lock-contention path reports ``MRS-DEPLOY-023`` and
    performs no copy/commit, matching the story's own "clean, re-entrant
    refusal, never a hard error" contract."""

    def acquire_advisory_lock(self, path, *, timeout_s):
        raise FsError("simulated: another process holds this lock")


class _LockTrackingFs(LocalFs):
    """A ``FsPort`` wrapper (real ``LocalFs``/real ``fcntl.flock`` for the
    lock mechanics themselves) recording every acquire/release call's own
    REQUESTED path (not the ``.lock`` sibling ``AdvisoryLock.path`` holds)
    and call order in one shared list -- proves the lock is acquired on
    ``specs_dir`` itself, and (used across two sequential ``run_promote``
    calls sharing one instance) that a second run's own locked section
    never overlaps the first's."""

    def __init__(self) -> None:
        super().__init__()
        self.events: list[tuple[str, Path]] = []
        self.acquire_calls = 0
        self.release_calls = 0
        self._requested_path_by_lock_id: dict[int, Path] = {}

    def acquire_advisory_lock(self, path, *, timeout_s):
        self.acquire_calls += 1
        lock = super().acquire_advisory_lock(path, timeout_s=timeout_s)
        self._requested_path_by_lock_id[id(lock)] = path
        self.events.append(("acquire", path))
        return lock

    def release_advisory_lock(self, lock) -> None:
        self.release_calls += 1
        requested_path = self._requested_path_by_lock_id.pop(id(lock), lock.path)
        self.events.append(("release", requested_path))
        super().release_advisory_lock(lock)


def _specs_dir(tmp_path: Path, slug: str) -> Path:
    return tmp_path / "_bmad-output" / "projects" / slug / "planning-artifacts" / "specs"


def test_promote_reports_warn_and_promotes_nothing_when_the_lock_is_contended(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "1-2-title", _VALID_SPEC)
    vcs = _FakeVcs(main_subjects=("Merge acme/1-2 into main",))

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=_LockRaisingFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-023" in codes
    assert payload["data"]["lock_contended"] is True
    assert payload["data"]["promoted"] == []
    assert payload["data"]["promoted_count"] == 0
    assert payload["verdict"] == "warn"
    assert exit_code == 0  # WARN never fails the exit code, same tier as MRS-DEPLOY-021/022
    assert vcs.commit_calls == []
    assert not _tracked_path(tmp_path, "acme", "1-2-title").exists()


def test_promote_with_nothing_to_promote_never_acquires_the_lock(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    vcs = _FakeVcs()  # no durable merges at all -- plan.to_promote is empty
    fs = _LockTrackingFs()

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=fs)

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["promoted"] == []
    assert payload["data"]["lock_contended"] is False
    assert fs.acquire_calls == 0
    assert fs.release_calls == 0
    assert exit_code == 0


def test_promote_acquires_and_releases_the_lock_on_specs_dir_around_copy_and_commit(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "1-2-title", _VALID_SPEC)
    vcs = _FakeVcs(main_subjects=("Merge acme/1-2 into main",))
    fs = _LockTrackingFs()

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=fs)

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["promoted"] == ["1.2"]
    assert payload["data"]["lock_contended"] is False
    assert exit_code == 0
    assert fs.acquire_calls == 1
    assert fs.release_calls == 1
    assert fs.events == [
        ("acquire", _specs_dir(tmp_path, "acme")),
        ("release", _specs_dir(tmp_path, "acme")),
    ]


def test_promote_hits_the_real_contention_path_when_another_holder_has_the_lock(tmp_path, capsys, monkeypatch):
    """Code review (2026-08-06, Edge Case Hunter): the other lock tests
    either mock ``acquire_advisory_lock`` outright or never actually
    contend (the ``_LockTrackingFs`` sequential test's second run has
    nothing left to promote, so it never re-enters the locked section at
    all) -- neither exercises ``run_promote``'s real try/except/else/
    finally wiring against a GENUINE, real ``fcntl.flock`` held by another
    holder. Here a background thread acquires the real lock on ``specs_dir``
    via its OWN ``LocalFs`` instance (a second, independent open-file
    descriptor -- ``fcntl.flock`` treats this as a distinct holder even
    within one process, exactly like two separate OS processes) and holds
    it past `run_promote`'s own (monkeypatched short) timeout, proving the
    foreground call takes the real ``MRS-DEPLOY-023`` contention path
    against ACTUAL lock contention, not a simulated one."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(deploy_module, "_PROMOTE_LOCK_TIMEOUT_S", 0.3)
    _write_tier3_spec(tmp_path, "acme", "1-2-title", _VALID_SPEC)
    vcs = _FakeVcs(main_subjects=("Merge acme/1-2 into main",))
    specs_dir = _specs_dir(tmp_path, "acme")

    holder_fs = LocalFs()
    release_event = threading.Event()
    held_event = threading.Event()

    def _hold_lock():
        lock = holder_fs.acquire_advisory_lock(specs_dir, timeout_s=5.0)
        held_event.set()
        release_event.wait(timeout=5.0)
        holder_fs.release_advisory_lock(lock)

    holder = threading.Thread(target=_hold_lock, daemon=True)
    holder.start()
    try:
        assert held_event.wait(timeout=5.0), "background holder never acquired the real lock"

        exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())
    finally:
        release_event.set()
        holder.join(timeout=5.0)

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-023" in codes
    assert payload["data"]["lock_contended"] is True
    assert payload["data"]["promoted"] == []
    assert exit_code == 0
    assert vcs.commit_calls == []


def test_promote_sequential_runs_for_the_same_project_never_overlap_the_locked_section(tmp_path, capsys, monkeypatch):
    """Two sequential ``run_promote`` invocations for the SAME project,
    sharing one lock-tracking ``FsPort`` -- proves the second run's own
    re-scan sees the first run's already-committed promotion (never a
    duplicate copy/commit) and that the first run's own acquire/release
    pair fully completes before anything from the second run is attempted
    (the second run has nothing left to promote, so it never even
    re-enters the locked section -- the strongest possible proof the two
    runs' write sections never overlap)."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "1-2-title", _VALID_SPEC)
    vcs = _FakeVcs(main_subjects=("Merge acme/1-2 into main",))
    fs = _LockTrackingFs()

    first_exit = deploy_module.run_promote(_args(), vcs=vcs, fs=fs)
    first_payload = json.loads(capsys.readouterr().out)

    second_exit = deploy_module.run_promote(_args(), vcs=vcs, fs=fs)
    second_payload = json.loads(capsys.readouterr().out)

    assert first_exit == 0
    assert second_exit == 0
    assert first_payload["data"]["promoted"] == ["1.2"]
    assert second_payload["data"]["promoted"] == []
    assert second_payload["data"]["already_promoted"] == ["1.2"]
    assert len(vcs.commit_calls) == 1  # never promoted twice
    assert fs.events == [
        ("acquire", _specs_dir(tmp_path, "acme")),
        ("release", _specs_dir(tmp_path, "acme")),
    ]


# =====================================================================
# ``unreachable_promotions_for_slug`` (Story 4.2).
# =====================================================================


def test_unreachable_promotions_for_slug_names_durable_unpromoted_and_missing_spec(
    tmp_path,
):
    """All three cases (code review, 2026-08-06, P3, widened the story's
    original Always bullet): durable-but-unpromoted (a valid Tier-3 spec
    exists, ``plan.to_promote``), durable-with-no-spec-at-all
    (``plan.missing_spec_keys``), AND durable-with-a-corrupt-spec
    (``plan.invalid_spec_keys``, MRS-DEPLOY-002) -- a truncated paper trail
    is at least as concerning as a missing one, so it is no longer
    excluded."""
    _write_tier3_spec(tmp_path, "acme", "1-2", _VALID_SPEC)  # unpromoted, valid
    _write_tier3_spec(tmp_path, "acme", "1-4", "")  # exists but invalid -- included (P3)
    vcs = _FakeVcs(
        main_subjects=(
            "Merge acme/1-2 into main",
            "Merge acme/1-3 into main",  # no Tier-3 spec at all -- missing
            "Merge acme/1-4 into main",
        )
    )

    keys = deploy_module.unreachable_promotions_for_slug(tmp_path, "acme", vcs=vcs, fs=LocalFs())

    assert set(str(key) for key in keys) == {"1.2", "1.3", "1.4"}


def test_unreachable_promotions_for_slug_includes_invalid_spec_keys(tmp_path):
    """Dedicated P3 regression: a durable story whose Tier-3 spec is
    truncated/zero-byte (MRS-DEPLOY-002) is included in the unreachable
    set -- a corrupt paper trail is not exempted from the refusal gate the
    way a broken-but-unmerged spec is."""
    _write_tier3_spec(tmp_path, "acme", "9-1", "")  # zero-byte -- invalid
    vcs = _FakeVcs(main_subjects=("Merge acme/9-1 into main",))

    keys = deploy_module.unreachable_promotions_for_slug(tmp_path, "acme", vcs=vcs, fs=LocalFs())

    assert set(str(key) for key in keys) == {"9.1"}


def test_unreachable_promotions_for_slug_excludes_already_promoted(tmp_path):
    _write_tier3_spec(tmp_path, "acme", "3-8", _VALID_SPEC)
    _write_tracked_spec(tmp_path, "acme", "3-8", _VALID_SPEC)
    vcs = _FakeVcs(main_subjects=("Merge acme/3-8 into main",))

    keys = deploy_module.unreachable_promotions_for_slug(tmp_path, "acme", vcs=vcs, fs=LocalFs())

    assert keys == ()


def test_unreachable_promotions_for_slug_empty_for_malformed_slug(tmp_path):
    vcs = _FakeVcs()
    keys = deploy_module.unreachable_promotions_for_slug(tmp_path, "../evil", vcs=vcs, fs=LocalFs())
    assert keys == ()


def test_unreachable_promotions_for_slug_returns_none_when_main_history_unreadable(tmp_path):
    """Code review, 2026-08-06, P1 (both reviewers' independent top
    finding): undeterminable durability now returns ``None`` -- UNDETERMINED
    -- never the same ``()`` a genuinely clean scan reports. The caller
    (``cli/init.py::run_teardown``) must be able to tell the two apart to
    avoid silently proceeding on an unevaluated safety check."""
    vcs = _FakeVcs(main_raises=True)
    keys = deploy_module.unreachable_promotions_for_slug(tmp_path, "acme", vcs=vcs, fs=LocalFs())
    assert keys is None


def test_unreachable_promotions_for_slug_is_computed_fresh_not_cached(tmp_path):
    """No caching anywhere (the story's own Never bullet): two calls with
    DIFFERENT git state produce different answers."""
    vcs = _FakeVcs(main_subjects=("Merge acme/6-1 into main",))
    first = deploy_module.unreachable_promotions_for_slug(tmp_path, "acme", vcs=vcs, fs=LocalFs())
    assert set(str(key) for key in first) == {"6.1"}

    _write_tier3_spec(tmp_path, "acme", "6-1", _VALID_SPEC)
    second = deploy_module.unreachable_promotions_for_slug(tmp_path, "acme", vcs=vcs, fs=LocalFs())
    assert set(str(key) for key in second) == {"6.1"}  # still unreachable: unpromoted now


# =====================================================================
# ``marshal deploy recover-spec`` (Story 4.2).
# =====================================================================


def _recover_args(*, slug: str = "acme", key: str = "4.2", format: str = "json") -> argparse.Namespace:
    return argparse.Namespace(slug=slug, key=key, format=format)


def _write_run_snapshot(tmp_path, slug: str, run_id: str, filename_key: str, text: str) -> Path:
    run_dir = tmp_path / "_bmad-output" / "projects" / slug / "implementation-artifacts" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / f"spec-{filename_key}.md"
    path.write_text(text, encoding="utf-8")
    return path


_EPICS_MD = """## Epic 4: Landing with a durable paper trail

### Story 4.1: Story-spec promotion with a durability predicate

As the operator,
I want every merged story's spec promoted automatically,
So that promoted means durable.

**Type:** feature • **Effort:** L

**Acceptance Criteria:**

**Given** a merged story
**Then** it is promoted

### Story 4.2: Teardown reachability and spec-recovery assistance

As the operator,
I want teardown to compute durability at teardown time and to help me when a spec is missing,
So that a stale flag can never authorize destroying the last copy.

**Type:** feature • **Effort:** M

**Acceptance Criteria:**

**Given** a loop home with merged stories
**Then** the refusal predicate is reachability computed at teardown time

### Story 4.3: Merge-subject conformance and review-cap landing

As the operator,
I want more landing rules,
So that landing is safe.
"""


def test_recover_spec_reports_snapshots_most_recent_first_and_writes_nothing(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    older = _write_run_snapshot(tmp_path, "acme", "run-a", "4-2", "old snapshot")
    newer = _write_run_snapshot(tmp_path, "acme", "run-b", "4-2-title", "new snapshot")
    import os as os_module
    import time

    old_time = time.time() - 1000
    os_module.utime(older, (old_time, old_time))

    exit_code = deploy_module.run_recover_spec(_recover_args(), fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    paths = [entry["path"] for entry in payload["data"]["snapshots"]]
    assert paths == [str(newer), str(older)]
    assert "recovered" not in payload["data"]
    assert "recovered_path" not in payload["data"]


def test_recover_spec_falls_back_to_epics_derived_regeneration(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    epics_path = tmp_path / "_bmad-output" / "projects" / "acme" / "planning-artifacts" / "epics.md"
    epics_path.parent.mkdir(parents=True, exist_ok=True)
    epics_path.write_text(_EPICS_MD, encoding="utf-8")

    exit_code = deploy_module.run_recover_spec(_recover_args(), fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["data"]["snapshots"] == []
    assert payload["data"]["recovered"] is True
    dest = Path(payload["data"]["recovered_path"])
    content = dest.read_text(encoding="utf-8")
    assert "recovery_source: 'epics-derived-contract-only'" in content
    assert "status: 'draft'" in content
    assert "I want teardown to compute durability at teardown time" in content
    assert "the refusal predicate is reachability computed at teardown time" in content
    # Never claims to be more than a reduced contract-only spec.
    assert "## Code Map" not in content
    assert "## Design Notes" not in content


def test_recover_spec_never_overwrites_an_existing_recovered_file(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    dest = tmp_path / "_bmad-output" / "projects" / "acme" / "implementation-artifacts" / "spec-4-2-recovered.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("PRE-EXISTING", encoding="utf-8")

    exit_code = deploy_module.run_recover_spec(_recover_args(), fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["data"]["already_present"] is True
    assert dest.read_text(encoding="utf-8") == "PRE-EXISTING"


def test_recover_spec_reports_orphaned_key_when_nothing_found(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)

    exit_code = deploy_module.run_recover_spec(_recover_args(key="9.9"), fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-004" in codes
    assert payload["verdict"] == "warn"
    assert exit_code == 0
    assert "recovered" not in payload["data"]


def test_recover_spec_malformed_key_reports_mrs_ident_001(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)

    exit_code = deploy_module.run_recover_spec(_recover_args(key="not-a-key"), fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-IDENT-001" in codes
    assert exit_code != 0


def test_recover_spec_malformed_slug_reports_mrs_policy_006(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)

    exit_code = deploy_module.run_recover_spec(_recover_args(slug="../evil"), fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-POLICY-006" in codes
    assert exit_code != 0


def test_recover_spec_snapshot_search_does_not_match_a_numeric_prefix_collision(tmp_path, capsys, monkeypatch):
    """Code review, 2026-08-06, P4 (both reviewers): a lookup for key 1.2
    must not match ``spec-1-20-*.md`` -- a DIFFERENT key that merely shares
    "1-2" as a numeric PREFIX. The glob needs a boundary immediately after
    the key's own digits (a title separator "-" or end-of-name), never
    trusting an unanchored ``*`` alone."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_run_snapshot(tmp_path, "acme", "run-a", "1-20-unrelated-story", "decoy")

    exit_code = deploy_module.run_recover_spec(_recover_args(key="1.2"), fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["data"]["snapshots"] == []


_EPICS_MD_EMPTY_AC = """### Story 7.7: Sparse story

As the operator,
I want something,
So that something happens.

**Type:** feature • **Effort:** S

**Acceptance Criteria:**

"""


def test_recover_spec_warns_when_acceptance_criteria_comes_back_empty(tmp_path, capsys, monkeypatch):
    """Code review, 2026-08-06, P5 (Edge Case Hunter): an epics.md section
    whose Acceptance Criteria block is empty after parsing still writes the
    recovered file (this command "reports, never fabricates" -- an empty
    section is itself reported, not silently hidden) but must ALSO warn
    that the recovery is likely hollow, rather than reporting
    ``recovered: true`` with no caveat."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    epics_path = tmp_path / "_bmad-output" / "projects" / "acme" / "planning-artifacts" / "epics.md"
    epics_path.parent.mkdir(parents=True, exist_ok=True)
    epics_path.write_text(_EPICS_MD_EMPTY_AC, encoding="utf-8")

    exit_code = deploy_module.run_recover_spec(_recover_args(key="7.7"), fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["recovered"] is True
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-005" in codes
    assert payload["verdict"] == "warn"
    assert exit_code == 0
    dest = Path(payload["data"]["recovered_path"])
    assert dest.exists()


# =====================================================================
# ``marshal deploy land-story`` (Story 4.3, FR-27/AD-24/AD-34).
# =====================================================================

from pyforge.marshal.cli import gate as gate_module  # noqa: E402
from pyforge.marshal.core.identity import normalize, render_merge_subject  # noqa: E402
from pyforge.marshal.core.model import Verdict, build_envelope  # noqa: E402
from pyforge.marshal.core.policy import DEFAULT_POLICY  # noqa: E402

#: Story 50.4/FR-191 CAP-247: the repo default now carries a `{slug}`
#: placeholder ("Merge {slug}/{key} into main") -- every fixture below that
#: represents a conforming, already-rendered merge subject for the "acme"
#: project must include the "acme/" segment to still classify.
_DEFAULT_MERGE_SUBJECT_TEMPLATE = str(DEFAULT_POLICY["merge_subject_template"])


def _land_args(
    *,
    slug: str = "acme",
    key: str = "4.3",
    justification: str | None = "landed manually, review did not converge",
    since: str | None = None,
    format: str = "json",
) -> argparse.Namespace:
    return argparse.Namespace(slug=slug, key=key, justification=justification, since=since, format=format)


def _fake_evaluate_gate(*, verdict: Verdict, findings: tuple = ()):
    def _evaluate(args, *, process, vcs, fs):
        return build_envelope(
            command="gate evaluate",
            verdict=verdict,
            data={"scope": "policy-seed-only"},
            findings=findings,
        )

    return _evaluate


def _must_not_be_called(*_args, **_kwargs):
    raise AssertionError("evaluate_gate must not be called")


def _find_land_journal_lines(tmp_path: Path, slug: str) -> list[dict]:
    runs_dir = tmp_path / "_bmad-output" / "projects" / slug / "implementation-artifacts" / "runs"
    lines: list[dict] = []
    for journal_path in sorted(runs_dir.glob("*/journal.jsonl")):
        for raw in journal_path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                lines.append(json.loads(raw))
    return lines


def test_land_story_refuses_missing_justification_before_any_gate_run(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(gate_module, "evaluate_gate", _must_not_be_called)
    vcs = _FakeVcs()

    exit_code = deploy_module.run_land_story(_land_args(justification=None), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-006" in codes
    assert payload["verdict"] == "unevaluable"
    assert exit_code != 0
    assert vcs.merge_branch_calls == []


def test_land_story_refuses_empty_justification(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(gate_module, "evaluate_gate", _must_not_be_called)
    vcs = _FakeVcs()

    exit_code = deploy_module.run_land_story(_land_args(justification="   "), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-006" in codes
    assert exit_code != 0


def test_land_story_refuses_when_the_station_branch_does_not_exist(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(gate_module, "evaluate_gate", _must_not_be_called)
    vcs = _FakeVcs(existing_branches=frozenset())

    exit_code = deploy_module.run_land_story(_land_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-007" in codes
    assert exit_code != 0
    assert vcs.merge_branch_calls == []


def test_land_story_refuses_when_gate_is_not_green(tmp_path, capsys, monkeypatch):
    """A gate-failed verdict must refuse the landing before any merge --
    no journal entry, no merge -- and the gate's own finding (naming which
    half failed) must be visible in this command's own report."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    gate_finding = {
        "code": "MRS-GATE-001",
        "severity": "error",
        "message": "verify command 'pytest -q' failed",
    }
    from pyforge.marshal.core.model import Finding, Severity

    monkeypatch.setattr(
        gate_module,
        "evaluate_gate",
        _fake_evaluate_gate(
            verdict=Verdict.GATE_FAILED,
            findings=(Finding(code="MRS-GATE-001", severity=Severity.ERROR, message=gate_finding["message"]),),
        ),
    )
    vcs = _FakeVcs(existing_branches=frozenset({"loop/acme"}))

    exit_code = deploy_module.run_land_story(_land_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-GATE-001" in codes
    assert payload["data"]["gate_verdict"] == "gate-failed"
    assert "merge_sha" not in payload["data"]
    assert exit_code != 0
    assert vcs.merge_branch_calls == []
    assert _find_land_journal_lines(tmp_path, "acme") == []


def test_land_story_merges_with_a_rendered_subject_and_journals_on_green(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(gate_module, "evaluate_gate", _fake_evaluate_gate(verdict=Verdict.CLEAN))
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        merge_base_sha="base-sha-123",
        merge_branch_sha="merge-sha-456",
        window_subjects=("Merge acme/4.3 into main",),
    )

    exit_code = deploy_module.run_land_story(_land_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["verdict"] == "clean"
    expected_subject = render_merge_subject(normalize("4.3"), _DEFAULT_MERGE_SUBJECT_TEMPLATE, "acme")
    assert payload["data"]["subject"] == expected_subject
    assert payload["data"]["merge_sha"] == "merge-sha-456"
    assert payload["data"]["non_conforming_merges"] == []
    # merge_branch is handed branch's CAPTURED tip sha (P4), not the bare
    # branch name -- see `resolve_ref`'s default return above.
    assert vcs.merge_branch_calls == [("branch-tip-sha", "main", expected_subject)]

    # Story 4.6: `land-story` now also journals an intent/outcome pair
    # around `merge_branch` itself (AD-6), alongside the pre-existing
    # manual-landing observation entry -- three lines total, not one.
    journal_lines = _find_land_journal_lines(tmp_path, "acme")
    assert len(journal_lines) == 3
    observations = [line for line in journal_lines if line["phase"] == "observation"]
    assert len(observations) == 1
    payload_entry = observations[0]["payload"]
    assert payload_entry["story_key"] == "4.3"
    assert payload_entry["merge_sha"] == "merge-sha-456"
    assert payload_entry["gate_verdict"] == "clean"
    assert "landed manually" in payload_entry["justification"]
    assert observations[0]["kind"] == "manual-landing"

    merge_intents = [
        line for line in journal_lines if line["kind"] == "deploy-land-story-merge" and line["phase"] == "intent"
    ]
    merge_outcomes = [
        line for line in journal_lines if line["kind"] == "deploy-land-story-merge" and line["phase"] == "outcome"
    ]
    assert len(merge_intents) == 1
    assert merge_intents[0]["payload"]["story_keys"] == ["4.3"]
    assert merge_intents[0]["payload"]["action"] == "merge_branch"
    assert len(merge_outcomes) == 1
    assert merge_outcomes[0]["intent_id"] == merge_intents[0]["id"]
    assert merge_outcomes[0]["payload"]["merge_sha"] == "merge-sha-456"


def test_land_story_reports_non_conforming_merges_without_blocking(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(gate_module, "evaluate_gate", _fake_evaluate_gate(verdict=Verdict.CLEAN))
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        window_subjects=("Merge acme/4.3 into main", "Merge pull request #42 from acme/feature"),
    )

    exit_code = deploy_module.run_land_story(_land_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["verdict"] == "clean"
    assert payload["data"]["non_conforming_merges"] == ["Merge pull request #42 from acme/feature"]
    assert payload["findings"] == []


def test_land_story_conformance_audit_read_failure_warns_but_does_not_block(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(gate_module, "evaluate_gate", _fake_evaluate_gate(verdict=Verdict.CLEAN))
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        window_subjects_raises=True,
    )

    exit_code = deploy_module.run_land_story(_land_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-009" in codes
    assert payload["verdict"] == "warn"
    assert exit_code == 0
    assert payload["data"]["non_conforming_merges"] is None
    # The merge and its journal entry already happened -- an audit gap must
    # never undo it.
    assert vcs.merge_branch_calls != []
    assert _find_land_journal_lines(tmp_path, "acme") != []


def test_land_story_merge_failure_leaves_an_open_intent_with_no_outcome(tmp_path, capsys, monkeypatch):
    """Story 4.6 (AD-6): the intent is written BEFORE `merge_branch` is
    even attempted, so a merge failure leaves exactly ONE journal line --
    the open intent, with no outcome and no manual-landing observation
    (the landing itself never happened). This used to assert NO journal
    entry at all; that was the exact AD-6 gap Story 4.6 exists to close --
    see the story's own Spec Change Log for why this assertion changed."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(gate_module, "evaluate_gate", _fake_evaluate_gate(verdict=Verdict.CLEAN))
    vcs = _FakeVcs(existing_branches=frozenset({"loop/acme"}), merge_branch_raises=True)

    exit_code = deploy_module.run_land_story(_land_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-008" in codes
    assert exit_code != 0
    assert "merge_sha" not in payload["data"]
    journal_lines = _find_land_journal_lines(tmp_path, "acme")
    assert len(journal_lines) == 1
    assert journal_lines[0]["kind"] == "deploy-land-story-merge"
    assert journal_lines[0]["phase"] == "intent"
    assert "intent_id" not in journal_lines[0]


def test_land_story_uses_an_explicit_since_ref_over_the_computed_merge_base(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(gate_module, "evaluate_gate", _fake_evaluate_gate(verdict=Verdict.CLEAN))

    class _RecordingVcs(_FakeVcs):
        def commit_subjects(self, repo_root, ref):
            self.last_ref = ref
            return super().commit_subjects(repo_root, ref)

    vcs = _RecordingVcs(existing_branches=frozenset({"loop/acme"}))

    exit_code = deploy_module.run_land_story(_land_args(since="explicit-ref"), vcs=vcs, fs=LocalFs())

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["since"] == "explicit-ref"
    assert vcs.last_ref == f"explicit-ref..{vcs.merge_branch_sha}"


# --- Code review (2026-08-06): P2/P3/P4/P6/P7 --------------------------


def test_land_story_refuses_a_warn_tier_gate_not_exactly_clean(tmp_path, capsys, monkeypatch):
    """P2 (Blind Hunter): `status_for` treats `warn` as 'ok', but FR-27
    requires a fully clean gate before a manual landing -- a warn-tier
    result (real findings exist, just non-blocking) must refuse, not merge."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    from pyforge.marshal.core.model import Finding, Severity

    monkeypatch.setattr(
        gate_module,
        "evaluate_gate",
        _fake_evaluate_gate(
            verdict=Verdict.WARN,
            findings=(
                Finding(
                    code="MRS-GATE-004",
                    severity=Severity.WARN,
                    message="no verify commands configured",
                ),
            ),
        ),
    )
    vcs = _FakeVcs(existing_branches=frozenset({"loop/acme"}))

    exit_code = deploy_module.run_land_story(_land_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-010" in codes
    assert payload["verdict"] != "clean"
    assert exit_code != 0
    assert vcs.merge_branch_calls == []
    assert _find_land_journal_lines(tmp_path, "acme") == []


def test_land_story_policy_read_failure_is_a_hard_stop_no_merge_attempted(tmp_path, capsys, monkeypatch):
    """P3 (both reviewers independently): a `PolicyIOError` resolving the
    merge-subject template must refuse the landing outright -- never fall
    through and merge with a silently-defaulted template (AD-24)."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(gate_module, "evaluate_gate", _must_not_be_called)
    fake_policy_path = tmp_path / "fake-marshal-policy.toml"
    fake_policy_path.write_text("not used -- _read_project_policy is patched", encoding="utf-8")
    monkeypatch.setattr(deploy_module, "conventional_project_policy_path", lambda slug: fake_policy_path)

    def _raise_policy_io_error(path):
        raise deploy_module.PolicyIOError(f"malformed policy TOML at {path}")

    monkeypatch.setattr(deploy_module, "_read_project_policy", _raise_policy_io_error)
    vcs = _FakeVcs(existing_branches=frozenset({"loop/acme"}))

    exit_code = deploy_module.run_land_story(_land_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-POLICY-004" in codes
    assert exit_code != 0
    assert vcs.merge_branch_calls == []
    assert _find_land_journal_lines(tmp_path, "acme") == []


def test_land_story_already_merged_is_a_clean_noop(tmp_path, capsys, monkeypatch):
    """P6: reuses Story 4.1's own durability-detection machinery
    (`core.promotion.merged_story_keys`) -- re-running `land-story` on an
    already-durably-merged key must be a clean no-op: no gate run, no
    merge attempt, no spurious empty merge commit, no duplicate journal
    entry."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(gate_module, "evaluate_gate", _must_not_be_called)
    already_landed_subject = render_merge_subject(normalize("4.3"), _DEFAULT_MERGE_SUBJECT_TEMPLATE, "acme")
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        main_subjects=(already_landed_subject,),
    )

    exit_code = deploy_module.run_land_story(_land_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["verdict"] == "clean"
    assert payload["data"]["already_merged"] is True
    assert vcs.merge_branch_calls == []
    assert _find_land_journal_lines(tmp_path, "acme") == []


def test_land_story_refuses_when_branch_moves_during_the_gate_window(tmp_path, capsys, monkeypatch):
    """P4: the gate evaluates `branch` at one point in time; a commit
    landing on `branch` before the merge actually runs must not be merged
    as if the (now-stale) gate result still applied to it."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(gate_module, "evaluate_gate", _fake_evaluate_gate(verdict=Verdict.CLEAN))
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        resolve_ref_sequence=["tip-at-gate-time", "tip-after-a-new-commit"],
    )

    exit_code = deploy_module.run_land_story(_land_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-011" in codes
    assert exit_code != 0
    assert vcs.merge_branch_calls == []
    assert _find_land_journal_lines(tmp_path, "acme") == []


def test_land_story_redaction_failure_warns_but_still_lands(tmp_path, capsys, monkeypatch):
    """P7 (both reviewers independently): a `--justification` redaction
    failure must register a visible WARN finding, not silently write
    `null` into the permanent journal record with no trace of the gap.
    The landing itself still proceeds -- this is a visibility fix only."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(gate_module, "evaluate_gate", _fake_evaluate_gate(verdict=Verdict.CLEAN))
    monkeypatch.setattr(deploy_module, "_land_redact_text", lambda text: None)
    vcs = _FakeVcs(existing_branches=frozenset({"loop/acme"}))

    exit_code = deploy_module.run_land_story(_land_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-012" in codes
    assert payload["verdict"] == "warn"
    assert exit_code == 0
    assert "merge_sha" in payload["data"]
    # Story 4.6: three lines total (merge intent + outcome, plus the
    # pre-existing manual-landing observation) -- not one.
    journal_lines = _find_land_journal_lines(tmp_path, "acme")
    assert len(journal_lines) == 3
    observations = [line for line in journal_lines if line["phase"] == "observation"]
    assert len(observations) == 1
    assert observations[0]["payload"]["justification"] is None


# =====================================================================
# Story 4.6 -- deploy idempotence and reconciliation of open intents
# (AD-6/AD-21/AD-28), ``land-story``'s own ``merge_branch`` intent/outcome
# pair and pre-action reconciliation.
# =====================================================================


def test_land_story_reconciles_a_prior_open_intent_when_evidence_confirms(tmp_path, capsys, monkeypatch):
    """A crashed prior `land-story` left an open intent for "4.3"; THIS
    run's own live evidence (the key is now reachable in main's own commit
    history) confirms it happened -- the intent is closed with a
    `reconciliation` outcome, and the already-merged short-circuit takes
    over (no fresh merge attempt)."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(gate_module, "evaluate_gate", _must_not_be_called)
    already_landed_subject = render_merge_subject(normalize("4.3"), _DEFAULT_MERGE_SUBJECT_TEMPLATE, "acme")
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        main_subjects=(already_landed_subject,),
    )
    prior_intent = _write_open_intent(
        tmp_path,
        "acme",
        run_id="prior-run-1",
        kind="deploy-land-story-merge",
        story_keys=["4.3"],
    )

    exit_code = deploy_module.run_land_story(_land_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["data"]["already_merged"] is True
    assert vcs.merge_branch_calls == []
    journal_lines = _find_land_journal_lines(tmp_path, "acme")
    reconciliations = [line for line in journal_lines if line["phase"] == "outcome"]
    assert len(reconciliations) == 1
    assert reconciliations[0]["kind"] == "reconciliation"
    assert reconciliations[0]["intent_id"] == prior_intent["id"]


def test_land_story_reports_warn_for_an_open_intent_without_evidence(tmp_path, capsys, monkeypatch):
    """A crashed prior `land-story`'s open intent names a DIFFERENT key
    ("9.9") than the one this run is landing -- nothing confirms it. It
    stays open and is reported via MRS-DEPLOY-021 (WARN, never blocking),
    and this run's own landing of "4.3" proceeds normally."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(gate_module, "evaluate_gate", _fake_evaluate_gate(verdict=Verdict.CLEAN))
    vcs = _FakeVcs(existing_branches=frozenset({"loop/acme"}))
    _write_open_intent(
        tmp_path,
        "acme",
        run_id="prior-run-1",
        kind="deploy-land-story-merge",
        story_keys=["9.9"],
    )

    exit_code = deploy_module.run_land_story(_land_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-021" in codes
    assert payload["verdict"] == "warn"
    assert exit_code == 0
    assert vcs.merge_branch_calls != []


def test_land_story_rerun_against_a_converged_system_is_zero_changes(tmp_path, capsys, monkeypatch):
    """NFR-7: `land-story` on an already-merged key is already established
    (P6) as a clean no-op; this proves it stays that way with zero NEW
    journal entries once the first landing's own intent/outcome pair has
    already closed itself."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(gate_module, "evaluate_gate", _fake_evaluate_gate(verdict=Verdict.CLEAN))
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        merge_base_sha="base-sha-123",
        merge_branch_sha="merge-sha-456",
        window_subjects=("Merge acme/4.3 into main",),
    )
    first_exit = deploy_module.run_land_story(_land_args(), vcs=vcs, fs=LocalFs())
    capsys.readouterr()
    journal_lines_after_first = _find_land_journal_lines(tmp_path, "acme")

    # The second run's own `_FakeVcs.commit_subjects("main", ...)` must now
    # report the story as merged for the already-merged short-circuit to
    # fire -- exactly what a REAL git repo would show after a real merge.
    landed_subject = render_merge_subject(normalize("4.3"), _DEFAULT_MERGE_SUBJECT_TEMPLATE, "acme")
    vcs.main_subjects = (landed_subject,)

    second_exit = deploy_module.run_land_story(_land_args(), vcs=vcs, fs=LocalFs())
    payload = json.loads(capsys.readouterr().out)

    assert first_exit == 0
    assert second_exit == 0
    assert payload["data"]["already_merged"] is True
    assert len(vcs.merge_branch_calls) == 1  # unchanged from the first run
    assert payload["findings"] == []
    # No open intent survived the first (successful) run, so the second
    # run's own reconciliation pass finds nothing and writes nothing new.
    assert _find_land_journal_lines(tmp_path, "acme") == journal_lines_after_first


# =====================================================================
# ``marshal deploy batch-pr`` (Story 4.4, FR-29/NFR-2, AD-34).
# =====================================================================

from pyforge.marshal.ports.forge import ForgeCommandError, PrInfo  # noqa: E402

_BMADLOOP_WAVE_SUBJECT = "Merge bmad-loop/run-1/4-4-batch into loop/acme (bmad-loop)"


class _FakeForge:
    """A minimal ``ForgePort`` stand-in -- records every call for
    assertion, mirrors ``_FakeVcs``'s own configurable-raise shape."""

    def __init__(
        self,
        *,
        existing: PrInfo | None = None,
        create_result: PrInfo | None = None,
        update_result: PrInfo | None = None,
        find_raises: bool = False,
        create_raises: bool = False,
        update_raises: bool = False,
        add_labels_raises: bool = False,
        check_status_map: dict[str, str | None] | None = None,
        check_status_raises: bool = False,
    ) -> None:
        self.existing = existing
        self.create_result = create_result or PrInfo(number=1, url="https://example/pr/1", state="open", base="main")
        self.update_result = update_result or PrInfo(number=2, url="https://example/pr/2", state="open", base="main")
        self.find_raises = find_raises
        self.create_raises = create_raises
        self.update_raises = update_raises
        self.add_labels_raises = add_labels_raises
        self.check_status_map = check_status_map or {}
        self.check_status_raises = check_status_raises
        self.find_calls: list = []
        self.create_calls: list = []
        self.update_calls: list = []
        self.add_labels_calls: list = []
        self.check_calls: list = []

    def find_open_pr(self, repo, head_branch):
        self.find_calls.append((repo, head_branch))
        if self.find_raises:
            raise ForgeCommandError("gh pr list failed")
        return self.existing

    def create_pr(self, repo, base, head, title, body):
        if self.create_raises:
            raise ForgeCommandError("gh pr create failed")
        self.create_calls.append((repo, base, head, title, body))
        return self.create_result

    def update_pr(self, repo, number, title, body):
        if self.update_raises:
            raise ForgeCommandError("gh pr edit failed")
        self.update_calls.append((repo, number, title, body))
        return self.update_result

    def add_labels(self, repo, number, labels):
        self.add_labels_calls.append((repo, number, labels))
        if self.add_labels_raises:
            raise ForgeCommandError("gh pr edit --add-label failed")

    def check_run_status(self, repo, ref, check_name):
        self.check_calls.append((repo.value, ref.value, check_name.value))
        if self.check_status_raises:
            raise ForgeCommandError("gh api check-runs failed")
        return self.check_status_map.get(check_name.value)


def _batch_pr_args(*, slug: str = "acme", format: str = "json") -> argparse.Namespace:
    return argparse.Namespace(slug=slug, format=format)


def _write_batch_pr_project_policy(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "batch-pr-marshal-policy.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_batch_pr_refuses_when_the_station_branch_does_not_exist(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    vcs = _FakeVcs(existing_branches=frozenset())
    forge = _FakeForge()

    exit_code = deploy_module.run_batch_pr(_batch_pr_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-007" in codes
    assert exit_code != 0
    assert forge.find_calls == []
    assert forge.create_calls == []


def test_batch_pr_empty_wave_is_a_clean_noop(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        merge_base_sha="base-sha",
        window_subjects=("an ordinary commit, not a story merge",),
    )
    forge = _FakeForge()

    exit_code = deploy_module.run_batch_pr(_batch_pr_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["wave"] == []
    assert payload["data"]["opened"] is False
    assert payload["data"]["updated"] is False
    assert payload["verdict"] == "clean"
    assert exit_code == 0
    assert forge.find_calls == []
    assert forge.create_calls == []


def test_batch_pr_opens_a_new_pr_when_none_exists(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        merge_base_sha="base-sha",
        window_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        resolve_ref_sha="head-sha-abc",
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = deploy_module.run_batch_pr(_batch_pr_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["wave"] == ["4.4"]
    assert payload["data"]["opened"] is True
    assert payload["data"]["updated"] is False
    assert payload["data"]["pr_number"] == 1
    assert payload["verdict"] == "clean"
    assert exit_code == 0
    assert len(forge.create_calls) == 1
    assert forge.update_calls == []
    repo, base, head, title, body = forge.create_calls[0]
    assert repo.value == "rxm7706/local-recipes"
    assert base.value == "main"
    assert head.value == "loop/acme"
    assert "4.4" in title.text
    assert "4.4" in body.text
    # FR-35: no AI-attribution or courtesy preamble anywhere Marshal emits.
    for forbidden in ("Generated with", "Co-Authored-By", "🤖"):
        assert forbidden not in title.text
        assert forbidden not in body.text


def test_batch_pr_updates_an_existing_pr_instead_of_duplicating(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        merge_base_sha="base-sha",
        window_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        resolve_ref_sha="head-sha-abc",
        changed_paths=("docs/notes.md",),
    )
    existing_pr = PrInfo(number=99, url="https://example/pr/99", state="open", base="main")
    forge = _FakeForge(existing=existing_pr, update_result=existing_pr)

    exit_code = deploy_module.run_batch_pr(_batch_pr_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["opened"] is False
    assert payload["data"]["updated"] is True
    assert payload["data"]["pr_number"] == 99
    assert exit_code == 0
    assert forge.create_calls == []
    assert len(forge.update_calls) == 1
    assert forge.update_calls[0][1] == 99


def test_batch_pr_blocks_on_an_unsatisfied_required_check_and_writes_no_pr(tmp_path, capsys, monkeypatch):
    policy_path = _write_batch_pr_project_policy(
        tmp_path,
        """
[[landing_rules]]
name = "environment-yaml-sync"
trigger_path_glob = "pixi.toml"
trigger_mode = "include"
required_check = "environment-yaml-sync"
ungated = true
""",
    )
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(deploy_module, "conventional_project_policy_path", lambda slug: policy_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        merge_base_sha="base-sha",
        window_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        resolve_ref_sha="head-sha-abc",
        changed_paths=("pixi.toml",),
    )
    forge = _FakeForge(existing=None, check_status_map={"environment-yaml-sync": "failure"})

    exit_code = deploy_module.run_batch_pr(_batch_pr_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-013" in codes
    assert any("remediation" in finding["message"] for finding in payload["findings"])
    assert payload["data"]["opened"] is False
    assert payload["data"]["updated"] is False
    assert exit_code != 0
    assert forge.create_calls == []
    assert forge.update_calls == []


def test_batch_pr_a_satisfied_required_check_does_not_block(tmp_path, capsys, monkeypatch):
    policy_path = _write_batch_pr_project_policy(
        tmp_path,
        """
[[landing_rules]]
name = "environment-yaml-sync"
trigger_path_glob = "pixi.toml"
trigger_mode = "include"
required_check = "environment-yaml-sync"
ungated = true
""",
    )
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(deploy_module, "conventional_project_policy_path", lambda slug: policy_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        merge_base_sha="base-sha",
        window_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        resolve_ref_sha="head-sha-abc",
        changed_paths=("pixi.toml",),
    )
    forge = _FakeForge(existing=None, check_status_map={"environment-yaml-sync": "success"})

    exit_code = deploy_module.run_batch_pr(_batch_pr_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "clean"
    assert exit_code == 0
    assert len(forge.create_calls) == 1
    rule_report = payload["data"]["hygiene_rules"][0]
    assert rule_report["applies"] is True
    assert rule_report["satisfied"] is True


def test_batch_pr_applies_a_fired_label_after_opening_never_blocking(tmp_path, capsys, monkeypatch):
    policy_path = _write_batch_pr_project_policy(
        tmp_path,
        """
[[landing_rules]]
name = "maintenance-label"
trigger_path_glob = "recipes/**"
trigger_mode = "exclude"
label = "maintenance"
""",
    )
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(deploy_module, "conventional_project_policy_path", lambda slug: policy_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        merge_base_sha="base-sha",
        window_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        resolve_ref_sha="head-sha-abc",
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = deploy_module.run_batch_pr(_batch_pr_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["data"]["opened"] is True
    assert payload["data"]["labels_applied"] == ["maintenance"]
    assert len(forge.add_labels_calls) == 1
    _repo, number, labels = forge.add_labels_calls[0]
    assert number == 1
    assert labels == ("maintenance",)


def test_batch_pr_reports_mrs_deploy_014_on_a_forge_command_failure(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        merge_base_sha="base-sha",
        window_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        resolve_ref_sha="head-sha-abc",
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None, create_raises=True)

    exit_code = deploy_module.run_batch_pr(_batch_pr_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-014" in codes
    assert exit_code != 0


def test_batch_pr_body_lists_the_wave_with_gate_verdicts_from_the_journal(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    run_dir = tmp_path / "_bmad-output" / "projects" / "acme" / "implementation-artifacts" / "runs" / "acme-run-1"
    run_dir.mkdir(parents=True)
    entry = {
        "id": {"writer_id": "land-story-1", "counter": 0},
        "ts": "2026-08-06T00:00:00.000Z",
        "run_id": "acme-run-1",
        "kind": "manual-landing",
        "phase": "observation",
        "payload": {
            "story_key": "4.4",
            "justification": "landed manually",
            "merge_sha": "deadbeef",
            "gate_verdict": "clean",
        },
    }
    (run_dir / "journal.jsonl").write_text(json.dumps(entry) + "\n", encoding="utf-8")

    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        merge_base_sha="base-sha",
        window_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        resolve_ref_sha="head-sha-abc",
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = deploy_module.run_batch_pr(_batch_pr_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    assert exit_code == 0
    _repo, _base, _head, _title, body = forge.create_calls[0]
    assert "4.4" in body.text
    assert "clean" in body.text


# =====================================================================
# Code review (2026-08-06) fixes for `marshal deploy batch-pr`.
# =====================================================================


def test_batch_pr_p1_refuses_on_malformed_landing_rules_policy(tmp_path, capsys, monkeypatch):
    """P1 (HIGH, both reviewers' top finding): a malformed `landing_rules`
    policy layer must HARD REFUSE the whole invocation, never silently
    proceed with an empty rule set (which would silently disable the
    entire hygiene preflight over a config typo)."""
    policy_path = _write_batch_pr_project_policy(
        tmp_path,
        """
landing_rules = "not-a-list-of-rules"
""",
    )
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(deploy_module, "conventional_project_policy_path", lambda slug: policy_path)
    vcs = _FakeVcs(existing_branches=frozenset({"loop/acme"}))
    forge = _FakeForge()

    exit_code = deploy_module.run_batch_pr(_batch_pr_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-POLICY-002" in codes
    assert "MRS-DEPLOY-015" in codes
    assert payload["data"]["opened"] is False
    assert payload["data"]["updated"] is False
    assert exit_code != 0
    # Never even reached wave discovery/the forge -- refused before either.
    assert forge.find_calls == []
    assert forge.create_calls == []


def test_batch_pr_p2_add_labels_failure_does_not_claim_labels_applied(tmp_path, capsys, monkeypatch):
    """P2 (HIGH, Edge Case Hunter, CONFIRMED): `data["labels_applied"]` must
    never claim a label was applied when `add_labels` itself raised."""
    policy_path = _write_batch_pr_project_policy(
        tmp_path,
        """
[[landing_rules]]
name = "maintenance-label"
trigger_path_glob = "recipes/**"
trigger_mode = "exclude"
label = "maintenance"
""",
    )
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(deploy_module, "conventional_project_policy_path", lambda slug: policy_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        merge_base_sha="base-sha",
        window_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        resolve_ref_sha="head-sha-abc",
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None, add_labels_raises=True)

    exit_code = deploy_module.run_batch_pr(_batch_pr_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["opened"] is True
    assert payload["data"]["labels_applied"] == []
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-014" in codes
    assert exit_code != 0


def test_batch_pr_p4_branch_moved_before_pr_write_refuses(tmp_path, capsys, monkeypatch):
    """P4 (HIGH, both reviewers): the hygiene preflight vets `head_sha`, a
    pinned SHA -- if `head_branch` advances before the PR write, the write
    must refuse rather than open/update a PR for unvetted content."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        merge_base_sha="base-sha",
        window_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
        # Two `resolve_ref` calls happen for `head_branch`: once to pin
        # `head_sha` before the hygiene preflight, once to reconfirm it
        # immediately before the PR write -- the branch "moves" between
        # them. `worktree_head_sha` is pinned to match the FIRST value so
        # the P5 precondition (checked first) passes cleanly.
        resolve_ref_sequence=["head-sha-abc", "moved-sha"],
        worktree_head_sha="head-sha-abc",
    )
    forge = _FakeForge(existing=None)

    exit_code = deploy_module.run_batch_pr(_batch_pr_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-016" in codes
    assert payload["data"]["opened"] is False
    assert payload["data"]["updated"] is False
    assert exit_code != 0
    assert forge.create_calls == []
    assert forge.update_calls == []


def test_batch_pr_p5_stale_worktree_refuses_before_changed_files(tmp_path, capsys, monkeypatch):
    """P5 (HIGH, Blind Hunter): `changed_files` diffs the LOCAL worktree --
    if it is not checked out at the same commit the hygiene preflight
    pins as the wave's head, the run must refuse rather than trust a
    possibly stale/under-reporting diff."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        merge_base_sha="base-sha",
        window_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        resolve_ref_sha="head-sha-abc",
        changed_paths=("docs/notes.md",),
        worktree_head_sha="stale-sha",
    )
    forge = _FakeForge(existing=None)

    exit_code = deploy_module.run_batch_pr(_batch_pr_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-017" in codes
    assert payload["data"]["opened"] is False
    assert payload["data"]["updated"] is False
    assert exit_code != 0
    assert forge.find_calls == []
    assert forge.create_calls == []


def test_batch_pr_p5_worktree_head_sha_read_failure_refuses(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        merge_base_sha="base-sha",
        window_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        resolve_ref_sha="head-sha-abc",
        changed_paths=("docs/notes.md",),
        worktree_head_sha_raises=True,
    )
    forge = _FakeForge(existing=None)

    exit_code = deploy_module.run_batch_pr(_batch_pr_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-017" in codes
    assert exit_code != 0


def test_batch_pr_p8_existing_pr_with_a_different_base_refuses(tmp_path, capsys, monkeypatch):
    """P8 (MEDIUM, Edge Case Hunter): an open PR for this head branch that
    targets a DIFFERENT base than policy declares must never be silently
    updated."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        merge_base_sha="base-sha",
        window_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        resolve_ref_sha="head-sha-abc",
        changed_paths=("docs/notes.md",),
    )
    existing_pr = PrInfo(number=77, url="https://example/pr/77", state="open", base="release")
    forge = _FakeForge(existing=existing_pr)

    exit_code = deploy_module.run_batch_pr(_batch_pr_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-018" in codes
    assert payload["data"]["opened"] is False
    assert payload["data"]["updated"] is False
    assert exit_code != 0
    assert forge.update_calls == []
    assert forge.create_calls == []


def test_batch_pr_p10_already_landed_wave_is_a_noop(tmp_path, capsys, monkeypatch):
    """P10 (MEDIUM, Edge Case Hunter): `existing is None` must not be
    conflated with "already merged and closed" -- a wave whose every story
    key is already durably reachable from `base` must short-circuit to a
    clean no-op, never a fresh `create_pr`."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        merge_base_sha="base-sha",
        window_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        main_subjects=(_BMADLOOP_WAVE_SUBJECT,),
    )
    forge = _FakeForge(existing=None)

    exit_code = deploy_module.run_batch_pr(_batch_pr_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["opened"] is False
    assert payload["data"]["updated"] is False
    assert payload["data"]["already_landed"] is True
    assert payload["verdict"] == "clean"
    assert exit_code == 0
    assert forge.find_calls == []
    assert forge.create_calls == []


# =====================================================================
# Story 4.6 -- deploy idempotence and reconciliation of open intents
# (AD-6/AD-21/AD-28), ``batch-pr``'s own ``create_pr``/``update_pr``
# intent/outcome pair and pre-action reconciliation.
# =====================================================================


def test_batch_pr_writes_an_intent_outcome_pair_around_create_pr(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        merge_base_sha="base-sha",
        window_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        resolve_ref_sha="head-sha-abc",
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = deploy_module.run_batch_pr(_batch_pr_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    assert exit_code == 0
    journal_lines = _find_land_journal_lines(tmp_path, "acme")
    intents = [line for line in journal_lines if line["kind"] == "deploy-batch-pr-write" and line["phase"] == "intent"]
    outcomes = [
        line for line in journal_lines if line["kind"] == "deploy-batch-pr-write" and line["phase"] == "outcome"
    ]
    assert len(intents) == 1
    assert intents[0]["payload"]["action"] == "create_pr"
    assert intents[0]["payload"]["story_keys"] == ["4.4"]
    assert len(outcomes) == 1
    assert outcomes[0]["intent_id"] == intents[0]["id"]
    assert outcomes[0]["payload"]["pr_number"] == 1


def test_batch_pr_create_pr_failure_leaves_an_open_intent_with_no_outcome(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        merge_base_sha="base-sha",
        window_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        resolve_ref_sha="head-sha-abc",
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None, create_raises=True)

    exit_code = deploy_module.run_batch_pr(_batch_pr_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    assert exit_code != 0
    journal_lines = _find_land_journal_lines(tmp_path, "acme")
    assert len(journal_lines) == 1
    assert journal_lines[0]["kind"] == "deploy-batch-pr-write"
    assert journal_lines[0]["phase"] == "intent"
    assert "intent_id" not in journal_lines[0]


def test_batch_pr_never_auto_reconciles_on_bare_pr_existence_alone(tmp_path, capsys, monkeypatch):
    """Code review (2026-08-06, P2, both reviewers' independent top
    finding): a crashed prior `batch-pr` left an open intent for this
    wave. `find_open_pr` now shows SOME PR on the head branch -- but bare
    PR-existence does not confirm it is a PR reflecting THIS intent's own
    story keys (a stale PR from an earlier, differently-scoped wave, or a
    manually-opened PR, would satisfy the old check identically). `PrInfo`
    carries no content field this port can verify per-key coverage
    against, so this evidence is no longer treated as confirming --
    reconciliation never auto-closes a `batch-pr` intent on it alone: the
    intent stays open and is reported via MRS-DEPLOY-021, requiring the
    operator's own confirmation. This does not change which of
    create_pr/update_pr is called (that decision is `existing`'s own,
    unchanged) -- `existing is not None` still routes to `update_pr`."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        merge_base_sha="base-sha",
        window_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        resolve_ref_sha="head-sha-abc",
        changed_paths=("docs/notes.md",),
    )
    existing_pr = PrInfo(number=7, url="https://example/pr/7", state="open", base="main")
    forge = _FakeForge(existing=existing_pr)
    prior_intent = _write_open_intent(
        tmp_path,
        "acme",
        run_id="prior-run-1",
        kind="deploy-batch-pr-write",
        story_keys=["4.4"],
    )

    exit_code = deploy_module.run_batch_pr(_batch_pr_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-021" in codes
    assert len(forge.update_calls) == 1
    assert forge.create_calls == []

    journal_lines = _find_land_journal_lines(tmp_path, "acme")
    reconciliations = [
        line for line in journal_lines if line["phase"] == "outcome" and line["kind"] == "reconciliation"
    ]
    # The prior intent stays open -- NOT auto-closed by bare PR-existence.
    assert reconciliations == []
    still_open_intents = [
        line
        for line in journal_lines
        if line["kind"] == "deploy-batch-pr-write" and line["phase"] == "intent" and line["id"] == prior_intent["id"]
    ]
    assert len(still_open_intents) == 1


def test_batch_pr_reports_warn_for_an_open_intent_without_evidence(tmp_path, capsys, monkeypatch):
    """A crashed prior `batch-pr`'s open intent has NO confirming evidence
    yet (no PR exists for the head branch) -- it stays open and is
    reported via MRS-DEPLOY-021 (WARN, never blocking), and this run's own
    `create_pr` attempt proceeds normally."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        merge_base_sha="base-sha",
        window_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        resolve_ref_sha="head-sha-abc",
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)
    _write_open_intent(
        tmp_path,
        "acme",
        run_id="prior-run-1",
        kind="deploy-batch-pr-write",
        story_keys=["4.4"],
    )

    exit_code = deploy_module.run_batch_pr(_batch_pr_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-021" in codes
    assert payload["verdict"] == "warn"
    assert exit_code == 0
    assert len(forge.create_calls) == 1


def test_batch_pr_rerun_against_a_converged_system_is_zero_changes(tmp_path, capsys, monkeypatch):
    """NFR-7: once every wave key is already durably landed on `base`, a
    re-run is already established (P10) as a clean no-op -- this proves it
    stays that way with zero NEW journal entries and no forge writes at
    all across two consecutive runs."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        merge_base_sha="base-sha",
        window_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        main_subjects=(_BMADLOOP_WAVE_SUBJECT,),
    )
    forge = _FakeForge(existing=None)

    first_exit = deploy_module.run_batch_pr(_batch_pr_args(), vcs=vcs, fs=LocalFs(), forge=forge)
    capsys.readouterr()
    second_exit = deploy_module.run_batch_pr(_batch_pr_args(), vcs=vcs, fs=LocalFs(), forge=forge)
    payload = json.loads(capsys.readouterr().out)

    assert first_exit == 0
    assert second_exit == 0
    assert payload["data"]["already_landed"] is True
    assert payload["findings"] == []
    assert forge.create_calls == []
    assert forge.update_calls == []
    assert _find_land_journal_lines(tmp_path, "acme") == []


def test_evaluate_hygiene_p9_label_does_not_fire_when_check_raises():
    """P9 (MEDIUM, Edge Case Hunter): a rule's label must not fire when its
    own required_check could not be determined (raised)."""
    from pyforge.marshal.core.landing import LandingRule
    from pyforge.marshal.ports.forge import ForgeRef

    rule = LandingRule(
        name="gated-label",
        trigger_path_glob="**",
        trigger_mode="include",
        required_check="ci",
        label="urgent",
    )
    forge = _FakeForge(check_status_raises=True)

    report, blocking, fired_labels = deploy_module._evaluate_hygiene(
        (rule,), ("a.txt",), forge, ForgeRef("acme/widgets"), "sha"
    )

    assert fired_labels == ()
    assert blocking  # still blocks, unaffected by the label fix


def test_evaluate_hygiene_p9_label_does_not_fire_when_check_resolves_failure():
    """P9, the other half: a check that resolved to a real non-success
    conclusion must suppress the label identically to a raised check."""
    from pyforge.marshal.core.landing import LandingRule
    from pyforge.marshal.ports.forge import ForgeRef

    rule = LandingRule(
        name="gated-label",
        trigger_path_glob="**",
        trigger_mode="include",
        required_check="ci",
        label="urgent",
    )
    forge = _FakeForge(check_status_map={"ci": "failure"})

    report, blocking, fired_labels = deploy_module._evaluate_hygiene(
        (rule,), ("a.txt",), forge, ForgeRef("acme/widgets"), "sha"
    )

    assert fired_labels == ()
    assert blocking


def test_evaluate_hygiene_p9_label_still_fires_when_check_succeeds():
    """P9 regression guard: a satisfied required_check must still let the
    SAME rule's label fire (the pre-existing, correct half of this
    behavior)."""
    from pyforge.marshal.core.landing import LandingRule
    from pyforge.marshal.ports.forge import ForgeRef

    rule = LandingRule(
        name="gated-label",
        trigger_path_glob="**",
        trigger_mode="include",
        required_check="ci",
        label="urgent",
    )
    forge = _FakeForge(check_status_map={"ci": "success"})

    report, blocking, fired_labels = deploy_module._evaluate_hygiene(
        (rule,), ("a.txt",), forge, ForgeRef("acme/widgets"), "sha"
    )

    assert fired_labels == ("urgent",)
    assert blocking == []


def test_gather_gate_verdicts_p6_skips_a_run_dir_whose_fold_raises_non_typeerror(tmp_path, monkeypatch):
    """P6 (MEDIUM, both reviewers): a run directory whose journal content
    makes `fold` raise something other than TypeError (e.g. ValueError)
    must be skipped, never crash the whole gather."""
    good_dir = tmp_path / "_bmad-output" / "projects" / "acme" / "implementation-artifacts" / "runs" / "good"
    bad_dir = tmp_path / "_bmad-output" / "projects" / "acme" / "implementation-artifacts" / "runs" / "bad"
    good_dir.mkdir(parents=True)
    bad_dir.mkdir(parents=True)

    class _StubFoldResult:
        def __init__(self, entries):
            self.entries = entries

    class _StubEntry:
        def __init__(self, kind, payload):
            self.kind = kind
            self.payload = payload

    def _stub_fold(lines, *, sidecars=None):
        text = "\n".join(lines)
        if "bad-marker" in text:
            raise ValueError("simulated malformed journal content")
        if "good-marker" in text:
            return _StubFoldResult([_StubEntry("manual-landing", {"story_key": "4.4", "gate_verdict": "clean"})])
        return _StubFoldResult([])

    (good_dir / "journal.jsonl").write_text("good-marker\n", encoding="utf-8")
    (bad_dir / "journal.jsonl").write_text("bad-marker\n", encoding="utf-8")

    monkeypatch.setattr(deploy_module, "fold", _stub_fold)

    verdicts = deploy_module._gather_gate_verdicts(LocalFs(), tmp_path, "acme")

    assert verdicts == {"4.4": "clean"}


def test_gather_gate_verdicts_p7_orders_by_mtime_not_directory_name(tmp_path, monkeypatch):
    """P7 (MEDIUM, both reviewers): run directory NAMES are not reliably
    chronologically sortable ("run-10" sorts before "run-2" lexically) --
    the most recently-landed verdict (by mtime) must win, regardless of
    directory-name order."""
    import os
    import time

    runs_dir = tmp_path / "_bmad-output" / "projects" / "acme" / "implementation-artifacts" / "runs"
    older_dir = runs_dir / "acme-run-10"  # lexicographically FIRST
    newer_dir = runs_dir / "acme-run-2"  # lexicographically LAST
    older_dir.mkdir(parents=True)
    newer_dir.mkdir(parents=True)

    def _entry(verdict: str) -> str:
        return (
            json.dumps(
                {
                    "id": {"writer_id": "land-story-1", "counter": 0},
                    "ts": "2026-08-06T00:00:00.000Z",
                    "run_id": "run",
                    "kind": "manual-landing",
                    "phase": "observation",
                    "payload": {
                        "story_key": "4.4",
                        "justification": None,
                        "merge_sha": "deadbeef",
                        "gate_verdict": verdict,
                    },
                }
            )
            + "\n"
        )

    (older_dir / "journal.jsonl").write_text(_entry("gate-failed"), encoding="utf-8")
    (newer_dir / "journal.jsonl").write_text(_entry("clean"), encoding="utf-8")

    # `older_dir` really is older by mtime, despite sorting lexicographically
    # BEFORE `newer_dir` by name.
    now = time.time()
    os.utime(older_dir, (now - 100, now - 100))
    os.utime(newer_dir, (now, now))

    verdicts = deploy_module._gather_gate_verdicts(LocalFs(), tmp_path, "acme")

    assert verdicts == {"4.4": "clean"}


def test_batch_pr_redact_p11_returns_none_on_any_redaction_failure(monkeypatch):
    """P11 (LOW, Blind Hunter): the redaction net must fail closed on ANY
    exception `to_redacted`/its callees raise, not only the hardcoded
    ValueError/LookupError/TypeError allowlist it used to catch."""

    def _raising_to_redacted(payload):
        raise RecursionError("simulated: an exception type outside the old allowlist")

    monkeypatch.setattr(deploy_module, "to_redacted", _raising_to_redacted)

    assert deploy_module._batch_pr_redact("some text") is None


# =====================================================================
# ``marshal deploy refresh-feed`` (Story 4.5, AD-33).
# =====================================================================

from pyforge.core.process import ProcessError, ProcessResult  # noqa: E402

from pyforge.marshal.core.journal import (  # noqa: E402
    JournalEntryId,
    Phase,
    build_entry,
    prepare_for_write,
)
from pyforge.marshal.ports.harness import RunStatusSnapshot, TaskPhaseSnapshot  # noqa: E402


class _FakeProcess:
    """A minimal ``ProcessPort`` stand-in: a fixed, deterministic result per
    command (or a raise), plus a call log so a test can assert exactly what
    ran -- mirrors ``_FakeVcs``'s own established shape. ``raise_exc``
    (code review, 2026-08-06, P2/P6) lets a test choose WHICH exception type
    a raising command produces -- ``ProcessError`` by default, or an
    ``OSError``/``TimeoutError`` a real ``ProcessPort`` implementation is
    not contractually forbidden from letting escape, proving
    ``_run_resync_commands``'s broadened catch actually catches them.
    ``timeout_calls`` (P6) records the ``timeout_s`` each call was made
    with, so a test can confirm a real timeout is always passed -- never
    ``None`` -- guarding against an unbounded hang."""

    def __init__(
        self,
        *,
        results: dict[str, ProcessResult] | None = None,
        raise_on: set = frozenset(),
        raise_exc: type[Exception] = ProcessError,
    ):
        self.results = results or {}
        self.raise_on = raise_on
        self.raise_exc = raise_exc
        self.calls: list[list[str]] = []
        self.timeout_calls: list[float | None] = []

    def run(self, argv, *, cwd, timeout_s=None):
        self.calls.append(list(argv))
        self.timeout_calls.append(timeout_s)
        command = " ".join(argv)
        if command in self.raise_on:
            raise self.raise_exc(f"could not launch {command!r}")
        return self.results.get(command, ProcessResult(returncode=0, stdout="", stderr=""))


class _FakeHarness:
    """A minimal ``HarnessPort`` stand-in exposing only
    ``run_status_snapshot`` -- the sole method ``refresh-feed`` calls.
    ``raises`` (code review, 2026-08-06, P2) lets a test simulate an
    implementation that does NOT honor this port's own "never raises"
    contract, proving ``_gather_claimed_commits``'s defensive wrap degrades
    to "no claim available" rather than crashing the whole gather."""

    def __init__(self, *, snapshot: RunStatusSnapshot | None = None, raises: Exception | None = None):
        self.snapshot = snapshot
        self.raises = raises
        self.calls: list[tuple] = []

    def run_status_snapshot(self, project, run_id):
        self.calls.append((project, run_id))
        if self.raises is not None:
            raise self.raises
        return self.snapshot


class _ExistsRaisingFs(LocalFs):
    """A ``FsPort`` wrapper that raises on ``exists`` -- code review
    (2026-08-06, P2): proves ``_gather_claimed_commits``'s own
    ``fs.exists(home)`` guard degrades to "no journal facts available"
    rather than crashing, for an ``FsPort`` implementation that does not
    honor the real ``LocalFs.exists``'s own "never raises" internal
    convention."""

    def exists(self, path):
        raise OSError("simulated fs.exists failure")


def _refresh_feed_args(*, project: str = "acme", format: str = "json") -> argparse.Namespace:
    return argparse.Namespace(project=project, format=format)


def _write_prior_run_with_harness_run_id(tmp_path, home: Path, slug: str, run_id: str, harness_run_id: str) -> Path:
    """Seeds a real Marshal run directory under ``home``'s own Tier-3 store
    with a minimal, valid ``run-launch`` outcome entry naming
    ``harness_run_id`` -- the SAME shape
    ``cli/spin.py::_resolve_harness_run_id_for_resume`` reads, mirroring
    ``test_spin.py::_seed_resolvable_prior_run``'s own real-filesystem
    convention (this module's tests use a real ``LocalFs``, never a fake
    one)."""
    run_dir = home / "_bmad-output" / "projects" / slug / "implementation-artifacts" / "runs" / run_id
    run_dir.mkdir(parents=True)
    entry = build_entry(
        id=JournalEntryId("spin-1", 1),
        ts="2026-08-01T00:00:00.000Z",
        run_id=run_id,
        kind="run-launch",
        phase=Phase.OUTCOME,
        intent_id=JournalEntryId("spin-1", 0),
        payload={"pid": 4242, "harness_run_id": harness_run_id},
    )
    line = prepare_for_write(entry).line
    (run_dir / "journal.jsonl").write_text(line + "\n", encoding="utf-8")
    return run_dir


def _write_refresh_feed_project_policy(tmp_path: Path, monkeypatch, text: str) -> Path:
    """Mirrors ``_write_batch_pr_project_policy``'s own pattern: writes to an
    arbitrary path and monkeypatches ``conventional_project_policy_path`` so
    ``run_refresh_feed``'s policy read finds it -- the real conventional
    path resolves against the REAL repo_root(), not the monkeypatched
    ``deploy_module.repo_root``."""
    path = tmp_path / "refresh-feed-marshal-policy.toml"
    path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(deploy_module, "conventional_project_policy_path", lambda slug: path)
    return path


def test_refresh_feed_reports_git_facts_with_no_journal_available(tmp_path, capsys, monkeypatch):
    """No loop home provisioned at all -- a legitimate state, per the
    story's own I/O matrix: git's own answer stands alone, no findings."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    vcs = _FakeVcs(main_subjects=("Merge acme/1.2 into main",))

    exit_code = deploy_module.run_refresh_feed(
        _refresh_feed_args(), vcs=vcs, fs=LocalFs(), process=_FakeProcess(), harness=_FakeHarness()
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["verdict"] == "clean"
    assert payload["data"]["stories"] == [
        {
            "story_key": "1.2",
            "durable": {"value": True, "domain": "git"},
            "claimed_commit_sha": {"value": None, "domain": "journal"},
        }
    ]
    # landing_resync defaults true, but landing_resync_commands defaults
    # empty -- resync runs, nothing to execute.
    assert payload["data"]["resync_skipped"] is False
    assert payload["data"]["resync_commands"] == []


def test_refresh_feed_claimed_commit_matching_git_is_consistent(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    home_root = tmp_path / "loop-homes"
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(home_root))
    home = home_root / "acme"
    _write_prior_run_with_harness_run_id(tmp_path, home, "acme", "acme-20260801T000000000Z-aaaa", "acme-hh01")
    vcs = _FakeVcs(main_subjects=("Merge acme/1.2 into main",))
    snapshot = RunStatusSnapshot(
        paused_stage=None,
        paused_story_key=None,
        paused_reason=None,
        escalated_spec_file=None,
        escalated_task_phase=None,
        deferred=(),
        tasks=(TaskPhaseSnapshot(story_key="1-2-title", phase="done", commit_sha="deadbeef"),),
    )
    harness = _FakeHarness(snapshot=snapshot)

    exit_code = deploy_module.run_refresh_feed(
        _refresh_feed_args(), vcs=vcs, fs=LocalFs(), process=_FakeProcess(), harness=harness
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["verdict"] == "clean"
    assert payload["data"]["stories"] == [
        {
            "story_key": "1.2",
            "durable": {"value": True, "domain": "git"},
            "claimed_commit_sha": {"value": "deadbeef", "domain": "journal"},
        }
    ]
    assert harness.calls == [(home, "acme-hh01")]


def test_refresh_feed_claimed_commit_not_confirmed_by_git_reports_mrs_status_001(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    home_root = tmp_path / "loop-homes"
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(home_root))
    home = home_root / "acme"
    _write_prior_run_with_harness_run_id(tmp_path, home, "acme", "acme-20260801T000000000Z-aaaa", "acme-hh01")
    vcs = _FakeVcs(main_subjects=())  # nothing merged, per git
    snapshot = RunStatusSnapshot(
        paused_stage=None,
        paused_story_key=None,
        paused_reason=None,
        escalated_spec_file=None,
        escalated_task_phase=None,
        deferred=(),
        tasks=(TaskPhaseSnapshot(story_key="9-9-title", phase="review", commit_sha="feedbead"),),
    )
    harness = _FakeHarness(snapshot=snapshot)

    exit_code = deploy_module.run_refresh_feed(
        _refresh_feed_args(), vcs=vcs, fs=LocalFs(), process=_FakeProcess(), harness=harness
    )

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-STATUS-001" in codes
    assert payload["verdict"] == "warn"
    assert exit_code == 0  # WARN stays exit 0 -- reported, never blocking
    row = payload["data"]["stories"][0]
    assert row["durable"]["value"] is False
    assert row["claimed_commit_sha"]["value"] == "feedbead"


def test_refresh_feed_landing_resync_false_skips_resync_step(tmp_path, capsys, monkeypatch, tmp_path_factory):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    _write_refresh_feed_project_policy(tmp_path, monkeypatch, "landing_resync = false\n")
    vcs = _FakeVcs()
    process = _FakeProcess()

    exit_code = deploy_module.run_refresh_feed(
        _refresh_feed_args(), vcs=vcs, fs=LocalFs(), process=process, harness=_FakeHarness()
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["data"]["resync_skipped"] is True
    assert payload["data"]["resync_commands"] == []
    assert process.calls == []


def test_refresh_feed_runs_configured_resync_commands_when_resync_is_true(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    _write_refresh_feed_project_policy(
        tmp_path,
        monkeypatch,
        'landing_resync = true\nlanding_resync_commands = ["true"]\n',
    )
    vcs = _FakeVcs()
    process = _FakeProcess(results={"true": ProcessResult(returncode=0, stdout="", stderr="")})

    exit_code = deploy_module.run_refresh_feed(
        _refresh_feed_args(), vcs=vcs, fs=LocalFs(), process=process, harness=_FakeHarness()
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["data"]["resync_skipped"] is False
    assert payload["data"]["resync_commands"] == [
        {"command": "true", "resolvable": True, "returncode": 0, "stdout": "", "stderr": ""}
    ]
    assert process.calls == [["true"]]


def test_refresh_feed_resync_command_failure_is_reported_not_swallowed(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    _write_refresh_feed_project_policy(
        tmp_path,
        monkeypatch,
        'landing_resync = true\nlanding_resync_commands = ["false"]\n',
    )
    vcs = _FakeVcs()
    process = _FakeProcess(results={"false": ProcessResult(returncode=1, stdout="", stderr="nope")})

    exit_code = deploy_module.run_refresh_feed(
        _refresh_feed_args(), vcs=vcs, fs=LocalFs(), process=process, harness=_FakeHarness()
    )

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-020" in codes
    assert payload["verdict"] == "gate-failed"
    assert exit_code != 0


def test_refresh_feed_resync_command_launch_failure_reports_mrs_deploy_019(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    _write_refresh_feed_project_policy(
        tmp_path,
        monkeypatch,
        'landing_resync = true\nlanding_resync_commands = ["missing-binary"]\n',
    )
    vcs = _FakeVcs()
    process = _FakeProcess(raise_on={"missing-binary"})

    deploy_module.run_refresh_feed(_refresh_feed_args(), vcs=vcs, fs=LocalFs(), process=process, harness=_FakeHarness())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-019" in codes
    assert payload["verdict"] == "unevaluable"


def test_refresh_feed_resync_command_with_bare_shell_syntax_is_never_spawned(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    _write_refresh_feed_project_policy(
        tmp_path,
        monkeypatch,
        'landing_resync = true\nlanding_resync_commands = ["true && false"]\n',
    )
    vcs = _FakeVcs()
    process = _FakeProcess()

    deploy_module.run_refresh_feed(_refresh_feed_args(), vcs=vcs, fs=LocalFs(), process=process, harness=_FakeHarness())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-019" in codes
    assert process.calls == []  # never spawned


def test_refresh_feed_with_no_active_project_reports_mrs_policy_005(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    exit_code = deploy_module.run_refresh_feed(
        _refresh_feed_args(project=""),
        vcs=_FakeVcs(),
        fs=LocalFs(),
        process=_FakeProcess(),
        harness=_FakeHarness(),
    )
    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-POLICY-005" in codes
    assert payload["data"]["stories"] == []
    assert exit_code == 0


def test_refresh_feed_hard_main_read_failure_reports_mrs_deploy_003(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    vcs = _FakeVcs(main_raises=True)

    exit_code = deploy_module.run_refresh_feed(
        _refresh_feed_args(), vcs=vcs, fs=LocalFs(), process=_FakeProcess(), harness=_FakeHarness()
    )

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-003" in codes
    assert payload["verdict"] == "unevaluable"
    assert exit_code != 0


def test_refresh_feed_is_a_provable_noop_across_two_runs(tmp_path, capsys, monkeypatch):
    """The story's own provable-no-op requirement: running refresh-feed
    twice against unchanged fixtures produces identical output (this
    report has no timestamp field, so byte-identical is the bar)."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    home_root = tmp_path / "loop-homes"
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(home_root))
    home = home_root / "acme"
    _write_prior_run_with_harness_run_id(tmp_path, home, "acme", "acme-20260801T000000000Z-aaaa", "acme-hh01")
    _write_refresh_feed_project_policy(
        tmp_path,
        monkeypatch,
        'landing_resync = true\nlanding_resync_commands = ["true"]\n',
    )
    snapshot = RunStatusSnapshot(
        paused_stage=None,
        paused_story_key=None,
        paused_reason=None,
        escalated_spec_file=None,
        escalated_task_phase=None,
        deferred=(),
        tasks=(TaskPhaseSnapshot(story_key="1-2-title", phase="done", commit_sha="deadbeef"),),
    )

    def _run_once():
        vcs = _FakeVcs(main_subjects=("Merge acme/1.2 into main",))
        process = _FakeProcess(results={"true": ProcessResult(returncode=0, stdout="", stderr="")})
        harness = _FakeHarness(snapshot=snapshot)
        deploy_module.run_refresh_feed(_refresh_feed_args(), vcs=vcs, fs=LocalFs(), process=process, harness=harness)
        return capsys.readouterr().out

    first = _run_once()
    second = _run_once()
    assert first == second
    assert json.loads(first)["data"]["stories"] != []


# =====================================================================
# Code review (2026-08-06): remediation for ``marshal deploy refresh-feed``
# (Blind Hunter + Edge Case Hunter, parallel pass -- see the spec's own
# Review Triage Log for the full P1-P8 list this file's new tests below
# cover).
# =====================================================================


def test_refresh_feed_whitespace_only_resync_command_is_reported_not_crashed(tmp_path, capsys, monkeypatch):
    """P1 (HIGH, both reviewers): a whitespace-only ``landing_resync_commands``
    entry ``shlex.split()``s CLEANLY to an empty token list -- distinct from
    a ``ValueError`` -- and must never reach ``ProcessPort.run`` with an
    empty argv. Reported as malformed and skipped, never crashing the whole
    invocation."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    _write_refresh_feed_project_policy(
        tmp_path, monkeypatch, 'landing_resync = true\nlanding_resync_commands = ["   "]\n'
    )
    vcs = _FakeVcs()
    process = _FakeProcess()

    exit_code = deploy_module.run_refresh_feed(
        _refresh_feed_args(), vcs=vcs, fs=LocalFs(), process=process, harness=_FakeHarness()
    )

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-019" in codes
    assert payload["data"]["resync_commands"][0]["resolvable"] is False
    assert process.calls == []  # never spawned with an empty argv
    assert exit_code != 0


def test_refresh_feed_resync_command_oserror_is_reported_not_crashed(tmp_path, capsys, monkeypatch):
    """P2 (HIGH): ``_run_resync_commands``'s own catch is broadened beyond
    ``ProcessError`` alone -- a ``ProcessPort`` implementation that lets a
    raw ``OSError`` escape ``run`` must still be reported, not crash the
    whole ``refresh-feed`` invocation."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    _write_refresh_feed_project_policy(
        tmp_path, monkeypatch, 'landing_resync = true\nlanding_resync_commands = ["flaky-cmd"]\n'
    )
    vcs = _FakeVcs()
    process = _FakeProcess(raise_on={"flaky-cmd"}, raise_exc=OSError)

    exit_code = deploy_module.run_refresh_feed(
        _refresh_feed_args(), vcs=vcs, fs=LocalFs(), process=process, harness=_FakeHarness()
    )

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-019" in codes
    assert exit_code != 0


def test_refresh_feed_resync_command_passes_a_real_timeout(tmp_path, capsys, monkeypatch):
    """P6 (MEDIUM): every resync command runs with a real ``timeout_s`` --
    never ``None`` -- so a hung command cannot hang the whole invocation."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    _write_refresh_feed_project_policy(
        tmp_path, monkeypatch, 'landing_resync = true\nlanding_resync_commands = ["true"]\n'
    )
    vcs = _FakeVcs()
    process = _FakeProcess(results={"true": ProcessResult(returncode=0, stdout="", stderr="")})

    deploy_module.run_refresh_feed(_refresh_feed_args(), vcs=vcs, fs=LocalFs(), process=process, harness=_FakeHarness())

    assert process.timeout_calls == [deploy_module._RESYNC_TIMEOUT_S]
    assert deploy_module._RESYNC_TIMEOUT_S is not None


def test_refresh_feed_resync_command_timeout_is_reported_not_hung(tmp_path, capsys, monkeypatch):
    """P6 (MEDIUM): a command that would exceed the timeout is reported as
    a launch failure, never left to hang -- simulated via the fake process
    port raising the SAME exception a real timed-out ``ProcessPort.run``
    would (never an actual hanging subprocess in this test)."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    _write_refresh_feed_project_policy(
        tmp_path, monkeypatch, 'landing_resync = true\nlanding_resync_commands = ["stalled-fetch"]\n'
    )
    vcs = _FakeVcs()
    process = _FakeProcess(raise_on={"stalled-fetch"}, raise_exc=TimeoutError)

    exit_code = deploy_module.run_refresh_feed(
        _refresh_feed_args(), vcs=vcs, fs=LocalFs(), process=process, harness=_FakeHarness()
    )

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-019" in codes
    assert exit_code != 0


def test_refresh_feed_degrades_gracefully_when_run_status_snapshot_raises(tmp_path, capsys, monkeypatch):
    """P2 (HIGH): ``HarnessPort.run_status_snapshot``'s own docstring
    promises "never raises", but ``_gather_claimed_commits`` defends its
    OWN identical promise anyway -- an implementation that raises degrades
    to "no claim available for this run" rather than crashing the whole
    ``refresh-feed`` invocation."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    home_root = tmp_path / "loop-homes"
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(home_root))
    home = home_root / "acme"
    _write_prior_run_with_harness_run_id(tmp_path, home, "acme", "acme-20260801T000000000Z-aaaa", "acme-hh01")
    vcs = _FakeVcs(main_subjects=("Merge acme/1.2 into main",))
    harness = _FakeHarness(raises=ValueError("simulated state.json corruption"))

    exit_code = deploy_module.run_refresh_feed(
        _refresh_feed_args(), vcs=vcs, fs=LocalFs(), process=_FakeProcess(), harness=harness
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["data"]["stories"] == [
        {
            "story_key": "1.2",
            "durable": {"value": True, "domain": "git"},
            "claimed_commit_sha": {"value": None, "domain": "journal"},
        }
    ]


def test_refresh_feed_degrades_gracefully_when_fs_exists_raises(tmp_path, capsys, monkeypatch):
    """P2 (HIGH): ``_gather_claimed_commits``'s own ``fs.exists(home)``
    guard is broadened beyond ``FsError`` alone -- an ``FsPort``
    implementation that lets a raw ``OSError`` escape ``exists`` must still
    degrade this gather to "no journal facts available", never crash."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    vcs = _FakeVcs(main_subjects=("Merge acme/1.2 into main",))

    exit_code = deploy_module.run_refresh_feed(
        _refresh_feed_args(),
        vcs=vcs,
        fs=_ExistsRaisingFs(),
        process=_FakeProcess(),
        harness=_FakeHarness(),
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["data"]["stories"] == [
        {
            "story_key": "1.2",
            "durable": {"value": True, "domain": "git"},
            "claimed_commit_sha": {"value": None, "domain": "journal"},
        }
    ]


def test_gather_claimed_commits_skips_a_malformed_story_key_not_fatal(tmp_path, monkeypatch):
    """P2 (HIGH): one task with a malformed (non-``str``) ``story_key`` is
    skipped -- reported by omission, never a fatal error for the whole
    gather -- mirroring ``_discover_candidates``'s own established
    skip-invalid convention."""
    home_root = tmp_path / "loop-homes"
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(home_root))
    home = home_root / "acme"
    _write_prior_run_with_harness_run_id(tmp_path, home, "acme", "acme-20260801T000000000Z-aaaa", "acme-hh01")
    snapshot = RunStatusSnapshot(
        paused_stage=None,
        paused_story_key=None,
        paused_reason=None,
        escalated_spec_file=None,
        escalated_task_phase=None,
        deferred=(),
        tasks=(
            TaskPhaseSnapshot(story_key=42, phase="done", commit_sha="badkey"),  # type: ignore[arg-type]
            TaskPhaseSnapshot(story_key="1-2-title", phase="done", commit_sha="deadbeef"),
        ),
    )
    harness = _FakeHarness(snapshot=snapshot)

    claims = deploy_module._gather_claimed_commits(LocalFs(), harness, home, "acme")

    assert [str(claim.story_key) for claim in claims] == ["1.2"]


def test_refresh_feed_policy_is_file_probe_oserror_still_reports_policyioerror(tmp_path, capsys, monkeypatch):
    """P2 (HIGH): confirms the SAME failure mode the finding names --
    ``candidate.is_file()`` raising ``OSError`` is treated as "file present"
    (the established convention: fail toward attempting the read, never
    silently toward "absent") -- is properly wrapped into a
    ``PolicyIOError``-shaped, reported outcome by the subsequent
    ``_read_project_policy`` call, rather than propagating a raw exception.
    Verified already correct by this codebase's own established
    ``_read_project_policy`` -- this test locks the behavior in."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    missing = tmp_path / "nonexistent-policy.toml"
    monkeypatch.setattr(deploy_module, "conventional_project_policy_path", lambda slug: missing)
    monkeypatch.setattr(Path, "is_file", lambda self: (_ for _ in ()).throw(OSError("simulated probe failure")))

    exit_code = deploy_module.run_refresh_feed(
        _refresh_feed_args(), vcs=_FakeVcs(), fs=LocalFs(), process=_FakeProcess(), harness=_FakeHarness()
    )

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert any(code == "MRS-POLICY-004" for code in codes)
    assert payload["data"]["stories"] == []
    assert exit_code != 0


def test_refresh_feed_early_refusal_still_includes_resync_commands_key(tmp_path, capsys, monkeypatch):
    """P5 (MEDIUM): an early-refusal path (no active project) still carries
    ``resync_commands`` in its envelope, matching the happy path's own
    shape (AD-14's "one envelope for every command")."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))

    exit_code = deploy_module.run_refresh_feed(
        _refresh_feed_args(project=""),
        vcs=_FakeVcs(),
        fs=LocalFs(),
        process=_FakeProcess(),
        harness=_FakeHarness(),
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert "resync_commands" in payload["data"]
    assert payload["data"]["resync_commands"] == []
    assert payload["data"]["resync_skipped"] is True


def test_refresh_feed_noop_reconciliation_holds_even_with_volatile_resync_output(tmp_path, capsys, monkeypatch):
    """P4 (MEDIUM, Blind Hunter): the provable-no-op guarantee applies to
    the RECONCILIATION portion of the report (``data.stories`` plus every
    finding) -- never to a resync command's own raw stdout/stderr, which is
    inherently volatile for anything but a fixed placeholder command (a
    real resync command might print a timestamp, an object count, etc.).
    This test uses a command whose output legitimately DIFFERS between the
    two runs and asserts the reconciliation portion still matches."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    home_root = tmp_path / "loop-homes"
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(home_root))
    home = home_root / "acme"
    _write_prior_run_with_harness_run_id(tmp_path, home, "acme", "acme-20260801T000000000Z-aaaa", "acme-hh01")
    _write_refresh_feed_project_policy(
        tmp_path, monkeypatch, 'landing_resync = true\nlanding_resync_commands = ["fetch"]\n'
    )
    snapshot = RunStatusSnapshot(
        paused_stage=None,
        paused_story_key=None,
        paused_reason=None,
        escalated_spec_file=None,
        escalated_task_phase=None,
        deferred=(),
        tasks=(TaskPhaseSnapshot(story_key="1-2-title", phase="done", commit_sha="deadbeef"),),
    )

    counter = {"n": 0}

    class _VolatileProcess:
        """Every call to ``fetch`` returns DIFFERENT stdout (a counter --
        mirrors a real resync command printing an object count/timestamp
        that legitimately varies run to run against otherwise-unchanged
        repository state)."""

        def run(self, argv, *, cwd, timeout_s=None):
            counter["n"] += 1
            return ProcessResult(returncode=0, stdout=f"fetched {counter['n']} objects", stderr="")

    def _run_once():
        vcs = _FakeVcs(main_subjects=("Merge acme/1.2 into main",))
        harness = _FakeHarness(snapshot=snapshot)
        deploy_module.run_refresh_feed(
            _refresh_feed_args(), vcs=vcs, fs=LocalFs(), process=_VolatileProcess(), harness=harness
        )
        return json.loads(capsys.readouterr().out)

    first = _run_once()
    second = _run_once()

    # The raw resync output legitimately differs between the two runs...
    assert first["data"]["resync_commands"][0]["stdout"] != second["data"]["resync_commands"][0]["stdout"]
    # ...but the reconciliation portion (the actual no-op guarantee, AD-12)
    # is identical regardless.
    assert first["data"]["stories"] == second["data"]["stories"]
    assert first["findings"] == second["findings"]


# =====================================================================
# Code review (2026-08-06), remediation pass: P1/P3/P5.
# =====================================================================


def test_deploy_writer_id_p1_unique_across_pid_reuse(monkeypatch):
    """Code review, 2026-08-06, P1 (both reviewers' independent top
    finding, CRITICAL): OS process ids are reused over time. Before this
    fix, `_deploy_writer_id` minted a bare `f"deploy-{action}-{pid}"`, with
    the per-invocation counter always restarting at 0 -- so a crashed
    invocation and a LATER, completely unrelated invocation of the same
    action could mint the IDENTICAL `(writer_id, counter=0)`
    `JournalEntryId` once `_fold_deploy_journal`'s GLOBAL fold combines
    every run directory together (a hazard this diff itself introduced),
    letting the fold mis-pair an outcome from one invocation against an
    intent from a different, unrelated one -- corrupting AD-28's own
    intent/outcome pairing guarantee. Two writer-id mints under the SAME
    mocked pid must now be distinct."""
    monkeypatch.setattr(deploy_module.os, "getpid", lambda: 4242)

    first = deploy_module._deploy_writer_id("promote")
    second = deploy_module._deploy_writer_id("promote")

    assert first != second
    # Both remain valid, filesystem-safe JournalEntryId writer ids.
    JournalEntryId(first, 0)
    JournalEntryId(second, 0)


def test_deploy_writer_id_p1_pid_reuse_does_not_mispair_a_global_fold(tmp_path, monkeypatch):
    """The end-to-end consequence of the P1 fix above: two SEPARATE
    `_DeployRun` invocations of the SAME action, minted under the SAME
    (mocked, reused) pid, produce DISTINCT writer ids -- so
    `_fold_deploy_journal`'s GLOBAL fold across both run directories never
    mis-pairs one invocation's own outcome against the other's own,
    unrelated intent. Run A "crashes" (an open intent for "1.1", no
    outcome); Run B, under the same pid, confirms and closes its own
    disjoint "2.2" intent. Without the fix, both `JournalEntryId`s could
    collide at `(writer_id, counter=0)`, and Run B's own outcome
    (`intent_id` matching that shared id) would incorrectly also close
    Run A's own still-open "1.1" intent in the fold."""
    monkeypatch.setattr(deploy_module.os, "getpid", lambda: 4242)
    fs = LocalFs()

    findings_a: list = []
    run_a = deploy_module._DeployRun(fs, tmp_path, "acme", deploy_module._deploy_writer_id("promote"))
    intent_a = run_a.write(
        findings_a,
        kind="deploy-promote-commit",
        phase=deploy_module.Phase.INTENT,
        payload={"action": "commit_paths", "story_keys": ["1.1"]},
    )
    # Run A "crashes" here -- no outcome is ever written for intent_a.

    findings_b: list = []
    run_b = deploy_module._DeployRun(fs, tmp_path, "acme", deploy_module._deploy_writer_id("promote"))
    intent_b = run_b.write(
        findings_b,
        kind="deploy-promote-commit",
        phase=deploy_module.Phase.INTENT,
        payload={"action": "commit_paths", "story_keys": ["2.2"]},
    )
    run_b.write(
        findings_b,
        kind="deploy-promote-commit",
        phase=deploy_module.Phase.OUTCOME,
        payload={"action": "commit_paths", "story_keys": ["2.2"]},
        intent_id=intent_b,
    )

    assert intent_a.writer_id != intent_b.writer_id

    fold_findings: list = []
    fold_result = deploy_module._fold_deploy_journal(fs, tmp_path, "acme", fold_findings)
    open_ids = {entry.id for entry in fold_result.open_intents}

    assert intent_a in open_ids  # "1.1" correctly still open -- never crashed
    assert intent_b not in open_ids  # "2.2" correctly closed by its own outcome
    assert fold_findings == []


def test_fold_deploy_journal_p3_reports_a_finding_on_blanket_fold_failure(tmp_path, capsys, monkeypatch):
    """Code review (2026-08-06, P3, Blind Hunter, HIGH): `_fold_deploy_journal`'s
    outer `fold()` call can itself fail on a shape `fold` does not
    tolerate. That used to degrade SILENTLY to an empty `FoldResult` --
    indistinguishable, to every caller, from "confirmed: no open intents
    anywhere" -- making every genuinely open intent across every run
    directory invisible in one shot with zero signal. It must now emit a
    registered MRS-DEPLOY-022 finding naming the failure instead, and the
    guarded action must still proceed normally (never blocking)."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_open_intent(
        tmp_path,
        "acme",
        run_id="prior-run-1",
        kind="deploy-promote-commit",
        story_keys=["9.9"],
    )

    real_fold = deploy_module.fold

    def _raising_fold(lines, *, sidecars=None):
        # Raise only for the REAL cross-run fold attempt (non-empty
        # lines); the fallback `fold((), sidecars={})` this function's own
        # except-clause makes must still succeed, exactly like the real
        # `core.journal.fold` does for an empty input.
        if lines:
            raise ValueError("simulated malformed cross-run journal content")
        return real_fold(lines, sidecars=sidecars or {})

    monkeypatch.setattr(deploy_module, "fold", _raising_fold)

    vcs = _FakeVcs()
    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())
    payload = json.loads(capsys.readouterr().out)

    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-022" in codes
    finding = next(f for f in payload["findings"] if f["code"] == "MRS-DEPLOY-022")
    assert finding["severity"] == "warn"
    # The fold failure means reconciliation could not run at all -- the
    # prior "9.9" open intent is therefore neither reconciled NOR reported
    # as MRS-DEPLOY-021 this run (it is invisible to this fold, exactly
    # the gap MRS-DEPLOY-022 exists to surface instead of hiding).
    assert "MRS-DEPLOY-021" not in codes
    # Never blocking -- the action this run guards still proceeds normally.
    assert exit_code == 0


def test_promote_reconciles_one_open_intent_while_leaving_a_disjoint_one_open(tmp_path, capsys, monkeypatch):
    """P5 (MEDIUM, Edge Case Hunter): two DISTINCT open intents of the same
    kind, from two different crashed runs, each naming a disjoint
    story-key subset -- `_reconcile_open_intents`'s loop must reconcile
    the one this run's own live evidence confirms while INDEPENDENTLY
    leaving the other open and reporting MRS-DEPLOY-021 for it alone.
    Every prior reconciliation test scenario carried exactly one open
    intent; this is the first to exercise the loop's multi-intent
    iteration branch."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "3-8", _VALID_SPEC)
    _write_tracked_spec(tmp_path, "acme", "3-8", _VALID_SPEC)
    vcs = _FakeVcs(main_subjects=("Merge acme/3-8 into main",))

    confirmed_intent = _write_open_intent(
        tmp_path,
        "acme",
        run_id="prior-run-confirmed",
        kind="deploy-promote-commit",
        story_keys=["3.8"],
        writer_id="prior-crashed-run-a",
    )
    unconfirmed_intent = _write_open_intent(
        tmp_path,
        "acme",
        run_id="prior-run-unconfirmed",
        kind="deploy-promote-commit",
        story_keys=["9.9"],
        writer_id="prior-crashed-run-b",
    )

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    codes = [finding["code"] for finding in payload["findings"]]
    assert codes.count("MRS-DEPLOY-021") == 1
    warn_finding = next(f for f in payload["findings"] if f["code"] == "MRS-DEPLOY-021")
    assert "9.9" in warn_finding["message"]
    assert "3.8" not in warn_finding["message"]

    journal_lines = _find_land_journal_lines(tmp_path, "acme")
    reconciliations = [
        line for line in journal_lines if line["phase"] == "outcome" and line["kind"] == "reconciliation"
    ]
    assert len(reconciliations) == 1
    assert reconciliations[0]["intent_id"] == confirmed_intent["id"]
    assert reconciliations[0]["intent_id"] != unconfirmed_intent["id"]


# =====================================================================
# ``marshal deploy reconcile-completions`` (Story 5.9, AD-5/AD-6/AD-29/
# AD-33): "a story finished by hand is not invisible to the ledger".
# ``VcsPort``/``HarnessPort`` are faked (mirrors this module's own
# established convention); filesystem I/O runs against a REAL
# ``tmp_path`` via the real ``LocalFs``, including the tracked ledger
# file and the Tier-3 feed -- this command's own line-level rewrite
# (``core.status.render_ledger_advancements``) and its own Tier-3
# repair-write need real bytes to prove byte-preservation against.
# Reported completion-path label is ``"not-loop-native"`` (Spec Change
# Log, 2026-08-12), never ``"bmad-quick-dev"``.
# =====================================================================

from pyforge.marshal.adapters.harness_bmadloop import HarnessError  # noqa: E402


class _FakeReconcileHarness:
    """A minimal ``HarnessPort`` stand-in exposing only ``ledger_story_
    statuses`` -- the ONE method Story 5.9's own CAP-4 isolation contract
    (AD-5) permits ``run_reconcile_completions`` to call. Every OTHER
    ``HarnessPort`` method raises ``AssertionError`` if invoked AT ALL --
    this is the isolation PROOF itself (the story's own AC: "proven by a
    test"), not a convenience default: a regression that starts reading a
    live run's own journal/``state.json`` fails this test loudly, from
    inside the system under test, rather than silently returning a
    plausible-looking value that would mask the violation. ``_DeployRun``/
    ``_fold_deploy_journal`` (Marshal's OWN per-deploy-action paper trail
    under ``implementation-artifacts/runs/``, AD-6) are a DIFFERENT
    journal, reached via ``FsPort`` -- untouched by this fake."""

    def __init__(
        self,
        *,
        ledger_statuses: tuple[tuple[str, str], ...] = (),
        ledger_raises: bool = False,
        ledger_error_message: str = "sprint status file not found",
    ) -> None:
        self.ledger_statuses = ledger_statuses
        self.ledger_raises = ledger_raises
        self.ledger_error_message = ledger_error_message
        self.ledger_calls: list[Path] = []

    def ledger_story_statuses(self, path):
        self.ledger_calls.append(path)
        if self.ledger_raises:
            raise HarnessError(self.ledger_error_message)
        return self.ledger_statuses

    def __getattr__(self, name):
        def _forbidden(*args, **kwargs):
            raise AssertionError(
                f"run_reconcile_completions must never call HarnessPort.{name!r} "
                "-- CAP-4 isolation (AD-5) permits ONLY ledger_story_statuses"
            )

        return _forbidden


class _PartialCommitFailureVcs(_FakeVcs):
    """``_FakeVcs``'s own ``commit_raises`` is a single flag applied to
    EVERY ``commit_paths`` call, which cannot distinguish "the ledger's own
    commit fails" from "the spec's own commit fails" -- exactly the
    distinction this story's own I/O matrix row ("Ledger commit_paths
    fails ... spec promotion for other keys still attempted") requires a
    test to prove. This subclass fails ``commit_paths`` ONLY for the one
    call whose ``paths`` contains ``fail_path`` (the ledger), while
    ``attempted_paths`` logs EVERY call -- succeeded or failed -- so a
    test can assert both that the ledger commit was genuinely attempted
    (not skipped) and that the SEPARATE spec-promotion commit still
    succeeded independently."""

    def __init__(self, *, fail_path: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self.fail_path = fail_path
        self.attempted_paths: list[tuple] = []

    def commit_paths(self, repo_root, paths, message):
        self.attempted_paths.append(paths)
        if self.fail_path in paths:
            raise VcsCommandError("git commit failed for the ledger")
        self.commit_calls.append((paths, message))
        return "deadbeef"


def _write_ledger(tmp_path: Path, slug: str, text: str) -> Path:
    ledger_path = tmp_path / "_bmad-output" / "projects" / slug / "planning-artifacts" / "sprint-status-ledger.yaml"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(text, encoding="utf-8")
    return ledger_path


def _ledger_text(*entries: tuple[str, str]) -> str:
    lines = ["development_status:"]
    for raw_key, raw_status in entries:
        lines.append(f"  {raw_key}: {raw_status}")
    return "\n".join(lines) + "\n"


def _write_tier3_feed(tmp_path: Path, slug: str, text: str) -> Path:
    feed_path = tmp_path / "_bmad-output" / "projects" / slug / "implementation-artifacts" / "sprint-status.yaml"
    feed_path.parent.mkdir(parents=True, exist_ok=True)
    feed_path.write_text(text, encoding="utf-8")
    return feed_path


def _not_loop_native_subject(branch_segment: str, pr: int = 500) -> str:
    """A real GitHub PR-merge commit-subject shape -- the ONE remaining
    route this story exists to detect: a story landed via any route
    Marshal itself did not drive (reported as ``"not-loop-native"`` --
    typically a human-run ``bmad-quick-dev`` session merged as a plain
    PR, but never a templated or bmad-loop-native form, which this
    detection alone cannot distinguish from a ``marshal land`` landing;
    see ``core.promotion.marshal_native_merged_keys``'s own docstring)."""
    return f"Merge pull request #{pr} from rxm7706/acme/{branch_segment}"


def test_reconcile_completions_advances_and_promotes_a_not_loop_native_story(tmp_path, capsys, monkeypatch):
    """The headline scenario (I/O matrix row 1): a backlog story merged via
    a plain GitHub PR, with a valid, durable Tier-3 spec -- advances the
    ledger AND promotes the spec, in two dedicated commits, and closes
    the Tier-3 feed divergence for the same key (a pre-existing feed is
    set up here so this happy path stays finding-free; the feed-missing
    MRS-DEPLOY-027 case has its own dedicated test below)."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    ledger_path = _write_ledger(tmp_path, "acme", _ledger_text(("5-9-title", "backlog")))
    feed_path = _write_tier3_feed(tmp_path, "acme", "development_status:\n  5-9-title: backlog\n")
    vcs = _FakeVcs(main_subjects=(_not_loop_native_subject("5-9-title"),))
    harness = _FakeReconcileHarness(ledger_statuses=(("5-9-title", "backlog"),))

    exit_code = deploy_module.run_reconcile_completions(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["advanced"] == ["5.9"]
    assert payload["data"]["promoted"] == ["5.9"]
    assert payload["data"]["missing_from_ledger"] == []
    assert payload["findings"] == []
    assert payload["verdict"] == "clean"
    assert exit_code == 0

    assert "5-9-title: done" in ledger_path.read_text(encoding="utf-8")
    dest = _tracked_path(tmp_path, "acme", "5-9-title")
    assert dest.read_text(encoding="utf-8") == _VALID_SPEC
    # The Tier-3 feed's own divergence was also closed, since it existed.
    assert "5-9-title: done" in feed_path.read_text(encoding="utf-8")

    # Two dedicated commits, one per concern (AD-29's "only promotion
    # paths" precedent, applied symmetrically to the ledger commit too).
    # The Tier-3 feed repair-write is never git-committed (Tier-3 is
    # gitignored).
    assert len(vcs.commit_calls) == 2
    ledger_commit = next(c for c in vcs.commit_calls if c[0] == (ledger_path,))
    assert "advance" in ledger_commit[1]
    spec_commit = next(c for c in vcs.commit_calls if c[0] == (dest,))
    assert "promote" in spec_commit[1]


def test_reconcile_completions_missing_ledger_row_reports_mrs_deploy_026(tmp_path, capsys, monkeypatch):
    """I/O matrix row 2: corroborated and not-loop-native-landed, but the
    tracked ledger carries no row for it at all -- never advanced, never
    invented, reported. Spec promotion is a SEPARATE concern from the
    ledger advance: `to_promote_scoped` does not depend on the ledger's
    own advance set at all, so the spec IS still promoted here even
    though the ledger row is missing."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    _write_ledger(tmp_path, "acme", _ledger_text(("1-1-x", "done")))
    vcs = _FakeVcs(main_subjects=(_not_loop_native_subject("5-9-title"),))
    harness = _FakeReconcileHarness(ledger_statuses=(("1-1-x", "done"),))

    exit_code = deploy_module.run_reconcile_completions(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = json.loads(capsys.readouterr().out)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-DEPLOY-026" in codes
    finding = next(f for f in payload["findings"] if f["code"] == "MRS-DEPLOY-026")
    assert finding["severity"] == "warn"
    assert "5.9" in finding["message"]
    assert payload["data"]["missing_from_ledger"] == ["5.9"]
    assert payload["data"]["advanced"] == []
    assert payload["data"]["promoted"] == ["5.9"]
    assert exit_code == 0  # WARN never blocks
    # Exactly one commit -- the spec's own; the ledger was never touched
    # (no row to advance).
    dest = _tracked_path(tmp_path, "acme", "5-9-title")
    assert vcs.commit_calls == [((dest,), vcs.commit_calls[0][1])]


def test_reconcile_completions_excludes_a_marshal_native_landed_key(tmp_path, capsys, monkeypatch):
    """I/O matrix row 3: a story merged via the AD-24 templated form (what
    ``deploy land-story`` itself renders) is Marshal-driven -- Story 5.4's
    own sync already owns it, and reconcile-completions leaves it alone
    entirely."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "4-3-title", _VALID_SPEC)
    _write_ledger(tmp_path, "acme", _ledger_text(("4-3-title", "backlog")))
    # The default `merge_subject_template` (Story 50.4/FR-191 CAP-247:
    # "Merge {slug}/{key} into main") rendered for 4.3's hyphen form:
    # exactly what `land-story` itself writes.
    vcs = _FakeVcs(main_subjects=("Merge acme/4-3 into main",))
    harness = _FakeReconcileHarness(ledger_statuses=(("4-3-title", "backlog"),))

    exit_code = deploy_module.run_reconcile_completions(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["advanced"] == []
    assert payload["data"]["promoted"] == []
    assert payload["data"]["missing_from_ledger"] == []
    assert payload["findings"] == []
    assert exit_code == 0
    assert vcs.commit_calls == []


def test_reconcile_completions_git_match_without_corroborating_spec_is_silent(tmp_path, capsys, monkeypatch):
    """I/O matrix row 4: a bare git match with no valid/durable spec
    (possible cross-project collision) never triggers a write, and is not
    reported by THIS command -- Story 5.4's own ``--reconcile-ledger``
    already covers this direction."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    (tmp_path / "_bmad-output" / "projects" / "acme" / "implementation-artifacts").mkdir(parents=True, exist_ok=True)
    _write_ledger(tmp_path, "acme", _ledger_text(("7-1-title", "backlog")))
    vcs = _FakeVcs(main_subjects=(_not_loop_native_subject("7-1-title"),))
    harness = _FakeReconcileHarness(ledger_statuses=(("7-1-title", "backlog"),))

    exit_code = deploy_module.run_reconcile_completions(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = json.loads(capsys.readouterr().out)
    # Per this story's own I/O matrix: "Not advanced, not reported (5.4's
    # --reconcile-ledger already covers this)" -- reconcile-completions
    # never surfaces `_scan_promotions`'s own per-candidate promotion gaps
    # (MRS-DEPLOY-001/002, `deploy promote`'s own reporting concern); a
    # bare git match with no corroborating spec is silent here.
    assert payload["findings"] == []
    assert payload["data"]["advanced"] == []
    assert payload["data"]["promoted"] == []
    assert payload["data"]["missing_from_ledger"] == []
    assert payload["verdict"] == "clean"
    assert exit_code == 0
    assert vcs.commit_calls == []


def test_reconcile_completions_tracked_spec_alone_with_no_merge_evidence_never_advances(tmp_path, capsys, monkeypatch):
    """Review fix, 2026-08-12, high-severity: the contract's own "a git
    match alone never triggers a write" bullet reads BOTH directions -- a
    tracked spec alone (corroborated via `scan.already_promoted`, with NO
    merge evidence ANYWHERE in history) must never be sufficient either.
    `not_loop_native_candidates` now requires `corroborated_keys &
    full_merged_keys` (git's FULL three-pattern reachability), not
    `corroborated_keys` alone."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tracked_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    ledger_path = _write_ledger(tmp_path, "acme", _ledger_text(("5-9-title", "backlog")))
    vcs = _FakeVcs(main_subjects=())  # zero merge evidence anywhere in history
    harness = _FakeReconcileHarness(ledger_statuses=(("5-9-title", "backlog"),))

    exit_code = deploy_module.run_reconcile_completions(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = json.loads(capsys.readouterr().out)
    assert payload["findings"] == []
    assert payload["data"]["advanced"] == []
    assert payload["data"]["promoted"] == []
    assert payload["data"]["missing_from_ledger"] == []
    assert exit_code == 0
    assert vcs.commit_calls == []
    assert ledger_path.read_text(encoding="utf-8") == _ledger_text(("5-9-title", "backlog"))


def test_reconcile_completions_blocked_row_is_never_force_advanced(tmp_path, capsys, monkeypatch):
    """Review fix, 2026-08-12, medium-severity: a `blocked` ledger row is a
    DELIBERATE operator/process signal -- git+spec-corroborated evidence
    must never silently overwrite it. Spec promotion for the SAME key
    still proceeds independently -- it does not depend on the ledger's own
    row status at all."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    ledger_path = _write_ledger(tmp_path, "acme", _ledger_text(("5-9-title", "blocked")))
    vcs = _FakeVcs(main_subjects=(_not_loop_native_subject("5-9-title"),))
    harness = _FakeReconcileHarness(ledger_statuses=(("5-9-title", "blocked"),))

    exit_code = deploy_module.run_reconcile_completions(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["advanced"] == []
    assert payload["data"]["missing_from_ledger"] == []  # present, just not backlog
    assert payload["findings"] == []
    assert exit_code == 0
    assert ledger_path.read_text(encoding="utf-8") == _ledger_text(("5-9-title", "blocked"))
    assert (ledger_path,) not in [c[0] for c in vcs.commit_calls]
    assert payload["data"]["promoted"] == ["5.9"]


def test_reconcile_completions_in_progress_row_is_never_force_advanced(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    ledger_path = _write_ledger(tmp_path, "acme", _ledger_text(("5-9-title", "in-progress")))
    vcs = _FakeVcs(main_subjects=(_not_loop_native_subject("5-9-title"),))
    harness = _FakeReconcileHarness(ledger_statuses=(("5-9-title", "in-progress"),))

    exit_code = deploy_module.run_reconcile_completions(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["advanced"] == []
    assert exit_code == 0
    assert ledger_path.read_text(encoding="utf-8") == _ledger_text(("5-9-title", "in-progress"))


def test_reconcile_completions_already_done_key_is_a_clean_no_op(tmp_path, capsys, monkeypatch):
    """I/O matrix row 5: AD-21's convergence property -- a FULLY CONVERGED
    system (ledger already `done` AND the spec already promoted -- a key
    that is merely `done` in the ledger but NOT yet promoted is no longer
    a no-op for promotion; see the dedicated `already_promoted_spec_
    still_advances_the_ledger`/promotion-retry tests for that independent
    axis) produces zero changes and no finding on re-run."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    _write_tracked_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    ledger_path = _write_ledger(tmp_path, "acme", _ledger_text(("5-9-title", "done")))
    before = ledger_path.read_text(encoding="utf-8")
    vcs = _FakeVcs(main_subjects=(_not_loop_native_subject("5-9-title"),))
    harness = _FakeReconcileHarness(ledger_statuses=(("5-9-title", "done"),))

    exit_code = deploy_module.run_reconcile_completions(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["advanced"] == []
    assert payload["data"]["promoted"] == []
    assert payload["findings"] == []
    assert payload["verdict"] == "clean"
    assert exit_code == 0
    assert vcs.commit_calls == []
    assert ledger_path.read_text(encoding="utf-8") == before


def test_reconcile_completions_ledger_unreadable_degrades_to_report_only(tmp_path, capsys, monkeypatch):
    """I/O matrix row 6: the tracked ledger cannot be read at all -- the
    WHOLE run degrades to report-only, MRS-DEPLOY-024 (WARN), and never
    crashes."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    vcs = _FakeVcs(main_subjects=(_not_loop_native_subject("5-9-title"),))
    harness = _FakeReconcileHarness(ledger_raises=True, ledger_error_message="sprint status file not found: acme")

    exit_code = deploy_module.run_reconcile_completions(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = json.loads(capsys.readouterr().out)
    codes = [f["code"] for f in payload["findings"]]
    assert codes == ["MRS-DEPLOY-024"]
    assert payload["findings"][0]["severity"] == "warn"
    assert payload["verdict"] == "warn"
    assert exit_code == 0
    assert payload["data"]["advanced"] == []
    assert payload["data"]["promoted"] == []
    assert payload["data"]["missing_from_ledger"] == []
    assert vcs.commit_calls == []


def test_reconcile_completions_ledger_commit_failure_still_attempts_promotion(tmp_path, capsys, monkeypatch):
    """I/O matrix row 7: the ledger's OWN commit fails (MRS-DEPLOY-025,
    ERROR) -- but spec promotion for the SAME advanced key is still
    attempted, and succeeds, independently (two dedicated commits, one per
    concern). `data["advanced"]`/`data["advanced_count"]` report the REAL
    outcome of the write+commit sequence: empty here, even though the key
    was ELIGIBLE, because the commit itself never durably landed -- the
    finding explains why. The local write is rolled back (review fix,
    2026-08-12, high-severity), so the ledger's own on-disk text is back
    to its pre-advance state, never a stranded uncommitted `done`."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    ledger_path = _write_ledger(tmp_path, "acme", _ledger_text(("5-9-title", "backlog")))
    vcs = _PartialCommitFailureVcs(fail_path=ledger_path, main_subjects=(_not_loop_native_subject("5-9-title"),))
    harness = _FakeReconcileHarness(ledger_statuses=(("5-9-title", "backlog"),))

    exit_code = deploy_module.run_reconcile_completions(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = json.loads(capsys.readouterr().out)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-DEPLOY-025" in codes
    finding = next(f for f in payload["findings"] if f["code"] == "MRS-DEPLOY-025")
    assert finding["severity"] == "error"
    assert "rolled back" in finding["message"]
    assert exit_code != 0

    # Both commit attempts genuinely happened -- the ledger's own (which
    # failed) and the spec's own (which succeeded independently).
    assert len(vcs.attempted_paths) == 2
    assert (ledger_path,) in vcs.attempted_paths
    dest = _tracked_path(tmp_path, "acme", "5-9-title")
    assert (dest,) in vcs.attempted_paths
    assert vcs.commit_calls == [((dest,), vcs.commit_calls[0][1])]

    # The envelope's own `advanced` reports the REAL outcome -- empty,
    # since the ledger commit itself failed -- never the pre-write
    # eligibility set. Promotion succeeded independently regardless.
    assert payload["data"]["advanced"] == []
    assert payload["data"]["advanced_count"] == 0
    assert payload["data"]["promoted"] == ["5.9"]
    # The ledger's own on-disk text was ROLLED BACK to its pre-advance
    # state -- never a stranded uncommitted `done` a later run's own
    # harness-based read (which reads the working tree, not git) would
    # misread as already converged.
    assert ledger_path.read_text(encoding="utf-8") == _ledger_text(("5-9-title", "backlog"))


def test_reconcile_completions_ledger_commit_failure_recovers_on_a_later_run(tmp_path, capsys, monkeypatch):
    """Proves the rollback fix composes correctly for full recovery: a
    ledger commit failure this run rolls the local write back to its
    pre-advance text (review fix, 2026-08-12, high-severity -- a stranded
    uncommitted `done` used to make a LATER run's own harness-based read,
    which reads the WORKING TREE and not git, misread the key as already
    converged, excluding it PERMANENTLY), and reports an empty
    `advanced`. A LATER run, with NO test-side reset of any kind, finds
    the key genuinely still eligible and successfully retries the ledger
    advance. The spec itself was already promoted on the first run
    (promotion's own decoupling from the ledger's advance set), so the
    second run has nothing left to promote."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    ledger_path = _write_ledger(tmp_path, "acme", _ledger_text(("5-9-title", "backlog")))
    failing_vcs = _PartialCommitFailureVcs(
        fail_path=ledger_path, main_subjects=(_not_loop_native_subject("5-9-title"),)
    )
    harness = _FakeReconcileHarness(ledger_statuses=(("5-9-title", "backlog"),))

    first_exit = deploy_module.run_reconcile_completions(_args(), vcs=failing_vcs, fs=LocalFs(), harness=harness)
    first_payload = json.loads(capsys.readouterr().out)
    assert first_payload["data"]["advanced"] == []
    assert first_payload["data"]["promoted"] == ["5.9"]
    assert first_exit != 0
    assert ledger_path.read_text(encoding="utf-8") == _ledger_text(("5-9-title", "backlog"))

    # A LATER run: the failure is no longer simulated. NO test-side reset
    # of the ledger file -- the rollback above already restored it, and
    # the SAME `_FakeReconcileHarness` fixture is reused unmodified.
    non_failing_vcs = _FakeVcs(main_subjects=(_not_loop_native_subject("5-9-title"),))
    second_exit = deploy_module.run_reconcile_completions(_args(), vcs=non_failing_vcs, fs=LocalFs(), harness=harness)
    second_payload = json.loads(capsys.readouterr().out)

    assert second_payload["data"]["advanced"] == ["5.9"]
    assert second_payload["data"]["promoted"] == []  # already promoted, nothing left
    assert second_exit == 0
    assert "5-9-title: done" in ledger_path.read_text(encoding="utf-8")
    assert len(non_failing_vcs.commit_calls) == 1
    assert non_failing_vcs.commit_calls[0][0] == (ledger_path,)


def test_reconcile_completions_toctou_mismatch_reports_mrs_deploy_026_and_writes_nothing(tmp_path, capsys, monkeypatch):
    """Review fix, 2026-08-12, high-severity: `render_ledger_advancements`
    reports back which raw keys it actually matched -- a whole-batch match
    failure (modeled here by a ledger file whose real, on-disk raw key
    spelling differs from what the harness reports for the SAME dot-form
    key, simulating a rewrite between the harness-based read and the
    raw-text re-read) still emits a finding rather than silently doing
    and reporting nothing, and no ledger write/commit is attempted (spec
    promotion for the SAME key is a separate concern and still proceeds
    independently -- it does not depend on the ledger's own text match at
    all)."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    ledger_path = _write_ledger(tmp_path, "acme", _ledger_text(("5-9-a-different-raw-spelling", "backlog")))
    vcs = _FakeVcs(main_subjects=(_not_loop_native_subject("5-9-title"),))
    harness = _FakeReconcileHarness(ledger_statuses=(("5-9-title", "backlog"),))

    exit_code = deploy_module.run_reconcile_completions(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = json.loads(capsys.readouterr().out)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-DEPLOY-026" in codes
    finding = next(f for f in payload["findings"] if f["code"] == "MRS-DEPLOY-026")
    assert finding["severity"] == "warn"
    assert "5.9" in finding["message"]
    assert payload["data"]["advanced"] == []
    assert payload["data"]["promoted"] == ["5.9"]
    assert exit_code == 0  # WARN never blocks
    assert (ledger_path,) not in [paths for paths, _ in vcs.commit_calls]
    assert ledger_path.read_text(encoding="utf-8") == _ledger_text(("5-9-a-different-raw-spelling", "backlog"))


class _SpecsDirLockRaisingFs(LocalFs):
    """A ``FsPort`` wrapper (real ``LocalFs``/real ``fcntl.flock`` for the
    lock mechanics otherwise) whose ``acquire_advisory_lock`` raises
    ``FsError`` ONLY when the requested path is ``raising_path`` --
    proves the ledger's own advisory lock (``ledger_path.parent``, a
    SEPARATE resource) is independently acquirable even while
    ``_execute_promotion_plan``'s own ``specs_dir`` lock is contended."""

    def __init__(self, *, raising_path: Path) -> None:
        super().__init__()
        self._raising_path = raising_path

    def acquire_advisory_lock(self, path, *, timeout_s):
        if path == self._raising_path:
            raise FsError("simulated: another process holds this lock")
        return super().acquire_advisory_lock(path, timeout_s=timeout_s)


def test_reconcile_completions_promotion_lock_failure_is_retried_on_a_later_run(tmp_path, capsys, monkeypatch):
    """A promotion failure (lock contention on `specs_dir`) for a key
    whose ledger advancement SUCCEEDED in the SAME run does not orphan
    that key's promotion: `to_promote_scoped` is scoped to
    `not_loop_native_candidates` directly, independent of the ledger's own
    advance set, so a later run retries the promotion regardless of the
    ledger's already-`done` state."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    ledger_path = _write_ledger(tmp_path, "acme", _ledger_text(("5-9-title", "backlog")))
    vcs = _FakeVcs(main_subjects=(_not_loop_native_subject("5-9-title"),))
    harness = _FakeReconcileHarness(ledger_statuses=(("5-9-title", "backlog"),))
    specs_dir = _specs_dir(tmp_path, "acme")
    promotion_locked_fs = _SpecsDirLockRaisingFs(raising_path=specs_dir)

    first_exit = deploy_module.run_reconcile_completions(_args(), vcs=vcs, fs=promotion_locked_fs, harness=harness)
    first_payload = json.loads(capsys.readouterr().out)

    # The ledger advanced -- its OWN, separate lock on `ledger_path.parent`
    # succeeded -- even though the promotion lock on `specs_dir` failed.
    codes = [f["code"] for f in first_payload["findings"]]
    assert "MRS-DEPLOY-023" in codes
    assert first_payload["data"]["advanced"] == ["5.9"]
    assert first_payload["data"]["promoted"] == []
    assert first_exit == 0  # WARN never blocks
    assert "5-9-title: done" in ledger_path.read_text(encoding="utf-8")
    assert not _tracked_path(tmp_path, "acme", "5-9-title").exists()

    # Second run: the harness now reports the (now-`done`) ledger row --
    # `not_loop_native_completions` correctly excludes it (AD-21
    # convergence, already done, and no longer in `ledger_backlog_keys`)
    # -- but the spec is STILL promoted, proving `to_promote_scoped` no
    # longer depends on the (now-empty) `advanced_dot_keys` set.
    harness_second = _FakeReconcileHarness(ledger_statuses=(("5-9-title", "done"),))
    second_exit = deploy_module.run_reconcile_completions(_args(), vcs=vcs, fs=LocalFs(), harness=harness_second)
    second_payload = json.loads(capsys.readouterr().out)

    assert second_payload["data"]["advanced"] == []  # already done -- no-op
    assert second_payload["data"]["promoted"] == ["5.9"]
    assert second_exit == 0
    dest = _tracked_path(tmp_path, "acme", "5-9-title")
    assert dest.read_text(encoding="utf-8") == _VALID_SPEC


def test_reconcile_completions_ledger_lock_contention_reports_warn_and_skips_the_write(tmp_path, capsys, monkeypatch):
    """The ledger's own read-modify-write sequence acquires an advisory
    lock on the ledger's OWN parent directory (a SEPARATE resource from
    `_execute_promotion_plan`'s own `specs_dir` lock) -- proven here
    against a GENUINE, real `fcntl.flock` held by another thread (mirrors
    `test_promote_hits_the_real_contention_path_when_another_holder_has_
    the_lock`'s own real-contention style), not a simulated one. The
    second (foreground) run reports the WARN and never touches the
    ledger; spec promotion for the same key still proceeds independently.
    The lock now wraps the `ledger_story_statuses` READ too (review fix,
    2026-08-12, medium-severity, the TOCTOU fix): `harness.ledger_calls`
    is asserted EMPTY, proving the read itself never happens under
    contention, not merely that the write is skipped afterward."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(deploy_module, "_LEDGER_LOCK_TIMEOUT_S", 0.3)
    _write_tier3_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    ledger_path = _write_ledger(tmp_path, "acme", _ledger_text(("5-9-title", "backlog")))
    before = ledger_path.read_text(encoding="utf-8")
    vcs = _FakeVcs(main_subjects=(_not_loop_native_subject("5-9-title"),))
    harness = _FakeReconcileHarness(ledger_statuses=(("5-9-title", "backlog"),))

    holder_fs = LocalFs()
    release_event = threading.Event()
    held_event = threading.Event()

    def _hold_lock():
        lock = holder_fs.acquire_advisory_lock(ledger_path.parent, timeout_s=5.0)
        held_event.set()
        release_event.wait(timeout=5.0)
        holder_fs.release_advisory_lock(lock)

    holder = threading.Thread(target=_hold_lock, daemon=True)
    holder.start()
    try:
        assert held_event.wait(timeout=5.0), "background holder never acquired the real lock"

        exit_code = deploy_module.run_reconcile_completions(_args(), vcs=vcs, fs=LocalFs(), harness=harness)
    finally:
        release_event.set()
        holder.join(timeout=5.0)

    payload = json.loads(capsys.readouterr().out)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-DEPLOY-024" in codes
    assert payload["data"]["advanced"] == []
    assert payload["data"]["advanced_count"] == 0
    assert exit_code == 0  # WARN never blocks
    # Never touched, never corrupted, never double-written.
    assert ledger_path.read_text(encoding="utf-8") == before
    assert (ledger_path,) not in [paths for paths, _ in vcs.commit_calls]
    # The TOCTOU fix: the harness-based read itself never happens while
    # the lock is contended, not merely the write.
    assert harness.ledger_calls == []

    # Spec promotion for the SAME key still proceeds independently of the
    # ledger's own lock contention.
    assert payload["data"]["promoted"] == ["5.9"]


def test_reconcile_completions_dirty_ledger_skips_the_write_but_promotion_still_proceeds(tmp_path, capsys, monkeypatch):
    """A pre-existing uncommitted edit to the tracked ledger (an ordinary,
    expected case -- other writers, including bmad-loop itself, touch this
    file) must never be silently folded into this command's own commit --
    the write is skipped, WARN reported, and spec promotion for the SAME
    eligible key still proceeds independently in the same run."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    ledger_path = _write_ledger(tmp_path, "acme", _ledger_text(("5-9-title", "backlog")))
    before = ledger_path.read_text(encoding="utf-8")
    vcs = _FakeVcs(
        main_subjects=(_not_loop_native_subject("5-9-title"),),
        dirty_paths=frozenset({ledger_path}),
    )
    harness = _FakeReconcileHarness(ledger_statuses=(("5-9-title", "backlog"),))

    exit_code = deploy_module.run_reconcile_completions(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = json.loads(capsys.readouterr().out)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-DEPLOY-024" in codes
    finding = next(
        f for f in payload["findings"] if f["code"] == "MRS-DEPLOY-024" and "uncommitted changes" in f["message"]
    )
    assert finding["severity"] == "warn"
    assert payload["data"]["advanced"] == []
    assert payload["data"]["advanced_count"] == 0
    assert exit_code == 0
    assert ledger_path.read_text(encoding="utf-8") == before  # never touched
    assert (ledger_path,) not in [paths for paths, _ in vcs.commit_calls]

    assert payload["data"]["promoted"] == ["5.9"]


def test_reconcile_completions_already_promoted_spec_still_advances_the_ledger(tmp_path, capsys, monkeypatch):
    """A key corroborated via `scan.already_promoted` (a valid,
    git-committed tracked copy already exists in the archive --
    `_write_tracked_spec`) rather than `scan.plan.to_promote`, with the
    ledger row still `backlog`, AND with real merge evidence in history.
    Corroboration requires a durable, valid spec (`to_promote UNION
    already_promoted`) AND real merge evidence, so the ledger still
    advances to `done`; there is nothing left to promote for this key."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    _write_tracked_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    ledger_path = _write_ledger(tmp_path, "acme", _ledger_text(("5-9-title", "backlog")))
    _write_tier3_feed(tmp_path, "acme", "development_status:\n  5-9-title: backlog\n")
    vcs = _FakeVcs(main_subjects=(_not_loop_native_subject("5-9-title"),))
    harness = _FakeReconcileHarness(ledger_statuses=(("5-9-title", "backlog"),))

    exit_code = deploy_module.run_reconcile_completions(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = json.loads(capsys.readouterr().out)
    assert payload["findings"] == []
    assert payload["data"]["missing_from_ledger"] == []
    assert payload["data"]["advanced"] == ["5.9"]
    assert payload["data"]["promoted"] == []
    assert exit_code == 0
    assert "5-9-title: done" in ledger_path.read_text(encoding="utf-8")
    # Exactly one commit -- the ledger's own; nothing left to promote.
    assert len(vcs.commit_calls) == 1
    assert vcs.commit_calls[0][0] == (ledger_path,)


def test_reconcile_completions_ledger_commit_has_an_ad6_intent_outcome_pair(tmp_path, capsys, monkeypatch):
    """Review fix, 2026-08-12, medium-severity: the ledger commit -- this
    command's own headline durable write -- now has an AD-6 intent/
    outcome pair, like every sibling write command in this module
    (`run_promote`/`run_land_story`)."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    _write_ledger(tmp_path, "acme", _ledger_text(("5-9-title", "backlog")))
    vcs = _FakeVcs(main_subjects=(_not_loop_native_subject("5-9-title"),))
    harness = _FakeReconcileHarness(ledger_statuses=(("5-9-title", "backlog"),))

    exit_code = deploy_module.run_reconcile_completions(_args(), vcs=vcs, fs=LocalFs(), harness=harness)
    assert exit_code == 0

    journal_lines = _find_land_journal_lines(tmp_path, "acme")
    ledger_entries = [line for line in journal_lines if line["kind"] == deploy_module._LEDGER_COMMIT_KIND]
    intents = [e for e in ledger_entries if e["phase"] == "intent"]
    outcomes = [e for e in ledger_entries if e["phase"] == "outcome"]
    assert len(intents) == 1
    assert len(outcomes) == 1
    assert intents[0]["payload"]["story_keys"] == ["5.9"]
    assert outcomes[0]["payload"]["story_keys"] == ["5.9"]
    assert outcomes[0]["id"] != intents[0]["id"]


def test_reconcile_completions_reconciles_a_prior_open_ledger_intent(tmp_path, capsys, monkeypatch):
    """A crashed prior `reconcile-completions` run left an open intent for
    "3.8"; THIS run's own fresh ledger read confirms its row now reads
    `done` -- the intent is closed with a `reconciliation` outcome,
    mirroring `run_promote`'s own identical AD-6 x AD-21 x AD-28
    precondition."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_open_intent(
        tmp_path,
        "acme",
        run_id="prior-run-ledger",
        kind=deploy_module._LEDGER_COMMIT_KIND,
        story_keys=["3.8"],
    )
    vcs = _FakeVcs()
    harness = _FakeReconcileHarness(ledger_statuses=(("3-8-title", "done"),))

    exit_code = deploy_module.run_reconcile_completions(_args(), vcs=vcs, fs=LocalFs(), harness=harness)
    assert exit_code == 0

    journal_lines = _find_land_journal_lines(tmp_path, "acme")
    reconciliations = [
        line for line in journal_lines if line["phase"] == "outcome" and line["kind"] == "reconciliation"
    ]
    assert len(reconciliations) == 1
    assert reconciliations[0]["payload"]["reconciled_kind"] == deploy_module._LEDGER_COMMIT_KIND


def test_reconcile_completions_closes_the_tier3_feed_divergence_after_a_successful_advance(
    tmp_path, capsys, monkeypatch
):
    """Spec Change Log, 2026-08-12, item 2: after a successful ledger
    commit, the Tier-3 feed for the project is closed for exactly the
    advanced keys, reusing `scripts/promote_sprint_status.py`'s own
    repair-feed logic -- no separate `sprint-ledger-sync --repair-feed`
    invocation required by the operator."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    ledger_path = _write_ledger(tmp_path, "acme", _ledger_text(("5-9-title", "backlog")))
    feed_path = _write_tier3_feed(tmp_path, "acme", "development_status:\n  5-9-title: backlog\n")
    vcs = _FakeVcs(main_subjects=(_not_loop_native_subject("5-9-title"),))
    harness = _FakeReconcileHarness(ledger_statuses=(("5-9-title", "backlog"),))

    exit_code = deploy_module.run_reconcile_completions(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = json.loads(capsys.readouterr().out)
    assert payload["findings"] == []
    assert exit_code == 0
    assert "5-9-title: done" in ledger_path.read_text(encoding="utf-8")
    assert "5-9-title: done" in feed_path.read_text(encoding="utf-8")
    # The Tier-3 feed is gitignored -- never git-committed by this step.
    assert (feed_path,) not in [paths for paths, _ in vcs.commit_calls]


def test_reconcile_completions_missing_tier3_feed_reports_mrs_deploy_027_ledger_still_stands(
    tmp_path, capsys, monkeypatch
):
    """The ordinary case on a fresh clone/CI runner: no local Tier-3
    artifacts at all (`implementation-artifacts/` is gitignored). The
    repair-write cannot complete, so `MRS-DEPLOY-027` (WARN) is reported
    -- but the ledger commit already landed and stands regardless, never
    rolled back by a failed, best-effort repair step."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    ledger_path = _write_ledger(tmp_path, "acme", _ledger_text(("5-9-title", "backlog")))
    vcs = _FakeVcs(main_subjects=(_not_loop_native_subject("5-9-title"),))
    harness = _FakeReconcileHarness(ledger_statuses=(("5-9-title", "backlog"),))

    exit_code = deploy_module.run_reconcile_completions(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = json.loads(capsys.readouterr().out)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-DEPLOY-027" in codes
    finding = next(f for f in payload["findings"] if f["code"] == "MRS-DEPLOY-027")
    assert finding["severity"] == "warn"
    assert exit_code == 0  # WARN never blocks
    assert payload["data"]["advanced"] == ["5.9"]
    assert "5-9-title: done" in ledger_path.read_text(encoding="utf-8")
    assert (ledger_path,) in [paths for paths, _ in vcs.commit_calls]


def test_reconcile_completions_never_reads_or_writes_a_live_runs_own_journal(tmp_path, capsys, monkeypatch):
    """Story 5.9's own CAP-4 isolation AC, proven by a test: a live
    bmad-loop run mid-run on a DIFFERENT story, on the same station, is
    neither read from nor written to. ``_FakeReconcileHarness`` raises
    ``AssertionError`` for every ``HarnessPort`` method other than
    ``ledger_story_statuses`` (proof by construction); a REAL file
    standing in for that live run's own journal is asserted
    byte-identical before and after."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    _write_ledger(tmp_path, "acme", _ledger_text(("5-9-title", "backlog")))
    vcs = _FakeVcs(main_subjects=(_not_loop_native_subject("5-9-title"),))
    harness = _FakeReconcileHarness(ledger_statuses=(("5-9-title", "backlog"),))

    # A real file standing in for a DIFFERENT, live bmad-loop run's own
    # journal on the same station (mid-run, on a different story) --
    # bmad-loop's own on-disk shape (external to this repo, AD-3), never
    # read by this module directly. Distinct from Marshal's OWN per-
    # deploy-action journal under `implementation-artifacts/runs/`, which
    # THIS run legitimately writes to (AD-6) via `FsPort`, never
    # `HarnessPort`.
    live_run_journal = tmp_path / "loop-home" / ".bmad-loop" / "runs" / "live-run-id" / "journal.jsonl"
    live_run_journal.parent.mkdir(parents=True, exist_ok=True)
    live_run_journal.write_bytes(b'{"kind": "story-transition", "story": "9.1"}\n')
    before = live_run_journal.read_bytes()

    exit_code = deploy_module.run_reconcile_completions(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    after = live_run_journal.read_bytes()
    assert after == before

    ledger_path = tmp_path / "_bmad-output" / "projects" / "acme" / "planning-artifacts" / "sprint-status-ledger.yaml"
    assert harness.ledger_calls == [ledger_path]

    # Sanity: this was not a trivial no-op that happened to touch nothing
    # -- the run did real, correct work.
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["advanced"] == ["5.9"]
    assert exit_code == 0


def test_reconcile_completions_text_format_smoke(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    _write_ledger(tmp_path, "acme", _ledger_text(("5-9-title", "backlog")))
    vcs = _FakeVcs(main_subjects=(_not_loop_native_subject("5-9-title"),))
    harness = _FakeReconcileHarness(ledger_statuses=(("5-9-title", "backlog"),))

    exit_code = deploy_module.run_reconcile_completions(_args(format="text"), vcs=vcs, fs=LocalFs(), harness=harness)

    out = capsys.readouterr().out
    assert "deploy reconcile-completions" in out
    assert "advanced: 1 (5.9)" in out
    assert "promoted: 1 (5.9)" in out
    assert exit_code == 0


def test_reconcile_completions_subparser_is_registered():
    """The new ``reconcile-completions`` action parses without error and
    dispatches to ``run_reconcile_completions`` -- mirrors this module's
    own convention of a bare parser-wiring smoke test."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    deploy_module.add_deploy_subparser(subparsers)

    args = parser.parse_args(["deploy", "reconcile-completions", "--project", "acme", "--format", "json"])
    assert args.handler is deploy_module.run_reconcile_completions
    assert args.project == "acme"
    assert args.format == "json"


# --- Story 51.2: `_scan_promotions`'s worktree-aware discovery -------------
#
# The landing record follows the session's write, not the primary's
# directory: a dispatch worktree's own Tier-3 dir is a second, optional
# discovery source, read before that worktree is torn down. No existing
# test calls `_scan_promotions` directly (it was previously only exercised
# via `run_promote`) -- these do, reusing `_write_tier3_spec`/`_VALID_SPEC`.


def test_scan_promotions_worktree_only_copy_is_discovered(tmp_path, monkeypatch):
    """A spec written only into the worktree's Tier-3 dir (never the
    primary checkout's) still surfaces in ``plan.to_promote`` once its
    story key is merged."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    worktree = tmp_path / "wt"
    _write_tier3_spec(worktree, "acme", "1-2", _VALID_SPEC)
    vcs = _FakeVcs(main_subjects=("Merge acme/1-2 into main",))

    scan = deploy_module._scan_promotions(tmp_path, "acme", vcs=vcs, fs=LocalFs(), worktree=worktree)

    assert scan.plan is not None
    promoted = {str(candidate.story_key): candidate for candidate in scan.plan.to_promote}
    assert "1.2" in promoted
    assert promoted["1.2"].text == _VALID_SPEC


def test_scan_promotions_worktree_copy_wins_on_key_collision(tmp_path, monkeypatch):
    """When both the primary and the worktree have a Tier-3 copy for the
    same story key, the worktree's (appended last) is the one
    ``classify_promotion_candidates`` classifies -- later entry wins."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    primary_text = "---\ntitle: 'x'\nstatus: 'shipped'\n---\n\nprimary body\n"
    worktree_text = "---\ntitle: 'x'\nstatus: 'shipped'\n---\n\nworktree body\n"
    _write_tier3_spec(tmp_path, "acme", "1-2", primary_text)
    worktree = tmp_path / "wt"
    _write_tier3_spec(worktree, "acme", "1-2", worktree_text)
    vcs = _FakeVcs(main_subjects=("Merge acme/1-2 into main",))

    scan = deploy_module._scan_promotions(tmp_path, "acme", vcs=vcs, fs=LocalFs(), worktree=worktree)

    assert scan.plan is not None
    promoted = {str(candidate.story_key): candidate for candidate in scan.plan.to_promote}
    assert promoted["1.2"].text == worktree_text


def test_scan_promotions_worktree_with_no_twin_is_silent(tmp_path, monkeypatch):
    """A worktree given but whose Tier-3 dir has no matching file (or
    doesn't even exist) behaves exactly as ``worktree=None`` would -- no
    finding, no change to what's classified."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "1-2", _VALID_SPEC)
    worktree = tmp_path / "wt-empty"  # never created

    with_worktree = deploy_module._scan_promotions(
        tmp_path,
        "acme",
        vcs=_FakeVcs(main_subjects=("Merge acme/1-2 into main",)),
        fs=LocalFs(),
        worktree=worktree,
    )
    without_worktree = deploy_module._scan_promotions(
        tmp_path,
        "acme",
        vcs=_FakeVcs(main_subjects=("Merge acme/1-2 into main",)),
        fs=LocalFs(),
        worktree=None,
    )

    assert with_worktree.plan is not None and without_worktree.plan is not None
    with_keys = {str(c.story_key) for c in with_worktree.plan.to_promote}
    without_keys = {str(c.story_key) for c in without_worktree.plan.to_promote}
    assert with_keys == without_keys == {"1.2"}
    assert with_worktree.findings == without_worktree.findings == ()


def test_scan_promotions_default_worktree_is_byte_identical(tmp_path, monkeypatch):
    """Omitting ``worktree`` entirely must classify the same as passing
    ``worktree=None`` explicitly -- the three other ``_scan_promotions``
    callers never pass it."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "1-2", _VALID_SPEC)

    explicit_none = deploy_module._scan_promotions(
        tmp_path,
        "acme",
        vcs=_FakeVcs(main_subjects=("Merge acme/1-2 into main",)),
        fs=LocalFs(),
        worktree=None,
    )
    omitted = deploy_module._scan_promotions(
        tmp_path,
        "acme",
        vcs=_FakeVcs(main_subjects=("Merge acme/1-2 into main",)),
        fs=LocalFs(),
    )

    explicit_keys = {str(c.story_key) for c in explicit_none.plan.to_promote}
    omitted_keys = {str(c.story_key) for c in omitted.plan.to_promote}
    assert explicit_keys == omitted_keys == {"1.2"}
