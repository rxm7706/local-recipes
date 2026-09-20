---
title: '3.10: Unpushed work is measured by tip, never by name'
type: 'change'
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

**Problem:** As the operator, I want `unpushed-work-check` to compare tips rather than branch names, So that a branch whose remote copy is stale stops reporting as safe.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `3-10-unpushed-work-is-measured-by-tip-never-by-name`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: change / S / —.

### Living CAP citations

- Cited from epics.md: FR-171

## Acceptance Criteria

- Given a local branch whose name exists on origin but whose remote tip is behind When `unpushed-work-check` runs Then it is reported as unpushed work, with the count of commits the remote lacks And station branches (`loop/*`) are in scope — they are exactly the long-lived branches whose name always exists remotely and whose tip silently falls behind between runs And a branch whose remote tip matches, or which is an ancestor of the remote, is still silent — the fix must not turn every branch into a finding And a regression test replays the live case: `loop/pyforge-doctor` on origin at `3f43f486c9` with the local branch 8 commits ahead reported clean under the name check, and reports under the tip check

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| a local branch whose name exists on origin but whose remote tip is behind | `unpushed-work-check` runs | it is reported as unpushed work, with the count of commits the remote lacks | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 3.10 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `3-10-unpushed-work-is-measured-by-tip-never-by-name: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
