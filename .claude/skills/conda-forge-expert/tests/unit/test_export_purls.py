"""export-purls CLI — the six-artifact purl + mapping exporter.

cyclonedx-universe-inventory Wave A / S1. Pins the artifact regression
surface: sort-by-name (NEVER full-line) ordering, G98 dots-preserved purl
names, the D1 fold-both-sides exceptions fix (both branches), determinism,
TSV header + `none`-provenance passthrough, NULL-version count parity,
recipe parse-error tolerance, and missing-DB → rc 1.
"""
from __future__ import annotations

import importlib.util
import sys
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
def cli_mod():
    return _load("export_purls")


@pytest.fixture
def db(tmp_path, atlas_mod):
    """Fixture atlas exercising every artifact branch:

    packages: `foo` + `foo-bar` (the sort-regression pair), a NULL-version
    row, an archived-but-active row (INCLUDED per the artifact contract),
    a `latest_status='archived'` row (EXCLUDED), a `none`-provenance mapped
    row, and an unmapped row with a github + an unparseable upstream.
    pypi_universe: dotted names for G98/D1.
    """
    conn = atlas_mod.open_db(tmp_path / "cf_atlas.db")
    atlas_mod.init_schema(conn)
    pkg_rows = [
        # (conda, pypi, status, archived, version, match_source, match_conf)
        # match_source / match_confidence are NOT NULL in the live schema —
        # unattributed rows store the LITERAL 'none' / 'n/a'.
        ("foo",       "foo",              "active",   0, "1.0",  "parselmouth", "verified"),
        ("foo-bar",   None,               "active",   0, "2.0",  "none",        "n/a"),
        ("noversion", None,               "active",   0, None,   "none",        "n/a"),
        ("oldie",     "oldie",            "active",   1, "0.9",  "none",        "n/a"),
        ("gone",      "gone",             "archived", 0, "0.1",  "parselmouth", "verified"),
        ("dotted",    "fs.googledrivefs", "active",   0, "1.2",  "parselmouth", "verified"),
        ("ghtool",    None,               "active",   0, "3.0",  "none",        "n/a"),
    ]
    for conda, pypi, status, archived, ver, src, confidence in pkg_rows:
        conn.execute(
            "INSERT INTO packages (conda_name, pypi_name, latest_status, "
            "feedstock_archived, latest_conda_version, match_source, "
            "match_confidence, relationship) VALUES (?,?,?,?,?,?,?, 'test')",
            (conda, pypi, status, archived, ver, src, confidence),
        )
    for name in ("foo", "oldie", "gone", "fs.googledrivefs", "pymilvus.model"):
        conn.execute(
            "INSERT INTO pypi_universe (pypi_name, last_serial, fetched_at) "
            "VALUES (?, 1, 1)", (name,),
        )
    conn.execute(
        "INSERT INTO upstream_versions (conda_name, source, version, url, fetched_at) "
        "VALUES ('ghtool', 'github', '3.0', 'https://github.com/acme/ghtool.git', 1)"
    )
    conn.execute(
        "INSERT INTO upstream_versions (conda_name, source, version, url, fetched_at) "
        "VALUES ('ghtool', 'npm', '3.0', 'not-a-url', 1)"
    )
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def recipes_dir(tmp_path):
    """Recipes tree exercising the exceptions branches: a not-on-cf conda
    name, both D1 pypi branches (dotted-present → NO line; absent → line),
    and one unparseable recipe.yaml."""
    root = tmp_path / "recipes"

    def _recipe(dirname: str, body: str) -> None:
        d = root / dirname
        d.mkdir(parents=True)
        (d / "recipe.yaml").write_text(body, encoding="utf-8")

    _recipe("pending-pkg", (
        "package: {name: pending-pkg}\n"
        "extra:\n"
        "  cfe-conda-name: pending-pkg\n"
        "  cfe-on-conda-forge-status: pending-submission-to-conda-forge\n"
    ))
    _recipe("dotted-ok", (
        "package: {name: dotted}\n"
        "extra:\n"
        "  cfe-conda-name: dotted\n"
        "  cfe-upstream-registry: pypi\n"
        "  cfe-upstream-name: pymilvus.model\n"
        "  cfe-on-conda-forge-status: blocked-pending-prerequisites\n"
    ))
    _recipe("dotted-missing", (
        "package: {name: foo}\n"
        "extra:\n"
        "  cfe-conda-name: foo\n"
        "  cfe-upstream-registry: pypi\n"
        "  cfe-upstream-name: genuinely.absent\n"
        "  cfe-on-conda-forge-status: pending-submission-to-conda-forge\n"
    ))
    _recipe("badyaml", "package: {name: [unclosed\n")
    _recipe("not-flagged", (
        "package: {name: whatever}\n"
        "extra:\n"
        "  cfe-on-conda-forge-status: confirmed-on-conda-forge\n"
    ))
    return root


def _export(cli_mod, db, tmp_path, recipes_dir):
    out = tmp_path / "out"
    return cli_mod.export_all(db, out, recipes_dir=recipes_dir), out


class TestCondaArtifacts:
    def test_population_and_channel_qualifier(self, db, cli_mod, tmp_path, recipes_dir):
        _, out = _export(cli_mod, db, tmp_path, recipes_dir)
        lines = (out / "purls_conda-forge.txt").read_text().splitlines()
        names = {ln.split("/", 1)[1].split("?")[0] for ln in lines}
        assert "oldie" in names, "archived-but-active must be INCLUDED"
        assert "gone" not in names, "latest_status='archived' must be EXCLUDED"
        assert all(ln.endswith("?channel=conda-forge") for ln in lines)

    def test_sorted_by_name_never_full_line(self, db, cli_mod, tmp_path, recipes_dir):
        _, out = _export(cli_mod, db, tmp_path, recipes_dir)
        lines = (out / "purls_conda-forge.txt").read_text().splitlines()
        foo = lines.index("pkg:conda/foo?channel=conda-forge")
        foobar = lines.index("pkg:conda/foo-bar?channel=conda-forge")
        assert foo < foobar, "by-name order puts `foo` before `foo-bar`"
        # Full-line C-sort would flip the pair (`-` 0x2D < `?` 0x3F).
        assert lines != sorted(lines)

    def test_versioned_parity_and_null_version(self, db, cli_mod, tmp_path, recipes_dir):
        _, out = _export(cli_mod, db, tmp_path, recipes_dir)
        plain = (out / "purls_conda-forge.txt").read_text().splitlines()
        versioned = (out / "purls_conda-forge_versioned.txt").read_text().splitlines()
        assert len(plain) == len(versioned), "count parity asserted by contract"
        assert "pkg:conda/noversion?channel=conda-forge" in versioned
        assert "pkg:conda/foo@1.0?channel=conda-forge" in versioned


class TestPypiArtifact:
    def test_g98_dots_preserved(self, db, cli_mod, tmp_path, recipes_dir):
        _, out = _export(cli_mod, db, tmp_path, recipes_dir)
        lines = (out / "purls_pypi.txt").read_text().splitlines()
        assert "pkg:pypi/fs.googledrivefs" in lines
        assert "pkg:pypi/pymilvus.model" in lines
        assert lines == sorted(lines), "artifact #3 is full-line C-sort"


class TestMappedTsv:
    def test_header_and_none_passthrough(self, db, cli_mod, tmp_path, recipes_dir):
        _, out = _export(cli_mod, db, tmp_path, recipes_dir)
        lines = (out / "purls_conda-pypi_mapped.tsv").read_text().splitlines()
        assert lines[0] == "conda_purl\tpypi_purl\tmatch_source\tmatch_confidence"
        none_rows = [ln for ln in lines if "\tnone\tn/a" in ln]
        assert none_rows, "`match_source='none'` rows are passthrough, not filtered"
        assert any("pkg:pypi/fs.googledrivefs" in ln for ln in lines)


class TestExceptions:
    def test_d1_both_branches_and_not_on_cf(self, db, cli_mod, tmp_path, recipes_dir):
        result, out = _export(cli_mod, db, tmp_path, recipes_dir)
        lines = (out / "recipe-purl-exceptions.txt").read_text().splitlines()
        joined = "\n".join(lines)
        # D1 branch 1: dotted name IS in the universe → zero pypi: lines for it.
        assert "pymilvus.model" not in joined
        # D1 branch 2: genuinely absent name → line emitted (branch stays alive).
        assert "dotted-missing: pypi:genuinely.absent not-in-pypi-export" in lines
        assert ("pending-pkg: conda:pending-pkg not-on-cf "
                "(status=pending-submission-to-conda-forge)") in lines
        assert result["recipes_parse_errors"] == 1
        assert result["recipes_scanned"] == 5


class TestUpstreamTsv:
    def test_github_row_and_unparseable_skip(self, db, cli_mod, tmp_path, recipes_dir):
        result, out = _export(cli_mod, db, tmp_path, recipes_dir)
        lines = (out / "purls_conda-upstream_mapped.tsv").read_text().splitlines()
        assert lines[0] == "conda_purl\tupstream_purl\tupstream_source"
        assert ("pkg:conda/ghtool?channel=conda-forge\t"
                "pkg:github/acme/ghtool\tgithub") in lines
        assert result["unparseable_upstream"] == 1


class TestDeterminismAndReport:
    def test_double_run_byte_identical(self, db, cli_mod, tmp_path, recipes_dir):
        _, out = _export(cli_mod, db, tmp_path, recipes_dir)
        first = {p.name: p.read_bytes() for p in out.iterdir()}
        result2 = cli_mod.export_all(db, out, recipes_dir=recipes_dir)
        second = {p.name: p.read_bytes() for p in out.iterdir()}
        assert first == second
        for info in result2["artifacts"].values():
            assert info["previous_lines"] == info["lines"]

    def test_previous_lines_none_on_first_run(self, db, cli_mod, tmp_path, recipes_dir):
        result, _ = _export(cli_mod, db, tmp_path, recipes_dir)
        assert all(i["previous_lines"] is None for i in result["artifacts"].values())


class TestUpstreamPurlHelper:
    @pytest.mark.parametrize("source,url,expected", [
        ("github", "https://github.com/acme/tool.git", "pkg:github/acme/tool"),
        # purl-spec: github namespace/name lowercased.
        ("github", "https://github.com/Acme/CoolTool", "pkg:github/acme/cooltool"),
        # purl-spec: npm scope `@` percent-encoded.
        ("npm", "https://registry.npmjs.org/@scope/pkg", "pkg:npm/%40scope/pkg"),
        ("npm", "https://registry.npmjs.org/plainpkg", "pkg:npm/plainpkg"),
        ("crates", "https://crates.io/api/v1/crates/serde", "pkg:cargo/serde"),
        ("rubygems", "https://rubygems.org/api/v1/gems/rails.json", "pkg:gem/rails"),
        ("maven", "https://repo1.maven.org/maven2/org/apache/foo/bar/maven-metadata.xml",
         "pkg:maven/org.apache.foo/bar"),
        # purl-spec: qualifier value percent-encoded.
        ("gitlab", "https://gitlab.com/grp/proj",
         "pkg:generic/proj?vcs_url=git%2Bhttps%3A%2F%2Fgitlab.com%2Fgrp%2Fproj"),
        # host-only URL: no repo to name → skip, not a nonsense purl.
        ("gitlab", "https://gitlab.com/", None),
        ("github", "https://example.com/nope", None),
        ("npm", "garbage", None),
    ])
    def test_mapping(self, cli_mod, source, url, expected):
        assert cli_mod.upstream_purl(source, url) == expected


class TestMissingDb:
    def test_rc_1(self, cli_mod, tmp_path, monkeypatch):
        monkeypatch.setattr(cli_mod, "DB_PATH", tmp_path / "missing.db")
        monkeypatch.setattr(sys, "argv", ["export_purls"])
        assert cli_mod.main() == 1


class TestEmptyUniverseGuard:
    def test_refuses_export_rc_1(self, cli_mod, atlas_mod, tmp_path, monkeypatch):
        """Empty pypi_universe (lean daily Phase D only): refuse to
        overwrite good artifacts with degraded output."""
        db_path = tmp_path / "cf_atlas.db"
        conn = atlas_mod.open_db(db_path)
        atlas_mod.init_schema(conn)
        conn.commit()
        conn.close()
        out = tmp_path / "out"
        monkeypatch.setattr(cli_mod, "DB_PATH", db_path)
        monkeypatch.setattr(sys, "argv", ["export_purls", "--out-dir", str(out)])
        assert cli_mod.main() == 1
        assert not out.exists(), "no artifacts may be written on refusal"


class TestG98Dedupe:
    def test_case_variants_collapse_to_one_line(self, atlas_mod, cli_mod, tmp_path):
        conn = atlas_mod.open_db(tmp_path / "dedupe.db")
        atlas_mod.init_schema(conn)
        for name in ("Foo_Bar", "foo-bar"):
            conn.execute(
                "INSERT INTO pypi_universe (pypi_name, last_serial, fetched_at) "
                "VALUES (?, 1, 1)", (name,),
            )
        conn.commit()
        lines = cli_mod.pypi_purl_lines(conn)
        assert lines == ["pkg:pypi/foo-bar"]
        conn.close()


class TestNonDictPackageKey:
    def test_warns_not_crashes(self, db, cli_mod, tmp_path):
        root = tmp_path / "r2"
        d = root / "weird"
        d.mkdir(parents=True)
        (d / "recipe.yaml").write_text(
            "package: just-a-string\n"
            "extra:\n"
            "  cfe-on-conda-forge-status: pending-submission-to-conda-forge\n",
            encoding="utf-8",
        )
        lines, scanned, errors = cli_mod.recipe_exception_lines(
            root, conda_names=set(), pypi_fold_index=set()
        )
        assert scanned == 1 and errors == 0
        # falls back to the dir name; flagged as not-on-cf, no AttributeError
        assert lines == ["weird: conda:weird not-on-cf "
                         "(status=pending-submission-to-conda-forge)"]
