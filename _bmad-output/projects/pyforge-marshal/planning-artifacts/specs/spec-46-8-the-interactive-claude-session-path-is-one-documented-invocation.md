---
title: '46.8: The interactive Claude session path is one documented invocation'
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

**Problem:** As an operator starting an interactive Claude session on the shared checkout, I want the wrap + caveman skill + retrieve/recall discipline written once where a session actually starts, So that the convenience path runs on the same instruments as dispatch instead of re-discovering the repo.

**Approach:** the Claude-facing session docs (CLAUDE.md session-path note) naming the one invocation; dispatch remains the measured path.

Ledger key: `46-8-the-interactive-claude-session-path-is-one-documented-invocation`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: docs / S / S-46.7.

### Living CAP citations

- `spec-pyforge-marshal` CAP-195 (fold remint of `spec-marshal-token-economy` CAP-22; `spec-marshal-token-economy` is absorbed — cite living numbers).
- Living: `spec-pyforge-marshal CAP-195` ← `spec-marshal-token-economy CAP-22`.

## Acceptance Criteria

- Given an operator starts interactive Claude on the shared checkout When they follow the documented path Then the session is demonstrably wrapped or seeded per the declared `[context]` layers, and wholesale `epics.md` / PRD loads are a miss against retrieve/recall

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
| an operator starts interactive Claude on the shared checkout | they follow the documented path | the session is demonstrably wrapped or seeded per the declared `[context]` layer | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 46.8 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.
