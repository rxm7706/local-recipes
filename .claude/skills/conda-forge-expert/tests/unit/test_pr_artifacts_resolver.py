"""Unit tests for `pr_artifacts.parse_pr_ref` + `resolve_build_ids`.

Fixture data mirrors the real `gh pr checks 33693 --repo
conda-forge/staged-recipes --json name,link,bucket,state` shape captured
during the v8.13.2 gh-copilot-cli session (PR #33693, buildId 1536673).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_PR_ARTIFACTS_PATH = (
    Path(__file__).resolve().parent.parent.parent / "scripts" / "pr_artifacts.py"
)
spec = importlib.util.spec_from_file_location("pr_artifacts", _PR_ARTIFACTS_PATH)
assert spec is not None and spec.loader is not None
pra = importlib.util.module_from_spec(spec)
sys.modules["pr_artifacts"] = pra
spec.loader.exec_module(pra)


# ── parse_pr_ref ────────────────────────────────────────────────────────────

class TestParsePrRef:
    def test_bare_pr_number_uses_default_repo(self):
        assert pra.parse_pr_ref("33693") == ("conda-forge/staged-recipes", 33693)

    def test_github_url_staged_recipes(self):
        url = "https://github.com/conda-forge/staged-recipes/pull/33693"
        assert pra.parse_pr_ref(url) == ("conda-forge/staged-recipes", 33693)

    def test_github_url_feedstock(self):
        url = "https://github.com/conda-forge/numpy-feedstock/pull/42"
        assert pra.parse_pr_ref(url) == ("conda-forge/numpy-feedstock", 42)

    def test_github_url_with_trailing_files_segment(self):
        url = "https://github.com/conda-forge/staged-recipes/pull/33693/files"
        assert pra.parse_pr_ref(url) == ("conda-forge/staged-recipes", 33693)

    def test_invalid_ref_raises(self):
        with pytest.raises(ValueError):
            pra.parse_pr_ref("not-a-pr")
        with pytest.raises(ValueError):
            pra.parse_pr_ref("https://example.com/foo")


# ── resolve_build_ids ───────────────────────────────────────────────────────

_PR_33693_ROWS = [
    {
        "name": "linter",
        "link": "https://github.com/conda-forge/staged-recipes/actions/runs/12345",
        "bucket": "pass",
        "state": "SUCCESS",
    },
    {
        "name": "staged-recipes",
        "link": (
            "https://dev.azure.com/conda-forge/feedstock-builds/_build/results"
            "?buildId=1536673&view=results"
        ),
        "bucket": "pass",
        "state": "SUCCESS",
    },
]

_FEEDSTOCK_ROWS = [
    {
        "name": "numpy-feedstock",
        "link": (
            "https://dev.azure.com/conda-forge/feedstock-builds/_build/results"
            "?buildId=9000001"
        ),
        "bucket": "pass",
        "state": "SUCCESS",
    },
]

_MULTI_RUN_ROWS = [
    {
        "name": "staged-recipes",
        "link": "https://dev.azure.com/conda-forge/feedstock-builds/_build/results?buildId=100",
        "bucket": "pass",
        "state": "SUCCESS",
    },
    {
        "name": "staged-recipes",
        "link": "https://dev.azure.com/conda-forge/feedstock-builds/_build/results?buildId=300",
        "bucket": "pass",
        "state": "SUCCESS",
    },
    {
        "name": "staged-recipes",
        "link": "https://dev.azure.com/conda-forge/feedstock-builds/_build/results?buildId=200",
        "bucket": "pass",
        "state": "SUCCESS",
    },
]


class TestResolveBuildIds:
    def test_staged_recipes_returns_single_buildid(self, monkeypatch):
        monkeypatch.setattr(pra, "_gh_pr_checks", lambda pr, repo: _PR_33693_ROWS)
        assert pra.resolve_build_ids(33693) == [1536673]

    def test_feedstock_repo_auto_detects_check_name(self, monkeypatch):
        monkeypatch.setattr(pra, "_gh_pr_checks", lambda pr, repo: _FEEDSTOCK_ROWS)
        ids = pra.resolve_build_ids(42, repo="conda-forge/numpy-feedstock")
        assert ids == [9000001]

    def test_all_runs_returns_multiple_descending(self, monkeypatch):
        monkeypatch.setattr(pra, "_gh_pr_checks", lambda pr, repo: _MULTI_RUN_ROWS)
        ids = pra.resolve_build_ids(33693, all_runs=True)
        assert ids == [300, 200, 100]

    def test_default_picks_highest_buildid(self, monkeypatch):
        monkeypatch.setattr(pra, "_gh_pr_checks", lambda pr, repo: _MULTI_RUN_ROWS)
        ids = pra.resolve_build_ids(33693, all_runs=False)
        assert ids == [300]

    def test_no_azure_check_raises_lookup_error(self, monkeypatch):
        only_linter = [_PR_33693_ROWS[0]]
        monkeypatch.setattr(pra, "_gh_pr_checks", lambda pr, repo: only_linter)
        with pytest.raises(LookupError) as excinfo:
            pra.resolve_build_ids(33693)
        assert "No Azure build found" in str(excinfo.value)

    def test_explicit_check_name_override(self, monkeypatch):
        rows = [
            {
                "name": "custom-build-row",
                "link": "https://dev.azure.com/conda-forge/feedstock-builds/_build/results?buildId=555",
                "bucket": "pass",
                "state": "SUCCESS",
            },
        ]
        monkeypatch.setattr(pra, "_gh_pr_checks", lambda pr, repo: rows)
        assert pra.resolve_build_ids(99, check_name="custom-build-row") == [555]


class TestGhPrChecksSubprocess:
    """Failure-mode coverage on the `gh pr checks` subprocess boundary.

    Patched at v8.14.0-post-review for: missing-binary friendly error,
    bounded timeout (no indefinite hang on auth prompt / network stall).
    """

    def test_gh_not_installed_raises_friendly_error(self, monkeypatch):
        import subprocess as _sp

        def fake_run(*args, **kwargs):
            raise FileNotFoundError(2, "No such file or directory: 'gh'")

        monkeypatch.setattr(pra.subprocess, "run", fake_run)
        with pytest.raises(RuntimeError, match="gh CLI not found"):
            pra._gh_pr_checks(33693, "conda-forge/staged-recipes")

    def test_gh_timeout_raises_friendly_error(self, monkeypatch):
        import subprocess as _sp

        def fake_run(*args, **kwargs):
            raise _sp.TimeoutExpired(cmd=args[0], timeout=60)

        monkeypatch.setattr(pra.subprocess, "run", fake_run)
        with pytest.raises(RuntimeError, match="timed out"):
            pra._gh_pr_checks(33693, "conda-forge/staged-recipes")

    def test_gh_timeout_kwarg_propagates_to_subprocess(self, monkeypatch):
        captured: dict = {}

        class _FakeResult:
            returncode = 0
            stdout = "[]"
            stderr = ""

        def fake_run(*args, **kwargs):
            captured["timeout"] = kwargs.get("timeout")
            return _FakeResult()

        monkeypatch.setattr(pra.subprocess, "run", fake_run)
        pra._gh_pr_checks(33693, "conda-forge/staged-recipes", timeout=30)
        assert captured["timeout"] == 30
