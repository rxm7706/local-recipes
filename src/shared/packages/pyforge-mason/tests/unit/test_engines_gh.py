"""Story 3.7 -- `engines/gh.py`'s standalone adapter: `probe()` and
`find_open_pr()`. Mirrors `test_engines_pixi.py`'s own conventions (mocking
`probe_engine`/`subprocess.run` at this module's own namespace) -- see that
file's module docstring for the shared rationale.

`find_open_pr` is built and unit-tested here standalone, never wired into
any `ship_*` function (spec Never boundary: `ship_conda_forge` does not
exist in this branch's lineage yet) -- this file's own coverage is the
entire proof of correctness for this adapter until that future wiring
lands."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

from pyforge.mason.engines import gh


def _fake_completed(
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=[],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


# --- probe() -------------------------------------------------------------------


def test_probe_delegates_to_probe_engine_with_the_gh_binary_name():
    with patch("pyforge.mason.engines.gh.probe_engine") as mock_probe:
        mock_probe.return_value.version = "gh version 2.97.0"
        version = gh.probe()

    mock_probe.assert_called_once_with("gh", "gh")
    assert version == "gh version 2.97.0"


# --- find_open_pr(): engine presence -------------------------------------------


def test_find_open_pr_returns_undeterminable_when_gh_is_absent_and_never_spawns():
    with (
        patch("pyforge.mason.engines.gh.probe_engine") as mock_probe,
        patch("pyforge.mason.engines.gh.subprocess.run") as mock_run,
    ):
        mock_probe.return_value.available = False
        result = gh.find_open_pr("conda-forge/staged-recipes", "add-recipe-pkg")

    assert result == gh.OpenPrSearchResult(found=None, url=None)
    mock_run.assert_not_called()


# --- find_open_pr(): invocation shape -------------------------------------------


def test_find_open_pr_invokes_gh_pr_list_with_the_documented_argv():
    with (
        patch("pyforge.mason.engines.gh.probe_engine") as mock_probe,
        patch(
            "pyforge.mason.engines.gh.subprocess.run",
            return_value=_fake_completed(stdout="[]"),
        ) as mock_run,
    ):
        mock_probe.return_value.available = True
        gh.find_open_pr("conda-forge/staged-recipes", "add-recipe-pkg")

    args, kwargs = mock_run.call_args
    argv = args[0]
    assert argv == [
        "gh",
        "pr",
        "list",
        "--repo",
        "conda-forge/staged-recipes",
        "--head",
        "add-recipe-pkg",
        "--state",
        "open",
        "--json",
        "number,url",
    ]
    assert "env" not in kwargs
    assert kwargs["stdout"] == subprocess.PIPE
    assert kwargs["stderr"] == subprocess.PIPE
    assert kwargs["text"] is True
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["errors"] == "replace"
    assert kwargs["check"] is False
    assert "timeout" in kwargs


def test_find_open_pr_head_branch_is_passed_bare_with_no_owner_prefix():
    """Design Notes: `gh pr list --help`'s own `"<owner>:<branch>" syntax
    not supported` note -- this adapter never resolves or holds a fork
    owner."""
    with (
        patch("pyforge.mason.engines.gh.probe_engine") as mock_probe,
        patch(
            "pyforge.mason.engines.gh.subprocess.run",
            return_value=_fake_completed(stdout="[]"),
        ) as mock_run,
    ):
        mock_probe.return_value.available = True
        gh.find_open_pr("conda-forge/staged-recipes", "add-recipe-langflow")

    argv = mock_run.call_args.args[0]
    head_index = argv.index("--head")
    assert argv[head_index + 1] == "add-recipe-langflow"


def test_find_open_pr_uses_the_default_timeout_when_none_given():
    with (
        patch("pyforge.mason.engines.gh.probe_engine") as mock_probe,
        patch(
            "pyforge.mason.engines.gh.subprocess.run",
            return_value=_fake_completed(stdout="[]"),
        ) as mock_run,
    ):
        mock_probe.return_value.available = True
        gh.find_open_pr("owner/repo", "branch")

    assert mock_run.call_args.kwargs["timeout"] == gh._GH_PR_LIST_TIMEOUT_SECONDS


def test_find_open_pr_forwards_an_explicit_timeout():
    with (
        patch("pyforge.mason.engines.gh.probe_engine") as mock_probe,
        patch(
            "pyforge.mason.engines.gh.subprocess.run",
            return_value=_fake_completed(stdout="[]"),
        ) as mock_run,
    ):
        mock_probe.return_value.available = True
        gh.find_open_pr("owner/repo", "branch", timeout=5.0)

    assert mock_run.call_args.kwargs["timeout"] == 5.0


# --- find_open_pr(): I/O & Edge-Case Matrix -------------------------------------


def test_find_open_pr_returns_found_true_with_the_first_matching_url():
    stdout = '[{"number": 123, "url": "https://github.com/conda-forge/staged-recipes/pull/123"}]'
    with (
        patch("pyforge.mason.engines.gh.probe_engine") as mock_probe,
        patch(
            "pyforge.mason.engines.gh.subprocess.run",
            return_value=_fake_completed(stdout=stdout),
        ),
    ):
        mock_probe.return_value.available = True
        result = gh.find_open_pr("conda-forge/staged-recipes", "add-recipe-pkg")

    assert result == gh.OpenPrSearchResult(
        found=True,
        url="https://github.com/conda-forge/staged-recipes/pull/123",
    )


def test_find_open_pr_returns_found_true_with_no_url_when_the_entry_lacks_one():
    """Adversarial review pass (this story): a matching entry missing the
    requested `url` field must degrade gracefully (`.get("url")` -> `None`),
    never raise -- `found` still reflects a real match even when `url`
    itself is unavailable."""
    with (
        patch("pyforge.mason.engines.gh.probe_engine") as mock_probe,
        patch(
            "pyforge.mason.engines.gh.subprocess.run",
            return_value=_fake_completed(stdout='[{"number": 123}]'),
        ),
    ):
        mock_probe.return_value.available = True
        result = gh.find_open_pr("conda-forge/staged-recipes", "add-recipe-pkg")

    assert result == gh.OpenPrSearchResult(found=True, url=None)


def test_find_open_pr_returns_found_false_for_an_empty_json_array():
    with (
        patch("pyforge.mason.engines.gh.probe_engine") as mock_probe,
        patch(
            "pyforge.mason.engines.gh.subprocess.run",
            return_value=_fake_completed(stdout="[]"),
        ),
    ):
        mock_probe.return_value.available = True
        result = gh.find_open_pr("conda-forge/staged-recipes", "add-recipe-pkg")

    assert result == gh.OpenPrSearchResult(found=False, url=None)


def test_find_open_pr_returns_undeterminable_on_a_nonzero_exit():
    with (
        patch("pyforge.mason.engines.gh.probe_engine") as mock_probe,
        patch(
            "pyforge.mason.engines.gh.subprocess.run",
            return_value=_fake_completed(returncode=1, stderr="error: not found\n"),
        ),
    ):
        mock_probe.return_value.available = True
        result = gh.find_open_pr("conda-forge/staged-recipes", "add-recipe-pkg")

    assert result == gh.OpenPrSearchResult(found=None, url=None)


def test_find_open_pr_returns_undeterminable_on_unparseable_json():
    with (
        patch("pyforge.mason.engines.gh.probe_engine") as mock_probe,
        patch(
            "pyforge.mason.engines.gh.subprocess.run",
            return_value=_fake_completed(stdout="not json"),
        ),
    ):
        mock_probe.return_value.available = True
        result = gh.find_open_pr("conda-forge/staged-recipes", "add-recipe-pkg")

    assert result == gh.OpenPrSearchResult(found=None, url=None)


def test_find_open_pr_returns_undeterminable_when_json_body_is_not_a_list():
    with (
        patch("pyforge.mason.engines.gh.probe_engine") as mock_probe,
        patch(
            "pyforge.mason.engines.gh.subprocess.run",
            return_value=_fake_completed(stdout='{"unexpected": true}'),
        ),
    ):
        mock_probe.return_value.available = True
        result = gh.find_open_pr("conda-forge/staged-recipes", "add-recipe-pkg")

    assert result == gh.OpenPrSearchResult(found=None, url=None)


def test_find_open_pr_returns_undeterminable_on_timeout():
    with (
        patch("pyforge.mason.engines.gh.probe_engine") as mock_probe,
        patch(
            "pyforge.mason.engines.gh.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["gh", "pr", "list"], timeout=30.0),
        ),
    ):
        mock_probe.return_value.available = True
        result = gh.find_open_pr("conda-forge/staged-recipes", "add-recipe-pkg")

    assert result == gh.OpenPrSearchResult(found=None, url=None)


def test_find_open_pr_returns_undeterminable_on_a_bare_oserror():
    """`gh` vanishing between `probe_engine`'s own check and this call's
    separate spawn -- mirrors `engines.pixi.upload`'s identical race."""
    with (
        patch("pyforge.mason.engines.gh.probe_engine") as mock_probe,
        patch(
            "pyforge.mason.engines.gh.subprocess.run",
            side_effect=FileNotFoundError("No such file or directory"),
        ),
    ):
        mock_probe.return_value.available = True
        result = gh.find_open_pr("conda-forge/staged-recipes", "add-recipe-pkg")

    assert result == gh.OpenPrSearchResult(found=None, url=None)


def test_find_open_pr_never_raises_for_any_undeterminable_cause():
    """Spec I/O matrix: 'conda-forge, gh absent' and every other
    undeterminable cause are data, never raised."""
    with (
        patch("pyforge.mason.engines.gh.probe_engine") as mock_probe,
        patch(
            "pyforge.mason.engines.gh.subprocess.run",
            side_effect=OSError("boom"),
        ),
    ):
        mock_probe.return_value.available = True
        result = gh.find_open_pr("conda-forge/staged-recipes", "add-recipe-pkg")

    assert result.found is None
    assert result.url is None
