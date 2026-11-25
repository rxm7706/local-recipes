---
title: '136.8: The seven atlas gate tasks run in atlas''s own environment'
type: 'fix'
created: '2026-11-25'
status: 'in-review'
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
- 2026-11-25: reproduced on the unchanged tree: the AC1 grep printed all seven tables under `feature.local-recipes` (`dashboard-serve`, `dashboard-dryrun`, `vizro-ai-dryrun`, `wasm-build`, `wasm-smoke`, `publish`, `publish-range`), and `gate-contract.md` named `local-recipes` for four rows and three no-pytest tasks.
- 2026-11-25: probes in `-e pyforge-atlas`, each command run by hand with its task's `PYTHONPATH` before the move, each read from its exit code: `dashboard-dryrun` exit 0 (200 passed, none skipped); `vizro-ai-dryrun` exit 0 (27 passed); `wasm-build` exit 0 (npm and node resolve in the environment; the artifact built); `wasm-smoke` exit 0 with its one test skipped (`no Chromium executable under PLAYWRIGHT_BROWSERS_PATH`, a machine provisioning gap that no environment changes; playwright imports); `dashboard-serve` not served: `python scripts/dashboard_serve.py --help` exit 0; `publish` not run: `import pyforge.atlas.publish, pyforge.atlas.publish.__main__, duckdb, pyarrow` exit 0; `publish-range` not run: `pytest tests/integration/publish --collect-only` exit 0, 13 tests collected.
- 2026-11-25: moved all seven tables to `[feature.pyforge-atlas.tasks]`, after `pyforge-atlas-build`; none stayed behind. One deviation from byte-identical: `dashboard-dryrun`'s description said "Runs in local-recipes (the env carrying vizro + boring_semantic_layer)" and now says `pyforge-atlas`; every `cmd` and `env` is unchanged. No dependency table changed, so `environment.yaml` was not regenerated; `pixi lock --check` exit 0 and `pixi.lock` is unmodified (local pixi 0.84.2, not the pinned 0.80.0: the pinned-pixi check is CI's).
- 2026-11-25: `gate-contract.md`: the four gate rows, the three no-pytest entries and the paragraph above the table name `pyforge-atlas`. Re-pointed: `docs/reference/agent-instruction-notes.md`, `docs/explanation/enterprise-deployment.md`, atlas `tests/integration/wasm/test_wasm_smoke.py` (its not-built message), `tests/integration/dashboard/test_vizro_static_export_flag.py` (docstring), `docs/how-to/pixi-tasks.md` and `docs/map.yaml` (regenerated by `docs-pixi-tasks`). Outside this story's declared surface, re-pointed because each told a reader to run a moved task in the old environment: `scripts/dashboard_serve.py`, atlas `wasm/README.md`, `wasm/build.py`, `src/pyforge/atlas/publish/__main__.py`, atlas `test-design-qa.md`. No workflow named `-e local-recipes` for a moved task. Atlas `AGENTS.md` names no environment for these gates and is unchanged.
- 2026-11-25: left as written: atlas `SPEC.md` (never hand-edited; its lines still cite `-e local-recipes` for these gates and need a memlog entry and `bmad-spec`), the dated entries of `docs/dreams/pyforge-atlas.md`, earlier story specs and the 2026-11-10 audit (records of their date), every ledger, epics file and memlog. The governing Specs' memlog reconcile and scoped stamps are not done here. `DW-atlas-46-1-4` is not edited here; nothing is left on it but those citations.
- 2026-11-25: AC1: the grep prints nothing (exit 1, no task left behind). AC2: `pyforge-atlas-test` exit 3 on its one run: the first segment reported 2974 passed, 27 skipped, then pytest-xdist raised INTERNALERROR from coverage (`sqlite3.OperationalError: no such table: file`) while other `pytest --cov` runs shared this worktree's `.coverage`; the second segment, which the `&&` never reached, run by hand exit 0 (53 passed, 5 skipped). The suite was not run a second time, so AC2 has no exit 0 yet and needs one uncontended run. `tests/meta/test_catalog_contract.py` (live-tree half) exit 0, 5 passed. AC3: `target-version-check` exit 0. `governance-currency` exit 0.
