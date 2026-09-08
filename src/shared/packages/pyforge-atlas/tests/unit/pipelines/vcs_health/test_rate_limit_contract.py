"""Phase K engineering-contract fixture tests (Story B1, AC-4 / AD-10 / AD-11).

The single-worker 3-RPS token bucket, the ``PHASE_K_AGGRESSIVE`` opt-out, ``Retry-
After`` parsing, and the 403 → ``last_error`` re-pick are proven against a STUBBED /
injected client with an injected clock — NEVER a live endpoint. The discipline lives
in ``datasets/rate_limit.py`` (a dataset/resource concern, AD-2), not in a node body.
"""

from __future__ import annotations

import pytest

from pyforge.atlas.datasets.rate_limit import (
    AGGRESSIVE_WORKERS,
    DEFAULT_RPS,
    SINGLE_WORKER,
    FetchError,
    RateLimitedScheduler,
    StubFetcherClient,
    parse_retry_after,
    resolve_worker_count,
)


class _FakeClock:
    """Deterministic monotonic clock; ``sleep`` advances it (no real waiting)."""

    def __init__(self) -> None:
        self.t = 0.0

    def now(self) -> float:
        return self.t

    def sleep(self, secs: float) -> None:
        self.t += secs


# -- single-worker 3-RPS default -------------------------------------------

def test_default_rps_is_3_and_single_worker():
    assert DEFAULT_RPS == 3.0
    assert resolve_worker_count(None) == SINGLE_WORKER == 1


def test_token_bucket_throttles_to_the_configured_rps():
    clk = _FakeClock()
    # small bucket so throttling is observable immediately
    sched = RateLimitedScheduler(rps=3.0, bucket_capacity=2, clock=clk.now, sleep=clk.sleep)
    # first 2 acquires are free (bucket starts full), no time passes
    assert sched.acquire() == 0.0
    assert sched.acquire() == 0.0
    # bucket now empty -> next acquire must wait 1/rps seconds for a refill
    waited = sched.acquire()
    assert waited == pytest.approx(1 / 3.0, rel=1e-6)
    assert clk.t == pytest.approx(1 / 3.0, rel=1e-6)


def test_acquire_more_than_capacity_raises_not_hangs():
    # a request larger than the bucket could never refill enough -> guard, don't hang
    sched = RateLimitedScheduler(rps=3.0, bucket_capacity=10)
    with pytest.raises(ValueError):
        sched.acquire(11)


def test_acquire_frozen_clock_no_op_sleep_raises_not_spins():
    # B2 review-hardening (DW-B1-2 code ceiling): a frozen clock + no-op sleep never
    # refills tokens, so acquire() would spin forever once the bucket drains. The code
    # ceiling RAISES instead of hanging.
    sched = RateLimitedScheduler(
        rps=3.0, bucket_capacity=1, clock=lambda: 0.0, sleep=lambda s: None
    )
    sched.acquire()  # first token is free (bucket starts full)
    with pytest.raises(RuntimeError, match="did not advance"):
        sched.acquire()  # bucket empty + clock frozen -> ceiling raises, no hang


def test_refill_is_continuous():
    clk = _FakeClock()
    sched = RateLimitedScheduler(rps=3.0, bucket_capacity=10, clock=clk.now, sleep=clk.sleep)
    for _ in range(10):  # drain the full bucket
        sched.acquire()
    assert sched.tokens == pytest.approx(0.0, abs=1e-9)
    clk.t += 1.0  # 1 second elapsed -> 3 tokens refilled (3 RPS)
    assert sched.acquire() == 0.0
    assert sched.tokens == pytest.approx(2.0, abs=1e-6)


# -- PHASE_K_AGGRESSIVE opt-out (only literal "1" re-arms burst) ------------

def test_aggressive_only_literal_one_re_arms_burst():
    assert resolve_worker_count("1") == AGGRESSIVE_WORKERS == 8
    # non-"1" values do NOT re-arm burst (CFA:5114-5115)
    for val in ("true", "0", "yes", "", None, "2"):
        assert resolve_worker_count(val) == SINGLE_WORKER


# -- Retry-After parsing (hard-capped, both RFC 7231 forms) -----------------

def test_parse_retry_after_delta_seconds_capped():
    assert parse_retry_after("5") == 5.0
    assert parse_retry_after(120) == 60.0  # hard cap at 60s
    assert parse_retry_after(None) == 0.0
    assert parse_retry_after("garbage") == 0.0


def test_parse_retry_after_naive_date_assumed_utc():
    # a naive HTTP-date (no tz) must be read as UTC, not local time
    got = parse_retry_after("Thu, 01 Jan 1970 00:00:30", now=0.0)
    assert got == pytest.approx(30.0, abs=1.0)


def test_parse_retry_after_http_date_form():
    # 10 s in the future from a fixed 'now' -> ~10 s wait
    now = 1_000_000.0
    got = parse_retry_after("Thu, 01 Jan 1970 00:00:10 GMT", now=0.0)  # 10s epoch
    assert got == pytest.approx(10.0, abs=1.0)
    # far-future date is capped at 60
    assert parse_retry_after("Wed, 21 Oct 2099 07:28:00 GMT", now=now) == 60.0


# -- stubbed fetcher acquires a token per fetch + 403 -> last_error ---------

def test_stub_fetcher_acquires_a_token_per_call():
    clk = _FakeClock()
    sched = RateLimitedScheduler(rps=3.0, bucket_capacity=1, clock=clk.now, sleep=clk.sleep)
    client = StubFetcherClient({"numpy": {"v": "2.0"}}, scheduler=sched)
    assert client.fetch("numpy") == {"v": "2.0"}   # first: free
    client.fetch("numpy")                           # second: throttled -> time advanced
    assert clk.t > 0.0
    assert len(client.calls) == 2


def test_stub_fetcher_403_raises_fetch_error_for_last_error_mapping():
    client = StubFetcherClient({}, raise_status={"gitea-pkg": 403})
    with pytest.raises(FetchError) as exc:
        client.fetch("gitea-pkg")
    # a 403 is what the fetcher maps to upstream_versions.last_error + TTL-bypass
    # re-pick; the node then preserves that last_error column (test_nodes.py).
    assert exc.value.status == 403
    assert exc.value.key == "gitea-pkg"
