---
title: '47.4: A genuine recall miss injects nothing, never a fabricated confidence claim'
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

**Problem:** Scribe's `recall` never invents an uncited answer — a genuine miss is explicit. If
Story 47.1's formatting helper turns that grounded miss into any injected text at all (even a
well-meaning "no relevant corrections found" line), it manufactures a confidence claim scribe
itself never made, undermining the exact honesty property this whole capability depends on.

**Approach:** The formatting helper's empty-answer branch produces no output — not a placeholder
sentence, not a "checked, nothing found" note. Absence of a block is itself the signal.

## Boundaries & Constraints

**Always:**
- A grounded-miss `RecallAnswer` maps to zero injected text — no block, no placeholder.
- The distinction between "query didn't run" (Story 47.1's fail-open path) and "query ran,
  genuinely found nothing" (this story) is a distinction without a behavioral difference — both
  produce no injected block, by design.

**Never:**
- Never synthesize a "no relevant corrections found" sentence or any other confidence claim scribe
  did not itself assert.
- Never treat an empty result as an error condition — it's a valid, honest answer.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Grounded miss | `scribe recall` returns a `RecallAnswer` with no citable hit | Formatting helper produces zero injected text | No error expected |
| Grounded hit | `scribe recall` returns a citable hit | Formatting helper produces the labeled block (contrast case, proves the distinction is real) | No error expected |
| Fixture assertion | Unit test drives both cases through the same helper | Empty-hit and non-empty-hit cases produce distinguishably different (empty vs. non-empty) output | No error expected |

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-011 binding corrected 2026-09-19 — the `-k recall` scoping is a manual check below, not the declared command).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-011 binding corrected 2026-09-19 — the `-k recall` scoping is a manual check below, not the declared command).

**Manual checks:**
- `pixi run -e pyforge-marshal pyforge-marshal-test -k recall` -- expected: a fixture test feeds
  the formatting helper a grounded-miss `RecallAnswer` and asserts the injected text is empty/
  absent, contrasted against a grounded-hit case in the same test module

## Auto Run Result
