"""Conformance tests -- CISA KEV enrichment + the ``fail-on-kev`` gate
(Story 6.4), exercised through PRODUCTION code: ``OsvEngine.run()`` directly
(mirrors ``test_osv_engine.py``'s real-``osv-scanner`` convention) AND the
full ``cli.main()`` pipeline (mirrors ``test_scan_harness.py``'s convention)
for the end-to-end AC ("exit 1 regardless of CVSS tier").

The hermetic fixture advisory, ``PDOS-KEV-FIXTURE-0001`` (package
``pdos-kev-fixture``, ``tests/fixtures/osv-db/pypi/PDOS-KEV-FIXTURE-0001.json``,
auto-loaded into every test's ambient offline OSV DB): its OWN id is
deliberately NOT CVE-shaped (mirrors real-world PyPI advisories, GHSA-/
PYSEC-scoped) -- the KEV-matchable CVE, ``CVE-1970-00001``, lives only in
its ``aliases`` (empirically confirmed via a real osv-scanner 2.4.0 run:
``groups[].ids == ["PDOS-KEV-FIXTURE-0001"]``, ``groups[].aliases ==
["CVE-1970-00001", "PDOS-KEV-FIXTURE-0001"]``) -- proving alias-based KEV
matching actually works, not merely that a fixture's own primary id happens
to look CVE-shaped. Its CVSS:3.1 vector computes to base score 5.4 (MEDIUM
-- warn by default), deliberately non-CRITICAL so a forced policy-violation
is provably independent of CVSS tier.

If ``osv-scanner`` is absent from PATH this suite HARD-FAILS (never skips)
-- matches the 1.5/2.5 provisioned-engine convention.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import jsonschema
import pytest

from pyforge.warden import feeds
from pyforge.warden.cli import main
from pyforge.warden.engines import OsvEngine
from pyforge.warden.inventory import PypiIdentity, ResolvedInventory
from pyforge.warden.models import AXIS_VULNERABILITY, ScannedManifest
from pyforge.warden.vuln import OSV_DB_CACHE_ENV_VAR, db_zip_path

TESTS_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = TESTS_ROOT / "fixtures"
OSV_RECORDS_DIR = FIXTURES / "osv-db" / "pypi"
PROJECTS = FIXTURES / "projects"
VULN_KEV = PROJECTS / "vuln_kev"
VULN_KEV_FAIL_ON_KEV_FALSE = PROJECTS / "vuln_kev_fail_on_kev_false"

FIXTURE_ADVISORY_ID = "PDOS-KEV-FIXTURE-0001"
FIXTURE_PACKAGE = "pdos-kev-fixture"
FIXTURE_VERSION = "1.0.0"
FIXTURE_CVE = "CVE-1970-00001"
FIXTURE_DATE_ADDED = "2026-01-01"
FIXTURE_FINDING_ID = f"vuln:{FIXTURE_ADVISORY_ID}:{FIXTURE_PACKAGE}@{FIXTURE_VERSION}"

MANIFEST = ScannedManifest(path="pyproject.toml", kind="pyproject.toml")


def _osv_scanner_bin() -> str:
    binary = shutil.which("osv-scanner")
    if binary is None:
        pytest.fail(
            "osv-scanner is not on PATH -- the vulnerability engine is a "
            "provisioned conda run-dep; a missing binary is a broken "
            "environment, not an excused (skipped) test. Run this suite via "
            "`pixi run -e pyforge-warden pyforge-warden-test`."
        )
    return binary


def _load_osv_builder():
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
    builder = _load_osv_builder()
    cache_root = tmp_path_factory.mktemp("kev-osv-engine-cache")
    return builder.build_offline_db(OSV_RECORDS_DIR, cache_root)


def _inventory(component_factory) -> ResolvedInventory:
    component = component_factory(
        name=FIXTURE_PACKAGE,
        version=FIXTURE_VERSION,
        pypi_identity=PypiIdentity(name=FIXTURE_PACKAGE, version=FIXTURE_VERSION),
    )
    return ResolvedInventory(components=(component,), resolved_scan_set=(MANIFEST,))


def _kev_cache_with_match(tmp_path: Path) -> Path:
    cache_dir = tmp_path / "kev-cache-match"
    feeds.write_kev_cache(
        cache_dir,
        {
            "vulnerabilities": [
                {"cveID": FIXTURE_CVE, "dateAdded": FIXTURE_DATE_ADDED},
            ]
        },
    )
    return cache_dir


def _kev_cache_without_match(tmp_path: Path) -> Path:
    cache_dir = tmp_path / "kev-cache-no-match"
    feeds.write_kev_cache(
        cache_dir,
        {
            "vulnerabilities": [
                {"cveID": "CVE-1970-09999", "dateAdded": "2026-09-09"},
            ]
        },
    )
    return cache_dir


# --- OsvEngine.run() level: kev/kev_date stamping + kev_data provenance -----


def test_kev_match_stamps_kev_true_and_kev_date(
    monkeypatch, tmp_path, offline_cache, component_factory
):
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(offline_cache))
    monkeypatch.setenv(
        feeds.FEED_CACHE_DIR_ENV_VAR, str(_kev_cache_with_match(tmp_path))
    )
    inventory = _inventory(component_factory)

    result = OsvEngine(fail_on_kev=True).run(tmp_path, inventory)

    assert result.errors == ()
    matches = [f for f in result.findings if f.id == FIXTURE_FINDING_ID]
    assert len(matches) == 1
    finding = matches[0]
    assert finding.kev is True
    assert finding.kev_date == FIXTURE_DATE_ADDED
    assert result.kev_data is not None
    assert result.kev_data.max_age_ok is True


def test_no_kev_match_stamps_kev_false(
    monkeypatch, tmp_path, offline_cache, component_factory
):
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(offline_cache))
    monkeypatch.setenv(
        feeds.FEED_CACHE_DIR_ENV_VAR, str(_kev_cache_without_match(tmp_path))
    )
    inventory = _inventory(component_factory)

    result = OsvEngine(fail_on_kev=True).run(tmp_path, inventory)

    assert result.errors == ()
    (finding,) = [f for f in result.findings if f.id == FIXTURE_FINDING_ID]
    assert finding.kev is False
    assert finding.kev_date is None
    assert result.kev_data is not None


def test_fail_on_kev_false_never_consults_the_kev_cache(
    monkeypatch, tmp_path, offline_cache, component_factory
):
    """Matrix row 3: with the gate off, the KEV cache is never even opened
    -- every finding's kev stays None, and kev_data stays None, even though
    a real match is sitting right there waiting to be found."""
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(offline_cache))
    monkeypatch.setenv(
        feeds.FEED_CACHE_DIR_ENV_VAR, str(_kev_cache_with_match(tmp_path))
    )
    inventory = _inventory(component_factory)

    result = OsvEngine(fail_on_kev=False).run(tmp_path, inventory)

    assert result.errors == ()
    (finding,) = [f for f in result.findings if f.id == FIXTURE_FINDING_ID]
    assert finding.kev is None
    assert finding.kev_date is None
    assert result.kev_data is None
    assert not any(f.id.startswith("indeterminate:kev-") for f in result.findings)


def test_kev_feed_absent_forces_whole_axis_indeterminate(
    monkeypatch, tmp_path, offline_cache, component_factory
):
    """Matrix row 4: no usable KEV cache -- the whole vulnerability axis
    lands indeterminate via one kev-data-unavailable finding; kev_data is
    None; the underlying vuln: finding's own kev stays None (never
    matched -- there was no catalog to match against)."""
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(offline_cache))
    monkeypatch.setenv(feeds.FEED_CACHE_DIR_ENV_VAR, str(tmp_path / "no-such-cache"))
    inventory = _inventory(component_factory)

    result = OsvEngine(fail_on_kev=True).run(tmp_path, inventory)

    assert result.errors == ()
    finding_ids = {f.id for f in result.findings}
    assert "indeterminate:kev-data-unavailable:kev-feed" in finding_ids
    assert result.kev_data is None
    (finding,) = [f for f in result.findings if f.id == FIXTURE_FINDING_ID]
    assert finding.kev is None


def test_kev_cache_vanishing_between_load_and_provenance_is_unavailable_not_a_crash(
    monkeypatch, tmp_path, offline_cache, component_factory
):
    """TOCTOU hardening: if the KEV cache file disappears in the narrow
    window between ``load_kev_catalog``'s successful read and
    ``feed_provenance``'s own ``path.stat()`` call, ``_kev_enrichment``
    must degrade to the same "no usable feed" outcome as an absent cache
    -- never let the race propagate as an uncaught ``OSError`` that would
    crash the whole engine run and discard every vuln finding."""
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(offline_cache))
    monkeypatch.setenv(
        feeds.FEED_CACHE_DIR_ENV_VAR, str(_kev_cache_with_match(tmp_path))
    )

    def _raise_missing(**_kwargs):
        raise FileNotFoundError("cache file vanished between read and stat")

    monkeypatch.setattr(
        "pyforge.warden.engines.feeds.feed_provenance", _raise_missing
    )
    inventory = _inventory(component_factory)

    result = OsvEngine(fail_on_kev=True).run(tmp_path, inventory)

    assert result.errors == ()
    finding_ids = {f.id for f in result.findings}
    assert "indeterminate:kev-data-unavailable:kev-feed" in finding_ids
    assert result.kev_data is None
    (finding,) = [f for f in result.findings if f.id == FIXTURE_FINDING_ID]
    assert finding.kev is None


def test_kev_feed_stale_forces_whole_axis_indeterminate_but_still_matches(
    monkeypatch, tmp_path, offline_cache, component_factory
):
    """Matrix row 5: a real, loadable-but-aged KEV cache -- the whole axis
    still lands indeterminate via kev-data-stale, kev_data.max_age_ok is
    False, but per-finding matching still ran (informational): this
    scenario deliberately uses a cache WITHOUT a match, so the axis-level
    indeterminate is the only signal (never obscured by a concurrent
    forced policy-violation)."""
    import os
    import time

    cache_dir = _kev_cache_without_match(tmp_path)
    stale_mtime = time.time() - (feeds.DEFAULT_FEED_MAX_AGE_DAYS + 1) * 86400
    kev_path = feeds.kev_cache_path(cache_dir)
    os.utime(kev_path, (stale_mtime, stale_mtime))
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(offline_cache))
    monkeypatch.setenv(feeds.FEED_CACHE_DIR_ENV_VAR, str(cache_dir))
    inventory = _inventory(component_factory)

    result = OsvEngine(fail_on_kev=True).run(tmp_path, inventory)

    assert result.errors == ()
    finding_ids = {f.id for f in result.findings}
    assert "indeterminate:kev-data-stale:kev-feed" in finding_ids
    assert result.kev_data is not None
    assert result.kev_data.max_age_ok is False
    (finding,) = [f for f in result.findings if f.id == FIXTURE_FINDING_ID]
    assert finding.kev is False  # per-finding matching still ran


def test_zero_vuln_matchable_candidates_never_consults_kev(tmp_path):
    """Matrix row 6: mirrors OsvEngine's own empty-candidate short-circuit
    -- no KEV consultation attempted at all."""
    inventory = ResolvedInventory(components=(), resolved_scan_set=(MANIFEST,))
    result = OsvEngine(fail_on_kev=True).run(tmp_path, inventory)
    assert result.findings == ()
    assert result.kev_data is None


# --- Full cli.main() pipeline: the end-to-end AC ------------------------------


def load_schema() -> dict:
    from importlib import resources

    schema_file = resources.files("pyforge.warden") / "data" / "report-schema.json"
    return json.loads(schema_file.read_text(encoding="utf-8"))


def run_scan(capsys, target, *extra: str) -> tuple[int, str, str]:
    capsys.readouterr()
    rc = main(["scan", str(target), "--format", "json", *extra])
    captured = capsys.readouterr()
    return rc, captured.out, captured.err


def parse_report(stdout: str) -> dict:
    document = json.loads(stdout)
    jsonschema.Draft202012Validator(load_schema()).validate(document)
    return document


def test_kev_match_forces_exit_1_regardless_of_cvss_tier(monkeypatch, tmp_path, capsys):
    """AC1, end to end: PDOS-KEV-FIXTURE-0001 is MEDIUM-tier (warn by
    default -- see the fixture record's own docstring, empirically
    verified 5.4 base score), yet with fail-on-kev unset (default true)
    and a KEV cache carrying its aliased CVE, the composed status is
    policy-violation and the exit code is 1 -- independent of the CVSS
    tier that would otherwise only warn."""
    monkeypatch.setenv(
        feeds.FEED_CACHE_DIR_ENV_VAR, str(_kev_cache_with_match(tmp_path))
    )
    rc, out, err = run_scan(capsys, VULN_KEV)
    document = parse_report(out)

    assert rc == 1
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "policy-violation"
    matches = [f for f in document["findings"] if f["id"] == FIXTURE_FINDING_ID]
    assert len(matches) == 1
    finding = matches[0]
    assert finding["severity"]["tier"] == "medium"
    assert finding["kev"] is True
    assert finding["kev_date"] == FIXTURE_DATE_ADDED
    assert document["kev_data"] is not None
    assert document["kev_data"]["max_age_ok"] is True
    assert err == ""


def test_fail_on_kev_false_is_byte_identical_cvss_only_gating(
    monkeypatch, tmp_path, capsys
):
    """AC2, end to end: the SAME KEV-matching cache, but `fail-on-kev =
    false` in the fixture's own [tool.pyforge-warden] table -- the KEV
    cache is never consulted (matrix "Policy off" row), every finding's
    kev stays null, and the MEDIUM-tier match's default warn/exit-0
    CVSS-only gating survives untouched."""
    monkeypatch.setenv(
        feeds.FEED_CACHE_DIR_ENV_VAR, str(_kev_cache_with_match(tmp_path))
    )
    rc, out, err = run_scan(capsys, VULN_KEV_FAIL_ON_KEV_FALSE)
    document = parse_report(out)

    assert rc == 0
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "warn"
    matches = [f for f in document["findings"] if f["id"] == FIXTURE_FINDING_ID]
    assert len(matches) == 1
    finding = matches[0]
    assert finding["kev"] is None
    assert finding["kev_date"] is None
    assert document["kev_data"] is None
    assert err == ""


def test_kev_feed_absent_end_to_end_composes_indeterminate(
    monkeypatch, tmp_path, capsys
):
    """Matrix row 4, end to end: no usable KEV cache while fail-on-kev is
    active composes indeterminate/exit 1 -- never a silent pass, even
    though the underlying CVSS match would otherwise only warn."""
    monkeypatch.setenv(feeds.FEED_CACHE_DIR_ENV_VAR, str(tmp_path / "no-such-cache"))
    rc, out, err = run_scan(capsys, VULN_KEV)
    document = parse_report(out)

    assert rc == 1
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "indeterminate"
    finding_ids = {f["id"] for f in document["findings"]}
    assert "indeterminate:kev-data-unavailable:kev-feed" in finding_ids
    assert document["kev_data"] is None
    assert err == ""
