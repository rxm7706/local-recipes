"""The BSL-driven Vizro app factory (Story D2, FR-9, AD-8/AD-17/NFR-8).

``build_dashboard`` assembles a ``vm.Dashboard`` from the honest-core page set and registers
each page's data function in Vizro's ``data_manager``. Data functions are LAZY — Vizro calls
them at render time, not at build — so the dashboard OBJECT builds fully offline with no
server and no migrated data present (the ``dashboard-dryrun`` gate builds the object + asserts
structure, exactly like the C1 ``dagster-dryrun`` / C2 ``viz-loadable`` gates; it never
``.run()``s a server). The one exception is a page that DECLARES filters: Vizro's own
``Filter.pre_build`` loads a target's data to choose the selector, so ``_declared_filters``
asks the loader for that page up front rather than hiding a second, hidden read behind it.

Every data function routes through ``dashboard.data`` (the AD-8 BSL seam) or
``dashboard.factory_status``; no metric is computed here.

Page set (the full 34-page inventory, Story 20.5 / CAP-7 closing DW-D2-1):
  * GROUNDED data pages — feedstock-health, my-feedstocks, estate-cache
    (BSL over a migrated dataset or the CAP-19 estate Parquet).
  * BSL-WIRED pages over the composed ``semantic_packages`` store — staleness-report,
    query-atlas, detail-cf-atlas, adoption-stage. The store is materialized by the
    ``semantic_packages`` pipeline (Story 20.3); a checkout that has not run it yet gets
    the honest-empty result ``_bsl_query_or_empty`` returns, never a fabricated row.
  * NO-BSL-MODEL SHELL pages — behind-upstream, whodepends (no D1 BSL model exists yet; a
    Card states the gap — no data function, no fabrication).
  * BSL-WIRED pages over their own per-page model (Story 20.5) — the remaining atlas-CLI /
    cyclonedx-suite / seed-gap-suggester pages, each routed through a model in
    ``semantic/models.py``. Each page's ``note`` names the pipeline that has still to
    produce its backing Parquet; until it does, the page renders the honest-empty state.
  * REPORT-ARTIFACT pages — export-purls, inventory-match, add-handoff, library-futures
    (FR-9: a write-path or per-invocation CLI; the dashboard surfaces the LATEST cached
    run only, never triggers one).
  * LIVE-SCAN-ARTIFACT pages — scan-project, env-inspect (per-invocation, user-supplied
    input). These two DO submit a new scan from the dashboard: a path input plus a Run
    button whose action goes through ``dashboard.scan_submit``, which runs the CLI over
    ``pyforge.core.process`` and refreshes the cached Parquet the page reads.
  * factory-status — the fully-specified BMAD-artifact-state page (AD-17 build stamp).

Each ``PageDef`` also declares the controls DESIGN.md § 3–5 specifies for that page — the
filter columns and the one chart — and ``_data_page`` renders them;
``tests/integration/dashboard/test_dashboard_controls.py`` compares the declarations
against DESIGN.md's own per-page Layout bullets.

The 19-page spine (BSL models, layouts, personas, journeys) is
``_bmad-output/projects/pyforge-atlas/planning-artifacts/{DESIGN,EXPERIENCE}.md`` (Story
20.4, CAP-7).
"""

from __future__ import annotations

import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import vizro.models as vm
import vizro.plotly.express as px
from dash import html, no_update
from vizro import Vizro
from vizro.managers import data_manager, model_manager
from vizro.models.types import capture
from vizro.tables import dash_ag_grid

from .. import provenance as _provenance
from ..provenance import ProvenanceInfo
from . import data as _data
from . import factory_status as _fs
from . import scan_submit as _scan

# `UserInput` is Vizro 0.1.60's text-entry component but is not in the default
# `Page.components` union (it is a form component). `add_type` is Vizro's own
# documented way to widen that union — the two live-scan pages need a free-text
# path field, which no selector in `SelectorType` provides.
vm.Page.add_type("components", vm.UserInput)

# The D2 AC's live-confirmed-first consumer set (order preserved for determinism).
LIVE_CONSUMER_CLIS = (
    "behind-upstream",
    "query-atlas",
    "whodepends",
    "feedstock-health",
    "my-feedstocks",
    "detail-cf-atlas",
    "staleness-report",
)


@dataclass(frozen=True)
class ChartDef:
    """The one ``vm.Graph`` a page's DESIGN.md § 3–5 Layout bullet names.

    ``x``/``y`` are columns of that page's own BSL loader, so a chart can never
    be declared over a column the page does not actually project.
    """

    kind: str  # the vizro.plotly.express function name, e.g. "bar"
    x: str
    y: str


@dataclass(frozen=True)
class PageDef:
    """Static description of a built page (introspected by the dashboard-dryrun gate)."""

    id: str
    title: str
    cli: str  # the legacy read CLI this page ports (or "factory-status")
    # "grounded-data" | "bsl-shell" | "no-bsl-shell" | "factory" | "report-artifact"
    # | "live-scan-artifact" — the latter two added by Story 20.5 (DESIGN.md § 1):
    # report-artifact reads the LATEST cached run of a write-path/per-invocation CLI
    # (the dashboard never triggers one); live-scan-artifact is per-invocation,
    # user-supplied input, and the dashboard DOES submit a new scan (Story 27.3).
    kind: str
    note: str = ""
    # The controls DESIGN.md specifies for this page (Story 27.3, DW-FU-20-5).
    # `filters` are loader column names, one `vm.Filter` each; `chart` is the one
    # `vm.Graph`. A page DESIGN.md gives no Filter/Graph bullet declares neither.
    filters: tuple[str, ...] = ()
    chart: ChartDef | None = None


PAGE_INVENTORY: tuple[PageDef, ...] = (
    PageDef("feedstock-health", "Feedstock Health", "feedstock-health", "grounded-data"),
    PageDef("my-feedstocks", "My Feedstocks", "my-feedstocks", "grounded-data"),
    PageDef("estate-cache", "Estate Cache", "estate-cache", "grounded-data"),
    PageDef(
        "staleness-report",
        "Staleness Report",
        "staleness-report",
        "bsl-shell",
        note="Wired to build_packages_model.staleness_age_days over the composed "
        "semantic_packages store (`kedro run --pipeline semantic_packages`). "
        "latest_conda_upload is declared NULL by that pipeline's node — it has no "
        "migrated input — so the staleness age is null wherever that is the only source.",
    ),
    PageDef(
        "query-atlas",
        "Query Atlas",
        "query-atlas",
        "bsl-shell",
        note="Wired to build_packages_model (is_actionable + adoption stage + downloads) "
        "over the composed semantic_packages store (`kedro run --pipeline "
        "semantic_packages`).",
    ),
    PageDef(
        "detail-cf-atlas",
        "Package Detail",
        "detail-cf-atlas",
        "bsl-shell",
        note="Wired to build_packages_model (full per-package metric row) over the "
        "composed semantic_packages store (`kedro run --pipeline semantic_packages`).",
    ),
    PageDef(
        "behind-upstream",
        "Behind Upstream",
        "behind-upstream",
        "no-bsl-shell",
        note="No D1 BSL model yet: the conda-vs-upstream currency join needs "
        "vcs_upstream_versions ⋈ packages (D1 shipped packages / feedstock_health / "
        "maintainers only). Full page CIS-two-spine-deferred (DW-D2).",
    ),
    PageDef(
        "whodepends",
        "Who Depends",
        "whodepends",
        "no-bsl-shell",
        note="No D1 BSL model yet: the reverse-dependency graph over core_dependencies is "
        "not a declared BSL model. Full page CIS-two-spine-deferred (DW-D2).",
    ),
    # -- Story 20.5 (CAP-7) — the remaining 19 pages, per DESIGN.md/EXPERIENCE.md --
    # Atlas-CLI pages (8, DESIGN.md § 3)
    PageDef(
        "cve-watcher",
        "CVE Watch",
        "cve-watcher",
        "bsl-shell",
        note="Wired to build_vuln_history_model; renders empty until the vuln_history "
        "snapshot-diff dataset materializes. DESIGN.md § 3.1 also names a maintainer "
        "filter; the loader projects no maintainer column, so only severity and "
        "since-days are declared here.",
        filters=("severity", "since_days"),
    ),
    PageDef(
        "version-downloads",
        "Version Downloads",
        "version-downloads",
        "bsl-shell",
        note="Wired to build_version_downloads_model; renders empty until the "
        "per-version download-history dataset materializes.",
        chart=ChartDef("bar", x="version", y="downloads"),
    ),
    PageDef(
        "release-cadence",
        "Release Cadence",
        "release-cadence",
        "bsl-shell",
        note="Wired to build_release_cadence_model.trend_label (release_cadence.py's "
        "own accelerating/stable/decelerating/silent classifier, ported verbatim); "
        "renders empty until the rolling-window dataset materializes. DESIGN.md § 3.3's "
        "bar-per-window chart needs a long `window` dimension the model does not "
        "project — it has one measure per window — so the 90-day window is charted.",
        chart=ChartDef("bar", x="conda_name", y="release_count_90d"),
    ),
    PageDef(
        "find-alternative",
        "Find Alternative",
        "find-alternative",
        "bsl-shell",
        note="Wired to build_alternative_candidates_model; renders empty until the "
        "Phase E/J similarity dataset materializes.",
        filters=("archived_name",),
    ),
    PageDef(
        "adoption-stage",
        "Adoption Stage",
        "adoption-stage",
        "bsl-shell",
        note="The portfolio-wide lifecycle VIEW; re-uses build_packages_model.adoption_stage "
        "(no new model) over the same composed semantic_packages store as detail-cf-atlas.",
        chart=ChartDef("bar", x="adoption_stage", y="package_count"),
    ),
    PageDef(
        "scan-project",
        "Scan Project",
        "scan-project",
        "live-scan-artifact",
        note="Wired to build_scan_result_model over the latest cached per-invocation scan. "
        "The page submits a new scan itself: enter a project path and press Run, and "
        "dashboard.scan_submit runs the scan-project CLI through pyforge.core.process, "
        "rewrites this page's cached Parquet, and the grid re-renders from it.",
    ),
    PageDef(
        "env-inspect",
        "Environment Inspect",
        "env-inspect",
        "live-scan-artifact",
        note="Wired to build_env_inspect_model over the latest cached per-invocation "
        "rollup. Same submit path as scan-project: a conda/pixi env prefix path goes to "
        "the env-inspect CLI's --licenses and --security modes through "
        "pyforge.core.process, and this page's cached Parquet is rewritten from both.",
    ),
    PageDef(
        "distribution-breakdown",
        "Distribution Breakdown",
        "distribution-breakdown",
        "bsl-shell",
        note="Merges platform-breakdown / pyver-breakdown / channel-split behind one "
        "`facet` dimension (build_distribution_breakdown_model); the python-version "
        "facet's --policy-check bump-safety classifier (pyver_breakdown.py's own "
        "policy_check_status, ported verbatim) rides along. Renders empty until the "
        "per-facet download-breakdown dataset materializes.",
        filters=("facet",),
        chart=ChartDef("bar", x="bucket", y="downloads_90d"),
    ),
    # Cyclonedx-suite pages (7, DESIGN.md § 4)
    PageDef(
        "export-purls",
        "Export Purls",
        "export-purls",
        "report-artifact",
        note="An artifact-freshness index (build_purl_export_model), not a row-query; "
        "renders empty until the six purl artifacts' regeneration manifest materializes.",
    ),
    PageDef(
        "mapping-gap",
        "Mapping Gap",
        "mapping-gap",
        "bsl-shell",
        note="Wired to build_mapping_gap_model, READ-ONLY (the CLI's --write mode stays "
        "CLI-only); renders empty until the classification-gap dataset materializes.",
    ),
    PageDef(
        "universe-sbom",
        "Universe SBOM",
        "universe-sbom",
        "bsl-shell",
        note="A SUMMARY over the ~856k-component BOM (build_universe_sbom_summary_model), "
        "never a full-table browse; renders empty until the universe-BOM summary "
        "dataset materializes.",
        filters=("slice",),
    ),
    PageDef(
        "inventory-match",
        "Inventory Match",
        "inventory-match",
        "report-artifact",
        note="FR-9 exception: the LATEST per-invocation match report only "
        "(build_inventory_match_report_model), never a live re-match from the dashboard.",
    ),
    PageDef(
        "add-handoff",
        "Add Handoff",
        "add-handoff",
        "report-artifact",
        note="FR-9 exception: the LATEST ADD-bucket worklist only "
        "(build_add_handoff_report_model), READ-ONLY — a write-path CLI, never "
        "triggered from the dashboard. Multi-agent claim/lock coordination is "
        "forward-looking work (DESIGN.md § 4.5).",
    ),
    PageDef(
        "library-futures",
        "Library Futures",
        "library-futures",
        "report-artifact",
        note="FR-9 exception: the LATEST cached futures scorecard only "
        "(build_library_futures_report_model) — in-memory/inventory-scoped by design, "
        "no live catalog column.",
    ),
    PageDef(
        "recommend-2027",
        "Recommend 2027",
        "recommend-2027",
        "bsl-shell",
        note="Wired to build_recommend_2027_model (the S5-S7 per-signal scorecard); "
        "renders empty until the annotated-BOM dataset materializes.",
    ),
    # Seed-gap-suggester pages (4, DESIGN.md § 5) — all READ-ONLY proposal lists
    PageDef(
        "lts-registry-gap",
        "LTS Registry Gap",
        "lts-registry-gap",
        "bsl-shell",
        note="Wired to build_lts_registry_gap_model, READ-ONLY suggester; renders "
        "empty until the endoflife.date diff dataset materializes.",
    ),
    PageDef(
        "cwe-seed-gap",
        "CWE Seed Gap",
        "cwe-seed-gap",
        "bsl-shell",
        note="Wired to build_cwe_seed_gap_model, READ-ONLY suggester; renders empty "
        "until the Other-bucket CWE classification dataset materializes.",
    ),
    PageDef(
        "spdx-schema-gap",
        "SPDX Schema Gap",
        "spdx-schema-gap",
        "bsl-shell",
        note="Wired to build_spdx_schema_gap_model, READ-ONLY suggester; renders "
        "empty until the vendored-vs-upstream SPDX diff dataset materializes.",
    ),
    PageDef(
        "license-map-gap",
        "License Map Gap",
        "license-map-gap",
        "bsl-shell",
        note="Wired to build_license_map_gap_model, READ-ONLY suggester; renders "
        "empty until the unmapped-license dataset materializes.",
    ),
    PageDef(
        "identity-catalog",
        "Identity Catalog",
        "identity-catalog",
        "bsl-shell",
        note="Wired to build_identity_catalog_model over identity_complete_export.parquet "
        "(Story 23.5 complete export); renders empty until bootstrap materializes it.",
    ),
    PageDef(
        "identity-ops",
        "Identity Ops",
        "identity-ops",
        "bsl-shell",
        note="Wired to build_identity_ops_model over identity_complete_export.parquet "
        "(Story 23.5); four panes (Priority/Issues/Builds/Census); renders empty until "
        "the complete export exists.",
    ),
    PageDef(
        "identity-workbook",
        "Identity Workbook",
        "identity-workbook",
        "bsl-shell",
        note="Wired to build_identity_workbook_model joining identity_complete_export.parquet "
        "(Story 23.5) with enterprise_jfrog_consumption.parquet (Story 23.2); "
        "renders an honest empty shell naming the specific missing file until both exist.",
    ),
    # -- Story 21.9 (CAP-5) — Epic 21 bootstrap verification operator pages --
    PageDef(
        "bootstrap-index-health",
        "Bootstrap Index Health",
        "bootstrap-index-health",
        "bsl-shell",
        note="Wired to build_bootstrap_index_health_model over Tier 0/1 catalog index "
        "manifest Parquet (Stories 21.3/21.4); renders empty until bootstrap "
        "materializes the index-health summary.",
    ),
    PageDef(
        "identity-export-snapshot",
        "Identity Export Snapshot",
        "identity-export-snapshot",
        "bsl-shell",
        note="Wired to build_identity_export_snapshot_model over identity_export_parquet "
        "(Story 21.6); renders empty until the identity join export materializes.",
    ),
    PageDef(
        "live-catalog-coverage",
        "Live Catalog Coverage",
        "live-catalog-coverage",
        "bsl-shell",
        note="Wired to build_live_catalog_coverage_model — aggregate BOOL coverage aligned "
        "with verification-matrix.md; renders empty until the coverage summary "
        "Parquet materializes.",
    ),
    PageDef("factory-status", "Factory Status", "factory-status", "factory"),
)

DASHBOARD_ID = "cf-atlas"
DASHBOARD_TITLE = "cf_atlas Factory"


def _provenance_line(provenance: ProvenanceInfo) -> str:
    """The AD-17 stamp line: THIS page's own backing data's provenance (a real
    file mtime / row timestamp, or an honest "unavailable" reason) — never the
    dashboard's build/render time standing in for it (C6)."""
    if provenance.kind == "unavailable":
        return f"**Data build stamp (AD-17):** unavailable — {provenance.reason}"
    return f"**Data build stamp (AD-17):** `{provenance.build_stamp}` ({provenance.kind})"


def _legibility_card(page: PageDef, *, grounded: bool, provenance: ProvenanceInfo) -> vm.Card:
    """A semantic markdown Card carrying the page's provenance + any data-gap note
    (NFR-8 agent-legibility — a deterministic, agent-readable header)."""
    lines = [
        f"### {page.title}",
        "",
        f"Ports the `{page.cli}` read CLI. Data flows through the D1 BSL models (AD-8).",
    ]
    if grounded:
        lines.append("")
        lines.append("**Data:** live — BSL query over the migrated catalog dataset.")
    if page.note:
        lines.append("")
        lines.append(f"**Data gap:** {page.note}")
    lines.append("")
    lines.append(_provenance_line(provenance))
    return vm.Card(id=f"{page.id}--about", text="\n".join(lines))


def _declared_chart(page: PageDef, key: str) -> vm.Graph | None:
    """The one ``vm.Graph`` this page's ``PageDef`` declares, over the same data key."""
    if page.chart is None:
        return None
    figure = getattr(px, page.chart.kind)
    return vm.Graph(id=f"{page.id}--chart", figure=figure(key, x=page.chart.x, y=page.chart.y))


def _declared_filter_bundle(
    page: PageDef, loader: Callable[[], Any]
) -> tuple[Any | None, list[vm.Filter]]:
    """One ``vm.Filter`` per declared column — but only once the page's data has rows.

    Returns ``(build_time_frame, filters)``. ``build_time_frame`` is the loader's
    successful read (including honest-empty frames); it is ``None`` only when the
    loader raised so ``_data_page`` can keep a dynamic data source for read-time
    errors.

    Vizro's ``Filter.pre_build`` refuses a column that "does not contain anything"
    (``vizro/models/_controls/filter.py`` carries its own ``TODO: Enable empty
    data_frame handling``), so an honest-empty page carries no Filter, exactly as it
    carries no rows. What DESIGN.md is compared against is the DECLARATION on
    ``PageDef``; this function decides only whether the declared control can be built
    against today's data.

    A declared column the loader does NOT project is a typo, not an empty state, and
    refuses loudly — an honest-empty frame still carries its declared columns.

    Building the dashboard must not depend on the data root being READABLE (it is
    offline-buildable against any root, including none), so a loader that raises
    yields no control here and the page's own read path surfaces the error where it
    belongs — in the page, at read time.
    """
    if not page.filters:
        return None, []
    try:
        frame = loader()
    except Exception as exc:  # noqa: BLE001 — any read failure is the page's to report
        warnings.warn(
            f"page {page.id!r} declares filters but its data could not be read "
            f"at build time ({type(exc).__name__}: {exc}); rendering no filter",
            stacklevel=2,
        )
        return None, []
    absent = [column for column in page.filters if column not in frame.columns]
    if absent:
        msg = (
            f"page {page.id!r} declares filter column(s) {absent} its loader does not "
            f"project (projected: {sorted(frame.columns)})"
        )
        raise ValueError(msg)
    filters = [
        vm.Filter(id=f"{page.id}--filter-{column}", column=column)
        for column in page.filters
        if bool(frame[column].notna().any())
    ]
    return frame, filters


def _declared_filters(page: PageDef, loader: Callable[[], Any]) -> list[vm.Filter]:
    """``_declared_filter_bundle`` without the build-time frame (tests and call sites)."""
    _, filters = _declared_filter_bundle(page, loader)
    return filters


def _data_page(page: PageDef, loader: Callable[[], Any], *, grounded: bool, provenance: ProvenanceInfo) -> vm.Page:
    """A page = a legibility Card + an AgGrid fed by a lazily-registered BSL data
    function, plus whatever filter/chart controls the ``PageDef`` declares."""
    key = f"data::{page.id}"
    build_frame, controls = _declared_filter_bundle(page, loader)
    if build_frame is not None:
        # Vizro marks filters on dynamic data sources as _dynamic; the selector is
        # built invisible and relies on a clientside reload that e2e caught as an
        # empty/hidden #…--filter-* container (Story 27.5 / DW-atlas-27-3-1). Pin
        # the same frame _declared_filter_bundle already read at build time.
        data_manager[key] = build_frame
    else:
        data_manager[key] = loader
    components: list[Any] = [
        _legibility_card(page, grounded=grounded, provenance=provenance),
        vm.AgGrid(id=f"{page.id}--grid", figure=dash_ag_grid(key)),
    ]
    chart = _declared_chart(page, key)
    if chart is not None:
        components.append(chart)
    return vm.Page(
        id=page.id,
        title=page.title,
        components=components,
        controls=controls,
    )


def _scan_action(page: PageDef, data_root: Path) -> vm.Action:
    """The live-scan pages' submit action (DESIGN.md § 3.6/3.7; DW-FU-20-5-2).

    ``page_id``/``data_root`` are closed over rather than passed as action
    arguments: Vizro reads every argument of a captured action as a runtime
    reference, and a static one would put the action on its deprecated legacy
    path. The one runtime argument is the path field's value.
    """
    page_id = page.id
    grid_id = f"{page.id}--grid"

    @capture("action")
    def run_scan(path_value: str | None) -> tuple[str, Any]:
        submission = _scan.submit_scan(page_id, path_value, data_root=data_root)
        if submission.frame is None:
            return f"**{submission.status}** — {submission.message}", no_update
        return (
            f"**{submission.status}** — {submission.message}",
            model_manager[grid_id](data_frame=submission.frame),
        )

    return vm.Action(
        id=f"{page.id}--submit-action",
        function=run_scan(f"{page.id}--path.value"),
        outputs=[f"{page.id}--status.text", f"{grid_id}.children"],
    )


def _scan_page(
    page: PageDef,
    loader: Callable[[], Any],
    *,
    provenance: ProvenanceInfo,
    data_root: Path,
) -> vm.Page:
    """A live-scan page: the shared Card + grid, plus a path field and a Run button.

    The button's action is the ONLY place the dashboard starts a process, and it
    goes through ``dashboard.scan_submit`` (``pyforge.core.process``, AD-4). The
    action writes the page's own cached Parquet and hands the refreshed frame
    straight back to this page's grid, so the result is on screen without a reload.
    """
    key = f"data::{page.id}"
    data_manager[key] = loader
    return vm.Page(
        id=page.id,
        title=page.title,
        components=[
            _legibility_card(page, grounded=False, provenance=provenance),
            vm.UserInput(
                id=f"{page.id}--path",
                title="Path to scan",
                placeholder="/path/to/project" if page.id == "scan-project" else "/path/to/env/prefix",
            ),
            vm.Button(id=f"{page.id}--submit", text="Run scan", actions=[_scan_action(page, data_root)]),
            vm.Text(id=f"{page.id}--status", text="No scan submitted yet in this session."),
            vm.AgGrid(id=f"{page.id}--grid", figure=dash_ag_grid(key)),
        ],
    )


def _shell_page(page: PageDef, *, provenance: ProvenanceInfo) -> vm.Page:
    """A no-BSL-model shell: a Card stating the gap, no data function (no fabrication)."""
    return vm.Page(
        id=page.id,
        title=page.title,
        components=[_legibility_card(page, grounded=False, provenance=provenance)],
    )


def _resolve_two_file_provenance(
    ranked_path: Path,
    enterprise_path: Path,
) -> ProvenanceInfo:
    """AD-17 for two-source pages: unavailable file wins; else older stamp."""
    ranked = _provenance.resolve_for_file(ranked_path)
    enterprise = _provenance.resolve_for_file(enterprise_path)
    if ranked.kind == "unavailable":
        return ranked
    if enterprise.kind == "unavailable":
        return enterprise
    ranked_stamp = ranked.build_stamp or ""
    enterprise_stamp = enterprise.build_stamp or ""
    return ranked if ranked_stamp <= enterprise_stamp else enterprise


def _identity_workbook_page(
    page: PageDef,
    *,
    complete_parquet: Path,
    enterprise_parquet: Path,
    provenance: ProvenanceInfo,
    gap_message: str | None,
) -> vm.Page:
    """JFROG map page — match-bucket grid + static external-count reference table."""
    key = f"data::{page.id}"
    data_manager[key] = lambda: _data.load_identity_workbook(complete_parquet, enterprise_parquet)
    lines = [
        f"### {page.title}",
        "",
        f"Ports the `{page.cli}` read CLI. Data flows through the D1 BSL models (AD-8).",
    ]
    if gap_message:
        lines.append("")
        lines.append(f"**Data gap:** {gap_message}")
    elif page.note:
        lines.append("")
        lines.append(f"**Data gap:** {page.note}")
    lines.append("")
    lines.append(_provenance_line(provenance))
    external_rows = "\n".join(
        f"| {src} | {count} | {via} | {legacy} |" for src, count, via, legacy in _data.IDENTITY_WORKBOOK_EXTERNAL_COUNTS
    )
    external_card = vm.Card(
        id=f"{page.id}--external",
        text=(
            "### External source counts\n\n"
            "| Source | Count | Via | Legacy tab |\n"
            "| --- | ---: | --- | --- |\n"
            f"{external_rows}"
        ),
    )
    return vm.Page(
        id=page.id,
        title=page.title,
        components=[
            vm.Card(id=f"{page.id}--about", text="\n".join(lines)),
            external_card,
            vm.AgGrid(id=f"{page.id}--grid", figure=dash_ag_grid(key)),
        ],
    )


def _identity_ops_page(
    page: PageDef,
    *,
    parquet: Path,
    provenance: ProvenanceInfo,
) -> vm.Page:
    """Four-pane identity-ops page — one shared provenance Card + four BSL AgGrids."""
    panes: tuple[tuple[str, str, Callable[[], Any]], ...] = (
        ("priority", "Priority (P × Work)", lambda: _data.load_identity_ops_priority(parquet)),
        ("issues", "Issues (packaging-issue gap)", lambda: _data.load_identity_ops_issues(parquet)),
        ("builds", "Builds (local build status)", lambda: _data.load_identity_ops_builds(parquet)),
        ("census", "Census (feedstock / staged / local)", lambda: _data.load_identity_ops_census(parquet)),
    )
    components: list[Any] = [
        _legibility_card(page, grounded=False, provenance=provenance),
    ]
    for pane_id, heading, loader in panes:
        key = f"data::{page.id}::{pane_id}"
        data_manager[key] = loader
        components.append(vm.Card(id=f"{page.id}--{pane_id}-hdr", text=f"### {heading}"))
        components.append(vm.AgGrid(id=f"{page.id}--{pane_id}-grid", figure=dash_ag_grid(key)))
    return vm.Page(id=page.id, title=page.title, components=components)


def _factory_page(
    page: PageDef,
    *,
    build_stamp: str,
    sprint_status_path: str | Path | None,
    epics_path: str | Path | None,
    specs_dir: str | Path | None,
) -> vm.Page:
    """factory-status — AD-17 build stamp (in a Card AND row 0 of the table) + the BMAD
    artifact-state table."""
    key = f"data::{page.id}"

    def _loader() -> Any:
        return _fs.build_factory_status_frame(
            build_stamp=build_stamp,
            sprint_status_path=sprint_status_path,
            epics_path=epics_path,
            specs_dir=specs_dir,
        )

    data_manager[key] = _loader
    stamp_card = vm.Card(
        id=f"{page.id}--stamp",
        text=(
            f"### Factory Status\n\n"
            f"**Build timestamp (AD-17):** `{build_stamp}`\n\n"
            "Live BMAD artifact state — sprint-status.yaml `development_status`, "
            "epics.md frontmatter, and each `docs/specs/*.md` status."
        ),
    )
    # AG Grid infers each column's cellDataType from row 0 alone — and row 0's "status" is
    # the ISO build_stamp, so auto-inference misreads that column as a date and blanks every
    # later status string ("done"/"in-progress"/...). `defaultColDef` merges (vizro's
    # `dash_ag_grid` deep-merges Mapping kwargs) rather than replacing `columnDefs` outright,
    # so the library's own sortable/filter defaults still apply per column.
    return vm.Page(
        id=page.id,
        title=page.title,
        components=[
            stamp_card,
            vm.AgGrid(
                id=f"{page.id}--grid",
                figure=dash_ag_grid(key, defaultColDef={"cellDataType": "text"}),
            ),
        ],
    )


class LandmarkDashboard(vm.Dashboard):
    """``vm.Dashboard`` with the two ARIA landmarks its shipped layout lacks.

    Vizro 0.1.60 builds the page select into a ``<div id="nav-control-panel">``
    and the page content into a ``<div id="right-side">``: a browser agent (or a
    screen reader) gets no ``navigation`` and no ``main`` landmark to jump to.
    This subclass re-tags exactly those two containers after
    ``_arrange_page`` has assembled them — nothing is reordered, no Vizro
    component template is patched, and a Vizro release that adds its own
    landmarks would simply make this a no-op rename.

    ``tests/integration/dashboard/test_dashboard_e2e.py`` asserts both landmarks
    against the rendered DOM (DW-FU-20-5-3).
    """

    def _arrange_page(self, outer_page: Any) -> Any:
        layout = super()._arrange_page(outer_page=outer_page)
        layout["right-side"].role = "main"
        nav_control_panel = layout["nav-control-panel"]
        nav_control_panel.children = [
            html.Nav(
                id="pyforge-nav",
                role="navigation",
                children=nav_control_panel.children,
                **{"aria-label": "Dashboard pages"},
            )
        ]
        return layout


def build_dashboard(
    *,
    build_stamp: str | None = None,
    data_root: str | Path | None = None,
    now: int | None = None,
    sprint_status_path: str | Path | None = None,
    epics_path: str | Path | None = None,
    specs_dir: str | Path | None = None,
    reset: bool = True,
) -> vm.Dashboard:
    """Assemble the BSL-driven Vizro Dashboard object (OFFLINE — no server, no live data).

    ``build_stamp`` (AD-17) and ``now`` are injectable for determinism; both default to wall
    clock resolved ONCE here (never at import). ``reset`` clears Vizro's global managers so
    repeated builds in one process (the gate) are independent.
    """
    if reset:
        Vizro._reset()
    if build_stamp is None:
        build_stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if now is None:
        now = int(time.time())
    root = Path(data_root) if data_root is not None else _data.default_data_root()

    # AD-17 (Story I4): each grounded/bsl-shell page's provenance is THAT page's own
    # backing Parquet file's mtime (resolve_for_file degrades to "unavailable" + a
    # reason when the file is absent, which is what a checkout that has not run the
    # producing pipeline gets). The 2 no-bsl-shell pages have no backing file at all
    # — a hardcoded "unavailable", never a fabricated stamp.
    # One page, one constant: tests/integration/dashboard/test_dashboard_provenance.py
    # pins each page to the Parquet constant its own loader reads (DW-FU-20-5-7).
    feedstock_health_provenance = _provenance.resolve_for_file(root / _data.FEEDSTOCK_HEALTH_PARQUET)
    my_feedstocks_provenance = _provenance.resolve_for_file(root / _data.PACKAGE_MAINTAINERS_PARQUET)
    estate_cache_provenance = _provenance.resolve_for_file(root / _data.ESTATE_CACHE_PARQUET)
    packages_provenance = _provenance.resolve_for_file(root / _data.PACKAGES_PARQUET)
    no_bsl_model_provenance = ProvenanceInfo(
        kind="unavailable",
        build_stamp=None,
        reason="no data function registered for this page",
    )

    # Story 20.5 (CAP-7) — the 19 remaining pages' own backing Parquet provenance
    # (same AD-17 discipline as above: each page's OWN file mtime, "unavailable" +
    # a reason when absent — never a fabricated stamp).
    cve_watcher_provenance = _provenance.resolve_for_file(root / _data.VULN_HISTORY_PARQUET)
    version_downloads_provenance = _provenance.resolve_for_file(root / _data.VERSION_DOWNLOADS_PARQUET)
    release_cadence_provenance = _provenance.resolve_for_file(root / _data.RELEASE_CADENCE_PARQUET)
    find_alternative_provenance = _provenance.resolve_for_file(root / _data.ALTERNATIVE_CANDIDATES_PARQUET)
    scan_project_provenance = _provenance.resolve_for_file(root / _data.SCAN_RESULT_LATEST_PARQUET)
    env_inspect_provenance = _provenance.resolve_for_file(root / _data.ENV_INSPECT_LATEST_PARQUET)
    distribution_breakdown_provenance = _provenance.resolve_for_file(root / _data.DISTRIBUTION_BREAKDOWN_PARQUET)
    export_purls_provenance = _provenance.resolve_for_file(root / _data.PURL_EXPORT_MANIFEST_PARQUET)
    mapping_gap_provenance = _provenance.resolve_for_file(root / _data.MAPPING_GAP_PARQUET)
    universe_sbom_provenance = _provenance.resolve_for_file(root / _data.UNIVERSE_SBOM_SUMMARY_PARQUET)
    inventory_match_provenance = _provenance.resolve_for_file(root / _data.INVENTORY_MATCH_LATEST_PARQUET)
    add_handoff_provenance = _provenance.resolve_for_file(root / _data.ADD_HANDOFF_LATEST_PARQUET)
    library_futures_provenance = _provenance.resolve_for_file(root / _data.LIBRARY_FUTURES_LATEST_PARQUET)
    recommend_2027_provenance = _provenance.resolve_for_file(root / _data.RECOMMEND_2027_PARQUET)
    lts_registry_gap_provenance = _provenance.resolve_for_file(root / _data.LTS_REGISTRY_GAP_PARQUET)
    cwe_seed_gap_provenance = _provenance.resolve_for_file(root / _data.CWE_SEED_GAP_PARQUET)
    spdx_schema_gap_provenance = _provenance.resolve_for_file(root / _data.SPDX_SCHEMA_GAP_PARQUET)
    license_map_gap_provenance = _provenance.resolve_for_file(root / _data.LICENSE_MAP_GAP_PARQUET)
    identity_catalog_provenance = _provenance.resolve_for_file(root / _data.IDENTITY_COMPLETE_EXPORT_PARQUET)
    identity_workbook_complete = root / _data.IDENTITY_COMPLETE_EXPORT_PARQUET
    identity_workbook_enterprise = root / _data.ENTERPRISE_JFROG_CONSUMPTION_PARQUET
    identity_workbook_provenance = _resolve_two_file_provenance(
        identity_workbook_complete,
        identity_workbook_enterprise,
    )
    identity_workbook_gap = _data.identity_workbook_gap_message(
        identity_workbook_complete,
        identity_workbook_enterprise,
    )
    bootstrap_index_health_provenance = _provenance.resolve_for_file(root / _data.BOOTSTRAP_INDEX_HEALTH_PARQUET)
    identity_export_snapshot_provenance = _provenance.resolve_for_file(root / _data.IDENTITY_EXPORT_PARQUET)
    live_catalog_coverage_provenance = _provenance.resolve_for_file(root / _data.LIVE_CATALOG_COVERAGE_PARQUET)

    by_id = {p.id: p for p in PAGE_INVENTORY}
    pages: list[vm.Page] = [
        _data_page(
            by_id["feedstock-health"],
            lambda: _data.load_feedstock_health(root / _data.FEEDSTOCK_HEALTH_PARQUET),
            grounded=True,
            provenance=feedstock_health_provenance,
        ),
        _data_page(
            by_id["my-feedstocks"],
            lambda: _data.load_my_feedstocks(root / _data.PACKAGE_MAINTAINERS_PARQUET),
            grounded=True,
            provenance=my_feedstocks_provenance,
        ),
        _data_page(
            by_id["estate-cache"],
            lambda: _data.load_estate_cache(root / _data.ESTATE_CACHE_PARQUET),
            grounded=True,
            provenance=estate_cache_provenance,
        ),
        _data_page(
            by_id["staleness-report"],
            lambda: _data.load_staleness(root / _data.PACKAGES_PARQUET, now=now),
            grounded=False,
            provenance=packages_provenance,
        ),
        _data_page(
            by_id["query-atlas"],
            lambda: _data.load_query_atlas(root / _data.PACKAGES_PARQUET, now=now),
            grounded=False,
            provenance=packages_provenance,
        ),
        _data_page(
            by_id["detail-cf-atlas"],
            lambda: _data.load_detail(root / _data.PACKAGES_PARQUET, now=now),
            grounded=False,
            provenance=packages_provenance,
        ),
        _shell_page(by_id["behind-upstream"], provenance=no_bsl_model_provenance),
        _shell_page(by_id["whodepends"], provenance=no_bsl_model_provenance),
        # -- Story 20.5 (CAP-7) — the remaining 19 pages --
        _data_page(
            by_id["cve-watcher"],
            lambda: _data.load_cve_watcher(root / _data.VULN_HISTORY_PARQUET),
            grounded=False,
            provenance=cve_watcher_provenance,
        ),
        _data_page(
            by_id["version-downloads"],
            lambda: _data.load_version_downloads(root / _data.VERSION_DOWNLOADS_PARQUET),
            grounded=False,
            provenance=version_downloads_provenance,
        ),
        _data_page(
            by_id["release-cadence"],
            lambda: _data.load_release_cadence(root / _data.RELEASE_CADENCE_PARQUET),
            grounded=False,
            provenance=release_cadence_provenance,
        ),
        _data_page(
            by_id["find-alternative"],
            lambda: _data.load_find_alternative(root / _data.ALTERNATIVE_CANDIDATES_PARQUET),
            grounded=False,
            provenance=find_alternative_provenance,
        ),
        _data_page(
            by_id["adoption-stage"],
            lambda: _data.load_adoption_stage(root / _data.PACKAGES_PARQUET, now=now),
            grounded=False,
            provenance=packages_provenance,
        ),
        _scan_page(
            by_id["scan-project"],
            lambda: _data.load_scan_project(root / _data.SCAN_RESULT_LATEST_PARQUET),
            provenance=scan_project_provenance,
            data_root=root,
        ),
        _scan_page(
            by_id["env-inspect"],
            lambda: _data.load_env_inspect(root / _data.ENV_INSPECT_LATEST_PARQUET),
            provenance=env_inspect_provenance,
            data_root=root,
        ),
        _data_page(
            by_id["distribution-breakdown"],
            lambda: _data.load_distribution_breakdown(root / _data.DISTRIBUTION_BREAKDOWN_PARQUET),
            grounded=False,
            provenance=distribution_breakdown_provenance,
        ),
        _data_page(
            by_id["export-purls"],
            lambda: _data.load_export_purls(root / _data.PURL_EXPORT_MANIFEST_PARQUET),
            grounded=False,
            provenance=export_purls_provenance,
        ),
        _data_page(
            by_id["mapping-gap"],
            lambda: _data.load_mapping_gap(root / _data.MAPPING_GAP_PARQUET),
            grounded=False,
            provenance=mapping_gap_provenance,
        ),
        _data_page(
            by_id["universe-sbom"],
            lambda: _data.load_universe_sbom(root / _data.UNIVERSE_SBOM_SUMMARY_PARQUET),
            grounded=False,
            provenance=universe_sbom_provenance,
        ),
        _data_page(
            by_id["inventory-match"],
            lambda: _data.load_inventory_match(root / _data.INVENTORY_MATCH_LATEST_PARQUET),
            grounded=False,
            provenance=inventory_match_provenance,
        ),
        _data_page(
            by_id["add-handoff"],
            lambda: _data.load_add_handoff(root / _data.ADD_HANDOFF_LATEST_PARQUET),
            grounded=False,
            provenance=add_handoff_provenance,
        ),
        _data_page(
            by_id["library-futures"],
            lambda: _data.load_library_futures(root / _data.LIBRARY_FUTURES_LATEST_PARQUET),
            grounded=False,
            provenance=library_futures_provenance,
        ),
        _data_page(
            by_id["recommend-2027"],
            lambda: _data.load_recommend_2027(root / _data.RECOMMEND_2027_PARQUET),
            grounded=False,
            provenance=recommend_2027_provenance,
        ),
        _data_page(
            by_id["lts-registry-gap"],
            lambda: _data.load_lts_registry_gap(root / _data.LTS_REGISTRY_GAP_PARQUET),
            grounded=False,
            provenance=lts_registry_gap_provenance,
        ),
        _data_page(
            by_id["cwe-seed-gap"],
            lambda: _data.load_cwe_seed_gap(root / _data.CWE_SEED_GAP_PARQUET),
            grounded=False,
            provenance=cwe_seed_gap_provenance,
        ),
        _data_page(
            by_id["spdx-schema-gap"],
            lambda: _data.load_spdx_schema_gap(root / _data.SPDX_SCHEMA_GAP_PARQUET),
            grounded=False,
            provenance=spdx_schema_gap_provenance,
        ),
        _data_page(
            by_id["license-map-gap"],
            lambda: _data.load_license_map_gap(root / _data.LICENSE_MAP_GAP_PARQUET),
            grounded=False,
            provenance=license_map_gap_provenance,
        ),
        _data_page(
            by_id["identity-catalog"],
            lambda: _data.load_identity_catalog(root / _data.IDENTITY_COMPLETE_EXPORT_PARQUET),
            grounded=False,
            provenance=identity_catalog_provenance,
        ),
        _identity_ops_page(
            by_id["identity-ops"],
            parquet=root / _data.IDENTITY_COMPLETE_EXPORT_PARQUET,
            provenance=identity_catalog_provenance,
        ),
        _identity_workbook_page(
            by_id["identity-workbook"],
            complete_parquet=identity_workbook_complete,
            enterprise_parquet=identity_workbook_enterprise,
            provenance=identity_workbook_provenance,
            gap_message=identity_workbook_gap,
        ),
        _data_page(
            by_id["bootstrap-index-health"],
            lambda: _data.load_bootstrap_index_health(root / _data.BOOTSTRAP_INDEX_HEALTH_PARQUET),
            grounded=False,
            provenance=bootstrap_index_health_provenance,
        ),
        _data_page(
            by_id["identity-export-snapshot"],
            lambda: _data.load_identity_export_snapshot(root / _data.IDENTITY_EXPORT_PARQUET),
            grounded=False,
            provenance=identity_export_snapshot_provenance,
        ),
        _data_page(
            by_id["live-catalog-coverage"],
            lambda: _data.load_live_catalog_coverage(root / _data.LIVE_CATALOG_COVERAGE_PARQUET),
            grounded=False,
            provenance=live_catalog_coverage_provenance,
        ),
        _factory_page(
            by_id["factory-status"],
            build_stamp=build_stamp,
            sprint_status_path=sprint_status_path,
            epics_path=epics_path,
            specs_dir=specs_dir,
        ),
    ]
    return LandmarkDashboard(id=DASHBOARD_ID, title=DASHBOARD_TITLE, pages=pages)
