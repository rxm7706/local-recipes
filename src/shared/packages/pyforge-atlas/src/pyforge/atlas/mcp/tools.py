"""Thin MCP tool bodies (Story B3, AD-7 / AD-23 / AD-17).

Every function here does exactly ONE of the two allowed shapes:

1. ``session.run(pipeline_name=<name>)`` — a pipeline trigger, or
2. ``catalog.load(<dataset>)`` — a dataset read passthrough.

NO metric/business logic lives here — metric semantics live in nodes
(legacy CLIs/views until D1, BSL after). Enforced by the AST scan in
``tests/mcp/test_no_business_logic_in_tool_bodies.py`` (no pandas/numpy/
duckdb/sqlite/sqlalchemy/ibis/pyarrow, no aggregation arithmetic).
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

from pyforge.atlas.mcp import session as _session

# The authoritative registry mirror: the four registered pipelines from
# B1/B2 (`find_pipelines()` discovers them from the pipelines/ package).
# Kept STATIC — not computed from a live registry — so list_pipelines()
# stays offline/thin; tests/mcp/test_audit_mapping.py pins this tuple
# against the real registry (the 4 create_pipeline modules).
PIPELINE_NAMES = ("core", "vcs_health", "pypi_intelligence", "vulnerability")


class AtlasMCPError(RuntimeError):
    """Raised for invalid MCP-surface requests (e.g. an unknown pipeline)."""


def run_pipeline(
    name: str,
    *,
    project_path: Path | str | None = None,
    extra_params: dict[str, Any] | None = None,
    env: str | None = None,
) -> dict[str, Any]:
    """Trigger the named registered pipeline through the ONE execution
    plane (AD-23): ``KedroSession.run(pipeline_name=...)``.

    Returns a thin advisory + timestamped receipt (AD-17) — the OUTPUT
    NAMES only, never the raw data (reads go through ``read_dataset``).
    """
    if name not in PIPELINE_NAMES:
        raise AtlasMCPError(f"unknown pipeline {name!r}; known: {PIPELINE_NAMES}")
    with _session.bootstrapped_session(project_path, extra_params, env) as s:
        result = s.run(pipeline_name=name)
    return {
        "pipeline": name,
        "triggered_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "outputs": sorted(result.keys()) if isinstance(result, dict) else [],
    }


def read_dataset(
    name: str,
    *,
    project_path: Path | str | None = None,
    env: str | None = None,
) -> Any:
    """``catalog.load(<name>)`` + a JSON-serializable coercion (AD-7).

    The load is the passthrough; the coercion is TRANSPORT plumbing, not
    metric/business logic — most catalog datasets are Parquet-backed and load
    as a pandas/polars DataFrame, which FastMCP cannot serialize (a raw
    DataFrame return `TypeError`s at the MCP boundary). We coerce DataFrame /
    Series / ndarray / set to JSON-native shapes by DUCK-TYPING on the class
    name + public methods — never importing pandas/numpy — so the AD-7 no-
    business-logic AST gate stays satisfied. Anything already JSON-native is
    returned as-is.

    Raises whatever ``catalog.load`` raises on an unknown dataset name.
    """
    with _session.bootstrapped_session(project_path, env=env) as s:
        result = _session.loaded_catalog(s).load(name)
    cls_name = result.__class__.__name__
    if cls_name == "DataFrame":
        # pandas: orient=records → list[row-dict]; polars: to_dicts().
        try:
            return result.to_dict(orient="records")
        except TypeError:
            return result.to_dicts()
    if cls_name == "Series":
        return result.to_dict()
    if cls_name == "ndarray":
        return result.tolist()
    if cls_name == "set":
        return list(result)
    return result


def list_pipelines(
    *,
    project_path: Path | str | None = None,
    env: str | None = None,
) -> list[str]:
    """The registered pipeline names — served from the static registry
    mirror (see PIPELINE_NAMES) so this stays offline/thin; the mirror is
    pinned against the real registry by test_audit_mapping."""
    return sorted(PIPELINE_NAMES)


def list_datasets(
    *,
    project_path: Path | str | None = None,
    env: str | None = None,
) -> list[str]:
    """The declared catalog dataset names (kedro 1.5.0: ``catalog.keys()``
    — the 1.x ``catalog.list()`` API was removed)."""
    with _session.bootstrapped_session(project_path, env=env) as s:
        return sorted(_session.loaded_catalog(s).keys())
