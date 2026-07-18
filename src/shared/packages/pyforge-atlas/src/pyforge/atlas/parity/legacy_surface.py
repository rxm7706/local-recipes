"""The legacy-surface view registry + the AD-14 parity-scope boundary (B4).

Q1's adopted default (spec §11 / ARCHITECTURE-SPINE AD-19): parity is proven by
**exact row-count + value parity on the ``v_actionable_packages``-family views**,
with timestamp/ordering-only diffs documented benign. This module freezes that
family (spec §3.3 view discipline; cf-atlas-legacy ``engineering-contracts.md``
§ View discipline) and encodes the **AD-14 boundary**: B4 compares LEGACY-SURFACE
outputs only — the B8/B9/B10 new-signal datasets (basilisk / release-velocity /
migration-readiness) are NEVER parity-gated.

Pure data + helpers only — no IO. The credentialed comparator (in ``tests/parity/``)
consumes this registry: in CREDENTIALED mode it reads ``SELECT * FROM <view>`` from
the real legacy ``cf_atlas.db`` (which already defines these views) and composes the
comparable frame from the named Kedro Parquet datasets. The per-view composition
detail is finalized at the attended event against the real schema (DW-B4); in-loop
the registry is exercised with synthetic data (fixture mode).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LegacySurfaceView:
    """One legacy-surface view in the Q1 parity set.

    - ``view``: the legacy ``cf_atlas.db`` view name — the credentialed comparator
      reads ``SELECT * FROM <view>`` directly (the legacy DB already defines it).
    - ``kedro_datasets``: the migrated Parquet output(s) that BACK the view; the
      comparator composes the Kedro-side comparable frame from these.
    - ``scope_note``: the ``# scope:`` justification (spec §3.3 meta-test).
    """

    view: str
    kedro_datasets: tuple[str, ...]
    scope_note: str


# The v_actionable_packages family — the ONLY views parity-gated at B4 (Q1).
LEGACY_SURFACE_VIEWS: tuple[LegacySurfaceView, ...] = (
    LegacySurfaceView(
        view="v_actionable_packages",
        kedro_datasets=(
            "core_packages_enumerated",
            "core_latest_status",
            "core_feedstock_attribution",
            "vcs_archived_feedstocks",
        ),
        scope_note=(
            "canonical persona-filter triplet conda_name IS NOT NULL AND "
            "latest_status='active' AND COALESCE(feedstock_archived,0)=0"
        ),
    ),
    LegacySurfaceView(
        view="v_pypi_candidates",
        kedro_datasets=("pypi_intelligence_scored", "pypi_universe"),
        scope_note="pypi-only candidates surfaced from the enrichment/scoring outputs",
    ),
    LegacySurfaceView(
        view="v_pypi_intelligence_valid",
        kedro_datasets=("pypi_intelligence_scored",),
        scope_note="consumers must read the view, never the raw table (spec §3.3)",
    ),
    LegacySurfaceView(
        view="v_packages_enriched",
        kedro_datasets=("core_packages_enumerated", "core_feedstock_health"),
        scope_note="the enriched package surface over the core enumeration",
    ),
    LegacySurfaceView(
        view="v_current_version_vulns",
        kedro_datasets=("vulnerability_package_version_vulns",),
        scope_note=(
            "the ONLY query-time-correct vuln source; the packages.vuln_* rollup "
            "is report-only (spec §3.3)"
        ),
    ),
)


# --- AD-14: the parity-scope boundary -------------------------------------
# B8/B9/B10 are additive NEW-SIGNAL stories, NEVER parity-gated (spec §9 preamble;
# ARCHITECTURE-SPINE AD-14). Their output datasets are OUT of B4's parity set. The
# names below are the planned new-signal outputs; the invariant that MATTERS is
# that NONE of them is ever a legacy-surface view (test_legacy_surface_scope).
@dataclass(frozen=True)
class NewSignalDataset:
    name: str
    fr: str
    story: str
    pipeline: str


NEW_SIGNAL_DATASETS: tuple[NewSignalDataset, ...] = (
    NewSignalDataset("vulnerability_basilisk_advisories", "FR-19", "B8", "vulnerability"),
    NewSignalDataset("vcs_release_velocity", "FR-20", "B9", "vcs_health"),
    NewSignalDataset("vcs_migration_readiness", "FR-21", "B10", "vcs_health"),
)

# The frozen exclusion set the scope test asserts the parity set never intersects.
EXCLUDED_NEW_SIGNAL_DATASETS: frozenset[str] = frozenset(
    d.name for d in NEW_SIGNAL_DATASETS
)


def legacy_surface_view_names() -> tuple[str, ...]:
    """The names of the Q1 legacy-surface views compared at B4."""
    return tuple(v.view for v in LEGACY_SURFACE_VIEWS)


def parity_scoped_kedro_datasets() -> frozenset[str]:
    """Every Kedro Parquet dataset that backs a legacy-surface view — the full
    set of outputs in B4's parity scope. Used to assert the parity scope never
    reaches into a B8/B9/B10 new-signal dataset (AD-14)."""
    return frozenset(ds for v in LEGACY_SURFACE_VIEWS for ds in v.kedro_datasets)


def view_by_name(name: str) -> LegacySurfaceView:
    for v in LEGACY_SURFACE_VIEWS:
        if v.view == name:
            return v
    raise KeyError(f"{name!r} is not a legacy-surface parity view")
