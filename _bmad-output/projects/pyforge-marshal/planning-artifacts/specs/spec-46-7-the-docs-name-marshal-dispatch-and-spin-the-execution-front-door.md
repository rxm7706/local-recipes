---
title: '46.7: The docs name marshal dispatch and spin the execution front door'
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

**Problem:** As an agent choosing how to run a story, I want AGENTS.md / CLAUDE.md / station skill notes to name `marshal factory dispatch` / `spin` as the default execution path and bare `bmad-build-auto` as the sanctioned-but-unmeasured path, So that the instrumented path is the default and the bare path is a conscious choice.

**Approach:** AGENTS.md, CLAUDE.md, and the bmad-build-auto skill note; an advisory (never gating) doctor detector may flag a bare dispatch.

Ledger key: `46-7-the-docs-name-marshal-dispatch-and-spin-the-execution-front-door`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: docs / S / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-194 (fold remint of `spec-marshal-token-economy` CAP-21; `spec-marshal-token-economy` is absorbed — cite living numbers).
- Living: `spec-pyforge-marshal CAP-194` ← `spec-marshal-token-economy CAP-21`.

## Acceptance Criteria

- Given an agent reads the repo's entry docs When it chooses an execution path for a story Then the docs point at marshal dispatch/spin as default and explain what the bare path forgoes (the layers, the journal, the benchmark) And nothing new turns red in CI because of this story

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
| an agent reads the repo's entry docs | it chooses an execution path for a story | the docs point at marshal dispatch/spin as default and explain what the bare pat | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 46.7 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).
