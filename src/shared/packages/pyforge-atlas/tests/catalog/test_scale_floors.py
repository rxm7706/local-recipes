"""Story 21.4 — Tier 1 scale-sanity floors (catalog-sources.md "Scale sanity gates").

Offline, fixture-injected floor assertions for the three floors this story owns:

- AOSS free Python  — ≥ 1,000 rows, asserted against the REAL committed seed file
  (``TrackedSeedDataset`` needs no injected fetcher, so the actual git-tracked artifact
  is what is tested, not a synthetic stand-in);
- Anaconda main     — ≥ 5,000 rows, asserted against a fixture-injected channeldata
  payload of realistic size through the UNCHANGED ``channeldata_json_to_rows`` parser;
- Basilisk packages — non-zero when a fixture fetcher returns data (qualitative).

Sub-threshold FAILS the assertion (never a log-only warning). No network anywhere —
this whole ``tests/catalog/`` suite is offline and non-credentialed by design
(AD-11/NFR-1); "Bootstrap smoke" in catalog-sources.md's wording is satisfied here.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from pyforge.atlas.datasets import (
    BasiliskPackagesDataset,
    RefreshRequest,
    TrackedSeedDataset,
    channeldata_json_to_rows,
)
from pyforge.atlas.pipelines.core.nodes import enumerate_anaconda_main_packages

from .conftest import CONF_SOURCE

# The documented order-of-magnitude floors (catalog-sources.md "Scale sanity gates").
AOSS_FREE_FLOOR = 1_000
ANACONDA_MAIN_FLOOR = 5_000

AOSS_FREE_SEED = CONF_SOURCE / "base" / "seeds" / "discovery_aoss_free_python_seed.json"
ANACONDA_DIST_SEED = CONF_SOURCE / "base" / "seeds" / "discovery_anaconda_dist_2026x_seed.json"


def _channeldata_payload(n: int) -> dict:
    return {"packages": {f"pkg-{i:05d}": {"subdirs": ["linux-64", "noarch"]} for i in range(n)}}


def _assert_floor(frame: pd.DataFrame, floor: int, label: str) -> None:
    assert len(frame) >= floor, (
        f"{label}: {len(frame)} rows is below the documented scale-sanity floor of {floor} "
        "(sub-threshold = FAIL, never warn-only — catalog-sources.md)"
    )


# -- AOSS free Python: the REAL committed seed --------------------------------


def test_aoss_free_seed_is_git_tracked_under_conf_seeds_not_data():
    assert AOSS_FREE_SEED.is_file(), f"tracked seed missing: {AOSS_FREE_SEED}"
    assert ANACONDA_DIST_SEED.is_file(), f"tracked seed missing: {ANACONDA_DIST_SEED}"
    for seed in (AOSS_FREE_SEED, ANACONDA_DIST_SEED):
        assert "data" not in seed.relative_to(CONF_SOURCE.parent).parts[:1]


def test_aoss_free_real_seed_meets_the_1000_floor():
    ds = TrackedSeedDataset(filepath=str(AOSS_FREE_SEED))
    frame = ds.load()
    assert list(frame.columns) == ["pypi_name", "source"]
    assert (frame["source"] == "tracked_seed").all()
    _assert_floor(frame, AOSS_FREE_FLOOR, "AOSS free Python (real committed seed)")


def test_aoss_free_seed_below_floor_fails_not_warns(tmp_path):
    """The matrix row: a 500-row seed (< 1,000) must FAIL the floor assertion."""
    seed = tmp_path / "short_seed.json"
    seed.write_text(json.dumps([f"pkg-{i}" for i in range(500)]), encoding="utf-8")
    frame = TrackedSeedDataset(filepath=str(seed)).load()
    assert len(frame) == 500
    with pytest.raises(AssertionError, match="below the documented scale-sanity floor"):
        _assert_floor(frame, AOSS_FREE_FLOOR, "AOSS free Python (fixture)")


# -- Anaconda main: fixture-injected channeldata ------------------------------


def test_anaconda_main_fixture_meets_the_5000_floor():
    # Live 2026-08-30: conda.anaconda.org/anaconda/channeldata.json carries 5,401 packages;
    # the fixture mirrors that magnitude through the SAME (unchanged) parser + node.
    raw = channeldata_json_to_rows(_channeldata_payload(5_401))
    out = enumerate_anaconda_main_packages(raw)
    assert list(out.columns) == ["conda_name", "subdirs"]
    _assert_floor(out, ANACONDA_MAIN_FLOOR, "Anaconda main channeldata (fixture)")


def test_anaconda_main_fixture_below_floor_fails_not_warns():
    raw = channeldata_json_to_rows(_channeldata_payload(4_000))
    out = enumerate_anaconda_main_packages(raw)
    with pytest.raises(AssertionError, match="below the documented scale-sanity floor"):
        _assert_floor(out, ANACONDA_MAIN_FLOOR, "Anaconda main channeldata (fixture)")


# -- Basilisk packages: non-zero when the (fixture) API is healthy ------------


def _basilisk_page(offset: int, size: int, total: int) -> str:
    items = [
        {"name": f"pkg-{i}", "browse_ecosystem": "conda-forge", "latest_version": "1.0"}
        for i in range(offset, min(offset + size, total))
    ]
    return json.dumps({"total": total, "offset": offset, "limit": size, "items": items})


def test_basilisk_packages_non_zero_when_fixture_api_healthy(tmp_path):
    total, size = 450, 200

    def fetcher(url: str) -> str:
        offset = int(url.rsplit("offset=", 1)[-1])
        return _basilisk_page(offset, size, total)

    ds = BasiliskPackagesDataset(
        url="https://api.basilisk.prefix.dev/v1/packages",
        filepath=str(tmp_path / "basilisk"),
        fetcher=fetcher,
        page_size=size,
    )
    ds.save(RefreshRequest(store="discovery_basilisk_packages_raw", force=True))
    frame = ds.load()
    assert len(frame) == total, "Basilisk package catalog must be non-zero when the API is healthy"
    assert len(frame) > 0
    assert ds.is_stale() is False


def test_basilisk_packages_zero_rows_from_healthy_fixture_would_fail(tmp_path):
    """The qualitative floor's negative: a healthy-looking fetcher that yields nothing
    leaves the store EMPTY + STALE — and the floor check on that outcome fails."""
    ds = BasiliskPackagesDataset(
        url="https://api.basilisk.prefix.dev/v1/packages",
        filepath=str(tmp_path / "basilisk"),
        fetcher=lambda url: json.dumps({"total": 0, "items": []}),
    )
    ds.save(RefreshRequest(store="discovery_basilisk_packages_raw", force=True))
    frame = ds.load()
    assert ds.is_stale() is True
    with pytest.raises(AssertionError):
        assert len(frame) > 0, "Basilisk package catalog is zero"
