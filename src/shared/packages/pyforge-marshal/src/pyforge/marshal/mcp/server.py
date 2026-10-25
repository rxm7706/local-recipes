"""Official ``mcp`` SDK registration wrapper for Marshal's tool surface (Story 18.1, 103.1).

``mcp`` is imported LAZILY inside :func:`build_server` so this module
— and ``pyforge.marshal.mcp.tools`` — import with the SDK absent.
Registration is the only SDK-touching step (atlas pattern).
"""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import version

from pyforge.marshal.mcp import tools


def build_server(name: str = "pyforge-marshal"):
    """Build the official MCP server exposing Marshal's named typed tools."""
    from mcp.server.mcpserver import MCPServer

    mcp = MCPServer(name)

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

    @mcp.tool()
    def marshal_watch(
        project: str | None = None,
        run: str | None = None,
        fleet: bool = False,
    ) -> dict:
        """Watch a pinned run, a station, or the fleet (structured JSON)."""
        return tools.marshal_watch(project=project, run=run, fleet=fleet)

    return mcp


def main(argv: list[str] | None = None) -> int:
    """Console-script entry for ``marshal-mcp`` (stdio MCP server)."""
    parser = argparse.ArgumentParser(
        prog="marshal-mcp",
        description=(
            "MCP server for pyforge-marshal (stdio transport). Registered in marshal policy as [mcp_servers.marshal]."
        ),
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the installed pyforge-marshal version and exit",
    )
    try:
        if argv is None:
            parsed, unknown = parser.parse_known_args()
        else:
            parsed, unknown = parser.parse_known_args(argv)
    except SystemExit as exc:
        code = exc.code
        if code is None or code == 0:
            return 0
        return int(code) if isinstance(code, int) else 2
    if unknown:
        parser.print_usage(sys.stderr)
        print(f"marshal-mcp: error: unrecognized arguments: {' '.join(unknown)}", file=sys.stderr)
        return 2
    if parsed.version:
        print(version("pyforge-marshal"))
        return 0
    build_server().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
