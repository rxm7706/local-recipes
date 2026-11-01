"""README.md's pipeline inventory is what ``find_pipelines()`` actually discovers.

Story 27.3, closing DW-FU-20-3-2. README's Status line claimed "8 Kedro pipelines
live" and named eight while eleven were registered: ``artifactory_downloads``,
``query_plane_cache`` and ``semantic_packages`` had been added with no doc edit and
nothing noticed. A hand-maintained inventory needs a gate or it rots again.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
from kedro.framework.project import configure_project

from pyforge.atlas import pipeline_registry
from pyforge.atlas.pipeline_registry import AFTER_RUN_PIPELINES, NAMED_RUN_ONLY_PIPELINES, register_pipelines

README = Path(__file__).resolve().parents[2] / "README.md"
PIXI_TOML = Path(__file__).resolve().parents[6] / "pixi.toml"  # the repo root

# "**Status:** 11 Kedro pipelines live (`a`, `b`, ...)" -- the count and the names
# are parsed separately so a mismatch between THEM also reds.
_STATUS = re.compile(r"\*\*Status:\*\*\s+(\d+)\s+Kedro pipelines live\s+\(([^)]*)\)", re.DOTALL)


def _readme_inventory() -> tuple[int, set[str]]:
    match = _STATUS.search(README.read_text(encoding="utf-8"))
    assert match is not None, "README.md no longer carries a '**Status:** N Kedro pipelines live (...)' line"
    return int(match.group(1)), set(re.findall(r"`([a-z_]+)`", match.group(2)))


def _registered() -> set[str]:
    # register_pipelines() also exposes the "__default__" sum of every pipeline,
    # which is not a pipeline of its own.
    configure_project("pyforge.atlas")
    return {name for name in register_pipelines() if name != "__default__"}


def test_readme_names_every_registered_pipeline_and_no_others() -> None:
    _count, named = _readme_inventory()
    registered = _registered()
    assert named == registered, (
        f"README.md pipeline inventory has drifted -- missing: {sorted(registered - named)}; "
        f"stale: {sorted(named - registered)}"
    )


def test_the_readme_count_matches_the_names_it_lists() -> None:
    count, named = _readme_inventory()
    assert count == len(named)


def test_the_bootstrap_task_runs_a_documented_subset_not_the_whole_registry() -> None:
    """The bootstrap section deliberately runs nine of the twelve as one DAG (it excludes the
    entry-scoped ``universal_sbom``, the ``query_plane_cache`` cache, and ``catalog_index``, which runs
    on its own after a build, Story 37.10; ``semantic_packages`` joined with Story 38.1, since it and
    ``derived_artifacts`` read each other's outputs). Pin that so "nine" there is not read as a drifted
    count."""
    text = README.read_text(encoding="utf-8")
    assert "Materializes nine pipelines" in text
    excluded = {"universal_sbom", "query_plane_cache", "catalog_index"}
    assert excluded <= _registered()
    assert len(_registered() - excluded) == 9


def _bootstrap_task_pipelines() -> list[str]:
    task = tomllib.loads(PIXI_TOML.read_text(encoding="utf-8"))["feature"]["pyforge-atlas"]["tasks"][
        "pyforge-atlas-bootstrap"
    ]
    return task["cmd"].split("--pipelines ", 1)[1].split()[0].split(",")


def test_a_plain_run_leaves_out_what_the_bootstrap_task_leaves_out(monkeypatch: pytest.MonkeyPatch) -> None:
    """Story 34.14 (CAP-64, AC1): ``__default__`` (a plain ``pyforge atlas run``) leaves out the two pipelines the
    ``pyforge-atlas-bootstrap`` task leaves out (``catalog_index`` aside, Story 37.10): ``query_plane_cache``, whose
    estate source has no producer until Story 36.3, and the entry-scoped ``universal_sbom``. Both stay registered, so a
    run that names them still reaches them."""
    monkeypatch.setattr(pipeline_registry, "kill_switch_on", lambda _key: True)  # universal_sbom registered
    configure_project("pyforge.atlas")
    registered = register_pipelines()
    left_out = set(registered) - {"__default__"} - set(_bootstrap_task_pipelines()) - set(AFTER_RUN_PIPELINES)

    assert set(NAMED_RUN_ONLY_PIPELINES) == left_out == {"query_plane_cache", "universal_sbom"}
    default_nodes = {node.name for node in registered["__default__"].nodes}
    for name in NAMED_RUN_ONLY_PIPELINES:
        nodes = {node.name for node in registered[name].nodes}
        assert nodes, f"{name} is no longer registered with nodes"
        assert sorted(nodes & default_nodes) == [], f"{name} is inside __default__"
