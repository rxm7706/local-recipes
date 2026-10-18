"""Phase P: PyPI monthly downloads from ClickHouse's public PyPI mirror (Story 34.9, CAP-64).

ClickHouse hosts clickpy, a public mirror of BigQuery's ``bigquery-public-data.pypi.file_downloads``,
at ``sql-clickhouse.clickhouse.com`` under the read-only ``play`` user. Legacy Phase P's default
source reads it (``_phase_p_clickhouse``, CFA:7399): one query for the top 1,000 projects by
downloads over the 90 days before today.

The ``play`` user caps every result at 1,000 rows (``max_result_rows``, ``result_overflow_mode =
break``) and answers read-only queries over GET. So the dataset makes small queries in sequence:

1. the server's ``today()``, which pins every later query to one window;
2. the top ``top_n`` projects by downloads over ``[today - 90, today)``, legacy's ranking, one
   page of at most 1,000 names per query;
3. those projects' downloads per calendar month over the ``months`` complete months before
   today's month, from ``pypi.pypi_downloads_per_month``, in batches of names small enough that
   a batch's rows stay under the cap.

Rows: ``pypi_name`` (PEP 503, as legacy writes it), ``month`` (``YYYY-MM``), ``downloads``.
Behind ``pyforge.atlas.live_public_sources``: off, the dataset serves last-good and fetches
nothing. A failed query keeps last-good under the AD-13 marker; the dataset never raises.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd
from kedro.io import AbstractDataset, DatasetError
from kedro_datasets.api import APIDataset
from pyforge.core.atomic_write import atomic_write

from . import public_sources
from .json_sources import _describe_exc
from .refresh import StalenessMarker, _safe_int

logger = logging.getLogger(__name__)

COLUMNS = ["pypi_name", "month", "downloads"]

#: the ``play`` user's ``max_result_rows`` (measured 2026-10-18)
RESULT_CAP = 1000

_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_PEP503 = re.compile(r"[-_.]+")


class _SourceEmpty(ValueError):
    """The mirror answered, but named no project."""


def _quote(value: str) -> str:
    """A ClickHouse string literal."""
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def canonical_name(project: str) -> str:
    """PEP 503, as legacy Phase P writes ``pypi_name`` (its BigQuery twin's ``REGEXP_REPLACE``)."""
    return _PEP503.sub("-", project.lower())


def _parquet_writer(frame: pd.DataFrame) -> Callable[[Path], None]:
    def _write(path: Path) -> None:
        frame.to_parquet(path, index=False)

    return _write


class PyPIClickHouseDownloadsDataset(AbstractDataset):
    """``pypi_clickhouse_downloads_raw``: monthly PyPI downloads for the top ``top_n`` projects.

    ``url`` is the mirror's base (``CLICKHOUSE_PYPI_BASE_URL``). With ``filepath``, the last
    good frame is kept at ``<filepath>/downloads.parquet`` beside the AD-13 ``.staleness.json``
    marker. Without ``filepath`` (fixtures) the dataset is an empty frame and fetches nothing.
    """

    STALENESS_FILENAME = ".staleness.json"
    LAST_GOOD_FILENAME = "downloads.parquet"

    def __init__(
        self,
        *,
        url: str,
        filepath: str | None = None,
        user: str = "play",
        top_n: int = 1000,
        months: int = 3,
        request_timeout_seconds: int = 60,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if int(top_n) < 1 or int(months) < 1:
            raise ValueError(f"top_n and months must be at least 1, not {top_n!r} and {months!r}")
        self._url = url.rstrip("/") + "/"
        self._dir = Path(filepath) if filepath else None
        self._user = user
        self._top_n = int(top_n)
        self._months = int(months)
        self._timeout = int(request_timeout_seconds)
        self.metadata = metadata
        # whether the last load ran a refresh; with the flag off it serves last-good untouched
        self.refreshed = False

    # -- paths and the AD-13 marker ---------------------------------------------------

    @property
    def last_good_path(self) -> Path | None:
        return self._dir / self.LAST_GOOD_FILENAME if self._dir is not None else None

    def staleness(self) -> StalenessMarker | None:
        """The current AD-13 marker, if the last refresh could not complete."""
        if self._dir is None:
            return None
        try:
            raw = json.loads((self._dir / self.STALENESS_FILENAME).read_text(encoding="utf-8"))
        except OSError, ValueError:
            return None
        if not isinstance(raw, dict):
            return None
        return StalenessMarker(
            stale=bool(raw.get("stale", True)),
            reason=str(raw.get("reason", "")),
            marked_at=_safe_int(raw.get("marked_at", 0)),
            last_good_exists=bool(raw.get("last_good_exists", False)),
        )

    def _mark_stale(self, reason: str) -> None:
        assert self._dir is not None and self.last_good_path is not None
        marker = StalenessMarker(stale=True, reason=reason[:300], last_good_exists=self.last_good_path.is_file())

        def _write(path: Path) -> None:
            path.write_text(json.dumps(marker.to_dict(), indent=2), encoding="utf-8")

        try:
            atomic_write(self._dir / self.STALENESS_FILENAME, _write)
        except OSError as exc:
            logger.warning("could not write staleness marker for %s: %s", self._dir, exc)
        logger.warning("%s: %s", type(self).__name__, marker.reason)

    def _clear_stale(self) -> None:
        assert self._dir is not None
        try:
            (self._dir / self.STALENESS_FILENAME).unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("could not clear staleness marker for %s: %s", self._dir, exc)

    # -- fetch -------------------------------------------------------------------------

    def _query(self, sql: str) -> list[dict[str, Any]]:
        """One read-only GET; its ``JSONEachRow`` lines. An error the server streams inside a 200
        -- plain text, or a ``{"exception": ...}`` object -- fails the query."""
        load_args = {
            **public_sources.request_args(self._timeout),
            "params": {"user": self._user, "query": f"{sql} FORMAT JSONEachRow"},
        }
        payload = APIDataset(url=self._url, load_args=load_args).load()
        content = getattr(payload, "content", None)
        if not isinstance(content, bytes):
            raise DatasetError(f"{self._url}: expected a bytes body, got {type(content).__name__}")
        rows: list[dict[str, Any]] = []
        for line in content.decode("utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(f"expected one JSON object per line, got {line[:80]!r}")
            if "exception" in record:
                raise DatasetError(f"the mirror answered with an error: {str(record['exception'])[:200]}")
            rows.append(record)
        return rows

    def _today(self) -> str:
        rows = self._query("SELECT toString(today()) AS today")
        today = str(rows[0].get("today", "")) if rows else ""
        if not _DATE.fullmatch(today):
            raise ValueError(f"the mirror's today() is not a date: {today!r}")
        return today

    def _top_projects(self, today: str) -> list[str]:
        projects: list[str] = []
        for offset in range(0, self._top_n, RESULT_CAP):
            limit = min(RESULT_CAP, self._top_n - offset)
            page = self._query(
                "SELECT project FROM pypi.pypi_downloads_per_day "
                f"WHERE date >= toDate('{today}') - 90 AND date < toDate('{today}') "
                f"GROUP BY project ORDER BY sum(count) DESC, project LIMIT {limit} OFFSET {offset}"
            )
            projects.extend(str(row["project"]) for row in page if row.get("project"))
            if len(page) < limit:
                break
        return projects

    def _monthly(self, today: str, projects: list[str]) -> list[dict[str, Any]]:
        batch = max(1, RESULT_CAP // self._months)  # at most one row per project per month
        rows: list[dict[str, Any]] = []
        for start in range(0, len(projects), batch):
            names = ", ".join(_quote(p) for p in projects[start : start + batch])
            rows.extend(
                self._query(
                    # the alias must not be `month`: ClickHouse would read it in WHERE (NO_COMMON_TYPE)
                    "SELECT project, toString(month) AS month_start, toUInt64(sum(count)) AS downloads "
                    "FROM pypi.pypi_downloads_per_month "
                    f"WHERE month >= addMonths(toStartOfMonth(toDate('{today}')), -{self._months}) "
                    f"AND month < toStartOfMonth(toDate('{today}')) AND project IN ({names}) "
                    "GROUP BY project, month"
                )
            )
        return rows

    def _fetch(self) -> pd.DataFrame:
        today = self._today()
        projects = self._top_projects(today)
        if not projects:
            raise _SourceEmpty("the mirror named no project for the 90-day ranking")
        rows = self._monthly(today, projects)
        if not rows:
            raise _SourceEmpty(f"the mirror holds no monthly rows for the top {len(projects)} projects")
        frame = pd.DataFrame(
            {
                "pypi_name": [canonical_name(str(r["project"])) for r in rows],
                "month": [str(r["month_start"])[:7] for r in rows],
                # UInt64 arrives quoted (output_format_json_quote_64bit_integers)
                "downloads": [int(r["downloads"]) for r in rows],
            }
        )
        # legacy sums names that collide under PEP 503
        return frame.groupby(["pypi_name", "month"], as_index=False)["downloads"].sum().astype({"downloads": "int64"})

    def refresh(self) -> None:
        """Fetch and keep the frame as last-good, clearing the marker. Never raises: a failure
        keeps last-good under the marker."""
        assert self._dir is not None and self.last_good_path is not None
        try:
            frame = self._fetch()
            atomic_write(self.last_good_path, _parquet_writer(frame))
        except (DatasetError, OSError, ValueError, KeyError, TypeError) as exc:
            self._mark_stale(f"ClickHouse Phase P refresh failed: {_describe_exc(exc)} -- keeping last-good")
            return
        self._clear_stale()

    # -- kedro -----------------------------------------------------------------------

    def _read_last_good(self) -> pd.DataFrame:
        path = self.last_good_path
        if path is None or not path.is_file():
            return pd.DataFrame(columns=COLUMNS)
        try:
            return pd.read_parquet(path)[COLUMNS]
        except (OSError, ValueError, KeyError) as exc:
            logger.warning("%s: last-good unreadable (%s)", type(self).__name__, exc)
            return pd.DataFrame(columns=COLUMNS)

    def load(self) -> pd.DataFrame:
        self.refreshed = False
        if self._dir is None:
            return pd.DataFrame(columns=COLUMNS)
        if public_sources.live():
            self._dir.mkdir(parents=True, exist_ok=True)
            self.refresh()
            self.refreshed = True
        return self._read_last_good()

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is read-only")

    def _describe(self) -> dict[str, Any]:
        return {
            "url": self._url,
            "user": self._user,
            "top_n": self._top_n,
            "months": self._months,
            "filepath": str(self._dir) if self._dir else None,
        }
