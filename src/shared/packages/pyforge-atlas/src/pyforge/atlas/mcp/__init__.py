"""Atlas MCP surface authored over Kedro session/catalog APIs (Story B3).

The CFE-agent-facing MCP surface, re-authored over the KEDRO APIs directly
(``KedroSession`` / ``DataCatalog``) — NOT over ``kedro-mcp``, which is
wrapped-where-helpful, never load-bearing (spec § 4.5 / § 5.5, FR-7, AD-1).

Design invariants honored here:

- **AD-7 (thin tool bodies)** — a tool body does exactly two shapes of
  thing: a ``catalog.load(<dataset>)`` passthrough or a
  ``session.run(pipeline_name=<name>)`` trigger. No metric/business logic
  ever lives in a tool body (AST-enforced by
  ``tests/mcp/test_no_business_logic_in_tool_bodies.py``).
- **AD-23 (one execution plane)** — an MCP trigger rides the identical
  ``KedroSession`` machinery (runner, hooks, profile) as a CLI run; there
  is no bespoke node-invocation path.
- **AD-1 (import direction)** — nothing in this package imports
  ``kedro_mcp`` or ``dagster`` (structurally enforced by
  ``tests/catalog/test_no_inline_io.py::test_ad1_import_direction``).

``.server`` (the FastMCP registration wrapper) is deliberately NOT imported
here — ``fastmcp`` stays a lazy, registration-time-only dependency so the
trigger/read surface imports with neither ``fastmcp`` nor ``kedro_mcp``
present.
"""

from __future__ import annotations

from pyforge.atlas.mcp.tools import (
    PIPELINE_NAMES,
    AtlasMCPError,
    list_datasets,
    list_pipelines,
    query_vizro_ai,
    read_dataset,
    run_pipeline,
)

__all__ = [
    "PIPELINE_NAMES",
    "AtlasMCPError",
    "list_datasets",
    "list_pipelines",
    "query_vizro_ai",
    "read_dataset",
    "run_pipeline",
]
