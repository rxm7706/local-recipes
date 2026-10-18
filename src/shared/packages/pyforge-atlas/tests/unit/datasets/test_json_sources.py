"""Story 34.1 (CAP-64): public JSON sources load as records, with AD-13 last-good.

``pypi_endoflife_raw`` and ``seed_spdx_upstream_list_raw`` were bare ``api.APIDataset``
entries whose ``load()`` returned a ``requests.Response``, so the seed-gap reports always
read an empty input. Network-free throughout (AD-11): the fast tests replace the composed
``APIDataset``; the recorded-body tests run the real ``APIDataset`` and patch only
``requests.Session.request``, so a real ``requests.Response`` carries trimmed recordings of
the live bodies (``tests/fixtures/json_sources``, taken 2026-10-18).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import requests
from kedro.io import DatasetError

from pyforge.atlas.datasets import JSONSourceDataset
from pyforge.atlas.datasets import json_sources as json_sources_module
from pyforge.atlas.pipelines.seed_gaps.nodes import _spdx_upstream_ids, report_spdx_schema_gap
from pyforge.atlas.provenance import resolve_for_catalog_dataset

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "json_sources"
ENDOFLIFE = json.loads((FIXTURES / "endoflife_all.json").read_text(encoding="utf-8"))
SPDX = json.loads((FIXTURES / "spdx_licenses.json").read_text(encoding="utf-8"))
URL = "https://example.invalid/x.json"


class _Response:
    """A ``requests.Response``-like body (``APIDataset.load()``'s return shape)."""

    def __init__(self, body: Any) -> None:
        self._body = body

    def json(self) -> Any:
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


class _FakeInner:
    def __init__(self, outcome: Any) -> None:
        self.outcome = outcome

    def load(self) -> Any:
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome if isinstance(self.outcome, _Response) else _Response(self.outcome)


def _dataset(tmp_path: Path, expect: str, outcome: Any, require_key: str | None = None) -> JSONSourceDataset:
    ds = JSONSourceDataset(url=URL, filepath=str(tmp_path / "store"), expect=expect, require_key=require_key)
    ds._inner = _FakeInner(outcome)  # the one seam: no network in a gate (AD-11)
    return ds


def _marker(tmp_path: Path) -> dict[str, Any] | None:
    path = tmp_path / "store" / JSONSourceDataset.STALENESS_FILENAME
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _last_good(tmp_path: Path) -> Any:
    return json.loads((tmp_path / "store" / JSONSourceDataset.LAST_GOOD_FILENAME).read_text(encoding="utf-8"))


# -- AC1: records, not a Response ------------------------------------------------


@pytest.mark.parametrize(("expect", "body", "key"), [("list", ENDOFLIFE, None), ("dict", SPDX, "licenses")])
def test_a_good_body_loads_decoded_and_becomes_last_good(tmp_path: Path, expect: str, body: Any, key: str) -> None:
    ds = _dataset(tmp_path, expect, body, require_key=key)

    data = ds.load()

    assert data == body
    assert not hasattr(data, "json")  # never a Response again (the defect this story fixes)
    assert _last_good(tmp_path) == body
    assert _marker(tmp_path) is None
    assert ds.exists() is True


def test_expect_must_name_a_shape(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="expect must be one of"):
        JSONSourceDataset(url=URL, filepath=str(tmp_path), expect="str")


def test_require_key_needs_a_dict_source(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="require_key applies only"):
        JSONSourceDataset(url=URL, filepath=str(tmp_path), expect="list", require_key="licenses")


# -- AC2: AD-13 -------------------------------------------------------------------


@pytest.mark.parametrize("expect", ["list", "dict"])
def test_a_failed_fetch_with_no_last_good_returns_the_empty_shape_under_a_marker(tmp_path: Path, expect: str) -> None:
    ds = _dataset(tmp_path, expect, DatasetError("unreachable"))

    data = ds.load()

    assert data == ({} if expect == "dict" else [])
    marker = _marker(tmp_path)
    assert marker is not None and marker["stale"] is True and marker["last_good_exists"] is False
    assert "fetch failed: DatasetError: unreachable" in marker["reason"]
    assert ds.exists() is False


def test_a_failed_fetch_keeps_last_good(tmp_path: Path) -> None:
    _dataset(tmp_path, "list", ENDOFLIFE).load()

    assert _dataset(tmp_path, "list", DatasetError("unreachable")).load() == ENDOFLIFE
    marker = _marker(tmp_path)
    assert marker is not None and marker["last_good_exists"] is True
    assert marker["reason"].endswith("keeping last-good")


@pytest.mark.parametrize(
    ("expect", "key", "bad_body", "reason"),
    [
        ("dict", "licenses", ["not", "a", "dict"], "body is list, expected dict"),
        ("list", None, [], "body is an empty list"),
        ("dict", "licenses", {}, "body is an empty dict"),
        ("dict", "licenses", {"message": "Not Found"}, "body has no non-empty 'licenses'"),
        ("dict", "licenses", {"licenses": []}, "body has no non-empty 'licenses'"),
    ],
)
def test_a_body_that_cannot_replace_last_good_keeps_it(
    tmp_path: Path, expect: str, key: str | None, bad_body: Any, reason: str
) -> None:
    good = SPDX if expect == "dict" else ENDOFLIFE
    _dataset(tmp_path, expect, good, require_key=key).load()

    assert _dataset(tmp_path, expect, bad_body, require_key=key).load() == good
    assert _last_good(tmp_path) == good  # never overwritten by an empty or wrong body
    assert reason in _marker(tmp_path)["reason"]


def test_an_undecodable_body_degrades_as_not_json(tmp_path: Path) -> None:
    ds = _dataset(tmp_path, "list", _Response(ValueError("Expecting value")))  # fetched, then undecodable

    assert ds.load() == []
    assert _marker(tmp_path)["reason"].startswith("body not JSON: ValueError")


@pytest.mark.parametrize("copy", ["{not json", "[]", '{"a": 1}'])
def test_an_unusable_last_good_counts_as_none(tmp_path: Path, copy: str) -> None:
    """Not JSON, an empty list, or the wrong shape: none is served as last-good."""
    (tmp_path / "store").mkdir()
    (tmp_path / "store" / JSONSourceDataset.LAST_GOOD_FILENAME).write_text(copy, encoding="utf-8")

    assert _dataset(tmp_path, "list", DatasetError("unreachable")).load() == []
    assert _marker(tmp_path)["last_good_exists"] is False


def test_the_marker_keeps_its_own_time(tmp_path: Path) -> None:
    ds = _dataset(tmp_path, "list", DatasetError("unreachable"))
    ds.load()

    marker = ds.staleness()

    assert marker is not None and marker.marked_at == _marker(tmp_path)["marked_at"]


def test_a_later_good_fetch_clears_the_marker(tmp_path: Path) -> None:
    _dataset(tmp_path, "list", DatasetError("unreachable")).load()
    assert _marker(tmp_path) is not None

    _dataset(tmp_path, "list", ENDOFLIFE).load()

    assert _marker(tmp_path) is None


def test_a_filesystem_error_never_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _refuse(*_args: Any, **_kwargs: Any) -> None:
        raise PermissionError("read-only store")

    monkeypatch.setattr(json_sources_module, "atomic_write", _refuse)

    assert _dataset(tmp_path, "list", ENDOFLIFE).load() == ENDOFLIFE  # good body still served
    assert _dataset(tmp_path, "list", DatasetError("unreachable")).load() == []  # no marker, no raise


# -- the real APIDataset path, recorded bodies -------------------------------------


def _serve(monkeypatch: pytest.MonkeyPatch, status: int, body: bytes) -> None:
    def _request(self: requests.Session, method: str, url: str, **_kwargs: Any) -> requests.Response:
        response = requests.Response()
        response.status_code = status
        response._content = body
        response.url = url
        response.request = requests.Request(method, url).prepare()
        return response

    monkeypatch.setattr(requests.sessions.Session, "request", _request)


@pytest.mark.parametrize(
    ("fixture", "expect", "key"), [("endoflife_all.json", "list", None), ("spdx_licenses.json", "dict", "licenses")]
)
def test_a_recorded_body_decodes_through_the_real_api_dataset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fixture: str, expect: str, key: str | None
) -> None:
    _serve(monkeypatch, 200, (FIXTURES / fixture).read_bytes())
    ds = JSONSourceDataset(url=URL, filepath=str(tmp_path / "store"), expect=expect, require_key=key)

    assert ds.load() == json.loads((FIXTURES / fixture).read_text(encoding="utf-8"))
    assert _marker(tmp_path) is None


def test_an_http_error_names_its_cause(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _serve(monkeypatch, 404, b"Not Found")
    ds = JSONSourceDataset(url=URL, filepath=str(tmp_path / "store"), expect="list")

    assert ds.load() == []
    reason = _marker(tmp_path)["reason"]
    assert reason.startswith("fetch failed: DatasetError")
    assert "HTTPError" in reason and "404" in reason


def test_a_connection_error_names_its_cause(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _refuse(self: requests.Session, method: str, url: str, **_kwargs: Any) -> requests.Response:
        raise requests.exceptions.ConnectionError("Name or service not known")

    monkeypatch.setattr(requests.sessions.Session, "request", _refuse)
    ds = JSONSourceDataset(url=URL, filepath=str(tmp_path / "store"), expect="list")

    assert ds.load() == []
    assert "(cause: ConnectionError: Name or service not known)" in _marker(tmp_path)["reason"]


def test_a_non_json_body_through_the_real_api_dataset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _serve(monkeypatch, 200, b"<html>maintenance</html>")
    ds = JSONSourceDataset(url=URL, filepath=str(tmp_path / "store"), expect="list")

    assert ds.load() == []
    assert _marker(tmp_path)["reason"].startswith("body not JSON")


# -- AC3: the report fills -----------------------------------------------------------


def test_the_spdx_document_fills_the_report(tmp_path: Path) -> None:
    """End to end through the node: the loaded document yields upstream-drift rows.

    With the old ``Response`` the node saw no ids and returned an empty frame.
    """
    doc = _dataset(tmp_path, "dict", SPDX, require_key="licenses").load()

    report = report_spdx_schema_gap({"enum": ["MIT"]}, doc, None)

    upstream = _spdx_upstream_ids(doc)
    assert "MIT" in upstream and len(upstream) == len(SPDX["licenses"])
    assert set(report["spdx_id"]) == set(upstream) - {"MIT"}
    assert set(report["tier"]) == {"upstream-drift"}
    assert report_spdx_schema_gap({"enum": ["MIT"]}, _Response(SPDX), None).empty  # the defect, pinned


# -- provenance: the read surface sees staleness --------------------------------------


def test_provenance_is_live_fetch_after_a_fresh_load(tmp_path: Path) -> None:
    ds = _dataset(tmp_path, "list", ENDOFLIFE)
    value = ds.load()

    info = resolve_for_catalog_dataset({"x": ds}, "x", value)

    assert info.kind == "live-fetch" and info.reason is None


def test_provenance_reports_last_good_and_the_marker_when_stale(tmp_path: Path) -> None:
    _dataset(tmp_path, "list", ENDOFLIFE).load()
    ds = _dataset(tmp_path, "list", DatasetError("unreachable"))
    value = ds.load()

    info = resolve_for_catalog_dataset({"x": ds}, "x", value)

    assert info.kind == "file-mtime"
    assert info.build_stamp is not None
    assert info.reason is not None and info.reason.startswith("stale: fetch failed")


def test_provenance_is_unavailable_when_stale_with_no_last_good(tmp_path: Path) -> None:
    ds = _dataset(tmp_path, "list", DatasetError("unreachable"))
    value = ds.load()

    info = resolve_for_catalog_dataset({"x": ds}, "x", value)

    assert info.kind == "unavailable"
    assert info.reason is not None and info.reason.startswith("stale:")


# -- Story 34.2: YAML sources ------------------------------------------------------


class _TextResponse:
    def __init__(self, text: str) -> None:
        self.text = text


def test_a_yaml_body_decodes_and_becomes_last_good(tmp_path: Path) -> None:
    ds = JSONSourceDataset(url=URL, filepath=str(tmp_path / "store"), expect="list", decode="yaml")
    ds._inner = _FakeInner(None)
    ds._inner.load = lambda: _TextResponse("- conda_name: a\n  pypi_name: A\n")  # type: ignore[method-assign]

    assert ds.load() == [{"conda_name": "a", "pypi_name": "A"}]
    assert _last_good(tmp_path) == [{"conda_name": "a", "pypi_name": "A"}]


def test_a_broken_yaml_body_degrades_as_not_yaml(tmp_path: Path) -> None:
    ds = JSONSourceDataset(url=URL, filepath=str(tmp_path / "store"), expect="list", decode="yaml")
    ds._inner = _FakeInner(None)
    ds._inner.load = lambda: _TextResponse("- [unclosed")  # type: ignore[method-assign]

    assert ds.load() == []
    assert _marker(tmp_path)["reason"].startswith("body not YAML")


def test_decode_must_name_a_format(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="decode must be one of"):
        JSONSourceDataset(url=URL, filepath=str(tmp_path), expect="list", decode="toml")


def test_provenance_reads_a_dataset_that_composes_a_json_source(tmp_path: Path) -> None:
    """Story 34.2: ParselmouthMappingDataset exposes its JSONSourceDataset as ``source``."""
    from pyforge.atlas.datasets import ParselmouthMappingDataset

    ds = ParselmouthMappingDataset(url=URL, filepath=str(tmp_path / "store"))
    ds.source._inner = _FakeInner(DatasetError("unreachable"))
    value = ds.load()

    info = resolve_for_catalog_dataset({"x": ds}, "x", value)

    assert info.kind == "unavailable" and info.reason is not None and info.reason.startswith("stale:")


@pytest.mark.parametrize(
    ("body", "why"),
    [
        ("- {conda_name: a, pypi_name: 2024-01-01}\n", "a bare YAML date"),
        ("- !!binary aGVsbG8=\n", "YAML binary"),
        ("- !!python/object/apply:os.system [echo pwned]\n", "an object tag the safe loader refuses"),
    ],
)
def test_a_yaml_body_json_cannot_hold_degrades(tmp_path: Path, body: str, why: str) -> None:
    ds = JSONSourceDataset(url=URL, filepath=str(tmp_path / "store"), expect="list", decode="yaml")
    ds._inner = _FakeInner(None)
    ds._inner.load = lambda: _TextResponse(body)  # type: ignore[method-assign]

    assert ds.load() == [], why  # never raises (AD-13); never constructs an object
    assert _marker(tmp_path)["reason"].startswith("body not YAML"), why
