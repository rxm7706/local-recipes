"""universe-sbom CLI + the S4 BOM validity gate.

cyclonedx-universe-inventory Wave B (S3 + S4). Fixtures deliberately carry
the live license variance the pre-Wave-B emitter mishandled: a single SPDX
id, an SPDX *expression* (`0BSD AND LGPL-2.1-or-later`), non-SPDX junk
(`(FTL or GPLv2+) and BSD`), and a non-Python package with a
`cfe:upstream_purl`. Gates pinned by the intake spec:

  • decision 1 — a mapped pair is ONE conda component; NO sibling pkg:pypi
  • decision 2 — archived/inactive INCLUDED + flagged; --actionable-only slices
  • decision 6 — freshness refusal (>14 d) with --allow-stale override
  • G98 purl forms (channel qualifier; lowercase `_`→`-`, dots preserved)
  • CycloneDX 1.6 schema validity (vendored schema, jsonschema)
  • round-trip through scan_project.parse_sbom_cyclonedx incl. the
    `?channel=` qualifier

The full-BOM schema run + measured size/time numbers are the LOCAL gate
(intake spec § Verification) — never fabricated here.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

import pytest


_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_SKILL_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


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
def cli_mod():
    return _load("universe_sbom")


@pytest.fixture(scope="module")
def sbom_mod():
    return _load("_sbom")


@pytest.fixture
def db(tmp_path, atlas_mod):
    conn = atlas_mod.open_db(tmp_path / "cf_atlas.db")
    atlas_mod.init_schema(conn)
    now = int(time.time())
    rows = [
        # (conda, version, license, pypi, source, conf, status, archived)
        ("dual",    "2.0", "0BSD AND LGPL-2.1-or-later", None, "none", "n/a", "active", 0),
        ("gotool",  "3.0", "Apache-2.0", None, "none", "n/a", "active", 0),
        ("junky",   "0.7", "(FTL or GPLv2+) and BSD", None, "none", "n/a", "active", 0),
        ("oldpkg",  "0.1", "MIT", "oldpkg", "parselmouth", "verified", "archived", 1),
        ("reqster", "1.0", "MIT", "reqster", "parselmouth", "verified", "active", 0),
    ]
    for conda, ver, lic, pypi, src, conf, status, arch in rows:
        conn.execute(
            "INSERT INTO packages (conda_name, latest_conda_version, "
            "conda_license, pypi_name, match_source, match_confidence, "
            "latest_status, feedstock_archived, relationship) "
            "VALUES (?,?,?,?,?,?,?,?, 'test')",
            (conda, ver, lic, pypi, src, conf, status, arch),
        )
    conn.execute(
        "INSERT INTO upstream_versions (conda_name, source, version, url, fetched_at) "
        "VALUES ('gotool', 'github', '3.0', 'https://github.com/Acme/GoTool', ?)",
        (now,),
    )
    for name in ("reqster", "oldpkg", "flask-extra", "fs.googledrivefs",
                 "Under_Score"):
        conn.execute(
            "INSERT INTO pypi_universe (pypi_name, last_serial, fetched_at) "
            "VALUES (?, 7, ?)", (name, now),
        )
    # Enriched unmapped project + an orphan (no universe row → view excludes).
    conn.execute(
        "INSERT INTO pypi_intelligence (pypi_name, latest_version, "
        "license_spdx, json_fetched_at) VALUES ('flask-extra', '9.9', 'MIT', ?)",
        (now,),
    )
    conn.execute(
        "INSERT INTO pypi_intelligence (pypi_name, latest_version, "
        "license_spdx, json_fetched_at) VALUES ('ghost', '0.1', 'MIT', ?)",
        (now,),
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES ('built_at', ?)",
        (str(now),),
    )
    conn.commit()
    yield conn
    conn.close()


def _bom(cli_mod, db, **kw):
    doc, summary = cli_mod.build_universe_bom(db, **kw)
    return doc, summary


def _comp(doc, name):
    hits = [c for c in doc["components"] if c["name"] == name]
    return hits[0] if hits else None


def _props(comp):
    return {p["name"]: p["value"] for p in comp.get("properties", [])}


class TestDecisionOne:
    def test_mapped_pair_is_one_component(self, db, cli_mod):
        doc, summary = _bom(cli_mod, db)
        purls = [c["purl"] for c in doc["components"]]
        assert not any(p.startswith("pkg:pypi/reqster") for p in purls), \
            "mapped pypi name must NOT appear as a sibling component"
        comp = _comp(doc, "reqster")
        props = _props(comp)
        assert props["cfe:pypi_purl"] == "pkg:pypi/reqster"
        assert props["cfe:match_source"] == "parselmouth"
        assert props["cfe:match_confidence"] == "verified"
        assert summary["conda_components"] == 5
        # unmapped universe names: flask-extra + fs.googledrivefs + Under_Score
        assert summary["pypi_components"] == 3


class TestLicenseNormalization:
    def test_three_forms(self, db, cli_mod):
        doc, _ = _bom(cli_mod, db)
        assert _comp(doc, "reqster")["licenses"] == [{"license": {"id": "MIT"}}]
        assert _comp(doc, "dual")["licenses"] == [
            {"expression": "0BSD AND LGPL-2.1-or-later"}]
        assert _comp(doc, "junky")["licenses"] == [
            {"license": {"name": "(FTL or GPLv2+) and BSD"}}]


class TestG98PurlForms:
    def test_channel_qualifier_and_normalization(self, db, cli_mod):
        import re as _re
        doc, _ = _bom(cli_mod, db)
        for c in doc["components"]:
            purl = c["purl"]
            if purl.startswith("pkg:conda/"):
                assert purl.endswith("?channel=conda-forge"), purl
            else:
                # G98: lowercase, `_`→`-`, dots PRESERVED.
                name = purl.removeprefix("pkg:pypi/").split("@")[0]
                assert _re.fullmatch(r"[a-z0-9.\-]+", name), purl
        assert any(c["purl"].startswith("pkg:pypi/fs.googledrivefs")
                   for c in doc["components"])
        # `_`→`-` actually exercised, not just regex-asserted
        assert any(c["purl"] == "pkg:pypi/under-score" for c in doc["components"])


class TestFlagsAndSlices:
    def test_inactive_included_and_flagged(self, db, cli_mod):
        doc, _ = _bom(cli_mod, db)
        props = _props(_comp(doc, "oldpkg"))
        assert props["cfe:latest_status"] == "archived"
        assert props["cfe:feedstock_archived"] == "true"

    def test_actionable_only_excludes_archived(self, db, cli_mod):
        doc, _ = _bom(cli_mod, db, actionable_only=True)
        assert _comp(doc, "oldpkg") is None
        assert _comp(doc, "reqster") is not None

    def test_conda_only_and_pypi_only(self, db, cli_mod):
        doc, summary = _bom(cli_mod, db, conda_only=True)
        assert summary["pypi_components"] == 0
        doc, summary = _bom(cli_mod, db, pypi_only=True)
        assert summary["conda_components"] == 0
        purls = [c["purl"] for c in doc["components"]]
        assert not any(p.startswith("pkg:conda/") for p in purls)
        # decision 1 holds even in the pypi-only slice
        assert not any(p.startswith("pkg:pypi/reqster") for p in purls)

    def test_mapped_only(self, db, cli_mod):
        doc, summary = _bom(cli_mod, db, mapped_only=True)
        names = {c["name"] for c in doc["components"]}
        assert names == {"reqster", "oldpkg"}
        assert summary["pypi_components"] == 0


class TestUpstreamAndEnrichment:
    def test_upstream_purl_on_non_python(self, db, cli_mod):
        props = _props(_comp(_bom(cli_mod, db)[0], "gotool"))
        assert props["cfe:upstream_purl"] == "pkg:github/acme/gotool"
        assert props["cfe:upstream_source"] == "github"

    def test_view_enrichment_and_orphan_exclusion(self, db, cli_mod):
        doc, _ = _bom(cli_mod, db)
        fx = _comp(doc, "flask-extra")
        assert fx["version"] == "9.9"
        assert fx["licenses"] == [{"license": {"id": "MIT"}}]
        assert _comp(doc, "ghost") is None, \
            "orphan pypi_intelligence rows are never components (ORPHAN_RULE)"


class TestFreshnessGate:
    def test_missing_stamp_refuses_fail_closed(self, db, cli_mod):
        db.execute("DELETE FROM meta WHERE key='built_at'")
        db.commit()
        with pytest.raises(cli_mod.StaleAtlasError):
            _bom(cli_mod, db)
        doc, _ = _bom(cli_mod, db, allow_stale=True)
        assert "properties" not in doc["metadata"] or all(
            p["name"] != "cfe:atlas_built_at"
            for p in doc["metadata"].get("properties", []))

    def test_stale_refuses_and_allow_stale_overrides(self, db, cli_mod):
        stale = int(time.time()) - 20 * 86400
        db.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('built_at', ?)",
                   (str(stale),))
        db.commit()
        with pytest.raises(cli_mod.StaleAtlasError):
            _bom(cli_mod, db)
        doc, _ = _bom(cli_mod, db, allow_stale=True)
        meta_props = {p["name"]: p["value"]
                      for p in doc["metadata"].get("properties", [])}
        assert meta_props["cfe:atlas_built_at"] == str(stale)


class TestSchemaValidity:
    def test_cyclonedx_16_schema_valid(self, db, cli_mod):
        jsonschema = pytest.importorskip("jsonschema")
        schema = json.loads((_DATA_DIR / "bom-1.6.schema.json").read_text())
        spdx = json.loads((_SKILL_DATA_DIR / "spdx.schema.json").read_text())
        jsf = json.loads((_DATA_DIR / "jsf-0.82.schema.json").read_text())
        doc, _ = _bom(cli_mod, db, with_vulns=True)
        base = "http://cyclonedx.org/schema/"
        store = {
            base + "bom-1.6.schema.json": schema,
            base + "spdx.schema.json": spdx,
            base + "jsf-0.82.schema.json": jsf,
            "spdx.schema.json": spdx,
            "jsf-0.82.schema.json": jsf,
        }
        try:
            # jsonschema >= 4.18: RefResolver is deprecated; use `referencing`.
            from referencing import Registry
            from referencing.jsonschema import DRAFT7
            registry = Registry().with_resources(
                (uri, DRAFT7.create_resource(s)) for uri, s in store.items())
            jsonschema.Draft7Validator(schema, registry=registry).validate(doc)
        except ImportError:
            resolver = jsonschema.RefResolver(
                base_uri=base + "bom-1.6.schema.json", referrer=schema, store=store)
            jsonschema.validate(doc, schema, resolver=resolver)

    def test_spdx_format_emits(self, db, cli_mod):
        doc, summary = _bom(cli_mod, db, fmt="spdx")
        assert doc["spdxVersion"] == "SPDX-2.3"
        assert summary["total_components"] == len(doc["packages"])
        dual = [p for p in doc["packages"] if p["name"] == "dual"][0]
        assert dual["licenseDeclared"] == "0BSD AND LGPL-2.1-or-later"


class TestRoundTrip:
    def test_scan_project_ingests_bom_with_channel_qualifier(self, db, cli_mod, tmp_path):
        doc, _ = _bom(cli_mod, db)
        bom_path = tmp_path / "u.cdx.json"
        bom_path.write_text(json.dumps(doc), encoding="utf-8")
        sp = _load("scan_project")
        deps = sp.parse_sbom_cyclonedx(bom_path)
        by_name = {d.name: d for d in deps}
        assert by_name["reqster"].ecosystem == "conda", \
            "?channel= qualifier must not break purl-prefix classification"
        assert by_name["reqster"].version == "1.0"
        assert by_name["flask-extra"].ecosystem == "pypi"


class TestFoldVariantSuppression:
    def test_mapping_spelling_variant_still_suppresses(self, tmp_path, atlas_mod, cli_mod):
        """D1: membership folds BOTH sides (PEP-503 fold_name) — a mapping
        stored as `ruamel-yaml` must suppress universe `ruamel.yaml`."""
        conn = atlas_mod.open_db(tmp_path / "fold.db")
        atlas_mod.init_schema(conn)
        conn.execute(
            "INSERT INTO packages (conda_name, latest_conda_version, pypi_name, "
            "match_source, match_confidence, relationship) "
            "VALUES ('ruamel.yaml', '0.18', 'ruamel-yaml', 'parselmouth', "
            "'verified', 'test')")
        conn.execute(
            "INSERT INTO pypi_universe (pypi_name, last_serial, fetched_at) "
            "VALUES ('ruamel.yaml', 1, 1)")
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES ('built_at', ?)",
            (str(int(time.time())),))
        conn.commit()
        doc, summary = cli_mod.build_universe_bom(conn)
        assert summary["pypi_components"] == 0,             "spelling variant must not resurrect a mapped name as a sibling"
        conn.close()


class TestSpdxDocument:
    def test_unique_spdxids_and_extracted_licensing(self, tmp_path, atlas_mod, cli_mod):
        """SPDXID sanitizer is many-to-one (`_`→`-`) — collisions must dedupe;
        name-form licenses survive as LicenseRef + hasExtractedLicensingInfos."""
        conn = atlas_mod.open_db(tmp_path / "spdx.db")
        atlas_mod.init_schema(conn)
        for name in ("prompt_toolkit", "prompt-toolkit"):
            conn.execute(
                "INSERT INTO packages (conda_name, latest_conda_version, "
                "conda_license, match_source, match_confidence, relationship) "
                "VALUES (?, '3.0', '(FTL or GPLv2+) and BSD', 'none', 'n/a', 'test')",
                (name,))
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES ('built_at', ?)",
            (str(int(time.time())),))
        conn.commit()
        doc, _ = cli_mod.build_universe_bom(conn, fmt="spdx", conda_only=True)
        ids = [pkg["SPDXID"] for pkg in doc["packages"]]
        assert len(ids) == len(set(ids)) == 2, "SPDXIDs must be unique"
        refs = {pkg["licenseDeclared"] for pkg in doc["packages"]}
        assert refs == {"LicenseRef-cfe-1"}
        infos = doc["hasExtractedLicensingInfos"]
        assert infos == [{"licenseId": "LicenseRef-cfe-1",
                          "extractedText": "(FTL or GPLv2+) and BSD"}]
        assert set(doc["documentDescribes"]) == set(ids)
        conn.close()


class TestSignalAges:
    def test_metadata_carries_per_signal_fetched_at(self, db, cli_mod):
        doc, _ = _bom(cli_mod, db, with_vulns=True)
        names = {p["name"] for p in doc["metadata"]["properties"]}
        assert "cfe:atlas_built_at" in names
        assert "cfe:pypi_universe_max_fetched_at" in names
        assert "cfe:upstream_versions_max_fetched_at" in names


class TestBoundedSliceRoundTrip:
    def test_fifty_plus_component_slice_parses(self, tmp_path, atlas_mod, cli_mod):
        """S4's bounded (~50-component) round-trip, in-process via
        scan_project.parse_sbom_cyclonedx. The CLI-level `scan-project
        --sbom-in` invocation of the same parser runs at the LOCAL live gate
        (needs the full env); recorded as a deferral, not skipped silently."""
        conn = atlas_mod.open_db(tmp_path / "big.db")
        atlas_mod.init_schema(conn)
        for i in range(60):
            conn.execute(
                "INSERT INTO pypi_universe (pypi_name, last_serial, fetched_at) "
                "VALUES (?, 1, 1)", (f"pkg-{i:03d}",))
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES ('built_at', ?)",
            (str(int(time.time())),))
        conn.commit()
        doc, summary = cli_mod.build_universe_bom(conn, pypi_only=True)
        assert summary["total_components"] >= 50
        bom_path = tmp_path / "slice.cdx.json"
        bom_path.write_text(json.dumps(doc), encoding="utf-8")
        sp = _load("scan_project")
        deps = sp.parse_sbom_cyclonedx(bom_path)
        assert len(deps) >= 50
        assert {d.ecosystem for d in deps} == {"pypi"}
        conn.close()


class TestNormalizeLicenseHelper:
    @pytest.mark.parametrize("raw,expected", [
        ("MIT", {"license": {"id": "MIT"}}),
        # idstring-SHAPED but not in the CycloneDX SPDX-id enum → name form
        # (schema-invalid as `id`; the enum gate is the Wave B review fix).
        ("LicenseRef-SustainableUseLicense-1.0",
         {"license": {"name": "LicenseRef-SustainableUseLicense-1.0"}}),
        ("GPL-2.0-or-later+", {"license": {"name": "GPL-2.0-or-later+"}}),
        ("PSF", {"license": {"name": "PSF"}}),
        ("GPLv2", {"license": {"name": "GPLv2"}}),
        ("Proprietary", {"license": {"name": "Proprietary"}}),
        # chained WITH violates the one-exception-per-simple-expression rule
        ("MIT WITH Classpath-exception-2.0 WITH LLVM-exception",
         {"license": {"name": "MIT WITH Classpath-exception-2.0 WITH LLVM-exception"}}),
        ("0BSD AND LGPL-2.1-or-later",
         {"expression": "0BSD AND LGPL-2.1-or-later"}),
        ("Apache-2.0 WITH LLVM-exception",
         {"expression": "Apache-2.0 WITH LLVM-exception"}),
        ("(MIT OR Apache-2.0) AND 0BSD",
         {"expression": "(MIT OR Apache-2.0) AND 0BSD"}),
        ("(FTL or GPLv2+) and BSD",
         {"license": {"name": "(FTL or GPLv2+) and BSD"}}),
        ("MIT AND", {"license": {"name": "MIT AND"}}),
        ("(MIT", {"license": {"name": "(MIT"}}),
        ("", None),
        (None, None),
    ])
    def test_forms(self, sbom_mod, raw, expected):
        assert sbom_mod.normalize_license(raw) == expected


class TestCliGuards:
    def test_missing_db_rc_1(self, cli_mod, tmp_path, monkeypatch):
        monkeypatch.setattr(cli_mod, "DB_PATH", tmp_path / "missing.db")
        monkeypatch.setattr(sys, "argv", ["universe_sbom"])
        assert cli_mod.main() == 1

    def test_contradictory_slices_raise_in_library(self, db, cli_mod):
        with pytest.raises(ValueError):
            _bom(cli_mod, db, conda_only=True, pypi_only=True)
        with pytest.raises(ValueError):
            _bom(cli_mod, db, mapped_only=True, pypi_only=True)
