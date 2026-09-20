---
title: '45.2: a drift detector fails a stale generated .mdc'
type: 'feature'
created: '2026-09-16'
status: 'done'
baseline_revision: 'a799295fd6'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** A generated .mdc can rot the first time SKILL.md changes.

**Approach:** Same script without --write is a scope=repo detector (bmad-cursor-mdc-check) discovered by scripts/detectors.py.

</intent-contract>

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `8d84e2fdb4` (2026-09-07, "feat(steward): Story 45.2 -- measure edge-case-hunter against a planted defect"). Ledger row `45-2-a-drift-detector-fails-a-stale-generated-mdc: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/.memlog.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pixi-candidate-currency/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-eval-quality/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-eval-quality/SPEC.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-eval-quality/pilot-contract.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-mcp-era-isolation/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-platform-image-one-pixi-env/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `evals/review-catches-planted-defect/README.md`, `evals/review-catches-planted-defect/arms/clean.diff` (+15 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
