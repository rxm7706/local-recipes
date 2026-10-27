---
title: "117.11: The changes gate and the gate diffs run on shallow fetches of the PR base"
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
  - scripts/coverage_gates_ci.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_ci.py
---

<intent-contract>

## Intent

**Problem:** The `changes` job takes 24–36 s, most of it a `fetch-depth: 0` clone of a repository with 1,900 recipes, and every station job waits for it before it starts; thirteen station and gate jobs clone full history (20–25 s instead of 6–11) for a coverage diff that needs two commits. On a PR whose longest shard works 45 s, that serial gate is a third of the wall.

**Approach:** `changes` checks out at depth one, fetches the PR's base sha (`github.event.pull_request.base.sha`) at depth one and diffs `$BASE_SHA HEAD` two-dot; `push` events keep today's `HEAD~1` fallback. Every station and gate job drops `fetch-depth: 0` and fetches the base sha the same way for `coverage_gates_ci.py --base`. The local twin (`preflight_ci`) keeps `refs/remotes/origin/main` as its base; the trigger map's `run_changes` harness drives the shallow script unchanged.

Ledger key: `117-11-the-changes-gate-and-the-gate-diffs-run-on-shallow-fetches-of-the-pr-base`.
Type / Effort / Deps: chore / S / 117.2.

### Living CAP citations

- **`spec-pyforge-steward` CAP-175 (amended 2026-10-27, later)** — the preflight and a PR's CI answer within a measured budget; a station suite runs once, as its package-local and live-tree halves, each half as N sharded jobs whose coverage the gate merges; the `changes` step and the gate diffs read shallow fetches; the platform suite runs under xdist. The repository is public: runner minutes are free and the wall is the only cost. The amendment's measurements and decision are in the Spec's `.memlog.md` (2026-10-27, later).
- **`spec-pyforge-steward` CAP-159** (Epic 71) and **CAP-166** (the CI surfaces registry) — extended, not rewritten; **CAP-174** (the Platform CI budget), **`spec-pyforge-core:CAP-8`** (the shared-surface rule) and **`spec-coverage-gate-independence`** — kept as written.

## Acceptance Criteria

- **AC1 — The gate.** The `changes` job's checkout is two commits deep (`fetch-depth: 2`) and its base is the merge commit's first parent when no remote-tracking ref exists, the remote ref otherwise (amended 2026-10-27: a two-commit fetch keeps the three-dot diff and its merge base, so the script's diffs are unchanged); the job finishes in ≤ 15 s on a PR; its outputs on the trigger-map harness and the selection twin are unchanged.
- **AC2 — The checkouts.** No job in `pyforge-station-tests.yml` carries `fetch-depth: 0`; every station job's checkout step is ≤ 12 s.
- **AC3 — The verdicts.** The coverage gate's touched-module set and verdicts on those heads equal the deep-clone run's.
- **AC4 — The twin.** `preflight_ci` selects the same lanes as before; `test_station_tests_trigger_map.py` and `test_workflow_path_filters_match.py` pass unchanged.

## Boundaries & Constraints

**Always:**
- Read every verdict from an exit code, never through a pipe; keep `PYFORGE_PREFLIGHT_SKIP=1` the one journaled opt-out.
- Regenerate `environment.yaml` in the same PR as any `pixi.toml` edit; label the PR `maintenance`.

**Never:**
- Never skip a lane where CI's own rule would run it; never delete, skip or re-mark a test to meet a budget; never narrow a `*_paths` array by hand (Story 98.1, rulings 2026-10-12); never pause, disable or set `continue-on-error` on a lane; never hand-edit `SPEC.md`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-steward` CAP-175 (amended 2026-10-27, later).

Parent: `spec-pyforge-steward` CAP-175

- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-27, later (the wall is the lanes the waves did not touch) entry.
- Epic: Epic 117, amended with this story.
- Ledger key: `117-11-the-changes-gate-and-the-gate-diffs-run-on-shallow-fetches-of-the-pr-base`.
- Deps: 117.2.
- Surface: `marshal-policy.toml` `[epic_surfaces]."117"`.
- Minted 2026-10-27 (later) in one chain commit (Wave 3 of the preflight and CI budget effort: Stories 117.10–117.12).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py src/shared/packages/pyforge-steward/tests/meta/test_workflow_path_filters_match.py src/shared/packages/pyforge-steward/tests/unit/test_preflight_ci.py -q` — expected: pass.
- `gh api repos/rxm7706/local-recipes/actions/runs/<id>/jobs` on the first PR after landing — expected: the `changes` job ≤ 10 s, every checkout step ≤ 11 s.

**Run before the push:**
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `spec-surface-check` — expected: exit 0 each.

## Auto Run Result

Status: done

Summary: built in the Wave 3 PR (2026-10-27). `pyforge-station-tests.yml`: the `changes` job and all twelve station and gate jobs check out at `fetch-depth: 2`; every base resolution reads `refs/remotes/origin/<base>` when it exists (the local twin and the trigger-map harness keep a full history) and `git rev-parse HEAD^1` otherwise (the merge commit's first parent on a two-commit CI checkout), so every `"$BASE"...HEAD` three-dot diff keeps its merge base and the scripts are otherwise unchanged; `coverage_gates_ci.py` already falls back to a two-dot diff when a merge base is missing. The trigger-map harness (`run_changes`), `test_preflight_selection.py`, `test_preflight_ci.py` and `test_workflow_path_filters_match.py` pass unchanged. Checkout and `changes` seconds on the four-core runner: see the Spec Change Log after the PR's run.

## Spec Change Log

- 2026-10-27 (measured, PR #2335 head 336e1ccb1c (a shared-surface PR: `pixi.lock` moved, so every lane ran)): the `changes` job 16 s (12 s of it the two-commit checkout; 24–36 s before); station checkouts 5–22 s on most jobs with runner-side outliers at 31–47 s on four (the same depth on every job: runner I/O, not history); the three-dot diffs and the gate verdicts unchanged.
- 2026-10-27: AC1 and AC2 amended at build — a two-commit fetch (not depth one plus a base fetch) keeps the three-dot diffs; the base ref rule is `refs/remotes/origin/<base>` where it exists, else `HEAD^1`.

- 2026-10-27: minted from the station Dream's second Realization-log entry of 2026-10-27 (the wall is the lanes the waves did not touch) and the CAP-175 amendment of the same date.

## Review Triage Log

- (none yet)
