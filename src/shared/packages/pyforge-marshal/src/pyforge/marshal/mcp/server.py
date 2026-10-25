"""Official ``mcp`` SDK registration wrapper for Marshal's tool surface (Story 18.1, 103.1).

``mcp`` is imported LAZILY inside :func:`build_server` so this module
-- and ``pyforge.marshal.mcp.tools`` -- import with the SDK absent.
Registration is the only SDK-touching step (atlas pattern). The eight
registered tools keep their names, arguments, docstrings and 1:1 delegation
to ``tools.py``; only the SDK class changed (mcp 2.x renamed ``FastMCP`` to
``MCPServer``, and the third-party ``fastmcp`` package is gone).
"""

from __future__ import annotations

import argparse
from importlib.metadata import PackageNotFoundError, version

from pyforge.marshal.mcp import tools

SERVER_NAME = "pyforge-marshal"


def build_server(name: str = SERVER_NAME):
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


def _installed_version() -> str:
    try:
        return version("pyforge-marshal")
    except PackageNotFoundError:
        return "unknown (pyforge-marshal is not installed)"


def _argparse_exit_code(code: object) -> int:
    if code is None or code == 0:
        return 0
    return code if isinstance(code, int) else 2


def main(argv: list[str] | None = None) -> int:
    """Console-script entry for ``marshal-mcp``.

    The arguments are parsed before anything else happens: ``--help`` and
    ``--version`` exit 0 and an unknown argument exits 2 (argparse's usage
    error) without reading stdin or building the server -- the cheat-sheet
    generator captures ``--help`` with the caller's stdin and a timeout. With
    no argument the server is built and serves MCP over stdio until the agent
    that launched it closes the pipe.
    """
    parser = argparse.ArgumentParser(
        prog="marshal-mcp",
        description=(
            "MCP server for pyforge-marshal, speaking MCP over stdio (newline-delimited JSON-RPC on "
            "stdin/stdout). Marshal policy registers it as [mcp_servers.marshal]; `marshal init` renders "
            "that into the loop home's .mcp.json, and `marshal preflight` starts it to prove the handshake."
        ),
        epilog=(
            "With no argument it serves stdio for the agent that launched it; --help and --version never "
            "start the server."
        ),
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="print the installed pyforge-marshal version and exit",
    )
    try:
        parsed = parser.parse_args(argv)
    except SystemExit as exc:  # argparse: 0 after --help, 2 after a usage error
        return _argparse_exit_code(exc.code)
    if parsed.version:
        print(_installed_version())
        return 0
    build_server().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
