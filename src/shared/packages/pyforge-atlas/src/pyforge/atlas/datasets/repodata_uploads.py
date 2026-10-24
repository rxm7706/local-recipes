"""Per-version upload times from conda-forge's full repodata (Story 37.6, CAP-69).

Legacy ``release_cadence.py`` reads ``package_version_downloads.upload_unix``, "the earliest upload time across a
version's files". Operator ruling 2026-10-23: atlas takes it from each subdir's full ``repodata.json.zst``, where every
file record carries a ``timestamp``. The bodies are large (linux-64 is 59 MB compressed, about 800,000 files), so each
is streamed: stdlib ``compression.zstd``, then an incremental JSON decode of one ``packages`` / ``packages.conda``
record at a time. A subdir is kept as one small aggregate, (``conda_name``, ``version``, ``upload_unix``,
``file_count``, ``last_upload_unix``, ``last_build_number``), so no run ever holds a whole repodata document.

Story 38.1 adds the last two: the build number and file time of a version's newest build, the record legacy Phase B
picks for ``latest_conda_upload`` (the highest ``build_number``, then the latest ``timestamp``; CFA:1293-1319). A copy
cached before them (aggregate version 1) is still served, with both null, until a live load fetches it again (AD-13).

As Story 34.4's ``S3DownloadStatsDataset`` does, a subdir is fetched again only when its ETag changes (a conditional
GET; a 304 keeps the cache), only behind ``pyforge.atlas.live_public_sources``, and a failure keeps the cached copy
under the AD-13 ``.staleness.json`` marker without raising.
"""

from __future__ import annotations

import codecs
import io
import json
import logging
import math
import re
from collections.abc import Callable, Iterator
from compression import zstd
from pathlib import Path
from typing import Any, Protocol, TypeGuard

import pandas as pd
import pyarrow.parquet as pq
from kedro.io import AbstractDataset, DatasetError
from kedro_datasets.api import APIDataset
from pyforge.core.atomic_write import atomic_write

from . import public_sources
from .core_sources import CONDA_FORGE_SUBDIRS
from .json_sources import _describe_exc
from .refresh import StalenessMarker, _safe_int

logger = logging.getLogger(__name__)

COLUMNS = ["conda_name", "version", "upload_unix", "file_count", "last_upload_unix", "last_build_number"]
#: a subdir copy cached at aggregate version 1, before Story 38.1's two columns
V1_COLUMNS = COLUMNS[:4]
#: the two record maps of a repodata document; ``removed`` and ``info`` carry no files
RECORD_SECTIONS = frozenset({"packages", "packages.conda"})
#: conda reads a timestamp above this (the last second of year 9999) as milliseconds
_MS_THRESHOLD = 253_402_300_799
_CHUNK = 1 << 20  # bytes read per refill
# the most text one value may span: a record is a few KB and `removed` a few MB, so a value still unparsed past
# this is a corrupt body, not a long one (it would otherwise pull the whole stream into memory)
_MAX_VALUE_CHARS = 64 << 20
# the most text one subdir may decompress to: linux-64 is about 1.5 G characters, so a body past this is hostile
# (a few KB of zstd can expand to any length of whitespace)
_MAX_BODY_CHARS = 8 << 30
# the failures a body or a transport can cause; anything else inside a subdir is logged with its traceback
_EXPECTED_ERRORS = (DatasetError, zstd.ZstdError, ValueError, EOFError, OSError, RecursionError)
# requests' timeout, per connect attempt and per silent gap between reads -- not a total (APIDataset sets none)
_REQUEST_TIMEOUT = 90
# bump when aggregate_records' output changes: a manifest of another version re-fetches every subdir
AGGREGATE_VERSION = 2  # 2: Story 38.1's last_upload_unix and last_build_number
# a build number outside int64 cannot be stored; legacy's `build_number or 0` default stands for it
_INT64_MIN, _INT64_MAX = -(1 << 63), (1 << 63) - 1
_WHITESPACE = " \t\r\n"
_WHITESPACE_RUN = re.compile(r"[ \t\r\n]*")


class _ByteStream(Protocol):
    def read(self, size: int = -1, /) -> bytes: ...


class _Reader:
    """An incremental JSON reader over a text stream: one value at a time, never the whole document."""

    def __init__(self, stream: _ByteStream, chunk: int) -> None:
        self._stream = stream
        self._chunk = chunk
        self._decoder = codecs.getincrementaldecoder("utf-8")()
        self._json = json.JSONDecoder()
        self.buf = ""
        self.pos = 0
        self.eof = False
        self._read = 0  # characters decoded so far

    def _fill(self) -> bool:
        """Append the next chunk, keeping what is unread. ``False`` at the end of the stream."""
        if self.eof:
            return False
        data = self._stream.read(self._chunk)
        text = self._decoder.decode(data, final=not data)
        self._read += len(text)
        if self._read > _MAX_BODY_CHARS:
            raise ValueError(f"repodata: the body decompresses past {_MAX_BODY_CHARS:,} characters")
        self.buf = self.buf[self.pos :] + text
        self.pos = 0
        if not data:
            self.eof = True
        return bool(text) or not self.eof

    def peek(self) -> str:
        """The next non-whitespace character, or ``""`` at the end."""
        while True:
            self.pos = _WHITESPACE_RUN.match(self.buf, self.pos).end()  # type: ignore[union-attr]  # `*` always matches
            if self.pos < len(self.buf):
                return self.buf[self.pos]
            if not self._fill():
                return ""

    def expect(self, char: str) -> None:
        if self.peek() != char:
            raise ValueError(f"repodata: expected {char!r} at offset {self.pos}, got {self.peek()!r}")
        self.pos += 1

    def key(self) -> str:
        """The next object key, which JSON requires to be a string."""
        if self.peek() != '"':
            raise ValueError(f"repodata: expected a string key at offset {self.pos}, got {self.peek()!r}")
        return str(self.value())

    def value(self) -> Any:
        """The next JSON value. A value that ends exactly at the buffer's end may be cut short (a number), so it is
        decoded again once more text is in."""
        self.peek()
        while True:
            start = self.pos
            try:
                value, end = self._json.raw_decode(self.buf, start)
            except json.JSONDecodeError:
                if len(self.buf) - start > _MAX_VALUE_CHARS or not self._fill():
                    raise ValueError(f"repodata: malformed JSON at offset {start}") from None
                continue
            if not self.eof and not isinstance(value, (dict, list, str)) and self._cut(end):
                if len(self.buf) - start > _MAX_VALUE_CHARS:
                    raise ValueError(f"repodata: a number at offset {start} runs past the value cap")
                self._fill()
                continue
            self.pos = end
            return value

    def _cut(self, end: int) -> bool:
        """Whether a number ending at ``end`` may be cut short: ``1.5`` read as ``1`` from ``1.``, at the buffer's end or
        before a character a number goes on with. Whitespace, a delimiter or anything else ends it; a container or a
        string closes itself."""
        return end == len(self.buf) or self.buf[end] in ".eE+-0123456789"


def iter_repodata_records(stream: _ByteStream, *, chunk: int = _CHUNK) -> Iterator[tuple[str, Any]]:
    """Yield ``(filename, record)`` for every file of a repodata document, from ``packages`` and ``packages.conda``,
    reading one record at a time. A document that is not a JSON object raises ``ValueError``."""
    reader = _Reader(stream, chunk)
    reader.expect("{")
    first = True
    while True:
        if reader.peek() == "}":
            return
        if not first:
            reader.expect(",")
        first = False
        key = reader.key()
        reader.expect(":")
        if key in RECORD_SECTIONS and reader.peek() == "{":
            reader.expect("{")
            inner_first = True
            while True:
                if reader.peek() == "}":
                    reader.pos += 1
                    break
                if not inner_first:
                    reader.expect(",")
                inner_first = False
                filename = reader.key()
                reader.expect(":")
                yield filename, reader.value()
        else:
            reader.value()  # info, repodata_version, removed, ...


def _seconds(timestamp: Any) -> int | None:
    """A record's ``timestamp`` in epoch seconds (milliseconds truncated), or ``None`` when it has none, or one no
    calendar holds (infinite, or past year 9999 even read as milliseconds): one bad record never fails a subdir."""
    if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
        return None
    if isinstance(timestamp, float) and not math.isfinite(timestamp):
        return None
    if timestamp <= 0:
        return None
    value = int(timestamp)
    if value > _MS_THRESHOLD:
        value //= 1000
    return value if value <= _MS_THRESHOLD else None


def _build_number(value: Any) -> int:
    """A record's ``build_number``, 0 when it has none, or one that is not an int64 (legacy ``build_number or 0``)."""
    if isinstance(value, bool) or not isinstance(value, int) or not _INT64_MIN <= value <= _INT64_MAX:
        return 0
    return value


def _text(value: Any) -> TypeGuard[str]:
    """A non-empty string Parquet can hold: JSON's ``\\ud800`` escape decodes to a lone surrogate, which UTF-8 cannot
    encode, so such a record is skipped rather than failing its subdir's write."""
    if not isinstance(value, str) or not value:
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def aggregate_records(records: Iterator[tuple[str, Any]]) -> pd.DataFrame:
    """One row per (``conda_name``, ``version``): the earliest file timestamp in seconds, the file count, and the
    newest build's build number and file timestamp (the highest build number, then the latest time; an untimed file
    ranks below a timed one, and a newest build with no timed file has no time, as legacy Phase B reads it)."""
    seen: dict[tuple[str, str], list[Any]] = {}
    for _, record in records:
        if not isinstance(record, dict):
            continue
        name, version = record.get("name"), record.get("version")
        if not _text(name) or not _text(version):
            continue
        entry = seen.get((name, version))
        if entry is None:
            entry = seen[(name, version)] = [None, 0, None, None]
        entry[1] += 1
        ts = _seconds(record.get("timestamp"))
        if ts is not None and (entry[0] is None or ts < entry[0]):
            entry[0] = ts
        build = _build_number(record.get("build_number"))
        if entry[3] is None or (build, ts or 0) > (entry[3], entry[2] or 0):
            entry[2], entry[3] = ts, build
    frame = pd.DataFrame(
        [(name, version, first, count, last, build) for (name, version), (first, count, last, build) in seen.items()],
        columns=COLUMNS,
    )
    return _typed(frame)


def aggregate_subdir(body: bytes, *, chunk: int = _CHUNK) -> pd.DataFrame:
    """A subdir's ``repodata.json.zst`` body, aggregated per version."""
    with zstd.ZstdFile(io.BytesIO(body)) as stream:
        return aggregate_records(iter_repodata_records(stream, chunk=chunk))


def _typed(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.astype(
        {
            "conda_name": object,
            "version": object,
            "upload_unix": "Int64",
            "file_count": "int64",
            "last_upload_unix": "Int64",
            "last_build_number": "Int64",
        }
    )


def _parquet_writer(frame: pd.DataFrame) -> Callable[[Path], None]:
    def _write(path: Path) -> None:
        frame.to_parquet(path, index=False)

    return _write


def _reason(exc: BaseException) -> str:
    """An exception as a marker line; an exception that cannot describe itself is named by its type."""
    try:
        return _describe_exc(exc)
    except Exception:  # noqa: BLE001
        return type(exc).__name__


def _readable(path: Path) -> bool:
    """Whether a cached subdir copy exists and its Parquet footer reads."""
    try:
        pq.read_metadata(path)
    except Exception:  # noqa: BLE001 -- absent, truncated or not Parquet
        return False
    return True


def combine_subdirs(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """The subdirs' aggregates as one: a version's earliest upload across subdirs, all its files, and its newest
    build across subdirs (the highest build number, then the latest time; a v1 copy's null build ranks lowest)."""
    frames = [f for f in frames if not f.empty]
    if not frames:
        return _typed(pd.DataFrame(columns=COLUMNS))
    keys = ["conda_name", "version"]
    joined = pd.concat(frames, ignore_index=True)
    out = joined.groupby(keys, sort=True, as_index=False).agg(
        upload_unix=("upload_unix", "min"),
        file_count=("file_count", "sum"),
    )
    ranked = joined.assign(
        _build=joined["last_build_number"].astype("Int64").fillna(_INT64_MIN),
        _time=joined["last_upload_unix"].astype("Int64").fillna(0),
    ).sort_values([*keys, "_build", "_time"], kind="stable")
    newest = ranked.drop_duplicates(keys, keep="last")[[*keys, "last_upload_unix", "last_build_number"]]
    out = out.merge(newest, on=keys, how="left")
    return _typed(out[COLUMNS])


class RepodataUploadsDataset(AbstractDataset):
    """conda-forge's full repodata, as one row per package version: its earliest upload and its file count.

    ``url`` is the channel base (``CONDA_FORGE_BASE_URL``). With ``filepath``, each subdir's aggregate is cached as
    ``<filepath>/subdirs/<subdir>.parquet`` and ``manifest.json`` holds each cached subdir's ETag under the aggregate
    version that wrote it. A failed fetch or parse keeps the cached copy under the AD-13 ``.staleness.json`` marker and
    never raises. Without ``filepath`` (fixtures) the dataset is the empty frame.
    """

    STALENESS_FILENAME = ".staleness.json"
    MANIFEST_FILENAME = "manifest.json"

    def __init__(
        self,
        *,
        url: str,
        subdirs: tuple[str, ...] | list[str] = CONDA_FORGE_SUBDIRS,
        filepath: str | None = None,
        load_args: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._url = url.rstrip("/")
        self._subdirs = tuple(subdirs)
        self._dir = Path(filepath) if filepath else None
        # a timeout, and no credential: public_sources.request_args keeps ~/.netrc out of it
        self._load_args = {**public_sources.request_args(_REQUEST_TIMEOUT), **(load_args or {})}
        self.metadata = metadata
        # whether the last load ran a refresh; with the flag off it serves the cache untouched,
        # and provenance must then report the cache's own age, never "now"
        self.refreshed = False

    # -- paths ---------------------------------------------------------------

    @property
    def _subdirs_dir(self) -> Path:
        assert self._dir is not None
        return self._dir / "subdirs"

    @property
    def last_good_path(self) -> Path | None:
        """The manifest: written after every cached subdir, so its mtime is the cache's age."""
        return self._dir / self.MANIFEST_FILENAME if self._dir is not None else None

    def _subdir_path(self, subdir: str) -> Path:
        return self._subdirs_dir / f"{subdir}.parquet"

    # -- AD-13 marker ------------------------------------------------------------

    def staleness(self) -> StalenessMarker | None:
        """The current AD-13 marker, if the last refresh could not complete."""
        if self._dir is None:
            return None
        try:
            raw = json.loads((self._dir / self.STALENESS_FILENAME).read_text(encoding="utf-8"))
        except OSError, ValueError, RecursionError:  # a missing, garbled or tampered file
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
        cached = self._subdirs_dir.is_dir() and any(self._subdirs_dir.glob("*.parquet"))
        marker = StalenessMarker(stale=True, reason=reason[:300], last_good_exists=cached)

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
        except OSError, ValueError, RecursionError:  # a missing, garbled or tampered file
            return {}
        if not isinstance(raw, dict) or raw.get("aggregate_version") != AGGREGATE_VERSION:
            return {}
        subdirs = raw.get("subdirs")
        return {str(k): str(v) for k, v in subdirs.items()} if isinstance(subdirs, dict) else {}

    def _write_manifest(self, manifest: dict[str, str]) -> None:
        assert self._dir is not None

        def _write(path: Path) -> None:
            doc = {"aggregate_version": AGGREGATE_VERSION, "subdirs": dict(sorted(manifest.items()))}
            path.write_text(json.dumps(doc, indent=2), encoding="utf-8")

        atomic_write(self._dir / self.MANIFEST_FILENAME, _write)

    # -- fetch ---------------------------------------------------------------------

    def _get(self, url: str, etag: str | None) -> tuple[int, bytes, str | None]:
        """One conditional GET: ``(status, body, etag)``. A 304 has an empty body."""
        load_args = dict(self._load_args)  # a fresh dict each time: APIDataset pops "auth"
        if etag:
            load_args["headers"] = {**load_args.get("headers", {}), "If-None-Match": etag}
        payload = APIDataset(url=url, load_args=load_args).load()
        status = int(getattr(payload, "status_code", 200))
        if status == 304:
            return status, b"", etag
        content = getattr(payload, "content", payload)
        if not isinstance(content, bytes):
            raise DatasetError(f"{url}: expected a bytes body, got {type(content).__name__}")
        headers = getattr(payload, "headers", None) or {}
        return status, content, headers.get("ETag") or headers.get("etag")

    def _subdir_url(self, subdir: str) -> str:
        return f"{self._url}/{subdir}/repodata.json.zst"

    def refresh(self) -> None:
        """Fetch every subdir whose ETag changed, or that is not cached under this aggregate version. Never raises."""
        assert self._dir is not None
        manifest = self._read_manifest()
        failures: list[str] = []
        for subdir in self._subdirs:
            path = self._subdir_path(subdir)
            # an ETag with no readable copy behind it would answer 304 forever and drop the subdir
            etag = manifest.get(subdir) if _readable(path) else None
            try:
                status, body, new_etag = self._get(self._subdir_url(subdir), etag)
                if status == 304:
                    if etag is None:  # a 304 to a GET that sent no ETag answers nothing: no copy stands behind it
                        raise DatasetError(f"{subdir}: 304 Not Modified to a request with no ETag")
                    continue
                atomic_write(path, _parquet_writer(aggregate_subdir(body)))
            # one subdir's failure, whatever raised it (a transport error, a hostile or corrupt body, a write), is that
            # subdir's: its copy stays, under the marker (atlas NFR-3: skip and mark stale, never fail). Each failure is
            # logged as it happens, an unexpected one with its traceback, so a parser bug is never only a stale serve.
            except Exception as exc:  # noqa: BLE001
                reason = _reason(exc)
                failures.append(f"{subdir}: {reason}")
                logger.warning(
                    "%s: %s not refreshed: %s",
                    type(self).__name__,
                    subdir,
                    reason,
                    exc_info=not isinstance(exc, _EXPECTED_ERRORS),
                )
                continue
            if new_etag:
                manifest[subdir] = new_etag
            else:
                manifest.pop(subdir, None)
            try:
                self._write_manifest(manifest)
            except OSError as exc:
                failures.append(f"{subdir}: manifest write failed: {exc}")
        if failures:
            self._mark_stale(
                f"{len(failures)} of {len(self._subdirs)} subdirs not refreshed ({'; '.join(failures)}) -- keeping them"
            )
        else:
            try:
                (self._dir / self.STALENESS_FILENAME).unlink(missing_ok=True)
            except OSError as exc:
                logger.warning("could not remove the staleness marker of %s: %s", self._dir, exc)

    # -- read ----------------------------------------------------------------------

    def _read_cache(self) -> pd.DataFrame:
        frames = []
        for subdir in self._subdirs:
            path = self._subdir_path(subdir)
            if not path.is_file():
                continue
            try:
                frame = pd.read_parquet(path)
                if list(frame.columns) == V1_COLUMNS:  # AD-13: last-good holds across the version bump
                    frame = frame.assign(last_upload_unix=pd.NA, last_build_number=pd.NA)
                if list(frame.columns) != COLUMNS:
                    raise ValueError(f"columns {list(frame.columns)}, not {COLUMNS}")
                frames.append(_typed(frame))
            # an unreadable copy, or one of another shape, is no copy; the next live load fetches it again
            except Exception as exc:  # noqa: BLE001
                logger.warning("%s: unusable cached %s skipped: %s", type(self).__name__, subdir, exc)
        return combine_subdirs(frames)

    def load(self) -> pd.DataFrame:
        self.refreshed = False
        if self._dir is None:
            return _typed(pd.DataFrame(columns=COLUMNS))
        if public_sources.live():
            self.refresh()
            self.refreshed = True
        return self._read_cache()

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is read-only")

    def _describe(self) -> dict[str, Any]:
        return {"url": self._url, "subdirs": list(self._subdirs), "filepath": str(self._dir) if self._dir else None}
