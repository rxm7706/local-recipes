"""Unit tests for ``cli/land.py`` (``marshal land``, Story 4.8, FR-60/AD-40).

Fake ``VcsPort``/``ForgePort`` doubles mirror ``tests/unit/test_deploy.py``'s
own established convention (hand-written classes implementing the Protocol,
never mocks); filesystem I/O runs against a REAL ``tmp_path`` via the real
``LocalFs``, same as every ``cli/deploy.py`` test.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pyforge.core.process import ProcessResult

from pyforge.marshal.adapters.fs_local import FsError, LocalFs
from pyforge.marshal.adapters.vcs_git import VcsCommandError
from pyforge.marshal.cli import deploy as deploy_module
from pyforge.marshal.cli import land as land_module
from pyforge.marshal.cli import spin as spin_module
from pyforge.marshal.core.identity import StoryKey, render_merge_subject
from pyforge.marshal.core.journal import JournalEntryId, Phase, build_entry, prepare_for_write
from pyforge.marshal.core.policy import DEFAULT_POLICY
from pyforge.marshal.ports.forge import ForgeCommandError, PrInfo
from pyforge.marshal.ports.harness import RunStatusSnapshot, TaskPhaseSnapshot

_BMADLOOP_WAVE_SUBJECT = "Merge bmad-loop/run-1/4-4-batch into loop/acme (bmad-loop)"
_DEFAULT_MERGE_SUBJECT_TEMPLATE = str(DEFAULT_POLICY["merge_subject_template"])


class _FakeVcs:
    """A minimal ``VcsPort`` stand-in exposing only what ``cli/land.py``
    calls -- mirrors ``tests/unit/test_deploy.py::_FakeVcs``'s own
    configurable-raise shape."""

    def __init__(
        self,
        *,
        existing_branches: frozenset = frozenset(),
        branch_exists_raises: bool = False,
        merge_base_sha: str = "base-sha",
        merge_base_raises: bool = False,
        wave_subjects: tuple[str, ...] = (),
        wave_subjects_raises: bool = False,
        base_subjects: tuple[str, ...] = (),
        base_subjects_raises: bool = False,
        resolve_ref_sha: str = "head-sha-abc",
        resolve_ref_raises: bool = False,
        worktree_head_sha: str | None = None,
        worktree_head_sha_raises: bool = False,
        changed_paths: tuple[str, ...] = (),
        changed_files_raises: bool = False,
        fetch_raises: bool = False,
        fast_forward_sha: str = "ff-sha",
        fast_forward_raises: bool = False,
        commit_paths_raises: bool = False,
        remote_ledger_text: str | None = None,
    ) -> None:
        self.existing_branches = existing_branches
        self.branch_exists_raises = branch_exists_raises
        self.merge_base_sha = merge_base_sha
        self.merge_base_raises = merge_base_raises
        self.wave_subjects = wave_subjects
        self.wave_subjects_raises = wave_subjects_raises
        self.base_subjects = base_subjects
        self.base_subjects_raises = base_subjects_raises
        self.resolve_ref_sha = resolve_ref_sha
        self.resolve_ref_raises = resolve_ref_raises
        self.resolve_ref_calls: list[str] = []
        self._worktree_head_sha = worktree_head_sha
        self.worktree_head_sha_raises = worktree_head_sha_raises
        self.changed_paths = changed_paths
        self.changed_files_raises = changed_files_raises
        self.fetch_raises = fetch_raises
        self.fetch_calls: list[tuple[object, str, str]] = []
        self.fast_forward_sha = fast_forward_sha
        self.fast_forward_raises = fast_forward_raises
        self.fast_forward_calls: list[tuple[object, str]] = []
        self.commit_paths_raises = commit_paths_raises
        self.commit_paths_calls: list[tuple[object, tuple[Path, ...], str]] = []
        self.isolated_promote_calls: list[tuple[object, str, str, tuple[tuple[str, str], ...], str]] = []
        # Story 68.1: the `preflight_skip_reason` each publish carried, parallel to the calls above.
        self.isolated_promote_reasons: list[str | None] = []
        self.remote_ledger_text = remote_ledger_text

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

    def commit_subjects(self, repo_root, ref):
        if ref == "refs/heads/main":
            if self.base_subjects_raises:
                raise VcsCommandError("corrupted repo, no main")
            return self.base_subjects
        if self.wave_subjects_raises:
            raise VcsCommandError("cannot enumerate the wave window")
        return self.wave_subjects

    def resolve_ref(self, repo_root, ref):
        self.resolve_ref_calls.append(ref)
        if self.resolve_ref_raises:
            raise VcsCommandError("git rev-parse --verify failed")
        return self.resolve_ref_sha

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

    def fetch(self, repo_root, remote, ref):
        self.fetch_calls.append((repo_root, remote, ref))
        if self.fetch_raises:
            raise VcsCommandError("git fetch failed: could not read from remote")

    def fast_forward(self, worktree_path, ref):
        self.fast_forward_calls.append((worktree_path, ref))
        if self.fast_forward_raises:
            raise VcsCommandError("git merge --ff-only failed: not possible to fast-forward, aborting")
        return self.fast_forward_sha

    def commit_paths(self, repo_root, paths, message):
        self.commit_paths_calls.append((repo_root, tuple(paths), message.text))
        if self.commit_paths_raises:
            raise VcsCommandError("git commit failed: nothing to commit (test double)")
        return "deferred-work-commit-sha"

    def file_text_at_ref(self, repo_root, ref, path):
        if self.remote_ledger_text is not None and str(path).endswith("sprint-status-ledger.yaml"):
            return self.remote_ledger_text
        candidate = Path(repo_root) / path
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
        return None

    def commit_paths_onto_remote_tip(self, repo_root, *, remote, ref, writes, message, preflight_skip_reason=None):
        self.isolated_promote_calls.append((repo_root, remote.value, ref.value, tuple(writes), message.text))
        self.isolated_promote_reasons.append(
            (preflight_skip_reason.text if preflight_skip_reason is not None else None)
        )
        if self.commit_paths_raises:
            raise VcsCommandError("git push failed: non-fast-forward (test double)")
        for rel, content in writes:
            dest = Path(repo_root) / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
        self.commit_paths_calls.append((repo_root, tuple(Path(rel) for rel, _ in writes), message.text))
        return "isolated-promote-sha"


class _FakeForge:
    """A minimal ``ForgePort`` stand-in -- mirrors
    ``tests/unit/test_deploy.py::_FakeForge``'s own shape, plus Story 4.8's
    ``merge_pr``."""

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
        merge_raises: bool = False,
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
        self.merge_raises = merge_raises
        self.find_calls: list = []
        self.create_calls: list = []
        self.update_calls: list = []
        self.add_labels_calls: list = []
        self.check_calls: list = []
        self.merge_calls: list = []

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

    def merge_pr(self, repo, number, strategy, *, expected_head_sha, delete_branch, subject=None):
        self.merge_calls.append(
            (
                repo,
                number,
                strategy.value,
                expected_head_sha.value,
                delete_branch,
                subject.value if subject is not None else None,
            )
        )
        if self.merge_raises:
            raise ForgeCommandError("gh pr merge failed")


def _args(*, slug: str = "acme", format: str = "json", retire_live_branch: bool = False) -> argparse.Namespace:
    return argparse.Namespace(slug=slug, format=format, retire_live_branch=retire_live_branch)


@pytest.fixture(autouse=True)
def _no_active_project_env(monkeypatch):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)


def _write_project_policy(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "land-marshal-policy.toml"
    path.write_text(text, encoding="utf-8")
    return path


def _patch_repo(monkeypatch, tmp_path, *, policy_path: Path | None = None) -> None:
    monkeypatch.setattr(land_module, "repo_root", lambda: tmp_path)
    if policy_path is not None:
        monkeypatch.setattr(land_module, "conventional_project_policy_path", lambda slug: policy_path)


def _payload(capsys):
    """Parses ``land``'s own (and ONLY) envelope off stdout. ``run_land``
    resyncs via ``cli/deploy.py::reconcile_feed`` -- the non-printing core
    ``run_refresh_feed`` itself calls before its own ``_emit`` -- so a
    resync never prints a second envelope; ``land``'s own ``_emit`` is the
    single JSON document on stdout."""
    text = capsys.readouterr().out
    return json.loads(text)


# --- preconditions -----------------------------------------------------


def test_malformed_slug_refuses_before_any_io(tmp_path, capsys, monkeypatch):
    _patch_repo(monkeypatch, tmp_path)
    vcs = _FakeVcs()
    forge = _FakeForge()

    exit_code = land_module.run_land(_args(slug="../evil"), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-POLICY-006" in codes
    assert exit_code != 0
    assert forge.find_calls == []


def test_station_branch_missing_refuses(tmp_path, capsys, monkeypatch):
    _patch_repo(monkeypatch, tmp_path)
    vcs = _FakeVcs(existing_branches=frozenset())
    forge = _FakeForge()

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-001" in codes
    assert exit_code != 0
    assert forge.find_calls == []


def test_malformed_landing_rules_hard_refuses(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, 'landing_rules = "not-a-list"\n')
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    vcs = _FakeVcs(existing_branches=frozenset({"loop/acme"}))
    forge = _FakeForge()

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-002" in codes
    assert exit_code != 0
    assert forge.find_calls == []


def test_a_malformed_landing_base_branch_hard_refuses(tmp_path, capsys, monkeypatch):
    """Story 61.1 review 1: `land` would otherwise fall back to `main` and merge there."""
    policy_path = _write_project_policy(tmp_path, 'landing_base_branch = "origin/release"\n')
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    vcs = _FakeVcs(existing_branches=frozenset({"loop/acme"}))
    forge = _FakeForge()

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert [f["code"] for f in payload["findings"]] == ["MRS-POLICY-002", "MRS-LAND-002"]
    assert "'landing_base_branch'" in payload["findings"][1]["message"]
    assert exit_code != 0
    assert forge.find_calls == [] and forge.merge_calls == []


# --- empty / already-landed wave -----------------------------------------


def test_empty_wave_is_a_clean_noop(tmp_path, capsys, monkeypatch):
    _patch_repo(monkeypatch, tmp_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=("an ordinary commit, not a story merge",),
    )
    forge = _FakeForge()

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert payload["data"]["wave"] == []
    assert payload["data"]["opened"] is False
    assert payload["data"]["updated"] is False
    assert payload["data"]["merged"] is False
    assert payload["verdict"] == "clean"
    assert exit_code == 0
    assert forge.find_calls == []


def test_already_landed_wave_branch_still_open_reports_warn(tmp_path, capsys, monkeypatch):
    _patch_repo(monkeypatch, tmp_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        base_subjects=(_BMADLOOP_WAVE_SUBJECT,),
    )
    existing_pr = PrInfo(number=5, url="https://example/pr/5", state="open", base="main")
    forge = _FakeForge(existing=existing_pr)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-003" in codes
    assert payload["data"]["already_landed"] is True
    assert payload["data"]["merged"] is True
    assert payload["data"]["branch_retired"] is None
    # MRS-LAND-003 is WARN-tier -- reported, never blocking (the landing
    # already happened; only its own retirement bookkeeping is unconfirmed).
    assert exit_code == 0
    assert forge.create_calls == []
    assert forge.merge_calls == []
    # Story 5.10: the already-landed shortcut never calls `merge_pr`, so no
    # subject is ever rendered -- byte-identical to before this story.
    assert "subject" not in payload["data"]


def test_already_landed_wave_branch_gone_is_clean(tmp_path, capsys, monkeypatch):
    _patch_repo(monkeypatch, tmp_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        base_subjects=(_BMADLOOP_WAVE_SUBJECT,),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert payload["data"]["already_landed"] is True
    assert payload["data"]["merged"] is True
    assert payload["data"]["branch_retired"] is True
    assert payload["verdict"] == "clean"
    assert exit_code == 0
    assert forge.merge_calls == []
    assert "subject" not in payload["data"]


# --- happy path: opens a PR, all checks green, merges --------------------


def _rule_policy(*, required_check: str | None = "environment-yaml-sync") -> str:
    if required_check is None:
        return (
            "[[landing_rules]]\n"
            'name = "maintenance-label"\n'
            'trigger_path_glob = "recipes/**"\n'
            'trigger_mode = "exclude"\n'
            'label = "maintenance"\n'
        )
    return (
        "[[landing_rules]]\n"
        'name = "environment-yaml-sync"\n'
        'trigger_path_glob = "pixi.toml"\n'
        'trigger_mode = "include"\n'
        f'required_check = "{required_check}"\n'
        "ungated = true\n"
    )


def test_happy_path_opens_pr_polls_checks_and_merges(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, _rule_policy())
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("pixi.toml",),
    )
    forge = _FakeForge(existing=None, check_status_map={"environment-yaml-sync": "success"})

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert payload["data"]["opened"] is True
    assert payload["data"]["merged"] is True
    assert payload["data"]["branch_retired"] is True
    assert payload["verdict"] == "clean"
    assert exit_code == 0
    assert len(forge.merge_calls) == 1
    repo, number, strategy, expected_head_sha, delete_branch, subject = forge.merge_calls[0]
    assert number == 1
    assert strategy == "merge"
    assert expected_head_sha
    assert delete_branch is True
    # Story 5.10: the single-key wave's rendered merge subject (AD-24),
    # threaded to `forge.merge_pr` and surfaced in `data["subject"]`.
    expected_subject = render_merge_subject(StoryKey(4, 4), _DEFAULT_MERGE_SUBJECT_TEMPLATE, "acme")
    assert subject == expected_subject
    assert payload["data"]["subject"] == expected_subject


def test_a_malformed_merge_subject_template_lands_with_the_default_subject(tmp_path, capsys, monkeypatch):
    """Story 82.3 (DW-5-10-1): a project ``merge_subject_template`` without exactly one ``{key}`` used
    to compose cleanly and then raise a bare ``ValueError`` out of ``render_merge_subject`` -- an
    uncaught traceback from a full merge. Composition now rejects it (``MRS-POLICY-002``) and the
    landing renders the default template instead."""
    policy_path = _write_project_policy(tmp_path, 'merge_subject_template = "Merge into main"\n' + _rule_policy())
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("pixi.toml",),
    )
    forge = _FakeForge(existing=None, check_status_map={"environment-yaml-sync": "success"})

    land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert "MRS-POLICY-002" in [f["code"] for f in payload["findings"]]
    expected_subject = render_merge_subject(StoryKey(4, 4), _DEFAULT_MERGE_SUBJECT_TEMPLATE, "acme")
    assert payload["data"]["subject"] == expected_subject
    assert forge.merge_calls[0][-1] == expected_subject


def test_render_text_land_reports_subject_line_on_a_full_merge(tmp_path, capsys, monkeypatch):
    """Story 5.10: `_render_text_land` gains one `subject: ...` line, gated
    on `"subject" in data`, mirroring `cli/deploy.py::_render_text_land_
    story`'s own precedent -- untested by every JSON-envelope assertion
    above, which never exercises the text renderer."""
    policy_path = _write_project_policy(tmp_path, _rule_policy())
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("pixi.toml",),
    )
    forge = _FakeForge(existing=None, check_status_map={"environment-yaml-sync": "success"})

    exit_code = land_module.run_land(_args(format="text"), vcs=vcs, fs=LocalFs(), forge=forge)

    rendered = capsys.readouterr().out
    assert exit_code == 0
    expected_subject = render_merge_subject(StoryKey(4, 4), _DEFAULT_MERGE_SUBJECT_TEMPLATE, "acme")
    assert f"subject: {expected_subject!r}" in rendered


def test_zero_applicable_required_check_rules_makes_no_check_calls(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert payload["data"]["merged"] is True
    assert exit_code == 0
    assert forge.check_calls == []
    assert payload["data"]["required_checks"] == []


def test_rule_with_both_label_and_required_check_applies_label_once_satisfied(tmp_path, capsys, monkeypatch):
    """Code review (2026-08-06, both reviewers independently): a landing
    rule declaring BOTH ``label`` and ``required_check`` (``core.landing.
    LandingRule`` explicitly permits this combination) previously never got
    its label applied under ``land`` at all -- it was excluded from
    ``_evaluate_hygiene``'s label-only subset, and the required-check path
    never collected labels. `_evaluate_required_checks` now fires the
    rule's own label once ITS OWN check reads ``"success"``."""
    policy_path = _write_project_policy(
        tmp_path,
        "[[landing_rules]]\n"
        'name = "sync-and-tag"\n'
        'trigger_path_glob = "pixi.toml"\n'
        'trigger_mode = "include"\n'
        'required_check = "environment-yaml-sync"\n'
        'label = "maintenance"\n'
        "ungated = true\n",
    )
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("pixi.toml",),
    )
    forge = _FakeForge(existing=None, check_status_map={"environment-yaml-sync": "success"})

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert exit_code == 0
    assert payload["data"]["merged"] is True
    assert payload["data"]["labels_applied"] == ["maintenance"]
    assert len(forge.add_labels_calls) == 1
    assert forge.add_labels_calls[0][2] == ("maintenance",)


# --- required-check matrix ------------------------------------------------


def test_required_check_failure_blocks_merge(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, _rule_policy())
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("pixi.toml",),
    )
    forge = _FakeForge(existing=None, check_status_map={"environment-yaml-sync": "failure"})

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-004" in codes
    assert payload["verdict"] == "gate-failed"
    assert payload["data"]["merged"] is False
    assert exit_code != 0
    assert forge.merge_calls == []
    # The PR was still opened -- required-check evaluation only GATES the
    # merge; a red/pending check never blocks opening/updating the PR
    # itself (the code review fix moved the poll BEFORE the PR write so a
    # combined label+required_check rule's label can still fire, but the
    # merge gate below still reuses these same results, never re-polling).
    assert payload["data"]["opened"] is True


def test_required_check_error_does_not_drop_an_unrelated_rules_pending_warn(tmp_path, capsys, monkeypatch):
    """Code review (2026-08-06, Edge Case Hunter): a WARN finding for one
    still-pending rule was previously dropped entirely whenever a
    DIFFERENT rule's check had already failed outright -- both must always
    be reported."""
    policy_path = _write_project_policy(
        tmp_path,
        "[[landing_rules]]\n"
        'name = "check-a"\n'
        'trigger_path_glob = "pixi.toml"\n'
        'trigger_mode = "include"\n'
        'required_check = "check-a"\n'
        "ungated = true\n\n"
        "[[landing_rules]]\n"
        'name = "check-b"\n'
        'trigger_path_glob = "pixi.toml"\n'
        'trigger_mode = "include"\n'
        'required_check = "check-b"\n'
        "ungated = true\n",
    )
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("pixi.toml",),
    )
    forge = _FakeForge(existing=None, check_status_map={"check-a": "failure", "check-b": None})

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-004" in codes
    assert "MRS-LAND-005" in codes
    assert payload["data"]["merged"] is False
    assert exit_code != 0
    assert forge.merge_calls == []


def test_required_check_pending_blocks_this_run_but_is_warn_tier(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, _rule_policy())
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("pixi.toml",),
    )
    forge = _FakeForge(existing=None, check_status_map={"environment-yaml-sync": None})

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-005" in codes
    assert "MRS-LAND-006" in codes  # unacknowledged -> escalated
    assert payload["data"]["merged"] is False
    assert exit_code != 0
    assert forge.merge_calls == []


def test_required_check_pending_and_acknowledged_proceeds_to_merge(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, _rule_policy())
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    ack_path = tmp_path / "ack" / "adapter-acknowledgements.json"
    ack_path.parent.mkdir(parents=True, exist_ok=True)
    # Scoped ack key (code review, 2026-08-06): acknowledging the bare
    # `MRS-LAND-005` code would bypass EVERY project/rule/check's pending
    # gate forever -- only THIS rule/check/project's own key is written.
    scoped_key = land_module._required_check_ack_key("environment-yaml-sync", "environment-yaml-sync", "acme")
    ack_path.write_text(json.dumps([scoped_key]), encoding="utf-8")
    # `run_land` imports `_ack_state_path` LOCALLY from `cli/init.py` on
    # every call, so patching `init_module`'s own attribute (not
    # `land_module`'s) is what actually takes effect.
    from pyforge.marshal.cli import init as init_module

    monkeypatch.setattr(init_module, "_ack_state_path", lambda: ack_path)

    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("pixi.toml",),
    )
    forge = _FakeForge(existing=None, check_status_map={"environment-yaml-sync": None})

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-005" in codes
    assert "MRS-LAND-006" not in codes
    assert payload["data"]["merged"] is True
    assert exit_code == 0
    assert len(forge.merge_calls) == 1


# --- merge_pr failure -----------------------------------------------------


def test_merge_pr_failure_reports_error_and_leaves_intent_open(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None, merge_raises=True)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-007" in codes
    assert payload["data"]["merged"] is False
    assert exit_code != 0


# --- landing_branch_retirement / landing_resync policy gates -------------


def test_branch_retirement_false_merges_without_deleting_branch(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(
        tmp_path, "landing_branch_retirement = false\n" + _rule_policy(required_check=None)
    )
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert exit_code == 0
    assert payload["data"]["branch_retired"] is False
    repo, number, strategy, expected_head_sha, delete_branch, subject = forge.merge_calls[0]
    assert delete_branch is False


def test_landing_resync_false_skips_resync(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, "landing_resync = false\n" + _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert exit_code == 0
    assert payload["data"]["resynced"] is False


def test_landing_resync_true_calls_refresh_feed_once(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    calls: list[object] = []
    from pyforge.marshal.cli import deploy as deploy_module

    def _spy_reconcile_feed(refresh_args, **kwargs):
        calls.append(refresh_args)
        return {"slug": refresh_args.project}, []

    monkeypatch.setattr(deploy_module, "reconcile_feed", _spy_reconcile_feed)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert exit_code == 0
    assert payload["data"]["resynced"] is True
    assert len(calls) == 1
    assert calls[0].project == "acme"


# =====================================================================
# Story 4.12 (FR-173): a landing leaves the loop home current with `main`.
# `_resync_home_branch` runs from ALL THREE of `run_land`'s own
# wave-outcome exits (the `if not wave_keys` no-op, the already-landed
# shortcut, and the full-merge path) -- `git_repo_root` for every `_FakeVcs`
# call is the fixed `Path("/fake-repo-root")` `repo_common_root` always
# returns, regardless of which exit is under test.
# =====================================================================


def test_resync_home_branch_no_op_wave_still_fast_forwards_home(tmp_path, capsys, monkeypatch):
    """The story's own PRIMARY scenario: `if not wave_keys` is a clean
    no-op (nothing merged since the last landing), but between-runs drift
    accumulates exactly here, whether or not anything new landed this
    invocation -- FR-173's resync must still run."""
    _patch_repo(monkeypatch, tmp_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=("an ordinary commit, not a story merge",),
    )
    forge = _FakeForge()

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert payload["data"]["wave"] == []
    assert payload["data"]["home_current"] is True
    assert exit_code == 0
    assert vcs.fetch_calls == [(Path("/fake-repo-root"), "origin", "main")]
    assert len(vcs.fast_forward_calls) == 1
    assert vcs.fast_forward_calls[0][1] == "refs/remotes/origin/main"
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-009" not in codes


def test_resync_home_branch_already_landed_wave_still_fast_forwards_home(tmp_path, capsys, monkeypatch):
    _patch_repo(monkeypatch, tmp_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        base_subjects=(_BMADLOOP_WAVE_SUBJECT,),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert payload["data"]["already_landed"] is True
    assert payload["data"]["home_current"] is True
    assert exit_code == 0
    assert len(vcs.fast_forward_calls) == 1


def test_resync_home_branch_full_merge_path_sets_home_current_true(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert payload["data"]["merged"] is True
    assert payload["data"]["home_current"] is True
    assert exit_code == 0
    assert len(vcs.fast_forward_calls) == 1
    assert vcs.fast_forward_calls[0][1] == "refs/remotes/origin/main"


def test_resync_home_branch_diverged_reports_warn_and_home_current_false(tmp_path, capsys, monkeypatch):
    """`fast_forward` refuses whenever `loop/<slug>` is not an ancestor of
    the fetched `origin/<base>` -- the exact shape a LIVE bmad-loop run that
    kept committing to the branch past the landed wave produces (this
    story's own Design Notes: safety comes from `--ff-only`'s own atomicity
    alone, with no dependency on Story 4.11's `is_run_live` predicate). The
    fake exercises the one failure branch `_resync_home_branch` has for
    this condition; a real, diverged git branch is proven separately by
    `tests/unit/test_vcs_git.py::test_fast_forward_refuses_a_diverged_branch`."""
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
        fast_forward_raises=True,
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-009" in codes
    message = payload["findings"][codes.index("MRS-LAND-009")]["message"]
    assert "loop/acme" in message
    assert payload["data"]["merged"] is True
    assert payload["data"]["home_current"] is False
    assert payload["verdict"] == "warn"
    # MRS-LAND-009 is WARN-tier -- reported, never blocking: the wave's own
    # landing already succeeded by the time this best-effort step runs.
    assert exit_code == 0


def test_resync_home_branch_fetch_failure_reports_warn(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
        fetch_raises=True,
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-009" in codes
    assert payload["data"]["merged"] is True
    assert payload["data"]["home_current"] is False
    assert exit_code == 0
    # fast_forward is never attempted once fetch has already failed.
    assert vcs.fast_forward_calls == []


def test_resync_home_branch_skips_fast_forward_when_home_has_drifted_off_head_branch(tmp_path, capsys, monkeypatch):
    """Code review (2026-08-10): `fast_forward` itself only asks "is this a
    fast-forward from whatever HEAD currently is" -- without a prior
    identity check, a `home` that drifted onto a different ref (or a
    detached HEAD) would get THAT ref silently advanced while `head_branch`
    stayed stale, yet `home_current` would still report `True`. Reusing
    `worktree_head_sha` != `resolve_ref(head_branch)` (the SAME pair
    `MRS-DEPLOY-017` already uses in the full-merge path) catches this
    before any fetch/fast-forward is attempted. Exercised via the no-op
    (`if not wave_keys`) exit -- the full-merge path (a THIRD call site, not
    exercised here) already runs its own, earlier `MRS-DEPLOY-017` identity
    check before ever reaching `_resync_home_branch`, which would mask this
    guard's own independent failure mode there; the already-landed shortcut
    has no such pre-check of its own and is covered separately below
    (`test_resync_home_branch_already_landed_reports_warn_when_home_has_drifted`)."""
    _patch_repo(monkeypatch, tmp_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=("an ordinary commit, not a story merge",),
        worktree_head_sha="some-other-checked-out-sha",
    )
    forge = _FakeForge()

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert payload["data"]["wave"] == []
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-009" in codes
    message = payload["findings"][codes.index("MRS-LAND-009")]["message"]
    assert "some-other-checked-out-sha" in message
    assert payload["data"]["home_current"] is False
    assert exit_code == 0
    # Neither fetch nor fast_forward is attempted once the identity check
    # itself has already failed.
    assert vcs.fetch_calls == []
    assert vcs.fast_forward_calls == []


def test_resync_home_branch_skipped_when_resync_disabled(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, "landing_resync = false\n" + _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert exit_code == 0
    assert "home_current" not in payload["data"]
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-009" not in codes
    assert vcs.fetch_calls == []
    assert vcs.fast_forward_calls == []


def test_resync_home_branch_skipped_when_merge_strategy_is_not_merge(tmp_path, capsys, monkeypatch):
    """Boundaries & Constraints (corrected 2026-08-09): this resync
    capability applies ONLY when `landing_merge_strategy == "merge"` --
    under `"squash"`/`"rebase"` the landed commits are never ancestors of
    `origin/<base>`, so a fast-forward is impossible BY CONSTRUCTION, on
    every invocation, permanently. The skip is silent by design: no fetch,
    no fast_forward attempt, no MRS-LAND-009, and `data["home_current"]` is
    ABSENT -- byte-identical in shape to `resync_enabled=False`."""
    policy_path = _write_project_policy(
        tmp_path,
        'landing_merge_strategy = "squash"\n' + _rule_policy(required_check=None),
    )
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert exit_code == 0
    assert "home_current" not in payload["data"]
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-009" not in codes
    assert vcs.fetch_calls == []
    assert vcs.fast_forward_calls == []


def test_resync_home_branch_already_landed_reports_warn_when_home_has_drifted(tmp_path, capsys, monkeypatch):
    """Code review (this pass): the already-landed shortcut has no
    `MRS-DEPLOY-017`-style pre-check of its own before reaching
    `_resync_home_branch` -- unlike the full-merge path, ITS identity-drift
    detection is exercised ONLY by this guard. The existing already-landed
    test (`test_resync_home_branch_already_landed_wave_still_fast_forwards_
    home`) only covers the matching-identity success path; this covers the
    mismatch."""
    _patch_repo(monkeypatch, tmp_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        base_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        worktree_head_sha="some-other-checked-out-sha",
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert payload["data"]["already_landed"] is True
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-009" in codes
    assert payload["data"]["home_current"] is False
    assert exit_code == 0
    assert vcs.fetch_calls == []
    assert vcs.fast_forward_calls == []


def test_resync_home_branch_reports_warn_when_head_branch_cannot_be_resolved(tmp_path, capsys, monkeypatch):
    """The identity guard's two lookups now run in separate `try` blocks
    (code review, this pass) so the WARN names which one actually failed --
    this covers `resolve_ref` raising; `worktree_head_sha` raising is
    covered by the sibling test below."""
    _patch_repo(monkeypatch, tmp_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=("an ordinary commit, not a story merge",),
        resolve_ref_raises=True,
    )
    forge = _FakeForge()

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-009" in codes
    message = payload["findings"][codes.index("MRS-LAND-009")]["message"]
    assert "resolve" in message
    assert payload["data"]["home_current"] is False
    assert exit_code == 0
    assert vcs.fetch_calls == []
    assert vcs.fast_forward_calls == []


def test_resync_home_branch_reports_warn_when_home_head_sha_cannot_be_read(tmp_path, capsys, monkeypatch):
    """`worktree_head_sha` raising -- the sibling half of the identity
    guard's now-separate `try` blocks (see the `resolve_ref` case above)."""
    _patch_repo(monkeypatch, tmp_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=("an ordinary commit, not a story merge",),
        worktree_head_sha_raises=True,
    )
    forge = _FakeForge()

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-009" in codes
    message = payload["findings"][codes.index("MRS-LAND-009")]["message"]
    assert "checked-out commit" in message
    assert payload["data"]["home_current"] is False
    assert exit_code == 0
    assert vcs.fetch_calls == []
    assert vcs.fast_forward_calls == []


def test_render_text_land_reports_home_current_line(tmp_path, capsys, monkeypatch):
    """Tasks & Acceptance: `_render_text_land` gains one line reporting
    `home_current` when the key is present -- untested by every other Story
    4.12 test, which all parse the JSON envelope via `_payload`."""
    _patch_repo(monkeypatch, tmp_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=("an ordinary commit, not a story merge",),
    )
    forge = _FakeForge()

    exit_code = land_module.run_land(_args(format="text"), vcs=vcs, fs=LocalFs(), forge=forge)

    rendered = capsys.readouterr().out
    assert exit_code == 0
    assert "home current with 'main': True" in rendered


# =====================================================================
# Story 4.11: `marshal land` refuses branch retirement while this slug's
# own bmad-loop run is still live -- `is_run_live` gates a policy-true
# `landing_branch_retirement` between where it is resolved and the
# `merge_pr` call. Fakes mirror `test_status.py`'s own `_FakeHarness`/
# `_FakeProcess`/journal-line-builder shape (the SAME real read sequence
# `cli/status.py::_gather_home_facts` performs for `marshal status`,
# reused verbatim here) -- `_resolve_harness_run_id_for_resume` stays REAL
# (reads the real seeded `journal.jsonl` via `LocalFs`), proving the
# wiring through `run_land`'s new `harness`/`process`/`clock` DI params
# end to end, never a shortcut that stubs `_gather_home_facts` itself.
# =====================================================================


class _FakeHarness:
    """Keyed by ``(str(home), harness_run_id)`` -- mirrors
    ``test_status.py::_FakeHarness``'s own convention."""

    def __init__(self, snapshots: dict[tuple[str, str], RunStatusSnapshot] | None = None) -> None:
        self.snapshots = snapshots or {}
        self.calls: list[tuple[str, str]] = []

    def run_status_snapshot(self, project, run_id):
        self.calls.append((str(project), run_id))
        return self.snapshots.get((str(project), run_id))


class _FakeProcess:
    """Mirrors ``test_status.py::_FakeProcess``'s own ``is_alive`` shape --
    ``run`` is never exercised by the liveness gate (``land``'s own resync
    step constructs its OWN ``PosixProcess()`` internally, unaffected by
    this DI param), so it raises loudly if ever called, proving that."""

    def __init__(self, alive_pids: frozenset[int] = frozenset()) -> None:
        self.alive_pids = alive_pids
        self.calls: list[int] = []

    def is_alive(self, pid: int) -> bool:
        self.calls.append(pid)
        return pid in self.alive_pids

    def run(self, argv, *, cwd, timeout_s=None):
        raise AssertionError("the liveness gate must never call ProcessPort.run")


class _FakeClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def monotonic(self) -> float:
        return 0.0


class _ExplosiveHarness:
    """Proves the liveness gate is never consulted at all -- used for the
    policy-already-off short-circuit test."""

    def run_status_snapshot(self, project, run_id):
        raise AssertionError(
            "the liveness gate must never be consulted when policy already has landing_branch_retirement=False"
        )


class _ExplosiveProcess:
    def is_alive(self, pid: int) -> bool:
        raise AssertionError(
            "the liveness gate must never be consulted when policy already has landing_branch_retirement=False"
        )

    def run(self, argv, *, cwd, timeout_s=None):
        raise AssertionError("must never be called")


def _land_outcome_line(run_id: str, *, pid: int, harness_run_id: str, ts: str = "2026-08-09T00:00:00.000Z") -> str:
    """A minimal, valid ``phase: outcome`` ``run-launch`` journal line --
    the SAME shape ``cli/spin.py`` itself journals, mirroring
    ``test_status.py::_outcome_line``'s identical shape."""
    entry = build_entry(
        id=JournalEntryId("spin-1", 1),
        ts=ts,
        run_id=run_id,
        kind="run-launch",
        phase=Phase.OUTCOME,
        intent_id=JournalEntryId("spin-1", 0),
        payload={"pid": pid, "harness_run_id": harness_run_id},
    )
    return prepare_for_write(entry).line


def _land_supervisor_attach_line(run_id: str, *, pid: int, ts: str = "2026-08-09T00:00:30.000Z") -> str:
    """A minimal, valid ``"supervisor-attach"`` journal line -- mirrors
    ``test_status.py::_supervisor_attach_line``'s identical shape. A
    DIFFERENT pid than ``_land_outcome_line``'s own -- the supervisor
    sidecar is a separate process from the detached harness."""
    entry = build_entry(
        id=JournalEntryId("supervisor-1", 1),
        ts=ts,
        run_id=run_id,
        kind="supervisor-attach",
        phase=Phase.OBSERVATION,
        payload={"pid": pid, "watched_pid": 4242},
    )
    return prepare_for_write(entry).line


def _seed_land_run_journal(tmp_path: Path, *, run_id: str, lines: list[str]) -> Path:
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "journal.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return run_dir


def _stub_land_latest_run_dir(monkeypatch, run_dir_map: dict[str, Path | None]) -> None:
    """Stubs ONLY ``cli/spin.py``'s own ``_latest_run_dir`` -- mirrors
    ``test_status.py::_stub_latest_run_dir``'s identical per-module-
    attribute patching (``cli/land.py`` imports it LOCALLY inside
    ``run_land``, so the live function is re-resolved off ``spin_module``
    at call time)."""

    def _latest_run_dir(home, slug):
        return run_dir_map.get(slug)

    monkeypatch.setattr(spin_module, "_latest_run_dir", _latest_run_dir)


def _live_snapshot(*, finished: bool = False, tasks: tuple[TaskPhaseSnapshot, ...] = ()) -> RunStatusSnapshot:
    return RunStatusSnapshot(
        paused_stage=None,
        paused_story_key=None,
        paused_reason=None,
        escalated_spec_file=None,
        escalated_task_phase=None,
        deferred=(),
        finished=finished,
        tasks=tasks,
    )


def test_live_run_refuses_branch_retirement_but_merge_still_proceeds(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    home_root = tmp_path / "loops"
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(home_root))
    home = home_root / "acme"

    run_dir = _seed_land_run_journal(
        tmp_path,
        run_id="acme-run1",
        lines=[
            _land_outcome_line("acme-run1", pid=4242, harness_run_id="hrid-1"),
            _land_supervisor_attach_line("acme-run1", pid=5252),
        ],
    )
    _stub_land_latest_run_dir(monkeypatch, run_dir_map={"acme": run_dir})

    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)
    harness = _FakeHarness(
        snapshots={
            (str(home), "hrid-1"): _live_snapshot(
                tasks=(TaskPhaseSnapshot(story_key="1.1", phase="dev-running", commit_sha=None),)
            )
        }
    )
    process = _FakeProcess(alive_pids=frozenset({5252}))
    clock = _FakeClock(now=datetime(2026, 8, 9, 0, 5, 0, tzinfo=timezone.utc))

    exit_code = land_module.run_land(
        _args(), vcs=vcs, fs=LocalFs(), forge=forge, harness=harness, process=process, clock=clock
    )

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-008" in codes
    assert "acme" in payload["findings"][codes.index("MRS-LAND-008")]["message"]
    assert "loop/acme" in payload["findings"][codes.index("MRS-LAND-008")]["message"]
    assert payload["data"]["merged"] is True
    assert payload["data"]["branch_retired"] is False
    assert exit_code == 0  # MRS-LAND-008 is WARN-tier -- reported, never blocking
    assert len(forge.merge_calls) == 1
    repo, number, strategy, expected_head_sha, delete_branch, subject = forge.merge_calls[0]
    assert delete_branch is False


def test_live_run_with_override_flag_retires_normally_no_finding(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    home_root = tmp_path / "loops"
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(home_root))
    home = home_root / "acme"

    run_dir = _seed_land_run_journal(
        tmp_path,
        run_id="acme-run1",
        lines=[
            _land_outcome_line("acme-run1", pid=4242, harness_run_id="hrid-1"),
            _land_supervisor_attach_line("acme-run1", pid=5252),
        ],
    )
    _stub_land_latest_run_dir(monkeypatch, run_dir_map={"acme": run_dir})

    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)
    harness = _FakeHarness(
        snapshots={
            (str(home), "hrid-1"): _live_snapshot(
                tasks=(TaskPhaseSnapshot(story_key="1.1", phase="dev-running", commit_sha=None),)
            )
        }
    )
    process = _FakeProcess(alive_pids=frozenset({5252}))
    clock = _FakeClock(now=datetime(2026, 8, 9, 0, 5, 0, tzinfo=timezone.utc))

    exit_code = land_module.run_land(
        _args(retire_live_branch=True),
        vcs=vcs,
        fs=LocalFs(),
        forge=forge,
        harness=harness,
        process=process,
        clock=clock,
    )

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-008" not in codes
    assert payload["data"]["merged"] is True
    assert payload["data"]["branch_retired"] is True
    assert exit_code == 0
    repo, number, strategy, expected_head_sha, delete_branch, subject = forge.merge_calls[0]
    assert delete_branch is True


def test_journal_unreadable_is_conservatively_treated_as_live(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    home_root = tmp_path / "loops"
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(home_root))

    # A run directory exists, but its journal never records a usable launch
    # pid -- `_gather_home_facts` degrades to `journal_unreadable=True`,
    # which `is_run_live` treats conservatively as live (mirrors
    # core/retire.py's own "an unprovable fact is refused" precedent).
    run_dir = _seed_land_run_journal(tmp_path, run_id="acme-run1", lines=[])
    _stub_land_latest_run_dir(monkeypatch, run_dir_map={"acme": run_dir})

    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)
    harness = _FakeHarness()
    process = _FakeProcess()
    clock = _FakeClock(now=datetime(2026, 8, 9, 0, 5, 0, tzinfo=timezone.utc))

    exit_code = land_module.run_land(
        _args(), vcs=vcs, fs=LocalFs(), forge=forge, harness=harness, process=process, clock=clock
    )

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-008" in codes
    assert payload["data"]["branch_retired"] is False
    assert exit_code == 0


@pytest.mark.parametrize(
    "snapshot_kwargs, alive_pids",
    [
        pytest.param({"finished": True}, frozenset({5252}), id="finished"),
        pytest.param({"finished": False}, frozenset(), id="dead-supervisor"),
    ],
)
def test_no_live_run_retires_normally_no_finding(tmp_path, capsys, monkeypatch, snapshot_kwargs, alive_pids):
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    home_root = tmp_path / "loops"
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(home_root))
    home = home_root / "acme"

    run_dir = _seed_land_run_journal(
        tmp_path,
        run_id="acme-run1",
        lines=[
            _land_outcome_line("acme-run1", pid=4242, harness_run_id="hrid-1"),
            _land_supervisor_attach_line("acme-run1", pid=5252),
        ],
    )
    _stub_land_latest_run_dir(monkeypatch, run_dir_map={"acme": run_dir})

    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)
    harness = _FakeHarness(snapshots={(str(home), "hrid-1"): _live_snapshot(**snapshot_kwargs)})
    process = _FakeProcess(alive_pids=alive_pids)
    clock = _FakeClock(now=datetime(2026, 8, 9, 0, 5, 0, tzinfo=timezone.utc))

    exit_code = land_module.run_land(
        _args(), vcs=vcs, fs=LocalFs(), forge=forge, harness=harness, process=process, clock=clock
    )

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-008" not in codes
    assert payload["data"]["merged"] is True
    assert payload["data"]["branch_retired"] is True
    assert exit_code == 0


def test_never_run_home_retires_normally_no_finding(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    home_root = tmp_path / "loops"
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(home_root))
    # No run directory exists at all for this slug.
    _stub_land_latest_run_dir(monkeypatch, run_dir_map={})

    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(
        _args(),
        vcs=vcs,
        fs=LocalFs(),
        forge=forge,
        harness=_FakeHarness(),
        process=_FakeProcess(),
        clock=_FakeClock(now=datetime(2026, 8, 9, 0, 5, 0, tzinfo=timezone.utc)),
    )

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-008" not in codes
    assert payload["data"]["merged"] is True
    assert payload["data"]["branch_retired"] is True
    assert exit_code == 0


def test_override_flag_short_circuits_the_liveness_gather_even_when_not_live(tmp_path, capsys, monkeypatch):
    """`--retire-live-branch` passed defensively (an operator unsure
    whether a run is live) short-circuits `if delete_branch and not args.
    retire_live_branch` before `_gather_home_facts`/`is_run_live` ever run
    -- so retirement proceeds identically whether or not a run is actually
    live. Proven here with `_ExplosiveHarness`/`_ExplosiveProcess` (the SAME
    doubles `test_policy_already_off_skips_liveness_gather_entirely` uses
    below): if the gate were ever consulted despite the flag, this test
    would fail on the explosion, not merely on a wrong assertion.

    `landing_resync = false` (Story 82.2): the post-merge home resync now
    shares the same liveness verdict, so it would gather too -- switching it
    off keeps this test proving the RETIREMENT gate alone."""
    policy_path = _write_project_policy(tmp_path, "landing_resync = false\n" + _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    home_root = tmp_path / "loops"
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(home_root))

    def _explosive_latest_run_dir(home, slug):
        raise AssertionError("the liveness gate must never be consulted when --retire-live-branch is passed")

    monkeypatch.setattr(spin_module, "_latest_run_dir", _explosive_latest_run_dir)

    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(
        _args(retire_live_branch=True),
        vcs=vcs,
        fs=LocalFs(),
        forge=forge,
        harness=_ExplosiveHarness(),
        process=_ExplosiveProcess(),
        clock=_FakeClock(now=datetime(2026, 8, 9, 0, 5, 0, tzinfo=timezone.utc)),
    )

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-008" not in codes
    assert payload["data"]["merged"] is True
    assert payload["data"]["branch_retired"] is True
    assert exit_code == 0
    repo, number, strategy, expected_head_sha, delete_branch, subject = forge.merge_calls[0]
    assert delete_branch is True


def test_policy_already_off_skips_liveness_gather_entirely(tmp_path, capsys, monkeypatch):
    """The Always bullet's short-circuit: `delete_branch` already `False`
    from policy means NO liveness gather at all -- proven here with fakes
    that raise if ever consulted, not merely by asserting the outcome.

    `landing_resync = false` (Story 82.2): the post-merge home resync now
    shares the same liveness verdict, so it would gather too -- switching it
    off keeps this test proving the RETIREMENT gate alone."""
    policy_path = _write_project_policy(
        tmp_path,
        "landing_branch_retirement = false\nlanding_resync = false\n" + _rule_policy(required_check=None),
    )
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)

    def _explosive_latest_run_dir(home, slug):
        raise AssertionError(
            "the liveness gate must never look up a run directory when "
            "policy already has landing_branch_retirement=False"
        )

    monkeypatch.setattr(spin_module, "_latest_run_dir", _explosive_latest_run_dir)

    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(
        _args(),
        vcs=vcs,
        fs=LocalFs(),
        forge=forge,
        harness=_ExplosiveHarness(),
        process=_ExplosiveProcess(),
    )

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-008" not in codes
    assert payload["data"]["branch_retired"] is False
    assert exit_code == 0


# =====================================================================
# Story 82.2 (DW-5-8-1, DW-FU-4-11, DW-FU-4-12): a live run's branch and home
# survive `marshal land` while its ENGINE is alive, even when its supervisor
# sidecar is dead. `is_run_live` now counts a confirmed-alive engine
# (`ProcessPort.is_alive(launch_pid)`), and `run_land` hands that same
# memoised verdict to `_resync_home_branch` at all three of its exits.
# `_land_outcome_line`'s pid (4242) is the detached HARNESS (the engine);
# `_land_supervisor_attach_line`'s pid (5252) is the supervisor sidecar.
# =====================================================================

_ENGINE_PID = 4242
_SUPERVISOR_PID = 5252


class _LiveHomeProcess(_FakeProcess):
    """``_FakeProcess`` whose ``run`` answers rather than raises: these tests
    drive the full merge and already-landed exits, whose ``landing_resync``
    feed reconcile may legitimately run a command -- liveness is the only
    thing under test."""

    def run(self, argv, *, cwd, timeout_s=None):
        return ProcessResult(returncode=0, stdout="", stderr="")


def _seed_liveness_home(
    tmp_path: Path, monkeypatch, *, alive_pids: frozenset[int], finished: bool = False
) -> tuple[_FakeHarness, _LiveHomeProcess, _FakeClock]:
    """One acme run with a journaled engine pid and supervisor pid; which of
    them ``is_alive`` reports is the caller's ``alive_pids``."""
    home_root = tmp_path / "loops"
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(home_root))
    run_dir = _seed_land_run_journal(
        tmp_path,
        run_id="acme-run1",
        lines=[
            _land_outcome_line("acme-run1", pid=_ENGINE_PID, harness_run_id="hrid-1"),
            _land_supervisor_attach_line("acme-run1", pid=_SUPERVISOR_PID),
        ],
    )
    _stub_land_latest_run_dir(monkeypatch, run_dir_map={"acme": run_dir})
    harness = _FakeHarness(
        snapshots={
            (str(home_root / "acme"), "hrid-1"): _live_snapshot(
                finished=finished,
                tasks=(TaskPhaseSnapshot(story_key="1.1", phase="dev-running", commit_sha=None),),
            )
        }
    )
    return (
        harness,
        _LiveHomeProcess(alive_pids=alive_pids),
        _FakeClock(now=datetime(2026, 8, 9, 0, 5, 0, tzinfo=timezone.utc)),
    )


def test_dead_supervisor_with_live_engine_refuses_branch_retirement(tmp_path, capsys, monkeypatch):
    """The 2026-08-11 incident's shape, at the call site `marshal land`
    actually uses: the supervisor sidecar is dead, the harness it launched is
    still working. Retirement is downgraded (`MRS-LAND-008`) and the merge
    still proceeds. `landing_resync = false` isolates the retirement gate."""
    policy_path = _write_project_policy(tmp_path, "landing_resync = false\n" + _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    harness, process, clock = _seed_liveness_home(tmp_path, monkeypatch, alive_pids=frozenset({_ENGINE_PID}))
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(
        _args(), vcs=vcs, fs=LocalFs(), forge=forge, harness=harness, process=process, clock=clock
    )

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-008" in codes
    assert "loop/acme" in payload["findings"][codes.index("MRS-LAND-008")]["message"]
    assert payload["data"]["merged"] is True
    assert payload["data"]["branch_retired"] is False
    assert exit_code == 0
    assert len(forge.merge_calls) == 1
    assert forge.merge_calls[0][4] is False  # delete_branch: the branch survives


def test_dead_supervisor_with_dead_engine_still_retires_normally(tmp_path, capsys, monkeypatch):
    """Both probes confirmed dead -- the engine term must not over-block."""
    policy_path = _write_project_policy(tmp_path, "landing_resync = false\n" + _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    harness, process, clock = _seed_liveness_home(tmp_path, monkeypatch, alive_pids=frozenset())
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(
        _args(), vcs=vcs, fs=LocalFs(), forge=forge, harness=harness, process=process, clock=clock
    )

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-008" not in codes
    assert payload["data"]["branch_retired"] is True
    assert exit_code == 0
    assert forge.merge_calls[0][4] is True


# One scenario per `_resync_home_branch` exit of `run_land`: the `if not
# wave_keys` no-op, the already-landed shortcut, and the full-merge path.
_RESYNC_EXITS = [
    pytest.param({"wave_subjects": ("an ordinary commit, not a story merge",)}, id="no-op"),
    pytest.param(
        {"wave_subjects": (_BMADLOOP_WAVE_SUBJECT,), "base_subjects": (_BMADLOOP_WAVE_SUBJECT,)},
        id="already-landed",
    ),
    pytest.param(
        {"wave_subjects": (_BMADLOOP_WAVE_SUBJECT,), "changed_paths": ("docs/notes.md",)},
        id="full-merge",
    ),
]


@pytest.mark.parametrize("vcs_kwargs", _RESYNC_EXITS)
@pytest.mark.parametrize(
    "alive_pids",
    [
        pytest.param(frozenset({_SUPERVISOR_PID}), id="supervisor-alive"),
        pytest.param(frozenset({_ENGINE_PID}), id="engine-alive-supervisor-dead"),
    ],
)
def test_live_run_skips_the_home_resync_at_every_exit(tmp_path, capsys, monkeypatch, vcs_kwargs, alive_pids):
    """A live run's home is never fetched into or fast-forwarded: `fast_forward`
    rewrites tracked files the run's own turn may be reading, and this runs
    from outside the run with no lock (DW-FU-4-12). One `MRS-LAND-009` WARN
    names the run, `home_current` is `False`, and the gather happened ONCE
    even where the retirement gate consulted the same verdict."""
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    harness, process, clock = _seed_liveness_home(tmp_path, monkeypatch, alive_pids=alive_pids)
    vcs = _FakeVcs(existing_branches=frozenset({"loop/acme"}), **vcs_kwargs)
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(
        _args(), vcs=vcs, fs=LocalFs(), forge=forge, harness=harness, process=process, clock=clock
    )

    payload = _payload(capsys)
    live_warns = [f for f in payload["findings"] if f["code"] == "MRS-LAND-009"]
    assert len(live_warns) == 1
    assert "loop/acme" in live_warns[0]["message"]
    assert "is live" in live_warns[0]["message"]
    assert payload["data"]["home_current"] is False
    assert vcs.fetch_calls == []
    assert vcs.fast_forward_calls == []
    assert exit_code == 0
    assert len(harness.calls) == 1  # one gather, shared by the retirement gate and the resync


@pytest.mark.parametrize("vcs_kwargs", _RESYNC_EXITS)
@pytest.mark.parametrize(
    "alive_pids, finished",
    [
        pytest.param(frozenset(), False, id="supervisor-and-engine-dead"),
        pytest.param(frozenset({_SUPERVISOR_PID, _ENGINE_PID}), True, id="finished"),
    ],
)
def test_dead_or_finished_run_resyncs_the_home_as_before(
    tmp_path, capsys, monkeypatch, vcs_kwargs, alive_pids, finished
):
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    harness, process, clock = _seed_liveness_home(tmp_path, monkeypatch, alive_pids=alive_pids, finished=finished)
    vcs = _FakeVcs(existing_branches=frozenset({"loop/acme"}), **vcs_kwargs)
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(
        _args(), vcs=vcs, fs=LocalFs(), forge=forge, harness=harness, process=process, clock=clock
    )

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-009" not in codes
    assert "MRS-LAND-008" not in codes
    assert payload["data"]["home_current"] is True
    assert vcs.fetch_calls == [(Path("/fake-repo-root"), "origin", "main")]
    assert len(vcs.fast_forward_calls) == 1
    assert exit_code == 0


@pytest.mark.parametrize("vcs_kwargs", _RESYNC_EXITS)
@pytest.mark.parametrize(
    "journal_lines",
    [
        pytest.param(
            [
                _land_outcome_line("acme-run1", pid=_ENGINE_PID, harness_run_id="hrid-1"),
                _land_supervisor_attach_line("acme-run1", pid=_SUPERVISOR_PID),
            ],
            id="retired-run-state-gone",
        ),
        pytest.param([], id="journal-unreadable"),
    ],
)
def test_unprovable_run_state_skips_the_home_resync_with_an_honest_warn(
    tmp_path, capsys, monkeypatch, vcs_kwargs, journal_lines
):
    """`is_run_live`'s conservative arms (a retired run whose clean finish cannot
    be proven, an unreadable journal) feed the resync exactly as they feed
    retirement: the home is left alone, and the WARN says the run is live OR
    could not be proven finished -- never claims a live run it did not prove.
    The snapshot is absent, so the retired shape is `run_state_retired=True`."""
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loops"))
    run_dir = _seed_land_run_journal(tmp_path, run_id="acme-run1", lines=journal_lines)
    _stub_land_latest_run_dir(monkeypatch, run_dir_map={"acme": run_dir})
    vcs = _FakeVcs(existing_branches=frozenset({"loop/acme"}), **vcs_kwargs)
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(
        _args(),
        vcs=vcs,
        fs=LocalFs(),
        forge=forge,
        harness=_FakeHarness(),
        process=_LiveHomeProcess(alive_pids=frozenset()),
        clock=_FakeClock(now=datetime(2026, 8, 9, 0, 5, 0, tzinfo=timezone.utc)),
    )

    payload = _payload(capsys)
    warns = [f for f in payload["findings"] if f["code"] == "MRS-LAND-009"]
    assert len(warns) == 1
    assert "could not be proven finished" in warns[0]["message"]
    assert payload["data"]["home_current"] is False
    assert vcs.fetch_calls == []
    assert vcs.fast_forward_calls == []
    assert exit_code == 0


def test_retire_live_branch_override_does_not_override_the_resync_skip(tmp_path, capsys, monkeypatch):
    """`--retire-live-branch` is an operator's call about RETIREMENT only. The
    resync still declines to rewrite a live run's working tree."""
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    harness, process, clock = _seed_liveness_home(tmp_path, monkeypatch, alive_pids=frozenset({_ENGINE_PID}))
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    land_module.run_land(
        _args(retire_live_branch=True),
        vcs=vcs,
        fs=LocalFs(),
        forge=forge,
        harness=harness,
        process=process,
        clock=clock,
    )

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-008" not in codes
    assert codes.count("MRS-LAND-009") == 1
    assert forge.merge_calls[0][4] is True  # retirement honoured by the override
    assert vcs.fetch_calls == []
    assert vcs.fast_forward_calls == []


def test_resync_off_or_non_merge_strategy_never_gathers_liveness(tmp_path, capsys, monkeypatch):
    """The resync computes its liveness verdict only when it would act at all:
    under `squash` (no fast-forward possible by construction) with retirement
    off, nothing consults the run -- explosive fakes prove it."""
    policy_path = _write_project_policy(
        tmp_path,
        'landing_merge_strategy = "squash"\nlanding_branch_retirement = false\n' + _rule_policy(required_check=None),
    )
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)

    def _explosive_latest_run_dir(home, slug):
        raise AssertionError("liveness must not be gathered when the resync would not act")

    monkeypatch.setattr(spin_module, "_latest_run_dir", _explosive_latest_run_dir)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(
        _args(),
        vcs=vcs,
        fs=LocalFs(),
        forge=forge,
        harness=_ExplosiveHarness(),
        process=_ExplosiveProcess(),
    )

    payload = _payload(capsys)
    assert exit_code == 0
    assert "home_current" not in payload["data"]
    assert vcs.fetch_calls == []


def test_resync_home_branch_run_live_touches_nothing(tmp_path):
    """The seam itself: `run_live=True` returns before `resolve_ref`, `fetch`
    and `fast_forward`, with one WARN that names the branch and the home;
    the default (`run_live` omitted, the `dispatch_land_finalize` call shape)
    still resyncs."""
    vcs = _FakeVcs()
    findings: list = []

    live = land_module._resync_home_branch(
        vcs, True, "merge", Path("/fake-repo-root"), tmp_path, "main", "loop/acme", findings, run_live=True
    )

    assert live is False
    assert vcs.resolve_ref_calls == []
    assert vcs.fetch_calls == []
    assert vcs.fast_forward_calls == []
    assert [f.code for f in findings] == ["MRS-LAND-009"]
    assert "loop/acme" in findings[0].message
    assert str(tmp_path) in findings[0].message

    findings.clear()
    default = land_module._resync_home_branch(
        vcs, True, "merge", Path("/fake-repo-root"), tmp_path, "main", "loop/acme", findings
    )

    assert default is True
    assert findings == []
    assert len(vcs.fast_forward_calls) == 1


# --- re-entrancy: PR open, checks green, merge never issued --------------


def test_reentrant_run_with_existing_pr_converges_to_full_landing(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, _rule_policy())
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    existing_pr = PrInfo(number=77, url="https://example/pr/77", state="open", base="main")
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("pixi.toml",),
    )
    forge = _FakeForge(
        existing=existing_pr,
        update_result=existing_pr,
        check_status_map={"environment-yaml-sync": "success"},
    )

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert payload["data"]["updated"] is True
    assert payload["data"]["opened"] is False
    assert payload["data"]["merged"] is True
    assert exit_code == 0
    assert forge.create_calls == []
    assert len(forge.update_calls) == 1
    assert len(forge.merge_calls) == 1
    assert forge.merge_calls[0][1] == 77


# --- main.py wiring smoke test -------------------------------------------


def test_run_land_with_default_ports_does_not_crash(tmp_path, monkeypatch, capsys):
    """Task 9's own AC: 'marshal land <slug>' with no acting doubles
    exercises the real GitVcs/LocalFs/GhForge default construction path
    (smoke-level only) -- a non-existent loop-home simply reports
    MRS-LAND-001, never a raw traceback."""
    monkeypatch.setattr(land_module, "repo_root", lambda: tmp_path)
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loops"))

    exit_code = land_module.run_land(_args(slug="no-such-project"))

    assert isinstance(exit_code, int)
    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-001" in codes


# =====================================================================
# Story 4.9 proof tests (AD-42): "regenerate on main, never a loop home"
# is proven, not merely assumed; the journal's own concurrency protocol
# stays untouched by the new advisory lock.
# =====================================================================


class _RecordingProcess:
    """A minimal ``ProcessPort`` stand-in recording every ``cwd`` a command
    ran with -- proves ``_run_resync_commands`` (called from ``land``'s own
    resync step via ``cli/deploy.py::reconcile_feed``) always runs with
    ``cwd=root``, never a loop home's own path."""

    def __init__(self) -> None:
        self.cwd_calls: list[Path] = []

    def run(self, argv, *, cwd, timeout_s=None):
        self.cwd_calls.append(cwd)
        return ProcessResult(returncode=0, stdout="", stderr="")


class _NoWriteFs:
    """A read-only ``FsPort`` stand-in: every WRITE-shaped method (including
    the new Story 4.9 lock pair) raises ``AssertionError`` -- proves
    ``reconcile_feed``'s resync path performs ZERO writes anywhere, home or
    otherwise. Read-shaped methods answer the minimum needed to reach
    ``_gather_claimed_commits``'s own early-return (``exists`` reports the
    loop home absent)."""

    def exists(self, path):
        return False

    def read_text(self, path):
        return None

    def is_dir(self, path):
        return False

    def read_symlink_target(self, path):
        return None

    def _refuse(self, name):
        raise AssertionError(f"reconcile_feed's resync path must never call FsPort.{name}")

    def write_text_atomic(self, path, content):
        self._refuse("write_text_atomic")

    def repoint_symlink_atomic(self, path, target):
        self._refuse("repoint_symlink_atomic")

    def ensure_dir(self, path):
        self._refuse("ensure_dir")

    def remove_empty_dir(self, path):
        self._refuse("remove_empty_dir")

    def resolve_path(self, path):
        self._refuse("resolve_path")

    def copy_file(self, src, dst):
        self._refuse("copy_file")

    def append_line(self, path, line, *, fsync):
        self._refuse("append_line")

    def create_dir_exclusive(self, path):
        self._refuse("create_dir_exclusive")

    def acquire_advisory_lock(self, path, *, timeout_s):
        self._refuse("acquire_advisory_lock")

    def release_advisory_lock(self, lock):
        self._refuse("release_advisory_lock")


class _UnusedHarness:
    """A ``HarnessPort`` stand-in that must never be called -- ``_NoWriteFs
    .exists`` above always reports the loop home absent, so
    ``_gather_claimed_commits`` short-circuits before ever reaching
    ``run_status_snapshot``."""

    def run_status_snapshot(self, project, run_id):
        raise AssertionError("should never be called: the loop home is absent")


def test_reconcile_feed_resync_runs_at_root_and_never_writes_under_a_loop_home(tmp_path, monkeypatch):
    """Story 4.9 proof test (AD-42 half one): ``land``'s resync step calls
    ``cli/deploy.py::reconcile_feed`` in-process (``_run_resync_if_enabled``)
    -- this is the SAME function, called the same way, so exercising it
    directly proves the exact invariant both ``marshal deploy refresh-feed``
    and ``marshal land``'s own resync step share: derived reporting surfaces
    regenerate against ``root = repo_root()`` (the checked-out integration
    branch), never a loop home's own Tier-3 copy. ``root``/``home_root`` are
    pinned to two DIFFERENT, non-overlapping directories -- a future edit
    that accidentally threaded ``home`` in instead of ``root`` anywhere in
    ``reconcile_feed``/``_run_resync_commands``/``_gather_claimed_commits``
    would make this test's own cwd/no-write assertions fail."""
    root = tmp_path / "main-checkout"
    root.mkdir()
    home_root = tmp_path / "loop-homes"
    monkeypatch.setattr(deploy_module, "repo_root", lambda: root)
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(home_root))

    policy_path = root / "marshal-policy.toml"
    policy_path.write_text('landing_resync = true\nlanding_resync_commands = ["true"]\n', encoding="utf-8")
    monkeypatch.setattr(deploy_module, "conventional_project_policy_path", lambda slug: policy_path)

    process = _RecordingProcess()
    fs = _NoWriteFs()
    vcs = _FakeVcs(base_subjects=("Merge 1.2 into main",))
    args = argparse.Namespace(project="acme", format="json")

    data, findings = deploy_module.reconcile_feed(args, vcs=vcs, fs=fs, process=process, harness=_UnusedHarness())

    assert root != home_root
    assert not str(root).startswith(str(home_root))
    assert not str(home_root).startswith(str(root))
    assert data["resync_skipped"] is False
    assert process.cwd_calls == [root]
    assert not home_root.exists()  # never created -- nothing ever wrote there
    assert not any(finding.severity.value == "error" for finding in findings)


def test_deploy_run_write_never_touches_the_new_advisory_lock(tmp_path):
    """Story 4.9 proof test (boundary, second half): the journal's own
    append protocol (``_DeployRun.write``/``_write_deploy_entry``, AD-25/
    AD-28/AD-30) is UNTOUCHED by this story's new
    ``FsPort.acquire_advisory_lock``/``release_advisory_lock`` pair -- F-6's
    own concurrency answer (per-run-directory isolation + a single
    ``O_APPEND`` write) stays the journal's sole mechanism. A fake FsPort
    that raises ``AssertionError`` from BOTH lock methods, otherwise
    delegating everything to a real ``LocalFs``, proves a full intent +
    outcome journal write cycle never reaches either one."""

    class _LockRefusingFs(LocalFs):
        def acquire_advisory_lock(self, path, *, timeout_s):
            raise AssertionError("journal writes must never acquire the new advisory lock")

        def release_advisory_lock(self, lock):
            raise AssertionError("journal writes must never release the new advisory lock")

    fs = _LockRefusingFs()
    deploy_run = deploy_module._DeployRun(fs, tmp_path, "acme", "writer-1")
    findings: list = []

    intent_id = deploy_run.write(
        findings,
        kind="promote-commit",
        phase=deploy_module.Phase.INTENT,
        payload={"story_keys": ["1.2"]},
    )
    assert intent_id is not None

    outcome_id = deploy_run.write(
        findings,
        kind="promote-commit",
        phase=deploy_module.Phase.OUTCOME,
        payload={"story_keys": ["1.2"]},
        intent_id=intent_id,
    )
    assert outcome_id is not None
    assert findings == []


# --- deferred-work promotion (Story 4.13, FR-175) -------------------------
#
# ``_BMADLOOP_WAVE_SUBJECT`` names story key ``4-4`` (see the module-level
# constant above) -- every fixture below names its Tier-3 deferral for that
# same story, so the wave discovered from ``wave_subjects``/``base_subjects``
# always matches.

_TIER3_DEFERRAL_TEXT = """\
### DW-8: Follow-up review still recommended for 4-4-batch after the damping cap was spent
origin: review-budget-followup
source_spec: `spec-4-4-batch.md`
severity: low
reason: The follow-up-review damping cap was spent with the story finalized while the review pass still recommended an independent follow-up.
status: open
"""

_TIER3_DEFERRAL_FOR_A_DIFFERENT_STORY = """\
### DW-9: Follow-up review still recommended for 5-1-unrelated after the damping cap was spent
origin: review-budget-followup
source_spec: `spec-5-1-unrelated.md`
severity: low
reason: Belongs to a story that is not part of this wave.
status: open
"""

_TRACKED_LEDGER_HEADER = (
    "---\ndoc_type: deferred-work-ledger\nproject: acme\n---\n\n"
    "# acme — deferred-work ledger (TRACKED)\n\nsome pre-existing prose.\n"
)


def _write_deferred_work_fixtures(
    tmp_path: Path, slug: str, *, tier3_text: str | None, tracked_text: str | None
) -> tuple[Path, Path]:
    tier3_path = tmp_path / "_bmad-output" / "projects" / slug / "implementation-artifacts" / "deferred-work.md"
    tracked_path = tmp_path / "_bmad-output" / "projects" / slug / "planning-artifacts" / "deferred-work-ledger.md"
    if tier3_text is not None:
        tier3_path.parent.mkdir(parents=True, exist_ok=True)
        tier3_path.write_text(tier3_text, encoding="utf-8")
    if tracked_text is not None:
        tracked_path.parent.mkdir(parents=True, exist_ok=True)
        tracked_path.write_text(tracked_text, encoding="utf-8")
    return tier3_path, tracked_path


def test_promote_on_merge_appends_and_commits_ledger_entry(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    _tier3_path, tracked_path = _write_deferred_work_fixtures(
        tmp_path, "acme", tier3_text=_TIER3_DEFERRAL_TEXT, tracked_text=_TRACKED_LEDGER_HEADER
    )
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert payload["data"]["merged"] is True
    assert payload["data"]["deferred_work_promoted"] == ["DW-FU-4-4"]
    assert exit_code == 0
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-010" not in codes

    ledger_text = tracked_path.read_text(encoding="utf-8")
    assert "### DW-FU-4-4:" in ledger_text
    # The bare Tier-3 id must survive into the promoted entry -- the exact
    # substring scripts/deferred_work_check.py looks for to confirm the
    # Tier-3 id now has a tracked twin.
    assert "DW-8" in ledger_text
    assert len(vcs.commit_paths_calls) == 1
    called_root, called_paths, called_message = vcs.commit_paths_calls[0]
    assert called_paths == (tracked_path,)
    assert "deferred-work" in called_message


def test_promote_on_already_landed_shortcut(tmp_path, capsys, monkeypatch):
    _patch_repo(monkeypatch, tmp_path)
    _tier3_path, tracked_path = _write_deferred_work_fixtures(
        tmp_path, "acme", tier3_text=_TIER3_DEFERRAL_TEXT, tracked_text=_TRACKED_LEDGER_HEADER
    )
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        base_subjects=(_BMADLOOP_WAVE_SUBJECT,),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert payload["data"]["already_landed"] is True
    assert payload["data"]["deferred_work_promoted"] == ["DW-FU-4-4"]
    assert exit_code == 0
    assert "### DW-FU-4-4:" in tracked_path.read_text(encoding="utf-8")
    assert len(vcs.commit_paths_calls) == 1


def test_promote_deferred_work_idempotent_rerun_no_duplicate_no_commit(tmp_path, capsys, monkeypatch):
    """The already-promoted case (Boundaries: "an id already present
    anywhere in the tracked ledger's text is never re-appended;
    idempotent -- a fully-idempotent run acquires no lock and writes
    nothing"). Simulates a SECOND ``land`` run against a ledger that
    already carries the promoted entry from a prior run."""
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    already_promoted_ledger = _TRACKED_LEDGER_HEADER + (
        "\n### DW-FU-4-4: Follow-up review still recommended for "
        "4-4-batch after the damping cap was spent\n\n"
        "- source_spec: `spec-4-4-batch.md`\n"
        "  summary: Follow-up review still recommended for 4-4-batch "
        "after the damping cap was spent\n"
        "  evidence: already promoted by a prior run\n"
        "  promoted: 2026-08-09 — promoted from Tier-3 "
        "`implementation-artifacts/deferred-work.md` (id `DW-8` there) "
        "under the ledger's `DW-FU-<story>` convention, so the next "
        "damped story cannot collide with a generic `DW-8`.\n"
        "  severity: low\n"
        "  status: open\n"
    )
    _tier3_path, tracked_path = _write_deferred_work_fixtures(
        tmp_path, "acme", tier3_text=_TIER3_DEFERRAL_TEXT, tracked_text=already_promoted_ledger
    )
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert payload["data"]["merged"] is True
    assert exit_code == 0
    assert "deferred_work_promoted" not in payload["data"]
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-010" not in codes
    assert vcs.commit_paths_calls == []
    final_text = tracked_path.read_text(encoding="utf-8")
    assert final_text == already_promoted_ledger
    assert final_text.count("DW-FU-4-4") == 1


def test_promote_deferred_work_lock_contention_reports_warn(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    _tier3_path, tracked_path = _write_deferred_work_fixtures(
        tmp_path, "acme", tier3_text=_TIER3_DEFERRAL_TEXT, tracked_text=_TRACKED_LEDGER_HEADER
    )

    class _AlwaysLockContendedFs(LocalFs):
        def acquire_advisory_lock(self, path, *, timeout_s):
            raise FsError(f"lock contended on {path} (test double)")

    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=_AlwaysLockContendedFs(), forge=forge)

    payload = _payload(capsys)
    assert payload["data"]["merged"] is True
    assert exit_code == 0  # MRS-LAND-010 is WARN-tier -- reported, never blocking
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-010" in codes
    assert "deferred_work_promoted" not in payload["data"]
    assert len(vcs.commit_paths_calls) == 0
    # Nothing was written -- the lock refusal happens before any write.
    assert tracked_path.read_text(encoding="utf-8") == _TRACKED_LEDGER_HEADER


def test_promote_deferred_work_no_matching_tier3_entry_is_silent(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    _write_deferred_work_fixtures(
        tmp_path,
        "acme",
        tier3_text=_TIER3_DEFERRAL_FOR_A_DIFFERENT_STORY,
        tracked_text=_TRACKED_LEDGER_HEADER,
    )
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert payload["data"]["merged"] is True
    assert exit_code == 0
    assert "deferred_work_promoted" not in payload["data"]
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-010" not in codes
    assert vcs.commit_paths_calls == []


def test_promote_deferred_work_no_tier3_file_is_silent(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert payload["data"]["merged"] is True
    assert exit_code == 0
    assert "deferred_work_promoted" not in payload["data"]
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-010" not in codes


def test_render_text_land_reports_deferred_work_promoted_line(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    _write_deferred_work_fixtures(
        tmp_path, "acme", tier3_text=_TIER3_DEFERRAL_TEXT, tracked_text=_TRACKED_LEDGER_HEADER
    )
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(format="text"), vcs=vcs, fs=LocalFs(), forge=forge)

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "deferred work promoted: DW-FU-4-4" in out


def test_promote_deferred_work_bootstraps_a_missing_tracked_ledger(tmp_path, capsys, monkeypatch):
    """Review finding (2026-08-10): a project with NO tracked ledger file
    at all must still get its first promotion -- not a silent, permanent
    no-op -- and the bootstrapped file must not carry leading blank lines."""
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    _tier3_path, tracked_path = _write_deferred_work_fixtures(
        tmp_path, "acme", tier3_text=_TIER3_DEFERRAL_TEXT, tracked_text=None
    )
    assert not tracked_path.exists()
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert exit_code == 0
    assert payload["data"]["deferred_work_promoted"] == ["DW-FU-4-4"]
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-010" not in codes
    ledger_text = tracked_path.read_text(encoding="utf-8")
    assert ledger_text.startswith("### DW-FU-4-4:")
    assert len(vcs.commit_paths_calls) == 1


def test_promote_deferred_work_dedupes_two_tier3_entries_for_the_same_story(tmp_path, capsys, monkeypatch):
    """Review finding (2026-08-10): two Tier-3 review-budget-followup
    blocks resolving to the SAME story key in one wave must never produce
    two identical ``### DW-FU-<story>:`` headings in a single write."""
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    duplicate_tier3_text = _TIER3_DEFERRAL_TEXT + (
        "\n### DW-20: Follow-up review still recommended for 4-4-batch "
        "after the damping cap was spent\n"
        "origin: review-budget-followup\n"
        "source_spec: `spec-4-4-batch.md`\n"
        "severity: low\n"
        "reason: A second, distinct followup entry for the same story key.\n"
        "status: open\n"
    )
    _tier3_path, tracked_path = _write_deferred_work_fixtures(
        tmp_path, "acme", tier3_text=duplicate_tier3_text, tracked_text=_TRACKED_LEDGER_HEADER
    )
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert exit_code == 0
    assert payload["data"]["deferred_work_promoted"] == ["DW-FU-4-4"]
    ledger_text = tracked_path.read_text(encoding="utf-8")
    assert ledger_text.count("### DW-FU-4-4:") == 1
    assert len(vcs.commit_paths_calls) == 1


def test_promote_deferred_work_ledger_deleted_between_reads_reports_warn(tmp_path, capsys, monkeypatch):
    """Review finding (2026-08-10): a tracked ledger that existed at the
    first, unlocked read but is gone by the time the lock is held is a
    genuine anomaly (concurrent deletion) -- it must be reported, never
    silently resurrected from stale pre-lock content."""
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    _tier3_path, tracked_path = _write_deferred_work_fixtures(
        tmp_path, "acme", tier3_text=_TIER3_DEFERRAL_TEXT, tracked_text=_TRACKED_LEDGER_HEADER
    )

    class _DeletesLedgerAfterFirstReadFs(LocalFs):
        def __init__(self, tracked_path: Path) -> None:
            self._tracked_path = tracked_path
            self._tracked_reads = 0

        def read_text(self, path):
            if path == self._tracked_path:
                self._tracked_reads += 1
                if self._tracked_reads >= 2:
                    return None
            return super().read_text(path)

    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=_DeletesLedgerAfterFirstReadFs(tracked_path), forge=forge)

    payload = _payload(capsys)
    assert exit_code == 0  # MRS-LAND-010 is WARN-tier -- reported, never blocking
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-010" in codes
    assert "deferred_work_promoted" not in payload["data"]
    assert vcs.commit_paths_calls == []


def test_promote_on_already_landed_shortcut_idempotent_rerun_no_duplicate(tmp_path, capsys, monkeypatch):
    """The already-landed-shortcut call site's own idempotency (Blind
    Hunter review finding, 2026-08-10: only the full-merge path had a
    dedicated idempotent-rerun regression test before this one)."""
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    already_promoted_ledger = _TRACKED_LEDGER_HEADER + (
        "\n### DW-FU-4-4: Follow-up review still recommended for "
        "4-4-batch after the damping cap was spent\n\n"
        "- source_spec: `spec-4-4-batch.md`\n"
        "  summary: Follow-up review still recommended for 4-4-batch "
        "after the damping cap was spent\n"
        "  evidence: already promoted by a prior run\n"
        "  promoted: 2026-08-09 — promoted from Tier-3 "
        "`implementation-artifacts/deferred-work.md` (id `DW-8` there) "
        "under the ledger's `DW-FU-<story>` convention, so the next "
        "damped story cannot collide with a generic `DW-8`.\n"
        "  severity: low\n"
        "  status: open\n"
    )
    _tier3_path, tracked_path = _write_deferred_work_fixtures(
        tmp_path, "acme", tier3_text=_TIER3_DEFERRAL_TEXT, tracked_text=already_promoted_ledger
    )
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        base_subjects=(_BMADLOOP_WAVE_SUBJECT,),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert payload["data"]["already_landed"] is True
    assert exit_code == 0
    assert "deferred_work_promoted" not in payload["data"]
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-010" not in codes
    assert vcs.commit_paths_calls == []
    final_text = tracked_path.read_text(encoding="utf-8")
    assert final_text == already_promoted_ledger
    assert final_text.count("DW-FU-4-4") == 1


def test_promote_deferred_work_multiple_stories_in_one_wave(tmp_path, capsys, monkeypatch):
    """Blind Hunter review finding (2026-08-10): multi-candidate promotion
    (>1 distinct story promoted in one wave/commit) was previously
    completely untested, including the commit-message pluralization
    branch."""
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    two_story_tier3_text = _TIER3_DEFERRAL_TEXT + (
        "\n### DW-21: Follow-up review still recommended for 4-5-other "
        "after the damping cap was spent\n"
        "origin: review-budget-followup\n"
        "source_spec: `spec-4-5-other.md`\n"
        "severity: low\n"
        "reason: A distinct followup entry for a second story in the same wave.\n"
        "status: open\n"
    )
    _tier3_path, tracked_path = _write_deferred_work_fixtures(
        tmp_path, "acme", tier3_text=two_story_tier3_text, tracked_text=_TRACKED_LEDGER_HEADER
    )
    second_subject = "Merge bmad-loop/run-1/4-5-other into loop/acme (bmad-loop)"
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT, second_subject),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert exit_code == 0
    assert sorted(payload["data"]["deferred_work_promoted"]) == ["DW-FU-4-4", "DW-FU-4-5"]
    ledger_text = tracked_path.read_text(encoding="utf-8")
    assert "### DW-FU-4-4:" in ledger_text
    assert "### DW-FU-4-5:" in ledger_text
    assert len(vcs.commit_paths_calls) == 1
    _called_root, _called_paths, called_message = vcs.commit_paths_calls[0]
    assert "entries" in called_message
    assert "2 deferred-work" in called_message
    # Story 5.10: a multi-key wave (`4-4`, `4-5`, sorted) renders its
    # subject from `wave_keys[0]` ONLY -- the wave's primary (lowest-sorted)
    # key -- never all wave keys.
    assert len(forge.merge_calls) == 1
    expected_subject = render_merge_subject(StoryKey(4, 4), _DEFAULT_MERGE_SUBJECT_TEMPLATE, "acme")
    assert forge.merge_calls[0][-1] == expected_subject
    assert payload["data"]["subject"] == expected_subject


# --- Story 15.2: sprint-status-ledger promotion on landing (FR-136/FR-139) --


def _write_sprint_ledger(tmp_path: Path, slug: str, statuses: dict[str, str]) -> Path:
    path = tmp_path / "_bmad-output" / "projects" / slug / "planning-artifacts" / "sprint-status-ledger.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(f"  {k}: {v}\n" for k, v in statuses.items())
    path.write_text(f"development_status:\n{body}", encoding="utf-8")
    return path


def test_sprint_ledger_promoted_on_merge(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    ledger_path = _write_sprint_ledger(tmp_path, "acme", {"4-4-batch": "in-progress"})
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert exit_code == 0
    assert payload["data"]["merged"] is True
    assert "4-4-batch" in payload["data"]["sprint_ledger_promoted"]
    assert "MRS-LAND-011" not in [f["code"] for f in payload["findings"]]
    assert "4-4-batch: done" in ledger_path.read_text(encoding="utf-8")
    assert any("sprint-status ledger" in msg for _r, _p, msg in vcs.commit_paths_calls)


def test_sprint_ledger_promoted_on_already_landed(tmp_path, capsys, monkeypatch):
    _patch_repo(monkeypatch, tmp_path)
    ledger_path = _write_sprint_ledger(tmp_path, "acme", {"4-4-batch": "review"})
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        base_subjects=(_BMADLOOP_WAVE_SUBJECT,),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert exit_code == 0
    assert payload["data"]["already_landed"] is True
    assert payload["data"]["sprint_ledger_promoted"] == ["4-4-batch"]
    assert "4-4-batch: done" in ledger_path.read_text(encoding="utf-8")


def test_sprint_ledger_idempotent_when_already_done(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    _write_sprint_ledger(tmp_path, "acme", {"4-4-batch": "done"})
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert exit_code == 0
    assert "sprint_ledger_promoted" not in payload["data"]
    # No sprint-ledger commit (deferred-work may still commit if fixtures present).
    sprint_commits = [msg for _r, _p, msg in vcs.commit_paths_calls if "sprint-status ledger" in msg]
    assert sprint_commits == []


def test_sprint_ledger_lock_contention_reports_warn(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    _write_sprint_ledger(tmp_path, "acme", {"4-4-batch": "in-progress"})

    class _LockRaisingFs(LocalFs):
        def acquire_advisory_lock(self, path, *, timeout_s):
            if path.name == "sprint-status-ledger.yaml":
                raise FsError("simulated sprint-ledger lock contention")
            return super().acquire_advisory_lock(path, timeout_s=timeout_s)

    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=_LockRaisingFs(), forge=forge)

    payload = _payload(capsys)
    assert exit_code == 0
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-011" in codes
    assert "sprint_ledger_promoted" not in payload["data"]


def test_sprint_ledger_promote_uses_isolated_remote_tip(tmp_path, capsys, monkeypatch):
    """CAP-5: land publishes via commit_paths_onto_remote_tip, never a
    raw commit_paths against the operator tree as the only write."""
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    _write_sprint_ledger(tmp_path, "acme", {"4-4-batch": "in-progress"})
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert exit_code == 0
    assert payload["data"]["sprint_ledger_promoted"] == ["4-4-batch"]
    assert len(vcs.isolated_promote_calls) == 1
    _root, remote, ref, writes, message = vcs.isolated_promote_calls[0]
    assert remote == "origin"
    assert ref == "main"
    assert writes[0][0].endswith("sprint-status-ledger.yaml")
    assert "4-4-batch: done" in writes[0][1]
    assert "sprint-status ledger" in message


def test_sprint_ledger_publish_names_its_story_in_the_preflight_reason(tmp_path, capsys, monkeypatch):
    """Story 68.1 (CAP-277): the promotion publish asks for the adapter's checked pre-push opt-out and
    names the promoted story in its reason (the hook journals it)."""
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    _write_sprint_ledger(tmp_path, "acme", {"4-4-batch": "in-progress"})
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=_FakeForge(existing=None))

    assert exit_code == 0
    [reason] = [
        r
        for (_root, _rm, _ref, writes, _msg), r in zip(vcs.isolated_promote_calls, vcs.isolated_promote_reasons)
        if writes[0][0].endswith("sprint-status-ledger.yaml")
    ]
    assert reason is not None
    assert "acme" in reason
    assert "story 4-4-batch" in reason


def _journal_entries(deploy_run) -> list[dict]:
    text = (deploy_run.run_dir / "journal.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line]


class _TimingOutPublishVcs(_FakeVcs):
    """64.1's failure shape: the promotion publish is killed at the git timeout."""

    def commit_paths_onto_remote_tip(self, repo_root, *, remote, ref, writes, message, preflight_skip_reason=None):
        self.isolated_promote_calls.append((repo_root, remote.value, ref.value, tuple(writes), message.text))
        self.isolated_promote_reasons.append(
            (preflight_skip_reason.text if preflight_skip_reason is not None else None)
        )
        raise VcsCommandError(
            f"git command timed out after 120.0s: git -C {repo_root} push origin abc123:refs/heads/main"
        )


def test_a_failed_ledger_publish_pairs_its_intent_with_an_outcome_ok_false(tmp_path):
    """Story 68.1 AC 4 (AD-6): INTENT, then OUTCOME `ok: false` naming the error, then MRS-LAND-011 and
    `()` -- never an INTENT left open while the run reports success."""
    _write_sprint_ledger(tmp_path, "acme", {"4-4-batch": "in-progress"})
    fs = LocalFs()
    vcs = _TimingOutPublishVcs()
    deploy_run = deploy_module._DeployRun(fs, tmp_path, "acme", "writer-1")
    findings: list = []

    promoted = land_module._promote_sprint_ledger(
        fs, vcs, tmp_path, "acme", [StoryKey(4, 4)], deploy_run, findings, base="main"
    )

    assert promoted == ()
    ledger_entries = [e for e in _journal_entries(deploy_run) if e["kind"] == "land-sprint-ledger-promotion"]
    assert [e["phase"] for e in ledger_entries] == ["intent", "outcome"]
    intent, outcome = ledger_entries
    assert outcome["intent_id"] == intent["id"]
    assert outcome["payload"]["ok"] is False
    assert "timed out after 120.0s" in outcome["payload"]["error"]
    assert outcome["payload"]["promoted"] == ["4-4-batch"]
    [finding] = [f for f in findings if f.code == "MRS-LAND-011"]
    assert finding.severity.name == "WARN"
    assert "timed out after 120.0s" in finding.message


def test_a_landed_ledger_publish_journals_an_outcome_ok_true(tmp_path):
    _write_sprint_ledger(tmp_path, "acme", {"4-4-batch": "in-progress"})
    fs = LocalFs()
    vcs = _FakeVcs()
    deploy_run = deploy_module._DeployRun(fs, tmp_path, "acme", "writer-1")
    findings: list = []

    promoted = land_module._promote_sprint_ledger(
        fs, vcs, tmp_path, "acme", [StoryKey(4, 4)], deploy_run, findings, base="main"
    )

    assert promoted == ("4-4-batch",)
    outcomes = [
        e
        for e in _journal_entries(deploy_run)
        if e["kind"] == "land-sprint-ledger-promotion" and e["phase"] == "outcome"
    ]
    assert [e["payload"]["ok"] for e in outcomes] == [True]
    assert not [f for f in findings if f.code == "MRS-LAND-011"]


def test_a_feed_only_ledger_sync_names_the_wave_keys_in_its_preflight_reason(tmp_path):
    """Story 68.1: when the Tier-3 feed advances rows but every wave key is already `done`, nothing was
    `promoted` -- the reason falls back to the wave's own story keys, so the hook's journal still names one."""
    ledger_path = _write_sprint_ledger(tmp_path, "acme", {"epic-4": "in-progress", "4-4-batch": "done"})
    feed_path = tmp_path / "_bmad-output" / "projects" / "acme" / "implementation-artifacts" / "sprint-status.yaml"
    feed_path.parent.mkdir(parents=True)
    feed_path.write_text(
        "development_status:\n  epic-4: in-progress\n  4-4-batch: done\n  4-5-follow-up: backlog\n",
        encoding="utf-8",
    )
    fs = LocalFs()
    vcs = _FakeVcs()
    deploy_run = deploy_module._DeployRun(fs, tmp_path, "acme", "writer-1")

    promoted = land_module._promote_sprint_ledger(
        fs, vcs, tmp_path, "acme", [StoryKey(4, 4)], deploy_run, [], base="main"
    )

    assert promoted == ("acme",)
    assert "4-5-follow-up" in ledger_path.read_text(encoding="utf-8")
    [reason] = vcs.isolated_promote_reasons
    assert reason is not None
    assert "story 4.4" in reason


def test_land_stays_exit_zero_with_a_warn_when_the_ledger_publish_times_out(tmp_path, capsys, monkeypatch):
    """`marshal land`'s own exit is unchanged (the wave already landed): the failure is a WARN finding."""
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    _write_sprint_ledger(tmp_path, "acme", {"4-4-batch": "in-progress"})
    vcs = _TimingOutPublishVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=_FakeForge(existing=None))

    payload = _payload(capsys)
    assert exit_code == 0
    assert "MRS-LAND-011" in [f["code"] for f in payload["findings"]]
    assert "sprint_ledger_promoted" not in payload["data"]


# --- Story 83.21: `marshal land`'s two promotion call sites publish the sync's epic roll-ups ----------------
#
# `run_land` reaches `_promote_sprint_ledger` from its merge path and from its already-landed path; both
# must publish the epic rows `scripts/promote_sprint_status.py::apply_epic_rollups` computes from the final
# statuses, never the Tier-3 feed's own stale `epic-N` row.

_STALE_EPIC_TWIN_83_21 = {"epic-4": "in-progress", "4-4-batch": "review", "4-5-other": "backlog"}


def _write_stale_epic_feed_83_21(tmp_path: Path) -> None:
    feed_path = tmp_path / "_bmad-output" / "projects" / "acme" / "implementation-artifacts" / "sprint-status.yaml"
    feed_path.parent.mkdir(parents=True, exist_ok=True)
    feed_path.write_text(
        "development_status:\n  epic-4: backlog\n  4-4-batch: review\n  4-5-other: backlog\n", encoding="utf-8"
    )


def _published_ledger_83_21(vcs) -> str:
    [ledger_text] = [
        writes[0][1]
        for (_root, _rm, _ref, writes, _msg) in vcs.isolated_promote_calls
        if writes[0][0].endswith("sprint-status-ledger.yaml")
    ]
    return ledger_text


def test_land_merge_path_publishes_the_syncs_epic_roll_up_over_a_stale_feed_epic_row(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    _write_sprint_ledger(tmp_path, "acme", _STALE_EPIC_TWIN_83_21)
    _write_stale_epic_feed_83_21(tmp_path)
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=_FakeForge(existing=None))

    payload = _payload(capsys)
    assert exit_code == 0
    assert payload["data"]["merged"] is True
    statuses = land_module._parse_sprint_ledger_statuses(_published_ledger_83_21(vcs))
    assert statuses == {"4-4-batch": "done", "4-5-other": "backlog", "epic-4": "in-progress"}


def test_land_already_landed_path_rolls_the_last_open_story_s_epic_to_done(tmp_path, capsys, monkeypatch):
    _patch_repo(monkeypatch, tmp_path)
    _write_sprint_ledger(tmp_path, "acme", {"epic-4": "in-progress", "4-4-batch": "review"})
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        base_subjects=(_BMADLOOP_WAVE_SUBJECT,),
    )

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=_FakeForge(existing=None))

    payload = _payload(capsys)
    assert exit_code == 0
    assert payload["data"]["already_landed"] is True
    statuses = land_module._parse_sprint_ledger_statuses(_published_ledger_83_21(vcs))
    assert statuses == {"4-4-batch": "done", "epic-4": "done"}


class _FakePromoteModForRefusal:
    @staticmethod
    def regressions(existing: dict, incoming: dict):
        # Mirrors scripts/promote_sprint_status.py::regressions -- a key
        # already done or story-blocked moving out of that state.
        TERMINAL = {"done"}
        out = []
        for key, old in sorted(existing.items()):
            if old not in TERMINAL:
                continue
            new = incoming.get(key)
            if new is None:
                out.append((key, old, "<absent>"))
            elif new not in TERMINAL:
                out.append((key, old, new))
        return out


def test_land_feed_sync_refusal_none_when_incoming_is_a_superset() -> None:
    existing = {"1-1-a": "done", "1-2-b": "backlog"}
    incoming = {"1-1-a": "done", "1-2-b": "backlog", "1-3-c": "backlog"}
    assert land_module._land_feed_sync_refusal(_FakePromoteModForRefusal, existing, incoming) is None


def test_land_feed_sync_refusal_catches_dropped_done_key() -> None:
    existing = {"1-1-a": "done"}
    incoming = {}
    refusal = land_module._land_feed_sync_refusal(_FakePromoteModForRefusal, existing, incoming)
    assert refusal is not None
    label, detail = refusal
    assert label == "un-finish"
    assert "1-1-a" in detail


def test_land_feed_sync_refusal_catches_dropped_backlog_key() -> None:
    # Live incident 2026-09-10: a still-backlog story in a freshly-authored
    # epic the feed has never seen -- regressions() alone misses this
    # entirely since "backlog" was never a protected state.
    existing = {"12-1-a": "done", "12-2-b": "backlog", "12-3-c": "backlog"}
    incoming = {"12-1-a": "done"}
    refusal = land_module._land_feed_sync_refusal(_FakePromoteModForRefusal, existing, incoming)
    assert refusal is not None
    label, detail = refusal
    assert label == "drop"
    assert "12-2-b" in detail
    assert "12-3-c" in detail


# --- Story 83.22: guard reads the publish target; sync parser everywhere; missing-roll-up WARN ---


def _write_tier3_feed(tmp_path: Path, slug: str, body: str) -> Path:
    path = tmp_path / "_bmad-output" / "projects" / slug / "implementation-artifacts" / "sprint-status.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_promote_feed_sync_guard_judges_origin_main_not_stale_local_ledger(tmp_path):
    """When the primary ledger lags origin/main, a feed that drops a remote-only backlog key is refused."""
    _write_sprint_ledger(
        tmp_path,
        "acme",
        {"12-1-a": "done"},
    )
    remote_twin = "development_status:\n  12-1-a: done\n  12-2-b: backlog\n"
    _write_tier3_feed(tmp_path, "acme", "development_status:\n  12-1-a: done\n")
    fs = LocalFs()
    vcs = _FakeVcs(remote_ledger_text=remote_twin)
    deploy_run = deploy_module._DeployRun(fs, tmp_path, "acme", "writer-83-22")
    findings: list = []

    promoted = land_module._promote_sprint_ledger(
        fs, vcs, tmp_path, "acme", [StoryKey(12, 1)], deploy_run, findings, base="main"
    )

    assert promoted == ()
    assert not vcs.isolated_promote_calls
    refusal = next(f for f in findings if f.code == "MRS-LAND-011" and "feed would drop" in f.message)
    assert "12-2-b" in refusal.message


def test_promote_feed_sync_guard_mutation_local_ledger_parser_would_sync_the_drop(tmp_path, monkeypatch):
    remote_twin = "development_status:\n  12-1-a: done\n  12-2-b: backlog\n"
    local_text = "development_status:\n  12-1-a: done\n"
    _write_sprint_ledger(tmp_path, "acme", {"12-1-a": "done"})
    _write_tier3_feed(tmp_path, "acme", "development_status:\n  12-1-a: done\n")
    fs = LocalFs()
    vcs = _FakeVcs(remote_ledger_text=remote_twin)
    deploy_run = deploy_module._DeployRun(fs, tmp_path, "acme", "writer-83-22-mut")
    findings: list = []

    monkeypatch.setattr(
        land_module,
        "_parse_sync_sprint_status_text",
        lambda _fresh: land_module._parse_sprint_ledger_statuses(local_text),
    )

    promoted = land_module._promote_sprint_ledger(
        fs, vcs, tmp_path, "acme", [StoryKey(12, 1)], deploy_run, findings, base="main"
    )

    assert promoted == ("acme",)
    assert vcs.isolated_promote_calls
    published = vcs.isolated_promote_calls[0][3][0][1]
    assert "12-2-b" not in published


def test_promote_feed_sync_refuses_un_finish_against_origin_main(tmp_path):
    remote_twin = "development_status:\n  12-1-a: done\n"
    _write_sprint_ledger(tmp_path, "acme", {"12-1-a": "backlog"})
    _write_tier3_feed(tmp_path, "acme", "development_status:\n  12-1-a: backlog\n")
    fs = LocalFs()
    vcs = _FakeVcs(remote_ledger_text=remote_twin)
    findings: list = []

    land_module._promote_sprint_ledger(
        fs, vcs, tmp_path, "acme", [StoryKey(12, 1)], deploy_module._DeployRun(fs, tmp_path, "acme", "w"), findings, base="main"
    )

    refusal = next(f for f in findings if "un-finish" in f.message)
    assert "12-1-a" in refusal.message
    assert not vcs.isolated_promote_calls


def test_promote_feed_sync_does_not_refuse_done_key_only_on_stale_local(tmp_path):
    remote_twin = "development_status:\n  12-1-a: backlog\n"
    _write_sprint_ledger(tmp_path, "acme", {"12-1-a": "done", "12-2-b": "backlog"})
    _write_tier3_feed(tmp_path, "acme", "development_status:\n  12-2-b: backlog\n")
    fs = LocalFs()
    vcs = _FakeVcs(remote_ledger_text=remote_twin)
    findings: list = []

    land_module._promote_sprint_ledger(
        fs, vcs, tmp_path, "acme", [StoryKey(12, 2)], deploy_module._DeployRun(fs, tmp_path, "acme", "w"), findings, base="main"
    )

    drop_refusals = [f for f in findings if "feed would drop" in f.message and "12-1-a" in f.message]
    assert not drop_refusals


def test_roll_up_epic_rows_reads_rows_below_a_column_zero_comment(tmp_path):
    text = (
        "development_status:\n"
        "# wave note\n"
        "  epic-4: in-progress\n"
        "  4-4-batch: done\n"
        "  4-5-other: done\n"
    )
    promote_mod = land_module._load_promote_sprint_status_module()
    rollup = land_module._sync_epic_rollup(promote_mod)
    assert rollup is not None
    rolled = land_module._roll_up_epic_rows(text, rollup)
    statuses = land_module._parse_sync_sprint_status_text(rolled)
    assert statuses["epic-4"] == "done"


def test_roll_up_epic_rows_mutation_land_parser_misses_comment_below_rows():
    text = (
        "development_status:\n"
        "# wave note\n"
        "  epic-4: in-progress\n"
        "  4-4-batch: done\n"
        "  4-5-other: done\n"
    )
    promote_mod = land_module._load_promote_sprint_status_module()
    rollup = land_module._sync_epic_rollup(promote_mod)
    assert rollup is not None
    statuses = {
        key: value.partition("#")[0].strip()
        for key, value in land_module._parse_sprint_ledger_statuses(text).items()
    }
    rolled = rollup(dict(statuses))
    assert rolled.get("epic-4") != "done"


def test_promote_warns_missing_rollup_when_feed_present_and_nothing_to_publish(tmp_path, monkeypatch):
    monkeypatch.setattr(land_module, "_load_promote_sprint_status_module", lambda: None)
    _write_sprint_ledger(tmp_path, "acme", {"4-4-batch": "done", "epic-4": "done"})
    _write_tier3_feed(tmp_path, "acme", "development_status:\n  4-4-batch: done\n  epic-4: done\n")
    fs = LocalFs()
    vcs = _FakeVcs()
    findings: list = []

    promoted = land_module._promote_sprint_ledger(
        fs, vcs, tmp_path, "acme", [StoryKey(4, 4)], deploy_module._DeployRun(fs, tmp_path, "acme", "w"), findings, base="main"
    )

    assert promoted == ()
    assert not vcs.isolated_promote_calls
    assert any("apply_epic_rollups" in f.message for f in findings)
