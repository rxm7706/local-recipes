---
title: '46.5: The journal splits silent saves from configured layers, and the rollup speaks per-harness currency'
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

**Problem:** As an operator reading savings, I want the journal taxonomy to distinguish silent saves (repo default) from configured layers, and the rollup keyed per harness × binding currency, So that a Cursor-first station never reads a Claude-shaped number as its own — USD for Claude, quota-burn for Cursor/Copilot, request-count for Gemini, ACUs for Devin, never one blended token number.

**Approach:** `core/layer_savings_sources.py` journal schema and the rollup report surface.

Ledger key: `46-5-the-journal-splits-silent-saves-from-configured-layers-and-the-rollup-speaks-per-harness-currency`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / S-46.4.

### Living CAP citations

- `spec-pyforge-marshal` CAP-193 (fold remint of `spec-marshal-token-economy` CAP-20; `spec-marshal-token-economy` is absorbed — cite living numbers).
- Living: `spec-pyforge-marshal CAP-193` ← `spec-marshal-token-economy CAP-20`.

## Acceptance Criteria

- Given runs on at least two harnesses with different binding currencies When the rollup renders Then each harness's savings appear in their own currency with no blended total And silent saves and configured layers are distinguishable per journal row

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
| runs on at least two harnesses with different binding currencies | the rollup renders | each harness's savings appear in their own currency with no blended total | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 46.5 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.
