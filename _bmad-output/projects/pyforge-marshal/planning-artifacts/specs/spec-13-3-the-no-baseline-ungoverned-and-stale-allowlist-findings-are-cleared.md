---
title: '13.3: The no-baseline, ungoverned and stale-allowlist findings are cleared'
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

**Problem:** As the operator, I want the 27 mechanically-clearable findings dispositioned, So that what remains is only the drift that needs real judgment.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `13-3-the-no-baseline-ungoverned-and-stale-allowlist-findings-are-cleared`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: change / M / S-13.1.

### Living CAP citations

- Cited from epics.md: FR-166

## Acceptance Criteria

- Given S-13.1's scoped stamp When the 24 `[no-baseline]` specs are registered Then each is stamped individually, and no `[drift]` finding disappears as a side effect — verified by diffing the finding set before and after And the two `[ungoverned]` files (`docs/governance/spec-pyforge-charter/{SPEC.md,.memlog.md}`) are given a surface or an allowlist entry, with the choice recorded (this is the Spec's own open question — the Charter defines the chain this detector polices) And the `[stale-allowlist]` entry `pixi.toml` is removed And anything that cannot be honestly cleared is filed as deferred work with its reason, never suppressed

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| S-13.1's scoped stamp | the 24 `[no-baseline]` specs are registered | each is stamped individually, and no `[drift]` finding disappears as a side effe | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 13.3 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `b3b2892297` (2026-08-08, "marshal 13.3 + 13.4: the spec-surface gate goes green, honestly"). Ledger row `13-3-the-no-baseline-ungoverned-and-stale-allowlist-findings-are-cleared: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-durable-runs/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-factory-console/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-fidelity-enforcement/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-team-memory/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md`, `docs/dashboard/data.js`, `scripts/.spec-surface-baseline.json`, `scripts/spec_surface_allowlist.txt`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
