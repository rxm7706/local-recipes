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

import logging
import os
import re
from typing import Any, Callable

from kedro.io import AbstractDataset
from kedro_datasets.api import APIDataset

from .rate_limit import DEFAULT_RPS, RateLimitedScheduler

# AUD-ATLAS-022: PyPI / anaconda path segments must be single safe names.
_PROJECT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*\Z")

# AUD-ATLAS-020: BigQuery TIMESTAMP literals interpolated into the query template.
_BQ_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC\Z"
)


def _require_project_path_segment(value: str, *, kind: str) -> str:
    """Return a sanitized path segment or raise ``ValueError`` (AUD-ATLAS-022)."""
    name = str(value).strip().strip("/")
    if not name or "/" in name or "\\" in name or ".." in name or not _PROJECT_NAME_RE.match(name):
        raise ValueError(f"unsafe {kind} name {value!r}: must be a single path segment")
    return name

logger = logging.getLogger(__name__)


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
        raise NotImplementedError(
            f"{type(self).__name__} is a read-only request source; it is never saved to."
        )

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
    """

    def request_path(self, owner: str, name: str) -> str:
        """Build the per-package request path — the parameterization a node may NOT
        perform (AC-2). ``owner`` defaults to ``conda-forge`` in the legacy path."""
        owner_seg = _require_project_path_segment(owner or "conda-forge", kind="owner")
        name_seg = _require_project_path_segment(name, kind="package")
        return f"{self._base_url.rstrip('/')}/{owner_seg}/{name_seg}"


class GitHubRequestDataset(_RequestParameterizedAPIDataset):
    """Per-query GitHub GraphQL/REST request-body source (Phases E.5 / K / N).

    Gap G-2: authored in B1 (E.5/K/N are ``vcs_health`` B1 phases), not B2. One
    dataset = one request body; :meth:`with_query` produces the parameterized
    ``load_args.json`` a node may NOT build (AC-2). The Phase K single-worker 3-RPS
    token bucket + ``Retry-After`` discipline are attached here (dataset level), not
    in the node body. ``vcs_github_api_raw``.
    """

    def with_query(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build the GraphQL POST body for a single query — dataset-owned request
        parameterization (AC-2). Returns the ``load_args.json`` payload; the concrete
        POST fan-out through :attr:`scheduler` is dataset-owned and deferred."""
        body: dict[str, Any] = {"query": query}
        if variables:
            body["variables"] = dict(variables)
        return body


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
        so a stray non-string cell cannot crash the fan-out.

        AUD-ATLAS-022: reject path-like / traversal names before URL composition.
        """
        if name is None:
            raise ValueError("request_path requires a project name, got None")
        safe = _require_project_path_segment(name, kind="pypi project")
        return f"{self._base_url.rstrip('/')}/pypi/{safe}/json"

    def load(self) -> Any:
        """The per-project fan-out is NOT a single-URL load — the DAG must drive it via
        :meth:`load_many` with the resolved actionable project names (credentialed +
        attended, NFR-2/AD-11). Raise a clear error rather than silently fetch the bare
        base URL (which is not a valid ``/pypi/<name>/json`` endpoint). B2 wires the
        DW-B1-2 ``acquire()`` into :meth:`load_many` / :meth:`fetch_one`; the concrete
        DAG-load fan-out (resolving names -> N gated requests) is dataset-owned +
        attended, mirroring B1's deferral of the anaconda/github fan-out."""
        raise NotImplementedError(
            "PyPIJsonRequestDataset is a per-project fan-out source: drive it via "
            "load_many(names) (the scheduler-gated per-project loop), not a single "
            "load(). Credentialed live fan-out is attended-only (NFR-2/AD-11)."
        )

    def load_many(
        self, names: list[str], *, fetcher: Callable[[str], Any] | None = None
    ) -> dict[str, Any]:
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
    except (TypeError, ValueError):
        logger.warning("%s=%r is not a valid float — using default %s", key, raw, default)
        return default


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        logger.warning("%s=%r is not a valid int — using default %s", key, raw, default)
        return default

# AD-6 admin-opt-in defaults (env-overridable). Phase P NEVER runs on a default
# schedule; unless PHASE_P_ENABLED=1 the dataset no-ops (mode-machine _phase_p_skip).
_DEFAULT_MAX_COST_USD = 10.0
_DEFAULT_MAX_COST_FIRST_PULL_USD = 100.0
_DEFAULT_JOB_TIMEOUT_MS = 600_000


class PhasePCostAbort(RuntimeError):
    """Raised by the free dry-run preflight when the estimated query cost exceeds the
    configured cap (``PHASE_P_MAX_COST_USD`` / ``PHASE_P_MAX_COST_FIRST_PULL_USD``).
    The estimate ALWAYS cites the dry-run's ``total_bytes_processed`` — never a
    literal (the two-layer cost gate is not a lie; test_no_thirty_gb_lie guards it)."""

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
            job_timeout_ms if job_timeout_ms is not None else _env_int("PHASE_P_JOB_TIMEOUT_MS", _DEFAULT_JOB_TIMEOUT_MS)
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
        are ISO-8601 UTC literals (e.g. ``2026-01-01 00:00:00 UTC``).

        AUD-ATLAS-020: bounds are validated before ``str.format`` interpolation so a
        caller cannot inject SQL via the timestamp slots.
        """
        if "_PARTITIONDATE" in self._query_template:
            raise ValueError(
                "Phase P query must NOT reference _PARTITIONDATE (D1: the table is "
                "column-partitioned on `timestamp`; _PARTITIONDATE raises "
                "'Unrecognized name'). Use literal TIMESTAMP bounds on `timestamp`."
            )
        for label, value in (("start_ts", start_ts), ("end_ts", end_ts)):
            if not isinstance(value, str) or not _BQ_TIMESTAMP_RE.match(value):
                raise ValueError(
                    f"Phase P {label} must be an ISO-UTC literal "
                    f"'YYYY-MM-DD HH:MM:SS UTC', got {value!r}"
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
        raise NotImplementedError(
            f"{type(self).__name__} is a read-only BigQuery source; it is never saved to."
        )

    def _describe(self) -> dict[str, Any]:
        return {
            "parameterization": type(self).__name__,
            "usd_per_tb": self._usd_per_tb,
            "max_cost_usd": self._max_cost_usd,
            "max_cost_first_pull_usd": self._max_cost_first_pull_usd,
            "job_timeout_ms": self._job_timeout_ms,
            "enabled": self.is_enabled(),
        }
