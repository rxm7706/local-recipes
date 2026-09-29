"""Story 23.8 — build_inventory_universe: the workbook-free metrics universe.

Offline, fixture-based (no network, no real bootstrap data). Covers the 9-source
union, provenance-label byte-identity, per-source `in_<source>` BOOLs, `role`, and
`openteams_universe_member`.
"""

from __future__ import annotations

import pandas as pd

from pyforge.atlas.pipelines.derived_artifacts.nodes import (
    build_inventory_universe,
    looks_like_pkg,
    norm_pkg,
    parse_openteams_title,
)


def _empty(*cols: str) -> pd.DataFrame:
    return pd.DataFrame(columns=list(cols))


def test_union_across_all_nine_sources_one_row_per_pep503_name():
    core_packages_enumerated = pd.DataFrame([{"conda_name": "Numpy", "latest_version": "1.0"}])
    core_anaconda_main_packages = pd.DataFrame([{"conda_name": "requests"}])
    discovery_anaconda_dist_2026x_raw = pd.DataFrame([{"conda_name": "pandas"}])
    discovery_basilisk_packages_raw = pd.DataFrame([{"conda_name": "scipy"}])
    discovery_aoss_free_python_raw = pd.DataFrame([{"pypi_name": "flask"}])
    discovery_aoss_premium_python_raw = pd.DataFrame([{"pypi_name": "django"}])
    enterprise_jfrog_names = pd.DataFrame([{"pypi_name": "click", "conda_name": None}])
    enterprise_conda_maintainers = pd.DataFrame(
        [
            {
                "core_python_package_name": "pytest",
                "role": "Maintainer",
                "feedstock_slug": "x",
                "repository_source": "CDO-ENT-CONDA",
            }
        ]
    )
    openteams_project_1_board_raw = pd.DataFrame([{"title": "[Conda-Forge Packaging] rich"}])

    universe = build_inventory_universe(
        core_packages_enumerated,
        core_anaconda_main_packages,
        discovery_anaconda_dist_2026x_raw,
        discovery_basilisk_packages_raw,
        discovery_aoss_free_python_raw,
        discovery_aoss_premium_python_raw,
        enterprise_jfrog_names,
        enterprise_conda_maintainers,
        openteams_project_1_board_raw,
    )

    assert len(universe) == 9
    by_name = universe.set_index("core_python_package_name")
    assert by_name.loc["numpy", "in_conda_forge"]
    assert by_name.loc["requests", "in_anaconda_main"]
    assert by_name.loc["pandas", "in_anaconda_dist"]
    assert by_name.loc["scipy", "in_basilisk"]
    assert by_name.loc["flask", "in_aoss_free"]
    assert by_name.loc["django", "in_aoss_premium"]
    assert by_name.loc["click", "in_cdo_ent_jfrog"]
    assert by_name.loc["pytest", "in_cdo_ent_conda"]
    assert by_name.loc["pytest", "role"] == "Maintainer"
    assert by_name.loc["rich", "in_openteams"]
    # names not in either enterprise universe are not counted as members.
    assert not by_name.loc["numpy", "openteams_universe_member"]
    assert by_name.loc["click", "openteams_universe_member"]
    assert by_name.loc["pytest", "openteams_universe_member"]


def test_package_input_names_and_sources_are_sorted_lists():
    core_packages_enumerated = pd.DataFrame([{"conda_name": "Numpy"}])
    universe = build_inventory_universe(
        core_packages_enumerated,
        _empty("conda_name"),
        _empty("conda_name"),
        _empty("conda_name"),
        _empty("pypi_name"),
        _empty("pypi_name"),
        _empty("pypi_name", "conda_name"),
        _empty("core_python_package_name", "role"),
        _empty("title"),
    )
    row = universe.iloc[0]
    assert row["core_python_package_name"] == "numpy"
    assert row["package_input_names"] == ["Numpy"]
    assert row["sources"] == ["tab:Conda-Forge"]
    assert row["role"] == "N/A"


def test_name_present_in_multiple_sources_carries_all_provenance_labels():
    universe = build_inventory_universe(
        pd.DataFrame([{"conda_name": "widget"}]),
        _empty("conda_name"),
        _empty("conda_name"),
        pd.DataFrame([{"conda_name": "widget"}]),
        _empty("pypi_name"),
        _empty("pypi_name"),
        pd.DataFrame([{"pypi_name": "widget", "conda_name": None}]),
        _empty("core_python_package_name", "role"),
        _empty("title"),
    )
    assert len(universe) == 1
    row = universe.iloc[0]
    assert row["core_python_package_name"] == "widget"
    assert set(row["sources"]) == {"tab:Conda-Forge", "tab:Basilisk", "tab:CDO-ENT-JFROG"}
    assert bool(row["openteams_universe_member"]) is True


def test_openteams_rule_c_row_contributes_no_package():
    board = pd.DataFrame([{"title": "CVE-2026-0001 | some advisory with no package token"}])
    universe = build_inventory_universe(
        _empty("conda_name"),
        _empty("conda_name"),
        _empty("conda_name"),
        _empty("conda_name"),
        _empty("pypi_name"),
        _empty("pypi_name"),
        _empty("pypi_name", "conda_name"),
        _empty("core_python_package_name", "role"),
        board,
    )
    assert universe.empty


def test_all_inputs_empty_yields_empty_but_correctly_columned_frame():
    universe = build_inventory_universe(
        _empty("conda_name"),
        _empty("conda_name"),
        _empty("conda_name"),
        _empty("conda_name"),
        _empty("pypi_name"),
        _empty("pypi_name"),
        _empty("pypi_name", "conda_name"),
        _empty("core_python_package_name", "role"),
        _empty("title"),
    )
    assert universe.empty
    assert list(universe.columns) == [
        "core_python_package_name",
        "package_input_names",
        "sources",
        "in_cdo_ent_jfrog",
        "in_cdo_ent_conda",
        "in_openteams",
        "in_conda_forge",
        "in_basilisk",
        "in_anaconda_main",
        "in_anaconda_dist",
        "in_aoss_free",
        "in_aoss_premium",
        "role",
        "openteams_universe_member",
    ]


def test_malformed_missing_column_inputs_never_raise():
    # None / missing-column frames degrade to "contributes nothing", never a crash.
    universe = build_inventory_universe(
        None,
        pd.DataFrame(),
        pd.DataFrame({"unexpected": [1]}),
        _empty("conda_name"),
        _empty("pypi_name"),
        _empty("pypi_name"),
        _empty("pypi_name", "conda_name"),
        _empty("core_python_package_name", "role"),
        _empty("title"),
    )
    assert universe.empty


def test_norm_pkg_and_looks_like_pkg_match_metrics_py_semantics():
    assert norm_pkg("Numpy_Extra.Thing") == "numpy-extra-thing"
    assert looks_like_pkg("numpy") is True
    assert looks_like_pkg("2026-08-12") is False
    assert looks_like_pkg("n/a") is False


def test_parse_openteams_title_rules_a_b_c():
    assert parse_openteams_title("some title | numpy, pandas") == ("a", ["numpy", "pandas"])
    assert parse_openteams_title("[Conda-Forge Packaging] rich") == ("b", ["rich"])
    assert parse_openteams_title("just a plain title") == ("c", [])
