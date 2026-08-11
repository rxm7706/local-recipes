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
if not settings.configured:
    settings.configure(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "pyforge-steward-dashboard-test",
            },
        },
    )

from django.core.cache.backends.locmem import LocMemCache  # noqa: E402
from django.core.cache import caches  # noqa: E402 -- must follow settings.configure()

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

    assert backend.get(lock_key) == "someone-elses-token", (
        "this call's finally block released a lock it did not own"
    )


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
