"""AC-1 / AC-5 / AD-23 — the pipeline-trigger surface (Story B3).

Fully offline (AD-11): ``bootstrapped_session`` is patched with a fake
session so the trigger dispatch — ``session.run(pipeline_name=<name>)``,
the ONE execution plane — is proven without bootstrapping the real
project or touching the network.
"""

from __future__ import annotations

import contextlib

import pytest

from pyforge.atlas.mcp import session as _session_mod
from pyforge.atlas.mcp import tools


class FakeSession:
    """Records ``run(pipeline_name=...)`` calls; returns a canned result."""

    def __init__(self, result=None):
        self.run_calls: list[dict] = []
        self._result = result if result is not None else {}

    def run(self, **kwargs):
        self.run_calls.append(kwargs)
        return self._result


def _patch_session(monkeypatch, fake):
    @contextlib.contextmanager
    def fake_bootstrapped_session(project_path=None, extra_params=None, env=None):
        yield fake

    monkeypatch.setattr(_session_mod, "bootstrapped_session", fake_bootstrapped_session)


def test_run_pipeline_dispatches_through_kedro_session_run(monkeypatch):
    fake = FakeSession(result={"vulnerability_package_rollup": object()})
    _patch_session(monkeypatch, fake)

    receipt = tools.run_pipeline("vulnerability")

    # the trigger rode session.run(pipeline_name=...) — AD-23, one plane
    assert fake.run_calls == [{"pipeline_name": "vulnerability"}]
    # thin advisory + timestamped receipt (AD-17): names only, no raw data
    assert receipt["pipeline"] == "vulnerability"
    assert isinstance(receipt["triggered_at"], str)
    assert "T" in receipt["triggered_at"]  # ISO-8601 shape
    assert receipt["outputs"] == ["vulnerability_package_rollup"]


def test_run_pipeline_rejects_unknown_name(monkeypatch):
    fake = FakeSession()
    _patch_session(monkeypatch, fake)

    with pytest.raises(tools.AtlasMCPError, match="unknown pipeline 'nope'"):
        tools.run_pipeline("nope")
    assert fake.run_calls == []  # rejected BEFORE any session work


def test_all_registered_pipelines_are_accepted(monkeypatch):
    assert tools.PIPELINE_NAMES == (
        "core",
        "vcs_health",
        "pypi_intelligence",
        "vulnerability",
        "seed_gaps",  # B6: the READ-ONLY seed-freshness report pipeline
        "universal_sbom",  # B7: § 4.10 intake -> CycloneDX -> six-bucket match
        "derived_artifacts",  # B7: full-universe CycloneDX BOM
    )
    fake = FakeSession()
    _patch_session(monkeypatch, fake)

    for name in tools.PIPELINE_NAMES:
        receipt = tools.run_pipeline(name)
        assert receipt["pipeline"] == name
        assert receipt["outputs"] == []  # non-dict/empty run result -> []

    assert fake.run_calls == [
        {"pipeline_name": name} for name in tools.PIPELINE_NAMES
    ]
