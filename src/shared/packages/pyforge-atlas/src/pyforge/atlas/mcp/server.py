"""Official ``mcp`` SDK registration wrapper for the atlas MCP surface.

``kedro-mcp`` is wrapped-where-helpful, NEVER load-bearing (spec § 4.5 /
§ 5.5, FR-7, AD-1): nothing here (or anywhere in the package) imports
``kedro_mcp``, and the trigger/read surface (``tools.py``) works with it
absent. ``mcp`` is imported LAZILY inside :func:`build_server` so this
module — and the whole ``pyforge.atlas.mcp`` package — imports with
the SDK absent. Registration is the only SDK-touching step. Tool wrappers
delegate 1:1 to ``tools.py`` (AD-7).
"""

from __future__ import annotations

import importlib
import sys

from pyforge.atlas.mcp import tools


def _official_mcp_server_class():
    """Load ``MCPServer`` from the PyPI ``mcp`` SDK.

    Atlas tests live under ``tests/mcp/`` and this package is
    ``pyforge.atlas.mcp``, so ``mcp`` on ``sys.path`` is often not the SDK.
    """
    from pathlib import Path

    saved_path = list(sys.path)
    shadowed: dict[str, object] = {}
    for entry in list(sys.path):
        root = Path(entry)
        normalized = str(root).replace("\\", "/")
        if "site-packages" in normalized:
            continue
        if root.name == "mcp" or ((root / "mcp").exists() and not (root / "pyforge").is_dir()):
            sys.path.remove(entry)
    for key in list(sys.modules):
        if key == "mcp" or key.startswith("mcp."):
            location = (getattr(sys.modules[key], "__file__", "") or "").replace("\\", "/")
            if "site-packages" not in location:
                shadowed[key] = sys.modules.pop(key)
    try:
        return importlib.import_module("mcp.server.mcpserver").MCPServer
    finally:
        sys.path[:] = saved_path
        sys.modules.update(shadowed)


def build_server(name: str = "pyforge-atlas-atlas"):
    """Build the official MCP server exposing the thin B3 surface."""
    MCPServer = _official_mcp_server_class()

    mcp = MCPServer(name)

    @mcp.tool()
    def run_core_pipeline() -> dict:
        """Trigger the `core` pipeline (conda-side backbone) run."""
        return tools.run_pipeline("core")

    @mcp.tool()
    def run_vcs_health_pipeline() -> dict:
        """Trigger the `vcs_health` pipeline (VCS + registry health) run."""
        return tools.run_pipeline("vcs_health")

    @mcp.tool()
    def run_pypi_intelligence_pipeline() -> dict:
        """Trigger the `pypi_intelligence` pipeline run."""
        return tools.run_pipeline("pypi_intelligence")

    @mcp.tool()
    def run_vulnerability_pipeline() -> dict:
        """Trigger the `vulnerability` pipeline (vuln intelligence) run."""
        return tools.run_pipeline("vulnerability")

    @mcp.tool()
    def run_seed_gaps_pipeline() -> dict:
        """Trigger the `seed_gaps` pipeline (READ-ONLY seed-freshness reports) run."""
        return tools.run_pipeline("seed_gaps")

    @mcp.tool()
    def run_universal_sbom_pipeline() -> dict:
        """Trigger the `universal_sbom` pipeline (§ 4.10 intake -> CycloneDX -> six-bucket match) run."""
        return tools.run_pipeline("universal_sbom")

    @mcp.tool()
    def run_derived_artifacts_pipeline() -> dict:
        """Trigger the `derived_artifacts` pipeline (full-universe CycloneDX BOM) run."""
        return tools.run_pipeline("derived_artifacts")

    @mcp.tool()
    def run_upstream_discovery_pipeline() -> dict:
        """Trigger the `upstream_discovery` pipeline (GitHub-trending discovery ingest, CAP-1) run."""
        return tools.run_pipeline("upstream_discovery")

    @mcp.tool()
    def read_atlas_dataset(name: str):
        """Read a catalog dataset, stamped with its own build provenance (AD-17):
        returns ``{schema_version, dataset, provenance_kind, build_stamp,
        build_stamp_newest, reason, value}`` — ``value`` is the JSON-coerced
        dataset read; the rest states the data's own recorded build time (a
        `fetched_at` column, a file mtime, or a live-fetch instant), or an
        honest `unavailable` + reason when no genuine provenance exists."""
        return tools.read_dataset(name)

    @mcp.tool()
    def list_atlas_pipelines() -> list[str]:
        """List the registered atlas pipeline names."""
        return tools.list_pipelines()

    @mcp.tool()
    def list_atlas_datasets() -> list[str]:
        """List the declared catalog dataset names."""
        return tools.list_datasets()

    @mcp.tool()
    def query_vizro_ai(query: str) -> dict:
        """Natural-language query -> Vizro-AI chart/insight over the BSL knowledge graph
        (D3, FR-9). The LLM backend routes through repo model-backend config (Q3 §11 — never
        a hardcoded endpoint); with no backend configured it returns a structured
        "backend not configured — attended Q3 bring-up (DW-D3)" advisory (no live LLM call)."""
        return tools.query_vizro_ai(query)

    @mcp.tool()
    def query_trending_candidates(
        period: str = "weekly",
        tier: str = "1,2",
        top: int = 25,
        not_on_cf: bool = True,
        min_stars: int = 500,
    ) -> dict:
        """Query the CAP-2 tiered/classified GitHub-trending candidate list (CAP-3,
        Story 13.3, FR-66): read-side only, offline-safe, filterable by
        period (daily|weekly|monthly|all) / tier (comma-list of 1/2/skip, or 'all') /
        top / not_on_cf / min_stars. Mirrors the `trending-candidates` CLI
        (`python -m pyforge.atlas.trending_candidates`) byte-for-byte for identical
        filters — both delegate to the same query_trending_candidates function."""
        return tools.query_trending_candidates(
            period=period,
            tier=tier,
            top=top,
            not_on_cf=not_on_cf,
            min_stars=min_stars,
        )

    return mcp
