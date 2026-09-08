---
title: 'Circuits trip on async too'
type: feature
created: '2026-08-25'
status: done
baseline_commit: 2b8d4a33b63
baseline_revision: 2b8d4a33b63
review_loop_iteration: 0
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-unifying-strategy-2026-08-24/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-unifying-strategy-2026-08-24/prd.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-unifying-strategy-2026-08-24/addendum.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/resilience-invariants.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** A dead outbound dependency can hang the estate. PyBreaker's `call()` treats an un-awaited asyncio coroutine as success, so the circuit never opens (FR-26, canopy:AD-15, BS-4). `pybreaker` is not in pixi; this story ships an in-tree wrapper, not a new dep.

**Approach:** One asyncio-aware circuit wrapper in `django-pyforge`. A failing awaited call registers as a failure. After repeated failures the circuit opens and the caller returns degraded inside the FR-26 budget. `fail_max` is coarse protection — tests never assert an exact failure count. Stations do not ship a second wrapper (adversarial F-10).

## Boundaries & Constraints

**Always:** Wrapper lives in `django-pyforge` (`django_pyforge.circuits`). Tests fail if `acall` does not await (AD-15: mechanism absent). Reuse FR-26 budget `0.5s` (`FAIL_FAST_SECONDS`). Specs under `_bmad-output/projects/pyforge-steward/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward`. Physical writes only under that slug. Consult `docs/reference/library-llms-full.md` before new imports — stdlib only here.

**Block If:** Implementation would add `pybreaker` / `aiocircuitbreaker` / `purgatory` to pixi, put `pyforge.*` under `src/platform/`, or require Redis for the unit tests.

**Never:** Start 25.2, 25.3, 25.4. MinIO/S3. `scripts/bmad-switch`. `bmad-loop`. Other stations' ledgers. Exact-count `fail_max` assertions. A second per-station breaker.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Repeated outbound failures | Async callable raises; many attempts (well above `fail_max`) | Circuit opens; next `call_or_degrade` returns `Degraded` | Failures recorded; no hang on the dead call |
| Within budget | Circuit already open; outbound would sleep past 500ms | Returns `Degraded` in `< FAIL_FAST_SECONDS` | Must not await the dead dependency |
| Async failure is a failure | `acall` of a raising coroutine | Failure counted; circuit can open | Not a false success |
| Naive `call` (mechanism absent) | Same raising coroutine passed to a non-awaiting `call` | Coroutine object returned; circuit stays closed | Documents the PyBreaker trap; AD-15 |
| Coarse `fail_max` | Hammer with a surplus of failures | Open after surplus; test does not assert `fail_count == fail_max` | Threshold is protection, not a latch |

</intent-contract>

## Code Map

- `src/shared/packages/django-pyforge/src/django_pyforge/circuits.py` -- NEW: in-tree breaker; `acall`, `call_or_degrade`, `Degraded`, `CircuitOpenError`; `call` is the non-awaiting trap for AD-15
- `src/platform/tests/test_circuits_trip_on_async_too.py` -- NEW: four ACs
- Never: `src/platform/**` importing `pyforge.*`; Epic 25.2 DuckDB / 25.3 HTMX 422 / 25.4 reconcile; pixi.toml unless a stdlib-only path is impossible

## Tasks & Acceptance

**Execution:**
- `django_pyforge/circuits.py` -- asyncio wrapper (~40 lines of mechanism)
- `src/platform/tests/test_circuits_trip_on_async_too.py` -- ACs including AD-15 absence

**Acceptance Criteria:**
- Given repeated outbound failures, when the circuit opens, then the caller returns degraded within budget.
- And a failing asyncio call registers as a failure (in-tree PyBreaker wrapper), not a success.
- And `fail_max` is coarse, never exact-count.
- And removing the wrapper makes the test fail.

## Spec Change Log

## Design Notes

PyBreaker on conda-forge is sync / Tornado; `breaker.call(async_fn)` returns the coroutine and records success. Rejected: `aiocircuitbreaker` (dormant 2022), `purgatory` (unpackaged). In-memory fail counter is exact in tests; Redis `setnx`/`incr` in upstream is not atomic, so production `fail_max` stays coarse — tests only prove "many failures ⇒ open", never "the Nth call opens". Open circuit fail-fast budget is the same 500ms as `QUERY_BUDGET_SECONDS` (FR-26 / 21.5); this module does not import supervisor.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

Summary: In-tree `django_pyforge.circuits` wrapper awaits asyncio, records failures, opens after a surplus of errors, and returns `Degraded` inside 500ms. Naive `call` still treats an un-awaited coroutine as success (AD-15). No pixi bump.

Files changed:
- `django_pyforge/circuits.py` -- `acall` / `call_or_degrade` / trap `call`
- `src/platform/tests/test_circuits_trip_on_async_too.py` -- four ACs
- this spec

Verification: `pixi run -e platform-ci-test pytest src/platform/tests/test_circuits_trip_on_async_too.py src/platform/tests/meta/test_no_pyforge_import.py -q` → 5 passed.
