"""library-futures — the S7 2027–2030 survival scorer.

cyclonedx-universe-inventory Wave D / S7. Pins: the py314 truth table, the
denominator-shrinking composite (no silent zeros; applicable-vs-absent), the
tier lattice meet (most-severe of base band + caps + floors), the EolClient
(injectable fetcher, TTL cache, offline stale-fallback, cache-miss→unknown),
the vuln subscore reading v_current_version_vulns (EPSS/CWE never scored),
and graph_depth_fanout present-when-resolved.

The LIVE endoflife.date fetch is the LOCAL wave; every test injects a fake
fetcher or a synthetic EolClient.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"


def _load(name: str):
    path = _SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def atlas_mod():
    return _load("conda_forge_atlas")


@pytest.fixture(scope="module")
def lf():
    return _load("library_futures")


NOW = int(time.time())
DAY = 86400


def _stub_eol(lf, **kw):
    """An EolClient whose lts_status returns a fixed dict (no fetch, no cache)."""
    default = {"lts_status": "none", "eol_date": None, "product_fully_eol": False,
               "pinned_line_eol_before_window": False, "source": "endoflife",
               "stale": False}
    default.update(kw)

    class _Stub:
        def lts_status(self, name, pinned_line=None):
            return dict(default)
    return _Stub()


@pytest.fixture
def db(tmp_path, atlas_mod):
    conn = atlas_mod.open_db(tmp_path / "cf_atlas.db")
    atlas_mod.init_schema(conn)
    # packages: (conda, pypi, version, upload_age_days, downloads_90d, license,
    #            archived, feedstock_bad, gh_status)
    rows = [
        ("healthy",   "healthy",  "2.0", 20,  500000, "MIT",          0, 0, None),
        ("vulnpkg",   "vulnpkg",  "1.0", 30,  10000,  "MIT",          0, 0, None),
        ("archived",  "archived", "0.9", 400, 100,    "MIT",          1, 0, None),
        ("silentpkg", "silentpkg","1.0", 600, 50,     "MIT",          0, 0, None),
        ("ripgrep",   None,       "14.0",25,  9000,   "MIT",          0, 0, None),  # non-Python
        ("nolicense", "nolicense","1.0", 20,  100,    None,           0, 0, None),
        ("compiled",  "compiled", "1.0", 20,  1000,   "BSD-3-Clause", 0, 0, None),
    ]
    for conda, pypi, ver, age, dl, lic, arch, bad, gh in rows:
        conn.execute(
            "INSERT INTO packages (conda_name, pypi_name, latest_conda_version, "
            "latest_conda_upload, downloads_90d, downloads_source, "
            "downloads_fetched_at, conda_license, feedstock_archived, "
            "feedstock_bad, gh_default_branch_status, latest_status, relationship, "
            "match_source, match_confidence) "
            "VALUES (?,?,?,?,?, 's3-parquet', ?, ?,?,?,?, 'active', 'test', "
            "'parselmouth', 'verified')",
            (conda, pypi, ver, NOW - age * DAY, dl, NOW, lic, arch, bad, gh))
    # version-download rows (cadence/adoption need these)
    for conda in ("healthy", "vulnpkg", "ripgrep", "compiled", "nolicense"):
        for i in range(4):
            conn.execute(
                "INSERT INTO package_version_downloads (conda_name, version, "
                "upload_unix, total_downloads) VALUES (?,?,?, 1000)",
                (conda, f"1.{i}", NOW - i * 10 * DAY))
    # v_current_version_vulns is query-time-correct: it LEFT JOINs
    # package_version_vulns on (conda_name, latest_conda_version). Seed a
    # per-version row for the current version — vulnpkg gets a KEV, the
    # healthy set a clean scan; nolicense stays unscanned (→ signal absent).
    for conda, ver, crit, high, kev in [
        ("vulnpkg", "1.0", 2, 1, 1),
        ("healthy", "2.0", 0, 0, 0),
        ("ripgrep", "14.0", 0, 0, 0),
        ("compiled", "1.0", 0, 0, 0),
    ]:
        conn.execute(
            "INSERT INTO package_version_vulns (conda_name, version, vuln_total, "
            "vuln_critical_affecting_version, vuln_high_affecting_version, "
            "vuln_kev_affecting_version, scanned_at) VALUES (?,?,?,?,?,?,?)",
            (conda, ver, crit + high, crit, high, kev, NOW))
    # pypi_universe + intelligence for the Python packages
    for name in ("healthy", "vulnpkg", "archived", "silentpkg", "nolicense",
                 "compiled"):
        conn.execute("INSERT INTO pypi_universe (pypi_name, last_serial, "
                     "fetched_at) VALUES (?, 1, ?)", (name, NOW))
    conn.execute(
        "INSERT INTO pypi_intelligence (pypi_name, activity_band, has_wheel, "
        "has_sdist, packaging_shape, latest_yanked, repo_url, docs_url, "
        "classifiers, requires_python, python_tags, json_fetched_at, "
        "cross_channel_at, in_bioconda) VALUES "
        "('healthy','hot',1,1,'pure-python',0,'https://x','https://d','[]',"
        "'>=3.9','[\"cp314-cp314\"]',?,?,1)", (NOW, NOW))
    conn.execute(
        "INSERT INTO pypi_intelligence (pypi_name, packaging_shape, has_sdist, "
        "requires_python, python_tags, classifiers, json_fetched_at) VALUES "
        "('compiled','c-extension',1,'>=3.8,<3.14','[\"cp311-cp311\"]','[]',?)",
        (NOW,))
    conn.execute(
        "INSERT INTO meta(key, value) VALUES ('built_at', ?)", (str(NOW),))
    conn.commit()
    yield conn
    conn.close()


# ── py314 readiness truth table ──────────────────────────────────────────────

class TestPy314:
    def test_cp314_tag_ready(self, lf):
        assert lf.py314_readiness('["cp314-cp314"]', "[]", ">=3.9", None,
                                  "pure-python", True) == "py314-ready"

    def test_classifier_ready(self, lf):
        assert lf.py314_readiness("[]", '["Programming Language :: Python :: 3.14"]',
                                  ">=3.9", None, "cython", True) == "py314-ready"

    def test_conda_py314_build_ready(self, lf):
        assert lf.py314_readiness("[]", "[]", ">=3.9", ["3.12", "3.14"],
                                  "c-extension", True) == "py314-ready"

    def test_pure_python_no_exclusion_likely(self, lf):
        assert lf.py314_readiness("[]", "[]", ">=3.9", None,
                                  "pure-python", True) == "py314-likely"

    def test_requires_python_upper_bound_not_ready(self, lf):
        assert lf.py314_readiness("[]", "[]", ">=3.8,<3.14", None,
                                  "pure-python", True) == "py314-not-ready"

    def test_compiled_no_cp314_not_ready(self, lf):
        assert lf.py314_readiness("[]", "[]", ">=3.8", None,
                                  "c-extension", True) == "py314-not-ready"

    def test_non_python_unknown(self, lf):
        assert lf.py314_readiness(None, None, None, None, None, False) == "unknown"


# ── composite / denominator ──────────────────────────────────────────────────

class TestComposite:
    def test_absent_shrinks_denominator_no_zero(self, lf):
        w = lf.DEFAULT_WEIGHTS
        # only two backbone signals present, both 100 → score 100 (not diluted)
        subs: dict = {s: (None, False) for s in w["signals"]}
        subs["vuln_posture"] = (100.0, True)
        subs["license_quality"] = (100.0, True)
        score, breakdown, absent, conf = lf.compute_composite(subs, w, is_py=False)
        assert score == 100.0
        assert "vuln_posture" not in absent and "upstream_freshness" in absent
        # python signals are NOT in the (non-python) applicable set → not absent
        assert "py_activity_band" not in absent

    def test_min_denominator_flips_confidence_low(self, lf):
        w = lf.DEFAULT_WEIGHTS
        subs: dict = {s: (None, False) for s in w["signals"]}
        subs["license_quality"] = (100.0, True)   # weight 8 of ~82 applicable
        score, _, _, conf = lf.compute_composite(subs, w, is_py=False)
        assert conf == "low"

    def test_all_absent_scores_none(self, lf):
        w = lf.DEFAULT_WEIGHTS
        subs: dict = {s: (None, False) for s in w["signals"]}
        score, _, _, _ = lf.compute_composite(subs, w, is_py=False)
        assert score is None


# ── EolClient ────────────────────────────────────────────────────────────────

_DJANGO = [
    {"cycle": "5.2", "lts": "2025-04-02", "eol": "2028-04-30", "latest": "5.2.1"},
    {"cycle": "4.2", "lts": "2023-04-03", "eol": "2026-04-07", "latest": "4.2.15"},
    {"cycle": "5.1", "lts": False, "eol": "2025-12-01"},
]


class TestEolClient:
    def test_ttl_hit_no_fetch(self, lf, tmp_path):
        cache = tmp_path / "eol.json"
        cache.write_text(json.dumps({"django": {"fetched_at": NOW, "cycles": _DJANGO}}))
        calls = []
        client = lf.EolClient(cache_path=cache, fetcher=lambda s: calls.append(s),
                              registry={}, now=NOW)
        res = client.lts_status("django", "5.2")
        assert calls == []                       # fresh cache → no fetch
        assert res["lts_status"] == "lts-supported" and res["eol_date"] == "2028-04-30"

    def test_expiry_triggers_refetch(self, lf, tmp_path):
        cache = tmp_path / "eol.json"
        cache.write_text(json.dumps(
            {"django": {"fetched_at": NOW - 30 * DAY, "cycles": []}}))
        calls = []

        def fetch(s):
            calls.append(s)
            return _DJANGO
        client = lf.EolClient(cache_path=cache, fetcher=fetch, registry={},
                              ttl_days=7, now=NOW)
        client.lts_status("django", "5.2")
        assert calls == ["django"]               # stale → refetched
        # and rewritten to cache
        assert json.loads(cache.read_text())["django"]["cycles"]

    def test_offline_stale_fallback(self, lf, tmp_path):
        cache = tmp_path / "eol.json"
        cache.write_text(json.dumps(
            {"django": {"fetched_at": NOW - 30 * DAY, "cycles": _DJANGO}}))
        client = lf.EolClient(cache_path=cache, fetcher=lambda s: None,
                              registry={}, now=NOW)
        res = client.lts_status("django", "5.2")
        assert res["stale"] is True              # served stale, no crash
        assert res["lts_status"] == "lts-supported"

    def test_cache_miss_offline_unknown(self, lf, tmp_path):
        client = lf.EolClient(cache_path=tmp_path / "none.json",
                              fetcher=lambda s: None, registry={}, now=NOW)
        res = client.lts_status("django", "5.2")
        assert res["lts_status"] == "unknown" and res["source"] == "cache-miss-offline"

    def test_django_52_lts_supported(self, lf, tmp_path):
        client = lf.EolClient(cache_path=tmp_path / "c.json",
                              fetcher=lambda s: _DJANGO, registry={}, now=NOW)
        res = client.lts_status("django", "5.2")
        assert res["lts_status"] == "lts-supported"
        assert res["eol_date"] == "2028-04-30"
        assert res["pinned_line_eol_before_window"] is False

    def test_django_42_eol_before_window(self, lf, tmp_path):
        client = lf.EolClient(cache_path=tmp_path / "c.json",
                              fetcher=lambda s: _DJANGO, registry={}, now=NOW)
        res = client.lts_status("django", "4.2")
        assert res["pinned_line_eol_before_window"] is True    # 2026 < 2027
        assert res["eol_date"] == "2026-04-07"


# ── signal scorers over the fixture DB ───────────────────────────────────────

class TestSignals:
    def test_vuln_reads_view_kev_penalized(self, lf, db):
        clean, present = lf._score_vuln_posture(db, "healthy", {}, None)
        assert present and clean == 100.0
        vuln, present = lf._score_vuln_posture(db, "vulnpkg", {}, None)
        # 100 - 2*30 - 1*10 - 1*25 = 5
        assert present and vuln == 5.0

    def test_vuln_absent_when_unscanned(self, lf, db):
        # nolicense has no vdb_scanned_at → absent, not a zero
        val, present = lf._score_vuln_posture(db, "nolicense", {}, None)
        assert present is False and val is None

    def test_license_absent_vs_osi(self, lf, db):
        pkg = lf._pkg_row(db, "healthy")
        val, present = lf._score_license_quality(db, "healthy", {}, pkg)
        assert present and val == 100.0
        pkg = lf._pkg_row(db, "nolicense")
        val, present = lf._score_license_quality(db, "nolicense", {}, pkg)
        assert present is False        # NULL license → absent, fail-safe

    def test_graph_depth_fanout_present_when_resolved(self, lf, db):
        val, present = lf._score_graph_depth_fanout(
            db, "healthy", {"depth": 0, "fanout": 3}, None)
        assert present and val is not None
        val, present = lf._score_graph_depth_fanout(db, "healthy", {}, None)
        assert present is False        # locked/unresolved row → absent


# ── tier lattice ─────────────────────────────────────────────────────────────

class TestTierLattice:
    def _mk(self, lf, db, conda, row=None, **eol):
        pkg = lf._pkg_row(db, conda)
        row = {"conda_name": conda, "ecosystem": "pypi", **(row or {})}
        return lf.derive_tier(db, 80.0, row, pkg, "py314-ready",
                              _stub_result(**eol), lf.DEFAULT_WEIGHTS)

    def test_keep_band_stays_keep(self, lf, db):
        tier, reasons, _ = self._mk(lf, db, "healthy")
        assert tier == "keep"

    def test_eol_before_window_floors_plan_migration(self, lf, db):
        tier, reasons, _ = self._mk(lf, db, "healthy",
                                    pinned_line_eol_before_window=True)
        assert tier == "plan-migration"           # NOT keep, per django-4.2

    def test_py314_not_ready_caps_watch(self, lf, db):
        pkg = lf._pkg_row(db, "healthy")
        row = {"conda_name": "healthy", "ecosystem": "pypi"}
        tier, _, _ = lf.derive_tier(db, 90.0, row, pkg, "py314-not-ready",
                                    _stub_result(), lf.DEFAULT_WEIGHTS)
        assert tier == "watch"

    def test_archived_with_alternatives_escalates_replace(self, lf, db):
        # give the archived pkg a healthier same-topic alternative to find
        db.execute("UPDATE packages SET conda_summary='json parser toolkit', "
                   "conda_keywords='[\"json\"]' WHERE conda_name='archived'")
        db.execute("UPDATE packages SET conda_summary='fast json parser toolkit', "
                   "conda_keywords='[\"json\"]', total_downloads=99999 "
                   "WHERE conda_name='healthy'")
        db.commit()
        pkg = lf._pkg_row(db, "archived")
        row = {"conda_name": "archived", "ecosystem": "pypi"}
        tier, reasons, alts = lf.derive_tier(db, 80.0, row, pkg, "py314-ready",
                                             _stub_result(), lf.DEFAULT_WEIGHTS)
        assert tier == "replace" and alts

    def test_most_severe_wins_over_multiple(self, lf, db):
        # archived floor (plan-migration) + product EOL floor → plan-migration;
        # score keep-band is overridden. ordering irrelevant.
        pkg = lf._pkg_row(db, "archived")   # archived=1
        row = {"conda_name": "archived", "ecosystem": "pypi"}
        tier, _, _ = lf.derive_tier(db, 95.0, row, pkg, "py314-ready",
                                    _stub_result(product_fully_eol=True),
                                    lf.DEFAULT_WEIGHTS)
        assert tier in ("plan-migration", "replace")   # never keep/watch

    def test_non_python_archived_floors_without_py314_cap(self, lf, db):
        pkg = lf._pkg_row(db, "ripgrep")    # no pypi_name → non-Python
        row = {"conda_name": "ripgrep", "ecosystem": "conda"}
        # even with py314-not-ready passed, non-Python must NOT trip the cap
        tier, reasons, _ = lf.derive_tier(db, 85.0, row, pkg, "py314-not-ready",
                                          _stub_result(), lf.DEFAULT_WEIGHTS)
        assert "py314" not in " ".join(reasons)


def _stub_result(**kw):
    d = {"lts_status": "none", "eol_date": None, "product_fully_eol": False,
         "pinned_line_eol_before_window": False, "stale": False}
    d.update(kw)
    return d


# ── end-to-end score_packages ────────────────────────────────────────────────

class TestScorePackages:
    def test_scores_matched_skips_add(self, lf, db):
        rows = [
            {"name": "healthy", "conda_name": "healthy", "ecosystem": "pypi",
             "bucket": "CURRENT", "pinned": "2.0", "signals_absent": []},
            {"name": "newpkg", "ecosystem": "pypi", "bucket": "ADD",
             "conda_name": None, "signals_absent": []},          # skipped (not on cf)
        ]
        out = lf.score_packages(db, rows, eol_client=_stub_eol(lf), now=NOW)
        assert [r["conda_name"] for r in out] == ["healthy"]
        assert out[0]["futures_tier"] in lf.TIERS
        assert out[0]["breakdown"]["vuln_posture"]["present"] is True

    def test_non_python_row_marks_python_enrichment_absent(self, lf, db):
        rows = [{"name": "ripgrep", "conda_name": "ripgrep", "ecosystem": "conda",
                 "bucket": "CURRENT", "pinned": "14.0", "signals_absent": []}]
        out = lf.score_packages(db, rows, eol_client=_stub_eol(lf), now=NOW)
        assert any("non-python" in s for s in out[0]["signals_absent"])
        # python-only signals excluded from the denominator, so still scored
        assert out[0]["futures_score"] is not None

    def test_healthy_python_keep(self, lf, db):
        rows = [{"name": "healthy", "conda_name": "healthy", "ecosystem": "pypi",
                 "bucket": "CURRENT", "pinned": "2.0", "signals_absent": [],
                 "freshness": {"verdict": "pass", "percentile": 0.9},
                 "weight": 3.0, "depth": 0, "fanout": 4}]
        out = lf.score_packages(db, rows,
                                eol_client=_stub_eol(lf, lts_status="lts-supported"),
                                now=NOW)
        assert out[0]["futures_tier"] == "keep"
        assert out[0]["py314_readiness"] == "py314-ready"
