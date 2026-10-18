"""Story 34.4 (CAP-64): Anaconda's monthly download parquet fills the five download tables.

Network-free: the bucket listing and each month's parquet are built in memory in the shape
measured on 2026-10-18 (dictionary-encoded columns, ``''`` for a noarch platform and an
unknown Python), and ``S3DownloadStatsDataset._get`` is replaced by a dict lookup.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from kedro.io import DatasetError
from pyforge.testing_kit import flag_states

from pyforge.atlas.datasets import S3DownloadStatsDataset
from pyforge.atlas.datasets import s3_downloads as S3
from pyforge.atlas.pipelines.core.nodes import compute_downloads, compute_version_download_history
from pyforge.atlas.provenance import resolve_for_catalog_dataset

BASE = "https://bucket.example.invalid"
ROWS = {
    "2026-08": [
        # data_source, pkg_name, pkg_version, pkg_platform, pkg_python, counts
        ("conda-forge", "numpy", "2.0", "linux-64", "3.12", 100),
        ("conda-forge", "numpy", "2.0", "osx-arm64", "3.12", 40),
        ("anaconda", "numpy", "2.0", "linux-64", "3.12", 900),  # another channel: the channel cut only
        ("conda-forge", "py_thing", "1.0", "", "", 5),  # '' platform is noarch
        ("conda-forge", "py-thing", "1.0", "linux-64", "3.12", 11),  # its own conda package: never merged
    ],
    "2026-09": [
        ("conda-forge", "numpy", "2.1", "linux-64", "3.13", 70),
        ("conda-forge", "numpy", "2.1", "linux-64", "7.3", 3),  # dirty pkg_python: no pyver row
        ("conda-forge", "", "1.0", "linux-64", "3.12", 99),  # no package name: dropped
        ("bioconda", "py_thing", "1.0", "", "", 2),
    ],
}


def _parquet(rows: list[tuple[Any, ...]]) -> bytes:
    cols = list(zip(*rows))
    table = pa.table(
        {
            "time": pa.array(["x"] * len(rows), pa.large_string()),
            "data_source": pa.array(cols[0]).dictionary_encode(),
            "pkg_name": pa.array(cols[1]).dictionary_encode(),
            "pkg_version": pa.array(cols[2]).dictionary_encode(),
            "pkg_platform": pa.array(cols[3]).dictionary_encode(),
            "pkg_python": pa.array(cols[4]).dictionary_encode(),
            "counts": pa.array(cols[5], pa.int64()),
        }
    )
    buf = io.BytesIO()
    pq.write_table(table, buf)
    return buf.getvalue()


def _listing(etags: dict[str, str], token: str | None = None) -> bytes:
    items = "".join(
        f"<Contents><Key>conda/monthly/{m[:4]}/{m}.parquet</Key><ETag>&quot;{e}&quot;</ETag><Size>1</Size></Contents>"
        for m, e in etags.items()
    )
    more = f"<IsTruncated>true</IsTruncated><NextContinuationToken>{token}</NextContinuationToken>" if token else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?><ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        f"<Name>anaconda-package-data</Name>{items}{more or '<IsTruncated>false</IsTruncated>'}</ListBucketResult>"
    ).encode()


class _Bucket:
    """The bucket as ``url -> bytes | Exception``; records every URL requested."""

    def __init__(self, etags: dict[str, str] | None = None) -> None:
        self.etags = dict(etags) if etags is not None else {"2026-08": "e8", "2026-09": "e9"}
        self.bodies: dict[str, Any] = {
            f"{BASE}/conda/monthly/{m[:4]}/{m}.parquet": _parquet(r) for m, r in ROWS.items()
        }
        self.listing: Any = None
        self.requested: list[str] = []

    def get(self, url: str) -> bytes:
        self.requested.append(url)
        if "list-type=2" in url:
            body = self.listing if self.listing is not None else _listing(self.etags)
        else:
            body = self.bodies[url]
        if isinstance(body, Exception):
            raise body
        return body

    def months_fetched(self) -> list[str]:
        return [u.rsplit("/", 1)[-1][:7] for u in self.requested if u.endswith(".parquet")]


def _dataset(tmp_path: Path, bucket: _Bucket, view: str = "breakdown") -> S3DownloadStatsDataset:
    ds = S3DownloadStatsDataset(url=BASE, view=view, filepath=str(tmp_path / "s3"))
    ds._get = bucket.get  # type: ignore[method-assign]
    return ds


@pytest.fixture()
def live(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(S3, "read_boolean", lambda key, default=False: key == S3.FLAG_KEY)


def _marker(tmp_path: Path) -> dict[str, Any] | None:
    p = tmp_path / "s3" / S3DownloadStatsDataset.STALENESS_FILENAME
    return json.loads(p.read_text()) if p.is_file() else None


# -- parsing ---------------------------------------------------------------------------


def test_listing_parses_month_keys_etags_and_the_continuation_token() -> None:
    months, token = S3.parse_s3_listing(_listing({"2017-01": "a", "2026-09": "b"}, token="t/1"))

    assert months == {"2017-01": "a", "2026-09": "b"}
    assert token == "t/1"
    assert S3.parse_s3_listing(_listing({"2026-09": "b"}))[1] is None


@pytest.mark.parametrize("body", [b"<html>not a listing</html>", b"not xml at all"])
def test_a_body_that_is_not_a_listing_raises_value_error(body: bytes) -> None:
    with pytest.raises(ValueError):
        S3.parse_s3_listing(body)


def test_a_month_aggregates_into_the_two_views() -> None:
    breakdown, versions = S3.aggregate_month("2026-08", _parquet(ROWS["2026-08"]))

    got = {tuple(r) for r in breakdown[S3.BREAKDOWN_COLUMNS].itertuples(index=False)}
    assert got == {
        ("numpy", "2026-08", "linux-64", "3.12", "conda-forge", 100),
        ("numpy", "2026-08", "osx-arm64", "3.12", "conda-forge", 40),
        ("numpy", "2026-08", "linux-64", "3.12", "anaconda", 900),
        ("py_thing", "2026-08", "noarch", "", "conda-forge", 5),
        ("py-thing", "2026-08", "linux-64", "3.12", "conda-forge", 11),
    }
    # versions read the home channel only
    assert {tuple(r) for r in versions.itertuples(index=False)} == {
        ("numpy", "2.0", 140),
        ("py_thing", "1.0", 5),
        ("py-thing", "1.0", 11),
    }


def test_a_row_with_no_package_name_is_dropped() -> None:
    breakdown, _ = S3.aggregate_month("2026-09", _parquet(ROWS["2026-09"]))

    assert "" not in set(breakdown["conda_name"])


# -- the month cache -------------------------------------------------------------------


def test_the_first_load_fetches_every_month_and_a_second_fetches_none(tmp_path: Path, live: None) -> None:
    bucket = _Bucket()

    first = _dataset(tmp_path, bucket).load()
    assert sorted(bucket.months_fetched()) == ["2026-08", "2026-09"]
    bucket.requested.clear()
    second = _dataset(tmp_path, bucket, view="versions").load()

    assert bucket.months_fetched() == []  # every ETag current: the two views share one cache
    assert len(first) == 8 and set(first["month"]) == {"2026-08", "2026-09"}
    assert _marker(tmp_path) is None
    # the versions view sums a version across months
    assert {tuple(r) for r in second.itertuples(index=False)} == {
        ("numpy", "2.0", 140),
        ("numpy", "2.1", 73),
        ("py_thing", "1.0", 5),
        ("py-thing", "1.0", 11),
    }


def test_a_new_etag_refetches_that_month_only(tmp_path: Path, live: None) -> None:
    bucket = _Bucket()
    _dataset(tmp_path, bucket).load()
    bucket.requested.clear()
    bucket.etags["2026-09"] = "e9-republished"
    bucket.etags["2026-10"] = "e10"
    bucket.bodies[f"{BASE}/conda/monthly/2026/2026-10.parquet"] = _parquet(
        [("conda-forge", "numpy", "2.1", "linux-64", "3.13", 1)]
    )

    out = _dataset(tmp_path, bucket).load()

    assert sorted(bucket.months_fetched()) == ["2026-09", "2026-10"]
    assert out["month"].max() == "2026-10"


def test_a_failed_listing_keeps_the_cache_under_a_marker(tmp_path: Path, live: None) -> None:
    bucket = _Bucket()
    good = _dataset(tmp_path, bucket).load()
    bucket.listing = DatasetError("unreachable")

    kept = _dataset(tmp_path, bucket).load()

    assert len(kept) == len(good)
    marker = _marker(tmp_path)
    assert marker is not None and marker["last_good_exists"] is True
    assert marker["reason"].startswith("listing failed: DatasetError")


def test_a_failed_month_keeps_the_others_and_names_it(tmp_path: Path, live: None) -> None:
    bucket = _Bucket()
    bucket.bodies[f"{BASE}/conda/monthly/2026/2026-09.parquet"] = b"PAR1 truncated"

    out = _dataset(tmp_path, bucket).load()

    assert set(out["month"]) == {"2026-08"}
    assert "1 of 2 months not refreshed (2026-09:" in _marker(tmp_path)["reason"]
    # the next run retries the month that failed, and only that one
    bucket.bodies[f"{BASE}/conda/monthly/2026/2026-09.parquet"] = _parquet(ROWS["2026-09"])
    bucket.requested.clear()
    _dataset(tmp_path, bucket).load()
    assert bucket.months_fetched() == ["2026-09"] and _marker(tmp_path) is None


def test_a_listing_with_no_months_keeps_the_cache(tmp_path: Path, live: None) -> None:
    bucket = _Bucket(etags={})

    out = _dataset(tmp_path, bucket).load()

    assert out.empty and list(out.columns) == S3.BREAKDOWN_COLUMNS
    assert _marker(tmp_path)["reason"].startswith("listing names no months")


def test_a_programming_error_raises(tmp_path: Path, live: None) -> None:
    bucket = _Bucket()
    bucket.listing = KeyError("bug")

    with pytest.raises(DatasetError) as raised:  # kedro's load wrapper
        _dataset(tmp_path, bucket).load()
    assert isinstance(raised.value.__cause__, KeyError)


def test_an_unknown_view_is_refused() -> None:
    with pytest.raises(TypeError):
        S3DownloadStatsDataset(url=BASE, view="monthly")


def test_without_filepath_the_dataset_is_the_empty_frame() -> None:
    out = S3DownloadStatsDataset(url=BASE).load()

    assert out.empty and list(out.columns) == S3.BREAKDOWN_COLUMNS


@flag_states(S3.FLAG_KEY)
def test_the_flag_gates_every_fetch(
    tmp_path: Path, flag_provider: dict[str, bool], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Off: the cache is served and nothing is requested (today's behaviour on a fresh root: empty)."""
    flag_on = flag_provider[S3.FLAG_KEY]
    monkeypatch.setattr(S3, "read_boolean", lambda key, default=False: flag_on if key == S3.FLAG_KEY else default)
    bucket = _Bucket()

    out = _dataset(tmp_path, bucket).load()

    if flag_on:
        assert len(out) == 8 and bucket.requested
    else:
        assert out.empty and bucket.requested == []


def test_provenance_reports_the_cache_and_the_marker(tmp_path: Path, live: None) -> None:
    bucket = _Bucket()
    fresh = _dataset(tmp_path, bucket)
    assert resolve_for_catalog_dataset({"x": fresh}, "x", fresh.load()).kind == "live-fetch"

    bucket.listing = DatasetError("unreachable")
    stale = _dataset(tmp_path, bucket)
    info = resolve_for_catalog_dataset({"x": stale}, "x", stale.load())

    assert info.kind == "file-mtime" and info.build_stamp is not None
    assert info.reason is not None and info.reason.startswith("stale: listing failed")


# -- the nodes over the s3 views ---------------------------------------------------------


def test_compute_downloads_reads_totals_from_the_home_channel(tmp_path: Path, live: None) -> None:
    s3 = _dataset(tmp_path, _Bucket()).load()
    ana = pd.DataFrame(columns=["conda_name", "version", "downloads"])

    downloads, platform, pyver, channel = compute_downloads(ana, s3)

    totals = downloads.set_index("conda_name")
    assert totals.loc["numpy", "downloads_total"] == 213  # 100 + 40 + 70 + 3; anaconda's 900 is not conda-forge's
    assert totals.loc["numpy", "downloads_30d"] == 73  # the latest month
    assert totals.loc["py_thing", "downloads_total"] == 5  # bioconda's 2 is another channel
    assert totals.loc["py-thing", "downloads_total"] == 11  # its own package: never merged with py_thing
    assert {tuple(r) for r in channel.itertuples(index=False)} >= {
        ("numpy", "anaconda", 900),
        ("py_thing", "bioconda", 2),
    }
    assert ("numpy", "7.3") not in {(r.conda_name, r.pyver) for r in pyver.itertuples()}
    assert ("py_thing", "noarch", 5) in {tuple(r) for r in platform.itertuples(index=False)}
    for frame in (downloads, platform, pyver, channel):
        assert not any(isinstance(frame[c].dtype, pd.CategoricalDtype) for c in frame.columns)


def test_version_history_prefers_s3_and_fills_from_the_api(tmp_path: Path, live: None) -> None:
    s3 = _dataset(tmp_path, _Bucket(), view="versions").load()
    ana = pd.DataFrame({"conda_name": ["numpy", "scipy"], "version": ["2.0", "1.0"], "downloads": [999, 50]})

    hist = compute_version_download_history(ana, s3)

    rows = {tuple(r) for r in hist.itertuples(index=False)}
    assert ("numpy", "2.0", 140) in rows and ("numpy", "2.0", 999) not in rows  # never summed across sources
    assert ("scipy", "1.0", 50) in rows  # a package s3 lacks keeps its api rows
