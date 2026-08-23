"""FastMCP registration wrapper for Marshal's tool surface (Story 18.1).

``fastmcp`` is imported LAZILY inside :func:`build_server` so this module
— and ``pyforge.marshal.mcp.tools`` — import with FastMCP absent.
Registration is the only FastMCP-touching step (atlas pattern).
"""

from __future__ import annotations

from pyforge.marshal.mcp import tools


def build_server(name: str = "pyforge-marshal"):
    """Build the FastMCP server exposing Marshal's named typed tools."""
    from fastmcp import FastMCP  # lazy: registration-time only

    mcp = FastMCP(name)

    @mcp.tool()
    def list_marshal_tools() -> dict:
        """List Marshal MCP tool names and their CLI argv templates."""
        return tools.list_marshal_tools()

    @mcp.tool()
    def marshal_status(project: str | None = None) -> dict:
        """Fleet-wide runtime status (structured JSON from marshal status)."""
        return tools.marshal_status(project=project)

    @mcp.tool()
    def marshal_check(scope: str = "all", project: str | None = None) -> dict:
        """Run the detector registry via marshal check (structured JSON)."""
        return tools.marshal_check(scope=scope, project=project)

    @mcp.tool()
    def marshal_homes() -> dict:
        """List every discovered loop home (structured JSON)."""
        return tools.marshal_homes()

    @mcp.tool()
    def marshal_preflight(slug: str) -> dict:
        """Preflight a loop home for the given project slug."""
        return tools.marshal_preflight(slug=slug)

    @mcp.tool()
    def marshal_upstream() -> dict:
        """Report the tracked upstream contribution register."""
        return tools.marshal_upstream()

    @mcp.tool()
    def marshal_refresh(project: str | None = None, base: str | None = None) -> dict:
        """Refresh loop homes from main (structured JSON)."""
        return tools.marshal_refresh(project=project, base=base)

    return mcp


def main() -> None:
    """Console-script entry for ``marshal-mcp`` (stdio MCP server)."""
    build_server().run()


if __name__ == "__main__":
    main()
