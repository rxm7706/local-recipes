---
title: '47.1: A bmad-loop dev pass automatically receives relevant scribe feedback before it starts'
type: 'feature' # feature | bugfix | refactor | chore
created: '2026-09-18'
status: 'in-review' # draft | ready-for-dev | in-progress | in-review | done | blocked
baseline_revision: '2f98ede57d5ebb7df285bbd1383782cf6a7c86af'
review_loop_iteration: 0 # incremented by step-04 before each review loopback
followup_review_recommended: false # set by step-04 on status: done; step-01 READS this — false HALTs, true allows one follow-up then forces false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-recall-in-the-loop/SPEC.md']
deferred: [] # append-only machine-readable deferred review findings; each item carries summary/evidence and optional location/severity
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Scribe's `recall`/`capture` primitive is real, shipped, and grounded (a genuine miss
is explicit, never an invented answer) — but it doesn't reach forward on its own. A correction
captured today doesn't automatically show up in the next `bmad-loop` dev pass working nearby
code; a human has to remember to run `scribe recall` and paste the result in by hand.

**Approach:** Before a `bmad-loop` dev pass (`bmad-dev-auto`) launches, `harness_bmadloop.py`
shells `scribe recall --scope <station-slug>` (CLI subprocess, never a direct `pyforge.scribe`
import — Scribe stays the sole owner of capture/compile per the parent Spec's own constraint) and,
if the answer is grounded, folds it into the dev-pass session's starting context as a
clearly-labeled block.

## Boundaries & Constraints

**Always:**
- Query scoped by `--scope <station-slug>`, reusing the mechanism `scribe-marshal-fact-visibility`
  CAP-1 already proves — never a narrower per-file-glob scope (this story's own resolution of the
  parent Spec's Open Question 1).
- One `scribe recall` subprocess call per story dispatch, run before the dev-pass session launches.
- The injected context block is clearly labeled as scribe-sourced feedback, distinguishable from
  the story's own spec/intent-contract content.
- Reach Scribe only through its CLI (`scribe recall ...` subprocess) — never `import
  pyforge.scribe`, matching this Spec's "read-only consumer" constraint.
- Scoped to `bmad-loop` dev passes only in this story — `bmad-build-auto` dispatch is explicitly
  out of scope here (this story's own resolution of Open Question 2, matching the source Dream's
  literal text).

**Never:**
- Never treat a recall failure (subprocess error, scribe unavailable) as a dispatch-blocking
  error — degrade silently to no injected context, same fail-open discipline this fleet's other
  live-query findings already use (e.g. doctor CAP-2/CAP-14).
- Never write to scribe's own capture store from this path — read-only consumer only.
- Never inject a fabricated or synthesized confidence claim when the query fails or times out —
  absence of a block is the correct behavior (Story 47.4 owns the "genuine empty hit" case; this
  story owns "the query didn't run at all," which behaves identically — no block).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Relevant feedback exists | `scribe recall --scope <slug>` returns a grounded hit for the story's station | Dev-pass session context includes the labeled feedback block before it starts working | No error expected |
| No relevant feedback | `scribe recall` returns a grounded miss (Story 47.4's own scope) | No block injected | No error expected |
| `scribe` CLI unavailable | subprocess exits non-zero or times out | No block injected; dispatch proceeds unaffected (fail-open) | Warn-level log only, never blocks dispatch |
| Story with no resolvable station slug | dispatch context lacks a station scope | Recall query skipped entirely (nothing to scope it to) | No error expected |

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-011 binding corrected 2026-09-19 — the `-k recall` scoping is a manual check below, not the declared command).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-011 binding corrected 2026-09-19 — the `-k recall` scoping is a manual check below, not the declared command).

**Manual checks:**
- `pixi run -e pyforge-marshal pyforge-marshal-test -k recall` -- expected: all new tests pass,
  covering every I/O matrix row above via fixture `scribe recall` output, not a live scribe
  process
- `pixi run -e pyforge-marshal marshal factory dispatch pyforge-doctor <a real backlog story>`
  (manual smoke, read-only recall query only) -- expected: the dispatch's own session log shows
  the recall query ran and, if scribe has a relevant entry for pyforge-doctor, that it was folded
  into context

## Auto Run Result
