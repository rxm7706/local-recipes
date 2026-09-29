"""Story 15.2 `kedro-test` gate -- the identity join and internal flag (CAP-2, CAP-3).

Proves the whole CAP-2/CAP-3 success signal offline against hand-constructed
``pd.DataFrame`` fixtures (no catalog, no live tables). One test per I/O & Edge-Case Matrix
row in the story spec, plus a duplicate-name-across-rows passthrough case, plus two tests
proving the provenance-rank collapse (modeled on
``tests/pipelines/pypi_intelligence/test_mapping_export.py``'s
``test_g10_spelling_survives_and_is_not_clobbered`` /
``test_equal_tier_collision_is_order_independent_deterministic``)."""

from __future__ import annotations

import pandas as pd

from pyforge.atlas.artifactory import DownloadRow, JoinedDownloadRow, join_identity

# --- public package, has a feedstock -------------------------------------------------


def test_public_package_with_feedstock_resolves_conda_name_and_is_not_internal():
    rows = [DownloadRow(name="requests", version="2.31.0", download_count=100)]
    mapping = pd.DataFrame(
        {
            "pypi_name": ["requests"],
            "conda_name": ["requests"],
            "match_source": ["parselmouth"],
        }
    )
    universe = pd.DataFrame({"pypi_name": ["requests"], "last_serial": [123]})

    result = join_identity(rows, mapping, universe)

    assert result == [
        JoinedDownloadRow(
            pypi_name="requests",
            version="2.31.0",
            download_count=100,
            conda_name="requests",
            match_source="parselmouth",
            is_internal=False,
        )
    ]


# --- mock-only package -----------------------------------------------------------------


def test_mock_only_package_is_flagged_internal_with_no_mapping():
    rows = [DownloadRow(name="acme-internal-tool", version="1.0.0", download_count=5)]
    mapping = pd.DataFrame({"pypi_name": ["requests"], "conda_name": ["requests"], "match_source": ["parselmouth"]})
    universe = pd.DataFrame({"pypi_name": ["requests"], "last_serial": [123]})

    [result] = join_identity(rows, mapping, universe)

    assert result.conda_name is None
    assert result.match_source is None
    assert result.is_internal is True


# --- public PyPI package, no feedstock ---------------------------------------------------


def test_public_package_without_feedstock_is_not_internal_and_has_no_conda_name():
    rows = [DownloadRow(name="some-pure-pypi-lib", version="0.1.0", download_count=1)]
    mapping = pd.DataFrame({"pypi_name": ["requests"], "conda_name": ["requests"], "match_source": ["parselmouth"]})
    universe = pd.DataFrame({"pypi_name": ["some-pure-pypi-lib"], "last_serial": [99]})

    [result] = join_identity(rows, mapping, universe)

    assert result.conda_name is None
    assert result.match_source is None
    assert result.is_internal is False


# --- casing/separator variant ------------------------------------------------------------


def test_casing_and_separator_variant_matches_via_pep503_fold():
    rows = [DownloadRow(name="My_Package", version="1.0", download_count=1)]
    mapping = pd.DataFrame(
        {"pypi_name": ["my-package"], "conda_name": ["my-package"], "match_source": ["g10_spelling"]}
    )
    universe = pd.DataFrame({"pypi_name": ["my.package"], "last_serial": [1]})

    [result] = join_identity(rows, mapping, universe)

    assert result.conda_name == "my-package"
    assert result.match_source == "g10_spelling"
    assert result.is_internal is False


# --- empty/malformed pypi_universe --------------------------------------------------------


def test_empty_universe_degrades_is_internal_to_false_for_every_row():
    rows = [
        DownloadRow(name="requests", version="2.31.0", download_count=100),
        DownloadRow(name="acme-internal-tool", version="1.0.0", download_count=5),
    ]
    mapping = pd.DataFrame({"pypi_name": ["requests"], "conda_name": ["requests"], "match_source": ["parselmouth"]})

    for empty_universe in (pd.DataFrame(), pd.DataFrame({"last_serial": [1]})):
        result = join_identity(rows, mapping, empty_universe)
        assert [r.is_internal for r in result] == [False, False]
        # identity join against pypi_conda_mapping still runs normally.
        assert result[0].conda_name == "requests"


def test_universe_with_only_null_names_degrades_is_internal_to_false():
    rows = [DownloadRow(name="requests", version="2.31.0", download_count=100)]
    mapping = pd.DataFrame({"pypi_name": [], "conda_name": [], "match_source": []})
    universe = pd.DataFrame({"pypi_name": [None, None], "last_serial": [1, 2]})

    [result] = join_identity(rows, mapping, universe)

    assert result.is_internal is False


# --- empty/malformed pypi_conda_mapping ---------------------------------------------------


def test_empty_mapping_degrades_conda_name_and_match_source_to_none():
    rows = [DownloadRow(name="requests", version="2.31.0", download_count=100)]
    universe = pd.DataFrame({"pypi_name": ["requests"], "last_serial": [123]})

    for empty_mapping in (pd.DataFrame(), pd.DataFrame({"pypi_name": ["requests"]})):
        result = join_identity(rows, empty_mapping, universe)
        assert result[0].conda_name is None
        assert result[0].match_source is None
        # is_internal is still resolved independently against a usable universe.
        assert result[0].is_internal is False


# --- duplicate-name-across-rows passthrough ------------------------------------------------


def test_duplicate_name_across_rows_resolves_each_row_independently():
    rows = [
        DownloadRow(name="requests", version="2.31.0", download_count=100),
        DownloadRow(name="requests", version="2.30.0", download_count=50),
    ]
    mapping = pd.DataFrame({"pypi_name": ["requests"], "conda_name": ["requests"], "match_source": ["parselmouth"]})
    universe = pd.DataFrame({"pypi_name": ["requests"], "last_serial": [123]})

    result = join_identity(rows, mapping, universe)

    assert [(r.version, r.download_count) for r in result] == [("2.31.0", 100), ("2.30.0", 50)]
    assert all(r.conda_name == "requests" and not r.is_internal for r in result)


# --- provenance-rank collapse (added review pass 1) -----------------------------------------


def test_g10_spelling_survives_and_is_not_clobbered_regardless_of_row_order():
    # pypi_name "x" has a g10_spelling row (conda-A) AND a weaker unknown row (conda-B):
    # g10_spelling MUST win regardless of row order (mirrors
    # test_mapping_export.py::test_g10_spelling_survives_and_is_not_clobbered).
    rows = [DownloadRow(name="x", version="1.0", download_count=1)]
    universe = pd.DataFrame({"pypi_name": ["x"], "last_serial": [1]})
    mapping = pd.DataFrame(
        {
            "pypi_name": ["x", "x"],
            "conda_name": ["conda-A", "conda-B"],
            "match_source": ["g10_spelling", "weak_source"],
        }
    )

    [result] = join_identity(rows, mapping, universe)
    assert result.conda_name == "conda-A"
    assert result.match_source == "g10_spelling"

    mapping_rev = mapping.iloc[::-1].reset_index(drop=True)
    [result_rev] = join_identity(rows, mapping_rev, universe)
    assert result_rev.conda_name == "conda-A"
    assert result_rev.match_source == "g10_spelling"


def test_equal_tier_collision_is_order_independent_deterministic():
    # EC7/BH-5 analogue: two SAME-tier rows with different conda_name resolve
    # deterministically (lexicographically smaller wins) regardless of row order (mirrors
    # test_mapping_export.py::test_equal_tier_collision_is_order_independent_deterministic).
    rows = [DownloadRow(name="q", version="1.0", download_count=1)]
    universe = pd.DataFrame({"pypi_name": ["q"], "last_serial": [1]})
    mapping = pd.DataFrame(
        {
            "pypi_name": ["q", "q"],
            "conda_name": ["conda-zzz", "conda-aaa"],
            "match_source": ["parselmouth", "parselmouth"],
        }
    )

    [result] = join_identity(rows, mapping, universe)
    assert result.conda_name == "conda-aaa"

    mapping_rev = mapping.iloc[::-1].reset_index(drop=True)
    [result_rev] = join_identity(rows, mapping_rev, universe)
    assert result_rev.conda_name == "conda-aaa"


def test_equal_tier_same_conda_name_different_match_source_is_order_independent():
    # Review pass 2: two rank-2 sources (parselmouth, recipe_source_url) resolving the SAME
    # conda_name -- match_source must still resolve deterministically (lexicographically
    # smaller wins), regardless of row order, not whichever happened to come first.
    rows = [DownloadRow(name="r", version="1.0", download_count=1)]
    universe = pd.DataFrame({"pypi_name": ["r"], "last_serial": [1]})
    mapping = pd.DataFrame(
        {
            "pypi_name": ["r", "r"],
            "conda_name": ["r-conda", "r-conda"],
            "match_source": ["recipe_source_url", "parselmouth"],
        }
    )

    [result] = join_identity(rows, mapping, universe)
    assert result.conda_name == "r-conda"
    assert result.match_source == "parselmouth"

    mapping_rev = mapping.iloc[::-1].reset_index(drop=True)
    [result_rev] = join_identity(rows, mapping_rev, universe)
    assert result_rev.conda_name == "r-conda"
    assert result_rev.match_source == "parselmouth"


# --- rows=None / empty rows --------------------------------------------------------------


def test_none_rows_returns_empty_list_without_raising():
    mapping = pd.DataFrame({"pypi_name": ["requests"], "conda_name": ["requests"], "match_source": ["parselmouth"]})
    universe = pd.DataFrame({"pypi_name": ["requests"], "last_serial": [123]})

    assert join_identity(None, mapping, universe) == []
    assert join_identity([], mapping, universe) == []
