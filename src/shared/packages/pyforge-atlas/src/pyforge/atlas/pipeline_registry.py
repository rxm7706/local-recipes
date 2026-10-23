"""Project pipelines."""

from __future__ import annotations

from kedro.framework.project import find_pipelines
from kedro.pipeline import Pipeline

#: Story 37.10: pipelines that read what the others wrote, so they run after them, never inside
#: ``__default__``'s one combined DAG (Kedro would schedule a node with no upstream edge first)
AFTER_RUN_PIPELINES = ("catalog_index",)


def register_pipelines() -> dict[str, Pipeline]:
    """Register the project's pipelines.

    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.
    """
    pipelines = find_pipelines(raise_errors=True)
    # Empty-scaffold guard (Story A1 review): sum() over zero pipelines would
    # yield int 0, not a Pipeline — seed with an empty Pipeline until A2/B1
    # register real ones.
    pipelines["__default__"] = sum(
        (pipeline for name, pipeline in pipelines.items() if name not in AFTER_RUN_PIPELINES), Pipeline([])
    )
    return pipelines
