---
title: "The real-Redis backoff test accepts the server's millisecond clock"
type: 'fix'
created: '2026-09-26'
status: 'done'
baseline_revision: '26c9b77150259100cd7c9434d0a37bbac35c68df'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-42-3-bus-delivery-semantics-and-a-deployed-consumer.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** `test_real_redis_retry_backoff_dlq_and_harvest` (Story 42.3) asserts `calls[1] - calls[0] >= 0.1` and `calls[2] - calls[1] >= 0.2`, where `calls` are `time.monotonic()` reads taken in the handler. The fabric decides a retry is due from Redis's `XPENDING` idle time, which the server computes as `now_ms - delivery_ms` in whole milliseconds. A retry Redis correctly counts as 200 ms idle can therefore be up to 1 ms early in real time. The client's timestamps add reply-latency jitter on top. Under CPU contention the test failed with a correct backoff:
- Platform CI twin, 2026-09-26: 199.5 ms.
- Four concurrent 20-run loops: 1 failure in 80, at 199.9 ms.
- Isolated: 30 of 30 passed.

**Approach:** Allow 5 ms of slack on both assertions, with a comment giving the reason. The fabric is unchanged. Its contract is Redis's idle time, and that contract held in every failure.

## Boundaries & Constraints

**Always:** The assertions still prove the backoff grows. With the slack, the steps are ≥ 95 ms and ≥ 195 ms, still distinguishing 100 from 200. Cite CAP-8 / canopy:FR-20 / canopy:AD-8.

**Never:** Change `django_pyforge.events.fabric` or its backoff schedule. Mark the test flaky or retry it.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Quiet machine | 100 / 200 ms backoff, 3 attempts | Passes | n/a |
| CPU contention | Client-measured 199.5-199.9 ms for the 200 ms step | Passes | n/a |
| Broken backoff | No wait between attempts | Fails (gap far below 95 ms) | Assertion names the gap |

</intent-contract>

## Code Map

- `src/platform/tests/test_cloudevents_redis_broker.py` -- `test_real_redis_retry_backoff_dlq_and_harvest`: `slack = 0.005` on both gap assertions, with the reason in a comment

## Tasks & Acceptance

**Execution:**
- Tolerance as above.

**Acceptance:**
- Four concurrent 20-run loops of the test (real `redis-server`, platform-ci-test interpreter) pass 80/80. The unmodified test failed 1/80 under the same load.
- `pixi run -e pyforge-guild platform-ci-local --test` passes.

## Outcome

Verified locally 2026-09-26. Without the slack: 1/80 failed under contention (`assert (36825.310320274 - 36825.110409777) >= 0.2`). With it: 80/80. Ruff and ruff format are clean, run from `src/platform` as Platform CI does.
