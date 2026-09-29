---
title: '13.6: The presumed set is worked down by measurement'
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

**Problem:** As the operator, I want the 994 `[drift-presumed]` entries dispositioned rather than carried, So that the informational channel stays small enough to read and a new entry means something.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `13-6-the-presumed-set-is-worked-down-by-measurement`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: change / M / S-13.2, S-13.5.

### Living CAP citations

- Cited from epics.md: FR-169

## Acceptance Criteria

- Given the 994 entries across four station Specs When each is traced to the commit that last moved it Then the set is partitioned `added` (baseline lag) vs `changed` (the per-file question), and the counts are measured, never estimated — 932 / 62 / 0, with 994/994 traced And every cluster is judged against its own Spec's capabilities, and that judgment is recorded in that Spec's memlog before any stamp — a stamp is honest only after the judgment, and the two orders are indistinguishable in the resulting number And anything moved by a story that is not `done`, or landing outside a contracted capability, is reported rather than stamped (measured: zero such files) And herald's 751 `presentations/` entries (15 deck clusters) are judged against HER-9, which contracts that corpus — not waved through on the strength of being the biggest cluster And no entry is cleared by naming 994 literal paths in a memlog: that satisfies the matcher and records nothing And the four Specs are scoped-stamped individually, each verified to change only its own baseline key And `spec-surface-check` reports 0 findings and 0 `[drift-presumed]`, with a before/after diff proving no gating `[drift]` was absorbed

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the 994 entries across four station Specs | each is traced to the commit that last moved it | the set is partitioned `added` (baseline lag) vs `changed` (the per-file questio | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 13.6 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `435e367cfe` (2026-08-08, "marshal 13.6: the presumed set is worked down by measurement"). Ledger row `13-6-the-presumed-set-is-worked-down-by-measurement: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md`, `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-surface-drift-reconciliation/SPEC.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/.memlog.md`, `docs/dashboard/data.js`, `docs/dreams/surface-drift-reconciliation.md`, `scripts/.spec-surface-baseline.json`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
