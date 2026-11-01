"""Story 34.15 (CAP-64, AD-13): the three core sources keep last-good when the network is refused.

``FeedstockOutputsArchiveDataset``, ``CondaRepodataDataset`` and ``PyPISimpleIndexDataset`` loaded through
``APIDataset`` with no fallback, so with every fetch refused a run over a filled data root stopped at
``core_feedstock_outputs_raw`` before any node ran. With ``filepath`` each now keeps its last good frame as
``last_good.parquet`` and serves it under ``.staleness.json`` when a fetch fails or a body does not parse to rows, the
way Story 34.12's vulnerability feeds do. Offline: ``Session.request`` answers from a list, and the socket guard in
``tests/conftest.py`` stays on underneath (AD-11).
"""

from __future__ import annotations

import io
import json
import logging
import zipfile
from collections.abc import Callable
from pathlib import Path

import pandas as pd
import pytest
import requests
import yaml
from kedro.io import DatasetError

from pyforge.atlas.datasets import core_sources
from pyforge.atlas.datasets.catalog_index import DATA_ROOT, CatalogIndexDataset, resolve_catalog_path
from pyforge.atlas.datasets.core_sources import (
    CondaRepodataDataset,
    FeedstockOutputsArchiveDataset,
    LastGoodFrameDataset,
    PyPISimpleIndexDataset,
)
from pyforge.atlas.pipelines.catalog_index.nodes import report_catalog_index_health
from pyforge.atlas.pipelines.core.nodes import attribute_feedstocks
from pyforge.atlas.provenance import resolve_for_catalog_dataset

_MEMBER = Path(__file__).resolve().parents[3]


def _zip(**members: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, text in members.items():
            zf.writestr(name, text)
    return buf.getvalue()


FEEDSTOCK_GOOD = _zip(
    **{"feedstock-outputs-main/outputs/w/i/d/widget.json": json.dumps({"feedstocks": ["widget-split", "widget"]})}
)
REPODATA_GOOD = json.dumps(
    {"packages": {"widget-1.0-0.tar.bz2": {"name": "widget", "version": "1.0", "timestamp": 1700000000000}}}
).encode()
SIMPLE_GOOD = json.dumps({"meta": {}, "projects": [{"name": "widget", "_last-serial": 7}]}).encode()
GATEWAY = b"<html>gateway</html>"


def _feedstock(filepath: str | None) -> LastGoodFrameDataset:
    return FeedstockOutputsArchiveDataset(url="https://source.invalid/outputs.zip", filepath=filepath)


def _repodata(filepath: str | None) -> LastGoodFrameDataset:
    return CondaRepodataDataset(url="https://source.invalid/conda-forge", subdirs=("noarch",), filepath=filepath)


def _simple(filepath: str | None) -> LastGoodFrameDataset:
    return PyPISimpleIndexDataset(url="https://source.invalid/simple", filepath=filepath)


# (factory, catalog entry, a good body, a malformed body and the verdict it earns, a body with no rows)
SOURCES = [
    pytest.param(
        _feedstock,
        "core_feedstock_outputs_raw",
        FEEDSTOCK_GOOD,
        "body unreadable -- keeping last-good: BadZipFile",
        _zip(**{"readme.txt": "no outputs"}),
        id="feedstock-outputs",
    ),
    pytest.param(
        _repodata,
        "core_repodata_raw",
        REPODATA_GOOD,
        # review follow-up: a subdir whose 200 body is no JSON object is that subdir's failed fetch, not a skip
        "fetch failed -- keeping last-good: ValueError: subdir noarch current_repodata.json is not a JSON object",
        json.dumps({"packages": {}}).encode(),
        id="repodata",
    ),
    pytest.param(
        _simple,
        "pypi_simple_index_raw",
        SIMPLE_GOOD,
        "body holds no rows -- keeping last-good",
        json.dumps({"meta": {}, "projects": []}).encode(),
        id="pypi-simple",
    ),
]
_ARGS = ("factory", "entry", "good", "malformed_verdict", "no_rows")
Factory = Callable[[str | None], LastGoodFrameDataset]


def _response(status: int, body: bytes) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response._content = body
    response.url = "https://source.invalid/x"
    response.encoding = "utf-8"
    response.reason = "Service Unavailable" if status == 503 else "OK"
    return response


class _Transport:
    """``Session.request``'s stand-in: each call takes the next answer, raising it if it is an exception."""

    def __init__(self) -> None:
        self.answers: list[object] = []
        self.calls: list[str] = []

    def request(self, method: str | None = None, url: str | None = None, **kwargs: object) -> object:
        self.calls.append(str(url))
        answer = self.answers.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        return answer


@pytest.fixture
def transport(monkeypatch: pytest.MonkeyPatch) -> _Transport:
    fake = _Transport()
    monkeypatch.setattr(requests.Session, "request", fake.request)
    return fake


def _refused() -> requests.exceptions.ConnectionError:
    return requests.exceptions.ConnectionError("HTTPSConnectionPool(host='source.invalid', port=443): refused")


def _store(tmp_path: Path) -> str:
    return str(tmp_path / "raw" / "store")


@pytest.mark.parametrize(_ARGS, SOURCES)
def test_a_refused_fetch_keeps_the_last_good_copy(
    factory: Factory, entry: str, good: bytes, malformed_verdict: str, no_rows: bytes, tmp_path: Path, transport
) -> None:
    transport.answers = [_response(200, good), _refused()]
    ds = factory(_store(tmp_path))
    first = ds.load()
    assert not first.empty and ds.staleness() is None and ds.refreshed
    assert ds.last_good_path is not None and ds.last_good_path.is_file()

    again = ds.load()

    pd.testing.assert_frame_equal(again, first)
    marker = ds.staleness()
    assert marker is not None and marker.stale and marker.last_good_exists and not ds.refreshed
    assert marker.reason.startswith("fetch failed -- keeping last-good: DatasetError: Failed to connect")


@pytest.mark.parametrize(_ARGS, SOURCES)
def test_an_http_error_keeps_the_last_good_copy(
    factory: Factory, entry: str, good: bytes, malformed_verdict: str, no_rows: bytes, tmp_path: Path, transport
) -> None:
    transport.answers = [_response(200, good), _response(503, b"busy")]
    ds = factory(_store(tmp_path))
    first = ds.load()

    again = ds.load()

    pd.testing.assert_frame_equal(again, first)
    marker = ds.staleness()
    assert marker is not None and marker.last_good_exists
    assert marker.reason.startswith("fetch failed -- keeping last-good: DatasetError: ")


@pytest.mark.parametrize(_ARGS, SOURCES)
def test_a_malformed_or_empty_body_keeps_the_last_good_copy(
    factory: Factory, entry: str, good: bytes, malformed_verdict: str, no_rows: bytes, tmp_path: Path, transport
) -> None:
    transport.answers = [_response(200, good), _response(200, GATEWAY), _response(200, no_rows)]
    ds = factory(_store(tmp_path))
    first = ds.load()

    malformed = ds.load()
    malformed_marker = ds.staleness()
    empty = ds.load()

    pd.testing.assert_frame_equal(malformed, first)
    pd.testing.assert_frame_equal(empty, first)
    assert malformed_marker is not None and malformed_marker.reason.startswith(malformed_verdict)
    marker = ds.staleness()
    assert marker is not None and marker.reason == "body holds no rows -- keeping last-good"


@pytest.mark.parametrize(_ARGS, SOURCES)
def test_every_failure_on_a_fresh_root_serves_the_empty_frame_under_the_marker(
    factory: Factory, entry: str, good: bytes, malformed_verdict: str, no_rows: bytes, tmp_path: Path, transport
) -> None:
    transport.answers = [_refused(), _response(503, b"busy"), _response(200, GATEWAY), _response(200, no_rows)]
    ds = factory(_store(tmp_path))

    for _ in range(4):
        frame = ds.load()
        assert frame.empty and list(frame.columns) == type(ds).COLUMNS
        marker = ds.staleness()
        assert marker is not None and marker.stale and not marker.last_good_exists
        assert "-- no last-good" in marker.reason
    assert ds.last_good_path is not None and not ds.last_good_path.exists()


@pytest.mark.parametrize(_ARGS, SOURCES)
def test_a_good_load_after_a_failure_clears_the_marker_and_keeps_the_new_copy(
    factory: Factory, entry: str, good: bytes, malformed_verdict: str, no_rows: bytes, tmp_path: Path, transport
) -> None:
    transport.answers = [_refused(), _response(200, good), _refused()]
    ds = factory(_store(tmp_path))
    assert ds.load().empty and ds.staleness() is not None

    fresh = ds.load()

    assert not fresh.empty and ds.staleness() is None and ds.refreshed
    pd.testing.assert_frame_equal(ds.load(), fresh)


@pytest.mark.parametrize(_ARGS, SOURCES)
def test_without_a_filepath_a_failure_raises_as_before(
    factory: Factory, entry: str, good: bytes, malformed_verdict: str, no_rows: bytes, transport
) -> None:
    """AC4: the fixtures keep no copy, so a refused fetch is still the load's error."""
    transport.answers = [_response(200, good), _refused()]
    ds = factory(None)
    assert not ds.load().empty and ds.last_good_path is None and ds.staleness() is None

    with pytest.raises(DatasetError, match="Failed to connect"):
        ds.load()


def test_the_feedstocks_of_a_served_copy_are_lists_phase_b5_reads(tmp_path: Path, transport) -> None:
    """Parquet hands a list column back as arrays; ``_pick_feedstock`` reads only lists, so an unrestored copy
    would attribute every package to no feedstock."""
    transport.answers = [_response(200, FEEDSTOCK_GOOD), _refused()]
    ds = _feedstock(_store(tmp_path))
    fresh = ds.load()

    served = ds.load()

    assert served["feedstocks"].tolist() == [["widget-split", "widget"]]
    pd.testing.assert_frame_equal(attribute_feedstocks(served), attribute_feedstocks(fresh))
    assert attribute_feedstocks(served)["feedstock_name"].tolist() == ["widget"]


def test_a_repodata_subdir_that_fails_serves_the_whole_copy(tmp_path: Path, transport) -> None:
    """A partial universe (one subdir answered, one refused) never replaces the copy."""
    linux = json.dumps(
        {"packages": {"gadget-2.0-0.tar.bz2": {"name": "gadget", "version": "2.0", "timestamp": 1}}}
    ).encode()
    transport.answers = [
        _response(200, REPODATA_GOOD),
        _response(200, linux),
        _response(200, REPODATA_GOOD),
        _refused(),
    ]
    ds = CondaRepodataDataset(
        url="https://source.invalid/conda-forge", subdirs=("noarch", "linux-64"), filepath=_store(tmp_path)
    )
    first = ds.load()
    assert set(first["subdir"]) == {"noarch", "linux-64"}

    again = ds.load()

    pd.testing.assert_frame_equal(again, first)
    marker = ds.staleness()
    assert marker is not None and marker.reason.startswith("fetch failed -- keeping last-good")


@pytest.mark.parametrize("body", [GATEWAY, b"[]"], ids=["gateway-page", "json-list"])
def test_a_repodata_subdir_that_answers_200_with_no_json_object_serves_the_whole_copy(
    body: bytes, tmp_path: Path, transport
) -> None:
    """Story 34.15 review follow-up: a subdir that answers 200 with a body that is no JSON object is that subdir's
    failed fetch, as a refused one is, so the subdirs that did answer never replace the copy with a partial universe."""
    linux = json.dumps(
        {"packages": {"gadget-2.0-0.tar.bz2": {"name": "gadget", "version": "2.0", "timestamp": 1}}}
    ).encode()
    transport.answers = [
        _response(200, REPODATA_GOOD),
        _response(200, linux),
        _response(200, REPODATA_GOOD),
        _response(200, body),
    ]
    ds = CondaRepodataDataset(
        url="https://source.invalid/conda-forge", subdirs=("noarch", "linux-64"), filepath=_store(tmp_path)
    )
    first = ds.load()
    assert ds.last_good_path is not None
    kept = ds.last_good_path.read_bytes()

    again = ds.load()

    pd.testing.assert_frame_equal(again, first)
    assert ds.last_good_path.read_bytes() == kept and not ds.refreshed
    marker = ds.staleness()
    assert marker is not None and marker.stale and marker.last_good_exists
    assert marker.reason == (
        "fetch failed -- keeping last-good: ValueError: subdir linux-64 current_repodata.json is not a JSON object"
    )


@pytest.mark.parametrize(
    "content", [b"not parquet", "other-shape", "no-rows"], ids=["garbage", "other-shape", "no-rows"]
)
def test_an_unusable_copy_is_set_aside_never_served(content: bytes | str, tmp_path: Path, transport) -> None:
    transport.answers = [_refused()]
    ds = _simple(_store(tmp_path))
    assert ds.last_good_path is not None
    ds.last_good_path.parent.mkdir(parents=True)
    if content == "other-shape":
        pd.DataFrame({"other": [1]}).to_parquet(ds.last_good_path)
    elif content == "no-rows":
        pd.DataFrame(columns=PyPISimpleIndexDataset.COLUMNS).to_parquet(ds.last_good_path)
    else:
        assert isinstance(content, bytes)
        ds.last_good_path.write_bytes(content)

    frame = ds.load()

    assert frame.empty and list(frame.columns) == PyPISimpleIndexDataset.COLUMNS
    marker = ds.staleness()
    assert marker is not None and not marker.last_good_exists
    assert not ds.last_good_path.exists() and (ds.last_good_path.parent / ".last_good.parquet.rejected").is_file()


def test_a_copy_or_marker_that_cannot_be_written_never_fails_the_load(
    tmp_path: Path, transport, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _refuse(path: Path, data: object, **kwargs: object) -> None:
        raise OSError("read-only file system")

    monkeypatch.setattr(core_sources, "atomic_write", _refuse)
    monkeypatch.setattr(core_sources, "atomic_write_bytes", _refuse)
    transport.answers = [_refused(), _response(200, SIMPLE_GOOD)]
    ds = _simple(_store(tmp_path))

    assert ds.load().empty
    assert ds.load()["pypi_name"].tolist() == ["widget"]
    assert ds.last_good_path is not None and not ds.last_good_path.exists()


def test_a_frame_parquet_cannot_hold_keeps_the_last_good_copy(tmp_path: Path, transport) -> None:
    mixed = json.dumps(
        {"projects": [{"name": "a", "_last-serial": {"x": 1}}, {"name": "b", "_last-serial": "text"}]}
    ).encode()
    transport.answers = [_response(200, SIMPLE_GOOD), _response(200, mixed)]
    ds = _simple(_store(tmp_path))
    first = ds.load()

    pd.testing.assert_frame_equal(ds.load(), first)
    marker = ds.staleness()
    assert marker is not None and marker.reason.startswith(
        "body unreadable -- keeping last-good: not storable as Parquet: "
    )


def test_an_unexpected_parse_failure_is_logged_with_its_traceback(
    tmp_path: Path, transport, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def _bug(self: object, payload: object) -> pd.DataFrame:
        raise AttributeError("a parser bug")

    monkeypatch.setattr(PyPISimpleIndexDataset, "_parse", _bug)
    transport.answers = [_response(200, SIMPLE_GOOD)]
    ds = _simple(_store(tmp_path))

    with caplog.at_level(logging.WARNING, logger=core_sources.__name__):
        assert ds.load().empty

    assert any(record.exc_info for record in caplog.records)
    marker = ds.staleness()
    assert marker is not None and marker.reason.startswith("body unreadable -- no last-good: AttributeError")


def test_provenance_reads_a_fresh_fetch_then_the_stale_copy(tmp_path: Path, transport) -> None:
    transport.answers = [_response(200, REPODATA_GOOD), _refused()]
    ds = _repodata(_store(tmp_path))
    ds.load()
    assert resolve_for_catalog_dataset({"x": ds}, "x", None).kind == "live-fetch"

    ds.load()

    stale = resolve_for_catalog_dataset({"x": ds}, "x", None)
    assert stale.kind == "file-mtime" and stale.build_stamp is not None
    assert stale.reason is not None and stale.reason.startswith("stale: fetch failed -- keeping last-good")


@pytest.mark.parametrize(_ARGS, SOURCES)
def test_each_source_keeps_its_copy_under_the_data_root(
    factory: Factory, entry: str, good: bytes, malformed_verdict: str, no_rows: bytes
) -> None:
    """AC5: the bootstrap-index-health board and the Pages job's data/raw cache find each copy by its path."""
    catalog = yaml.safe_load((_MEMBER / "conf" / "base" / "catalog.yml").read_text(encoding="utf-8"))
    assert resolve_catalog_path(catalog[entry]["filepath"], {}) == (DATA_ROOT, f"raw/{entry}")


@pytest.mark.parametrize(_ARGS, SOURCES)
def test_the_index_health_board_reads_the_source_marker(
    factory: Factory, entry: str, good: bytes, malformed_verdict: str, no_rows: bytes, tmp_path: Path, transport
) -> None:
    root = tmp_path / "data"
    transport.answers = [_response(200, good), _refused()]
    ds = factory(str(root / "raw" / entry))
    ds.load()
    ds.load()

    index = CatalogIndexDataset(filepath=str(_MEMBER / "conf" / "base" / "catalog.yml"), path=str(root)).load()
    health = report_catalog_index_health(index, {})

    row = health.loc[health["catalog_entry"] == entry].iloc[0]
    assert row["status"] == "stale"
    assert row["stale_reason"].startswith("fetch failed -- keeping last-good")
