"""Story 34.9 (CAP-64): Phase P fills from ClickHouse's public PyPI mirror.

Network-free: ``APIDataset`` is replaced by a stand-in that answers each query from the
shapes measured on 2026-10-18 (``JSONEachRow`` lines, ``UInt64`` quoted, ``month`` as a
``YYYY-MM-DD`` string) and records every request.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import requests
from kedro.io import DatasetError
from pyforge.testing_kit import flag_states

from pyforge.atlas.datasets import PyPIBigQueryDownloadsDataset, PyPIClickHouseDownloadsDataset, public_sources
from pyforge.atlas.datasets import clickhouse_downloads as CH
from pyforge.atlas.pipelines.pypi_intelligence.nodes import fetch_pypi_downloads
from pyforge.atlas.provenance import resolve_for_catalog_dataset

BASE = "https://clickhouse.example.invalid"
RANKED = ["boto3", "Foo_Bar", "foo-bar", "packaging", "o'brien"]  # 90-day order, as the mirror ranks
MONTHLY = {  # project -> {month: downloads}
    "boto3": {"2026-07-01": 900, "2026-08-01": 950, "2026-09-01": 990},
    "Foo_Bar": {"2026-09-01": 7},
    "foo-bar": {"2026-09-01": 5},  # collides with Foo_Bar under PEP 503: summed, as legacy does
    "packaging": {"2026-08-01": 600},
    "o'brien": {"2026-09-01": 1},
}


class _Response:
    def __init__(self, body: bytes) -> None:
        self.content = body


class _Mirror:
    """A stand-in for the composed ``APIDataset``: one per request, as the dataset builds them."""

    def __init__(self, today: str = "2026-10-18", fail_on: str | None = None, body: bytes | None = None) -> None:
        self.today = today
        self.fail_on = fail_on
        self.body = body
        self.requests: list[dict[str, Any]] = []

    def __call__(self, *, url: str, load_args: dict[str, Any]) -> Any:
        mirror = self

        class _One:
            def load(self) -> _Response:
                mirror.requests.append({"url": url, **load_args})
                query = load_args["params"]["query"]
                if mirror.fail_on and mirror.fail_on in query:
                    raise DatasetError("Failed to fetch data")
                if mirror.body is not None:
                    return _Response(mirror.body)
                return _Response(mirror.answer(query).encode())

        return _One()

    def answer(self, query: str) -> str:
        if "today()" in query and "pypi_downloads_per_day" not in query:
            return json.dumps({"today": self.today}) + "\n"
        if "pypi_downloads_per_day" in query:
            limit = int(query.split("LIMIT ")[1].split()[0])
            offset = int(query.split("OFFSET ")[1].split()[0])
            return "".join(json.dumps({"project": p}) + "\n" for p in RANKED[offset : offset + limit])
        names = query.split("project IN (")[1].split(") GROUP BY")[0]
        lines = []
        for project, months in MONTHLY.items():
            if CH._quote(project) in names:
                lines += [
                    json.dumps({"project": project, "month_start": m, "downloads": str(n)}) for m, n in months.items()
                ]
        return "\n".join(lines) + "\n"

    def queries(self) -> list[str]:
        return [r["params"]["query"] for r in self.requests]


def _dataset(
    tmp_path: Path, mirror: _Mirror, monkeypatch: pytest.MonkeyPatch, **kw: Any
) -> PyPIClickHouseDownloadsDataset:
    monkeypatch.setattr(CH, "APIDataset", mirror)
    return PyPIClickHouseDownloadsDataset(url=BASE, filepath=str(tmp_path / "ch"), **kw)


def _live(monkeypatch: pytest.MonkeyPatch, on: bool = True) -> None:
    monkeypatch.setattr(public_sources, "live", lambda: on)


# -- the fetch ------------------------------------------------------------------------


def test_a_live_load_ranks_then_reads_each_months_downloads(tmp_path, monkeypatch):
    _live(monkeypatch)
    mirror = _Mirror()

    out = _dataset(tmp_path, mirror, monkeypatch).load()

    got = {(r.pypi_name, r.month): r.downloads for r in out.itertuples()}
    assert got == {
        ("boto3", "2026-07"): 900,
        ("boto3", "2026-08"): 950,
        ("boto3", "2026-09"): 990,
        ("foo-bar", "2026-09"): 12,
        ("packaging", "2026-08"): 600,
        ("o'brien", "2026-09"): 1,
    }
    assert list(out.columns) == CH.COLUMNS and str(out["downloads"].dtype) == "int64"
    today, ranking, monthly = mirror.queries()
    assert "toString(today())" in today
    # legacy's window and ranking, pinned to the server's date
    assert "date >= toDate('2026-10-18') - 90 AND date < toDate('2026-10-18')" in ranking
    assert "ORDER BY sum(count) DESC, project LIMIT 1000 OFFSET 0" in ranking
    # the three complete months before October
    assert "month >= addMonths(toStartOfMonth(toDate('2026-10-18')), -3)" in monthly
    assert "month < toStartOfMonth(toDate('2026-10-18'))" in monthly
    assert "'o\\'brien'" in monthly  # a quote in a name is escaped


def test_every_request_is_a_public_read_only_get_with_no_credential(tmp_path, monkeypatch):
    _live(monkeypatch)
    mirror = _Mirror()

    _dataset(tmp_path, mirror, monkeypatch, request_timeout_seconds=17).load()

    for request in mirror.requests:
        assert request["url"] == BASE + "/"
        assert request["params"]["user"] == "play"
        assert request["params"]["query"].endswith(" FORMAT JSONEachRow")
        assert request["timeout"] == 17
        # a truthy no-op auth: requests never reads ~/.netrc for the host
        assert callable(request["auth"]) and request["auth"]("r") == "r"


def test_the_ranking_pages_under_the_result_cap_and_stops_on_a_short_page(tmp_path, monkeypatch):
    _live(monkeypatch)
    monkeypatch.setattr(CH, "RESULT_CAP", 2)
    mirror = _Mirror()

    _dataset(tmp_path, mirror, monkeypatch, top_n=9, months=1).load()

    ranking = [q for q in mirror.queries() if "pypi_downloads_per_day" in q]
    assert [q.split("LIMIT ")[1].removesuffix(" FORMAT JSONEachRow") for q in ranking] == [
        "2 OFFSET 0",
        "2 OFFSET 2",
        "2 OFFSET 4",
    ]
    monthly = [q for q in mirror.queries() if "pypi_downloads_per_month" in q]
    assert len(monthly) == 3  # five names, two per batch at one month each


def test_top_n_bounds_the_ranking(tmp_path, monkeypatch):
    _live(monkeypatch)
    mirror = _Mirror()

    out = _dataset(tmp_path, mirror, monkeypatch, top_n=1).load()

    assert set(out["pypi_name"]) == {"boto3"}
    assert "LIMIT 1 OFFSET 0" in mirror.queries()[1]


def test_a_batch_holds_at_most_one_row_per_project_per_month_under_the_cap(tmp_path, monkeypatch):
    _live(monkeypatch)
    monkeypatch.setattr(CH, "RESULT_CAP", 7)
    mirror = _Mirror()

    _dataset(tmp_path, mirror, monkeypatch, months=3).load()

    monthly = [q for q in mirror.queries() if "pypi_downloads_per_month" in q]
    assert [q.split("project IN (")[1].count("', '") + 1 for q in monthly] == [2, 2, 1]  # 7 // 3 names each


def test_the_constructor_refuses_an_empty_window():
    for kw in ({"top_n": 0}, {"months": 0}):
        with pytest.raises(ValueError, match="at least 1"):
            PyPIClickHouseDownloadsDataset(url=BASE, **kw)


def test_canonical_name_is_pep_503():
    assert CH.canonical_name("Foo__Bar.baz-Qux") == "foo-bar-baz-qux"


# -- AD-13: failures keep last-good under the marker --------------------------------------


@pytest.mark.parametrize(
    ("mirror", "reason"),
    [
        (_Mirror(fail_on="pypi_downloads_per_month"), "DatasetError"),
        (
            _Mirror(body=b'{"today": "2026-10-18"}\nCode: 241. DB::Exception: Memory limit exceeded\n'),
            "JSONDecodeError",
        ),
        (_Mirror(body=b"[1, 2]\n"), "expected one JSON object per line"),
        (_Mirror(body=b'{"exception": "Code: 386. DB::Exception: NO_COMMON_TYPE"}\n'), "answered with an error"),
        (_Mirror(today="soon"), "is not a date"),
        (_Mirror(body=b'{"today": "2026-10-18"}\n'), "named no project"),
    ],
    ids=["http-error", "error-text-in-a-200", "not-an-object", "exception-object", "bad-date", "empty-ranking"],
)
def test_a_failed_refresh_keeps_last_good_under_the_marker(tmp_path, monkeypatch, mirror, reason):
    _live(monkeypatch)
    good = _dataset(tmp_path, _Mirror(), monkeypatch).load()

    ds = _dataset(tmp_path, mirror, monkeypatch)
    out = ds.load()

    pd.testing.assert_frame_equal(out, good)
    marker = ds.staleness()
    assert marker is not None and marker.last_good_exists and reason in marker.reason


def test_no_monthly_rows_is_a_failure_not_an_empty_success(tmp_path, monkeypatch):
    _live(monkeypatch)
    mirror = _Mirror()
    mirror.answer = lambda q, _a=mirror.answer: "" if "pypi_downloads_per_month" in q else _a(q)  # type: ignore[method-assign]

    ds = _dataset(tmp_path, mirror, monkeypatch)

    assert ds.load().empty and "no monthly rows" in ds.staleness().reason
    assert not ds.last_good_path.exists()


def test_a_clean_refresh_clears_an_earlier_marker(tmp_path, monkeypatch):
    _live(monkeypatch)
    ds = _dataset(tmp_path, _Mirror(fail_on="today()"), monkeypatch)
    ds.load()
    assert ds.staleness() is not None

    ds = _dataset(tmp_path, _Mirror(), monkeypatch)
    assert len(ds.load()) == 6 and ds.staleness() is None and ds.refreshed


def test_an_unreadable_last_good_reads_as_empty(tmp_path, monkeypatch):
    _live(monkeypatch, on=False)
    ds = _dataset(tmp_path, _Mirror(), monkeypatch)
    ds.last_good_path.parent.mkdir(parents=True)
    ds.last_good_path.write_bytes(b"not parquet")

    assert ds.load().empty


def test_without_filepath_the_dataset_is_empty_and_fetches_nothing(monkeypatch):
    _live(monkeypatch)
    mirror = _Mirror()
    monkeypatch.setattr(CH, "APIDataset", mirror)

    ds = PyPIClickHouseDownloadsDataset(url=BASE)

    assert ds.load().empty and mirror.requests == [] and ds.staleness() is None
    with pytest.raises(DatasetError, match="read-only"):
        ds.save(pd.DataFrame())
    assert ds._describe()["top_n"] == 1000


# -- the flag -----------------------------------------------------------------------------


@flag_states("pyforge.atlas.live_public_sources")  # spelled out: the flag gate reads this file for the key
def test_the_flag_is_read_at_each_load(tmp_path, flag_provider, monkeypatch):
    """On: the dataset fetches. Off: nothing is requested, and last-good is served untouched."""
    flag_on = flag_provider[public_sources.FLAG_KEY]
    _live(monkeypatch, on=True)
    good = _dataset(tmp_path, _Mirror(), monkeypatch).load()  # last-good from an earlier live run

    mirror = _Mirror()
    ds = _dataset(tmp_path, mirror, monkeypatch)  # built while the flag is on
    _live(monkeypatch, on=flag_on)
    out = ds.load()

    pd.testing.assert_frame_equal(out, good)
    assert bool(mirror.requests) is flag_on and ds.refreshed is flag_on and ds.staleness() is None


# -- the node: source selection -----------------------------------------------------------


def _monthly(names: list[str]) -> pd.DataFrame:
    return pd.DataFrame({"pypi_name": names, "month": ["2026-09"] * len(names), "downloads": range(1, len(names) + 1)})


def test_clickhouse_rows_stand_when_bigquery_supplies_none():
    out = fetch_pypi_downloads(_monthly(["boto3", "boto3"]), pd.DataFrame(columns=["pypi_name", "month", "downloads"]))

    assert out.to_dict("records") == [
        {"pypi_name": "boto3", "month": "2026-09", "downloads": 1, "downloads_source": "clickhouse-clickpy"}
    ]


def test_bigquery_rows_win_when_an_attended_run_supplies_them():
    out = fetch_pypi_downloads(_monthly(["boto3"]), _monthly(["numpy", "pandas"]))

    assert list(out["pypi_name"]) == ["numpy", "pandas"]
    assert set(out["downloads_source"]) == {"bigquery-incremental"}  # legacy's label (CFA:7803)


def test_neither_source_is_a_no_op_with_the_full_columns():
    for ch, bq in ((pd.DataFrame(), pd.DataFrame()), (None, None), (pd.DataFrame({"x": [1]}), pd.DataFrame())):
        out = fetch_pypi_downloads(ch, bq)
        assert out.empty and list(out.columns) == ["pypi_name", "month", "downloads", "downloads_source"]


# -- review round 1 -------------------------------------------------------------------------


def test_the_cap_is_the_play_users_and_a_default_batch_holds_333_names(tmp_path, monkeypatch):
    """The ``play`` user's ``max_result_rows`` is 1,000 with ``result_overflow_mode = break``: a
    larger batch would be cut silently, so the cap is pinned."""
    assert CH.RESULT_CAP == 1000
    _live(monkeypatch)
    many = [f"p{i:04d}" for i in range(400)]
    monkeypatch.setattr(sys.modules[__name__], "RANKED", many)
    mirror = _Mirror()

    _dataset(tmp_path, mirror, monkeypatch, top_n=400).load()

    monthly = [q for q in mirror.queries() if "pypi_downloads_per_month" in q]
    assert [q.split("project IN (")[1].count("', '") + 1 for q in monthly] == [333, 67]


def _http_500(body: str) -> DatasetError:
    response = requests.Response()
    response.status_code = 500
    response._content = body.encode()
    try:
        raise requests.HTTPError("500 Server Error", response=response)
    except requests.HTTPError as exc:
        try:
            raise DatasetError("Failed to fetch data") from exc
        except DatasetError as wrapped:
            return wrapped


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        ('{"exception": "Code: 386. DB::Exception: There is no supertype for types String, Date"}', "Code: 386"),
        ("upstream connect error", "Failed to fetch data"),
        ("{not json", "Failed to fetch data"),
    ],
    ids=["the-servers-exception", "no-json-body", "a-brace-but-not-json"],
)
def test_an_http_500_carries_the_servers_reason_into_the_marker(tmp_path, monkeypatch, body, reason):
    _live(monkeypatch)
    error = _http_500(body)

    class _Failing(_Mirror):
        def __call__(self, *, url, load_args):
            class _One:
                def load(self):
                    raise error

            return _One()

    ds = _dataset(tmp_path, _Failing(), monkeypatch)
    ds.load()

    assert reason in ds.staleness().reason


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        (b'{"today": "2026-10-18"}\n', "KeyError"),  # the stand-in's monthly row carries no project
        (b'{"today": "2026-10-18x"}\n', "is not a date"),
    ],
    ids=["row-missing-a-column", "date-with-trailing-text"],
)
def test_a_malformed_answer_keeps_last_good_under_the_marker(tmp_path, monkeypatch, body, reason):
    _live(monkeypatch)

    class _Odd(_Mirror):
        def answer(self, query):
            if "today()" in query and "pypi_downloads_per_day" not in query:
                return body.decode().split("\n")[0] + "\n"
            if "pypi_downloads_per_day" in query:
                return '{"project": "boto3"}\n'
            return '{"month_start": "2026-09-01", "downloads": "3"}\n'

    ds = _dataset(tmp_path, _Odd(), monkeypatch)

    assert ds.load().empty and reason in ds.staleness().reason


def test_a_downloads_value_that_is_not_a_number_is_a_failure(tmp_path, monkeypatch):
    _live(monkeypatch)
    mirror = _Mirror()
    mirror.answer = lambda q, _a=mirror.answer: (  # type: ignore[method-assign]
        '{"project": "boto3", "month_start": "2026-09-01", "downloads": null}\n'
        if "pypi_downloads_per_month" in q
        else _a(q)
    )

    ds = _dataset(tmp_path, mirror, monkeypatch)

    assert ds.load().empty and "TypeError" in ds.staleness().reason


def test_a_body_that_is_not_bytes_is_a_failure(tmp_path, monkeypatch):
    _live(monkeypatch)

    class _Text(_Mirror):
        def __call__(self, *, url, load_args):
            class _One:
                def load(self):
                    return {"not": "a response"}

            return _One()

    ds = _dataset(tmp_path, _Text(), monkeypatch)

    assert ds.load().empty and "expected a bytes body" in ds.staleness().reason


def test_blank_lines_between_rows_are_skipped(tmp_path, monkeypatch):
    _live(monkeypatch)
    mirror = _Mirror()
    mirror.answer = lambda q, _a=mirror.answer: "\n" + _a(q).replace("\n", "\n\n")  # type: ignore[method-assign]

    assert len(_dataset(tmp_path, mirror, monkeypatch).load()) == 6


def test_a_backslash_in_a_name_is_escaped():
    assert CH._quote("a\\b'c") == "'a\\\\b\\'c'"


def test_a_url_with_a_query_string_is_refused():
    with pytest.raises(ValueError, match="no query string"):
        PyPIClickHouseDownloadsDataset(url="https://sql-clickhouse.clickhouse.com/?user=play")


def test_a_file_where_the_store_belongs_never_raises(tmp_path, monkeypatch):
    _live(monkeypatch)
    (tmp_path / "ch").write_text("not a directory")

    out = _dataset(tmp_path, _Mirror(), monkeypatch).load()

    assert out.empty


# -- provenance -----------------------------------------------------------------------------


def test_provenance_reports_the_last_good_and_the_marker(tmp_path, monkeypatch):
    _live(monkeypatch)
    fresh = _dataset(tmp_path, _Mirror(), monkeypatch)
    assert resolve_for_catalog_dataset({"x": fresh}, "x", fresh.load()).kind == "live-fetch"

    stale = _dataset(tmp_path, _Mirror(fail_on="today()"), monkeypatch)
    info = resolve_for_catalog_dataset({"x": stale}, "x", stale.load())

    assert info.kind == "file-mtime" and info.build_stamp is not None
    assert info.reason is not None and info.reason.startswith("stale: ClickHouse Phase P refresh failed")


def test_provenance_with_the_flag_off_reports_the_copy_as_it_stood(tmp_path, monkeypatch):
    _live(monkeypatch)
    _dataset(tmp_path, _Mirror(), monkeypatch).load()
    _live(monkeypatch, on=False)

    ds = _dataset(tmp_path, _Mirror(), monkeypatch)
    info = resolve_for_catalog_dataset({"x": ds}, "x", ds.load())

    assert info.kind == "file-mtime" and info.reason == "not fetched this load: the copy as last fetched"
    fresh_root = _dataset(tmp_path / "empty", _Mirror(), monkeypatch)
    none = resolve_for_catalog_dataset({"x": fresh_root}, "x", fresh_root.load())
    assert none.kind == "unavailable" and none.reason.startswith("not fetched this load, and no copy:")


# -- PHASE_P_ENABLED, as a legacy shell exports it ------------------------------------------


def test_phase_p_enabled_alone_leaves_the_clickhouse_rows_standing(monkeypatch):
    monkeypatch.setenv("PHASE_P_ENABLED", "1")
    monkeypatch.delenv("PHASE_P_SOURCE", raising=False)

    assert PyPIBigQueryDownloadsDataset().load().empty


def test_phase_p_source_bigquery_still_demands_the_attended_run(monkeypatch):
    monkeypatch.setenv("PHASE_P_ENABLED", "1")
    monkeypatch.setenv("PHASE_P_SOURCE", " BigQuery ")  # any case, as legacy; surrounding space trimmed

    with pytest.raises(DatasetError, match="attended credentialed run"):
        PyPIBigQueryDownloadsDataset().load()
