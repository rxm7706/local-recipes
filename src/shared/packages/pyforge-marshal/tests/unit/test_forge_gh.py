"""Unit tests for ``pyforge.marshal.adapters.forge_gh`` (Story 4.4, NFR-2,
AD-4/AD-34) -- ``GhForge`` against a FAKE ``subprocess.run`` (mirrors
``tests/unit/test_process_posix.py``/``test_harness_bmadloop_spin.py``'s own
``monkeypatch.setattr(module.subprocess, "run", ...)`` convention): never a
real network call, per the story's own Manual Checks note.
"""

from __future__ import annotations

import json
import subprocess

import pytest

from pyforge.marshal.adapters import forge_gh as forge_gh_module
from pyforge.marshal.adapters.forge_gh import GhForge
from pyforge.marshal.core.egress import Redacted
from pyforge.marshal.ports.forge import ForgeCommandError, ForgeRef, PrInfo


class _ScriptedRun:
    """A fake ``subprocess.run`` returning queued
    ``subprocess.CompletedProcess`` results in call order, recording every
    invoked ``argv`` for assertion."""

    def __init__(self, results: list[subprocess.CompletedProcess[str]]) -> None:
        self._results = list(results)
        self.calls: list[list[str]] = []

    def __call__(self, args, **kwargs):
        self.calls.append(list(args))
        if not self._results:
            raise AssertionError(f"no scripted result left for {args!r}")
        return self._results.pop(0)


def _completed(args: list[str], *, returncode: int = 0, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(args=args, returncode=returncode, stdout=stdout, stderr=stderr)


@pytest.fixture
def forge() -> GhForge:
    return GhForge()


_REPO = ForgeRef("acme/widgets")


# --- find_open_pr -------------------------------------------------------------


def test_find_open_pr_returns_none_when_no_open_pr(forge, monkeypatch):
    run = _ScriptedRun([_completed([], stdout="[]")])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    assert forge.find_open_pr(_REPO, ForgeRef("loop/acme")) is None


def test_find_open_pr_returns_pr_info(forge, monkeypatch):
    payload = json.dumps(
        [{"number": 42, "url": "https://example/pr/42", "state": "OPEN", "baseRefName": "main"}]
    )
    run = _ScriptedRun([_completed([], stdout=payload)])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    result = forge.find_open_pr(_REPO, ForgeRef("loop/acme"))
    assert result == PrInfo(number=42, url="https://example/pr/42", state="open", base="main")


def test_find_open_pr_raises_on_missing_base_ref_name(forge, monkeypatch):
    payload = json.dumps([{"number": 42, "url": "https://example/pr/42", "state": "OPEN"}])
    run = _ScriptedRun([_completed([], stdout=payload)])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    with pytest.raises(ForgeCommandError, match="baseRefName"):
        forge.find_open_pr(_REPO, ForgeRef("loop/acme"))


def test_find_open_pr_raises_on_nonzero_exit(forge, monkeypatch):
    run = _ScriptedRun([_completed([], returncode=1, stderr="not authenticated")])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    with pytest.raises(ForgeCommandError, match="not authenticated"):
        forge.find_open_pr(_REPO, ForgeRef("loop/acme"))


def test_find_open_pr_raises_on_invalid_json(forge, monkeypatch):
    run = _ScriptedRun([_completed([], stdout="not json")])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    with pytest.raises(ForgeCommandError, match="invalid JSON"):
        forge.find_open_pr(_REPO, ForgeRef("loop/acme"))


def test_find_open_pr_raises_on_non_list_payload(forge, monkeypatch):
    run = _ScriptedRun([_completed([], stdout=json.dumps({"not": "a list"}))])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    with pytest.raises(ForgeCommandError, match="non-list payload"):
        forge.find_open_pr(_REPO, ForgeRef("loop/acme"))


def test_find_open_pr_passes_repo_and_head_branch_argv(forge, monkeypatch):
    run = _ScriptedRun([_completed([], stdout="[]")])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    forge.find_open_pr(_REPO, ForgeRef("loop/acme"))
    (argv,) = run.calls
    assert argv[:3] == ["gh", "pr", "list"]
    assert "--repo" in argv and argv[argv.index("--repo") + 1] == "acme/widgets"
    assert "--head" in argv and argv[argv.index("--head") + 1] == "loop/acme"


# --- create_pr ------------------------------------------------------------


def test_create_pr_requires_redacted_title_and_body(forge):
    with pytest.raises(TypeError):
        forge.create_pr(
            _REPO, ForgeRef("main"), ForgeRef("loop/acme"), "bare-str-title", Redacted(text="body")
        )
    with pytest.raises(TypeError):
        forge.create_pr(
            _REPO, ForgeRef("main"), ForgeRef("loop/acme"), Redacted(text="title"), "bare-str-body"
        )


def test_create_pr_creates_then_looks_up_the_new_pr(forge, monkeypatch):
    created = json.dumps(
        [{"number": 7, "url": "https://example/pr/7", "state": "open", "baseRefName": "main"}]
    )
    run = _ScriptedRun([_completed([], returncode=0, stdout=""), _completed([], stdout=created)])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    result = forge.create_pr(
        _REPO, ForgeRef("main"), ForgeRef("loop/acme"), Redacted(text="title"), Redacted(text="body")
    )
    assert result == PrInfo(number=7, url="https://example/pr/7", state="open", base="main")
    create_argv, list_argv = run.calls
    assert create_argv[:3] == ["gh", "pr", "create"]
    assert "--title" in create_argv and create_argv[create_argv.index("--title") + 1] == "title"
    assert "--body" in create_argv and create_argv[create_argv.index("--body") + 1] == "body"
    assert list_argv[:3] == ["gh", "pr", "list"]


def test_create_pr_raises_when_gh_pr_create_fails(forge, monkeypatch):
    run = _ScriptedRun([_completed([], returncode=1, stderr="validation failed")])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    with pytest.raises(ForgeCommandError, match="validation failed"):
        forge.create_pr(
            _REPO, ForgeRef("main"), ForgeRef("loop/acme"), Redacted(text="t"), Redacted(text="b")
        )


def test_create_pr_raises_when_followup_lookup_finds_nothing(forge, monkeypatch):
    run = _ScriptedRun([_completed([], returncode=0), _completed([], stdout="[]")])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    with pytest.raises(ForgeCommandError, match="no open PR"):
        forge.create_pr(
            _REPO, ForgeRef("main"), ForgeRef("loop/acme"), Redacted(text="t"), Redacted(text="b")
        )


# --- update_pr --------------------------------------------------------------


def test_update_pr_requires_redacted_title_and_body(forge):
    with pytest.raises(TypeError):
        forge.update_pr(_REPO, 1, "bare-str", Redacted(text="body"))


def test_update_pr_edits_then_views(forge, monkeypatch):
    viewed = json.dumps(
        {"number": 9, "url": "https://example/pr/9", "state": "OPEN", "baseRefName": "main"}
    )
    run = _ScriptedRun([_completed([], returncode=0), _completed([], stdout=viewed)])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    result = forge.update_pr(_REPO, 9, Redacted(text="new title"), Redacted(text="new body"))
    assert result == PrInfo(number=9, url="https://example/pr/9", state="open", base="main")
    edit_argv, view_argv = run.calls
    assert edit_argv[:3] == ["gh", "pr", "edit"]
    assert edit_argv[3] == "9"
    assert view_argv[:3] == ["gh", "pr", "view"]


def test_update_pr_raises_when_edit_fails(forge, monkeypatch):
    run = _ScriptedRun([_completed([], returncode=1, stderr="no such PR")])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    with pytest.raises(ForgeCommandError, match="no such PR"):
        forge.update_pr(_REPO, 9, Redacted(text="t"), Redacted(text="b"))


def test_update_pr_raises_when_view_fails_after_edit(forge, monkeypatch):
    run = _ScriptedRun([_completed([], returncode=0), _completed([], returncode=1, stderr="gone")])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    with pytest.raises(ForgeCommandError, match="gone"):
        forge.update_pr(_REPO, 9, Redacted(text="t"), Redacted(text="b"))


# --- add_labels ---------------------------------------------------------------


def test_add_labels_is_a_noop_for_an_empty_tuple(forge, monkeypatch):
    run = _ScriptedRun([])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    forge.add_labels(_REPO, 3, ())
    assert run.calls == []


def test_add_labels_applies_every_label(forge, monkeypatch):
    run = _ScriptedRun([_completed([], returncode=0)])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    forge.add_labels(_REPO, 3, ("maintenance", "urgent"))
    (argv,) = run.calls
    assert argv[:3] == ["gh", "pr", "edit"]
    assert argv.count("--add-label") == 2
    assert "maintenance" in argv and "urgent" in argv


def test_add_labels_raises_on_failure(forge, monkeypatch):
    run = _ScriptedRun([_completed([], returncode=1, stderr="label does not exist")])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    with pytest.raises(ForgeCommandError, match="label does not exist"):
        forge.add_labels(_REPO, 3, ("bogus",))


# --- check_run_status ----------------------------------------------------------


def test_check_run_status_returns_the_matching_conclusion(forge, monkeypatch):
    payload = json.dumps(
        {
            "check_runs": [
                {"name": "environment-yaml-sync", "conclusion": "success"},
                {"name": "other-check", "conclusion": "failure"},
            ]
        }
    )
    run = _ScriptedRun([_completed([], stdout=payload)])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    status = forge.check_run_status(_REPO, ForgeRef("deadbeef"), ForgeRef("environment-yaml-sync"))
    assert status == "success"


def test_check_run_status_returns_none_when_no_such_check(forge, monkeypatch):
    payload = json.dumps({"check_runs": [{"name": "other-check", "conclusion": "success"}]})
    run = _ScriptedRun([_completed([], stdout=payload)])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    status = forge.check_run_status(_REPO, ForgeRef("deadbeef"), ForgeRef("no-such-check"))
    assert status is None


def test_check_run_status_returns_none_when_conclusion_still_pending(forge, monkeypatch):
    payload = json.dumps({"check_runs": [{"name": "slow-check", "conclusion": None}]})
    run = _ScriptedRun([_completed([], stdout=payload)])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    status = forge.check_run_status(_REPO, ForgeRef("deadbeef"), ForgeRef("slow-check"))
    assert status is None


def test_check_run_status_raises_on_gh_failure(forge, monkeypatch):
    run = _ScriptedRun([_completed([], returncode=1, stderr="not found")])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    with pytest.raises(ForgeCommandError, match="not found"):
        forge.check_run_status(_REPO, ForgeRef("deadbeef"), ForgeRef("x"))


def test_check_run_status_uses_the_repo_commit_check_runs_endpoint(forge, monkeypatch):
    run = _ScriptedRun([_completed([], stdout=json.dumps({"check_runs": []}))])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    forge.check_run_status(_REPO, ForgeRef("deadbeef"), ForgeRef("x"))
    (argv,) = run.calls
    assert argv == ["gh", "api", "repos/acme/widgets/commits/deadbeef/check-runs"]


def test_check_run_status_prefers_the_most_recent_run_over_response_order(forge, monkeypatch):
    """Code review (2026-08-06, P3, both reviewers independently): GitHub
    can report multiple runs under the same check name (reruns), and this
    endpoint's response order is not guaranteed newest-first. An older
    "success" appearing FIRST in the response must never mask a real,
    newer "failure" -- the most recent run by ``started_at`` wins,
    regardless of response order."""
    payload = json.dumps(
        {
            "check_runs": [
                {
                    "name": "environment-yaml-sync",
                    "conclusion": "success",
                    "started_at": "2026-08-01T00:00:00Z",
                },
                {
                    "name": "environment-yaml-sync",
                    "conclusion": "failure",
                    "started_at": "2026-08-06T00:00:00Z",
                },
            ]
        }
    )
    run = _ScriptedRun([_completed([], stdout=payload)])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    status = forge.check_run_status(_REPO, ForgeRef("deadbeef"), ForgeRef("environment-yaml-sync"))
    assert status == "failure"


def test_check_run_status_treats_a_missing_started_at_as_oldest(forge, monkeypatch):
    payload = json.dumps(
        {
            "check_runs": [
                {"name": "x", "conclusion": "failure"},
                {"name": "x", "conclusion": "success", "started_at": "2026-08-06T00:00:00Z"},
            ]
        }
    )
    run = _ScriptedRun([_completed([], stdout=payload)])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    status = forge.check_run_status(_REPO, ForgeRef("deadbeef"), ForgeRef("x"))
    assert status == "success"


# --- merge_pr (Story 4.8) --------------------------------------------------


def test_merge_pr_merge_strategy_argv(forge, monkeypatch):
    run = _ScriptedRun([_completed([], returncode=0)])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    forge.merge_pr(
        _REPO, 42, ForgeRef("merge"), expected_head_sha=ForgeRef("deadbeef"), delete_branch=False
    )
    (argv,) = run.calls
    assert argv[:4] == ["gh", "pr", "merge", "42"]
    assert "--repo" in argv and argv[argv.index("--repo") + 1] == "acme/widgets"
    assert "--merge" in argv
    assert "--match-head-commit" in argv
    assert argv[argv.index("--match-head-commit") + 1] == "deadbeef"
    assert "--delete-branch" not in argv


def test_merge_pr_squash_strategy_argv(forge, monkeypatch):
    run = _ScriptedRun([_completed([], returncode=0)])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    forge.merge_pr(
        _REPO, 42, ForgeRef("squash"), expected_head_sha=ForgeRef("deadbeef"), delete_branch=False
    )
    (argv,) = run.calls
    assert "--squash" in argv


def test_merge_pr_rebase_strategy_argv(forge, monkeypatch):
    run = _ScriptedRun([_completed([], returncode=0)])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    forge.merge_pr(
        _REPO, 42, ForgeRef("rebase"), expected_head_sha=ForgeRef("deadbeef"), delete_branch=False
    )
    (argv,) = run.calls
    assert "--rebase" in argv


def test_merge_pr_delete_branch_true_adds_flag(forge, monkeypatch):
    run = _ScriptedRun([_completed([], returncode=0)])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    forge.merge_pr(
        _REPO, 42, ForgeRef("merge"), expected_head_sha=ForgeRef("deadbeef"), delete_branch=True
    )
    (argv,) = run.calls
    assert "--delete-branch" in argv


def test_merge_pr_raises_on_gh_failure(forge, monkeypatch):
    run = _ScriptedRun([_completed([], returncode=1, stderr="pull request is not mergeable")])
    monkeypatch.setattr(forge_gh_module, "_run", run)
    with pytest.raises(ForgeCommandError, match="not mergeable"):
        forge.merge_pr(
            _REPO, 42, ForgeRef("merge"), expected_head_sha=ForgeRef("deadbeef"), delete_branch=True
        )


# --- gh launch failures (never a real network call; a real gh is never invoked) --


def test_a_missing_gh_executable_raises_forge_command_error(forge, monkeypatch):
    def _raise_not_found(args, **kwargs):
        raise FileNotFoundError("no such file: gh")

    monkeypatch.setattr(forge_gh_module.subprocess, "run", _raise_not_found)
    with pytest.raises(ForgeCommandError, match="gh executable not found"):
        forge.find_open_pr(_REPO, ForgeRef("loop/acme"))


def test_a_hung_gh_process_raises_forge_command_error(forge, monkeypatch):
    def _raise_timeout(args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args, timeout=kwargs.get("timeout", 1))

    monkeypatch.setattr(forge_gh_module.subprocess, "run", _raise_timeout)
    with pytest.raises(ForgeCommandError, match="timed out"):
        forge.find_open_pr(_REPO, ForgeRef("loop/acme"))
