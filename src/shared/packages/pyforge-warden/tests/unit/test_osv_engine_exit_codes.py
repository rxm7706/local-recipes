"""Unit tests -- ``OsvEngine.run()``'s exit-code disposition (Story 1.5),
exercised with an INJECTED FAKE ``subprocess.run`` against a REAL offline DB
(so the content pre-flight passes and each exit-code branch is actually
reached). Complements ``tests/conformance/test_osv_engine.py`` (real
osv-scanner binary, vulnerable/clean/DB-absent) by covering the three
exit-code rows its own I/O matrix documents but that suite's real-binary
scope cannot easily force: 127 (a passing pre-flight but osv still failed to
load the DB), 128 (no packages found), and any other/unexpected code.
"""

from __future__ import annotations

import importlib.util
import subprocess
import types
from pathlib import Path

import pytest

from pyforge.warden.engines import OsvEngine
from pyforge.warden.inventory import PypiIdentity, ResolvedInventory
from pyforge.warden.models import (
    AXIS_VULNERABILITY,
    Ecosystem,
    ErrorKind,
    ScannedManifest,
)
from pyforge.warden.vuln import OSV_DB_CACHE_ENV_VAR

TESTS_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = TESTS_ROOT / "fixtures"
OSV_RECORDS_DIR = FIXTURES / "osv-db" / "pypi"

MANIFEST = ScannedManifest(path="pyproject.toml", kind="pyproject.toml")
FIXTURE_PACKAGE = "pdos-vuln-fixture"
FIXTURE_VERSION = "1.0.0"


def _load_builder():
    """Import ``fixtures/osv_db_builder`` by path -- mirrors
    ``test_osv_offline_db_spike.py``'s ``_load_builder()``; production code
    never imports it."""
    module_path = FIXTURES / "osv_db_builder.py"
    spec = importlib.util.spec_from_file_location("osv_db_builder", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def offline_cache(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A REAL, content-valid offline DB -- so the pre-flight passes and
    ``OsvEngine.run()`` actually reaches ``_engine_env`` (and its exit-code
    branch) rather than short-circuiting on a failed pre-flight."""
    builder = _load_builder()
    cache_root = tmp_path_factory.mktemp("osv-exit-code-cache")
    return builder.build_offline_db(OSV_RECORDS_DIR, cache_root)


def _inventory(component_factory) -> ResolvedInventory:
    component = component_factory(
        name=FIXTURE_PACKAGE,
        version=FIXTURE_VERSION,
        pypi_identity=PypiIdentity(name=FIXTURE_PACKAGE, version=FIXTURE_VERSION),
    )
    return ResolvedInventory(components=(component,), resolved_scan_set=(MANIFEST,))


def _fake_run_exit(returncode: int, content: str = ""):
    """A ``subprocess.run`` stand-in that writes ``content`` to the
    ``--output-file`` path (osv-scanner's own flag, distinct from deptry's
    ``-o``) and returns ``returncode`` -- mirrors
    ``test_engine_env_deptry.py``'s ``_fake_run_writing`` helper. Story 6.6:
    ``OsvEngine.run`` now calls ``["osv-scanner", "--version"]`` FIRST (the
    version pre-flight) immediately before the real subprocess call this
    fake answers -- transparently answered with a fixed in-range version so
    every EXISTING exit-code test (which doesn't care about the version
    gate) is unaffected."""

    def fake_run(argv, **kwargs):
        if argv[:2] == ["osv-scanner", "--version"]:
            return types.SimpleNamespace(
                returncode=0,
                stdout=b"osv-scanner version: 2.4.0\n",
                stderr=b"",
            )
        out_path = argv[argv.index("--output-file") + 1]
        Path(out_path).write_text(content, encoding="utf-8")
        return types.SimpleNamespace(returncode=returncode, stdout=b"", stderr=b"")

    return fake_run


def test_exit_127_after_passing_preflight_is_typed_engine_execution_failed(
    monkeypatch, tmp_path, offline_cache, component_factory
):
    """127 after a PASSING content pre-flight is an anomaly (e.g. a TOCTOU
    DB change mid-scan) -- never re-treated as a coverage gap (that
    disposition is reserved for a pre-flight FAILURE, which never reaches
    ``_engine_env`` at all)."""
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(offline_cache))
    monkeypatch.setattr(subprocess, "run", _fake_run_exit(127, "{}"))
    inventory = _inventory(component_factory)

    result = OsvEngine().run(tmp_path, inventory)

    assert result.findings == ()
    (error,) = result.errors
    assert error.kind is ErrorKind.ENGINE_EXECUTION_FAILED
    assert error.owner == "osv-scanner"
    assert result.coverage == ()
    assert result.vuln_data is None


def test_exit_128_no_packages_mirrors_preflight_failure_withholding(
    monkeypatch, tmp_path, offline_cache, component_factory
):
    """128 (osv found no packages in the synthesized input) is routed
    IDENTICALLY to a failed pre-flight: one
    ``indeterminate:offline-db-unavailable:<pkg>`` finding per candidate,
    never a confident clean, no error record (this is a coverage gap, not
    an operational failure)."""
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(offline_cache))
    monkeypatch.setattr(subprocess, "run", _fake_run_exit(128))
    inventory = _inventory(component_factory)

    result = OsvEngine().run(tmp_path, inventory)

    assert result.errors == ()
    (finding,) = result.findings
    assert finding.id == (
        f"indeterminate:offline-db-unavailable:{FIXTURE_PACKAGE}@{FIXTURE_VERSION}"
    )
    assert finding.axis == AXIS_VULNERABILITY
    assert result.coverage == ()
    assert result.vuln_data is None


def test_unexpected_exit_code_is_typed_engine_execution_failed(
    monkeypatch, tmp_path, offline_cache, component_factory
):
    """Any exit code outside {0, 1, 127, 128} is a typed operational
    failure -- never a content-read that could bottom out at clean."""
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(offline_cache))
    monkeypatch.setattr(subprocess, "run", _fake_run_exit(3, "{}"))
    inventory = _inventory(component_factory)

    result = OsvEngine().run(tmp_path, inventory)

    assert result.findings == ()
    (error,) = result.errors
    assert error.kind is ErrorKind.ENGINE_EXECUTION_FAILED
    assert "3" in error.message
    assert result.coverage == ()
    assert result.vuln_data is None


def test_conda_ecosystem_candidate_with_resolved_identity_is_scanned(
    monkeypatch, tmp_path, offline_cache, component_factory
):
    """Story 2.1: a CONDA-ecosystem component with a resolved pypi_identity
    and vuln_matchable=True reaches the osv-scanner candidate set -- before
    the fix the ecosystem==PYPI filter made it invisible (the
    pytorch->torch false-green gap). Exit 128 ("no packages found") is
    osv-scanner's own signal, reachable only once the engine actually tried
    to run it -- proving the conda component was not filtered out
    pre-flight."""
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(offline_cache))
    monkeypatch.setattr(subprocess, "run", _fake_run_exit(128))
    conda_component = component_factory(
        name="numpy-conda-name",
        version=FIXTURE_VERSION,
        ecosystem=Ecosystem.CONDA,
        pypi_identity=PypiIdentity(name=FIXTURE_PACKAGE, version=FIXTURE_VERSION),
        vuln_matchable=True,  # the critical precondition this test exercises
    )
    inventory = ResolvedInventory(
        components=(conda_component,), resolved_scan_set=(MANIFEST,)
    )

    result = OsvEngine().run(tmp_path, inventory)

    assert result.errors == ()
    (finding,) = result.findings
    assert finding.id == (
        f"indeterminate:offline-db-unavailable:numpy-conda-name@{FIXTURE_VERSION}"
    )
    assert finding.axis == AXIS_VULNERABILITY


@pytest.mark.parametrize("returncode", [127, 128, 3])
def test_purity_guard_findings_survive_every_operational_failure_path(
    monkeypatch, tmp_path, offline_cache, component_factory, returncode
):
    """NFR-S6: a purity-guard-excluded candidate's
    ``indeterminate:unsafe-identity:<pkg>`` finding must survive an osv
    operational failure that happens AFTER the guard already ran (127, 128,
    or any other unexpected code) -- never silently dropped just because
    osv itself failed for the safe remainder of the candidates."""
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(offline_cache))
    monkeypatch.setattr(subprocess, "run", _fake_run_exit(returncode, "{}"))
    safe = component_factory(
        name=FIXTURE_PACKAGE,
        version=FIXTURE_VERSION,
        pypi_identity=PypiIdentity(name=FIXTURE_PACKAGE, version=FIXTURE_VERSION),
    )
    unsafe = component_factory(
        name="-rf",
        version="1.0",
        pypi_identity=PypiIdentity(name="-rf", version="1.0"),
    )
    inventory = ResolvedInventory(
        components=(safe, unsafe), resolved_scan_set=(MANIFEST,)
    )

    result = OsvEngine().run(tmp_path, inventory)

    unsafe_ids = [f.id for f in result.findings if f.id.startswith("indeterminate:unsafe-identity:")]
    if returncode == 128:
        # 128 reclassifies EVERY candidate (including purity-guard-excluded
        # ones) into offline-db-unavailable -- the story's own sanctioned
        # I/O-matrix disposition -- so no unsafe-identity finding survives,
        # but nothing is silently dropped either (both candidates still get
        # a withheld finding).
        assert unsafe_ids == []
        assert len(result.findings) == 2
    else:
        assert unsafe_ids == ["indeterminate:unsafe-identity:-rf@1.0"]
