"""AD-14 parity-scope boundary tests (Story B4, AC-4).

B4 compares LEGACY-SURFACE outputs only; the B8/B9/B10 new-signal datasets
(basilisk / release-velocity / migration-readiness) are NEVER parity-gated
(ARCHITECTURE-SPINE AD-14; spec §9 preamble). These tests pin that the compared
set is exactly the Q1 ``v_actionable_packages`` family and provably excludes the
new-signal datasets — so a future edit that drags a new-signal view into the
parity set fails here.
"""

from __future__ import annotations

from pyforge.atlas.parity import (
    EXCLUDED_NEW_SIGNAL_DATASETS,
    LEGACY_SURFACE_VIEWS,
    legacy_surface_view_names,
)
from pyforge.atlas.parity.legacy_surface import (
    NEW_SIGNAL_DATASETS,
    parity_scoped_kedro_datasets,
)

# The Q1 legacy-surface family (spec §3.3 view discipline).
_EXPECTED_VIEWS = {
    "v_actionable_packages",
    "v_pypi_candidates",
    "v_pypi_intelligence_valid",
    "v_packages_enriched",
    "v_current_version_vulns",
}


def test_parity_set_is_the_q1_actionable_family():
    assert set(legacy_surface_view_names()) == _EXPECTED_VIEWS


def test_excluded_set_is_non_empty():
    """Guards against a vacuous 'excludes nothing' pass — AD-14 must exclude the
    three concrete new-signal datasets."""
    assert EXCLUDED_NEW_SIGNAL_DATASETS
    assert len(EXCLUDED_NEW_SIGNAL_DATASETS) == 3


def test_parity_views_never_intersect_new_signal_datasets():
    """AC-4: no legacy-surface view is a B8/B9/B10 new-signal dataset."""
    assert set(legacy_surface_view_names()) & EXCLUDED_NEW_SIGNAL_DATASETS == set()


def test_parity_scoped_kedro_datasets_exclude_new_signals():
    """The Kedro Parquet datasets B4 actually diffs must not reach into any
    basilisk/velocity/migration-readiness output."""
    assert parity_scoped_kedro_datasets() & EXCLUDED_NEW_SIGNAL_DATASETS == set()


def test_new_signal_datasets_are_documented_with_fr_and_story():
    """Each excluded dataset is traceable to its FR + additive story (AD-14)."""
    frs = {d.fr for d in NEW_SIGNAL_DATASETS}
    stories = {d.story for d in NEW_SIGNAL_DATASETS}
    assert frs == {"FR-19", "FR-20", "FR-21"}
    assert stories == {"B8", "B9", "B10"}


def test_every_view_has_backing_datasets_and_scope_note():
    for v in LEGACY_SURFACE_VIEWS:
        assert v.kedro_datasets, f"{v.view} has no backing Kedro datasets"
        assert v.scope_note, f"{v.view} has no scope note"
