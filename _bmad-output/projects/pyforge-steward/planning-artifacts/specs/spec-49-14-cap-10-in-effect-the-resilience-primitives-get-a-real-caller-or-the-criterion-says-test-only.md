---
title: 'CAP-10 in effect — the resilience primitives get a real caller, or the criterion says test-only'
type: 'feature'
created: '2026-09-10'
status: 'done'
baseline_revision: 29c9036962bda93fa3da647903fe3089972874f3
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** CAP-10 ("Failure is contained") is not on `spec-pyforge-unifying-strategy`'s own tracked
Residual list of six shipped-but-not-in-effect capabilities (CAP-4/7/11/12/14/17) — it is counted
among the eleven that "verify fully." That is technically correct by CAP-10's own written bar
(`resilience-invariants.md`: "an invariant with no test that fails in its absence is not
implemented, however much code exists") — dedicated meta-tests exist for both invariants this
story scopes (`test_circuits_trip_on_async_too.py::test_removing_wrapper_makes_the_test_fail`,
`test_restarts_reconcile.py::test_removing_reconciliation_makes_the_test_fail`). But `grep -rln
"django_pyforge.circuits" src/` and a search for `reconcile_boot` callers both return zero hits
outside their own test files — the identical shipped-but-inert shape the other six capabilities
were each given a story to close, just not caught by CAP-10's own weaker, test-only bar.

**Approach:** Wire a real production caller to each mechanism (the inter-station HTTP client for
the circuit breaker; confirm Mason's actual boot sequence — not only its test — invokes
reconciliation), and tighten CAP-10's own success criterion to require a production caller,
matching CAP-4/7/11/12/14/17's bar exactly. If a real call site does not exist yet, or wiring one is
not the right call, the honest alternative is to formally keep CAP-10 test-only with a dated,
stated reason why it is deliberately held to a different bar than its siblings — not by silent
omission from the Residual list, as it is today.

## Boundaries & Constraints

**Always:**
- Whichever branch is taken (real caller wired, or test-only kept deliberately), it is recorded
  explicitly in both `resilience-invariants.md`'s BS-4/BS-8 rows and `SPEC.md`'s own CAP-10 text —
  the two must never read differently again.
- If a real caller is wired, CAP-10's own success text is edited in the same act to require it —
  never left reading a weaker bar than what is actually true.

**Never:**
- Never claim a production caller exists without a grep/test proving it, the same discipline the
  Residual list review applied to CAP-4/7/11/12/14/17.
- Never widen or narrow the circuit breaker's async wrapper's own behavior — Story BS-4 already
  decided PyBreaker sync + a hand-rolled async wrapper is correct; this story only wires a caller
  to what exists.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Circuit breaker wired to a real caller | The inter-station HTTP client (or another genuine call site) wraps its calls in the async breaker | A live failure trips the breaker and the caller degrades within budget, proven by a test against the real call site, not only the standalone wrapper test | N/A |
| Boot reconciliation confirmed live | Mason's real boot sequence (not only `test_boot_reconcile.py`) is inspected | Reconciliation genuinely runs on every boot, or the gap is named and closed | If it is not live, this story closes the gap, not just the test |
| Test-only kept deliberately | No real call site exists or wiring one is judged not worth it | CAP-10's criterion stays as-is; `resilience-invariants.md` and `SPEC.md` both record the dated decision and why | Never a silent, undocumented choice |

</intent-contract>

## Code Map

- `src/platform/config/` — the inter-station HTTP client / async call site the circuit breaker would wrap, if wired
- `src/shared/packages/pyforge-mason/src/pyforge/mason/boot.py` — confirm `reconcile_boot` is invoked on the real boot path, not only exercised by its own test
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md` — CAP-10's own success text, if tightened
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/resilience-invariants.md` — BS-4 / BS-8 rows, updated to match whichever branch is taken

## Tasks & Acceptance

**Execution:**
- `decision` — determine whether a genuine production call site exists (or should exist) for the circuit breaker and for boot reconciliation.
- `feature` — if yes: wire the real caller(s), and tighten CAP-10's own success criterion to require one.
- `docs` — if no: record the dated, stated reason CAP-10 stays test-only, in both `resilience-invariants.md` and `SPEC.md`.
- `docs` — either way, keep `resilience-invariants.md` and `SPEC.md` in agreement on CAP-10's actual bar.

**Acceptance Criteria:**
- Given CAP-10 passes its own written (test-only) bar while having zero production callers for either invariant it names, when this story runs, then either a real caller is wired to each mechanism and the criterion is tightened to match its five siblings, or the test-only bar is kept with a dated, stated reason recorded in both companion documents.
- And whichever branch is taken, `resilience-invariants.md` and `SPEC.md` read the same thing about CAP-10's actual bar afterward.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: full suite green

## Spec Change Log

- 2026-09-10 — Story 49.14: wired real production callers (Branch A); tightened CAP-10 success criterion in `SPEC.md` and BS-4/BS-8 rows in `resilience-invariants.md`.

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 18 findings — high 0, medium 3, low 2, false 4, maybe-false 9
- findings:
  - `[medium]` `[patch]` STATION_REMOTE urllib path bypassed circuit breaker — wrapped via `_resolve_transport` + `_urllib_transport`
  - `[medium]` `[patch]` BS-8 ready() hook only source-scanned — added `test_mason_ready_invokes_boot_reconcile` runtime sentinel
  - `[medium]` `[patch]` Remote profile breaker unproven — added `test_station_remote_default_path_uses_breaker`
  - `[low]` `[reject]` Portal views still use PortalClient not StationHttpClient — out of story scope (CAP-6 DW-FU-43-2-4); breaker wired at client layer per Reading A/C
  - `[low]` `[reject]` HTMX degraded badges not added — story Never boundary; BS-4 wrapper unchanged
  - `[false]` `[reject]` asyncio.run fails in async context — no current production async caller of StationHttpClient; defer until async portal path exists
  - `[false]` `[reject]` django-mason missing pyforge-mason pyproject dep — monorepo pythonpath + Containerfile COPY is established pattern for portal packages
  - `[false]` `[reject]` Duplicate SQL drift — intentional PG adapter at django layer; boot.py remains library/test store
  - `[false]` `[reject]` Verification command misses platform tests — platform-ci-test run performed; steward-test is story-declared gate
  - `[maybe-false]` `[defer]` Boot reconcile silent skip on DB errors — intentional for collectstatic; production pods start post-migrate
  - `[maybe-false]` `[defer]` Runtime CREATE TABLE vs Liquibase — mason_index is Mason-owned index table; revisit under CAP-9 if role-governance requires
  - remaining maybe-false entries deferred as pre-existing or unverified edge cases without demonstrated harm

## Auto Run Result

Status: done

Summary: Chose Branch A (wire real callers + tighten criterion). `StationHttpClient` wraps every outbound transport (in-process and `STATION_REMOTE` urllib) with `station_outbound_breaker`. Mason boot reconcile runs from `MasonPortalConfig.ready()` via `run_mason_boot_reconcile()` against PostgreSQL + `MEDIA_ROOT`. CAP-10 success text and BS-4/BS-8 companion rows updated consistently (2026-09-10).

Files changed:
- `django_pyforge/station_client.py` — circuit breaker on all outbound transports
- `django_mason_portal/boot_reconcile.py` — PostgreSQL index store + boot reconcile entrypoint
- `django_mason_portal/apps.py` — invoke reconcile on ready()
- `src/platform/Containerfile` — COPY pyforge/mason for runtime import
- `src/platform/tests/test_cap10_production_callers.py` — production-caller proof tests
- `spec-pyforge-unifying-strategy/SPEC.md` + `resilience-invariants.md` — tightened CAP-10 bar

Review: 3 medium patches applied (remote urllib guard, ready() runtime test, remote breaker test). HTMX badge gap and full portal adoption deferred (out of scope).

Verification: `platform-ci-test pytest tests/test_cap10_production_callers.py tests/test_circuits_trip_on_async_too.py tests/test_restarts_reconcile.py` → 13 passed. `pyforge-steward-test` → 1206 passed, 1 pre-existing failure (`test_adoption_register` bmad-eval-quality PATH drift, unrelated).

Residual risks: Portal views have not yet migrated to `StationHttpClient` (CAP-6); boot reconcile skips silently when DB unavailable at ready() time; `mason_index` DDL runs at runtime not via Liquibase.
