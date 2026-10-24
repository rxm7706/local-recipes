"""Story 37.4 (spec-pyforge-atlas CAP-69): behind-upstream, whodepends, live-catalog coverage and the
universe SBOM boards fill, behind ``pyforge.atlas.board_projections``. Story 37.5 adds the cve-watcher,
which reads the vulnerability pipeline's diff of two snapshots under the same flag.

The three ``derived_artifacts`` projections, the two new models, the loaders on frames shaped like the
produced datasets, and the page set each flag state builds. Pure; no network.
"""

from __future__ import annotations

import dataclasses
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest
from pyforge.testing_kit.flags import flagd_tree
from vizro.managers import data_manager

from pyforge.atlas import provenance
from pyforge.atlas.dashboard import app, data, static_export
from pyforge.atlas.pipelines.catalog_index.nodes import report_catalog_index_health
from pyforge.atlas.pipelines.derived_artifacts.alternatives import score_alternative_candidates
from pyforge.atlas.pipelines.derived_artifacts.lifecycle import project_version_downloads
from pyforge.atlas.pipelines.derived_artifacts.nodes import (
    BEHIND_UPSTREAM_COLUMNS,
    LIVE_CATALOG_COVERAGE_FIELDS,
    classify_lag,
    project_behind_upstream,
    project_live_catalog_coverage,
    project_universe_sbom_summary,
)
from pyforge.atlas.pipelines.derived_artifacts.purl_exports import export_purl_artifacts
from pyforge.atlas.pipelines.derived_artifacts.release_cadence import project_release_cadence
from pyforge.atlas.pipelines.pypi_intelligence.nodes import classify_mapping_gap
from pyforge.atlas.pipelines.vulnerability.nodes import diff_vulnerability_snapshots, snapshot_vulnerability_rollup

FLAG = "pyforge.atlas.board_projections"
REPO_ROOT = Path(__file__).resolve().parents[6]
FLAGS = REPO_ROOT / "src" / "platform" / "config" / "flags.json"
OVERLAYS = REPO_ROOT / "src" / "platform" / "config" / "flag-overlays.json"
PROJECTED = (
    "behind-upstream",
    "whodepends",
    "universe-sbom",
    "live-catalog-coverage",
    "cve-watcher",
    "mapping-gap",
    "bootstrap-index-health",
    "export-purls",
    "find-alternative",
    "release-cadence",
    "version-downloads",
)
NOW = 1_700_000_000
STAMP = "2026-10-22T00:00:00Z"


def _write(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    return path


def _upstream(rows: list[tuple[str, str, str | None, str | None]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["conda_name", "host", "upstream_version", "last_error"])


def _enumerated(rows: list[tuple[str, str | None]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["conda_name", "latest_version"])


# --------------------------------------------------------------------------- #
# The flag
# --------------------------------------------------------------------------- #


def test_the_flag_is_in_the_tree_off_by_default_and_on_only_in_dev() -> None:
    entry = json.loads(FLAGS.read_text(encoding="utf-8"))["flags"][FLAG]
    assert entry["defaultVariant"] == "off"
    assert entry["variants"] == {"on": True, "off": False}
    assert entry["metadata"]["owner"] == "atlas"
    assert (
        entry["metadata"]["story"]
        == "37-4-behind-upstream-whodepends-live-catalog-coverage-and-the-universe-sbom-boards-fill"
    )
    overlays = json.loads(OVERLAYS.read_text(encoding="utf-8"))
    assert {env: overlays[env][FLAG] for env in ("dev", "staging", "production")} == {
        "dev": "on",
        "staging": "off",
        "production": "off",
    }
    assert data.BOARD_PROJECTIONS_FLAG == FLAG


def test_the_reader_follows_the_tree(tmp_path: Path, real_board_projections) -> None:
    on = flagd_tree(tmp_path, {FLAG: "on"}, name="on.json")
    off = flagd_tree(tmp_path, {FLAG: "off"}, name="off.json")
    assert real_board_projections(flags_path=str(on)) is True
    assert real_board_projections(flags_path=str(off)) is False
    assert real_board_projections(flags_path=str(tmp_path / "missing.json")) is False


def test_the_page_set_swaps_the_four_boards_only_with_the_flag_on() -> None:
    off = {page.id: page for page in app.page_inventory(projected=False)}
    on = {page.id: page for page in app.page_inventory(projected=True)}

    assert app.page_inventory(projected=False) == app.PAGE_INVENTORY
    assert [page.id for page in app.page_inventory(projected=True)] == [page.id for page in app.PAGE_INVENTORY]
    assert {off[pid].kind for pid in ("behind-upstream", "whodepends")} == {"no-bsl-shell"}
    # Story 37.8: export-purls keeps its report-artifact kind; every other projected board is a BSL shell
    assert {on[pid].kind for pid in PROJECTED if pid != "export-purls"} == {"bsl-shell"}
    assert on["export-purls"].kind == off["export-purls"].kind == "report-artifact"
    assert on["universe-sbom"].filters == off["universe-sbom"].filters == ("slice",)
    assert {pid for pid in on if on[pid] != off[pid]} == set(PROJECTED)


def test_the_page_set_reads_the_flag_when_not_told(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(data, "board_projections", lambda **_: True)
    assert app.page_inventory()[0] is app.PAGE_INVENTORY[0]
    assert {page.id: page.kind for page in app.page_inventory()}["whodepends"] == "bsl-shell"


# --------------------------------------------------------------------------- #
# Behind-upstream: legacy's lag labels, one upstream per package
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("conda", "upstream", "label"),
    [
        ("1.1.9", "1.2.0", "minor"),
        ("1.9", "2.0", "major"),
        ("1.0.0", "1.0.1", "patch"),
        ("1.0", "1.0", "current"),
        ("2.0", "1.9", "current"),
        ("1.0", "1.0.0", "current"),
        ("1.0", "not-a-version", "unknown"),
        (None, "1.0", "unknown"),
        ("1.0", "", "unknown"),
        ("3", "3.1", "patch"),  # one release segment: no minor to compare, as legacy
    ],
)
def test_the_lag_label_is_legacys(conda, upstream, label) -> None:
    assert classify_lag(conda, upstream) == label


def test_behind_upstream_keeps_the_newer_upstream_in_host_order() -> None:
    upstream = _upstream(
        [
            ("a", "gitlab", "3.0", None),
            ("a", "github", "1.2", None),  # GitHub wins over GitLab
            ("b", "codeberg", "2.0", None),
            ("c", "github", "1.0", None),  # current: left out
            ("d", "github", "9.9", "HTTP 404"),  # an error: skipped, GitLab's version used
            ("d", "gitlab", "1.5", None),
            ("e", "github", None, None),  # no version: left out
            ("x", "github", "5.0", None),  # not enumerated: left out
            ("f", "pypi", "9.0", None),  # not a VCS host: left out
        ]
    )
    enumerated = _enumerated([("a", "1.1"), ("b", "1.0"), ("c", "1.0"), ("d", "1.0"), ("e", "1.0"), ("f", "1.0")])

    out = project_behind_upstream(upstream, enumerated)

    assert list(out.columns) == list(BEHIND_UPSTREAM_COLUMNS)
    assert out.values.tolist() == [
        ["a", "1.1", "github", "1.2", "minor"],
        ["b", "1.0", "codeberg", "2.0", "major"],
        ["d", "1.0", "gitlab", "1.5", "minor"],
    ]


def test_behind_upstream_keeps_an_upstream_that_does_not_parse_as_unknown() -> None:
    # legacy keeps these rows (priority 1); a tag such as bzip2-1.0.8 is not PEP 440
    out = project_behind_upstream(
        _upstream([("bzip2", "gitlab", "bzip2-1.0.8", None)]), _enumerated([("bzip2", "1.0.8")])
    )
    assert out.values.tolist() == [["bzip2", "1.0.8", "gitlab", "bzip2-1.0.8", "unknown"]]


def test_behind_upstream_leaves_out_a_package_with_no_latest_version() -> None:
    out = project_behind_upstream(_upstream([("a", "github", "2.0", None)]), _enumerated([("a", None)]))
    assert out.empty


def test_behind_upstream_reads_a_store_without_last_error() -> None:
    upstream = pd.DataFrame({"conda_name": ["a"], "host": ["github"], "upstream_version": ["2.0"]})
    out = project_behind_upstream(upstream, _enumerated([("a", "1.0")]))
    assert out["lag_label"].tolist() == ["major"]


@pytest.mark.parametrize(
    ("upstream", "enumerated"),
    [
        (None, None),
        (pd.DataFrame(), _enumerated([("a", "1.0")])),
        (_upstream([("a", "github", "2.0", None)]), pd.DataFrame({"conda_name": ["a"]})),
        (pd.DataFrame({"x": [1]}), _enumerated([("a", "1.0")])),
        (_upstream([("a", "github", "1.0", None)]), _enumerated([("a", "1.0")])),  # every package current
    ],
)
def test_behind_upstream_is_a_typed_empty_table_otherwise(upstream, enumerated) -> None:
    out = project_behind_upstream(upstream, enumerated)
    assert out.empty and list(out.columns) == list(BEHIND_UPSTREAM_COLUMNS)
    assert all(str(dtype) == "string" for dtype in out.dtypes)


# --------------------------------------------------------------------------- #
# Live-catalog coverage: one row per inventory flag
# --------------------------------------------------------------------------- #


def test_coverage_counts_each_flag_over_the_exports_rows() -> None:
    export = pd.DataFrame(
        {
            "PyPI_Verified": ["Yes", "No", None],
            "CondaForge_Verified": ["Yes", "Yes", "No"],
            "in_basilisk": [True, False, True],
            "in_fedora": [False, False, False],
            "Package": ["a", "b", "c"],
        }
    )

    out = project_live_catalog_coverage(export)

    assert out.values.tolist() == [
        ["PyPI_Verified", 1, 3],
        ["CondaForge_Verified", 2, 3],
        ["in_basilisk", 2, 3],
        ["in_fedora", 0, 3],
    ]
    assert str(out["true_count"].dtype) == "Int64" and str(out["field_name"].dtype) == "string"


def test_coverage_names_the_two_verified_flags_and_the_fifteen_channel_flags() -> None:
    assert LIVE_CATALOG_COVERAGE_FIELDS[:2] == ("PyPI_Verified", "CondaForge_Verified")
    assert len(LIVE_CATALOG_COVERAGE_FIELDS) == 17
    assert all(name.startswith("in_") for name in LIVE_CATALOG_COVERAGE_FIELDS[2:])


@pytest.mark.parametrize(
    "export",
    [
        None,
        pd.DataFrame(),
        pd.DataFrame({"Package": ["a"]}),
        "not a frame",
        pd.DataFrame(columns=["Package", *LIVE_CATALOG_COVERAGE_FIELDS]),  # a run's real empty export
    ],
)
def test_coverage_is_a_typed_empty_table_otherwise(export) -> None:
    out = project_live_catalog_coverage(export)
    assert out.empty and list(out.columns) == ["field_name", "true_count", "total_count"]
    assert str(out["total_count"].dtype) == "Int64"


# --------------------------------------------------------------------------- #
# Universe SBOM summary: one row per component
# --------------------------------------------------------------------------- #


def test_the_sbom_summary_slices_mapped_and_unmapped_components() -> None:
    bom = {
        "components": [
            {"purl": "pkg:conda/conda-forge/a@1.0", "properties": [{"name": "cfe:pypi_name", "value": "a"}]},
            {"purl": "pkg:conda/conda-forge/b@2.0"},
            {"purl": "pkg:conda/conda-forge/c@3.0", "properties": [{"name": "cfe:pypi_name", "value": ""}]},
            {"purl": "pkg:conda/conda-forge/d@4.0", "properties": [{"name": "other", "value": "x"}]},
            {"name": "no-purl"},
            "not a component",
        ]
    }

    out = project_universe_sbom_summary(bom)

    assert out[["component_purl", "slice"]].values.tolist() == [
        ["pkg:conda/conda-forge/a@1.0", "mapped"],
        ["pkg:conda/conda-forge/b@2.0", "unmapped"],
        ["pkg:conda/conda-forge/c@3.0", "unmapped"],
        ["pkg:conda/conda-forge/d@4.0", "unmapped"],
    ]
    assert out["with_vulns_count"].isna().all() and str(out["with_vulns_count"].dtype) == "Int64"


@pytest.mark.parametrize("bom", [None, {}, {"components": "x"}, {"components": []}, [], {"components": [{}]}])
def test_the_sbom_summary_is_a_typed_empty_table_otherwise(bom) -> None:
    out = project_universe_sbom_summary(bom)
    assert out.empty and list(out.columns) == ["component_purl", "slice", "with_vulns_count"]
    assert str(out["slice"].dtype) == "string"


# --------------------------------------------------------------------------- #
# The loaders over the produced datasets
# --------------------------------------------------------------------------- #


def test_the_behind_upstream_board_reads_the_projection(tmp_path: Path) -> None:
    frame = project_behind_upstream(
        _upstream([("a", "github", "2.0", None), ("b", "gitlab", "1.1", None)]),
        _enumerated([("a", "1.0"), ("b", "1.0")]),
    )

    out = data.load_behind_upstream(_write(tmp_path / "b.parquet", frame)).sort_values("conda_name")

    assert out[["conda_name", "lag_label", "package_count"]].values.tolist() == [["a", "major", 1], ["b", "minor", 1]]


def test_the_whodepends_board_counts_each_packages_dependents(tmp_path: Path) -> None:
    # core_dependencies: conda_name depends on depends_on (build_dependency_graph's columns)
    frame = pd.DataFrame(
        {
            "conda_name": ["a", "b", "b", "c"],
            "depends_on": ["numpy", "numpy", "numpy", "numpy"],
            "dep_type": ["run", "run", "run", "host"],
        }
    )

    out = data.load_whodepends(_write(tmp_path / "d.parquet", frame)).sort_values("dep_type")

    assert out.values.tolist() == [["numpy", "host", 1], ["numpy", "run", 2]]


def test_the_coverage_board_reads_the_projection(tmp_path: Path) -> None:
    frame = project_live_catalog_coverage(pd.DataFrame({"PyPI_Verified": ["Yes", "No"], "in_spack": [True, True]}))

    out = data.load_live_catalog_coverage(_write(tmp_path / "c.parquet", frame)).sort_values("field_name")

    assert out.values.tolist() == [["PyPI_Verified", 1, 2], ["in_spack", 2, 2]]


def test_the_sbom_board_reads_the_projection(tmp_path: Path) -> None:
    frame = project_universe_sbom_summary({"components": [{"purl": "pkg:conda/conda-forge/a@1.0"}]})

    out = data.load_universe_sbom(_write(tmp_path / "s.parquet", frame))

    assert out[["component_purl", "slice"]].values.tolist() == [["pkg:conda/conda-forge/a@1.0", "unmapped"]]


@pytest.mark.parametrize(
    ("loader", "frame"),
    [
        (data.load_behind_upstream, project_behind_upstream(None, None)),
        (data.load_live_catalog_coverage, project_live_catalog_coverage(None)),
        (data.load_universe_sbom, project_universe_sbom_summary(None)),
    ],
)
def test_each_board_reads_its_typed_empty_projection(tmp_path: Path, loader, frame) -> None:
    out = loader(_write(tmp_path / "e.parquet", frame))
    assert out.empty


# --------------------------------------------------------------------------- #
# The dashboard each flag state builds
# --------------------------------------------------------------------------- #


def _data_root(tmp_path: Path) -> Path:
    root = tmp_path / "data"
    _write(
        root / data.BEHIND_UPSTREAM_PARQUET,
        project_behind_upstream(_upstream([("a", "github", "2.0", None)]), _enumerated([("a", "1.0")])),
    )
    _write(
        root / data.CORE_DEPENDENCIES_PARQUET,
        pd.DataFrame({"conda_name": ["a"], "depends_on": ["numpy"], "dep_type": ["run"]}),
    )
    _write(
        root / data.DERIVED_LIVE_CATALOG_COVERAGE_PARQUET,
        project_live_catalog_coverage(pd.DataFrame({"PyPI_Verified": ["Yes"]})),
    )
    _write(
        root / data.DERIVED_UNIVERSE_SBOM_SUMMARY_PARQUET,
        project_universe_sbom_summary({"components": [{"purl": "pkg:conda/conda-forge/a@1.0"}]}),
    )
    # Story 37.5: two snapshots of a one-package rollup whose total moved
    snapshots = pd.concat(
        [
            snapshot_vulnerability_rollup(
                pd.DataFrame({"package_name": ["a"], "vuln_count": [count], "vuln_critical_high": [0]}), now=stamp
            )
            for stamp, count in ((0, 1), (10 * 86_400, 2))
        ],
        ignore_index=True,
    )
    _write(root / data.DERIVED_VULN_HISTORY_PARQUET, diff_vulnerability_snapshots(snapshots, 7))
    # Story 37.9: one enumerated package with no PyPI name
    _write(
        root / data.DERIVED_MAPPING_GAP_PARQUET,
        classify_mapping_gap(_enumerated([("a", "1.0")]), None, None, None, None, None),
    )
    # Story 37.10: one catalog entry's health
    _write(
        root / data.CATALOG_INDEX_HEALTH_PARQUET,
        report_catalog_index_health(
            pd.DataFrame(
                {
                    "catalog_entry": ["core_packages_enumerated"],
                    "layer": ["intermediate"],
                    "relpath": ["intermediate/x.parquet"],
                    "regenerated_at": [pd.Timestamp("2026-10-23T00:00:00Z")],
                    "row_count": [40000],
                    "stale": [False],
                    "stale_reason": [None],
                }
            ),
            {"tiers": {"core_packages_enumerated": "Tier 0"}},
        ),
    )
    # Story 37.7: one archived package and the one active package that shares its summary
    _write(
        root / data.DERIVED_ALTERNATIVE_CANDIDATES_PARQUET,
        score_alternative_candidates(
            pd.DataFrame(
                {
                    "feedstock_name": ["old", "new"],
                    "conda_name": ["old", "new"],
                    "depends_on": [None, None],
                    "feedstock_archived": [True, False],
                    "summary": ["Parse yaml files", "Parse yaml quickly"],
                    "keywords": [[], []],
                }
            ),
            pd.DataFrame({"conda_name": ["old", "new"], "feedstock_name": ["old", "new"]}),
            pd.DataFrame({"conda_name": ["old", "new"], "latest_status": ["active", "active"]}),
            None,
            now=NOW,
        ),
    )
    # Story 38.1: one version's downloads with its upload date
    _write(
        root / data.DERIVED_VERSION_DOWNLOADS_PARQUET,
        project_version_downloads(
            pd.DataFrame({"conda_name": ["a"], "version": ["1.0"], "downloads": [5]}),
            pd.DataFrame({"conda_name": ["a"], "version": ["1.0"], "upload_unix": [NOW - 86_400]}),
        ),
    )
    # Story 37.6: one package with a version uploaded ten days before NOW
    _write(
        root / data.DERIVED_RELEASE_CADENCE_PARQUET,
        project_release_cadence(
            pd.DataFrame(
                {"conda_name": ["a"], "version": ["1.0"], "upload_unix": [NOW - 10 * 86_400], "file_count": [2]}
            ),
            _enumerated([("a", "1.0")]),
            now=NOW,
        ),
    )
    # Story 37.8: one active package's artifacts and their manifest
    _write(
        root / data.DERIVED_PURL_EXPORT_MANIFEST_PARQUET,
        export_purl_artifacts(_enumerated([("a", "1.0")]), None, None, None, None, None, None, now=NOW)[1],
    )
    return root


def _frame(page_id: str) -> pd.DataFrame | None:
    try:
        source = data_manager[f"data::{page_id}"]
    except KeyError:
        return None
    return source.load()


def test_with_the_flag_on_the_four_boards_read_their_datasets(tmp_path: Path) -> None:
    dashboard = app.build_dashboard(build_stamp=STAMP, data_root=_data_root(tmp_path), now=NOW, board_projections=True)

    assert {page.id for page in dashboard.pages} >= set(PROJECTED)
    rows = {"export-purls": 6}  # Story 37.8: one manifest row per artifact
    for page_id in PROJECTED:
        frame = _frame(page_id)
        assert frame is not None and len(frame) == rows.get(page_id, 1), page_id


def test_with_the_flag_off_the_four_boards_read_as_before(tmp_path: Path) -> None:
    app.build_dashboard(build_stamp=STAMP, data_root=_data_root(tmp_path), now=NOW, board_projections=False)

    assert _frame("behind-upstream") is None and _frame("whodepends") is None  # shells: no data function
    for page_id in (
        "universe-sbom",
        "live-catalog-coverage",
        "cve-watcher",
        "mapping-gap",
        "bootstrap-index-health",
        "export-purls",
        "find-alternative",
        "release-cadence",
        "version-downloads",
    ):
        frame = _frame(page_id)
        assert frame is not None and frame.empty, page_id  # the earlier paths, absent from this fixture


def test_with_the_flag_off_version_downloads_reads_the_history_with_no_date(tmp_path: Path) -> None:
    root = _data_root(tmp_path)
    _write(
        root / data.VERSION_DOWNLOADS_PARQUET, pd.DataFrame({"conda_name": ["a"], "version": ["1.0"], "downloads": [7]})
    )

    app.build_dashboard(build_stamp=STAMP, data_root=root, now=NOW, board_projections=False)

    frame = _frame("version-downloads")
    assert frame is not None and len(frame) == 1 and int(frame["downloads"].iloc[0]) == 7
    assert frame["upload_date"].isna().all()


def _card_text(dashboard, page_id: str) -> str:
    page = next(p for p in dashboard.pages if p.id == page_id)
    return next(c.text for c in page.components if hasattr(c, "text"))


def test_with_the_flag_on_each_board_is_stamped_from_the_file_it_reads(tmp_path: Path) -> None:
    root = _data_root(tmp_path)
    reads = {
        "behind-upstream": data.BEHIND_UPSTREAM_PARQUET,
        "whodepends": data.CORE_DEPENDENCIES_PARQUET,
        "universe-sbom": data.DERIVED_UNIVERSE_SBOM_SUMMARY_PARQUET,
        "live-catalog-coverage": data.DERIVED_LIVE_CATALOG_COVERAGE_PARQUET,
        "cve-watcher": data.DERIVED_VULN_HISTORY_PARQUET,
        "mapping-gap": data.DERIVED_MAPPING_GAP_PARQUET,
        "bootstrap-index-health": data.CATALOG_INDEX_HEALTH_PARQUET,
        "export-purls": data.DERIVED_PURL_EXPORT_MANIFEST_PARQUET,
        "find-alternative": data.DERIVED_ALTERNATIVE_CANDIDATES_PARQUET,
        "release-cadence": data.DERIVED_RELEASE_CADENCE_PARQUET,
        "version-downloads": data.DERIVED_VERSION_DOWNLOADS_PARQUET,
    }
    for offset, path in enumerate(reads.values()):  # a distinct mtime per file, so a swapped stamp shows
        stamp = 1_600_000_000 + offset * 86_400
        os.utime(root / path, (stamp, stamp))

    dashboard = app.build_dashboard(build_stamp=STAMP, data_root=root, now=NOW, board_projections=True)

    for page_id, path in reads.items():
        expected = provenance.resolve_for_file(root / path).build_stamp
        assert expected and expected in _card_text(dashboard, page_id), page_id


def test_find_alternative_classifies_its_candidates_on_the_boards_clock(tmp_path: Path) -> None:
    """Story 38.1 review 2: a candidate scored at 360 days old reads declining on a board built a week later, as the
    adoption-stage board reads the same package."""
    root = _data_root(tmp_path)
    candidates = pd.read_parquet(root / data.DERIVED_ALTERNATIVE_CANDIDATES_PARQUET).iloc[:1]
    candidates = candidates.assign(
        latest_conda_upload=pd.array([NOW - 360 * 86_400], dtype="Int64"),
        latest_upload_age_days=pd.array([360], dtype="Int64"),
        releases_30d=pd.array([0], dtype="Int64"),
        total_versions=pd.array([2], dtype="Int64"),
    )
    _write(root / data.DERIVED_ALTERNATIVE_CANDIDATES_PARQUET, candidates)

    app.build_dashboard(build_stamp=STAMP, data_root=root, now=NOW + 7 * 86_400, board_projections=True)

    assert _frame("find-alternative")["adoption_stage"].tolist() == ["declining"]


def test_the_dashboard_reads_the_flag_when_not_told(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(data, "board_projections", lambda **_: True)

    app.build_dashboard(build_stamp=STAMP, data_root=_data_root(tmp_path), now=NOW)

    assert _frame("behind-upstream") is not None and _frame("whodepends") is not None


@pytest.mark.parametrize(("variant", "table"), [("on", True), ("off", False)])
def test_the_static_export_reads_the_flag_from_the_tree_it_is_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, real_board_projections, variant: str, table: bool
) -> None:
    monkeypatch.setattr(data, "board_projections", real_board_projections)
    tree = flagd_tree(tmp_path, {FLAG: variant}, name=f"{variant}.json")

    static_export.export_boards(
        tmp_path / "vizro",
        export_commit="a" * 40,
        exported_at=datetime(2026, 10, 22, tzinfo=UTC),
        data_root=_data_root(tmp_path),
        now=NOW,
        flags_path=tree,
    )

    for page_id in ("behind-upstream", "whodepends"):
        html = (tmp_path / "vizro" / page_id / "index.html").read_text(encoding="utf-8")
        assert ("<table" in html) is table, (page_id, variant)


@pytest.mark.parametrize(("variant", "table"), [("on", True), ("off", False)])
def test_the_export_task_passes_its_flags_path_through(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    real_board_projections,
    variant: str,
    table: bool,
) -> None:
    tools = Path(__file__).resolve().parents[2] / "tools"
    monkeypatch.syspath_prepend(str(tools))
    import vizro_static_export as cli  # the vizro-static-export task's entry point

    monkeypatch.setattr(data, "board_projections", real_board_projections)
    tree = flagd_tree(tmp_path, {"pyforge.atlas.vizro_static_boards": "on", FLAG: variant}, name=f"{variant}.json")
    out = tmp_path / "vizro"

    code = cli.main(
        ["--out", str(out), "--data-root", str(_data_root(tmp_path)), "--flags-path", str(tree)]
        + ["--export-commit", "b" * 40, "--clock", "now"]  # a fake commit has no committer time
    )

    assert code == 0, capsys.readouterr().err
    html = (out / "whodepends" / "index.html").read_text(encoding="utf-8")
    assert ("<table" in html) is table


# --------------------------------------------------------------------------- #
# Review round 2: the projected definitions, their charts and the access column
# --------------------------------------------------------------------------- #


def test_the_projected_pages_declare_their_charts() -> None:
    on = {page.id: page for page in app.page_inventory(projected=True)}
    off = {page.id: page for page in app.page_inventory(projected=False)}

    assert on["behind-upstream"].chart == app.ChartDef("bar", x="lag_label", y="package_count")
    assert on["whodepends"].chart == app.ChartDef("bar", x="depends_on", y="dependent_count")
    assert off["behind-upstream"].chart is None and off["whodepends"].chart is None


def test_with_the_flag_on_the_two_boards_draw_their_charts_under_their_own_notes(tmp_path: Path) -> None:
    dashboard = app.build_dashboard(build_stamp=STAMP, data_root=_data_root(tmp_path), now=NOW, board_projections=True)

    for page_id, model in (
        ("behind-upstream", "build_behind_upstream_model"),
        ("whodepends", "build_whodepends_model"),
    ):
        page = next(p for p in dashboard.pages if p.id == page_id)
        assert any(getattr(c, "id", "") == f"{page_id}--chart" for c in page.components), page_id
        assert model in _card_text(dashboard, page_id)


def test_the_static_whodepends_table_lists_the_most_depended_on_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(data, "board_projections", lambda **_: True)
    root = _data_root(tmp_path)
    _write(
        root / data.CORE_DEPENDENCIES_PARQUET,
        pd.DataFrame(
            {
                "conda_name": ["a", "b", "c", "a", "b", "c"],
                "depends_on": ["numpy", "numpy", "numpy", "aaa", "aaa", "pandas"],
                "dep_type": ["run"] * 6,
            }
        ),
    )

    static_export.export_boards(
        tmp_path / "vizro",
        export_commit="c" * 40,
        exported_at=datetime(2026, 10, 22, tzinfo=UTC),
        data_root=root,
        now=NOW,
    )

    html = (tmp_path / "vizro" / "whodepends" / "index.html").read_text(encoding="utf-8")
    table = html[html.index('id="whodepends--grid"') :]
    positions = [table.index(f"<td>{name}</td>") for name in ("numpy", "aaa", "pandas")]
    assert positions == sorted(positions)  # 3, 2, 1 dependents: the measure's order, not the alphabet


@pytest.mark.parametrize("projected", [True, False])
def test_the_page_swap_keeps_a_pages_access_column(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, projected) -> None:
    pages = tuple(
        dataclasses.replace(page, access_column="org") if page.id == "whodepends" else page
        for page in app.PAGE_INVENTORY
    )
    monkeypatch.setattr(app, "PAGE_INVENTORY", pages)
    monkeypatch.setattr(data, "board_projections", lambda **_: projected)

    assert {p.id: p for p in app.page_inventory()}["whodepends"].access_column == "org"
    with pytest.raises(static_export.AccessColumnRefusedError):
        static_export.export_boards(tmp_path / "vizro", export_commit="d" * 40, data_root=_data_root(tmp_path), now=NOW)
