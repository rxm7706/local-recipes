"""Story 34.3 (CAP-64): the conda-forge bot's split graph repos fill dependencies, health and maintainers.

``regro/cf-graph-countyfair`` now serves ``conda-forge/conda-forge-bot-data``, whose tarball has no
``node_attrs/``, ``pr_info/`` or ``version_pr_info/``. cf-scripts publishes them as three repos,
each ``<repo>-main/<5 sha1 hex dirs>/<feedstock>.json``. Network-free: tarballs are built in memory
and the composed ``APIDataset`` objects are replaced.
"""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from kedro.io import DatasetError

from pyforge.atlas.datasets import CfGraphTarballDataset
from pyforge.atlas.datasets.core_sources import parse_cf_graph_tarballs
from pyforge.atlas.pipelines.core.nodes import build_dependency_graph, compute_feedstock_health
from pyforge.atlas.pipelines.vcs_health.nodes import enrich_maintainers
from pyforge.atlas.provenance import resolve_for_catalog_dataset


def _sharded(repo: str, node: str) -> str:
    """cf-scripts' ``get_sharded_path`` with the top directory trimmed, as the split repos store
    it: the sha1 of the basename, as five one-character directories, before the basename."""
    *dirs, name = node.split("/")
    hx = hashlib.sha1(f"{name}.json".encode()).hexdigest()[:5]
    return "/".join([f"{repo}-main", *dirs, *hx, f"{name}.json"])


def _tar(repo: str, records: dict[str, dict[str, Any]]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for feedstock, payload in records.items():
            data = json.dumps(payload).encode()
            info = tarfile.TarInfo(name=_sharded(repo, feedstock))
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


NODE_ATTRS = {
    "numpy": {
        "feedstock_name": "numpy",
        "archived": False,
        "meta_yaml": {
            "requirements": {
                "build": ["{{ compiler('c') }}", "${{ stdlib('c') }}"],  # jinja targets are never edges
                "host": ["python", "cython"],
                "run": ["python >=3.11", "libblas", "numpy"],  # a self-reference is never an edge
            },
            "extra": {"recipe-maintainers": ["rgommers", "jakirkham", "rgommers"]},
        },
    },
    "noreqs": {"feedstock_name": "noreqs", "meta_yaml": {"extra": {"recipe-maintainers": ["solo"]}}},
    # outputs named beyond the requirements blocks still anchor (Phase E: every output has maintainers)
    "multi": {
        "outputs_names": {"__set__": True, "elements": ["multi-core", "multi-extra"]},
        "meta_yaml": {
            "outputs": [{"name": "multi-core", "requirements": {"run": ["python"]}}],
            "extra": {"recipe-maintainers": ["mo"]},
        },
    },
    # no requirements, but outputs_names gives the real package name
    "renamed": {"outputs_names": ["real-name"], "meta_yaml": {"extra": {"recipe-maintainers": ["renamer"]}}},
    "oldpkg": {"archived": True, "meta_yaml": {"requirements": {"run": ["python"]}}},
}
PR_INFO = {
    "numpy": {
        "PRed": [
            {"PR": {"state": "closed"}, "data": {"version": "2.0"}},
            # live PRs are references into conda-forge-bot-data-pr_json (measured 2026-10-18)
            {"PR": {"__lazy_json__": "pr_json/4799436437.json"}, "data": {"version": "2.1"}},
            {"PR": {"__lazy_json__": "pr_json/999.json"}, "data": {"version": "2.2"}},  # unresolvable
        ],
        "bad": False,
    },
    "botonly": {"PRed": [], "bad": "parse error"},
}
VERSION_PR_INFO = {
    "numpy": {"new_version_errors": {"2.2": "solver failed"}, "bad": False},
    "vbad": {"bad": "solver error"},  # bad on version_pr_info alone flags the feedstock too
}
PR_JSON = {"4799436437": {"number": 7, "state": "open"}}


def _frame() -> pd.DataFrame:
    return parse_cf_graph_tarballs(
        _tar("conda-forge-bot-data-node_attrs", NODE_ATTRS),
        _tar("conda-forge-bot-data-pr_info", PR_INFO),
        _tar("conda-forge-bot-data-version_pr_info", VERSION_PR_INFO),
        _tar("conda-forge-bot-data-pr_json", PR_JSON),
    )


def test_split_tarballs_yield_edges_from_sharded_paths() -> None:
    g = _frame()

    edges = build_dependency_graph(g)

    assert set(map(tuple, edges[["conda_name", "depends_on", "dep_type"]].values)) == {
        ("numpy", "python", "host"),
        ("numpy", "cython", "host"),
        ("numpy", "python", "run"),
        ("numpy", "libblas", "run"),
        ("multi-core", "python", "run"),
    }  # version pins stripped; no self-reference, jinja target, anchor row or archived feedstock


def test_a_nested_node_is_not_merged_with_its_basename_twin() -> None:
    """node_attrs nests a few nodes (``conda-forge/label/<name>``); the key is the node name."""
    g = parse_cf_graph_tarballs(
        _tar(
            "conda-forge-bot-data-node_attrs",
            {"twin": {"meta_yaml": {}}, "conda-forge/label/twin": {"archived": True, "meta_yaml": {}}},
        )
    )

    flags = g.drop_duplicates("feedstock_name").set_index("feedstock_name")["feedstock_archived"]
    assert flags.to_dict() == {"conda-forge/label/twin": True, "twin": False}
    assert list(compute_feedstock_health(g)["feedstock_name"]) == ["twin"]


def test_bot_health_ports_legacy_phase_m() -> None:
    health = compute_feedstock_health(_frame()).set_index("feedstock_name")

    numpy = health.loc["numpy"]
    assert numpy["open_prs"] == 1  # the resolved reference; the unresolvable one is unknown, never open
    assert pd.isna(numpy["bot_last_pr_state"]) and numpy["bot_last_pr_version"] == "2.2"
    assert numpy["bot_version_errors_count"] == 1
    assert not numpy["feedstock_bad"]
    assert bool(health.loc["botonly", "feedstock_bad"]) is True  # bot data, no node_attrs: still a health row
    assert bool(health.loc["vbad", "feedstock_bad"]) is True


def test_an_archived_feedstock_is_flagged_and_kept_out_of_edges_and_health() -> None:
    g = _frame()

    assert set(g.loc[g["feedstock_archived"].astype(bool), "feedstock_name"]) == {"oldpkg"}
    assert "oldpkg" not in set(build_dependency_graph(g)["conda_name"])
    assert "oldpkg" not in set(compute_feedstock_health(g)["feedstock_name"])


def test_an_empty_graph_keeps_every_health_column() -> None:
    assert list(compute_feedstock_health(_frame().iloc[0:0]).columns) == [
        "feedstock_name",
        "ci_status",
        "open_prs",
        "open_issues",
        "bot_last_pr_state",
        "bot_last_pr_version",
        "bot_version_errors_count",
        "feedstock_bad",
    ]


def test_maintainers_reach_enrich_maintainers_even_without_edges() -> None:
    maintainers, package_maintainers = enrich_maintainers(_frame())

    assert set(maintainers["maintainer"]) == {"jakirkham", "mo", "renamer", "rgommers", "solo"}
    pairs = set(map(tuple, package_maintainers[["conda_name", "maintainer"]].values))
    assert ("numpy", "rgommers") in pairs and ("noreqs", "solo") in pairs  # the anchor row carries a no-edge feedstock
    assert {("multi-core", "mo"), ("multi-extra", "mo")} <= pairs  # an output with no requirements block
    assert ("real-name", "renamer") in pairs and ("renamed", "renamer") not in pairs


def test_the_combined_layout_still_parses_through_the_dataset(tmp_path: Path) -> None:
    """One URL: the pre-split tarball, ``node_attrs/``, ``pr_info/`` and ``version_pr_info/`` in one."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for kind, records in (("node_attrs", NODE_ATTRS), ("pr_info", PR_INFO), ("version_pr_info", VERSION_PR_INFO)):
            for feedstock, payload in records.items():
                data = json.dumps(payload).encode()
                info = tarfile.TarInfo(name=f"cf-graph-countyfair-master/{kind}/{feedstock}.json")
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))
    ds = CfGraphTarballDataset(url="https://example.invalid/combined.tgz", filepath=str(tmp_path / "cfg"))
    ds._inners = {"node_attrs": _Blob(buf.getvalue())}

    g = ds.load()

    assert ("numpy", "libblas", "run") in set(map(tuple, build_dependency_graph(g).values))
    health = compute_feedstock_health(g).set_index("feedstock_name")
    assert health.loc["numpy", "bot_version_errors_count"] == 1
    assert health.loc["numpy", "open_prs"] == 0  # no pr_json in the combined layout: references stay unknown


class _Blob:
    def __init__(self, outcome: Any) -> None:
        self.outcome = outcome

    def load(self) -> Any:
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def _dataset(tmp_path: Path, node_attrs: Any, pr_info: Any = None) -> CfGraphTarballDataset:
    ds = CfGraphTarballDataset(
        url="https://example.invalid/na.tgz",
        pr_info_url="https://example.invalid/pi.tgz",
        version_pr_info_url="https://example.invalid/vpi.tgz",
        pr_json_url="https://example.invalid/prj.tgz",
        filepath=str(tmp_path / "cfg"),
    )
    ds._inners = {
        "node_attrs": _Blob(node_attrs),
        "pr_info": _Blob(_tar("conda-forge-bot-data-pr_info", PR_INFO) if pr_info is None else pr_info),
        "version_pr_info": _Blob(_tar("conda-forge-bot-data-version_pr_info", VERSION_PR_INFO)),
        "pr_json": _Blob(_tar("conda-forge-bot-data-pr_json", PR_JSON)),
    }
    return ds


def _marker(tmp_path: Path) -> dict[str, Any] | None:
    p = tmp_path / "cfg" / CfGraphTarballDataset.STALENESS_FILENAME
    return json.loads(p.read_text()) if p.is_file() else None


def test_a_good_fetch_keeps_last_good_and_no_marker(tmp_path: Path) -> None:
    frame = _dataset(tmp_path, _tar("conda-forge-bot-data-node_attrs", NODE_ATTRS)).load()

    assert not frame.empty
    assert (tmp_path / "cfg" / CfGraphTarballDataset.LAST_GOOD_FILENAME).is_file()
    assert _marker(tmp_path) is None


def test_a_failed_fetch_serves_last_good_under_a_marker(tmp_path: Path) -> None:
    good = _dataset(tmp_path, _tar("conda-forge-bot-data-node_attrs", NODE_ATTRS)).load()

    kept = _dataset(tmp_path, DatasetError("unreachable")).load()

    assert len(kept) == len(good)
    # the parquet copy reads back exactly as the fresh frame does downstream (list columns included)
    for fresh, served in zip(enrich_maintainers(good), enrich_maintainers(kept)):
        pd.testing.assert_frame_equal(fresh, served)
    marker = _marker(tmp_path)
    assert marker is not None and marker["last_good_exists"] is True
    assert "DatasetError" in marker["reason"]


def test_a_good_fetch_clears_an_earlier_marker(tmp_path: Path) -> None:
    _dataset(tmp_path, DatasetError("unreachable")).load()
    assert _marker(tmp_path) is not None

    _dataset(tmp_path, _tar("conda-forge-bot-data-node_attrs", NODE_ATTRS)).load()

    assert _marker(tmp_path) is None


def test_a_bot_repo_with_no_records_keeps_last_good(tmp_path: Path) -> None:
    """A partial redirect: pr_info answers with no records; an all-zero health frame must not win."""
    good = _dataset(tmp_path, _tar("conda-forge-bot-data-node_attrs", NODE_ATTRS)).load()

    kept = _dataset(
        tmp_path, _tar("conda-forge-bot-data-node_attrs", NODE_ATTRS), pr_info=_tar("conda-forge-bot-data-main", {})
    ).load()

    assert len(kept) == len(good)
    assert _marker(tmp_path)["reason"] == "pr_info yielded no records -- keeping last-good"


def test_a_body_that_is_not_a_tarball_degrades(tmp_path: Path) -> None:
    out = _dataset(tmp_path, b"<html>not a tarball</html>").load()

    assert out.empty
    assert "ReadError" in _marker(tmp_path)["reason"]


def test_a_parser_bug_raises_instead_of_serving_stale(tmp_path: Path) -> None:
    """Only fetch and tarball errors degrade; anything else is a bug and fails the run."""
    with pytest.raises(DatasetError) as raised:  # kedro's load wrapper re-raises it as DatasetError
        _dataset(tmp_path, KeyError("bug")).load()

    assert isinstance(raised.value.__cause__, KeyError)
    assert _marker(tmp_path) is None


def test_a_failed_fetch_with_no_last_good_returns_the_empty_frame(tmp_path: Path) -> None:
    out = _dataset(tmp_path, DatasetError("unreachable")).load()

    assert out.empty and "maintainers" in out.columns
    assert _marker(tmp_path)["last_good_exists"] is False


def test_an_empty_parse_keeps_last_good(tmp_path: Path) -> None:
    """The cf-graph-countyfair redirect's own failure mode: a tarball with no node_attrs."""
    good = _dataset(tmp_path, _tar("conda-forge-bot-data-node_attrs", NODE_ATTRS)).load()

    kept = _dataset(tmp_path, _tar("conda-forge-bot-data-main", {})).load()

    assert len(kept) == len(good)
    assert "parsed frame is empty" in _marker(tmp_path)["reason"]


def test_provenance_reports_the_copy_and_the_marker(tmp_path: Path) -> None:
    fresh = _dataset(tmp_path, _tar("conda-forge-bot-data-node_attrs", NODE_ATTRS))
    assert resolve_for_catalog_dataset({"x": fresh}, "x", fresh.load()).kind == "live-fetch"

    stale = _dataset(tmp_path, DatasetError("unreachable"))
    info = resolve_for_catalog_dataset({"x": stale}, "x", stale.load())

    assert info.kind == "file-mtime" and info.build_stamp is not None
    assert info.reason is not None and info.reason.startswith("stale: fetch or parse failed")


def test_without_filepath_a_failure_still_raises(tmp_path: Path) -> None:
    ds = CfGraphTarballDataset(url="https://example.invalid/na.tgz")
    ds._inners = {"node_attrs": _Blob(DatasetError("unreachable"))}

    with pytest.raises(DatasetError):
        ds.load()
