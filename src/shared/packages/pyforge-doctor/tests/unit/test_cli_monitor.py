"""Unit tests for ``pyforge.doctor.__main__``'s ``monitor`` subcommand
(Story 2.3, FR-9) -- covers every row of the story spec's I/O & Edge-Case
Matrix: ``--fleet`` required, default axis set when ``--watch`` is omitted,
``--watch`` multi-axis composition + validation, ``--source`` filtering
(human AND ``--json`` parity), ``--target`` threading, and schema-valid
``--json`` output (``verb: "monitor"``, no ``prescriptions`` key -- mirrors
Story 1.5's own ``check`` schema proof).

``sources.atlas.gather`` is monkeypatched throughout -- this suite never
spawns a real subprocess or opens a real MCP session (mirrors
``test_cli_check.py``'s own ``run_doctor_checks`` monkeypatch idiom)."""

from __future__ import annotations

import json
from importlib import resources

import jsonschema
import pytest

from pyforge.doctor.__main__ import main
from pyforge.doctor.models import DoctorStatus, Finding, Source
from pyforge.doctor.sources import atlas


def _schema() -> dict:
    schema_text = (
        resources.files("pyforge.doctor")
        .joinpath("data", "report-schema.json")
        .read_text(encoding="utf-8")
    )
    return json.loads(schema_text)


def _finding(source: Source, check: str, status: DoctorStatus) -> Finding:
    return Finding(
        source=source, check=check, status=status, message="stub", evidence={}
    )


def _stub_gather(monkeypatch, by_axis: dict[str, tuple[Finding, ...]]):
    """Records every ``(axis, target)`` call and returns ``by_axis[axis]``
    (defaulting to an empty tuple for an axis not in the map)."""
    calls: list[tuple[str, str | None]] = []

    def fake_gather(axis, *, target=None, **kwargs):
        calls.append((axis, target))
        return by_axis.get(axis, ())

    monkeypatch.setattr(atlas, "gather", fake_gather)
    return calls


# --- --fleet is required -----------------------------------------------


def test_monitor_without_fleet_is_a_usage_error(capsys):
    exit_code = main(["monitor"])
    assert exit_code == 2
    assert "--fleet" in capsys.readouterr().err


# --- default axis set ----------------------------------------------------


def test_monitor_default_axis_set_is_staleness_and_cve(monkeypatch):
    calls = _stub_gather(monkeypatch, {})
    main(["monitor", "--fleet"])
    assert [axis for axis, _target in calls] == ["staleness", "cve"]


def test_monitor_watch_flag_overrides_the_default(monkeypatch):
    calls = _stub_gather(monkeypatch, {})
    main(["monitor", "--fleet", "--watch", "abandonment"])
    assert [axis for axis, _target in calls] == ["abandonment"]


def test_monitor_watch_multi_axis_calls_gather_once_per_axis(monkeypatch):
    calls = _stub_gather(monkeypatch, {})
    main(["monitor", "--fleet", "--watch", "staleness,cve"])
    assert [axis for axis, _target in calls] == ["staleness", "cve"]


def test_monitor_watch_duplicate_axes_are_deduplicated(monkeypatch):
    calls = _stub_gather(monkeypatch, {})
    main(["monitor", "--fleet", "--watch", "staleness,staleness"])
    assert [axis for axis, _target in calls] == ["staleness"]


def test_monitor_watch_unknown_axis_is_a_usage_error(capsys, monkeypatch):
    calls = _stub_gather(monkeypatch, {})
    exit_code = main(["monitor", "--fleet", "--watch", "bogus"])
    assert exit_code == 2
    assert "bogus" in capsys.readouterr().err
    assert calls == []  # never reached gather -- validated before dispatch


def test_monitor_watch_empty_value_is_a_usage_error(capsys):
    exit_code = main(["monitor", "--fleet", "--watch", ""])
    assert exit_code == 2
    assert "--watch" in capsys.readouterr().err


# --- multi-axis composition (Story 2.2 AC3) -------------------------------


def test_monitor_multi_axis_exit_code_reflects_the_fail_among_them(monkeypatch):
    _stub_gather(
        monkeypatch,
        {
            "staleness": (
                _finding(Source.STALENESS_REPORT, "pkg-a", DoctorStatus.WARN),
            ),
            "cve": (_finding(Source.CVE_WATCHER, "pkg-b", DoctorStatus.FAIL),),
        },
    )
    exit_code = main(["monitor", "--fleet", "--watch", "staleness,cve", "--json"])
    assert exit_code == 2  # a FAIL finding is present -- verdict.py's own contract


def test_monitor_multi_axis_json_report_has_both_sources(monkeypatch, capsys):
    _stub_gather(
        monkeypatch,
        {
            "staleness": (
                _finding(Source.STALENESS_REPORT, "pkg-a", DoctorStatus.WARN),
            ),
            "cve": (_finding(Source.CVE_WATCHER, "pkg-b", DoctorStatus.FAIL),),
        },
    )
    main(["monitor", "--fleet", "--watch", "staleness,cve", "--json"])
    document = json.loads(capsys.readouterr().out)
    sources = {f["source"] for f in document["findings"]}
    assert sources == {"staleness-report", "cve-watcher"}


# --- --target threading ----------------------------------------------------


def test_monitor_target_threads_to_every_axis(monkeypatch):
    calls = _stub_gather(monkeypatch, {})
    main(["monitor", "--fleet", "--watch", "staleness,cve", "--target", "rxm7706"])
    assert calls == [("staleness", "rxm7706"), ("cve", "rxm7706")]


def test_monitor_no_target_passes_none(monkeypatch):
    calls = _stub_gather(monkeypatch, {})
    main(["monitor", "--fleet"])
    assert all(target is None for _axis, target in calls)


# --- --source filtering (human + json parity) -----------------------------


def test_monitor_source_filters_human_output(monkeypatch, capsys):
    _stub_gather(
        monkeypatch,
        {
            "staleness": (
                _finding(Source.STALENESS_REPORT, "pkg-a", DoctorStatus.WARN),
            ),
            "cve": (_finding(Source.CVE_WATCHER, "pkg-b", DoctorStatus.FAIL),),
        },
    )
    main(["monitor", "--fleet", "--watch", "staleness,cve", "--source", "cve-watcher"])
    out = capsys.readouterr().out
    assert "pkg-b" in out
    assert "pkg-a" not in out


def test_monitor_source_filters_json_output_identically(monkeypatch, capsys):
    _stub_gather(
        monkeypatch,
        {
            "staleness": (
                _finding(Source.STALENESS_REPORT, "pkg-a", DoctorStatus.WARN),
            ),
            "cve": (_finding(Source.CVE_WATCHER, "pkg-b", DoctorStatus.FAIL),),
        },
    )
    main(
        [
            "monitor",
            "--fleet",
            "--watch",
            "staleness,cve",
            "--source",
            "cve-watcher",
            "--json",
        ]
    )
    document = json.loads(capsys.readouterr().out)
    assert [f["check"] for f in document["findings"]] == ["pkg-b"]


def test_monitor_unknown_source_is_a_usage_error(capsys, monkeypatch):
    calls = _stub_gather(monkeypatch, {})
    exit_code = main(["monitor", "--fleet", "--source", "not-a-real-source"])
    assert exit_code == 2
    assert "not-a-real-source" in capsys.readouterr().err
    assert calls == []


# --- --json schema parity (mirrors Story 1.5's own check proof) -----------


def test_monitor_json_is_schema_valid_verb_monitor_no_prescriptions(monkeypatch, capsys):
    _stub_gather(
        monkeypatch,
        {"staleness": (_finding(Source.STALENESS_REPORT, "pkg-a", DoctorStatus.OK),)},
    )
    main(["monitor", "--fleet", "--watch", "staleness", "--json"])
    document = json.loads(capsys.readouterr().out)
    jsonschema.validate(document, _schema())
    assert document["verb"] == "monitor"
    assert "prescriptions" not in document


def test_monitor_json_and_human_have_the_same_finding_count(monkeypatch, capsys):
    findings = (
        _finding(Source.STALENESS_REPORT, "pkg-a", DoctorStatus.WARN),
        _finding(Source.STALENESS_REPORT, "pkg-b", DoctorStatus.FAIL),
    )
    _stub_gather(monkeypatch, {"staleness": findings})

    main(["monitor", "--fleet", "--watch", "staleness"])
    human_out = capsys.readouterr().out
    assert human_out.splitlines()[0].startswith("doctor monitor: 2 finding(s)")

    main(["monitor", "--fleet", "--watch", "staleness", "--json"])
    document = json.loads(capsys.readouterr().out)
    assert len(document["findings"]) == 2


# --- exit code -------------------------------------------------------------


def test_monitor_exit_code_reflects_fail_findings(monkeypatch):
    _stub_gather(
        monkeypatch,
        {"cve": (_finding(Source.CVE_WATCHER, "pkg-a", DoctorStatus.FAIL),)},
    )
    assert main(["monitor", "--fleet", "--watch", "cve"]) == 2


def test_monitor_exit_code_zero_for_warn_only(monkeypatch):
    _stub_gather(
        monkeypatch,
        {"cve": (_finding(Source.CVE_WATCHER, "pkg-a", DoctorStatus.WARN),)},
    )
    assert main(["monitor", "--fleet", "--watch", "cve"]) == 0
