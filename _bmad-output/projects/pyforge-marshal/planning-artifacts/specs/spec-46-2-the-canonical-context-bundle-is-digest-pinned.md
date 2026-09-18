---
title: '46.2: The canonical context bundle is digest-pinned'
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

**Problem:** As an operator running mixed harnesses, I want a canonical, digest-pinned context bundle extending Story 28.8's declaration half, So that every harness opens on identical bytes and prefix stability — the only portable cache — holds across Claude, Cursor, Copilot, Gemini, and Devin.

**Approach:** the 28.8 context-declaration surface extended to a canonical bundle with a recorded digest; a compare surface two harnesses can be checked against.

Ledger key: `46-2-the-canonical-context-bundle-is-digest-pinned`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-192 (story slice CAP-19(b) of the reminted CAP-192). Fold remint: `spec-marshal-token-economy` CAP-19 → CAP-192 (`spec-marshal-token-economy` absorbed).
- Living: `spec-pyforge-marshal CAP-192` ← `spec-marshal-token-economy CAP-19`.

## Acceptance Criteria

- Given two harnesses on the same commit When each assembles its opening context Then the bundles compare byte-identical by digest And a drift in either assembly is a named finding, not a silent divergence

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
| two harnesses on the same commit | each assembles its opening context | the bundles compare byte-identical by digest | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 46.2 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.
