"""FastMCP registration wrapper for the atlas MCP surface (Story B3).

``kedro-mcp`` is wrapped-where-helpful, NEVER load-bearing (spec § 4.5 /
§ 5.5, FR-7, AD-1): nothing here (or anywhere in the package) imports
``kedro_mcp``, and the trigger/read surface (``tools.py``) works with it
absent. ``fastmcp`` is imported LAZILY inside :func:`build_server` so this
module — and the whole ``pyforge.atlas.mcp`` package — imports with
neither ``fastmcp`` nor ``kedro_mcp`` installed. Registration is the only
FastMCP-touching step, matching the legacy server's ``@mcp.tool()``
patterns (``.claude/tools/conda_forge_server.py``, read-only reference).
"""

from __future__ import annotations

from pyforge.atlas.mcp import tools


def build_server(name: str = "pyforge-atlas-atlas"):
    """Build the FastMCP server exposing the thin B3 surface.

    Tool wrappers delegate 1:1 to ``tools.py`` — the bodies stay the two
    allowed shapes (AD-7): pipeline trigger + dataset read passthrough.
    """
    from fastmcp import FastMCP  # lazy: registration-time only

    mcp = FastMCP(name)

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
    def read_atlas_dataset(name: str):
        """Read a catalog dataset natively — a thin catalog.load passthrough."""
        return tools.read_dataset(name)

    @mcp.tool()
    def list_atlas_pipelines() -> list[str]:
        """List the registered atlas pipeline names."""
        return tools.list_pipelines()

    @mcp.tool()
    def list_atlas_datasets() -> list[str]:
        """List the declared catalog dataset names."""
        return tools.list_datasets()

    return mcp
