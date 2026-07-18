"""Register the prototype pipelines (GENERATED — do not edit by hand).

Emitted by tools/regenerate_from_atlas.py to mirror the real pyforge-atlas
pipeline set. Re-run `pixi run -e local-recipes regenerate-kedro-viz-proto`.
"""

from kedro.pipeline import Pipeline

from pyforge.atlas_kedro_viz.pipelines import (
    core,
    derived_artifacts,
    pypi_intelligence,
    seed_gaps,
    universal_sbom,
    vcs_health,
    vulnerability,
)


def register_pipelines() -> dict[str, Pipeline]:
    pipelines = {
        "core": core.create_pipeline(),
        "derived_artifacts": derived_artifacts.create_pipeline(),
        "pypi_intelligence": pypi_intelligence.create_pipeline(),
        "seed_gaps": seed_gaps.create_pipeline(),
        "universal_sbom": universal_sbom.create_pipeline(),
        "vcs_health": vcs_health.create_pipeline(),
        "vulnerability": vulnerability.create_pipeline(),
    }
    pipelines["__default__"] = sum(pipelines.values(), Pipeline([]))
    return pipelines
