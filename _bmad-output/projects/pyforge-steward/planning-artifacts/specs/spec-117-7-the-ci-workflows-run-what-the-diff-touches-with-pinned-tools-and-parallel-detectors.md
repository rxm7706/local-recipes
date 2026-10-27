---
title: "117.7: The CI workflows run what the diff touches, with pinned tools and parallel detectors"
type: 'chore'
created: '2026-10-27'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
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

**Problem:** Four small defects cost ~6 runner-minutes per PR and up to 3 minutes of wall: detectors run serially in CI only, two jobs have no path rule, pixi floats in 11 setups (cache keys churn), and mypy's cache is rebuilt every run. The atlas job still runs the `--with-deps` apt install CAP-174 removed from the platform job.

**Approach:** Workflow-only edits, each mirrored in the meta-tests that read the workflows. The atlas step takes CAP-174's launch-then-fallback shape (the operator's open question in the Spec, answered here as a step shape; atlas owns its job's budget).

Ledger key: `117-7-the-ci-workflows-run-what-the-diff-touches-with-pinned-tools-and-parallel-detectors`.
Type / Effort / Deps: chore / S / none.

### Living CAP citations

- **`spec-pyforge-steward` CAP-175** — the preflight and a PR's CI answer within a measured budget, and a station suite runs once, as its package-local and live-tree halves; this story is one of its eight parts (Epic 117). Operator rulings D1–D4 of 2026-10-27 in the Spec's `.memlog.md`.
- **`spec-pyforge-steward` CAP-159** (Epic 71: the preflight's journal, CI-rule lane selection, concurrency, coverage reuse, xdist for the then-large suites) and **CAP-166** (the CI surfaces registry, its switches and render) — extended, not rewritten.
- **`spec-pyforge-steward` CAP-174**, **`spec-pyforge-core:CAP-8`** (the shared-surface rule) and **`spec-coverage-gate-independence`** — kept as written.

## Acceptance Criteria

- **AC1 — Detectors.** `detectors.yml` runs `scripts/detectors.py --scope repo --jobs auto`; the job's duration on the landing PR ≤ 150 s.
- **AC2 — Gated jobs.** The seed oracle reads `skipped` on a planning-only PR and `success` on a PR touching a seed-managed artifact or marshal. Not taken at build (2026-10-27): a `needs: changes` gate on `scripts-suite` — its tests run the detectors over the live tree (planning artifacts, docs, skills, `src/`), so the honest gate is the whole repo; this PR's planning-only first commit red `tests/scripts/test_tea_playwright_check.py`, which is exactly what such a gate would have hidden.
- **AC3 — Pins.** Not taken at build (2026-10-27): `pixi.toml`'s `requires-pixi` comment names the pin sites that must move together; 16 more `pixi-version:` lines widen that drift surface for a cache-key stability the measurements never showed costing time (`setup-pixi` 10–30 s everywhere). Left to the pixi-currency work.
- **AC4 — Caches.** lint-types restores `.mypy_cache` on the second run of the same `pixi.lock` (the step log reads `Cache restored`).
- **AC5 — Atlas step.** The atlas job's Chromium step runs `playwright install chromium`, launches, and runs `install-deps` only on failure; its duration on the runner image ≤ 30 s.

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
- Ledger key: `117-7-the-ci-workflows-run-what-the-diff-touches-with-pinned-tools-and-parallel-detectors`.
- Deps: none.
- Surface: `marshal-policy.toml` `[epic_surfaces]."117"`.
- Minted 2026-10-27 in one chain commit (the preflight and CI budget effort: steward Epic 117; doctor, herald, mason, atlas, scribe and warden chains follow).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_workflow_path_filters_match.py src/shared/packages/pyforge-steward/tests/unit/test_preflight_selection.py -q` — expected: pass.
- `python scripts/ci_surface_gates.py --check` — expected: exit 0.
- `gh api repos/rxm7706/local-recipes/actions/runs/<id>/jobs` on the landing PR — expected: `detectors` ≤ 150 s, `scripts-suite` skipped when untouched.

**Run before the push:**
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check`, `spec-surface-check` — expected: exit 0 each.

## Auto Run Result

Status: done

Summary: built in PR #2331 (2026-10-27): `detectors.yml` runs `scripts/detectors.py --scope repo --jobs auto` and cancels per PR number; `lint-types.yml` restores the per-environment mypy caches (`actions/cache@v4`, keyed on `pixi.lock` and the package sources); the atlas job's Chromium step takes CAP-174's launch-then-fallback shape; `marshal-local-recipes-seed-oracle.yml` fires on the managed artifacts, the manifest tree and marshal only (pull_request and push lists identical).

## Spec Change Log

- 2026-10-27: minted from the station Dream's entry of 2026-10-27 and the operator's rulings D1–D4 of the same date.

- 2026-10-27: AC2 and AC3 amended: the `scripts-suite` gate and the setup-pixi pins are not taken, with the reasons recorded in the ACs.

## Review Triage Log

- (none yet)
