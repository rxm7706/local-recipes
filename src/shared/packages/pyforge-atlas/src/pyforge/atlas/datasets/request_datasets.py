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
import time
from collections.abc import Callable, Sequence
from typing import Any

import pandas as pd
from kedro.io import AbstractDataset
from kedro_datasets.api import APIDataset
from pyforge.core.errors import PyforgeError

from .basilisk import chunk_queries
from .rate_limit import DEFAULT_RPS, RateLimitedScheduler
from .refresh import (
    DEFAULT_REFRESH_MAX_RETRIES,
    DEFAULT_REFRESH_TIMEOUT_SECONDS,
    MappingCacheDataset,
    RefreshRequest,
)
from .vcs_sources import _ParquetRefreshStore, _retry_backoff_seconds

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


def _coerce_api_json(raw: Any) -> Any:
    """``APIDataset.load()`` returns a ``requests.Response`` for JSON endpoints."""
    if hasattr(raw, "json") and callable(raw.json):
        try:
            return raw.json()
        except Exception:  # noqa: BLE001 — malformed body stays as-is for callers
            return raw
    return raw


_DEFAULT_PYPI_JSON_FANOUT_LIMIT = 200


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
        coupling note on the class docstring."""
        self.scheduler.acquire()
        if fetcher is not None:
            return fetcher(request_key)
        return self._inner.load()

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
    )

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

    def _fetch_batch_with_retry(
        self,
        chunk: Sequence[tuple[str, str]],
        *,
        fetcher: Callable[[dict[str, Any]], Any] | None = None,
    ) -> tuple[Any, Exception | None]:
        """One chunk's batched POST, retried up to ``max_retries`` times. The
        rate-limit token is acquired on EVERY attempt (review fix #3/#4 — mirrors
        ``VcsHostSeedDataset.fetch_one``), with a short injectable backoff between
        retries. Building the query lives INSIDE the try (review finding) so a
        query-build failure degrades the same way a network failure does. Returns
        ``(payload, None)`` on success or ``(None, exc)`` after exhausting retries —
        never raises (AD-13)."""
        attempt = 0
        while True:
            try:
                self.scheduler.acquire()
                body = self.build_batch_query(chunk)
                if fetcher is not None:
                    return fetcher(body), None
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
                if attempt > self._max_retries:
                    return None, exc
                self._sleep(_retry_backoff_seconds(attempt))

    def fetch_repo_health(
        self,
        repos: Sequence[tuple[str, str]],
        *,
        fetcher: Callable[[dict[str, Any]], Any] | None = None,
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
        for chunk in chunk_queries(list(repos), GITHUB_BATCH_QUERY_MAX):
            payload, exc = self._fetch_batch_with_retry(chunk, fetcher=fetcher)
            if exc is not None:
                logger.warning("GitHub batch fetch failed, keeping last-good: %s", exc)
                for owner, name in chunk:
                    rows.append(
                        {
                            "feedstock_name": name,
                            "conda_name": pd.NA,
                            "archived": pd.NA,
                            "upstream_version": pd.NA,
                            "last_error": f"batch fetch failed: {type(exc).__name__}: {exc}",
                            "stars": pd.NA,
                            "last_commit": pd.NA,
                            "open_issues": pd.NA,
                        }
                    )
                continue
            data = payload.get("data") if isinstance(payload, dict) else None
            for i, (owner, name) in enumerate(chunk):
                repo = data.get(f"r{i}") if isinstance(data, dict) else None
                if not isinstance(repo, dict):
                    rows.append(
                        {
                            "feedstock_name": name,
                            "conda_name": pd.NA,
                            "archived": pd.NA,
                            "upstream_version": pd.NA,
                            "last_error": "repository not found in response",
                            "stars": pd.NA,
                            "last_commit": pd.NA,
                            "open_issues": pd.NA,
                        }
                    )
                    continue
                issues = repo.get("issues") if isinstance(repo.get("issues"), dict) else {}
                rows.append(
                    {
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
        self._persist(frame if has_success else empty)
        return frame

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
        if not data.force and not self._refresh_due(data.cadence_seconds):
            self._clear_stale()
            return
        # Story 21.2 scope: no production repo-identifier source is wired yet; an
        # empty batch makes zero network calls and degrades cleanly to keep-last-good
        # + mark stale (AD-13, review fix #2). Real identifier wiring is deferred to
        # Story 21.6 (upstream_discovery identity join).
        self.fetch_repo_health(())


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
        inner = APIDataset(
            url=url,
            method=self._method,
            load_args=self._load_args,
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
        for name in names:
            if name is None or (isinstance(name, float) and name != name):  # None / NaN
                continue
            key = self.request_path(name)
            out[name] = self.fetch_one(key, fetcher=fetcher)
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

    def _candidate_names(self) -> tuple[list[str], dict[str, str]]:
        try:
            mapping = self._mapping_cache.load()
        except Exception as exc:  # never raise: degrade to an empty candidate set.
            logger.warning("pypi_conda_map_store unreadable, degrading to empty: %s", exc)
            mapping = {}
        if not isinstance(mapping, dict):
            mapping = {}
        # review fix #12: filter BOTH key and value to real strings (matches
        # ParselmouthMappingDataset's filter) — a malformed entry must not crash the
        # fan-out or surface a non-string conda_name downstream.
        names = sorted(k for k, v in mapping.items() if isinstance(k, str) and k and isinstance(v, str))
        return names, mapping

    def fetch_candidates(self, *, fetcher: Callable[[str], Any] | None = None) -> pd.DataFrame:
        """The real per-project fan-out (Story 21.2, dataset-owned IO, AD-2): bounded
        by ``PYPI_JSON_FANOUT_LIMIT`` (``0`` explicitly disables it this cycle —
        review fix #7). Persists through the AD-13 last-good pattern; :meth:`load_many`
        (KEEP as-is) does the actual per-project requests — this method only sources
        the candidate list and persists the result."""
        empty = pd.DataFrame(columns=list(self._COLUMNS))
        limit = _pypi_json_fanout_limit()
        if limit == 0:
            self._mark_stale("fan-out disabled this cycle (PYPI_JSON_FANOUT_LIMIT=0)")
            return empty
        names, mapping = self._candidate_names()
        if not names:
            self._persist(empty)
            return empty
        names = names[:limit]
        payloads = self.load_many(names, fetcher=fetcher)
        rows: list[dict[str, Any]] = []
        for name in names:
            row = _payload_to_pypi_json_row(name, payloads.get(name))
            row["conda_name"] = mapping.get(name)
            rows.append(row)
        frame = pd.DataFrame(rows, columns=_PYPI_JSON_FRAME_COLUMNS).reset_index(drop=True)
        self._persist(frame)
        return frame

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
        if not data.force and not self._refresh_due(data.cadence_seconds):
            self._clear_stale()
            return
        self.fetch_candidates()


class PyPIBigQueryDownloadsDataset(AbstractDataset):
    """Catalog entry for ``pypi_bigquery_downloads_raw`` — Phase P admin opt-in stub.

    ``PHASE_P_ENABLED=1`` runs are attended-only (NFR-2/AD-11); the default pipeline
    path returns an empty but correctly-columned frame so ``fetch_pypi_downloads``
    no-ops (AD-6, never a default BigQuery job).
    """

    _COLS = ["pypi_name", "month", "downloads"]

    def __init__(self, *, metadata: dict[str, Any] | None = None, **kwargs: Any) -> None:
        _ = kwargs  # url/credentials kept in catalog for credentialed materialization flip
        self.metadata = metadata

    def load(self) -> pd.DataFrame:
        if BigQueryDownloadsDataset.is_enabled():
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
