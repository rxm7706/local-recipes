---
title: Five modules wire through the provisioning verb
type: feature
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 6da3b4089c
---

<intent-contract>

## Intent

**Problem:** `steward provision --module` only supports `bmb`; tea, cis, utility-skills, and manticore remain unwired despite being CAP-3 wire-decided modules (spec-bmad-suite-channel-product).

**Approach:** Grow `_SUPPORTED_MODULES` from `{bmb}` to `{bmb, tea, cis, utility-skills, manticore}` using each conda package's installer entry points. Each addition is manifest-recorded, skill-name-collision-checked, retired-ID guard + integrity meta tests green, reproducible on a fresh clone. Record WDS as an explicit skip-decision with the upstream-deprecation citation (absorbing into bmad-ux).

## Acceptance Criteria

- `_SUPPORTED_MODULES` includes bmb, tea, cis, utility-skills, manticore.
- Each new module provisions via `steward provision --module <name>` (manifest, collision check, retired-ID guard).
- Integrity / meta tests green; fresh-clone path covered by fixtures.
- WDS documented as skip with upstream-deprecation citation (not in `_SUPPORTED_MODULES`).
- Does not implement 15.4 native-path spot-checks or install-class wiring for method/loop/skf/labs/dashboards/template.

## Boundaries & Constraints

**Never:** Wire WDS. Never absorb bmad-method core or bmad-loop into `--module`. Never `scripts/bmad-switch`. Steward 12-7 remains skipped. Finalize steward ledger only. Do not touch marshal 19-3 / PR #677.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py` — `_SUPPORTED_MODULES`
- Conformance tests under `tests/conformance/` for provision --module
- Skip-decision note (SPEC/memlog or provision help) for WDS

## Verification

- `pixi run --frozen -e pyforge-steward pytest …` green for provision module suite
- `steward provision --list-modules` names the five; WDS absent
- CI: detectors, linter, package tests
