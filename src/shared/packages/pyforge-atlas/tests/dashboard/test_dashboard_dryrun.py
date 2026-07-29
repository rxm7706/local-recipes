"""`dashboard-dryrun` gate (Story D2, FR-9, AD-8/AD-17, NFR-8) — BUILD OBJECT ONLY.

Structural, OFFLINE gate mirroring the C1 ``dagster-dryrun`` / C2 ``viz-loadable`` pattern:
it builds the BSL-driven Vizro ``Dashboard`` object and asserts the D2 acceptance criteria
that ARE buildable now (the full 28-page inventory + per-page design is CIS-two-spine
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

import pandas as pd
import pytest
import vizro.models as vm
from vizro import Vizro
from vizro.managers import data_manager

from pyforge.atlas.dashboard import app
from pyforge.atlas.dashboard import data as dash_data
from pyforge.atlas.dashboard import factory_status as fs
from pyforge.atlas.semantic import models

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


# --------------------------------------------------------------------------- #
# AD-8 — pages are BSL-driven (loaders route through the semantic models)
# --------------------------------------------------------------------------- #


def test_feedstock_health_page_is_bsl_driven(feedstock_health_parquet):
    """The loader's output EQUALS an independent build_feedstock_health_model query —
    proving the page data flows through the BSL model, not a re-implemented metric (AD-8)."""
    got = dash_data.load_feedstock_health(feedstock_health_parquet)
    table = models.duckdb_table_from_parquet(feedstock_health_parquet)
    expected = (
        models.build_feedstock_health_model(table)
        .query(dimensions=["feedstock_name", "ci_red", "has_open_prs", "has_open_issues"])
        .execute()
    )
    pd.testing.assert_frame_equal(
        got.sort_values("feedstock_name").reset_index(drop=True),
        expected.sort_values("feedstock_name").reset_index(drop=True),
    )
    # sanity: the BSL ci_red domain actually fired (failure/error → True, success → False).
    red = dict(zip(got["feedstock_name"], got["ci_red"]))
    assert red == {"alpha": True, "beta": False, "gamma": True}


def test_my_feedstocks_page_is_bsl_driven(package_maintainers_parquet):
    got = dash_data.load_my_feedstocks(package_maintainers_parquet)
    table = models.duckdb_table_from_parquet(package_maintainers_parquet)
    expected = (
        models.build_package_maintainers_model(table)
        .query(dimensions=["maintainer", "conda_name"])
        .execute()
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
    expected = (
        models.build_packages_model(table, now_unix=NOW)
        .query(dimensions=["conda_name", "staleness_age_days", "adoption_stage"])
        .execute()
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


def test_present_but_untyped_parquet_degrades_not_crash(write_parquet):
    """Reviewer-B S2: a PRESENT but degenerate store — a 0-row packages Parquet whose
    columns round-trip untyped (all-null object) — makes a metric predicate like
    `latest_status.fill_null("active")` raise IbisTypeError. The loader must degrade to the
    declared-column empty frame, never crash the page build."""
    import pandas as pd

    # 0-row, object-typed columns (no pyarrow schema) → the crash the migration's typed
    # schemas avoid, but a first sparse store could hit.
    untyped = pd.DataFrame(
        {c: pd.Series([], dtype="object") for c in
         ("conda_name", "latest_status", "feedstock_archived", "latest_conda_upload",
          "downloads_total", "downloads_30d", "latest_upload_age_days", "releases_30d", "total_versions")}
    )
    path = write_parquet(untyped, "untyped_packages")
    st = dash_data.load_staleness(path, now=NOW)
    assert st.empty and list(st.columns) == ["conda_name", "staleness_age_days", "adoption_stage"]


def test_registered_data_functions_are_callable_and_return_frames(dashboard):
    """Every data/factory page registers a lazy data function that returns a DataFrame
    offline (empty here — no data root); the no-bsl shells register NO data function
    (no fabrication)."""
    for page in app.PAGE_INVENTORY:
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
    frame = fs.build_factory_status_frame(build_stamp=STAMP)
    sprint = frame[frame["source"] == "sprint-status.yaml"]
    keyed = dict(zip(sprint["key"], sprint["status"]))
    # D1/D2 are real stories in the live sprint feed.
    assert "d1-define-the-boring-semantic-layer-bsl-models" in keyed
    assert "d2-build-the-vizro-dashboard-port-the-28-clis-to-pages" in keyed
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
    non-factory page (the 3 bsl-shell + 2 no-bsl-shell pages) honestly states
    its OWN data as "unavailable" + `AD-17` — never a fabricated stamp, never
    the dashboard's render time standing in for it."""
    shell_ids = {
        "staleness-report",
        "query-atlas",
        "detail-cf-atlas",
        "behind-upstream",
        "whodepends",
    }
    no_bsl_ids = {"behind-upstream", "whodepends"}
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
