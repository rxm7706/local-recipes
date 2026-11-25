---
title: '136.8: The seven atlas gate tasks run in atlas''s own environment'
type: 'fix'
created: '2026-11-25'
status: 'ready-for-dev'
story: 136-8-the-seven-atlas-gate-tasks-run-in-atlas-s-own-environment
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'pixi.toml'
  - 'pixi.lock'
  - 'environment.yaml'
  - '_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/gate-contract.md'
  - 'src/shared/packages/pyforge-atlas/tests/**'
  - 'src/shared/packages/pyforge-atlas/AGENTS.md'
  - 'docs/**'
  - '.github/workflows/**'
  - '_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-atlas-46-1-4`. Seven atlas gate tasks sit in `[feature.local-recipes.tasks]`, so they run only in `-e local-recipes`. CI already runs the wasm build and these suites in `-e pyforge-atlas`. Steward declined the move in the 2026-11-10 change because that change made no estate change; that change has landed.

**Approach:** For each of the seven, first run it (or its `--help` or dry form, for `dashboard-serve` and the two `publish` tasks, which are not run for effect here) in `-e pyforge-atlas` and record whether every command and import it needs resolves there. Move each task that does to `[feature.pyforge-atlas.tasks]`, byte-identical but for its table name. A task whose dependencies `pyforge-atlas` does not solve stays where it is, is named in the change log, and is not fixed by adding a dependency: an estate pin is the estate-refresh lane's. Then move the rows of `gate-contract.md` (its meta-test names them), re-point every doc, workflow and test that names `-e local-recipes` for a moved task, regenerate `environment.yaml` by `pyforge steward estate reconcile` if `pixi.toml`'s dependency tables changed, and check the lock with the pinned pixi and `pixi lock --check`.

Ledger key: `136-8-the-seven-atlas-gate-tasks-run-in-atlas-s-own-environment`.

### Living CAP citations

- spec-pyforge-steward CAP-5 (`pyforge-guild` and each station's own environment, never `local-recipes`, carry station work; realized, no text change); reads `spec-pyforge-atlas:CAP-50` and `spec-pyforge-atlas:CAP-69` (their `gate-contract.md` table moves with the tasks; no capability text change); no AD moves.

## Boundaries & Constraints

**Always:**
- Reproduce what the row reports on the unchanged tree before changing it, and record the reproduction in the Spec Change Log.
- Append the surface reconcile to the memlog of each Spec that governs a moved file before the scoped stamps.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never add, move or re-pin a dependency.
- Never run `pixi update` or `pixi add`.
- Never run `publish` or `publish-range` for effect.
- Never add a flag, a capability or an architecture decision; a fix that would need one stops and is reported.

## Acceptance Criteria

**Given** `DW-atlas-46-1-4` reports seven atlas gate tasks that run only in `-e local-recipes`, and the change that held them there has landed
**When** each task whose dependencies `pyforge-atlas` already solves is moved to `[feature.pyforge-atlas.tasks]` unchanged, and `gate-contract.md` and every caller name the new environment
**Then** each moved task resolves and runs in `-e pyforge-atlas`, is no longer defined under `feature.local-recipes`, and `gate-contract.md`'s table and its meta-test agree with `pixi.toml`
**And** no dependency is added or moved, the lock is unchanged or passes `pixi lock --check` with the pinned pixi, a task that could not move is named with its reason, and the row reads resolved or names what is left

- **AC1 — No moved task is still defined under the recipe-factory feature.** Expected: prints the tasks left behind, each named in the change log.

  ```bash
  grep -n -E '^\[feature\.local-recipes\.tasks\.(dashboard-dryrun|dashboard-serve|vizro-ai-dryrun|publish|publish-range|wasm-build|wasm-smoke)\]' pixi.toml
  ```

- **AC2 — Atlas's package suite holds, the gate-contract meta-test with it.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-atlas pyforge-atlas-test
  ```

- **AC3 — The task registry is consistent.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild target-version-check
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-5 (`pyforge-guild` and each station's own environment, never `local-recipes`, carry station work; realized, no text change); reads `spec-pyforge-atlas:CAP-50` and `spec-pyforge-atlas:CAP-69` (their `gate-contract.md` table moves with the tasks; no capability text change); no AD moves.
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-25 entry (the rows a lapsed blocker held close); operator ruling of 2026-11-25: "All 22 rows".
- Epic: Epic 136, minted with this story.
- Ledger key: `136-8-the-seven-atlas-gate-tasks-run-in-atlas-s-own-environment`.
- Deferred-work row: `DW-atlas-46-1-4`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."136"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry (the rows a lapsed blocker held close) and the operator's ruling of the same date. Not implemented.
