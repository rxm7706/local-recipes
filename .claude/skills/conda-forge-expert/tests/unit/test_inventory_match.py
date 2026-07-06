"""inventory-match CLI — the S5 gap / version-lag matcher.

cyclonedx-universe-inventory Wave C. Pins the matcher contract: bucket
assignment via the three-way comparison (decision 3), mapping-tier
confidence passthrough (never-upgrade), fold-based resolution (G10/G98),
freshness percentile policy (dense/sparse), the deterministic policy gate,
weights sidecar, intake format detection, and CycloneDX annotation
(`cfe:gap_status` / `cfe:conda_purl`).

The local-wave surfaces (transitive resolution, channeldata probing, live
PyPI eligible sets, vuln thresholds) are tested offline via injected
fetchers / monkeypatched resolvers; their live network behavior is
exercised by the § Verification S5 end-to-end smoke.
"""
from __future__ import annotations

import importlib.util
import json
import sqlite3
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
def im():
    return _load("inventory_match")


@pytest.fixture(scope="module")
def sp_mod():
    return _load("scan_project")


NOW = int(time.time())


@pytest.fixture
def db(tmp_path, atlas_mod):
    """Fixture atlas exercising every bucket + confidence tier:

    numpy        exact pypi mapping, cf == upstream        → CURRENT / UPDATE-PIN
    pytorch      mapping under a DIFFERENT conda name       → mapping resolution
    olddep       cf 1.0 < upstream 2.0, history rows        → UPDATE-FEEDSTOCK + lag
    ripgrep      conda-only, github upstream                → non-Python matched row
    fs-googledrivefs  dotted pypi mapping                   → fold-based mapping hit
    coincide     match_source name_coincidence              → confidence passthrough
    weird        unparseable versions                       → version_comparison unreliable
    oldarch      feedstock_archived                         → flagged, still matched
    noupstream   conda pkg, no upstream_versions row        → signals_absent
    """
    conn = atlas_mod.open_db(tmp_path / "cf_atlas.db")
    atlas_mod.init_schema(conn)
    pkg_rows = [
        # (conda, pypi, version, source, confidence, license, archived)
        ("numpy",            "numpy",            "1.26.4", "parselmouth", "verified", "BSD-3-Clause", 0),
        ("pytorch",          "torch",            "2.2.0",  "parselmouth", "verified", "BSD-3-Clause", 0),
        ("olddep",           "olddep",           "1.0",    "parselmouth", "verified", "MIT",          0),
        ("ripgrep",          None,               "14.1.0", "none",        "n/a",      "MIT",          0),
        ("fs-googledrivefs", "fs.googledrivefs", "2.4.1",  "parselmouth", "verified", "MIT",          0),
        ("coincide",         "coincide",         "0.5",    "name_coincidence", "likely", "GPL-3.0-only", 0),
        ("weird",            "weird",            "abd",    "parselmouth", "verified", "MIT",          0),
        ("oldarch",          "oldarch",          "0.9",    "parselmouth", "verified", "MIT",          1),
        ("noupstream",       None,               "3.3",    "none",        "n/a",      None,           0),
        # the wasmtime trap: conda `wasmtime` maps to a DIFFERENT pypi name
        ("wasmtime",         "wasmtime-py",      "20.0",   "parselmouth", "verified", "Apache-2.0",   0),
        # conda names are exact identifiers: two fold-equivalent packages
        ("ruamel.yaml",      "ruamel.yaml",      "0.18.10", "parselmouth", "verified", "MIT",         0),
        ("ruamel_yaml",      None,               "0.15.80", "none",       "n/a",      "MIT",          0),
        # cf behind upstream with NO history rows (lag from current row only)
        ("behind-nohist",    "behind-nohist",    "1.0",    "parselmouth", "verified", "MIT",          0),
    ]
    for conda, pypi, ver, src, confidence, lic, archived in pkg_rows:
        conn.execute(
            "INSERT INTO packages (conda_name, pypi_name, latest_status, "
            "feedstock_archived, latest_conda_version, match_source, "
            "match_confidence, conda_license, relationship) "
            "VALUES (?,?, 'active', ?, ?, ?, ?, ?, 'test')",
            (conda, pypi, archived, ver, src, confidence, lic),
        )
    for name, source, version in [
        ("numpy",   "pypi",   "1.26.4"),
        ("pytorch", "pypi",   "2.2.0"),
        ("olddep",  "pypi",   "2.0"),
        ("ripgrep", "github", "14.1.0"),
        ("fs-googledrivefs", "pypi", "2.4.1"),
        ("weird",   "pypi",   "abd"),
        ("behind-nohist", "pypi", "2.0"),
    ]:
        conn.execute(
            "INSERT INTO upstream_versions (conda_name, source, version, url, fetched_at) "
            "VALUES (?,?,?, 'https://example.com', ?)", (name, source, version, NOW),
        )
    # olddep history: two releases past cf's 1.0, first seen 30 / 10 days ago
    for snap, ver in [(NOW - 30 * 86400, "1.5"), (NOW - 10 * 86400, "2.0"),
                      (NOW - 40 * 86400, "1.0")]:
        conn.execute(
            "INSERT INTO upstream_versions_history (snapshot_at, conda_name, source, version) "
            "VALUES (?, 'olddep', 'pypi', ?)", (snap, ver),
        )
    # numpy dense history: 12 versions for the freshness percentile
    for i in range(12):
        conn.execute(
            "INSERT INTO upstream_versions_history (snapshot_at, conda_name, source, version) "
            "VALUES (?, 'numpy', 'pypi', ?)", (NOW - i * 86400, f"1.{15 + i}.0"),
        )
    for name in ("numpy", "torch", "olddep", "fs.googledrivefs", "coincide",
                 "weird", "leftpadpy", "oldarch", "wasmtime", "wasmtime-py",
                 "behind-nohist"):
        conn.execute(
            "INSERT INTO pypi_universe (pypi_name, last_serial, fetched_at) "
            "VALUES (?, 1, ?)", (name, NOW),
        )
    # ADD-bucket enrichment for the unmapped universe name
    conn.execute(
        "INSERT INTO pypi_intelligence (pypi_name, latest_version, license_spdx, "
        "conda_forge_readiness, recommended_template, staged_recipes_pr_url, "
        "json_fetched_at) VALUES ('leftpadpy', '3.1.0', 'MIT', 87, "
        "'templates/python/recipe.yaml', "
        "'https://github.com/conda-forge/staged-recipes/pull/99999', ?)", (NOW,),
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES ('built_at', ?)", (str(NOW),),
    )
    conn.commit()
    yield conn
    conn.close()


def _dep(sp_mod, name, version, eco="pypi", manifest="test.txt", **extras):
    return sp_mod.Dep(name=name, version=version, ecosystem=eco,
                      manifest=manifest, extras=dict(extras))


def _match_one(im, db, dep_rows):
    inv = im.dedupe_deps(dep_rows)
    return im.match_inventory(db, inv)


# ── version comparison ladder ────────────────────────────────────────────────

class TestCmpVersions:
    def test_pep440(self, im):
        assert im.cmp_versions("1.2.0", "1.10.0") == (-1, True)
        assert im.cmp_versions("2.0.0", "2.0") == (0, True)
        assert im.cmp_versions("2.0.0rc1", "2.0.0") == (-1, True)

    def test_conda_epoch(self, im):
        assert im.cmp_versions("1!1.0", "2.0") == (1, True)

    def test_missing_side(self, im):
        assert im.cmp_versions(None, "1.0") == (None, True)
        assert im.cmp_versions("1.0", None) == (None, True)

    def test_string_equality_reliable(self, im):
        assert im.cmp_versions("abd", "abd") == (0, True)

    def test_string_inequality_unreliable(self, im):
        cmp, reliable = im.cmp_versions("abc", "abd")
        assert cmp == -1 and reliable is False


# ── freshness policy (dense / sparse / unknown) ──────────────────────────────

class TestFreshness:
    def test_dense_top_percentile_pass(self, im):
        eligible = [f"1.{i}" for i in range(12)]
        assert im.freshness_check("1.11", eligible)["verdict"] == "pass"

    def test_dense_old_pin_fail(self, im):
        eligible = [f"1.{i}" for i in range(12)]
        out = im.freshness_check("1.0", eligible)
        assert out["verdict"] == "fail"
        assert out["percentile"] == pytest.approx(1 / 12, abs=1e-4)

    def test_dense_boundary_exactly_top_20pct(self, im):
        # 10 eligible; pin at position 8 → percentile 0.8 → pass (>=)
        eligible = [f"2.{i}" for i in range(10)]
        assert im.freshness_check("2.7", eligible)["verdict"] == "pass"

    def test_sparse_last_minus_one_passes(self, im):
        assert im.freshness_check("2.0", ["1.0", "2.0", "3.0"])["verdict"] == "pass"

    def test_sparse_older_fails(self, im):
        assert im.freshness_check("1.0", ["1.0", "2.0", "3.0"])["verdict"] == "fail"

    def test_unknown_without_pin_or_history(self, im):
        assert im.freshness_check(None, ["1.0"])["verdict"] == "unknown"
        assert im.freshness_check("1.0", None)["verdict"] == "unknown"

    def test_unparseable_history_warns(self, im):
        out = im.freshness_check("zzz", ["abc", "abd", "zzz"])
        assert out["verdict"] == "warn"

    def test_history_provider_needs_two_versions(self, im, db):
        provider = im.history_version_provider(db)
        assert provider("ripgrep") is None          # single version
        assert "2.0" in provider("olddep")          # history + current
        assert "offline" in provider.basis


# ── bucket assignment (decision 3) ───────────────────────────────────────────

class TestBuckets:
    def test_current(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "numpy", "1.26.4")])
        assert rows[0]["bucket"] == "CURRENT"
        assert rows[0]["conda_name"] == "numpy"
        assert rows[0]["match_via"] == "mapping"
        assert rows[0]["match_confidence"] == "verified"
        assert rows[0]["version_comparison"] == "reliable"

    def test_update_pin(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "numpy", "1.24.0")])
        assert rows[0]["bucket"] == "UPDATE-PIN"
        assert rows[0]["cf_latest"] == "1.26.4"

    def test_pin_ahead_of_cf_is_current(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "numpy", "1.99.0")])
        assert rows[0]["bucket"] == "CURRENT"

    def test_update_feedstock_with_lag(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "olddep", "1.0")])
        r = rows[0]
        assert r["bucket"] == "UPDATE-FEEDSTOCK"
        assert r["upstream_version"] == "2.0"
        assert r["lag_releases"] == 2               # 1.5 + 2.0 newer than cf 1.0
        assert 29 <= r["lag_days"] <= 31            # earliest newer seen ~30 d ago
        assert r["pin_behind_cf"] is False          # pin == cf

    def test_mapping_under_different_conda_name(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "torch", "2.1.0")])
        r = rows[0]
        assert r["conda_name"] == "pytorch"
        assert r["bucket"] == "UPDATE-PIN"
        assert r["conda_purl"] == "pkg:conda/pytorch@2.2.0?channel=conda-forge"

    def test_dotted_fold_mapping(self, im, db, sp_mod):
        # G98/G10: the dep spelling fs_googledrivefs folds onto the stored
        # mapping pypi_name fs.googledrivefs
        rows = _match_one(im, db, [_dep(sp_mod, "fs_googledrivefs", "2.4.1")])
        assert rows[0]["conda_name"] == "fs-googledrivefs"
        assert rows[0]["bucket"] == "CURRENT"

    def test_conda_dep_direct(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "ripgrep", "14.1.0", eco="conda")])
        r = rows[0]
        assert r["bucket"] == "CURRENT"
        assert r["match_via"] == "conda_name"
        assert r["upstream_source"] == "github"     # non-Python w/ GitHub upstream

    def test_other_ecosystem_bare_fold(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "ripgrep", "14.1.0", eco="cargo")])
        assert rows[0]["match_via"] == "g10_bare"
        assert rows[0]["match_confidence"] == "likely"

    def test_add_with_enrichment(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "leftpadpy", "3.0.0")])
        r = rows[0]
        assert r["bucket"] == "ADD"
        assert r["conda_forge_readiness"] == 87
        assert r["recommended_template"] == "templates/python/recipe.yaml"
        assert "staged-recipes/pull/99999" in r["staged_recipes_pr_url"]
        assert r["upstream_version"] == "3.1.0"     # PyPI latest as upstream

    def test_unknown_pypi_not_in_universe(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "ghost-package", "1.0")])
        assert rows[0]["bucket"] == "UNKNOWN"
        assert "pypi_universe" in rows[0]["signals_absent"]

    def test_add_nonpypi(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "left-pad", "1.3.0", eco="npm")])
        assert rows[0]["bucket"] == "ADD-NONPYPI"

    def test_unknown_conda_dep_never_guessed_into_add(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "bioconda-thing", "1.0", eco="conda")])
        assert rows[0]["bucket"] == "UNKNOWN"
        assert "conda_forge_presence" in rows[0]["signals_absent"]

    def test_name_coincidence_confidence_never_upgraded(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "coincide", "0.5")])
        assert rows[0]["match_source"] == "name_coincidence"
        assert rows[0]["match_confidence"] == "likely"

    def test_unreliable_comparison_flagged(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "weird", "abc")])
        r = rows[0]
        assert r["version_comparison"] == "unreliable"
        assert r["bucket"] == "UPDATE-PIN"          # abc < abd lexicographically

    def test_archived_feedstock_flagged(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "oldarch", "0.9")])
        assert rows[0]["feedstock_archived"] is True
        assert rows[0]["bucket"] == "CURRENT"

    def test_no_upstream_row_signals_absent(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "noupstream", "3.3", eco="conda")])
        assert "upstream_freshness" in rows[0]["signals_absent"]
        assert rows[0]["bucket"] == "CURRENT"       # inv == cf still decidable

    def test_unpinned_dep_current_when_cf_current(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "numpy", None)])
        assert rows[0]["pin_kind"] == "unpinned"
        assert rows[0]["bucket"] == "CURRENT"

    def test_wasmtime_trap_bare_fold_refused(self, im, db, sp_mod):
        """A pypi dep whose bare fold hits a conda package already mapped
        to a DIFFERENT pypi name must NOT match it (mapping_gap G10) —
        it falls through to the ADD/universe path."""
        rows = _match_one(im, db, [_dep(sp_mod, "wasmtime", "20.0")])
        r = rows[0]
        assert r["conda_name"] is None
        assert r["bucket"] == "ADD"          # pypi `wasmtime` is in the universe

    def test_conda_exact_name_beats_fold(self, im, db, sp_mod):
        # ruamel_yaml and ruamel.yaml are two DIFFERENT conda packages
        rows = _match_one(im, db, [_dep(sp_mod, "ruamel_yaml", "0.15.80", eco="conda")])
        r = rows[0]
        assert r["conda_name"] == "ruamel_yaml"
        assert r["match_confidence"] == "exact"
        assert r["bucket"] == "CURRENT"

    def test_conda_fold_fallback_flagged_likely(self, im, db, sp_mod):
        # no exact conda name → fold fallback is a flagged guess, not exact
        rows = _match_one(im, db, [_dep(sp_mod, "fs.googledrivefs", "2.4.1", eco="conda")])
        r = rows[0]
        assert r["conda_name"] == "fs-googledrivefs"
        assert r["match_via"] == "conda_fold"
        assert r["match_confidence"] == "likely"

    def test_other_eco_python_package_is_name_coincidence(self, im, db, sp_mod):
        # a cargo dep matching a conda package that maps to PyPI is
        # probably a different artifact of the same name
        rows = _match_one(im, db, [_dep(sp_mod, "numpy", "1.26.4", eco="cargo")])
        assert rows[0]["match_confidence"] == "name_coincidence"

    def test_update_feedstock_lag_without_history(self, im, db, sp_mod):
        # current upstream row proves lag >= 1 even with no history snapshot
        rows = _match_one(im, db, [_dep(sp_mod, "behind-nohist", "1.0")])
        r = rows[0]
        assert r["bucket"] == "UPDATE-FEEDSTOCK"
        assert r["lag_releases"] == 1
        assert r["lag_days"] is None


# ── dedupe ───────────────────────────────────────────────────────────────────

class TestDedupe:
    def test_fold_equivalent_names_merge(self, im, sp_mod):
        rows = im.dedupe_deps([
            _dep(sp_mod, "Requests", None, manifest="pyproject.toml"),
            _dep(sp_mod, "requests", "2.31.0", manifest="uv.lock"),
        ])
        assert len(rows) == 1
        assert rows[0]["pinned"] == "2.31.0"        # pinned occurrence wins
        assert set(rows[0]["manifests"]) == {"pyproject.toml", "uv.lock"}

    def test_conda_and_pypi_never_merge(self, im, sp_mod):
        rows = im.dedupe_deps([
            _dep(sp_mod, "numpy", "1.26.4", eco="conda"),
            _dep(sp_mod, "numpy", "1.26.4", eco="pypi"),
        ])
        assert len(rows) == 2

    def test_locked_resolution_wins(self, im, sp_mod):
        rows = im.dedupe_deps([
            _dep(sp_mod, "numpy", None, resolution="direct"),
            _dep(sp_mod, "numpy", "1.26.4", resolution="locked"),
        ])
        assert rows[0]["resolution"] == "locked"

    def test_conda_fold_variants_never_merge(self, im, sp_mod):
        rows = im.dedupe_deps([
            _dep(sp_mod, "ruamel.yaml", "0.18.10", eco="conda"),
            _dep(sp_mod, "ruamel_yaml", "0.15.80", eco="conda"),
        ])
        assert len(rows) == 2               # exact conda identity, no folding

    def test_pin_conflict_recorded(self, im, sp_mod):
        rows = im.dedupe_deps([
            _dep(sp_mod, "numpy", "1.24.0", manifest="a.lock"),
            _dep(sp_mod, "numpy", "1.26.4", manifest="b.lock"),
        ])
        assert rows[0]["pinned"] == "1.24.0"           # first wins
        assert rows[0]["pin_conflict"] == ["1.26.4"]   # conflict surfaced

    def test_range_bound_never_a_pin(self, im, sp_mod):
        # extras op from requirements/pyproject parsers demotes to constraint
        rows = im.dedupe_deps([_dep(sp_mod, "requests", "2.0", op=">=")])
        assert rows[0]["pinned"] is None
        assert rows[0]["constraint"] == ">=2.0"
        assert rows[0]["pin_kind"] == "range"
        # raw spec strings (pixi.toml-style) demote by value
        rows = im.dedupe_deps([_dep(sp_mod, "numpy", ">=1.0,<2")])
        assert rows[0]["pinned"] is None and rows[0]["pin_kind"] == "range"
        # explicit == survives as exact
        rows = im.dedupe_deps([_dep(sp_mod, "numpy", "==1.26.4")])
        assert rows[0]["pinned"] == "1.26.4" and rows[0]["pin_kind"] == "exact"

    def test_policy_tier_propagates(self, im, sp_mod):
        rows = im.dedupe_deps([_dep(sp_mod, "attrs", "25.3.0", policy_tier="future")])
        assert rows[0]["policy_tier"] == "future"
        # most-supported tier wins when a dep appears in mixed sources
        rows = im.dedupe_deps([
            _dep(sp_mod, "attrs", "25.3.0", policy_tier="future", manifest="pdm.lock"),
            _dep(sp_mod, "attrs", None, policy_tier="policy", manifest="pyproject.toml"),
        ])
        assert rows[0]["policy_tier"] == "policy"


# ── weights + policy gate ────────────────────────────────────────────────────

class TestPolicyGate:
    def test_weights_csv_and_json(self, im, tmp_path):
        c = tmp_path / "w.csv"
        c.write_text("name,weight\nNumPy,5\ntorch,2.5\n")
        w = im.load_weights(c)
        assert w["numpy"] == 5.0 and w["torch"] == 2.5
        j = tmp_path / "w.json"
        j.write_text('{"ruamel.yaml": 3}')
        assert im.load_weights(j)["ruamel-yaml"] == 3.0   # fold-keyed

    def test_bucket_ceiling_violation(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "leftpadpy", "3.0.0")])
        out = im.evaluate_policy(rows, {"buckets": {"max": {"ADD": 0}}})
        assert out["pass"] is False
        assert out["violations"][0]["check"] == "buckets.max.ADD"
        assert out["violations"][0]["rows"] == ["leftpadpy"]

    def test_freshness_gate_counts_unknown_when_fail_closed(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "torch", "2.1.0")])
        # torch/pytorch has no history → verdict unknown; fail-closed default
        out = im.evaluate_policy(rows, {"freshness": {"max_fail": 0}})
        assert out["pass"] is False
        out2 = im.evaluate_policy(
            rows, {"freshness": {"max_fail": 0}, "block_on_missing_data": False})
        assert out2["pass"] is True

    def test_freshness_gate_dense_history_pass(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "numpy", "1.26.4")])
        assert rows[0]["freshness"]["verdict"] == "pass"
        out = im.evaluate_policy(rows, {"freshness": {"max_fail": 0}})
        assert out["pass"] is True

    def test_license_deny(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "coincide", "0.5")])
        out = im.evaluate_policy(rows, {"license": {"deny": ["GPL-3.0-only"]}})
        assert out["pass"] is False
        assert out["violations"][0]["check"] == "license.deny"

    def test_license_require_present(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "noupstream", "3.3", eco="conda")])
        out = im.evaluate_policy(rows, {"license": {"require_present": True}})
        assert out["pass"] is False

    def test_vuln_threshold_gate(self, im, db, sp_mod):
        db.execute("UPDATE packages SET vuln_critical_affecting_current = 2, "
                   "vuln_high_affecting_current = 0, "
                   "vuln_kev_affecting_current = 0 WHERE conda_name = 'numpy'")
        rows = _match_one(im, db, [_dep(sp_mod, "numpy", "1.26.4")])
        assert rows[0]["vulns"]["critical"] == 2
        out = im.evaluate_policy(rows, {"vulns": {"max_critical": 0},
                                        "block_on_missing_data": False})
        assert out["pass"] is False
        assert out["violations"][0]["check"] == "vulns.max_critical"

    def test_vuln_missing_rollups_fail_closed(self, im, db, sp_mod):
        # fixture packages carry NULL rollups → signals_absent: vuln_rollups;
        # with block_on_missing_data (default true) they count as offending.
        rows = _match_one(im, db, [_dep(sp_mod, "torch", "2.2.0")])
        assert "vuln_rollups" in rows[0]["signals_absent"]
        out = im.evaluate_policy(rows, {"vulns": {"max_critical": 0}})
        assert out["pass"] is False
        assert "missing" in out["violations"][0]["note"]
        relaxed = im.evaluate_policy(rows, {"vulns": {"max_critical": 0},
                                            "block_on_missing_data": False})
        assert relaxed["pass"] is True

    def test_vuln_unknown_key_is_schema_violation(self, im):
        out = im.evaluate_policy([], {"vulns": {"max_criticall": 0}})
        assert out["pass"] is False
        assert out["violations"][0]["check"] == "policy.schema"

    def test_violation_rows_weight_ordered(self, im, db, sp_mod):
        inv = im.dedupe_deps([
            _dep(sp_mod, "numpy", "1.24.0"),
            _dep(sp_mod, "torch", "2.1.0"),
        ])
        rows = im.match_inventory(db, inv, weights={"torch": 9.0, "numpy": 1.0})
        out = im.evaluate_policy(rows, {"buckets": {"max": {"UPDATE-PIN": 0}}})
        assert out["violations"][0]["rows"] == ["torch", "numpy"]

    def test_policy_toml(self, im, tmp_path):
        p = tmp_path / "policy.toml"
        p.write_text("[freshness]\nmax_fail = 0\n")
        assert im.load_policy(p) == {"freshness": {"max_fail": 0}}

    def test_policy_schema_unknown_key_fails_closed(self, im):
        out = im.evaluate_policy([], {"freshnesss": {"max_fail": 0}})
        assert out["pass"] is False
        assert out["violations"][0]["check"] == "policy.schema"
        assert "freshnesss" in out["violations"][0]["note"]

    def test_policy_schema_misspelled_bucket_fails_closed(self, im):
        out = im.evaluate_policy([], {"buckets": {"max": {"add": 0}}})
        assert out["pass"] is False
        assert "add" in out["violations"][0]["note"]

    def test_policy_schema_freshness_missing_max_fail(self, im):
        out = im.evaluate_policy([], {"freshness": {"max_failures": 0}})
        assert out["pass"] is False

    def test_policy_schema_deny_must_be_list(self, im):
        out = im.evaluate_policy([], {"license": {"deny": "GPL-3.0-only"}})
        assert out["pass"] is False

    def test_license_deny_hits_compound_expression(self, im, db, sp_mod):
        # coincide carries GPL-3.0-only; a compound string must also trip
        rows = _match_one(im, db, [_dep(sp_mod, "coincide", "0.5")])
        rows[0]["conda_license"] = "GPL-3.0-only OR MIT"
        out = im.evaluate_policy(rows, {"license": {"deny": ["GPL-3.0-only"]}})
        assert out["pass"] is False


# ── intake: format detection + resolution stamping ───────────────────────────

class TestIntake:
    def test_detect_canonical_filenames(self, im, tmp_path):
        (tmp_path / "uv.lock").write_text("")
        assert im.detect_format(tmp_path / "uv.lock") == "uv-lock"

    def test_detect_pip_freeze_text(self, im, tmp_path):
        p = tmp_path / "deps.txt"
        p.write_text("certifi==2024.2.2\nrequests==2.31.0\n")
        assert im.detect_format(p) == "pip"

    def test_detect_conda_list_text(self, im, tmp_path):
        p = tmp_path / "env.txt"
        p.write_text("# packages in environment at /opt/conda:\nnumpy  1.26.4  py312  conda-forge\n")
        assert im.detect_format(p) == "conda-list"

    def test_detect_conda_export_text(self, im, tmp_path):
        p = tmp_path / "export.txt"
        p.write_text("python=3.12.3=hab00c5b_0\n")
        assert im.detect_format(p) == "conda-list"

    def test_detect_cyclonedx_json(self, im, tmp_path):
        p = tmp_path / "some.json"
        p.write_text(json.dumps({"bomFormat": "CycloneDX", "specVersion": "1.6"}))
        assert im.detect_format(p) == "cyclonedx"

    def test_manifest_rows_flagged_direct(self, im, tmp_path):
        p = tmp_path / "requirements.txt"
        p.write_text("numpy==1.24.0\n")
        deps, labels, warnings = im.load_inventory([p], None)
        assert deps[0].extras["resolution"] == "direct"   # bare manifest
        assert not warnings

    def test_lockfile_rows_flagged_locked(self, im, tmp_path):
        p = tmp_path / "freeze.txt"
        p.write_text("numpy==1.26.4\n")
        deps, _, _ = im.load_inventory([p], "pip")
        assert deps[0].extras["resolution"] == "locked"

    def test_unrecognized_input_warns(self, im, tmp_path):
        p = tmp_path / "mystery.dat"
        p.write_text("???")
        deps, _, warnings = im.load_inventory([p], None)
        assert not deps and warnings

    def test_directory_discovery_lock_over_manifest(self, im, tmp_path):
        (tmp_path / "pixi.toml").write_text("[dependencies]\nnumpy = '1.*'\n")
        (tmp_path / "pixi.lock").write_text(
            "packages:\n"
            "- conda: https://conda.anaconda.org/conda-forge/linux-64/numpy-1.26.4-py312_0.conda\n"
        )
        deps, labels, _ = im.load_inventory([tmp_path], None)
        assert all(d.manifest != "pixi.toml" for d in deps)
        assert any(d.name == "numpy" and d.version == "1.26.4" for d in deps)


# ── end-to-end run() + outputs ───────────────────────────────────────────────

class TestRunAndOutputs:
    def test_run_counts_and_report(self, im, db, sp_mod):
        deps = [
            _dep(sp_mod, "numpy", "1.24.0"),
            _dep(sp_mod, "olddep", "1.0"),
            _dep(sp_mod, "leftpadpy", "3.0.0"),
            _dep(sp_mod, "left-pad", "1.3.0", eco="npm"),
        ]
        result = im.run(db, deps, ["fixture"], policy={"buckets": {"max": {"ADD": 0}}})
        assert result["counts"]["UPDATE-PIN"] == 1
        assert result["counts"]["UPDATE-FEEDSTOCK"] == 1
        assert result["counts"]["ADD"] == 1
        assert result["counts"]["ADD-NONPYPI"] == 1
        assert result["policy"]["pass"] is False
        report = im.render_report(result)
        assert "UPDATE-FEEDSTOCK" in report
        assert "lag 2 releases" in report
        assert "verdict: FAIL" in report
        assert "upstream_versions_history" in result["freshness_basis"]

    def test_sbom_annotation(self, im, db, sp_mod, tmp_path):
        bom = {
            "bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1,
            "components": [
                {"type": "library", "name": "numpy", "version": "1.24.0",
                 "purl": "pkg:pypi/numpy@1.24.0"},
                {"type": "library", "name": "unrelated", "version": "1.0",
                 "purl": "pkg:npm/unrelated@1.0"},
            ],
        }
        bom_path = tmp_path / "in.cdx.json"
        bom_path.write_text(json.dumps(bom))
        deps = im.FORMAT_PARSERS["cyclonedx"](bom_path)
        result = im.run(db, deps, [str(bom_path)])
        annotated = im.annotate_sbom(bom_path, result["rows"], result["built_at"])
        numpy_props = {p["name"]: p["value"]
                       for p in annotated["components"][0]["properties"]}
        assert numpy_props["cfe:gap_status"] == "UPDATE-PIN"
        assert numpy_props["cfe:conda_purl"] == "pkg:conda/numpy@1.26.4?channel=conda-forge"
        meta_props = {p["name"] for p in annotated["metadata"]["properties"]}
        assert "cfe:atlas_built_at" in meta_props

    def test_annotate_rejects_non_cyclonedx(self, im, tmp_path):
        p = tmp_path / "x.json"
        p.write_text('{"spdxVersion": "SPDX-2.3"}')
        with pytest.raises(ValueError):
            im.annotate_sbom(p, [], "0")

    def test_injectable_version_provider(self, im, db, sp_mod):
        def provider(conda_name):
            return [f"9.{i}" for i in range(12)]
        provider.basis = "injected-test"
        inv = im.dedupe_deps([_dep(sp_mod, "numpy", "1.26.4")])
        rows = im.match_inventory(db, inv, version_provider=provider)
        assert rows[0]["freshness"]["verdict"] == "fail"   # 1.26.4 below all 9.x

    def test_annotate_nonpypi_purl_component(self, im, db, sp_mod, tmp_path):
        """ADD-NONPYPI rows (npm/cargo purls) must annotate too, and a
        pkg:npm component must never inherit a same-named PyPI row."""
        bom = {
            "bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1,
            "components": [
                {"type": "library", "name": "left-pad", "version": "1.3.0",
                 "purl": "pkg:npm/left-pad@1.3.0"},
                {"type": "library", "name": "numpy", "version": "1.0",
                 "purl": "pkg:npm/numpy@1.0"},
            ],
        }
        bom_path = tmp_path / "npm.cdx.json"
        bom_path.write_text(json.dumps(bom))
        deps = im.FORMAT_PARSERS["cyclonedx"](bom_path)
        result = im.run(db, deps, [str(bom_path)])
        annotated = im.annotate_sbom(bom_path, result["rows"], result["built_at"])
        lp_props = {p["name"]: p["value"]
                    for p in annotated["components"][0]["properties"]}
        assert lp_props["cfe:gap_status"] == "ADD-NONPYPI"
        # npm numpy gets ITS row (name_coincidence conda match), not the
        # pypi numpy row's verdict via a name fallback
        np_row = next(r for r in result["rows"] if r["ecosystem"] == "npm"
                      and r["name"] == "numpy")
        np_props = {p["name"]: p["value"]
                    for p in annotated["components"][1]["properties"]}
        assert np_props["cfe:gap_status"] == np_row["bucket"]

    def test_usage_errors_exit_1_not_2(self, im, monkeypatch):
        # exit 2 is RESERVED for the policy verdict; argparse usage errors
        # (bad flag, no inputs) must exit 1
        for argv in (["inventory-match", "--nonsense"], ["inventory-match"]):
            monkeypatch.setattr(sys, "argv", argv)
            with pytest.raises(SystemExit) as exc:
                im.main()
            assert exc.value.code == 1

    def test_add_yanked_latest_flagged(self, im, db, sp_mod):
        db.execute(
            "INSERT INTO pypi_universe (pypi_name, last_serial, fetched_at) "
            "VALUES ('yankedpkg', 1, ?)", (NOW,))
        db.execute(
            "INSERT INTO pypi_intelligence (pypi_name, latest_version, "
            "latest_yanked, json_fetched_at) VALUES ('yankedpkg', '2.0', 1, ?)",
            (NOW,))
        db.commit()
        rows = _match_one(im, db, [_dep(sp_mod, "yankedpkg", "1.0")])
        assert rows[0]["bucket"] == "ADD"
        assert rows[0]["upstream_yanked"] is True


# ── local wave (Wave C): live providers + transitive resolver ────────────────
# All offline: fetchers/resolvers are injected or monkeypatched; the live
# network behavior is exercised by the § Verification S5 end-to-end smoke.

class TestLiveCfCheck:
    def test_add_row_recovered_as_atlas_stale(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "leftpadpy", "3.1.0")])
        assert rows[0]["bucket"] == "ADD"
        stats = im.apply_live_cf_check(rows, {"leftpadpy": {"version": "3.1.0"}})
        assert stats == {"checked": 1, "recovered": 1, "confirmed_absent": 0}
        assert rows[0]["bucket"] == "CURRENT"
        assert rows[0]["atlas_stale"] is True
        assert rows[0]["conda_name"] == "leftpadpy"
        assert rows[0]["live_cf_check"] == "present"
        assert "?channel=conda-forge" in rows[0]["conda_purl"]

    def test_add_row_recovered_update_pin(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "leftpadpy", "2.0")])
        im.apply_live_cf_check(rows, {"leftpadpy": {"version": "3.1.0"}})
        assert rows[0]["bucket"] == "UPDATE-PIN"

    def test_absence_confirmed(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "leftpadpy", "3.1.0")])
        stats = im.apply_live_cf_check(rows, {"unrelated": {"version": "1.0"}})
        assert stats["confirmed_absent"] == 1
        assert rows[0]["bucket"] == "ADD"
        assert rows[0]["live_cf_check"] == "absent-confirmed"

    def test_conda_unknown_recovered_exact(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "brandnew", "1.0", eco="conda")])
        assert rows[0]["bucket"] == "UNKNOWN"
        im.apply_live_cf_check(rows, {"brandnew": {"version": "1.0"}})
        assert rows[0]["bucket"] == "CURRENT"
        assert rows[0]["match_confidence"] == "exact"
        assert rows[0]["match_via"] == "channeldata_live"

    def test_matched_rows_untouched(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "numpy", "1.26.4")])
        stats = im.apply_live_cf_check(rows, {"numpy": {"version": "99.0"}})
        assert stats["checked"] == 0
        assert rows[0]["cf_latest"] == "1.26.4"


class TestLiveEligibleProvider:
    def test_yanked_and_requires_python_filtered(self, im, db):
        releases = {
            "1.0": [{"requires_python": ">=3.8"}],
            "1.1": [{}],
            "2.0": [{"yanked": True}],                    # fully yanked → out
            "3.0": [{"requires_python": ">=3.99"}],       # excludes runtime → out
            "4.0": [],                                    # no artifacts → out
        }
        provider = im.live_pypi_version_provider(
            db, py_version="3.12.0", fetch=lambda name: releases)
        assert provider("numpy") == ["1.0", "1.1"]
        assert provider.stats["live"] == 1

    def test_fallback_on_fetch_failure(self, im, db):
        provider = im.live_pypi_version_provider(
            db, py_version="3.12.0", fetch=lambda name: None)
        got = provider("numpy")   # numpy has 12 history versions in fixture
        assert got is not None and len(got) >= 12
        assert provider.stats["fallback"] == 1

    def test_no_pypi_identity_uses_fallback(self, im, db):
        provider = im.live_pypi_version_provider(
            db, py_version="3.12.0",
            fetch=lambda name: (_ for _ in ()).throw(AssertionError("no fetch")))
        assert provider("ripgrep") is None  # no mapping, no dense history
        assert provider.stats["fallback"] == 1


class TestPipGraph:
    REPORT = {
        "environment": {"python_version": "3.12"},
        "install": [
            {"requested": True,
             "metadata": {"name": "rootpkg", "version": "1.0",
                          "requires_dist": ["midpkg>=1", "winonly; sys_platform == 'win32'"]}},
            {"metadata": {"name": "midpkg", "version": "2.0",
                          "requires_dist": ["leafpkg"]}},
            {"metadata": {"name": "leafpkg", "version": "0.3",
                          "requires_dist": None}},
            {"metadata": {"name": "winonly", "version": "9.9",
                          "requires_dist": []}},
        ],
    }

    def test_depth_fanout_and_marker_exclusion(self, im):
        nodes = im.derive_pip_graph(self.REPORT)
        assert nodes["rootpkg"]["depth"] == 0
        assert nodes["midpkg"]["depth"] == 1
        assert nodes["leafpkg"]["depth"] == 2
        # the win32 marker edge is excluded on this platform → unreachable
        assert nodes["winonly"]["depth"] is None
        assert nodes["rootpkg"]["fanout"] == 1
        assert nodes["leafpkg"]["fanout"] == 0

    def test_resolve_upgrades_and_adds_transitive(self, im, sp_mod, monkeypatch):
        monkeypatch.setattr(im, "_pip_report", lambda specs, warnings: self.REPORT)
        deps = [_dep(sp_mod, "rootpkg", None, manifest="requirements.txt",
                     resolution="direct", policy_tier="policy")]
        warnings: list[str] = []
        stats = im.resolve_transitive(deps, warnings)
        assert stats["pypi_upgraded"] == 1 and stats["added"] == 3
        assert deps[0].extras["resolution"] == "resolved"
        assert deps[0].version == "1.0"          # resolver-chosen version
        assert deps[0].extras["fanout"] == 1
        added = {d.name: d for d in deps[1:]}
        assert set(added) == {"midpkg", "leafpkg", "winonly"}
        assert added["midpkg"].extras["via"] == "transitive"
        assert added["midpkg"].extras["policy_tier"] == "policy"
        assert not warnings

    def test_resolver_failure_keeps_direct(self, im, sp_mod, monkeypatch):
        monkeypatch.setattr(im, "_pip_report", lambda specs, warnings:
                            warnings.append("pip resolver failed") or None)
        deps = [_dep(sp_mod, "rootpkg", None, resolution="direct")]
        warnings: list[str] = []
        stats = im.resolve_transitive(deps, warnings)
        assert stats == {"pypi_upgraded": 0, "conda_upgraded": 0, "added": 0}
        assert deps[0].extras["resolution"] == "direct"
        assert warnings


class TestCondaGraph:
    class _Rec:
        def __init__(self, name, version, depends):
            self.name = type("N", (), {"normalized": name})()
            self.version = version
            self.depends = depends

    def test_depth_and_fanout(self, im):
        records = [
            self._Rec("app", "1.0", ["libfoo >=2", "python >=3.10"]),
            self._Rec("libfoo", "2.1", ["libbar"]),
            self._Rec("libbar", "0.9", []),
            self._Rec("python", "3.12.4", []),
        ]
        nodes = im.derive_conda_graph(records, {"app"})
        assert nodes["app"]["depth"] == 0
        assert nodes["libfoo"]["depth"] == 1
        assert nodes["libbar"]["depth"] == 2
        assert nodes["app"]["fanout"] == 2

    def test_conda_solve_failure_keeps_direct(self, im, sp_mod, monkeypatch):
        monkeypatch.setattr(im, "_conda_solve_records", lambda specs, warnings:
                            warnings.append("conda solve failed") or None)
        deps = [_dep(sp_mod, "somepkg", None, eco="conda", resolution="direct")]
        warnings: list[str] = []
        im.resolve_transitive(deps, warnings)
        assert deps[0].extras["resolution"] == "direct"
        assert warnings


class TestDedupResolution:
    def test_resolved_beats_direct_and_graph_fields_carry(self, im, sp_mod):
        rows = im.dedupe_deps([
            _dep(sp_mod, "numpy", None, resolution="direct"),
            _dep(sp_mod, "numpy", "1.26.4", resolution="resolved",
                 depth=2, fanout=5),
        ])
        assert rows[0]["resolution"] == "resolved"
        assert rows[0]["depth"] == 2 and rows[0]["fanout"] == 5

    def test_locked_still_wins_over_resolved(self, im, sp_mod):
        rows = im.dedupe_deps([
            _dep(sp_mod, "numpy", "1.26.4", resolution="resolved"),
            _dep(sp_mod, "numpy", "1.26.4", resolution="locked"),
        ])
        assert rows[0]["resolution"] == "locked"

    def test_depth_flows_to_match_row(self, im, db, sp_mod):
        rows = _match_one(im, db, [_dep(sp_mod, "numpy", "1.26.4",
                                        resolution="resolved", depth=1, fanout=3)])
        assert rows[0]["depth"] == 1 and rows[0]["fanout"] == 3
