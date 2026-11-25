---
title: '136.9: The two named-test steps have a local preflight lane'
type: 'fix'
created: '2026-11-25'
status: 'ready-for-dev'
story: 136-9-the-two-named-test-steps-have-a-local-preflight-lane
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'pixi.toml'
  - 'environment.yaml'
  - 'src/shared/packages/pyforge-steward/tests/**'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/preflight*.py'
  - 'docs/how-to/pixi-tasks.md'
  - 'docs/**'
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

**Problem:** the review finding of Story 136.6 (no deferred-work row was written; it is fixed in the PR that carries the story). `pr-preflight` reads its lanes from the `depends-on` of `pr-preflight-lanes` in `pixi.toml`. `steward-share-tree-test` (`-e pyforge-guild`) and `scribe-plane-and-portal-test` (`-e pyforge-foundry-full`), the two steps Story 136.6 added to `.github/workflows/lint-types.yml`, are not in it, so a full local preflight is green where CI can be red.

**Approach:** Add both tasks to `pr-preflight-lanes`' `depends-on`, the second pinned to `pyforge-foundry-full` as `mypy` is, beside the `lint-types` entries whose job runs them. Check how the preflight maps a lane to the workflow that selects it (the touched scope and the `changes` rules read `lint-types.yml`'s paths), so the two lanes are selected when that workflow fires and not otherwise; update whatever test pins the lane list or its count; regenerate the generated task page.

Ledger key: `136-9-the-two-named-test-steps-have-a-local-preflight-lane`.

### Living CAP citations

- spec-pyforge-steward CAP-159 (the preflight selects and runs every lane a PR gates on) and CAP-175 (realized, no text change); no AD moves.

## Boundaries & Constraints

**Always:**
- Reproduce what is reported on the unchanged tree before changing it, and record the reproduction in the Spec Change Log.
- Append the surface reconcile to the memlog of each Spec that governs a moved file before the scoped stamps.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never add a dependency or a CI job.
- Never add a flag, a capability or an architecture decision; a fix that would need one stops and is reported.

## Acceptance Criteria

**Given** the review of Story 136.6 found that the two new lint-types steps have no `pr-preflight` lane
**When** both tasks are added to `pr-preflight-lanes`, each in the environment its CI step uses
**Then** a full-scope `pr-preflight` lists and runs `steward-share-tree-test` in `pyforge-guild` and `scribe-plane-and-portal-test` in `pyforge-foundry-full`, and `pixi run --dry-run -e pyforge-guild pr-preflight-lanes` resolves every task
**And** steward's preflight tests pass, and no CI job, ci-surfaces row or dependency is added

- **AC1 — Both tasks are lanes.** Expected: prints 2.

  ```bash
  grep -c -E 'steward-share-tree-test|scribe-plane-and-portal-test' <(python3 -c "import tomllib;print('\n'.join(str(x) for x in tomllib.load(open('pixi.toml','rb'))['feature']['guild-tasks']['tasks']['pr-preflight-lanes']['depends-on']))")
  ```

- **AC2 — The lane list resolves under pixi and steward's preflight tests hold.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_pr_preflight_lanes_resolve_under_pixi.py src/shared/packages/pyforge-steward/tests/unit/test_preflight.py -q
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-159 (the preflight selects and runs every lane a PR gates on) and CAP-175 (realized, no text change); no AD moves.
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-25 entry (the remainder of the rows a lapsed blocker held); operator ruling of 2026-11-25: "lets address these too".
- Epic: Epic 136.
- Ledger key: `136-9-the-two-named-test-steps-have-a-local-preflight-lane`.
- Deferred-work row: the review finding of Story 136.6 (no deferred-work row was written; it is fixed in the PR that carries the story).
- Surface: `marshal-policy.toml` `[epic_surfaces]."136"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry (the remainder of the rows a lapsed blocker held) and the operator's ruling of the same date. Not implemented.
