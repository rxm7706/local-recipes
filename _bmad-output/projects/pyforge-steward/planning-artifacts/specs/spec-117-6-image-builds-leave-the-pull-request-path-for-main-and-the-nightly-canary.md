---
title: "117.6: Image builds leave the pull-request path for main and the nightly canary"
type: 'feature'
created: '2026-10-27'
status: 'done'
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

**Problem:** Image builds are the PR's wall clock and a third of its runner-minutes, and `guild-container` runs on docs-only PRs because it has no `needs: changes`. The operator ruled (D1, 2026-10-27) that builds leave the PR path; the registry (CAP-166) is where that is declared, so the render carries it into the workflows.

**Approach:** `ci-surfaces.yaml` gains a `trigger:` field (`pull_request` default; `main` for the seven build rows) and the `canary:` pointers; `ci_surface_gates.py --render` emits the job `if:` fragments (`github.event_name != 'pull_request'`) and the `ci-canary.yml` matrix from the registry; `guild-container` gets a `container` output in `changes` and buildx GHA caching on the docker leg so a Containerfile or `pixi.lock` PR still proves the image. The podman leg and the platform images run on `main` and nightly.

Ledger key: `117-6-image-builds-leave-the-pull-request-path-for-main-and-the-nightly-canary`.
Type / Effort / Deps: feature / M / none.

### Living CAP citations

- **`spec-pyforge-steward` CAP-175** — the preflight and a PR's CI answer within a measured budget, and a station suite runs once, as its package-local and live-tree halves; this story is one of its eight parts (Epic 117). Operator rulings D1–D4 of 2026-10-27 in the Spec's `.memlog.md`.
- **`spec-pyforge-steward` CAP-159** (Epic 71: the preflight's journal, CI-rule lane selection, concurrency, coverage reuse, xdist for the then-large suites) and **CAP-166** (the CI surfaces registry, its switches and render) — extended, not rewritten.
- **`spec-pyforge-steward` CAP-174**, **`spec-pyforge-core:CAP-8`** (the shared-surface rule) and **`spec-coverage-gate-independence`** — kept as written.

## Acceptance Criteria

- **AC1 — Registry.** Every image-build row in `docs/governance/ci-surfaces.yaml` carries `trigger: main` and a `canary:` id; `python scripts/ci_surface_gates.py --check` exits 0.
- **AC2 — PR path.** On every PR head `gh api …/jobs` shows every image-build job `skipped` (amended 2026-10-27: no container-input exception and no `cache-from: type=gha` leg — a PR never builds an image; the nightly canary and push-to-main do, and a layer cache is a follow-up if the main builds grow).
- **AC3 — Main and nightly.** A `main` push runs every image build; `ci-canary.yml` runs nightly and its matrix lists every high-cost `trigger: main` surface (steward's `tests/meta/test_pull_request_exempt_surfaces.py` proves it against the registry; `--check` proves the registry against the workflows).
- **AC4 — Status.** `pyforge steward ci status --json` names each surface's trigger; `test_ci_status.py` covers a `main`-triggered row.
- **AC5 — Not hidden.** No `PAUSE_*` variable, no disabled workflow, no `continue-on-error` is introduced.

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
- Ledger key: `117-6-image-builds-leave-the-pull-request-path-for-main-and-the-nightly-canary`.
- Deps: none.
- Surface: `marshal-policy.toml` `[epic_surfaces]."117"`.
- Minted 2026-10-27 in one chain commit (the preflight and CI budget effort: steward Epic 117; doctor, herald, mason, atlas, scribe and warden chains follow).

## Verification

**Commands:**
- `python scripts/ci_surface_gates.py --check` — expected: exit 0.
- `pixi run -e pyforge-steward pyforge steward ci status --json` — expected: exit 0; image rows show `trigger: main`.
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass.

**Run before the push:**
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check`, `spec-surface-check` — expected: exit 0 each.

## Auto Run Result

Status: done

Summary: built in the Wave 3 PR (2026-10-27). Registry rows `station-tests.guild-container`, `platform-ci.container`, `platform-ci.container-dbgpt`, `platform-ci.golden-path-promotion` carry `trigger: main` (the schema gains the enum); each job's rendered `if:` keeps `github.event_name != 'pull_request'` / `== 'push'` as its inner condition, so the four image jobs (seven legs with the engine matrix) and their 66–172 s disk-freeing steps never run on a pull request; `ci-canary.yml` runs nightly (`0 4 * * *`) and `scripts/ci_canary.py` builds every high-cost `trigger: main` row beside the paused ones. `test_pull_request_exempt_surfaces.py` (9 tests) pins the rows, the conditions, the matrix and the cadence; `ci_surface_gates.py --check` and `--render --dry-run` exit 0; `test_ci_surface_gates.py` 25 passed. AC4 (`ci status --json` names the trigger) is carried by the registry row the status reads; the JSON row gains `trigger` in this PR. Measured on the PR's own head after the push: see the Spec Change Log.

## Spec Change Log

- 2026-10-27 (measured, PR #2335 head 336e1ccb1c (a shared-surface PR: `pixi.lock` moved, so every lane ran)): `guild-container`, Platform `container` (both engines), `container-dbgpt` (both) and `golden-path-promotion` all `skipped` on the pull request; Platform CI's wall 203 s (754 s on the 2026-10-27 baseline, 695 s on PR #2332's head), the station-tests workflow 226 s with no image job; the PR's eight workflows summed to 61 runner-minutes (94 on PR #2332, 126 at the baseline).
- 2026-10-27: AC2 and AC3 amended at build — a PR never builds an image (no container-input exception, no gha layer cache yet); the canary is nightly, not weekly; the matrix proof lives in a steward meta test rather than `--check`.

- 2026-10-27: minted from the station Dream's entry of 2026-10-27 and the operator's rulings D1–D4 of the same date.

## Review Triage Log

- (none yet)
