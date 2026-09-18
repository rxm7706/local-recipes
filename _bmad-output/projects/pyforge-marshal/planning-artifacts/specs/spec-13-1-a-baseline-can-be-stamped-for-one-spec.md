---
title: '13.1: A baseline can be stamped for one spec'
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

**Problem:** As the operator, I want to settle one spec's baseline without accepting any other spec's pending drift, So that the sanctioned fix for a single finding stops destroying the evidence for 34 others.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `13-1-a-baseline-can-be-stamped-for-one-spec`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: change / S / —.

### Living CAP citations

- Cited from epics.md: FR-164, FR-167

## Acceptance Criteria

- Given a committed `scripts/.spec-surface-baseline.json` When `--write-baseline --spec <name>` runs (repeatable) Then only the named specs' entries change and every other entry is byte-identical And an unknown spec name exits 2 and prints the known set — never a silent no-op And unscoped `--write-baseline` still works, and its `--help` states plainly that it accepts every other spec's pending drift as correct And the stamp merges into the committed file rather than rewriting from the in-memory set, so a spec absent from this invocation is not silently dropped And a mutation test proves the guard both ways: removing the scoping re-reds the isolation test, restoring it passes

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| a committed `scripts/.spec-surface-baseline.json` | `--write-baseline --spec <name>` runs (repeatable) | only the named specs' entries change and every other entry is byte-identical | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 13.1 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.
