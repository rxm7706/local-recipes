---
title: '136.6: The tests that ran in no CI job run in one'
type: 'fix'
created: '2026-11-25'
status: 'ready-for-dev'
story: 136-6-the-tests-that-ran-in-no-ci-job-run-in-one
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - '.github/workflows/lint-types.yml'
  - '.github/workflows/pyforge-station-tests.yml'
  - 'pixi.toml'
  - 'environment.yaml'
  - 'src/shared/packages/pyforge-steward/tests/unit/test_provision_module_installers.py'
  - 'src/shared/packages/pyforge-scribe/tests/meta/test_live_tree_split.py'
  - 'src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_plane.py'
  - 'src/shared/packages/pyforge-scribe/tests/meta/test_first_portal_slice.py'
  - 'docs/reference/github-workflows.md'
  - 'docs/governance/**'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md'
  - '_bmad-output/projects/pyforge-scribe/planning-artifacts/deferred-work-ledger.md'
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

**Problem:** `DW-steward-cutover-2026-11-10-8`, `DW-steward-cutover-2026-11-10-12`, `DW-scribe-cutover-2026-11-10-2`. Seven tests run in no CI job. Steward's `test_live_share_skill_names_are_disjoint_across_installer_modules` and `test_live_utility_skills_share_tree_matches_the_ten_expected_names` read `.pixi/envs/pyforge-guild/share` and skip in the steward job, whose environment has no bmad share package. Scribe's four plane GraphStore round trips (`tests/unit/test_graph_store_plane.py`) `importorskip` duckdb and `pyforge.atlas.duckdb_writer`, and its portal render test (`tests/meta/test_first_portal_slice.py`) `importorskip`s django; none is installed in `-e pyforge-scribe`.

**Approach:** Operator ruling 2026-11-25: "No new lane". Add steps to jobs that already install the needed environment, and add no job, no ci-surfaces row and no dependency. The two steward tests run as a step of a job that already installs `pyforge-guild`; the five scribe tests run as a step of the job that already installs `pyforge-foundry-full`, which carries scribe with duckdb, pyforge-atlas and django. Each step names its tests by node id, and fails when one of them skips (`-rs` read back, or `--strict` on a skip count), so a later import change cannot turn the step into a silent pass. First prove locally that each test passes, not skips, in the environment chosen; if `pyforge-foundry-full` does not carry one of the imports, stop and record it rather than add a dependency. Give each a pixi task so the local run and CI run the same command, and correct the skip reasons and scribe's skip-site guard so they say where the tests run.

Ledger key: `136-6-the-tests-that-ran-in-no-ci-job-run-in-one`.

### Living CAP citations

- spec-pyforge-steward CAP-175 (a station suite runs once, as its two halves) and CAP-166 (every pausable CI surface is declared once; no row is added, by the operator ruling of 2026-11-25 "No new lane"); reads `spec-pyforge-scribe:CAP-26` (no text change); no AD moves.

## Boundaries & Constraints

**Always:**
- Reproduce what the row reports on the unchanged tree before changing it, and record the reproduction in the Spec Change Log.
- Append the surface reconcile to the memlog of each Spec that governs a moved file before the scoped stamps.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never add a CI job, a ci-surfaces row or a dependency.
- Never delete an `importorskip`: the tests still skip where their imports are absent.
- Never add a flag, a capability or an architecture decision; a fix that would need one stops and is reported.

## Acceptance Criteria

**Given** `DW-steward-cutover-2026-11-10-8`, `DW-steward-cutover-2026-11-10-12` and `DW-scribe-cutover-2026-11-10-2` report seven tests that skip in the only environment their suite runs in, and the operator rules "No new lane"
**When** each test is run by node id as a step of an existing CI job whose environment holds its imports, through a pixi task, and the step fails when a named test skips
**Then** the two share-tree tests pass in a job on `pyforge-guild`, the five scribe tests pass in the job on `pyforge-foundry-full`, each locally through its pixi task, and no CI job, ci-surfaces row, budget or dependency is added
**And** a skip of any of the seven fails its step, each skip reason and scribe's skip-site guard name the task that runs the test, `docs/reference/github-workflows.md` says so, and the three rows read resolved

- **AC1 — The share-tree tests run and pass in the Guild environment.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild steward-share-tree-test
  ```

- **AC2 — The five scribe tests run and pass in the full environment.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-foundry-full scribe-plane-and-portal-test
  ```

- **AC3 — No ci-surfaces row was added.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pyforge steward ci status
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-175 (a station suite runs once, as its two halves) and CAP-166 (every pausable CI surface is declared once; no row is added, by the operator ruling of 2026-11-25 "No new lane"); reads `spec-pyforge-scribe:CAP-26` (no text change); no AD moves.
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-25 entry (the rows a lapsed blocker held close); operator ruling of 2026-11-25: "All 22 rows".
- Epic: Epic 136, minted with this story.
- Ledger key: `136-6-the-tests-that-ran-in-no-ci-job-run-in-one`.
- Deferred-work row: `DW-steward-cutover-2026-11-10-8`, `DW-steward-cutover-2026-11-10-12`, `DW-scribe-cutover-2026-11-10-2`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."136"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry (the rows a lapsed blocker held close) and the operator's ruling of the same date. Not implemented.
