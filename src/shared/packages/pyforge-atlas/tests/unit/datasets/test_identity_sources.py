"""Story 21.6 (CAP-3, Phase D identity join) dataset tests: PurlAssociatorMappingsDataset,
OpenTeamsBoardDataset, StagedRecipesPRDataset, LocalRecipesOverlayDataset.

Mirrors ``tests/datasets/test_upstream_discovery.py``'s ``AboutMaintainersDataset``
taxonomy for the three ``ExternalRefreshDataset`` subclasses (cadence/force freshness +
AD-13 keep-last-good/never-crash/atomic-write machinery is proven there for the shared
base) — these tests cover each class's OWN fetch/parse/persist contract. All IO is via
injected stubs — never a real network call.
"""

from __future__ import annotations

import pandas as pd
import pytest

from pyforge.atlas.datasets import RefreshRequest
from pyforge.atlas.datasets.identity_sources import (
    LocalRecipesOverlayDataset,
    OpenTeamsBoardDataset,
    PurlAssociatorMappingsDataset,
    StagedRecipesPRDataset,
    parse_openteams_board_nodes,
    parse_pr_files_response,
    parse_purl_associator_index,
    parse_recipe_dir,
    parse_staged_pr_page,
)

ASSOC_URL = "https://prefix-dev.github.io/purl-associator/mappings-index.json"
BOARD_URL = "https://api.github.com/graphql"
STAGED_URL = "https://api.github.com"


# ---------------------------------------------------------------------------
# parse_purl_associator_index / PurlAssociatorMappingsDataset
# ---------------------------------------------------------------------------

_ASSOC_PAYLOAD = {
    "packages": {
        "requests": {
            "purl": "pkg:pypi/requests",
            "type": "pypi",
            "status": "confirmed",
            "alternative_purls": ["pkg:github/psf/requests", {"purl": "pkg:conda/requests"}],
            "cpes": ["cpe:2.3:a:python:requests"],
        },
        "not-a-dict": "oops",
    },
    "not-a-key": 1,
}


def test_parse_purl_associator_index_extracts_rows_and_joins_lists():
    rows = parse_purl_associator_index(_ASSOC_PAYLOAD)
    assert len(rows) == 1
    row = rows[0]
    assert row["assoc_key"] == "requests"
    assert row["purl"] == "pkg:pypi/requests"
    assert row["alternative_purls"] == "pkg:github/psf/requests; pkg:conda/requests"
    assert row["cpes"] == "cpe:2.3:a:python:requests"


def test_parse_purl_associator_index_accepts_raw_json_text():
    import json

    rows = parse_purl_associator_index(json.dumps(_ASSOC_PAYLOAD))
    assert len(rows) == 1


@pytest.mark.parametrize("payload", [None, "not json", {"packages": "not-a-dict"}, {}, []])
def test_parse_purl_associator_index_malformed_payload_returns_empty(payload):
    assert parse_purl_associator_index(payload) == []


def _assoc(path, *, fetcher=None) -> PurlAssociatorMappingsDataset:
    return PurlAssociatorMappingsDataset(filepath=str(path), url=ASSOC_URL, fetcher=fetcher)


def test_assoc_constructs_offline_no_refresher(tmp_path):
    ds = _assoc(tmp_path / "assoc")
    assert ds._describe()["refresher_wired"] is False
    assert ds._describe()["url"] == ASSOC_URL


def test_assoc_fetch_success_persists_and_not_stale(tmp_path):
    ds = _assoc(tmp_path / "assoc", fetcher=lambda url: _ASSOC_PAYLOAD)
    ds.save(RefreshRequest(store="purl_associator_mappings_raw", force=True))
    assert ds.is_stale() is False
    out = ds.load()
    assert len(out) == 1
    assert out.iloc[0]["assoc_key"] == "requests"


def test_assoc_fetch_failure_keeps_last_good_and_marks_stale(tmp_path):
    p = tmp_path / "assoc"
    _assoc(p, fetcher=lambda url: _ASSOC_PAYLOAD).save(RefreshRequest(store="purl_associator_mappings_raw", force=True))

    def boom(url):
        raise ConnectionError("unreachable")

    ds = _assoc(p, fetcher=boom)
    ds.save(RefreshRequest(store="purl_associator_mappings_raw", force=True))
    assert ds.is_stale() is True
    assert ds.staleness().last_good_exists is True
    assert len(ds.load()) == 1


def test_assoc_offline_no_fetcher_marks_stale_and_keeps_last_good(tmp_path):
    p = tmp_path / "assoc"
    _assoc(p, fetcher=lambda url: _ASSOC_PAYLOAD).save(RefreshRequest(store="purl_associator_mappings_raw", force=True))
    offline = _assoc(p)
    offline.save(RefreshRequest(store="purl_associator_mappings_raw", force=True))
    assert offline.is_stale() is True
    assert len(offline.load()) == 1


def test_assoc_offline_missing_store_load_returns_empty_and_marks_stale(tmp_path):
    ds = _assoc(tmp_path / "never")
    out = ds.load()
    assert out.empty and "assoc_key" in out.columns
    assert ds.is_stale() is True


def test_assoc_write_rejects_frame_missing_required_columns(tmp_path):
    with pytest.raises(ValueError):
        _assoc(tmp_path / "assoc")._write(pd.DataFrame({"nonsense": [1]}))


def test_assoc_fetch_shard_never_raises_and_degrades_to_empty(tmp_path):
    ds = _assoc(tmp_path / "assoc")
    assert ds.fetch_shard("requests") == {}

    def boom(url):
        raise ConnectionError("nope")

    assert ds.fetch_shard("requests", fetcher=boom) == {}


def test_assoc_fetch_shard_returns_parsed_payload():
    ds = _assoc("unused")
    out = ds.fetch_shard("requests", fetcher=lambda url: {"alternative_purls": ["x"]})
    assert out == {"alternative_purls": ["x"]}


# ---------------------------------------------------------------------------
# parse_openteams_board_nodes / OpenTeamsBoardDataset
# ---------------------------------------------------------------------------

_BOARD_NODES = [
    {
        "content": {
            "__typename": "Issue",
            "number": 42,
            "title": "[Conda-Forge Packaging] cool-pkg",
            "url": "https://github.com/OpenTeams-WFT-CDO/mgmt-wf-python-modernization/issues/42",
            "state": "OPEN",
            "milestone": {"title": "OSS Enhancements (Conda Forge, Pixi, ect)"},
        }
    },
    {"content": {"__typename": "DraftIssue"}},
    "not-a-dict",
]


def test_parse_openteams_board_nodes_extracts_issue_rows_only():
    rows = parse_openteams_board_nodes(_BOARD_NODES)
    assert len(rows) == 1
    assert rows[0]["number"] == 42
    assert rows[0]["milestone"] == "OSS Enhancements (Conda Forge, Pixi, ect)"


@pytest.mark.parametrize("nodes", [None, "not-a-list", {}])
def test_parse_openteams_board_nodes_malformed_returns_empty(nodes):
    assert parse_openteams_board_nodes(nodes) == []


def _board_page(nodes, *, has_next=False, cursor=None) -> dict:
    return {
        "data": {
            "organization": {
                "projectV2": {
                    "items": {
                        "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
                        "nodes": nodes,
                    }
                }
            }
        }
    }


def _board(path, *, fetcher=None) -> OpenTeamsBoardDataset:
    return OpenTeamsBoardDataset(filepath=str(path), url=BOARD_URL, fetcher=fetcher, credentials={"token": "stub"})


def test_board_constructs_offline_no_refresher(tmp_path):
    ds = _board(tmp_path / "board")
    assert ds._describe()["refresher_wired"] is False


def test_board_single_page_fetch_success_persists_and_not_stale(tmp_path):
    ds = _board(tmp_path / "board", fetcher=lambda url, body: _board_page(_BOARD_NODES))
    ds.save(RefreshRequest(store="openteams_project_1_board_raw", force=True))
    assert ds.is_stale() is False
    out = ds.load()
    assert len(out) == 1
    assert out.iloc[0]["title"] == "[Conda-Forge Packaging] cool-pkg"


def test_board_paginates_across_multiple_pages(tmp_path):
    calls: list[dict] = []
    page1_nodes = [
        {
            "content": {
                "__typename": "Issue",
                "number": 1,
                "title": "[Conda-Forge Packaging] pkg-one",
                "url": "https://example/issues/1",
                "state": "OPEN",
                "milestone": None,
            }
        }
    ]
    page2_nodes = [
        {
            "content": {
                "__typename": "Issue",
                "number": 2,
                "title": "[Conda-Forge Packaging] pkg-two",
                "url": "https://example/issues/2",
                "state": "OPEN",
                "milestone": None,
            }
        }
    ]

    def fetcher(url, body):
        calls.append(body)
        cursor = (body.get("variables") or {}).get("cursor")
        if cursor is None:
            return _board_page(page1_nodes, has_next=True, cursor="CURSOR_1")
        return _board_page(page2_nodes, has_next=False)

    ds = _board(tmp_path / "board", fetcher=fetcher)
    ds.save(RefreshRequest(store="openteams_project_1_board_raw", force=True))
    out = ds.load()
    assert len(out) == 2
    assert len(calls) == 2


def test_board_partial_pagination_failure_keeps_pages_already_succeeded(tmp_path):
    page1_nodes = [
        {
            "content": {
                "__typename": "Issue",
                "number": 1,
                "title": "[Conda-Forge Packaging] pkg-one",
                "url": "https://example/issues/1",
                "state": "OPEN",
                "milestone": None,
            }
        }
    ]

    def fetcher(url, body):
        cursor = (body.get("variables") or {}).get("cursor")
        if cursor is None:
            return _board_page(page1_nodes, has_next=True, cursor="CURSOR_1")
        raise ConnectionError("second page failed")

    ds = _board(tmp_path / "board", fetcher=fetcher)
    ds.save(RefreshRequest(store="openteams_project_1_board_raw", force=True))
    out = ds.load()
    assert len(out) == 1  # first page kept, second page's failure never raises


def test_board_fully_empty_fetch_keeps_last_good_and_marks_stale(tmp_path):
    p = tmp_path / "board"
    _board(p, fetcher=lambda url, body: _board_page(_BOARD_NODES)).save(
        RefreshRequest(store="openteams_project_1_board_raw", force=True)
    )

    def empty_fetcher(url, body):
        raise ConnectionError("unreachable")

    ds = _board(p, fetcher=empty_fetcher)
    ds.save(RefreshRequest(store="openteams_project_1_board_raw", force=True))
    assert ds.is_stale() is True
    assert len(ds.load()) == 1  # last-good never clobbered with empty


def test_board_unparseable_response_stops_pagination_without_raising(tmp_path):
    ds = _board(tmp_path / "board", fetcher=lambda url, body: "not json")
    ds.save(RefreshRequest(store="openteams_project_1_board_raw", force=True))  # never raises
    assert ds.is_stale() is True


def test_board_missing_items_connection_stops_without_raising(tmp_path):
    ds = _board(tmp_path / "board", fetcher=lambda url, body: {"data": {}})
    ds.save(RefreshRequest(store="openteams_project_1_board_raw", force=True))
    assert ds.is_stale() is True


def test_board_write_rejects_frame_missing_required_columns(tmp_path):
    with pytest.raises(ValueError):
        _board(tmp_path / "board")._write(pd.DataFrame({"nonsense": [1]}))


def test_board_offline_missing_store_load_returns_empty_and_marks_stale(tmp_path):
    ds = _board(tmp_path / "never")
    out = ds.load()
    assert out.empty and "number" in out.columns
    assert ds.is_stale() is True


# ---------------------------------------------------------------------------
# parse_staged_pr_page / parse_pr_files_response / StagedRecipesPRDataset
# ---------------------------------------------------------------------------

_STAGED_PAGE_1 = [
    {"number": 100, "state": "open", "merged_at": None, "html_url": "https://x/100", "title": "Add cool-pkg recipe"},
]


def test_parse_staged_pr_page_extracts_rows():
    rows = parse_staged_pr_page(_STAGED_PAGE_1)
    assert len(rows) == 1
    assert rows[0]["number"] == 100
    assert rows[0]["file_paths"] == ""


@pytest.mark.parametrize("payload", [None, "not json", {}, "[]"])
def test_parse_staged_pr_page_malformed_or_empty_returns_expected(payload):
    if payload == "[]":
        assert parse_staged_pr_page(payload) == []
    else:
        assert parse_staged_pr_page(payload) == []


def test_parse_pr_files_response_extracts_filenames():
    payload = [{"filename": "recipes/cool-pkg/recipe.yaml"}, {"no": "filename"}]
    assert parse_pr_files_response(payload) == ["recipes/cool-pkg/recipe.yaml"]


@pytest.mark.parametrize("payload", [None, "not json", {}])
def test_parse_pr_files_response_malformed_returns_empty(payload):
    assert parse_pr_files_response(payload) == []


def _staged(path, *, fetcher=None) -> StagedRecipesPRDataset:
    return StagedRecipesPRDataset(filepath=str(path), url=STAGED_URL, fetcher=fetcher, credentials={"token": "stub"})


def test_staged_constructs_offline_no_refresher(tmp_path):
    ds = _staged(tmp_path / "staged")
    assert ds._describe()["refresher_wired"] is False


def test_staged_fetch_success_persists_and_files_fanout_for_open_prs(tmp_path):
    def fetcher(url):
        if "/files" in url:
            return [{"filename": "recipes/cool-pkg/recipe.yaml"}]
        if "page=1" in url:
            return _STAGED_PAGE_1
        return []  # page 2+ empty -> stop pagination

    ds = _staged(tmp_path / "staged", fetcher=fetcher)
    ds.save(RefreshRequest(store="discovery_staged_recipes_prs_raw", force=True))
    assert ds.is_stale() is False
    out = ds.load()
    assert len(out) == 1
    assert out.iloc[0]["file_paths"] == "recipes/cool-pkg/recipe.yaml"


def test_staged_per_pr_files_fetch_failure_degrades_to_empty_never_drops_row(tmp_path):
    def fetcher(url):
        if "/files" in url:
            raise ConnectionError("nope")
        if "page=1" in url:
            return _STAGED_PAGE_1
        return []

    ds = _staged(tmp_path / "staged", fetcher=fetcher)
    ds.save(RefreshRequest(store="discovery_staged_recipes_prs_raw", force=True))
    out = ds.load()
    assert len(out) == 1
    assert out.iloc[0]["file_paths"] == ""


_STAGED_FULL_PAGE = [
    {
        "number": n,
        "state": "closed",
        "merged_at": "2026-01-01T00:00:00Z",
        "html_url": f"https://x/{n}",
        "title": f"pkg-{n} recipe",
    }
    for n in range(1, 101)
]


def test_staged_page_fetch_failure_keeps_accumulated_rows(tmp_path):
    """A full page-1 (100 rows) forces a page-2 fetch attempt; page 2 raising
    must not discard page 1's already-accumulated rows (AD-13)."""

    def fetcher(url):
        if "/files" in url:
            return []
        # NOTE: match on the trailing `&page=N` param, never a bare substring
        # check against "page=1" — the FIXED "per_page=100" query param itself
        # contains that substring for every page, which would make every call
        # look like page 1.
        if url.endswith("&page=1"):
            return _STAGED_FULL_PAGE
        raise ConnectionError("page 2 failed")

    ds = _staged(tmp_path / "staged", fetcher=fetcher)
    ds.save(RefreshRequest(store="discovery_staged_recipes_prs_raw", force=True))
    out = ds.load()
    assert len(out) == 100


def test_staged_fully_empty_fetch_keeps_last_good_and_marks_stale(tmp_path):
    p = tmp_path / "staged"

    def good_fetcher(url):
        if "/files" in url:
            return []
        if "page=1" in url:
            return _STAGED_PAGE_1
        return []

    _staged(p, fetcher=good_fetcher).save(RefreshRequest(store="discovery_staged_recipes_prs_raw", force=True))

    def empty_fetcher(url):
        raise ConnectionError("unreachable")

    ds = _staged(p, fetcher=empty_fetcher)
    ds.save(RefreshRequest(store="discovery_staged_recipes_prs_raw", force=True))
    assert ds.is_stale() is True
    assert len(ds.load()) == 1


def test_staged_write_rejects_frame_missing_required_columns(tmp_path):
    with pytest.raises(ValueError):
        _staged(tmp_path / "staged")._write(pd.DataFrame({"nonsense": [1]}))


def test_staged_offline_missing_store_load_returns_empty_and_marks_stale(tmp_path):
    ds = _staged(tmp_path / "never")
    out = ds.load()
    assert out.empty and "number" in out.columns
    assert ds.is_stale() is True


# ---------------------------------------------------------------------------
# parse_recipe_dir / LocalRecipesOverlayDataset
# ---------------------------------------------------------------------------

_RECIPE_YAML = """\
package:
  name: cool-pkg
  version: 1.0.0

extra:
  cfe-local-build-status: success
"""


def test_parse_recipe_dir_extracts_names_url_and_build_status():
    row = parse_recipe_dir("cool-pkg", {"recipe.yaml": _RECIPE_YAML})
    assert row["dir_name"] == "cool-pkg"
    assert "cool-pkg" in row["names"].split("; ")
    assert row["url"] == "https://github.com/rxm7706/local-recipes/tree/main/recipes/cool-pkg"
    assert row["build_status"] == "success"


def test_parse_recipe_dir_no_recipe_files_still_returns_dir_name_alias():
    row = parse_recipe_dir("bare-dir", {})
    assert row["names"] == "bare-dir"
    assert row["build_status"] == ""


def test_parse_recipe_dir_filters_title_stop_tokens():
    text = "package:\n  name: the\n"
    row = parse_recipe_dir("mydir", {"recipe.yaml": text})
    assert "the" not in row["names"].split("; ")
    assert "mydir" in row["names"].split("; ")


def test_local_recipes_overlay_dataset_scans_a_real_directory(tmp_path):
    recipes_dir = tmp_path / "recipes"
    (recipes_dir / "cool-pkg").mkdir(parents=True)
    (recipes_dir / "cool-pkg" / "recipe.yaml").write_text(_RECIPE_YAML, encoding="utf-8")
    (recipes_dir / ".hidden").mkdir()

    ds = LocalRecipesOverlayDataset(filepath=str(recipes_dir))
    out = ds.load()
    assert len(out) == 1  # .hidden dir excluded
    assert out.iloc[0]["dir_name"] == "cool-pkg"
    assert out.iloc[0]["build_status"] == "success"


def test_local_recipes_overlay_dataset_missing_directory_degrades_to_empty(tmp_path):
    ds = LocalRecipesOverlayDataset(filepath=str(tmp_path / "does-not-exist"))
    out = ds.load()
    assert out.empty
    assert list(out.columns) == ["dir_name", "names", "url", "build_status"]


def test_local_recipes_overlay_dataset_is_read_only(tmp_path):
    from kedro.io.core import DatasetError

    ds = LocalRecipesOverlayDataset(filepath=str(tmp_path))
    with pytest.raises(DatasetError, match="read-only"):
        ds.save(pd.DataFrame())


def test_local_recipes_overlay_dataset_rejects_unexpected_kwargs():
    with pytest.raises(TypeError):
        LocalRecipesOverlayDataset(filepath="recipes", bogus_kwarg=True)  # type: ignore[call-arg]
