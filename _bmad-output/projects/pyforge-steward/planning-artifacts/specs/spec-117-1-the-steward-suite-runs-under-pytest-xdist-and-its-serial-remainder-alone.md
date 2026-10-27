---
title: "117.1: The steward suite runs under pytest-xdist and its serial remainder alone"
type: 'chore'
created: '2026-10-27'
status: 'backlog'
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

**Problem:** `pyforge-steward-test` is the longest lane of the local preflight (698 s median, 586–1239 s) and the longest job of the station-tests workflow (547 s): the suite runs as one process while four other stations already run under `pytest-xdist` (Story 71.6 covered the suites that were large on 2026-09-27; steward's was 19 s then and is 2501 tests now).

**Approach:** Add `pytest-xdist` to the steward feature, split the task into the xdist segment and the serial remainder (`test_preflight_concurrency.py` kills its own process with SIGINT at lines 398 and 1090, which would take an xdist worker with it), group fixtures that share scratch, then profile with `--durations=40` and fix the three slow classes named in the Dream entry. `coverage_gates_ci._pytest_first_run_flags` already mirrors `-n`/`--dist`/`--ignore` into the coverage run, so the gate inherits the split.

Ledger key: `117-1-the-steward-suite-runs-under-pytest-xdist-and-its-serial-remainder-alone`.
Type / Effort / Deps: chore / M / none.

### Living CAP citations

- **`spec-pyforge-steward` CAP-175** — the preflight and a PR's CI answer within a measured budget, and a station suite runs once, as its package-local and live-tree halves; this story is one of its eight parts (Epic 117). Operator rulings D1–D4 of 2026-10-27 in the Spec's `.memlog.md`.
- **`spec-pyforge-steward` CAP-159** (Epic 71: the preflight's journal, CI-rule lane selection, concurrency, coverage reuse, xdist for the then-large suites) and **CAP-166** (the CI surfaces registry, its switches and render) — extended, not rewritten.
- **`spec-pyforge-steward` CAP-174**, **`spec-pyforge-core` CAP-8** (the shared-surface rule) and **`spec-coverage-gate-independence`** — kept as written.

## Acceptance Criteria

- **AC1 — Collected count.** `pixi run --frozen -e pyforge-steward pyforge-steward-test` passes and collects the same number of tests as the serial run at the story's baseline commit (the serial remainder included).
- **AC2 — Local lane.** A touched-scope `pr-preflight` on a steward-only diff journals `pyforge-steward-test` at ≤ 70 s (`.steward/preflight-runs.jsonl`, `lanes[].seconds`).
- **AC3 — CI job.** The `steward-test` job of `pyforge-station-tests.yml` completes in ≤ 240 s on the PR that lands this story (`gh api …/runs/<id>/jobs`).
- **AC4 — Nothing cut.** No test is deleted, skipped or marked `slow` to meet AC2/AC3; `-m` selects nothing new.
- **AC5 — Shared surface.** `environment.yaml` matches `pixi.toml` (`pixi run -e pyforge-guild llms-full-check` and the reconcile exporter exit 0).

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
- Ledger key: `117-1-the-steward-suite-runs-under-pytest-xdist-and-its-serial-remainder-alone`.
- Deps: none.
- Surface: `marshal-policy.toml` `[epic_surfaces]."117"`.
- Minted 2026-10-27 in one chain commit (the preflight and CI budget effort: steward Epic 117; doctor, herald, mason, atlas, scribe and warden chains follow).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass, same collected count as the baseline serial run.
- `PYFORGE_PREFLIGHT_SCOPE=touched pixi run -e pyforge-guild pr-preflight` on a steward-only diff — expected: exit 0; the journal's `pyforge-steward-test` lane ≤ 70 s.
- `pixi run -e pyforge-guild llms-full-check` — expected: exit 0 after `environment.yaml` regenerates.

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
