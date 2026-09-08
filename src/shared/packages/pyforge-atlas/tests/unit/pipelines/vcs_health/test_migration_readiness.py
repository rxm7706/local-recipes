"""FR-21 migration-readiness classification node tests (Story B10; NEW-SIGNAL, AD-14).

Two MANDATORY fixture-enforced tests (spec § 9 Story B10):
  1. Zero-code-change partitioning — feeding a NEW migration name through the category-list
     -> partition -> classification chain classifies it with NO code change (python314 then
     python315, both classify).
  2. Inferred-label — the `not-in-tracker` bucket is labeled inferred in the report output,
     NEVER presented as confirmed tracker status.

Plus: four-way split correctness (noarch / rebuild-done / confirmed-pending / not-in-tracker),
the conda_noarch derivation from subdirs (list / comma-string / None), the downloads join ->
top-unmigrated-by-volume ordering, version_status.v2.json exclusion, and empty-input safety.
"""

from __future__ import annotations

import pandas as pd

from pyforge.atlas.datasets.migration_status import (
    MigrationDetailDataset,
    migration_names,
)
from pyforge.atlas.pipelines.vcs_health.nodes import (
    READINESS_CONFIRMED_PENDING,
    READINESS_NOARCH,
    READINESS_NOT_IN_TRACKER,
    READINESS_REBUILD_DONE,
    classify_migration_readiness,
)

_COLS = [
    "migration",
    "conda_name",
    "readiness",
    "blocker",
    "not_in_tracker_inferred",
    "downloads_total",
    "unmigrated_volume_rank",
]


def _pkgs(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["conda_name", "latest_version", "subdirs"])


def _downloads(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["conda_name", "downloads_total"])


def _detail_stub(details: dict):
    def fetch(url):
        name = url.rsplit("/", 1)[-1][: -len(".json")]
        return details.get(name)

    return fetch


# ============================================================================
# MANDATORY 1 — zero-code-change partitioning (category list -> partition ->
#               classification; a new migration flows through with no code edit)
# ============================================================================

def _run_chain(tmp_path, category_payload: dict, details: dict, pkgs, downloads):
    """Exercise the FULL chain: category list -> active names -> detail partitions ->
    classification. NO migration name is referenced literally anywhere."""
    active = migration_names(category_payload)
    detail_ds = MigrationDetailDataset(
        url="https://raw.githubusercontent.com/conda-forge/conda-forge-bot-data/main/status/migration_json",
        filepath=str(tmp_path / "detail"),
        fetcher=_detail_stub(details),
    )
    detail_ds.fetch_partitions(active)
    return classify_migration_readiness(detail_ds.load(), pkgs, downloads)


def test_zero_code_change_partitioning_new_migration_flows_through(tmp_path):
    pkgs = _pkgs(
        [
            {"conda_name": "numpy", "latest_version": "2.0", "subdirs": ["linux-64"]},
            {"conda_name": "scipy", "latest_version": "1.0", "subdirs": ["linux-64"]},
        ]
    )
    downloads = _downloads([{"conda_name": "numpy", "downloads_total": 100.0}])
    details = {
        "python314": {"done": ["numpy"], "in-pr": ["scipy"]},
        "python315": {"done": ["scipy"], "awaiting-pr": ["numpy"]},
    }

    # First: only python314 in the category list -> one migration classified.
    out1 = _run_chain(tmp_path / "a", {"python314": {}}, details, pkgs, downloads)
    assert set(out1["migration"]) == {"python314"}

    # Then: ADD python315 to the category-list fixture — with NO code change it flows to a
    # new partition AND classifies (both migrations present in the output).
    out2 = _run_chain(tmp_path / "b", {"python314": {}, "python315": {}}, details, pkgs, downloads)
    assert set(out2["migration"]) == {"python314", "python315"}
    # the new migration classified its feedstocks correctly (scipy done in python315).
    p315 = out2[out2["migration"] == "python315"].set_index("conda_name")
    assert p315.loc["scipy", "readiness"] == READINESS_REBUILD_DONE
    assert p315.loc["numpy", "readiness"] == READINESS_CONFIRMED_PENDING
    assert p315.loc["numpy", "blocker"] == "awaiting-pr"


# ============================================================================
# MANDATORY 2 — the not-in-tracker bucket is INFERRED, never confirmed
# ============================================================================

def test_not_in_tracker_is_labeled_inferred_never_confirmed():
    pkgs = _pkgs(
        [
            {"conda_name": "numpy", "latest_version": "2.0", "subdirs": ["linux-64"]},
            {"conda_name": "pend", "latest_version": "3.0", "subdirs": ["linux-64"]},  # a CONFIRMED-pending row
            {"conda_name": "ghost", "latest_version": "1.0", "subdirs": ["linux-64"]},  # absent from detail
        ]
    )
    # `pend` sits in a confirmed pending bucket — the "confirmed" class the inferred flag
    # must never touch (Reviewer-A F1: the mandatory test must place a confirmed-pending
    # row in the frame, else a regression setting inferred=True on it slips through).
    detail = {"python314": {"done": ["numpy"], "in-pr": ["pend"]}}  # ghost is in NO bucket
    out = classify_migration_readiness(detail, pkgs, _downloads([])).set_index("conda_name")

    # ghost: absent from the migration JSON -> not-in-tracker, and the inferred flag is SET.
    assert out.loc["ghost", "readiness"] == READINESS_NOT_IN_TRACKER
    assert bool(out.loc["ghost", "not_in_tracker_inferred"]) is True

    # numpy: confirmed done -> the inferred flag is explicitly FALSE (never conflated).
    assert out.loc["numpy", "readiness"] == READINESS_REBUILD_DONE
    assert bool(out.loc["numpy", "not_in_tracker_inferred"]) is False

    # pend: confirmed PENDING (in-pr) -> inferred is explicitly FALSE. A confirmed row that
    # carried the inferred flag is exactly the "present an inference as confirmed status"
    # failure the FR-21 contract forbids.
    assert out.loc["pend", "readiness"] == READINESS_CONFIRMED_PENDING
    assert bool(out.loc["pend", "not_in_tracker_inferred"]) is False

    # The inferred column exists and is a real boolean surface in the report.
    assert "not_in_tracker_inferred" in out.columns
    # ONLY not-in-tracker rows carry the inferred flag — now proven with a confirmed-pending
    # row present, so the set-equality genuinely excludes the pending class.
    inferred_rows = out[out["not_in_tracker_inferred"]]
    assert set(inferred_rows["readiness"]) == {READINESS_NOT_IN_TRACKER}


# ============================================================================
# four-way split correctness
# ============================================================================

def test_four_way_split_all_classes_present():
    pkgs = _pkgs(
        [
            {"conda_name": "purepy", "latest_version": "1.0", "subdirs": ["noarch"]},   # noarch
            {"conda_name": "numpy", "latest_version": "2.0", "subdirs": ["linux-64"]},   # done
            {"conda_name": "scipy", "latest_version": "1.0", "subdirs": ["linux-64"]},   # pending
            {"conda_name": "ghost", "latest_version": "1.0", "subdirs": ["linux-64"]},   # absent
        ]
    )
    detail = {"python314": {"done": ["numpy"], "not-solvable": ["scipy"]}}
    out = classify_migration_readiness(detail, pkgs, _downloads([]))
    assert list(out.columns) == _COLS
    out = out.set_index("conda_name")

    assert out.loc["purepy", "readiness"] == READINESS_NOARCH
    assert out.loc["numpy", "readiness"] == READINESS_REBUILD_DONE
    assert out.loc["scipy", "readiness"] == READINESS_CONFIRMED_PENDING
    assert out.loc["scipy", "blocker"] == "not-solvable"
    assert out.loc["ghost", "readiness"] == READINESS_NOT_IN_TRACKER


def test_noarch_takes_precedence_over_tracker_bucket():
    # a noarch package needs no rebuild for a python migration — noarch wins even if the
    # tracker ALSO lists it (it is ready by construction; no double-count).
    pkgs = _pkgs([{"conda_name": "purepy", "latest_version": "1.0", "subdirs": ["noarch", "linux-64"]}])
    detail = {"python314": {"in-pr": ["purepy"]}}  # tracker says pending...
    out = classify_migration_readiness(detail, pkgs, _downloads([]))
    assert out.iloc[0]["readiness"] == READINESS_NOARCH  # ...but noarch wins
    assert bool(out.iloc[0]["not_in_tracker_inferred"]) is False


def test_conda_noarch_derived_from_subdirs_shapes():
    # subdirs as list, numpy array (parquet round-trip), comma-string, and None all resolve
    # correctly (the spec's conda_noarch derivation from the existing subdirs column). noarch
    # matches only as an EXACT token — "noarch-extra" must NOT match.
    import numpy as np

    pkgs = _pkgs(
        [
            {"conda_name": "a", "latest_version": "1", "subdirs": ["noarch"]},          # list -> noarch
            {"conda_name": "b", "latest_version": "1", "subdirs": "linux-64,noarch"},    # comma-str -> noarch
            {"conda_name": "c", "latest_version": "1", "subdirs": "linux-64,osx-64"},    # comma-str -> not noarch
            {"conda_name": "d", "latest_version": "1", "subdirs": None},                 # None -> not noarch
            {"conda_name": "e", "latest_version": "1", "subdirs": np.array(["noarch"])}, # np array -> noarch
            {"conda_name": "f", "latest_version": "1", "subdirs": ["noarch-extra"]},     # substring -> NOT noarch
        ]
    )
    detail = {"python314": {"done": []}}  # nobody done -> non-noarch fall to not-in-tracker
    out = classify_migration_readiness(detail, pkgs, _downloads([])).set_index("conda_name")
    assert out.loc["a", "readiness"] == READINESS_NOARCH
    assert out.loc["b", "readiness"] == READINESS_NOARCH
    assert out.loc["c", "readiness"] == READINESS_NOT_IN_TRACKER
    assert out.loc["d", "readiness"] == READINESS_NOT_IN_TRACKER
    assert out.loc["e", "readiness"] == READINESS_NOARCH
    assert out.loc["f", "readiness"] == READINESS_NOT_IN_TRACKER


# ============================================================================
# downloads join -> top-unmigrated-by-volume ranking
# ============================================================================

def test_downloads_join_ranks_unmigrated_by_volume():
    pkgs = _pkgs(
        [
            {"conda_name": "big", "latest_version": "1", "subdirs": ["linux-64"]},    # pending, high vol
            {"conda_name": "small", "latest_version": "1", "subdirs": ["linux-64"]},  # not-in-tracker, low vol
            {"conda_name": "done1", "latest_version": "1", "subdirs": ["linux-64"]},  # done -> no rank
        ]
    )
    downloads = _downloads(
        [
            {"conda_name": "big", "downloads_total": 1000.0},
            {"conda_name": "small", "downloads_total": 5.0},
            {"conda_name": "done1", "downloads_total": 9999.0},
        ]
    )
    detail = {"python314": {"done": ["done1"], "in-pr": ["big"]}}
    out = classify_migration_readiness(detail, pkgs, downloads).set_index("conda_name")
    # unmigrated (big pending + small not-in-tracker) ranked by volume: big=1, small=2.
    assert int(out.loc["big", "unmigrated_volume_rank"]) == 1
    assert int(out.loc["small", "unmigrated_volume_rank"]) == 2
    # a ready (done) row carries a NULL rank (never ranked despite huge volume).
    assert pd.isna(out.loc["done1", "unmigrated_volume_rank"])
    assert out.loc["big", "downloads_total"] == 1000.0


def test_downloads_join_missing_row_ranks_as_zero_not_dropped():
    pkgs = _pkgs(
        [
            {"conda_name": "havol", "latest_version": "1", "subdirs": ["linux-64"]},
            {"conda_name": "novol", "latest_version": "1", "subdirs": ["linux-64"]},  # no download row
        ]
    )
    downloads = _downloads([{"conda_name": "havol", "downloads_total": 50.0}])
    detail = {"python314": {"in-pr": ["havol", "novol"]}}
    out = classify_migration_readiness(detail, pkgs, downloads).set_index("conda_name")
    # both kept; the one with a download row outranks the zero-volume one.
    assert int(out.loc["havol", "unmigrated_volume_rank"]) == 1
    assert int(out.loc["novol", "unmigrated_volume_rank"]) == 2
    assert pd.isna(out.loc["novol", "downloads_total"])  # no row -> NaN downloads (kept)


def test_duplicate_download_rows_take_max():
    pkgs = _pkgs([{"conda_name": "p", "latest_version": "1", "subdirs": ["linux-64"]}])
    downloads = _downloads(
        [{"conda_name": "p", "downloads_total": 10.0}, {"conda_name": "p", "downloads_total": 99.0}]
    )
    detail = {"python314": {"in-pr": ["p"]}}
    out = classify_migration_readiness(detail, pkgs, downloads)
    assert out.iloc[0]["downloads_total"] == 99.0


# ============================================================================
# edge cases / AD-13 safety
# ============================================================================

def test_feedstock_in_detail_but_not_in_atlas_is_out_of_scope():
    # the atlas feedstock set is the authoritative row universe; a bucket member NOT in the
    # atlas set produces no row.
    pkgs = _pkgs([{"conda_name": "numpy", "latest_version": "2.0", "subdirs": ["linux-64"]}])
    detail = {"python314": {"done": ["numpy", "not-in-atlas-pkg"]}}
    out = classify_migration_readiness(detail, pkgs, _downloads([]))
    assert set(out["conda_name"]) == {"numpy"}


def test_duplicate_feedstock_rows_deduped():
    pkgs = _pkgs(
        [
            {"conda_name": "numpy", "latest_version": "2.0", "subdirs": ["linux-64"]},
            {"conda_name": "numpy", "latest_version": "2.0", "subdirs": ["linux-64"]},
        ]
    )
    detail = {"python314": {"done": ["numpy"]}}
    out = classify_migration_readiness(detail, pkgs, _downloads([]))
    assert len(out) == 1  # one row per (migration, feedstock)


def test_multi_bucket_feedstock_uses_precedence_blocker():
    # a feedstock in multiple pending buckets gets the first-precedence blocker (in-pr wins).
    pkgs = _pkgs([{"conda_name": "p", "latest_version": "1", "subdirs": ["linux-64"]}])
    detail = {"python314": {"in-pr": ["p"], "awaiting-pr": ["p"], "bot-error": ["p"]}}
    out = classify_migration_readiness(detail, pkgs, _downloads([]))
    assert out.iloc[0]["readiness"] == READINESS_CONFIRMED_PENDING
    assert out.iloc[0]["blocker"] == "in-pr"


def test_done_and_pending_done_wins_no_double_count():
    # if the same feedstock is (inconsistently) in both done and a pending bucket, done wins
    # (rebuild-done precedence) and it is emitted exactly once.
    pkgs = _pkgs([{"conda_name": "p", "latest_version": "1", "subdirs": ["linux-64"]}])
    detail = {"python314": {"done": ["p"], "in-pr": ["p"]}}
    out = classify_migration_readiness(detail, pkgs, _downloads([]))
    assert len(out) == 1
    assert out.iloc[0]["readiness"] == READINESS_REBUILD_DONE


def test_malformed_detail_bucket_is_not_list_never_crashes():
    pkgs = _pkgs([{"conda_name": "p", "latest_version": "1", "subdirs": ["linux-64"]}])
    detail = {"python314": {"done": "numpy", "in-pr": {"a": 1}}}  # scalar / dict buckets
    out = classify_migration_readiness(detail, pkgs, _downloads([]))
    # p is in no *list* bucket -> not-in-tracker (never crashes on the bad shapes).
    assert out.iloc[0]["readiness"] == READINESS_NOT_IN_TRACKER


def test_empty_and_missing_inputs_return_typed_empty_frame():
    empty = pd.DataFrame()
    out = classify_migration_readiness({}, empty, empty)
    assert out.empty and list(out.columns) == _COLS
    assert out["not_in_tracker_inferred"].dtype == bool
    assert str(out["downloads_total"].dtype) == "float64"
    assert str(out["unmigrated_volume_rank"].dtype) == "Int64"
    # no detail partitions but a real atlas set -> still empty (nothing to classify against).
    pkgs = _pkgs([{"conda_name": "numpy", "latest_version": "2.0", "subdirs": ["linux-64"]}])
    assert classify_migration_readiness({}, pkgs, empty).empty
    # missing conda_name column -> typed empty.
    assert classify_migration_readiness({"python314": {"done": []}}, pd.DataFrame({"x": [1]}), empty).empty


def test_non_dict_detail_input_is_safe():
    pkgs = _pkgs([{"conda_name": "numpy", "latest_version": "2.0", "subdirs": ["linux-64"]}])
    assert classify_migration_readiness(None, pkgs, _downloads([])).empty
    assert classify_migration_readiness([1, 2, 3], pkgs, _downloads([])).empty


# ============================================================================
# AD-14 parity boundary (new-signal, never parity-gated)
# ============================================================================

def test_output_dataset_is_in_the_frozen_new_signal_exclusion_set():
    from pyforge.atlas.parity import EXCLUDED_NEW_SIGNAL_DATASETS
    from pyforge.atlas.parity.legacy_surface import parity_scoped_kedro_datasets

    assert "vcs_migration_readiness" in EXCLUDED_NEW_SIGNAL_DATASETS
    # the frozen set stays len==3 (B10 aligned to an ALREADY-present name; added none).
    assert len(EXCLUDED_NEW_SIGNAL_DATASETS) == 3
    # never a legacy-surface parity dataset.
    assert parity_scoped_kedro_datasets() & EXCLUDED_NEW_SIGNAL_DATASETS == set()
