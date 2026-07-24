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

import importlib.metadata
import json
import sys
from email.message import Message
from importlib import resources
from pathlib import Path

import jsonschema
import pytest

from pyforge.warden import engines as engines_module
from pyforge.warden import feeds
from pyforge.warden.cli import main
from pyforge.warden.config import ConfigLoader
from pyforge.warden.interfaces import EngineResult
from pyforge.warden.mapping import load_conda_pypi_map
from pyforge.warden.models import (
    AXIS_HYGIENE,
    AXIS_VULNERABILITY,
    ErrorKind,
    ErrorRecord,
    Finding,
    SeverityTier,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "projects"
CLEAN = FIXTURES / "clean"
SENTINEL = FIXTURES / "sentinel"
DEPTRY_MISSING = FIXTURES / "deptry_missing"
DEPTRY_UNUSED = FIXTURES / "deptry_unused"
DEPTRY_STDLIB = FIXTURES / "deptry_stdlib"
DEPTRY_IGNORE = FIXTURES / "deptry_ignore"
VULN_CRITICAL = FIXTURES / "vuln_critical"
VULN_HIGH = FIXTURES / "vuln_high"
WARN_AND_INDETERMINATE = FIXTURES / "warn_and_indeterminate"
RECIPE_COMMON = FIXTURES / "recipe_common"
HYGIENE_NOT_APPLICABLE = FIXTURES / "hygiene_not_applicable"
HYGIENE_NOT_APPLICABLE_MALFORMED = FIXTURES / "hygiene_not_applicable_malformed"
PIXI_LOCK_BASIC = FIXTURES / "pixi_lock_basic"
CONDA_LOCK_BASIC = FIXTURES / "conda_lock_basic"
CONFIG_PRECEDENCE = FIXTURES / "config_precedence"


def load_schema() -> dict:
    schema_file = (
        resources.files("pyforge.warden") / "data" / "report-schema.json"
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


# --- Fix 9 (review finding, 2026-07-18): pin PyPI license metadata ----------
#
# LicenseEngine (Story 6.2) resolves a pypi component's license via
# importlib.metadata.metadata() against WHATEVER version of requests/
# packaging happens to be installed in this pixi env -- every
# pyforge-warden dependency is unpinned ("*") in pixi.toml (see
# docs/library-llms-full.md's regeneration header), so a routine relock
# could silently flip these fixtures' license-axis outcome (e.g.
# allowed -> unknown) with ZERO code change, breaking every assertion below
# that expects a genuinely clean/finding-free scan of CLEAN/CONFIG_PRECEDENCE/
# DEPTRY_IGNORE (all of which declare requests and/or packaging). Mirrors
# tests/unit/test_license.py's own _fake_metadata/_patch_metadata
# monkeypatch pattern: only "requests"/"packaging" get pinned, deterministic,
# resolvable metadata; every other name (leftpad, pdos-vuln-fixture*,
# totally_absent_pkg_xyz, argparse, ...) still goes through the REAL
# importlib.metadata.metadata, preserving the genuine PackageNotFoundError
# path those fixtures intentionally exercise.


def _fake_metadata(*, license_expression: str) -> Message:
    msg = Message()
    msg["License-Expression"] = license_expression
    return msg


_PINNED_PYPI_LICENSE_METADATA: dict[str, Message] = {
    "requests": _fake_metadata(license_expression="Apache-2.0"),
    "packaging": _fake_metadata(license_expression="Apache-2.0 OR BSD-2-Clause"),
}


@pytest.fixture(autouse=True)
def _pin_pypi_license_metadata(monkeypatch):
    real_metadata = importlib.metadata.metadata

    def fake_metadata(name, *args, **kwargs):
        pinned = _PINNED_PYPI_LICENSE_METADATA.get(name)
        if pinned is not None:
            return pinned
        return real_metadata(name, *args, **kwargs)

    monkeypatch.setattr(importlib.metadata, "metadata", fake_metadata)


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


def test_clean_fixture_coverage_reflects_deptry_hygiene_assessment(capsys):
    _, out, _ = run_scan(capsys, CLEAN)
    document = parse_report(out)
    by_axis = {block["axis"]: block for block in document["coverage"]}
    # Story 6.1: license/currency register as producer axes.
    assert set(by_axis) == {"hygiene", "vulnerability", "license", "currency"}
    # Story 6.2: license now has a real producer too (LicenseEngine) — both
    # of the fixture's deps (requests, packaging) resolve to a deterministic,
    # pinned Apache-2.0/dual license (Fix 9: _pin_pypi_license_metadata,
    # never the ambient env's actual installed metadata), so the axis is
    # applicable AND assesses both, exactly like hygiene/vulnerability.
    # Story 6.3: currency now has a real producer too (CurrencyEngine) —
    # requests/packaging (and the running interpreter) resolve currency-clean
    # against the ambient endoflife.date snapshot (tests/conftest.py's
    # autouse _currency_ambient_feed_env fixture, the currency-axis sibling
    # of Fix 9), so the axis is applicable AND assesses both deps too.
    for axis in ("hygiene", "vulnerability", "license", "currency"):
        block = by_axis[axis]
        assert block["manifests_found"] == 1
        assert block["manifests_parsed"] == 1
        assert block["deps_total"] == 2
        assert block["resolution_depth"] == "direct-only"
    # Story 1.3: deptry assessed all declared deps for hygiene. Story 1.5:
    # osv-scanner ran against the ambient test-session offline DB (conftest)
    # and assessed both vuln-matchable deps too — a genuinely clean scan,
    # not the pre-1.5 "no engine ever consulted" stub 0.
    assert by_axis["hygiene"]["deps_assessed"] == 2
    assert by_axis["vulnerability"]["deps_assessed"] == 2
    assert by_axis["license"]["deps_assessed"] == 2
    assert by_axis["currency"]["deps_assessed"] == 2


def test_sentinel_fixture_never_false_greens(capsys):
    rc, out, err = run_scan(capsys, SENTINEL)
    document = parse_report(out)
    assert rc != 0  # never exit 0
    assert rc == 1
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "indeterminate"
    assert document["status"]["driver"] is not None
    assert len(document["findings"]) >= 1
    # Story 6.2: leftpad is not an installed package, so the license axis
    # ALSO withholds it (verdict unknown) -- a real, warn-capped
    # license:unknown: finding alongside the two vulnerability-axis
    # withholds; indeterminate still wins the composed verdict either way.
    # Story 6.3: neither dep has a resolved version (leftpad: no-version;
    # requests>=2.0: range-only), so BOTH are currency:unknown: too --
    # currency resolution needs a concrete version to match against any
    # tier, unlike license's name-only importlib.metadata lookup.
    vuln_findings = [f for f in document["findings"] if f["axis"] == "vulnerability"]
    license_findings = [f for f in document["findings"] if f["axis"] == "license"]
    currency_findings = [f for f in document["findings"] if f["axis"] == "currency"]
    assert all(f["id"].startswith("indeterminate:") for f in vuln_findings)
    assert {f["id"] for f in license_findings} == {
        "license:unknown:leftpad@unspecified"
    }
    assert {f["id"] for f in currency_findings} == {
        "currency:unknown:leftpad@unspecified",
        "currency:unknown:requests@unspecified",
    }
    assert len(vuln_findings) + len(license_findings) + len(currency_findings) == len(
        document["findings"]
    )
    assert document["errors"] == []
    assert err == ""
    # Both withhold reasons are exercised by the fixture's two deps.
    reasons = {f["id"].split(":")[1] for f in vuln_findings}
    assert reasons == {"no-version", "range-only"}


def test_sentinel_driver_references_an_emitted_finding(capsys):
    _, out, _ = run_scan(capsys, SENTINEL)
    document = parse_report(out)
    driver = document["status"]["driver"]
    assert driver["finding_id"] in {f["id"] for f in document["findings"]}
    assert driver["axis"] == "vulnerability"


def test_sentinel_fixture_hygiene_axis_is_not_applicable(capsys):
    """Story 2.4 (AC3), review finding, 2026-07-17: SENTINEL has zero
    adjacent .py files, so DeptryEngine no longer runs against it at all --
    the pre-2.4 shape (deps_total=2, deps_assessed=2, resolution_depth=
    direct-only, driven only by the fixture's own [tool.deptry] ignore
    silencing DEP002) must not silently regress back. Pinned separately
    from test_sentinel_fixture_never_false_greens (which already proves NO
    hygiene-axis finding leaks in) so a future change to the not-applicable
    coverage shape itself is caught here specifically."""
    _, out, _ = run_scan(capsys, SENTINEL)
    document = parse_report(out)
    by_axis = {block["axis"]: block for block in document["coverage"]}
    assert by_axis["hygiene"]["deps_total"] == 0
    assert by_axis["hygiene"]["deps_assessed"] == 0
    assert by_axis["hygiene"]["resolution_depth"] is None
    assert by_axis["vulnerability"]["deps_total"] == 2


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
    # Story 3.1: pyproject.toml is BOTH the primary config source and the
    # manifest -- malformed TOML there now produces TWO independent typed
    # errors (config-parse from ConfigLoader, unparsable-manifest from
    # extraction, each reading the same broken file for its own purpose).
    # verdict.compose's deterministic tie-break (smallest (axis, finding_id);
    # both share AXIS_INGESTION) picks config-parse, since "config-parse" <
    # "unparsable-manifest" lexically.
    assert document["status"]["driver"]["finding_id"].startswith(
        "error:config-parse:"
    )
    assert {e["kind"] for e in document["errors"]} == {
        "config-parse",
        "unparsable-manifest",
    }
    assert err != ""  # the diagnostic went to stderr, not stdout


def test_conda_pypi_map_is_populated_and_correctly_shaped():
    """The asset-loading plumbing works and the bundled map is populated
    (Story 2.1) with the {pypi_name, match_source, match_confidence} shape
    per entry — never flattened to name->name."""
    mapping = load_conda_pypi_map()
    assert mapping
    entry = mapping["numpy"]
    assert isinstance(entry, dict)
    assert entry.keys() == {"pypi_name", "match_source", "match_confidence"}
    assert entry["pypi_name"] == "numpy"


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
    do NOT reference findings[] (Story 1.7 ratified this as the final
    grammar): driver non-null, findings possibly empty, report still
    schema-valid. This fixture's failure is a malformed pyproject.toml --
    BOTH a config-load failure (Story 3.1) and a pre-engine EXTRACT-stage
    failure, so the driver's axis is "ingestion" either way (never a
    blanket vulnerability default); config-parse wins the deterministic
    tie-break (see test_malformed_toml_still_emits_an_error_report above)."""
    (tmp_path / "pyproject.toml").write_text(
        "[project\nname = 'broken", encoding="utf-8"
    )
    rc, out, _ = run_scan(capsys, tmp_path)
    document = parse_report(out)  # schema-valid despite the dangling driver
    assert rc == 2
    driver = document["status"]["driver"]
    assert driver is not None
    assert driver["finding_id"].startswith("error:config-parse:")
    assert driver["axis"] == "ingestion"
    assert document["findings"] == []
    assert driver["finding_id"] not in {f["id"] for f in document["findings"]}


@pytest.mark.parametrize(
    "fixture",
    [WARN_AND_INDETERMINATE, VULN_CRITICAL, VULN_HIGH, DEPTRY_MISSING],
    ids=lambda p: p.name,
)
def test_non_error_status_driver_references_an_emitted_finding(capsys, fixture):
    """The two-namespace finding_id contract (ratified, Story 1.7): every
    NON-error-status driver must equal an id present in that report's own
    findings[] — only Status.ERROR's error:<kind>:<subject> grammar is
    exempt (pinned separately by
    test_error_report_driver_is_a_dangling_error_grammar_id above).
    ``DEPTRY_MISSING`` (review finding, 2026-07-17) exercises the fourth
    (status, axis) combination the contract claims to hold universally: a
    hygiene-axis ``policy-violation`` (DEP001-block), not just the
    vulnerability-axis/indeterminate cases above."""
    _, out, _ = run_scan(capsys, fixture)
    document = parse_report(out)
    assert document["status"]["value"] != "error"
    driver = document["status"]["driver"]
    assert driver is not None
    assert driver["finding_id"] in {f["id"] for f in document["findings"]}


# --- engine errors feed the verdict (the false-green seam) -------------------


def register_engine_for_test(monkeypatch, engine_cls) -> None:
    """Append a fake engine for one test (the registry list is restored by
    monkeypatch; registration order — null first — is preserved)."""
    monkeypatch.setattr(
        engines_module,
        "_ENGINE_FACTORIES",
        [*engines_module._ENGINE_FACTORIES, engine_cls],
    )


class FindingsOnlyEngine:
    name = "findings-only"
    axis = AXIS_HYGIENE

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
            errors=(),
            coverage=(),
            axis=self.axis,
        )


class SysExitEngine:
    name = "sys-exit"
    axis = AXIS_VULNERABILITY

    def run(self, target, inventory) -> EngineResult:
        raise SystemExit(0)


class CrashingFactory:
    name = "crashing-factory"
    axis = AXIS_HYGIENE

    def __init__(self) -> None:
        raise RuntimeError("factory blew up at instantiation")

    def run(self, target, inventory) -> EngineResult:
        raise AssertionError("unreachable: the constructor always raises")


class ErrorsOnlyEngine:
    name = "errors-only"
    axis = AXIS_VULNERABILITY

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
            axis=self.axis,
        )


class FindingAndErrorEngine:
    name = "finding-and-error"
    axis = AXIS_HYGIENE

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
            axis=self.axis,
            errors=(
                ErrorRecord(
                    kind=ErrorKind.ENGINE_OUTPUT_UNPARSEABLE,
                    owner="finding-and-error",
                    message="half the output was garbage",
                ),
            ),
            coverage=(),
        )


def test_findings_only_engine_surfaces_its_finding_and_never_greens(
    capsys, monkeypatch
):
    """THE false-green seam row: an engine returning findings WITHOUT errors
    is publicly reachable via ``register_engine`` today, and a
    finding-carrying report must never compose ``clean`` (C0c). Story 1.3
    routes the hygiene axis through its real default table: a DEP002 finding
    maps to ``warn`` (its real ceiling) — the finding is surfaced and the
    status is ``warn``, NOT ``clean``. ``warn`` projects to exit 0 by policy
    (``warn_is_error`` is Story 1.6); the C0 property is that the status is
    never ``clean`` while a finding stands, which holds."""
    register_engine_for_test(monkeypatch, FindingsOnlyEngine)
    rc, out, err = run_scan(capsys, CLEAN)
    document = parse_report(out)
    assert document["status"]["value"] == "warn"
    assert document["status"]["value"] != "clean"  # the C0 property
    assert rc == 0
    assert rc == document["exit_code"]
    finding_ids = {f["id"] for f in document["findings"]}
    assert "hygiene:DEP002:requests" in finding_ids
    driver = document["status"]["driver"]
    assert driver is not None
    assert driver["finding_id"] in finding_ids
    assert document["errors"] == []


def test_sys_exit_engine_cannot_dictate_the_gate(capsys, monkeypatch):
    """An engine calling sys.exit(0) — an exit-code sole-ownership
    violation — must not exit the process green with no report: the seam
    guard converts the SystemExit to engine-execution-failed with the
    report STILL emitted and the error exit returned."""
    register_engine_for_test(monkeypatch, SysExitEngine)
    rc, out, err = run_scan(capsys, CLEAN)
    document = parse_report(out)
    assert rc == 2
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "error"
    (error,) = document["errors"]
    assert error["kind"] == "engine-execution-failed"
    assert "SystemExit" in error["message"]


def test_crashing_engine_factory_still_emits_the_report(capsys, monkeypatch):
    """Instantiation is part of the seam: a factory that crashes in its
    constructor (a misconfigured 1.3/1.5 runner) yields a typed
    engine-unavailable record with the report STILL emitted — never a
    traceback with no report."""
    register_engine_for_test(monkeypatch, CrashingFactory)
    rc, out, err = run_scan(capsys, CLEAN)
    document = parse_report(out)
    assert rc == 2
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "error"
    (error,) = document["errors"]
    assert error["kind"] == "engine-unavailable"
    assert "factory blew up at instantiation" in error["message"]
    assert document["status"]["driver"]["finding_id"].startswith(
        "error:engine-unavailable:"
    )
    assert err != ""


def test_deeply_nested_toml_is_unparsable_manifest_not_a_crash(
    capsys, tmp_path
):
    """Hostile nesting overflows tomllib's recursive parser with
    RecursionError (not TOMLDecodeError): still a structurally-broken
    manifest — unparsable-manifest, report emitted, error exit; never a
    traceback with no report and never 'internal error'. Story 3.1:
    ConfigLoader independently hits the identical RecursionError reading
    the same file for [tool.pyforge-warden] (config.py mirrors extract/
    pyproject.py's own hostile-input guard), so a config-parse error rides
    alongside the pre-existing unparsable-manifest one -- neither crashes."""
    (tmp_path / "pyproject.toml").write_text(
        "x = " + "[" * 8000 + "]" * 8000 + "\n", encoding="utf-8"
    )
    rc, out, err = run_scan(capsys, tmp_path)
    document = parse_report(out)
    assert rc == 2
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "error"
    assert {e["kind"] for e in document["errors"]} == {
        "config-parse",
        "unparsable-manifest",
    }
    assert err != ""


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


class CrashingEngine:
    name = "crashing"
    axis = AXIS_VULNERABILITY

    def run(self, target, inventory) -> EngineResult:
        raise RuntimeError("engine blew up mid-run")


def test_crashing_engine_still_emits_the_report(capsys, monkeypatch):
    """A RAISING engine (not one returning ErrorRecords — one that crashes)
    must yield a typed engine-execution-failed record + the error verdict,
    with the report STILL emitted — never a traceback with no report."""
    register_engine_for_test(monkeypatch, CrashingEngine)
    rc, out, err = run_scan(capsys, CLEAN)
    document = parse_report(out)  # the report IS still emitted, schema-valid
    assert rc == 2
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "error"
    (error,) = document["errors"]
    assert error["kind"] == "engine-execution-failed"
    assert "engine blew up mid-run" in error["message"]
    assert document["status"]["driver"]["finding_id"] == (
        "error:engine-execution-failed:crashing"
    )
    assert err != ""


def test_two_engines_failing_on_different_axes_both_surface(capsys, monkeypatch):
    """Review finding (2026-07-17): axis is no longer a single hardcoded
    constant across every error rung (Story 1.7) — a hygiene-axis crash
    (``CrashingFactory``, instantiation) and a vulnerability-axis crash
    (``CrashingEngine``, mid-run) in the SAME scan must BOTH reach the
    verdict: composed status/exit are unaffected (still error/2), and
    NEITHER typed error is dropped from errors[] regardless of which one
    the verdict picks as status.driver (that choice was already arbitrary
    pre-1.7 too, just via a different tie-break key)."""
    register_engine_for_test(monkeypatch, CrashingFactory)
    register_engine_for_test(monkeypatch, CrashingEngine)
    rc, out, _ = run_scan(capsys, CLEAN)
    document = parse_report(out)
    assert rc == 2
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "error"
    assert document["status"]["driver"] is not None
    assert {e["kind"] for e in document["errors"]} == {
        "engine-unavailable",
        "engine-execution-failed",
    }
    assert any("CrashingFactory" in e["message"] for e in document["errors"])
    assert any(e["owner"] == "crashing" for e in document["errors"])


def test_zero_dependency_manifest_is_indeterminate_not_not_applicable(
    capsys, tmp_path
):
    """D2(c) (Story 1.9): a manifest that PARSES but yields zero components/
    findings/errors is ambiguous/partial discovery, never a silent
    not-applicable — the previous 1.2-era not-applicable/exit-0 reading for
    this exact scenario is the false-green D2(c) exists to close. Status
    lands indeterminate/exit 1 by default, distinguishable on stderr from
    the empty-dir case, with coverage recording no resolution-depth claim
    (``coverage: none``) despite the manifest having been found+parsed."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.0.1"\ndependencies = []\n',
        encoding="utf-8",
    )
    rc, out, err = run_scan(capsys, tmp_path)
    document = parse_report(out)
    assert rc == 1
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "indeterminate"
    assert document["inventory_count"] == 0
    driver = document["status"]["driver"]
    assert driver is not None
    assert driver["finding_id"] == "indeterminate:empty-extraction:scan"
    assert driver["axis"] == "ingestion"
    assert driver["finding_id"] in {f["id"] for f in document["findings"]}
    # Manifest-kind-agnostic wording (Story 1.9): the old pyproject-specific
    # "[project].dependencies" claim was a false claim for the 7 other
    # manifest kinds once D2(c) made this an actual gate failure.
    assert "manifest(s) parsed but zero dependencies/components" in err
    assert "no manifest found" not in err  # NOT the empty-dir notice
    for block in document["coverage"]:
        assert block["manifests_found"] == 1
        assert block["manifests_parsed"] == 1
        assert block["deps_total"] == 0
        assert block["resolution_depth"] is None  # coverage: none


def test_zero_dependency_manifest_allow_empty_downgrades_exit_only(
    capsys, tmp_path
):
    """``--allow-empty`` downgrades D2(c)'s exit to 0 while ``status`` stays
    ``indeterminate`` (never ``clean``) — the flag only widens the exit
    projection, never the verdict itself."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.0.1"\ndependencies = []\n',
        encoding="utf-8",
    )
    rc, out, _ = run_scan(capsys, tmp_path, "--allow-empty")
    document = parse_report(out)
    assert rc == 0
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "indeterminate"
    for block in document["coverage"]:
        assert block["resolution_depth"] is None
    # Review finding (2026-07-17 pass 2): the two-namespace contract must
    # hold on the --allow-empty branch too, not just the default exit-1
    # path checked above.
    driver = document["status"]["driver"]
    assert driver["finding_id"] in {f["id"] for f in document["findings"]}


# --- deptry end-to-end fixtures (the first real engine) ----------------------


def _one_hygiene_finding(document: dict, finding_id: str) -> dict:
    """Assert exactly one finding with ``finding_id`` (axis hygiene) exists
    and return it."""
    matches = [f for f in document["findings"] if f["id"] == finding_id]
    present = [f["id"] for f in document["findings"]]
    assert matches, f"expected {finding_id!r} among {present}"
    assert len(matches) == 1
    assert matches[0]["axis"] == AXIS_HYGIENE
    return matches[0]


def test_deptry_missing_dependency_blocks_by_default(capsys):
    """DEP001 (imported-but-undeclared) BLOCKS (exit 1) by default (Story
    2.1, Gap-A): a pure-PyPI project has no conda-mapping ambiguity in its
    inventory, so the scan-wide dep001_trusted gate stays True and DEP001's
    upgraded default (policy-violation) applies. The finding is still
    surfaced with a driver on the hygiene axis (never a false-green)."""
    rc, out, err = run_scan(capsys, DEPTRY_MISSING)
    document = parse_report(out)
    assert rc == 1
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "policy-violation"
    finding = _one_hygiene_finding(
        document, "hygiene:DEP001:totally_absent_pkg_xyz"
    )
    assert finding["subject"] == "totally_absent_pkg_xyz"
    driver = document["status"]["driver"]
    assert driver["axis"] == "hygiene"
    assert driver["finding_id"] == "hygiene:DEP001:totally_absent_pkg_xyz"
    assert document["errors"] == []


def test_deptry_unused_dependency_is_a_warning(capsys):
    """DEP002 (declared-but-unused) maps to warn -> exit 0."""
    rc, out, err = run_scan(capsys, DEPTRY_UNUSED)
    document = parse_report(out)
    assert rc == 0
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "warn"
    _one_hygiene_finding(document, "hygiene:DEP002:requests")
    assert document["errors"] == []


def test_deptry_stdlib_dependency_is_a_warning(capsys):
    """DEP005 is a STDLIB dependency (verified against deptry 0.25.1), not
    'unused-dev' -> warn, exit 0."""
    rc, out, err = run_scan(capsys, DEPTRY_STDLIB)
    document = parse_report(out)
    assert rc == 0
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "warn"
    finding = _one_hygiene_finding(document, "hygiene:DEP005:argparse")
    assert "standard library" in finding["message"]
    assert document["errors"] == []


def test_deptry_ignore_config_is_honored_natively(capsys):
    """FR9: the project's own [tool.deptry] ignore suppresses DEP002 natively
    -> no hygiene finding -> a clean scan. We do not re-implement ignores."""
    rc, out, err = run_scan(capsys, DEPTRY_IGNORE)
    document = parse_report(out)
    assert rc == 0
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "clean"
    assert document["findings"] == []
    assert document["errors"] == []


def test_deptry_output_never_leaks_onto_our_streams(capsys):
    """AC2: deptry's chatty stdout/stderr are captured to the seam's
    diagnostics sink — our stdout stays exactly one schema-valid JSON doc and
    our stderr carries no deptry chatter (a clean run needs no diagnostics)."""
    rc, out, err = run_scan(capsys, DEPTRY_UNUSED)
    parse_report(out)  # exactly one schema-valid JSON document on stdout
    assert "Scanning" not in err
    assert "deptry" not in err.lower()


def test_deptry_corpus_unparseable_rate_is_within_baseline():
    """NFR-R2 ratchet: every record deptry emits over the real fixture corpus
    must map cleanly -- unparseable_rate <= UNPARSEABLE_RATE_BASELINE (which
    may only ever DECREASE)."""
    from pyforge.warden.engines import _engine_env
    from pyforge.warden.hygiene import (
        UNPARSEABLE_RATE_BASELINE,
        parse_deptry_output,
    )

    corpus = [
        CLEAN,
        DEPTRY_MISSING,
        DEPTRY_UNUSED,
        DEPTRY_STDLIB,
        DEPTRY_IGNORE,
        SENTINEL,
    ]
    for fixture in corpus:
        text, error, _exit_code = _engine_env(
            lambda output_path: ["deptry", ".", "-o", output_path, "--no-ansi"],
            owner="deptry",
            cwd=fixture,
        )
        assert error is None, f"deptry failed on {fixture.name}: {error}"
        assert text is not None
        parse = parse_deptry_output(text)
        assert parse.output_parsed, f"deptry output unparsed on {fixture.name}"
        assert parse.records_unparseable == 0, fixture.name
        assert parse.unparseable_rate <= UNPARSEABLE_RATE_BASELINE, fixture.name


def test_deptry_frontdoor_flag_is_a_genuine_no_op_against_real_deptry(capsys):
    """Fix 8 regression (2026-07-16 review): the only existing test proving
    the Story 2.2 front-door flag is a no-op for a native-pyproject.toml
    target (test_deptry_engine_frontdoor_is_a_no_op_when_native_pyproject_
    present, tests/unit/test_engine_env_deptry.py) fully mocks
    subprocess.run -- it proves only that OUR OWN code always appends
    --requirements-files, never that the REAL deptry binary actually still
    ignores it. This runs the REAL production pipeline (``cli.main``, which
    unconditionally synthesizes the front-door and passes the flag -- Story
    2.2) against DEPTRY_UNUSED, and separately invokes real deptry with NO
    --requirements-files flag at all (the pre-2.2 argv shape) over the SAME
    fixture -- the two must report the IDENTICAL hygiene finding, a genuine
    regression pin on deptry's own documented -rf-ignoring behavior (never
    just our own argv construction). deptry is a provisioned conda run-dep
    of this package (unlike test_extraction_oracle.py's renderers, which are
    test-only): a missing/failing binary here is a broken environment, so
    this mirrors this file's own no-skip-guard convention (see
    test_deptry_corpus_unparseable_rate_is_within_baseline above) rather
    than test_extraction_oracle.py's explicit skip-if-unavailable one."""
    from pyforge.warden.engines import _engine_env
    from pyforge.warden.hygiene import parse_deptry_output

    rc, out, err = run_scan(capsys, DEPTRY_UNUSED)
    document = parse_report(out)
    assert rc == 0
    with_frontdoor_ids = {
        f["id"] for f in document["findings"] if f["axis"] == AXIS_HYGIENE
    }

    text, error, _exit_code = _engine_env(
        lambda output_path: ["deptry", ".", "-o", output_path, "--no-ansi"],
        owner="deptry",
        cwd=DEPTRY_UNUSED,
    )
    assert error is None, f"deptry failed: {error}"
    assert text is not None
    parse = parse_deptry_output(text)
    assert parse.output_parsed
    without_frontdoor_ids = {f.id for f in parse.findings}

    assert with_frontdoor_ids == without_frontdoor_ids == {"hygiene:DEP002:requests"}


def test_deptry_frontdoor_merges_the_projects_own_requirements_txt(
    capsys, tmp_path
):
    """Follow-up review (2026-07-16), real deptry, no mocks:
    ``--requirements-files`` REPLACES deptry's own native default
    requirements source (``requirements.txt``) rather than merging with it
    -- verified live: ``deptry .`` over a requirements.txt project is clean,
    ``deptry . --requirements-files <other>`` reports DEP001 for every dep
    the project's own requirements.txt declares. Before the merge fix, a
    conda-sourced scan (this is a NEW 2.2 scan class -- pre-2.2 such a
    project was not-applicable and deptry never ran) with a sibling
    requirements.txt therefore false-DEP001'd all its pip-declared deps.
    The scan root's requirements.txt is now re-appended to the flag's
    comma-list; same no-skip-guard convention as the no-op test above."""
    (tmp_path / "environment.yml").write_text(
        "dependencies:\n  - numpy=1.20\n", encoding="utf-8"
    )
    (tmp_path / "requirements.txt").write_text("requests\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("import requests\n", encoding="utf-8")
    rc, out, _err = run_scan(capsys, tmp_path)
    document = parse_report(out)
    hygiene_ids = {
        f["id"] for f in document["findings"] if f["axis"] == AXIS_HYGIENE
    }
    # requests is declared by the project's OWN requirements.txt -- merged,
    # so no false DEP001; numpy (declared via the conda front-door, never
    # imported) still surfaces deptry's real signal for this fixture.
    assert "hygiene:DEP001:requests" not in hygiene_ids
    assert "hygiene:DEP002:numpy" in hygiene_ids


def test_deptry_frontdoor_merges_config_declared_requirements_files(
    capsys, tmp_path
):
    """Second review pass (2026-07-16), real deptry, no mocks: deptry's
    requirements source is its ``[tool.deptry].requirements_files`` config
    when declared -- the flag REPLACES that setting too, not just the
    ``requirements.txt`` default, so a conda-first project keeping pip deps
    at a configured path false-DEP001'd every dep it declares (verified
    live: bare ``deptry .`` green, with the flag red). The configured list
    is now what gets re-appended; same no-skip-guard convention as the
    other real-deptry tests."""
    (tmp_path / "environment.yml").write_text(
        "dependencies:\n  - numpy=1.20\n", encoding="utf-8"
    )
    (tmp_path / "pyproject.toml").write_text(
        '[tool.deptry]\nrequirements_files = ["reqs/base.txt"]\n',
        encoding="utf-8",
    )
    (tmp_path / "reqs").mkdir()
    (tmp_path / "reqs" / "base.txt").write_text("requests\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("import requests\n", encoding="utf-8")
    rc, out, _err = run_scan(capsys, tmp_path)
    document = parse_report(out)
    hygiene_ids = {
        f["id"] for f in document["findings"] if f["axis"] == AXIS_HYGIENE
    }
    # requests is declared by the config-declared reqs/base.txt -- merged,
    # so no false DEP001; numpy (declared via the conda front-door, never
    # imported) still surfaces deptry's real signal.
    assert "hygiene:DEP001:requests" not in hygiene_ids
    assert "hygiene:DEP002:numpy" in hygiene_ids


@pytest.mark.parametrize(
    "fixture",
    [DEPTRY_MISSING, DEPTRY_UNUSED, DEPTRY_STDLIB],
    ids=lambda p: p.name,
)
def test_deptry_fixture_twice_run_is_byte_identical(capsys, fixture):
    """Real-finding determinism: two scans of a deptry fixture emit
    byte-identical stdout."""
    rc_one, out_one, _ = run_scan(capsys, fixture)
    rc_two, out_two, _ = run_scan(capsys, fixture)
    assert rc_one == rc_two
    assert out_one.encode("utf-8") == out_two.encode("utf-8")


# --- Story 1.6: severity gate + verdict composition end-to-end ---------------


def test_critical_vuln_fixture_composes_policy_violation(capsys):
    """AC1: a real cli.main() scan of a pin matching the seeded CRITICAL OSV
    advisory (PDOS-FIXTURE-0001) composes policy-violation end to end -- the
    severity gate, not just the unit-level vuln_rung."""
    rc, out, err = run_scan(capsys, VULN_CRITICAL)
    document = parse_report(out)
    assert rc == 1
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "policy-violation"
    finding_id = "vuln:PDOS-FIXTURE-0001:pdos-vuln-fixture@1.0.0"
    matches = [f for f in document["findings"] if f["id"] == finding_id]
    assert len(matches) == 1
    finding = matches[0]
    assert finding["axis"] == "vulnerability"
    assert finding["severity"]["tier"] == "critical"
    driver = document["status"]["driver"]
    assert driver is not None
    assert driver["finding_id"] == finding_id
    assert driver["axis"] == "vulnerability"
    assert err == ""
    # The fixture's own comment: the fictitious dependency is also flagged
    # DEP002 (unused) by deptry -- policy-violation still outranks warn in
    # the composed verdict. Verify that concurrent finding actually exists,
    # not just that the top-level status survived it.
    _one_hygiene_finding(document, "hygiene:DEP002:pdos-vuln-fixture")


def test_high_severity_vuln_fixture_composes_warn(capsys):
    """A real (non-critical) osv-scanner match must NOT block by default
    (FR18: critical + KEV only) -- proves the warn side of the severity
    gate through the real osv-scanner subprocess, not just a hand-built
    Finding in the unit tests."""
    rc, out, err = run_scan(capsys, VULN_HIGH)
    document = parse_report(out)
    assert rc == 0
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "warn"
    finding_id = "vuln:PDOS-FIXTURE-0002:pdos-vuln-fixture-high@1.0.0"
    matches = [f for f in document["findings"] if f["id"] == finding_id]
    assert len(matches) == 1
    finding = matches[0]
    assert finding["axis"] == "vulnerability"
    assert finding["severity"]["tier"] == "high"
    # Three equal-rank warn rungs land here (this vuln: finding + deptry's
    # own DEP002 on the same fictitious, never-imported dependency + Story
    # 6.3's currency:unknown: -- pdos-vuln-fixture-high is not a bundled-
    # registry/ambient-endoflife-covered name) -- verdict.compose's
    # deterministic tie-break picks the smallest (axis, finding_id), and
    # "currency" < "hygiene" < "vulnerability" lexicographically.
    _one_hygiene_finding(document, "hygiene:DEP002:pdos-vuln-fixture-high")
    currency_finding_id = "currency:unknown:pdos-vuln-fixture-high@1.0.0"
    assert currency_finding_id in {f["id"] for f in document["findings"]}
    driver = document["status"]["driver"]
    assert driver is not None
    assert driver["finding_id"] == currency_finding_id
    assert driver["axis"] == "currency"
    assert err == ""


# --- Story 3.1: configurable policy (--fail-on, config precedence) -----------


def test_fail_on_high_escalates_vuln_high_fixture_to_policy_violation(capsys):
    """--fail-on=high moves a HIGH-severity finding from warn to
    policy-violation -- the same VULN_HIGH fixture as the warn/exit-0 test
    above, now escalated end to end through the real osv-scanner subprocess
    plus the CLI's --fail-on flag."""
    rc, out, err = run_scan(capsys, VULN_HIGH, "--fail-on", "high")
    document = parse_report(out)
    assert rc == 1
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "policy-violation"
    finding_id = "vuln:PDOS-FIXTURE-0002:pdos-vuln-fixture-high@1.0.0"
    matches = [f for f in document["findings"] if f["id"] == finding_id]
    assert len(matches) == 1
    assert matches[0]["severity"]["tier"] == "high"
    driver = document["status"]["driver"]
    assert driver is not None
    assert driver["finding_id"] == finding_id
    assert driver["axis"] == "vulnerability"
    assert err == ""


def test_config_precedence_pyproject_wins_with_conflict_warning(capsys):
    """FR30: pyproject.toml (fail-on=high) and pixi.toml (fail-on=low) in
    the same directory -- a same-key conflict resolves pyproject-wins,
    surfaced as one stderr warning naming the key + both values + the
    winner, never failing the build (the scan still completes normally)."""
    rc, out, err = run_scan(capsys, CONFIG_PRECEDENCE)
    document = parse_report(out)
    assert rc == 0
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "clean"
    assert document["errors"] == []
    assert "fail-on" in err
    assert "high" in err
    assert "low" in err
    assert "pyproject.toml" in err
    config, warnings = ConfigLoader().load(CONFIG_PRECEDENCE)
    assert config.fail_on is SeverityTier.HIGH
    assert len(warnings) == 1


def test_config_cli_flag_overrides_both_files(capsys):
    """CLI flags win over both files unconditionally -- --fail-on=critical
    resolves to CRITICAL even though pyproject.toml says "high" and
    pixi.toml says "low" (same CONFIG_PRECEDENCE fixture as above)."""
    config, _ = ConfigLoader().load(CONFIG_PRECEDENCE, cli_fail_on="critical")
    assert config.fail_on is SeverityTier.CRITICAL
    rc, out, err = run_scan(capsys, CONFIG_PRECEDENCE, "--fail-on", "critical")
    document = parse_report(out)
    assert rc == 0
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "clean"
    assert document["errors"] == []


def test_fail_under_coverage_rejects_out_of_range_value_as_a_usage_error(capsys):
    """--fail-under-coverage's own argparse `type=` callback validates at
    parse time -- an out-of-range value is a usage error (argparse's own
    exit 2), never reaching ConfigLoader/ConfigValidationError (review
    finding: this end-to-end argparse path had no test)."""
    rc, out, err = run_scan(capsys, CLEAN, "--fail-under-coverage", "150")
    assert rc == 2
    assert out == ""
    assert "--fail-under-coverage" in err


def test_fail_under_coverage_rejects_non_numeric_value_as_a_usage_error(capsys):
    rc, out, err = run_scan(capsys, CLEAN, "--fail-under-coverage", "not-a-number")
    assert rc == 2
    assert out == ""
    assert "--fail-under-coverage" in err


def test_indeterminate_outranks_a_live_warn_end_to_end(capsys):
    """AC2: one project composing a real hygiene warn rung (DEP002 on
    requests) alongside a real vulnerability-axis indeterminate rung
    (no-version withhold on leftpad) -- indeterminate outranks warn in the
    composed verdict, end to end. Story 6.2: leftpad is also unresolvable on
    the license axis (a THIRD, independently-warn-capped rung) -- proving
    indeterminate still outranks warn even with two distinct warn-tier
    sources feeding the composition, not just hygiene's."""
    rc, out, err = run_scan(capsys, WARN_AND_INDETERMINATE)
    document = parse_report(out)
    assert rc == 1
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "indeterminate"
    warn_finding = _one_hygiene_finding(document, "hygiene:DEP002:requests")
    assert warn_finding["axis"] == "hygiene"
    # The fixture's own comment: leftpad is ALSO unused, so it carries its
    # own hygiene:DEP002 finding independent of its vulnerability-axis
    # withhold -- both must coexist on the same package name.
    _one_hygiene_finding(document, "hygiene:DEP002:leftpad")
    indeterminate_finding_id = "indeterminate:no-version:leftpad"
    matches = [
        f for f in document["findings"] if f["id"] == indeterminate_finding_id
    ]
    assert len(matches) == 1
    assert matches[0]["axis"] == "vulnerability"
    # leftpad is not an installed package -> license axis withholds it too
    # (requests resolves to a deterministic, pinned resolvable license --
    # Fix 9 -- so it contributes no license finding).
    license_matches = [
        f for f in document["findings"] if f["id"] == "license:unknown:leftpad@unspecified"
    ]
    assert len(license_matches) == 1
    assert license_matches[0]["axis"] == "license"
    # Story 6.3: leftpad has no resolved version -> currency:unknown: too
    # (requests==2.31.0 resolves currency-clean against the ambient
    # endoflife.date snapshot -- tests/conftest.py's autouse
    # _currency_ambient_feed_env fixture -- so it contributes no currency
    # finding).
    currency_matches = [
        f
        for f in document["findings"]
        if f["id"] == "currency:unknown:leftpad@unspecified"
    ]
    assert len(currency_matches) == 1
    assert currency_matches[0]["axis"] == "currency"
    assert len(document["findings"]) == 5
    driver = document["status"]["driver"]
    assert driver is not None
    assert driver["finding_id"] == indeterminate_finding_id
    assert driver["axis"] == "vulnerability"
    assert err == ""


@pytest.mark.parametrize(
    "fixture",
    [VULN_CRITICAL, VULN_HIGH, WARN_AND_INDETERMINATE],
    ids=lambda p: p.name,
)
def test_severity_gate_fixture_twice_run_is_byte_identical(capsys, fixture):
    """Determinism (NFR-I3), same standard every other real-finding fixture
    in this module is held to."""
    rc_one, out_one, _ = run_scan(capsys, fixture)
    rc_two, out_two, _ = run_scan(capsys, fixture)
    assert rc_one == rc_two
    assert out_one.encode("utf-8") == out_two.encode("utf-8")


# --- Fix 8 (review finding, 2026-07-18): license gating tracks the engine ---


def test_license_gating_is_false_when_the_axis_never_ran(capsys, tmp_path):
    """--deny-licenses activates config.license_gating regardless of
    whether anything was actually scanned -- an empty target
    (manifests_parsed == 0) never runs LicenseEngine at all (cli.py's
    engines_to_run is () there), so AXIS_LICENSE never enters
    assessed_by_axis. Threading config.license_gating straight through
    used to report gating=true alongside deps_total=0/deps_assessed=0 --
    self-contradictory ("the gate is active" + "nothing was assessed")."""
    rc, out, err = run_scan(capsys, tmp_path, "--deny-licenses", "GPL-3.0-only")
    document = parse_report(out)
    by_axis = {block["axis"]: block for block in document["coverage"]}
    assert by_axis["license"]["deps_total"] == 0
    assert by_axis["license"]["deps_assessed"] == 0
    assert by_axis["license"]["gating"] is False


def test_license_gating_is_true_when_the_axis_actually_ran(capsys):
    """The contrasting case (never just a hardcoded False): a real scan
    where the license engine DID run reports gating=true for the same
    --deny-licenses flag."""
    rc, out, err = run_scan(capsys, CLEAN, "--deny-licenses", "GPL-3.0-only")
    document = parse_report(out)
    by_axis = {block["axis"]: block for block in document["coverage"]}
    assert by_axis["license"]["deps_total"] == 2
    assert by_axis["license"]["deps_assessed"] == 2
    assert by_axis["license"]["gating"] is True


# --- Story 6.3: the currency axis producer + its gate flags (FR34/FR35) ------


def test_currency_axis_produces_a_real_warn_capped_finding_end_to_end(capsys):
    """The E2E wiring proof: SENTINEL's two unresolvable-version deps
    (leftpad, requests>=2.0) each produce a real currency:unknown: finding
    via the live CurrencyEngine -- WARN-capped, never escalated (this
    story's own producer never feeds a rung above warn -- see
    tests/conformance/test_axis_producer_ceiling.py for the mechanical
    proof)."""
    rc, out, err = run_scan(capsys, SENTINEL)
    document = parse_report(out)
    currency_findings = [f for f in document["findings"] if f["axis"] == "currency"]
    assert {f["id"] for f in currency_findings} == {
        "currency:unknown:leftpad@unspecified",
        "currency:unknown:requests@unspecified",
    }
    for finding in currency_findings:
        assert finding["currency"]["verdict"] == "unknown"


def test_currency_axis_python_runtime_eol_finding_round_trips_through_the_schema(
    monkeypatch, capsys, tmp_path
):
    """The ``!``-prefixed Python-runtime ``currency:<reason>:!python-
    runtime@<ver>`` finding shape was previously only exercised via direct
    unit calls to ``currency_findings()`` (tests/unit/test_currency.py) --
    this drives it through the REAL ``cli.main()`` pipeline (report.py's
    serialization + schema validation) with a non-``unknown`` reason,
    proving the sentinel subject and the finding round-trip correctly end
    to end. Reuses the ambient endoflife-feed machinery ``tests/conftest.
    py``'s ``_currency_ambient_feed_env`` fixture already provisions
    session-wide (Fix-9's currency-axis sibling): this test overrides
    ``$PYFORGE_WARDEN_FEED_CACHE_DIR`` to its OWN isolated ``tmp_path`` (the
    same override pattern ``tests/unit/test_currency.py``'s ``test_
    currency_findings_mixed_fixture_covers_all_three_reasons`` already
    uses) so it can seed a ``python`` cycle whose ``eol`` is in the past --
    the running interpreter then resolves ``eol``, not ``unknown``."""
    runtime_version = ".".join(str(part) for part in sys.version_info[:3])
    monkeypatch.setenv(feeds.FEED_CACHE_DIR_ENV_VAR, str(tmp_path))
    feeds.write_kev_cache(tmp_path, {"vulnerabilities": []})
    feeds.write_endoflife_cache(
        tmp_path,
        {
            "python": [
                {
                    "cycle": runtime_version,
                    "releaseDate": "2020-01-01",
                    "eol": "2020-06-01",  # long past -- verdict EOL
                    "latest": runtime_version,
                }
            ]
        },
    )

    rc, out, err = run_scan(capsys, CLEAN)
    document = parse_report(out)  # schema-valid, incl. the CurrencyInfo shape

    finding_id = f"currency:eol:!python-runtime@{runtime_version}"
    matches = [f for f in document["findings"] if f["id"] == finding_id]
    assert len(matches) == 1
    finding = matches[0]
    assert finding["axis"] == "currency"
    assert finding["subject"] == "!python-runtime"
    assert finding["currency"]["verdict"] == "eol"
    assert finding["currency"]["eol_date"] == "2020-06-01"


def test_currency_gating_is_false_when_the_axis_never_ran(capsys, tmp_path):
    """--max-lag activates config.currency_gating regardless of whether
    anything was actually scanned -- mirrors Fix 8's license-axis
    precedent exactly."""
    rc, out, err = run_scan(capsys, tmp_path, "--max-lag", "5")
    document = parse_report(out)
    by_axis = {block["axis"]: block for block in document["coverage"]}
    assert by_axis["currency"]["deps_total"] == 0
    assert by_axis["currency"]["deps_assessed"] == 0
    assert by_axis["currency"]["gating"] is False


@pytest.mark.parametrize(
    "flag", [["--max-lag", "5"], ["--require-lts"], ["--fail-on-eol"]]
)
def test_currency_gating_is_true_when_the_axis_actually_ran(capsys, flag):
    """The contrasting case, parametrized over all three gate flags: a real
    scan where the currency engine DID run reports gating=true."""
    rc, out, err = run_scan(capsys, CLEAN, *flag)
    document = parse_report(out)
    by_axis = {block["axis"]: block for block in document["coverage"]}
    assert by_axis["currency"]["deps_total"] == 2
    assert by_axis["currency"]["deps_assessed"] == 2
    assert by_axis["currency"]["gating"] is True


@pytest.mark.parametrize(
    "flag", [["--max-lag", "5"], ["--require-lts"], ["--fail-on-eol"]]
)
def test_currency_gate_flags_never_change_the_findings_themselves(capsys, flag):
    """The story's own core AC: currency_findings()'s own output (ids,
    verdicts, tiers) is BYTE-IDENTICAL whether or not any of the three gate
    flags is set -- proving this story adds no escalation logic. Only
    ``currency.gating`` differs."""
    _, out_unconfigured, _ = run_scan(capsys, WARN_AND_INDETERMINATE)
    document_unconfigured = parse_report(out_unconfigured)
    _, out_gated, _ = run_scan(capsys, WARN_AND_INDETERMINATE, *flag)
    document_gated = parse_report(out_gated)

    def _currency_findings(document: dict) -> list:
        return sorted(
            (f for f in document["findings"] if f["axis"] == "currency"),
            key=lambda f: f["id"],
        )

    assert _currency_findings(document_unconfigured) == _currency_findings(document_gated)
    by_axis_unconfigured = {
        block["axis"]: block for block in document_unconfigured["coverage"]
    }
    by_axis_gated = {block["axis"]: block for block in document_gated["coverage"]}
    assert by_axis_unconfigured["currency"]["gating"] is False
    assert by_axis_gated["currency"]["gating"] is True


def test_max_lag_rejects_a_negative_value_as_a_usage_error(capsys):
    """--max-lag's own argparse `type=` callback validates at parse time --
    mirrors test_fail_under_coverage_rejects_out_of_range_value_as_a_usage_
    error's proof for --fail-under-coverage."""
    rc, out, err = run_scan(capsys, CLEAN, "--max-lag", "-1")
    assert rc == 2
    assert out == ""
    assert "--max-lag" in err


def test_max_lag_rejects_a_non_numeric_value_as_a_usage_error(capsys):
    rc, out, err = run_scan(capsys, CLEAN, "--max-lag", "not-a-number")
    assert rc == 2
    assert out == ""
    assert "--max-lag" in err


def test_blank_deny_licenses_flag_is_a_clean_config_error_not_a_crash(capsys):
    """Fix 5 follow-up (review finding, 2026-07-18): an explicitly blank
    --deny-licenses now raises ConfigValidationError inside
    ConfigLoader.load -- cli.py's own error-recovery fallback
    (EffectiveConfig.default_with_cli_overrides, meant to preserve a GOOD
    CLI flag past an UNRELATED config-file failure) used to re-apply the
    SAME bad flag value and raise a second, uncaught
    ConfigValidationError, misprojecting as `internal error` + a traceback
    (main's last-resort net) instead of a clean config-validation exit.
    Must land as a normal error report: exit 2, one config-validation
    error record, never a traceback on stderr."""
    rc, out, err = run_scan(capsys, CLEAN, "--deny-licenses", "")
    document = parse_report(out)
    assert rc == 2
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "error"
    assert [e["kind"] for e in document["errors"]] == ["config-validation"]
    assert "deny-licenses" in document["errors"][0]["message"]
    assert "internal error" not in err
    assert "Traceback" not in err


def test_invalid_spdx_deny_licenses_flag_is_a_clean_config_error_not_a_crash(capsys):
    """Follow-up review pass (2026-07-18): an entry that cannot normalize
    as SPDX (the colloquial ``GPLv3``) could never match any resolved
    license — a configured-but-structurally-inert gate. Config load now
    rejects it; must land as a normal error report through cli.py's whole
    recovery chain: exit 2, one config-validation record naming the entry,
    never a traceback."""
    rc, out, err = run_scan(capsys, CLEAN, "--deny-licenses", "GPLv3")
    document = parse_report(out)
    assert rc == 2
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "error"
    assert [e["kind"] for e in document["errors"]] == ["config-validation"]
    assert "GPLv3" in document["errors"][0]["message"]
    assert "internal error" not in err
    assert "Traceback" not in err


# --- Story 2.4: honest split coverage + the indeterminate producer (C0b) ----


def test_recipe_common_is_the_combined_ac1_ac2_ac3_conformance_proof(capsys):
    """The single fixture that simultaneously proves AC1 (split coverage +
    the coverage-qualified indeterminate verdict), AC2 (a withheld dep is
    never dropped or defaulted to clean), and AC3 (a source-less conda
    manifest never becomes a DEP002 noise wall) through the REAL cli.main()
    pipeline over a real conda producer -- not a hand-built ComplianceReport.

    ``recipe_common/recipe.yaml`` mixes a range-only dep (``numpy >=1.20``),
    a bare no-version dep (``python``), and a conda-map-unresolvable dep
    (``mypkg==1.2.3``) -- by construction it has zero adjacent ``.py``
    files, so it doubles as the AC3 regression proof in the same test."""
    rc, out, err = run_scan(capsys, RECIPE_COMMON)
    document = parse_report(out)
    assert rc == 1
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "indeterminate"
    by_axis = {block["axis"]: block for block in document["coverage"]}
    assert set(by_axis) == {"hygiene", "vulnerability", "license", "currency"}
    # AC3: no adjacent .py source anywhere -- the hygiene axis is honestly
    # not-applicable, never a 100%-DEP002 noise wall.
    assert by_axis["hygiene"]["deps_total"] == 0
    assert by_axis["hygiene"]["deps_assessed"] == 0
    assert by_axis["hygiene"]["resolution_depth"] is None
    # Stronger than a DEP002-only check (review finding, 2026-07-17):
    # DeptryEngine is filtered out of engines_to_run entirely when hygiene
    # isn't applicable, so NO hygiene-family finding of any DEP code can
    # appear -- assert that directly rather than a narrower proxy for it.
    assert [f for f in document["findings"] if f["axis"] == "hygiene"] == []
    # AC1/AC2: the vulnerability axis's coverage is real, and the withheld
    # deps are never dropped or defaulted to clean.
    assert by_axis["vulnerability"]["deps_total"] == document["inventory_count"]
    assert document["errors"] == []
    assert err == ""


def test_hygiene_not_applicable_fixture_is_clean_and_isolated(capsys):
    """AC3, isolated from any concurrent indeterminate noise: a fully
    resolvable, source-less conda/pixi manifest stays genuinely clean --
    hygiene-not-applicable never blocks an otherwise-clean scan."""
    rc, out, err = run_scan(capsys, HYGIENE_NOT_APPLICABLE)
    document = parse_report(out)
    assert rc == 0
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "clean"
    assert document["findings"] == []
    assert document["errors"] == []
    by_axis = {block["axis"]: block for block in document["coverage"]}
    assert by_axis["hygiene"]["deps_total"] == 0
    assert by_axis["hygiene"]["deps_assessed"] == 0
    assert by_axis["vulnerability"]["deps_total"] == 1
    assert by_axis["vulnerability"]["deps_assessed"] == 1
    assert err == ""


@pytest.mark.parametrize(
    ("fixture", "expected_status", "expected_rc"),
    [
        # ca-certificates is conda-map-unmapped -> indeterminate/exit 1.
        (PIXI_LOCK_BASIC, "indeterminate", 1),
        # numpy/requests are both exact-pinned and fully clean against the
        # offline test DB on the hygiene/vulnerability axes. Story 6.2:
        # numpy's conda-lock.yml provenance carries no about:license (that
        # field only exists on a recipe.yaml/meta.yaml), so the license axis
        # honestly withholds it -> one warn-capped finding, composing "warn"
        # (still exit 0 -- warn_is_error is never set by cli.py).
        (CONDA_LOCK_BASIC, "warn", 0),
    ],
    ids=lambda v: v.name if isinstance(v, Path) else str(v),
)
def test_lockfile_presence_marks_resolution_depth_locked_closure_for_a_real_conda_producer(
    capsys, fixture, expected_status, expected_rc
):
    """AC1: ``resolution_depth`` through a REAL conda/pixi producer end to
    end (not the pyproject.toml-only proof in ``tests/unit/
    test_discovery_extract_cli.py``) -- a committed lockfile (mixing real
    conda: and pypi: rows) claims the full transitive closure on the
    vulnerability axis. Neither lockfile fixture carries any adjacent ``.py``
    source, so (AC3) the hygiene axis is honestly not-applicable here --
    ``resolution_depth`` is the vulnerability axis's claim to make.

    ``expected_status``/``expected_rc`` are explicit expected-value pins, not
    a tautological self-consistency check (review finding, 2026-07-17) --
    each verified live via ``cli.main`` under this suite's own conftest
    fixtures (the two lockfiles genuinely differ: PIXI_LOCK_BASIC carries an
    unmapped conda dep; CONDA_LOCK_BASIC's deps are hygiene/vulnerability-
    clean, but Story 6.2's license axis honestly withholds numpy -- a
    lockfile carries no about:license -- composing 'warn')."""
    rc, out, err = run_scan(capsys, fixture)
    document = parse_report(out)
    by_axis = {block["axis"]: block for block in document["coverage"]}
    assert by_axis["hygiene"]["resolution_depth"] is None
    assert by_axis["vulnerability"]["resolution_depth"] == "locked-closure"
    assert rc == expected_rc
    assert rc == document["exit_code"]
    assert document["status"]["value"] == expected_status


def test_recipe_common_without_a_lockfile_stays_direct_only(capsys):
    """The direct-only counterpart to the lockfile row above, over the SAME
    real conda producer (``recipe_common``, no lockfile present)."""
    rc, out, err = run_scan(capsys, RECIPE_COMMON)
    document = parse_report(out)
    by_axis = {block["axis"]: block for block in document["coverage"]}
    # AC3: hygiene is not-applicable here (no adjacent .py source), so its
    # own resolution_depth is None by construction -- the vulnerability axis
    # is the one that carries the direct-only claim for this fixture.
    assert by_axis["vulnerability"]["resolution_depth"] == "direct-only"
    # An explicit expected-value pin (review finding, 2026-07-17): see the
    # lockfile row above -- recipe_common's own range-only/no-version/
    # unmapped deps make indeterminate/exit 1 the real, verified verdict.
    assert rc == 1
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "indeterminate"


def test_hygiene_not_applicable_never_leaks_a_hygiene_axis_finding(capsys):
    """Review finding, 2026-07-17 (verified live before this fix): a
    RAW_MALFORMED component's hygiene_covered=False is derived by
    DefaultPolicy.evaluate purely from the component itself -- independent
    of whether DeptryEngine ever ran -- so before this fix, a source-less
    manifest with an unresolvable dep reported hygiene deps_total=0
    (not-applicable) alongside a live `axis: "hygiene"` finding, a direct
    self-contradiction of the not-applicable claim. cli.py now filters
    hygiene-axis findings/rungs out of DefaultPolicy's output when
    hygiene_applicable is False; this fixture's SAME malformed component
    independently withholds on the vulnerability axis too, so the verdict
    stays correctly indeterminate -- proving the filter never manufactures
    a false clean by removing the sole non-clean signal."""
    rc, out, err = run_scan(capsys, HYGIENE_NOT_APPLICABLE_MALFORMED)
    document = parse_report(out)
    by_axis = {block["axis"]: block for block in document["coverage"]}
    assert by_axis["hygiene"]["deps_total"] == 0
    assert by_axis["hygiene"]["deps_assessed"] == 0
    assert [f for f in document["findings"] if f["axis"] == "hygiene"] == []
    # The malformed component's OWN vulnerability-axis withhold still
    # correctly drives a non-clean verdict -- never a false clean.
    assert document["status"]["value"] == "indeterminate"
    assert rc == 1
    assert rc == document["exit_code"]
    assert any(f["axis"] == "vulnerability" for f in document["findings"])


def test_retired_clean_at_phrasing_never_appears_in_source():
    """Ratchet: the retired 'clean at N%' phrasing (outlawed by FR16) must
    never appear anywhere under the package's own source."""
    package_root = Path(__file__).resolve().parent.parent.parent / "src" / "pyforge" / "warden"
    offenders = []
    for path in package_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "clean at" in text.lower():
            offenders.append(str(path))
    assert offenders == []


# --- Story 1.8: --format text renderer + NFR-I3 pseudo-TTY regression -------


def test_text_format_clean_fixture_is_a_single_header_line(capsys):
    """FR17: text is the default format; a clean scan emits only the
    verdict line -- no driver/finding/error lines follow."""
    rc = main(["scan", str(CLEAN)])
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "warden: status=clean exit_code=0 findings=0\n"
    assert captured.err == ""


def test_text_format_findings_fixture_emits_driver_and_finding_lines(capsys):
    """FR17: a real (non-clean) scan's text output carries the driver line
    plus one line per finding -- the human summary the AC actually asks
    for, not the pre-1.8 single debug line."""
    rc = main(["scan", str(DEPTRY_UNUSED)])
    captured = capsys.readouterr()
    assert rc == 0
    lines = captured.out.splitlines()
    assert len(lines) == 3
    assert lines[0] == "warden: status=warn exit_code=0 findings=1"
    assert lines[1] == "  driver: axis=hygiene id=hygiene:DEP002:requests"
    # line 2's message text is deptry's own; only the prefix is pinned here.
    assert lines[2].startswith("  [hygiene] none hygiene:DEP002:requests -- ")


def test_text_format_error_fixture_emits_driver_and_error_lines(capsys, tmp_path):
    """FR17/error taxonomy: a Status.ERROR report's text output carries the
    error:<kind>:<subject> driver line plus one line per error. Story 3.1:
    a malformed pyproject.toml now yields TWO errors (config-parse +
    unparsable-manifest -- see test_malformed_toml_still_emits_an_error_
    report), so this now carries two error lines, sorted by (kind, owner,
    message) -- "config-parse" < "unparsable-manifest" lexically."""
    (tmp_path / "pyproject.toml").write_text(
        "[project\nname = 'broken", encoding="utf-8"
    )
    rc = main(["scan", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 2
    lines = captured.out.splitlines()
    assert len(lines) == 4
    assert lines[0] == "warden: status=error exit_code=2 findings=0"
    assert lines[1].startswith("  driver: axis=ingestion id=error:config-parse:")
    # line 2/3's message text is exception-derived; only the prefix is pinned.
    assert lines[2].startswith("  [error:config-parse] config -- ")
    assert lines[3].startswith("  [error:unparsable-manifest] extract -- ")


def test_json_format_stays_pure_under_a_chatty_engine_and_a_pseudo_tty(
    capsys, monkeypatch
):
    """NFR-I3 regression (spec's I/O matrix, Story 1.8): ``test_deptry_
    output_never_leaks_onto_our_streams`` above already proves a chatty
    real engine (DEPTRY_UNUSED) never contaminates stdout under an
    ordinary (non-TTY) captured stream. Nothing in this codebase currently
    branches on ``isatty()`` (verified: zero references under ``src/``;
    ``_engine_env`` routes every engine subprocess's stdout/stderr to
    ``DEVNULL`` unconditionally, never inspecting the parent's TTY status)
    -- this test does NOT exercise a real TTY-conditional code path today.
    It pins that fact as a forward regression guard: stdout stays exactly
    one schema-valid JSON document, no engine chatter, even with
    ``isatty()`` patched True, so a future change that starts branching on
    TTY status (a progress bar, ANSI color) cannot silently reintroduce
    stdout contamination without breaking this test first."""
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    assert sys.stdout.isatty() is True  # the patch actually took effect
    rc, out, err = run_scan(capsys, DEPTRY_UNUSED)
    document = parse_report(out)  # exactly one schema-valid JSON document
    assert rc == document["exit_code"]
    assert "Scanning" not in err
    assert "deptry" not in err.lower()
