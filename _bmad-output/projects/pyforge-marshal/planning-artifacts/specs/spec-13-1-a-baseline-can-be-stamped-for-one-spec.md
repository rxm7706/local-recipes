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

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `22a76e3bd2` (2026-08-08, "marshal 13.1 + 13.2: the spec-surface gate becomes clearable and trustworthy"). Ledger row `13-1-a-baseline-can-be-stamped-for-one-spec: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.claude/skills/conda-forge-expert/tests/meta/test_spec_surface_check.py`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-regenerable-factory/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-surface-drift-reconciliation/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml`, `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-packaging-factory/.memlog.md`, `docs/dashboard/data.js`, `scripts/spec_surface_check.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
