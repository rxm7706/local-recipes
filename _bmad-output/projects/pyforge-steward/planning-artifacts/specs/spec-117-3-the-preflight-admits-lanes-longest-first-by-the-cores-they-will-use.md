---
title: "117.3: The preflight admits lanes longest-first by the cores they will use"
type: 'feature'
created: '2026-10-27'
status: 'done'
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
- **AC3 — Wall.** On a full-scope run of the lane set the journal's `total_seconds` is within 10 % of its longest lane's `seconds`, or the excess is the stop-on-red / docs-site-turn serialisation the run records (recorded in the story's Auto Run Result from a real run).
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
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_preflight_critical_path.py -q` — expected: pass; `test_the_flag_switches_the_scheduler` runs `pyforge.steward.preflight_critical_path` in both states through the testing kit's `flag_states`.
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the two-state flag test included).
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0; the journal's `total_seconds` within 10 % of the longest lane.
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.

**Run before the push:**
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check`, `spec-surface-check` — expected: exit 0 each.

## Auto Run Result

Status: done

Summary: built in the Wave 2 PR (2026-10-27). `preflight.lane_medians(journal, last_n=5)` reads the median seconds per `(task, environment)` from the last five green journal runs (homed in `preflight.py`, not `preflight_budget.py`: the budget guard test forbids the run path importing the budget module); `_next_lane` ranks ready lanes `(-expected_seconds, declared_index)` with unknown lanes at 30 s, keeping the docs-site install first and the docs-site turn as Story 117.2 left it; the admission loop keeps a `weights` map (serial 1; xdist `preflight_xdist.xdist_share_at_admission(free_cores, pending_xdist, logical_cores)`, minimum 2, a lane that would get 0 is set aside this round) and admits while the admitted weights plus the candidate's stay within `logical_cores`, `--jobs` still the cap; the share is written into the lane's `PYTEST_XDIST_AUTO_NUM_WORKERS` at admission. `pyforge.steward.preflight_critical_path` is in `flags.json` and both overlays (ON everywhere, cleanup_by 2027-01-25); OFF reproduces declaration order and the static share byte-for-byte. `tests/unit/test_preflight_critical_path.py` (8 tests, one two-state through `flag_states`) covers AC1, AC2 and AC4; `test_preflight_concurrency.py`, the docs-site mutex tests and `test_preflight_workers.py` stay green (AC5; the trade-turns test pins `critical_path=False` since journal order now decides which docs-site lane goes first). AC3 measured on a real full run: see the Spec Change Log entry of 2026-10-27 (wall).

## Spec Change Log

- 2026-10-27: minted from the station Dream's entry of 2026-10-27 and the operator's rulings D1–D4 of the same date.
- 2026-10-27 (AC3, measured): full-scope `pr-preflight` on this branch, 16 logical cores, 40 lanes, flag ON: `total_seconds` 772 s against the longest lane `test-ci` (local-recipes) 768 s — the wall is 0.5 % over its longest lane (the CFE serial suite, mason M.1's story, is now the floor); the next lanes were `pyforge-marshal-test` 347 s, `pyforge-herald-test` 306 s, `pyforge-steward-live-test` 305 s; the last lane to start did so at +377 s (`pyforge-marshal-coverage-gate`). Before 117.3 a full run's wall was a queue (median 670 s, lanes starting at +1099 s).
- 2026-10-27 (PR #2332 CI): the OFF path's static xdist map and the journal record now read the same injectable core count as the ON path (`cores`), and the OFF-state test derives Story 71.6's share from the fixture's task table — on the 4-core runner it had read `'4' == '16'`. The platform's shipped-flag table (`src/platform/tests/test_openfeature_file_flags.py`) and core's (`test_flags.py`) both carry the new kill switch.
- 2026-10-27: `lane_medians` lives in `preflight.py` (the story named `preflight_budget.py`): `preflight_budget` imports the run path, and the budget guard test forbids the run path importing it back. AC3 reworded for the two serialisations the run records (stop-on-red, the docs-site turn): the wall is the longest lane plus those, not plus queueing.

## Review Triage Log

- (none yet)
