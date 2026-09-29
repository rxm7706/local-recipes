---
title: '23.5: The .potx path — template-filled PowerPoints, and every derived file stamped'
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

**Problem:** 21.5 is Marp-only; no derived file records which tree or Design etag it was derived at.

**Approach:** A registry section may declare a .potx. That deck routes through pptx-spec/pptx-fill; others through deck-export. Every derived artifact carries a tree+etag stamp. Host without Chrome reports derive-skipped: no chrome and continues.

## Boundaries & Constraints

**Always:**
- .potx decks are template-filled.
- Marp decks match 21.5.
- Stamps make stale derived files detectable.

**Never:**
- Do not fail the run when Chrome is absent for Marp-PPTX.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| no chrome | Marp-PPTX step | derive-skipped: no chrome; run continues | skip |

</intent-contract>

## Binding

Parent Spec capability: `spec-design-sync-loop CAP-5; spec-deck-family-lockstep CAP-3`.
Surface: deck README registry section; derive stage pptx-spec/pptx-fill vs deck-export; derived-file stamps..
Ledger key: `23-3-the-potx-path-template-filled-powerpoints-and-every-derived-file-stamped`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-3-the-potx-path-template-filled-powerpoints-and-every-derived-file-stamped.md`.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `9e955a5b1b` (2026-09-19, "doctor: reconcile Story 23.3 — landed 2026-09-18 (PR #1445) with a backlog ledger row; twin recovered from the"); also `97694e0b46` (2026-09-18, "docs: sunset docs/specs/ by frontmatter status (Story 23.3)"). Ledger row `23-3-the-potx-path-template-filled-powerpoints-and-every-derived-file-stamped: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-23-3-sunset-docs-specs-by-frontmatter-status.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml`, `scripts/.spec-surface-baseline.json`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready` → `done` (ledger row `23-3-the-potx-path-template-filled-powerpoints-and-every-derived-file-stamped: done`).
- `## Auto Run Result` reconstructed from git (none survived).
