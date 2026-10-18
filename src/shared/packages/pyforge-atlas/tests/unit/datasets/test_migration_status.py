"""conda-forge-bot-data migration-status source dataset tests (Story B10, FR-21).

Proves the DATASET-owned discipline against a STUB fetcher — NO live GitHub call (AD-11):
the GITHUB_RAW_BASE_URL-routed fetch, the category-list -> partition-key derivation (the
zero-code-change generalization), the version_status.v2.json exclusion, and the AD-13
offline-skip + keep-last-good + staleness marker for BOTH dataset kinds.
"""

from __future__ import annotations

import json as _json
from pathlib import Path

import pandas as pd
import pytest
from kedro.io.core import DatasetError
from pyforge.testing_kit import flag_states

from pyforge.atlas.datasets import public_sources
from pyforge.atlas.datasets.migration_status import (
    EXCLUDED_STATUS_FILES,
    MigrationCategoryDataset,
    MigrationDetailDataset,
    migration_names,
)
from pyforge.atlas.pipelines.vcs_health.nodes import classify_migration_readiness, drive_migration_status

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
    ds = _detail(tmp_path, fetcher=lambda url: seen.append(url) or {"done": []})
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
    ds = _detail(tmp_path, fetcher=lambda url: seen.append(url) or {"done": []})
    # even if the excluded name is passed in, it is never fetched as a partition.
    ds.fetch_partitions(["python314", "version_status.v2.json"])
    assert all("version_status.v2.json" not in u for u in seen)


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
    ds = _detail(tmp_path, fetcher=lambda url: seen.append(url) or {"done": []})
    ds.fetch_partitions(pd.Series(["python314", "numpy2"]))  # must NOT raise on a Series
    assert len(seen) == 2


def test_detail_save_offline_keeps_last_good_and_marks_stale(tmp_path):
    """Story 34.8: the save is the driver node's sweep; offline (no fetcher, flag off) it fetches
    nothing, keeps last-good and marks stale -- it never raises (AD-13)."""
    ds = _detail(tmp_path)

    ds.save(["python314"])

    assert ds.is_stale() is True and ds.load() == {}


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
    assert (
        det._describe()["partitioned_by"] == "migration"
    )  # Story 34.8: every listed migration, not only the active ones


# --- Story 34.8: the bot's public status files, and the driver node's sweep ----------------


_BOT = "https://raw.githubusercontent.com/conda-forge/conda-forge-bot-data/main/status"
_PUBLIC = {
    f"{_BOT}/regular_status.json": {"python314": "python314 Migration Status", "gsl28": "gsl28 Migration Status"},
    f"{_BOT}/migration_json/python314.json": {"done": ["numpy"], "in-pr": ["scipy"]},
    f"{_BOT}/migration_json/gsl28.json": {"done": ["gsl"]},
}


def _public_text(requested):
    def fetch_text(url, **_kw):
        requested.append(url)
        if url not in _PUBLIC:
            raise DatasetError(f"404 {url}")
        return _json.dumps(_PUBLIC[url])

    return fetch_text


@flag_states("pyforge.atlas.live_public_sources")  # spelled out: the flag gate reads this file for the key
def test_a_category_with_no_fetcher_reads_the_public_status_file(tmp_path, flag_provider, monkeypatch):
    requested: list[str] = []
    monkeypatch.setattr(public_sources, "fetch_text", _public_text(requested))
    monkeypatch.setattr(public_sources, "live", lambda: flag_provider["pyforge.atlas.live_public_sources"])

    payload = _cat(tmp_path).load()

    if flag_provider["pyforge.atlas.live_public_sources"]:
        assert requested == [f"{_BOT}/regular_status.json"]
        assert migration_names(payload) == ["python314", "gsl28"] and not _cat(tmp_path).is_stale()
    else:
        assert requested == [] and payload is None and _cat(tmp_path).is_stale()


def test_the_driver_names_every_migration_each_list_carries_once_in_list_order():
    regular = {"python314": "s", "gsl28": "s"}
    longterm = {"python315": "s"}
    paused = {"cuda130": "s", "gsl28": "s"}  # cuda130 is in no other list
    closed = {"giflib6": "giflib6 closed at 2026-10-15"}
    total = {"python314": "s", "python315": "s", "cuda130": "s", "gsl28": "s"}  # upstream: the open + paused union

    names, categories = drive_migration_status(regular, longterm, paused, closed, total)

    assert names == ["python314", "gsl28", "python315", "cuda130", "giflib6"]
    assert dict(zip(categories["migration"], categories["category"], strict=True)) == {
        "python314": "regular",
        "gsl28": "regular",  # its first list
        "python315": "longterm",
        "cuda130": "paused",
        "giflib6": "closed",
    }


def test_total_keeps_the_open_names_when_their_own_list_failed_with_no_last_good():
    total = {"python314": "s", "python315": "s"}

    names, categories = drive_migration_status(None, None, None, {"giflib6": "c"}, total)

    assert names == ["giflib6", "python314", "python315"]
    assert list(categories["category"]) == ["closed", "unlisted", "unlisted"]
    empty_names, empty = drive_migration_status(None, None, None, None, None)
    assert empty_names == [] and list(empty.columns) == ["migration", "category"] and empty.empty


@flag_states("pyforge.atlas.live_public_sources")
def test_the_detail_save_sweeps_one_partition_per_name(tmp_path, flag_provider, monkeypatch):
    requested: list[str] = []
    monkeypatch.setattr(public_sources, "fetch_text", _public_text(requested))
    monkeypatch.setattr(public_sources, "live", lambda: flag_provider["pyforge.atlas.live_public_sources"])
    ds = MigrationDetailDataset(url=f"{_BOT}/migration_json", filepath=str(tmp_path / "detail"))

    ds.save(["python314", "gsl28", "gone"])  # "gone" answers 404: skipped, run marked stale
    loaded = ds.load()

    if flag_provider["pyforge.atlas.live_public_sources"]:
        assert requested == [f"{_BOT}/migration_json/{n}.json" for n in ("python314", "gsl28", "gone")]
        assert set(loaded) == {"python314", "gsl28"}
        assert ds.staleness().reason == "one or more migration detail partitions could not refresh"  # the load kept it
    else:
        assert requested == [] and loaded == {}
        assert ds.staleness().reason == "offline: no GitHub-raw fetcher wired (consumer profile)"


def test_a_clean_sweep_clears_the_marker_and_feeds_the_readiness_node(tmp_path, monkeypatch):
    requested: list[str] = []
    monkeypatch.setattr(public_sources, "fetch_text", _public_text(requested))
    monkeypatch.setattr(public_sources, "live", lambda: True)
    detail = MigrationDetailDataset(url=f"{_BOT}/migration_json", filepath=str(tmp_path / "detail"))
    names, categories = drive_migration_status(_cat(tmp_path).load(), None, None, None, None)

    detail.save(names)
    out = classify_migration_readiness(
        detail.load(),
        pd.DataFrame({"conda_name": ["numpy", "scipy"], "subdirs": [["linux-64"], ["linux-64"]]}),
        pd.DataFrame({"conda_name": ["numpy"], "downloads_total": [5]}),
        categories,
    )
    assert set(out["category"]) == {"regular"}

    assert detail.staleness() is None
    assert set(map(tuple, out[["migration", "conda_name", "readiness"]].values)) >= {
        ("python314", "numpy", "rebuild-done"),
        ("python314", "scipy", "confirmed-pending"),
    }


def _live_detail(tmp_path, monkeypatch, requested):
    monkeypatch.setattr(public_sources, "fetch_text", _public_text(requested))
    monkeypatch.setattr(public_sources, "live", lambda: True)
    ds = MigrationDetailDataset(url=f"{_BOT}/migration_json", filepath=str(tmp_path / "detail"))
    (tmp_path / "detail").mkdir()
    (tmp_path / "detail" / "closed_one.json").write_text(_json.dumps({"done": ["old"]}))
    return ds


def test_a_clean_sweep_removes_the_partition_of_a_migration_no_longer_active(tmp_path, monkeypatch):
    ds = _live_detail(tmp_path, monkeypatch, [])

    ds.save(["python314", "gsl28"])

    assert set(ds.load()) == {"python314", "gsl28"} and ds.staleness() is None


def test_a_sweep_with_a_failed_partition_removes_nothing(tmp_path, monkeypatch):
    ds = _live_detail(tmp_path, monkeypatch, [])

    ds.save(["python314", "gone"])

    assert set(ds.load()) == {"closed_one", "python314"} and ds.is_stale()


def test_no_names_is_never_a_clean_sweep(tmp_path, monkeypatch):
    requested: list[str] = []
    ds = _live_detail(tmp_path, monkeypatch, requested)

    ds.save([])

    assert requested == [] and set(ds.load()) == {"closed_one"}
    marker = ds.staleness()
    assert marker.reason == "no migration names to sweep (category lists empty or unreadable)"
    assert marker.last_good_exists is True


def test_a_partition_that_cannot_be_removed_is_logged_and_the_sweep_stands(tmp_path, monkeypatch, caplog):
    ds = _live_detail(tmp_path, monkeypatch, [])
    real_unlink = Path.unlink

    def refuse(self, *a, **kw):
        if self.name == "closed_one.json":
            raise PermissionError("read-only")
        return real_unlink(self, *a, **kw)

    monkeypatch.setattr(Path, "unlink", refuse)
    ds.save(["python314"])

    assert "migration detail partition not removed" in caplog.text and ds.staleness() is None


# --- Story 34.8 review round 1 -------------------------------------------------------------


def _fresh_live_detail(tmp_path, monkeypatch, requested):
    monkeypatch.setattr(public_sources, "fetch_text", _public_text(requested))
    monkeypatch.setattr(public_sources, "live", lambda: True)
    return MigrationDetailDataset(url=f"{_BOT}/migration_json", filepath=str(tmp_path / "detail"))


@pytest.mark.parametrize(
    ("names", "reason"),
    [
        (["gone"], "one or more migration detail partitions could not refresh"),
        ([], "no migration names to sweep (category lists empty or unreadable)"),
    ],
    ids=["every-partition-failed", "no-names"],
)
def test_on_a_fresh_root_the_load_keeps_the_sweeps_own_marker(tmp_path, monkeypatch, names, reason):
    ds = _fresh_live_detail(tmp_path, monkeypatch, [])
    ds.save(names)
    marked_at = ds.staleness().marked_at

    assert ds.load() == {}
    marker = ds.staleness()
    assert marker.reason == reason and marker.marked_at == marked_at


def test_before_any_sweep_the_load_says_the_sweep_is_pending(tmp_path, monkeypatch):
    ds = _fresh_live_detail(tmp_path, monkeypatch, [])

    assert ds.load() == {} and ds.staleness().reason == "no detail partitions yet (sweep pending)"


def test_an_injected_fetcher_beats_the_public_path_with_the_flag_on(tmp_path, monkeypatch):
    requested: list[str] = []
    monkeypatch.setattr(public_sources, "fetch_text", _public_text(requested))
    monkeypatch.setattr(public_sources, "live", lambda: True)
    injected: list[str] = []

    def fetch(url):
        injected.append(url)
        return {"done": ["numpy"]}

    detail = MigrationDetailDataset(url=f"{_BOT}/migration_json", filepath=str(tmp_path / "detail"), fetcher=fetch)
    detail.save(["python314"])
    category = _cat(tmp_path, fetcher=lambda url: {"python314": {}})

    assert injected == [f"{_BOT}/migration_json/python314.json"] and set(detail.load()) == {"python314"}
    # B10's attended contract: a category with an injected fetcher never fetches on load
    assert category.load() is None and requested == []
    assert category.staleness().reason == "wired fetcher but category not yet populated (attended fetch pending)"


def test_the_bots_public_empty_category_is_a_valid_empty_list(tmp_path, monkeypatch):
    monkeypatch.setattr(public_sources, "fetch_text", lambda url, **_kw: "{}")
    monkeypatch.setattr(public_sources, "live", lambda: True)
    ds = _cat(tmp_path)
    ds._atomic_write(ds._store_path, _json.dumps({"flang19": "s"}))  # last-good named a paused migration

    assert ds.load() == {} and ds.staleness() is None
    assert migration_names(_cat(tmp_path)._read_last_good()) == []


def test_a_name_that_is_not_a_migrator_slug_is_never_fetched_or_written(tmp_path, monkeypatch, caplog):
    requested: list[str] = []
    ds = _fresh_live_detail(tmp_path, monkeypatch, requested)
    (tmp_path / "regular").mkdir()
    (tmp_path / "regular" / "category.json").write_text("good")

    ds.save(["../regular/category", ".hidden", "python314"])

    assert requested == [f"{_BOT}/migration_json/python314.json"]
    assert (tmp_path / "regular" / "category.json").read_text() == "good"
    assert "is not a migrator slug" in caplog.text and set(ds.load()) == {"python314"}


def test_the_prune_never_touches_a_hidden_file(tmp_path, monkeypatch):
    ds = _fresh_live_detail(tmp_path, monkeypatch, [])
    (tmp_path / "detail").mkdir()
    (tmp_path / "detail" / ".notes.json").write_text("{}")

    ds.save(["python314"])

    assert (tmp_path / "detail" / ".notes.json").exists() and set(ds.load()) == {"python314"}


def test_the_detail_describe_names_the_public_url(tmp_path):
    described = MigrationDetailDataset(url=f"{_BOT}/migration_json", filepath=str(tmp_path))._describe()

    assert described["public_url"] == f"{_BOT}/migration_json" and described["partitioned_by"] == "migration"


# --- Story 34.8 review round 2 -------------------------------------------------------------


def _planted(tmp_path):
    (tmp_path / "detail").mkdir()
    for name in ("kept", "other_one"):
        (tmp_path / "detail" / f"{name}.json").write_text(_json.dumps({"done": [name]}))


@pytest.mark.parametrize("names", [["other"], []], ids=["unlisted-partitions", "no-names"])
def test_a_flag_off_save_removes_nothing(tmp_path, monkeypatch, names):
    """Production's default is off: the offline sweep is never clean, so the prune never runs."""
    monkeypatch.setattr(public_sources, "live", lambda: False)
    _planted(tmp_path)
    ds = MigrationDetailDataset(url=f"{_BOT}/migration_json", filepath=str(tmp_path / "detail"))

    ds.save(names)

    assert set(ds.load()) == {"kept", "other_one"}
    marker = ds.staleness()
    assert marker.reason == "offline: no GitHub-raw fetcher wired (consumer profile)" and marker.last_good_exists


def test_a_path_behind_a_slug_prefix_is_never_fetched_or_written(tmp_path, monkeypatch):
    requested: list[str] = []
    ds = _fresh_live_detail(tmp_path, monkeypatch, requested)

    ds.save(["python314/../../regular/category", "python314"])

    assert requested == [f"{_BOT}/migration_json/python314.json"] and set(ds.load()) == {"python314"}


def test_a_flag_on_load_replaces_an_earlier_offline_reason(tmp_path, monkeypatch):
    ds = MigrationDetailDataset(url=f"{_BOT}/migration_json", filepath=str(tmp_path / "detail"))
    monkeypatch.setattr(public_sources, "live", lambda: False)
    ds.load()
    assert ds.staleness().reason.startswith("offline:")

    monkeypatch.setattr(public_sources, "live", lambda: True)
    ds.load()

    assert ds.staleness().reason == "no detail partitions yet (sweep pending)"


def test_a_failed_sweep_marks_last_good_as_present(tmp_path, monkeypatch):
    ds = _live_detail(tmp_path, monkeypatch, [])

    ds.save(["gone"])

    marker = ds.staleness()
    assert marker.reason == "one or more migration detail partitions could not refresh" and marker.last_good_exists


def test_the_bots_public_null_is_no_data_not_an_empty_category(tmp_path, monkeypatch):
    monkeypatch.setattr(public_sources, "fetch_text", lambda url, **_kw: "null")
    monkeypatch.setattr(public_sources, "live", lambda: True)
    ds = _cat(tmp_path)
    ds._atomic_write(ds._store_path, _json.dumps({"flang19": "s"}))

    assert ds.load() == {"flang19": "s"} and ds.staleness().reason == "category fetch returned no data"


def test_readiness_without_a_categories_frame_has_a_null_category():
    out = classify_migration_readiness(
        {"python314": {"done": ["numpy"]}},
        pd.DataFrame({"conda_name": ["numpy"], "subdirs": [["linux-64"]]}),
        pd.DataFrame(),
    )

    assert list(out["category"]) == [None]
