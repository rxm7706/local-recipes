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
from pyforge.warden.models import Ecosystem
from pyforge.warden.native_lockfiles import (
    NON_PYTHON_ECOSYSTEMS_FLAG,
    _components_from_osv_document,
    is_native_lockfile_kind,
    is_non_python_native_ecosystem,
)
from pyforge.warden.report import assemble_report
from pyforge.warden.sbom import render_cyclonedx

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
