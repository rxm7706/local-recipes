---
title: 'CAP-11 in effect — the eviction test'
type: 'test'
created: '2026-09-11'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '6ae202c53f5213eb6faab857fbed1415d1c17f26'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** CAP-11 claims the `redis-cache` / `redis-broker` split (Story 40.2) protects Celery's
queue/stream/PEL state from a cache eviction storm, but no test actually fills `redis-cache` to its
`allkeys-lru` limit while broker traffic is in flight — so the claim is unexercised.

**Approach:** Add a real-Redis test under `src/platform/tests/` that fills `redis-cache` to its
configured `allkeys-lru` limit while tasks are queued on `redis-broker`, and asserts nothing on the
broker side (queued task, stream entry, or PEL entry) is lost. If the chart split (Story 48.2's
`hpa.yaml`, if not already landed) doesn't yet separate the two Redis instances, this story lands it
first — the test is meaningless against a single shared instance.

## Boundaries & Constraints

**Always:**
- The test uses a REAL Redis instance under eviction pressure — never a mock of eviction behavior.
- The test must FAIL if run against a single shared (non-split) Redis instance, proving it actually
  exercises the split rather than passing vacuously.

**Never:**
- Never assert eviction-safety by inspecting configuration alone (e.g. "the maxmemory-policy is set
  correctly") — the test must observe real broker-side survival under real cache pressure.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Cache filled to eviction limit | `redis-cache` at `allkeys-lru` limit, tasks queued on `redis-broker` | No queued task, stream entry, or PEL entry lost | N/A |
| Unsplit Redis (regression guard) | A single shared instance stands in for both roles | Test fails, proving the split is what protects broker state | N/A |

</intent-contract>

## Code Map

- `src/platform/tests/` — new real-Redis eviction test
- chart `hpa.yaml` — only if Story 48.2's `redis-cache`/`redis-broker` split has not already landed

## Tasks & Acceptance

**Execution:**
- `test` — a real-Redis test filling `redis-cache` to its `allkeys-lru` limit while `redis-broker`
  carries queued tasks, asserting no broker-side data loss.
- `feature` (conditional) — land the chart's `redis-cache`/`redis-broker` split if Story 48.2 hasn't
  already shipped it.

**Acceptance Criteria:**
- Given the chart split is real and no test fills the cache, when a test fills `redis-cache` to its
  `allkeys-lru` limit while tasks are queued on `redis-broker`, then no queued task, stream entry, or
  PEL entry is lost, and the test fails without the split.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: full suite green (no
  steward-package code changes expected; this command proves nothing else regressed)

**Manual checks (if no CLI):**
- `pixi run -e local-recipes platform-ci-local -- --test` — expected: full `src/platform/` suite
  green, including the new eviction test (the test itself lives here, not in pyforge-steward)

## Spec Change Log

## Review Triage Log
