"""Conformance tests -- ``OsvEngine.run()`` against the REAL ``osv-scanner``
binary (Story 1.5), exercised through PRODUCTION code (``engines.OsvEngine``,
never a spike-local runner). Reuses the Story 1.4 fixture DB builder +
records (the same substrate ``test_osv_offline_db_spike.py`` proves the raw
mechanics against) -- imported BY PATH, exactly like that spike test does;
this suite never imports it as a package.

If ``osv-scanner`` is absent from PATH this suite HARD-FAILS (never skips)
-- matches the 1.3/1.4 provisioned-engine convention. The DB-absent case
below never actually spawns the subprocess (OsvEngine's own content
pre-flight short-circuits it in pure Python -- decision record § 4), but the
suite-wide hard-fail still applies: a conformance suite for a provisioned
engine must not silently green over a broken environment.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import time
import zipfile
from pathlib import Path

import pytest

from pyforge.warden.engines import OsvEngine
from pyforge.warden.inventory import PypiIdentity, ResolvedInventory
from pyforge.warden.models import (
    AXIS_VULNERABILITY,
    ScannedManifest,
    SeverityTier,
    WithholdReason,
)
from pyforge.warden.vuln import DB_MAX_AGE_DAYS, OSV_DB_CACHE_ENV_VAR, db_zip_path

TESTS_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = TESTS_ROOT / "fixtures"
OSV_RECORDS_DIR = FIXTURES / "osv-db" / "pypi"

FIXTURE_ADVISORY_ID = "PDOS-FIXTURE-0001"
FIXTURE_PACKAGE = "pdos-vuln-fixture"
FIXTURE_VULNERABLE_VERSION = "1.0.0"
FIXTURE_CLEAN_VERSION = "2.0.0"  # the fixture record's own "deliberately clean" fix

MANIFEST = ScannedManifest(path="pyproject.toml", kind="pyproject.toml")


def _osv_scanner_bin() -> str:
    """Return the ``osv-scanner`` path, HARD-FAILING (never skipping) if it
    is not on PATH -- mirrors ``test_osv_offline_db_spike.py``'s helper."""
    binary = shutil.which("osv-scanner")
    if binary is None:
        pytest.fail(
            "osv-scanner is not on PATH -- the vulnerability engine is a "
            "provisioned conda run-dep; a missing binary is a broken "
            "environment, not an excused (skipped) test. Run this suite via "
            "`pixi run -e pyforge-warden pyforge-warden-test`."
        )
    return binary


def _load_builder():
    """Import ``fixtures/osv_db_builder`` by path -- the same helper
    ``test_osv_offline_db_spike.py`` uses; production code never imports it."""
    module_path = FIXTURES / "osv_db_builder.py"
    spec = importlib.util.spec_from_file_location("osv_db_builder", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True, scope="module")
def _require_osv_scanner_on_path() -> None:
    _osv_scanner_bin()


@pytest.fixture(scope="module")
def offline_cache(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the Story 1.4 hermetic offline OSV DB into a session-scoped tmp
    cache and hand back the cache root (the value OsvEngine resolves
    ``OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY`` to)."""
    builder = _load_builder()
    cache_root = tmp_path_factory.mktemp("osv-engine-cache")
    return builder.build_offline_db(OSV_RECORDS_DIR, cache_root)


def _inventory(component_factory, *, version: str) -> ResolvedInventory:
    component = component_factory(
        name=FIXTURE_PACKAGE,
        version=version,
        pypi_identity=PypiIdentity(name=FIXTURE_PACKAGE, version=version),
    )
    return ResolvedInventory(components=(component,), resolved_scan_set=(MANIFEST,))


def test_vulnerable_pin_end_to_end_through_osv_engine(
    monkeypatch, tmp_path, offline_cache, component_factory
):
    """The Given/When/Then AC: a known-vulnerable pin against the 1.4
    fixture DB, run through PRODUCTION OsvEngine (not the spike runner) --
    the advisory + CVSS severity lands as a ``vuln:`` finding, coverage
    claims it assessed, and ``vuln_data`` is populated with the DB's own
    provenance."""
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(offline_cache))
    inventory = _inventory(component_factory, version=FIXTURE_VULNERABLE_VERSION)

    result = OsvEngine().run(tmp_path, inventory)

    assert result.errors == ()
    (finding,) = result.findings
    assert finding.id == (
        f"vuln:{FIXTURE_ADVISORY_ID}:{FIXTURE_PACKAGE}@{FIXTURE_VULNERABLE_VERSION}"
    )
    assert finding.axis == AXIS_VULNERABILITY
    assert finding.subject == FIXTURE_PACKAGE
    assert finding.severity is not None
    assert finding.severity.tier is SeverityTier.CRITICAL
    assert finding.severity.raw == "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"

    (coverage,) = result.coverage
    assert coverage.axis == AXIS_VULNERABILITY
    assert coverage.deps_total == inventory.count == 1
    assert coverage.deps_assessed == 1

    expected_zip = offline_cache / "osv-scanner" / "PyPI" / "all.zip"
    assert result.vuln_data is not None
    assert result.vuln_data.source == str(expected_zip)
    assert result.vuln_data.snapshot_at is not None
    # Story 2.5: the DB was just built (fresh mtime), so max_age_ok is now a
    # computed True -- never the pre-2.5 hardcoded None.
    assert result.vuln_data.max_age_ok is True


def test_clean_pin_end_to_end_through_osv_engine(
    monkeypatch, tmp_path, offline_cache, component_factory
):
    """A pin OUTSIDE the seeded advisory's affected versions is genuinely
    clean: osv ran, consulted the real DB, found nothing -- no finding, but
    coverage + vuln_data still populate (the axis WAS consulted)."""
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(offline_cache))
    inventory = _inventory(component_factory, version=FIXTURE_CLEAN_VERSION)

    result = OsvEngine().run(tmp_path, inventory)

    assert result.errors == ()
    assert result.findings == ()
    (coverage,) = result.coverage
    assert coverage.deps_assessed == 1
    assert result.vuln_data is not None
    assert result.vuln_data.source is not None
    assert result.vuln_data.snapshot_at is not None


def test_db_absent_never_reports_clean(monkeypatch, tmp_path, component_factory):
    """The cardinal false-green osv-scanner's own JSON body cannot
    distinguish (decision record § 4): with no usable local DB, OsvEngine
    must NEVER report a confident clean or an empty result -- one
    ``indeterminate:offline-db-unavailable:<pkg>`` finding per candidate,
    no coverage claim, no vuln_data."""
    monkeypatch.delenv(OSV_DB_CACHE_ENV_VAR, raising=False)
    inventory = _inventory(component_factory, version=FIXTURE_VULNERABLE_VERSION)

    result = OsvEngine().run(tmp_path, inventory)

    assert result.errors == ()
    (finding,) = result.findings
    assert finding.id == (
        f"indeterminate:offline-db-unavailable:"
        f"{FIXTURE_PACKAGE}@{FIXTURE_VULNERABLE_VERSION}"
    )
    assert finding.axis == AXIS_VULNERABILITY
    assert result.coverage == ()  # coverage-skipped -- never a confident claim
    assert result.vuln_data is None


def test_db_present_but_empty_zip_never_reports_clean(monkeypatch, tmp_path, component_factory):
    """The empty/hollow-DB false-green (decision record H1): a present-but-
    EMPTY all.zip must fail the content pre-flight exactly like an absent
    one -- never a namelist-only check that a 0-entry zip would pass."""
    empty_cache = tmp_path / "empty-cache"
    (empty_cache / "osv-scanner" / "PyPI").mkdir(parents=True)
    with zipfile.ZipFile(empty_cache / "osv-scanner" / "PyPI" / "all.zip", "w"):
        pass
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(empty_cache))
    inventory = _inventory(component_factory, version=FIXTURE_VULNERABLE_VERSION)

    result = OsvEngine().run(tmp_path, inventory)

    assert result.errors == ()
    (finding,) = result.findings
    assert finding.id == (
        f"indeterminate:offline-db-unavailable:"
        f"{FIXTURE_PACKAGE}@{FIXTURE_VULNERABLE_VERSION}"
    )
    assert result.coverage == ()
    assert result.vuln_data is None


def test_zero_candidates_never_invokes_osv(tmp_path):
    """No vuln-matchable PyPI candidates -> the empty EngineResult, osv never
    invoked at all (mirrors NullEngine)."""
    inventory = ResolvedInventory(components=(), resolved_scan_set=(MANIFEST,))
    result = OsvEngine().run(tmp_path, inventory)
    assert result.findings == ()
    assert result.errors == ()
    assert result.coverage == ()
    assert result.vuln_data is None


# --- Story 2.5: the name-level tier (FR13) + stale-DB honesty (FR12) --------


def test_name_level_only_candidate_yields_the_critical_finding_without_a_subprocess(
    monkeypatch, tmp_path, component_factory
):
    """FR13's Given/When/Then AC, end to end through PRODUCTION OsvEngine: a
    mapped-but-unversioned component (a ``pdos-vuln-fixture>=1.0.0``-style
    ranged/name-only dep) whose name carries a CRITICAL advisory at SOME
    version yields the name-level finding -- never a confident clean -- and,
    since there are no exact-match candidates at all, the osv-scanner
    subprocess is never invoked: no coverage claim, no ``vuln:`` finding."""
    builder = _load_builder()
    cache_root = builder.build_offline_db(OSV_RECORDS_DIR, tmp_path / "db-cache")
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(cache_root))
    component = component_factory(
        name=FIXTURE_PACKAGE,
        version=None,
        pypi_identity=PypiIdentity(name=FIXTURE_PACKAGE, version=None),
        indeterminate_reason=WithholdReason.RANGE_ONLY,
    )
    inventory = ResolvedInventory(
        components=(component,), resolved_scan_set=(MANIFEST,)
    )

    result = OsvEngine().run(tmp_path, inventory)

    assert result.errors == ()
    (finding,) = result.findings
    assert finding.id == (
        f"indeterminate:name-level-critical-cve:{FIXTURE_PACKAGE}@unspecified"
    )
    assert finding.axis == AXIS_VULNERABILITY
    assert finding.severity is None
    # A worry-list nudge, never real coverage -- and never a `vuln:` finding
    # (that family only ever comes from a real version-matched osv-scanner
    # run, which never happened here).
    assert result.coverage == ()
    assert result.vuln_data is not None
    assert result.vuln_data.source == str(db_zip_path(cache_root))
    assert result.vuln_data.max_age_ok is True


def test_stale_db_forces_the_whole_axis_indeterminate_even_when_otherwise_clean(
    monkeypatch, tmp_path, component_factory
):
    """FR12's Given/When/Then AC: a ``snapshot_at`` strictly older than
    ``DB_MAX_AGE_DAYS`` forces the WHOLE vulnerability axis to
    ``indeterminate`` via a ``vuln-data-stale`` finding -- even when the
    underlying pin is genuinely OUTSIDE the seeded advisory's affected
    versions (``parse_osv_output`` would otherwise report a genuinely clean
    scan: no ``vuln:`` findings at all)."""
    builder = _load_builder()
    cache_root = builder.build_offline_db(OSV_RECORDS_DIR, tmp_path / "db-cache")
    zip_path = db_zip_path(cache_root)
    assert zip_path is not None
    stale_mtime = time.time() - (DB_MAX_AGE_DAYS + 1) * 86400
    os.utime(zip_path, (stale_mtime, stale_mtime))
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(cache_root))
    inventory = _inventory(component_factory, version=FIXTURE_CLEAN_VERSION)

    result = OsvEngine().run(tmp_path, inventory)

    assert result.errors == ()
    finding_ids = {f.id for f in result.findings}
    assert "indeterminate:vuln-data-stale:vuln-database" in finding_ids
    # The underlying match is genuinely clean: no `vuln:` finding is present
    # despite the whole axis landing indeterminate.
    assert not any(fid.startswith("vuln:") for fid in finding_ids)
    (coverage,) = result.coverage
    assert coverage.deps_assessed == 1
    assert result.vuln_data is not None
    assert result.vuln_data.max_age_ok is False


# NOTE: the exactly-at-the-boundary case is deterministically unit-tested in
# tests/unit/test_vuln.py (test_is_db_stale_exactly_at_the_boundary_is_not_
# stale) with an INJECTED `now` -- a conformance-level equivalent through the
# real engine (which calls datetime.now(UTC) internally, uninjectable) would
# be racy: the small elapsed wall-clock time between setting the DB's mtime
# and OsvEngine.run's own now() call could tip a "boundary" mtime over into
# genuinely stale, non-deterministically.


def test_name_level_only_candidate_with_a_stale_db_merges_both_findings(
    monkeypatch, tmp_path, component_factory
):
    """Review finding, 2026-07-16: the class docstring promises the stale
    finding merges into every content-bearing result INCLUDING the
    name-level-only path (no exact-match candidates at all, so the
    osv-scanner subprocess never runs) -- this combination had no direct
    test. A mapped-but-unversioned component against a DB that is BOTH
    genuinely critical-for-that-name AND stale must surface BOTH findings,
    and ``vuln_data.max_age_ok`` must reflect the staleness even though the
    only DB access was the in-process name-level scan, never a subprocess."""
    builder = _load_builder()
    cache_root = builder.build_offline_db(OSV_RECORDS_DIR, tmp_path / "db-cache")
    zip_path = db_zip_path(cache_root)
    assert zip_path is not None
    stale_mtime = time.time() - (DB_MAX_AGE_DAYS + 1) * 86400
    os.utime(zip_path, (stale_mtime, stale_mtime))
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(cache_root))
    component = component_factory(
        name=FIXTURE_PACKAGE,
        version=None,
        pypi_identity=PypiIdentity(name=FIXTURE_PACKAGE, version=None),
        indeterminate_reason=WithholdReason.RANGE_ONLY,
    )
    inventory = ResolvedInventory(
        components=(component,), resolved_scan_set=(MANIFEST,)
    )

    result = OsvEngine().run(tmp_path, inventory)

    assert result.errors == ()
    finding_ids = {f.id for f in result.findings}
    assert (
        f"indeterminate:name-level-critical-cve:{FIXTURE_PACKAGE}@unspecified"
        in finding_ids
    )
    assert "indeterminate:vuln-data-stale:vuln-database" in finding_ids
    assert result.vuln_data is not None
    assert result.vuln_data.source == str(zip_path)
    assert result.vuln_data.max_age_ok is False


def test_purity_guard_excludes_everything_still_reports_name_level_and_staleness(
    monkeypatch, tmp_path, component_factory
):
    """Review finding, 2026-07-16: when every EXACT-match candidate is
    excluded by the NFR-S6 purity guard (nothing left to feed osv-scanner),
    ``OsvEngine.run`` previously dropped ``vuln_data``/the stale finding even
    though the SAME resolved DB zip was genuinely consulted for the
    independently-computed name-level scan -- a coverage-honesty gap this
    patch closes. One unsafe-identity exact candidate (excluded) plus one
    critical, mapped-but-unversioned candidate, against a stale DB."""
    builder = _load_builder()
    cache_root = builder.build_offline_db(OSV_RECORDS_DIR, tmp_path / "db-cache")
    zip_path = db_zip_path(cache_root)
    assert zip_path is not None
    stale_mtime = time.time() - (DB_MAX_AGE_DAYS + 1) * 86400
    os.utime(zip_path, (stale_mtime, stale_mtime))
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(cache_root))
    unsafe_component = component_factory(
        name="-rf",
        version="1.0",
        pypi_identity=PypiIdentity(name="-rf", version="1.0"),
    )
    name_level_component = component_factory(
        name=FIXTURE_PACKAGE,
        version=None,
        pypi_identity=PypiIdentity(name=FIXTURE_PACKAGE, version=None),
        indeterminate_reason=WithholdReason.RANGE_ONLY,
    )
    inventory = ResolvedInventory(
        components=(unsafe_component, name_level_component),
        resolved_scan_set=(MANIFEST,),
    )

    result = OsvEngine().run(tmp_path, inventory)

    assert result.errors == ()
    finding_ids = {f.id for f in result.findings}
    assert "indeterminate:unsafe-identity:-rf@1.0" in finding_ids
    assert (
        f"indeterminate:name-level-critical-cve:{FIXTURE_PACKAGE}@unspecified"
        in finding_ids
    )
    assert "indeterminate:vuln-data-stale:vuln-database" in finding_ids
    assert result.vuln_data is not None
    assert result.vuln_data.source == str(zip_path)
    assert result.vuln_data.max_age_ok is False
