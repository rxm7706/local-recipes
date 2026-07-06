"""Register the six modular pipelines of the target-state cf_atlas DAG."""

from kedro.pipeline import Pipeline

from cf_atlas_kedro.pipelines import (
    core,
    pypi_intelligence,
    read_surface,
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
        "read_surface": read_surface.create_pipeline(),
    }
    pipelines["__default__"] = sum(pipelines.values(), Pipeline([]))
    return pipelines
