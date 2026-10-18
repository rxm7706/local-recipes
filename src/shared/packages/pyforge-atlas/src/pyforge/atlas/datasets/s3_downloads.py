"""Phases F and I: Anaconda's public monthly download parquet (Story 34.4, CAP-64).

``anaconda-package-data`` publishes one parquet per month at
``conda/monthly/<YYYY>/<YYYY-MM>.parquet`` (``time``, ``data_source``, ``pkg_name``,
``pkg_version``, ``pkg_platform``, ``pkg_python``, ``counts``), public over HTTPS; legacy
Phase F's ``s3-parquet`` path reads the same files (``_phase_f_via_s3``, CFA:3009).

Each month is fetched once through a composed ``APIDataset`` and kept as two small
aggregates: the ``breakdown`` view (``conda_name``, ``month``, ``platform``, ``pyver``,
``channel``, ``downloads``, every channel, legacy Waves 2 and 3) and the ``versions``
view (``conda_name``, ``version``, ``downloads``, conda-forge only, legacy Aggregate 2).
A month is fetched again only when the bucket listing gives it a new ETag, so a run
re-reads the newest month and nothing else. Behind ``pyforge.atlas.live_public_sources``:
off, the dataset serves its cache and fetches nothing.
"""

from __future__ import annotations

import io
import json
import logging
import re
import urllib.parse
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from kedro.io import AbstractDataset, DatasetError
from kedro_datasets.api import APIDataset
from pyforge.core.atomic_write import atomic_write
from pyforge.core.flags import read_boolean

from .json_sources import _describe_exc
from .refresh import StalenessMarker, _safe_int

logger = logging.getLogger(__name__)

FLAG_KEY = "pyforge.atlas.live_public_sources"

#: the channel legacy Phase F's totals, platform and Python cuts read (CFA:3009, Wave 2)
HOME_CHANNEL = "conda-forge"

BREAKDOWN_COLUMNS = ["conda_name", "month", "platform", "pyver", "channel", "downloads"]
VERSION_COLUMNS = ["conda_name", "version", "downloads"]
VIEWS = {"breakdown": BREAKDOWN_COLUMNS, "versions": VERSION_COLUMNS}

_MONTH_KEY = re.compile(r"(\d{4}-\d{2})\.parquet$")
_S3_NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"
_MAX_LIST_PAGES = 50  # ~50k keys; the bucket held 117 month keys on 2026-10-18
_PARQUET_COLUMNS = ["data_source", "pkg_name", "pkg_version", "pkg_platform", "pkg_python", "counts"]

# a fetch failure (kedro's wrapper), or a body pyarrow cannot read as the expected parquet
_MONTH_ERRORS = (DatasetError, pa.ArrowException, OSError)


def parse_s3_listing(body: bytes) -> tuple[dict[str, str], str | None]:
    """One ListObjectsV2 page -> ``({YYYY-MM: ETag}, continuation token or None)``.

    Keys that do not end in ``YYYY-MM.parquet`` are ignored; a body that is not an S3
    listing raises ``ValueError``."""
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise ValueError(f"listing is not XML: {exc}") from exc
    if root.tag != f"{_S3_NS}ListBucketResult":
        raise ValueError(f"listing root is {root.tag!r}, not ListBucketResult")
    months: dict[str, str] = {}
    for item in root.iter(f"{_S3_NS}Contents"):
        key = item.findtext(f"{_S3_NS}Key") or ""
        match = _MONTH_KEY.search(key)
        if match:
            months[match.group(1)] = (item.findtext(f"{_S3_NS}ETag") or "").strip('"')
    truncated = (root.findtext(f"{_S3_NS}IsTruncated") or "").strip().lower() == "true"
    token = root.findtext(f"{_S3_NS}NextContinuationToken") if truncated else None
    return months, token or None


def _string(table: pa.Table, column: str) -> pa.ChunkedArray:
    return pc.fill_null(table.column(column).cast(pa.string()), "")


def _summed(table: pa.Table, keys: list[str]) -> pa.Table:
    """``sum(downloads)`` per ``keys``, named ``downloads`` (pyarrow names it ``downloads_sum``)."""
    out = table.group_by(keys).aggregate([("downloads", "sum")])
    return out.rename_columns(["downloads" if n == "downloads_sum" else n for n in out.column_names])


def aggregate_month(month: str, body: bytes) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One month's parquet -> ``(breakdown, versions)`` frames.

    ``pkg_name`` is kept exactly: a conda name is not a PyPI name, and ``typing_extensions``
    and ``typing-extensions`` are two conda-forge packages. (Legacy DW-W2-2 PEP 503
    canonicalizes it after filtering, so legacy writes 0 for every eligible name holding
    ``_`` or ``.``.) An empty ``pkg_platform`` is ``noarch`` (legacy Wave 2); rows with no
    package name or channel are dropped."""
    table = pq.read_table(io.BytesIO(body), columns=_PARQUET_COLUMNS)
    name = _string(table, "pkg_name")
    platform = _string(table, "pkg_platform")
    platform = pc.if_else(pc.equal(platform, ""), "noarch", platform)
    flat = pa.table(
        {
            "conda_name": name,
            "platform": platform,
            "pyver": _string(table, "pkg_python"),
            "channel": _string(table, "data_source"),
            "version": _string(table, "pkg_version"),
            "downloads": pc.fill_null(table.column("counts"), 0),
        }
    )
    flat = flat.filter(pc.and_(pc.not_equal(flat["conda_name"], ""), pc.not_equal(flat["channel"], "")))
    breakdown = _summed(flat, ["conda_name", "platform", "pyver", "channel"])
    breakdown = breakdown.append_column("month", pa.array([month] * breakdown.num_rows, pa.string()))
    home = flat.filter(pc.equal(flat["channel"], HOME_CHANNEL))
    versions = _summed(home, ["conda_name", "version"])
    versions = versions.filter(pc.not_equal(versions["version"], ""))
    return (
        breakdown.select(BREAKDOWN_COLUMNS).to_pandas(),
        versions.select(VERSION_COLUMNS).to_pandas(),
    )


def _parquet_writer(frame: pd.DataFrame) -> Callable[[Path], None]:
    def _write(path: Path) -> None:
        frame.to_parquet(path, index=False)

    return _write


class S3DownloadStatsDataset(AbstractDataset):
    """Anaconda's monthly download parquet, as one of two views over one month cache.

    ``url`` is the bucket base (``S3_PARQUET_BASE_URL``) and ``prefix`` the month folder.
    With ``filepath``, months are cached under ``<filepath>/months/``: ``<YYYY-MM>.breakdown.parquet``
    and ``<YYYY-MM>.versions.parquet``, with ``manifest.json`` holding each cached month's
    ETag. Two catalog entries share one ``filepath``; whichever loads first fetches, the
    other finds every ETag current. A failed listing or month keeps the cache under the
    AD-13 ``.staleness.json`` marker and never raises. Without ``filepath`` (fixtures) the
    dataset is the empty frame it always was.
    """

    STALENESS_FILENAME = ".staleness.json"
    MANIFEST_FILENAME = "manifest.json"

    def __init__(
        self,
        *,
        url: str,
        prefix: str = "conda/monthly",
        view: str = "breakdown",
        filepath: str | None = None,
        load_args: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if view not in VIEWS:
            raise TypeError(f"S3DownloadStatsDataset view must be one of {sorted(VIEWS)}, not {view!r}")
        self._url = url.rstrip("/")
        self._prefix = prefix.strip("/")
        self._view = view
        self._dir = Path(filepath) if filepath else None
        self._load_args = load_args
        self.metadata = metadata

    # -- paths ---------------------------------------------------------------

    @property
    def _months_dir(self) -> Path:
        assert self._dir is not None
        return self._dir / "months"

    @property
    def last_good_path(self) -> Path | None:
        """The manifest: written after every cached month, so its mtime is the cache's age."""
        return self._dir / self.MANIFEST_FILENAME if self._dir is not None else None

    def _month_path(self, month: str, view: str) -> Path:
        return self._months_dir / f"{month}.{view}.parquet"

    # -- AD-13 marker ------------------------------------------------------------

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
        assert self._dir is not None
        marker = StalenessMarker(stale=True, reason=reason[:300], last_good_exists=bool(self._read_manifest()))

        def _write(path: Path) -> None:
            path.write_text(json.dumps(marker.to_dict(), indent=2), encoding="utf-8")

        try:
            atomic_write(self._dir / self.STALENESS_FILENAME, _write)
        except OSError as exc:
            logger.warning("could not write staleness marker for %s: %s", self._dir, exc)
        logger.warning("%s: %s", type(self).__name__, marker.reason)

    # -- manifest ----------------------------------------------------------------

    def _read_manifest(self) -> dict[str, str]:
        assert self._dir is not None
        try:
            raw = json.loads((self._dir / self.MANIFEST_FILENAME).read_text(encoding="utf-8"))
        except OSError, ValueError:
            return {}
        return {str(k): str(v) for k, v in raw.items()} if isinstance(raw, dict) else {}

    def _write_manifest(self, manifest: dict[str, str]) -> None:
        assert self._dir is not None

        def _write(path: Path) -> None:
            path.write_text(json.dumps(dict(sorted(manifest.items())), indent=2), encoding="utf-8")

        atomic_write(self._dir / self.MANIFEST_FILENAME, _write)

    # -- fetch ---------------------------------------------------------------------

    def _get(self, url: str) -> bytes:
        payload = APIDataset(url=url, load_args=self._load_args).load()
        content = getattr(payload, "content", payload)
        if not isinstance(content, bytes):
            raise DatasetError(f"{url}: expected a bytes body, got {type(content).__name__}")
        return content

    def _list(self) -> dict[str, str]:
        months: dict[str, str] = {}
        token: str | None = None
        for _ in range(_MAX_LIST_PAGES):
            url = f"{self._url}/?list-type=2&prefix={self._prefix}/"
            if token:
                url += "&continuation-token=" + urllib.parse.quote(token, safe="")
            page, token = parse_s3_listing(self._get(url))
            months.update(page)
            if not token:
                break
        return months

    def _month_url(self, month: str) -> str:
        return f"{self._url}/{self._prefix}/{month[:4]}/{month}.parquet"

    def refresh(self) -> None:
        """Fetch every month the listing names that is absent or has a new ETag. Never raises."""
        assert self._dir is not None
        try:
            listed = self._list()
        except (DatasetError, ValueError) as exc:
            self._mark_stale(f"listing failed: {_describe_exc(exc)} -- keeping the cached months")
            return
        if not listed:
            self._mark_stale("listing names no months -- keeping the cached months")
            return
        manifest = self._read_manifest()
        failures: list[str] = []
        for month, etag in sorted(listed.items()):
            cached = all(self._month_path(month, view).is_file() for view in VIEWS)
            if cached and manifest.get(month) == etag:
                continue
            try:
                frames = dict(zip(("breakdown", "versions"), aggregate_month(month, self._get(self._month_url(month)))))
            except _MONTH_ERRORS as exc:
                failures.append(f"{month}: {_describe_exc(exc)}")
                continue
            try:
                for view, frame in frames.items():
                    atomic_write(self._month_path(month, view), _parquet_writer(frame))
                manifest[month] = etag
                self._write_manifest(manifest)
            except OSError as exc:
                failures.append(f"{month}: write failed: {exc}")
        if failures:
            self._mark_stale(f"{len(failures)} of {len(listed)} months not refreshed ({failures[0]}) -- keeping them")
        else:
            (self._dir / self.STALENESS_FILENAME).unlink(missing_ok=True)

    # -- read ----------------------------------------------------------------------

    def _read_cache(self) -> pd.DataFrame:
        columns = VIEWS[self._view]
        files = sorted(self._months_dir.glob(f"*.{self._view}.parquet")) if self._months_dir.is_dir() else []
        if not files:
            return pd.DataFrame(columns=columns)
        if self._view == "versions":
            table = _summed(pa.concat_tables([pq.read_table(f) for f in files]), ["conda_name", "version"])
            return table.select(columns).to_pandas()
        # ~19M rows over every month (measured 2026-10-18): text is read straight into parquet
        # dictionaries, never materialized as strings, and leaves as pandas categoricals
        text = ["conda_name", "month", "platform", "pyver", "channel"]
        frame = pa.concat_tables([pq.read_table(f, read_dictionary=text) for f in files]).select(columns).to_pandas()
        months = sorted(str(m) for m in frame["month"].cat.categories)
        frame["month"] = frame["month"].cat.reorder_categories(months, ordered=True)  # max() is the latest month
        return frame

    def load(self) -> pd.DataFrame:
        if self._dir is None:
            return pd.DataFrame(columns=VIEWS[self._view])
        if read_boolean(FLAG_KEY, default=False):
            self.refresh()
        return self._read_cache()

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is read-only")

    def _describe(self) -> dict[str, Any]:
        return {
            "url": self._url,
            "prefix": self._prefix,
            "view": self._view,
            "filepath": str(self._dir) if self._dir else None,
        }
