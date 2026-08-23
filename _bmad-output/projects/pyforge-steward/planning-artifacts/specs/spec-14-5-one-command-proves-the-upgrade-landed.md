---
title: One command proves the upgrade landed
type: feature
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 56e440cc2aaa8c4d4077a667292f75746b871702
deferred:
  - summary: >-
      Trap 8 (.git/info/exclude stale shield lines) is not automated in prove-landed.
    evidence: |-
      failure-modes.md lists trap 8 under CAP-5 orbit, but story ACs only require
      drift integrity + CFE meta + loop-home init/validate. Hand cleanup remains.
    location: >-
      upgrade.py CAP-5 gates
    severity: low
---

<intent-contract>

## Intent

**Problem:** After a bmad-core apply there is no single command that proves the upgrade landed (spec-bmad-method-core-upgrade CAP-5); operators still run an ad-hoc 2026-08-21 checklist by hand.

**Approach:** Extend the steward upgrade duty so one command runs the repo's own gates — bmad-drift-check integrity, CFE skill meta-tests, per-loop-home `bmad-loop init` relay refresh + `validate` — and reports a single verdict. The 2026-08-21 checklist (8/8 homes validate clean, zero warnings) is the reproduced worked example.

## Acceptance Criteria

- One command post-apply runs: bmad-drift-check integrity, CFE skill meta-tests, per-loop-home `bmad-loop init` relay refresh + `validate`.
- Reports a single overall verdict.
- Fixture/worked-example path covers the 2026-08-21 8/8-homes-clean shape (or a scaled fixture equivalent).
- Report-only gates do not mutate foreign station trees beyond documented relay refresh.

## Boundaries & Constraints

**Never:** Implement Epic 15 channel-product stories. Never `scripts/bmad-switch` from parallel agents. Steward 12-7 remains skipped. Finalize steward ledger only.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py` — prove-landed orchestrator
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — prove/verify verb
- Calls out to existing `bmad-drift-check`, CFE meta-tests, loop-home validate
- Unit tests under `pyforge-steward/tests/`

## Verification

- `pixi run --frozen -e pyforge-steward pytest …` green
- Single-verdict fixture for clean vs failing gate
- CI: detectors, linter, package tests

## Review Triage Log

### 2026-08-23 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 1, low 1)
- defer: 1: (high 0, medium 0, low 1)
- reject: 0
- addressed_findings:
  - `[low]` `[patch]` Removed duplicate `Mapping` import from `typing` (kept `collections.abc`).
  - `[medium]` `[patch]` Added `verify` CLI alias matching Code Map prove/verify verb.

## Auto Run Result

Status: done

Summary: CAP-5 `steward upgrade prove-landed` (alias `verify`) runs bmad-drift integrity (`factory.gather` HARD/FAIL), CFE meta-test `test_bmad_artifacts_in_sync`, and per-loop-home `bmad-loop init` + `validate`, then emits a single pass/fail verdict. Default init is the only documented foreign-tree mutation; `--no-init` is validate-only.

Files changed:
- `upgrade.py` — GateResult / ProveLandedReport + orchestrator runners
- `cli.py` — prove-landed + verify verbs
- `tests/unit/test_upgrade_prove_landed.py` — 8/8 clean fixture, failing-gate, CLI JSON
- this spec — status/review/finalize

Review: 2 patches applied; 1 deferred (trap 8 exclude cleanup); followup_review_recommended=false (score 3×1 medium + 1×1 low = 4 < 5).

Verification: `pixi run --frozen -e pyforge-steward pytest …/test_upgrade_*.py` → 39 passed.
