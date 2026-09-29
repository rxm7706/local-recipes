"""Story 9.1 — `get_master_dataset()` single-flight + no-role-filtered-frame
invariant (AD-5 / CAP-2), proven by a real threaded race against a real
Django `LocMemCache` backend, plus direct inspection of that backend's
contents afterward.
"""

from __future__ import annotations

import threading
import time

import pytest

# `cache.py` is the one module besides `apps.py` that genuinely needs django,
# so without the `[dashboard]` extra this file must SKIP, not raise a
# collection error (review pass 2).
pytest.importorskip("django", reason="cache.py requires pyforge-steward[dashboard]")

from django.conf import settings  # noqa: E402

# Settings may already be configured if this file collects alongside another
# test module that configured them first -- guard so a second `configure()`
# call (which Django refuses) never crashes the run.
#
# Story 9.3 (review pass 1): `INSTALLED_APPS`/`DATABASES` are included here
# too, matching `test_dashboard_audit.py`'s own declaration, even though this
# file's own tests need neither -- `test_dashboard_audit.py` needs both and
# previously claimed its own settings were "a strict superset that satisfies
# both files regardless of which one wins the race," which was false in this
# direction: this block used to set only `CACHES`, so if THIS file ever won
# the one-shot `settings.configure()` race, the audit file's `django.setup()`
# + `migrate` had no app and no database to work with. Making both files'
# declarations mutual supersets closes that regardless of collection order.
# The audit file no longer asserts EXACT equality of `INSTALLED_APPS`
# (review pass 2), so a future addition to this list is no longer a
# collection-order-dependent failure over there -- but the two blocks must
# still agree on the sqlite `NAME`, which that file does hard-assert, since
# it migrates and truncates whatever database is configured.
if not settings.configured:
    settings.configure(
        INSTALLED_APPS=["pyforge.steward.dashboard"],
        DATABASES={
            "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
        },
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "pyforge-steward-dashboard-test",
            },
        },
        USE_TZ=True,
    )

from django.core.cache import caches  # noqa: E402 -- must follow settings.configure()
from django.core.cache.backends.locmem import LocMemCache  # noqa: E402

from pyforge.steward.dashboard.cache import get_master_dataset  # noqa: E402

_LOCK_PREFIX = "dashboard-fetch-lock:"


def _fresh_backend():
    backend = caches["default"]
    # If another module won the `settings.configure()` race above, `default`
    # is ITS backend, not the one declared here -- and this file's raw-store
    # inspection would then raise AttributeError instead of failing an
    # assertion, or silently assert against the wrong backend entirely
    # (review pass 2). Fail loudly and legibly instead.
    assert isinstance(backend, LocMemCache), (
        f"these tests require the LocMemCache declared above, got "
        f"{type(backend).__name__} -- another test module configured Django "
        f"settings first"
    )
    # The isinstance check alone cannot detect the LIKELIEST collision (review
    # pass 3): Django's own default CACHES is ALSO a LocMemCache, so a module
    # that configured settings without CACHES would pass the assertion above
    # while this file's raw-store inspection ran against a different store.
    # Assert the declaration in force is the one at the top of this file.
    assert settings.CACHES["default"].get("LOCATION") == "pyforge-steward-dashboard-test", (
        f"another test module configured Django settings first: CACHES[default] "
        f"is {settings.CACHES['default']!r}, not the backend declared in this file"
    )
    backend.clear()
    return backend


def test_concurrent_cache_miss_collapses_to_one_fetch():
    backend = _fresh_backend()
    key = "master-dataset-concurrency-test"

    call_count = 0
    call_lock = threading.Lock()

    def fetch():
        nonlocal call_count
        with call_lock:
            call_count += 1
        time.sleep(0.2)  # hold the lock long enough for the loser to poll
        return {"rows": [{"region": "east"}, {"region": "west"}]}

    results: dict[str, list] = {}
    errors: list[BaseException] = []

    # A barrier makes contention MANDATORY rather than merely likely (review
    # pass 2). With only a sleep inside `fetch`, a slow-starting second thread
    # could arrive after the first had already finished and still leave
    # call_count == 1 -- so the test passed identically whether or not the
    # two callers ever actually raced, which is the one thing it exists to
    # prove.
    both_ready = threading.Barrier(2, timeout=5)

    def worker(role):
        try:
            both_ready.wait()
            master = get_master_dataset(key, fetch, cache=backend)
            # Role-filtering happens AFTER get_master_dataset returns, by the
            # caller -- never inside the cache layer itself.
            results[role] = [row for row in master["rows"] if row["region"] == role]
        except BaseException as exc:  # noqa: BLE001 -- surfaced by the assert below
            errors.append(exc)

    t1 = threading.Thread(target=worker, args=("east",))
    t2 = threading.Thread(target=worker, args=("west",))
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    # Without these, a deadlock in the polling loop surfaced as an opaque
    # KeyError on `results["east"]` and then hung the interpreter at exit
    # waiting on the still-live non-daemon thread.
    assert not t1.is_alive() and not t2.is_alive(), "a worker deadlocked in get_master_dataset"
    assert not errors, f"worker raised: {errors!r}"

    assert call_count == 1, "concurrent misses on the same key must collapse to exactly one upstream fetch"
    assert results["east"] == [{"region": "east"}]
    assert results["west"] == [{"region": "west"}]


def test_cache_backend_holds_only_the_unfiltered_master_frame():
    backend = _fresh_backend()
    key = "master-dataset-inspection-test"
    master = {"rows": [{"region": "east"}, {"region": "west"}]}

    def fetch():
        return master

    get_master_dataset(key, fetch, cache=backend)

    assert backend.get(key) == master

    # The lock is released once the fetch completes -- it never lingers as a
    # permanent extra entry in the backend.
    assert backend.get(f"{_LOCK_PREFIX}{key}") is None

    # Direct inspection of LocMemCache's own store (not the public `get`/`has_key`
    # API, which can only be asked about a key it is already told to look for):
    # exactly one raw entry exists after the fetch/hit cycle, and it is the
    # declared master key -- proving no role-scoped key/value was ever written
    # alongside it, not merely that the ones we thought to check are absent.
    raw_keys = list(backend._cache.keys())  # noqa: SLF001 -- deliberate direct backend inspection
    assert len(raw_keys) == 1, f"expected exactly the master key in the backend, found {raw_keys!r}"
    assert raw_keys[0].endswith(f":{key}")


def test_none_is_a_valid_cached_value_and_is_not_refetched():
    """A `fetch()` that legitimately returns `None` must still be cached --
    `is not None` (rather than a presence sentinel) would defeat caching for
    this value and re-fetch on every call.
    """
    backend = _fresh_backend()
    key = "master-dataset-none-value-test"
    call_count = 0

    def fetch():
        nonlocal call_count
        call_count += 1
        return None

    first = get_master_dataset(key, fetch, cache=backend)
    second = get_master_dataset(key, fetch, cache=backend)

    assert first is None
    assert second is None
    assert call_count == 1, "a legitimately None master dataset must still be cached, not re-fetched every call"


def test_finally_never_releases_a_lock_it_does_not_own():
    """Proves the compare-before-delete fix deterministically, without
    depending on real thread timing: `fetch()` simulates this call's lock
    having expired mid-fetch and a DIFFERENT caller having already acquired
    a new lock under the same key. The old unconditional `cache.delete(
    lock_key)` would have wiped that other caller's lock out from under it;
    the fix must leave it untouched.
    """
    backend = _fresh_backend()
    key = "master-dataset-ownership-test"
    lock_key = f"{_LOCK_PREFIX}{key}"

    def fetch():
        backend.set(lock_key, "someone-elses-token", timeout=30)
        return {"rows": []}

    get_master_dataset(key, fetch, cache=backend, lock_timeout=30)

    assert backend.get(lock_key) == "someone-elses-token", "this call's finally block released a lock it did not own"


@pytest.mark.parametrize("bad", [0, None, -1, 1.5, True, "30"])
def test_lock_timeout_must_be_a_positive_int(bad):
    """Review pass 2: `lock_timeout` reached `cache.add()` unvalidated, and
    Django reads two of these as instructions rather than as mistakes --
    `0` as "expire immediately" (so `add()` stores nothing, EVERY caller wins
    the lock, and single-flight is silently off) and `None` as "cache
    forever" (so a hard-killed fetcher leaves a lock nothing ever clears).
    Both defeat the story's headline invariant with no error at all, which is
    why they have to be refused at the boundary.
    """
    backend = _fresh_backend()
    with pytest.raises(ValueError, match="lock_timeout"):
        get_master_dataset("k", lambda: {"rows": []}, cache=backend, lock_timeout=bad)


def test_zero_lock_timeout_would_have_voided_single_flight():
    """The consequence the guard above prevents, demonstrated directly
    against the backend rather than asserted in prose: with a 0-second
    timeout, `add()` stores nothing and every caller in turn wins the lock.
    """
    backend = _fresh_backend()
    assert [backend.add("demo-lock", "token", timeout=0) for _ in range(3)] == [True, True, True]


def test_release_failure_never_masks_the_real_outcome():
    """Review pass 2: an exception raised inside `finally` REPLACES whatever
    was in flight. A backend blip during lock release would have turned an
    already-cached success into a failure -- and, worse, swallowed a genuine
    `fetch()` error and reported the blip instead.
    """

    class ExplodingRelease:
        """Delegates everything to a real backend, but fails on lock reads."""

        def __init__(self, inner):
            self._inner = inner

        def get(self, key, default=None):
            if key.startswith(_LOCK_PREFIX):
                raise RuntimeError("backend blip during lock release")
            return self._inner.get(key, default)

        def add(self, key, value, timeout=None):
            return self._inner.add(key, value, timeout=timeout)

        def set(self, key, value, timeout=None):
            return self._inner.set(key, value, timeout=timeout)

        def delete(self, key):
            return self._inner.delete(key)

    backend = ExplodingRelease(_fresh_backend())

    # A successful fetch stays successful.
    assert get_master_dataset("ok-key", lambda: {"rows": [1]}, cache=backend) == {"rows": [1]}

    # A failing fetch reports ITS error, not the release blip.
    def boom():
        raise ValueError("the real fetch error")

    with pytest.raises(ValueError, match="the real fetch error"):
        get_master_dataset("bad-key", boom, cache=backend)


def test_a_cache_write_failure_never_discards_a_successful_fetch():
    """Review pass 3: pass 2 guarded the lock RELEASE but not the value
    `set()`, so a backend blip on the write turned an already-successful
    fetch into a hard failure and threw the fetched data away. A cache is an
    accelerator; returning uncached data beats failing the request.
    """

    class ExplodingWrite:
        """Delegates everything to a real backend, but fails writing the value."""

        def __init__(self, inner):
            self._inner = inner

        def get(self, key, default=None):
            return self._inner.get(key, default)

        def add(self, key, value, timeout=None):
            return self._inner.add(key, value, timeout=timeout)

        def set(self, key, value, timeout=None):
            if not key.startswith(_LOCK_PREFIX):
                raise RuntimeError("backend blip while caching the value")
            return self._inner.set(key, value, timeout=timeout)

        def delete(self, key):
            return self._inner.delete(key)

    inner = _fresh_backend()
    backend = ExplodingWrite(inner)

    assert get_master_dataset("write-blip-key", lambda: {"rows": [1]}, cache=backend) == {"rows": [1]}
    # Nothing was cached -- which is the accepted degradation, not an error.
    assert inner.get("write-blip-key") is None


@pytest.mark.parametrize("bad", ["300", object(), [30]])
def test_timeout_type_is_validated_at_the_boundary(bad):
    """Review pass 3: an unusable `timeout` type raised from deep inside the
    backend only AFTER `fetch()` had run and its result had been discarded.
    Same "validate at the boundary" argument as the `lock_timeout` guard one
    line above it in the source.
    """
    backend = _fresh_backend()
    calls = []

    def fetch():
        calls.append(1)
        return {"rows": []}

    with pytest.raises(TypeError, match="timeout"):
        get_master_dataset("k", fetch, cache=backend, timeout=bad)

    assert calls == [], "the bad timeout must be rejected before fetch() runs"


def test_timeout_zero_is_still_allowed_as_caching_disabled():
    """Deliberately NOT rejected: Django reads `timeout=0` as "expire
    immediately", i.e. the caller explicitly turning caching off, which is
    their call to make (a prior pass rejected this as a defect on exactly
    that reasoning). Pinned so the new type guard above cannot quietly
    broaden into a behavior change.
    """
    backend = _fresh_backend()
    calls = []

    def fetch():
        calls.append(1)
        return {"rows": []}

    assert get_master_dataset("zero-timeout-key", fetch, cache=backend, timeout=0) == {"rows": []}
    assert backend.get("zero-timeout-key") is None, "timeout=0 means nothing is retained"
    assert calls == [1]


def test_a_key_in_the_lock_namespace_is_refused():
    """Review pass 4: pass 1 moved the lock key from a suffix to the
    `dashboard-fetch-lock:` PREFIX so a caller key could not collide with it,
    but nothing stopped a caller key from starting WITH that prefix. Caching
    data at `"dashboard-fetch-lock:sales"` occupies precisely the lock slot
    for `"sales"`, and the next caller for `"sales"` reads that data frame as
    a permanently-held lock. Reproduced as a hang before this guard.
    """
    backend = _fresh_backend()
    with pytest.raises(ValueError, match="reserved lock-key prefix"):
        get_master_dataset(f"{_LOCK_PREFIX}sales", lambda: "DATA", cache=backend)


def test_timeout_rejects_bool_but_still_allows_zero():
    """Review pass 4: `lock_timeout`'s guard excludes `bool` explicitly;
    `timeout`'s (added in pass 3) did not. `timeout=False` IS an int to
    `isinstance`, reaches the backend as `0` — "expire immediately" — and
    silently caches nothing (reproduced), which is the same silent-void
    consequence the `lock_timeout` guard exists to refuse.

    `timeout=0` stays allowed on purpose: that is a caller explicitly
    disabling caching (pass 2 rejected treating it as a defect), and it is
    asserted here so this guard cannot quietly broaden into a behavior change.
    """
    backend = _fresh_backend()
    with pytest.raises(TypeError, match="timeout must be"):
        get_master_dataset("bool-timeout", lambda: "V", cache=backend, timeout=False)

    assert get_master_dataset("zero-timeout", lambda: "V", cache=backend, timeout=0) == "V"


def test_winning_the_lock_rechecks_the_key_before_fetching():
    """Review pass 4: the second check of double-checked locking was missing.
    Between a caller's own miss and its `cache.add()`, another fetcher can
    complete and populate the key; without a re-read this call fetched anyway
    and then OVERWROTE the fresher value with its own staler one (reproduced:
    the cache ended up holding `STALE`, not `FRESH`).

    Simulated deterministically rather than by thread timing: the backend
    populates the data key at the exact instant the lock is won.
    """
    _fresh_backend()
    key = "double-checked-locking"
    calls: list[int] = []

    class PopulateWhenLockWon(LocMemCache):
        armed = True

        def add(self, add_key, value, **kwargs):
            won = super().add(add_key, value, **kwargs)
            if won and PopulateWhenLockWon.armed:
                PopulateWhenLockWon.armed = False
                super().set(key, "FRESH-from-the-other-fetcher")
            return won

    racing = PopulateWhenLockWon(f"double-check-{time.monotonic_ns()}", {})

    def fetch():
        calls.append(1)
        return "STALE-from-us"

    result = get_master_dataset(key, fetch, cache=racing)

    assert calls == [], "the key was already populated when the lock was won — fetch must not run"
    assert result == "FRESH-from-the-other-fetcher"
    assert racing.get(key) == "FRESH-from-the-other-fetcher", "a stale fetch must not overwrite it"


def test_a_backend_that_never_grants_the_lock_raises_instead_of_spinning():
    """Review pass 4: `time.sleep` lived ONLY inside the "lock is visibly
    held" poll loop, so when `add()` reported failure while the lock key read
    as absent, that loop's body never ran and the outer loop retried with no
    delay at all — an unbounded busy loop that never returned and never
    fetched (measured: 1.1M backend operations in 2s, 0 fetches, thread still
    alive).

    Not hypothetical: Django's `DatabaseCache._base_set` ends in a bare
    `except DatabaseError: return False`, so write contention presents exactly
    this way while reads keep working.
    """
    from pyforge.steward.dashboard.cache import LockUnavailableError

    class NeverGrantsTheLock(LocMemCache):
        operations = 0

        def add(self, *args, **kwargs):
            NeverGrantsTheLock.operations += 1
            return False

        def get(self, add_key, default=None, **kwargs):
            NeverGrantsTheLock.operations += 1
            return super().get(add_key, default, **kwargs)

    backend = NeverGrantsTheLock(f"no-lock-{time.monotonic_ns()}", {})
    calls: list[int] = []

    started = time.monotonic()
    with pytest.raises(LockUnavailableError, match="could not acquire or observe"):
        get_master_dataset("ungrantable", lambda: calls.append(1), cache=backend, lock_timeout=1)
    elapsed = time.monotonic() - started

    assert calls == [], "fetch() is never reached in this state"
    # Bounded by _MAX_WAIT_MULTIPLIER * lock_timeout, and it SLEEPS between
    # attempts rather than spinning: the old busy loop issued hundreds of
    # thousands of operations per second, this issues a handful per second.
    assert 2 <= elapsed < 10, f"expected the wait to be bounded by the deadline, took {elapsed}s"
    assert NeverGrantsTheLock.operations < 500, (
        f"the retry path must sleep between attempts, not spin — "
        f"{NeverGrantsTheLock.operations} backend operations in {elapsed:.1f}s"
    )
