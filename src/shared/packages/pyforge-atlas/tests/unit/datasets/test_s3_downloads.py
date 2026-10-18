"""Story 34.4 (CAP-64): Anaconda's monthly download parquet fills the five download tables.

Network-free: the bucket listing and each month's parquet are built in memory in the shape
measured on 2026-10-18 (dictionary-encoded columns, ``''`` for a noarch platform and an
unknown Python), and ``S3DownloadStatsDataset._get`` is replaced by a dict lookup, except in
the one test that drives ``_get`` through a stand-in ``APIDataset``.
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

from pyforge.atlas.datasets import S3DownloadStatsDataset, public_sources
from pyforge.atlas.datasets import s3_downloads as S3
from pyforge.atlas.pipelines.core.nodes import compute_downloads, compute_version_download_history
from pyforge.atlas.provenance import resolve_for_catalog_dataset

BASE = "https://bucket.example.invalid"
ROWS = {
    "2026-08": [
        # data_source, pkg_name, pkg_version, pkg_platform, pkg_python, counts
        ("conda-forge", "numpy", "2.0", "linux-64", "3.12", 100),
        ("conda-forge", "numpy", "2.0", "osx-arm64", "3.12", 40),
        ("conda-forge", "numpy", "2.1", "linux-64", "3.13", 6),  # 2.1 spans both months
        ("anaconda", "numpy", "2.0", "linux-64", "3.12", 900),  # another channel: the channel cut only
        ("conda-forge", "py_thing", "1.0", "", "", 5),  # '' platform is noarch
        ("conda-forge", "py-thing", "1.0", "linux-64", "3.12", 11),  # its own conda package: never merged
        ("conda-forge", "python%5fabi", "1.0", "linux-64", "3.12", 4),  # URL-encoded debris: no package
    ],
    "2026-09": [
        ("conda-forge", "numpy", "2.1", "linux-64", "3.13", 70),
        ("conda-forge", "numpy", "2.1", "linux-64", "7.3", 3),  # dirty pkg_python values legacy drops
        ("conda-forge", "numpy", "2.1", "linux-64", "3.81", 2),
        ("conda-forge", "numpy", "2.1", "linux-64", "2.30", 1),
        ("conda-forge", "", "1.0", "linux-64", "3.12", 99),  # no package name: dropped
        ("conda-forge", "PyHive", "0.6", "noarch", "", 8),  # outside conda's lowercase grammar: dropped
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


def _listing(etags: dict[str, str], token: str | None = None, ns: bool = True) -> bytes:
    items = "".join(
        f"<Contents><Key>conda/monthly/{m[:4]}/{m}.parquet</Key><ETag>&quot;{e}&quot;</ETag><Size>1</Size></Contents>"
        for m, e in etags.items()
    )
    more = f"<IsTruncated>true</IsTruncated><NextContinuationToken>{token}</NextContinuationToken>" if token else ""
    xmlns = ' xmlns="http://s3.amazonaws.com/doc/2006-03-01/"' if ns else ""
    return (
        f'<?xml version="1.0" encoding="UTF-8"?><ListBucketResult{xmlns}>'
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
        self.paged = False  # two listing pages: 2026-08, then (behind a token) 2026-09
        self.requested: list[str] = []

    def get(self, url: str) -> bytes:
        self.requested.append(url)
        if "list-type=2" in url:
            if self.paged:
                if "continuation-token=" not in url:
                    body: Any = _listing({"2026-08": "e8"}, token="t/1+")
                else:
                    assert url.endswith("continuation-token=t%2F1%2B")  # the token, quoted
                    body = _listing({"2026-09": "e9"})
            else:
                body = self.listing if self.listing is not None else _listing(self.etags)
        else:
            body = self.bodies[url]
        if isinstance(body, Exception):
            raise body
        return body

    def months_fetched(self) -> list[str]:
        return [u.rsplit("/", 1)[-1][:7] for u in self.requested if u.endswith(".parquet")]

    def listings(self) -> int:
        return sum("list-type=2" in u for u in self.requested)


def _dataset(tmp_path: Path, bucket: _Bucket, view: str = "breakdown") -> S3DownloadStatsDataset:
    ds = S3DownloadStatsDataset(url=BASE, view=view, filepath=str(tmp_path / "s3"))
    ds._get = bucket.get  # type: ignore[method-assign]
    return ds


@pytest.fixture()
def live(monkeypatch: pytest.MonkeyPatch) -> None:
    """The root conftest pins every test offline; these tests drive the live path."""
    monkeypatch.setattr(public_sources, "live", lambda: True)


def _marker(tmp_path: Path) -> dict[str, Any] | None:
    p = tmp_path / "s3" / S3DownloadStatsDataset.STALENESS_FILENAME
    return json.loads(p.read_text()) if p.is_file() else None


def _rows(frame: pd.DataFrame) -> set[tuple[Any, ...]]:
    return {tuple(r) for r in frame.itertuples(index=False)}


# -- parsing ---------------------------------------------------------------------------


def test_listing_parses_month_keys_etags_and_the_continuation_token() -> None:
    months, token = S3.parse_s3_listing(_listing({"2017-01": "a", "2026-09": "b"}, token="t/1"))

    assert months == {"2017-01": "a", "2026-09": "b"}
    assert token == "t/1"
    assert S3.parse_s3_listing(_listing({"2026-09": "b"}))[1] is None


def test_listing_ignores_namespaces_and_keys_outside_the_month_layout() -> None:
    body = (
        b"<ListBucketResult><IsTruncated>false</IsTruncated>"
        b"<Contents><Key>conda/monthly/2026/2026-08.parquet</Key><ETag>a</ETag></Contents>"
        b"<Contents><Key>conda/monthly/2025/2026-09.parquet</Key><ETag>b</ETag></Contents>"
        b"<Contents><Key>conda/monthly/notes-2026-10.parquet</Key><ETag>c</ETag></Contents>"
        b"</ListBucketResult>"
    )

    assert S3.parse_s3_listing(body) == ({"2026-08": "a"}, None)


@pytest.mark.parametrize("body", [b"<html>not a listing</html>", b"not xml at all"])
def test_a_body_that_is_not_a_listing_raises_value_error(body: bytes) -> None:
    with pytest.raises(ValueError):
        S3.parse_s3_listing(body)


def test_a_month_aggregates_into_the_two_views() -> None:
    breakdown, versions = S3.aggregate_month("2026-08", _parquet(ROWS["2026-08"]))

    assert _rows(breakdown[S3.BREAKDOWN_COLUMNS]) == {
        ("numpy", "2026-08", "linux-64", "3.12", "conda-forge", 100),
        ("numpy", "2026-08", "osx-arm64", "3.12", "conda-forge", 40),
        ("numpy", "2026-08", "linux-64", "3.13", "conda-forge", 6),
        ("numpy", "2026-08", "linux-64", "3.12", "anaconda", 900),
        ("py_thing", "2026-08", "noarch", "", "conda-forge", 5),
        ("py-thing", "2026-08", "linux-64", "3.12", "conda-forge", 11),
    }
    # versions read the home channel only
    assert _rows(versions) == {
        ("numpy", "2.0", 140),
        ("numpy", "2.1", 6),
        ("py_thing", "1.0", 5),
        ("py-thing", "1.0", 11),
    }


def test_a_name_outside_the_conda_grammar_is_dropped() -> None:
    breakdown, versions = S3.aggregate_month("2026-09", _parquet(ROWS["2026-09"]))

    assert set(breakdown["conda_name"]) == {"numpy", "py_thing"}  # not '', 'PyHive' or 'python%5fabi'
    assert set(versions["conda_name"]) == {"numpy"}


# -- the month cache -------------------------------------------------------------------


def test_the_first_load_fetches_every_month_and_a_second_fetches_none(tmp_path: Path, live: None) -> None:
    bucket = _Bucket()

    first = _dataset(tmp_path, bucket).load()
    assert sorted(bucket.months_fetched()) == ["2026-08", "2026-09"]
    bucket.requested.clear()
    second = _dataset(tmp_path, bucket, view="versions").load()

    assert bucket.months_fetched() == []  # every ETag current: the two views share one cache
    assert len(first) == 11 and set(first["month"]) == {"2026-08", "2026-09"}
    assert _marker(tmp_path) is None
    # the versions view sums a version across months: numpy 2.1 is 6 (Aug) + 76 (Sep)
    assert _rows(second) == {
        ("numpy", "2.0", 140),
        ("numpy", "2.1", 82),
        ("py_thing", "1.0", 5),
        ("py-thing", "1.0", 11),
    }


def test_a_two_page_listing_sends_the_token_and_stops(tmp_path: Path, live: None) -> None:
    bucket = _Bucket()
    bucket.paged = True

    out = _dataset(tmp_path, bucket).load()

    assert bucket.listings() == 2
    assert set(out["month"]) == {"2026-08", "2026-09"}


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


def test_a_missing_view_file_refetches_its_month(tmp_path: Path, live: None) -> None:
    bucket = _Bucket()
    _dataset(tmp_path, bucket).load()
    (tmp_path / "s3" / "months" / "2026-08.versions.parquet").unlink()
    bucket.requested.clear()

    _dataset(tmp_path, bucket).load()

    assert bucket.months_fetched() == ["2026-08"]  # its ETag is current, but a view is gone


def test_a_manifest_of_another_aggregate_version_refetches_every_month(tmp_path: Path, live: None) -> None:
    bucket = _Bucket()
    _dataset(tmp_path, bucket).load()
    manifest = tmp_path / "s3" / S3DownloadStatsDataset.MANIFEST_FILENAME
    doc = json.loads(manifest.read_text())
    manifest.write_text(json.dumps({**doc, "aggregate_version": S3.AGGREGATE_VERSION - 1}))
    bucket.requested.clear()

    _dataset(tmp_path, bucket).load()

    assert sorted(bucket.months_fetched()) == ["2026-08", "2026-09"]
    assert json.loads(manifest.read_text())["aggregate_version"] == S3.AGGREGATE_VERSION


def test_a_failed_listing_keeps_the_cache_under_a_marker(tmp_path: Path, live: None) -> None:
    bucket = _Bucket()
    good = _dataset(tmp_path, bucket).load()
    bucket.listing = DatasetError("unreachable")

    kept = _dataset(tmp_path, bucket).load()

    assert len(kept) == len(good)
    marker = _marker(tmp_path)
    assert marker is not None and marker["last_good_exists"] is True
    assert marker["reason"].startswith("listing failed: DatasetError")


def test_a_listing_that_is_not_a_listing_marks_stale(tmp_path: Path, live: None) -> None:
    """A proxy's HTML page, or a mirror's error body: stale, never a crash."""
    bucket = _Bucket()
    bucket.listing = b"<html>maintenance</html>"

    out = _dataset(tmp_path, bucket).load()

    assert out.empty
    assert _marker(tmp_path)["reason"].startswith("listing failed: ValueError")


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


def test_the_fetch_composes_an_api_dataset_with_a_timeout(
    tmp_path: Path, live: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``_get`` itself (AD-2): one composed APIDataset per URL, a timeout, a bytes body."""
    bucket = _Bucket()
    calls: list[tuple[str, Any]] = []

    class _Response:
        def __init__(self, content: Any) -> None:
            self.content = content

    class _API:
        def __init__(self, *, url: str, load_args: Any = None) -> None:
            calls.append((url, dict(load_args)))
            load_args.pop("auth", None)  # what kedro's APIDataset does to the dict it is given
            self._url = url

        def load(self) -> _Response:
            if self._url.endswith("2026-09.parquet"):
                return _Response("a text body")  # not bytes: that month fails, the other is kept
            return _Response(bucket.get(self._url))

    monkeypatch.setattr(S3, "APIDataset", _API)
    ds = S3DownloadStatsDataset(url=BASE, filepath=str(tmp_path / "s3"))

    out = ds.load()

    url, load_args = calls[0]
    assert url == f"{BASE}/?list-type=2&prefix=conda/monthly/" and load_args["timeout"] == 300
    sentinel = object()
    assert load_args["auth"](sentinel) is sentinel  # a no-op auth: requests never reads ~/.netrc
    assert all("auth" in args for _, args in calls)  # every request, not only the first
    assert set(out["month"]) == {"2026-08"}
    assert "2026-09: DatasetError" in _marker(tmp_path)["reason"]


def test_an_unknown_view_is_refused() -> None:
    with pytest.raises(TypeError):
        S3DownloadStatsDataset(url=BASE, view="monthly")


def test_without_filepath_the_dataset_is_the_empty_frame() -> None:
    out = S3DownloadStatsDataset(url=BASE).load()

    assert out.empty and list(out.columns) == S3.BREAKDOWN_COLUMNS


@flag_states("pyforge.atlas.live_public_sources")  # spelled out: the flag gate reads this file for the key
def test_the_flag_gates_every_fetch(
    tmp_path: Path, flag_provider: dict[str, bool], monkeypatch: pytest.MonkeyPatch
) -> None:
    """On: the dataset fetches. Off: nothing is requested (today's behaviour on a fresh root: empty)."""
    flag_on = flag_provider[S3.FLAG_KEY]
    monkeypatch.setattr(public_sources, "live", lambda: flag_on)
    bucket = _Bucket()

    out = _dataset(tmp_path, bucket).load()

    if flag_on:
        assert len(out) == 11 and bucket.requested
    else:
        assert out.empty and bucket.requested == []


def test_flag_off_serves_the_cache_as_it_stood(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The Epic's OFF state keeps last-good: a filled cache is served, unrefreshed, and provenance
    reports the cache's own age, never "now"."""
    monkeypatch.setattr(public_sources, "live", lambda: True)
    bucket = _Bucket()
    filled = _dataset(tmp_path, bucket).load()
    monkeypatch.setattr(public_sources, "live", lambda: False)
    bucket.requested.clear()

    ds = _dataset(tmp_path, bucket)
    served = ds.load()
    info = resolve_for_catalog_dataset({"x": ds}, "x", served)

    assert bucket.requested == []
    pd.testing.assert_frame_equal(served, filled)
    assert info.kind == "file-mtime" and info.reason == "not fetched this load: the copy as last fetched"


def test_flag_off_on_a_fresh_root_says_there_is_no_copy(tmp_path: Path) -> None:
    ds = _dataset(tmp_path, _Bucket())

    info = resolve_for_catalog_dataset({"x": ds}, "x", ds.load())

    assert info.kind == "unavailable"
    assert info.reason is not None and info.reason.startswith("not fetched this load, and no copy:")


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
    assert totals.loc["numpy", "downloads_total"] == 222  # 146 + 76; anaconda's 900 is not conda-forge's
    assert totals.loc["numpy", "downloads_30d"] == 76  # the latest month
    assert totals.loc["py_thing", "downloads_total"] == 5  # bioconda's 2 is another channel
    assert totals.loc["py_thing", "downloads_30d"] == 0  # nothing in the latest month: 0, as legacy writes it
    assert totals.loc["py-thing", "downloads_total"] == 11  # its own package: never merged with py_thing
    assert _rows(channel) >= {("numpy", "anaconda", 900), ("py_thing", "bioconda", 2)}
    assert _rows(pyver) == {("numpy", "3.12", 140), ("numpy", "3.13", 76), ("py-thing", "3.12", 11)}  # no 7.3/3.81/2.30
    assert ("py_thing", "noarch", 5) in _rows(platform)
    for frame in (downloads, platform, pyver, channel):
        assert not any(isinstance(frame[c].dtype, pd.CategoricalDtype) for c in frame.columns)


def test_version_history_prefers_s3_and_fills_from_the_api(tmp_path: Path, live: None) -> None:
    s3 = _dataset(tmp_path, _Bucket(), view="versions").load()
    ana = pd.DataFrame({"conda_name": ["numpy", "scipy"], "version": ["2.0", "1.0"], "downloads": [999, 50]})

    hist = compute_version_download_history(ana, s3)

    rows = _rows(hist)
    assert ("numpy", "2.0", 140) in rows and ("numpy", "2.0", 999) not in rows  # never summed across sources
    assert ("scipy", "1.0", 50) in rows  # a package s3 lacks keeps its api rows


# -- the one real flag read (the suite pins it OFF everywhere else) ------------------------


@pytest.mark.parametrize("variant", ["on", "off"])
def test_live_reads_the_flag_key_from_the_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, real_live: Any, variant: str
) -> None:
    from pyforge.testing_kit import flagd_tree

    tree = flagd_tree(tmp_path, {public_sources.FLAG_KEY: variant})
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))

    assert real_live() is (variant == "on")


def test_the_shipped_tree_reads_off_in_production(monkeypatch: pytest.MonkeyPatch, real_live: Any) -> None:
    tree = Path(__file__).resolve().parents[7] / "src" / "platform" / "config" / "flags.json"
    assert tree.is_file()  # the shipped tree itself, never a lookup that could pass without it
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "production")

    assert real_live() is False
