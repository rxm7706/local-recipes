"""Story 37.6 (CAP-69): per-version upload times from conda-forge's full repodata.

Network-free: each subdir's ``repodata.json.zst`` is built in memory (``compression.zstd``) in the shape conda-forge
serves (``info``, ``packages``, ``packages.conda``, ``removed``, ``repodata_version``), and
``RepodataUploadsDataset._get`` is replaced by a dict lookup, except in the tests that drive ``_get`` through a
stand-in ``APIDataset``.
"""

from __future__ import annotations

import io
import json
import logging
from compression import zstd
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from kedro.io import DatasetError

from pyforge.atlas.datasets import RepodataUploadsDataset, public_sources
from pyforge.atlas.datasets import repodata_uploads as RU
from pyforge.atlas.provenance import resolve_for_catalog_dataset

BASE = "https://conda.example.invalid/conda-forge"
DAY = 86_400
T0 = 1_700_000_000  # seconds


def _record(name: str | None, version: str | None, timestamp: Any = None, **extra: Any) -> dict[str, Any]:
    rec: dict[str, Any] = {"build": "0", "depends": ["python >=3.11"], "subdir": "noarch", **extra}
    if name is not None:
        rec["name"] = name
    if version is not None:
        rec["version"] = version
    if timestamp is not None:
        rec["timestamp"] = timestamp
    return rec


def _repodata(packages: dict[str, Any], conda: dict[str, Any] | None = None, *, indent: int | None = None) -> bytes:
    doc = {
        "info": {"subdir": "noarch", "base_url": "https://example.invalid"},
        "packages": packages,
        "packages.conda": conda or {},
        "removed": ["gone-1.0-0.tar.bz2"],
        "repodata_version": 12345,
    }
    return zstd.compress(json.dumps(doc, indent=indent, ensure_ascii=False).encode("utf-8"))


NOARCH = _repodata(
    {
        "a-1.0-0.tar.bz2": _record("a", "1.0", (T0 + 5 * DAY) * 1000),  # milliseconds
        "a-1.0-1.tar.bz2": _record("a", "1.0", T0 + 3 * DAY),  # seconds; the earlier
        "b-2.0-0.tar.bz2": _record("b", "2.0"),  # no timestamp
        "nameless-0.tar.bz2": _record(None, "1.0", T0),
        "versionless-0.tar.bz2": _record("v", None, T0),
    },
    # its only file, in milliseconds with a fractional second (as conda-forge serves them): truncated to seconds
    {"a-2.0-0.conda": _record("a", "2.0", (T0 + 9 * DAY) * 1000 + 999, summary="naïve — ünïcode")},
)
LINUX = _repodata(
    {"a-1.0-0.tar.bz2": _record("a", "1.0", T0 + 1 * DAY)},  # earlier than noarch's
    {"b-2.0-0.conda": _record("b", "2.0", 0), "c-0.1-0.conda": _record("c", "0.1", True)},  # 0 and a bool: no time
    indent=2,
)


def _rows(frame: pd.DataFrame) -> dict[tuple[str, str], tuple[Any, int]]:
    return {
        (n, v): (None if pd.isna(u) else int(u), int(c))
        for n, v, u, c in frame[["conda_name", "version", "upload_unix", "file_count"]].itertuples(index=False)
    }


# --------------------------------------------------------------------------- #
# the stream parse
# --------------------------------------------------------------------------- #


def test_every_record_of_both_sections_is_read_and_aggregated() -> None:
    out = RU.aggregate_subdir(NOARCH)

    assert _rows(out) == {
        ("a", "1.0"): (T0 + 3 * DAY, 2),  # the earlier file; milliseconds read as seconds
        ("a", "2.0"): (T0 + 9 * DAY, 1),  # packages.conda too
        ("b", "2.0"): (None, 1),  # counted, untimed
    }
    assert list(out.columns) == RU.COLUMNS and str(out["upload_unix"].dtype) == "Int64"


@pytest.mark.parametrize("chunk", [1, 2, 3, 5, 7, 64, 1 << 20])
def test_any_chunk_boundary_gives_the_same_records(chunk: int) -> None:
    """A chunk can end inside a multi-byte character, a key, a record or the top-level number."""
    with zstd.ZstdFile(io.BytesIO(NOARCH)) as stream:
        records = dict(RU.iter_repodata_records(stream, chunk=chunk))

    assert set(records) == {
        "a-1.0-0.tar.bz2",
        "a-1.0-1.tar.bz2",
        "b-2.0-0.tar.bz2",
        "nameless-0.tar.bz2",
        "versionless-0.tar.bz2",
        "a-2.0-0.conda",
    }
    assert records["a-2.0-0.conda"]["summary"] == "naïve — ünïcode"


def test_a_number_cut_at_the_buffer_end_is_read_whole() -> None:
    body = io.BytesIO(b'{"repodata_version": 12345, "packages": {"x-1-0.tar.bz2": {"name": "x", "version": "1"}}}')

    records = list(RU.iter_repodata_records(body, chunk=23))  # the first chunk ends inside 12345

    assert records == [("x-1-0.tar.bz2", {"name": "x", "version": "1"})]


@pytest.mark.parametrize("number", [b"1.5", b"1e+5", b"12.25"], ids=["after-point", "after-exponent", "mid-fraction"])
def test_a_float_cut_at_the_buffer_end_is_read_whole(number: bytes) -> None:
    """``1.`` decodes as ``1`` with text left over; a scalar is accepted only once a delimiter follows it."""
    raw = b'{"repodata_version": ' + number + b', "packages": {"x-1-0.tar.bz2": {"name": "x", "version": "1"}}}'

    for chunk in range(21, 21 + len(number) + 1):  # every cut inside the number
        records = list(RU.iter_repodata_records(io.BytesIO(raw), chunk=chunk))
        assert records == [("x-1-0.tar.bz2", {"name": "x", "version": "1"})], chunk


def test_an_unholdable_timestamp_is_no_time_and_the_file_still_counts() -> None:
    bad = [float("inf"), float("nan"), 1e300, 10**22, -5, "1700000000", None]
    records = [(f"x-{i}.conda", _record("x", "1", ts)) for i, ts in enumerate(bad)]
    records.append(("x-ok.conda", _record("x", "1", T0)))
    records.append(("y-huge.conda", _record("y", "1", 10**22)))  # its only file: past year 9999 even as ms
    records.append(("z-inf.conda", _record("z", "1", float("inf"))))

    out = RU.aggregate_records(iter(records))

    assert _rows(out) == {("x", "1"): (T0, len(bad) + 1), ("y", "1"): (None, 1), ("z", "1"): (None, 1)}


@pytest.mark.parametrize(
    "body",
    [b'{"packages": {"x-1-0.tar.bz2": {"name": "x"', b'["not", "an", "object"]', b'{"packages": {"x": 1} "y": 2}'],
    ids=["truncated", "not-an-object", "missing-comma"],
)
def test_a_malformed_document_raises_value_error(body: bytes) -> None:
    with pytest.raises(ValueError):
        list(RU.iter_repodata_records(io.BytesIO(body), chunk=8))


def test_whitespace_after_a_number_never_refills(monkeypatch: pytest.MonkeyPatch) -> None:
    """A number followed by whitespace is whole: a long run of it must not pile up in the buffer."""
    monkeypatch.setattr(RU, "_MAX_VALUE_CHARS", 100)
    raw = b'{"repodata_version": 1' + b" " * 10_000 + b', "packages": {"x-1.conda": {"name": "x", "version": "1"}}}'

    records = list(RU.iter_repodata_records(io.BytesIO(raw), chunk=16))

    assert records == [("x-1.conda", {"name": "x", "version": "1"})]


def test_a_number_that_never_ends_stops_at_the_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """``1.`` followed by more than the cap of non-delimiters is a corrupt body, read only up to the cap."""
    monkeypatch.setattr(RU, "_MAX_VALUE_CHARS", 100)
    body = io.BytesIO(b'{"a": 1.' + b"5" * 10_000 + b"x}")

    with pytest.raises(ValueError):
        list(RU.iter_repodata_records(body, chunk=16))
    assert body.tell() < 300


def test_a_record_whose_name_is_a_lone_surrogate_is_skipped() -> None:
    """JSON's ``\\ud800`` escape decodes to a string UTF-8 cannot encode, so Parquet could not write it."""
    body = zstd.compress(
        b'{"packages": {"bad.conda": {"name": "\\ud800", "version": "1", "timestamp": 1700000000},'
        b' "bad2.conda": {"name": "y", "version": "\\udfff", "timestamp": 1700000000},'
        b' "ok.conda": {"name": "x", "version": "1", "timestamp": 1700000000}}}'
    )

    out = RU.aggregate_subdir(body)

    assert _rows(out) == {("x", "1"): (1_700_000_000, 1)}


def test_a_value_longer_than_the_cap_stops_the_read_early(monkeypatch: pytest.MonkeyPatch) -> None:
    """A corrupt body (a string that never closes) must not pull the whole stream into memory."""
    monkeypatch.setattr(RU, "_MAX_VALUE_CHARS", 100)
    raw = b'{"info": "' + b"x" * 10_000 + b'"}'
    body = io.BytesIO(raw)

    with pytest.raises(ValueError):
        list(RU.iter_repodata_records(body, chunk=16))
    assert body.tell() < 300  # stopped near the cap, not at the end


def test_a_body_that_is_not_zstd_raises() -> None:
    with pytest.raises(zstd.ZstdError):
        RU.aggregate_subdir(b"not zstd at all")


def test_the_subdirs_combine_to_the_earliest_upload_and_every_file() -> None:
    out = RU.combine_subdirs([RU.aggregate_subdir(NOARCH), RU.aggregate_subdir(LINUX)])

    assert _rows(out) == {
        ("a", "1.0"): (T0 + 1 * DAY, 3),
        ("a", "2.0"): (T0 + 9 * DAY, 1),
        ("b", "2.0"): (None, 2),
        ("c", "0.1"): (None, 1),
    }


def test_no_subdir_gives_the_typed_empty_frame() -> None:
    out = RU.combine_subdirs([])

    assert out.empty and list(out.columns) == RU.COLUMNS and str(out["upload_unix"].dtype) == "Int64"


# --------------------------------------------------------------------------- #
# the dataset: cache, ETag, marker, flag
# --------------------------------------------------------------------------- #


class _Server:
    """``_get`` as a dict lookup: a subdir answers 304 when the ETag sent is its current one."""

    def __init__(self, bodies: dict[str, bytes], etags: dict[str, str]) -> None:
        self.bodies, self.etags = bodies, etags
        self.calls: list[tuple[str, str | None]] = []
        self.fail: set[str] = set()

    def __call__(self, url: str, etag: str | None) -> tuple[int, bytes, str | None]:
        subdir = url.removeprefix(BASE + "/").split("/")[0]
        self.calls.append((subdir, etag))
        if subdir in self.fail:
            raise DatasetError(f"{url}: 503")
        if etag is not None and etag == self.etags[subdir]:
            return 304, b"", etag
        return 200, self.bodies[subdir], self.etags[subdir]


def _dataset(tmp_path: Path, server: _Server, monkeypatch: pytest.MonkeyPatch) -> RepodataUploadsDataset:
    ds = RepodataUploadsDataset(url=BASE, subdirs=("noarch", "linux-64"), filepath=str(tmp_path / "store"))
    monkeypatch.setattr(ds, "_get", server)
    return ds


@pytest.fixture
def live(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(public_sources, "live", lambda: True)


def test_without_a_filepath_the_dataset_is_the_empty_frame() -> None:
    out = RepodataUploadsDataset(url=BASE).load()

    assert out.empty and list(out.columns) == RU.COLUMNS


@pytest.mark.usefixtures("live")
def test_a_refresh_caches_each_subdir_and_its_etag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    server = _Server({"noarch": NOARCH, "linux-64": LINUX}, {"noarch": '"n1"', "linux-64": '"l1"'})
    ds = _dataset(tmp_path, server, monkeypatch)

    out = ds.load()

    assert _rows(out)[("a", "1.0")] == (T0 + 1 * DAY, 3) and ds.refreshed
    assert server.calls == [("noarch", None), ("linux-64", None)]
    manifest = json.loads((tmp_path / "store" / "manifest.json").read_text())
    assert manifest == {"aggregate_version": RU.AGGREGATE_VERSION, "subdirs": {"linux-64": '"l1"', "noarch": '"n1"'}}
    assert sorted(p.name for p in (tmp_path / "store" / "subdirs").iterdir()) == ["linux-64.parquet", "noarch.parquet"]
    assert ds.staleness() is None


@pytest.mark.usefixtures("live")
def test_an_unchanged_subdir_is_a_304_and_is_not_parsed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    server = _Server({"noarch": NOARCH, "linux-64": LINUX}, {"noarch": '"n1"', "linux-64": '"l1"'})
    ds = _dataset(tmp_path, server, monkeypatch)
    first = ds.load()
    server.calls.clear()
    server.etags["linux-64"] = '"l2"'
    server.bodies["linux-64"] = _repodata({"a-1.0-0.tar.bz2": _record("a", "1.0", T0)})
    parsed: list[int] = []
    real = RU.aggregate_subdir
    monkeypatch.setattr(RU, "aggregate_subdir", lambda body, **kw: parsed.append(1) or real(body, **kw))

    second = ds.load()

    assert server.calls == [("noarch", '"n1"'), ("linux-64", '"l1"')]  # each sends its cached ETag
    assert len(parsed) == 1  # only the changed subdir
    assert _rows(second)[("a", "1.0")] == (T0, 3) and _rows(first)[("a", "1.0")] == (T0 + DAY, 3)


@pytest.mark.usefixtures("live")
def test_a_failed_subdir_keeps_its_copy_under_the_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    server = _Server({"noarch": NOARCH, "linux-64": LINUX}, {"noarch": '"n1"', "linux-64": '"l1"'})
    ds = _dataset(tmp_path, server, monkeypatch)
    ds.load()
    server.fail.add("linux-64")
    server.etags["linux-64"] = '"l2"'

    out = ds.load()

    marker = ds.staleness()
    assert marker is not None and marker.stale and marker.last_good_exists
    assert "1 of 2 subdirs not refreshed (linux-64:" in marker.reason
    assert _rows(out)[("a", "1.0")] == (T0 + DAY, 3)  # linux-64's cached copy still counts
    server.fail.clear()
    ds.load()
    assert ds.staleness() is None  # a full success removes the marker


@pytest.mark.usefixtures("live")
@pytest.mark.parametrize(
    "body",
    [
        b"garbage",
        b"",
        NOARCH[: len(NOARCH) // 2],
        zstd.compress(b'{"packages": {"x-1-0.tar.bz2": {"name": '),
        zstd.compress(b'{[1]: 2, "packages": {}}'),
        zstd.compress(b'{{"a": 1}: 2}'),
        zstd.compress(b'{1: 2, "packages": {}}'),
        zstd.compress(b'{"packages": {1: {"name": "x", "version": "1"}}}'),
    ],
    ids=[
        "not-zstd",
        "empty",
        "zstd-cut-short",
        "json-cut-short",
        "list-key",
        "object-key",
        "number-key",
        "number-filename",
    ],
)
def test_a_corrupt_body_is_a_subdir_failure_never_a_raise(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: bytes
) -> None:
    server = _Server({"noarch": body, "linux-64": LINUX}, {"noarch": '"n1"', "linux-64": '"l1"'})
    ds = _dataset(tmp_path, server, monkeypatch)

    out = ds.load()

    assert (
        set(out["conda_name"]) == {"a", "b", "c"} and not (tmp_path / "store" / "subdirs" / "noarch.parquet").exists()
    )
    marker = ds.staleness()
    assert marker is not None and marker.reason.startswith("1 of 2 subdirs not refreshed (noarch:")


@pytest.mark.usefixtures("live")
def test_a_body_nested_past_the_decoder_never_fails_a_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Whether 100,000 levels of nesting raise RecursionError depends on the interpreter's C stack (Python 3.14 bounds
    it by the real stack, so a CI runner parses what a laptop refuses). Either way the load never raises: the subdir
    fails under the marker, or parses to no version."""
    nested = zstd.compress(b'{"packages": {"x": ' + b"[" * 100_000 + b"]" * 100_000 + b"}}")
    server = _Server({"noarch": nested, "linux-64": LINUX}, {"noarch": '"n1"', "linux-64": '"l1"'})
    ds = _dataset(tmp_path, server, monkeypatch)

    out = ds.load()

    assert set(out["conda_name"]) == {"a", "b", "c"}  # linux-64's versions; the nested record names none
    marker = ds.staleness()
    assert marker is None or marker.reason.startswith("1 of 2 subdirs not refreshed (noarch: RecursionError")


@pytest.mark.usefixtures("live")
def test_any_failure_of_one_subdir_is_that_subdirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Whatever raises inside one subdir's fetch, parse or write, the load never raises (atlas NFR-3)."""
    server = _Server({"noarch": NOARCH, "linux-64": LINUX}, {"noarch": '"n1"', "linux-64": '"l1"'})
    ds = _dataset(tmp_path, server, monkeypatch)
    real = RU.aggregate_subdir

    def flaky(body: bytes, **kw: Any) -> pd.DataFrame:
        if body is NOARCH:
            raise TypeError("an unexpected shape")
        return real(body, **kw)

    monkeypatch.setattr(RU, "aggregate_subdir", flaky)

    out = ds.load()

    assert set(out["conda_name"]) == {"a", "b", "c"}
    marker = ds.staleness()
    assert marker is not None and "noarch: " in marker.reason and "unexpected shape" in marker.reason


@pytest.mark.usefixtures("live")
def test_an_unreadable_copy_is_skipped_and_fetched_again(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    server = _Server({"noarch": NOARCH, "linux-64": LINUX}, {"noarch": '"n1"', "linux-64": '"l1"'})
    ds = _dataset(tmp_path, server, monkeypatch)
    ds.load()
    (tmp_path / "store" / "subdirs" / "noarch.parquet").write_bytes(b"not parquet")

    monkeypatch.setattr(public_sources, "live", lambda: False)
    served = ds.load()  # the flag off: the unreadable copy is skipped, never raised
    monkeypatch.setattr(public_sources, "live", lambda: True)
    server.calls.clear()
    fetched = ds.load()

    assert set(served["conda_name"]) == {"a", "b", "c"} and ("a", "2.0") not in _rows(served)
    assert server.calls == [("noarch", None), ("linux-64", '"l1"')] and ("a", "2.0") in _rows(fetched)


@pytest.mark.usefixtures("live")
def test_every_failure_is_named_and_an_unexpected_one_logged_with_its_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    server = _Server({"noarch": NOARCH, "linux-64": b""}, {"noarch": '"n1"', "linux-64": '"l1"'})
    ds = _dataset(tmp_path, server, monkeypatch)
    real = RU.aggregate_subdir

    def buggy(body: bytes, **kw: Any) -> pd.DataFrame:
        if body is NOARCH:
            raise TypeError("a parser bug")
        return real(body, **kw)

    monkeypatch.setattr(RU, "aggregate_subdir", buggy)

    with caplog.at_level(logging.WARNING, logger=RU.__name__):
        ds.load()

    marker = ds.staleness()
    assert marker is not None and marker.reason.startswith("2 of 2 subdirs not refreshed (noarch: ")
    assert "a parser bug" in marker.reason and "linux-64: " in marker.reason
    traced = {
        subdir: bool(r.exc_info)
        for r in caplog.records
        for subdir in ("noarch", "linux-64")
        if f": {subdir} not refreshed: " in r.getMessage()
    }
    assert traced == {"noarch": True, "linux-64": False}  # the parser bug carries its traceback; an empty body does not


@pytest.mark.usefixtures("live")
def test_a_304_to_a_request_with_no_etag_is_a_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With no copy and no ETag sent, a 304 answers nothing: the subdir must not vanish without a marker."""
    ds = RepodataUploadsDataset(url=BASE, subdirs=("noarch",), filepath=str(tmp_path / "store"))
    monkeypatch.setattr(ds, "_get", lambda url, etag: (304, b"", None))

    out = ds.load()

    marker = ds.staleness()
    assert out.empty and marker is not None and "304 Not Modified to a request with no ETag" in marker.reason


@pytest.mark.usefixtures("live")
def test_a_corrupt_body_under_a_new_etag_keeps_the_old_etag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The ETag advances only with a written copy, or the corrupt body would answer 304 from then on."""
    server = _Server({"noarch": NOARCH, "linux-64": LINUX}, {"noarch": '"n1"', "linux-64": '"l1"'})
    ds = _dataset(tmp_path, server, monkeypatch)
    ds.load()
    server.bodies["noarch"], server.etags["noarch"] = b"corrupt", '"n2"'
    server.etags["linux-64"] = '"l2"'  # a sibling that succeeds writes the manifest
    ds.load()
    server.calls.clear()

    ds.load()

    assert server.calls[0] == ("noarch", '"n1"')
    assert json.loads((tmp_path / "store" / "manifest.json").read_text())["subdirs"]["noarch"] == '"n1"'


@pytest.mark.usefixtures("live")
def test_a_marker_that_cannot_be_removed_never_fails_a_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    server = _Server({"noarch": NOARCH, "linux-64": LINUX}, {"noarch": '"n1"', "linux-64": '"l1"'})
    ds = _dataset(tmp_path, server, monkeypatch)
    ds.load()
    (tmp_path / "store" / ".staleness.json").mkdir()  # unlink() refuses a directory

    out = ds.load()  # every subdir a 304: a full success, which removes the marker

    assert _rows(out)[("a", "1.0")] == (T0 + DAY, 3)


@pytest.mark.parametrize(
    "frame",
    [
        pd.DataFrame({"conda_name": ["a"], "version": ["1"]}),  # columns missing
        pd.DataFrame({"conda_name": ["a"], "version": ["1"], "upload_unix": ["soon"], "file_count": [1]}),
        pd.DataFrame({"conda_name": ["a"], "version": ["1"], "upload_unix": [1.5], "file_count": [1]}),
    ],
    ids=["other-columns", "string-times", "fractional-times"],
)
def test_a_cached_copy_of_another_shape_is_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, frame) -> None:
    server = _Server({"noarch": NOARCH, "linux-64": LINUX}, {"noarch": '"n1"', "linux-64": '"l1"'})
    ds = _dataset(tmp_path, server, monkeypatch)
    monkeypatch.setattr(public_sources, "live", lambda: True)
    ds.load()
    frame.to_parquet(tmp_path / "store" / "subdirs" / "noarch.parquet", index=False)
    monkeypatch.setattr(public_sources, "live", lambda: False)

    out = ds.load()

    assert set(out["conda_name"]) == {"a", "b", "c"} and ("a", "2.0") not in _rows(out)


@pytest.mark.usefixtures("live")
def test_a_tampered_manifest_or_marker_never_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    server = _Server({"noarch": NOARCH, "linux-64": LINUX}, {"noarch": '"n1"', "linux-64": '"l1"'})
    ds = _dataset(tmp_path, server, monkeypatch)
    ds.load()
    store = tmp_path / "store"
    (store / "manifest.json").write_text("[" * 100_000 + "]" * 100_000)
    server.calls.clear()

    ds.load()  # the manifest reads as none: both fetched again

    assert server.calls == [("noarch", None), ("linux-64", None)]
    (store / ".staleness.json").write_text("[" * 100_000 + "]" * 100_000)
    assert ds.staleness() is None
    (store / ".staleness.json").write_text('{"stale": true, "reason": "x", "marked_at": Infinity}')
    marker = ds.staleness()
    assert marker is not None and marker.marked_at == 0


def test_a_body_that_decompresses_past_the_cap_stops(monkeypatch: pytest.MonkeyPatch) -> None:
    """A few KB of zstd can expand to any length of whitespace."""
    monkeypatch.setattr(RU, "_MAX_BODY_CHARS", 1_000)
    body = zstd.compress(b'{"packages": {}' + b" " * 100_000 + b"}")

    with pytest.raises(ValueError):
        RU.aggregate_subdir(body, chunk=64)


@pytest.mark.usefixtures("live")
def test_a_lost_subdir_copy_is_fetched_without_its_etag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An ETag with no copy behind it would 304 forever and drop the subdir silently."""
    server = _Server({"noarch": NOARCH, "linux-64": LINUX}, {"noarch": '"n1"', "linux-64": '"l1"'})
    ds = _dataset(tmp_path, server, monkeypatch)
    ds.load()
    (tmp_path / "store" / "subdirs" / "noarch.parquet").unlink()
    server.calls.clear()

    out = ds.load()

    assert server.calls == [("noarch", None), ("linux-64", '"l1"')]
    assert ("a", "2.0") in _rows(out)


@pytest.mark.usefixtures("live")
def test_a_manifest_of_another_aggregate_version_fetches_again(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    server = _Server({"noarch": NOARCH, "linux-64": LINUX}, {"noarch": '"n1"', "linux-64": '"l1"'})
    ds = _dataset(tmp_path, server, monkeypatch)
    ds.load()
    manifest = tmp_path / "store" / "manifest.json"
    manifest.write_text(json.dumps({"aggregate_version": RU.AGGREGATE_VERSION + 1, "subdirs": {"noarch": '"n1"'}}))
    server.calls.clear()

    ds.load()

    assert server.calls == [("noarch", None), ("linux-64", None)]


def test_with_the_flag_off_the_cache_is_served_and_nothing_fetched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    server = _Server({"noarch": NOARCH, "linux-64": LINUX}, {"noarch": '"n1"', "linux-64": '"l1"'})
    ds = _dataset(tmp_path, server, monkeypatch)
    monkeypatch.setattr(public_sources, "live", lambda: True)
    ds.load()
    monkeypatch.setattr(public_sources, "live", lambda: False)
    server.calls.clear()

    out = ds.load()

    assert server.calls == [] and not ds.refreshed and _rows(out)[("a", "1.0")] == (T0 + DAY, 3)


# --------------------------------------------------------------------------- #
# _get through a stand-in APIDataset
# --------------------------------------------------------------------------- #


class _Response:
    def __init__(self, status: int, content: bytes, etag: str | None) -> None:
        self.status_code, self.content = status, content
        self.headers = {"ETag": etag} if etag else {}


def _api(monkeypatch: pytest.MonkeyPatch, response: _Response, calls: list) -> None:
    class _API:
        def __init__(self, *, url: str, load_args: dict | None = None, **kwargs: Any) -> None:
            calls.append((url, dict(load_args or {})))

        def load(self) -> _Response:
            return response

    monkeypatch.setattr(RU, "APIDataset", _API)


def test_get_sends_the_cached_etag_and_no_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list = []
    _api(monkeypatch, _Response(304, b"", None), calls)

    status, body, etag = RepodataUploadsDataset(url=BASE)._get(f"{BASE}/noarch/repodata.json.zst", '"n1"')

    assert (status, body, etag) == (304, b"", '"n1"')
    ((url, load_args),) = calls
    assert url == f"{BASE}/noarch/repodata.json.zst" and load_args["headers"] == {"If-None-Match": '"n1"'}
    assert load_args["timeout"] == RU._REQUEST_TIMEOUT and load_args["auth"]("req") == "req"


def test_get_returns_the_body_and_its_new_etag(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list = []
    _api(monkeypatch, _Response(200, NOARCH, '"n2"'), calls)

    status, body, etag = RepodataUploadsDataset(url=BASE)._get(f"{BASE}/noarch/repodata.json.zst", None)

    assert (status, body, etag) == (200, NOARCH, '"n2"') and "headers" not in calls[0][1]


def test_get_refuses_a_body_that_is_not_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    _api(monkeypatch, _Response(200, "text", None), [])  # type: ignore[arg-type]

    with pytest.raises(DatasetError):
        RepodataUploadsDataset(url=BASE)._get(f"{BASE}/noarch/repodata.json.zst", None)


# --------------------------------------------------------------------------- #
# provenance (AD-17)
# --------------------------------------------------------------------------- #


@pytest.mark.usefixtures("live")
def test_provenance_reads_the_cache_age_and_the_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    server = _Server({"noarch": NOARCH, "linux-64": LINUX}, {"noarch": '"n1"', "linux-64": '"l1"'})
    ds = _dataset(tmp_path, server, monkeypatch)
    ds.load()
    assert resolve_for_catalog_dataset({"x": ds}, "x", None).kind == "live-fetch"

    server.fail.add("noarch")
    server.etags["noarch"] = '"n2"'
    ds.load()

    stale = resolve_for_catalog_dataset({"x": ds}, "x", None)
    assert stale.kind != "live-fetch" and stale.reason is not None and stale.reason.startswith("stale: 1 of 2")
