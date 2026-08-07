"""Unit tests for ``cli/land.py`` (``marshal land``, Story 4.8, FR-60/AD-40).

Fake ``VcsPort``/``ForgePort`` doubles mirror ``tests/unit/test_deploy.py``'s
own established convention (hand-written classes implementing the Protocol,
never mocks); filesystem I/O runs against a REAL ``tmp_path`` via the real
``LocalFs``, same as every ``cli/deploy.py`` test.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from pyforge.marshal.adapters.fs_local import LocalFs
from pyforge.marshal.adapters.vcs_git import VcsCommandError
from pyforge.marshal.cli import deploy as deploy_module
from pyforge.marshal.cli import land as land_module
from pyforge.marshal.ports.forge import ForgeCommandError, PrInfo
from pyforge.marshal.ports.process import ProcessResult

_BMADLOOP_WAVE_SUBJECT = "Merge bmad-loop/run-1/4-4-batch into loop/acme (bmad-loop)"


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
        if ref == "main":
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

    def merge_pr(self, repo, number, strategy, *, expected_head_sha, delete_branch):
        self.merge_calls.append(
            (repo, number, strategy.value, expected_head_sha.value, delete_branch)
        )
        if self.merge_raises:
            raise ForgeCommandError("gh pr merge failed")


def _args(*, slug: str = "acme", format: str = "json") -> argparse.Namespace:
    return argparse.Namespace(slug=slug, format=format)


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
        monkeypatch.setattr(
            land_module, "conventional_project_policy_path", lambda slug: policy_path
        )


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
    policy_path = _write_project_policy(tmp_path, "landing_rules = \"not-a-list\"\n")
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    vcs = _FakeVcs(existing_branches=frozenset({"loop/acme"}))
    forge = _FakeForge()

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-LAND-002" in codes
    assert exit_code != 0
    assert forge.find_calls == []


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
    repo, number, strategy, expected_head_sha, delete_branch = forge.merge_calls[0]
    assert number == 1
    assert strategy == "merge"
    assert expected_head_sha
    assert delete_branch is True


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


def test_rule_with_both_label_and_required_check_applies_label_once_satisfied(
    tmp_path, capsys, monkeypatch
):
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


def test_required_check_error_does_not_drop_an_unrelated_rules_pending_warn(
    tmp_path, capsys, monkeypatch
):
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
    forge = _FakeForge(
        existing=None, check_status_map={"check-a": "failure", "check-b": None}
    )

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


def test_required_check_pending_and_acknowledged_proceeds_to_merge(
    tmp_path, capsys, monkeypatch
):
    policy_path = _write_project_policy(tmp_path, _rule_policy())
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    ack_path = tmp_path / "ack" / "adapter-acknowledgements.json"
    ack_path.parent.mkdir(parents=True, exist_ok=True)
    # Scoped ack key (code review, 2026-08-06): acknowledging the bare
    # `MRS-LAND-005` code would bypass EVERY project/rule/check's pending
    # gate forever -- only THIS rule/check/project's own key is written.
    scoped_key = land_module._required_check_ack_key(
        "environment-yaml-sync", "environment-yaml-sync", "acme"
    )
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
    repo, number, strategy, expected_head_sha, delete_branch = forge.merge_calls[0]
    assert delete_branch is False


def test_landing_resync_false_skips_resync(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(
        tmp_path, "landing_resync = false\n" + _rule_policy(required_check=None)
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
        raise AssertionError(
            f"reconcile_feed's resync path must never call FsPort.{name}"
        )

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


def test_reconcile_feed_resync_runs_at_root_and_never_writes_under_a_loop_home(
    tmp_path, monkeypatch
):
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
    policy_path.write_text(
        'landing_resync = true\nlanding_resync_commands = ["true"]\n', encoding="utf-8"
    )
    monkeypatch.setattr(
        deploy_module, "conventional_project_policy_path", lambda slug: policy_path
    )

    process = _RecordingProcess()
    fs = _NoWriteFs()
    vcs = _FakeVcs(base_subjects=("Merge 1.2 into main",))
    args = argparse.Namespace(project="acme", format="json")

    data, findings = deploy_module.reconcile_feed(
        args, vcs=vcs, fs=fs, process=process, harness=_UnusedHarness()
    )

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
