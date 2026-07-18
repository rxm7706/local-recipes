"""Story B7 — the 14-day freshness contract / stale-refusal (AC-3, AD-15).
Consumers refuse a stale atlas exactly as the legacy universe_sbom.check_freshness."""

from __future__ import annotations

import time

import pandas as pd
import pytest

from pyforge.atlas.pipelines.universal_sbom.nodes import (
    StaleUniverseError,
    check_universe_freshness,
    match_against_universe,
)

DAY = 86400


def _universe_built_at(epoch):
    return {"metadata": {"properties": [{"name": "cfe:atlas_built_at", "value": str(int(epoch))}]}, "components": []}


def test_fresh_universe_passes():
    now = time.time()
    assert check_universe_freshness(_universe_built_at(now - 3 * DAY), 14, now=now) is not None


def test_stale_universe_is_refused():
    """A universe older than 14 days RAISES (refuse-stale) — the headline of AC-3."""
    now = time.time()
    with pytest.raises(StaleUniverseError, match="days old"):
        check_universe_freshness(_universe_built_at(now - 30 * DAY), 14, now=now)


def test_missing_built_at_is_fail_closed():
    """No parseable built_at -> REFUSED like a stale one (decision 6, fail-closed)."""
    with pytest.raises(StaleUniverseError, match="no parseable"):
        check_universe_freshness({"metadata": {}, "components": []}, 14)


def test_allow_stale_overrides_both():
    now = time.time()
    assert check_universe_freshness(_universe_built_at(now - 30 * DAY), 14, now=now, allow_stale=True) is not None
    assert check_universe_freshness({"metadata": {}, "components": []}, 14, allow_stale=True) is None


def test_matcher_refuses_a_stale_universe_via_params():
    """The matcher (a consumer) enforces params:freshness.stale_after_days."""
    now = time.time()
    stale = _universe_built_at(now - 30 * DAY)
    core = pd.DataFrame([{"conda_name": "numpy", "latest_version": "1.26.0"}])
    mapping = pd.DataFrame([{"pypi_name": "numpy", "conda_name": "numpy"}])
    universe = pd.DataFrame([{"pypi_name": "numpy", "last_serial": 1}])
    bom = {"bomFormat": "CycloneDX", "components": []}
    params = {"freshness": {"stale_after_days": 14}, "sbom": {"now": now}}
    with pytest.raises(StaleUniverseError):
        match_against_universe(bom, core, mapping, stale, universe, params)
    # allow_stale lets it through (but the report records the true staleness)
    params["sbom"]["allow_stale"] = True
    report = match_against_universe(bom, core, mapping, stale, universe, params)
    assert report["kind"] == "sbom-match-report"
    assert report["stale"] is True
