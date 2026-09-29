"""Story 21.4 — Tier 1 scale-sanity floors (catalog-sources.md "Scale sanity gates").

Offline, fixture-injected floor assertions for the three floors this story owns:

- AOSS free Python  — ≥ 1,000 rows, asserted against the REAL committed seed file
  (``TrackedSeedDataset`` needs no injected fetcher, so the actual git-tracked artifact
  is what is tested, not a synthetic stand-in);
- Anaconda main     — ≥ 5,000 rows, asserted against a fixture-injected channeldata
  payload of realistic size through the UNCHANGED ``channeldata_json_to_rows`` parser;
- Basilisk packages — non-zero when a fixture fetcher returns data (qualitative).

Story 23.1 extends this module with Tier 3 OS-distro bulk-index floors (homebrew,
nixpkgs, spack, debian, fedora) — sub-threshold FAILS the assertion (never warn-only).

Sub-threshold FAILS the assertion (never a log-only warning). No network anywhere —
this whole ``tests/catalog/`` suite is offline and non-credentialed by design
(AD-11/NFR-1); "Bootstrap smoke" in catalog-sources.md's wording is satisfied here.
"""

from __future__ import annotations

import json
import shutil
import subprocess

import pandas as pd
import pytest

from pyforge.atlas.datasets import (
    BasiliskPackagesDataset,
    RefreshRequest,
    TrackedSeedDataset,
    channeldata_json_to_rows,
)
from pyforge.atlas.datasets.rate_limit import RateLimitedScheduler
from pyforge.atlas.datasets.tier3_sources import (
    parse_debian_packages_control,
    parse_fedora_packages,
    parse_homebrew_formulae_json,
    parse_nixpkgs_packages_json,
    parse_spack_packages,
)
from pyforge.atlas.pipelines.core.nodes import enumerate_anaconda_main_packages

from .conftest import CONF_SOURCE

# The documented order-of-magnitude floors (catalog-sources.md "Scale sanity gates").
AOSS_FREE_FLOOR = 1_000
ANACONDA_MAIN_FLOOR = 5_000
HOMEBREW_FLOOR = 5_000
NIXPKGS_FLOOR = 50_000
SPACK_FLOOR = 3_000
DEBIAN_FLOOR = 20_000
FEDORA_FLOOR = 15_000

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


def _git_says_not_ignored(path) -> bool | None:
    """``git check-ignore -q <path>`` exit 1 == NOT ignored (0 == ignored). ``None``
    when git is unavailable or the tree is not a git checkout (caller skips)."""
    git = shutil.which("git")
    if git is None:
        return None
    try:
        inside = subprocess.run(
            [git, "rev-parse", "--is-inside-work-tree"],
            cwd=path.parent,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except OSError, subprocess.SubprocessError:
        return None
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return None
    probe = subprocess.run([git, "check-ignore", "-q", str(path)], cwd=path.parent, capture_output=True, timeout=30)
    if probe.returncode == 0:
        return False  # ignored
    if probe.returncode == 1:
        return True  # not ignored
    return None  # 128 = fatal (not a checkout / bad path) -> skip


def test_aoss_free_seed_is_git_tracked_under_conf_seeds_not_data():
    seeds_dir = CONF_SOURCE / "base" / "seeds"
    for seed in (AOSS_FREE_SEED, ANACONDA_DIST_SEED):
        assert seed.is_file(), f"tracked seed missing: {seed}"
        # under conf/base/seeds/ — NEVER under the gitignored data/ root
        assert seed.parent == seeds_dir, seed
        assert seed.relative_to(CONF_SOURCE.parent).parts[:3] == ("conf", "base", "seeds")
        not_ignored = _git_says_not_ignored(seed)
        if not_ignored is None:
            pytest.skip("git unavailable or not a git checkout — cannot verify ignore status")
        assert not_ignored, f"{seed} is gitignored — it would NOT survive a fresh clone"


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


def _no_sleep_scheduler() -> RateLimitedScheduler:
    """Frozen clock + no sleep: multi-page walks burn no wall-clock here."""
    return RateLimitedScheduler(rps=1000.0, bucket_capacity=100, clock=lambda: 0.0, sleep=lambda s: None)


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
        scheduler=_no_sleep_scheduler(),
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
        scheduler=_no_sleep_scheduler(),
    )
    ds.save(RefreshRequest(store="discovery_basilisk_packages_raw", force=True))
    frame = ds.load()
    assert ds.is_stale() is True
    with pytest.raises(AssertionError):
        assert len(frame) > 0, "Basilisk package catalog is zero"


# -- Story 23.1: Tier 3 OS-distro bulk-index scale floors ---------------------


def _homebrew_fixture(n: int) -> str:
    return json.dumps([{"name": f"pkg-{i}"} for i in range(n)])


def _nixpkgs_fixture(n: int) -> str:
    return json.dumps({f"python3Packages.pkg{i}": {} for i in range(n)})


def _spack_fixture(n: int) -> str:
    return json.dumps([f"py-pkg-{i}" for i in range(n)])


def _debian_fixture(n: int) -> str:
    return "\n\n".join(f"Package: python3-pkg-{i}" for i in range(n))


def _fedora_fixture(n: int) -> str:
    return json.dumps({"projects": [{"name": f"python-pkg-{i}"} for i in range(n)]})


@pytest.mark.parametrize(
    ("parser", "fixture_fn", "floor", "label"),
    [
        (parse_homebrew_formulae_json, _homebrew_fixture, HOMEBREW_FLOOR, "homebrew"),
        (parse_nixpkgs_packages_json, _nixpkgs_fixture, NIXPKGS_FLOOR, "nixpkgs"),
        (parse_spack_packages, _spack_fixture, SPACK_FLOOR, "spack"),
        (parse_debian_packages_control, _debian_fixture, DEBIAN_FLOOR, "debian"),
        (parse_fedora_packages, _fedora_fixture, FEDORA_FLOOR, "fedora"),
    ],
)
def test_tier3_fixture_meets_documented_floor(parser, fixture_fn, floor, label):
    names = parser(fixture_fn(floor))
    _assert_floor(pd.DataFrame({"name": names}), floor, label)


@pytest.mark.parametrize(
    ("parser", "fixture_fn", "floor", "label"),
    [
        (parse_homebrew_formulae_json, _homebrew_fixture, HOMEBREW_FLOOR, "homebrew"),
        (parse_nixpkgs_packages_json, _nixpkgs_fixture, NIXPKGS_FLOOR, "nixpkgs"),
    ],
)
def test_tier3_fixture_below_floor_fails_not_warns(parser, fixture_fn, floor, label):
    names = parser(fixture_fn(floor - 1))
    with pytest.raises(AssertionError, match="below the documented scale-sanity floor"):
        _assert_floor(pd.DataFrame({"name": names}), floor, label)
