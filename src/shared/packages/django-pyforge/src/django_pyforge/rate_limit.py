"""Per-subject token buckets for agent traffic (canopy AD-10, red-team A-6).

Nothing rate-limited ``POST /stations/<name>/mcp`` or supervisor ``start``, so a
looping agent could publish a ``RunState`` row and a Celery task per call until
PostgreSQL and the ``noeviction`` broker filled and Channels, Celery and the
event bus died together. Loop-depth caps only bus recursion. Directive **R-8**.

Three properties are load-bearing, and each is a refusal to do the obvious
cheaper thing:

**The subject is the `sub` claim, never a client name.** A client name is
self-asserted and shared; ``sub`` comes from an assertion this host verified,
so one agent's loop cannot consume another caller's allowance and cannot escape
its own by renaming itself.

**State lives in the cache, never on the broker.** ``CACHES[CACHE_ALIAS]`` is
``redis-cache`` in a deployed profile (AD-10) — evictable, ``allkeys-lru``.
Putting limiter keys on ``redis-broker`` would make the limiter a second writer
to the ``noeviction`` instance whose exhaustion it exists to prevent, and an
evicted bucket costs only a caller getting its full allowance again.

**The limiter cannot fail open.** ``django_redis`` runs with
``IGNORE_EXCEPTIONS``, so a connection failure is swallowed into ``None``
rather than raised — which is why this module passes a private sentinel as
``get``'s default: ``None`` back from that call means the store did not answer,
and is refused with an ``ERROR`` log, while the sentinel means "no bucket yet"
and is a full bucket. A backend that raises instead lands in the same branch.
Silently allowing traffic because the cache is down is the one outcome this
module must never produce.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# The Django cache alias carrying limiter state. `default` is redis-cache in
# `config.settings.production` (`django_cache_aliases(REDIS_CACHE_URL)`) and
# LocMemCache on a laptop, where one process is the whole platform.
CACHE_ALIAS = "default"
KEY_PREFIX = "pyforge:ratelimit"

MCP_SCOPE = "mcp"
START_SCOPE = "start"

SECONDS_PER_MINUTE = 60.0

# Documented defaults — every number below is a Django setting, and these are
# what a deployment that names none of them gets. The MCP route carries reads
# (`tools/list`, `get`) as well as writes, so it is the wider of the two; the
# supervisor `start` bucket is deliberately much narrower because each grant
# costs a database row and a queued task.
DEFAULT_MCP_RATE_PER_MINUTE = 120
DEFAULT_MCP_BURST = 120
DEFAULT_START_RATE_PER_MINUTE = 30
DEFAULT_START_BURST = 30

SETTING_MCP_RATE = "MCP_RATE_LIMIT_PER_MINUTE"
SETTING_MCP_BURST = "MCP_RATE_LIMIT_BURST"
SETTING_START_RATE = "SUPERVISOR_START_RATE_PER_MINUTE"
SETTING_START_BURST = "SUPERVISOR_START_BURST"

_SCOPE_SETTINGS: dict[str, tuple[tuple[str, int], tuple[str, int]]] = {
    MCP_SCOPE: (
        (SETTING_MCP_RATE, DEFAULT_MCP_RATE_PER_MINUTE),
        (SETTING_MCP_BURST, DEFAULT_MCP_BURST),
    ),
    START_SCOPE: (
        (SETTING_START_RATE, DEFAULT_START_RATE_PER_MINUTE),
        (SETTING_START_BURST, DEFAULT_START_BURST),
    ),
}

REASON_OK = "ok"
REASON_RATE_LIMITED = "rate-limited"
REASON_CACHE_UNAVAILABLE = "cache-unavailable"
REASON_NO_SUBJECT = "no-subject"

# What a caller waits when the limiter itself could not answer. Short, because
# the refusal is about the platform's own health rather than the caller's rate.
UNAVAILABLE_RETRY_AFTER_SECONDS = 5

# Ceiling on any advertised wait. One token is at most one full refill away, so
# a larger number is a corrupted bucket, not a wait -- and handing it out is a
# lockout dressed as backpressure.
MAX_RETRY_AFTER_SECONDS = 300

# Never `None`: `None` is what a swallowed cache failure returns, and the whole
# fail-closed guarantee is that the two are distinguishable.
_MISSING = object()

_TOKENS_KEY = "tokens"
_AT_KEY = "at"


@dataclass(frozen=True)
class Bucket:
    """One scope's refill rate and depth."""

    scope: str
    rate_per_minute: int
    burst: int

    @property
    def per_second(self) -> float:
        """Refill rate. Floored at one per minute: ``int_setting`` already
        rejects a non-positive rate, but a ``Bucket`` built by hand must not be
        able to turn the limiter into a ``ZeroDivisionError`` -- which would
        take the route down rather than throttle it.
        """
        return max(self.rate_per_minute, 1) / SECONDS_PER_MINUTE

    @property
    def ttl_seconds(self) -> int:
        """Long enough for a drained bucket to refill completely.

        An expired key reads as a full bucket, which is exactly the state a
        fully refilled bucket is in — so expiry loses nothing, and an idle
        subject stops occupying cache memory instead of being kept forever.
        """
        return int(math.ceil(max(self.burst, 1) / self.per_second)) + 60


@dataclass(frozen=True)
class Decision:
    """The limiter's verdict. ``allowed`` is the whole contract."""

    allowed: bool
    scope: str
    subject: str
    reason: str
    retry_after: int
    remaining: float


def int_setting(name: str, default: int) -> int:
    """A positive integer Django setting, or the documented default.

    Zero and negatives are rejected rather than honoured: a zero rate is a
    division by zero, and "block everything" is a deployment decision that
    belongs in a route, not in a silently-misread limit.
    """
    raw = _django_setting(name, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        logger.error(
            "ratelimit.bad_setting",
            extra={"event": "ratelimit.bad_setting", "setting": name},
        )
        return default
    if value <= 0:
        logger.error(
            "ratelimit.bad_setting",
            extra={
                "event": "ratelimit.bad_setting",
                "setting": name,
                "value": value,
            },
        )
        return default
    return value


def _django_setting(name: str, default: Any) -> Any:
    """The Django setting, when a *configured* Django is importable."""
    try:
        from django.conf import settings  # noqa: PLC0415
        from django.core.exceptions import ImproperlyConfigured  # noqa: PLC0415
    except ImportError:
        return default
    try:
        return getattr(settings, name, default)
    except ImproperlyConfigured:
        return default


def bucket_for(scope: str) -> Bucket:
    """The configured bucket for ``scope``. Unknown scopes get the MCP shape."""
    (rate_name, rate_default), (burst_name, burst_default) = _SCOPE_SETTINGS.get(
        scope,
        _SCOPE_SETTINGS[MCP_SCOPE],
    )
    return Bucket(
        scope=scope,
        rate_per_minute=int_setting(rate_name, rate_default),
        burst=int_setting(burst_name, burst_default),
    )


def bucket_key(scope: str, subject: str) -> str:
    return f"{KEY_PREFIX}:{scope}:{subject}"


def limiter_cache() -> Any | None:
    """``CACHES[CACHE_ALIAS]``, or ``None`` when it cannot be resolved."""
    try:
        from django.core.cache import caches  # noqa: PLC0415

        return caches[CACHE_ALIAS]
    except Exception as exc:  # noqa: BLE001 -- any failure here is "no limiter"
        logger.error(
            "ratelimit.cache_unavailable",
            extra={
                "event": "ratelimit.cache_unavailable",
                "alias": CACHE_ALIAS,
                "error": repr(exc),
            },
        )
        return None


def _unavailable(scope: str, subject: str, detail: str) -> Decision:
    """Refuse, loudly. The one thing this module may not do is allow."""
    logger.error(
        "ratelimit.cache_unavailable",
        extra={
            "event": "ratelimit.cache_unavailable",
            "scope": scope,
            "sub": subject,
            "detail": detail,
        },
    )
    return Decision(
        allowed=False,
        scope=scope,
        subject=subject,
        reason=REASON_CACHE_UNAVAILABLE,
        retry_after=UNAVAILABLE_RETRY_AFTER_SECONDS,
        remaining=0.0,
    )


def _unattributable(scope: str) -> Decision:
    """Refuse a call that names no subject. Loud, but not as a cache failure.

    No ``retry_after``: waiting will not give the call a subject, and a
    ``Retry-After`` here would tell a caller to keep trying something that
    cannot succeed.
    """
    logger.error(
        "ratelimit.unattributable",
        extra={"event": "ratelimit.unattributable", "scope": scope},
    )
    return Decision(
        allowed=False,
        scope=scope,
        subject="",
        reason=REASON_NO_SUBJECT,
        retry_after=0,
        remaining=0.0,
    )


def _restore(state: Any, bucket: Bucket, now: float) -> tuple[float, float]:
    """``(tokens, updated_at)`` from stored state; a full bucket when absent.

    Tokens are CLAMPED into ``[0, burst]``. Finiteness alone is not enough: a
    negative reading -- a shrunk ``burst``, a corrupted value, anything that
    ever wrote below zero -- flows straight into
    ``ceil((1 - tokens) / per_second)`` and produces an unbounded
    ``Retry-After``, locking the subject out for as long as the bad number is
    large. The store is shared, evictable and not this module's to trust.
    """
    if state is _MISSING or not isinstance(state, dict):
        return float(bucket.burst), now
    try:
        tokens = float(state[_TOKENS_KEY])
        updated_at = float(state[_AT_KEY])
    except (KeyError, TypeError, ValueError):
        return float(bucket.burst), now
    if not math.isfinite(tokens) or not math.isfinite(updated_at):
        return float(bucket.burst), now
    return min(max(tokens, 0.0), float(bucket.burst)), updated_at


def consume(
    scope: str,
    subject: str,
    *,
    bucket: Bucket | None = None,
    cache: Any | None = None,
    now: float | None = None,
) -> Decision:
    """Spend one token for ``subject`` in ``scope``. Never raises, never allows
    on a cache failure.

    ``now`` is wall clock rather than a monotonic reading on purpose: the bucket
    is shared across web pods through redis-cache, and monotonic clocks are not
    comparable between processes.
    """
    if not subject:
        # An unattributable call cannot be bounded, so it is refused rather
        # than exempted -- a limiter with an unbounded hole is not a limiter.
        # Its own reason and event, not `cache_unavailable`: a missing subject
        # is an attribution fault upstream of this module, and an operator
        # paging on the cache event must not be woken for it.
        return _unattributable(scope)
    limits = bucket if bucket is not None else bucket_for(scope)
    store = cache if cache is not None else limiter_cache()
    if store is None:
        return _unavailable(scope, subject, "cache alias unresolved")
    moment = time.time() if now is None else now
    key = bucket_key(scope, subject)
    try:
        state = store.get(key, _MISSING)
    except Exception as exc:  # noqa: BLE001 -- a raising backend is "down" too
        return _unavailable(scope, subject, f"get failed: {exc!r}")
    if state is None:
        # Not the default we passed: django_redis swallowed a connection
        # failure into None. The store did not answer.
        return _unavailable(scope, subject, "get returned None")
    tokens, updated_at = _restore(state, limits, moment)
    elapsed = max(0.0, moment - updated_at)
    tokens = min(float(limits.burst), tokens + elapsed * limits.per_second)
    allowed = tokens >= 1.0
    if allowed:
        tokens -= 1.0
        retry_after = 0
    else:
        # Bounded as well as clamped: the wait for ONE token can never exceed a
        # full refill of the bucket, so anything larger is arithmetic gone wrong
        # rather than a real wait, and must not be handed to a caller as one.
        wait = int(math.ceil((1.0 - tokens) / limits.per_second))
        retry_after = min(max(1, wait), MAX_RETRY_AFTER_SECONDS)
    try:
        store.set(
            key,
            {_TOKENS_KEY: tokens, _AT_KEY: moment},
            timeout=limits.ttl_seconds,
        )
    except Exception as exc:  # noqa: BLE001 -- an unwritable bucket is no bucket
        return _unavailable(scope, subject, f"set failed: {exc!r}")
    if not allowed:
        logger.warning(
            "ratelimit.refused",
            extra={
                "event": "ratelimit.refused",
                "scope": scope,
                "sub": subject,
                "retry_after": retry_after,
                "rate_per_minute": limits.rate_per_minute,
                "burst": limits.burst,
            },
        )
    return Decision(
        allowed=allowed,
        scope=scope,
        subject=subject,
        reason=REASON_OK if allowed else REASON_RATE_LIMITED,
        retry_after=retry_after,
        remaining=tokens,
    )


def reset(scope: str, subject: str, *, cache: Any | None = None) -> None:
    """Drop one subject's bucket. For tests and operator remediation only."""
    store = cache if cache is not None else limiter_cache()
    if store is None:
        return
    try:
        store.delete(bucket_key(scope, subject))
    except Exception as exc:  # noqa: BLE001 -- best effort by construction
        logger.warning(
            "ratelimit.reset_failed",
            extra={"event": "ratelimit.reset_failed", "error": repr(exc)},
        )
