---
title: '23.5: Archive citations for the five already-moved _bmad-output/ files'
type: 'fix'
created: '2026-09-16'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Five files already live under archive/_bmad-output/ and inbound citations still use the old root path.

**Approach:** Rewrite those citations. No live doc cites the old _bmad-output/ root path for those five files.

## Boundaries & Constraints

**Always:**
- No live doc cites the old _bmad-output/ root path for those five files.

**Never:**
- Do not move the archived files back to the root.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| old citation | _bmad-output/DREAM-TRIAGE-2026-08-08.md | points at archive/_bmad-output/… | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-docs-shelf-alignment CAP-5`.
Surface: docs/intake/README.md; station planning-artifacts/specs/README.md files that still cite the old root paths..
Ledger key: `23-5-archive-citations-for-the-five-already-moved-_bmad-output-files`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-5-archive-citations-for-the-five-already-moved-_bmad-output-files.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

