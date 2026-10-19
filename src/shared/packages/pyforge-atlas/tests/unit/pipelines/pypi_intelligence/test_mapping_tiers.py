"""Story 34.11 (CAP-64): the Phase C mapping fills legacy's two further tiers.

Pure: frames built in memory in the shapes measured on 2026-10-18 (``core_cf_graph_raw``'s
anchor rows carry ``source_url``; ``pypi_universe`` names every PyPI project).
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from pyforge.atlas.datasets import core_sources as CS
from pyforge.atlas.pipelines.pypi_intelligence.nodes import map_pypi_conda, recipe_source_pypi_name

ENUM = pd.DataFrame(
    {"conda_name": ["numpy", "django", "ipydrawio", "ipydrawio-export", "jina-core", "boost", "Pillow-SIMD", "gone"]}
)
PARSELMOUTH = pd.DataFrame({"pypi_name": ["numpy"], "conda_name": ["numpy"]})
UNIVERSE = pd.DataFrame({"pypi_name": ["numpy", "Django", "pillow-simd", "unrelated"], "last_serial": [1, 2, 3, 4]})
GRAPH = pd.DataFrame(
    {
        "conda_name": ["ipydrawio", "ipydrawio-export", "jina-core", "boost", "django", "numpy"],
        "source_url": [
            "https://pypi.io/packages/source/i/ipydrawio/ipydrawio-1.3.0.tar.gz",
            "https://pypi.io/packages/source/i/ipydrawio/ipydrawio-1.3.0.tar.gz",
            "https://files.pythonhosted.org/packages/source/j/Jina/jina-3.7.7.tar.gz",
            "https://github.com/boostorg/boost/archive/1.86.tar.gz",
            "https://pypi.org/packages/source/d/django-other/x.tar.gz",
            "https://pypi.io/packages/source/n/numpy-other/x.tar.gz",
        ],
    }
)


def _tiers(out: pd.DataFrame) -> dict[str, tuple[str, str]]:
    return {c: (p, s) for p, c, s in zip(out["pypi_name"], out["conda_name"], out["match_source"], strict=True)}


def test_each_tier_fills_only_a_package_the_one_before_left_unmapped():
    out = map_pypi_conda(PARSELMOUTH, ENUM, GRAPH, UNIVERSE)

    assert _tiers(out) == {
        "numpy": ("numpy", "parselmouth"),  # its recipe URL names another project: parselmouth wins
        # a coincidence keeps its name and takes the recipe label (legacy's COALESCE, CFA:2434)
        "django": ("django", "recipe_source_url"),
        "Pillow-SIMD": ("pillow-simd", "name_coincidence"),  # lower-cased on both sides
        "ipydrawio": ("ipydrawio", "recipe_source_url"),
        "ipydrawio-export": ("ipydrawio", "recipe_source_url"),  # every output of the feedstock
        "jina-core": ("jina", "recipe_source_url"),  # files.pythonhosted.org, lower-cased
    }  # boost: a GitHub source; gone: no tier names it


def test_a_pypi_project_parselmouth_maps_elsewhere_never_matches_by_name():
    # legacy Phase D checks the PyPI side first (CFA:1869): GNU flex is not PyPI flex
    parselmouth = pd.DataFrame({"pypi_name": ["flex"], "conda_name": ["flex-swagger"]})
    enum = pd.DataFrame({"conda_name": ["flex", "flex-swagger"]})
    universe = pd.DataFrame({"pypi_name": ["Flex"]})

    assert _tiers(map_pypi_conda(parselmouth, enum, None, universe)) == {"flex-swagger": ("flex", "parselmouth")}


def test_a_package_parselmouth_maps_never_takes_a_coincidence():
    parselmouth = pd.DataFrame({"pypi_name": ["torch"], "conda_name": ["pytorch"]})
    enum = pd.DataFrame({"conda_name": ["pytorch"]})
    universe = pd.DataFrame({"pypi_name": ["pytorch", "torch"]})

    assert _tiers(map_pypi_conda(parselmouth, enum, None, universe)) == {"pytorch": ("torch", "parselmouth")}


def test_the_pypi_side_check_compares_pep_503_names():
    parselmouth = pd.DataFrame({"pypi_name": ["foo_bar"], "conda_name": ["py-foo-bar"]})
    enum = pd.DataFrame({"conda_name": ["foo-bar", "py-foo-bar"]})
    universe = pd.DataFrame({"pypi_name": ["foo-bar"]})

    assert "foo-bar" not in _tiers(map_pypi_conda(parselmouth, enum, None, universe))  # foo_bar is foo-bar


def test_a_parselmouth_name_blocks_a_coincidence_even_for_an_unenumerated_package():
    # stricter than legacy's packages-table read: a recorded deviation (spec 34.11)
    parselmouth = pd.DataFrame({"pypi_name": ["flex"], "conda_name": ["flex-swagger"]})
    enum = pd.DataFrame({"conda_name": ["flex"]})  # flex-swagger is not on the channel

    assert _tiers(map_pypi_conda(parselmouth, enum, None, pd.DataFrame({"pypi_name": ["flex"]}))) == {}


def test_one_coincidence_per_pypi_project():
    enum = pd.DataFrame({"conda_name": ["foo-bar", "foo_bar"]})
    universe = pd.DataFrame({"pypi_name": ["foo-bar", "foo_bar"]})

    out = map_pypi_conda(pd.DataFrame(), enum, None, universe)

    assert _tiers(out) == {"foo-bar": ("foo-bar", "name_coincidence")}  # the same project under PEP 503


def test_every_output_attributed_to_the_feedstock_maps_to_its_recipe_project():
    graph = pd.DataFrame(
        {
            "feedstock_name": ["airflow", "old", "new", "blank", "pypi"],
            "conda_name": ["airflow", "x", "x", "y", "y"],
            "source_url": [
                "https://pypi.io/packages/source/a/apache-airflow/a.tgz",
                "https://pypi.io/packages/source/o/old-name/o.tgz",
                "https://pypi.io/packages/source/n/new-name/n.tgz",
                None,  # a null-URL first anchor never hides the next
                "https://pypi.io/packages/source/y/y-py/y.tgz",
            ],
        }
    )
    attribution = pd.DataFrame(
        {
            "conda_name": ["airflow", "airflow-with-amazon", "x", "z"],
            "feedstock_name": ["airflow", "airflow", "new", "blank"],
        }
    )
    enum = pd.DataFrame({"conda_name": ["airflow", "airflow-with-amazon", "x", "y", "z"]})
    graph = pd.concat(  # z is anchored in a PyPI-sourced feedstock but attributed to one with no PyPI URL
        [
            graph,
            pd.DataFrame(
                {
                    "feedstock_name": ["blank", "zpypi"],
                    "conda_name": ["z", "z"],
                    "source_url": [
                        "https://github.com/z/z/archive/1.tar.gz",
                        "https://pypi.io/packages/source/z/z/z.tgz",
                    ],
                }
            ),
        ],
        ignore_index=True,
    )

    out = map_pypi_conda(pd.DataFrame(), enum, graph, None, attribution)

    assert _tiers(out) == {
        "airflow": ("apache-airflow", "recipe_source_url"),
        "airflow-with-amazon": ("apache-airflow", "recipe_source_url"),  # attributed, not an anchor
        "x": ("new-name", "recipe_source_url"),  # attribution picks the feedstock, not the first anchor
        "y": ("y-py", "recipe_source_url"),  # no attribution row: the first anchor whose URL names a PyPI project
    }  # z: attribution names a GitHub-sourced feedstock, so its PyPI-sourced anchor never counts


def test_a_frame_without_source_url_skips_the_recipe_tier_and_says_so(caplog):
    graph = pd.DataFrame({"feedstock_name": ["django"], "conda_name": ["django"]})  # pre-34.11 last-good

    with caplog.at_level("WARNING"):
        out = map_pypi_conda(PARSELMOUTH, ENUM, graph, None)

    assert _tiers(out) == {"numpy": ("numpy", "parselmouth")} and "no source_url column" in caplog.text


def test_a_name_outside_the_enumerated_packages_is_never_mapped():
    graph = pd.DataFrame({"conda_name": ["ghost"], "source_url": ["https://pypi.io/packages/source/g/ghost/g.tgz"]})
    universe = pd.DataFrame({"pypi_name": ["ghost-2"]})

    out = map_pypi_conda(PARSELMOUTH, ENUM, graph, universe)

    assert "ghost" not in set(out["conda_name"])


@pytest.mark.parametrize(
    ("graph", "universe"),
    [
        (None, None),
        (pd.DataFrame(), pd.DataFrame()),
        (pd.DataFrame({"conda_name": ["boost"]}), pd.DataFrame({"last_serial": [1]})),  # no source_url, no pypi_name
    ],
    ids=["absent", "empty", "columns-missing"],
)
def test_without_the_new_inputs_the_mapping_is_parselmouth_alone(graph, universe):
    assert _tiers(map_pypi_conda(PARSELMOUTH, ENUM, graph, universe)) == {"numpy": ("numpy", "parselmouth")}


def test_with_no_parselmouth_mapping_the_other_tiers_still_fill():
    out = map_pypi_conda(pd.DataFrame(), ENUM, GRAPH, UNIVERSE)

    tiers = _tiers(out)
    assert tiers["Pillow-SIMD"] == ("pillow-simd", "name_coincidence") and tiers["ipydrawio"][1] == "recipe_source_url"
    assert tiers["numpy"] == ("numpy", "recipe_source_url")  # no parselmouth row to protect it from the relabel


def test_with_nothing_at_all_the_frame_is_empty_but_columned():
    out = map_pypi_conda(pd.DataFrame(), pd.DataFrame({"conda_name": []}), None, None)
    assert out.empty and list(out.columns) == ["pypi_name", "conda_name", "match_source"]


@pytest.mark.parametrize(
    ("url", "name"),
    [
        ("https://pypi.io/packages/source/r/requests/requests-2.0.tar.gz", "requests"),
        ("https://pypi.org/packages/source/P/PyYAML/PyYAML-6.0.tar.gz", "pyyaml"),
        ("https://files.pythonhosted.org/packages/source/a/absl-py/absl_py-2.5.1.tar.gz", "absl-py"),
        ("https://files.pythonhosted.org/packages/aa/bb/cc/x-1.0.tar.gz", None),  # hashed path: no name
        ("https://github.com/psf/requests/archive/v2.tar.gz", None),
        (None, None),
        (["https://pypi.io/packages/source/r/requests/r.tgz"], None),  # the frame holds the first URL already
    ],
)
def test_the_recipe_source_name_is_legacys_pattern_plus_files_pythonhosted(url: Any, name: str | None):
    assert recipe_source_pypi_name(url) == name


@pytest.mark.parametrize(
    ("payload", "url"),
    [
        ({"meta_yaml": {"source": {"url": "https://a/x.tgz"}}}, "https://a/x.tgz"),
        ({"meta_yaml": {"source": [{"path": "."}, {"url": "https://b/y.tgz"}]}}, "https://b/y.tgz"),
        ({"meta_yaml": {"source": {"url": ["", "https://c/z.tgz"]}}}, "https://c/z.tgz"),
        ({"meta_yaml": {"source": {"git_url": "https://g"}}}, None),
        ({"meta_yaml": {}}, None),
        ({}, None),
        ({"meta_yaml": "not a dict"}, None),
    ],
)
def test_the_frame_reads_the_first_source_url(payload: dict[str, Any], url: str | None):
    assert CS._source_url(payload) == url


def test_anchor_rows_carry_the_url_and_edge_rows_do_not():
    payload = {
        "meta_yaml": {
            "source": {"url": "https://pypi.io/packages/source/f/foo/foo-1.tgz"},
            "requirements": {"run": ["python"]},
        },
        "name": "foo",
    }
    frame = CS._cf_graph_frame([("foo", payload)], {}, {}, {})

    anchors = frame[frame["depends_on"].isna()]
    edges = frame[frame["depends_on"].notna()]
    assert set(anchors["source_url"]) == {"https://pypi.io/packages/source/f/foo/foo-1.tgz"}
    assert edges["source_url"].isna().all()


def test_a_frame_of_bot_records_alone_still_has_the_column():
    frame = CS._cf_graph_frame([], {"bar": {}}, {}, {})

    assert "source_url" in frame.columns and frame["source_url"].isna().all()


def test_the_graph_is_fetched_once_per_session_and_each_node_gets_its_own_frame(monkeypatch):
    ds = CS.CfGraphTarballDataset(url="https://example.invalid/node_attrs.tar.gz")
    calls = {"n": 0}

    def fetch() -> pd.DataFrame:
        calls["n"] += 1
        return pd.DataFrame({"conda_name": ["foo"], "source_url": ["u"]})

    monkeypatch.setattr(ds, "_fetch", fetch)

    first = ds.load()
    first["added"] = 1  # one node assigning a column
    second = ds.load()

    assert calls["n"] == 1 and "added" not in second.columns


def test_the_catalog_form_with_a_filepath_also_fetches_once(monkeypatch, tmp_path):
    ds = CS.CfGraphTarballDataset(url="https://example.invalid/node_attrs.tar.gz", filepath=str(tmp_path))
    calls = {"n": 0}

    def fetch() -> pd.DataFrame:
        calls["n"] += 1
        return pd.DataFrame({"conda_name": ["foo"], "source_url": ["u"]})

    monkeypatch.setattr(ds, "_fetch", fetch)

    ds.load()
    ds.load()

    assert calls["n"] == 1 and (tmp_path / CS.CfGraphTarballDataset.LAST_GOOD_FILENAME).exists()


def test_an_instance_kept_past_the_memo_window_fetches_again(monkeypatch):
    ds = CS.CfGraphTarballDataset(url="https://example.invalid/node_attrs.tar.gz")
    calls = {"n": 0}
    clock = {"t": 1000.0}

    def fetch() -> pd.DataFrame:
        calls["n"] += 1
        return pd.DataFrame({"conda_name": ["foo"]})

    monkeypatch.setattr(ds, "_fetch", fetch)
    monkeypatch.setattr(CS.time, "monotonic", lambda: clock["t"])

    ds.load()
    clock["t"] += CS.CfGraphTarballDataset.MEMO_SECONDS - 1
    ds.load()
    clock["t"] += 1
    ds.load()

    assert calls["n"] == 2 and CS.CfGraphTarballDataset.MEMO_SECONDS == 3600.0
