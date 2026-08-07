"""The atlas Watch-axis gather filter -- MCP-first, CLI fallback (Stories
2.1/2.2, FR-4/FR-5, AD-5/AD-6).

``gather(axis)`` normalizes one of cf_atlas's Watch-axis signals into
``Finding`` tuples, one per underlying row (never re-aggregated -- mirrors
``sources/warden.py``'s "never re-aggregated" rule). Three axes are wired:

* ``"staleness"`` (Story 2.1) -- ``staleness_report`` -> ``Source.STALENESS_REPORT``.
* ``"cve"`` (Story 2.2) -- ``cve_watcher`` -> ``Source.CVE_WATCHER``.
* ``"abandonment"`` (Story 2.2) -- a COMPOSITE of ``feedstock_health``
  (called twice, ``--filter stuck`` and ``--filter bad``) ->
  ``Source.FEEDSTOCK_HEALTH``, plus ``release_cadence`` (client-side
  filtered to the ``decelerating``/``silent`` trend labels) ->
  ``Source.RELEASE_CADENCE``. Each sub-call keeps its own originating
  ``Source`` tag -- an "abandonment" Finding is never presented as if it
  came from one instrument (Story 2.2 AC2). A sub-call failure degrades to
  its OWN one-FAIL-Finding, tagged with ITS OWN Source, and does not stop
  the other sub-calls from running (partial degrade, not all-or-nothing --
  the three sub-calls are independent instruments).
* ``"adoption"`` (Story 4.3, FR-12, AD-9) -- a COMPOSITE of
  ``adoption_stage`` (fleet/maintainer-scoped, always attempted) and
  ``version_downloads`` (per-PACKAGE, no maintainer mode -- attempted only
  when ``target`` is given, since there is nothing fleet-wide to call it
  with), BOTH normalized under the single ``Source.ADOPTION`` tag (unlike
  ``abandonment``'s per-sub-instrument tagging -- Story 4.3 AC1 asks for one
  ``Source.ADOPTION``, not two). Opt-in only: never added to
  ``monitor --fleet``'s default axis set (Story 2.3's existing
  ``staleness``/``cve`` default is unchanged by this addition).

Every axis reaches its underlying data over the SAME two transports
(``conda_forge_server.py``'s MCP tools are thin ``_run_script(...)`` shims
over the exact scripts the CLI fallback also calls) and normalizes to the
identical ``Finding`` shape for equivalent data (AD-6's "never diverge"
rule):

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
  site) against the matching ``.claude/scripts/conda-forge-expert/*.py
  --json`` script.

"An MCP client is available in-process" is operationalized as "the stdio
session establishes and ``initialize()`` succeeds" -- attempted every call,
never ambiently detected (there is no reliable process-level signal for
"an MCP host happens to be present" from inside a plain library call). Any
failure at any stage of the MCP attempt -- import, connection, protocol, an
unexpected JSON shape -- is "no MCP client available," and falls through to
the CLI path transparently. This module never persists a session across
calls (no background-event-loop machinery -- Herald's own documented
"no session continuity needed" reasoning applies identically here).

``gather()`` never raises for a runtime/environment failure: if BOTH the
MCP and CLI paths fail for a (sub-)call, that (sub-)call degrades to
exactly one FAIL ``Finding`` naming the failure (mirrors
``sources/warden.py``'s degrade-to-Finding contract). An unrecognized
``axis`` is the one thing that DOES raise -- a programmer error at the call
boundary, not a runtime degrade case.

Multi-axis composition (Story 2.2 AC3, e.g. ``--watch staleness,cve``)
is deliberately NOT this module's job: ``gather()`` stays single-axis
(unchanged shape from Story 2.1) -- the CLI layer (Story 2.3) calls it once
per requested axis and concatenates the ``Finding`` tuples into one
``DoctorReport``. Each axis's own Findings are already individually
Source-tagged, so a plain concatenation is sufficient; adding an
axis-list parameter here would duplicate that composition for no benefit.

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

_VALID_AXES = frozenset({"staleness", "cve", "abandonment", "adoption"})

# Public alias -- Story 2.3's CLI layer validates `--watch` axis names
# against this without reaching into a leading-underscore module internal.
VALID_WATCH_AXES = _VALID_AXES

#: Which `Source` member(s) each axis's own `gather()` dispatch (above)
#: can produce -- `"abandonment"` is a composite of TWO instruments
#: (`_gather_abandonment`'s own feedstock-health + release-cadence
#: sub-sources), every other axis is a single `Source`. Public: Story 4.2's
#: `monitor --fleet --surface` uses this to recompute which axes are still
#: genuinely represented after a `--source` filter narrows `findings`
#: (review finding: recording the REQUESTED `--watch` axes verbatim, even
#: when `--source` drops an entire axis's findings, contradicted the
#: surface's own documented "exactly which axes the triggering run
#: covered" claim).
AXIS_SOURCES: dict[str, frozenset[Source]] = {
    "staleness": frozenset({Source.STALENESS_REPORT}),
    "cve": frozenset({Source.CVE_WATCHER}),
    "abandonment": frozenset({Source.FEEDSTOCK_HEALTH, Source.RELEASE_CADENCE}),
    "adoption": frozenset({Source.ADOPTION}),
}

# Trend labels release_cadence's own `_classify` can emit that count as an
# "abandonment" signal (Story 2.2 AC2) -- filtered client-side since the
# underlying tool has no `--trend` flag of its own.
_ABANDONMENT_CADENCE_TRENDS = frozenset({"decelerating", "silent"})

# feedstock_health filter_kind values Story 2.2's "abandonment" axis calls,
# one sub-call each -- deliberately NOT `--filter all` (which also covers
# ci-red/open-issues/open-prs-human, out of "abandonment"'s scope per the
# architecture spine's own decision log).
_ABANDONMENT_HEALTH_FILTERS = ("stuck", "bad")

DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_CVE_SEVERITY = "C"  # mirrors cve_watcher.py's own CLI default


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


def _default_cli_script(script_name: str) -> Path:
    return (
        _default_repo_root()
        / ".claude"
        / "scripts"
        / "conda-forge-expert"
        / script_name
    )


def _one_fail_finding(
    source: Source, message: str, *, check: str = "doctor.sources.atlas"
) -> Finding:
    return Finding(
        source=source,
        check=check,
        status=DoctorStatus.FAIL,
        message=message,
        evidence={},
    )


def _row_check_name(row: dict[str, Any]) -> str:
    name = row.get("feedstock_name") or row.get("conda_name") or row.get("name")
    return str(name) if name else "<unknown feedstock>"


def _normalize_staleness_rows(rows: list[Any]) -> tuple[Finding, ...]:
    """One ``Finding`` per feedstock row -- never one aggregate ``Finding``
    for the whole report (mirrors ``sources/warden.py``'s "never
    re-aggregated" rule). A non-dict row degrades to its own FAIL Finding
    rather than being silently dropped or crashing the whole gather."""
    findings: list[Finding] = []
    for row in rows:
        if not isinstance(row, dict):
            findings.append(
                _one_fail_finding(
                    Source.STALENESS_REPORT,
                    f"staleness_report returned a non-object row: {row!r}",
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


def _normalize_cve_rows(rows: list[Any], *, severity: str) -> tuple[Finding, ...]:
    """One ``Finding`` per ``cve_watcher`` row, tagged ``Source.CVE_WATCHER``
    (Story 2.2 AC1). An increase in the watched severity's affecting-count
    (``delta > 0``) is a real regression -- ``FAIL``; any other change
    (including a decrease) is informational -- ``WARN``, mirroring
    staleness's own "no pass/fail threshold in the underlying data itself"
    reasoning for a signal that is, at bottom, a drift report."""
    findings: list[Finding] = []
    for row in rows:
        if not isinstance(row, dict):
            findings.append(
                _one_fail_finding(
                    Source.CVE_WATCHER,
                    f"cve_watcher returned a non-object row: {row!r}",
                )
            )
            continue
        delta = row.get("delta")
        now_v = row.get("now_v")
        then_v = row.get("then_v")
        message = (
            f"severity={severity} then={then_v!s} now={now_v!s} "
            f"delta={delta!s} latest_conda_version={row.get('latest_conda_version')!s}"
        )
        findings.append(
            Finding(
                source=Source.CVE_WATCHER,
                check=_row_check_name(row),
                status=DoctorStatus.FAIL
                if isinstance(delta, (int, float)) and delta > 0
                else DoctorStatus.WARN,
                message=message,
                evidence=dict(row, severity=severity),
            )
        )
    return tuple(findings)


def _normalize_feedstock_health_rows(
    rows: list[Any], *, filter_kind: str
) -> tuple[Finding, ...]:
    """One ``Finding`` per ``feedstock_health`` row, tagged
    ``Source.FEEDSTOCK_HEALTH`` (Story 2.2 AC2, the "abandonment" axis's
    first sub-instrument). ``filter_kind == "bad"`` (cf-graph's own
    ``feedstock_bad`` flag) is a harder signal than ``"stuck"`` (the bot
    merely has open version-update errors) -- ``FAIL`` vs. ``WARN``."""
    findings: list[Finding] = []
    for row in rows:
        if not isinstance(row, dict):
            findings.append(
                _one_fail_finding(
                    Source.FEEDSTOCK_HEALTH,
                    f"feedstock_health returned a non-object row: {row!r}",
                )
            )
            continue
        message = (
            f"filter={filter_kind} bot_version_errors_count="
            f"{row.get('bot_version_errors_count')!s} feedstock_bad="
            f"{row.get('feedstock_bad')!s} bot_open_pr_count="
            f"{row.get('bot_open_pr_count')!s}"
        )
        findings.append(
            Finding(
                source=Source.FEEDSTOCK_HEALTH,
                check=_row_check_name(row),
                status=DoctorStatus.FAIL
                if filter_kind == "bad"
                else DoctorStatus.WARN,
                message=message,
                evidence=dict(row, filter_kind=filter_kind),
            )
        )
    return tuple(findings)


def _normalize_release_cadence_rows(rows: list[Any]) -> tuple[Finding, ...]:
    """One ``Finding`` per ``release_cadence`` row whose ``trend`` label is
    ``decelerating``/``silent`` (Story 2.2 AC2, the "abandonment" axis's
    second sub-instrument) -- ``accelerating``/``stable``/``one-version``
    rows are not an abandonment signal and are silently excluded (never a
    failure, never a Finding). ``silent`` (zero releases in 365 days) is
    the harder signal -- ``FAIL`` vs. ``WARN`` for ``decelerating``."""
    findings: list[Finding] = []
    for row in rows:
        if not isinstance(row, dict):
            findings.append(
                _one_fail_finding(
                    Source.RELEASE_CADENCE,
                    f"release_cadence returned a non-object row: {row!r}",
                )
            )
            continue
        trend = row.get("trend")
        if trend not in _ABANDONMENT_CADENCE_TRENDS:
            continue
        message = (
            f"trend={trend} releases_30d={row.get('releases_30d')!s} "
            f"releases_90d={row.get('releases_90d')!s} "
            f"releases_365d={row.get('releases_365d')!s}"
        )
        findings.append(
            Finding(
                source=Source.RELEASE_CADENCE,
                check=_row_check_name(row),
                status=DoctorStatus.FAIL if trend == "silent" else DoctorStatus.WARN,
                message=message,
                evidence=dict(row),
            )
        )
    return tuple(findings)


# adoption_stage's own `_classify` labels (see the skill script) that count
# as a real health signal -- "silent" (no release in 730 days) is the
# harder signal, mirroring release_cadence's own decelerating/silent split.
_ADOPTION_DECLINING_STAGES = frozenset({"declining"})
_ADOPTION_SILENT_STAGES = frozenset({"silent"})


def _normalize_adoption_stage_rows(rows: list[Any]) -> tuple[Finding, ...]:
    """One ``Finding`` per ``adoption_stage`` row, tagged
    ``Source.ADOPTION`` (Story 4.3 AC1). ``stage in {"declining", "silent"}``
    is a real abandonment-adjacent signal (``"silent"`` -- FAIL -- being the
    harder of the two); every other stage (``bleeding-edge``/``stable``/
    ``mature``/``unknown``) is informational -- WARN would overstate a
    healthy or merely-unclassified package, so those stay OK."""
    findings: list[Finding] = []
    for row in rows:
        if not isinstance(row, dict):
            findings.append(
                _one_fail_finding(
                    Source.ADOPTION,
                    f"adoption_stage returned a non-object row: {row!r}",
                )
            )
            continue
        stage = row.get("stage")
        message = (
            f"stage={stage} age_days={row.get('age_days')!s} "
            f"releases_30d={row.get('releases_30d')!s} "
            f"total_downloads={row.get('total_downloads')!s}"
        )
        if stage in _ADOPTION_SILENT_STAGES:
            status = DoctorStatus.FAIL
        elif stage in _ADOPTION_DECLINING_STAGES:
            status = DoctorStatus.WARN
        else:
            status = DoctorStatus.OK
        findings.append(
            Finding(
                source=Source.ADOPTION,
                check=_row_check_name(row),
                status=status,
                message=message,
                evidence=dict(row),
            )
        )
    return tuple(findings)


def _normalize_version_downloads_rows(
    rows: list[Any], *, package: str
) -> tuple[Finding, ...]:
    """One ``Finding`` per ``version_downloads`` row, tagged
    ``Source.ADOPTION`` (Story 4.3 AC1's second sub-instrument). Rows carry
    NO package-identity field of their own (the underlying query is already
    scoped to one ``name`` -- see the skill script's own SELECT) -- ``check``
    is set to the ``package`` this sub-call was made FOR, injected the same
    way ``_normalize_cve_rows`` injects ``severity`` into its own evidence.
    Purely informational supplementary evidence for ``adoption_stage``'s own
    verdict (a single version's download count implies no health signal by
    itself) -- always OK, never WARN/FAIL on its own."""
    findings: list[Finding] = []
    for row in rows:
        if not isinstance(row, dict):
            findings.append(
                _one_fail_finding(
                    Source.ADOPTION,
                    f"version_downloads returned a non-object row: {row!r}",
                )
            )
            continue
        message = (
            f"version={row.get('version')!s} "
            f"total_downloads={row.get('total_downloads')!s}"
        )
        findings.append(
            Finding(
                source=Source.ADOPTION,
                check=package,
                status=DoctorStatus.OK,
                message=message,
                evidence=dict(row, conda_name=package),
            )
        )
    return tuple(findings)


# --- MCP transport -----------------------------------------------------


async def _call_mcp_async(
    server_script_path: Path,
    tool_name: str,
    arguments: dict[str, Any],
    *,
    timeout: float,
) -> str:
    """One ``asyncio.run()``-scoped stdio session: connect, initialize, call
    the tool, close. Never persisted across calls (see module docstring).
    The WHOLE session lifecycle (connect + initialize + call + close) is
    bounded by ``asyncio.wait_for(..., timeout=timeout)`` -- review finding
    (Story 2.1): without this, a stalled local server (mid-import,
    deadlocked) hung ``gather()`` indefinitely regardless of the ``timeout``
    argument passed in, even though the CLI fallback leg always honored it
    via ``cli_bridge``.

    ``tool_name`` is now a parameter (Story 2.2 -- was hardcoded to
    ``"staleness_report"`` in Story 2.1) so every axis's MCP call shares
    this one transport implementation rather than duplicating it per tool.

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
                result = await session.call_tool(tool_name, arguments)
        text = "".join(
            block.text
            for block in result.content
            if getattr(block, "type", "") == "text"
        )
        if result.isError:
            raise RuntimeError(f"{tool_name} MCP tool returned an error: {text}")
        return text

    return await asyncio.wait_for(_run(), timeout=timeout)


def _call_mcp(
    server_script_path: Path,
    tool_name: str,
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
        return mcp_caller(tool_name, arguments)

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
        _call_mcp_async(server_script_path, tool_name, arguments, timeout=timeout)
    )


# --- CLI fallback --------------------------------------------------------


def _call_cli(
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


# --- shared MCP-first/CLI-fallback fetch, one tool call at a time -------


class _FetchFailed(Exception):
    """Both the MCP and CLI transports failed (or returned an unexpected
    shape) for ONE tool call. Caught by the calling axis and turned into
    exactly one FAIL ``Finding`` tagged with that axis's own ``Source`` --
    never propagates out of :func:`gather`."""


def _extract_list_rows(payload: Any) -> list[Any]:
    """``staleness_report``/``feedstock_health``/``release_cadence`` all
    print a bare JSON list of rows."""
    if not isinstance(payload, list):
        raise ValueError(
            f"expected a JSON list of rows, got {type(payload).__name__}"
        )
    return payload


def _extract_cve_rows(payload: Any) -> list[Any]:
    """``cve_watcher`` prints ``{"meta": {...}, "rows": [...]}`` -- read the
    live script's own ``--json`` shape (confirmed 2026-08-07) before writing
    this, per Story 2.1's own Design Notes precedent of never assuming a
    tool's JSON shape."""
    if not isinstance(payload, dict) or not isinstance(payload.get("rows"), list):
        raise ValueError(
            "expected a JSON object with a 'rows' list, got "
            f"{type(payload).__name__}"
        )
    return payload["rows"]


def _fetch_rows(
    *,
    tool_name: str,
    mcp_arguments: dict[str, Any],
    cli_script_path: Path,
    cli_args: list[str],
    server_script_path: Path,
    timeout: float,
    mcp_caller: Callable[[str, dict[str, Any]], str] | None,
    cli_runner: Callable[[Path, list[str]], Any] | None,
    extract_rows: Callable[[Any], list[Any]],
) -> list[Any]:
    """MCP-first, CLI-fallback fetch of ONE atlas tool's rows -- the one
    shared implementation every axis (staleness, cve, and abandonment's two
    sub-instruments) calls, so the MCP-first/CLI-fallback rule (AD-6) lives
    in exactly one place rather than being re-proven per axis.

    ``extract_rows`` adapts a tool's raw JSON payload to a plain list of row
    dicts (see :func:`_extract_list_rows`/:func:`_extract_cve_rows`) and
    raises ``ValueError`` itself for an unexpected shape -- folded into the
    same degrade path as every other failure.

    Raises :class:`_FetchFailed` (never a raw MCP/CLI exception) when BOTH
    transports fail; returns the extracted rows otherwise."""
    mcp_error: Exception | None = None
    try:
        text = _call_mcp(
            server_script_path,
            tool_name,
            mcp_arguments,
            timeout=timeout,
            mcp_caller=mcp_caller,
        )
        payload = _json_loads_or_raise(text)
        rows = extract_rows(payload)
    except Exception as exc:  # noqa: BLE001 -- ANY MCP failure falls back to
        # CLI; deliberately `Exception`, not `BaseException` (Story 2.1
        # review finding) -- `KeyboardInterrupt`/`SystemExit`/`GeneratorExit`
        # must propagate normally, never be silently absorbed as "no MCP
        # client available" and re-routed into a fresh CLI subprocess spawn.
        mcp_error = exc
    else:
        return rows

    try:
        payload = _call_cli(cli_script_path, cli_args, timeout=timeout, cli_runner=cli_runner)
        rows = extract_rows(payload)
    except CliBridgeError as exc:
        raise _FetchFailed(
            f"{tool_name} unavailable: MCP failed ({mcp_error!r}) and CLI "
            f"fallback failed ({exc!r})"
        ) from exc
    except Exception as exc:  # noqa: BLE001 -- degrade, never crash the verb
        raise _FetchFailed(
            f"{tool_name} unavailable: MCP failed ({mcp_error!r}) and CLI "
            f"fallback failed unexpectedly ({exc!r})"
        ) from exc
    return rows


# --- per-axis gather -----------------------------------------------------


def _gather_staleness(
    *,
    target: str | None,
    server_script_path: Path,
    cli_script_path: Path | None,
    timeout: float,
    mcp_caller: Callable[[str, dict[str, Any]], str] | None,
    cli_runner: Callable[[Path, list[str]], Any] | None,
) -> tuple[Finding, ...]:
    mcp_arguments: dict[str, Any] = {}
    if target is not None:
        mcp_arguments["maintainer"] = target
    cli_args = ["--json"]
    if target is not None:
        cli_args.extend(["--maintainer", target])

    try:
        rows = _fetch_rows(
            tool_name="staleness_report",
            mcp_arguments=mcp_arguments,
            cli_script_path=cli_script_path or _default_cli_script("staleness_report.py"),
            cli_args=cli_args,
            server_script_path=server_script_path,
            timeout=timeout,
            mcp_caller=mcp_caller,
            cli_runner=cli_runner,
            extract_rows=_extract_list_rows,
        )
    except _FetchFailed as exc:
        return (_one_fail_finding(Source.STALENESS_REPORT, str(exc)),)
    return _normalize_staleness_rows(rows)


def _gather_cve(
    *,
    target: str | None,
    severity: str,
    server_script_path: Path,
    cli_script_path: Path | None,
    timeout: float,
    mcp_caller: Callable[[str, dict[str, Any]], str] | None,
    cli_runner: Callable[[Path, list[str]], Any] | None,
) -> tuple[Finding, ...]:
    mcp_arguments: dict[str, Any] = {"severity": severity}
    if target is not None:
        mcp_arguments["maintainer"] = target
    cli_args = ["--json", "--severity", severity]
    if target is not None:
        cli_args.extend(["--maintainer", target])

    try:
        rows = _fetch_rows(
            tool_name="cve_watcher",
            mcp_arguments=mcp_arguments,
            cli_script_path=cli_script_path or _default_cli_script("cve_watcher.py"),
            cli_args=cli_args,
            server_script_path=server_script_path,
            timeout=timeout,
            mcp_caller=mcp_caller,
            cli_runner=cli_runner,
            extract_rows=_extract_cve_rows,
        )
    except _FetchFailed as exc:
        return (_one_fail_finding(Source.CVE_WATCHER, str(exc)),)
    return _normalize_cve_rows(rows, severity=severity)


def _gather_abandonment(
    *,
    target: str | None,
    server_script_path: Path,
    timeout: float,
    mcp_caller: Callable[[str, dict[str, Any]], str] | None,
    cli_runner: Callable[[Path, list[str]], Any] | None,
) -> tuple[Finding, ...]:
    """Composite of ``feedstock_health`` (``stuck``/``bad``, two independent
    sub-calls) and ``release_cadence`` (client-filtered to
    ``decelerating``/``silent``) -- three sub-calls total, each with its own
    MCP-first/CLI-fallback fetch and its own degrade-to-FAIL-Finding on
    total failure, so one sub-instrument being unreachable never hides the
    other two's Findings (unlike the single-tool axes, this axis is NOT
    all-or-nothing). No ``cli_script_path`` override parameter here -- three
    different underlying scripts are involved, so (unlike the single-tool
    axes) there is no one path a caller could sensibly override; only
    ``server_script_path`` (to force MCP failure) is supported."""
    findings: list[Finding] = []
    mcp_arguments_base: dict[str, Any] = {}
    if target is not None:
        mcp_arguments_base["maintainer"] = target

    for filter_kind in _ABANDONMENT_HEALTH_FILTERS:
        mcp_arguments = dict(mcp_arguments_base, filter_kind=filter_kind)
        cli_args = ["--json", "--filter", filter_kind]
        if target is not None:
            cli_args.extend(["--maintainer", target])
        try:
            rows = _fetch_rows(
                tool_name="feedstock_health",
                mcp_arguments=mcp_arguments,
                cli_script_path=_default_cli_script("feedstock_health.py"),
                cli_args=cli_args,
                server_script_path=server_script_path,
                timeout=timeout,
                mcp_caller=mcp_caller,
                cli_runner=cli_runner,
                extract_rows=_extract_list_rows,
            )
        except _FetchFailed as exc:
            findings.append(_one_fail_finding(Source.FEEDSTOCK_HEALTH, str(exc)))
        else:
            findings.extend(
                _normalize_feedstock_health_rows(rows, filter_kind=filter_kind)
            )

    cli_args = ["--json"]
    if target is not None:
        cli_args.extend(["--maintainer", target])
    try:
        rows = _fetch_rows(
            tool_name="release_cadence",
            mcp_arguments=dict(mcp_arguments_base),
            cli_script_path=_default_cli_script("release_cadence.py"),
            cli_args=cli_args,
            server_script_path=server_script_path,
            timeout=timeout,
            mcp_caller=mcp_caller,
            cli_runner=cli_runner,
            extract_rows=_extract_list_rows,
        )
    except _FetchFailed as exc:
        findings.append(_one_fail_finding(Source.RELEASE_CADENCE, str(exc)))
    else:
        findings.extend(_normalize_release_cadence_rows(rows))

    return tuple(findings)


def _gather_adoption(
    *,
    target: str | None,
    server_script_path: Path,
    timeout: float,
    mcp_caller: Callable[[str, dict[str, Any]], str] | None,
    cli_runner: Callable[[Path, list[str]], Any] | None,
) -> tuple[Finding, ...]:
    """Composite of ``adoption_stage`` (always attempted, fleet/maintainer
    scoped) and ``version_downloads`` (per-package, only attempted when
    ``target`` is given -- the underlying tool has no fleet-wide/maintainer
    mode of its own, see module docstring) -- both normalized under
    ``Source.ADOPTION`` (Story 4.3 AC1), each with its own independent
    degrade-to-FAIL-Finding on failure (mirrors ``_gather_abandonment``'s own
    partial-degrade discipline: one sub-instrument failing never hides the
    other's Findings). No ``cli_script_path`` override parameter -- same
    rationale as ``_gather_abandonment``: two different underlying scripts,
    no one path a caller could sensibly override."""
    findings: list[Finding] = []

    mcp_arguments: dict[str, Any] = {}
    if target is not None:
        mcp_arguments["maintainer"] = target
    cli_args = ["--json"]
    if target is not None:
        cli_args.extend(["--maintainer", target])
    try:
        rows = _fetch_rows(
            tool_name="adoption_stage",
            mcp_arguments=mcp_arguments,
            cli_script_path=_default_cli_script("adoption_stage.py"),
            cli_args=cli_args,
            server_script_path=server_script_path,
            timeout=timeout,
            mcp_caller=mcp_caller,
            cli_runner=cli_runner,
            extract_rows=_extract_list_rows,
        )
    except _FetchFailed as exc:
        findings.append(_one_fail_finding(Source.ADOPTION, str(exc)))
    else:
        findings.extend(_normalize_adoption_stage_rows(rows))

    if target is not None:
        try:
            rows = _fetch_rows(
                tool_name="version_downloads",
                mcp_arguments={"name": target},
                cli_script_path=_default_cli_script("version_downloads.py"),
                cli_args=["--json", target],
                server_script_path=server_script_path,
                timeout=timeout,
                mcp_caller=mcp_caller,
                cli_runner=cli_runner,
                extract_rows=_extract_list_rows,
            )
        except _FetchFailed as exc:
            findings.append(_one_fail_finding(Source.ADOPTION, str(exc)))
        else:
            findings.extend(_normalize_version_downloads_rows(rows, package=target))

    return tuple(findings)


# --- entrypoint ------------------------------------------------------------


def gather(
    axis: str,
    *,
    target: str | None = None,
    server_script_path: Path | None = None,
    cli_script_path: Path | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    cve_severity: str = DEFAULT_CVE_SEVERITY,
    mcp_caller: Callable[[str, dict[str, Any]], str] | None = None,
    cli_runner: Callable[[Path, list[str]], Any] | None = None,
) -> tuple[Finding, ...]:
    """Gather one atlas Watch axis's signal, MCP-first with CLI fallback.

    ``axis`` is validated against a small closed set (``{"staleness",
    "cve", "abandonment", "adoption"}`` as of Story 4.3) -- an unrecognized axis raises
    ``ValueError`` at the call boundary (a programmer error, not a runtime
    degrade case). Every other failure degrades to a ``Finding`` (see
    module docstring); no other exception escapes.

    ``target`` (an optional maintainer/feedstock scope) threads to every
    underlying tool's MCP ``maintainer`` argument and CLI ``--maintainer``
    flag identically.

    ``server_script_path`` defaults to the repo-local
    ``.claude/tools/conda_forge_server.py`` -- overriding it with an
    unreachable path is the supported way to force the MCP path to fail and
    exercise CLI fallback (used by the live equivalence smoke test).
    ``cli_script_path`` is honored for the single-tool axes
    (``"staleness"``/``"cve"``); the ``"abandonment"`` composite ignores it
    (see :func:`_gather_abandonment`'s docstring). ``cve_severity`` (default
    ``"C"``, mirroring ``cve_watcher.py``'s own CLI default) scopes the
    ``"cve"`` axis to one severity band -- ``{"C", "H", "K", "T"}``, not
    independently validated here (an unrecognized value is forwarded as-is
    and rejected by the underlying tool, surfacing as an ordinary MCP/CLI
    failure). ``mcp_caller`` / ``cli_runner`` are the injectable unit-test
    seams; neither is used outside tests."""
    if axis not in _VALID_AXES:
        raise ValueError(
            f"unknown axis {axis!r}; expected one of {sorted(_VALID_AXES)}"
        )

    server_script_path = server_script_path or _default_mcp_server_script()

    if axis == "staleness":
        return _gather_staleness(
            target=target,
            server_script_path=server_script_path,
            cli_script_path=cli_script_path,
            timeout=timeout,
            mcp_caller=mcp_caller,
            cli_runner=cli_runner,
        )
    if axis == "cve":
        return _gather_cve(
            target=target,
            severity=cve_severity,
            server_script_path=server_script_path,
            cli_script_path=cli_script_path,
            timeout=timeout,
            mcp_caller=mcp_caller,
            cli_runner=cli_runner,
        )
    if axis == "abandonment":
        return _gather_abandonment(
            target=target,
            server_script_path=server_script_path,
            timeout=timeout,
            mcp_caller=mcp_caller,
            cli_runner=cli_runner,
        )
    # axis == "adoption" (the only remaining member of _VALID_AXES)
    return _gather_adoption(
        target=target,
        server_script_path=server_script_path,
        timeout=timeout,
        mcp_caller=mcp_caller,
        cli_runner=cli_runner,
    )


def _json_loads_or_raise(text: str) -> Any:
    return json.loads(text)
