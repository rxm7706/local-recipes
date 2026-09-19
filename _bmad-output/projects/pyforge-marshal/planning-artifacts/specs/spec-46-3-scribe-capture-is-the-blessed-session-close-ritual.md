---
title: '46.3: `scribe capture` is the blessed session-close ritual'
type: 'docs'
created: '2026-09-18'
status: 'backlog'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** As an operator who wants memory write-back from every harness, I want `scribe capture` named in the front-door docs as the harness-neutral session-close ritual, So that what a session learned lands in the shared substrate no matter which harness ran it.

**Approach:** AGENTS.md / CLAUDE.md / the station skill notes — the same docs that name the front door — plus one line in each harness profile's notes.

Ledger key: `46-3-scribe-capture-is-the-blessed-session-close-ritual`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: docs / S / S-46.7.

### Living CAP citations

- `spec-pyforge-marshal` CAP-192 (story slice CAP-19(c) of the reminted CAP-192). Fold remint: `spec-marshal-token-economy` CAP-19 → CAP-192 (`spec-marshal-token-economy` absorbed).
- Living: `spec-pyforge-marshal CAP-192` ← `spec-marshal-token-economy CAP-19`.

## Acceptance Criteria

- Given a session closes in any harness When the operator or agent follows the front-door docs Then the close ritual is `scribe capture` with decision-grade facts, and the docs say so in one place And capture hygiene is stated: no secrets, decision-grade facts only

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.
- Do not cite absorbed `spec-marshal-token-economy` CAP-19..24 as living numbers; use CAP-192..197.
- Do not flip the parent Dream to `realized` (benchmark artifact is the realized-guard).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| a session closes in any harness | the operator or agent follows the front-door docs | the close ritual is `scribe capture` with decision-grade facts, and the docs say | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 46.3 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).
