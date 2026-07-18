"""Provenance-honesty guard (Story D1, DW-B1-1 discipline).

The DW-B1-1 trap is a parity fixture that "proves" parity by encoding an implementer
belief as legacy truth. This gate makes the honesty structural: every declared core
metric MUST carry a classified provenance record, every ``migrated-node-derived``
metric MUST be flagged for recapture, and every deferred legacy filter MUST be
documented (never silently dropped).
"""

from __future__ import annotations

from pyforge.atlas.semantic import metrics

_VALID_PROVENANCE = {"legacy-formula", "migrated-node-derived-flag-recapture"}
_VALID_WIRING = {"migrated-column", "deferred-input-not-in-migrated-store"}

# The CORE metric set the AC-1 names (+ the first-class maintainer dimension, AC-2).
_CORE_METRICS = {
    "staleness_age_days",
    "adoption_stage",
    "is_actionable",
    "downloads_total",
    "downloads_30d",
    "ci_red",
    "has_open_prs",
    "has_open_issues",
    "maintainer",
}


def test_every_core_metric_has_a_provenance_record():
    assert _CORE_METRICS <= set(metrics.METRIC_PROVENANCE), (
        "core metrics missing a provenance record: "
        f"{_CORE_METRICS - set(metrics.METRIC_PROVENANCE)}"
    )


def test_provenance_records_are_well_formed():
    for name, rec in metrics.METRIC_PROVENANCE.items():
        assert rec["provenance"] in _VALID_PROVENANCE, name
        assert rec["data_wiring"] in _VALID_WIRING, name
        assert rec["legacy_source"].strip(), name
        assert rec["note"].strip(), name


def test_migrated_derived_metrics_are_flagged_for_recapture():
    # A shape-port metric must NOT masquerade as a legacy-formula anchor. All three
    # core_feedstock_health filters read migrated columns whose rename/collapse from the
    # legacy Phase M/N signal is unverified — they must be explicitly flagged (mirrors
    # the B2 shape-only-seed flag).
    flagged = {
        n
        for n, r in metrics.METRIC_PROVENANCE.items()
        if r["provenance"] == "migrated-node-derived-flag-recapture"
    }
    assert {"ci_red", "has_open_prs", "has_open_issues"} <= flagged


def test_deferred_feedstock_health_filters_are_documented_not_dropped():
    # 'stuck' / 'bad' need Phase M columns absent from the migrated shape — D1 must NOT
    # fabricate them; it documents the gap so D2 knows to recapture.
    assert set(metrics.DEFERRED_FEEDSTOCK_HEALTH_FILTERS) == {"stuck", "bad"}
    for reason in metrics.DEFERRED_FEEDSTOCK_HEALTH_FILTERS.values():
        assert reason.strip()
