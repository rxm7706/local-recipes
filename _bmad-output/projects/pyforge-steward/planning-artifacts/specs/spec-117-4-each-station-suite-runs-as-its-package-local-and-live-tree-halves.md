---
title: "117.4: Each station suite runs as its package-local and live-tree halves"
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

**Problem:** Fan-out is by design: Story 98.1 makes each job fire on everything its tests read, and the readers are a minority of each suite — yet they drag the whole unit suite along. Five recent PRs each ran 8–10 of 10 suite jobs (~1000–1700 runner-s of non-owner suites). Narrowing the arrays is not allowed (it reds `steward-test` and reverses the 2026-10-12 ruling); splitting the suites keeps the contract and drops the fan-out.

**Approach:** One convention for the live-tree half (a `tests/live/` directory, or a `live_tree` marker collected by `-m`), two pixi tasks per station, two jobs per station in the workflow, and the trigger map keyed by job (it already reads `task_paths` from `pixi.toml` per job): the package half's derived reads must be empty outside the package, so a new outside read in a package test reds `steward-test` in the PR that adds it. Steward moves its own readers here; every other station moves its readers on its own chain (doctor D.4, herald H.2, mason M.3, atlas A.2, scribe S.2, warden W.1), citing this story.

Ledger key: `117-4-each-station-suite-runs-as-its-package-local-and-live-tree-halves`.
Type / Effort / Deps: feature / L / none.

### Living CAP citations

- **`spec-pyforge-steward` CAP-175** — the preflight and a PR's CI answer within a measured budget, and a station suite runs once, as its package-local and live-tree halves; this story is one of its eight parts (Epic 117). Operator rulings D1–D4 of 2026-10-27 in the Spec's `.memlog.md`.
- **`spec-pyforge-steward` CAP-159** (Epic 71: the preflight's journal, CI-rule lane selection, concurrency, coverage reuse, xdist for the then-large suites) and **CAP-166** (the CI surfaces registry, its switches and render) — extended, not rewritten.
- **`spec-pyforge-steward` CAP-174**, **`spec-pyforge-core:CAP-8`** (the shared-surface rule) and **`spec-coverage-gate-independence`** — kept as written.

## Acceptance Criteria

- **AC1 — Two halves.** For steward (this story) and for every station whose own chain lands its split (doctor Story 55.4 lands with this one; herald, mason, atlas, scribe and warden on theirs), `pyforge-<s>-test` and `pyforge-<s>-live-test` exist in `pixi.toml`, together collect exactly the tests the old task collected, and `pyforge-station-tests` runs both.
- **AC2 — Derived gates.** `test_station_tests_trigger_map.py` derives the package job's outside reads as empty for steward and asserts it; the live job's reads equal today's derived set; every read fires its job; `PRESERVED` is unchanged.
- **AC3 — Fan-out.** The `changes` script on a one-file fixture diff under `src/shared/packages/pyforge-steward/src/` sets `steward=true`, `core=true` (CAP-8, by design) and `steward_live=true`, and no split station's package output `true` except steward's; on a one-file diff under `_bmad-output/projects/pyforge-doctor/planning-artifacts/` no split station's package output is `true`. An unsplit station's output (atlas and scribe read `src/shared/packages`; marshal reads the planning globs) keeps firing until its own chain splits it — the trigger map's fan-out test names them and shrinks as each lands.
- **AC4 — The twin.** `preflight_ci.select_lanes` selects the same lanes CI runs for both fixture diffs (`test_preflight_selection.py`).
- **AC5 — Nothing exempt.** No `*_paths` entry is removed except by the derivation shrinking; `on.pull_request.paths` still matches every derived read.

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
- Ledger key: `117-4-each-station-suite-runs-as-its-package-local-and-live-tree-halves`.
- Deps: none.
- Surface: `marshal-policy.toml` `[epic_surfaces]."117"`.
- Minted 2026-10-27 in one chain commit (the preflight and CI budget effort: steward Epic 117; doctor, herald, mason, atlas, scribe and warden chains follow).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_preflight_selection.py -q` — expected: pass.
- `pixi run -e pyforge-guild pyforge-station-tests` — expected: exit 0 (both halves of every station).

**Run before the push:**
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check`, `spec-surface-check` — expected: exit 0 each.

## Auto Run Result

Status: done

Summary: built in the Wave 2 PR (2026-10-27), with doctor Story 55.4. The convention is the `live_tree` marker (`pytestmark = pytest.mark.live_tree`, registered in each package's `[tool.pytest.ini_options]`): 68 steward modules carry it (every module the trigger map derives an outside read for, plus `tests/meta/**`). `pyforge-steward-test` collects `-m "not slow and not live_tree"` (1623 tests; 62 s with the set-aside `test_preflight_concurrency.py` alone), `pyforge-steward-live-test` collects `-m "live_tree and not slow"` (1446 tests; 108 s, `test_preflight_scope.py` and `test_preflight_scratch.py` alone), the two together the 3069 the old task collected; each writes its own `--cov` report and the gate judges `coverage_gates_ci.py --report steward-unit.json --report steward-live.json` (`merge_coverage_reports`: the union of executed lines and branches, coverage.py's percent formula). Workflow: `changes` emits `<s>` on the package and shared surface (`src/shared/packages/pyforge-<s>` + the shared globs) and `<s>_live` on the derived arrays (today's `*_paths`, renamed `<s>_live_paths`); new `steward-live-test` and `steward-gate` jobs (the gate downloads both `coverage-steward-*` artifacts); `ci-surfaces.yaml` carries the four new rows. `test_station_tests_trigger_map.py` keys both jobs, filters each half's derivation by the marker (AST), asserts the package half reads nothing outside its package (`test_the_package_half_reads_nothing_outside_its_package`), keeps `PRESERVED`, and its mutation tests target the live arrays; `test_preflight_selection.py` and `test_preflight_docs_site_lanes.py` follow the split. Measured locally (16 cores): steward 62 s + 108 s versus 303 s for the one suite in CI before; doctor 12 s + 47 s.

## Spec Change Log

- 2026-10-27: minted from the station Dream's entry of 2026-10-27 and the operator's rulings D1–D4 of the same date.
- 2026-10-27: AC1 scoped to the stations whose chains land the split (steward here, doctor 55.4 beside it); AC3 names the unsplit stations whose outputs still fire (atlas, scribe on `src/shared/packages`; marshal on the planning globs) — their chains (A.2, S.2, marshal's) shrink the fan-out test's named set. The convention chosen is the `live_tree` marker, not a `tests/live/` directory: the readers stay beside the tests they sit with and `-m` selects them.

## Review Triage Log

- (none yet)
