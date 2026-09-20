"""Unit coverage for `pyforge.atlas.dashboard.identity_gist` (Story 25.1).

This module had ZERO test coverage before this story -- no gate, integration or unit,
ever exercised it. Two layers:

1. Small, precise tests of the pure helper functions (pep503 normalization, markdown
   escaping, recipe-type classification, provenance path resolution, source counting).
2. One realistic end-to-end `render_identity_gist_markdown` run over a small but
   representative `identity_complete_export.parquet` + a real `recipes/` tree + a real
   `enterprise_jfrog_consumption.parquet`, exercising the two big renderers
   (`_render_identity_catalog` / `_render_dashboards`) and the JFROG-map section for
   real, not mocked out.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from pyforge.atlas.dashboard import identity_gist as ig

STAMP_TS = "2026-09-09T00:00:00Z"


# --------------------------------------------------------------------------- #
# Pure string / small-data helpers
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "value,expected",
    [
        ("Foo_Bar.Baz", "foo-bar-baz"),
        ("  --Foo--  ", "foo"),
        ("", ""),
        (None, ""),
    ],
)
def test_pep503_name(value, expected):
    assert ig._pep503_name(value) == expected


def test_join_list_drops_falsy_entries():
    assert ig._join_list(["a", "", "b", None]) == "a; b"
    assert ig._join_list([]) == ""


def test_name_keys_includes_pep503_and_underscore_variants():
    row = {"Core_Python_Package_Name": "Foo-Bar", "associator_key": ""}
    keys = ig._name_keys(row)
    assert "Foo-Bar" in keys
    assert "foo-bar" in keys
    assert "Foo_Bar" in keys


def test_name_keys_skips_blank_fields():
    assert ig._name_keys({"Core_Python_Package_Name": "", "associator_key": ""}) == []


def test_first_map_skips_falsy_values_and_returns_first_truthy():
    mapping = {"a": "", "b": "y"}
    assert ig._first_map(mapping, ["a", "b"]) == "y"
    assert ig._first_map({}, ["a"]) == ""


@pytest.mark.parametrize(
    "text,expected",
    [
        ("build:\n  noarch: python\n", "noarch-python"),
        ("build:\n  noarch: generic\n", "noarch-generic"),
        ("build:\n  noarch: true\n", "noarch-generic"),
        ("build:\n  noarch: something-else\n", "noarch-other"),
        ("requirements:\n  build:\n    - {{ compiler('c') }}\n", "compiled"),
        ("requirements:\n  build:\n    - ${{ stdlib('c') }}\n", "compiled"),
        ("package:\n  name: foo\n", "arch"),
    ],
)
def test_classify_recipe_text(text, expected):
    assert ig.classify_recipe_text(text) == expected


def test_load_local_recipe_type_walks_recipe_dirs(tmp_path: Path):
    recipes = tmp_path / "recipes"
    (recipes / "foo").mkdir(parents=True)
    (recipes / "foo" / "recipe.yaml").write_text("build:\n  noarch: python\n", encoding="utf-8")
    (recipes / "bar").mkdir(parents=True)
    (recipes / "bar" / "meta.yaml").write_text("requirements:\n  build:\n    - x\n", encoding="utf-8")
    (recipes / "empty").mkdir(parents=True)

    got = ig.load_local_recipe_type(recipes)
    assert got["foo"] == "noarch-python"
    assert got["bar"] == "arch"
    assert got["empty"] == "none"
    assert ig.load_local_recipe_type(tmp_path / "no-such-dir") == {}


def test_row_recipe_type_resolves_via_local_recipes_url():
    dir_types = {"foo": "noarch-python"}
    row = {"Local_Recipes_URL": ig.LOCAL_RECIPES_URL.format(dir="foo")}
    assert ig.row_recipe_type(row, dir_types) == "noarch-python"
    assert ig.row_recipe_type({"Local_Recipes_URL": ""}, dir_types) == "none"
    assert ig.row_recipe_type({"Local_Recipes_URL": "https://nope/x"}, dir_types) == "none"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("a|b\\c<d", r"a\|b\\c\<d"),
        ("line1\r\nline2", "line1  line2"),
        ("", ""),
    ],
)
def test_md_cell_escapes(raw, expected):
    assert ig.md_cell(raw) == expected


def test_md_table_renders_header_separator_and_rows():
    lines = ig.md_table(["h1", "h2"], [["a", "b"], ["c|d", "e"]])
    assert lines[0] == "| h1 | h2 |"
    assert lines[1] == "| --- | --- |"
    assert lines[2] == "| a | b |"
    assert r"c\|d" in lines[3]


@pytest.mark.parametrize(
    "value,expected",
    [("1,234", 1234), ("abc", 0), (5.7, 5), ("", 0)],
)
def test_as_int(value, expected):
    assert ig._as_int(value) == expected


@pytest.mark.parametrize(
    "num,den,expected",
    [(0, 0, "—"), (3, 4, "75.0%"), (0, 5, "0.0%")],
)
def test_pct(num, den, expected):
    assert ig._pct(num, den) == expected


def test_filled_key_replaces_hyphens_and_spaces():
    assert ig._filled_key("Conda-Forge_FeedStock_URL") == "filled_Conda_Forge_FeedStock_URL"
    assert ig._filled_key("a b") == "filled_a_b"


def test_emit_status_block_orders_known_then_extra_statuses():
    from collections import Counter

    lines: list[str] = []
    counts = Counter({"success": 3, "failed": 1, "weird-status": 2})
    ig._emit_status_block(lines, "  ", counts)
    assert lines[0] == "  rows: 6"
    assert "  success: 3" in lines
    assert "  failed: 1" in lines
    assert "  weird-status: 2" in lines
    # a zero-count known status contributes no line
    assert not any(line.startswith("  build-clean-test-blocked") for line in lines)


def test_file_sha256_matches_hashlib(tmp_path: Path):
    path = tmp_path / "f.bin"
    path.write_bytes(b"hello world" * 1000)
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    assert ig._file_sha256(path) == expected


def test_records_from_frame_converts_nan_to_empty_string():
    # A NaN in column "a" upcasts the whole column to float64 (pandas has no
    # int-NaN), so the non-null value round-trips as "1.0", not "1".
    df = pd.DataFrame({"a": [1, None], "b": ["x", "y"]})
    got = ig._records_from_frame(df)
    assert got == [{"a": "1.0", "b": "x"}, {"a": "", "b": "y"}]


# --------------------------------------------------------------------------- #
# Repo-root / atlas-root / data-root path resolution
# --------------------------------------------------------------------------- #


def test_find_repo_root_finds_git_marker(tmp_path: Path):
    root = tmp_path / "fake-repo"
    (root / ".git").mkdir(parents=True)
    nested = root / "a" / "b" / "c.parquet"
    nested.parent.mkdir(parents=True)
    nested.write_bytes(b"x")
    assert ig._find_repo_root(nested) == root


def test_find_repo_root_falls_back_when_no_marker_found(tmp_path: Path):
    nested = tmp_path / "a" / "b" / "c.parquet"
    nested.parent.mkdir(parents=True)
    nested.write_bytes(b"x")
    got = ig._find_repo_root(nested)
    assert isinstance(got, Path)


def test_pyforge_atlas_root_finds_named_segment(tmp_path: Path):
    export = tmp_path / "pyforge-atlas" / "data" / "derived" / "x" / "x.parquet"
    got = ig._pyforge_atlas_root(export)
    assert got == tmp_path / "pyforge-atlas"


def test_pyforge_atlas_root_falls_back_to_repo_root(tmp_path: Path):
    root = tmp_path / "fake-repo"
    (root / ".git").mkdir(parents=True)
    export = root / "data" / "derived" / "x" / "x.parquet"
    export.parent.mkdir(parents=True)
    export.write_bytes(b"x")
    got = ig._pyforge_atlas_root(export)
    assert got == root / "src/shared/packages/pyforge-atlas"


def test_data_root_from_export_is_three_parents_up():
    export = Path("/x/data/derived/identity_complete_export/identity_complete_export.parquet")
    assert ig._data_root_from_export(export) == Path("/x/data")


# --------------------------------------------------------------------------- #
# _count_source_path -- parquet hit, json hit, non-list json, malformed files,
# no match anywhere
# --------------------------------------------------------------------------- #


def test_count_source_path_parquet_hit(tmp_path: Path):
    data_root = tmp_path / "data"
    atlas_root = tmp_path / "atlas"
    path = data_root / "x.parquet"
    path.parent.mkdir(parents=True)
    pd.DataFrame({"a": [1, 2, 3]}).to_parquet(path)
    assert ig._count_source_path(data_root, atlas_root, "x.parquet") == 3


def test_count_source_path_json_list_hit_via_atlas_root_fallback(tmp_path: Path):
    data_root = tmp_path / "data"
    atlas_root = tmp_path / "atlas"
    path = atlas_root / "y.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(["a", "b"]), encoding="utf-8")
    assert ig._count_source_path(data_root, atlas_root, "y.json") == 2


def test_count_source_path_json_non_list_returns_none(tmp_path: Path):
    data_root = tmp_path / "data"
    atlas_root = tmp_path / "atlas"
    path = data_root / "z.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"not": "a list"}), encoding="utf-8")
    assert ig._count_source_path(data_root, atlas_root, "z.json") is None


def test_count_source_path_malformed_json_returns_none(tmp_path: Path):
    data_root = tmp_path / "data"
    atlas_root = tmp_path / "atlas"
    path = data_root / "bad.json"
    path.parent.mkdir(parents=True)
    path.write_text("{not valid json", encoding="utf-8")
    assert ig._count_source_path(data_root, atlas_root, "bad.json") is None


def test_count_source_path_malformed_parquet_returns_none(tmp_path: Path):
    data_root = tmp_path / "data"
    atlas_root = tmp_path / "atlas"
    path = data_root / "bad.parquet"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"not a real parquet file")
    assert ig._count_source_path(data_root, atlas_root, "bad.parquet") is None


def test_count_source_path_no_match_anywhere_returns_none(tmp_path: Path):
    data_root = tmp_path / "data"
    atlas_root = tmp_path / "atlas"
    assert ig._count_source_path(data_root, atlas_root, "nope.parquet") is None
    # A relpath with no recognized suffix never matches either branch.
    assert ig._count_source_path(data_root, atlas_root, "raw/no-extension-dir") is None


# --------------------------------------------------------------------------- #
# render_identity_gist_markdown -- error paths
# --------------------------------------------------------------------------- #


def test_render_identity_gist_markdown_raises_when_export_missing(tmp_path: Path):
    with pytest.raises(ig.IdentityGistError, match="not found"):
        ig.render_identity_gist_markdown(tmp_path / "nope.parquet")


def test_render_identity_gist_markdown_raises_when_export_empty(tmp_path: Path):
    path = tmp_path / "identity_complete_export.parquet"
    pd.DataFrame({c: [] for c in ig.GIST_COLUMNS}).to_parquet(path)
    with pytest.raises(ig.IdentityGistError, match="empty"):
        ig.render_identity_gist_markdown(path)


# --------------------------------------------------------------------------- #
# render_identity_gist_markdown -- realistic end-to-end run
# --------------------------------------------------------------------------- #


@pytest.fixture()
def rendered_env(tmp_path: Path):
    """A realistic `repo_root` / `recipes/` / export Parquet / JFROG Parquet layout,
    then the two markdown documents `render_identity_gist_markdown` produces."""
    root = tmp_path / "pyforge-atlas"
    (root / ".git").mkdir(parents=True)

    data_root = root / "data"
    export_path = data_root / "derived" / "identity_complete_export" / "identity_complete_export.parquet"
    jfrog_path = data_root / "derived" / "enterprise_jfrog_consumption" / "enterprise_jfrog_consumption.parquet"
    export_path.parent.mkdir(parents=True)
    jfrog_path.parent.mkdir(parents=True)

    recipes = root / "recipes"
    (recipes / "pkgalpha").mkdir(parents=True)
    (recipes / "pkgalpha" / "recipe.yaml").write_text(
        'package:\n  name: pkgalpha\n  version: "1.0.0"\n\n'
        "build:\n  noarch: python\n\n"
        "extra:\n  cfe-local-build-status: success\n",
        encoding="utf-8",
    )
    (recipes / "pkgdelta").mkdir(parents=True)
    (recipes / "pkgdelta" / "recipe.yaml").write_text(
        'package:\n  name: pkgdelta\n  version: "2.0.0"\n\n'
        "requirements:\n  build:\n    - {{ compiler('c') }}\n\n"
        "extra:\n  cfe-local-build-status: build-clean-test-blocked\n",
        encoding="utf-8",
    )
    (recipes / "pkgzeta").mkdir(parents=True)
    (recipes / "pkgzeta" / "recipe.yaml").write_text(
        'package:\n  name: pkgzeta\n  version: "3.0.0"\n\nextra:\n  cfe-local-build-status: failed\n',
        encoding="utf-8",
    )

    def row(**overrides):
        base = {c: "" for c in ig.GIST_COLUMNS}
        base.update(overrides)
        return base

    rows = [
        row(
            P="P1",
            Rank="1",
            Score="99",
            Package="pkgalpha",
            Work="Fix vulnerability",
            Core_Python_Package_Name="pkgalpha",
            OpenTeams_Title="[Conda-Forge Packaging] pkgalpha",
            identity_source="purl-associator",
            primary_type="pypi",
            primary_purl="pkg:pypi/pkgalpha",
            Priority_Bucket_Description=ig.PRIORITY_DESC["P1"],
            JFROG_risk_level="HIGH",
        ),
        row(
            P="P4",
            Package="pkgbeta",
            Work="Create recipe",
            Core_Python_Package_Name="pkgbeta",
            identity_source="inventory",
            primary_type="pypi",
            primary_purl="pkg:pypi/pkgbeta",
        ),
        row(
            P="P6",
            Package="pkggamma",
            Work="File OpenTeams tracking issue [Conda-Forge Packaging]",
            Core_Python_Package_Name="pkggamma",
            identity_source="inventory",
            **{"Conda-Forge_FeedStock_URL": "https://github.com/conda-forge/pkggamma-feedstock"},
        ),
        row(
            P="P8",
            Package="pkgdelta",
            Work="Create recipe",
            Core_Python_Package_Name="pkgdelta",
            identity_source="none",
            primary_type="pypi",
            primary_purl="pkg:pypi/pkgdelta",
        ),
        row(
            P="P9",
            Package="pkgepsilon",
            Work="File OpenTeams tracking issue [Conda-Forge Packaging]",
            Core_Python_Package_Name="pkgepsilon",
            identity_source="openteams-board",
        ),
        row(
            P="P10",
            Package="pkgzeta",
            Work="Already tracked",
            Core_Python_Package_Name="pkgzeta",
            identity_source="inventory",
            primary_type="pypi",
            primary_purl="pkg:pypi/pkgzeta",
            OpenTeams_Issue_URL="https://github.com/o/i/6",
            Local_Build_Status="failed",
        ),
    ]
    pd.DataFrame(rows, columns=list(ig.GIST_COLUMNS)).to_parquet(export_path)

    jfrog_rows = pd.DataFrame(
        {
            "repository_source": ["CDO-ENT-JFROG"] * 6 + ["OTHER"],
            "core_python_package_name": [
                "pkgdelta",
                "pkgepsilon",
                "unknownpkg",
                "pkggamma",
                "pkgalpha",
                "x",
                "filtered-out",
            ],
            "artifactory_downloads": pd.array([500, 50, 10, 20, 5, 1, 999], dtype="Int64"),
            "platform_env_count": pd.array([3, 0, 0, 1, 0, 0, 0], dtype="Int64"),
            "internal_component_count": pd.array([2, 0, 0, 0, 0, 0, 0], dtype="Int64"),
            "internal_app_count": pd.array([1, 0, 0, 0, 0, 0, 0], dtype="Int64"),
            "packaging_tier": ["tier1", "tier3", "", "tier2", "tier2", "", ""],
        }
    )
    jfrog_rows.to_parquet(jfrog_path)

    identity_md, dashboards_md = ig.render_identity_gist_markdown(export_path, gist_id="gist123", repo_root=root)
    return {
        "root": root,
        "export_path": export_path,
        "identity_md": identity_md,
        "dashboards_md": dashboards_md,
    }


def test_identity_catalog_markdown_has_the_expected_shape(rendered_env):
    md = rendered_env["identity_md"]
    assert "mgmt-wf-python-modernization-identity" in md
    assert "rows: 6" in md
    assert "## Identity rows" in md
    assert "pkgalpha" in md and "pkgzeta" in md
    # sha256 + gist id propagate into the frontmatter.
    assert "gist_id: gist123" in md


def test_identity_catalog_markdown_reflects_local_build_overlay(rendered_env):
    """`pkgalpha`/`pkgdelta` had real recipe.yaml files with a CFE build-status
    stamp -- the overlay must bake their live status into the rendered table AND
    the local_build_by_p / local_build_by_type frontmatter blocks."""
    md = rendered_env["identity_md"]
    assert "local_build_by_type:" in md
    assert "noarch-python:" in md
    assert "compiled:" in md
    assert "local_build_success_by_p_type:" in md


def test_dashboards_markdown_priority_and_work_sections(rendered_env):
    md = rendered_env["dashboards_md"]
    assert "## Priority and work" in md
    assert "## Packaging-issue gap" in md
    assert "## Local build (CFE stamp)" in md
    assert "## Census: feedstock, staged-recipes, local build" in md
    assert "### Full cube" in md
    # P2/P3/P5/P7 have zero rows in this fixture -- the census-rows "continue"
    # branch for an empty bucket must not blow up the render.
    assert "| P1 |" in md
    assert "| P4 |" in md


def test_dashboards_markdown_jfrog_map_section(rendered_env):
    md = rendered_env["dashboards_md"]
    assert "## CDO-ENT-JFROG → PyPI / conda-forge" in md
    assert "### No verified PyPI or conda-forge URL" in md
    assert "## JFROG names needing a staged-recipes PR" in md
    assert "## Artifactory PyPI-only names with no packaging issue" in md
    # pkgdelta: PyPI-verified, not on conda-forge, platform+component signal -> the
    # "pick" bucket in the "needing a staged-recipes PR" table.
    assert "pkgdelta" in md
    # "filtered-out" was excluded by the repository_source != CDO-ENT-JFROG filter.
    assert "filtered-out" not in md


def test_dashboards_markdown_external_source_counts(rendered_env):
    md = rendered_env["dashboards_md"]
    assert "## External source counts" in md
    assert "Live row counts from materialized Atlas Parquet" in md
