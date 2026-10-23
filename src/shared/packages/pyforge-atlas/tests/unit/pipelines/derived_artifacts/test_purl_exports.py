"""Story 37.8 — legacy export-purls' six artifacts and their manifest."""

from __future__ import annotations

import pandas as pd
import pytest

from pyforge.atlas.pipelines.derived_artifacts import purl_exports as px

NOW = 1_700_000_000


def _enumerated(rows: list[tuple[str, str | None]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["conda_name", "latest_version"])


def _status(rows: list[tuple[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["conda_name", "latest_status"])


def _mapping(rows: list[tuple[str, str, str]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["conda_name", "pypi_name", "match_source"])


def _graph(rows: list[tuple[str, str | None, str | None]]) -> pd.DataFrame:
    """``(conda_name, repo_url, source_url)`` as cf-graph anchor rows, one feedstock each."""
    return pd.DataFrame(
        [
            {"feedstock_name": f"{n}-feedstock", "conda_name": n, "depends_on": None, "repo_url": r, "source_url": s}
            for n, r, s in rows
        ]
    )


def _export(**kwargs) -> tuple[dict[str, list[str]], pd.DataFrame]:
    args = {
        "core_packages_enumerated": None,
        "core_latest_status": None,
        "pypi_conda_mapping": None,
        "pypi_universe": None,
        "discovery_recipe_extras_raw": None,
        "core_cf_graph_raw": None,
        "core_feedstock_attribution": None,
    }
    args.update(kwargs)
    partitions, manifest = px.export_purl_artifacts(**args, now=NOW)
    assert set(partitions) == set(px.ARTIFACTS)
    return {name: text.splitlines() for name, text in partitions.items()}, manifest


def test_conda_purls_cover_the_active_packages_in_c_locale_name_order():
    got, _ = _export(
        core_packages_enumerated=_enumerated([("foo-bar", "2"), ("foo", "1"), ("Zed", None), ("gone", "9")]),
        core_latest_status=_status([("foo-bar", "active"), ("foo", "active"), ("Zed", "active"), ("gone", "inactive")]),
    )
    # by name, not by line: foo before foo-bar (a full-line sort would put "?" after "-")
    assert got["purls_conda-forge.txt"] == [
        "pkg:conda/Zed?channel=conda-forge",
        "pkg:conda/foo?channel=conda-forge",
        "pkg:conda/foo-bar?channel=conda-forge",
    ]
    assert got["purls_conda-forge_versioned.txt"] == [
        "pkg:conda/Zed?channel=conda-forge",
        "pkg:conda/foo@1?channel=conda-forge",
        "pkg:conda/foo-bar@2?channel=conda-forge",
    ]


def test_without_a_status_every_enumerated_package_is_active():
    got, _ = _export(core_packages_enumerated=_enumerated([("a", "1")]))
    assert got["purls_conda-forge.txt"] == ["pkg:conda/a?channel=conda-forge"]


def test_pypi_purls_are_g98_normalized_deduplicated_and_full_line_sorted():
    universe = pd.DataFrame({"pypi_name": ["Zope.Interface", "zope.interface", "my_pkg", "a-b"]})
    got, _ = _export(pypi_universe=universe)
    assert got["purls_pypi.txt"] == ["pkg:pypi/a-b", "pkg:pypi/my-pkg", "pkg:pypi/zope.interface"]


def test_the_mapping_tsv_passes_provenance_through_with_a_header():
    got, _ = _export(
        core_packages_enumerated=_enumerated([("b", "1"), ("a", "1"), ("off", "1")]),
        core_latest_status=_status([("b", "active"), ("a", "active"), ("off", "inactive")]),
        pypi_conda_mapping=_mapping(
            [("b", "B_Pkg", "parselmouth"), ("a", "a", "recipe_source_url"), ("off", "off", "x"), ("a", "", "x")]
        ),
    )
    assert got["purls_conda-pypi_mapped.tsv"] == [
        px.MAPPED_TSV_HEADER,
        "pkg:conda/a?channel=conda-forge\tpkg:pypi/a\trecipe_source_url\t",
        "pkg:conda/b?channel=conda-forge\tpkg:pypi/b-pkg\tparselmouth\t",
    ]


def _extras(rows: list[tuple]) -> pd.DataFrame:
    return pd.DataFrame(
        rows, columns=["dir_name", "conda_name", "status", "upstream_registry", "upstream_name", "parse_error"]
    )


def test_recipe_exceptions_are_legacys():
    got, _ = _export(
        core_packages_enumerated=_enumerated([("onpypi", "1"), ("missing-upstream", "1")]),
        pypi_universe=pd.DataFrame({"pypi_name": ["On_PyPI"]}),
        discovery_recipe_extras_raw=_extras(
            [
                ("zz-new", "brand-new", "pending-review", None, None, False),
                # not pending or blocked: never an exception, even when it is not on conda-forge
                ("ok-built", "built-elsewhere", "built", None, None, False),
                ("aa-pypi", "onpypi", "pending-merge", "pypi", "on.pypi", False),
                ("bb-pypi", "missing-upstream", "blocked-license", "pypi", None, False),
            ]
        ),
    )
    assert got["recipe-purl-exceptions.txt"] == [
        "bb-pypi: pypi:missing-upstream not-in-pypi-export",
        "zz-new: conda:brand-new not-on-cf (status=pending-review)",
    ]


@pytest.mark.parametrize(
    ("source", "url", "purl"),
    [
        ("github", "https://github.com/Owner/Repo.git", "pkg:github/owner/repo"),
        ("npm", "https://registry.npmjs.org/@scope/name/-/name-1.0.tgz", "pkg:npm/%40scope/name"),
        ("crates", "https://crates.io/api/v1/crates/serde/1.0.0/download", "pkg:cargo/serde"),
        ("rubygems", "https://rubygems.org/gems/rake", "pkg:gem/rake"),
        ("maven", "https://repo1.maven.org/maven2/org/x/y/maven-metadata.xml", "pkg:maven/org.x/y"),
        (
            "gitlab",
            "https://gitlab.com/group/proj",
            "pkg:generic/proj?vcs_url=git%2Bhttps%3A%2F%2Fgitlab.com%2Fgroup%2Fproj",
        ),
        ("gitlab", "https://gitlab.com", None),
        ("github", "https://example.org/x", None),
    ],
)
def test_upstream_purl_is_legacys(source, url, purl):
    assert px.upstream_purl(source, url) == purl


def test_upstream_tsv_lists_unmapped_active_packages_by_their_recipe_urls():
    got, _ = _export(
        core_packages_enumerated=_enumerated([("tool", "1"), ("mapped", "1"), ("nourl", "1")]),
        pypi_conda_mapping=_mapping([("mapped", "mapped", "parselmouth")]),
        core_cf_graph_raw=_graph(
            [
                ("tool", "https://github.com/Org/Tool", "https://registry.npmjs.org/tool/-/tool-1.0.tgz"),
                ("mapped", "https://github.com/org/mapped", None),
                ("nourl", None, "https://example.org/nourl.tar.gz"),
            ]
        ),
    )
    assert got["purls_conda-upstream_mapped.tsv"] == [
        px.UPSTREAM_TSV_HEADER,
        "pkg:conda/tool?channel=conda-forge\tpkg:github/org/tool\tgithub",
        "pkg:conda/tool?channel=conda-forge\tpkg:npm/tool\tnpm",
    ]


def test_recipe_urls_are_split_and_cut_to_their_project():
    got, _ = _export(
        core_packages_enumerated=_enumerated([("r-bindr", "1"), ("eigen", "5"), ("gnutls", "3"), ("bare", "1")]),
        core_cf_graph_raw=_graph(
            [
                ("r-bindr", "https://github.com/krlmlr/bindr, https://krlmlr.github.io/bindr", None),
                ("eigen", None, "https://gitlab.com/libeigen/eigen/-/archive/5.0.1/eigen-5.0.1.tar.gz"),
                ("gnutls", "https://gitlab.com/gnutls/gnutls/tree/master", None),
                ("bare", "https://gitlab.com/onlyone", None),
            ]
        ),
    )
    lines = got["purls_conda-upstream_mapped.tsv"][1:]
    assert lines == [
        "pkg:conda/eigen?channel=conda-forge\tpkg:generic/eigen?vcs_url=git%2Bhttps%3A%2F%2Fgitlab.com%2Flibeigen%2Feigen"
        "\tgitlab",
        "pkg:conda/gnutls?channel=conda-forge\tpkg:generic/gnutls?vcs_url=git%2Bhttps%3A%2F%2Fgitlab.com%2Fgnutls%2Fgnutls"
        "\tgitlab",
        "pkg:conda/r-bindr?channel=conda-forge\tpkg:github/krlmlr/bindr\tgithub",
    ]


@pytest.mark.parametrize(
    ("source", "url", "project"),
    [
        ("gitlab", "https://gitlab.com/group/sub/proj.git", "https://gitlab.com/group/sub/proj"),
        ("codeberg", "https://codeberg.org/o/p/releases/tag/v1", "https://codeberg.org/o/p"),
        ("gitlab", "https://gitlab.com/onlyone", None),
        ("github", "https://github.com/o/r/archive/v1.tar.gz", "https://github.com/o/r/archive/v1.tar.gz"),
    ],
)
def test_project_url(source, url, project):
    assert px.project_url(source, url) == project


def test_two_spellings_that_normalize_alike_are_one_mapping_line():
    got, _ = _export(
        core_packages_enumerated=_enumerated([("a", "1")]),
        pypi_conda_mapping=_mapping([("a", "a_b", "parselmouth"), ("a", "a-b", "recipe_source_url")]),
    )
    assert got["purls_conda-pypi_mapped.tsv"][1:] == ["pkg:conda/a?channel=conda-forge\tpkg:pypi/a-b\tparselmouth\t"]


def test_the_manifest_counts_each_artifact_a_tsv_header_not_counted():
    _, manifest = _export(
        core_packages_enumerated=_enumerated([("a", "1"), ("b", "2")]),
        pypi_conda_mapping=_mapping([("a", "a", "parselmouth")]),
    )
    assert list(manifest.columns) == px.MANIFEST_COLUMNS
    counts = dict(zip(manifest["artifact_name"], manifest["row_count"], strict=True))
    assert counts == {
        "purls_conda-forge.txt": 2,
        "purls_conda-forge_versioned.txt": 2,
        "purls_pypi.txt": 0,
        "purls_conda-pypi_mapped.tsv": 1,
        "recipe-purl-exceptions.txt": 0,
        "purls_conda-upstream_mapped.tsv": 0,
    }
    assert {int(ts.timestamp()) for ts in manifest["regenerated_at"]} == {NOW}


def test_nothing_in_gives_header_only_artifacts_and_a_typed_manifest():
    got, manifest = _export()
    assert got["purls_conda-forge.txt"] == []
    assert got["purls_conda-pypi_mapped.tsv"] == [px.MAPPED_TSV_HEADER]
    assert str(manifest["row_count"].dtype) == "int64"
    assert set(manifest["row_count"]) == {0}


def test_the_board_reads_the_manifest(tmp_path):
    from pyforge.atlas.dashboard import data as dash_data

    _, manifest = _export(core_packages_enumerated=_enumerated([("a", "1")]))
    path = tmp_path / "m.parquet"
    manifest.to_parquet(path, index=False)
    board = dash_data.load_export_purls(path)
    assert len(board) == 6
    assert int(board.loc[board["artifact_name"] == "purls_conda-forge.txt", "row_count"].iloc[0]) == 1
