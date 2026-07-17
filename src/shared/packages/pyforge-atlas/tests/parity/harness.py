"""Parity-diff harness (Story B1, Task 5 / AC-7).

The Wave-B ``parity-diff`` gate BEGINS here. In FIXTURE MODE (``--frozen``, non-
credentialed, offline — AD-11) it runs each migrated node against a captured legacy
input fixture and diffs the node's output DataFrame against the captured legacy OUTPUT
snapshot, on the declared columns. B1 seeds the Core + VCS fixtures for the 11 phases
ported here; B2-B3 extend the harness; B4 CONSUMES it at the attended credentialed
event (the exact row-count + value parity on the ``v_actionable_packages`` family — NOT
in B1 scope, AD-19).

Fixtures live in the TRACKED test tree (``tests/parity/fixtures/``), never read from
``.claude/data/`` at gate time (spine "Tests & fixtures" row). See ``PARITY_NOTES.md``
for the fixture provenance + the documented maintainer-universe delta (AC-5).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

from pyforge.atlas.pipelines.core import nodes as core_nodes
from pyforge.atlas.pipelines.vcs_health import nodes as vcs_nodes

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# node name -> (callable, ordered input catalog names, ordered output catalog names).
# This is the single dispatch registry the harness + the B4 credentialed run share.
NODE_REGISTRY: dict[str, tuple] = {
    # -- core --
    "enumerate_conda_packages": (
        core_nodes.enumerate_conda_packages,
        ["core_repodata_raw", "core_channeldata_raw"],
        ["core_packages_enumerated"],
    ),
    "attribute_feedstocks": (
        core_nodes.attribute_feedstocks,
        ["core_feedstock_outputs_raw"],
        ["core_feedstock_attribution"],
    ),
    "detect_latest_status": (
        core_nodes.detect_latest_status,
        ["core_repodata_raw", "core_channeldata_raw"],
        ["core_latest_status"],
    ),
    "compute_downloads": (
        core_nodes.compute_downloads,
        ["core_anaconda_downloads_raw", "core_s3_download_stats_raw"],
        [
            "core_downloads",
            "core_downloads_platform_breakdown",
            "core_downloads_pyver_breakdown",
            "core_downloads_channel_breakdown",
        ],
    ),
    "compute_version_download_history": (
        core_nodes.compute_version_download_history,
        ["core_anaconda_downloads_raw"],
        ["core_version_download_history"],
    ),
    "build_dependency_graph": (
        core_nodes.build_dependency_graph,
        ["core_cf_graph_raw"],
        ["core_dependencies"],
    ),
    "compute_feedstock_health": (
        core_nodes.compute_feedstock_health,
        ["core_cf_graph_raw"],
        ["core_feedstock_health"],
    ),
    # -- vcs_health --
    "enrich_maintainers": (
        vcs_nodes.enrich_maintainers,
        ["core_cf_graph_raw"],
        ["vcs_maintainers", "vcs_package_maintainers"],
    ),
    "detect_archived_feedstocks": (
        vcs_nodes.detect_archived_feedstocks,
        ["vcs_github_api_raw"],
        ["vcs_archived_feedstocks"],
    ),
    "track_upstream_versions": (
        vcs_nodes.track_upstream_versions,
        ["vcs_github_api_raw", "vcs_gitlab_api_raw", "vcs_codeberg_api_raw"],
        ["vcs_upstream_versions"],
    ),
    "track_registry_versions": (
        vcs_nodes.track_registry_versions,
        [
            "vcs_registry_npm_raw", "vcs_registry_cran_raw", "vcs_registry_cpan_raw",
            "vcs_registry_luarocks_raw", "vcs_registry_crates_raw",
            "vcs_registry_rubygems_raw", "vcs_registry_maven_raw", "vcs_registry_nuget_raw",
        ],
        ["vcs_registry_versions"],
    ),
    "fetch_live_health": (
        vcs_nodes.fetch_live_health,
        ["vcs_github_api_raw"],
        ["vcs_live_health"],
    ),
}


def discover_fixtures() -> list[Path]:
    return sorted(FIXTURES_DIR.rglob("*.json"))


def _to_frame(records) -> pd.DataFrame:
    return pd.DataFrame(records)


def _clean_null(v):
    """Uniform null representation (None) so JSON ``null`` and pandas NaN/NA compare
    equal — future-proof against pandas raising on mismatched null-likes. List cells
    are passed through (``pd.isna`` on a list is ambiguous)."""
    if isinstance(v, list):
        return v
    return None if v is None or pd.isna(v) else v


def _normalize(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Project to the expected columns, unify nulls, sort deterministically, reset
    index — so the diff is order-independent (a parity diff is about content, not row
    order). List-valued columns (e.g. ``subdirs``, ``maintainers``) are excluded from
    the sort KEY (unhashable) but still compared."""
    proj = df[[c for c in columns if c in df.columns]].copy()
    proj = proj.map(_clean_null)
    # Deterministic order independent of input row order — even when scalar columns
    # tie and only a list column differs (B2-B4 reuse this on larger captures). Sort
    # by a stringified key of EVERY column (list cells stringify to a stable form).
    if len(proj.columns):
        key = proj.map(lambda v: repr(v))
        order = key.sort_values(list(proj.columns), kind="stable").index
        proj = proj.loc[order]
    return proj.reset_index(drop=True)


def run_fixture(path: Path) -> None:
    """Run one fixture: build input frames, call the node, diff each declared output
    against its captured legacy snapshot. Raises ``AssertionError`` on a parity diff."""
    spec = json.loads(path.read_text(encoding="utf-8"))
    node_name = spec["node"]
    func, input_names, output_names = NODE_REGISTRY[node_name]

    args = [_to_frame(spec["inputs"].get(name, [])) for name in input_names]
    result = func(*args)
    outputs = result if isinstance(result, tuple) else (result,)
    assert len(outputs) == len(output_names), (
        f"{node_name}: node returned {len(outputs)} outputs, registry declares {len(output_names)}"
    )

    expected = spec["expected"]
    for out_name, actual in zip(output_names, outputs):
        assert out_name in expected, (
            f"{path.name}: fixture 'expected' is missing declared output {out_name!r}"
        )
        exp_records = expected[out_name]
        exp = _to_frame(exp_records)
        cols = list(exp.columns) if not exp.empty else list(getattr(actual, "columns", []))
        assert_frame_equal(
            _normalize(actual, cols),
            _normalize(exp, cols),
            check_dtype=False,
            check_like=False,
        )
