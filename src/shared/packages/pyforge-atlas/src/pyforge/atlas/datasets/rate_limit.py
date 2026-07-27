"""Rate-limit + fetch discipline — a DATASET/RESOURCE concern, never a node body.

Story B1 (THE CRUX — the whole migration's thesis): Phase K's 3-RPS token bucket,
Phase F's provenance fetches, ``Retry-After`` + jittered backoff, and per-registry
concurrency caps are, in the legacy monolith (``conda_forge_atlas.py`` @ b18cbb5),
imperative code *inside* the phase functions. They CANNOT live in a pure node body
(``tests/catalog/test_no_inline_io.py`` structurally bans HTTP/DB clients across the
whole package). Per AD-2 / AD-5 / AD-13 the fetching + rate-limiting move into the
catalog request datasets (``request_datasets.py``) or an injected fetcher-client
passed to a node as a catalog input; the node body stays pure and receives
already-fetched DataFrames (or a client handle whose IO is dataset-owned).

This module carries the pure, IO-free pieces of that discipline so the *contract*
(single-worker 3 RPS, ``PHASE_K_AGGRESSIVE`` opt-out, ``Retry-After`` parsing) is
FIXTURE-TESTED against a stubbed/injected client, NEVER a live endpoint (AD-10 /
AD-11). NOTHING here imports an HTTP/DB client — the token bucket is pure time-math
(clock + sleep are injectable) and ``FetcherClient`` is a typing ``Protocol``; the
concrete HTTP implementation is dataset-owned (``request_datasets.py`` composes
``kedro_datasets.api.APIDataset``).

Legacy provenance (cf-atlas-legacy ``references/engineering-contracts.md`` § "Phase K
scheduler", all citations @ b18cbb5):
- ``class _RateLimitedScheduler`` CFA:1345; single-worker default CFA:1344/1352-1353;
  ctor ``(rps, bucket_capacity=10)`` CFA:1358; refill ``bucket + elapsed*rps`` CFA:1393;
  wait CFA:1397; default 3.0 RPS ("~3x safety margin") CFA:1333.
- ``PHASE_K_AGGRESSIVE=1`` → ``ThreadPoolExecutor(max_workers=8)`` CFA:1340/5077/5132;
  non-"1" values do NOT re-arm burst CFA:5114-5115.
- ``_parse_retry_after`` CFA:2668 (in CFA, NOT ``_http.py``).
"""

from __future__ import annotations

import logging
import math
import threading
import time
from datetime import timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

# Phase K default request rate. 3.0 RPS is the legacy "~3x safety margin" against
# GitHub's *secondary* (burst) rate limit, which is invisible to /rate_limit
# (CFA:1333). Host-agnostic — GitHub / GitLab / Codeberg all share one scheduler.
DEFAULT_RPS = 3.0
DEFAULT_BUCKET_CAPACITY = 10

# Worker counts. The single-worker default is the whole point of the token bucket;
# PHASE_K_AGGRESSIVE=1 (EXACTLY "1") restores 8 workers. Any other value (incl.
# "true", "0", "yes") does NOT re-arm burst mode (CFA:5114-5115) — a deliberate
# fail-safe so a typo cannot silently trip the secondary rate limit.
SINGLE_WORKER = 1
AGGRESSIVE_WORKERS = 8

# Retry-After hard cap + jitter band (engineering-contracts § Phase K; CFA:2668
# consumed with a hard cap + ±25% jitter). Kept as module constants so the
# request datasets and the fixtures agree on one source of truth.
RETRY_AFTER_CAP_SECONDS = 60.0
RETRY_AFTER_JITTER = 0.25


def resolve_worker_count(aggressive_env: str | None) -> int:
    """Map ``PHASE_K_AGGRESSIVE`` to a worker count.

    Returns :data:`AGGRESSIVE_WORKERS` (8) only when ``aggressive_env`` is EXACTLY
    the string ``"1"``; every other value (including ``"true"``, ``"0"``, ``None``,
    whitespace) yields :data:`SINGLE_WORKER` (1). This mirrors the legacy fail-safe
    (CFA:5114-5115) — a non-``"1"`` opt-out must not accidentally re-arm burst mode.
    """
    if aggressive_env == "1":
        return AGGRESSIVE_WORKERS
    if aggressive_env not in (None, "", "0"):
        logger.warning(
            "PHASE_K_AGGRESSIVE=%r is not the literal '1' — burst mode is NOT "
            "re-armed (single-worker 3 RPS stays in effect).",
            aggressive_env,
        )
    return SINGLE_WORKER


def parse_retry_after(value: str | int | float | None, *, now: float | None = None) -> float:
    """Parse an HTTP ``Retry-After`` header value into a wait in seconds.

    Accepts the two RFC 7231 forms — delta-seconds (``"30"``) or an HTTP-date
    (``"Wed, 21 Oct 2026 07:28:00 GMT"``) — and returns a non-negative wait,
    hard-capped at :data:`RETRY_AFTER_CAP_SECONDS`. An unparseable / missing value
    yields ``0.0`` (caller falls back to its own backoff). ``now`` (epoch seconds)
    is injectable so the HTTP-date branch is deterministic under test. Legacy:
    ``_parse_retry_after`` CFA:2668 — note it lives in CFA, not ``_http.py``.
    """
    if value is None:
        return 0.0
    # delta-seconds form
    try:
        secs = float(value)
        if math.isnan(secs) or math.isinf(secs):
            return 0.0
        return max(0.0, min(secs, RETRY_AFTER_CAP_SECONDS))
    except (TypeError, ValueError):
        pass
    # HTTP-date form
    try:
        target = parsedate_to_datetime(str(value))
    except (TypeError, ValueError):
        return 0.0
    if target is None:
        return 0.0
    # A naive HTTP-date (no tz / "-0000") would make `.timestamp()` assume LOCAL time
    # and skew the wait by the local UTC offset — RFC 7231 dates are UTC, so pin it.
    if target.tzinfo is None:
        target = target.replace(tzinfo=timezone.utc)
    now = time.time() if now is None else now
    delta = target.timestamp() - now
    return max(0.0, min(delta, RETRY_AFTER_CAP_SECONDS))


class RateLimitedScheduler:
    """Single-worker token bucket enforcing a fixed request rate (Phase K).

    Pure time-math: ``clock`` and ``sleep`` are injectable so the discipline is
    fixture-tested against a stubbed clock with NO real waiting and NO network
    (AD-10 / AD-11). Refill is continuous — ``tokens = min(capacity, tokens +
    elapsed * rps)`` (CFA:1393) — and :meth:`acquire` blocks (via the injected
    ``sleep``) only until one token is available (CFA:1397).

    Parameters
    ----------
    rps:
        Requests per second (default :data:`DEFAULT_RPS` = 3.0).
    bucket_capacity:
        Burst budget (default :data:`DEFAULT_BUCKET_CAPACITY` = 10).
    clock / sleep:
        Injected time source + sleeper (default ``time.monotonic`` / ``time.sleep``).
    """

    def __init__(
        self,
        rps: float = DEFAULT_RPS,
        bucket_capacity: int = DEFAULT_BUCKET_CAPACITY,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if rps <= 0:
            raise ValueError(f"rps must be > 0; got {rps!r}")
        if bucket_capacity <= 0:
            raise ValueError(f"bucket_capacity must be > 0; got {bucket_capacity!r}")
        self.rps = float(rps)
        self.capacity = int(bucket_capacity)
        self._clock = clock
        self._sleep = sleep
        # Start full so a burst up to `capacity` is allowed before throttling kicks
        # in (legacy default — the bucket begins at capacity, CFA:1352-1353).
        self._tokens = float(bucket_capacity)
        self._last = clock()
        self._lock = threading.Lock()

    @property
    def tokens(self) -> float:
        with self._lock:
            return self._tokens

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._last
        if elapsed > 0:
            self._tokens = min(self.capacity, self._tokens + elapsed * self.rps)
            self._last = now

    def acquire(self, n: int = 1) -> float:
        """Consume ``n`` tokens, sleeping (via the injected sleeper) until they are
        available. Returns the total seconds slept (0.0 when tokens were ready)."""
        if n <= 0:
            return 0.0
        if n > self.capacity:
            # The bucket refills only up to `capacity`, so a request larger than the
            # bucket could never be satisfied — guard against the infinite wait.
            raise ValueError(
                f"cannot acquire {n} tokens from a bucket of capacity {self.capacity}"
            )
        slept = 0.0
        stalls = 0
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= n:
                    self._tokens -= n
                    return slept
                deficit = n - self._tokens
                wait = deficit / self.rps
            before = self._clock()
            self._sleep(wait)
            slept += wait
            # Code ceiling (DW-B1-2): tokens refill only as the clock advances, so a
            # FROZEN clock + a NO-OP sleep would spin this loop forever (the coupling
            # the docstring warns about). If the injected sleep did not advance the
            # clock, count a stall and RAISE after 2 consecutive stalls rather than
            # hang. A real clock (or an advancing fake clock) advances after sleep, so
            # legitimate slow refills never trip this.
            if self._clock() <= before:
                stalls += 1
                if stalls >= 2:
                    raise RuntimeError(
                        "RateLimitedScheduler.acquire cannot make progress: the clock "
                        "did not advance after sleep (frozen clock + no-op sleep). Use "
                        "an advancing clock or bucket_capacity >= n."
                    )
            else:
                stalls = 0


@runtime_checkable
class FetcherClient(Protocol):
    """The injected fetcher-client contract (AD-2).

    A node that needs upstream data receives a ``FetcherClient`` as a catalog input
    (or the request dataset owns one internally). The client encapsulates ALL IO +
    the rate-limit discipline; the node body only calls :meth:`fetch` and transforms
    the returned rows. The concrete HTTP implementation is dataset-owned
    (``request_datasets.py``) and lives OUTSIDE the node — this Protocol carries no
    HTTP import, so a node module referencing it stays clean under the no-inline-IO
    gate.
    """

    def fetch(self, key: str, **params: Any) -> Any:  # pragma: no cover - protocol
        ...


class StubFetcherClient:
    """A deterministic, network-free :class:`FetcherClient` for fixtures (AD-11).

    Records every ``fetch`` call and returns canned responses keyed by ``key``. Used
    to prove the rate-limit + provenance contracts against a stub, never a live
    endpoint. When constructed with a :class:`RateLimitedScheduler`, each ``fetch``
    acquires a token first, so a fixture can assert the scheduler was exercised.
    """

    def __init__(
        self,
        responses: dict[str, Any] | None = None,
        *,
        scheduler: RateLimitedScheduler | None = None,
        raise_status: dict[str, int] | None = None,
    ) -> None:
        self._responses = dict(responses or {})
        self._scheduler = scheduler
        self._raise_status = dict(raise_status or {})
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def fetch(self, key: str, **params: Any) -> Any:
        if self._scheduler is not None:
            self._scheduler.acquire()
        self.calls.append((key, dict(params)))
        status = self._raise_status.get(key)
        if status is not None:
            raise FetchError(key, status)
        return self._responses.get(key)


class FetchError(RuntimeError):
    """Raised by a fetcher on a non-success status (e.g. GitHub 403 secondary
    rate-limit). Phase K maps a 403 to ``upstream_versions.last_error`` and re-picks
    the row via the TTL bypass — that mapping is a *node/transform* concern and is
    fixture-tested in the K node suite."""

    def __init__(self, key: str, status: int) -> None:
        super().__init__(f"fetch({key!r}) failed with status {status}")
        self.key = key
        self.status = status
