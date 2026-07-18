"""``viz`` smoke (Story C2, FR-6 / AC-3) — DAG IS VIZ-LOADABLE, OFFLINE.

Story C2 exposes ``pixi run viz`` (``kedro viz run``) so an operator inspects
dataset schemas + data lineage in the browser instead of reading orchestrator
source. This smoke does NOT launch the viz server (no socket, no browser) — it
asserts the thing the server needs: Kedro-Viz's own ``load_data`` can build the
migrated atlas DAG (catalog + pipelines) from the project OFFLINE. If the DAG is
loadable here, ``kedro viz run`` has a DAG to render.

AD-1/AD-6: ``kedro_viz`` is REPLACEABLE VISUALIZATION GLUE — it is imported ONLY
here in a test (never in package code; the package-wide import-ban in
``tests/catalog/test_no_inline_io.py`` scans the src tree, not tests). The
operator surface is the pixi ``viz`` task, not a package import.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

# atlas project root: <repo>/src/shared/packages/pyforge-atlas (parents[2] from
# tests/orchestration/<this file>: [0]=orchestration [1]=tests [2]=pyforge-atlas).
PROJECT_PATH = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_PATH.parents[3]  # pyforge-atlas -> packages -> shared -> src -> repo


def test_kedro_viz_load_data_builds_the_atlas_dag_offline():
    # No network: Wave-B datasets default to offline fetchers; the `local` env
    # resolves only placeholder creds (same offline property the dagster-dryrun
    # gate relies on). load_data returns (catalog, pipelines, node_extras).
    from kedro_viz.integrations.kedro.data_loader import load_data

    catalog, pipelines, _extras = load_data(PROJECT_PATH, env="local")

    # the seven domain pipelines + __default__ are all discoverable by viz.
    assert "__default__" in pipelines
    expected = {
        "core",
        "vcs_health",
        "pypi_intelligence",
        "vulnerability",
        "seed_gaps",
        "universal_sbom",
        "derived_artifacts",
    }
    assert expected <= set(pipelines), f"viz cannot see pipelines: {expected - set(pipelines)}"

    # the DAG has real nodes + declared datasets for viz to render lineage over.
    nodes = {n for p in pipelines.values() for n in p.nodes}
    assert len(nodes) >= 30, f"viz DAG unexpectedly small: {len(nodes)} nodes"
    assert len(list(catalog.keys())) >= 50, "viz catalog surface unexpectedly small"


def test_viz_pixi_task_is_registered():
    """The AC's 'viz task lands in the pixi task inventory' — the operator
    entrypoint exists, is scoped to the atlas project cwd, and drives kedro viz
    (so it renders THIS project's DAG, not a stray cwd's)."""
    pixi = tomllib.loads((REPO_ROOT / "pixi.toml").read_text(encoding="utf-8"))
    task = pixi["feature"]["pyforge-atlas"]["tasks"]["viz"]
    assert "kedro viz" in task["cmd"]
    assert task["cwd"] == "src/shared/packages/pyforge-atlas"
