"""add-handoff CLI — the S6 ADD-bucket packaging worklist.

cyclonedx-universe-inventory Wave C / S6. Pins: the bounded injectable
enrichment (Phase R's own upsert — idempotency proven by a zero-fetch
second run), canonical-formula re-scoring scoped to the slice, the
FAIL-CLOSED license rule (NULL license_spdx == `license-unknown` blocker,
never a silent pass — including under --no-enrich), --limit reporting
dropped names, 404/transient-failure semantics, readiness-desc ordering,
and ADD-NONPYPI appended unscored with purl identity.

The LIVE fetch path (`_phase_r_fetch_one` over the network) is the LOCAL
wave; every test here injects a fake fetcher.
"""
from __future__ import annotations

import importlib.util
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
def ah():
    return _load("add_handoff")


NOW = int(time.time())


def _payload(name: str, *, license_str: str = "MIT", yanked: bool = False,
             requires_python: str = ">=3.10") -> dict:
    """A minimal but realistic pypi.org/pypi/<name>/json document that
    scores 100 by the canonical formula when defaults are used."""
    version = "2.0.0"
    return {
        "info": {
            "name": name,
            "version": version,
            "license": license_str,
            "requires_python": requires_python,
            "summary": f"{name} does things",
            "project_urls": {"Repository": f"https://github.com/acme/{name}"},
            "classifiers": [],
        },
        "urls": [
            {"packagetype": "sdist", "filename": f"{name}-{version}.tar.gz",
             "yanked": yanked},
            {"packagetype": "bdist_wheel",
             "filename": f"{name}-{version}-py3-none-any.whl", "yanked": yanked},
        ],
        "releases": {
            version: [
                {"packagetype": "sdist",
                 "upload_time_iso_8601": time.strftime(
                     "%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - 5 * 86400)),
                 "yanked": yanked},
            ],
        },
    }


def _fake_fetcher(responses: dict):
    """responses: name → payload dict | 'HTTP 404' | 'HTTP 503'."""
    calls: list[str] = []

    def fetch(name: str):
        calls.append(name)
        r = responses.get(name)
        if isinstance(r, dict):
            return (name, r, None)
        return (name, None, r or "HTTP 404")

    fetch.calls = calls  # type: ignore[attr-defined]
    return fetch


def _add_row(name: str, **kw) -> dict:
    return {"name": name, "pypi_name": name, "ecosystem": "pypi",
            "bucket": "ADD", **kw}


@pytest.fixture
def db(tmp_path, atlas_mod):
    conn = atlas_mod.open_db(tmp_path / "cf_atlas.db")
    atlas_mod.init_schema(conn)
    for name in ("goodpkg", "nonosipkg", "ghostpkg", "flakypkg", "yankedpkg",
                 "prescored"):
        conn.execute(
            "INSERT INTO pypi_universe (pypi_name, last_serial, fetched_at) "
            "VALUES (?, 1, ?)", (name, NOW),
        )
    # already-enriched row: non-OSI license, mid readiness — no fetch needed
    conn.execute(
        "INSERT INTO pypi_intelligence (pypi_name, latest_version, license_spdx, "
        "conda_forge_readiness, recommended_template, json_fetched_at, has_sdist, "
        "packaging_shape) VALUES ('prescored', '1.0', 'CC-BY-4.0', 55, "
        "'templates/python/recipe.yaml', ?, 1, 'pure-python')", (NOW,),
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES ('built_at', ?)", (str(NOW),),
    )
    conn.commit()
    yield conn
    conn.close()


class TestEnrichment:
    def test_fetch_upsert_score_via_canonical_paths(self, ah, db):
        fetcher = _fake_fetcher({"goodpkg": _payload("goodpkg")})
        result = ah.run_handoff(db, [_add_row("goodpkg")], fetcher=fetcher)
        assert result["enrichment"]["fetched"] == 1
        entry = result["worklist"][0]
        # canonical Phase S formula: OSI 25 + py>=3.10 20 + repo 15 +
        # recent 15 + sdist 10 + pure-python 15 = 100
        assert entry["readiness"] == 100
        assert entry["template"] == "templates/python/recipe.yaml"
        assert entry["blockers"] == []

    def test_second_run_is_zero_fetch(self, ah, db):
        """Idempotency proof — json_fetched_at set by run 1 makes run 2
        skip the name entirely (the S2 write-path discipline)."""
        fetcher = _fake_fetcher({"goodpkg": _payload("goodpkg")})
        ah.run_handoff(db, [_add_row("goodpkg")], fetcher=fetcher)
        ah.run_handoff(db, [_add_row("goodpkg")], fetcher=fetcher)
        assert fetcher.calls == ["goodpkg"]          # exactly one live fetch

    def test_already_enriched_never_fetched(self, ah, db):
        fetcher = _fake_fetcher({})
        result = ah.run_handoff(db, [_add_row("prescored")], fetcher=fetcher)
        assert fetcher.calls == []
        assert result["worklist"][0]["readiness"] == 55

    def test_limit_drops_are_reported_not_silent(self, ah, db):
        fetcher = _fake_fetcher({"goodpkg": _payload("goodpkg"),
                                 "flakypkg": _payload("flakypkg")})
        result = ah.run_handoff(
            db, [_add_row("goodpkg"), _add_row("flakypkg")],
            fetcher=fetcher, limit=1)
        enr = result["enrichment"]
        assert enr["fetched"] == 1
        assert enr["dropped_by_limit"] == ["flakypkg"]
        report = ah.render_report(result)
        assert "flakypkg" in report and "dropped" in report

    def test_404_is_an_answer_transient_stays_eligible(self, ah, db):
        fetcher = _fake_fetcher({"ghostpkg": "HTTP 404", "flakypkg": "HTTP 503"})
        ah.run_handoff(db, [_add_row("ghostpkg"), _add_row("flakypkg")],
                       fetcher=fetcher)
        # 404 bumps json_fetched_at (project gone — do not refetch) …
        got = db.execute("SELECT json_fetched_at, json_last_error FROM "
                         "pypi_intelligence WHERE pypi_name='ghostpkg'").fetchone()
        assert got[0] is not None and got[1] == "HTTP 404"
        # … transient failure does NOT (stays eligible for the next run)
        got = db.execute("SELECT json_fetched_at FROM pypi_intelligence "
                         "WHERE pypi_name='flakypkg'").fetchone()
        assert got[0] is None
        fetcher2 = _fake_fetcher({"flakypkg": _payload("flakypkg")})
        result = ah.run_handoff(db, [_add_row("ghostpkg"), _add_row("flakypkg")],
                                fetcher=fetcher2)
        assert fetcher2.calls == ["flakypkg"]        # ghost not retried
        assert result["enrichment"]["fetched"] == 1


class TestFailClosedLicense:
    def test_no_enrich_rows_stay_blocked(self, ah, db):
        """--no-enrich must NEVER let a NULL license pass the OSI check."""
        result = ah.run_handoff(db, [_add_row("goodpkg")], enrich=False)
        entry = result["worklist"][0]
        assert "license-unknown" in entry["blockers"]
        assert "pypi_enrichment" in entry["signals_absent"]
        report = ah.render_report(result)
        assert "SKIPPED" in report

    def test_enriched_but_unresolvable_license_blocks(self, ah, db):
        fetcher = _fake_fetcher(
            {"goodpkg": _payload("goodpkg", license_str="Proprietary :: Custom")})
        result = ah.run_handoff(db, [_add_row("goodpkg")], fetcher=fetcher)
        assert "license-unknown" in result["worklist"][0]["blockers"]

    def test_non_osi_license_blocks_with_id(self, ah, db):
        result = ah.run_handoff(db, [_add_row("prescored")], enrich=False)
        assert result["worklist"][0]["blockers"] == ["license-non-osi (CC-BY-4.0)"]

    def test_gone_project_blocked(self, ah, db):
        fetcher = _fake_fetcher({"ghostpkg": "HTTP 404"})
        result = ah.run_handoff(db, [_add_row("ghostpkg")], fetcher=fetcher)
        blockers = result["worklist"][0]["blockers"]
        assert "pypi-project-gone" in blockers
        assert "license-unknown" in blockers

    def test_yanked_latest_blocked(self, ah, db):
        fetcher = _fake_fetcher({"yankedpkg": _payload("yankedpkg", yanked=True)})
        result = ah.run_handoff(db, [_add_row("yankedpkg")], fetcher=fetcher)
        assert "latest-yanked" in result["worklist"][0]["blockers"]


class TestWorklistShape:
    def test_readiness_desc_unscored_last(self, ah, db):
        fetcher = _fake_fetcher({"goodpkg": _payload("goodpkg"),
                                 "flakypkg": "HTTP 503"})
        result = ah.run_handoff(
            db, [_add_row("flakypkg"), _add_row("prescored"), _add_row("goodpkg")],
            fetcher=fetcher)
        names = [e["pypi_name"] for e in result["worklist"]]
        assert names == ["goodpkg", "prescored", "flakypkg"]  # 100, 55, unscored

    def test_nonpypi_appended_unscored_with_purl(self, ah, db):
        rows = [
            _add_row("prescored"),
            {"name": "left-pad", "ecosystem": "npm", "bucket": "ADD-NONPYPI",
             "pinned": "1.3.0"},
            {"name": "ripgrep", "ecosystem": "cargo", "bucket": "ADD-NONPYPI",
             "pinned": None},
        ]
        result = ah.run_handoff(db, rows, enrich=False)
        assert result["nonpypi"] == [
            {"name": "left-pad", "ecosystem": "npm",
             "upstream_purl": "pkg:npm/left-pad@1.3.0"},
            {"name": "ripgrep", "ecosystem": "cargo",
             "upstream_purl": "pkg:cargo/ripgrep"},
        ]
        report = ah.render_report(result)
        assert "pkg:npm/left-pad@1.3.0" in report

    def test_non_add_buckets_ignored(self, ah, db):
        rows = [
            {"name": "numpy", "ecosystem": "pypi", "bucket": "CURRENT"},
            {"name": "olddep", "ecosystem": "pypi", "bucket": "UPDATE-FEEDSTOCK"},
        ]
        result = ah.run_handoff(db, rows, enrich=False)
        assert result["add_count"] == 0 and result["worklist"] == []

    def test_duplicate_names_fetched_once(self, ah, db):
        fetcher = _fake_fetcher({"goodpkg": _payload("goodpkg")})
        result = ah.run_handoff(
            db, [_add_row("goodpkg"), _add_row("goodpkg")], fetcher=fetcher)
        assert fetcher.calls == ["goodpkg"]          # deduped, one live fetch
        # both rows still appear in the worklist (dedup is on FETCH, not display)
        assert len(result["worklist"]) == 2

    def test_not_in_universe_name_not_fetched(self, ah, db):
        """An ADD name absent from pypi_universe (stale --matches) is NOT
        live-fetched — that would mint the orphan pypi_intelligence row the
        ORPHAN_RULE excludes — and is reported."""
        fetcher = _fake_fetcher({"orphanpkg": _payload("orphanpkg")})
        result = ah.run_handoff(db, [_add_row("orphanpkg")], fetcher=fetcher)
        assert fetcher.calls == []
        assert "orphanpkg" in result["enrichment"]["not_in_universe"]
        # no orphan row minted
        assert db.execute("SELECT COUNT(*) FROM pypi_intelligence "
                          "WHERE pypi_name='orphanpkg'").fetchone()[0] == 0
        assert "not in" in ah.render_report(result)

    def test_malformed_matches_rows_skipped_not_crash(self, ah, db):
        rows = [
            {"bucket": "ADD"},                       # no name at all
            _add_row("prescored"),
            {"bucket": "ADD-NONPYPI", "pinned": "1.0"},   # no name/ecosystem
        ]
        result = ah.run_handoff(db, rows, enrich=False)
        assert [e["pypi_name"] for e in result["worklist"]] == ["prescored"]
        assert result["nonpypi"] == []              # nameless nonpypi skipped

    def test_built_at_rendered_iso(self, ah, db):
        result = ah.run_handoff(db, [_add_row("prescored")], enrich=False)
        assert result["built_at"].endswith("Z") and "T" in result["built_at"]

    def test_in_flight_pr_and_local_recipe_surfaced(self, ah, db):
        db.execute("UPDATE pypi_intelligence SET staged_recipes_pr_url = "
                   "'https://github.com/conda-forge/staged-recipes/pull/12345' "
                   "WHERE pypi_name = 'prescored'")
        db.commit()
        result = ah.run_handoff(
            db, [_add_row("prescored", local_recipe=True)], enrich=False)
        entry = result["worklist"][0]
        assert entry["staged_recipes_pr_url"].endswith("/pull/12345")
        assert entry["local_recipe"] is True
        report = ah.render_report(result)
        assert "PR in flight" in report and "local recipe present" in report
