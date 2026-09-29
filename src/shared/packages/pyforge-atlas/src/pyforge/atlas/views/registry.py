"""The curated static-view catalog — Story 14.1 (CAP-1).

Six of the 11 conda-forge-expert skill CLIs run their ``query()`` with zero required
arguments: ``staleness-report``, ``feedstock-health``, ``behind-upstream``, ``cve-watcher``,
``release-cadence``, ``adoption-stage``. The other 5 (``whodepends``, ``version-downloads``,
``find-alternative``, ``detail-cf-atlas``, ``scan-project``) all require a package-name/path
argument, so they don't fit a parameterless static view — deferred to the interactive layer
(Story 14.3).

Each :class:`View`'s ``query_kwargs`` mirrors that CLI's own ``argparse`` defaults exactly
(read from the script source, never guessed), and ``columns`` mirrors the exact dict-key
order ``query()`` returns for those defaults (its ``SELECT`` column list plus any computed
keys it adds) — with one documented exception: ``behind-upstream``'s internal ``_priority``
sort key is dropped. ``behind_upstream.query()`` itself never strips it (it's set on every
row for the in-Python sort and returned as-is); the drop happens here, at render time, via
this ``View.columns`` whitelist simply not listing ``_priority`` (``render.py::render_rows``
only ever projects the declared columns). The CLI's own ``main()`` also ``pop``s
``_priority`` before printing/JSON-ing a row, but that's a separate, coincidental parallel
in a different code path — not the mechanism this catalog relies on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any


@dataclass(frozen=True)
class View:
    """One entry in the static-view catalog.

    ``script`` is the CLI script's module stem (no ``.py``), resolved against
    :func:`pyforge.atlas.views.cli_bridge.default_scripts_dir` by
    :func:`pyforge.atlas.views.cli_bridge.load_cli_module`. ``widget`` is the widget-type
    NAME looked up in :data:`pyforge.atlas.views.widgets.WIDGETS` at render time (Story
    14.2, CAP-3) — declared here as a plain string, never validated at construction time, so
    this module never has to depend on ``widgets.py`` (which itself depends on this module
    for the :class:`View` type — that would be a cycle).
    ``columns`` is the ordered, declared table-column list — stable even when a query
    returns 0 rows.
    """

    name: str
    title: str
    script: str
    widget: str
    columns: tuple[str, ...]
    query_kwargs: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # query_kwargs is declared as a plain dict for construction convenience (the
        # STATIC_VIEWS literals below read naturally as dict literals), but a frozen
        # dataclass with a mutable field undermines its own immutability guarantee — wrap
        # it in a read-only view here (the standard frozen-dataclass escape hatch, since
        # __setattr__ is disabled). ``**view.query_kwargs`` still works fine on a
        # MappingProxyType at every call site.
        object.__setattr__(self, "query_kwargs", MappingProxyType(dict(self.query_kwargs)))


STATIC_VIEWS: tuple[View, ...] = (
    View(
        name="staleness-report",
        title="Staleness Report",
        script="staleness_report",
        widget="grid",
        columns=(
            "conda_name",
            "feedstock_name",
            "latest_conda_version",
            "latest_conda_upload",
            "total_downloads",
            "recipe_format",
            "feedstock_archived",
            "vuln_total",
            "vuln_critical_affecting_current",
            "vuln_high_affecting_current",
            "vuln_kev_affecting_current",
            "vuln_max_epss_score",
            "vuln_max_epss_percentile",
            "vuln_cwe_top",
            "vdb_scanned_at",
            "age_days",
            "uploaded_iso",
        ),
        query_kwargs={
            "maintainer": None,
            "min_age_days": 0,
            "limit": 25,
            "include_archived": False,
            "by_risk": False,
            "has_vulns": False,
            "bot_stuck": False,
            "by_epss": False,
            "has_cwe": None,
        },
    ),
    View(
        name="feedstock-health",
        title="Feedstock Health",
        script="feedstock_health",
        widget="grid",
        columns=(
            "conda_name",
            "feedstock_name",
            "latest_conda_version",
            "bot_open_pr_count",
            "bot_last_pr_state",
            "bot_last_pr_version",
            "bot_version_errors_count",
            "feedstock_bad",
            "bot_status_fetched_at",
            "total_downloads",
            "vuln_critical_affecting_current",
            "vuln_high_affecting_current",
            "gh_default_branch_status",
            "gh_open_issues_count",
            "gh_open_prs_count",
            "gh_pushed_at",
            "gh_status_fetched_at",
        ),
        query_kwargs={
            "maintainer": None,
            "filter_kind": "stuck",
            "limit": 25,
        },
    ),
    View(
        name="behind-upstream",
        title="Behind Upstream",
        script="behind_upstream",
        widget="grid",
        columns=(
            "conda_name",
            "pypi_name",
            "latest_conda_version",
            "latest_conda_upload",
            "total_downloads",
            "vuln_critical_affecting_current",
            "vuln_high_affecting_current",
            "conda_source_registry",
            "upstream_source",
            "upstream_version",
            "upstream_url",
            "lag_label",
        ),
        query_kwargs={
            "maintainer": None,
            "limit": 50,
        },
    ),
    View(
        name="cve-watcher",
        title="CVE Watcher",
        script="cve_watcher",
        widget="grid",
        columns=(
            "conda_name",
            "now_v",
            "then_v",
            "delta",
            "latest_conda_version",
            "total_downloads",
        ),
        query_kwargs={
            "maintainer": None,
            "since_days": 7,
            "severity": "C",
            "only_increases": False,
            "limit": 25,
            "epss_threshold": None,
        },
    ),
    View(
        name="release-cadence",
        title="Release Cadence",
        script="release_cadence",
        widget="grid",
        columns=(
            "conda_name",
            "total_versions",
            "releases_30d",
            "releases_90d",
            "releases_365d",
            "last_upload",
            "first_upload",
            "latest_v",
            "trend",
        ),
        query_kwargs={
            "package": None,
            "maintainer": None,
            "limit": 30,
        },
    ),
    View(
        name="adoption-stage",
        title="Adoption Stage",
        script="adoption_stage",
        widget="grid",
        columns=(
            "conda_name",
            "latest_conda_version",
            "latest_conda_upload",
            "total_downloads",
            "latest_version_downloads",
            "total_versions",
            "releases_30d",
            "first_upload_unix",
            "age_days",
            "stage",
            "lifetime_days",
        ),
        query_kwargs={
            "package": None,
            "maintainer": None,
            "limit": 30,
        },
    ),
)


def get_view(name: str) -> View:
    """Look up a :class:`View` by name; raises ``KeyError`` naming the unknown view."""
    for view in STATIC_VIEWS:
        if view.name == name:
            return view
    raise KeyError(f"unknown static view {name!r}; known views: {', '.join(v.name for v in STATIC_VIEWS)}")
