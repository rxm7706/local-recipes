---
title: '40.4: No document still frames it as a separate thing'
type: 'docs'
created: '2026-09-18'
status: 'done'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** As a fleet operator, I want every `Satellite: Genesis Installer` header and separate-thing prose removed from the planning tree, So that the retirement is real in the documents, not only in the numbering.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `40-4-no-document-still-frames-it-as-a-separate-thing`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: docs / M / S-40.2.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-120` ← `spec-genesis-installer-name-retirement CAP-6`.

## Acceptance Criteria

- Given the 2026-08-02 consolidation left satellite framing in place When this story lands Then `grep -i "genesis.installer"` across `{prds,architecture,specs,briefs}` returns nothing outside `archive/` and memlogs

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the 2026-08-02 consolidation left satellite framing in place | this story lands | `grep -i "genesis.installer"` across `{prds,architecture,specs,briefs}` returns  | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 40.4 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `40-4-no-document-still-frames-it-as-a-separate-thing: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
