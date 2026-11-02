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
    # Story 16.9: the license and currency engines judge the npm component too.
    assert inventory_count_for_axis(inventory, "license") == 2
    assert inventory_count_for_axis(inventory, "currency") == 2
    assert inventory_count_for_axis((npm,), "license") == 1
    assert inventory_count_for_axis((npm,), "hygiene") == 0


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
    # Story 16.9: the license row counts the npm component its engine judged.
    license_cov = next(c for c in report["coverage"] if c["axis"] == "license")
    assert license_cov["deps_total"] == report["inventory_count"] == 1


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


def test_native_vuln_ecosystems_names_only_vuln_findings() -> None:
    """Story 16.8: each native ``vuln:`` finding -> its ecosystem; sentinels are left out."""
    from pyforge.warden.models import Finding
    from pyforge.warden.native_lockfiles import native_vuln_ecosystems

    vuln = Finding(
        id="vuln:GHSA-xxxx:leftpad@1.0.0",
        axis=AXIS_VULNERABILITY,
        message="leftpad: GHSA-xxxx",
        subject="leftpad",
        severity=None,
    )
    sentinel = Finding(
        id="indeterminate:offline-db-unavailable-ecosystem:Go",
        axis=AXIS_VULNERABILITY,
        message="no Go DB",
        subject="Go",
        severity=None,
    )

    def _scan(ecosystem: Ecosystem, *findings: Finding) -> NativeLockfileScan:
        return NativeLockfileScan(
            components=(),
            parse=OsvParse(findings=findings, errors=()),
            ecosystem=ecosystem,
            db_consulted=True,
            db_zip=None,
            snapshot_at=None,
        )

    scans = (_scan(Ecosystem.NPM, vuln), _scan(Ecosystem.GO, sentinel))
    assert native_vuln_ecosystems(scans) == {vuln.id: "npm"}
    assert native_vuln_ecosystems(()) == {}


def test_label_outcome_ecosystems_labels_only_the_named_outcomes() -> None:
    """Story 16.8: a labelled outcome carries ``ecosystem``; every other is unchanged."""
    from pyforge.warden.actuator import Actuation, PROutcome, label_outcome_ecosystems

    npm = PROutcome(finding_id="vuln:A:leftpad@1.0.0", action="upgrade", subject="leftpad", status="planned")
    pypi = PROutcome(finding_id="vuln:B:requests@2.0.0", action="upgrade", subject="requests", status="planned")
    actuation = Actuation(dry_run=True, outcomes=(npm, pypi))

    assert label_outcome_ecosystems(actuation, {}) is actuation
    labelled = label_outcome_ecosystems(actuation, {npm.finding_id: "npm"})
    by_id = {outcome["finding_id"]: outcome for outcome in labelled.to_json_dict()["outcomes"]}
    assert by_id[npm.finding_id]["ecosystem"] == "npm"
    assert "ecosystem" not in by_id[pypi.finding_id]


def test_fix_prs_dry_run_names_the_native_finding_ecosystem(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Story 16.8: in one scan, the npm ``vuln:`` outcome says ``npm``; the PyPI one says nothing."""
    import shutil
    import sys
    from io import StringIO

    builder = _load_builder()
    cache = tmp_path / "osv-cache"
    builder.build_offline_db(OSV_NPM_RECORDS, cache, ecosystem="npm")
    builder.build_offline_db(FIXTURES / "osv-db" / "pypi", cache, ecosystem="PyPI")
    project = tmp_path / "mixed"
    shutil.copytree(FIXTURES / "projects" / "vuln_high", project)
    shutil.copy2(NPM_PROJECT / "package-lock.json", project / "package-lock.json")
    on_tree = _flag_tree(tmp_path / "flags", enabled=True)
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(on_tree))
    monkeypatch.setenv("OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY", str(cache))
    buffer = StringIO()
    monkeypatch.setattr(sys, "stdout", buffer)

    warden_main(["scan", str(project), "--format", "json", "--fix-prs-dry-run"])

    report = json.loads(buffer.getvalue())
    outcomes = {outcome["finding_id"]: outcome for outcome in report["actuation"]["outcomes"]}
    npm_outcome = outcomes["vuln:PDOS-NPM-FIXTURE-0001:pdos-npm-vuln-fixture@1.0.0"]
    pypi_outcome = outcomes["vuln:PDOS-FIXTURE-0002:pdos-vuln-fixture-high@1.0.0"]
    assert npm_outcome["status"] == pypi_outcome["status"] == "planned"
    assert npm_outcome["ecosystem"] == "npm"
    assert "ecosystem" not in pypi_outcome


# --- Story 16.9: a non-Python repo's license and currency rows report what ran ---

_CLEAN_NPM_PACKAGES = (("pdos-npm-clean-alpha", "3.1.0"), ("pdos-npm-clean-beta", "0.4.2"))


def _clean_lock_project(tmp_path: Path) -> Path:
    """An npm lock whose packages match no advisory in the npm fixture DB."""
    project = tmp_path / "npm_clean"
    project.mkdir()
    packages: dict[str, object] = {"": {"name": "npm-clean-fixture", "version": "1.0.0"}}
    dependencies: dict[str, object] = {}
    for name, version in _CLEAN_NPM_PACKAGES:
        entry = {
            "version": version,
            "resolved": f"https://registry.npmjs.org/{name}/-/{name}-{version}.tgz",
            "integrity": "sha512-placeholder=",
        }
        packages[f"node_modules/{name}"] = entry
        dependencies[name] = entry
    lock = {"name": "npm-clean-fixture", "lockfileVersion": 2, "packages": packages, "dependencies": dependencies}
    (project / "package-lock.json").write_text(json.dumps(lock, indent=2), encoding="utf-8")
    return project


def _npm_project(kind: str, tmp_path: Path) -> tuple[Path, int]:
    """The clean-lock or vulnerable-lock fixture and its component count N."""
    if kind == "clean":
        return _clean_lock_project(tmp_path), len(_CLEAN_NPM_PACKAGES)
    return NPM_PROJECT, 1


def _npm_scan_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    builder = _load_builder()
    cache = tmp_path / "osv-cache"
    builder.build_offline_db(OSV_NPM_RECORDS, cache, ecosystem="npm")
    on_tree = _flag_tree(tmp_path / "flags", enabled=True)
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(on_tree))
    monkeypatch.setenv("OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY", str(cache))


def _scan_json(project: Path, monkeypatch: pytest.MonkeyPatch, *extra: str) -> tuple[int, dict]:
    import sys
    from io import StringIO

    buffer = StringIO()
    monkeypatch.setattr(sys, "stdout", buffer)
    exit_code = warden_main(["scan", str(project), "--format", "json", *extra])
    return exit_code, json.loads(buffer.getvalue())


def test_scan_native_lockfile_inventories_a_clean_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AC3: osv-scanner lists every package (``--all-packages``), not only the vulnerable ones."""
    _npm_scan_env(tmp_path, monkeypatch)
    project = _clean_lock_project(tmp_path)

    scan = scan_native_lockfile(project, ScannedManifest(path="package-lock.json", kind="package-lock.json"))

    assert scan.parse.errors == ()
    assert [(c.name, c.version) for c in scan.components] == sorted(_CLEAN_NPM_PACKAGES)
    assert not [f for f in scan.parse.findings if f.id.startswith("vuln:")]


@pytest.mark.parametrize("kind", ["clean", "vulnerable"])
def test_npm_license_and_currency_rows_count_what_ran(
    kind: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC1/AC3: the license and currency rows count the N components those axes judged."""
    from pyforge.warden.models import EMPTY_EXTRACTION_DRIVER_ID

    _npm_scan_env(tmp_path, monkeypatch)
    project, count = _npm_project(kind, tmp_path)

    _exit_code, report = _scan_json(project, monkeypatch)

    assert report["inventory_count"] == count
    assert not [f for f in report["findings"] if f["id"] == EMPTY_EXTRACTION_DRIVER_ID]
    rows = {row["axis"]: row for row in report["coverage"]}
    for axis in ("license", "currency"):
        assert rows[axis]["deps_total"] == rows[axis]["deps_assessed"] == count, axis
        unknowns = [f for f in report["findings"] if f["id"].startswith(f"{axis}:unknown:pdos-npm-")]
        assert len(unknowns) == count, axis
    assert rows["hygiene"]["deps_total"] == 0


@pytest.mark.parametrize(
    ("gate", "extra", "expected"),
    [
        ("ungated", (), "warn"),
        ("license", ("--deny-licenses", "GPL-3.0-only"), "indeterminate"),
        ("currency", ("--fail-on-eol",), "indeterminate"),
    ],
)
@pytest.mark.parametrize("kind", ["clean", "vulnerable"])
def test_npm_lock_composed_status_is_pinned(
    kind: str,
    gate: str,
    extra: tuple[str, ...],
    expected: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC2/AC6: unknowns warn ungated and route to indeterminate gated; never clean."""
    from pyforge.warden.report import REPORT_SCHEMA_VERSION

    _npm_scan_env(tmp_path, monkeypatch)
    project, _count = _npm_project(kind, tmp_path)

    exit_code, report = _scan_json(project, monkeypatch, *extra)

    assert report["schema_version"] == REPORT_SCHEMA_VERSION == "1.1.0"
    assert report["status"]["value"] == expected
    assert exit_code == (0 if expected == "warn" else 1)
    vuln_ids = [f["id"] for f in report["findings"] if f["id"].startswith("vuln:")]
    if kind == "vulnerable":
        assert vuln_ids == ["vuln:PDOS-NPM-FIXTURE-0001:pdos-npm-vuln-fixture@1.0.0"]
    else:
        assert vuln_ids == []
    if gate != "ungated":
        assert report["status"]["driver"]["axis"] == gate
        assert next(row for row in report["coverage"] if row["axis"] == gate)["gating"] is True
