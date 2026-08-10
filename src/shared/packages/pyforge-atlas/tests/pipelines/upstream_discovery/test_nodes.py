"""``upstream_discovery`` node unit tests (Story 13.1, CAP-1 / FR-64).

Pure trigger-node test mirroring ``tests/pipelines/vulnerability/test_nodes.py``'s style
(there is no equivalent trigger-node test file there — the closest precedent is
``refresh_vdb_store``'s cadence coercion, exercised indirectly via
``tests/pipelines/test_refresh_schedule_fixtures.py``; here it is tested directly against
a ``ttls`` dict, present / missing / non-numeric)."""

from __future__ import annotations

from pyforge.atlas.datasets.refresh import RefreshRequest
from pyforge.atlas.pipelines.upstream_discovery.nodes import (
    DAILY_SECONDS,
    refresh_trending_candidates,
)


def test_refresh_trending_candidates_reads_the_ttls_cadence():
    req = refresh_trending_candidates({"trending_candidates": 86400})
    assert isinstance(req, RefreshRequest)
    assert req.store == "trending_candidates"
    assert req.cadence_seconds == 86400
    assert req.force is False


def test_refresh_trending_candidates_missing_key_falls_back_to_daily_default():
    assert refresh_trending_candidates({}).cadence_seconds == DAILY_SECONDS
    assert refresh_trending_candidates(None).cadence_seconds == DAILY_SECONDS


def test_refresh_trending_candidates_non_numeric_value_falls_back_to_daily_default():
    assert refresh_trending_candidates({"trending_candidates": "nope"}).cadence_seconds == DAILY_SECONDS
    assert refresh_trending_candidates({"trending_candidates": None}).cadence_seconds == DAILY_SECONDS
