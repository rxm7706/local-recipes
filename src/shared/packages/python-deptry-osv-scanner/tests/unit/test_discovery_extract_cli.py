"""Unit tests — the I/O-matrix edges: discovery stub, pyproject extractor,
routing, and the CLI surface (Story 1.2).

The matrix is testable, not aspirational: every extractor row
(pinned/range/arbitrary-equality/bare/invalid-string/markers-ignored,
TOMLDecodeError path) and every CLI row (``--version``→0, usage error→2
never 0, KeyboardInterrupt→130 in every window incl. parse_args,
nonexistent/empty target → empty stdout + 2, text format single line,
BrokenPipeError absorbed, error-taxonomy rows: unreadable manifest /
unknown kind / internal ValueError / discovery OSError) has a
deterministic unit test here.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from importlib import resources
from pathlib import Path

import jsonschema
import pytest

from python_deptry_osv_scanner import cli
from python_deptry_osv_scanner.cli import main
from python_deptry_osv_scanner.discovery import PYPROJECT_KIND, discover
from python_deptry_osv_scanner.extract import (
    UnparsableManifestError,
    extractor_for,
)
from python_deptry_osv_scanner.extract.pyproject import (
    PROJECT_DEPENDENCIES_SECTION,
    PyprojectExtractor,
)
from python_deptry_osv_scanner.models import (
    CveMatchLevel,
    Ecosystem,
    ExtractionMode,
    IdentitySource,
    ScannedManifest,
    WithholdReason,
)
from python_deptry_osv_scanner.routing import DefaultRouter
from python_deptry_osv_scanner.verdict import EXIT_SIGINT

MANIFEST = ScannedManifest(path=PYPROJECT_KIND, kind=PYPROJECT_KIND)


def write_pyproject(directory: Path, deps: list[str]) -> Path:
    # json.dumps of a list of plain strings is valid TOML array syntax.
    body = (
        "[project]\n"
        'name = "demo"\n'
        'version = "0.0.1"\n'
        f"dependencies = {json.dumps(deps)}\n"
    )
    path = directory / "pyproject.toml"
    path.write_text(body, encoding="utf-8")
    return path


def extract_from(directory: Path, deps: list[str]):
    path = write_pyproject(directory, deps)
    return PyprojectExtractor(DefaultRouter()).extract(path, MANIFEST)


def load_schema() -> dict:
    schema_file = (
        resources.files("python_deptry_osv_scanner") / "data" / "report-schema.json"
    )
    return json.loads(schema_file.read_text(encoding="utf-8"))


def scan_json(capsys, target) -> tuple[int, dict, str]:
    """Run a JSON-format scan and return (rc, schema-validated report,
    stderr) — the report-still-emitted assertion for error-path rows."""
    capsys.readouterr()
    rc = main(["scan", str(target), "--format", "json"])
    captured = capsys.readouterr()
    document = json.loads(captured.out)
    jsonschema.Draft202012Validator(load_schema()).validate(document)
    return rc, document, captured.err


# --- discovery stub ----------------------------------------------------------


def test_discover_finds_the_single_manifest(tmp_path):
    write_pyproject(tmp_path, [])
    manifests = discover(tmp_path)
    assert manifests == (
        ScannedManifest(path="pyproject.toml", kind="pyproject.toml"),
    )


def test_discover_records_the_path_relative_to_the_target(tmp_path):
    write_pyproject(tmp_path, [])
    (manifest,) = discover(tmp_path)
    assert manifest.path == "pyproject.toml"  # never absolute
    assert not Path(manifest.path).is_absolute()


def test_discover_returns_empty_for_a_dir_without_manifest(tmp_path):
    assert discover(tmp_path) == ()


def test_discover_fails_closed_on_a_pyproject_directory(tmp_path):
    """A pyproject.toml that exists but is not a regular file is
    found-but-refused: it must FAIL CLOSED, never read as absent."""
    (tmp_path / "pyproject.toml").mkdir()
    with pytest.raises(OSError, match="not a regular file"):
        discover(tmp_path)


def test_discover_treats_a_file_target_as_absent(tmp_path):
    """<file>/pyproject.toml stats NotADirectoryError — genuinely absent,
    not an error."""
    file_target = tmp_path / "somefile"
    file_target.write_text("", encoding="utf-8")
    assert discover(file_target) == ()


def test_discover_fails_closed_on_a_vanished_target(tmp_path):
    """A nonexistent target directory is undeterminable manifest state
    (the TOCTOU window: it passed the CLI gate, then vanished) — it must
    fail closed, never read as "no manifest" → exit 0."""
    with pytest.raises(OSError, match="vanished"):
        discover(tmp_path / "gone")


@pytest.mark.skipif(os.name != "posix", reason="symlinks are POSIX-reliable")
def test_discover_fails_closed_on_a_dangling_symlink(tmp_path):
    """A dangling pyproject.toml symlink is visibly present but unreadable:
    found-but-refused, never 'nothing existed'."""
    (tmp_path / "pyproject.toml").symlink_to(tmp_path / "no-such-target")
    with pytest.raises(OSError, match="dangling symlink"):
        discover(tmp_path)


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission semantics")
def test_discover_propagates_unexpected_stat_errors(tmp_path):
    """Path.is_file() swallows OSError (permission-denied would read as "no
    manifest" → a false green); the explicit stat propagates it instead."""
    if os.geteuid() == 0:
        pytest.skip("root ignores directory permission bits")
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0)
    try:
        with pytest.raises(PermissionError):
            discover(locked)
    finally:
        locked.chmod(0o755)


# --- extractor rows ----------------------------------------------------------


def test_pinned_dep_is_concrete_and_matchable(tmp_path):
    (component,) = extract_from(tmp_path, ["requests==2.31.0"])
    assert component.name == "requests"
    assert component.version == "2.31.0"
    assert component.ecosystem is Ecosystem.PYPI
    assert component.cve_match_level == CveMatchLevel.EXACT
    assert component.extraction_mode == ExtractionMode.PARSED
    assert component.identity_source == IdentitySource.NATIVE
    assert component.pypi_identity is not None
    assert component.pypi_identity.name == "requests"
    assert component.pypi_identity.version == "2.31.0"
    assert component.vuln_matchable is True
    assert component.indeterminate_reason is None
    assert component.purl == "pkg:pypi/requests@2.31.0"
    assert [(p.manifest, p.section) for p in component.provenance] == [
        ("pyproject.toml", PROJECT_DEPENDENCIES_SECTION)
    ]


def test_range_dep_is_withheld_range_only(tmp_path):
    (component,) = extract_from(tmp_path, ["requests>=2.0"])
    assert component.version is None
    assert component.cve_match_level == CveMatchLevel.NAME_ONLY
    assert component.vuln_matchable is False
    assert component.indeterminate_reason == WithholdReason.RANGE_ONLY


def test_prefix_pin_is_a_range_not_an_exact_pin(tmp_path):
    """==1.2.* is a prefix match — conservatively withheld, never a version
    guess (Gap-C)."""
    (component,) = extract_from(tmp_path, ["requests==2.31.*"])
    assert component.version is None
    assert component.indeterminate_reason == WithholdReason.RANGE_ONLY


def test_bare_dep_is_withheld_no_version(tmp_path):
    (component,) = extract_from(tmp_path, ["leftpad"])
    assert component.version is None
    assert component.cve_match_level == CveMatchLevel.NAME_ONLY
    assert component.vuln_matchable is False
    assert component.indeterminate_reason == WithholdReason.NO_VERSION


def test_invalid_requirement_is_kept_raw_malformed(tmp_path):
    raw = "not a valid requirement !!!"
    (component,) = extract_from(tmp_path, [raw])
    assert component.name == raw  # kept, never dropped silently
    assert component.version is None
    assert component.extraction_mode == ExtractionMode.RAW_MALFORMED
    assert component.identity_source == IdentitySource.NONE
    assert component.pypi_identity is None
    assert component.vuln_matchable is False
    assert component.indeterminate_reason == WithholdReason.NO_VERSION


def test_environment_markers_are_ignored(tmp_path):
    (component,) = extract_from(
        tmp_path, ["requests==2.31.0; python_version >= '3.8'"]
    )
    assert component.name == "requests"
    assert component.version == "2.31.0"
    assert component.vuln_matchable is True


def test_marker_conditional_dep_is_labeled_union_marked(tmp_path):
    """Union semantics are extracted AND labeled: a marker-conditional dep
    carries extraction_mode=union-marked (the frozen enum's slot for
    exactly this case), staying distinguishable from an unconditional
    one; an unconditional dep stays 'parsed'."""
    marked, plain = extract_from(
        tmp_path,
        ["requests==2.31.0; python_version >= '3.8'", "urllib3==2.2.1"],
    )
    assert marked.extraction_mode == ExtractionMode.UNION_MARKED
    assert plain.extraction_mode == ExtractionMode.PARSED
    # honesty labeling must not weaken matchability: the pin is concrete
    assert marked.vuln_matchable is True


def test_arbitrary_equality_is_a_concrete_pin(tmp_path):
    """PEP 440 arbitrary equality (===) pins exactly one version — treated
    like ==, never withheld as range-only."""
    (component,) = extract_from(tmp_path, ["pkg===1.2.3"])
    assert component.version == "1.2.3"
    assert component.cve_match_level == CveMatchLevel.EXACT
    assert component.vuln_matchable is True
    assert component.indeterminate_reason is None


def test_wildcard_equality_stays_range_only_beside_arbitrary_equality(tmp_path):
    """==1.2.* wildcards a RANGE (unlike ===) — still withheld."""
    (component,) = extract_from(tmp_path, ["pkg==1.2.*"])
    assert component.version is None
    assert component.indeterminate_reason == WithholdReason.RANGE_ONLY


def test_wildcard_looking_arbitrary_equality_is_withheld_too(tmp_path):
    """===1.2.* would flow a wildcard-looking token into CVE matching as a
    'concrete' version — conservatively withheld (Gap-C: never guess)."""
    (component,) = extract_from(tmp_path, ["pkg===1.2.*"])
    assert component.version is None
    assert component.vuln_matchable is False
    assert component.indeterminate_reason == WithholdReason.RANGE_ONLY


def test_invalid_utf8_manifest_is_unparsable_manifest(tmp_path):
    """Invalid UTF-8 raises UnicodeDecodeError out of tomllib — a ValueError
    subclass but NOT TOMLDecodeError. A wrong-encoding save is a broken
    manifest, never an internal tool bug."""
    path = tmp_path / "pyproject.toml"
    path.write_bytes(b'[project]\nname = "x\xff\xfe"\ndependencies = []\n')
    with pytest.raises(UnparsableManifestError):
        PyprojectExtractor(DefaultRouter()).extract(path, MANIFEST)


def test_identity_name_is_pep503_canonical_component_name_stays_raw(tmp_path):
    """The single-record path matches the 1.1 merge path's canonical
    spelling: identity name PEP-503-canonical, Component.name raw."""
    (component,) = extract_from(tmp_path, ["Django==5.0.6"])
    assert component.name == "Django"
    assert component.pypi_identity is not None
    assert component.pypi_identity.name == "django"
    assert component.pypi_identity.version == "5.0.6"


def test_identity_canonicalization_covers_the_versionless_path(tmp_path):
    (component,) = extract_from(tmp_path, ["Zope.Interface>=5"])
    assert component.name == "Zope.Interface"
    assert component.pypi_identity is not None
    assert component.pypi_identity.name == "zope-interface"
    assert component.pypi_identity.version is None


def test_malformed_toml_raises_value_error(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text("[project\nname = 'broken", encoding="utf-8")
    with pytest.raises(ValueError):
        PyprojectExtractor(DefaultRouter()).extract(path, MANIFEST)


def test_malformed_toml_raises_the_unparsable_manifest_subclass(tmp_path):
    """Genuine manifest problems raise UnparsableManifestError specifically —
    the class the CLI maps to ErrorRecord(kind=unparsable-manifest)."""
    path = tmp_path / "pyproject.toml"
    path.write_text("[project\nname = 'broken", encoding="utf-8")
    with pytest.raises(UnparsableManifestError):
        PyprojectExtractor(DefaultRouter()).extract(path, MANIFEST)


def test_non_string_dependency_entry_raises_value_error(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text(
        '[project]\nname = "demo"\ndependencies = [1, 2]\n', encoding="utf-8"
    )
    with pytest.raises(ValueError):
        PyprojectExtractor(DefaultRouter()).extract(path, MANIFEST)


def test_unknown_manifest_kind_has_no_extractor():
    with pytest.raises(ValueError):
        extractor_for("meta.yaml", DefaultRouter())


# --- routing -----------------------------------------------------------------


def test_router_routes_pyproject_dependencies_to_pypi():
    ecosystem = DefaultRouter().route(PYPROJECT_KIND, PROJECT_DEPENDENCIES_SECTION)
    assert ecosystem is Ecosystem.PYPI


def test_router_fails_loud_on_unknown_kind():
    with pytest.raises(ValueError):
        DefaultRouter().route("meta.yaml", PROJECT_DEPENDENCIES_SECTION)


def test_router_fails_loud_on_unknown_section():
    with pytest.raises(ValueError):
        DefaultRouter().route(PYPROJECT_KIND, "tool.pixi.dependencies")


# --- CLI rows ----------------------------------------------------------------


def test_version_flag_exits_zero(capsys):
    assert main(["--version"]) == 0
    captured = capsys.readouterr()
    assert captured.out.startswith("python-deptry-osv-scanner ")


def test_missing_verb_is_a_usage_error(capsys):
    rc = main([])
    assert rc == 2
    assert rc != 0  # usage errors never exit 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "usage" in captured.err


def test_unknown_flag_is_a_usage_error(capsys):
    rc = main(["scan", ".", "--bogus"])
    assert rc == 2
    captured = capsys.readouterr()
    assert captured.out == ""


def test_unknown_verb_is_a_usage_error():
    assert main(["frobnicate"]) == 2


def test_nonexistent_target_is_early_fatal(capsys, tmp_path):
    rc = main(["scan", str(tmp_path / "no" / "such" / "dir"), "--format", "json"])
    captured = capsys.readouterr()
    assert rc == 2
    assert captured.out == ""  # stdout EMPTY: no report exists to emit
    assert captured.err != ""


def test_keyboard_interrupt_returns_sigint_with_no_report(
    capsys, monkeypatch, tmp_path
):
    def interrupted(target: Path):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "discover", interrupted)
    rc = main(["scan", str(tmp_path), "--format", "json"])
    captured = capsys.readouterr()
    assert rc == EXIT_SIGINT
    assert captured.out == ""  # no clean report on stdout
    assert "SIGINT" in captured.err


def test_text_format_emits_one_non_contract_summary_line(capsys, tmp_path):
    write_pyproject(tmp_path, ["requests==2.31.0"])
    rc = main(["scan", str(tmp_path)])  # text is the default format
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out.count("\n") == 1
    line = captured.out.strip()
    assert "status=clean" in line
    assert "exit_code=0" in line
    assert "findings=0" in line


def test_text_format_on_empty_dir_reports_not_applicable(capsys, tmp_path):
    rc = main(["scan", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "status=not-applicable" in captured.out


def test_keyboard_interrupt_during_parse_args_returns_sigint(
    capsys, monkeypatch
):
    """The SIGINT window covers ALL of main — an interrupt while argparse is
    still parsing must return EXIT_SIGINT, never a traceback."""

    def interrupted(self, *args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", interrupted)
    rc = main(["scan", "."])
    captured = capsys.readouterr()
    assert rc == EXIT_SIGINT
    assert captured.out == ""
    assert "SIGINT" in captured.err


def test_empty_path_argument_is_early_fatal(capsys):
    """'' would Path-normalize to '.' and silently scan the CWD — it must be
    the early-fatal invalid-target branch instead."""
    rc = main(["scan", "", "--format", "json"])
    captured = capsys.readouterr()
    assert rc == 2
    assert captured.out == ""  # stdout EMPTY: no report exists to emit
    assert captured.err != ""


def test_whitespace_path_argument_is_early_fatal(capsys):
    rc = main(["scan", "   "])
    captured = capsys.readouterr()
    assert rc == 2
    assert captured.out == ""
    assert captured.err != ""


def test_broken_pipe_on_stdout_returns_the_computed_exit_code(
    monkeypatch, tmp_path
):
    """A vanished stdout consumer (e.g. `| head`) must not traceback: the
    report's already-computed exit code is still returned."""
    write_pyproject(tmp_path, ["requests==2.31.0"])

    class BrokenStdout:
        def write(self, data):
            raise BrokenPipeError

        def fileno(self):
            raise OSError("no real file descriptor behind this stream")

    monkeypatch.setattr(sys, "stdout", BrokenStdout())
    rc = main(["scan", str(tmp_path), "--format", "json"])
    assert rc == 0  # the clean verdict's exit code survives the broken pipe


def test_broken_pipe_in_text_mode_is_absorbed_too(monkeypatch, tmp_path):
    class BrokenStdout:
        def write(self, data):
            raise BrokenPipeError

        def fileno(self):
            raise OSError("no real file descriptor behind this stream")

    monkeypatch.setattr(sys, "stdout", BrokenStdout())
    rc = main(["scan", str(tmp_path)])  # empty dir, text format
    assert rc == 0


# --- error-taxonomy rows (unparsable-manifest vs internal-error) --------------


def test_newline_in_dependency_name_still_completes_the_scan(capsys, tmp_path):
    """A dependency name embedding a newline (valid TOML) must not crash
    Finding construction: the scan completes with the escaped form in the
    finding ids and the raw name in the subjects. The raw-malformed entry
    surfaces BOTH deficiencies: withheld from vuln matching AND not
    hygiene-covered (the hygiene axis never goes silent)."""
    write_pyproject(tmp_path, ["foo\nbar"])
    rc, document, _ = scan_json(capsys, tmp_path)
    assert rc == 1
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "indeterminate"
    assert sorted(f["id"] for f in document["findings"]) == [
        "indeterminate:no-version:foo%0Abar",
        "indeterminate:uncovered:foo%0Abar",
    ]
    assert all(f["subject"] == "foo\nbar" for f in document["findings"])
    axes = {f["id"]: f["axis"] for f in document["findings"]}
    assert axes["indeterminate:no-version:foo%0Abar"] == "vulnerability"
    assert axes["indeterminate:uncovered:foo%0Abar"] == "hygiene"


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission semantics")
def test_unreadable_manifest_is_unparsable_manifest_not_a_crash(
    capsys, tmp_path
):
    """An OS failure READING the manifest (chmod-000) is a genuine manifest
    problem: kind unparsable-manifest with the OS error in the message,
    report emitted, exit via the error projection."""
    if os.geteuid() == 0:
        pytest.skip("root ignores file permission bits")
    path = write_pyproject(tmp_path, ["requests==2.31.0"])
    path.chmod(0)
    try:
        rc, document, err = scan_json(capsys, tmp_path)
    finally:
        path.chmod(0o644)
    assert rc == 2
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "error"
    (error,) = document["errors"]
    assert error["kind"] == "unparsable-manifest"
    assert "unreadable manifest" in error["message"]
    assert "Permission denied" in error["message"]  # the OS error is stated
    assert document["status"]["driver"]["finding_id"] == (
        "error:unparsable-manifest:pyproject.toml"
    )
    assert err != ""


def test_unknown_manifest_kind_is_internal_error_not_a_crash(
    capsys, tmp_path, monkeypatch
):
    """extractor_for lives inside the guarded region: an unknown kind out of
    discovery is an internal-error report, never a traceback — and never
    a false 'unparsable-manifest' diagnosis."""
    write_pyproject(tmp_path, ["requests==2.31.0"])
    unknown = ScannedManifest(path="pyproject.toml", kind="meta.yaml")
    monkeypatch.setattr(cli, "discover", lambda target: (unknown,))
    rc, document, err = scan_json(capsys, tmp_path)
    assert rc == 2
    assert document["status"]["value"] == "error"
    (error,) = document["errors"]
    assert error["kind"] == "internal-error"
    assert document["status"]["driver"]["finding_id"] == (
        "error:internal-error:pyproject.toml"
    )
    assert err != ""


def test_internal_value_error_from_an_extractor_is_internal_error(
    capsys, tmp_path, monkeypatch
):
    """Only genuine manifest problems are unparsable-manifest: any other
    ValueError out of the extract path is diagnosed internal-error."""
    write_pyproject(tmp_path, ["requests==2.31.0"])

    class ExplodingExtractor:
        def extract(self, manifest_path, manifest):
            raise ValueError("sentinel internal failure")

    monkeypatch.setattr(
        cli, "extractor_for", lambda kind, router: ExplodingExtractor()
    )
    rc, document, err = scan_json(capsys, tmp_path)
    assert rc == 2
    (error,) = document["errors"]
    assert error["kind"] == "internal-error"
    assert "sentinel internal failure" in error["message"]
    assert document["status"]["driver"]["finding_id"] == (
        "error:internal-error:pyproject.toml"
    )


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission semantics")
def test_permission_denied_discovery_is_an_error_report_not_a_false_green(
    capsys, tmp_path
):
    """A target whose contents cannot be statted must yield an error report
    (with the errno stated), never a green 'no manifest found'."""
    if os.geteuid() == 0:
        pytest.skip("root ignores directory permission bits")
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0)
    try:
        rc, document, err = scan_json(capsys, locked)
    finally:
        locked.chmod(0o755)
    assert rc == 2
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "error"
    (error,) = document["errors"]
    assert error["kind"] == "internal-error"
    assert "errno" in error["message"]
    assert err != ""
    assert "no manifest found" not in err  # not the not-applicable notice


# --- exit-path hardening rows --------------------------------------------------


def test_unexpected_internal_exception_never_exits_one(
    capsys, tmp_path, monkeypatch
):
    """The last-resort net: an unexpected exception (here render_json's
    fail-loud path) returns exit_code_for(error) with stdout EMPTY — never
    the interpreter's default exit 1, which would read as 'findings found'
    to an exit-code-only CI consumer."""
    write_pyproject(tmp_path, ["requests==2.31.0"])

    def exploding_render(report):
        raise RuntimeError("sentinel render failure")

    monkeypatch.setattr(cli, "render_json", exploding_render)
    rc = main(["scan", str(tmp_path), "--format", "json"])
    captured = capsys.readouterr()
    assert rc == 2
    assert rc != 1  # never the interpreter's uncaught-exception code
    assert captured.out == ""  # the invalid report never reached stdout
    assert "internal error" in captured.err
    assert "sentinel render failure" in captured.err


def test_non_int_system_exit_code_projects_as_error(capsys, monkeypatch):
    """argparse only exits with ints under this parser config; if a custom
    action ever exits with a message string, the CLI projects it as the
    error exit instead of crashing in int()."""

    def exits_with_a_string(self, *args, **kwargs):
        raise SystemExit("boom")

    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", exits_with_a_string)
    rc = main(["scan", "."])
    assert rc == 2
    captured = capsys.readouterr()
    assert captured.out == ""


@pytest.mark.skipif(os.name != "posix", reason="symlinks are POSIX-reliable")
def test_dangling_manifest_symlink_is_an_error_report(capsys, tmp_path):
    """A dangling pyproject.toml symlink must never scan green as
    'no manifest found': discovery fails closed and the CLI emits an error
    report (exit 2, report still emitted)."""
    (tmp_path / "pyproject.toml").symlink_to(tmp_path / "no-such-target")
    rc, document, err = scan_json(capsys, tmp_path)
    assert rc == 2
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "error"
    (error,) = document["errors"]
    assert error["kind"] == "internal-error"
    assert "dangling symlink" in error["message"]
    assert "no manifest found" not in err


@pytest.mark.skipif(os.name != "posix", reason="symlinks are POSIX-reliable")
def test_unstattable_target_is_could_not_stat_not_not_there(capsys, tmp_path):
    """The target gate stats explicitly: a self-referential symlink loop
    (ELOOP) is diagnosed 'cannot stat', never the false claim 'is not an
    existing directory'."""
    loop = tmp_path / "loop"
    loop.symlink_to(loop)
    rc = main(["scan", str(loop), "--format", "json"])
    captured = capsys.readouterr()
    assert rc == 2
    assert captured.out == ""  # early-fatal: no report exists to emit
    assert "cannot stat" in captured.err
    assert "not an existing directory" not in captured.err
