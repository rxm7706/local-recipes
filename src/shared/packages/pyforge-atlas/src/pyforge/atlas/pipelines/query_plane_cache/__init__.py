"""``query_plane_cache`` pipeline (steward Story 34.2, FR-47 / canopy AD-22).

Named Kedro extract of estate tables to compressed Parquet. Auto-discovered
by ``find_pipelines()``. Atlas is the one Kedro home — not eight projects.
"""

from .pipeline import create_pipeline

__all__ = ["create_pipeline"]
