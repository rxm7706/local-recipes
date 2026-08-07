"""Unit tests for ``pyforge.doctor.sources.atlas``'s ``cve``/``abandonment``
axes (Story 2.2) -- covers every row of the spec's I/O & Edge-Case Matrix.
Mirrors ``test_sources_atlas.py``'s own idiom: the MCP path is faked via the
injectable ``mcp_caller`` seam and the CLI path via the injectable
``cli_runner`` seam, so this suite never spawns a real subprocess or opens a
real MCP session."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.doctor.cli_bridge import CliBridgeError
from pyforge.doctor.models import DoctorStatus, Finding, Source
from pyforge.doctor.sources.atlas import gather

# --- cve axis fixtures -----------------------------------------------------

_CVE_ROWS = [
    {
        "conda_name": "some-package",
        "now_v": 2,
        "then_v": 0,
        "delta": 2,
        "latest_conda_version": "1.2.3",
        "total_downloads": 12345,
    },
    {
        "conda_name": "another-package",
        "now_v": 1,
        "then_v": 3,
        "delta": -2,
        "latest_conda_version": "0.9.0",
        "total_downloads": 42,
    },
]

_CVE_PAYLOAD = {"meta": {"severity": "C"}, "rows": _CVE_ROWS}


def _mcp_returns(tool_name: str, text: str):
    def caller(tool: str, arguments: dict) -> str:
        assert tool == tool_name
        return text

    return caller


def _mcp_raises(exc: BaseException):
    def caller(tool: str, arguments: dict) -> str:
        raise exc

    return caller


def _cli_ok(payload):
    def runner(script_path: Path, args: list[str]):
        return payload

    return runner


def _cli_raises(exc: BaseException):
    def runner(script_path: Path, args: list[str]):
        raise exc

    return runner


# --- cve axis: MCP success -------------------------------------------------


def test_cve_mcp_success_returns_one_finding_per_row():
    findings = gather(
        "cve", mcp_caller=_mcp_returns("cve_watcher", json.dumps(_CVE_PAYLOAD))
    )
    assert len(findings) == 2
    for finding, row in zip(findings, _CVE_ROWS):
        assert isinstance(finding, Finding)
        assert finding.source is Source.CVE_WATCHER
        assert finding.check == row["conda_name"]
        assert finding.evidence["severity"] == "C"
        assert finding.evidence["conda_name"] == row["conda_name"]


def test_cve_delta_positive_is_fail_delta_nonpositive_is_warn():
    findings = gather(
        "cve", mcp_caller=_mcp_returns("cve_watcher", json.dumps(_CVE_PAYLOAD))
    )
    by_check = {f.check: f for f in findings}
    assert by_check["some-package"].status is DoctorStatus.FAIL  # delta=2
    assert by_check["another-package"].status is DoctorStatus.WARN  # delta=-2


def test_cve_severity_threads_to_mcp_and_cli():
    seen_mcp = {}

    def caller(tool, arguments):
        seen_mcp["arguments"] = arguments
        return json.dumps({"meta": {}, "rows": []})

    gather("cve", cve_severity="K", mcp_caller=caller)
    assert seen_mcp["arguments"]["severity"] == "K"

    seen_cli = {}

    def runner(script_path, args):
        seen_cli["args"] = args
        return {"meta": {}, "rows": []}

    gather(
        "cve",
        cve_severity="K",
        mcp_caller=_mcp_raises(ConnectionError("simulated failure")),
        cli_runner=runner,
    )
    assert "--severity" in seen_cli["args"]
    assert seen_cli["args"][seen_cli["args"].index("--severity") + 1] == "K"


def test_cve_target_threads_to_maintainer():
    seen = {}

    def caller(tool, arguments):
        seen["arguments"] = arguments
        return json.dumps({"meta": {}, "rows": []})

    gather("cve", target="somemaintainer", mcp_caller=caller)
    assert seen["arguments"]["maintainer"] == "somemaintainer"


# --- cve axis: envelope shape (dict-with-rows, not a bare list) -----------


def test_cve_mcp_bare_list_payload_falls_back_to_cli():
    # cve_watcher's real shape is {"meta":..., "rows": [...]} -- a bare list
    # (staleness's own shape) must NOT be silently accepted.
    findings = gather(
        "cve",
        mcp_caller=_mcp_returns("cve_watcher", json.dumps(_CVE_ROWS)),
        cli_runner=_cli_ok(_CVE_PAYLOAD),
    )
    assert len(findings) == 2


def test_cve_cli_non_dict_payload_degrades_to_one_fail_finding():
    findings = gather(
        "cve",
        mcp_caller=_mcp_raises(ConnectionError("simulated failure")),
        cli_runner=_cli_ok([1, 2, 3]),
    )
    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.FAIL
    assert findings[0].source is Source.CVE_WATCHER


# --- cve axis: both transports fail ----------------------------------------


def test_cve_both_mcp_and_cli_fail_returns_one_fail_finding_tagged_cve():
    findings = gather(
        "cve",
        mcp_caller=_mcp_raises(ConnectionError("simulated: server unreachable")),
        cli_runner=_cli_raises(CliBridgeError("simulated: script missing")),
    )
    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.CVE_WATCHER
    assert finding.status is DoctorStatus.FAIL
    assert "simulated: server unreachable" in finding.message
    assert "simulated: script missing" in finding.message


def test_cve_non_dict_row_degrades_to_a_fail_finding_not_a_crash():
    findings = gather(
        "cve",
        mcp_caller=_mcp_returns(
            "cve_watcher", json.dumps({"meta": {}, "rows": ["not-a-dict"]})
        ),
    )
    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.FAIL
    assert findings[0].source is Source.CVE_WATCHER


def test_cve_equivalence_mcp_and_cli_paths():
    via_mcp = gather(
        "cve", mcp_caller=_mcp_returns("cve_watcher", json.dumps(_CVE_PAYLOAD))
    )
    via_cli = gather(
        "cve",
        mcp_caller=_mcp_raises(ConnectionError("forced failure")),
        cli_runner=_cli_ok(_CVE_PAYLOAD),
    )
    mcp_dicts = sorted(
        (f.source.value, f.check, f.status.value, tuple(sorted(f.evidence.items())))
        for f in via_mcp
    )
    cli_dicts = sorted(
        (f.source.value, f.check, f.status.value, tuple(sorted(f.evidence.items())))
        for f in via_cli
    )
    assert mcp_dicts == cli_dicts


# --- abandonment axis: composite of feedstock_health + release_cadence ----

_HEALTH_ROW = {
    "conda_name": "stuck-package",
    "feedstock_name": "stuck-package-feedstock",
    "bot_version_errors_count": 3,
    "feedstock_bad": 0,
    "bot_open_pr_count": 1,
}

_BAD_ROW = {
    "conda_name": "bad-package",
    "feedstock_name": "bad-package-feedstock",
    "bot_version_errors_count": 0,
    "feedstock_bad": 1,
    "bot_open_pr_count": 0,
}

_CADENCE_ROWS = [
    {
        "conda_name": "silent-package",
        "trend": "silent",
        "releases_30d": 0,
        "releases_90d": 0,
        "releases_365d": 0,
    },
    {
        "conda_name": "decelerating-package",
        "trend": "decelerating",
        "releases_30d": 1,
        "releases_90d": 5,
        "releases_365d": 20,
    },
    {
        "conda_name": "accelerating-package",
        "trend": "accelerating",
        "releases_30d": 10,
        "releases_90d": 5,
        "releases_365d": 20,
    },
]


def _abandonment_mcp_caller(
    *, health_stuck=None, health_bad=None, cadence=None, raise_for=None
):
    """Fake dispatcher for the abandonment axis's three MCP sub-calls,
    keyed by (tool_name, arguments['filter_kind']) for feedstock_health and
    plain tool_name for release_cadence."""
    health_stuck = health_stuck if health_stuck is not None else [_HEALTH_ROW]
    health_bad = health_bad if health_bad is not None else [_BAD_ROW]
    cadence = cadence if cadence is not None else _CADENCE_ROWS
    raise_for = raise_for or frozenset()

    def caller(tool: str, arguments: dict) -> str:
        if tool == "feedstock_health":
            kind = arguments.get("filter_kind")
            if ("feedstock_health", kind) in raise_for:
                raise ConnectionError(f"simulated failure: feedstock_health/{kind}")
            return json.dumps(health_stuck if kind == "stuck" else health_bad)
        if tool == "release_cadence":
            if "release_cadence" in raise_for:
                raise ConnectionError("simulated failure: release_cadence")
            return json.dumps(cadence)
        raise AssertionError(f"unexpected tool: {tool}")

    return caller


def test_abandonment_composes_three_sub_calls_with_correct_sources():
    findings = gather("abandonment", mcp_caller=_abandonment_mcp_caller())
    by_source = {}
    for f in findings:
        by_source.setdefault(f.source, []).append(f)

    assert Source.FEEDSTOCK_HEALTH in by_source
    assert Source.RELEASE_CADENCE in by_source
    # feedstock_health: one row from "stuck" + one from "bad" = 2 Findings.
    assert len(by_source[Source.FEEDSTOCK_HEALTH]) == 2
    checks = {f.check for f in by_source[Source.FEEDSTOCK_HEALTH]}
    assert checks == {"stuck-package-feedstock", "bad-package-feedstock"}

    # release_cadence: only decelerating/silent rows survive the client-side
    # filter -- "accelerating-package" must be excluded entirely.
    cadence_checks = {f.check for f in by_source[Source.RELEASE_CADENCE]}
    assert cadence_checks == {"silent-package", "decelerating-package"}


def test_abandonment_bad_filter_is_fail_stuck_filter_is_warn():
    findings = gather("abandonment", mcp_caller=_abandonment_mcp_caller())
    by_check = {f.check: f for f in findings if f.source is Source.FEEDSTOCK_HEALTH}
    assert by_check["bad-package-feedstock"].status is DoctorStatus.FAIL
    assert by_check["stuck-package-feedstock"].status is DoctorStatus.WARN


def test_abandonment_silent_trend_is_fail_decelerating_is_warn():
    findings = gather("abandonment", mcp_caller=_abandonment_mcp_caller())
    by_check = {f.check: f for f in findings if f.source is Source.RELEASE_CADENCE}
    assert by_check["silent-package"].status is DoctorStatus.FAIL
    assert by_check["decelerating-package"].status is DoctorStatus.WARN


def test_abandonment_one_sub_call_failing_does_not_hide_the_others():
    # feedstock_health/stuck fails on MCP -- no CLI fallback wired here
    # either, so it degrades to its OWN fail Finding; bad + release_cadence
    # must still produce their real Findings (partial degrade, never
    # all-or-nothing for this composite axis).
    findings = gather(
        "abandonment",
        mcp_caller=_abandonment_mcp_caller(
            raise_for=frozenset({("feedstock_health", "stuck")})
        ),
    )
    by_source = {}
    for f in findings:
        by_source.setdefault(f.source, []).append(f)

    health_findings = by_source[Source.FEEDSTOCK_HEALTH]
    assert len(health_findings) == 2  # one degraded FAIL + one real "bad" Finding
    fail_sentinel = [f for f in health_findings if f.check == "doctor.sources.atlas"]
    assert len(fail_sentinel) == 1
    assert fail_sentinel[0].status is DoctorStatus.FAIL
    real_bad = [f for f in health_findings if f.check == "bad-package-feedstock"]
    assert len(real_bad) == 1

    assert Source.RELEASE_CADENCE in by_source
    assert len(by_source[Source.RELEASE_CADENCE]) == 2


def test_abandonment_target_threads_to_maintainer_on_all_three_sub_calls():
    seen: list[dict] = []

    def caller(tool: str, arguments: dict) -> str:
        seen.append(dict(arguments))
        if tool == "feedstock_health":
            return json.dumps([])
        return json.dumps([])

    gather("abandonment", target="somemaintainer", mcp_caller=caller)
    assert len(seen) == 3
    assert all(arguments.get("maintainer") == "somemaintainer" for arguments in seen)


def test_abandonment_cli_fallback_for_all_three_sub_calls():
    def cli_runner(script_path: Path, args: list[str]):
        if script_path.name == "feedstock_health.py":
            kind_index = args.index("--filter") + 1
            return [_HEALTH_ROW] if args[kind_index] == "stuck" else [_BAD_ROW]
        if script_path.name == "release_cadence.py":
            return _CADENCE_ROWS
        raise AssertionError(f"unexpected script: {script_path}")

    findings = gather(
        "abandonment",
        mcp_caller=_mcp_raises(ConnectionError("forced failure")),
        cli_runner=cli_runner,
    )
    by_source = {}
    for f in findings:
        by_source.setdefault(f.source, []).append(f)
    assert len(by_source[Source.FEEDSTOCK_HEALTH]) == 2
    assert len(by_source[Source.RELEASE_CADENCE]) == 2


def test_abandonment_non_dict_row_degrades_to_a_fail_finding_not_a_crash():
    findings = gather(
        "abandonment",
        mcp_caller=_abandonment_mcp_caller(
            health_stuck=["not-a-dict"], health_bad=[], cadence=[]
        ),
    )
    fails = [
        f
        for f in findings
        if f.source is Source.FEEDSTOCK_HEALTH and f.status is DoctorStatus.FAIL
    ]
    assert len(fails) == 1
    assert "non-object row" in fails[0].message


# --- multi-axis composition is a CLI-layer concern (Story 2.3), not this --


def test_gather_stays_single_axis_shaped():
    # Story 2.2 AC3 ("--watch staleness,cve" produces one DoctorReport with
    # every requested axis's Findings, still individually Source-tagged) is
    # satisfied by the CLI layer calling gather() once per axis and
    # concatenating -- gather() itself takes exactly one axis string, never
    # a list/comma-joined string.
    with pytest.raises(ValueError):
        gather("staleness,cve")
