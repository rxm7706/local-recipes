---
title: One command proves the upgrade landed
type: feature
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 667ed9003f
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
