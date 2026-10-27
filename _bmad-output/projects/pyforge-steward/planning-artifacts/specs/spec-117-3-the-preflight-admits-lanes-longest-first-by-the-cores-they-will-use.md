---
title: "117.3: The preflight admits lanes longest-first by the cores they will use"
type: 'feature'
created: '2026-10-27'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag:
  key: pyforge.steward.preflight_critical_path
  provider: openfeature-file
  default: {production: on, staging: on, dev: on}
  scope: global
  fallback: "declaration-order admission and the static per-lane xdist share (Story 71.3 / 71.6 behaviour)"
  cleanup: "90 days after ON in every environment (Q4); the owning station files the removal story"
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

**Problem:** Story 71.3 made the lanes concurrent but admits them in declaration order with a static per-lane xdist share (`preflight_xdist.py:47-66`): a full run puts 32–38 lanes on 16 slots, short lanes hold slots while `steward-test`, `doctor-test`, `detectors-ci` and `test-ci` wait, and the journal shows a lane starting at +1099 s. The wall is a queue, not the longest lane.

**Approach:** `preflight_budget.lane_medians(journal)` reads the journal the preflight already writes; `preflight_xdist.lane_weight` gives each lane a weight (serial 1, xdist its share) at admission and writes it into `coord.xdist_workers`; `_next_lane` orders by `(-expected_seconds, declared_index)`; the admission loop at `preflight.py:1370` admits by core budget. The flag is a kill switch read through `pyforge.core.flags` at the scheduler's one decision point; OFF is the current behaviour byte-for-byte.

Ledger key: `117-3-the-preflight-admits-lanes-longest-first-by-the-cores-they-will-use`.
Type / Effort / Deps: feature / M / none.

### Living CAP citations

- **`spec-pyforge-steward` CAP-175** — the preflight and a PR's CI answer within a measured budget, and a station suite runs once, as its package-local and live-tree halves; this story is one of its eight parts (Epic 117). Operator rulings D1–D4 of 2026-10-27 in the Spec's `.memlog.md`.
- **`spec-pyforge-steward` CAP-159** (Epic 71: the preflight's journal, CI-rule lane selection, concurrency, coverage reuse, xdist for the then-large suites) and **CAP-166** (the CI surfaces registry, its switches and render) — extended, not rewritten.
- **`spec-pyforge-steward` CAP-174**, **`spec-pyforge-core:CAP-8`** (the shared-surface rule) and **`spec-coverage-gate-independence`** — kept as written.

## Acceptance Criteria

- **AC1 — Order.** With a journal fixture of five lanes (one xdist, four serial, known medians) the admission order is longest-expected first and the xdist lane's `PYTEST_XDIST_AUTO_NUM_WORKERS` is its computed share, not the static minimum.
- **AC2 — Budget.** Admitted weights never exceed `logical_cores`; `--jobs N` still caps lanes in flight; a lane with no journal history weighs 30 s and is never starved past one admission round.
- **AC3 — Wall.** On a full-scope run of the 38-lane set the journal's `total_seconds` is within 10 % of its longest lane's `seconds` (recorded in the story's Auto Run Result from a real run).
- **AC4 — Flag.** `pyforge.steward.preflight_critical_path` is in `flags.json` and every overlay with the five metadata fields; OFF reproduces declaration order and the static share; one test runs both states.
- **AC5 — Unchanged.** `DOCS_SITE_TASKS` turn-taking, stop-on-red, SIGINT handling and the exit domain are unchanged (`test_preflight_concurrency.py` green).

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
- Ledger key: `117-3-the-preflight-admits-lanes-longest-first-by-the-cores-they-will-use`.
- Deps: none.
- Surface: `marshal-policy.toml` `[epic_surfaces]."117"`.
- Minted 2026-10-27 in one chain commit (the preflight and CI budget effort: steward Epic 117; doctor, herald, mason, atlas, scribe and warden chains follow).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the two-state flag test included).
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0; the journal's `total_seconds` within 10 % of the longest lane.
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.

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
