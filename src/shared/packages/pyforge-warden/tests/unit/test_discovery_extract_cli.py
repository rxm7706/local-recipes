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
import errno
import io
import json
import os
import sys
from importlib import resources
from pathlib import Path

import jsonschema
import pytest

from pyforge.warden import cli
from pyforge.warden.cli import main
from pyforge.warden.discovery import (
    CONDA_LOCK_KIND,
    ENVIRONMENT_YML_KIND,
    META_YAML_KIND,
    PIXI_LOCK_KIND,
    PIXI_TOML_KIND,
    PYPROJECT_KIND,
    RECIPE_YAML_KIND,
    discover,
)
from pyforge.warden.extract import (
    UnparsableManifestError,
    extractor_for,
)
from pyforge.warden.extract.lockfiles import (
    CONDA_LOCK_CONDA_SECTION,
    CONDA_LOCK_PYPI_SECTION,
    PIXI_LOCK_CONDA_SECTION,
    PIXI_LOCK_PYPI_SECTION,
    CondaLockExtractor,
    PixiLockExtractor,
)
from pyforge.warden.extract.pyproject import (
    PROJECT_DEPENDENCIES_SECTION,
    PyprojectExtractor,
)
from pyforge.warden.inventory import merge_components
from pyforge.warden.models import (
    CveMatchLevel,
    Ecosystem,
    ExtractionMode,
    IdentitySource,
    ScannedManifest,
    WithholdReason,
)
from pyforge.warden.routing import DefaultRouter
from pyforge.warden.verdict import EXIT_SIGINT

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


def write_pixi_lock(directory: Path, name: str, version: str) -> Path:
    body = (
        "version: 6\n"
        "packages:\n"
        f"- pypi: https://files.pythonhosted.org/packages/aa/bb/"
        f"{name}-{version}-py3-none-any.whl\n"
        f"  name: {name}\n"
        f"  version: {version}\n"
    )
    path = directory / PIXI_LOCK_KIND
    path.write_text(body, encoding="utf-8")
    return path


def extract_from(directory: Path, deps: list[str]):
    path = write_pyproject(directory, deps)
    return PyprojectExtractor(DefaultRouter()).extract(path, MANIFEST)


def load_schema() -> dict:
    schema_file = (
        resources.files("pyforge.warden") / "data" / "report-schema.json"
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


def test_discover_fails_closed_on_a_file_target(tmp_path):
    """<file>/pyproject.toml stats NotADirectoryError. The CLI's gate
    proved a directory at scan start, so ENOTDIR at discovery time means
    the target was REPLACED by a file mid-scan (TOCTOU) — or a direct API
    caller passed a file. Either way: FAIL CLOSED, never 'no manifest' →
    exit 0 (this was previously read as genuine absence, the exact TOCTOU
    false green the module docstring forbids)."""
    file_target = tmp_path / "somefile"
    file_target.write_text("", encoding="utf-8")
    with pytest.raises(OSError, match="not a directory"):
        discover(file_target)


def test_discover_fails_closed_on_a_vanished_target(tmp_path):
    """A nonexistent target directory is undeterminable manifest state
    (vanished after the CLI gate, or never existed for a direct API
    caller — the message claims neither as fact) — it must fail closed,
    never read as "no manifest" → exit 0."""
    with pytest.raises(OSError, match="vanished mid-scan or never existed"):
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


# --- discovery: the 2 new lockfile kinds (Story 2.6, additive) ---------------


def test_discover_finds_a_pixi_lock_manifest(tmp_path):
    (tmp_path / PIXI_LOCK_KIND).write_text("version: 6\npackages: []\n", encoding="utf-8")
    assert discover(tmp_path) == (
        ScannedManifest(path=PIXI_LOCK_KIND, kind=PIXI_LOCK_KIND),
    )


def test_discover_finds_a_conda_lock_manifest(tmp_path):
    (tmp_path / CONDA_LOCK_KIND).write_text("version: 1\npackage: []\n", encoding="utf-8")
    assert discover(tmp_path) == (
        ScannedManifest(path=CONDA_LOCK_KIND, kind=CONDA_LOCK_KIND),
    )


def test_discover_finds_all_three_kinds_together_in_fixed_order(tmp_path):
    write_pyproject(tmp_path, [])
    (tmp_path / PIXI_LOCK_KIND).write_text("version: 6\npackages: []\n", encoding="utf-8")
    (tmp_path / CONDA_LOCK_KIND).write_text("version: 1\npackage: []\n", encoding="utf-8")
    assert discover(tmp_path) == (
        ScannedManifest(path=PYPROJECT_KIND, kind=PYPROJECT_KIND),
        ScannedManifest(path=PIXI_LOCK_KIND, kind=PIXI_LOCK_KIND),
        ScannedManifest(path=CONDA_LOCK_KIND, kind=CONDA_LOCK_KIND),
    )


def test_discover_fails_closed_on_a_pixi_lock_directory(tmp_path):
    (tmp_path / PIXI_LOCK_KIND).mkdir()
    with pytest.raises(OSError, match="not a regular file"):
        discover(tmp_path)


def test_discover_fails_closed_on_a_conda_lock_directory(tmp_path):
    (tmp_path / CONDA_LOCK_KIND).mkdir()
    with pytest.raises(OSError, match="not a regular file"):
        discover(tmp_path)


@pytest.mark.skipif(os.name != "posix", reason="symlinks are POSIX-reliable")
def test_discover_fails_closed_on_a_dangling_pixi_lock_symlink(tmp_path):
    (tmp_path / PIXI_LOCK_KIND).symlink_to(tmp_path / "no-such-target")
    with pytest.raises(OSError, match="dangling symlink"):
        discover(tmp_path)


@pytest.mark.skipif(os.name != "posix", reason="symlinks are POSIX-reliable")
def test_discover_fails_closed_on_a_dangling_conda_lock_symlink(tmp_path):
    (tmp_path / CONDA_LOCK_KIND).symlink_to(tmp_path / "no-such-target")
    with pytest.raises(OSError, match="dangling symlink"):
        discover(tmp_path)


# --- discovery: the 4 new conda/pixi source-manifest kinds (Story 2.2) -------


@pytest.mark.parametrize(
    "kind,body",
    [
        (RECIPE_YAML_KIND, "requirements:\n  run: []\n"),
        (META_YAML_KIND, "requirements:\n  run: []\n"),
        (ENVIRONMENT_YML_KIND, "dependencies: []\n"),
        (PIXI_TOML_KIND, "[dependencies]\n"),
    ],
)
def test_discover_finds_each_new_source_manifest_kind(tmp_path, kind, body):
    (tmp_path / kind).write_text(body, encoding="utf-8")
    assert discover(tmp_path) == (ScannedManifest(path=kind, kind=kind),)


def test_discover_returns_empty_when_no_source_manifest_present(tmp_path):
    assert discover(tmp_path) == ()


def test_discover_finds_all_seven_kinds_together_in_fixed_order(tmp_path):
    write_pyproject(tmp_path, [])
    (tmp_path / PIXI_LOCK_KIND).write_text("version: 6\npackages: []\n", encoding="utf-8")
    (tmp_path / CONDA_LOCK_KIND).write_text("version: 1\npackage: []\n", encoding="utf-8")
    (tmp_path / RECIPE_YAML_KIND).write_text("requirements:\n  run: []\n", encoding="utf-8")
    (tmp_path / META_YAML_KIND).write_text("requirements:\n  run: []\n", encoding="utf-8")
    (tmp_path / ENVIRONMENT_YML_KIND).write_text("dependencies: []\n", encoding="utf-8")
    (tmp_path / PIXI_TOML_KIND).write_text("[dependencies]\n", encoding="utf-8")
    assert discover(tmp_path) == (
        ScannedManifest(path=PYPROJECT_KIND, kind=PYPROJECT_KIND),
        ScannedManifest(path=PIXI_LOCK_KIND, kind=PIXI_LOCK_KIND),
        ScannedManifest(path=CONDA_LOCK_KIND, kind=CONDA_LOCK_KIND),
        ScannedManifest(path=RECIPE_YAML_KIND, kind=RECIPE_YAML_KIND),
        ScannedManifest(path=META_YAML_KIND, kind=META_YAML_KIND),
        ScannedManifest(path=ENVIRONMENT_YML_KIND, kind=ENVIRONMENT_YML_KIND),
        ScannedManifest(path=PIXI_TOML_KIND, kind=PIXI_TOML_KIND),
    )


@pytest.mark.parametrize(
    "kind",
    [RECIPE_YAML_KIND, META_YAML_KIND, ENVIRONMENT_YML_KIND, PIXI_TOML_KIND],
)
def test_discover_fails_closed_on_a_source_manifest_directory(tmp_path, kind):
    """A source manifest that exists but is not a regular file is
    found-but-refused: it must FAIL CLOSED, never read as absent (mirrors
    the pyproject.toml/lockfile rows)."""
    (tmp_path / kind).mkdir()
    with pytest.raises(OSError, match="not a regular file"):
        discover(tmp_path)


@pytest.mark.skipif(os.name != "posix", reason="symlinks are POSIX-reliable")
@pytest.mark.parametrize(
    "kind",
    [RECIPE_YAML_KIND, META_YAML_KIND, ENVIRONMENT_YML_KIND, PIXI_TOML_KIND],
)
def test_discover_fails_closed_on_a_dangling_source_manifest_symlink(tmp_path, kind):
    (tmp_path / kind).symlink_to(tmp_path / "no-such-target")
    with pytest.raises(OSError, match="dangling symlink"):
        discover(tmp_path)


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
    # "meta.yaml" gained an extractor in Story 2.2 -- a genuinely-fictional
    # kind token is the sentinel now.
    with pytest.raises(ValueError):
        extractor_for("some-unknown-manifest.kind", DefaultRouter())


def test_pixi_lock_kind_dispatches_to_pixi_lock_extractor():
    extractor = extractor_for(PIXI_LOCK_KIND, DefaultRouter())
    assert isinstance(extractor, PixiLockExtractor)


def test_conda_lock_kind_dispatches_to_conda_lock_extractor():
    extractor = extractor_for(CONDA_LOCK_KIND, DefaultRouter())
    assert isinstance(extractor, CondaLockExtractor)


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


def test_router_routes_pixi_lock_conda_section_to_conda():
    ecosystem = DefaultRouter().route(PIXI_LOCK_KIND, PIXI_LOCK_CONDA_SECTION)
    assert ecosystem is Ecosystem.CONDA


def test_router_routes_pixi_lock_pypi_section_to_pypi():
    ecosystem = DefaultRouter().route(PIXI_LOCK_KIND, PIXI_LOCK_PYPI_SECTION)
    assert ecosystem is Ecosystem.PYPI


def test_router_routes_conda_lock_conda_section_to_conda():
    ecosystem = DefaultRouter().route(CONDA_LOCK_KIND, CONDA_LOCK_CONDA_SECTION)
    assert ecosystem is Ecosystem.CONDA


def test_router_routes_conda_lock_pypi_section_to_pypi():
    ecosystem = DefaultRouter().route(CONDA_LOCK_KIND, CONDA_LOCK_PYPI_SECTION)
    assert ecosystem is Ecosystem.PYPI


def test_router_does_not_cross_wire_pixi_lock_and_conda_lock_sections():
    with pytest.raises(ValueError):
        DefaultRouter().route(PIXI_LOCK_KIND, CONDA_LOCK_CONDA_SECTION)
    with pytest.raises(ValueError):
        DefaultRouter().route(CONDA_LOCK_KIND, PIXI_LOCK_CONDA_SECTION)


# --- cross-ecosystem non-merge (Story 2.5, FR7) -------------------------------


def test_cross_ecosystem_same_name_stays_two_distinct_components(tmp_path):
    """FR7 regression: ``inventory.identity()``'s ``(ecosystem,
    canonical_name, version)`` key already keeps a same-named conda + PyPI
    component distinct -- no production change, this pins the guarantee. A
    ``pyproject.toml`` PyPI dep and a ``pixi.lock`` conda row both literally
    named ``requests`` must never merge into one ``Component``."""
    pyproject_path = write_pyproject(tmp_path, ["requests==2.31.0"])
    (pypi_component,) = PyprojectExtractor(DefaultRouter()).extract(
        pyproject_path, MANIFEST
    )

    lock_path = tmp_path / PIXI_LOCK_KIND
    lock_path.write_text(
        "version: 6\n"
        "packages:\n"
        "- conda: https://conda.anaconda.org/conda-forge/noarch/"
        "requests-2.31.0-pyhd8ed1ab_0.conda\n",
        encoding="utf-8",
    )
    lock_manifest = ScannedManifest(path=PIXI_LOCK_KIND, kind=PIXI_LOCK_KIND)
    (conda_component,) = PixiLockExtractor(DefaultRouter()).extract(
        lock_path, lock_manifest
    )

    merged = merge_components((pypi_component, conda_component))

    assert len(merged) == 2
    by_ecosystem = {c.ecosystem: c for c in merged}
    assert set(by_ecosystem) == {Ecosystem.PYPI, Ecosystem.CONDA}
    assert by_ecosystem[Ecosystem.PYPI].name == "requests"
    assert by_ecosystem[Ecosystem.PYPI].version == "2.31.0"
    assert by_ecosystem[Ecosystem.CONDA].name == "requests"
    assert by_ecosystem[Ecosystem.CONDA].version == "2.31.0"


# --- CLI rows ----------------------------------------------------------------


def test_version_flag_exits_zero(capsys):
    assert main(["--version"]) == 0
    captured = capsys.readouterr()
    assert captured.out.startswith("warden ")


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
    # A declared-but-never-imported dependency (this fixture ships no source)
    # is flagged DEP002 by deptry (Story 1.3) -> status warn, one finding,
    # exit 0. The text format still emits exactly ONE summary line.
    write_pyproject(tmp_path, ["requests==2.31.0"])
    rc = main(["scan", str(tmp_path)])  # text is the default format
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out.count("\n") == 1
    line = captured.out.strip()
    assert "status=warn" in line
    assert "exit_code=0" in line
    assert "findings=1" in line


def test_text_format_on_empty_dir_reports_not_applicable(capsys, tmp_path):
    rc = main(["scan", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "status=not-applicable" in captured.out


# --- resolution_depth: locked-closure (Story 2.6) -----------------------------


def test_pixi_lock_presence_marks_resolution_depth_locked_closure(capsys, tmp_path):
    """A parsed pixi.lock claims the full transitive closure on BOTH axes —
    the I/O matrix's 'any lockfile parses successfully' row."""
    write_pyproject(tmp_path, [])
    write_pixi_lock(tmp_path, "requests", "2.31.0")
    rc, document, _ = scan_json(capsys, tmp_path)
    by_axis = {block["axis"]: block for block in document["coverage"]}
    assert by_axis["hygiene"]["resolution_depth"] == "locked-closure"
    assert by_axis["vulnerability"]["resolution_depth"] == "locked-closure"
    assert rc == document["exit_code"]


def test_pyproject_only_resolution_depth_stays_direct_only(capsys, tmp_path):
    """No lockfile present: 1.2's direct-only behavior is unchanged."""
    write_pyproject(tmp_path, ["requests==2.31.0"])
    rc, document, _ = scan_json(capsys, tmp_path)
    by_axis = {block["axis"]: block for block in document["coverage"]}
    assert by_axis["hygiene"]["resolution_depth"] == "direct-only"
    assert by_axis["vulnerability"]["resolution_depth"] == "direct-only"
    assert rc == document["exit_code"]


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
    hygiene-covered (the hygiene axis never goes silent). deptry handles the
    odd name gracefully (no finding, no error), so the extractor's
    indeterminate verdict stands."""
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
    # The errno is stated SYMBOLICALLY: locale-independent (glibc renders
    # strerror in the session locale) and free of the absolute path that
    # OSError.__str__ embeds (report bytes must not vary by locale or
    # scan location).
    assert "EACCES" in error["message"]
    assert "PermissionError" in error["message"]
    assert str(tmp_path) not in error["message"]  # no absolute path leak
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
    # "meta.yaml" gained an extractor in Story 2.2 -- a genuinely-fictional
    # kind token is the sentinel now.
    unknown = ScannedManifest(path="pyproject.toml", kind="some-unknown-manifest.kind")
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


def test_system_exit_from_the_scan_region_projects_as_error(
    capsys, tmp_path, monkeypatch
):
    """sys.exit raised INSIDE the scan region (a sole-ownership violation
    by a component) must never exit the process with its carried code —
    sys.exit(0) mid-scan would read as a green gate with no report. It is
    projected to exit_code_for(error), stdout stays empty."""

    def exiting_discover(target):
        raise SystemExit(0)

    monkeypatch.setattr(cli, "discover", exiting_discover)
    rc = main(["scan", str(tmp_path), "--format", "json"])
    captured = capsys.readouterr()
    assert rc == 2
    assert rc != 0  # the carried code is never trusted
    assert captured.out == ""
    assert "SystemExit" in captured.err
    assert "sole-ownership" in captured.err


def test_closed_stderr_does_not_escape_the_exception_nets(
    monkeypatch, tmp_path
):
    """_stderr runs INSIDE the exception handlers; print on a CLOSED
    stderr raises ValueError (not OSError). Unabsorbed, the handler itself
    would escape main() as an uncaught traceback with interpreter exit 1 —
    the exact exit-1 collision the module docstring forbids."""

    def exploding_discover(target):
        raise RuntimeError("sentinel internal failure")

    monkeypatch.setattr(cli, "discover", exploding_discover)
    closed = io.StringIO()
    closed.close()
    monkeypatch.setattr(sys, "stderr", closed)
    rc = main(["scan", str(tmp_path), "--format", "json"])
    assert rc == 2  # returned, not raised — and never the interpreter's 1


def test_non_epipe_stdout_failure_keeps_the_computed_exit_code(
    monkeypatch, tmp_path, capsys
):
    """A non-EPIPE stdout failure (ENOSPC full disk, EIO) is environmental:
    the computed verdict must survive — never replaced by the error exit,
    never misdiagnosed as an internal error."""
    write_pyproject(tmp_path, ["requests>=2.0"])  # range-only → exit 1

    class FullDiskStdout:
        def write(self, data):
            raise OSError(errno.ENOSPC, "No space left on device")

        def flush(self):
            pass

    monkeypatch.setattr(sys, "stdout", FullDiskStdout())
    rc = main(["scan", str(tmp_path), "--format", "json"])
    captured = capsys.readouterr()
    assert rc == 1  # the indeterminate verdict's code, not error's 2
    assert "stdout emission failed" in captured.err
    assert "internal error" not in captured.err


def test_closed_stdout_keeps_the_computed_exit_code(monkeypatch, tmp_path, capsys):
    """A closed/replaced sys.stdout raises ValueError ('I/O operation on
    closed file'), NOT OSError — the emit guard must absorb it too, or it
    escapes to the last-resort net and overrides the verdict with error-2
    (an exit-code sole-ownership violation). Regression for the follow-up
    Opus review; the ENOSPC (OSError) sibling is above."""
    write_pyproject(tmp_path, ["requests==2.31.0"])  # clean → exit 0

    class ClosedStdout:
        def write(self, data):
            raise ValueError("I/O operation on closed file")

        def flush(self):
            pass

    monkeypatch.setattr(sys, "stdout", ClosedStdout())
    rc = main(["scan", str(tmp_path), "--format", "json"])
    captured = capsys.readouterr()
    assert rc == 0  # the clean verdict's code — NOT error's 2
    assert "stdout emission failed" in captured.err
    assert "internal error" not in captured.err
    assert "Traceback" not in captured.err


def test_nul_byte_scan_target_is_early_fatal_not_internal_error(capsys):
    """A path with an embedded NUL raises ValueError (not OSError) from
    stat() — a user-input error, diagnosed at the boundary, never routed to
    the internal-error traceback net. Regression for the follow-up Opus
    review."""
    capsys.readouterr()
    rc = main(["scan", "bad\x00path", "--format", "json"])
    captured = capsys.readouterr()
    assert rc == 2  # exit_code_for(Status.ERROR); no {1,2,130} literal in src
    assert captured.out == ""  # stdout stays empty in json mode
    assert "not a valid path" in captured.err
    assert "internal error" not in captured.err
    assert "Traceback" not in captured.err


def test_poetry_only_deps_are_covered_by_deptry_natively(capsys, tmp_path):
    """CHARACTERIZATION: our OWN extractor reads only [project].dependencies,
    so a Poetry/PDM manifest yields zero components (inventory_count 0) — the
    section-aware D2 split is still Story 1.9's. BUT deptry reads
    [tool.poetry.dependencies] NATIVELY (FR9), so the unused `requests`
    surfaces as a DEP002 warn: exit 0 but NOT the silent not-applicable
    false-green the pre-1.3 pipeline produced. When 1.9 lands section-aware
    discovery the inventory (and vuln axis) will cover it too."""
    (tmp_path / "pyproject.toml").write_text(
        "[tool.poetry]\n"
        'name = "demo"\n'
        "\n"
        "[tool.poetry.dependencies]\n"
        'python = "^3.12"\n'
        'requests = "^2.31"\n',
        encoding="utf-8",
    )
    rc, document, err = scan_json(capsys, tmp_path)
    assert rc == 0
    assert document["status"]["value"] == "warn"
    assert document["inventory_count"] == 0  # our extractor found nothing
    assert "hygiene:DEP002:requests" in {f["id"] for f in document["findings"]}


def test_stderr_helper_drops_diagnostic_when_stderr_is_none(monkeypatch):
    """NFR-I3 (Gemini review): when sys.stderr is None (pythonw / GUI /
    embedded host), print(..., file=None) falls back to sys.stdout WITHOUT
    raising — so a diagnostic would silently corrupt the JSON contract
    stream. _stderr must guard on None and drop the diagnostic instead."""
    fake_stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdout", fake_stdout)
    monkeypatch.setattr(sys, "stderr", None)
    cli._stderr("diagnostic that must not reach stdout")
    assert fake_stdout.getvalue() == ""  # nothing leaked onto the contract


def test_unexpected_extractor_exception_still_emits_the_report(
    capsys, tmp_path, monkeypatch
):
    """The extractor seam gets the same doctrine as the engine seam: ANY
    unexpected exception out of an extractor (a 1.3+ implementation bug —
    here a TypeError, which the old ValueError-only net let escape to the
    no-report catch-all) yields a typed internal-error record with the
    report STILL emitted."""
    write_pyproject(tmp_path, ["requests==2.31.0"])

    class ExplodingExtractor:
        def extract(self, manifest_path, manifest):
            raise TypeError("sentinel type failure")

    monkeypatch.setattr(
        cli, "extractor_for", lambda kind, router: ExplodingExtractor()
    )
    rc, document, err = scan_json(capsys, tmp_path)
    assert rc == 2
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "error"
    (error,) = document["errors"]
    assert error["kind"] == "internal-error"
    assert "sentinel type failure" in error["message"]
    assert document["status"]["driver"]["finding_id"] == (
        "error:internal-error:pyproject.toml"
    )


def test_extractor_recursion_error_is_unparsable_manifest(tmp_path):
    """Hostile nesting overflows tomllib recursively (RecursionError, a
    RuntimeError — neither TOMLDecodeError nor ValueError): still a
    structurally-broken manifest, so the extractor folds it into
    UnparsableManifestError (the CLI-level row lives in conformance)."""
    (tmp_path / "pyproject.toml").write_text(
        "x = " + "[" * 8000 + "]" * 8000 + "\n", encoding="utf-8"
    )
    with pytest.raises(UnparsableManifestError):
        PyprojectExtractor(DefaultRouter()).extract(
            tmp_path / "pyproject.toml", MANIFEST
        )
