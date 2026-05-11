#!/usr/bin/env python3
"""
Local parquet cache for the `anaconda-package-data` monthly dataset.

Backs Phase F's S3 backend. Downloads `YYYY-MM.parquet` files via `_http.py`
(so JFrog auth and `S3_PARQUET_BASE_URL` overrides apply) into
`.claude/data/conda-forge-expert/cache/parquet/`, then reads them through
`pyarrow.parquet.read_table` with pushdown filters.

Private module (underscore-prefixed) — not exposed as a CLI.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).parent))
from _http import (  # type: ignore[import-not-found]
    list_s3_parquet_months,
    make_request,
    open_url,
    resolve_s3_parquet_urls,
)

_MIN_PARQUET_BYTES = 1024  # real parquets are >10 MB; this just guards against 0-byte/truncated bodies

_CACHE_DIR_OVERRIDE: Path | None = None


def set_cache_dir(path: Path | None) -> None:
    """Test hook: redirect `cache_dir()` to `path` (None resets default)."""
    global _CACHE_DIR_OVERRIDE
    _CACHE_DIR_OVERRIDE = path


def cache_dir() -> Path:
    """Return the parquet cache dir; create it on first use."""
    if _CACHE_DIR_OVERRIDE is not None:
        _CACHE_DIR_OVERRIDE.mkdir(parents=True, exist_ok=True)
        return _CACHE_DIR_OVERRIDE
    base = Path(__file__).parent.parent.parent.parent / "data" / "conda-forge-expert"
    path = base / "cache" / "parquet"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _current_month() -> str:
    """Latest `YYYY-MM` advertised by the bucket — that's the always-refresh sentinel."""
    months = list_s3_parquet_months()
    if not months:
        raise RuntimeError("S3 bucket list-objects returned no parquet months")
    return months[-1]


def _download_month(month: str, dest: Path) -> None:
    last_err: Exception | None = None
    for url in resolve_s3_parquet_urls(month):
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        try:
            req = make_request(url)
            with open_url(req, timeout=300) as resp, open(tmp, "wb") as fh:
                shutil.copyfileobj(resp, fh, length=1024 * 1024)
            size = tmp.stat().st_size
            if size < _MIN_PARQUET_BYTES:
                raise RuntimeError(
                    f"downloaded parquet for {month} is {size} bytes "
                    f"(< {_MIN_PARQUET_BYTES}); likely truncated or empty"
                )
            tmp.rename(dest)
            return
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            continue
    raise RuntimeError(f"All parquet sources failed for {month}; last error: {last_err}")


def ensure_month(month: str, *, current_month: str | None = None) -> Path:
    """Return path to the cached parquet for `month`, downloading if needed.

    The current month (latest advertised by S3) is always re-fetched —
    mid-month updates are rare but cheap to keep current. Other months are
    cached indefinitely. Pass `current_month` to avoid a second list-objects
    call when batching many months.
    """
    out = cache_dir() / f"{month}.parquet"
    if current_month is None:
        try:
            current_month = _current_month()
        except Exception:  # noqa: BLE001
            # Listing failed; trust the cached file if it exists rather than
            # re-download blindly. No cache → fall through to download attempt.
            if out.exists():
                return out
    if out.exists() and month != current_month:
        return out
    _download_month(month, out)
    return out


def read_filtered(
    months: Iterable[str],
    *,
    pkg_names: set[str] | None = None,
    data_source: str = "conda-forge",
):
    """Read the listed cached months filtered to `data_source` and pkg_names.

    Returns a `pyarrow.Table` with the standard columns
    (`time`, `data_source`, `pkg_name`, `pkg_version`, `pkg_platform`,
    `pkg_python`, `counts`). Predicate pushdown handles `data_source` and
    optional `pkg_name` filtering inside the parquet reader.
    """
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError(
            "pyarrow is required for PHASE_F_SOURCE=s3-parquet but is not installed; "
            "install pyarrow in the active env or set PHASE_F_SOURCE=anaconda-api"
        ) from exc

    paths = [str(cache_dir() / f"{m}.parquet") for m in months]
    filters: list = [("data_source", "=", data_source)]
    if pkg_names:
        filters.append(("pkg_name", "in", list(pkg_names)))
    columns = [
        "time", "data_source", "pkg_name", "pkg_version",
        "pkg_platform", "pkg_python", "counts",
    ]
    return pq.read_table(paths, filters=filters, columns=columns)
