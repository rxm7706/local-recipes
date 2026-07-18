"""Project pipelines."""
from __future__ import annotations

from kedro.framework.project import find_pipelines
from kedro.pipeline import Pipeline


def register_pipelines() -> dict[str, Pipeline]:
    """Register the project's pipelines.

    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.
    """
    pipelines = find_pipelines(raise_errors=True)
    # Empty-scaffold guard (Story A1 review): sum() over zero pipelines would
    # yield int 0, not a Pipeline — seed with an empty Pipeline until A2/B1
    # register real ones.
    pipelines["__default__"] = sum(pipelines.values(), Pipeline([]))
    return pipelines
