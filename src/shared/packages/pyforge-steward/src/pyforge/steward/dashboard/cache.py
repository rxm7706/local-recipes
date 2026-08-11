"""Story 9.1 — `get_master_dataset()`: AD-5's cache invariant, single-flight.

A thin wrapper over `django.core.cache`: fetches and caches the MASTER
(unfiltered) dataset only. Role-filtering is entirely the caller's job,
applied to what this function returns, after it leaves the cache — this
module never accepts a role, never filters, and never derives a role-scoped
key (CAP-2 / AD-5).

The other half of that invariant is a CALLER CONTRACT this module cannot
enforce, stated plainly here in review pass 4 rather than claimed away: it
writes exactly what `fetch()` returned, under exactly the `key` it was
given, so a caller that passes a role-FILTERING closure (or a per-role key)
defeats CAP-2 while every assertion in this module's suite still passes.
Demonstrated: an east-role closure warms `key="master"`, and the next caller
— west role, same key — is served east rows. `fetch` must return the master
frame. Giving the API a shape that cannot be misused this way (taking the
`AccessDeclaration` and deriving the key itself) belongs with Story 9.2, the
first story with a real consumer; it is on the deferred-work ledger.

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
The lock is never extended or heartbeated, so sizing `lock_timeout` above the
real fetch's ceiling is load-bearing, not advisory. The suite pins the
fast-fetch case only. The retry loop has no attempt cap, but since review
pass 4 it does have a wall-clock deadline (`_MAX_WAIT_MULTIPLIER`), so a
caller that can never make progress raises `LockUnavailableError` instead of
waiting forever; bounding the *degradation* itself still needs the backend
decision on the ledger.

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
* `DatabaseCache.add()` can return `False` while storing nothing and while
  reads keep working: Django's `_base_set` ends in a bare
  ``except DatabaseError: return False`` ("to be threadsafe, updates/inserts
  are allowed to fail silently"), so write contention looks identical to
  "someone else holds the lock" — except that nobody does. Review pass 4
  bounds the wait for exactly this case (see `_MAX_WAIT_MULTIPLIER` below);
  before that bound the function could neither acquire nor observe a lock
  and spun without ever returning.

Choosing a backend that can actually carry the property — and refusing one
that cannot when the deployment runs more than one worker, which is AD-5's
other half — is the deployment perimeter's job (Story 9.5), not this
module's; see the deferred-work ledger (drafted run-local and promoted into
``_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md``
when this story lands — see this package's `__init__` docstring; review pass
3 repointed this away from the gitignored run-local path, and pass 4
corrected it from asserting the tracked ledger already carries the entries).

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
(see the deferred-work ledger named above).
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

# A waiter never legitimately waits longer than `lock_timeout`: the lock
# cannot outlive it, so by then either the value is present or the waiter
# races to become the fetcher itself. Waiting twice that without either
# outcome means the backend is not carrying the lock primitive at all (see
# the `DatabaseCache` note in the module docstring), which is a condition to
# report, not to wait out forever. Only the RETRY path is bounded — a fetch
# already in progress in this call is never interrupted.
_MAX_WAIT_MULTIPLIER = 2

_MISSING = object()  # sentinel: distinguishes "not cached" from "cached None"


class LockUnavailableError(RuntimeError):
    """The fetch lock could neither be acquired nor observed to be held.

    Raised only after `_MAX_WAIT_MULTIPLIER * lock_timeout` seconds of that
    state, which no working backend produces: it means `cache.add()` keeps
    reporting failure while the lock key stays unreadable, so this call can
    never make progress. Added in review pass 4, where the same condition
    was an unbounded busy loop instead — no sleep runs on that path, so a
    single call issued ~500k backend operations per second, indefinitely,
    without ever calling `fetch()` (reproduced: 1.1M ops in 2s, 0 fetches).
    Failing loudly beats both spinning and hanging.
    """


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

    ``key`` must not start with the reserved lock-key prefix — data stored
    there would occupy another key's lock slot (review pass 4).

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

    # `bool` excluded here too (review pass 4), for the same reason the
    # `lock_timeout` guard one line above already excludes it: `timeout=False`
    # IS an int to `isinstance`, reaches the backend as `0` — "expire
    # immediately" — and silently caches nothing, which is the very
    # consequence that guard exists to refuse, arrived at by a different door.
    # (`timeout=0` stays deliberately allowed: that is a caller explicitly
    # disabling caching. `False` is not that statement.)
    if (
        timeout is not DEFAULT_TIMEOUT
        and timeout is not None
        and (isinstance(timeout, bool) or not isinstance(timeout, (int, float)))
    ):
        raise TypeError(
            f"timeout must be DEFAULT_TIMEOUT, None, or a number of seconds, "
            f"got {timeout!r} — anything else raises from inside the cache "
            f"backend only AFTER fetch() has run and its result been discarded"
        )

    # The lock namespace is reserved (review pass 4). Review pass 1 moved the
    # lock key from a suffix to this prefix so a caller key could not collide
    # with it — but nothing stopped a caller key from starting WITH it, and
    # `get_master_dataset("dashboard-fetch-lock:sales", ...)` writes a data
    # frame into precisely the slot that is `"sales"`'s lock. A later caller
    # for `"sales"` then reads that frame as a permanently-held lock and
    # never returns (reproduced). Refused at the boundary, where it is one
    # line, rather than diagnosed later as a hang.
    if key.startswith(_LOCK_KEY_PREFIX):
        raise ValueError(
            f"key {key!r} starts with the reserved lock-key prefix "
            f"{_LOCK_KEY_PREFIX!r} — caching data there would occupy another "
            f"key's lock slot and hang every caller waiting on it"
        )

    lock_key = f"{_LOCK_KEY_PREFIX}{key}"
    # Bounds only the WAIT/RETRY path; a fetch started by this call always
    # runs to completion. See `LockUnavailableError`.
    deadline = time.monotonic() + _MAX_WAIT_MULTIPLIER * lock_timeout

    def _lock_unavailable() -> LockUnavailableError:
        return LockUnavailableError(
            f"could not acquire or observe the fetch lock for {key!r} within "
            f"{_MAX_WAIT_MULTIPLIER * lock_timeout}s (lock_timeout="
            f"{lock_timeout}s) — the cache backend is reporting failed "
            f"add()s while the lock key stays unreadable, so this call cannot "
            f"make progress"
        )

    while True:
        hit = cache.get(key, _MISSING)
        if hit is not _MISSING:
            return hit

        token = secrets.token_hex(16)
        if cache.add(lock_key, token, timeout=lock_timeout):
            try:
                # Double-check under the lock (review pass 4) — the second
                # check of double-checked locking, which was missing. Between
                # this call's miss above and its `add()` here, another fetcher
                # can complete and populate `key`; without this re-read we
                # fetch again anyway and then OVERWRITE the fresher value with
                # our own staler one (reproduced). Costs one cache read on the
                # miss path only.
                hit = cache.get(key, _MISSING)
                if hit is not _MISSING:
                    return hit

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
            if time.monotonic() >= deadline:
                raise _lock_unavailable()
            time.sleep(_POLL_INTERVAL_SECONDS)

        # Neither acquired the lock nor observed one held: `add()` reported
        # failure and the lock key reads as absent. Review pass 4 — this is
        # the ONLY path through the outer loop that reaches its top without
        # sleeping, because the sleep above lives inside a loop whose body
        # never runs in this state. A backend that stays in it (Django's
        # `DatabaseCache` under write contention does; see the module
        # docstring) turned this function into an unbounded busy loop that
        # never returned and never fetched — measured at ~500k backend
        # operations per second. Sleep like every other wait, and give up
        # loudly once no working backend could still be explaining it.
        if time.monotonic() >= deadline:
            raise _lock_unavailable()
        time.sleep(_POLL_INTERVAL_SECONDS)
