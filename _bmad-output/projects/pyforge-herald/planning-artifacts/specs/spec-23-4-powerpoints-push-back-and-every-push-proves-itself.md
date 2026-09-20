---
title: '23.6: PowerPoints push back, and every push proves itself'
type: 'feature'
created: '2026-09-16'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** deck push skips both PPTX (Story 5.1 deferral) and read-back is a hand curl-and-strip.

**Approach:** Prove a binary write_files shape on one PPTX and adopt it for the pair. Push reads every pushed file back through the serve URL with harness stripped. Read-back mismatch is a refusal that names the file.

## Boundaries & Constraints

**Always:**
- Read-back is byte-identical for 100% of pushed files.
- Second push pushes nothing.

**Never:**
- Do not warn on a read-back mismatch — refuse and name the file.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| mismatch | serve bytes != pushed bytes | refuse naming the file | refuse |

</intent-contract>

## Binding

Parent Spec capability: `spec-design-sync-loop CAP-6`.
Surface: herald/deck_pipeline.py push_exports PPTX pair + --prove; state.py; README ledger etag row..
Ledger key: `23-4-powerpoints-push-back-and-every-push-proves-itself`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-4-powerpoints-push-back-and-every-push-proves-itself.md`.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `7920fb2afa` (2026-09-19, "doctor: Story 23.4 landing record — memlog + scoped stamp"); also `b48896ff58` (2026-09-19, "doctor: Story 23.4 — empty the intake inbox per its own README"). Ledger row `23-4-powerpoints-push-back-and-every-push-proves-itself: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md`, `scripts/.spec-surface-baseline.json`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready` → `done` (ledger row `23-4-powerpoints-push-back-and-every-push-proves-itself: done`).
- `## Auto Run Result` reconstructed from git (none survived).
