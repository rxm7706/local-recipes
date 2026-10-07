"""Story 16.4 — non-Python lockfiles via osv-scanner parsers."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest
from pyforge.core import flags as core_flags
from pyforge.core.flags import read_boolean

from pyforge.warden.cli import main as warden_main
from pyforge.warden.discovery import discover
from pyforge.warden.interfaces import AxisCoverage, EngineResult
from pyforge.warden.models import AXIS_VULNERABILITY, Ecosystem, ScannedManifest
from pyforge.warden.native_lockfiles import (
    NON_PYTHON_ECOSYSTEMS_FLAG,
    NativeLockfileScan,
    _components_from_osv_document,
    _lockfile_scan_path,
    inventory_count_for_axis,
    is_native_lockfile_kind,
    is_non_python_native_ecosystem,
    merge_native_scans_into_vuln_result,
    scan_native_lockfile,
)
from pyforge.warden.report import assemble_report
from pyforge.warden.sbom import render_cyclonedx
from pyforge.warden.vuln import OsvParse

TESTS_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = TESTS_ROOT / "fixtures"
NPM_PROJECT = FIXTURES / "projects" / "npm_vuln"
OSV_NPM_RECORDS = FIXTURES / "osv-db" / "npm"


def _load_builder():
    module_path = FIXTURES / "osv_db_builder.py"
    spec = importlib.util.spec_from_file_location("osv_db_builder", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _bool_flag_entry(*, default_variant: str) -> dict[str, object]:
    return {
        "state": "ENABLED",
        "variants": {"on": True, "off": False},
        "defaultVariant": default_variant,
        "metadata": {
            "owner": "warden",
            "story": "16-4-non-python-lockfiles-scan-through-osv-scanner-s-own-parsers",
            "created": "2026-09-28",
            "on_everywhere": "",
            "cleanup_by": "",
        },
    }


def _flag_tree(tmp_path: Path, *, enabled: bool) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    variant = "on" if enabled else "off"
    path = tmp_path / "flags.json"
    path.write_text(
        json.dumps({"flags": {NON_PYTHON_ECOSYSTEMS_FLAG: _bool_flag_entry(default_variant="off")}}),
        encoding="utf-8",
    )
    overlays = {
        "dev": {NON_PYTHON_ECOSYSTEMS_FLAG: variant},
        "staging": {NON_PYTHON_ECOSYSTEMS_FLAG: variant},
        "production": {NON_PYTHON_ECOSYSTEMS_FLAG: "off"},
    }
    (tmp_path / core_flags.OVERLAYS_FILE_NAME).write_text(json.dumps(overlays), encoding="utf-8")
    return path


def test_flag_off_leaves_discovery_unchanged(tmp_path: Path) -> None:
    project = tmp_path / "repo"
    project.mkdir()
    (project / "package-lock.json").write_text("{}", encoding="utf-8")
    assert discover(project, include_non_python_lockfiles=False) == ()


def test_flag_on_discovers_package_lock(tmp_path: Path) -> None:
    project = tmp_path / "repo"
    project.mkdir()
    (project / "package-lock.json").write_text("{}", encoding="utf-8")
    manifests = discover(project, include_non_python_lockfiles=True)
    assert len(manifests) == 1
    assert manifests[0].kind == "package-lock.json"


def test_native_ecosystem_predicate() -> None:
    assert is_non_python_native_ecosystem(Ecosystem.NPM)
    assert not is_non_python_native_ecosystem(Ecosystem.PYPI)
    assert is_native_lockfile_kind("package-lock.json")


def test_lockfile_scan_path_uses_go_mod_for_go_sum(tmp_path: Path) -> None:
    project = tmp_path / "repo"
    subdir = project / "subdir"
    subdir.mkdir(parents=True)
    (subdir / "go.mod").write_text("module example.com/foo\n", encoding="utf-8")
    (subdir / "go.sum").write_text("", encoding="utf-8")
    manifest = ScannedManifest(path="subdir/go.sum", kind="go.sum")
    assert _lockfile_scan_path(project, manifest) == subdir / "go.mod"


def test_components_from_osv_document_skips_malformed_entries() -> None:
    assert _components_from_osv_document(None, manifest_path="x", default_ecosystem=Ecosystem.NPM) == ()
    assert _components_from_osv_document({"results": "nope"}, manifest_path="x", default_ecosystem=Ecosystem.NPM) == ()
    document = {
        "results": [
            "skip",
            {"packages": "nope"},
            {
                "packages": [
                    "skip",
                    {"package": "nope"},
                    {"package": {"name": "", "version": "1"}},
                    {"package": {"name": "dup", "version": "1.0.0", "ecosystem": "npm"}},
                    {"package": {"name": "dup", "version": "1.0.0", "ecosystem": "npm"}},
                    {"package": {"name": "noversion", "ecosystem": "npm"}},
                ]
            },
        ]
    }
    components = _components_from_osv_document(
        document,
        manifest_path="package-lock.json",
        default_ecosystem=Ecosystem.NPM,
    )
    assert len(components) == 2
    noversion = next(c for c in components if c.name == "noversion")
    assert noversion.vuln_matchable is False


def test_inventory_count_for_axis_excludes_native_on_hygiene(component_factory) -> None:
    npm = component_factory(name="a", version="1", ecosystem=Ecosystem.NPM)
    pypi = component_factory(name="b", version="1", ecosystem=Ecosystem.PYPI)
    inventory = (npm, pypi)
    assert inventory_count_for_axis(inventory, AXIS_VULNERABILITY) == 2
    assert inventory_count_for_axis(inventory, "hygiene") == 1


def test_merge_native_scans_empty_returns_unchanged() -> None:
    base = EngineResult(findings=(), errors=(), coverage=(), axis=AXIS_VULNERABILITY)
    assert merge_native_scans_into_vuln_result(base, (), inventory_count=0) is base


def test_merge_native_scans_merges_findings_and_stale_db(component_factory, tmp_path: Path) -> None:
    import time

    from pyforge.warden.interfaces import VulnData

    component = component_factory(name="leftpad", version="1.0.0", ecosystem=Ecosystem.NPM)
    stale_mtime = time.time() - (10 * 86400)
    zip_path = tmp_path / "npm.zip"
    zip_path.write_bytes(b"pk")
    os.utime(zip_path, (stale_mtime, stale_mtime))
    scan = NativeLockfileScan(
        components=(component,),
        parse=OsvParse(findings=(), errors=()),
        ecosystem=Ecosystem.NPM,
        db_consulted=True,
        db_zip=zip_path,
        snapshot_at="2020-01-01T00:00:00Z",
    )
    base = EngineResult(
        findings=(),
        errors=(),
        coverage=(
            AxisCoverage(
                axis=AXIS_VULNERABILITY,
                manifests_found=1,
                manifests_parsed=1,
                deps_total=2,
                deps_assessed=1,
                resolution_depth="locked-closure",
            ),
        ),
        axis=AXIS_VULNERABILITY,
        vuln_data=VulnData(source="/pypi.zip", snapshot_at="2026-01-01T00:00:00Z", max_age_ok=True),
    )
    merged = merge_native_scans_into_vuln_result(base, (scan,), inventory_count=2)
    assert merged.vuln_data is not None
    assert merged.vuln_data.max_age_ok is False
    assert merged.coverage[0].deps_assessed == 2


def test_scan_native_lockfile_version_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    builder = _load_builder()
    cache = tmp_path / "cache"
    builder.build_offline_db(OSV_NPM_RECORDS, cache, ecosystem="npm")
    monkeypatch.setenv("OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY", str(cache))
    project = tmp_path / "proj"
    project.mkdir()
    (project / "package-lock.json").write_text("{}", encoding="utf-8")
    manifest = ScannedManifest(path="package-lock.json", kind="package-lock.json")

    from pyforge.warden.models import ErrorKind, ErrorRecord

    version_error = ErrorRecord(kind=ErrorKind.ENGINE_UNAVAILABLE, owner="osv-scanner", message="bad version")
    monkeypatch.setattr(
        "pyforge.warden.engines._check_engine_version",
        lambda **kwargs: version_error,
    )

    scan = scan_native_lockfile(project, manifest)
    assert scan.parse.errors == (version_error,)
    assert scan.components == ()


def test_components_from_osv_document_npm() -> None:
    document = {
        "results": [
            {
                "packages": [
                    {
                        "package": {"name": "leftpad", "version": "1.0.0", "ecosystem": "npm"},
                        "groups": [],
                    }
                ]
            }
        ]
    }
    components = _components_from_osv_document(
        document,
        manifest_path="package-lock.json",
        default_ecosystem=Ecosystem.NPM,
    )
    assert len(components) == 1
    assert components[0].ecosystem is Ecosystem.NPM
    assert components[0].purl == "pkg:npm/leftpad@1.0.0"
    assert components[0].vuln_matchable is True
    assert components[0].hygiene_covered is False


def test_read_boolean_flag_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    on_tree = _flag_tree(tmp_path / "on", enabled=True)
    off_tree = _flag_tree(tmp_path / "off", enabled=False)
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    assert read_boolean(NON_PYTHON_ECOSYSTEMS_FLAG, flags_path=on_tree) is True
    assert read_boolean(NON_PYTHON_ECOSYSTEMS_FLAG, flags_path=off_tree) is False


def test_flag_off_scan_ignores_package_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "npm_only"
    project.mkdir()
    (project / "package-lock.json").write_text(
        (NPM_PROJECT / "package-lock.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    off_tree = _flag_tree(tmp_path / "flags", enabled=False)
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "production")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(off_tree))
    import sys
    from io import StringIO

    buffer = StringIO()
    monkeypatch.setattr(sys, "stdout", buffer)
    exit_code = warden_main(["scan", str(project), "--format", "json"])
    report = json.loads(buffer.getvalue())
    assert exit_code == 0
    assert report["inventory_count"] == 0
    assert discover(project, include_non_python_lockfiles=False) == ()


def test_npm_lock_vuln_with_offline_db(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    builder = _load_builder()
    cache = tmp_path / "osv-cache"
    builder.build_offline_db(OSV_NPM_RECORDS, cache, ecosystem="npm")
    on_tree = _flag_tree(tmp_path / "flags", enabled=True)
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(on_tree))
    monkeypatch.setenv("OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY", str(cache))
    exit_code = warden_main(["scan", str(NPM_PROJECT), "--format", "json"])
    assert exit_code in (0, 1)
    import sys
    from io import StringIO

    buffer = StringIO()
    monkeypatch.setattr(sys, "stdout", buffer)
    warden_main(["scan", str(NPM_PROJECT), "--format", "json"])
    report = json.loads(buffer.getvalue())
    vuln_findings = [f for f in report["findings"] if f["id"].startswith("vuln:")]
    assert vuln_findings, "expected a vuln finding for the pinned npm advisory"
    vuln_cov = next(c for c in report["coverage"] if c["axis"] == "vulnerability")
    assert vuln_cov["deps_assessed"] >= 1
    hygiene_cov = next(c for c in report["coverage"] if c["axis"] == "hygiene")
    assert hygiene_cov["deps_total"] == 0
    license_cov = next(c for c in report["coverage"] if c["axis"] == "license")
    assert license_cov["deps_total"] == 0


def test_npm_lock_without_npm_db_is_indeterminate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    builder = _load_builder()
    cache = tmp_path / "pypi-only"
    builder.build_offline_db(FIXTURES / "osv-db" / "pypi", cache, ecosystem="PyPI")
    on_tree = _flag_tree(tmp_path / "flags", enabled=True)
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(on_tree))
    monkeypatch.setenv("OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY", str(cache))
    import sys
    from io import StringIO

    buffer = StringIO()
    monkeypatch.setattr(sys, "stdout", buffer)
    exit_code = warden_main(["scan", str(NPM_PROJECT), "--format", "json"])
    assert exit_code == 1
    report = json.loads(buffer.getvalue())
    assert report["status"] != "clean"
    eco_findings = [
        f
        for f in report["findings"]
        if "offline-db-unavailable" in f["id"] and ("npm" in f["id"].lower() or "npm" in f["message"].lower())
    ]
    assert eco_findings


def test_stale_npm_offline_db_merges_stale_vuln_finding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import time

    builder = _load_builder()
    cache = tmp_path / "cache"
    builder.build_offline_db(OSV_NPM_RECORDS, cache, ecosystem="npm")
    zip_path = cache / "osv-scanner" / "npm" / "all.zip"
    stale_mtime = time.time() - (10 * 86400)

    os.utime(zip_path, (stale_mtime, stale_mtime))
    on_tree = _flag_tree(tmp_path / "flags", enabled=True)
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(on_tree))
    monkeypatch.setenv("OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY", str(cache))
    import sys
    from io import StringIO

    buffer = StringIO()
    monkeypatch.setattr(sys, "stdout", buffer)
    exit_code = warden_main(["scan", str(NPM_PROJECT), "--format", "json"])
    assert exit_code != 0
    report = json.loads(buffer.getvalue())
    assert report["status"] != "clean"
    assert any(f["id"].startswith("indeterminate:vuln-data-stale:") for f in report["findings"])


def test_sbom_emits_pkg_npm_purl(component_factory) -> None:
    from pyforge.warden.inventory import ResolvedInventory, merge_components
    from pyforge.warden.models import VulnData

    component = component_factory(
        name="leftpad",
        version="1.0.0",
        ecosystem=Ecosystem.NPM,
        pypi_identity=None,
        hygiene_covered=False,
        license_covered=False,
        currency_covered=False,
        provenance=(("package-lock.json", "lockfile"),),
    )
    inventory = ResolvedInventory(components=merge_components([component]), resolved_scan_set=())
    report = assemble_report(
        inventory=inventory,
        findings=(),
        errors=(),
        rungs=(),
        engine_results=(),
        manifests_found=1,
        manifests_parsed=1,
        vuln_data=VulnData(None, None, None),
    )
    bom = json.loads(render_cyclonedx(inventory, report))
    purl = bom["components"][0]["purl"]
    assert purl == "pkg:npm/leftpad@1.0.0"
