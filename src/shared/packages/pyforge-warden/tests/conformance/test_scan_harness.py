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

from pyforge.warden import engines as engines_module
from pyforge.warden.cli import main
from pyforge.warden.interfaces import EngineResult
from pyforge.warden.mapping import load_conda_pypi_map
from pyforge.warden.models import (
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
VULN_CRITICAL = FIXTURES / "vuln_critical"
VULN_HIGH = FIXTURES / "vuln_high"
WARN_AND_INDETERMINATE = FIXTURES / "warn_and_indeterminate"
RECIPE_COMMON = FIXTURES / "recipe_common"
HYGIENE_NOT_APPLICABLE = FIXTURES / "hygiene_not_applicable"
HYGIENE_NOT_APPLICABLE_MALFORMED = FIXTURES / "hygiene_not_applicable_malformed"
PIXI_LOCK_BASIC = FIXTURES / "pixi_lock_basic"
CONDA_LOCK_BASIC = FIXTURES / "conda_lock_basic"


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
    # Story 1.3: deptry assessed all declared deps for hygiene. Story 1.5:
    # osv-scanner ran against the ambient test-session offline DB (conftest)
    # and assessed both vuln-matchable deps too — a genuinely clean scan,
    # not the pre-1.5 "no engine ever consulted" stub 0.
    assert by_axis["hygiene"]["deps_assessed"] == 2
    assert by_axis["vulnerability"]["deps_assessed"] == 2


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
    assert document["status"]["driver"]["finding_id"].startswith(
        "error:unparsable-manifest:"
    )
    assert [e["kind"] for e in document["errors"]] == ["unparsable-manifest"]
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
    # Two equal-rank warn rungs land here (this vuln: finding + deptry's own
    # DEP002 on the same fictitious, never-imported dependency below) --
    # verdict.compose's deterministic tie-break picks the smallest
    # (axis, finding_id), and "hygiene" < "vulnerability" lexicographically.
    _one_hygiene_finding(document, "hygiene:DEP002:pdos-vuln-fixture-high")
    driver = document["status"]["driver"]
    assert driver is not None
    assert driver["finding_id"] == "hygiene:DEP002:pdos-vuln-fixture-high"
    assert driver["axis"] == "hygiene"
    assert err == ""


def test_indeterminate_outranks_a_live_warn_end_to_end(capsys):
    """AC2: one project composing a real hygiene warn rung (DEP002 on
    requests) alongside a real vulnerability-axis indeterminate rung
    (no-version withhold on leftpad) -- indeterminate outranks warn in the
    composed verdict, end to end."""
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
    assert len(document["findings"]) == 3
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
    assert set(by_axis) == {"hygiene", "vulnerability"}
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
    "fixture", [PIXI_LOCK_BASIC, CONDA_LOCK_BASIC], ids=lambda p: p.name
)
def test_lockfile_presence_marks_resolution_depth_locked_closure_for_a_real_conda_producer(
    capsys, fixture
):
    """AC1: ``resolution_depth`` through a REAL conda/pixi producer end to
    end (not the pyproject.toml-only proof in ``tests/unit/
    test_discovery_extract_cli.py``) -- a committed lockfile (mixing real
    conda: and pypi: rows) claims the full transitive closure on the
    vulnerability axis. Neither lockfile fixture carries any adjacent ``.py``
    source, so (AC3) the hygiene axis is honestly not-applicable here --
    ``resolution_depth`` is the vulnerability axis's claim to make."""
    rc, out, err = run_scan(capsys, fixture)
    document = parse_report(out)
    by_axis = {block["axis"]: block for block in document["coverage"]}
    assert by_axis["hygiene"]["resolution_depth"] is None
    assert by_axis["vulnerability"]["resolution_depth"] == "locked-closure"
    # An explicit expected-value pin, not a tautological self-consistency
    # check (review finding, 2026-07-17): both fixtures carry at least one
    # withheld/unmapped dep, so the real verdict is indeterminate/exit 1 --
    # a regression that flipped the overall status would be caught here.
    assert rc == 1
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "indeterminate"


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
