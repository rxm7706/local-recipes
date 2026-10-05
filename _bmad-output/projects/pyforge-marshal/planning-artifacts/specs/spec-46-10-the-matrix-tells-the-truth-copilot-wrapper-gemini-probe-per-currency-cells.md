---
title: '46.10: The matrix tells the truth, copilot wrapper, gemini probe, per-currency cells'
type: 'feature'
created: '2026-09-18'
status: 'done'
baseline_revision: '93d945a4315584dba56121846b62f7e3486aa822'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** As an operator reading the multi-harness matrix, I want the output layer recorded as multi-harness (caveman's 21 targets), a verified `[wrapper]` in `copilot.toml` (headroom ships `wrap copilot`), and the Gemini wire seam probed, So that each harness × layer cell names what is real and its binding currency — and "never" appears only with evidence.

**Approach:** `data/harness_profiles/copilot.toml` `[wrapper]` declaration + one live copilot dispatch through the wrap; a dated gemini probe finding (env/proxy seam or upstream headroom target); the matrix doc corrected (output layer is multi-harness).

Ledger key: `46-10-the-matrix-tells-the-truth-copilot-wrapper-gemini-probe-per-currency-cells`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-197 (fold remint of `spec-marshal-token-economy` CAP-24; `spec-marshal-token-economy` is absorbed — cite living numbers).
- Living: `spec-pyforge-marshal CAP-197` ← `spec-marshal-token-economy CAP-24`.

## Acceptance Criteria

- Given the copilot profile declares a wrapper When a copilot dispatch launches Then `headroom wrap copilot` is on the argv and the run journals the wire layer — or the profile carries a dated finding and `auto` skips honestly And gemini's wire cell reads "probed, none" with evidence or gains a target And Devin stays the deliberate unverified stub (loud absence)

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
| the copilot profile declares a wrapper | a copilot dispatch launches | `headroom wrap copilot` is on the argv and the run journals the wire layer — or  | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 46.10 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

## Auto Run Result

Status: done

**Summary:** Packaged `copilot.toml` now declares a reversible headroom `[wrapper]` (`wrap copilot --port {wire_port} --`) so repo-default wire `"auto"` applies compression on copilot dispatches without policy edits. Gemini's wire cell is documented as probed-with-none (no upstream `wrap gemini`). The token-economy companions record output compression as multi-harness (caveman's 21 targets) in `integration-layers.md` and the new `multi-harness-matrix.md` per-harness table. Devin unchanged as the loud unverified stub.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/copilot.toml`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/gemini.toml`
- `src/shared/packages/pyforge-marshal/tests/unit/test_harness_profile.py`
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/integration-layers.md`
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/multi-harness-matrix.md`

**Verification:** `pyforge-marshal-test` (11718 passed after fix), `pyforge-deps-test` (130 passed), `python scripts/spec_surface_reconcile.py` (exit 0), `pixi run -e pyforge-guild spec-surface-check` (exit 0). Live: `headroom wrap copilot --help` and `headroom wrap gemini` probe on this host (2026-10-05); wrapped copilot launch not smoke-tested (quota — recorded in profile notes).

**Residual risks:** Copilot wrapped dispatch still consumes premium-request quota; no live end-to-end wrapped session on this machine. Gemini wire remains unavailable until headroom adds a target.
