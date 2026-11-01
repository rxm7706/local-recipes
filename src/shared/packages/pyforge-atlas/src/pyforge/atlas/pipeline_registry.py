"""Project pipelines."""

from __future__ import annotations

from kedro.framework.project import find_pipelines
from kedro.pipeline import Pipeline
from pyforge.core.flags import kill_switch_on

#: Story 37.10: pipelines that read what the others wrote, so they run after them, never inside
#: ``__default__``'s one combined DAG (Kedro would schedule a node with no upstream edge first)
AFTER_RUN_PIPELINES = ("catalog_index",)

#: Story 34.14 (CAP-64): pipelines a plain run leaves out, the two the ``pyforge-atlas-bootstrap`` task leaves out,
#: so a plain ``pyforge atlas run`` on a fresh data root exits 0. ``query_plane_cache`` reads
#: ``query_plane_estate_source``, which nothing produces until Story 36.3; Story 36.3 takes it out of this tuple.
#: ``universal_sbom`` is entry-scoped: it reads an intake file named with ``--params sbom_intake_path``. Each stays
#: registered under its own name, so ``pyforge atlas run --pipelines <name>`` and the MCP trigger still reach it.
NAMED_RUN_ONLY_PIPELINES = ("query_plane_cache", "universal_sbom")

MANIFEST_INVENTORY_FLAG_KEY = "pyforge.atlas.manifest_inventory"  # CAP-13's kill switch, spelled literally
MANIFEST_INVENTORY_PIPELINE = "universal_sbom"


def register_pipelines() -> dict[str, Pipeline]:
    """Register the project's pipelines.

    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.
    """
    pipelines = find_pipelines(raise_errors=True)
    # Epic 42 (spec-feature-flag-governance CAP-7; spec-pyforge-atlas CAP-13, Story 42.2): with the manifest
    # inventory's kill switch OFF its pipeline is not registered at all, so neither `__default__` nor a direct
    # `kedro run --pipeline universal_sbom` (or `--nodes`) reaches its gate. ON: byte-identical.
    if not kill_switch_on(MANIFEST_INVENTORY_FLAG_KEY):
        pipelines.pop(MANIFEST_INVENTORY_PIPELINE, None)
    # Empty-scaffold guard (Story A1 review): sum() over zero pipelines would
    # yield int 0, not a Pipeline — seed with an empty Pipeline until A2/B1
    # register real ones.
    left_out = AFTER_RUN_PIPELINES + NAMED_RUN_ONLY_PIPELINES
    pipelines["__default__"] = sum(
        (pipeline for name, pipeline in pipelines.items() if name not in left_out), Pipeline([])
    )
    return pipelines
