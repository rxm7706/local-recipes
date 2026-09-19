---
title: '47.2: A bmad-loop review pass sees the same scoped feedback the dev pass saw'
type: 'feature' # feature | bugfix | refactor | chore
created: '2026-09-18'
status: 'ready-for-dev' # draft | ready-for-dev | in-progress | in-review | done | blocked
baseline_revision: ''
review_loop_iteration: 0 # incremented by step-04 before each review loopback
followup_review_recommended: false # set by step-04 on status: done; step-01 READS this — false HALTs, true allows one follow-up then forces false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-recall-in-the-loop/SPEC.md']
deferred: [] # append-only machine-readable deferred review findings; each item carries summary/evidence and optional location/severity
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 47.1 gives the dev pass a correction scribe already knows about — but the
review pass grading that dev pass's work starts from a blank context too. A correction visible
to the implementer but invisible to the reviewer is only half the propagation the parent Spec's
"review bot" framing names.

**Approach:** The review pass launch path reuses Story 47.1's already-run recall query and
formatted context block for the same story dispatch — one query, shared by both passes, never a
second independent `scribe recall` call.

## Boundaries & Constraints

**Always:**
- Reuse Story 47.1's query result verbatim — same scope, same answer, no re-query for the review
  pass.
- The review pass's existing findings-report shape is the vehicle for naming a discrepancy against
  a known correction — no new reporting mechanism invented for this story.

**Never:**
- Never issue a second `scribe recall` subprocess call per story dispatch — one query serves both
  passes.
- Never silently drop the injected block for the review pass if it was present for the dev pass —
  the two passes see identical recall context.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Dev pass received a feedback block | Story 47.1's query returned a grounded hit | Review pass session context includes the identical block | No error expected |
| Dev pass received no block | Story 47.1's query returned a miss, or didn't run (scribe unavailable) | Review pass also receives no block — no independent query attempted | No error expected |
| Review verdict contradicts a known correction | Injected block names a constraint the dev pass's diff violates | Review's own findings report names the discrepancy as a finding, using its existing report shape | No error expected |

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-011 binding corrected 2026-09-19 — the `-k recall` scoping is a manual check below, not the declared command).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-011 binding corrected 2026-09-19 — the `-k recall` scoping is a manual check below, not the declared command).

**Manual checks:**
- `pixi run -e pyforge-marshal pyforge-marshal-test -k recall` -- expected: a fixture test asserts
  the review-pass launch path consumes Story 47.1's cached query result rather than issuing its
  own, and that exactly one `scribe recall` subprocess call happens per story dispatch across both
  passes

## Auto Run Result
