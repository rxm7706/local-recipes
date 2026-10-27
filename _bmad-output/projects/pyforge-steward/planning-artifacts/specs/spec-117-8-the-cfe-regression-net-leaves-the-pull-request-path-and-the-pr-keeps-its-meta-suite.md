---
title: "117.8: The CFE regression net leaves the pull-request path, and the PR keeps its meta suite"
type: 'feature'
created: '2026-10-27'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a CI job, a test task or a preflight report (spec-feature-flag-governance Q1; roster list)
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md
  - docs/dreams/pyforge-steward.md
  - docs/governance/ci-surfaces.yaml
  - .github/workflows/pyforge-station-tests.yml
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
---

<intent-contract>

## Intent

**Problem:** The CFE regression net is the longest PR workflow (716 s mean) and most of it is environment: the 9.8 GB `local-recipes` env and a 564 s serial suite. The operator ruled (D1) that it leaves the PR path; the fast `tests/meta` subset stays so a CFE PR still gets a recipe-rule verdict before merge.

**Approach:** Registry-first: the net's row gains `trigger: main` + `canary:`, a `cfe-meta` row is added, and `ci_surface_gates.py --render` carries both into the workflows. The `cfe-meta` job runs mason's `test-ci-meta` task (mason's story on its own chain; Deps). Steward's `test_cfe_regression_net_paths.py` moves from asserting the PR trigger to asserting the main trigger plus the meta job's paths.

Ledger key: `117-8-the-cfe-regression-net-leaves-the-pull-request-path-and-the-pr-keeps-its-meta-suite`.
Type / Effort / Deps: feature / S / mason's `test-ci-meta` task story (minted on the mason chain; cites this story).

### Living CAP citations

- **`spec-pyforge-steward` CAP-175** — the preflight and a PR's CI answer within a measured budget, and a station suite runs once, as its package-local and live-tree halves; this story is one of its eight parts (Epic 117). Operator rulings D1–D4 of 2026-10-27 in the Spec's `.memlog.md`.
- **`spec-pyforge-steward` CAP-159** (Epic 71: the preflight's journal, CI-rule lane selection, concurrency, coverage reuse, xdist for the then-large suites) and **CAP-166** (the CI surfaces registry, its switches and render) — extended, not rewritten.
- **`spec-pyforge-steward` CAP-174**, **`spec-pyforge-core` CAP-8** (the shared-surface rule) and **`spec-coverage-gate-independence`** — kept as written.

## Acceptance Criteria

- **AC1 — Trigger.** `cfe-regression-net.yml` has no `pull_request` trigger; it runs on `push` to `main`, `workflow_dispatch` and the nightly canary; the registry row reads `trigger: main`.
- **AC2 — Meta on PR.** A PR touching `.claude/skills/conda-forge-expert/**` runs the `cfe-meta` job (`pytest .claude/skills/conda-forge-expert/tests/meta -q`) and it passes; a PR touching nothing CFE skips it.
- **AC3 — Wall.** On a CFE PR, the head's slowest workflow is ≤ 5 min (`gh run list`).
- **AC4 — Meta-test.** `test_cfe_regression_net_paths.py` passes against the new shape and fails if the `pull_request` trigger returns or the meta job's paths drop a CFE path.
- **AC5 — Not hidden.** No `PAUSE_*`, no disabled workflow.

## Boundaries & Constraints

**Always:**
- Read every verdict from an exit code, never through a pipe; keep `PYFORGE_PREFLIGHT_SKIP=1` the one journaled opt-out.
- Regenerate `environment.yaml` in the same PR as any `pixi.toml` edit; label the PR `maintenance`.

**Never:**
- Never skip a lane where CI's own rule would run it; never delete, skip or re-mark a test to meet a budget; never narrow a `*_paths` array by hand (Story 98.1, rulings 2026-10-12); never pause, disable or set `continue-on-error` on a lane; never hand-edit `SPEC.md`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-steward` CAP-175.

Parent: `spec-pyforge-steward` CAP-175

- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-27 (the preflight answers in eleven minutes, a PR's CI in thirteen) entry.
- Epic: Epic 117, minted with this story.
- Ledger key: `117-8-the-cfe-regression-net-leaves-the-pull-request-path-and-the-pr-keeps-its-meta-suite`.
- Deps: mason's `test-ci-meta` task story (minted on the mason chain; cites this story).
- Surface: `marshal-policy.toml` `[epic_surfaces]."117"`.
- Minted 2026-10-27 in one chain commit (the preflight and CI budget effort: steward Epic 117; doctor, herald, mason, atlas, scribe and warden chains follow).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_cfe_regression_net_paths.py -q` — expected: pass.
- `python scripts/ci_surface_gates.py --check` — expected: exit 0.
- `pixi run -e local-recipes pytest .claude/skills/conda-forge-expert/tests/meta -q` — expected: pass (the lane the PR keeps).

**Run before the push:**
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check`, `spec-surface-check` — expected: exit 0 each.

## Auto Run Result

Status: backlog

Summary: not started.

## Spec Change Log

- 2026-10-27: minted from the station Dream's entry of 2026-10-27 and the operator's rulings D1–D4 of the same date.

## Review Triage Log

- (none yet)
