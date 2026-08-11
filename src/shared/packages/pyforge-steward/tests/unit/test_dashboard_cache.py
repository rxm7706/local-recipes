"""Story 9.1 — `get_master_dataset()` single-flight + no-role-filtered-frame
invariant (AD-5 / CAP-2), proven by a real threaded race against a real
Django `LocMemCache` backend, plus direct inspection of that backend's
contents afterward.
"""

from __future__ import annotations

import threading
import time

from django.conf import settings

# Settings may already be configured if this file collects alongside another
# test module that configured them first -- guard so a second `configure()`
# call (which Django refuses) never crashes the run.
if not settings.configured:
    settings.configure(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "pyforge-steward-dashboard-test",
            },
        },
    )

from django.core.cache import caches  # noqa: E402 -- must follow settings.configure()

from pyforge.steward.dashboard.cache import get_master_dataset  # noqa: E402

_LOCK_PREFIX = "dashboard-fetch-lock:"


def _fresh_backend():
    backend = caches["default"]
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
        time.sleep(0.2)  # widen the race window between the two threads
        return {"rows": [{"region": "east"}, {"region": "west"}]}

    results: dict[str, list] = {}

    def worker(role):
        master = get_master_dataset(key, fetch, cache=backend)
        # Role-filtering happens AFTER get_master_dataset returns, by the
        # caller -- never inside the cache layer itself.
        results[role] = [row for row in master["rows"] if row["region"] == role]

    t1 = threading.Thread(target=worker, args=("east",))
    t2 = threading.Thread(target=worker, args=("west",))
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

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

    assert backend.get(lock_key) == "someone-elses-token", (
        "this call's finally block released a lock it did not own"
    )
