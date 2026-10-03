"""Regression guard for ``stub_smithy_maintainer_lookups`` (tests/conftest.py).

conda-smithy's linter asks github.com whether each recipe maintainer exists.
On 2026-10-02 ``cfe-regression-net`` (no ``GH_TOKEN``) failed twice, in a
different ``test_workflow_npm.py`` case each time, with
``Recipe maintainer "rxm7706" does not exist``. The same HEAD from a
workstation returned 200.

Mutation: disable the body of ``stub_smithy_maintainer_lookups`` in
``tests/conftest.py``. This module then fails — the in-process lookups hit
the GitHub trap, and ``validate_recipe``'s conda-smithy child does the same.

Mutation: empty ``sitecustomize_source()``. The validate_recipe child test
fails — the trap execs that empty file and does not re-apply the stub.
"""
from __future__ import annotations

import os

import pytest
import requests

from _smithy_maintainer_stub import (
    CFE_STUB_SMITHY_LOOKUPS_ENV,
    stub_maintainer_exists,
    stub_team_exists,
)

_TRAP_THEN_STUB_SITECUSTOMIZE = '''\
"""Trap github.com requests after chaining to the fixture sitecustomize."""
from __future__ import annotations

import os
from pathlib import Path

import requests

# First on PYTHONPATH, so import shadows the fixture sitecustomize. Exec that
# file (do not re-implement the stub), then wrap requests.
_here = Path(__file__).resolve().parent
for entry in os.environ.get("PYTHONPATH", "").split(os.pathsep):
    if not entry:
        continue
    candidate = Path(entry) / "sitecustomize.py"
    if not candidate.is_file() or candidate.resolve().parent == _here:
        continue
    exec(
        compile(candidate.read_text(encoding="utf-8"), str(candidate), "exec"),
        globals(),
    )
    break

_GITHUB_MARKERS = ("github.com", "api.github.com")
_orig_head = requests.head
_orig_get = requests.get


def _trap(orig, url, *args, **kwargs):
    target = str(url)
    if any(marker in target for marker in _GITHUB_MARKERS):
        raise AssertionError(f"CFE test asked GitHub: {url}")
    return orig(url, *args, **kwargs)


requests.head = lambda url, *a, **k: _trap(_orig_head, url, *a, **k)
requests.get = lambda url, *a, **k: _trap(_orig_get, url, *a, **k)
'''


@pytest.fixture
def github_request_trap(monkeypatch, tmp_path):
    """Fail if a github.com request leaves this process or a script_runner child.

    The child trap is a sitecustomize prepended on ``PYTHONPATH``. It execs
    the fixture's production sitecustomize already on PYTHONPATH, then wraps
    ``requests``. It does not re-implement the stub: emptying
    ``sitecustomize_source()`` leaves the child un-stubbed, so
    ``validate_recipe`` fails. Mutation (fixture body disabled) leaves the
    stub site off PYTHONPATH: the child keeps the trap and the real lookups,
    so ``validate_recipe`` fails.
    """
    hits: list[str] = []
    orig_head = requests.head
    orig_get = requests.get

    def _trap(orig, url, *args, **kwargs):
        target = str(url)
        if "github.com" in target:
            hits.append(target)
            raise AssertionError(f"CFE test asked GitHub: {url}")
        return orig(url, *args, **kwargs)

    monkeypatch.setattr(
        requests, "head", lambda url, *a, **k: _trap(orig_head, url, *a, **k)
    )
    monkeypatch.setattr(
        requests, "get", lambda url, *a, **k: _trap(orig_get, url, *a, **k)
    )

    trap_site = tmp_path / "github_trap_site"
    trap_site.mkdir()
    (trap_site / "sitecustomize.py").write_text(
        _TRAP_THEN_STUB_SITECUSTOMIZE, encoding="utf-8"
    )
    existing = os.environ.get("PYTHONPATH", "")
    monkeypatch.setenv(
        "PYTHONPATH",
        f"{trap_site}{os.pathsep}{existing}" if existing else str(trap_site),
    )
    return hits


def test_lookups_make_no_request(github_request_trap):
    import conda_smithy.lint_recipe as lint_recipe

    assert lint_recipe._maintainer_exists("rxm7706") is True
    assert lint_recipe._team_exists("conda-forge/core") is True
    assert github_request_trap == []
    assert lint_recipe._maintainer_exists is stub_maintainer_exists
    assert lint_recipe._team_exists is stub_team_exists


def test_validate_recipe_lint_of_a_named_maintainer_makes_no_request(
    github_request_trap, script_runner, recipes_dir,
):
    assert os.environ.get(CFE_STUB_SMITHY_LOOKUPS_ENV) == "1"
    rc, out, err = script_runner(
        "validate_recipe.py", str(recipes_dir / "v1-noarch"), timeout=120,
    )
    combined = out + err
    assert "conda-smithy lint: not available" not in combined, (
        f"conda-smithy did not run; child stub was not exercised:\n{combined}"
    )
    assert "conda-smithy lint:" in combined, combined
    assert "does not exist" not in combined, combined
    assert "Recipe validation passed" in combined, (
        f"validate failed:\nout={out}\nerr={err}"
    )
    assert rc == 0
    assert github_request_trap == []


@pytest.mark.network
def test_network_marked_helper_sees_real_smithy_lookups():
    """Fixture must not replace the functions on a ``network``-marked test."""
    import conda_smithy.lint_recipe as lint_recipe

    assert lint_recipe._maintainer_exists is not stub_maintainer_exists
    assert lint_recipe._team_exists is not stub_team_exists
    assert lint_recipe._maintainer_exists.__module__ == "conda_smithy.lint_recipe"
    assert lint_recipe._team_exists.__module__ == "conda_smithy.lint_recipe"
    assert CFE_STUB_SMITHY_LOOKUPS_ENV not in os.environ
