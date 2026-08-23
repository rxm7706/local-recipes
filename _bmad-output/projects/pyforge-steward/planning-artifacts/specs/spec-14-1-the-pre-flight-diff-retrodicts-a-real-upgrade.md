---
title: The pre-flight diff retrodicts a real upgrade
type: feature
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: a6ad8c41256
---

<intent-contract>

## Intent

**Problem:** BMAD-METHOD core upgrades are manual one-offs; there is no report-only pre-flight that lists what a target release would change before apply (`spec-bmad-method-core-upgrade` CAP-1).

**Approach:** Add a steward report-only upgrade pre-flight command that, given installed `_bmad/_config/manifest.yaml` and a target bmad-method release, lists skill adds/removes/renames (shim disposition + `removals.txt` deletions), upstream-touched files the repo has locally modified, `_bmad/custom/**` overrides that stop applying (legacy-name unattended-halt trap), and new hard prerequisites. Fixture: pointed at the 6.10.0→6.11.0 pair, retrodicts the 2026-08-21 findings (failure-modes.md traps 1–4, 9, 11).

## Acceptance Criteria

- Report-only command (no apply/mutate) lists skill adds/removes/renames with shim disposition and `removals.txt` deletions.
- Reports upstream-touched files that the repo has locally modified.
- Reports `_bmad/custom/**` overrides that would stop applying (legacy-name unattended-halt trap).
- Reports new hard prerequisites for the target release.
- Fixture test: 6.10.0→6.11.0 pair retrodicts failure-modes.md traps 1–4, 9, 11.

## Boundaries & Constraints

**Never:** Implement apply/branched upgrade (Story 14.2+). Never mutate `_bmad/` or custom surfaces in this story. Verb naming may extend `steward provision` or introduce `steward upgrade bmad-core` — pick one and document. Detection of "you're behind" stays doctor's; this is steward's pre-flight report surface.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/` — new upgrade duty + CLI
- `spec-bmad-method-core-upgrade/SPEC.md` CAP-1 + `failure-modes.md` traps 1–4, 9, 11
- Fixture: 6.10.0→6.11.0 retrodiction

## Verification

- `pixi run --frozen -e pyforge-steward pytest` targeting the new pre-flight tests
- Fixture asserts trap retrodiction for 6.10→6.11
