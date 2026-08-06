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

    def commit_subjects(self, repo_root, ref):
        if ref == "origin/main":
            if self.origin_raises:
                raise VcsCommandError("no origin remote configured")
            return self.origin_subjects
        if ref == "main":
            if self.main_raises:
                raise VcsCommandError("corrupted repo, no main")
            return self.main_subjects
        raise VcsCommandError(f"unexpected ref {ref!r}")

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

    dest = _tracked_path(tmp_path, "acme", "1-2")
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
