"""Request-parameterized API datasets — the B1 catalog FLIPs (AC-1 / AC-2 / G-2).

Two catalog entries were declared in Story A2 as an interim single-URL
``api.APIDataset`` with an explicit ``# FLIP``/``# NOTE`` that "one APIDataset = one
URL, but this feed is per-{package,query}-parameterized … nodes may NOT build request
URLs (AC-2)". Story B1 lands the real request-parameterized datasets so the
parameterization + the rate-limit discipline live HERE (dataset-owned IO, AD-2), and
the node body stays a pure ``DataFrame -> DataFrame`` transform:

- ``AnacondaDownloadsDataset`` — per-package ``/package/<owner>/<name>`` anaconda.org
  download stats (Phases F + I). Catalog: ``core_anaconda_downloads_raw`` (was
  ``# FLIP(B1)``). This story completes that flip.
- ``GitHubRequestDataset`` — per-query GitHub GraphQL/REST request bodies (Phases
  E.5 / K / N) with the Phase K single-worker 3-RPS + ``Retry-After`` discipline
  attached at dataset level. Catalog: ``vcs_github_api_raw``. **Gap G-2**: A2's
  comment mis-attributed this to "the vcs port (B2)"; E.5/K/N are B1 ``vcs_health``
  phases, so the request dataset is authored HERE and the attribution corrected.

Both COMPOSE ``kedro_datasets.api.APIDataset`` for the physical HTTP (fsspec/requests
are owned by the composed dataset, NOT imported here — this module stays clean under
``tests/catalog/test_no_inline_io.py``). Construction is lazy + offline (the composed
APIDataset does no network at ``__init__``), so both materialize under the
``kedro-catalog-check`` offline resolution gate with stub credentials.

The concrete per-{package,query} FAN-OUT (issuing N requests through the scheduler)
is dataset-owned and deferred — B1 seeds the parameterization surface + the
rate-limit ownership; the node consumes already-fetched DataFrames (THE CRUX). The
rate-limit *contract* is fixture-tested against a stub in ``tests/datasets`` /
``tests/pipelines`` (AD-10 / AD-11), never a live endpoint.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import urllib.parse
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pandas as pd
from kedro.io import AbstractDataset, DatasetError
from kedro_datasets.api import APIDataset
from pyforge.core.atomic_write import atomic_write
from pyforge.core.errors import PyforgeError

from . import credentials as credential_switch
from . import public_sources
from .basilisk import chunk_queries
from .rate_limit import DEFAULT_RPS, RateLimitedScheduler, parse_retry_after
from .refresh import (
    DEFAULT_REFRESH_MAX_RETRIES,
    DEFAULT_REFRESH_TIMEOUT_SECONDS,
    MappingCacheDataset,
    RefreshRequest,
    _ParquetRefreshStore,
    retry_backoff_seconds,
)

logger = logging.getLogger(__name__)

# GitHub GraphQL practical complexity/node-count ceiling per aliased batch request —
# unlike Basilisk's documented 1,000-query REST batch endpoint, GitHub's GraphQL API
# has no single published number, but a large number of aliased sub-selections in one
# query risks tripping the node-limit / query-cost analyzer. Chunk larger batches
# using the SAME chunk_queries() precedent Basilisk already established (review
# fix #5), issuing one POST per chunk rather than one unbounded POST for the whole
# repos sequence.
GITHUB_BATCH_QUERY_MAX = 100

_PYPI_JSON_FRAME_COLUMNS = [
    "pypi_name",
    "version",
    "pypi_last_serial",
    "pypi_version_serial_at_fetch",
    "fetched_at",
    "upload_time_iso_8601",
    "conda_name",
    "license_spdx",
    "license_raw",
    "packaging_shape",
    "notes",
    "pure_python",
    "has_ext_modules",
    "cython",
    "rust",
    "wheel_tags",
]


# Story 35.1: on the credentialed path these are sent once and stop the remaining chunks: a rejected
# token (401), a refusal or secondary rate limit (403) and a rate limit (429) do not clear in
# milliseconds, and GitHub can block a client that keeps sending through them
_STOP_STATUSES = (401, 403, 429)
# Story 35.3: Phase N's batches acquire rate tokens side by side; the scheduler has no lock of its own
# (module-level, so a dataset stays picklable and deep-copyable)
_SCHEDULER_LOCK = threading.Lock()


class _Stopped(PyforgeError, RuntimeError):
    """Story 35.3: a batch not sent because another one stopped the run (a refusal)."""


#: Story 35.3: the failure of a batch never sent because the run had stopped; it writes no row
_UNSENT = "not sent: the run stopped"


def _renumbered(by_alias: dict[Any, Any], offset: int) -> dict[str, Any]:
    """Story 35.3: a half batch's ``r<i>`` aliases as the whole batch's ``r<i + offset>``; any
    other key (``rateLimit``, a body-level error) is dropped."""
    return {
        f"r{int(alias[1:]) + offset}": value
        for alias, value in by_alias.items()
        if isinstance(alias, str) and alias[:1] == "r" and alias[1:].isdigit()
    }


def _http_status(exc: BaseException) -> int | None:
    """The HTTP status inside kedro's ``DatasetError("Failed to send data", HTTPError)``, if any."""
    for arg in (exc, *getattr(exc, "args", ())):
        status = getattr(getattr(arg, "response", None), "status_code", None)
        if isinstance(status, int):
            return status
    return None


def _retry_after(exc: BaseException) -> float:
    """The ``Retry-After`` wait (seconds, capped) inside kedro's ``DatasetError``, else ``0.0``."""
    for arg in (exc, *getattr(exc, "args", ())):
        headers = getattr(getattr(arg, "response", None), "headers", None)
        if headers is not None and headers.get("Retry-After") is not None:
            return parse_retry_after(headers.get("Retry-After"))
    return 0.0


def normalize_release_tag(tag: str | None) -> str | None:
    """Story 35.3: a release tag as a version, as legacy Phase K normalizes it
    (``_normalize_release_tag``, CFA:4608): one case-insensitive prefix of ``release-``,
    ``release_``, ``rel-``, ``rel_`` or ``v`` is stripped."""
    if not tag:
        return None
    s = tag.strip()
    for prefix in ("release-", "release_", "rel-", "rel_", "v"):
        if s.lower().startswith(prefix):
            s = s[len(prefix) :]
            break
    return s or None


def _graphql_errors(payload: Any) -> dict[str | None, str]:
    """GitHub GraphQL ``errors``: the first message per alias (``path[0]``), and the first message
    of all under ``None`` (a body of errors and no data: rate limit, a bad query)."""
    out: dict[str | None, str] = {}
    errors = payload.get("errors") if isinstance(payload, dict) else None
    for err in errors if isinstance(errors, list) else []:
        if not isinstance(err, dict):
            continue
        message = str(err.get("type") or "") + (": " if err.get("type") else "") + str(err.get("message", ""))[:200]
        path = err.get("path")
        alias = path[0] if isinstance(path, list) and path and isinstance(path[0], (str, int)) else None
        out.setdefault(str(alias) if alias is not None else None, message)
        out.setdefault(None, message)
    return out


def _coerce_api_json(raw: Any) -> Any:
    """``APIDataset.load()`` returns a ``requests.Response`` for JSON endpoints."""
    if hasattr(raw, "json") and callable(raw.json):
        try:
            return raw.json()
        except Exception:  # noqa: BLE001 — malformed body stays as-is for callers
            return raw
    return raw


_DEFAULT_PYPI_JSON_FANOUT_LIMIT = 200

# Story 34.10: legacy Phase H's per-request timeout, its 429/503 attempts, and its
# 30-day safety re-check (CFA:4073, CFA:4205).
_PYPI_JSON_TIMEOUT_SECONDS = 30
_PYPI_JSON_ATTEMPTS = 3
_PYPI_JSON_RETRY_STATUSES = (429, 503)
_PHASE_H_RECHECK_SECONDS = 30 * 86400


def _pep503(name: str) -> str:
    """PEP 503 normal form: one PyPI project, one key (``dagster_aws`` is ``dagster-aws``)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _pypi_json_fanout_cap() -> int | None:
    """Story 34.10: ``PYPI_JSON_FANOUT_LIMIT`` as an explicit cap on the eligible set --
    ``None`` when unset (uncapped), ``0`` to skip the fetch this cycle."""
    raw = os.environ.get("PYPI_JSON_FANOUT_LIMIT")
    if raw is None or raw.strip() == "":
        return None
    try:
        cap = int(raw)
    except ValueError:
        logger.warning("PYPI_JSON_FANOUT_LIMIT=%r is not an int -- the live fan-out stays uncapped", raw)
        return None
    return cap if cap >= 0 else None


def _pypi_json_fanout_limit() -> int:
    """``PYPI_JSON_FANOUT_LIMIT`` — bounded, non-unlimited default (review finding:
    the prior amendment dropped the attended-only ``PYPI_JSON_LIVE_FANOUT`` gate
    without giving the limit a real ceiling, which would have made the fan-out
    unbounded by default).

    Returns:
    - a positive int: the bounded fan-out batch size.
    - ``0``: the operator explicitly disabled fan-out THIS cycle (review fix #7 —
      the literal ``"0"`` is distinct from unset/blank/non-numeric/negative, all of
      which degrade to the bounded default rather than being treated as "disabled";
      an operator writing ``PYPI_JSON_FANOUT_LIMIT=0`` almost certainly means
      "skip the live fetch this cycle", the opposite of "use the default").
    """
    raw = os.environ.get("PYPI_JSON_FANOUT_LIMIT")
    if raw is None or raw.strip() == "":
        return _DEFAULT_PYPI_JSON_FANOUT_LIMIT
    try:
        limit = int(raw)
    except TypeError, ValueError:
        logger.warning(
            "PYPI_JSON_FANOUT_LIMIT=%r is not a valid int — using default %s",
            raw,
            _DEFAULT_PYPI_JSON_FANOUT_LIMIT,
        )
        return _DEFAULT_PYPI_JSON_FANOUT_LIMIT
    if limit == 0:
        return 0
    return limit if limit > 0 else _DEFAULT_PYPI_JSON_FANOUT_LIMIT


def _payload_to_pypi_json_row(name: str, payload: Any) -> dict[str, Any]:
    """Normalize one ``/pypi/<name>/json`` document to the node-facing row shape."""
    row: dict[str, Any] = {col: pd.NA for col in _PYPI_JSON_FRAME_COLUMNS}
    row["pypi_name"] = name
    row["fetched_at"] = int(time.time())
    if not isinstance(payload, dict):
        return row
    info = payload.get("info") or {}
    version = info.get("version")
    row["version"] = version
    if version:
        rel = (payload.get("releases") or {}).get(version) or []
        if isinstance(rel, list) and rel and isinstance(rel[0], dict):
            row["upload_time_iso_8601"] = rel[0].get("upload_time")
    row["license_raw"] = info.get("license")
    classifiers = info.get("classifiers") or []
    tag_str = " ".join(classifiers) if isinstance(classifiers, list) else str(classifiers)
    row["wheel_tags"] = tag_str
    row["pure_python"] = "Programming Language :: Python :: 3" in tag_str and "none-any" in tag_str.lower()
    row["has_ext_modules"] = bool(info.get("has_ext_modules"))
    return row


class _RequestParameterizedAPIDataset(AbstractDataset):
    """Shared base: compose an ``APIDataset`` + own a rate-limit scheduler.

    The parameterization (building the per-request path/body) is a DATASET method,
    never a node responsibility — that is the AC-2 boundary the whole migration
    exists to enforce. Subclasses expose the concrete parameterization surface.

    **DW-B1-2 (wired in B2)** — B1 built + composed :class:`RateLimitedScheduler`
    but ``load()`` never called ``self.scheduler.acquire()`` (the token bucket was
    enforced on nothing). B2 wires ``acquire()`` into the live fetch path: the
    single-fetch :meth:`load` acquires one token before delegating, and the
    per-{package,query} fan-out (:meth:`fetch_one` / :meth:`PyPIJsonRequestDataset.load_many`)
    acquires a token per request. The acquire stays at DATASET level — a node never
    reaches it.

    **Fake-clock coupling (DW-B1-2 regression note)** — the scheduler refills tokens
    as a function of ``clock`` elapsed. A frozen clock + a no-op ``sleep`` makes
    :meth:`RateLimitedScheduler.acquire` **infinite-spin** once the bucket drains
    (tokens never refill because the clock never advances, yet the no-op sleep never
    advances it either). Any fixture that exercises the fan-out MUST use an ADVANCING
    clock (a fake clock whose ``sleep`` advances ``now``) OR a ``bucket_capacity`` >=
    the number of requests it issues. See ``tests/datasets/test_pypi_json_request_dataset.py``.
    """

    def __init__(
        self,
        *,
        url: str,
        method: str = "GET",
        load_args: dict[str, Any] | None = None,
        save_args: dict[str, Any] | None = None,
        credentials: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        rps: float = DEFAULT_RPS,
        scheduler: RateLimitedScheduler | None = None,
    ) -> None:
        self._base_url = url
        self._method = method
        self._load_args = dict(load_args or {})
        self._credentials = credentials
        self.metadata = metadata
        # Rate-limit discipline is a DATASET concern (AD-2). The scheduler is
        # single-worker 3-RPS by default (Phase K contract); the concrete fan-out
        # acquires a token per request. Injectable clock/sleep keep it fixture-safe;
        # an injected scheduler lets a fixture supply an advancing fake clock.
        self.scheduler = scheduler if scheduler is not None else RateLimitedScheduler(rps=rps)
        # Story 34.2: per-request misses from the last fan-out, ``name -> reason``.
        self.last_failures: dict[str, str] = {}
        # Compose the physical HTTP IO lazily (no network at __init__).
        self._inner = APIDataset(
            url=url,
            method=method,
            load_args=load_args,
            save_args=save_args,
            credentials=credentials,
            metadata=metadata,
        )

    # -- kedro 1.5.0 AbstractDataset public abstract methods ----------------

    def load(self) -> Any:
        """Delegate the physical fetch to the composed ``APIDataset``, acquiring a
        rate-limit token first (DW-B1-2: the token bucket now gates the live fetch
        path). A node NEVER reaches this — it receives the resolved DataFrame via the
        catalog."""
        self.scheduler.acquire()
        return self._inner.load()

    def fetch_one(self, request_key: str, *, fetcher: Callable[[str], Any] | None = None) -> Any:
        """Fetch ONE parameterized request, acquiring a rate-limit token first
        (DW-B1-2). This is the per-{package,query} fan-out primitive the concrete
        subclasses loop over (Phase H per-project JSON, Phase R enrichment). The
        physical fetch is dataset-owned: ``fetcher`` is injectable so the discipline
        is fixture-testable against a stub; the default delegates to the composed
        ``APIDataset``. ``acquire()`` is called for EVERY request — see the fake-clock
        coupling note on the class docstring.

        Story 34.4: the default fetch requests ``request_key`` (an absolute URL, or a path
        under the base URL) and decodes a JSON body; it used to load the composed base URL,
        whatever key it was given."""
        self.scheduler.acquire()
        if fetcher is not None:
            return fetcher(request_key)
        key = str(request_key)
        url = key if key.startswith(("http://", "https://")) else f"{self._base_url.rstrip('/')}/{key.lstrip('/')}"
        # the dataset's credentials go to its own host only, never to an absolute key elsewhere
        if urllib.parse.urlsplit(url).netloc != urllib.parse.urlsplit(self._base_url).netloc:
            raise ValueError(f"{type(self).__name__}.fetch_one: {url!r} is not on {self._base_url!r}")
        inner = APIDataset(
            url=url,
            method=self._method,
            load_args=self._load_args,
            credentials=self._credentials,
            metadata=self.metadata,
        )
        return _coerce_api_json(inner.load())

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is a read-only request source; it is never saved to.")

    def _describe(self) -> dict[str, Any]:
        return {
            "base_url": self._base_url,
            "method": self._method,
            "rps": self.scheduler.rps,
            "parameterization": type(self).__name__,
        }


class AnacondaDownloadsDataset(_RequestParameterizedAPIDataset):
    """Per-package anaconda.org download-stats source (Phases F + I).

    The A2 interim declared a single ``.../package`` URL; the real feed is
    per-package path-parameterized (``/package/<owner>/<name>``). :meth:`request_path`
    builds that path so the NODE never does (AC-2). ``core_anaconda_downloads_raw``.

    A bare :meth:`load` returns an empty but correctly-columned frame — the per-package
    fan-out is dataset-owned via :meth:`load_many` (credentialed, attended). The Kedro
    DAG's catalog load must not hit the unparameterized base URL (404).
    """

    _EMPTY_COLUMNS = ["conda_name", "version", "downloads"]

    def request_path(self, owner: str, name: str) -> str:
        """Build the per-package request path — the parameterization a node may NOT
        perform (AC-2). ``owner`` defaults to ``conda-forge`` in the legacy path."""
        owner = (owner or "conda-forge").strip("/")
        name = name.strip("/")
        return f"{self._base_url.rstrip('/')}/{owner}/{name}"

    def load(self) -> pd.DataFrame:
        """No-op stub until the attended per-package fan-out is wired.

        ``compute_downloads`` / ``compute_version_download_history`` treat an empty
        frame as "anaconda-api path absent" and degrade gracefully (s3-parquet or empty
        outputs). Drive live stats via :meth:`load_many`.
        """
        return pd.DataFrame(columns=self._EMPTY_COLUMNS)

    def load_many(
        self,
        names: list[str],
        *,
        owner: str = "conda-forge",
        fetcher: Callable[[str], Any] | None = None,
    ) -> pd.DataFrame:
        """Per-package fan-out (Phase F/I): one request per ``conda_name``.

        Returns a flat frame with ``conda_name``, ``version``, ``downloads`` rows
        (one row per file version in the anaconda.org payload). ``fetcher`` is
        injectable for fixtures; the default routes each path through the composed
        ``APIDataset``.
        """
        rows: list[dict[str, Any]] = []
        for name in names:
            if name is None or (isinstance(name, float) and name != name):
                continue
            path = self.request_path(owner, str(name))
            payload = self.fetch_one(path, fetcher=fetcher)
            if not isinstance(payload, dict):
                continue
            for f in payload.get("files") or []:
                if not isinstance(f, dict):
                    continue
                ver = f.get("version")
                dl = f.get("ndownloads")
                if ver is None:
                    continue
                rows.append(
                    {
                        "conda_name": str(name),
                        "version": str(ver),
                        "downloads": int(dl or 0),
                    }
                )
        if not rows:
            return pd.DataFrame(columns=self._EMPTY_COLUMNS)
        return pd.DataFrame(rows)[self._EMPTY_COLUMNS]


class GitHubRequestDataset(_ParquetRefreshStore, _RequestParameterizedAPIDataset):
    # Story 35.3: one row per (kind, key): "upstream" (Phase K, keyed by conda_name), "feedstock"
    # (Phase N) and "archived" (Phase E.5), keyed by feedstock name; "health" is the path before 35.3
    merge_on = ("kind", "key")

    """Per-query GitHub GraphQL request-body source (Phases E.5 / K / N).

    Gap G-2: authored in B1 (E.5/K/N are ``vcs_health`` B1 phases), not B2. One
    dataset = one request body; :meth:`with_query` produces the parameterized
    ``load_args.json`` a node may NOT build (AC-2). The Phase K single-worker 3-RPS
    token bucket + ``Retry-After`` discipline are attached here (dataset level), not
    in the node body. ``vcs_github_api_raw``.

    ``load()`` is a read-only projection of the persisted store (mirrors
    :class:`~pyforge.atlas.datasets.vcs_sources.VcsHostSeedDataset`) — the real
    batched GraphQL fetch (:meth:`fetch_repo_health`) runs only via
    ``save(RefreshRequest(...))``, the pipeline's refresh-trigger node being the
    single writer (Story 21.2).
    """

    _COLUMNS = (
        "feedstock_name",
        "conda_name",
        "archived",
        "upstream_version",
        "last_error",
        "stars",
        "last_commit",
        "open_issues",
        # Story 35.3
        "kind",
        "key",
        "repo",
        "open_prs",
        "ci_status",
        "archived_at",
    )
    #: Story 35.3: legacy's batch sizes (Phase K 100, CFA:4697; Phase N 25, CFA:6600)
    UPSTREAM_BATCH = 100
    FEEDSTOCK_BATCH = 25
    PROGRESS_EVERY = 25  # a progress line every this many batches, as legacy Phase K prints
    GRAPHQL_TIMEOUT_SECONDS = 60
    HALVE_MIN = 12  # a batch of this many repositories or fewer is not halved again
    FAILED_BATCHES_LIMIT = 10  # this many batches failing whole in a row stop the run (an outage)
    FEEDSTOCK_CONCURRENCY = 4  # legacy PHASE_N_CONCURRENCY's default
    ARCHIVED_MAX_PAGES = 200

    def __init__(
        self,
        *,
        url: str,
        filepath: str,
        method: str = "POST",
        load_args: dict[str, Any] | None = None,
        save_args: dict[str, Any] | None = None,
        credentials: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        rps: float = DEFAULT_RPS,
        scheduler: RateLimitedScheduler | None = None,
        sleep: Callable[[float], None] = time.sleep,
        timeout_seconds: int = DEFAULT_REFRESH_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_REFRESH_MAX_RETRIES,
    ) -> None:
        super().__init__(
            url=url,
            method=method,
            load_args=load_args,
            save_args=save_args,
            credentials=credentials,
            metadata=metadata,
            rps=rps,
            scheduler=scheduler,
        )
        self._filepath = str(filepath)
        self._timeout_seconds = int(timeout_seconds)
        self._max_retries = int(max_retries)
        self._sleep = sleep
        # review fix #8: there is exactly ONE GitHub catalog entry, so the expected
        # store is a fixed literal (unlike VcsHostSeedDataset/RegistryUpstreamDataset,
        # which are parameterized per host/registry) — validated in save().
        self._expected_store = "vcs_github_api_raw"

    def with_query(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build the GraphQL POST body for a single query — dataset-owned request
        parameterization (AC-2)."""
        body: dict[str, Any] = {"query": query}
        if variables:
            body["variables"] = dict(variables)
        return body

    def build_batch_query(self, repos: Sequence[tuple[str, str]]) -> dict[str, Any]:
        """Build ONE batched GraphQL query (aliased sub-selections) covering every
        ``(owner, name)`` pair in ``repos`` — the Phase K batched-query design
        (KEEP). Dataset-owned request parameterization (AC-2): a node may never build
        this. Callers are responsible for pre-chunking ``repos`` to
        :data:`GITHUB_BATCH_QUERY_MAX` (review fix #5 — this method builds exactly
        one query for whatever it is given, unbounded). An empty ``repos`` falls back
        to the harmless rate-limit probe query."""
        if not repos:
            return self.with_query("query { rateLimit { remaining } }")
        parts = [
            f"r{i}: repository(owner: {json.dumps(str(owner))}, name: {json.dumps(str(name))}) "
            "{ isArchived stargazerCount pushedAt issues(states: OPEN) { totalCount } }"
            for i, (owner, name) in enumerate(repos)
        ]
        return self.with_query("query { " + " ".join(parts) + " }")

    def _post(self, body: dict[str, Any], auth: credential_switch.BearerAuth) -> Any:
        """Story 35.1: one GraphQL POST with ``auth``. ``APIDataset.load()`` sends only GET, so
        the POST goes through ``save()``, and the response comes back through an in-memory
        ``response_dataset`` (``save()``'s own return value does not survive kedro's wrapper)."""
        inner = APIDataset(
            url=self._base_url,
            method="POST",
            # Story 35.3: GitHub ends a GraphQL query after about ten seconds; legacy Phase K stops
            # waiting at 45 (PHASE_K_BATCH_HARD_TIMEOUT_S), so a stalled connection never holds the run
            save_args={"timeout": min(self._timeout_seconds, self.GRAPHQL_TIMEOUT_SECONDS)},
            credentials=auth,  # type: ignore[arg-type, unused-ignore]  # a callable auth; requests accepts it
            metadata=self.metadata,
            response_dataset={"type": "kedro.io.MemoryDataset", "copy_mode": "assign"},
        )
        inner.save(body)
        return _coerce_api_json(inner.get_last_response())

    def _fetch_batch_with_retry(
        self,
        chunk: Sequence[tuple[str, str]],
        *,
        fetcher: Callable[[dict[str, Any]], Any] | None = None,
        auth: credential_switch.BearerAuth | None = None,
        build: Callable[[Sequence[Any]], dict[str, Any]] | None = None,
        before_attempt: Callable[[], bool] | None = None,
        on_wait: Callable[[float], None] | None = None,
    ) -> tuple[Any, Exception | None]:
        """One chunk's batched POST, retried up to ``max_retries`` times. ``build`` makes the body
        (default :meth:`build_batch_query`). The
        rate-limit token is acquired on EVERY attempt (review fix #3/#4 — mirrors
        ``VcsHostSeedDataset.fetch_one``), with a short injectable backoff between
        retries. Building the query lives INSIDE the try (review finding) so a
        query-build failure degrades the same way a network failure does. Returns
        ``(payload, None)`` on success or ``(None, exc)`` after exhausting retries —
        never raises (AD-13)."""
        attempt = 0
        while True:
            # Story 35.3: a pause another batch set is waited out, and nothing is sent after a stop
            if before_attempt is not None and not before_attempt():
                return None, _Stopped("stopped")
            try:
                with _SCHEDULER_LOCK:
                    self.scheduler.acquire()
                body = (build or self.build_batch_query)(chunk)
                if fetcher is not None:
                    return fetcher(body), None
                if auth is not None:
                    return self._post(body, auth), None
                inner = APIDataset(
                    url=self._base_url,
                    method="POST",
                    load_args={"json": body, "timeout": self._timeout_seconds},
                    credentials=self._credentials,
                    metadata=self.metadata,
                )
                return _coerce_api_json(inner.load()), None
            except Exception as exc:  # AD-13: an unreachable endpoint never fails the run.
                attempt += 1
                # Story 35.1: a rejected token is never sent again (GitHub can block a client that
                # keeps sending bad credentials)
                status = _http_status(exc) if auth is not None else None
                wait = _retry_after(exc) if status in (403, 429) else 0.0
                if attempt > self._max_retries or (status in _STOP_STATUSES and not wait):
                    return None, exc
                # Story 35.3: a 403 or 429 that names its wait (a secondary rate limit) is retried after it,
                # and every other batch running beside this one waits it out too
                delay = wait or retry_backoff_seconds(attempt)
                if wait and on_wait is not None:
                    on_wait(wait)
                # the status or the exception's type only: its text can quote a request header
                reason = f"HTTP {_http_status(exc)}" if _http_status(exc) else type(exc).__name__
                logger.info("GitHub batch: %s, retry %d/%d in %.1fs", reason, attempt, self._max_retries, delay)
                self._sleep(delay)

    def fetch_repo_health(
        self,
        repos: Sequence[tuple[str, str]],
        *,
        fetcher: Callable[[dict[str, Any]], Any] | None = None,
        auth: credential_switch.BearerAuth | None = None,
    ) -> pd.DataFrame:
        """The real GraphQL fetch (Phase K/N): one batched POST per
        :data:`GITHUB_BATCH_QUERY_MAX`-sized chunk of ``repos`` (review fix #5,
        mirrors the Basilisk ``chunk_queries`` precedent), each retried under
        :meth:`_fetch_batch_with_retry` (review fix #3/#4). An EMPTY ``repos`` makes
        ZERO network calls — not even the harmless rate-limit probe (review fix #2;
        mirrors ``VcsHostSeedDataset``/``RegistryUpstreamDataset``'s empty-batch
        no-op: their ``for`` loop over an empty identifier list never calls
        ``fetch_one``). A chunk that fails after retries degrades to per-repo error
        rows for just that chunk (never the whole batch) rather than raising.
        Persists through the same last-good + ``StalenessMarker`` pattern as
        :class:`~pyforge.atlas.datasets.vcs_sources.VcsHostSeedDataset`, including its
        total-failure clobber-safety fix."""
        empty = pd.DataFrame(columns=list(self._COLUMNS))
        if not repos:
            self._persist(empty)
            return empty
        rows: list[dict[str, Any]] = []
        last_failure = ""
        stopped = False
        for chunk in chunk_queries(list(repos), GITHUB_BATCH_QUERY_MAX):
            if stopped:
                break  # Story 35.1: the remaining chunks would meet the same refusal
            payload, exc = self._fetch_batch_with_retry(chunk, fetcher=fetcher, auth=auth)
            if exc is not None:
                status = _http_status(exc)
                if auth is not None:
                    # never the exception text on the credentialed path: it can quote a request header
                    last_failure = f"HTTP {status}" if status else type(exc).__name__
                    stopped = status in _STOP_STATUSES
                else:
                    last_failure = f"{type(exc).__name__}: {exc}"
                logger.warning("GitHub batch fetch failed, keeping last-good: %s", last_failure)
                for owner, name in chunk:
                    rows.append(
                        {
                            "kind": "health",
                            "key": name,
                            "feedstock_name": name,
                            "conda_name": pd.NA,
                            "archived": pd.NA,
                            "upstream_version": pd.NA,
                            "last_error": f"batch fetch failed: {last_failure}",
                            "stars": pd.NA,
                            "last_commit": pd.NA,
                            "open_issues": pd.NA,
                        }
                    )
                continue
            data = payload.get("data") if isinstance(payload, dict) else None
            alias_errors = _graphql_errors(payload)
            general = alias_errors.get(None) if not isinstance(data, dict) else None
            if general:  # a body of errors and no data: a rate limit, a bad query
                last_failure = f"GraphQL error: {general}"
            for i, (owner, name) in enumerate(chunk):
                repo = data.get(f"r{i}") if isinstance(data, dict) else None
                if not isinstance(repo, dict):
                    rows.append(
                        {
                            "kind": "health",
                            "key": name,
                            "feedstock_name": name,
                            "conda_name": pd.NA,
                            "archived": pd.NA,
                            "upstream_version": pd.NA,
                            "last_error": alias_errors.get(f"r{i}") or general or "repository not found in response",
                            "stars": pd.NA,
                            "last_commit": pd.NA,
                            "open_issues": pd.NA,
                        }
                    )
                    continue
                issues = repo.get("issues") if isinstance(repo.get("issues"), dict) else {}
                rows.append(
                    {
                        "kind": "health",
                        "key": name,
                        "feedstock_name": name,
                        "conda_name": pd.NA,
                        "archived": bool(repo.get("isArchived")),
                        "upstream_version": pd.NA,
                        "last_error": None,
                        "stars": repo.get("stargazerCount"),
                        "last_commit": repo.get("pushedAt"),
                        "open_issues": issues.get("totalCount"),
                    }
                )
        frame = pd.DataFrame(rows, columns=list(self._COLUMNS))
        # AD-13 clobber-safety: a batch where every repo failed must not overwrite
        # last-good with an all-error result (mirrors the VcsHost/Registry fix).
        has_success = bool(rows) and frame["last_error"].isna().any()
        if auth is not None and not has_success and last_failure:
            # Story 35.1: say why (a rejected token reads HTTP 401; no exception text, which could
            # quote a request header)
            self._mark_stale(f"every GitHub batch failed ({last_failure}) -- keeping last-good")
            return frame
        self._persist(frame if has_success else empty)
        if stopped and has_success:
            # the rows fetched before the refusal are kept, but the store is not current
            self._mark_stale(f"stopped after {last_failure} -- the remaining batches keep last-good")
        return frame

    # -- Story 35.3: legacy's three GitHub reads (Phases K, N and E.5) -------------------------

    def build_upstream_query(self, repos: Sequence[tuple[str, str]]) -> dict[str, Any]:
        """Phase K (``_phase_k_github_graphql_batch``, CFA:4695-4760): each repo's latest release
        and latest tag, and the rate limit."""
        parts = [
            f"r{i}: repository(owner: {json.dumps(str(owner))}, name: {json.dumps(str(name))}) {{ "
            "releases(first: 1, orderBy: {field: CREATED_AT, direction: DESC}) { nodes { tagName } } "
            'refs(refPrefix: "refs/tags/", first: 1, orderBy: {field: TAG_COMMIT_DATE, direction: DESC}) '
            "{ nodes { name } } }"
            for i, (owner, name) in enumerate(repos)
        ]
        return self.with_query("query { " + " ".join(parts) + " rateLimit { cost remaining resetAt } }")

    def build_feedstock_query(self, feedstocks: Sequence[str]) -> dict[str, Any]:
        """Phase N (CFA:6461-6474): each ``conda-forge/<name>-feedstock``'s last push, default-branch
        CI state and open issues and PRs (and whether it is archived)."""
        parts = [
            f'r{i}: repository(owner: "conda-forge", name: {json.dumps(str(fs) + "-feedstock")}) {{ '
            "pushedAt isArchived defaultBranchRef { target { ... on Commit { statusCheckRollup { state } } } } "
            "issues(states: OPEN) { totalCount } pullRequests(states: OPEN) { totalCount } }"
            for i, fs in enumerate(feedstocks)
        ]
        return self.with_query("query { " + " ".join(parts) + " }")

    def build_archived_query(self, cursor: str | None) -> dict[str, Any]:
        """Phase E.5 (``phase_e5_archived_feedstocks``, CFA:2504): one page of the conda-forge
        organization's archived repositories."""
        after = f", after: {json.dumps(cursor)}" if cursor else ""
        return self.with_query(
            'query { organization(login: "conda-forge") { '
            f"repositories(first: 100, isArchived: true{after}) {{ "
            "nodes { name archivedAt } pageInfo { hasNextPage endCursor } } } }"
        )

    def fetch_github(
        self,
        upstream_repos: Sequence[tuple[str, str, str]],
        feedstocks: Sequence[str],
        *,
        auth: credential_switch.BearerAuth | None = None,
        fetcher: Callable[[dict[str, Any]], Any] | None = None,
    ) -> pd.DataFrame:
        """Story 35.3: the upstream versions (Phase K), the feedstock health (Phase N) and the
        archived feedstocks (Phase E.5), as rows of ``kind`` ``upstream``, ``feedstock`` and
        ``archived``. Never raises (AD-13).

        - A 401, 403 or 429 that names no wait, or a ``RATE_LIMITED`` answer, stops every request
          not yet sent, in every thread (Story 35.1); a ``Retry-After`` pauses every thread.
        - A repository the run could not read keeps its last-good values, its ``last_error`` set
          (legacy Phase N sets ``gh_status_last_error`` and keeps the rest); one with no last-good
          row gets an empty row with the error.
        - When no Phase K or N repository was read, nothing is written and last-good is kept.
        - The marker names what failed: a stop, the repositories that still failed, or an
          archived-listing page."""
        rows: list[dict[str, Any]] = []
        failed_rows: set[tuple[str, str]] = set()
        lock = threading.Lock()
        mine = threading.local()  # the pause each thread has already waited out
        state: dict[str, Any] = {
            "failure": "",
            "first_failure": "",
            "stopped": False,
            "pause_until": 0.0,
            "batches_failed_in_a_row": 0,
            "archived_failed": "",
        }

        def before_attempt() -> bool:
            """Every thread waits out a pause another set, and none sends after a stop."""
            until = state["pause_until"]
            if until > getattr(mine, "waited_until", 0.0):
                wait = until - time.monotonic()
                if wait > 0:
                    self._sleep(wait)
                mine.waited_until = until
            return not state["stopped"]

        def on_wait(seconds: float) -> None:
            """A ``Retry-After`` this thread waits out pauses every other thread too."""
            until = time.monotonic() + seconds
            with lock:
                state["pause_until"] = max(state["pause_until"], until)
            mine.waited_until = until

        def stop(failure: str) -> None:
            with lock:
                state["stopped"] = True
                state["failure"] = failure

        def run(
            chunk: Sequence[Any], build: Callable[[Sequence[Any]], dict[str, Any]]
        ) -> tuple[tuple[dict, dict] | None, str, bool]:
            """One batch: ``(data and errors, or None; the failure; whether it timed out)``."""
            if state["stopped"]:
                return None, _UNSENT, False
            payload, exc = self._fetch_batch_with_retry(
                chunk, fetcher=fetcher, auth=auth, build=build, before_attempt=before_attempt, on_wait=on_wait
            )
            if exc is not None:
                status = _http_status(exc)
                # never the exception text on the credentialed path: it can quote a request header
                if isinstance(exc, _Stopped):
                    return None, _UNSENT, False
                failure = f"HTTP {status}" if status else type(exc).__name__
                if status in _STOP_STATUSES:
                    stop(failure)
                logger.warning("GitHub batch fetch failed, keeping last-good: %s", failure)
                timed_out = status in (502, 504) or "Timeout" in type(exc.__cause__).__name__
                return None, failure, timed_out
            errors = _graphql_errors(payload)
            if str(errors.get(None, "")).startswith("RATE_LIMITED"):
                failure = f"GraphQL error: {errors[None]}"
                stop(failure)  # the hour's points are spent: nothing more is sent
                return None, failure, False
            data = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(data, dict):
                return None, f"GraphQL error: {errors.get(None) or 'no data'}", False
            return (data, errors), "", False

        def run_split(
            chunk: Sequence[Any], build: Callable[[Sequence[Any]], dict[str, Any]]
        ) -> tuple[dict, dict, dict[int, str]]:
            """Story 35.3: a batch GitHub could not answer in time (502, 504 or a timeout) is halved
            and each half asked, while it holds more than ``HALVE_MIN`` repositories; legacy Phase K
            drops the whole batch. Returns the data and errors by the batch's own aliases, and the
            failure of each repository the run could not read, by index."""
            got, failure, timed_out = run(chunk, build)
            if got is not None:
                return got[0], got[1], {}
            if len(chunk) <= self.HALVE_MIN or state["stopped"] or not timed_out:
                return {}, {}, dict.fromkeys(range(len(chunk)), failure)
            half = len(chunk) // 2
            data: dict[str, Any] = {}
            errors: dict[str | None, str] = {}
            failed: dict[int, str] = {}
            for offset, part in ((0, chunk[:half]), (half, chunk[half:])):
                sub_data, sub_errors, sub_failed = run_split(part, build)
                data.update(_renumbered(sub_data, offset))
                errors.update(_renumbered(sub_errors, offset))
                failed.update({i + offset: f for i, f in sub_failed.items()})
            return data, errors, failed

        def answered(chunk: Sequence[Any], failed: dict[int, str]) -> None:
            """Count the batches that failed whole, in a row; ten stop the run (a lasting outage)."""
            failed = {i: f for i, f in failed.items() if f != _UNSENT}
            with lock:
                if len(failed) == len(chunk) and chunk:
                    first = next(iter(failed.values()))
                    state["failure"] = state["failure"] or first
                    state["first_failure"] = state["first_failure"] or first
                    state["batches_failed_in_a_row"] += 1
                    if state["batches_failed_in_a_row"] >= self.FAILED_BATCHES_LIMIT and not state["stopped"]:
                        state["stopped"] = True
                        state["failure"] = f"{self.FAILED_BATCHES_LIMIT} batches failed in a row ({first})"
                else:
                    state["batches_failed_in_a_row"] = 0
                    if failed:
                        state["first_failure"] = state["first_failure"] or next(iter(failed.values()))

        # Phase K: each distinct repo once (GitHub names ignore case), its version written to every
        # package that names it; the first spelling met is the one asked
        packages: dict[tuple[str, str], list[str]] = {}
        spelled: dict[tuple[str, str], tuple[str, str]] = {}
        for conda, owner, name in upstream_repos:
            repo = spelled.setdefault((owner.lower(), name.lower()), (owner, name))
            packages.setdefault(repo, []).append(conda)
        upstream_chunks = list(chunk_queries(sorted(packages), self.UPSTREAM_BATCH))
        for n, chunk in enumerate(upstream_chunks, start=1):
            if n % self.PROGRESS_EVERY == 1:
                logger.info("GitHub upstream versions: batch %d of %d", n, len(upstream_chunks))
            data, errors, failed = run_split(chunk, self.build_upstream_query)
            answered(chunk, failed)
            for i, (owner, name) in enumerate(chunk):
                if failed.get(i) == _UNSENT:
                    continue  # never asked: no row, last-good untouched
                version: str | None = None
                error: str | None
                if i in failed:
                    error = failed[i]
                else:
                    node = data.get(f"r{i}")
                    if isinstance(node, dict):
                        releases = (node.get("releases") or {}).get("nodes") or []
                        tags = (node.get("refs") or {}).get("nodes") or []
                        tag = releases[0].get("tagName") if releases and isinstance(releases[0], dict) else None
                        if not tag and tags and isinstance(tags[0], dict):
                            tag = tags[0].get("name")
                        version = normalize_release_tag(tag)
                        error = None if version else "no tags"
                    else:
                        error = errors.get(f"r{i}") or "repository not found in response"
                for conda in packages[(owner, name)]:
                    if i in failed:
                        failed_rows.add(("upstream", conda))
                    rows.append(
                        {
                            "kind": "upstream",
                            "key": conda,
                            "conda_name": conda,
                            "repo": f"{owner}/{name}",
                            "upstream_version": version,
                            "last_error": error,
                        }
                    )
        # Phase N: legacy runs its batches four at a time (PHASE_N_CONCURRENCY, CFA:6585); in order
        feedstock_chunks = list(chunk_queries(sorted(set(feedstocks)), self.FEEDSTOCK_BATCH))
        with ThreadPoolExecutor(max_workers=self.FEEDSTOCK_CONCURRENCY) as pool:
            answers = pool.map(lambda chunk: run_split(chunk, self.build_feedstock_query), feedstock_chunks)
            for n, (chunk, (data, errors, failed)) in enumerate(zip(feedstock_chunks, answers, strict=True), start=1):
                if n % self.PROGRESS_EVERY == 1:
                    logger.info("GitHub feedstock health: batch %d of %d", n, len(feedstock_chunks))
                answered(chunk, failed)
                for i, fs in enumerate(chunk):
                    if failed.get(i) == _UNSENT:
                        continue  # never asked: no row, last-good untouched
                    row: dict[str, Any] = {
                        "kind": "feedstock",
                        "key": fs,
                        "feedstock_name": fs,
                        "repo": f"conda-forge/{fs}-feedstock",
                    }
                    node = None if i in failed else data.get(f"r{i}")
                    if isinstance(node, dict):
                        target = (node.get("defaultBranchRef") or {}).get("target") or {}
                        rollup = target.get("statusCheckRollup") if isinstance(target, dict) else None
                        ci = rollup.get("state") if isinstance(rollup, dict) else None
                        row.update(
                            last_commit=node.get("pushedAt"),
                            archived=bool(node.get("isArchived")),
                            open_issues=(node.get("issues") or {}).get("totalCount"),
                            open_prs=(node.get("pullRequests") or {}).get("totalCount"),
                            # legacy stores the rollup state lowercased (_row_from_payload), and the
                            # semantic layer's red states are "failure" and "error"
                            ci_status=str(ci).lower() if ci else None,
                            last_error=None,
                        )
                    elif i in failed:
                        row["last_error"] = failed[i]
                        failed_rows.add(("feedstock", fs))
                    else:
                        row["last_error"] = errors.get(f"r{i}") or "repository not found in response"
                    rows.append(row)
        # Phase E.5: the organization's archived repositories, page by page
        cursor: str | None = None
        for page_number in range(1, self.ARCHIVED_MAX_PAGES + 1):
            got, failure, _timed_out = run([cursor], lambda chunk: self.build_archived_query(chunk[0]))
            if got is None:
                state["archived_failed"] = f"archived listing stopped at page {page_number}: {failure}"
                break
            listing = (got[0].get("organization") or {}).get("repositories") or {}
            for node in listing.get("nodes") or []:
                repo_name = node.get("name") if isinstance(node, dict) else None
                if isinstance(repo_name, str) and repo_name.endswith("-feedstock"):
                    fs = repo_name[: -len("-feedstock")]
                    rows.append(
                        {
                            "kind": "archived",
                            "key": fs,
                            "feedstock_name": fs,
                            "archived": True,
                            "archived_at": node.get("archivedAt"),
                            "last_error": None,
                        }
                    )
            page = listing.get("pageInfo") or {}
            if not page.get("hasNextPage") or not page.get("endCursor"):
                break
            cursor = str(page["endCursor"])

        frame = pd.DataFrame(rows, columns=list(self._COLUMNS))
        asked = frame["kind"].isin(("upstream", "feedstock"))
        read_any = bool(
            (asked & ~frame.apply(lambda r: (r["kind"], r["key"]) in failed_rows, axis=1)).any()
            if not frame.empty
            else False
        )
        if asked.any() and not read_any:
            self._mark_stale(
                f"every GitHub batch failed ({state['failure'] or state['first_failure']}) -- keeping last-good"
            )
            return frame
        if not rows:
            self._mark_stale(f"nothing fetched ({state['failure'] or state['archived_failed'] or 'nothing asked'})")
            return frame
        self._persist(self._carried_forward(frame, failed_rows))
        reasons = []
        if state["stopped"]:
            reasons.append(f"stopped after {state['failure']} -- the remaining batches keep last-good")
        elif failed_rows:
            reasons.append(
                f"repositories that failed: {len(failed_rows)} ({state['first_failure']}) -- they keep last-good"
            )
        if state["archived_failed"]:
            reasons.append(state["archived_failed"])
        if reasons:
            self._mark_stale("; ".join(reasons))
        return frame

    def _carried_forward(self, frame: pd.DataFrame, failed_rows: set[tuple[str, str]]) -> pd.DataFrame:
        """Story 35.3: each row the run could not read takes its last-good values, keeping only its
        new ``last_error`` (legacy Phase N's ``gh_status_last_error``); a row with no last-good stays
        empty with its error."""
        if not failed_rows or not self._store_exists():
            return frame
        try:
            stored = pd.read_parquet(self._store_path)
        except Exception:  # noqa: BLE001 -- an unreadable store carries nothing forward
            return frame
        if not {"kind", "key"} <= set(stored.columns):
            return frame
        stored = stored.drop_duplicates(["kind", "key"], keep="last").set_index(["kind", "key"])
        out = frame.astype(object)  # a column the run left all-null takes a stored string or number
        for idx, row in out.iterrows():
            ident = (row["kind"], row["key"])
            if ident not in failed_rows or ident not in stored.index:
                continue
            last = stored.loc[ident]
            for column in out.columns:
                if column not in ("kind", "key", "last_error") and column in stored.columns:
                    out.at[idx, column] = last[column]
        return out

    def _persist(self, frame: pd.DataFrame) -> None:
        """Story 35.3: a store written before this story has no ``kind`` or ``key``; its rows are
        the identity health rows, so they take ``kind="health"`` and ``key=feedstock_name`` before
        the merge, rather than all collapsing onto one empty key."""
        if self._store_exists():
            try:
                existing = pd.read_parquet(self._store_path)
                if "kind" not in existing.columns or "key" not in existing.columns:
                    for column in ("kind", "key"):
                        if column not in existing.columns:
                            existing[column] = pd.Series(index=existing.index, dtype=object)
                    existing["kind"] = existing["kind"].fillna("health")
                    existing["key"] = existing["key"].fillna(existing["feedstock_name"])
                    self._atomic_write(self._store_path, lambda p: existing.to_parquet(p, index=False))
            except Exception as exc:  # noqa: BLE001 -- the base merge then writes the batch alone
                logger.warning("could not migrate %s to kind/key rows: %s", self._store_path, exc)
        super()._persist(frame)

    def load(self) -> pd.DataFrame:
        """The store as the consumers read it. Story 35.3: with ``pyforge.atlas.live_vcs_universe`` off,
        only the identity health rows, as before the story; a store written under the flag keeps its
        other kinds for when it is on again."""
        frame = self._read_store(self._COLUMNS)
        if credential_switch.live_vcs_universe() or "kind" not in frame.columns:
            return frame
        return frame[frame["kind"].isna() | (frame["kind"] == "health")].reset_index(drop=True)

    def save(self, data: Any) -> None:
        if not isinstance(data, RefreshRequest):
            raise NotImplementedError(
                f"{type(self).__name__} only accepts a RefreshRequest trigger; it is "
                "otherwise a read-only request source."
            )
        if data.store != self._expected_store:
            # review fix #8: see VcsHostSeedDataset.save.
            raise ValueError(
                f"{type(self).__name__} is configured for store {self._expected_store!r} "
                f"but received a RefreshRequest for {data.store!r} — pipeline wiring has "
                "drifted out of sync."
            )
        if not data.force and not self._refresh_due(data.cadence_seconds):
            self._clear_stale()
            return
        if credential_switch.live_vcs_universe():
            # Story 35.1: GitHub's GraphQL API needs a token, so this fetch runs only when the
            # operator set the switch for the run; otherwise nothing is sent (AD-11)
            auth = credential_switch.github_auth(self._credentials, self._base_url)
            if auth is None:
                self._mark_stale(credential_switch.skip_reason(self._base_url))
                return
            # Stories 35.2 and 35.3: the universe's upstreams and feedstocks, read as legacy reads them
            self.fetch_github(data.upstream_repos, data.feedstocks, auth=auth)
            return
        self.fetch_repo_health(data.github_repos)


class PyPIJsonRequestDataset(_RequestParameterizedAPIDataset):
    """Per-project ``/pypi/<name>/json`` request source (Phases H + R). B2 FLIP.

    The A2 interim declared a single ``.../pypi`` URL with an explicit ``# FLIP(B2)``:
    ``one APIDataset = one URL, but this feed is per-project parameterized … nodes may
    NOT build request URLs (AC-2)``. This class lands the real request-parameterized
    dataset: :meth:`request_path` builds the per-project path a node may never build,
    and :meth:`load_many` is the concrete per-project fan-out that acquires a
    rate-limit token per request (DW-B1-2). ``pypi_json_raw``.

    The node (Phase H ``fetch_pypi_current_versions`` / Phase R ``enrich_pypi_intelligence``)
    consumes the already-fetched frames THIS dataset resolves — it never reaches the
    fan-out (THE CRUX).
    """

    #: Story 34.10: the wait between 429/503 attempts (injectable; tests never sleep)
    retry_sleep: Callable[[float], None] = staticmethod(time.sleep)

    def request_path(self, name: str) -> str:
        """Build the per-project ``/pypi/<name>/json`` request path — the
        parameterization a node may NOT perform (AC-2). ``name`` is coerced to ``str``
        so a stray non-string cell cannot crash the fan-out."""
        if name is None:
            raise ValueError("request_path requires a project name, got None")
        return f"{self._base_url.rstrip('/')}/pypi/{str(name).strip('/')}/json"

    def fetch_one(self, request_key: str, *, fetcher: Callable[[str], Any] | None = None) -> Any:
        """Fetch one per-project JSON URL, acquiring a rate-limit token first."""
        self.scheduler.acquire()
        if fetcher is not None:
            return fetcher(request_key)
        url = (
            request_key
            if str(request_key).startswith("http")
            else self.request_path(str(request_key).split("/")[-2] if "/pypi/" in str(request_key) else request_key)
        )
        load_args = dict(self._load_args)
        if self._credentials is None:
            # Story 34.10: a public GET -- a timeout, and no ~/.netrc credential; a fresh
            # dict each time, because APIDataset pops "auth" out of the args it is given
            load_args = {**public_sources.request_args(_PYPI_JSON_TIMEOUT_SECONDS), **load_args}
        inner = APIDataset(
            url=url,
            method=self._method,
            load_args=load_args,
            credentials=self._credentials,
            metadata=self.metadata,
        )
        return _coerce_api_json(inner.load())

    def load(self) -> Any:
        """The per-project fan-out is NOT a single-URL load — the DAG must drive it via
        :meth:`load_many` with the resolved actionable project names (credentialed +
        attended, NFR-2/AD-11). Raise a clear error rather than silently fetch the bare
        base URL (which is not a valid ``/pypi/<name>/json`` endpoint). B2 wires the
        DW-B1-2 ``acquire()`` into :meth:`load_many` / :meth:`fetch_one`; the concrete
        DAG-load fan-out (resolving names -> N gated requests) is dataset-owned +
        attended, mirroring B1's deferral of the anaconda/github fan-out."""
        from kedro.io.core import DatasetError

        raise DatasetError(
            "PyPIJsonRequestDataset is a per-project fan-out source: drive it via "
            "load_many(names) (the scheduler-gated per-project loop), not a single "
            "load(). Credentialed live fan-out is attended-only (NFR-2/AD-11)."
        )

    def load_many(self, names: list[str], *, fetcher: Callable[[str], Any] | None = None) -> dict[str, Any]:
        """Concrete per-project fan-out (Phase H/R): issue ONE request per project
        name, acquiring a rate-limit token before each (DW-B1-2). Returns a mapping
        ``name -> resolved payload``. ``fetcher`` is injectable for fixtures; the
        default routes each per-project path through the composed ``APIDataset``.
        Missing names (``None`` / NaN) are skipped.

        WARNING (fake-clock coupling): a frozen clock + no-op sleep makes
        :meth:`RateLimitedScheduler.acquire` infinite-spin once the bucket drains — B2
        adds a CODE ceiling in :meth:`RateLimitedScheduler.acquire` that RAISES rather
        than hangs, but fixtures should still use an advancing clock OR
        ``bucket_capacity >= len(names)`` (see the class docstring +
        ``tests/datasets/test_pypi_json_request_dataset.py``).
        """
        out: dict[str, Any] = {}
        failures: dict[str, str] = {}
        for name in names:
            if name is None or (isinstance(name, float) and name != name):  # None / NaN
                continue
            key = self.request_path(name)
            for attempt in range(_PYPI_JSON_ATTEMPTS):
                try:
                    out[name] = self.fetch_one(key, fetcher=fetcher)
                    break
                except DatasetError as exc:
                    # Story 34.2: kedro's APIDataset wraps every HTTP and connection failure as
                    # DatasetError; one project's miss never aborts the fan-out. Anything else (a
                    # rate-limiter guard, a programming error) still raises.
                    cause = exc.__cause__ if exc.__cause__ is not None else exc
                    response = getattr(cause, "response", None)
                    status = getattr(response, "status_code", None)
                    if status in _PYPI_JSON_RETRY_STATUSES and attempt + 1 < _PYPI_JSON_ATTEMPTS:
                        # Story 34.10: legacy Phase H's 429/503 retry -- the server's Retry-After
                        # (capped at 60 s), else 1 s then 2 s (CFA:4117). Unlike legacy, there is
                        # no jitter (one sequential worker) and no retry of non-HTTP failures.
                        headers = getattr(response, "headers", None) or {}
                        wait = parse_retry_after(headers.get("Retry-After")) or float(2**attempt)
                        self.retry_sleep(wait)
                        continue
                    prefix = f"HTTP {status}: " if status is not None else ""
                    failures[name] = f"{prefix}{type(cause).__name__}: {cause}"[:200]
                    break
        # Story 34.2: a name PyPI does not serve (the bot's mapping carries a few) is a
        # per-project miss; callers read the misses here.
        self.last_failures = failures
        return out


class PyPIJsonFanOutDataset(_ParquetRefreshStore, PyPIJsonRequestDataset):
    """Catalog entry for ``pypi_json_raw``: live per-project fan-out over the
    candidate names already resolved by ``pypi_conda_map_store`` (Story 21.2 —
    replaces the ``cf_atlas.db`` seed; ``PYPI_JSON_LIVE_FANOUT`` is no longer a hard
    gate, so live fan-out is the default fetch path).

    ``load()`` is a read-only projection of the persisted store (review fix #6 —
    mirrors ``GitHubRequestDataset``/``VcsHostSeedDataset``: the AD-13 last-good +
    staleness pattern every other class in this diff follows, rather than doing an
    unbounded, ungated live fetch on every ``load()`` call with no fallback). The
    real per-project fan-out (:meth:`fetch_candidates`) runs only via
    ``save(RefreshRequest(...))``, the ``pypi_intelligence`` pipeline's
    ``refresh_pypi_json_store`` trigger node being the single writer — a network
    hiccup during that refresh keeps the previous last-good slice rather than
    degrading every downstream consumer to nothing.

    The candidate ``pypi_name`` universe comes from the already-populated
    ``pypi_conda_map_store`` flat cache (read via a composed
    :class:`~.refresh.MappingCacheDataset`, never a second fetch); both the key
    (``pypi_name``) and value (``conda_name``) are filtered to real strings (review
    fix #12, matching ``ParselmouthMappingDataset``'s filter). ``PYPI_JSON_FANOUT_LIMIT``
    bounds the batch (default 200; ``0`` explicitly disables the fetch this cycle —
    review fix #7; see :func:`_pypi_json_fanout_limit`).
    """

    _COLUMNS = tuple(_PYPI_JSON_FRAME_COLUMNS)
    # Story 34.10: one row per PyPI project. The base merges on conda_name, so a second
    # project mapped to the same conda package replaced the first.
    merge_on = ("pypi_name",)

    def __init__(
        self,
        *,
        url: str,
        filepath: str,
        mapping_filepath: str,
        method: str = "GET",
        load_args: dict[str, Any] | None = None,
        save_args: dict[str, Any] | None = None,
        credentials: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        rps: float = DEFAULT_RPS,
        scheduler: RateLimitedScheduler | None = None,
    ) -> None:
        # review fix #9: a fully explicit signature (no **kwargs sink) — matches the
        # no-kwargs-sink principle already applied to ParselmouthMappingDataset; an
        # unrecognized catalog key raises TypeError loudly instead of being silently
        # forwarded/swallowed.
        super().__init__(
            url=url,
            method=method,
            load_args=load_args,
            save_args=save_args,
            credentials=credentials,
            metadata=metadata,
            rps=rps,
            scheduler=scheduler,
        )
        self._filepath = str(filepath)  # this dataset's OWN persisted store (_ParquetRefreshStore)
        self._mapping_cache = MappingCacheDataset(filepath=mapping_filepath)
        # review fix #8: exactly one catalog entry — validated in save().
        self._expected_store = "pypi_json_raw"

    def _candidate_names(self, pairs: Sequence[tuple[str, str]] = ()) -> tuple[list[str], dict[str, str]]:
        """The candidate universe: ``pairs`` from the same run's Phase C mapping (Story
        34.2; on a fresh data root the flat cache below does not exist yet) united with the
        flat ``pypi_conda_map_store`` from the previous run (its C.5 source-URL matches)."""
        try:
            mapping = self._mapping_cache.load()
        except Exception as exc:  # never raise: degrade to an empty candidate set.
            logger.warning("pypi_conda_map_store unreadable, degrading to empty: %s", exc)
            mapping = {}
        if not isinstance(mapping, dict):
            mapping = {}
        # Story 34.10: keyed by the PEP 503 name, so two spellings of one project (the bot and
        # a recipe tier may differ: `dagster_aws`, `dagster-aws`) are one candidate and one row.
        # The flat cache from the previous run wins on conflict; this run's pairs only add.
        merged: dict[str, str] = {}
        for k, v in dict(mapping).items():
            if isinstance(k, str) and k and isinstance(v, str):
                merged.setdefault(_pep503(k), v)
        for pair in pairs:
            if len(pair) == 2 and isinstance(pair[0], str) and pair[0] and isinstance(pair[1], str) and pair[1]:
                merged.setdefault(_pep503(pair[0]), pair[1])
        # review fix #12: filter BOTH key and value to real strings (matches
        # ParselmouthMappingDataset's filter) — a malformed entry must not crash the
        # fan-out or surface a non-string conda_name downstream.
        names = sorted(merged)
        return names, merged

    def _eligible(self, names: list[str], serials: dict[str, int], now: float) -> list[str]:
        """Story 34.10: legacy Phase H's eligible set (``_phase_h_eligible_pypi_names``,
        CFA:4174) over the candidates: never fetched, then serial moved (NULL-safe, as
        legacy's ``IS NOT``: a known serial against a missing stamp counts as moved), then
        fetched more than 30 days ago, oldest first. Anything else is current.

        A known miss (a 404, kept in ``misses.json`` as legacy stamps it, CFA:4300) is not
        "never fetched": it waits, like a stored row, for its serial to move or 30 days, and
        then goes last, so permanent misses never crowd out a moved serial under a cap."""
        stored = self._read_store(("pypi_name", "fetched_at", "pypi_version_serial_at_fetch"))
        misses = self._read_misses()

        def _miss_at(name: str) -> float:
            try:
                return float(misses.get(name, {}).get("fetched_at") or 0)
            except TypeError, ValueError:  # a malformed miss is simply due
                return 0.0

        fetched_at: dict[str, float] = {}
        stamped: dict[str, int | None] = {}
        for name, at, serial in zip(
            stored["pypi_name"],
            pd.to_numeric(stored["fetched_at"], errors="coerce"),
            pd.to_numeric(stored["pypi_version_serial_at_fetch"], errors="coerce"),
            strict=True,
        ):
            if isinstance(name, str):
                fetched_at[name] = float(at) if pd.notna(at) else 0.0
                stamped[name] = int(serial) if pd.notna(serial) else None
        never, moved, recheck, missed = [], [], [], []
        for name in names:
            miss = misses.get(name)
            if name in fetched_at and miss is not None and _miss_at(name) > fetched_at[name]:
                # a project once stored, then gone: its newer 404 is what it was last fetched at
                del fetched_at[name]
            if name not in fetched_at:
                if miss is None:
                    never.append(name)
                elif (name in serials and serials[name] != miss.get("serial")) or _miss_at(
                    name
                ) < now - _PHASE_H_RECHECK_SECONDS:
                    missed.append(name)
            elif name in serials and serials[name] != stamped.get(name):
                moved.append(name)
            elif fetched_at[name] < now - _PHASE_H_RECHECK_SECONDS:
                recheck.append(name)
        recheck.sort(key=lambda n: fetched_at[n])
        return never + moved + recheck + missed

    _MISSES_FILENAME = "misses.json"

    def _read_misses(self) -> dict[str, dict[str, Any]]:
        try:
            raw = json.loads((Path(self._filepath) / self._MISSES_FILENAME).read_text(encoding="utf-8"))
        except OSError, ValueError:
            return {}
        return {k: v for k, v in raw.items() if isinstance(v, dict)} if isinstance(raw, dict) else {}

    def _write_misses(self, misses: dict[str, dict[str, Any]]) -> None:
        def _write(path: Path) -> None:
            path.write_text(json.dumps(dict(sorted(misses.items())), indent=1), encoding="utf-8")

        try:
            Path(self._filepath).mkdir(parents=True, exist_ok=True)
            atomic_write(Path(self._filepath) / self._MISSES_FILENAME, _write)
        except OSError as exc:
            logger.warning("could not keep the pypi fan-out misses: %s", exc)

    def fetch_candidates(
        self,
        *,
        fetcher: Callable[[str], Any] | None = None,
        pairs: Sequence[tuple[str, str]] = (),
        serials: Sequence[tuple[str, int]] = (),
    ) -> pd.DataFrame:
        """The real per-project fan-out (Story 21.2, dataset-owned IO, AD-2): bounded
        by ``PYPI_JSON_FANOUT_LIMIT`` (``0`` explicitly disables it this cycle —
        review fix #7). Persists through the AD-13 last-good pattern; :meth:`load_many`
        (KEEP as-is) does the actual per-project requests — this method only sources
        the candidate list and persists the result.

        Story 34.10: while live public sources are on, the batch is legacy Phase H's
        eligible set over every candidate (:meth:`_eligible`), uncapped unless
        ``PYPI_JSON_FANOUT_LIMIT`` is set; each row stamps the serial it was fetched at.
        Off, the bounded rotation below is unchanged."""
        if public_sources.live():
            return self._fetch_eligible(fetcher=fetcher, pairs=pairs, serials=dict(serials))
        empty = pd.DataFrame(columns=list(self._COLUMNS))
        limit = _pypi_json_fanout_limit()
        if limit == 0:
            self._mark_stale("fan-out disabled this cycle (PYPI_JSON_FANOUT_LIMIT=0)")
            return empty
        names, mapping = self._candidate_names(pairs)
        if not names:
            self._persist(empty)
            return empty
        offset_path = Path(self._filepath) / ".fanout_offset"
        offset = 0
        if offset_path.is_file():
            try:
                offset = int(offset_path.read_text(encoding="utf-8").strip() or "0")
            except OSError, ValueError:
                offset = 0
        if offset >= len(names):
            offset = 0
        rotated = names[offset:] + names[:offset]
        batch = rotated[:limit]
        next_offset = (offset + len(batch)) % len(names) if names else 0
        payloads = self.load_many(batch, fetcher=fetcher)
        failures = self.last_failures
        if payloads:
            # Story 34.2: advance the rotation only when the batch got answers, so an outage
            # does not skip a whole batch of names.
            try:
                offset_path.parent.mkdir(parents=True, exist_ok=True)

                def _write_offset(path: Path) -> None:
                    path.write_text(str(next_offset), encoding="utf-8")

                atomic_write(offset_path, _write_offset)
            except OSError as exc:
                logger.warning("could not persist pypi fan-out offset: %s", exc)
        if failures:
            logger.warning(
                "pypi_json_raw fan-out: %d of %d projects failed (e.g. %s)",
                len(failures),
                len(batch),
                next(iter(failures.items())),
            )
        if batch and not payloads:
            # Every request failed (an outage, not a few missing projects): keep last-good (AD-13).
            self._mark_stale(f"every request in the batch failed ({len(failures)}) -- keeping last-good")
            return empty
        rows: list[dict[str, Any]] = []
        for name in batch:
            if name not in payloads:  # a failed project keeps its last-good row, if any
                continue
            row = _payload_to_pypi_json_row(name, payloads.get(name))
            row["conda_name"] = mapping.get(name)
            rows.append(row)
        frame = pd.DataFrame(rows, columns=_PYPI_JSON_FRAME_COLUMNS).reset_index(drop=True)
        self._persist(frame)
        return frame

    #: Story 34.10: a cold run persists every this many projects, so a crash keeps what it
    #: fetched (legacy commits every 500 rows, CFA:4272) and stamps spread across the run
    PERSIST_EVERY = 500

    def _fetch_eligible(
        self,
        *,
        fetcher: Callable[[str], Any] | None,
        pairs: Sequence[tuple[str, str]],
        serials: dict[str, int],
    ) -> pd.DataFrame:
        """Story 34.10: fetch the eligible set in chunks, persisting each, and stamp each row's
        serial at fetch: the snapshot's serial when the trigger supplied it (legacy stamps Phase
        D's), else the payload's own ``last_serial``. A 404 is recorded as a miss; any other
        failure leaves the project eligible next run. An outage -- nothing answered and no 404
        -- keeps last-good under the marker."""
        empty = pd.DataFrame(columns=list(self._COLUMNS))
        cap = _pypi_json_fanout_cap()
        if cap == 0:
            self._mark_stale("fan-out disabled this cycle (PYPI_JSON_FANOUT_LIMIT=0)")
            return empty
        names, mapping = self._candidate_names(pairs)
        if not names:
            self._mark_stale("no candidates: the mapping names no PyPI project -- keeping last-good")
            return empty
        batch = self._eligible(names, serials, time.time())
        if cap is not None:
            batch = batch[:cap]
        logger.info("pypi_json_raw: %d of %d candidates eligible this run", len(batch), len(names))
        if not batch:
            self._clear_stale()  # every candidate is current: nothing to do is a clean run
            return empty
        misses = self._read_misses()
        failures: dict[str, str] = {}
        frames: list[pd.DataFrame] = []
        answered = recorded = 0
        for start in range(0, len(batch), self.PERSIST_EVERY):
            chunk = batch[start : start + self.PERSIST_EVERY]
            payloads = self.load_many(chunk, fetcher=fetcher)
            failures.update(self.last_failures)
            rows: list[dict[str, Any]] = []
            for name in chunk:
                if name in payloads:
                    payload = payloads[name]
                    row = _payload_to_pypi_json_row(name, payload)
                    row["conda_name"] = mapping.get(name)
                    own = payload.get("last_serial") if isinstance(payload, dict) else None
                    own_serial = int(own) if isinstance(own, int) and not isinstance(own, bool) else None
                    row["pypi_last_serial"] = serials.get(name, own_serial)
                    row["pypi_version_serial_at_fetch"] = serials.get(name, own_serial)
                    rows.append(row)
                    misses.pop(name, None)
                elif self.last_failures.get(name, "").startswith("HTTP 404"):
                    misses[name] = {"fetched_at": int(time.time()), "serial": serials.get(name)}
                    recorded += 1
            answered += len(rows)
            if rows:
                frame = pd.DataFrame(rows, columns=_PYPI_JSON_FRAME_COLUMNS).reset_index(drop=True)
                self._persist(frame)
                frames.append(frame)
            self._write_misses(misses)  # with each chunk, so a crash keeps the misses it found
        self.last_failures = failures
        if failures:
            logger.warning(
                "pypi_json_raw fan-out: %d of %d projects failed, %d of them 404 (e.g. %s)",
                len(failures),
                len(batch),
                recorded,
                next(iter(failures.items())),
            )
        if not answered and not recorded:
            self._mark_stale(f"every request in the batch failed ({len(failures)}) -- keeping last-good")
            return empty
        if not answered:
            self._clear_stale()  # only known-missing names this run: the endpoint answered
        return pd.concat(frames, ignore_index=True) if frames else empty

    def load(self) -> pd.DataFrame:
        return self._read_store(self._COLUMNS)

    def save(self, data: Any) -> None:
        if not isinstance(data, RefreshRequest):
            raise NotImplementedError(
                f"{type(self).__name__} only accepts a RefreshRequest trigger; it is "
                "otherwise a read-only request source."
            )
        if data.store != self._expected_store:
            # review fix #8: see VcsHostSeedDataset.save.
            raise ValueError(
                f"{type(self).__name__} is configured for store {self._expected_store!r} "
                f"but received a RefreshRequest for {data.store!r} — pipeline wiring has "
                "drifted out of sync."
            )
        # Story 34.10: live, the serial gate decides what is due, so the store's cadence
        # never holds back a project whose serial moved
        if not data.force and not public_sources.live() and not self._refresh_due(data.cadence_seconds):
            self._clear_stale()
            return
        self.fetch_candidates(pairs=data.pypi_pairs, serials=data.pypi_serials)


class PyPIBigQueryDownloadsDataset(AbstractDataset):
    """Catalog entry for ``pypi_bigquery_downloads_raw`` — Phase P admin opt-in stub.

    ``PHASE_P_ENABLED=1`` with ``PHASE_P_SOURCE=bigquery`` runs are attended-only
    (NFR-2/AD-11); every other path (``PHASE_P_ENABLED=1`` alone routes to ClickHouse, as
    legacy does -- Story 34.9) returns an empty but correctly-columned frame, so
    ``fetch_pypi_downloads`` keeps the ClickHouse rows (AD-6, never a default BigQuery job).
    """

    _COLS = ["pypi_name", "month", "downloads"]

    def __init__(self, *, metadata: dict[str, Any] | None = None, **kwargs: Any) -> None:
        _ = kwargs  # url/credentials kept in catalog for credentialed materialization flip
        self.metadata = metadata

    def load(self) -> pd.DataFrame:
        # Story 34.9: legacy routes PHASE_P_ENABLED=1 to ClickHouse unless PHASE_P_SOURCE=bigquery
        # (CFA:7387), so a shell that exports it for legacy must not fail the atlas run; the
        # ClickHouse rows then stand
        bigquery = os.environ.get("PHASE_P_SOURCE", "clickhouse").strip().lower() == "bigquery"
        if BigQueryDownloadsDataset.is_enabled() and bigquery:
            from kedro.io.core import DatasetError

            raise DatasetError(
                "PHASE_P_ENABLED=1 but BigQuery Phase P requires an attended "
                "credentialed run via BigQueryDownloadsDataset.run_gated(); "
                "the default Kedro catalog load path stays offline-safe."
            )
        return pd.DataFrame(columns=self._COLS)

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is read-only")

    def _describe(self) -> dict[str, Any]:
        return {
            "parameterization": type(self).__name__,
            "enabled": BigQueryDownloadsDataset.is_enabled(),
        }


# --- Phase P — the BigQuery cost-gate request dataset (THE CRUX) -------------

# On-demand BigQuery pricing, USD per TB scanned (tunable via env). The cost of a
# query is derived from a DRY-RUN's total_bytes_processed × this rate — NEVER a
# hardcoded "scans N GB" literal (test_no_thirty_gb_lie carries over the guard).
#
# NOTE (review-hardening): BigQuery on-demand pricing is quoted per *TiB* (2^40 bytes,
# ~1.0995e12). This module uses a *decimal* TB (1e12) as the conversion unit, which is
# deliberately CONSERVATIVE in both gate directions: it over-estimates the dry-run cost
# by ~10% (aborts sooner) AND caps `maximum_bytes_billed` ~10% lower (bills fewer bytes).
# Do NOT "correct" _BYTES_PER_TB to 2^40 on the strength of the TiB price label — that
# would LOOSEN both caps ~10%. The conservative decimal unit is the safe choice.
_DEFAULT_USD_PER_TB = 6.25
_BYTES_PER_TB = 1_000_000_000_000  # decimal TB (conservative vs the 2^40 TiB unit — see note


def _env_float(key: str, default: float) -> float:
    """Parse a float env var, falling back to ``default`` on a missing/malformed value
    (a typo'd PHASE_P_* env must not crash dataset construction)."""
    raw = os.environ.get(key)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except TypeError, ValueError:
        logger.warning("%s=%r is not a valid float — using default %s", key, raw, default)
        return default


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except TypeError, ValueError:
        logger.warning("%s=%r is not a valid int — using default %s", key, raw, default)
        return default


# AD-6 admin-opt-in defaults (env-overridable). Phase P NEVER runs on a default
# schedule; unless PHASE_P_ENABLED=1 the dataset no-ops (mode-machine _phase_p_skip).
_DEFAULT_MAX_COST_USD = 10.0
_DEFAULT_MAX_COST_FIRST_PULL_USD = 100.0
_DEFAULT_JOB_TIMEOUT_MS = 600_000


class PhasePCostAbort(PyforgeError, RuntimeError):
    """Raised by the free dry-run preflight when the estimated query cost exceeds the
    configured cap (``PHASE_P_MAX_COST_USD`` / ``PHASE_P_MAX_COST_FIRST_PULL_USD``).
    The estimate ALWAYS cites the dry-run's ``total_bytes_processed`` — never a
    literal (the two-layer cost gate is not a lie; test_no_thirty_gb_lie guards it).

    Story 14.3, SPEC-pyforge-core CAP-5: gains ``PyforgeError`` as an
    additional base -- ``RuntimeError`` stays in the MRO."""

    def __init__(self, est_usd: float, cap_usd: float, bytes_processed: int) -> None:
        super().__init__(
            f"Phase P dry-run preflight aborted: estimated ${est_usd:.2f} "
            f"(from a dry-run scanning {bytes_processed} bytes) exceeds cap ${cap_usd:.2f}"
        )
        self.est_usd = est_usd
        self.cap_usd = cap_usd
        self.bytes_processed = bytes_processed


class BigQueryDownloadsDataset(AbstractDataset):
    """Phase P ``pypi.file_downloads`` BigQuery source, owning the **two-layer cost
    gate** (THE CRUX). ``pypi_bigquery_downloads_raw`` (interim api.APIDataset in the
    catalog; this class is authored + fixture-tested here, credentialed materialization
    is attended-only per NFR-2 / AD-11 — google-cloud-bigquery is not in the lean env).

    **Two-layer cost gate** (spec:253-261; CFA:7606-7753):
      1. Free **dry-run preflight** — estimate ``total_bytes_processed`` (dry_run=True,
         use_query_cache=False) → USD; abort above ``PHASE_P_MAX_COST_USD``
         (default 10) / ``PHASE_P_MAX_COST_FIRST_PULL_USD`` (default 100).
      2. Server-side hard cap — ``maximum_bytes_billed = int((cap_usd/usd_per_tb)*1e12)``
         + ``job_timeout_ms`` from ``PHASE_P_JOB_TIMEOUT_MS`` (default 600000).

    **D1 divergence — follow the CODE, not the spec prose.** Queries use literal
    ``TIMESTAMP`` bounds on the ``timestamp`` column — NOT ``_PARTITIONDATE`` (the
    table is column-partitioned on ``timestamp``; ``_PARTITIONDATE`` raises
    ``Unrecognized name: _PARTITIONDATE``, verified live 2026-06-12, CFA:7690-7705).

    **AD-6 admin-opt-in, never a default schedule.** If ``PHASE_P_ENABLED`` is unset
    the dataset no-ops (returns an empty frame / ``None`` — the mode-machine
    ``_phase_p_skip``); the ``fetch_pypi_downloads`` node then no-ops.

    **No inline IO.** This class NEVER imports ``google.cloud.bigquery`` (it is on the
    A2 no-inline-IO denylist AND absent from the lean env). The BigQuery ``client`` is
    INJECTED; the lean gate stubs it, credentialed runs pass a real client at the
    attended B4 event. The client contract is duck-typed:
    ``client.query(sql, job_config=...) -> job`` with ``job.total_bytes_processed`` on
    a dry-run and ``job.result().to_dataframe()`` on a real run; ``make_job_config`` is
    an injected factory that builds the vendor ``QueryJobConfig`` (kept out of this
    module so no bigquery symbol is imported here).
    """

    def __init__(
        self,
        *,
        query_template: str,
        client: Any | None = None,
        make_job_config: Callable[..., Any] | None = None,
        usd_per_tb: float | None = None,
        max_cost_usd: float | None = None,
        max_cost_first_pull_usd: float | None = None,
        job_timeout_ms: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._query_template = query_template
        self._client = client
        self._make_job_config = make_job_config
        self.metadata = metadata
        self._usd_per_tb = (
            usd_per_tb if usd_per_tb is not None else _env_float("PHASE_P_USD_PER_TB", _DEFAULT_USD_PER_TB)
        )
        # A non-positive price would make every cost 0 (bypassing the abort) and blow up
        # maximum_bytes_billed with a ZeroDivisionError — reject it at construction.
        if self._usd_per_tb <= 0:
            raise ValueError(f"usd_per_tb must be > 0 (got {self._usd_per_tb!r})")
        self._max_cost_usd = (
            max_cost_usd if max_cost_usd is not None else _env_float("PHASE_P_MAX_COST_USD", _DEFAULT_MAX_COST_USD)
        )
        self._max_cost_first_pull_usd = (
            max_cost_first_pull_usd
            if max_cost_first_pull_usd is not None
            else _env_float("PHASE_P_MAX_COST_FIRST_PULL_USD", _DEFAULT_MAX_COST_FIRST_PULL_USD)
        )
        self._job_timeout_ms = (
            job_timeout_ms
            if job_timeout_ms is not None
            else _env_int("PHASE_P_JOB_TIMEOUT_MS", _DEFAULT_JOB_TIMEOUT_MS)
        )

    # -- helpers (pure) ------------------------------------------------------

    @staticmethod
    def is_enabled() -> bool:
        """AD-6: Phase P is admin-opt-in. Only the literal ``"1"`` enables it — any
        other value (incl. ``"true"``, ``"0"``, unset) leaves it OFF, so a typo can
        never trip a $500 BigQuery job on a default schedule."""
        return os.environ.get("PHASE_P_ENABLED") == "1"

    def build_query(self, start_ts: str, end_ts: str) -> str:
        """Render the query with **literal TIMESTAMP bounds on the ``timestamp``
        column** (D1 — the code REJECTS ``_PARTITIONDATE``). ``start_ts``/``end_ts``
        are ISO-8601 UTC literals (e.g. ``2026-01-01 00:00:00 UTC``)."""
        if "_PARTITIONDATE" in self._query_template:
            raise ValueError(
                "Phase P query must NOT reference _PARTITIONDATE (D1: the table is "
                "column-partitioned on `timestamp`; _PARTITIONDATE raises "
                "'Unrecognized name'). Use literal TIMESTAMP bounds on `timestamp`."
            )
        return self._query_template.format(start_ts=start_ts, end_ts=end_ts)

    def estimate_cost_usd(self, bytes_processed: int) -> float:
        """Cost = scanned-bytes (from a DRY RUN) × price-per-TiB. The bytes ALWAYS
        come from a dry-run's ``total_bytes_processed`` — never a hardcoded GB
        literal (test_no_thirty_gb_lie)."""
        return (bytes_processed / _BYTES_PER_TB) * self._usd_per_tb

    def maximum_bytes_billed(self, cap_usd: float) -> int:
        """Server-side hard cap in bytes for a given USD cap (CFA:7743)."""
        return int((cap_usd / self._usd_per_tb) * _BYTES_PER_TB)

    def preflight(self, query: str, *, client: Any | None = None) -> tuple[int, float]:
        """Layer 1 — the FREE dry-run preflight. Returns ``(bytes_processed, est_usd)``
        from a ``dry_run=True, use_query_cache=False`` job (CFA:7709-7717). The
        estimate is derived from the dry-run's ``total_bytes_processed`` (never a
        literal). Raises ``RuntimeError`` if no client / job-config factory is wired."""
        client = client if client is not None else self._client
        if client is None or self._make_job_config is None:
            raise RuntimeError(
                "Phase P preflight needs an injected BigQuery client + make_job_config "
                "factory (credentialed runs are attended-only, NFR-2/AD-11)."
            )
        job_config = self._make_job_config(dry_run=True, use_query_cache=False)
        job = client.query(query, job_config=job_config)
        raw_bytes = job.total_bytes_processed
        # FAIL CLOSED: a dry run that reports no byte estimate cannot be costed, so we
        # must NOT proceed to a (potentially $500) real query — abort instead of
        # crashing on int(None) or silently treating it as $0.
        if raw_bytes is None:
            raise RuntimeError(
                "Phase P dry-run returned no total_bytes_processed — cannot estimate "
                "cost; aborting (fail-closed) rather than issuing an un-costed query."
            )
        bytes_processed = int(raw_bytes)
        return bytes_processed, self.estimate_cost_usd(bytes_processed)

    def run_gated(
        self,
        start_ts: str,
        end_ts: str,
        *,
        first_pull: bool = False,
        client: Any | None = None,
    ) -> Any:
        """Run the two-layer cost gate then (if within cap) the real query. Returns the
        result DataFrame. AD-6: raises if Phase P is not enabled. The cap is the
        first-pull cap on a first pull, else the incremental cap."""
        if not self.is_enabled():
            raise RuntimeError(
                "Phase P is disabled (PHASE_P_ENABLED != '1') — the dataset must not "
                "issue a BigQuery job (AD-6, never a default schedule)."
            )
        client = client if client is not None else self._client
        cap_usd = self._max_cost_first_pull_usd if first_pull else self._max_cost_usd
        query = self.build_query(start_ts, end_ts)
        # Layer 1 — free dry-run preflight.
        bytes_processed, est_usd = self.preflight(query, client=client)
        if est_usd > cap_usd:
            raise PhasePCostAbort(est_usd, cap_usd, bytes_processed)
        # Layer 2 — server-side hard cap + job timeout.
        job_config = self._make_job_config(
            dry_run=False,
            use_query_cache=False,
            maximum_bytes_billed=self.maximum_bytes_billed(cap_usd),
            job_timeout_ms=self._job_timeout_ms,
        )
        job = client.query(query, job_config=job_config)
        return job.result().to_dataframe()

    # -- kedro AbstractDataset API -------------------------------------------

    def load(self) -> Any:
        """AD-6: no-op unless Phase P is enabled (``_phase_p_skip``) — returns
        ``None`` so the ``fetch_pypi_downloads`` node yields no rows. A credentialed
        run drives :meth:`run_gated` explicitly at the attended B4 event."""
        if not self.is_enabled():
            return None
        raise RuntimeError(
            "PHASE_P_ENABLED=1 but no time window was supplied to load(); drive "
            "run_gated(start_ts, end_ts) explicitly (credentialed, attended)."
        )

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is a read-only BigQuery source; it is never saved to.")

    def _describe(self) -> dict[str, Any]:
        return {
            "parameterization": type(self).__name__,
            "usd_per_tb": self._usd_per_tb,
            "max_cost_usd": self._max_cost_usd,
            "max_cost_first_pull_usd": self._max_cost_first_pull_usd,
            "job_timeout_ms": self._job_timeout_ms,
            "enabled": self.is_enabled(),
        }
