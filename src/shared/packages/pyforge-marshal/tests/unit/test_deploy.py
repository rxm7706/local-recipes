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
from pathlib import Path

import pytest

from pyforge.marshal.adapters.fs_local import LocalFs
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
        self.resolve_ref_sequence = (
            list(resolve_ref_sequence) if resolve_ref_sequence is not None else None
        )
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
    return (
        tmp_path
        / "_bmad-output"
        / "projects"
        / slug
        / "planning-artifacts"
        / "specs"
        / f"spec-{filename_key}.md"
    )


@pytest.fixture(autouse=True)
def _no_active_project_env(monkeypatch):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)


def test_promote_copies_and_commits_a_durable_unpromoted_spec(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "1-2-title", _VALID_SPEC)
    vcs = _FakeVcs(main_subjects=("Merge 1-2 into main",))

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
    vcs = _FakeVcs(main_subjects=("Merge 3-8 into main",))

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["promoted"] == []
    assert payload["data"]["already_promoted"] == ["3.8"]
    assert payload["data"]["gap_count"] == 0
    assert exit_code == 0
    assert vcs.commit_calls == []


def test_promote_reports_a_gap_for_a_merged_story_with_no_tier3_spec(
    tmp_path, capsys, monkeypatch
):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    (tmp_path / "_bmad-output" / "projects" / "acme" / "implementation-artifacts").mkdir(
        parents=True, exist_ok=True
    )
    vcs = _FakeVcs(main_subjects=("Merge 4.1 into main",))

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-001" in codes
    assert payload["data"]["gap_count"] == 1
    assert payload["verdict"] == "warn"
    assert exit_code == 0


def test_promote_reports_a_gap_for_an_invalid_tier3_spec_and_does_not_promote_it(
    tmp_path, capsys, monkeypatch
):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "2-3", "")  # zero-byte
    vcs = _FakeVcs(main_subjects=("Merge 2-3 into main",))

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-002" in codes
    assert payload["data"]["promoted"] == []
    assert exit_code == 0
    assert not _tracked_path(tmp_path, "acme", "2-3").exists()


def test_promote_never_overwrites_a_good_tracked_copy_with_a_broken_tier3_one(
    tmp_path, capsys, monkeypatch
):
    """The already-promoted check runs BEFORE validity of the Tier-3 copy is
    even consulted -- a good tracked copy is untouched regardless of the
    Tier-3 source's own state (AD-13's own "never promoted over a GOOD
    copy")."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "1-5", "")  # zero-byte in Tier-3
    _write_tracked_spec(tmp_path, "acme", "1-5", _VALID_SPEC)  # good tracked copy
    vcs = _FakeVcs(main_subjects=("Merge 1-5 into main",))

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["gap_count"] == 0
    assert payload["data"]["already_promoted"] == ["1.5"]
    assert exit_code == 0
    assert _tracked_path(tmp_path, "acme", "1-5").read_text(encoding="utf-8") == _VALID_SPEC


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
    vcs = _FakeVcs(main_subjects=("Merge 6-1 into main",), origin_raises=True)

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
    vcs = _FakeVcs(main_subjects=(), origin_subjects=("Merge 7-2 into main",))

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["promoted"] == ["7.2"]
    assert exit_code == 0


def test_promote_reports_hard_unevaluable_finding_when_main_read_fails(
    tmp_path, capsys, monkeypatch
):
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
    vcs = _FakeVcs(main_subjects=("Merge 8-4 into main",), commit_raises=True)

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-003" in codes
    assert payload["verdict"] == "unevaluable"
    assert exit_code == 1


def test_promote_zero_candidates_is_a_clean_empty_run(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    (tmp_path / "_bmad-output" / "projects" / "acme" / "implementation-artifacts").mkdir(
        parents=True, exist_ok=True
    )
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


def test_promote_with_a_malformed_slug_reports_mrs_policy_006_and_touches_nothing(
    tmp_path, capsys, monkeypatch
):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    vcs = _FakeVcs()

    exit_code = deploy_module.run_promote(
        _args(project="../escape"), vcs=vcs, fs=LocalFs()
    )

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
    vcs = _FakeVcs(main_subjects=("Merge 9-1 into main",), dirty_paths=frozenset({dest}))

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["promoted"] == ["9.1"]
    assert payload["data"]["already_promoted"] == []
    assert exit_code == 0
    assert len(vcs.commit_calls) == 1
    committed_paths, _ = vcs.commit_calls[0]
    assert committed_paths == (dest,)


def test_promote_never_trusts_a_tracked_copy_whose_status_is_unconfirmable(
    tmp_path, capsys, monkeypatch
):
    """When git itself cannot answer whether a tracked copy is committed
    (`path_has_uncommitted_changes` raising), the candidate must not be
    trusted as already-promoted -- fail safe, same shape as an invalid
    Tier-3 source."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "9-2", _VALID_SPEC)
    _write_tracked_spec(tmp_path, "acme", "9-2", _VALID_SPEC)
    vcs = _FakeVcs(main_subjects=("Merge 9-2 into main",), path_status_raises=True)

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
    (tmp_path / "_bmad-output" / "projects" / "acme" / "implementation-artifacts").mkdir(
        parents=True, exist_ok=True
    )
    vcs = _FakeVcs(main_subjects=("fastmcp-v4", "pixi update requires-pixi"))

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["subjects_examined"] == 2
    assert payload["data"]["subjects_matched"] == 0
    assert payload["data"]["promoted_count"] == 0
    assert exit_code == 0


def test_promote_recognizes_a_real_github_merge_subject(tmp_path, capsys, monkeypatch):
    """The spec-amendment's own live regression -- a real GitHub PR-merge
    subject (never the templated form) must be recognized as durable."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "2-3", _VALID_SPEC)
    vcs = _FakeVcs(
        main_subjects=(
            "Merge pull request #269 from rxm7706/marshal/2-3-frozen-surface-scope-check",
        )
    )

    exit_code = deploy_module.run_promote(_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["promoted"] == ["2.3"]
    assert payload["data"]["subjects_examined"] == 1
    assert payload["data"]["subjects_matched"] == 1
    assert exit_code == 0


def test_promote_text_format_renders_a_summary(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "1-2", _VALID_SPEC)
    vcs = _FakeVcs(main_subjects=("Merge 1-2 into main",))

    exit_code = deploy_module.run_promote(_args(format="text"), vcs=vcs, fs=LocalFs())

    output = capsys.readouterr().out
    assert "deploy promote:" in output
    assert "promoted: 1" in output
    assert exit_code == 0


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
            "Merge 1-2 into main",
            "Merge 1-3 into main",  # no Tier-3 spec at all -- missing
            "Merge 1-4 into main",
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
    vcs = _FakeVcs(main_subjects=("Merge 9-1 into main",))

    keys = deploy_module.unreachable_promotions_for_slug(tmp_path, "acme", vcs=vcs, fs=LocalFs())

    assert set(str(key) for key in keys) == {"9.1"}


def test_unreachable_promotions_for_slug_excludes_already_promoted(tmp_path):
    _write_tier3_spec(tmp_path, "acme", "3-8", _VALID_SPEC)
    _write_tracked_spec(tmp_path, "acme", "3-8", _VALID_SPEC)
    vcs = _FakeVcs(main_subjects=("Merge 3-8 into main",))

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
    vcs = _FakeVcs(main_subjects=("Merge 6-1 into main",))
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
    run_dir = (
        tmp_path
        / "_bmad-output"
        / "projects"
        / slug
        / "implementation-artifacts"
        / "runs"
        / run_id
    )
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


def test_recover_spec_reports_snapshots_most_recent_first_and_writes_nothing(
    tmp_path, capsys, monkeypatch
):
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
    dest = (
        tmp_path
        / "_bmad-output"
        / "projects"
        / "acme"
        / "implementation-artifacts"
        / "spec-4-2-recovered.md"
    )
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


def test_recover_spec_snapshot_search_does_not_match_a_numeric_prefix_collision(
    tmp_path, capsys, monkeypatch
):
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


def test_recover_spec_warns_when_acceptance_criteria_comes_back_empty(
    tmp_path, capsys, monkeypatch
):
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


def _land_args(
    *,
    slug: str = "acme",
    key: str = "4.3",
    justification: str | None = "landed manually, review did not converge",
    since: str | None = None,
    format: str = "json",
) -> argparse.Namespace:
    return argparse.Namespace(
        slug=slug, key=key, justification=justification, since=since, format=format
    )


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


def test_land_story_refuses_missing_justification_before_any_gate_run(
    tmp_path, capsys, monkeypatch
):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(gate_module, "evaluate_gate", _must_not_be_called)
    vcs = _FakeVcs()

    exit_code = deploy_module.run_land_story(
        _land_args(justification=None), vcs=vcs, fs=LocalFs()
    )

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

    exit_code = deploy_module.run_land_story(
        _land_args(justification="   "), vcs=vcs, fs=LocalFs()
    )

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-006" in codes
    assert exit_code != 0


def test_land_story_refuses_when_the_station_branch_does_not_exist(
    tmp_path, capsys, monkeypatch
):
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
            findings=(
                Finding(code="MRS-GATE-001", severity=Severity.ERROR, message=gate_finding["message"]),
            ),
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


def test_land_story_merges_with_a_rendered_subject_and_journals_on_green(
    tmp_path, capsys, monkeypatch
):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        gate_module, "evaluate_gate", _fake_evaluate_gate(verdict=Verdict.CLEAN)
    )
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        merge_base_sha="base-sha-123",
        merge_branch_sha="merge-sha-456",
        window_subjects=("Merge 4.3 into main",),
    )

    exit_code = deploy_module.run_land_story(_land_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["verdict"] == "clean"
    expected_subject = render_merge_subject(normalize("4.3"), "Merge {key} into main")
    assert payload["data"]["subject"] == expected_subject
    assert payload["data"]["merge_sha"] == "merge-sha-456"
    assert payload["data"]["non_conforming_merges"] == []
    # merge_branch is handed branch's CAPTURED tip sha (P4), not the bare
    # branch name -- see `resolve_ref`'s default return above.
    assert vcs.merge_branch_calls == [("branch-tip-sha", "main", expected_subject)]

    journal_lines = _find_land_journal_lines(tmp_path, "acme")
    assert len(journal_lines) == 1
    payload_entry = journal_lines[0]["payload"]
    assert payload_entry["story_key"] == "4.3"
    assert payload_entry["merge_sha"] == "merge-sha-456"
    assert payload_entry["gate_verdict"] == "clean"
    assert "landed manually" in payload_entry["justification"]
    assert journal_lines[0]["kind"] == "manual-landing"
    assert journal_lines[0]["phase"] == "observation"


def test_land_story_reports_non_conforming_merges_without_blocking(
    tmp_path, capsys, monkeypatch
):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        gate_module, "evaluate_gate", _fake_evaluate_gate(verdict=Verdict.CLEAN)
    )
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        window_subjects=("Merge 4.3 into main", "Merge pull request #42 from acme/feature"),
    )

    exit_code = deploy_module.run_land_story(_land_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["verdict"] == "clean"
    assert payload["data"]["non_conforming_merges"] == [
        "Merge pull request #42 from acme/feature"
    ]
    assert payload["findings"] == []


def test_land_story_conformance_audit_read_failure_warns_but_does_not_block(
    tmp_path, capsys, monkeypatch
):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        gate_module, "evaluate_gate", _fake_evaluate_gate(verdict=Verdict.CLEAN)
    )
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


def test_land_story_merge_failure_is_a_hard_stop_with_no_journal_entry(
    tmp_path, capsys, monkeypatch
):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        gate_module, "evaluate_gate", _fake_evaluate_gate(verdict=Verdict.CLEAN)
    )
    vcs = _FakeVcs(existing_branches=frozenset({"loop/acme"}), merge_branch_raises=True)

    exit_code = deploy_module.run_land_story(_land_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-008" in codes
    assert exit_code != 0
    assert "merge_sha" not in payload["data"]
    assert _find_land_journal_lines(tmp_path, "acme") == []


def test_land_story_uses_an_explicit_since_ref_over_the_computed_merge_base(
    tmp_path, capsys, monkeypatch
):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        gate_module, "evaluate_gate", _fake_evaluate_gate(verdict=Verdict.CLEAN)
    )

    class _RecordingVcs(_FakeVcs):
        def commit_subjects(self, repo_root, ref):
            self.last_ref = ref
            return super().commit_subjects(repo_root, ref)

    vcs = _RecordingVcs(existing_branches=frozenset({"loop/acme"}))

    exit_code = deploy_module.run_land_story(
        _land_args(since="explicit-ref"), vcs=vcs, fs=LocalFs()
    )

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


def test_land_story_policy_read_failure_is_a_hard_stop_no_merge_attempted(
    tmp_path, capsys, monkeypatch
):
    """P3 (both reviewers independently): a `PolicyIOError` resolving the
    merge-subject template must refuse the landing outright -- never fall
    through and merge with a silently-defaulted template (AD-24)."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(gate_module, "evaluate_gate", _must_not_be_called)
    fake_policy_path = tmp_path / "fake-marshal-policy.toml"
    fake_policy_path.write_text("not used -- _read_project_policy is patched", encoding="utf-8")
    monkeypatch.setattr(
        deploy_module, "conventional_project_policy_path", lambda slug: fake_policy_path
    )

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
    already_landed_subject = render_merge_subject(normalize("4.3"), "Merge {key} into main")
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


def test_land_story_refuses_when_branch_moves_during_the_gate_window(
    tmp_path, capsys, monkeypatch
):
    """P4: the gate evaluates `branch` at one point in time; a commit
    landing on `branch` before the merge actually runs must not be merged
    as if the (now-stale) gate result still applied to it."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        gate_module, "evaluate_gate", _fake_evaluate_gate(verdict=Verdict.CLEAN)
    )
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
    monkeypatch.setattr(
        gate_module, "evaluate_gate", _fake_evaluate_gate(verdict=Verdict.CLEAN)
    )
    monkeypatch.setattr(deploy_module, "_land_redact_text", lambda text: None)
    vcs = _FakeVcs(existing_branches=frozenset({"loop/acme"}))

    exit_code = deploy_module.run_land_story(_land_args(), vcs=vcs, fs=LocalFs())

    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-DEPLOY-012" in codes
    assert payload["verdict"] == "warn"
    assert exit_code == 0
    assert "merge_sha" in payload["data"]
    journal_lines = _find_land_journal_lines(tmp_path, "acme")
    assert len(journal_lines) == 1
    assert journal_lines[0]["payload"]["justification"] is None


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
        self.create_result = create_result or PrInfo(
            number=1, url="https://example/pr/1", state="open", base="main"
        )
        self.update_result = update_result or PrInfo(
            number=2, url="https://example/pr/2", state="open", base="main"
        )
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


def test_batch_pr_blocks_on_an_unsatisfied_required_check_and_writes_no_pr(
    tmp_path, capsys, monkeypatch
):
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
    monkeypatch.setattr(
        deploy_module, "conventional_project_policy_path", lambda slug: policy_path
    )
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
    monkeypatch.setattr(
        deploy_module, "conventional_project_policy_path", lambda slug: policy_path
    )
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


def test_batch_pr_applies_a_fired_label_after_opening_never_blocking(
    tmp_path, capsys, monkeypatch
):
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
    monkeypatch.setattr(
        deploy_module, "conventional_project_policy_path", lambda slug: policy_path
    )
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


def test_batch_pr_body_lists_the_wave_with_gate_verdicts_from_the_journal(
    tmp_path, capsys, monkeypatch
):
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    run_dir = (
        tmp_path
        / "_bmad-output"
        / "projects"
        / "acme"
        / "implementation-artifacts"
        / "runs"
        / "acme-run-1"
    )
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
    monkeypatch.setattr(
        deploy_module, "conventional_project_policy_path", lambda slug: policy_path
    )
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


def test_batch_pr_p2_add_labels_failure_does_not_claim_labels_applied(
    tmp_path, capsys, monkeypatch
):
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
    monkeypatch.setattr(
        deploy_module, "conventional_project_policy_path", lambda slug: policy_path
    )
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


def test_gather_gate_verdicts_p6_skips_a_run_dir_whose_fold_raises_non_typeerror(
    tmp_path, monkeypatch
):
    """P6 (MEDIUM, both reviewers): a run directory whose journal content
    makes `fold` raise something other than TypeError (e.g. ValueError)
    must be skipped, never crash the whole gather."""
    good_dir = (
        tmp_path / "_bmad-output" / "projects" / "acme" / "implementation-artifacts" / "runs" / "good"
    )
    bad_dir = (
        tmp_path / "_bmad-output" / "projects" / "acme" / "implementation-artifacts" / "runs" / "bad"
    )
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
            return _StubFoldResult(
                [_StubEntry("manual-landing", {"story_key": "4.4", "gate_verdict": "clean"})]
            )
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
        return json.dumps(
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
        ) + "\n"

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
