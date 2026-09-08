"""External-refresh dataset tests (Story B5 — AC-1 / AC-3 / AC-5 / DW-B2-2).

Dataset-level proofs for the § 3.4 refresh assets: the declared vuln-db resource + the
retry/observability budget, the `coerce_cvss_score` read boundary (DW-B2-2), the cadence/
force freshness semantics, and the AD-13 air-gapped degradation (keep-last-good + staleness
marker; never overwrite good data with empty; never raise; atomic writes). All IO is via
injected stubs — never a real vuln-db env, never a live GCS bucket.
"""

from __future__ import annotations

import json

import pandas as pd

from pyforge.atlas.datasets import (
    MappingCacheDataset,
    OSVOfflineStoreDataset,
    RefreshRequest,
    VDBStoreDataset,
    VULN_DB_ENV_RESOURCE,
)

_FORCE = RefreshRequest(store="s", force=True)


def _good_vdb_frame() -> pd.DataFrame:
    return pd.DataFrame({"package_name": ["a"], "cve_id": ["CVE-1"], "cvss_score": [7.5]})


def _seed_vdb(path) -> None:
    """Write a last-good vdb store on disk via a wired refresher (store absent => due)."""
    VDBStoreDataset(filepath=str(path), refresher=_good_vdb_frame).save(RefreshRequest(store="v"))


# -- offline / lazy construction (kedro-catalog-check compatibility) ---------

def test_vdb_constructs_offline_no_refresher(tmp_path):
    ds = VDBStoreDataset(filepath=str(tmp_path / "vdb"))
    desc = ds._describe()
    assert desc["refresher_wired"] is False
    # AC-1: retry/observability budget declared as per-asset metadata (AD-6).
    assert desc["retry_budget"] == {"timeout_seconds": 900, "max_retries": 3}


def test_osv_constructs_offline_no_refresher(tmp_path):
    ds = OSVOfflineStoreDataset(filepath=str(tmp_path / "cve"), bucket_url="https://example/osv")
    desc = ds._describe()
    assert desc["refresher_wired"] is False
    assert desc["bucket_url"] == "https://example/osv"


def test_mapping_constructs_offline(tmp_path):
    ds = MappingCacheDataset(filepath=str(tmp_path / "map.json"))
    assert ds._describe()["refresher_wired"] is False


# -- AC-3: declared resource + coerce_cvss_score boundary --------------------

def test_vdb_declares_vuln_db_resource(tmp_path):
    ds = VDBStoreDataset(filepath=str(tmp_path / "vdb"))
    assert ds._describe()["required_resource"] == {
        "name": "vuln-db",
        "tool": "appthreat-vulnerability-db",
    }
    assert VULN_DB_ENV_RESOURCE.name == "vuln-db"
    assert VULN_DB_ENV_RESOURCE.tool == "appthreat-vulnerability-db"


def test_vdb_load_coerces_cvss_numeric_nan_to_none(tmp_path):
    # DW-B2-2: an absent (NaN) score must come out None at the READ boundary (never NaN),
    # a real 0.0 is preserved (not treated as unknown), 9.8 stays 9.8.
    raw = pd.DataFrame(
        {
            "package_name": ["a", "b", "c"],
            "cve_id": ["CVE-1", "CVE-2", "CVE-3"],
            "cvss_score": [9.8, None, 0.0],  # homogeneous float column (None -> NaN)
        }
    )
    ds = VDBStoreDataset(filepath=str(tmp_path / "vdb"), refresher=lambda: raw)
    ds.save(RefreshRequest(store="v"))
    vals = ds.load()["cvss_score"].tolist()
    assert vals[0] == 9.8 and isinstance(vals[0], float)
    assert vals[1] is None  # NaN -> None (unknown), never NaN
    assert vals[2] == 0.0 and isinstance(vals[2], float)  # real 0.0 preserved
    assert ds.is_stale() is False


def test_vdb_load_coerces_string_score_to_float(tmp_path):
    # DW-B2-2: a numeric-STRING cvss (the partial-model_dump shape that survives parquet)
    # must come out a float via coerce_cvss_score at the read boundary.
    raw = pd.DataFrame(
        {"package_name": ["a", "b"], "cve_id": ["CVE-1", "CVE-2"], "cvss_score": ["9.8", "7.0"]}
    )
    ds = VDBStoreDataset(filepath=str(tmp_path / "vdb"), refresher=lambda: raw)
    ds.save(RefreshRequest(store="v"))
    vals = ds.load()["cvss_score"].tolist()
    assert vals == [9.8, 7.0]
    assert all(isinstance(v, float) for v in vals)


# -- AC-1: cadence / force freshness semantics -------------------------------

def test_fresh_store_within_cadence_is_a_noop_not_stale(tmp_path):
    # A store still fresh within cadence + no force => no-op, NOT marked stale (the
    # operator's out-of-band cron keeps it fresh). This is the BH-2 "no permanent-stale" fix.
    p = tmp_path / "vdb"
    _seed_vdb(p)
    ds = VDBStoreDataset(filepath=str(p))  # no refresher, but store is fresh
    ds.save(RefreshRequest(store="v", cadence_seconds=604800, force=False))
    assert ds.is_stale() is False
    assert ds.load()["cve_id"].tolist() == ["CVE-1"]


def test_force_triggers_a_due_refresh(tmp_path):
    # RefreshRequest.force is load-bearing (BH-1 fix): it forces a refresh even on a fresh
    # store — with a wired refresher the store is rewritten.
    p = tmp_path / "vdb"
    _seed_vdb(p)
    new = pd.DataFrame({"package_name": ["z"], "cve_id": ["CVE-9"], "cvss_score": [1.0]})
    ds = VDBStoreDataset(filepath=str(p), refresher=lambda: new)
    ds.save(RefreshRequest(store="v", force=True))
    assert ds.load()["cve_id"].tolist() == ["CVE-9"]
    assert ds.is_stale() is False


# -- AC-5: air-gapped degradation (keep last-good + mark stale) --------------

def test_vdb_airgapped_due_refresh_keeps_last_good_and_marks_stale(tmp_path):
    p = tmp_path / "vdb"
    _seed_vdb(p)
    # A DUE refresh (force) with no refresher wired must NOT clobber + must mark stale.
    offline = VDBStoreDataset(filepath=str(p))
    offline.save(_FORCE)
    assert offline.is_stale() is True
    marker = offline.staleness()
    assert marker is not None and marker.last_good_exists is True
    assert offline.load()["cve_id"].tolist() == ["CVE-1"]  # consumer still reads last-good


def test_vdb_refresher_raising_never_fails_and_keeps_last_good(tmp_path):
    p = tmp_path / "vdb"
    _seed_vdb(p)

    def boom():
        raise ConnectionError("endpoint unreachable")

    ds = VDBStoreDataset(filepath=str(p), refresher=boom)
    ds.save(_FORCE)  # MUST NOT raise (AD-13)
    assert ds.is_stale() is True
    assert ds.load()["cve_id"].tolist() == ["CVE-1"]


def test_vdb_empty_refresh_does_not_clobber(tmp_path):
    p = tmp_path / "vdb"
    _seed_vdb(p)
    VDBStoreDataset(filepath=str(p), refresher=lambda: pd.DataFrame()).save(_FORCE)
    assert VDBStoreDataset(filepath=str(p)).load()["cve_id"].tolist() == ["CVE-1"]


def test_vdb_malformed_refresh_is_rejected_and_keeps_last_good(tmp_path):
    # A refresh frame missing package_name/cve_id must NOT persist (it would read as
    # "no vulnerabilities" downstream) — save() catches the _write error, keeps last-good.
    p = tmp_path / "vdb"
    _seed_vdb(p)
    bad = pd.DataFrame({"nonsense": [1, 2]})
    ds = VDBStoreDataset(filepath=str(p), refresher=lambda: bad)
    ds.save(_FORCE)  # must not raise
    assert ds.is_stale() is True
    assert ds.load()["cve_id"].tolist() == ["CVE-1"]  # last-good intact


def test_vdb_missing_store_load_returns_empty_and_marks_stale(tmp_path):
    ds = VDBStoreDataset(filepath=str(tmp_path / "never"))
    out = ds.load()
    assert isinstance(out, pd.DataFrame) and out.empty
    assert ds.is_stale() is True


def test_vdb_unreadable_store_degrades_to_empty(tmp_path):
    p = tmp_path / "vdb"
    _seed_vdb(p)
    # Corrupt the parquet on disk — load() must degrade (not crash).
    (p / VDBStoreDataset.STORE_FILENAME).write_bytes(b"not a parquet")
    ds = VDBStoreDataset(filepath=str(p))
    out = ds.load()
    assert out.empty
    assert ds.is_stale() is True


def test_osv_refresh_then_airgapped_read(tmp_path):
    p = tmp_path / "cve"
    good = OSVOfflineStoreDataset(
        filepath=str(p), bucket_url="https://example/osv", refresher=lambda: [{"id": "CVE-1"}]
    )
    good.save(RefreshRequest(store="o"))
    assert good.load() == [{"id": "CVE-1"}]
    assert good.is_stale() is False
    offline = OSVOfflineStoreDataset(filepath=str(p), bucket_url="https://example/osv")
    offline.save(_FORCE)
    assert offline.is_stale() is True
    assert offline.load() == [{"id": "CVE-1"}]


def test_osv_empty_fetch_does_not_clobber(tmp_path):
    p = tmp_path / "cve"
    OSVOfflineStoreDataset(filepath=str(p), refresher=lambda: [{"id": "CVE-1"}]).save(RefreshRequest(store="o"))
    OSVOfflineStoreDataset(filepath=str(p), refresher=lambda: []).save(_FORCE)
    assert OSVOfflineStoreDataset(filepath=str(p)).load() == [{"id": "CVE-1"}]


def test_osv_non_list_refresh_is_rejected(tmp_path):
    p = tmp_path / "cve"
    OSVOfflineStoreDataset(filepath=str(p), refresher=lambda: [{"id": "CVE-1"}]).save(RefreshRequest(store="o"))
    # a dict return is malformed (list(dict) would persist only keys) — rejected, last-good kept.
    ds = OSVOfflineStoreDataset(filepath=str(p), refresher=lambda: {"CVE-2": {}})
    ds.save(_FORCE)
    assert ds.is_stale() is True
    assert ds.load() == [{"id": "CVE-1"}]


def test_osv_non_list_on_disk_degrades_to_empty(tmp_path):
    p = tmp_path / "cve"
    p.mkdir(parents=True, exist_ok=True)
    (p / OSVOfflineStoreDataset.STORE_FILENAME).write_text('{"not": "a list"}', encoding="utf-8")
    ds = OSVOfflineStoreDataset(filepath=str(p))
    assert ds.load() == []
    assert ds.is_stale() is True


# -- staleness marker robustness (EC4) ---------------------------------------

def test_staleness_robust_to_malformed_marker(tmp_path):
    ds = VDBStoreDataset(filepath=str(tmp_path / "vdb"))
    ds._staleness_path.parent.mkdir(parents=True, exist_ok=True)
    # non-dict JSON (a bare int) must not crash is_stale().
    ds._staleness_path.write_text("123", encoding="utf-8")
    assert ds.staleness() is None
    assert ds.is_stale() is False
    # a dict with a non-numeric marked_at must not crash.
    ds._staleness_path.write_text(
        json.dumps({"stale": True, "reason": "x", "marked_at": "nope"}), encoding="utf-8"
    )
    marker = ds.staleness()
    assert marker is not None and marker.stale is True and marker.marked_at == 0


# -- MappingCacheDataset: merge + keep-last-good (AC-4 / AC-5) ----------------

def test_mapping_merge_retains_old_only_keys_and_new_wins(tmp_path):
    p = tmp_path / "map.json"
    ds = MappingCacheDataset(filepath=str(p))
    ds.save({"a": "conda-a", "b": "conda-b-old"})
    # a second export: b updated (Phase C wins), c added, a absent from this export.
    ds.save({"b": "conda-b-new", "c": "conda-c"})
    merged = ds.load()
    assert merged == {"a": "conda-a", "b": "conda-b-new", "c": "conda-c"}  # 'a' retained


def test_mapping_empty_export_keeps_last_good_and_marks_stale(tmp_path):
    p = tmp_path / "map.json"
    ds = MappingCacheDataset(filepath=str(p))
    ds.save({"a": "conda-a"})
    ds.save({})  # degenerate/empty Phase C — must NOT clobber the good cache.
    assert ds.is_stale() is True
    assert ds.load() == {"a": "conda-a"}


def test_mapping_missing_cache_load_returns_empty(tmp_path):
    ds = MappingCacheDataset(filepath=str(tmp_path / "never.json"))
    assert ds.load() == {}
    assert ds.is_stale() is True


# -- B5 follow-up review (independent): invalid-UTF-8 bytes must degrade, not crash ----
# The narrow `except (OSError, json.JSONDecodeError)` missed UnicodeDecodeError (a
# ValueError subclass), so an invalid-UTF-8 corrupt JSON store/marker crashed
# load()/save()/is_stale() — a real AD-13 never-fail violation the valid-UTF-8
# corruption tests couldn't reach. Guards widened to (OSError, ValueError).
_BAD_UTF8 = b"\xff\xfe\x00\x80not utf-8"


def test_osv_load_degrades_on_invalid_utf8_store(tmp_path):
    p = tmp_path / "cve"
    OSVOfflineStoreDataset(
        filepath=str(p), refresher=lambda: [{"id": "CVE-1"}]
    ).save(RefreshRequest(store="o"))
    (p / OSVOfflineStoreDataset.STORE_FILENAME).write_bytes(_BAD_UTF8)
    ds = OSVOfflineStoreDataset(filepath=str(p))
    assert ds.load() == []          # degrades, does not raise
    assert ds.is_stale() is True


def test_mapping_load_and_save_degrade_on_invalid_utf8_last_good(tmp_path):
    p = tmp_path / "map.json"  # filepath IS the file for MappingCacheDataset
    ds = MappingCacheDataset(filepath=str(p))
    ds.save({"numpy": "numpy"})
    p.write_bytes(_BAD_UTF8)  # corrupt the last-good cache with invalid UTF-8
    assert ds.load() == {}    # corrupt last-good → empty, no crash
    # save() must not raise even though last-good is unreadable (single-writer path);
    # the unreadable last-good is treated as absent, so the new export lands.
    ds.save({"pandas": "pandas"})
    assert json.loads(p.read_text())["pandas"] == "pandas"


def test_is_stale_survives_invalid_utf8_marker(tmp_path):
    p = tmp_path / "vdb"
    _seed_vdb(p)
    ds = VDBStoreDataset(filepath=str(p))
    ds._staleness_path.parent.mkdir(parents=True, exist_ok=True)
    ds._staleness_path.write_bytes(_BAD_UTF8)
    # is_stale() must not raise on a corrupt (invalid-UTF-8) marker
    assert ds.is_stale() in (True, False)
