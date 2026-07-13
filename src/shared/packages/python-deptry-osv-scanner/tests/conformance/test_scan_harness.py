"""Conformance harness — the loop's verify gate (Story 1.2).

The two-fixture regression harness (clean → green; false-green sentinel →
≥1 finding) plus the I/O-matrix edge rows. Every scenario invokes
``cli.main([...])`` IN-PROCESS (capsys): the call returning IS the
0-uncaught-exceptions assertion, and any socket attempt anywhere in the
pipeline is intercepted by the conftest deny harness. Every later story
inherits these gates via the loop's verify command.

Assertions per fixture: exit-code-matches (clean→0, sentinel→1, AND
rc == the report's own exit_code), stdout parses as exactly one JSON
document that validates against the packaged schema, false-green=0
(sentinel: ≥1 finding + non-zero exit; clean: findings==[]), errors[] empty,
stderr-only diagnostics, twice-run byte-identical stdout in default AND
``--deterministic`` mode.
"""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

import jsonschema
import pytest

from python_deptry_osv_scanner import engines as engines_module
from python_deptry_osv_scanner.cli import main
from python_deptry_osv_scanner.interfaces import EngineResult
from python_deptry_osv_scanner.mapping import load_conda_pypi_map
from python_deptry_osv_scanner.models import (
    AXIS_HYGIENE,
    ErrorKind,
    ErrorRecord,
    Finding,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "projects"
CLEAN = FIXTURES / "clean"
SENTINEL = FIXTURES / "sentinel"


def load_schema() -> dict:
    schema_file = (
        resources.files("python_deptry_osv_scanner") / "data" / "report-schema.json"
    )
    return json.loads(schema_file.read_text(encoding="utf-8"))


def run_scan(capsys, target, *extra: str) -> tuple[int, str, str]:
    capsys.readouterr()  # drain anything a prior call in this test produced
    rc = main(["scan", str(target), "--format", "json", *extra])
    captured = capsys.readouterr()
    return rc, captured.out, captured.err


def parse_report(stdout: str) -> dict:
    # json.loads over the FULL capture: raises unless stdout is exactly one
    # JSON document (plus insignificant whitespace) — the NFR-I3 assertion.
    document = json.loads(stdout)
    jsonschema.Draft202012Validator(load_schema()).validate(document)
    return document


def test_clean_fixture_is_green(capsys):
    rc, out, err = run_scan(capsys, CLEAN)
    document = parse_report(out)
    assert rc == 0
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "clean"
    assert document["findings"] == []
    assert document["errors"] == []
    assert err == ""  # diagnostics are stderr-only; a green run needs none
    assert document["inventory_count"] == 2
    assert document["resolved_scan_set"] == [
        {"path": "pyproject.toml", "kind": "pyproject.toml"}
    ]


def test_clean_fixture_coverage_is_honest_under_the_null_engine(capsys):
    _, out, _ = run_scan(capsys, CLEAN)
    document = parse_report(out)
    assert {block["axis"] for block in document["coverage"]} == {
        "hygiene",
        "vulnerability",
    }
    for block in document["coverage"]:
        assert block["manifests_found"] == 1
        assert block["manifests_parsed"] == 1
        assert block["deps_total"] == 2
        assert block["deps_assessed"] == 0  # nothing assessed by an engine
        assert block["resolution_depth"] == "direct-only"


def test_sentinel_fixture_never_false_greens(capsys):
    rc, out, err = run_scan(capsys, SENTINEL)
    document = parse_report(out)
    assert rc != 0  # never exit 0
    assert rc == 1
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "indeterminate"
    assert document["status"]["driver"] is not None
    assert len(document["findings"]) >= 1
    assert all(f["id"].startswith("indeterminate:") for f in document["findings"])
    assert all(f["axis"] == "vulnerability" for f in document["findings"])
    assert document["errors"] == []
    assert err == ""
    # Both withhold reasons are exercised by the fixture's two deps.
    reasons = {f["id"].split(":")[1] for f in document["findings"]}
    assert reasons == {"no-version", "range-only"}


def test_sentinel_driver_references_an_emitted_finding(capsys):
    _, out, _ = run_scan(capsys, SENTINEL)
    document = parse_report(out)
    driver = document["status"]["driver"]
    assert driver["finding_id"] in {f["id"] for f in document["findings"]}
    assert driver["axis"] == "vulnerability"


@pytest.mark.parametrize(
    "mode", [(), ("--deterministic",)], ids=["default", "deterministic"]
)
@pytest.mark.parametrize("fixture", [CLEAN, SENTINEL], ids=["clean", "sentinel"])
def test_twice_run_stdout_is_byte_identical(capsys, fixture, mode):
    rc_one, out_one, _ = run_scan(capsys, fixture, *mode)
    rc_two, out_two, _ = run_scan(capsys, fixture, *mode)
    assert rc_one == rc_two
    assert out_one.encode("utf-8") == out_two.encode("utf-8")


def test_deterministic_mode_matches_default_output(capsys):
    """--deterministic is a documented no-op: same bytes as default mode."""
    _, out_default, _ = run_scan(capsys, CLEAN)
    _, out_pinned, _ = run_scan(capsys, CLEAN, "--deterministic")
    assert out_default.encode("utf-8") == out_pinned.encode("utf-8")


def test_empty_dir_is_not_applicable(capsys, tmp_path):
    rc, out, err = run_scan(capsys, tmp_path)
    document = parse_report(out)
    assert rc == 0
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "not-applicable"
    assert document["status"]["driver"] is None
    assert document["inventory_count"] == 0
    assert document["resolved_scan_set"] == []
    assert document["findings"] == []
    assert document["errors"] == []
    # The honest empty/zero coverage forms: no claim, nothing counted.
    for block in document["coverage"]:
        assert block["manifests_found"] == 0
        assert block["manifests_parsed"] == 0
        assert block["deps_total"] == 0
        assert block["deps_assessed"] == 0
        assert block["resolution_depth"] is None


def test_malformed_toml_still_emits_an_error_report(capsys, tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        "[project\nname = 'broken", encoding="utf-8"
    )
    rc, out, err = run_scan(capsys, tmp_path)
    document = parse_report(out)  # the report IS still emitted, schema-valid
    assert rc == 2
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "error"
    assert document["status"]["driver"] is not None
    assert document["status"]["driver"]["finding_id"].startswith(
        "error:unparsable-manifest:"
    )
    assert [e["kind"] for e in document["errors"]] == ["unparsable-manifest"]
    assert err != ""  # the diagnostic went to stderr, not stdout


def test_conda_pypi_map_stub_is_an_empty_mapping():
    """The asset-loading plumbing works and the stub map is {} (the real
    shape + generation are Story 2.1's)."""
    assert load_conda_pypi_map() == {}


def test_empty_scan_set_emits_a_stderr_notice_in_both_formats(capsys, tmp_path):
    """The not-applicable path says so on stderr in BOTH formats; stdout
    purity is unaffected (json: one schema-valid document; text: the single
    summary line)."""
    rc, out, err = run_scan(capsys, tmp_path)
    parse_report(out)  # stdout still carries exactly one schema-valid doc
    assert rc == 0
    assert "no manifest found" in err
    assert "nothing to scan" in err
    rc_text = main(["scan", str(tmp_path)])  # text mode
    captured = capsys.readouterr()
    assert rc_text == 0
    assert "no manifest found" in captured.err
    assert captured.out.count("\n") == 1  # one summary line, notice-free
    assert "status=not-applicable" in captured.out


def test_error_report_driver_is_a_dangling_error_grammar_id(capsys, tmp_path):
    """Error-status drivers use the ``error:<kind>:<subject>`` grammar and
    do NOT reference findings[] (Story 1.7 owns the final grammar): driver
    non-null, findings possibly empty, report still schema-valid."""
    (tmp_path / "pyproject.toml").write_text(
        "[project\nname = 'broken", encoding="utf-8"
    )
    rc, out, _ = run_scan(capsys, tmp_path)
    document = parse_report(out)  # schema-valid despite the dangling driver
    assert rc == 2
    driver = document["status"]["driver"]
    assert driver is not None
    assert driver["finding_id"] == "error:unparsable-manifest:pyproject.toml"
    assert document["findings"] == []
    assert driver["finding_id"] not in {f["id"] for f in document["findings"]}


# --- engine errors feed the verdict (the false-green seam) -------------------


def register_engine_for_test(monkeypatch, engine_cls) -> None:
    """Append a fake engine for one test (the registry list is restored by
    monkeypatch; registration order — null first — is preserved)."""
    monkeypatch.setattr(
        engines_module,
        "_ENGINE_FACTORIES",
        [*engines_module._ENGINE_FACTORIES, engine_cls],
    )


class ErrorsOnlyEngine:
    name = "errors-only"

    def run(self, target, inventory) -> EngineResult:
        return EngineResult(
            findings=(),
            errors=(
                ErrorRecord(
                    kind=ErrorKind.ENGINE_EXECUTION_FAILED,
                    owner="errors-only",
                    message="engine exploded",
                ),
            ),
            coverage=(),
        )


class FindingAndErrorEngine:
    name = "finding-and-error"

    def run(self, target, inventory) -> EngineResult:
        return EngineResult(
            findings=(
                Finding(
                    id="hygiene:DEP002:requests",
                    axis=AXIS_HYGIENE,
                    message="unused dependency",
                    subject="requests",
                    severity=None,
                ),
            ),
            errors=(
                ErrorRecord(
                    kind=ErrorKind.ENGINE_OUTPUT_UNPARSEABLE,
                    owner="finding-and-error",
                    message="half the output was garbage",
                ),
            ),
            coverage=(),
        )


def test_errors_only_engine_yields_an_error_report(capsys, monkeypatch):
    """An engine that only errors must reach the verdict: status error,
    error-projection exit, errors[] populated — and the report is STILL
    emitted and schema-valid (exit code orthogonal to emission)."""
    register_engine_for_test(monkeypatch, ErrorsOnlyEngine)
    rc, out, err = run_scan(capsys, CLEAN)
    document = parse_report(out)
    assert rc == 2
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "error"
    assert document["status"]["driver"]["finding_id"] == (
        "error:engine-execution-failed:errors-only"
    )
    assert [e["kind"] for e in document["errors"]] == ["engine-execution-failed"]
    assert document["findings"] == []


def test_erroring_engine_still_surfaces_its_findings(capsys, monkeypatch):
    """A finding-emitting-and-erroring engine surfaces BOTH: the finding in
    findings[] and the error in errors[] (with the error verdict winning)."""
    register_engine_for_test(monkeypatch, FindingAndErrorEngine)
    rc, out, _ = run_scan(capsys, CLEAN)
    document = parse_report(out)
    assert rc == 2
    assert document["status"]["value"] == "error"
    assert [e["kind"] for e in document["errors"]] == [
        "engine-output-unparseable"
    ]
    assert "hygiene:DEP002:requests" in {f["id"] for f in document["findings"]}
