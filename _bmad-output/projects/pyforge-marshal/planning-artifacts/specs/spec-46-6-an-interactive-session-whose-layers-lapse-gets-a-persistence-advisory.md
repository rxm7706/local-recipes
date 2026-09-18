---
title: '46.6: An interactive session whose layers lapse gets a persistence advisory'
type: 'feature'
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

**Problem:** As an operator on the interactive path, I want a persistence advisory when a session's declared layers would lapse, So that silent savings do not silently stop.

**Approach:** the session-path advisory surface (journal + session-close output).

Ledger key: `46-6-an-interactive-session-whose-layers-lapse-gets-a-persistence-advisory`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / S-46.4.

### Living CAP citations

- `spec-pyforge-marshal` CAP-193 (fold remint of `spec-marshal-token-economy` CAP-20; `spec-marshal-token-economy` is absorbed — cite living numbers).
- Living: `spec-pyforge-marshal CAP-193` ← `spec-marshal-token-economy CAP-20`.

## Acceptance Criteria

- Given an interactive session whose `[context]` layers were active When the session ends or the layers lapse Then the journal carries a persistence advisory naming what lapsed

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
| an interactive session whose `[context]` layers were active | the session ends or the layers lapse | the journal carries a persistence advisory naming what lapsed | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 46.6 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.
