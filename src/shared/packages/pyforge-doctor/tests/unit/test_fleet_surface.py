"""Unit tests for ``pyforge.doctor.fleet_surface`` (Story 4.2, FR-11) --
covers every row of the story's AC matrix: strictly-derived content,
idempotent regeneration, schema_version, and axis-set fidelity."""

from __future__ import annotations

import json

from pyforge.doctor.fleet_surface import (
    FLEET_SURFACE_SCHEMA_VERSION,
    build_surface,
    write_surface,
)
from pyforge.doctor.models import DoctorStatus, Finding, Source


def _finding(source, check, status=DoctorStatus.OK):
    return Finding(source=source, check=check, status=status, message="stub", evidence={})


def test_build_surface_carries_schema_version_one():
    document = build_surface([], axes=[])
    assert document["schema_version"] == FLEET_SURFACE_SCHEMA_VERSION == 1


def test_build_surface_is_strictly_derived_from_the_given_findings():
    findings = (
        _finding(Source.STALENESS_REPORT, "pkg-a", DoctorStatus.WARN),
        _finding(Source.CVE_WATCHER, "pkg-b", DoctorStatus.FAIL),
    )
    document = build_surface(findings, axes=["staleness", "cve"])
    assert document["summary"] == {"ok": 0, "warn": 1, "fail": 1, "total": 2}
    checks = {f["check"] for f in document["findings"]}
    assert checks == {"pkg-a", "pkg-b"}


def test_build_surface_is_idempotent_for_the_same_findings():
    findings = (
        _finding(Source.STALENESS_REPORT, "pkg-a"),
        _finding(Source.CVE_WATCHER, "pkg-b", DoctorStatus.FAIL),
    )
    first = build_surface(findings, axes=["staleness", "cve"])
    second = build_surface(findings, axes=["staleness", "cve"])
    assert first == second
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_build_surface_output_order_is_independent_of_input_order():
    a = _finding(Source.STALENESS_REPORT, "pkg-a")
    b = _finding(Source.CVE_WATCHER, "pkg-b")
    forward = build_surface((a, b), axes=["staleness", "cve"])
    reversed_ = build_surface((b, a), axes=["staleness", "cve"])
    assert forward == reversed_


def test_build_surface_axes_are_sorted_and_deduplicated():
    document = build_surface([], axes=["cve", "staleness", "cve"])
    assert document["axes"] == ["cve", "staleness"]


def test_build_surface_never_carries_a_wall_clock_field():
    document = build_surface([_finding(Source.STALENESS_REPORT, "pkg-a")], axes=["staleness"])
    assert "generated_at" not in document
    assert "timestamp" not in document


def test_build_surface_reflects_whatever_axes_the_run_covered_including_adoption():
    document = build_surface(
        [_finding(Source.ADOPTION, "pkg-a")], axes=["staleness", "cve", "adoption"]
    )
    assert document["axes"] == ["adoption", "cve", "staleness"]


def test_write_surface_writes_valid_json_and_returns_the_document(tmp_path):
    path = tmp_path / "nested" / "fleet-health.json"
    findings = (_finding(Source.STALENESS_REPORT, "pkg-a"),)
    document = write_surface(path, findings, axes=["staleness"])
    assert path.is_file()
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk == document


def test_write_surface_overwrite_is_idempotent(tmp_path):
    path = tmp_path / "fleet-health.json"
    findings = (_finding(Source.STALENESS_REPORT, "pkg-a"),)
    write_surface(path, findings, axes=["staleness"])
    first_text = path.read_text(encoding="utf-8")
    write_surface(path, findings, axes=["staleness"])
    second_text = path.read_text(encoding="utf-8")
    assert first_text == second_text
