---
title: '1.12: A stale loop home cannot be spun'
type: 'feature'
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

**Problem:** As the operator, I want preflight to refuse a loop home that is behind `main`, So that a stale baseline cannot silently switch the surface guard off.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `1-12-a-stale-loop-home-cannot-be-spun`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: feature / S / S-1.11.

### Living CAP citations

- Cited from epics.md: FR-180

## Acceptance Criteria

- Given a provisioned loop home whose HEAD is an ancestor of `origin/main` When `marshal preflight <slug>` runs Then it reports `MRS-PREFLIGHT-014` at ERROR and exits non-zero, naming both shas and printing a remedy that is runnable exactly as shown And a home whose HEAD equals `origin/main` is silent — otherwise every preflight reds and the gate stops being read And a home merely AHEAD (unlanded story merges — the ordinary mid-run state) is not refused And any probe failure yields no finding: a diagnostic must never become a refusal And FR-173's landing resync is amended to push the station branch, since provisioning reads origin and seven homes sat 33–74 commits behind there after their work had landed

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| a provisioned loop home whose HEAD is an ancestor of `origin/main` | `marshal preflight <slug>` runs | it reports `MRS-PREFLIGHT-014` at ERROR and exits non-zero, naming both shas and | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 1.12 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `736a2af407` (2026-08-09, "fix(marshal 1.12): the currency check was inert — missing import, wrong port method"); also `7a52b6da13` (2026-08-09, "marshal 1.12: a stale loop home cannot be spun"). Ledger row `1-12-a-stale-loop-home-cannot-be-spun: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md`, `scripts/.spec-surface-baseline.json`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/init.py`, `src/shared/packages/pyforge-marshal/tests/meta/test_ad11_write_boundary.py`, `src/shared/packages/pyforge-marshal/tests/unit/test_init.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
