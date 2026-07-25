"""Conformance tests -- FIRST.org EPSS enrichment + the ``--min-epss`` gate
(Story 6.7), exercised through PRODUCTION code: ``OsvEngine.run()`` directly
(mirrors ``test_kev_enrichment.py``'s real-``osv-scanner`` convention) AND
the full ``cli.main()`` pipeline (mirrors ``test_scan_harness.py``'s
convention) for the end-to-end AC ("exit 1 regardless of CVSS tier").

Reuses the SAME hermetic fixture advisory ``test_kev_enrichment.py`` does,
``PDOS-KEV-FIXTURE-0001`` (package ``pdos-kev-fixture``, ``tests/fixtures/
osv-db/pypi/PDOS-KEV-FIXTURE-0001.json``, auto-loaded into every test's
ambient offline OSV DB): its OWN id is deliberately NOT CVE-shaped -- the
EPSS-matchable CVE, ``CVE-1970-00001``, lives only in its ``aliases`` --
EPSS matching reuses ``OsvParse.kev_candidates`` verbatim (Story 6.7's
Boundaries), so the SAME candidate-collection proof KEV's own suite already
establishes applies here unchanged. Its CVSS:3.1 vector computes to base
score 5.4 (MEDIUM -- warn by default), deliberately non-CRITICAL so a forced
policy-violation is provably independent of CVSS tier.

``--min-epss`` is a real, two-mode CLI flag (unlike ``--fail-on-kev``'s
TOML-only shape) -- the E2E tests reuse ``vuln_kev_fail_on_kev_false``'s
fixture project (``fail-on-kev = false`` in its own ``[tool.pyforge-
warden]``) so EPSS's own effect is isolated from KEV's default-on gate.

If ``osv-scanner`` is absent from PATH this suite HARD-FAILS (never skips)
-- matches the 1.5/2.5/6.4 provisioned-engine convention.
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
VULN_KEV_FAIL_ON_KEV_FALSE = PROJECTS / "vuln_kev_fail_on_kev_false"
VULN_KEV = PROJECTS / "vuln_kev"
VULN_MIN_EPSS_TOML = PROJECTS / "vuln_min_epss_toml"

FIXTURE_ADVISORY_ID = "PDOS-KEV-FIXTURE-0001"
FIXTURE_PACKAGE = "pdos-kev-fixture"
FIXTURE_VERSION = "1.0.0"
FIXTURE_CVE = "CVE-1970-00001"
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
    cache_root = tmp_path_factory.mktemp("epss-osv-engine-cache")
    return builder.build_offline_db(OSV_RECORDS_DIR, cache_root)


def _inventory(component_factory) -> ResolvedInventory:
    component = component_factory(
        name=FIXTURE_PACKAGE,
        version=FIXTURE_VERSION,
        pypi_identity=PypiIdentity(name=FIXTURE_PACKAGE, version=FIXTURE_VERSION),
    )
    return ResolvedInventory(components=(component,), resolved_scan_set=(MANIFEST,))


def _epss_cache_with_match(tmp_path: Path, *, score: float = 0.7) -> Path:
    cache_dir = tmp_path / "epss-cache-match"
    feeds.write_epss_cache(
        cache_dir,
        {"scores": [{"cve": FIXTURE_CVE, "epss": score, "percentile": 0.9}]},
    )
    return cache_dir


def _epss_cache_without_match(tmp_path: Path) -> Path:
    cache_dir = tmp_path / "epss-cache-no-match"
    feeds.write_epss_cache(
        cache_dir,
        {"scores": [{"cve": "CVE-1970-09999", "epss": 0.5, "percentile": 0.5}]},
    )
    return cache_dir


# --- OsvEngine.run() level: epss stamping + epss_data provenance ------------


def test_epss_match_stamps_score_and_percentile(
    monkeypatch, tmp_path, offline_cache, component_factory
):
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(offline_cache))
    monkeypatch.setenv(
        feeds.FEED_CACHE_DIR_ENV_VAR, str(_epss_cache_with_match(tmp_path))
    )
    inventory = _inventory(component_factory)

    result = OsvEngine(fail_on_kev=False, min_epss=0.9).run(tmp_path, inventory)

    assert result.errors == ()
    matches = [f for f in result.findings if f.id == FIXTURE_FINDING_ID]
    assert len(matches) == 1
    finding = matches[0]
    assert finding.epss is not None
    assert finding.epss.score == 0.7
    assert finding.epss.percentile == 0.9
    assert result.epss_data is not None
    assert result.epss_data.max_age_ok is True


def test_no_epss_match_leaves_epss_none(
    monkeypatch, tmp_path, offline_cache, component_factory
):
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(offline_cache))
    monkeypatch.setenv(
        feeds.FEED_CACHE_DIR_ENV_VAR, str(_epss_cache_without_match(tmp_path))
    )
    inventory = _inventory(component_factory)

    result = OsvEngine(fail_on_kev=False, min_epss=0.5).run(tmp_path, inventory)

    assert result.errors == ()
    (finding,) = [f for f in result.findings if f.id == FIXTURE_FINDING_ID]
    assert finding.epss is None
    assert result.epss_data is not None


def test_out_of_range_cached_score_degrades_instead_of_crashing(
    monkeypatch, tmp_path, offline_cache, component_factory
):
    """Review finding (two passes): a corrupted cache entry (here, a score
    of 2.0, outside the valid probability range) must degrade the SAME way
    a non-match already does (``epss`` stays ``None``), never crash the
    whole scan. Since the follow-up pass, ``feeds.load_epss_scores`` filters
    the entry out at LOAD time (domain check), so the corrupt entry never
    even reaches ``_stamp_epss`` -- whose own ``try/except ValueError``
    remains as a last-resort crash-guard behind it."""
    cache_dir = tmp_path / "epss-cache-out-of-range"
    feeds.write_epss_cache(
        cache_dir, {"scores": [{"cve": FIXTURE_CVE, "epss": 2.0, "percentile": 0.9}]}
    )
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(offline_cache))
    monkeypatch.setenv(feeds.FEED_CACHE_DIR_ENV_VAR, str(cache_dir))
    inventory = _inventory(component_factory)

    result = OsvEngine(fail_on_kev=False, min_epss=0.5).run(tmp_path, inventory)

    assert result.errors == ()
    (finding,) = [f for f in result.findings if f.id == FIXTURE_FINDING_ID]
    assert finding.epss is None


def test_min_epss_none_never_consults_the_epss_cache(
    monkeypatch, tmp_path, offline_cache, component_factory
):
    """Gate off (default): the EPSS cache is never even opened -- every
    finding's epss stays None, and epss_data stays None, even though a real
    match is sitting right there waiting to be found."""
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(offline_cache))
    monkeypatch.setenv(
        feeds.FEED_CACHE_DIR_ENV_VAR, str(_epss_cache_with_match(tmp_path))
    )
    inventory = _inventory(component_factory)

    result = OsvEngine(fail_on_kev=False, min_epss=None).run(tmp_path, inventory)

    assert result.errors == ()
    (finding,) = [f for f in result.findings if f.id == FIXTURE_FINDING_ID]
    assert finding.epss is None
    assert result.epss_data is None
    assert not any(f.id.startswith("indeterminate:epss-") for f in result.findings)


def test_epss_feed_absent_forces_whole_axis_indeterminate(
    monkeypatch, tmp_path, offline_cache, component_factory
):
    """No usable EPSS cache while --min-epss is active -- the whole
    vulnerability axis lands indeterminate via one epss-data-unavailable
    finding; epss_data is None; the underlying vuln: finding's own epss
    stays None (never matched -- there was no catalog to match against)."""
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(offline_cache))
    monkeypatch.setenv(feeds.FEED_CACHE_DIR_ENV_VAR, str(tmp_path / "no-such-cache"))
    inventory = _inventory(component_factory)

    result = OsvEngine(fail_on_kev=False, min_epss=0.5).run(tmp_path, inventory)

    assert result.errors == ()
    finding_ids = {f.id for f in result.findings}
    assert "indeterminate:epss-data-unavailable:epss-feed" in finding_ids
    assert result.epss_data is None
    (finding,) = [f for f in result.findings if f.id == FIXTURE_FINDING_ID]
    assert finding.epss is None


def test_epss_cache_vanishing_between_load_and_provenance_is_unavailable_not_a_crash(
    monkeypatch, tmp_path, offline_cache, component_factory
):
    """TOCTOU hardening: if the EPSS cache file disappears in the narrow
    window between ``load_epss_scores``'s successful read and
    ``feed_provenance``'s own ``path.stat()`` call, ``_epss_enrichment``
    must degrade to the same "no usable feed" outcome as an absent cache --
    never let the race propagate as an uncaught ``OSError``."""
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(offline_cache))
    monkeypatch.setenv(
        feeds.FEED_CACHE_DIR_ENV_VAR, str(_epss_cache_with_match(tmp_path))
    )

    def _raise_missing(**_kwargs):
        raise FileNotFoundError("cache file vanished between read and stat")

    monkeypatch.setattr(
        "pyforge.warden.engines.feeds.feed_provenance", _raise_missing
    )
    inventory = _inventory(component_factory)

    result = OsvEngine(fail_on_kev=False, min_epss=0.5).run(tmp_path, inventory)

    assert result.errors == ()
    finding_ids = {f.id for f in result.findings}
    assert "indeterminate:epss-data-unavailable:epss-feed" in finding_ids
    assert result.epss_data is None
    (finding,) = [f for f in result.findings if f.id == FIXTURE_FINDING_ID]
    assert finding.epss is None


def test_epss_feed_stale_forces_whole_axis_indeterminate_but_still_matches(
    monkeypatch, tmp_path, offline_cache, component_factory
):
    """A real, loadable-but-aged EPSS cache -- the whole axis still lands
    indeterminate via epss-data-stale, epss_data.max_age_ok is False, but
    per-finding matching still ran (informational)."""
    import os
    import time

    cache_dir = _epss_cache_with_match(tmp_path)
    stale_mtime = time.time() - (feeds.DEFAULT_FEED_MAX_AGE_DAYS + 1) * 86400
    epss_path = feeds.epss_cache_path(cache_dir)
    os.utime(epss_path, (stale_mtime, stale_mtime))
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(offline_cache))
    monkeypatch.setenv(feeds.FEED_CACHE_DIR_ENV_VAR, str(cache_dir))
    inventory = _inventory(component_factory)

    result = OsvEngine(fail_on_kev=False, min_epss=0.5).run(tmp_path, inventory)

    assert result.errors == ()
    finding_ids = {f.id for f in result.findings}
    assert "indeterminate:epss-data-stale:epss-feed" in finding_ids
    assert result.epss_data is not None
    assert result.epss_data.max_age_ok is False
    (finding,) = [f for f in result.findings if f.id == FIXTURE_FINDING_ID]
    assert finding.epss is not None  # per-finding matching still ran
    assert finding.epss.score == 0.7


def test_zero_vuln_matchable_candidates_never_consults_epss(monkeypatch, tmp_path):
    """Mirrors OsvEngine's own empty-candidate short-circuit (engines.py's
    empty-inventory return precedes ``_epss_enrichment``) -- no EPSS
    consultation attempted at all. Review finding (follow-up pass): the
    original version asserted only output shape, which an implementation
    that DID open the cache but matched nothing would also satisfy -- the
    fail-sentinel on the cache read makes "never consulted" the thing
    actually proven."""

    def _fail_if_consulted(*_args, **_kwargs):
        pytest.fail("EPSS cache was consulted despite zero matchable candidates")

    monkeypatch.setattr(
        "pyforge.warden.engines.feeds.load_epss_scores", _fail_if_consulted
    )
    inventory = ResolvedInventory(components=(), resolved_scan_set=(MANIFEST,))
    result = OsvEngine(fail_on_kev=False, min_epss=0.5).run(tmp_path, inventory)
    assert result.findings == ()
    assert result.epss_data is None


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


def test_min_epss_forces_exit_1_regardless_of_cvss_tier(monkeypatch, tmp_path, capsys):
    """AC, end to end: PDOS-KEV-FIXTURE-0001 is MEDIUM-tier (warn by default
    -- 5.4 base score), yet with --min-epss 0.5 and a cache carrying its
    aliased CVE at score 0.7, the composed status is policy-violation and
    the exit code is 1 -- independent of the CVSS tier that would otherwise
    only warn. Uses vuln_kev_fail_on_kev_false's fixture (fail-on-kev off)
    so EPSS's own effect is isolated from KEV's default-on gate."""
    monkeypatch.setenv(
        feeds.FEED_CACHE_DIR_ENV_VAR, str(_epss_cache_with_match(tmp_path))
    )
    rc, out, err = run_scan(
        capsys, VULN_KEV_FAIL_ON_KEV_FALSE, "--min-epss", "0.5"
    )
    document = parse_report(out)

    assert rc == 1
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "policy-violation"
    matches = [f for f in document["findings"] if f["id"] == FIXTURE_FINDING_ID]
    assert len(matches) == 1
    finding = matches[0]
    assert finding["severity"]["tier"] == "medium"
    assert finding["epss"] == {"score": 0.7, "percentile": 0.9}
    assert document["epss_data"] is not None
    assert document["epss_data"]["max_age_ok"] is True
    assert err == ""


def test_min_epss_unset_leaves_cvss_only_gating_unaffected(monkeypatch, tmp_path, capsys):
    """With no --min-epss flag, the SAME EPSS-matching cache is never
    consulted -- every finding's epss stays null, and the MEDIUM-tier
    match's default warn/exit-0 CVSS-only gating survives untouched (no
    regression to pre-6.7 behavior). Review finding: renamed from a prior
    "byte identical" name that overclaimed a full byte-for-byte report
    comparison this test never actually performed -- it pins the specific
    fields that matter (status/exit/epss/epss_data), not the whole
    document."""
    monkeypatch.setenv(
        feeds.FEED_CACHE_DIR_ENV_VAR, str(_epss_cache_with_match(tmp_path))
    )
    rc, out, err = run_scan(capsys, VULN_KEV_FAIL_ON_KEV_FALSE)
    document = parse_report(out)

    assert rc == 0
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "warn"
    matches = [f for f in document["findings"] if f["id"] == FIXTURE_FINDING_ID]
    assert len(matches) == 1
    finding = matches[0]
    assert finding["epss"] is None
    assert document["epss_data"] is None
    assert err == ""


def test_epss_feed_absent_end_to_end_composes_indeterminate(
    monkeypatch, tmp_path, capsys
):
    """No usable EPSS cache while --min-epss is active composes
    indeterminate/exit 1 -- never a silent pass, even though the underlying
    CVSS match would otherwise only warn."""
    monkeypatch.setenv(feeds.FEED_CACHE_DIR_ENV_VAR, str(tmp_path / "no-such-cache"))
    rc, out, err = run_scan(
        capsys, VULN_KEV_FAIL_ON_KEV_FALSE, "--min-epss", "0.5"
    )
    document = parse_report(out)

    assert rc == 1
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "indeterminate"
    finding_ids = {f["id"] for f in document["findings"]}
    assert "indeterminate:epss-data-unavailable:epss-feed" in finding_ids
    assert document["epss_data"] is None
    assert err == ""


def test_epss_feed_stale_end_to_end_never_composes_a_pass(
    monkeypatch, tmp_path, capsys
):
    """Review finding (follow-up pass): the stale-feed path had only
    engine-level coverage -- this pins the full composition. A loadable but
    AGED cache while --min-epss is active raises the whole-axis
    epss-data-stale finding (indeterminate rung) AND still matches
    per-finding against the aged catalog, so the at/above-threshold score
    escalates to policy-violation -- which outranks indeterminate in the
    verdict ladder. Composed status: policy-violation, exit 1. Both
    outcomes are non-pass: exactly the "never a silent pass" promise, with
    the stale provenance visible in epss_data.max_age_ok."""
    import os
    import time

    cache_dir = _epss_cache_with_match(tmp_path)
    stale_mtime = time.time() - (feeds.DEFAULT_FEED_MAX_AGE_DAYS + 1) * 86400
    epss_path = feeds.epss_cache_path(cache_dir)
    os.utime(epss_path, (stale_mtime, stale_mtime))
    monkeypatch.setenv(feeds.FEED_CACHE_DIR_ENV_VAR, str(cache_dir))

    rc, out, err = run_scan(capsys, VULN_KEV_FAIL_ON_KEV_FALSE, "--min-epss", "0.5")
    document = parse_report(out)

    assert rc == 1
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "policy-violation"
    finding_ids = {f["id"] for f in document["findings"]}
    assert "indeterminate:epss-data-stale:epss-feed" in finding_ids
    matches = [f for f in document["findings"] if f["id"] == FIXTURE_FINDING_ID]
    assert len(matches) == 1
    assert matches[0]["epss"] == {"score": 0.7, "percentile": 0.9}
    assert document["epss_data"] is not None
    assert document["epss_data"]["max_age_ok"] is False
    assert err == ""


def test_toml_only_min_epss_drives_the_gate_end_to_end(monkeypatch, tmp_path, capsys):
    """Review finding (follow-up pass): --min-epss is a real TWO-mode flag,
    but every other E2E test in this suite activates it via the CLI --
    leaving the TOML mode proven only down to ``ConfigLoader.load``. Here
    ``min-epss = 0.5`` comes exclusively from the fixture project's own
    ``[tool.pyforge-warden]`` (no --min-epss argument anywhere), proving
    the TOML value alone drives consultation, stamping, and escalation to
    policy-violation/exit 1 through the very same engine wiring."""
    monkeypatch.setenv(
        feeds.FEED_CACHE_DIR_ENV_VAR, str(_epss_cache_with_match(tmp_path))
    )
    rc, out, err = run_scan(capsys, VULN_MIN_EPSS_TOML)
    document = parse_report(out)

    assert rc == 1
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "policy-violation"
    matches = [f for f in document["findings"] if f["id"] == FIXTURE_FINDING_ID]
    assert len(matches) == 1
    assert matches[0]["epss"] == {"score": 0.7, "percentile": 0.9}
    assert document["epss_data"] is not None
    assert document["epss_data"]["max_age_ok"] is True
    assert err == ""


def test_default_fail_on_kev_and_min_epss_both_active_on_the_same_finding(
    monkeypatch, tmp_path, capsys
):
    """Review finding: ``fail_on_kev`` defaults ``True``, so the realistic
    out-of-the-box combination once a user adds ``--min-epss`` is BOTH gates
    active simultaneously -- every other test in this suite deliberately
    isolates EPSS via ``vuln_kev_fail_on_kev_false``'s fixture. Uses
    ``PROJECTS/vuln_kev`` (``fail-on-kev`` left at its default) with one
    cache dir carrying both a KEV entry and an EPSS score for the SAME
    aliased CVE -- both gates escalate the same finding (idempotent, already
    the ceiling), and both provenance sections are populated."""
    cache_dir = tmp_path / "both-gates-cache"
    feeds.write_kev_cache(
        cache_dir,
        {"vulnerabilities": [{"cveID": FIXTURE_CVE, "dateAdded": "2026-01-01"}]},
    )
    feeds.write_epss_cache(
        cache_dir, {"scores": [{"cve": FIXTURE_CVE, "epss": 0.8, "percentile": 0.95}]}
    )
    monkeypatch.setenv(feeds.FEED_CACHE_DIR_ENV_VAR, str(cache_dir))

    rc, out, err = run_scan(capsys, VULN_KEV, "--min-epss", "0.5")
    document = parse_report(out)

    assert rc == 1
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "policy-violation"
    matches = [f for f in document["findings"] if f["id"] == FIXTURE_FINDING_ID]
    assert len(matches) == 1
    finding = matches[0]
    assert finding["kev"] is True
    assert finding["epss"] == {"score": 0.8, "percentile": 0.95}
    assert document["kev_data"] is not None
    assert document["epss_data"] is not None
    assert err == ""


# --- --min-epss argparse-layer usage errors ----------------------------------


def test_min_epss_rejects_a_negative_value_as_a_usage_error(capsys):
    """``--min-epss``'s own argparse ``type=`` callback validates at parse
    time -- mirrors ``test_max_lag_rejects_a_negative_value_as_a_usage_
    error``'s proof (test_scan_harness.py). Review finding: this flag's
    wiring had no direct test exercising the actual argparse layer -- every
    other test above calls ``ConfigLoader``/``EffectiveConfig`` with an
    already-parsed float, which would not catch a wrong ``type=`` or a
    misspelled flag string."""
    rc, out, err = run_scan(capsys, VULN_KEV_FAIL_ON_KEV_FALSE, "--min-epss", "-0.1")
    assert rc == 2
    assert out == ""
    assert "--min-epss" in err


def test_min_epss_rejects_an_out_of_range_value_as_a_usage_error(capsys):
    rc, out, err = run_scan(capsys, VULN_KEV_FAIL_ON_KEV_FALSE, "--min-epss", "1.5")
    assert rc == 2
    assert out == ""
    assert "--min-epss" in err


def test_min_epss_rejects_a_non_numeric_value_as_a_usage_error(capsys):
    rc, out, err = run_scan(
        capsys, VULN_KEV_FAIL_ON_KEV_FALSE, "--min-epss", "not-a-number"
    )
    assert rc == 2
    assert out == ""
    assert "--min-epss" in err
