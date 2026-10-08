---
title: '47.2: A bmad-loop review pass sees the same scoped feedback the dev pass saw'
type: 'feature' # feature | bugfix | refactor | chore
created: '2026-09-18'
status: 'done' # draft | ready-for-dev | in-progress | in-review | done | blocked
baseline_revision: '791030287c325966410b5f4da1fca5edb72dcb44'
review_loop_iteration: 1 # incremented by step-04 before each review loopback
followup_review_recommended: false # set by step-04 on status: done; step-01 READS this — false HALTs, true allows one follow-up then forces false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-recall-in-the-loop/SPEC.md']
deferred:
  - summary: >-
      augment_bmad_loop_session_prompt_with_recall is not yet invoked from an in-tree bmad-loop session launcher; end-to-end recall in live loops still needs a caller (same integration seam as Story 47.1).
    evidence: |-
      Grep shows the helper is exercised only from tests/unit/test_harness_bmadloop_recall.py; bmad_loop site-packages has no recall hook. The story surface is the harness review-pass launch helper itself, which is implemented and unit-tested.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py:1409
    severity: medium (unverified)
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

## Review Triage Log

### 2026-10-08 — Review pass
- verdicts: 1 findings — high 0, medium 0, low 0, false 0, maybe-false 1
- findings:
  - `[maybe-false]` `[defer]` No in-tree production caller wires `augment_bmad_loop_session_prompt_with_recall` into live bmad-loop session launch yet — deferred with location on the helper; unit tests prove dev+review share one scribe call and identical cached blocks when the helper is used.

## Auto Run Result

- **Summary:** Added CAP-2 review-pass launch helper on `harness_bmadloop.py`: `augment_bmad_loop_session_prompt_with_recall` runs at most one `scribe recall` per dispatch (dev role when query marker absent), then folds the cached `recall-feedback.md` block into dev and review session prompts identically; review never re-queries. Shared formatting lives in `core/recall_feedback.py` (header mentions both passes).
- **Files changed:**
  - `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` — inject/augment/cache-read helpers and query marker
  - `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/recall_feedback.py` — query/path/render helpers (new)
  - `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop_recall.py` — dev+review parity and single-scribe-call tests (new)
  - `src/shared/packages/pyforge-marshal/tests/unit/test_recall_feedback.py` — pure helper tests (new)
  - `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-recall-in-the-loop/.memlog.md` — surface reconcile entry
  - `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md` — co-governor reconcile for `recall_feedback.py`
- **Review:** 0 patches; 1 defer (integration caller outside this story’s harness surface).
- **Verification:** `pyforge-marshal-test` pass; `pyforge-marshal-test -k recall` 54 passed; `pyforge-deps-test` 130 passed; `python scripts/spec_surface_reconcile.py` OK after memlog reconcile (no `--write-baseline`).
- **Residual risk:** Story 47.1 remains `blocked` on intent gaps (grounding + dev reader); this branch does not land spin-time inject or bmad-loop engine wiring. Live loops gain review parity only once a session launcher calls the augment helper.
