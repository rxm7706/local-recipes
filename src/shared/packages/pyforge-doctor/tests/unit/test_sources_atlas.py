"""Unit tests for ``pyforge.doctor.sources.atlas`` (Story 2.1) -- covers
every row of the spec's I/O & Edge-Case Matrix. The MCP path is faked via
the injectable ``mcp_caller`` seam and the CLI path via the injectable
``cli_runner`` seam (mirrors Herald's ``caller: ToolCaller | None``
pattern) -- this suite never spawns a real subprocess or opens a real MCP
session."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from pyforge.doctor.cli_bridge import CliBridgeError
from pyforge.doctor.models import DoctorStatus, Finding, Source
from pyforge.doctor.sources.atlas import _call_mcp_async, gather

_ROWS = [
    {
        "conda_name": "some-package",
        "feedstock_name": "some-package-feedstock",
        "latest_conda_version": "1.2.3",
        "latest_conda_upload": 1700000000,
        "age_days": 400,
        "uploaded_iso": "2023-11-14",
        "total_downloads": 12345,
        "recipe_format": "v1",
        "feedstock_archived": 0,
    },
    {
        "conda_name": "another-package",
        "feedstock_name": "another-package-feedstock",
        "latest_conda_version": "0.9.0",
        "latest_conda_upload": 1650000000,
        "age_days": 900,
        "uploaded_iso": "2022-04-15",
        "total_downloads": 42,
        "recipe_format": "v0",
        "feedstock_archived": 0,
    },
]


def _mcp_ok(rows=None):
    def caller(tool: str, arguments: dict) -> str:
        assert tool == "staleness_report"
        return json.dumps(rows if rows is not None else _ROWS)

    return caller


def _mcp_raises(exc: BaseException):
    def caller(tool: str, arguments: dict) -> str:
        raise exc

    return caller


def _cli_ok(rows=None):
    def runner(script_path: Path, args: list[str]):
        return rows if rows is not None else _ROWS

    return runner


def _cli_raises(exc: BaseException):
    def runner(script_path: Path, args: list[str]):
        raise exc

    return runner


# --- MCP path succeeds -------------------------------------------------


def test_mcp_success_returns_one_finding_per_row():
    findings = gather("staleness", mcp_caller=_mcp_ok())

    assert len(findings) == 2
    for finding, row in zip(findings, _ROWS):
        assert isinstance(finding, Finding)
        assert finding.source is Source.STALENESS_REPORT
        assert finding.check == row["feedstock_name"]
        assert finding.status is DoctorStatus.WARN
        assert row["latest_conda_version"] in finding.message
        assert row["uploaded_iso"] in finding.message
        assert str(row["age_days"]) in finding.message
        assert finding.evidence == row


def test_mcp_success_never_calls_cli_runner():
    def cli_runner_should_not_run(script_path, args):
        raise AssertionError("CLI fallback must not run when MCP succeeds")

    findings = gather(
        "staleness", mcp_caller=_mcp_ok(), cli_runner=cli_runner_should_not_run
    )
    assert len(findings) == 2


# --- MCP unreachable, CLI fallback succeeds -----------------------------


def test_mcp_unreachable_falls_back_to_cli_transparently():
    findings = gather(
        "staleness",
        mcp_caller=_mcp_raises(ConnectionError("simulated: server unreachable")),
        cli_runner=_cli_ok(),
    )

    assert len(findings) == 2
    for finding, row in zip(findings, _ROWS):
        assert finding.source is Source.STALENESS_REPORT
        assert finding.check == row["feedstock_name"]
        assert finding.status is DoctorStatus.WARN
        assert finding.evidence == row


def test_keyboard_interrupt_during_mcp_call_propagates_not_swallowed():
    """Review finding (Blind Hunter + Edge Case Hunter, converged): the MCP
    call site used to catch `BaseException`, so a `KeyboardInterrupt` (e.g.
    Ctrl-C while the stdio session is in flight) was silently absorbed and
    execution fell through into a fresh CLI subprocess spawn. Narrowed to
    `Exception` -- a `KeyboardInterrupt`/`SystemExit` must propagate,
    never be treated as "no MCP client available"."""

    def cli_runner_should_not_run(script_path, args):
        raise AssertionError(
            "CLI fallback must not run for a propagated KeyboardInterrupt"
        )

    with pytest.raises(KeyboardInterrupt):
        gather(
            "staleness",
            mcp_caller=_mcp_raises(KeyboardInterrupt()),
            cli_runner=cli_runner_should_not_run,
        )


def test_mcp_transport_is_bounded_by_the_timeout_argument(monkeypatch):
    """Review finding (Blind Hunter + Edge Case Hunter, converged): `timeout`
    must bound the WHOLE MCP session lifecycle (connect + initialize +
    call + close), not just the CLI fallback leg -- a stalled local server
    must not hang indefinitely regardless of the `timeout` argument passed
    in. Exercises the REAL `_call_mcp_async` (not the `mcp_caller` fake,
    which bypasses the async transport entirely) against a `stdio_client`
    that never completes."""
    import mcp.client.stdio as stdio_module

    class _HangingStdioClient:
        def __init__(self, params):
            pass

        async def __aenter__(self):
            await asyncio.sleep(10)
            raise AssertionError("should have timed out before this point")

        async def __aexit__(self, *exc_info):
            return False

    monkeypatch.setattr(stdio_module, "stdio_client", _HangingStdioClient)

    with pytest.raises(TimeoutError):
        asyncio.run(
            _call_mcp_async(
                Path("/nonexistent"), "staleness_report", {}, timeout=0.05
            )
        )


def test_mcp_non_list_payload_falls_back_to_cli():
    # A shape-drifted (or error-envelope) MCP payload must not be silently
    # accepted as "zero rows" -- it counts as an MCP failure and falls
    # through to CLI, same as a connection failure.
    findings = gather(
        "staleness",
        mcp_caller=lambda tool, args: json.dumps({"error": "script not found"}),
        cli_runner=_cli_ok(),
    )
    assert len(findings) == 2


# --- equivalence: MCP-path and CLI-path produce identical Finding sets --


def test_mcp_and_cli_paths_are_field_for_field_equivalent():
    via_mcp = gather("staleness", mcp_caller=_mcp_ok())
    via_cli = gather(
        "staleness",
        mcp_caller=_mcp_raises(ConnectionError("forced failure")),
        cli_runner=_cli_ok(),
    )

    assert len(via_mcp) == len(via_cli)
    mcp_dicts = sorted(
        (f.source.value, f.check, f.status.value, f.message, tuple(sorted(f.evidence.items())))
        for f in via_mcp
    )
    cli_dicts = sorted(
        (f.source.value, f.check, f.status.value, f.message, tuple(sorted(f.evidence.items())))
        for f in via_cli
    )
    assert mcp_dicts == cli_dicts


# --- both MCP and CLI fail ----------------------------------------------


def test_both_mcp_and_cli_fail_returns_one_fail_finding():
    findings = gather(
        "staleness",
        mcp_caller=_mcp_raises(ConnectionError("simulated: server unreachable")),
        cli_runner=_cli_raises(CliBridgeError("simulated: script missing")),
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.STALENESS_REPORT
    assert finding.check == "doctor.sources.atlas"
    assert finding.status is DoctorStatus.FAIL
    assert "simulated: server unreachable" in finding.message
    assert "simulated: script missing" in finding.message


def test_cli_unparseable_json_degrades_to_one_fail_finding_no_exception():
    findings = gather(
        "staleness",
        mcp_caller=_mcp_raises(ConnectionError("simulated: server unreachable")),
        cli_runner=_cli_raises(
            CliBridgeError("script.py produced unparseable JSON on stdout")
        ),
    )

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.FAIL
    assert "unparseable JSON" in findings[0].message


def test_cli_non_list_payload_degrades_to_one_fail_finding():
    findings = gather(
        "staleness",
        mcp_caller=_mcp_raises(ConnectionError("simulated: server unreachable")),
        cli_runner=_cli_ok(rows={"error": "script not found"}),
    )

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.FAIL


# --- target scoping ------------------------------------------------------


def test_target_threads_to_mcp_maintainer_argument():
    seen = {}

    def caller(tool: str, arguments: dict) -> str:
        seen["arguments"] = arguments
        return json.dumps([])

    gather("staleness", target="somemaintainer", mcp_caller=caller)
    assert seen["arguments"] == {"maintainer": "somemaintainer"}


def test_target_threads_to_cli_maintainer_flag():
    seen = {}

    def runner(script_path: Path, args: list[str]):
        seen["args"] = args
        return []

    gather(
        "staleness",
        target="somemaintainer",
        mcp_caller=_mcp_raises(ConnectionError("simulated failure")),
        cli_runner=runner,
    )
    assert "--maintainer" in seen["args"]
    assert "somemaintainer" in seen["args"]
    assert seen["args"][seen["args"].index("--maintainer") + 1] == "somemaintainer"


# --- unrecognized axis ----------------------------------------------------


def test_unrecognized_axis_raises_value_error():
    with pytest.raises(ValueError, match="bogus"):
        gather("bogus")


def test_cve_and_abandonment_axes_are_now_supported():
    # Story 2.2 wired these -- both must no longer raise (Story 2.1 had
    # this test asserting the opposite; Story 2.2 supersedes it).
    gather("cve", mcp_caller=lambda tool, args: json.dumps({"meta": {}, "rows": []}))
    gather("abandonment", mcp_caller=lambda tool, args: json.dumps([]))


# --- empty result set ------------------------------------------------------


def test_empty_row_list_returns_empty_findings_tuple():
    findings = gather("staleness", mcp_caller=_mcp_ok(rows=[]))
    assert findings == ()


# --- malformed row shape ---------------------------------------------------


def test_non_dict_row_degrades_to_a_fail_finding_not_a_crash():
    findings = gather("staleness", mcp_caller=_mcp_ok(rows=["not-a-dict"]))
    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.FAIL
