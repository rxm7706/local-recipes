"""recommend-2027 — the S8 2027–2030 window scorecard.

cyclonedx-universe-inventory Wave D / S8. Pins THE CALIBRATION GATE the
spec demands ("the tiers must rank all of these correctly before weights
are accepted"): known-good keep (numpy/pydantic-shaped + one healthy
non-Python), known-bad not-keep (archived / KEV / >18mo-silent incl. one
non-Python), django 5.2 → lts-supported (EOL 2028-04-30) vs django 4.2 →
eol-before-window (EOL 2026-04-07, must NOT tier keep), a py314-not-ready
compiled package (caps watch), a py314-ready compiled package (no cap).
Plus: the 2027–2030 header, --matches/inline parity, the five cfe:* BOM
properties, operator overrides shown-never-silent, and Phase-P staleness
detected-not-executed.

All EOL data comes from an injected fake endoflife fetcher — deterministic
and offline; the live fetch is the LOCAL wave.
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


@pytest.fixture(scope="module")
def r27():
    return _load("recommend_2027")


NOW = int(time.time())
DAY = 86400

_DJANGO_CYCLES = [
    {"cycle": "5.2", "lts": "2025-04-02", "eol": "2028-04-30"},
    {"cycle": "4.2", "lts": "2023-04-03", "eol": "2026-04-07"},
    {"cycle": "5.1", "lts": False, "eol": "2025-12-01"},
]


def _fake_eol_fetcher(slug):
    return _DJANGO_CYCLES if slug == "django" else None


@pytest.fixture
def db(tmp_path, atlas_mod):
    """The calibration atlas: every spec-named case as a fixture package."""
    conn = atlas_mod.open_db(tmp_path / "cf_atlas.db")
    atlas_mod.init_schema(conn)
    # (conda, pypi, version, upload_age_d, dl90, license, archived)
    pkgs = [
        ("numpy",     "numpy",     "2.1.0", 15,  9_000_000, "BSD-3-Clause", 0),
        ("pydantic",  "pydantic",  "2.8.0", 10,  5_000_000, "MIT",          0),
        ("ripgrep",   None,        "14.1.0", 20, 800_000,   "MIT",          0),  # healthy non-Python
        ("deadproj",  "deadproj",  "0.4",   900, 10,        "MIT",          1),  # archived (bad)
        ("kevpkg",    "kevpkg",    "1.2",   25,  400_000,   "MIT",          0),  # KEV-listed (bad)
        ("quietlib",  "quietlib",  "3.0",   700, 2_000,     "MIT",          0),  # >18mo silent (bad)
        ("oldtool",   None,        "1.1",   800, 500,       "MIT",          1),  # bad non-Python (archived+silent)
        ("django",    "django",    "5.2",   12,  2_000_000, "BSD-3-Clause", 0),
        ("legacyext", "legacyext", "1.0",   30,  50_000,    "MIT",          0),  # py314-not-ready compiled
        ("fastext",   "fastext",   "2.0",   18,  70_000,    "Apache-2.0",   0),  # py314-ready compiled
    ]
    for conda, pypi, ver, age, dl, lic, arch in pkgs:
        conn.execute(
            "INSERT INTO packages (conda_name, pypi_name, latest_conda_version, "
            "latest_conda_upload, downloads_90d, downloads_source, "
            "downloads_fetched_at, conda_license, feedstock_archived, "
            "latest_status, relationship, match_source, match_confidence) "
            "VALUES (?,?,?,?,?, 's3-parquet', ?, ?, ?, 'active', 'test', "
            "'parselmouth', 'verified')",
            (conda, pypi, ver, NOW - age * DAY, dl, NOW, lic, arch))
    # cadence/adoption raw rows for the active packages
    for conda in ("numpy", "pydantic", "ripgrep", "kevpkg", "django",
                  "legacyext", "fastext"):
        for i in range(5):
            conn.execute(
                "INSERT INTO package_version_downloads (conda_name, version, "
                "upload_unix, total_downloads) VALUES (?,?,?, 5000)",
                (conda, f"1.{i}", NOW - (i * 20 + 5) * DAY))
    # vuln truth: clean scans everywhere except kevpkg (KEV on current)
    clean = ("numpy", "pydantic", "ripgrep", "django", "legacyext", "fastext",
             "quietlib")
    for conda, _pypi, ver, *_rest in pkgs:
        if conda not in clean:
            continue
        conn.execute(
            "INSERT INTO package_version_vulns (conda_name, version, vuln_total, "
            "vuln_critical_affecting_version, vuln_high_affecting_version, "
            "vuln_kev_affecting_version, scanned_at) VALUES (?,?,0,0,0,0,?)",
            (conda, ver, NOW))
    conn.execute(
        "INSERT INTO package_version_vulns (conda_name, version, vuln_total, "
        "vuln_critical_affecting_version, vuln_high_affecting_version, "
        "vuln_kev_affecting_version, scanned_at) VALUES "
        "('kevpkg', '1.2', 2, 1, 1, 1, ?)", (NOW,))
    # upstream identities (fresh — no lag)
    for conda, src, ver in [("numpy", "pypi", "2.1.0"), ("pydantic", "pypi", "2.8.0"),
                            ("ripgrep", "github", "14.1.0"), ("django", "pypi", "5.2"),
                            ("kevpkg", "pypi", "1.2"), ("legacyext", "pypi", "1.0"),
                            ("fastext", "pypi", "2.0")]:
        conn.execute(
            "INSERT INTO upstream_versions (conda_name, source, version, url, "
            "fetched_at) VALUES (?,?,?, 'https://example.com', ?)",
            (conda, src, ver, NOW))
    # PyPI enrichment
    for name in ("numpy", "pydantic", "deadproj", "kevpkg", "quietlib",
                 "django", "legacyext", "fastext"):
        conn.execute("INSERT INTO pypi_universe (pypi_name, last_serial, "
                     "fetched_at) VALUES (?, 1, ?)", (name, NOW))
    intel = [
        # (name, band, wheel, sdist, shape, req_py, tags, upload_at)
        ("numpy",    "hot",  1, 1, "c-extension", ">=3.10", '["cp314-cp314"]', NOW - 15 * DAY),
        ("pydantic", "hot",  1, 1, "pure-python", ">=3.9",  '["py3-none"]',    NOW - 10 * DAY),
        ("kevpkg",   "warm", 1, 1, "pure-python", ">=3.9",  '["py3-none"]',    NOW - 25 * DAY),
        ("quietlib", "dormant", 1, 1, "pure-python", ">=3.8", '["py3-none"]',  NOW - 700 * DAY),
        ("django",   "hot",  1, 1, "pure-python", ">=3.10", '["py3-none"]',    NOW - 12 * DAY),
        ("legacyext","warm", 1, 1, "c-extension", ">=3.8,<3.14", '["cp311-cp311"]', NOW - 30 * DAY),
        ("fastext",  "warm", 1, 1, "c-extension", ">=3.9",  '["cp314-cp314"]', NOW - 18 * DAY),
    ]
    for name, band, whl, sd, shape, rp, tags, up in intel:
        conn.execute(
            "INSERT INTO pypi_intelligence (pypi_name, activity_band, has_wheel, "
            "has_sdist, packaging_shape, latest_yanked, latest_upload_at, "
            "repo_url, docs_url, classifiers, requires_python, python_tags, "
            "json_fetched_at, downloads_fetched_at) VALUES "
            "(?,?,?,?,?,0,?, 'https://r','https://d','[]',?,?,?,?)",
            (name, band, whl, sd, shape, up, rp, tags, NOW, NOW))
    conn.execute("INSERT INTO meta(key, value) VALUES ('built_at', ?)", (str(NOW),))
    conn.commit()
    yield conn
    conn.close()


def _row(conda, eco="pypi", pinned=None, bucket="CURRENT", **kw):
    return {"name": conda, "conda_name": conda, "ecosystem": eco,
            "bucket": bucket, "pinned": pinned, "signals_absent": [], **kw}


@pytest.fixture
def eol_client(lf, tmp_path):
    return lf.EolClient(cache_path=tmp_path / "eol.json",
                        fetcher=_fake_eol_fetcher, registry={}, now=NOW)


CALIBRATION_ROWS = [
    ("numpy",     dict(pinned="2.1.0")),
    ("pydantic",  dict(pinned="2.8.0")),
    ("ripgrep",   dict(eco="conda", pinned="14.1.0")),
    ("deadproj",  dict(pinned="0.4")),
    ("kevpkg",    dict(pinned="1.2")),
    ("quietlib",  dict(pinned="3.0")),
    ("oldtool",   dict(eco="conda", pinned="1.1")),
    ("legacyext", dict(pinned="1.0")),
    ("fastext",   dict(pinned="2.0")),
]


class TestCalibrationGate:
    """The spec's acceptance gate: every named case must rank correctly."""

    @pytest.fixture
    def scored(self, r27, db, eol_client):
        rows = [_row(c, **kw) for c, kw in CALIBRATION_ROWS]
        rows.append(_row("django", pinned="5.2"))
        result = r27.run_recommend(db, rows, eol_client=eol_client, now=NOW)
        return {r["conda_name"]: r for r in result["rows"]}

    def test_known_good_keep(self, scored):
        assert scored["numpy"]["futures_tier"] == "keep"
        assert scored["pydantic"]["futures_tier"] == "keep"

    def test_healthy_non_python_keep(self, scored):
        assert scored["ripgrep"]["futures_tier"] == "keep"
        assert any("non-python" in s for s in scored["ripgrep"]["signals_absent"])

    def test_archived_not_keep(self, scored):
        assert scored["deadproj"]["futures_tier"] in ("plan-migration", "replace")

    def test_kev_listed_not_keep(self, scored):
        assert scored["kevpkg"]["futures_tier"] != "keep"
        assert any("KEV" in why for why in scored["kevpkg"]["tier_reasons"])

    def test_silent_18mo_not_keep(self, scored):
        assert scored["quietlib"]["futures_tier"] != "keep"

    def test_bad_non_python_not_keep(self, scored):
        assert scored["oldtool"]["futures_tier"] in ("plan-migration", "replace")

    def test_django_52_lts_supported_keep(self, scored):
        r = scored["django"]
        assert r["lts_status"] == "lts-supported"
        assert r["eol_date"] == "2028-04-30"
        assert r["futures_tier"] == "keep"

    def test_django_42_eol_before_window_not_keep(self, r27, db, eol_client):
        result = r27.run_recommend(db, [_row("django", pinned="4.2")],
                                   eol_client=eol_client, now=NOW)
        r = result["rows"][0]
        assert r["eol_date"] == "2026-04-07"
        assert r["futures_tier"] != "keep"                 # the spec's MUST NOT
        assert r["futures_tier"] in ("plan-migration", "replace")

    def test_py314_not_ready_caps_watch(self, scored):
        r = scored["legacyext"]
        assert r["py314_readiness"] == "py314-not-ready"
        assert r["futures_tier"] == "watch"

    def test_py314_ready_compiled_uncapped(self, scored):
        r = scored["fastext"]
        assert r["py314_readiness"] == "py314-ready"
        assert r["futures_tier"] == "keep"


class TestReportAndParity:
    def test_window_header_and_ages(self, r27, db, eol_client):
        result = r27.run_recommend(db, [_row("numpy", pinned="2.1.0")],
                                   eol_client=eol_client, now=NOW)
        report = r27.render_report(result)
        assert "2027–2030 window" in report
        assert "Signal freshness" in report
        assert result["signal_ages"]["conda_downloads_age_days"] == 0

    def test_matches_replay_parity(self, r27, db, eol_client, tmp_path):
        """Drives the REAL --matches path: load_matches over a written file
        must yield the same scorecard as the in-memory rows."""
        rows = [_row("numpy", pinned="2.1.0"), _row("kevpkg", pinned="1.2")]
        direct = r27.run_recommend(db, rows, eol_client=eol_client, now=NOW)
        matches_file = tmp_path / "matches.json"
        matches_file.write_text(json.dumps(
            {"generated_at": "x", "counts": {}, "rows": rows}))
        replayed = r27.run_recommend(db, r27.load_matches(matches_file),
                                     eol_client=eol_client, now=NOW)
        strip = ("generated_at",)
        assert {k: v for k, v in direct.items() if k not in strip} == \
               {k: v for k, v in replayed.items() if k not in strip}

    def test_load_matches_rejects_wrong_shapes(self, r27, tmp_path):
        bare_list = tmp_path / "list.json"
        bare_list.write_text(json.dumps([{"name": "x"}]))
        assert r27.load_matches(bare_list) is None       # no AttributeError
        no_rows = tmp_path / "norows.json"
        no_rows.write_text(json.dumps({"counts": {}}))
        assert r27.load_matches(no_rows) is None

    def test_rows_never_vanish_from_the_scorecard(self, r27, db, eol_client):
        """scored + not_evaluated must PARTITION the input — a hand-edited
        --matches row with a conda_name but an unscoreable bucket lands in
        not_evaluated, never silently dropped."""
        weird = [
            {"name": "numpy", "conda_name": "numpy", "ecosystem": "pypi",
             "bucket": "ADD", "signals_absent": []},          # contradictory shape
            {"name": "numpy2", "conda_name": "numpy", "ecosystem": "pypi",
             "bucket": "current", "signals_absent": []},      # case-skewed bucket
        ]
        result = r27.run_recommend(db, weird, eol_client=eol_client, now=NOW)
        assert len(result["rows"]) + len(result["not_evaluated"]) == len(weird)

    def test_not_evaluated_listed(self, r27, db, eol_client):
        rows = [_row("numpy", pinned="2.1.0"),
                {"name": "newpkg", "ecosystem": "pypi", "bucket": "ADD",
                 "conda_name": None, "signals_absent": []}]
        result = r27.run_recommend(db, rows, eol_client=eol_client, now=NOW)
        assert result["not_evaluated"] == [
            {"name": "newpkg", "ecosystem": "pypi", "bucket": "ADD"}]
        assert "not on conda-forge" in r27.render_report(result)


class TestAnnotation:
    def test_reannotation_idempotent(self, r27, db, eol_client, tmp_path):
        """This run's --sbom-in is a prior run's --sbom-out: cfe:* properties
        must be replaced, never stacked."""
        bom = {"bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1,
               "components": [{"type": "library", "name": "django",
                               "version": "5.2", "purl": "pkg:pypi/django@5.2"}]}
        p = tmp_path / "in.cdx.json"
        p.write_text(json.dumps(bom))
        result = r27.run_recommend(db, [_row("django", pinned="5.2")],
                                   eol_client=eol_client, now=NOW)
        once = r27.annotate_sbom(p, result["rows"], result["built_at"])
        p.write_text(json.dumps(once))
        twice = r27.annotate_sbom(p, result["rows"], result["built_at"])
        names = [x["name"] for x in twice["components"][0]["properties"]]
        assert len(names) == len(set(names))          # no duplicates
        meta_names = [x["name"] for x in twice["metadata"]["properties"]]
        assert meta_names.count("cfe:atlas_built_at") == 1

    def test_bom_carries_all_cfe_properties(self, r27, db, eol_client, tmp_path):
        bom = {"bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1,
               "components": [
                   {"type": "library", "name": "django", "version": "5.2",
                    "purl": "pkg:pypi/django@5.2"},
                   {"type": "library", "name": "unrelated", "version": "1.0",
                    "purl": "pkg:npm/unrelated@1.0"}]}
        p = tmp_path / "in.cdx.json"
        p.write_text(json.dumps(bom))
        result = r27.run_recommend(db, [_row("django", pinned="5.2")],
                                   eol_client=eol_client, now=NOW)
        annotated = r27.annotate_sbom(p, result["rows"], result["built_at"])
        props = {x["name"]: x["value"]
                 for x in annotated["components"][0]["properties"]}
        assert props["cfe:futures_tier"] == "keep"
        assert float(props["cfe:futures_score"]) > 0
        assert props["cfe:py314_readiness"]
        assert props["cfe:lts_status"] == "lts-supported"
        assert props["cfe:eol_date"] == "2028-04-30"
        assert "properties" not in annotated["components"][1]  # unmatched untouched
        meta = {x["name"] for x in annotated["metadata"]["properties"]}
        assert "cfe:atlas_built_at" in meta

    def test_annotate_rejects_non_cyclonedx(self, r27, tmp_path):
        p = tmp_path / "x.json"
        p.write_text('{"spdxVersion": "SPDX-2.3"}')
        with pytest.raises(ValueError):
            r27.annotate_sbom(p, [], "0")


class TestOverrides:
    def test_sidecar_override_shown_never_silent(self, r27, db, eol_client, tmp_path):
        ov = tmp_path / "ov.json"
        ov.write_text(json.dumps({"kevpkg": {"tier": "keep",
                                             "reason": "airgapped, accepted risk"}}))
        overrides = r27.load_overrides_sidecar(ov)
        result = r27.run_recommend(db, [_row("kevpkg", pinned="1.2")],
                                   eol_client=eol_client, overrides=overrides,
                                   now=NOW)
        r = result["rows"][0]
        assert r["futures_tier"] == "keep"                  # overridden
        assert r["override"]["original_tier"] == "watch"    # original visible
        report = r27.render_report(result)
        assert "OVERRIDDEN from watch" in report
        assert "accepted risk" in report

    def test_notes_override_channel(self, r27, db, eol_client):
        db.execute("UPDATE pypi_intelligence SET notes = "
                   "'ops: cfe:futures_tier=plan-migration scheduled sunset' "
                   "WHERE pypi_name = 'numpy'")
        db.commit()
        result = r27.run_recommend(db, [_row("numpy", pinned="2.1.0")],
                                   eol_client=eol_client, now=NOW)
        r = result["rows"][0]
        assert r["futures_tier"] == "plan-migration"
        assert r["override"]["reason"] == "pypi_intelligence.notes"

    def test_bad_sidecar_tier_rejected(self, r27, tmp_path):
        ov = tmp_path / "ov.json"
        ov.write_text(json.dumps({"x": {"tier": "yolo"}}))
        with pytest.raises(ValueError):
            r27.load_overrides_sidecar(ov)

    def test_empty_notes_marker_no_crash(self, r27, db, eol_client, capsys):
        # 'cfe:futures_tier=' with no value must warn, never IndexError
        db.execute("UPDATE pypi_intelligence SET notes = 'cfe:futures_tier=' "
                   "WHERE pypi_name = 'numpy'")
        db.commit()
        result = r27.run_recommend(db, [_row("numpy", pinned="2.1.0")],
                                   eol_client=eol_client, now=NOW)
        assert "override" not in result["rows"][0]
        assert "override ignored" in capsys.readouterr().err

    def test_punctuated_notes_tier_still_applies(self, r27, db, eol_client):
        # 'cfe:futures_tier=replace.' — trailing punctuation must not
        # silently drop the override
        db.execute("UPDATE pypi_intelligence SET notes = "
                   "'ops: cfe:futures_tier=replace. sunset planned' "
                   "WHERE pypi_name = 'numpy'")
        db.commit()
        result = r27.run_recommend(db, [_row("numpy", pinned="2.1.0")],
                                   eol_client=eol_client, now=NOW)
        assert result["rows"][0]["futures_tier"] == "replace"

    def test_unrecognized_notes_tier_warns(self, r27, db, eol_client, capsys):
        db.execute("UPDATE pypi_intelligence SET notes = "
                   "'cfe:futures_tier=yolo' WHERE pypi_name = 'numpy'")
        db.commit()
        result = r27.run_recommend(db, [_row("numpy", pinned="2.1.0")],
                                   eol_client=eol_client, now=NOW)
        assert "override" not in result["rows"][0]
        assert "unrecognized futures tier" in capsys.readouterr().err

    def test_override_exact_key_beats_fold_variant(self, r27, tmp_path):
        # exact lowercase entries never clobbered by a fold-equivalent name
        ov = tmp_path / "ov.json"
        ov.write_text(json.dumps({"ruamel.yaml": {"tier": "keep"},
                                  "ruamel_yaml": {"tier": "replace"}}))
        overrides = r27.load_overrides_sidecar(ov)
        rows = [
            {"conda_name": "ruamel.yaml", "name": "ruamel.yaml",
             "futures_tier": "watch", "futures_score": 50.0},
            {"conda_name": "ruamel_yaml", "name": "ruamel_yaml",
             "futures_tier": "watch", "futures_score": 50.0},
        ]
        r27.apply_overrides(rows, overrides)
        assert rows[0]["futures_tier"] == "keep"
        assert rows[1]["futures_tier"] == "replace"


class TestPhasePOffer:
    def test_stale_downloads_detected_not_executed(self, r27, db, eol_client):
        db.execute("UPDATE pypi_intelligence SET downloads_fetched_at = ?",
                   (NOW - 200 * DAY,))
        db.commit()
        result = r27.run_recommend(db, [_row("numpy", pinned="2.1.0")],
                                   eol_client=eol_client, now=NOW)
        stale = result["downloads_staleness"]
        assert stale and stale["age_days"] >= 200
        assert "preflight" in stale["offer"]
        report = r27.render_report(result)
        assert "Phase P offer (operator-gated" in report

    def test_fresh_downloads_no_offer(self, r27, db, eol_client):
        result = r27.run_recommend(db, [_row("numpy", pinned="2.1.0")],
                                   eol_client=eol_client, now=NOW)
        assert result["downloads_staleness"] is None
