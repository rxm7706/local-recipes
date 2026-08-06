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
