"""Story 9.1 — `get_master_dataset()`: AD-5's cache invariant, single-flight.

A thin wrapper over `django.core.cache`: fetches and caches the MASTER
(unfiltered) dataset only. Role-filtering is entirely the caller's job,
applied to what this function returns, after it leaves the cache — this
module never accepts a role, never filters, and never writes a role-scoped
key or a role-filtered value back to the cache backend (CAP-2 / AD-5).

Concurrent misses for the same cache key collapse to one upstream `fetch()`
call — for as long as the lock below is held, which is `lock_timeout`. The
primitive is `cache.add()` — acquire-if-absent — used as a lock: the first
caller to `add()` the lock key wins the right to call `fetch()` and populate
the real key; every other concurrent caller polls until either the value
appears or the lock is released without one (the fetcher raised), in which
case it races again to become the new fetcher rather than waiting forever.

That is a bound, not an absolute (stated plainly in review pass 3 — the
opening claim here used to read "exactly one" unconditionally, which the
`lock_timeout` paragraph further down then contradicted). A `fetch()` that
runs longer than `lock_timeout` loses its exclusive claim partway through, so
concurrent callers issue roughly `fetch_duration / lock_timeout` fetches
rather than one: measured at 3 fetches for a 3s fetch under `lock_timeout=1`.
The lock is never extended or heartbeated and the retry loop has no attempt
cap, so sizing `lock_timeout` above the real fetch's ceiling is load-bearing,
not advisory. The suite pins the fast-fetch case only.

How well that holds depends on the backend, and the honest statement is
narrower than "atomic everywhere" (corrected in review pass 2, which
disproved the original claim by execution):

* `LocMemCache` and a Redis backend do provide an atomic `add()`, so
  single-flight holds — in-process for the former, cross-process for the
  latter.
* `FileBasedCache.add()` is an unlocked check-then-set, so concurrent
  processes can both win.
* `DummyCache.add()` returns `True` unconditionally and stores nothing, so
  EVERY caller "wins" and `fetch()` runs on every call. Caching is off by
  definition there, so this degrades rather than breaks, but it degrades
  silently.

Choosing a backend that can actually carry the property — and refusing one
that cannot when the deployment runs more than one worker, which is AD-5's
other half — is the deployment perimeter's job (Story 9.5), not this
module's; see
``_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md``
(the tracked ledger — review pass 3; this used to name the gitignored
run-local `deferred-work.md`, a path absent from every clone).

Each acquisition writes a random, per-call token as the lock's value and
only deletes the lock if it still holds that same token (review pass 1):
without this, a `fetch()` slower than `lock_timeout` lets the lock expire
mid-fetch, a second caller acquires a *new* lock and starts its own
`fetch()`, and the *first* caller's `finally` then deletes the *second*
caller's still-active lock -- defeating the single-flight guarantee for any
fetch slower than the timeout. `lock_timeout` is caller-set specifically so
it can be sized above the real fetch's expected ceiling.

That compare-before-delete narrows the window but does not close it: `get`
then `delete` are two round trips, and a lock that expires and is re-acquired
between them is still deleted by the wrong owner. Closing it needs an atomic
compare-and-delete (e.g. a Redis Lua script), which Django's cache API does
not expose — deferred with the backend decision above rather than papered
over here.

This function is synchronous and its waiter path sleeps. Calling it from an
async consumer blocks that worker's whole event loop for the duration; an
async variant belongs with the story that first puts it on an async hot path
(see the tracked deferred-work ledger named above).
"""

from __future__ import annotations

import secrets
import time
from typing import Callable, TypeVar

from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache

T = TypeVar("T")

_LOCK_KEY_PREFIX = "dashboard-fetch-lock:"
_DEFAULT_LOCK_TIMEOUT_SECONDS = 30
_POLL_INTERVAL_SECONDS = 0.05

_MISSING = object()  # sentinel: distinguishes "not cached" from "cached None"


def get_master_dataset(
    key: str,
    fetch: Callable[[], T],
    *,
    cache: BaseCache,
    timeout: object = DEFAULT_TIMEOUT,
    lock_timeout: int = _DEFAULT_LOCK_TIMEOUT_SECONDS,
) -> T:
    """Return the master dataset cached under `key`, fetching it at most once.

    ``cache`` is an explicit `django.core.cache` backend instance (e.g.
    `django.core.cache.cache`, or one of `django.core.cache.caches[alias]`)
    — never defaulted implicitly, so a caller cannot accidentally reach for
    an unconfigured Django cache framework. ``fetch`` is called with no
    arguments and must return the master (unfiltered) dataset -- including
    ``None``, a legitimate value distinguished from "not yet cached" by a
    sentinel, never by identity/``None`` comparison; its return value is the
    only thing ever written to `cache` under `key`. ``lock_timeout`` must
    exceed how long ``fetch`` can realistically take: a fetch slower than
    ``lock_timeout`` still runs to completion and still caches correctly,
    but no longer holds an exclusive claim to do so for its full duration.
    It must be a positive integer: Django reads ``0`` as "expire immediately"
    (so `add()` stores nothing and every caller wins the lock, silently
    voiding single-flight) and ``None`` as "cache forever" (so a hard-killed
    fetcher leaves a lock no timeout ever clears). Both are rejected here
    rather than discovered in production (review pass 2).

    ``timeout`` is the DATA TTL, passed straight to ``cache.set``, so it
    follows Django's own conventions: the ``DEFAULT_TIMEOUT`` sentinel (use
    the backend's configured default), ``None`` (cache forever), or a number
    of seconds. Only the TYPE is checked here (review pass 3) — an unusable
    type such as ``"300"`` previously raised a `TypeError` from deep inside
    the backend AFTER ``fetch()`` had already run and its result had been
    thrown away, which is the same "validate at the boundary" argument the
    ``lock_timeout`` guard above already makes. ``timeout=0`` is deliberately
    still allowed: Django reads it as "expire immediately", i.e. the caller
    explicitly disabling caching, which is their call to make.
    """
    if not isinstance(lock_timeout, int) or isinstance(lock_timeout, bool) or lock_timeout <= 0:
        raise ValueError(
            f"lock_timeout must be a positive integer number of seconds, got "
            f"{lock_timeout!r} — 0 disables the lock entirely (every caller "
            f"wins) and None makes it immortal (a dead fetcher blocks every "
            f"waiter forever)"
        )

    if timeout is not DEFAULT_TIMEOUT and timeout is not None and not isinstance(timeout, (int, float)):
        raise TypeError(
            f"timeout must be DEFAULT_TIMEOUT, None, or a number of seconds, "
            f"got {timeout!r} — anything else raises from inside the cache "
            f"backend only AFTER fetch() has run and its result been discarded"
        )

    lock_key = f"{_LOCK_KEY_PREFIX}{key}"

    while True:
        hit = cache.get(key, _MISSING)
        if hit is not _MISSING:
            return hit

        token = secrets.token_hex(16)
        if cache.add(lock_key, token, timeout=lock_timeout):
            try:
                value = fetch()
                # A cache WRITE failure must not destroy a successful fetch
                # (review pass 3). The data is already in hand; failing the
                # whole request because the accelerator blipped is strictly
                # worse than returning uncached data. Same reasoning as the
                # release guard below — with the same limit: a persistent
                # write failure degrades to a fetch per call, silently.
                # (A blip on the READ or the lock `add()` above still
                # propagates; making the cache wholly optional is a failure-
                # semantics decision tied to the deferred backend choice.)
                try:
                    cache.set(key, value, timeout=timeout)
                except Exception:  # noqa: BLE001 -- a cache miss beats an outage
                    pass
                return value
            finally:
                # Only release the lock if it is still the one THIS call
                # acquired -- otherwise it already expired and was
                # re-acquired by another caller, and deleting it here would
                # release a lock this call never held.
                #
                # Wrapped because an exception raised in a `finally` REPLACES
                # whatever was in flight (review pass 2): a backend blip here
                # would otherwise mask a real `fetch()` error, or turn an
                # already-cached success into a failure. A lock we could not
                # release just expires on its own.
                try:
                    if cache.get(lock_key) == token:
                        cache.delete(lock_key)
                except Exception:  # noqa: BLE001 -- never mask the real outcome
                    pass

        # Someone else holds the lock and is fetching. Wait for either the
        # value to appear or the lock to be released (fetcher finished,
        # successfully or not) -- then loop back to the top: re-check the
        # key, and if it is still absent (the other fetcher raised or its
        # lock merely expired), race to become the new fetcher ourselves
        # rather than waiting forever.
        while cache.get(lock_key) is not None:
            hit = cache.get(key, _MISSING)
            if hit is not _MISSING:
                return hit
            time.sleep(_POLL_INTERVAL_SECONDS)
