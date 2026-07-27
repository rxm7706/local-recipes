"""conda-forge-bot-data migration-status source dataset tests (Story B10, FR-21).

Proves the DATASET-owned discipline against a STUB fetcher — NO live GitHub call (AD-11):
the GITHUB_RAW_BASE_URL-routed fetch, the category-list -> partition-key derivation (the
zero-code-change generalization), the version_status.v2.json exclusion, and the AD-13
offline-skip + keep-last-good + staleness marker for BOTH dataset kinds.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest
from kedro.io.core import DatasetError

from pyforge.atlas.datasets.migration_status import (
    EXCLUDED_STATUS_FILES,
    MigrationCategoryDataset,
    MigrationDetailDataset,
    migration_names,
)


# --- migration_names (the pure partition-key derivation) --------------------

def test_migration_names_from_dict_keyed_by_name_drops_meta():
    payload = {"_wrote_at": 123, "python314": {"total": 10}, "boost187": {"total": 5}}
    assert migration_names(payload) == ["python314", "boost187"]


def test_migration_names_from_migrations_subdict():
    payload = {"migrations": {"python314": {}, "numpy2": {}}}
    assert migration_names(payload) == ["python314", "numpy2"]


def test_migration_names_from_list_of_names_and_of_dicts():
    assert migration_names(["python314", "python315"]) == ["python314", "python315"]
    assert migration_names([{"name": "python314"}, {"name": "numpy2"}]) == ["python314", "numpy2"]


def test_migration_names_excludes_version_status_queue():
    # even if the excluded name leaks into a category payload it is NEVER surfaced.
    payload = {"python314": {}, "version_status.v2.json": {}}
    assert migration_names(payload) == ["python314"]
    assert "version_status.v2.json" in EXCLUDED_STATUS_FILES


def test_migration_names_robust_to_junk():
    assert migration_names(None) == []
    assert migration_names(42) == []
    assert migration_names({"python314": {}, "": {}, "  ": {}}) == ["python314"]
    # duplicates dropped, order preserved.
    assert migration_names(["a", "a", "b"]) == ["a", "b"]


def test_migration_names_rejects_path_traversal_slugs():
    # AUD-ATLAS-014: remotely-fetched keys must not become partition paths.
    payload = {
        "python314": {},
        "../etc/passwd": {},
        "foo/bar": {},
        "..": {},
        "evil\\win": {},
        "ok-name_1.2": {},
    }
    assert migration_names(payload) == ["python314", "ok-name_1.2"]


# --- MigrationCategoryDataset (fetch + AD-13) -------------------------------

def _cat(tmp_path, **kw):
    return MigrationCategoryDataset(
        url="https://raw.githubusercontent.com/conda-forge/conda-forge-bot-data/main/status/regular_status.json",
        filepath=str(tmp_path / "regular"),
        **kw,
    )


def test_category_refresh_persists_and_clears_stale(tmp_path):
    payload = {"python314": {"total": 10}, "numpy2": {"total": 3}}
    ds = _cat(tmp_path, fetcher=lambda url: payload)
    out = ds.refresh()
    assert out == payload
    assert not ds.is_stale()  # a good fetch clears stale
    assert migration_names(ds.load()) == ["python314", "numpy2"]


def test_category_url_routes_through_github_raw_base_url(tmp_path):
    ds = _cat(tmp_path, fetcher=lambda url: {"python314": {}})
    seen = {}
    ds.refresh(fetcher=lambda url: seen.setdefault("url", url) or {"python314": {}})
    assert "raw.githubusercontent.com" in seen["url"]
    assert seen["url"].endswith("/status/regular_status.json")


def test_category_offline_marks_stale_keeps_last_good(tmp_path):
    good = {"python314": {"total": 10}}
    ds_live = _cat(tmp_path, fetcher=lambda url: good)
    ds_live.refresh()
    # OFFLINE (no fetcher) -> keep last-good + mark stale, never crash.
    ds_off = _cat(tmp_path, fetcher=None)
    assert ds_off.load() == good  # last-good preserved
    assert ds_off.is_stale() is True
    marker = ds_off.staleness()
    assert marker is not None and marker.last_good_exists is True


def test_category_empty_fetch_never_clobbers_last_good(tmp_path):
    good = {"python314": {}}
    ds = _cat(tmp_path, fetcher=lambda url: good)
    ds.refresh()
    ds._fetcher = lambda url: {}  # a later empty fetch
    ds.refresh()
    assert ds.is_stale() is True
    assert ds.load() == good  # never wrote empty over good


def test_category_fetcher_raises_marks_stale_no_propagate(tmp_path):
    def boom(url):
        raise RuntimeError("github unreachable")

    ds = _cat(tmp_path, fetcher=boom)
    out = ds.refresh()  # must NOT raise
    assert out is None  # no last-good yet
    assert ds.is_stale() is True


def test_category_wired_but_unpopulated_load_marks_stale(tmp_path):
    ds = _cat(tmp_path, fetcher=lambda url: {"python314": {}})
    # load() before any refresh: wired but store empty -> surface stale (AD-13 guard).
    assert ds.load() is None
    assert ds.is_stale() is True


def test_category_save_is_read_only(tmp_path):
    ds = _cat(tmp_path)
    with pytest.raises((NotImplementedError, DatasetError), match="read-only"):
        ds.save({"x": 1})


def test_category_describe_records_exclusion(tmp_path):
    ds = _cat(tmp_path)
    desc = ds._describe()
    assert "version_status.v2.json" in desc["excluded_status_files"]


# --- MigrationDetailDataset (partitioned by migration + AD-13) --------------

def _detail(tmp_path, **kw):
    return MigrationDetailDataset(
        url="https://raw.githubusercontent.com/conda-forge/conda-forge-bot-data/main/status/migration_json",
        filepath=str(tmp_path / "detail"),
        **kw,
    )


def _detail_fetcher(details: dict):
    """A stub GET that maps a /<name>.json url to its detail payload (404 == None)."""

    def fetch(url):
        name = url.rsplit("/", 1)[-1][: -len(".json")]
        return details.get(name)

    return fetch


def test_detail_fetch_partitions_one_per_active_migration(tmp_path):
    details = {
        "python314": {"done": ["numpy"], "in-pr": ["scipy"]},
        "numpy2": {"done": ["pandas"]},
    }
    ds = _detail(tmp_path, fetcher=_detail_fetcher(details))
    out = ds.fetch_partitions(["python314", "numpy2"])
    assert set(out) == {"python314", "numpy2"}
    assert out["python314"]["done"] == ["numpy"]
    assert not ds.is_stale()  # every partition refreshed
    # partitions persisted as <name>.json files.
    assert (tmp_path / "detail" / "python314.json").is_file()
    assert (tmp_path / "detail" / "numpy2.json").is_file()


def test_detail_url_appends_name_json(tmp_path):
    seen = []
    ds = _detail(tmp_path, fetcher=lambda url: (seen.append(url) or {"done": []}))
    ds.fetch_partitions(["python314"])
    assert seen == [
        "https://raw.githubusercontent.com/conda-forge/conda-forge-bot-data/main/status/migration_json/python314.json"
    ]


def test_detail_404_partition_marks_stale_keeps_others(tmp_path):
    # a migration listed but with NO detail json (404 -> None): skipped, others survive,
    # the run is marked stale (AD-13).
    details = {"python314": {"done": ["numpy"]}}  # numpy2 absent -> 404
    ds = _detail(tmp_path, fetcher=_detail_fetcher(details))
    out = ds.fetch_partitions(["python314", "numpy2"])
    assert set(out) == {"python314"}  # only the resolvable one
    assert ds.is_stale() is True


def test_detail_never_fetches_version_status_queue(tmp_path):
    seen = []
    ds = _detail(tmp_path, fetcher=lambda url: (seen.append(url) or {"done": []}))
    # even if the excluded name is passed in, it is never fetched as a partition.
    ds.fetch_partitions(["python314", "version_status.v2.json"])
    assert all("version_status.v2.json" not in u for u in seen)


def test_detail_fetch_rejects_path_traversal_names(tmp_path):
    # AUD-ATLAS-014: traversal names must not be fetched or written.
    seen = []
    ds = _detail(tmp_path, fetcher=lambda url: (seen.append(url) or {"done": []}))
    out = ds.fetch_partitions(["python314", "../escape", "foo/bar"])
    assert set(out) == {"python314"}
    assert all("../" not in u and "foo/bar" not in u for u in seen)
    assert not (tmp_path / "escape.json").exists()
    assert (tmp_path / "detail" / "python314.json").is_file()


def test_detail_offline_marks_stale_keeps_last_good(tmp_path):
    details = {"python314": {"done": ["numpy"]}}
    ds_live = _detail(tmp_path, fetcher=_detail_fetcher(details))
    ds_live.fetch_partitions(["python314"])
    # OFFLINE (no fetcher) -> keep last-good partitions + mark stale.
    ds_off = _detail(tmp_path, fetcher=None)
    resolved = ds_off.load()
    assert resolved == {"python314": {"done": ["numpy"]}}
    assert ds_off.is_stale() is True
    marker = ds_off.staleness()
    assert marker is not None and marker.last_good_exists is True


def test_detail_load_empty_wired_but_unpopulated_marks_stale(tmp_path):
    ds = _detail(tmp_path, fetcher=lambda url: {"done": []})
    # load() before any sweep: wired but no partitions -> surface stale (AD-13 guard).
    assert ds.load() == {}
    assert ds.is_stale() is True


def test_detail_fetcher_raises_per_migration_no_propagate(tmp_path):
    def boom(url):
        raise RuntimeError("unreachable")

    ds = _detail(tmp_path, fetcher=boom)
    out = ds.fetch_partitions(["python314"])  # must NOT raise
    assert out == {}
    assert ds.is_stale() is True


def test_detail_corrupt_partition_skipped_not_fatal(tmp_path):
    details = {"python314": {"done": ["numpy"]}}
    ds = _detail(tmp_path, fetcher=_detail_fetcher(details))
    ds.fetch_partitions(["python314"])
    # corrupt one partition on disk — load must skip it, never crash.
    (tmp_path / "detail" / "python314.json").write_text("{not json", encoding="utf-8")
    assert ds.load() == {}  # unreadable partition skipped


def test_detail_accepts_series_of_names(tmp_path):
    seen = []
    ds = _detail(tmp_path, fetcher=lambda url: (seen.append(url) or {"done": []}))
    ds.fetch_partitions(pd.Series(["python314", "numpy2"]))  # must NOT raise on a Series
    assert len(seen) == 2


def test_detail_save_is_read_only(tmp_path):
    ds = _detail(tmp_path)
    with pytest.raises((NotImplementedError, DatasetError), match="read-only"):
        ds.save({"x": 1})


def test_detail_load_includes_orphaned_partitions(tmp_path):
    """Demonstrates that unlisted partition JSON files left on disk

    are still loaded by the glob pattern (the orphaned partition observation).
    """
    ds = _detail(tmp_path)
    (tmp_path / "detail").mkdir(parents=True, exist_ok=True)
    (tmp_path / "detail" / "python314.json").write_text('{"done": ["numpy"]}', encoding="utf-8")
    (tmp_path / "detail" / "orphaned_old.json").write_text('{"done": ["boost"]}', encoding="utf-8")

    loaded = ds.load()
    assert "python314" in loaded
    assert "orphaned_old" in loaded


# --- offline construction (kedro-catalog-check parity) ----------------------

def test_datasets_construct_offline_no_network():
    # __init__ does NO network (materializes under the catalog gate with stub config).
    cat = MigrationCategoryDataset(url="https://x/status/regular_status.json", filepath="/tmp/x")
    det = MigrationDetailDataset(url="https://x/status/migration_json", filepath="/tmp/y")
    assert cat._describe()["fetcher_wired"] is False
    assert det._describe()["partitioned_by"] == "active_migration"
