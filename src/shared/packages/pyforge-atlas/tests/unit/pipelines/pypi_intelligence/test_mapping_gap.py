"""Story 37.9 — why an enumerated package has no PyPI name (legacy mapping_gap, read-only)."""

from __future__ import annotations

import pandas as pd
import pytest

from pyforge.atlas.pipelines.pypi_intelligence import nodes


def _enumerated(*names: str) -> pd.DataFrame:
    return pd.DataFrame({"conda_name": list(names), "latest_version": ["1.0"] * len(names)})


def _mapping(pairs: list[tuple[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(pairs, columns=["conda_name", "pypi_name"]).assign(match_source="parselmouth")


def _python_deps(*names: str) -> pd.DataFrame:
    return pd.DataFrame(
        {"conda_name": list(names), "depends_on": ["python"] * len(names), "dep_type": ["run"] * len(names)}
    )


def _universe(*names: str) -> pd.DataFrame:
    return pd.DataFrame({"pypi_name": list(names)})


def _gap(enumerated, *, mapping=None, deps=None, upstream=None, registry=None, universe=None) -> dict[str, dict]:
    out = nodes.classify_mapping_gap(enumerated, mapping, deps, upstream, registry, universe)
    assert list(out.columns) == nodes.MAPPING_GAP_COLUMNS
    return {row["conda_name"]: row for row in out.to_dict("records")}


def _value(row: dict, column: str):
    value = row[column]
    return None if value is pd.NA or value is None else value


def test_a_mapped_package_is_not_in_the_gap():
    got = _gap(_enumerated("numpy", "zlib"), mapping=_mapping([("numpy", "numpy")]))
    assert set(got) == {"zlib"}


def test_the_three_classes_are_legacys():
    got = _gap(
        _enumerated("py-thing", "pypi-up", "gh-up", "reg-up", "bare-c"),
        deps=_python_deps("py-thing"),
        upstream=pd.DataFrame({"conda_name": ["gh-up"], "host": ["github"]}),
        registry=pd.DataFrame({"conda_name": ["pypi-up", "reg-up"], "registry": ["PyPI", "cran"]}),
    )
    assert {name: row["classification"] for name, row in got.items()} == {
        "py-thing": "python_track",
        "pypi-up": "python_track",
        "gh-up": "non_python_with_identity",
        "reg-up": "non_python_with_identity",
        "bare-c": "non_python_no_identity",
    }
    assert _value(got["gh-up"], "match_confidence") is None and _value(got["bare-c"], "match_source") is None


def test_a_build_only_python_dependency_is_not_python_track():
    deps = pd.DataFrame({"conda_name": ["tool"], "depends_on": ["python"], "dep_type": ["build"]})
    assert _gap(_enumerated("tool"), deps=deps)["tool"]["classification"] == "non_python_no_identity"


@pytest.mark.parametrize(
    ("conda_name", "universe", "confidence", "candidate", "transform"),
    [
        ("Foo_Bar", ["foo-bar"], "likely", "foo-bar", "bare"),
        ("thing-py", ["thing"], "uncorroborated", "thing", "strip-py"),
        ("thing-python", ["thing"], "uncorroborated", "thing", "strip-python"),
        ("python-thing", ["thing"], "uncorroborated", "thing", "strip-python-prefix"),
        ("both-py", ["both-py", "both"], "ambiguous", None, None),
        ("nothing", ["other"], "unrecovered", None, None),
    ],
)
def test_the_offline_recovery_is_legacys(conda_name, universe, confidence, candidate, transform):
    row = _gap(_enumerated(conda_name), deps=_python_deps(conda_name), universe=_universe(*universe))[conda_name]
    assert row["match_confidence"] == confidence
    assert _value(row, "candidate") == candidate
    assert _value(row, "transform") == transform
    assert _value(row, "match_source") == ("g10_spelling" if confidence == "likely" else None)


def test_a_name_another_package_maps_to_is_a_collision():
    got = _gap(
        _enumerated("wasmtime", "wasmtime-py"),
        mapping=_mapping([("wasmtime", "wasmtime")]),
        deps=_python_deps("wasmtime-py"),
        universe=_universe("wasmtime-py"),
    )
    # wasmtime-py's bare spelling is in the universe and unclaimed: likely
    assert got["wasmtime-py"]["match_confidence"] == "likely"
    got = _gap(
        _enumerated("wasmtime", "wasmtime-py"),
        mapping=_mapping([("wasmtime", "wasmtime")]),
        deps=_python_deps("wasmtime-py"),
        universe=_universe("wasmtime"),
    )
    assert got["wasmtime-py"]["match_confidence"] == "collision"
    assert got["wasmtime-py"]["candidate"] == "wasmtime"


def test_two_unmapped_packages_cannot_both_claim_one_name():
    got = _gap(
        _enumerated("Foo.Bar", "foo-bar"), deps=_python_deps("Foo.Bar", "foo-bar"), universe=_universe("foo_bar")
    )
    # sorted order: "Foo.Bar" claims first, so "foo-bar" collides with it (legacy's intra-run claim)
    assert got["Foo.Bar"]["match_confidence"] == "likely"
    assert got["foo-bar"]["match_confidence"] == "collision"


@pytest.mark.parametrize("enumerated", [None, pd.DataFrame(), _enumerated()])
def test_no_enumerated_packages_give_an_empty_typed_table(enumerated):
    out = nodes.classify_mapping_gap(enumerated, None, None, None, None, None)
    assert out.empty
    assert list(out.columns) == nodes.MAPPING_GAP_COLUMNS
    assert {str(t) for t in out.dtypes} == {"string"}


def test_every_package_mapped_gives_an_empty_typed_table():
    out = nodes.classify_mapping_gap(_enumerated("a"), _mapping([("a", "a")]), None, None, None, None)
    assert out.empty and list(out.columns) == nodes.MAPPING_GAP_COLUMNS


def test_the_board_reads_the_table(tmp_path):
    from pyforge.atlas.dashboard import data as dash_data

    out = nodes.classify_mapping_gap(
        _enumerated("thing-py", "zlib"), None, _python_deps("thing-py"), None, None, _universe("thing")
    )
    path = tmp_path / "derived_mapping_gap.parquet"
    out.to_parquet(path, index=False)
    board = dash_data.load_mapping_gap(path)
    assert set(board["classification"]) == {"python_track", "non_python_no_identity"}
    assert int(board["gap_count"].sum()) == 2
