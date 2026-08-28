"""``semantic_packages`` pipeline -- composed dashboard-store derivation (Story 20.3,
CAP-6 / `query-plane-catalog` ruling, 2026-08-26). Named, downstream-only Kedro extract
that reads the sealed `core` + `vcs_health` pipelines' ALREADY-PRODUCED catalog outputs
and composes the `semantic_packages` primary store `build_packages_model`
(semantic/models.py) binds to. Auto-discovered by `find_pipelines()` -- zero registry
edits (`pipeline_registry.py::register_pipelines`).
"""

from .pipeline import create_pipeline

__all__ = ["create_pipeline"]
