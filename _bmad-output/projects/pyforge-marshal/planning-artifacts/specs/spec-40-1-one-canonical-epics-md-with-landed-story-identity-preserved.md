---
title: '40.1: One canonical epics.md, with landed story identity preserved'
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

**Problem:** As a fleet operator, I want `epics-genesis-installer.md` merged into one `epics.md` and archived rather than deleted, with every already-landed story key unchanged, So that the second epics document stops existing without rewriting delivered history.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `40-1-one-canonical-epics-md-with-landed-story-identity-preserved`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: docs / M / —.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-115` ← `spec-genesis-installer-name-retirement CAP-1`.

## Acceptance Criteria

- Given a second epics document existed alongside the canonical one When this story lands Then one `epics.md` remains and the old file is archived, not deleted And every `status=done` key is identical after the rewrite; only backlog-only epics are free to be restructured

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| a second epics document existed alongside the canonical one | this story lands | one `epics.md` remains and the old file is archived, not deleted | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 40.1 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `40-1-one-canonical-epics-md-with-landed-story-identity-preserved: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
