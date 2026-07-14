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
DEPTRY_MISSING = FIXTURES / "deptry_missing"
DEPTRY_UNUSED = FIXTURES / "deptry_unused"
DEPTRY_STDLIB = FIXTURES / "deptry_stdlib"
DEPTRY_IGNORE = FIXTURES / "deptry_ignore"


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


def test_clean_fixture_coverage_reflects_deptry_hygiene_assessment(capsys):
    _, out, _ = run_scan(capsys, CLEAN)
    document = parse_report(out)
    by_axis = {block["axis"]: block for block in document["coverage"]}
    assert set(by_axis) == {"hygiene", "vulnerability"}
    for block in by_axis.values():
        assert block["manifests_found"] == 1
        assert block["manifests_parsed"] == 1
        assert block["deps_total"] == 2
        assert block["resolution_depth"] == "direct-only"
    # Story 1.3: deptry assessed all declared deps for hygiene; the
    # vulnerability axis has no engine yet (Story 1.5), so it stays 0.
    assert by_axis["hygiene"]["deps_assessed"] == 2
    assert by_axis["vulnerability"]["deps_assessed"] == 0


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


class FindingsOnlyEngine:
    name = "findings-only"

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
        )


class SysExitEngine:
    name = "sys-exit"

    def run(self, target, inventory) -> EngineResult:
        raise SystemExit(0)


class CrashingFactory:
    name = "crashing-factory"

    def __init__(self) -> None:
        raise RuntimeError("factory blew up at instantiation")

    def run(self, target, inventory) -> EngineResult:
        raise AssertionError("unreachable: the constructor always raises")


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
    traceback with no report and never 'internal error'."""
    (tmp_path / "pyproject.toml").write_text(
        "x = " + "[" * 8000 + "]" * 8000 + "\n", encoding="utf-8"
    )
    rc, out, err = run_scan(capsys, tmp_path)
    document = parse_report(out)
    assert rc == 2
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "error"
    (error,) = document["errors"]
    assert error["kind"] == "unparsable-manifest"
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


def test_zero_dependency_manifest_is_distinguishable_on_stderr(
    capsys, tmp_path
):
    """A parsed manifest declaring no dependencies is honest not-applicable
    (nothing existed to scan) but must be distinguishable from the
    empty-dir case: a dedicated stderr notice, and coverage that records
    the manifest as found+parsed."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.0.1"\ndependencies = []\n',
        encoding="utf-8",
    )
    rc, out, err = run_scan(capsys, tmp_path)
    document = parse_report(out)
    assert rc == 0
    assert document["status"]["value"] == "not-applicable"
    assert document["inventory_count"] == 0
    # The notice names WHAT was scanned ([project].dependencies) instead of
    # claiming "declares no dependencies" — a poetry-style manifest with
    # deps only outside that section hits this path too, and the old
    # wording was a false claim for it (section-aware discovery is 1.9's).
    assert "no dependencies found in [project].dependencies" in err
    assert "no manifest found" not in err  # NOT the empty-dir notice
    for block in document["coverage"]:
        assert block["manifests_found"] == 1
        assert block["manifests_parsed"] == 1
        assert block["deps_total"] == 0


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


def test_deptry_missing_dependency_is_a_warning(capsys):
    """DEP001 (imported-but-undeclared) WARNS in 1.3 (exit 0), not blocks:
    Gap-A requires DEP001's block to be gated on name-mapping confidence,
    which needs Story 2.1's conda->pypi map; deptry's DEP001 false-positives
    (guarded optional imports) would otherwise produce a benign false-red.
    The finding is still surfaced with a driver on the hygiene axis (never a
    false-green) — 2.1 upgrades it to block-on-high-confidence. Follow-up
    Opus review, 2026-07-14."""
    rc, out, err = run_scan(capsys, DEPTRY_MISSING)
    document = parse_report(out)
    assert rc == 0
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "warn"
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
    from python_deptry_osv_scanner.engines import _engine_env
    from python_deptry_osv_scanner.hygiene import (
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
        text, error = _engine_env(
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
