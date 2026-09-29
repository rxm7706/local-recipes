"""`dashboard-dryrun` gate (Story D2, FR-9, AD-8/AD-17, NFR-8) — BUILD OBJECT ONLY.

Structural, OFFLINE gate mirroring the C1 ``dagster-dryrun`` / C2 ``viz-loadable`` pattern:
it builds the BSL-driven Vizro ``Dashboard`` object and asserts the D2 acceptance criteria
that ARE buildable now (the full PAGE_INVENTORY page set + per-page design is CIS-two-spine
deferred, DW-D2). It performs NO live execution — no Vizro server, no ``.run()``. Data
functions are lazy, so the object builds with no migrated data present; the gate exercises
them directly against fixtures to prove they are BSL-driven.

Asserts:
  * the Dashboard object builds offline (Vizro can even build the Dash app);
  * every expected page is present with a stable id + title (deterministic layout, NFR-8);
  * pages are BSL-driven — the data loaders route through the D1 semantic models (AD-8),
    proven by comparing each loader's output to an INDEPENDENT BSL query;
  * the factory-status page reads the real sprint-status.yaml + carries a build stamp (AD-17);
  * agent-legibility structural properties hold (title/id, semantic table, no fabrication).
"""

from __future__ import annotations

import ibis
import pandas as pd
import pytest
import vizro.models as vm
from vizro import Vizro
from vizro.managers import data_manager

from pyforge.atlas.dashboard import app
from pyforge.atlas.dashboard import data as dash_data
from pyforge.atlas.dashboard import factory_status as fs
from pyforge.atlas.semantic import models
from pyforge.atlas.semantic.query_helpers import bsl_query

NOW = 1_700_000_000
STAMP = "2026-07-18T12:00:00Z"


def _dm_get(key: str):
    try:
        return data_manager[key]
    except KeyError:
        return None


@pytest.fixture()
def dashboard():
    return app.build_dashboard(build_stamp=STAMP, data_root="/nonexistent-data-root", now=NOW)


# --------------------------------------------------------------------------- #
# Offline build + structure
# --------------------------------------------------------------------------- #


def test_dashboard_builds_offline(dashboard):
    assert isinstance(dashboard, vm.Dashboard)
    assert dashboard.id == app.DASHBOARD_ID
    # Vizro can build the Dash app object OFFLINE (no server, no data touched at build).
    Vizro._reset()
    d2 = app.build_dashboard(build_stamp=STAMP, data_root="/nonexistent-data-root", now=NOW, reset=False)
    built = Vizro().build(d2)
    assert built is not None


def test_all_expected_pages_present_with_stable_id_and_title(dashboard):
    got = {p.id: p.title for p in dashboard.pages}
    expected = {p.id: p.title for p in app.PAGE_INVENTORY}
    assert got == expected


def test_live_confirmed_consumer_set_ports_first(dashboard):
    """Every CLI in the D2 AC's live-confirmed-first set has a page (id == cli)."""
    page_ids = {p.id for p in dashboard.pages}
    for cli in app.LIVE_CONSUMER_CLIS:
        assert cli in page_ids, f"live-consumer CLI not ported to a page: {cli}"
    assert "factory-status" in page_ids


def test_layout_is_deterministic():
    """NFR-8 deterministic layout: two builds yield identical page id + title order."""
    d1 = app.build_dashboard(build_stamp=STAMP, data_root="/nope", now=NOW)
    order1 = [(p.id, p.title) for p in d1.pages]
    d2 = app.build_dashboard(build_stamp=STAMP, data_root="/nope", now=NOW)
    order2 = [(p.id, p.title) for p in d2.pages]
    assert order1 == order2


def test_every_page_has_title_and_nonempty_components(dashboard):
    """NFR-8 agent-legibility: each page carries a stable id + title + ≥1 component."""
    for page in dashboard.pages:
        assert page.id, "page missing id"
        assert page.title, f"page {page.id} missing title"
        assert page.components, f"page {page.id} has no components"


# `PageDef.kind` is a bare `str` documented in app.py only as a comment (6 values as of
# Story 20.5) -- this is the structural guard that a stray/misspelled kind never ships
# silently (Reviewer-LOW).
_ALLOWED_PAGE_KINDS = {
    "grounded-data",
    "bsl-shell",
    "no-bsl-shell",
    "factory",
    "report-artifact",
    "live-scan-artifact",
}


def test_every_page_kind_is_one_of_the_documented_values():
    got = {p.kind for p in app.PAGE_INVENTORY}
    assert got <= _ALLOWED_PAGE_KINDS, f"undocumented PageDef.kind value(s): {got - _ALLOWED_PAGE_KINDS}"


# --------------------------------------------------------------------------- #
# AD-8 — pages are BSL-driven (loaders route through the semantic models)
# --------------------------------------------------------------------------- #


def test_feedstock_health_page_is_bsl_driven(feedstock_health_parquet):
    """The loader's output EQUALS an independent build_feedstock_health_model query —
    proving the page data flows through the BSL model, not a re-implemented metric (AD-8)."""
    got = dash_data.load_feedstock_health(feedstock_health_parquet)
    table = models.duckdb_table_from_parquet(feedstock_health_parquet)
    expected = bsl_query(
        models.build_feedstock_health_model(table),
        dimensions=["feedstock_name", "ci_red", "has_open_prs", "has_open_issues"],
    )
    pd.testing.assert_frame_equal(
        got.sort_values("feedstock_name").reset_index(drop=True),
        expected.sort_values("feedstock_name").reset_index(drop=True),
    )
    # sanity: the BSL ci_red domain actually fired (failure/error → True, success → False).
    red = dict(zip(got["feedstock_name"], got["ci_red"]))
    assert red == {"alpha": True, "beta": False, "gamma": True}


def test_estate_cache_page_is_bsl_driven(write_parquet):
    """Lane 3 / 36.2 — estate-cache loader equals an independent BSL query."""
    path = write_parquet(
        pd.DataFrame({"sku": ["widget-a", "widget-b"], "units": [12, 7]}),
        "query_plane_estate",
    )
    got = dash_data.load_estate_cache(path)
    table = models.duckdb_table_from_parquet(path)
    expected = models.build_estate_cache_model(table).query(dimensions=["sku"], measures=["units_total"]).execute()
    pd.testing.assert_frame_equal(
        got.sort_values("sku").reset_index(drop=True),
        expected.sort_values("sku").reset_index(drop=True),
    )


def test_estate_cache_page_is_in_inventory(dashboard):
    page = next(p for p in dashboard.pages if p.id == "estate-cache")
    assert page.title == "Estate Cache"
    assert _dm_get("data::estate-cache") is not None


def test_my_feedstocks_page_is_bsl_driven(package_maintainers_parquet):
    got = dash_data.load_my_feedstocks(package_maintainers_parquet)
    table = models.duckdb_table_from_parquet(package_maintainers_parquet)
    expected = bsl_query(
        models.build_package_maintainers_model(table),
        dimensions=["maintainer", "conda_name"],
    )
    pd.testing.assert_frame_equal(
        got.sort_values(["maintainer", "conda_name"]).reset_index(drop=True),
        expected.sort_values(["maintainer", "conda_name"]).reset_index(drop=True),
    )


def test_packages_shell_pages_are_bsl_wired_and_light_up_with_data(packages_parquet):
    """The bsl-shell pages (staleness / query-atlas / detail) are genuinely wired to
    build_packages_model — given the composed store they produce the BSL query result."""
    got = dash_data.load_staleness(packages_parquet, now=NOW)
    table = models.duckdb_table_from_parquet(packages_parquet)
    expected = bsl_query(
        models.build_packages_model(table, now_unix=NOW),
        dimensions=["conda_name", "staleness_age_days", "adoption_stage"],
    )
    pd.testing.assert_frame_equal(
        got.sort_values("conda_name").reset_index(drop=True),
        expected.sort_values("conda_name").reset_index(drop=True),
    )
    # query-atlas + detail also go through build_packages_model without raising.
    qa = dash_data.load_query_atlas(packages_parquet, now=NOW)
    assert set(qa.columns) == {"conda_name", "is_actionable", "adoption_stage", "downloads_total"}
    detail = dash_data.load_detail(packages_parquet, now=NOW)
    assert not detail.empty


def test_dashboard_only_imports_semantic_seam_never_bsl_directly():
    """AD-8 discipline: the dashboard data layer consumes the semantic MODELS (the seam),
    and does not itself import boring_semantic_layer (that ban is enforced package-wide by
    tests/catalog/test_no_inline_io.py; asserted here at the module level too)."""
    from pathlib import Path

    src = Path(dash_data.__file__).read_text(encoding="utf-8")
    assert "from ..semantic import models" in src
    assert "import boring_semantic_layer" not in src


# --------------------------------------------------------------------------- #
# Offline data-gap discipline — empty, never fabricated
# --------------------------------------------------------------------------- #


def test_data_loaders_offline_return_empty_typed_frames_not_fabricated():
    """Missing Parquet (the store's real state today) → empty frame with the declared
    columns; NO fabricated rows."""
    fh = dash_data.load_feedstock_health("/nope.parquet")
    assert fh.empty and list(fh.columns) == ["feedstock_name", "ci_red", "has_open_prs", "has_open_issues"]
    st = dash_data.load_staleness("/nope.parquet", now=NOW)
    assert st.empty and list(st.columns) == ["conda_name", "staleness_age_days", "adoption_stage"]
    mf = dash_data.load_my_feedstocks("/nope.parquet")
    assert mf.empty and list(mf.columns) == ["maintainer", "conda_name"]
    ec = dash_data.load_estate_cache("/nope.parquet")
    assert ec.empty and list(ec.columns) == ["sku", "units_total"]


def test_present_but_untyped_parquet_degrades_not_crash(write_parquet):
    """Reviewer-B S2: a PRESENT but degenerate store — a 0-row packages Parquet whose
    columns round-trip untyped (all-null object) — makes a metric predicate like
    `latest_status.fill_null("active")` raise IbisTypeError. The loader must degrade to the
    declared-column empty frame, never crash the page build."""
    import pandas as pd

    # 0-row, object-typed columns (no pyarrow schema) → the crash the migration's typed
    # schemas avoid, but a first sparse store could hit.
    untyped = pd.DataFrame(
        {
            c: pd.Series([], dtype="object")
            for c in (
                "conda_name",
                "latest_status",
                "feedstock_archived",
                "latest_conda_upload",
                "downloads_total",
                "downloads_30d",
                "latest_upload_age_days",
                "releases_30d",
                "total_versions",
            )
        }
    )
    path = write_parquet(untyped, "untyped_packages")
    st = dash_data.load_staleness(path, now=NOW)
    assert st.empty and list(st.columns) == ["conda_name", "staleness_age_days", "adoption_stage"]


def test_registered_data_functions_are_callable_and_return_frames(dashboard):
    """Every data/factory page registers a lazy data function that returns a DataFrame
    offline (empty here — no data root); the no-bsl shells register NO data function
    (no fabrication)."""
    identity_ops_panes = ("priority", "issues", "builds", "census")
    for page in app.PAGE_INVENTORY:
        if page.id == "identity-ops":
            for pane in identity_ops_panes:
                key = f"data::{page.id}::{pane}"
                obj = _dm_get(key)
                assert obj is not None, f"{page.id}::{pane} data function not registered"
                assert isinstance(obj.load(), pd.DataFrame)
            continue
        key = f"data::{page.id}"
        obj = _dm_get(key)
        if page.kind == "no-bsl-shell":
            assert obj is None, f"{page.id} must not register a data function"
        else:
            assert obj is not None, f"{page.id} data function not registered"
            assert isinstance(obj.load(), pd.DataFrame)


# --------------------------------------------------------------------------- #
# factory-status — BMAD state + AD-17 build stamp
# --------------------------------------------------------------------------- #


def test_factory_status_reads_the_real_sprint_status():
    """The factory-status frame reads the REAL tracked sprint-status.yaml (default path)
    and surfaces known story keys + their statuses."""
    sprint_status_path = fs._default_paths()["sprint_status_path"]
    if not sprint_status_path.exists():
        pytest.skip(
            f"{sprint_status_path} is a gitignored, locally-generated Tier-3 file "
            "(sprint-ledger-sync) -- absent in a fresh worktree/clone"
        )
    frame = fs.build_factory_status_frame(build_stamp=STAMP)
    sprint = frame[frame["source"] == "sprint-status.yaml"]
    keyed = dict(zip(sprint["key"], sprint["status"]))
    # Epic 5's stories (D1/D2 in epics.md's spec-ID alias) are real stories in the live sprint
    # feed. Matched by suffix, not the full key, since the leading numbering scheme is a ledger
    # convention (currently Epic.Story, e.g. "5-1-...") that has already been renamed once
    # (PR #322, 2026-08-08) and may be renamed again.
    assert any(k.endswith("define-the-boring-semantic-layer-bsl-models") for k in keyed)
    assert any(k.endswith("build-the-vizro-dashboard-port-the-28-clis-to-pages") for k in keyed)
    # epics.md frontmatter + spec statuses are surfaced too.
    assert (frame["source"] == "epics.md").any()
    assert (frame["source"] == "docs/specs").sum() >= 1


def test_factory_status_carries_build_timestamp_ad17(dashboard):
    """AD-17: the injected build stamp travels in the rendered surface — row 0 of the
    factory frame AND the factory page's stamp Card text."""
    frame = fs.build_factory_status_frame(build_stamp=STAMP)
    assert frame.iloc[0]["key"] == "generated_at"
    assert frame.iloc[0]["status"] == STAMP
    factory_page = next(p for p in dashboard.pages if p.id == "factory-status")
    stamp_card = next(c for c in factory_page.components if isinstance(c, vm.Card))
    assert STAMP in stamp_card.text
    assert "AD-17" in stamp_card.text


def test_factory_status_exposes_a_semantic_table(dashboard):
    """Agent-legibility: the factory page exposes its data through an AgGrid (semantic
    HTML table) with a stable column schema."""
    factory_page = next(p for p in dashboard.pages if p.id == "factory-status")
    assert any(isinstance(c, vm.AgGrid) for c in factory_page.components)
    frame = fs.build_factory_status_frame(build_stamp=STAMP)
    assert list(frame.columns) == fs.FRAME_COLUMNS


def test_factory_status_grid_pins_text_celldatatype(dashboard):
    """AG Grid infers a column's cellDataType from row 0 alone; row 0's "status" is the
    ISO build_stamp, which would otherwise get the column misread as a date and blank
    every later status string. Offline regression lock for the fix (mirrors the
    Playwright-only e2e coverage at a fast, deterministic layer)."""
    factory_page = next(p for p in dashboard.pages if p.id == "factory-status")
    grid = next(c for c in factory_page.components if isinstance(c, vm.AgGrid))
    assert grid.figure["defaultColDef"]["cellDataType"] == "text"


def test_factory_status_reads_injected_fixture_artifacts(bmad_fixture):
    frame = fs.build_factory_status_frame(
        build_stamp=STAMP,
        sprint_status_path=bmad_fixture["sprint"],
        epics_path=bmad_fixture["epics"],
        specs_dir=bmad_fixture["specs"],
    )
    sprint = dict(
        zip(
            frame.loc[frame["source"] == "sprint-status.yaml", "key"],
            frame.loc[frame["source"] == "sprint-status.yaml", "status"],
        )
    )
    assert sprint["d1-define-the-boring-semantic-layer-bsl-models"] == "done"
    assert frame.loc[frame["source"] == "epics.md", "status"].iloc[0] == "final"
    specs = dict(
        zip(
            frame.loc[frame["source"] == "docs/specs", "artifact"],
            frame.loc[frame["source"] == "docs/specs", "status"],
        )
    )
    # two.md/one.md have status; no-fm.md has no frontmatter → omitted (not fabricated).
    assert specs == {"one": "ready", "two": "shipped"}


def test_factory_status_degrades_on_missing_and_malformed_artifacts(tmp_path):
    """Edge cases: a missing file and a malformed YAML both degrade to an empty
    contribution — never a crash, never a fabricated status."""
    # missing everything → only the build-stamp row survives.
    frame = fs.build_factory_status_frame(
        build_stamp=STAMP,
        sprint_status_path=str(tmp_path / "absent.yaml"),
        epics_path=str(tmp_path / "absent.md"),
        specs_dir=str(tmp_path / "absent-dir"),
    )
    # ONLY the build-stamp row survives: a missing epics.md contributes ZERO rows, exactly
    # like the other two sources — never a fabricated literal "None" status (Reviewer-B S1).
    assert list(frame["source"]) == ["build"]
    assert frame.iloc[0]["status"] == STAMP
    assert "None" not in set(frame["status"])  # no fabricated status leaks in

    # malformed sprint YAML → empty development_status, no crash.
    bad = tmp_path / "bad.yaml"
    bad.write_text("development_status: : : [unbalanced\n", encoding="utf-8")
    assert fs.read_sprint_status(str(bad)) == {}


def test_no_bsl_shell_pages_state_the_gap_without_data(dashboard):
    """behind-upstream / whodepends carry a Card stating the BSL-model gap and register
    NO data function (honest deferral, no fabricated data)."""
    for pid in ("behind-upstream", "whodepends"):
        page = next(p for p in dashboard.pages if p.id == pid)
        assert all(isinstance(c, vm.Card) for c in page.components)
        assert _dm_get(f"data::{pid}") is None
        card = page.components[0]
        assert "Data gap" in card.text


# --------------------------------------------------------------------------- #
# AD-17 (Story I4) — every page carries ITS OWN data's provenance
# --------------------------------------------------------------------------- #


def test_grounded_page_carries_file_mtime_not_render_time(tmp_path):
    """The feedstock-health page's Card states THAT FILE's own mtime (via a
    deliberately old ``os.utime``) — not the dashboard's build_stamp/now
    render-time constants standing in for the data's provenance (C6)."""
    import datetime
    import os

    parquet = tmp_path / dash_data.FEEDSTOCK_HEALTH_PARQUET
    parquet.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"feedstock_name": ["alpha"]}).to_parquet(parquet)
    old_ts = 1_600_000_000  # 2020-09-13 — deliberately far from STAMP/NOW below
    os.utime(parquet, (old_ts, old_ts))

    d = app.build_dashboard(build_stamp=STAMP, data_root=tmp_path, now=NOW)
    page = next(p for p in d.pages if p.id == "feedstock-health")
    card = next(c for c in page.components if isinstance(c, vm.Card))

    expected_stamp = datetime.datetime.fromtimestamp(old_ts, tz=datetime.UTC).isoformat()
    assert expected_stamp in card.text
    assert "AD-17" in card.text
    # NOT the dashboard's own render-time stand-ins.
    assert STAMP not in card.text
    assert str(NOW) not in card.text


def test_shell_pages_state_unavailable_provenance_honestly(dashboard):
    """Under the default, file-absent ``data_root`` every non-grounded,
    non-factory page (the bsl-shell / report-artifact / live-scan-artifact pages
    plus the 2 no-bsl-shell pages) honestly states its OWN data as "unavailable" +
    `AD-17` — never a fabricated stamp, never the dashboard's render time standing
    in for it. Story 20.5 (CAP-7) extends this from the original 3 packages-backed
    shells to all 19 new pages — every one of them routes through the SAME
    `_bsl_query_or_empty` + `resolve_for_file` seam, so the same honest-empty
    contract must hold identically."""
    no_bsl_ids = {"behind-upstream", "whodepends"}
    shell_ids = no_bsl_ids | {
        p.id for p in app.PAGE_INVENTORY if p.kind in {"bsl-shell", "report-artifact", "live-scan-artifact"}
    }
    seen = set()
    for page in dashboard.pages:
        if page.id not in shell_ids:
            continue
        seen.add(page.id)
        card = next(c for c in page.components if isinstance(c, vm.Card))
        assert "unavailable" in card.text
        assert "AD-17" in card.text
        # The TWO distinct unavailable states stay distinguishable — a
        # file-absent bsl-shell page must not read like a no-data-function
        # page (and vice versa).
        if page.id in no_bsl_ids:
            assert "no data function registered" in card.text
        else:
            assert "backing file not found" in card.text
    assert seen == shell_ids


# --------------------------------------------------------------------------- #
# Story 20.5 (CAP-7) — the 19 remaining pages
# --------------------------------------------------------------------------- #

_NEW_PAGE_LOADERS_NO_ARGS: dict[str, tuple] = {
    "cve-watcher": (
        dash_data.load_cve_watcher,
        ["conda_name", "severity", "since_days", "vuln_kev_affecting_current", "then_count", "now_count", "delta"],
    ),
    "version-downloads": (dash_data.load_version_downloads, ["conda_name", "version", "upload_date", "downloads"]),
    "release-cadence": (
        dash_data.load_release_cadence,
        ["conda_name", "trend_label", "release_count_30d", "release_count_90d", "release_count_365d"],
    ),
    "find-alternative": (
        dash_data.load_find_alternative,
        ["archived_name", "candidate_name", "adoption_stage", "similarity_score", "downloads_total"],
    ),
    "scan-project": (
        dash_data.load_scan_project,
        ["conda_name", "severity", "license_spdx", "fix_available", "scan_status", "finding_count"],
    ),
    "env-inspect": (
        dash_data.load_env_inspect,
        ["conda_name", "license_spdx", "non_permissive_flag", "vuln_critical", "vuln_high"],
    ),
    "distribution-breakdown": (
        dash_data.load_distribution_breakdown,
        ["conda_name", "facet", "bucket", "python_min_bump_status", "downloads_90d"],
    ),
    "export-purls": (dash_data.load_export_purls, ["artifact_name", "regenerated_at", "row_count"]),
    "mapping-gap": (
        dash_data.load_mapping_gap,
        ["conda_name", "classification", "match_source", "match_confidence", "gap_count"],
    ),
    "universe-sbom": (dash_data.load_universe_sbom, ["component_purl", "slice", "with_vulns_count"]),
    "inventory-match": (
        dash_data.load_inventory_match,
        ["conda_name", "bucket", "freshness_percentile", "match_confidence", "row_count"],
    ),
    "add-handoff": (dash_data.load_add_handoff, ["conda_name", "readiness", "license_blocker", "row_count"]),
    "library-futures": (
        dash_data.load_library_futures,
        ["package_name", "futures_tier", "py314_readiness", "futures_score"],
    ),
    "recommend-2027": (
        dash_data.load_recommend_2027,
        ["package_name", "futures_tier", "lts_status", "eol_date", "futures_score"],
    ),
    "lts-registry-gap": (
        dash_data.load_lts_registry_gap,
        ["product_name", "tier", "matched_conda_name", "candidate_count"],
    ),
    "cwe-seed-gap": (dash_data.load_cwe_seed_gap, ["cwe_id", "tier", "suggested_category", "package_impact_count"]),
    "spdx-schema-gap": (dash_data.load_spdx_schema_gap, ["license_id", "tier", "package_usage_count"]),
    "license-map-gap": (dash_data.load_license_map_gap, ["license_raw", "tier", "suggested_spdx", "package_count"]),
    "identity-catalog": (
        dash_data.load_identity_catalog,
        [
            "P",
            "Rank",
            "Score",
            "Package",
            "Work",
            "Core_Python_Package_Name",
            "Platforms",
            "Apps",
            "Downloads",
            "Versions",
            "Vuln",
        ],
    ),
    "identity-ops-priority": (dash_data.load_identity_ops_priority, ["P", "Work", "package_count"]),
    "identity-ops-issues": (
        dash_data.load_identity_ops_issues,
        ["P", "has_open_issue", "package_count"],
    ),
    "identity-ops-builds": (
        dash_data.load_identity_ops_builds,
        ["Local_Build_Status", "package_count"],
    ),
    "identity-ops-census": (
        dash_data.load_identity_ops_census,
        ["has_feedstock", "has_staged_pr", "has_local_recipe", "package_count"],
    ),
    "bootstrap-index-health": (
        dash_data.load_bootstrap_index_health,
        ["catalog_entry", "tier", "regenerated_at", "row_count"],
    ),
    "identity-export-snapshot": (
        dash_data.load_identity_export_snapshot,
        [
            "identity_source",
            "package_count",
            "primary_purl_coverage_count",
            "openteams_issue_url_coverage_count",
        ],
    ),
    "live-catalog-coverage": (
        dash_data.load_live_catalog_coverage,
        ["field_name", "true_count", "total_count"],
    ),
}


# Reviewer-MEDIUM: the (dimensions, measures) each new loader REQUESTS, paired with the
# `build_*_model` it queries against — proven, below, to be a SUBSET of what that model
# actually DECLARES (via `SemanticModel.dimensions`/`.measures`), never just cross-checked
# against a second hand-written list in this test file. A naming drift (typo, rename) in
# either data.py or models.py would otherwise ship green today and only surface as an
# uncaught `boring_semantic_layer.UnknownFieldError` at real-data time.
_NEW_MODEL_SCHEMAS: dict[str, tuple] = {
    "cve-watcher": (
        models.build_vuln_history_model,
        ["conda_name", "severity", "since_days", "vuln_kev_affecting_current"],
        ["then_count", "now_count", "delta"],
    ),
    "version-downloads": (
        models.build_version_downloads_model,
        ["conda_name", "version", "upload_date"],
        ["downloads"],
    ),
    "release-cadence": (
        models.build_release_cadence_model,
        ["conda_name", "trend_label"],
        ["release_count_30d", "release_count_90d", "release_count_365d"],
    ),
    "find-alternative": (
        models.build_alternative_candidates_model,
        ["archived_name", "candidate_name", "adoption_stage"],
        ["similarity_score", "downloads_total"],
    ),
    "scan-project": (
        models.build_scan_result_model,
        ["conda_name", "severity", "license_spdx", "fix_available", "scan_status"],
        ["finding_count"],
    ),
    "env-inspect": (
        models.build_env_inspect_model,
        ["conda_name", "license_spdx", "non_permissive_flag"],
        ["vuln_critical", "vuln_high"],
    ),
    "distribution-breakdown": (
        models.build_distribution_breakdown_model,
        ["conda_name", "facet", "bucket", "python_min_bump_status"],
        ["downloads_90d"],
    ),
    "export-purls": (
        models.build_purl_export_model,
        ["artifact_name", "regenerated_at"],
        ["row_count"],
    ),
    "mapping-gap": (
        models.build_mapping_gap_model,
        ["conda_name", "classification", "match_source", "match_confidence"],
        ["gap_count"],
    ),
    "universe-sbom": (
        models.build_universe_sbom_summary_model,
        ["component_purl", "slice"],
        ["with_vulns_count"],
    ),
    "inventory-match": (
        models.build_inventory_match_report_model,
        ["conda_name", "bucket", "freshness_percentile", "match_confidence"],
        ["row_count"],
    ),
    "add-handoff": (
        models.build_add_handoff_report_model,
        ["conda_name", "readiness", "license_blocker"],
        ["row_count"],
    ),
    "library-futures": (
        models.build_library_futures_report_model,
        ["package_name", "futures_tier", "py314_readiness"],
        ["futures_score"],
    ),
    "recommend-2027": (
        models.build_recommend_2027_model,
        ["package_name", "futures_tier", "lts_status", "eol_date"],
        ["futures_score"],
    ),
    "lts-registry-gap": (
        models.build_lts_registry_gap_model,
        ["product_name", "tier", "matched_conda_name"],
        ["candidate_count"],
    ),
    "cwe-seed-gap": (
        models.build_cwe_seed_gap_model,
        ["cwe_id", "tier", "suggested_category"],
        ["package_impact_count"],
    ),
    "spdx-schema-gap": (
        models.build_spdx_schema_gap_model,
        ["license_id", "tier"],
        ["package_usage_count"],
    ),
    "license-map-gap": (
        models.build_license_map_gap_model,
        ["license_raw", "tier", "suggested_spdx"],
        ["package_count"],
    ),
    "identity-catalog": (
        models.build_identity_catalog_model,
        [
            "P",
            "Rank",
            "Score",
            "Package",
            "Work",
            "Core_Python_Package_Name",
            "Platforms",
            "Apps",
            "Downloads",
            "Versions",
            "Vuln",
        ],
        [],
    ),
    "identity-ops-priority": (
        models.build_identity_ops_model,
        ["P", "Work"],
        ["package_count"],
    ),
    "identity-ops-issues": (
        models.build_identity_ops_model,
        ["P", "has_open_issue"],
        ["package_count"],
    ),
    "identity-ops-builds": (
        models.build_identity_ops_model,
        ["Local_Build_Status"],
        ["package_count"],
    ),
    "identity-ops-census": (
        models.build_identity_ops_model,
        ["has_feedstock", "has_staged_pr", "has_local_recipe"],
        ["package_count"],
    ),
    "identity-workbook": (
        models.build_identity_workbook_model,
        ["match_bucket"],
        ["package_count", "artifactory_downloads_total"],
    ),
    "bootstrap-index-health": (
        models.build_bootstrap_index_health_model,
        ["catalog_entry", "tier", "regenerated_at"],
        ["row_count"],
    ),
    "identity-export-snapshot": (
        models.build_identity_export_snapshot_model,
        ["identity_source"],
        [
            "package_count",
            "primary_purl_coverage_count",
            "openteams_issue_url_coverage_count",
        ],
    ),
    "live-catalog-coverage": (
        models.build_live_catalog_coverage_model,
        ["field_name"],
        ["true_count", "total_count"],
    ),
}


def test_new_page_loaders_request_only_dimensions_measures_the_model_declares():
    """Reviewer-MEDIUM regression: introspect each new `build_*_model`'s OWN declared
    schema (`SemanticModel.dimensions`/`.measures` — construction is lazy, so this needs
    no real Parquet fixture, just a placeholder Ibis table) and assert the loader's
    requested dimension/measure names are a SUBSET of it. Catches a naming drift between
    data.py's loader and models.py's model declaration that the offline-empty-frame test
    below cannot (it only compares against a second hand-written column list)."""
    placeholder = ibis.table({"_unused": "string"}, name="placeholder")
    for page_id, (build_model, dimensions, measures) in _NEW_MODEL_SCHEMAS.items():
        model = build_model(placeholder)
        declared_dims = set(model.dimensions)
        declared_measures = set(model.measures)
        missing_dims = set(dimensions) - declared_dims
        missing_measures = set(measures) - declared_measures
        assert not missing_dims, f"{page_id}: loader requests undeclared dimension(s) {missing_dims}"
        assert not missing_measures, f"{page_id}: loader requests undeclared measure(s) {missing_measures}"


def test_new_pages_offline_return_empty_typed_frames_not_fabricated():
    """Story 20.5 (CAP-7): every one of the 19 new pages' loaders (except
    adoption-stage, exercised by ``test_adoption_stage_reuses_packages_model``
    below) degrades to an empty frame with exactly its declared columns when the
    backing Parquet is absent — NO fabricated rows, mirroring
    ``test_data_loaders_offline_return_empty_typed_frames_not_fabricated`` above."""
    for page_id, (loader, columns) in _NEW_PAGE_LOADERS_NO_ARGS.items():
        got = loader("/nope.parquet")
        assert got.empty, page_id
        assert list(got.columns) == columns, page_id


def test_adoption_stage_reuses_packages_model(packages_parquet):
    """`adoption-stage` re-uses build_packages_model (AC-2-style reuse, no new
    model) — its loader's output equals an independent query, and it degrades
    honestly like the other packages-backed shells."""
    empty = dash_data.load_adoption_stage("/nope.parquet", now=NOW)
    assert empty.empty and list(empty.columns) == ["conda_name", "adoption_stage", "package_count"]

    got = dash_data.load_adoption_stage(packages_parquet, now=NOW)
    table = models.duckdb_table_from_parquet(packages_parquet)
    expected = (
        models.build_packages_model(table, now_unix=NOW)
        .query(dimensions=["conda_name", "adoption_stage"], measures=["package_count"])
        .execute()
    )
    pd.testing.assert_frame_equal(
        got.sort_values("conda_name").reset_index(drop=True),
        expected.sort_values("conda_name").reset_index(drop=True),
    )


def test_release_cadence_trend_label_is_bsl_driven(write_parquet):
    """`release-cadence`'s loader output equals an independent
    build_release_cadence_model query — proving genuine BSL routing (AD-8) for the
    metrics.release_trend_label classifier (release_cadence.py::_classify, ported)."""
    path = write_parquet(
        pd.DataFrame(
            {
                "conda_name": ["a", "b", "c", "d"],
                "releases_30d": pd.array([5, 0, 0, 0], dtype="Int64"),
                "releases_90d": pd.array([6, 0, 0, 2], dtype="Int64"),
                "releases_365d": pd.array([10, 0, 1, 2], dtype="Int64"),
            }
        ),
        "release_cadence",
    )
    got = dash_data.load_release_cadence(path)
    table = models.duckdb_table_from_parquet(path)
    expected = (
        models.build_release_cadence_model(table)
        .query(
            dimensions=["conda_name", "trend_label"],
            measures=["release_count_30d", "release_count_90d", "release_count_365d"],
        )
        .execute()
    )
    pd.testing.assert_frame_equal(
        got.sort_values("conda_name").reset_index(drop=True),
        expected.sort_values("conda_name").reset_index(drop=True),
    )
    label = dict(zip(got["conda_name"], got["trend_label"]))
    assert label == {"a": "accelerating", "b": "silent", "c": "one-version", "d": "decelerating"}


def test_distribution_breakdown_bump_status_is_bsl_driven(write_parquet):
    """`distribution-breakdown`'s python-version facet bump-safety classifier
    (metrics.python_min_bump_status, ported from pyver_breakdown.py::policy_check_status)
    is genuinely BSL-driven, proven against an independent model query."""
    path = write_parquet(
        pd.DataFrame(
            {
                "conda_name": ["a", "b", "c", "d"],
                "facet": ["python-version"] * 4,
                "bucket": ["3.9", "3.10", "3.11", "3.9"],
                "declared_python_min": ["3.9", "3.9", "3.11", None],
                "empirical_floor": ["3.11", "3.9", "3.9", "3.9"],
                "downloads_90d": pd.array([100, 200, 300, 400], dtype="Int64"),
            }
        ),
        "distribution_breakdown",
    )
    got = dash_data.load_distribution_breakdown(path)
    table = models.duckdb_table_from_parquet(path)
    expected = (
        models.build_distribution_breakdown_model(table)
        .query(
            dimensions=["conda_name", "facet", "bucket", "python_min_bump_status"],
            measures=["downloads_90d"],
        )
        .execute()
    )
    pd.testing.assert_frame_equal(
        got.sort_values("conda_name").reset_index(drop=True),
        expected.sort_values("conda_name").reset_index(drop=True),
    )
    status = dict(zip(got["conda_name"], got["python_min_bump_status"]))
    assert status == {"a": "bump-safe", "b": "aligned", "c": "aggressive", "d": "unknown"}


def test_distribution_breakdown_bump_status_degrades_on_malformed_non_null_value(write_parquet):
    """Reviewer-HIGH regression: a MALFORMED but non-NULL declared_python_min/
    empirical_floor (e.g. "garbage" or "3.9.1" — doesn't match ``3\\.(\\d+)``)
    must degrade to "unknown", not raise. On the DuckDB backend a regex MISS
    extracts to an empty string, not NULL, and CAST('' AS INT64) raises
    duckdb.ConversionException — a different exception than the TypeError
    _bsl_query_or_empty degrades on, so this must be handled INSIDE
    metrics._python_minor (the .nullif("") fix), never rely on the outer seam."""
    path = write_parquet(
        pd.DataFrame(
            {
                "conda_name": ["a", "b", "c"],
                "facet": ["python-version"] * 3,
                "bucket": ["3.9", "3.9", "3.9"],
                "declared_python_min": ["garbage", "3.9.1", "3.9"],
                "empirical_floor": ["3.9", "3.9", "py39"],
                "downloads_90d": pd.array([10, 20, 30], dtype="Int64"),
            }
        ),
        "distribution_breakdown",
    )
    got = dash_data.load_distribution_breakdown(path)
    assert not got.empty
    status = dict(zip(got["conda_name"], got["python_min_bump_status"]))
    assert status == {"a": "unknown", "b": "unknown", "c": "unknown"}


def test_bootstrap_index_health_is_bsl_wired_and_light_up_with_data(write_parquet):
    """Story 21.9 — `bootstrap-index-health` loader equals build_bootstrap_index_health_model."""
    path = write_parquet(
        pd.DataFrame(
            {
                "catalog_entry": ["core_packages_enumerated", "pypi_universe"],
                "tier": ["0", "0"],
                "regenerated_at": ["2026-08-30T12:00:00Z", "2026-08-30T12:00:00Z"],
                "row_count": pd.array([30000, 500000], dtype="Int64"),
            }
        ),
        "bootstrap_index_health",
    )
    got = dash_data.load_bootstrap_index_health(path)
    table = models.duckdb_table_from_parquet(path)
    expected = (
        models.build_bootstrap_index_health_model(table)
        .query(
            dimensions=["catalog_entry", "tier", "regenerated_at"],
            measures=["row_count"],
        )
        .execute()
    )
    pd.testing.assert_frame_equal(
        got.sort_values("catalog_entry").reset_index(drop=True),
        expected.sort_values("catalog_entry").reset_index(drop=True),
    )


def test_identity_export_snapshot_is_bsl_wired_and_light_up_with_data(write_parquet):
    """Story 21.9 — `identity-export-snapshot` loader equals build_identity_export_snapshot_model."""
    path = write_parquet(
        pd.DataFrame(
            {
                "Core_Python_Package_Name": ["a", "b", "c"],
                "identity_source": ["from_assoc", "from_inventory", "from_board_only"],
                "primary_purl": ["pkg:pypi/a", "", "pkg:pypi/c"],
                "OpenTeams_Issue_URL": ["https://github.com/o/i/1", "", ""],
            }
        ),
        "identity_export_snapshot",
    )
    got = dash_data.load_identity_export_snapshot(path)
    table = models.duckdb_table_from_parquet(path)
    expected = (
        models.build_identity_export_snapshot_model(table)
        .query(
            dimensions=["identity_source"],
            measures=[
                "package_count",
                "primary_purl_coverage_count",
                "openteams_issue_url_coverage_count",
            ],
        )
        .execute()
    )
    pd.testing.assert_frame_equal(
        got.sort_values("identity_source").reset_index(drop=True),
        expected.sort_values("identity_source").reset_index(drop=True),
    )


def test_live_catalog_coverage_is_bsl_wired_and_light_up_with_data(write_parquet):
    """Story 21.9 — `live-catalog-coverage` loader equals build_live_catalog_coverage_model."""
    path = write_parquet(
        pd.DataFrame(
            {
                "field_name": ["PyPI_Verified", "CondaForge_Verified"],
                "true_count": pd.array([800, 600], dtype="Int64"),
                "total_count": pd.array([1000, 1000], dtype="Int64"),
            }
        ),
        "live_catalog_coverage",
    )
    got = dash_data.load_live_catalog_coverage(path)
    table = models.duckdb_table_from_parquet(path)
    expected = (
        models.build_live_catalog_coverage_model(table)
        .query(
            dimensions=["field_name"],
            measures=["true_count", "total_count"],
        )
        .execute()
    )
    pd.testing.assert_frame_equal(
        got.sort_values("field_name").reset_index(drop=True),
        expected.sort_values("field_name").reset_index(drop=True),
    )
