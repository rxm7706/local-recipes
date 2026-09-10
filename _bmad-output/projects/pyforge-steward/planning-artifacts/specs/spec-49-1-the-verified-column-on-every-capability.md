---
title: 'The verified column on every capability'
type: 'chore'
created: '2026-09-10'
status: 'in-progress'
baseline_revision: '82626b1239a5c47dc8604676ae3066bced6c52e9'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/research/currency-review-pyforge-unifying-strategy-2026-09-09.md
warnings: []
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** Epic 49's realization gate needs a machine-readable `**verified:**` column on every
Unifying Strategy CAP-1..19 naming which success clause has a live exercise and which is
fixture-only; without it `capability-effect-check` (Story 49.2) has nothing to read.

**Approach:** Append one `**verified:**` line per CAP in `spec-pyforge-unifying-strategy/SPEC.md`
§ Capabilities, grounded in the 2026-09-09 currency review grading plus file:line evidence from
live tests and source.

## Boundaries & Constraints

**Always:**
- Edit only `spec-pyforge-unifying-strategy/SPEC.md` § Capabilities (CAP-1..19).
- Each line names live vs fixture-only clauses with at least one file:line anchor.
- Preserve existing intent/success text; append `**verified:**` after `**success:**`.

**Never:**
- Do not implement `capability-effect-check` (Story 49.2).
- Do not change CAP success criteria or close Epic 49 effect stories (49.3–49.8).
- Do not edit companion specs (`resilience-invariants.md`, `stack.md`, etc.) in this story.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| All nineteen CAPs | SPEC.md § Capabilities before edit | Each CAP-1..19 block gains exactly one `**verified:**` line after `**success:**` | N/A |
| Partial CAPs | Currency review §1.4 six gaps | Verified line names the unexercised clause with file:line | N/A |
| Fully verified CAPs | Eleven CAPs per Residual | Verified line names live exercise with file:line; fixture-only if any sub-clause untested | N/A |

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md` — sole edit surface; § Capabilities CAP-1..19
- `_bmad-output/projects/pyforge-steward/planning-artifacts/research/currency-review-pyforge-unifying-strategy-2026-09-09.md` — §1.4 grading (six partial, eleven full)
- `src/platform/tests/test_django_pyforge_chrome.py` — CAP-1 chrome dedup
- `src/platform/tests/test_front_door_publish.py` — CAP-2 Lane 1
- `src/platform/tests/test_station_portal_shells.py` — CAP-3 portals/session
- `src/platform/tests/test_start_get_survives_disconnect.py` — CAP-4 start/get
- `src/shared/packages/pyforge-core/tests/meta/test_cli_parity_matrix.py` — CAP-5 parity
- `src/platform/tests/test_django_pyforge_assertion.py` — CAP-6 identity client
- `src/platform/tests/test_host_board_row_isolation.py` — CAP-7 board fixture
- `src/platform/tests/test_cloudevents_redis_broker.py` — CAP-8 events
- `src/platform/tests/policy/test_liquibase_ddl_governance.py` — CAP-9 DDL
- `src/platform/tests/test_circuits_trip_on_async_too.py` — CAP-10 circuit (test-only caller)
- `src/platform/tests/test_chart_invariants.py` — CAP-11/CAP-12 chart policies
- `src/platform/tests/test_openfeature_file_flags.py` — CAP-13 flags
- `src/shared/packages/pyforge-scribe/tests/unit/test_recall_semantic.py` — CAP-14 semantic
- `src/shared/packages/pyforge-steward/tests/meta/test_five_tier_check.py` — CAP-15 roster
- `src/shared/packages/pyforge-warden/tests/meta/test_station_persona.py` — CAP-16 persona
- `src/platform/tests/test_front_door_queries_supervisor.py` — CAP-17 runs board
- `src/shared/packages/pyforge-core/tests/unit/test_hooks.py` — CAP-18 hooks
- `src/shared/packages/pyforge-atlas/tests/unit/test_query_plane_parquet_cache.py` — CAP-19 plane

## Tasks & Acceptance

**Execution:**
- `spec-pyforge-unifying-strategy/SPEC.md` — append `**verified:**` after each CAP `**success:**` block (CAP-1..19) — Story 49.1 deliverable

**Acceptance Criteria:**
- Given the currency review's per-CAP grading, when each CAP-1..19 gains a `**verified:**` line, then it names which success clause has a live exercise (artifact, deployed check, measured number) and which is fixture-only, with file:line.
- And eleven CAPs read fully verified and six read partial per Residual (2026-09-09).
- And the column is the input `capability-effect-check` will read (Story 49.2).

## Verification

**Commands:**
- `grep -c '  - \*\*verified:\*\*' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md` — expected: 19
- `pixi run -e local-recipes chain-completeness-check` — expected: exit 0

**Manual checks (if no CLI):**
- Each CAP block in SPEC.md § Capabilities has `**verified:**` immediately after its `**success:**` paragraph and before the next CAP or section break.
