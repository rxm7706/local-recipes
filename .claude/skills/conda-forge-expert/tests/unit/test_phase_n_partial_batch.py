"""Tests for Phase N's partial-batch handling.

Background (2026-05-23): GitHub GraphQL returns valid partial data + an
``errors[]`` array when one repo in a batch doesn't exist (e.g.
renamed/deleted feedstock). The `gh` CLI exits non-zero in that case
even though the response body is usable. Without explicit handling, a
single missing feedstock poisons the whole 25-feedstock batch.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"


def _load(name: str):
    path = _SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def atlas_mod():
    return _load("conda_forge_atlas")


def _completed(stdout: str, stderr: str = "", returncode: int = 0):
    """Build a CompletedProcess stub matching what subprocess.run returns."""
    return subprocess.CompletedProcess(
        args=["gh", "api", "graphql"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def test_partial_batch_with_one_missing_repo_keeps_other_data(atlas_mod):
    """When the gh CLI exits non-zero but stdout has valid partial data
    + errors[] (one repo not found), the function must return the
    partial `data` dict so per-alias parsing recovers 24 of 25 rather
    than discarding the whole batch."""
    payload_body = json.dumps({
        "data": {
            "r0": {"name": "numpy-feedstock", "pushedAt": "2026-05-19T05:38:54Z"},
            "r1": None,  # the missing repo
            "r2": {"name": "pandas-feedstock", "pushedAt": "2026-05-12T16:15:38Z"},
        },
        "errors": [{
            "type": "NOT_FOUND",
            "path": ["r1"],
            "message": "Could not resolve to a Repository with the name 'conda-forge/staged-recipes-feedstock'.",
        }],
    })
    # gh CLI behavior in this case: returncode=1, stderr has the human message.
    stub = _completed(
        stdout=payload_body,
        stderr="gh: Could not resolve to a Repository with the name 'conda-forge/staged-recipes-feedstock'.",
        returncode=1,
    )
    with patch("subprocess.run", return_value=stub):
        data, err = atlas_mod._phase_n_query_batch(
            ["numpy", "staged-recipes", "pandas"]
        )
    # The function must return usable data, not (None, err)
    assert err is None, f"expected partial-recovery, got err={err}"
    assert data is not None
    # Two good repos survived; missing one is None (downstream marks 404)
    assert data["r0"]["name"] == "numpy-feedstock"
    assert data["r1"] is None
    assert data["r2"]["name"] == "pandas-feedstock"


def test_clean_success_path_still_works(atlas_mod):
    """returncode=0 + no errors should still return the data normally."""
    payload_body = json.dumps({
        "data": {
            "r0": {"name": "numpy-feedstock", "pushedAt": "2026-05-19T05:38:54Z"},
        },
    })
    stub = _completed(stdout=payload_body, returncode=0)
    with patch("subprocess.run", return_value=stub):
        data, err = atlas_mod._phase_n_query_batch(["numpy"])
    assert err is None
    assert data["r0"]["name"] == "numpy-feedstock"


def test_total_failure_no_usable_payload_returns_error(atlas_mod):
    """When the gh CLI fails AND stdout is empty/unparseable, the
    function must still return (None, err) to signal whole-batch
    failure — the rate-limit / network-error path."""
    stub = _completed(
        stdout="",
        stderr="HTTP 401: bad credentials",
        returncode=1,
    )
    with patch("subprocess.run", return_value=stub):
        with patch.object(atlas_mod.time, "sleep"):  # don't actually sleep
            data, err = atlas_mod._phase_n_query_batch(["numpy"])
    assert data is None
    assert err is not None
    assert "401" in err or "bad credentials" in err


def test_unparseable_stdout_on_returncode_zero_still_errors(atlas_mod):
    """The edge case: returncode=0 but stdout isn't JSON (shouldn't
    happen with real gh, but defensive). Must surface as error."""
    stub = _completed(stdout="not json at all", returncode=0)
    with patch("subprocess.run", return_value=stub):
        data, err = atlas_mod._phase_n_query_batch(["numpy"])
    assert data is None
    assert err is not None
    assert "JSON" in err or "parseable" in err


def test_payload_without_data_field_treated_as_error(atlas_mod):
    """If the response is valid JSON but lacks `data`, that's an error.
    Possible if GraphQL endpoint returns only an `errors[]` array."""
    body = json.dumps({"errors": [{"message": "Bad Request"}]})
    stub = _completed(stdout=body, returncode=1, stderr="gh: bad request")
    with patch("subprocess.run", return_value=stub):
        with patch.object(atlas_mod.time, "sleep"):
            data, err = atlas_mod._phase_n_query_batch(["numpy"])
    assert data is None
    assert err is not None


def test_rate_limit_stderr_still_retries(atlas_mod):
    """A secondary-rate-limit stderr message must still trigger the
    retry path — this test guards against the new stdout-parse code
    accidentally short-circuiting before the rate-limit retry."""
    rl_stub = _completed(
        stdout="",
        stderr="API rate limit exceeded for installation",
        returncode=1,
    )
    ok_stub = _completed(
        stdout=json.dumps({"data": {"r0": {"name": "numpy-feedstock"}}}),
        returncode=0,
    )
    call_count = {"n": 0}

    def _side_effect(*a, **kw):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return rl_stub
        return ok_stub

    with patch("subprocess.run", side_effect=_side_effect):
        with patch.object(atlas_mod.time, "sleep"):  # skip the real backoff
            data, err = atlas_mod._phase_n_query_batch(["numpy"])
    assert err is None
    assert data is not None
    assert data["r0"]["name"] == "numpy-feedstock"
    assert call_count["n"] == 2  # one rate-limit + one success
