"""Register the seven modular pipelines of the target-state cf_atlas DAG."""

from kedro.pipeline import Pipeline

from pyforge.atlas_kedro_viz.pipelines import (
    core,
    pypi_intelligence,
    read_surface,
    seed_gaps,
    universal_sbom,
    vcs_health,
    vulnerability,
)


def register_pipelines() -> dict[str, Pipeline]:
    pipelines = {
        "core": core.create_pipeline(),
        "vcs_health": vcs_health.create_pipeline(),
        "pypi_intelligence": pypi_intelligence.create_pipeline(),
        "vulnerability": vulnerability.create_pipeline(),
        "universal_sbom": universal_sbom.create_pipeline(),
        "seed_gaps": seed_gaps.create_pipeline(),
        "read_surface": read_surface.create_pipeline(),
    }
    pipelines["__default__"] = sum(pipelines.values(), Pipeline([]))
    return pipelines
