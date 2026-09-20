"""Thin MCP tool bodies (Story B3, AD-7 / AD-23 / AD-17).

Every function here does exactly ONE of the two allowed shapes:

1. ``session.run(pipeline_name=<name>)`` — a pipeline trigger, or
2. ``_provenance.load_with_provenance(catalog, <dataset>)`` — ONE seam call
   behind which the ``catalog.load`` itself AND its build-provenance
   envelope live (Story I4, AD-17).

NO metric/business logic lives here — metric semantics live in nodes
(legacy CLIs/views until D1, BSL after). Enforced by the AST scan in
``tests/mcp/test_no_business_logic_in_tool_bodies.py`` (no pandas/numpy/
duckdb/sqlite/sqlalchemy/ibis/pyarrow, no aggregation arithmetic).
"""

from __future__ import annotations

import datetime
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pyforge.core.errors import PyforgeError

from pyforge.atlas import nl as _nl
from pyforge.atlas import provenance as _provenance
from pyforge.atlas.mcp import session as _session
from pyforge.atlas.trending_candidates import query as _trending

# FR-155 inventory registry (Story 25.3): one entry per MCP tool registered on
# ``server.build_server``. ``cli`` is the argv template AFTER the program name;
# ``None`` marks a tool-only helper with no ``pyforge-atlas`` counterpart.
TOOL_SPECS: dict[str, dict[str, Any]] = {
    "run_core_pipeline": {
        "description": "Trigger the `core` pipeline run.",
        "cli": ["run", "--pipeline", "core"],
    },
    "run_vcs_health_pipeline": {
        "description": "Trigger the `vcs_health` pipeline run.",
        "cli": ["run", "--pipeline", "vcs_health"],
    },
    "run_pypi_intelligence_pipeline": {
        "description": "Trigger the `pypi_intelligence` pipeline run.",
        "cli": ["run", "--pipeline", "pypi_intelligence"],
    },
    "run_vulnerability_pipeline": {
        "description": "Trigger the `vulnerability` pipeline run.",
        "cli": ["run", "--pipeline", "vulnerability"],
    },
    "run_seed_gaps_pipeline": {
        "description": "Trigger the `seed_gaps` pipeline run.",
        "cli": ["run", "--pipeline", "seed_gaps"],
    },
    "run_universal_sbom_pipeline": {
        "description": "Trigger the `universal_sbom` pipeline run.",
        "cli": ["run", "--pipeline", "universal_sbom"],
    },
    "run_derived_artifacts_pipeline": {
        "description": "Trigger the `derived_artifacts` pipeline run.",
        "cli": ["run", "--pipeline", "derived_artifacts"],
    },
    "run_upstream_discovery_pipeline": {
        "description": "Trigger the `upstream_discovery` pipeline run.",
        "cli": ["run", "--pipeline", "upstream_discovery"],
    },
    "read_atlas_dataset": {
        "description": "Read a catalog dataset with build-provenance envelope.",
        "cli": None,
    },
    "list_atlas_pipelines": {
        "description": "List registered atlas pipeline names.",
        "cli": None,
    },
    "list_atlas_datasets": {
        "description": "List declared catalog dataset names.",
        "cli": None,
    },
    "query_vizro_ai": {
        "description": "Natural-language Vizro-AI query over the BSL graph.",
        "cli": None,
    },
    "query_trending_candidates": {
        "description": "Query tiered GitHub-trending candidates (CAP-3).",
        "cli": None,
    },
}

# The authoritative registry mirror: the four registered pipelines from
# B1/B2 (`find_pipelines()` discovers them from the pipelines/ package).
# Kept STATIC — not computed from a live registry — so list_pipelines()
# stays offline/thin; tests/mcp/test_audit_mapping.py pins this tuple
# against the real registry (the 5 create_pipeline modules). B6 added
# `seed_gaps` (the four READ-ONLY seed-freshness report nodes). NB: this is
# the generic per-PIPELINE trigger the registry-mirror invariant requires —
# the four seed-gap SUGGESTERS themselves stay CLI-only (AD-7): no per-tool
# MCP read surface is added for them.
PIPELINE_NAMES = (
    "core",
    "vcs_health",
    "pypi_intelligence",
    "vulnerability",
    "seed_gaps",
    "universal_sbom",  # B7: § 4.10 intake -> CycloneDX -> six-bucket match
    "derived_artifacts",  # B7: full-universe CycloneDX BOM (AD-15 freshness)
    "upstream_discovery",  # Story 13.1: GitHub-trending discovery ingest (CAP-1, FR-64)
)


class AtlasMCPError(PyforgeError, RuntimeError):
    """Raised for invalid MCP-surface requests (e.g. an unknown pipeline).

    Story 14.3, SPEC-pyforge-core CAP-5: gains ``PyforgeError`` as an
    additional base -- ``RuntimeError`` stays in the MRO."""


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
) -> dict[str, Any]:
    """``catalog.load(<name>)`` + a JSON-serializable coercion, wrapped in a
    build-provenance envelope (AD-7, AD-17).

    Returns ``{schema_version, dataset, provenance_kind, build_stamp,
    build_stamp_newest, reason, value}``: ``value`` is the existing coerced
    return (byte-for-byte unchanged); the rest is the dataset's OWN recorded
    build provenance (never a read-time clock stand-in) — a ``fetched_at``
    column's oldest/newest recorded value, a materialized file's mtime, or
    ``now`` for a live-fetch API source; ``unavailable`` + a reason when no
    genuine provenance exists (a required, valid, non-error response).

    The load + provenance dispatch both happen inside
    ``_provenance.load_with_provenance`` (one seam call) so the session's
    catalog is only ever built ONCE per read (``_session.loaded_catalog(s)``
    is not called a second time here).

    The coercion is TRANSPORT plumbing, not metric/business logic — most
    catalog datasets are Parquet-backed and load as a pandas/polars
    DataFrame, which FastMCP cannot serialize (a raw DataFrame return
    `TypeError`s at the MCP boundary). We coerce DataFrame / Series / ndarray
    / set to JSON-native shapes by DUCK-TYPING on the class name + public
    methods — never importing pandas/numpy — so the AD-7 no-business-logic
    AST gate stays satisfied. Anything already JSON-native is returned as-is.

    Raises whatever ``catalog.load`` raises on an unknown dataset name (the
    envelope wraps only the success path).
    """
    with _session.bootstrapped_session(project_path, env=env) as s:
        catalog = _session.loaded_catalog(s)
        result, info = _provenance.load_with_provenance(catalog, name)
    cls_name = result.__class__.__name__
    if cls_name == "DataFrame":
        # pandas: orient=records → list[row-dict]; polars: to_dicts().
        try:
            value = result.to_dict(orient="records")
        except TypeError:
            value = result.to_dicts()
    elif cls_name == "Series":
        value = result.to_dict()
    elif cls_name == "ndarray":
        value = result.tolist()
    elif cls_name == "set":
        value = list(result)
    else:
        value = result
    return {
        "schema_version": _provenance.SCHEMA_VERSION,
        "dataset": name,
        "provenance_kind": info.kind,
        "build_stamp": info.build_stamp,
        "build_stamp_newest": info.build_stamp_newest,
        "reason": info.reason,
        "value": value,
    }


def query_vizro_ai(query: str, *, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Natural-language -> Vizro chart/insight over the BSL knowledge graph (D3, FR-9).

    THIN delegation to the ``nl/`` seam (AD-7): the NL/LLM logic — backend resolution from
    repo model-backend config (Q3 §11, never a hardcoded endpoint) and the BSL-grounded
    (deferred) Vizro-AI call — lives in ``pyforge.atlas.nl``, not in this tool body. With no
    backend configured (the in-container default) the seam returns a structured
    "backend not configured — attended Q3 bring-up (DW-D3)" advisory: no network, no live LLM
    call, no fabricated chart.
    """
    return _nl.query_vizro_ai(query, env=env)


def query_trending_candidates(
    period: str = "weekly",
    tier: str = "1,2",
    top: int = 25,
    not_on_cf: bool = True,
    min_stars: int = 500,
    *,
    project_path: Path | str | None = None,
    env: str | None = None,
) -> dict[str, Any]:
    """CAP-3 operator surface (Story 13.3, FR-66): THIN delegation to the
    ``trending_candidates`` seam (AD-7) — the filter/sort/cap/validation logic (pandas)
    lives in ``pyforge.atlas.trending_candidates.query``, not in this tool body. The
    CLI (``python -m pyforge.atlas.trending_candidates``) delegates to the SAME
    function, so identical filters yield identical output by construction."""
    return _trending.query_trending_candidates(
        period=period,
        tier=tier,
        top=top,
        not_on_cf=not_on_cf,
        min_stars=min_stars,
        project_path=project_path,
        env=env,
    )


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
