"""The atlas Watch-axis gather filter -- MCP-first, CLI fallback (Story 2.1,
FR-5, AD-5/AD-6).

``gather("staleness")`` normalizes cf_atlas's ``staleness_report`` signal
into ``Finding(source=Source.STALENESS_REPORT, ...)`` tuples, one per
feedstock row (never re-aggregated -- mirrors ``sources/warden.py``'s
"never re-aggregated" rule). Two transports reach the SAME underlying data
(``conda_forge_server.py::staleness_report`` is a thin
``_run_script(ATLAS_STALENESS_SCRIPT, args)`` shim over the exact script the
CLI fallback also calls) and normalize to the identical ``Finding`` shape
(AD-6's "never diverge" rule):

* **MCP** (primary): a lazy ``mcp`` SDK import, one ``asyncio.run()``-scoped
  ``mcp.client.stdio`` session per call against the local FastMCP server at
  ``.claude/tools/conda_forge_server.py`` (``python3
  conda_forge_server.py`` spawned as the SDK's own stdio child process --
  the SDK's internal transport mechanics, not a call this package makes to
  ``subprocess`` itself, so it does not need to go through
  ``cli_bridge.py``). Mirrors ``pyforge.herald.transport.mcp_transport``'s
  proven pattern (lazy import, one-session-per-call, injectable caller
  seam), swapped from remote streamable-HTTP+OAuth to local stdio+no-auth
  (the local server has no credential layer).
* **CLI fallback**: ``cli_bridge.run_cli_json`` (AD-5's sole subprocess
  site) against ``.claude/scripts/conda-forge-expert/staleness_report.py
  --json``.

"An MCP client is available in-process" is operationalized as "the stdio
session establishes and ``initialize()`` succeeds" -- attempted every call,
never ambiently detected (there is no reliable process-level signal for
"an MCP host happens to be present" from inside a plain library call). Any
failure at any stage of the MCP attempt -- import, connection, protocol, a
non-list JSON shape -- is "no MCP client available," and falls through to
the CLI path transparently. This module never persists a session across
calls (no background-event-loop machinery -- Herald's own documented
"no session continuity needed" reasoning applies identically here).

``gather()`` never raises for a runtime/environment failure: if BOTH the
MCP and CLI paths fail, the whole call degrades to exactly one FAIL
``Finding`` naming the failure (mirrors ``sources/warden.py``'s
degrade-to-Finding contract). An unrecognized ``axis`` is the one thing
that DOES raise -- a programmer error at the call boundary, not a runtime
degrade case.

This is the ONE sanctioned ``mcp`` import site in ``pyforge.doctor``
(mirrors ``sources/warden.py``'s sole-``pyforge.warden``-import pattern);
the meta-test ``test_atlas_sole_mcp_import.py`` enforces it. The import is
LAZY -- inside the async helper, never at module import time -- so
importing this module costs nothing and a fully-faked unit test never
needs the SDK installed.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Callable

from ..cli_bridge import CliBridgeError, run_cli_json
from ..models import DoctorStatus, Finding, Source

_VALID_AXES = frozenset({"staleness"})

_MCP_TOOL_NAME = "staleness_report"

DEFAULT_TIMEOUT_SECONDS = 60.0


def _default_repo_root() -> Path:
    """Walk up from this file to the repo root -- anchored on ``.git`` (a
    unique repo-root marker) rather than a hardcoded ``parents[N]``, so this
    resolves whether the package runs from the source tree or an installed
    layout. Mirrors ``pyforge.atlas.dashboard.factory_status.default_repo_root``."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists() or (parent / "_bmad-output").is_dir():
            return parent
    return current.parents[8] if len(current.parents) > 8 else current.parent


def _default_mcp_server_script() -> Path:
    return _default_repo_root() / ".claude" / "tools" / "conda_forge_server.py"


def _default_cli_script() -> Path:
    return (
        _default_repo_root()
        / ".claude"
        / "scripts"
        / "conda-forge-expert"
        / "staleness_report.py"
    )


def _one_fail_finding(message: str) -> tuple[Finding, ...]:
    return (
        Finding(
            source=Source.STALENESS_REPORT,
            check="doctor.sources.atlas",
            status=DoctorStatus.FAIL,
            message=message,
            evidence={},
        ),
    )


def _row_check_name(row: dict[str, Any]) -> str:
    name = row.get("feedstock_name") or row.get("conda_name") or row.get("name")
    return str(name) if name else "<unknown feedstock>"


def _normalize_rows(rows: list[Any]) -> tuple[Finding, ...]:
    """One ``Finding`` per feedstock row -- never one aggregate ``Finding``
    for the whole report (mirrors ``sources/warden.py``'s "never
    re-aggregated" rule). A non-dict row degrades to its own FAIL Finding
    rather than being silently dropped or crashing the whole gather."""
    findings: list[Finding] = []
    for row in rows:
        if not isinstance(row, dict):
            findings.append(
                Finding(
                    source=Source.STALENESS_REPORT,
                    check="doctor.sources.atlas",
                    status=DoctorStatus.FAIL,
                    message=f"staleness_report returned a non-object row: {row!r}",
                    evidence={},
                )
            )
            continue
        version = row.get("latest_conda_version")
        uploaded = row.get("uploaded_iso")
        age_days = row.get("age_days")
        message = (
            f"latest_conda_version={version!s} uploaded={uploaded!s} "
            f"age_days={age_days!s}"
        )
        findings.append(
            Finding(
                source=Source.STALENESS_REPORT,
                check=_row_check_name(row),
                # A staleness signal is a drift warning, not a hard
                # failure -- the report is already filtered/sorted to
                # stale-first by construction; there is no pass/fail
                # threshold in the underlying data itself.
                status=DoctorStatus.WARN,
                message=message,
                evidence=dict(row),
            )
        )
    return tuple(findings)


# --- MCP transport -----------------------------------------------------


async def _call_staleness_mcp_async(
    server_script_path: Path, arguments: dict[str, Any], *, timeout: float
) -> str:
    """One ``asyncio.run()``-scoped stdio session: connect, initialize, call
    the tool, close. Never persisted across calls (see module docstring).
    The WHOLE session lifecycle (connect + initialize + call + close) is
    bounded by ``asyncio.wait_for(..., timeout=timeout)`` -- review finding:
    without this, a stalled local server (mid-import, deadlocked) hung
    ``gather()`` indefinitely regardless of the ``timeout`` argument passed
    in, even though the CLI fallback leg always honored it via
    ``cli_bridge``.

    The ``mcp`` import is lazy so importing ``sources.atlas`` costs nothing
    and a fake-``mcp_caller`` unit test never needs the SDK installed."""
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    async def _run() -> str:
        params = StdioServerParameters(
            command=sys.executable, args=[str(server_script_path)]
        )
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(_MCP_TOOL_NAME, arguments)
        text = "".join(
            block.text
            for block in result.content
            if getattr(block, "type", "") == "text"
        )
        if result.isError:
            raise RuntimeError(
                f"{_MCP_TOOL_NAME} MCP tool returned an error: {text}"
            )
        return text

    return await asyncio.wait_for(_run(), timeout=timeout)


def _call_staleness_mcp(
    server_script_path: Path,
    arguments: dict[str, Any],
    *,
    timeout: float,
    mcp_caller: Callable[[str, dict[str, Any]], str] | None = None,
) -> str:
    """Returns the tool's raw JSON text, or raises on ANY failure (import,
    connection, protocol, a live event loop already running, a timeout) --
    the caller treats every exception here as "no MCP client available" and
    falls back to CLI.

    ``mcp_caller`` is the injectable seam (mirrors Herald's ``caller:
    ToolCaller | None``): tests pass a fake ``(tool, arguments) -> str``
    callable instead of ever spawning a real MCP session -- ``timeout`` is
    not applied to a fake caller, since there is no real I/O to bound."""
    if mcp_caller is not None:
        return mcp_caller(_MCP_TOOL_NAME, arguments)

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass  # no loop running: `asyncio.run` is free to make one
    else:
        raise RuntimeError(
            "the synchronous atlas MCP transport cannot run inside a live "
            "event loop"
        )
    return asyncio.run(
        _call_staleness_mcp_async(server_script_path, arguments, timeout=timeout)
    )


# --- CLI fallback --------------------------------------------------------


def _call_staleness_cli(
    cli_script_path: Path,
    args: list[str],
    *,
    timeout: float,
    cli_runner: Callable[[Path, list[str]], Any] | None = None,
) -> Any:
    """Returns the parsed JSON payload, or raises ``CliBridgeError`` on any
    failure. ``cli_runner`` is the injectable seam so unit tests never
    spawn a real subprocess (mirrors ``mcp_caller`` above)."""
    if cli_runner is not None:
        return cli_runner(cli_script_path, args)
    return run_cli_json(cli_script_path, args, timeout=timeout)


# --- entrypoint ------------------------------------------------------------


def gather(
    axis: str,
    *,
    target: str | None = None,
    server_script_path: Path | None = None,
    cli_script_path: Path | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    mcp_caller: Callable[[str, dict[str, Any]], str] | None = None,
    cli_runner: Callable[[Path, list[str]], Any] | None = None,
) -> tuple[Finding, ...]:
    """Gather one atlas Watch axis's signal, MCP-first with CLI fallback.

    ``axis`` is validated against a small closed set (``{"staleness"}``
    this story) -- an unrecognized axis raises ``ValueError`` at the call
    boundary (a programmer error, not a runtime degrade case). Every other
    failure degrades to a ``Finding`` (see module docstring); no other
    exception escapes.

    ``target`` (an optional maintainer/feedstock scope) threads to both the
    MCP ``maintainer`` argument and the CLI ``--maintainer`` flag
    identically.

    ``server_script_path`` / ``cli_script_path`` default to the repo-local
    ``.claude/tools/conda_forge_server.py`` /
    ``.claude/scripts/conda-forge-expert/staleness_report.py`` -- overriding
    ``server_script_path`` with an unreachable path is the supported way to
    force the MCP path to fail and exercise CLI fallback (used by the live
    equivalence smoke test). ``mcp_caller`` / ``cli_runner`` are the
    injectable unit-test seams; neither is used outside tests."""
    if axis not in _VALID_AXES:
        raise ValueError(
            f"unknown axis {axis!r}; expected one of {sorted(_VALID_AXES)}"
        )

    server_script_path = server_script_path or _default_mcp_server_script()
    cli_script_path = cli_script_path or _default_cli_script()

    mcp_arguments: dict[str, Any] = {}
    if target is not None:
        mcp_arguments["maintainer"] = target

    cli_args = ["--json"]
    if target is not None:
        cli_args.extend(["--maintainer", target])

    mcp_error: Exception | None = None
    try:
        text = _call_staleness_mcp(
            server_script_path, mcp_arguments, timeout=timeout, mcp_caller=mcp_caller
        )
        payload = _json_loads_or_raise(text)
        if not isinstance(payload, list):
            raise ValueError(
                f"staleness_report MCP tool returned {type(payload).__name__}, "
                "expected a JSON list of feedstock rows"
            )
    except Exception as exc:  # noqa: BLE001 -- ANY MCP failure falls back to CLI;
        # deliberately `Exception`, not `BaseException` (review finding) --
        # `KeyboardInterrupt`/`SystemExit`/`GeneratorExit` must propagate
        # normally, never be silently absorbed as "no MCP client available"
        # and re-routed into a fresh CLI subprocess spawn.
        mcp_error = exc
    else:
        return _normalize_rows(payload)

    try:
        payload = _call_staleness_cli(
            cli_script_path, cli_args, timeout=timeout, cli_runner=cli_runner
        )
    except CliBridgeError as exc:
        return _one_fail_finding(
            f"staleness_report unavailable: MCP failed ({mcp_error!r}) and "
            f"CLI fallback failed ({exc!r})"
        )
    except Exception as exc:  # noqa: BLE001 -- degrade, never crash the verb
        return _one_fail_finding(
            f"staleness_report unavailable: MCP failed ({mcp_error!r}) and "
            f"CLI fallback failed unexpectedly ({exc!r})"
        )

    if not isinstance(payload, list):
        return _one_fail_finding(
            f"staleness_report unavailable: MCP failed ({mcp_error!r}) and "
            f"CLI fallback returned {type(payload).__name__}, expected a "
            "JSON list of feedstock rows"
        )
    return _normalize_rows(payload)


def _json_loads_or_raise(text: str) -> Any:
    return json.loads(text)
