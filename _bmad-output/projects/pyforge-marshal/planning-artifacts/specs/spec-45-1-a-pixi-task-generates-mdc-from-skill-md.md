---
title: '45.1: a pixi task generates .mdc from SKILL.md'
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

**Problem:** Cursor chat had no mechanical .mdc for the bmad-build / bmad-build-auto pilot.

**Approach:** scripts/bmad_cursor_mdc_check.py --write derives .cursor/rules/*.mdc from SKILL.md frontmatter plus the two-step trigger. Pixi task bmad-cursor-mdc-generate.

</intent-contract>

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `6d092e571c` (2026-09-05, "suite(pin): bmad-eval-quality >=0.2.0.dev0 in the unix target tables, WDS pin dropped; Story 45.1 done"). Ledger row `45-1-a-pixi-task-generates-mdc-from-skill-md: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/.memlog.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pixi-candidate-currency/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-install-class-wiring/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-install-class-wiring/install-class-playbook.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-mcp-era-isolation/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-platform-image-one-pixi-env/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `docs/dreams/bmad-eval-quality.md`, `docs/reference/library-llms-full.md` (+6 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
