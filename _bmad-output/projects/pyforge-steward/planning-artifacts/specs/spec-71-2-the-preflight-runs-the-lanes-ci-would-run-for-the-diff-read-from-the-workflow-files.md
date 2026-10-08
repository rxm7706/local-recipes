---
title: '71.2: The preflight runs the lanes CI would run for the diff, read from the workflow files'
type: 'feature'
created: '2026-09-27'
status: 'in-progress'
baseline_revision: '55178370efd04ed67215393fb3ea4f27acf21ce0'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the preflight runs all 28 lanes for every diff, where CI runs a lane only when its workflow's rules fire. For a marshal-only branch CI runs `pyforge-core-test` and `pyforge-marshal-test` (`.github/workflows/pyforge-station-tests.yml`: the workflow's `on.pull_request.paths`, then its `changes` job — a station's suite on that station's paths, core on any station, all nine on `pyforge-core` / `pyforge-testing-kit` / `pixi.toml` / `pixi.lock` / the workflow file); the preflight ran all nine — 250.4 s of suites CI would not run (Dream, 2026-09-27). `test-ci` (111.5 s) ran too, where `cfe-regression-net.yml` fires only on the CFE paths, `pixi.toml`, `pixi.lock` and its own file; `site-check` runs where `docsite-check.yml` would not.

**Approach:** before running, the runner (Story 71.1) computes the changed paths — `git diff --name-only refs/remotes/origin/main...HEAD` (the full ref: spec-pyforge-core CAP-10, steward CAP-158), plus the working tree's staged, unstaged and untracked paths, since a dirty file can only add lanes. For each lane it finds its CI counterpart in `.github/workflows/*.yml`: a step, in a workflow with an `on.pull_request` trigger, whose `run:` invokes `pixi run … <task>` for the lane's own task or for a task whose `depends-on` closure holds it (CI's `atlas-test` runs `kedro-test`, which depends on `pyforge-atlas-test`), or whose `run:` carries the lane's own command line (the `named-module-gates` matrix runs `python scripts/coverage_gates_ci.py` per station; `detectors.yml` runs `scripts/detectors.py --scope repo`). The lane runs when that workflow fires for the changed paths — `on.pull_request.paths` matched by GitHub's filter-pattern rules (`*` stops at `/`, `**` crosses it; never `fnmatch`), a trigger with no `paths` always fires — and the step's job `if:` holds. A job condition of the form `needs.changes.outputs.<x> == 'true'` or `!= '[]'` (and a matrix over `fromJSON(needs.changes.outputs.<x>)`) is evaluated from that workflow's own `changes` step, run against the same base with `github.event_name` = `pull_request`, `GITHUB_BASE_REF=main` and a scratch `GITHUB_OUTPUT` — its path lists are never copied into steward. Anything the reader cannot evaluate runs the lane: no `refs/remotes/origin/main`, a `paths-ignore`, another `if:` shape or expression, a matrix it cannot expand, a `changes` step that fails, a lane with no CI counterpart (`docs-map-render-test` and `docs-gen-test` today — CI only sees them skip under `pyforge-ci`). The journal line records the selection and, for each skipped lane, the workflow and rule that skipped it.

Ledger key: `71-2-the-preflight-runs-the-lanes-ci-would-run-for-the-diff-read-from-the-workflow-files`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / S-71.1.

### Living CAP citations

- `spec-pyforge-steward` CAP-159 (FR-32); `spec-pyforge-core` CAP-8 / CAP-10 (the station-tests rule and its full-ref base) as Kinship; steward CAP-158 (full refs).

## Acceptance Criteria

- Given a fixture git repository carrying copies of the real `.github/workflows/` files and `pixi.toml`, with one commit on `refs/remotes/origin/main` and a branch commit touching one file under `src/shared/packages/pyforge-marshal/` When the preflight selects lanes Then it selects exactly the five lint-types lanes, `detectors-ci`, `pyforge-doctor-scripts-test`, `docs-map-render-test`, `docs-gen-test`, `pyforge-core-test`, `pyforge-marshal-test` and `pyforge-marshal-coverage-gate`
- Given a branch touching `pixi.toml` When lanes are selected Then every lane is selected except the eight coverage gates — `coverage-gates.yml`'s own trigger paths leave `pixi.toml` out (its `changes` job lists it as shared surface, but the workflow never starts)
- Given a branch touching only a file under `.claude/skills/conda-forge-expert/` When lanes are selected Then `test-ci` is selected and no station suite or coverage gate is
- Given a branch touching only a file under `docs/dreams/` When lanes are selected Then only `detectors-ci`, `pyforge-doctor-scripts-test`, `docs-map-render-test` and `docs-gen-test` are selected
- Given each fixture diff above plus one under `docsite/` When the selection is compared with the lanes the workflows' own rules select (the `changes` steps executed in the fixture repository, the `paths` globs matched by GitHub's rules) Then the two sets are equal, apart from the lanes with no CI counterpart, which are always selected
- Given no `refs/remotes/origin/main` When lanes are selected Then every lane is selected and the journal says why
- Given a workflow whose job `if:` or `paths-ignore` the reader does not recognise When lanes are selected Then that workflow's lanes are selected and the journal names the rule it could not evaluate
- Given an untracked file under `src/shared/packages/pyforge-steward/` on an otherwise marshal-only branch When lanes are selected Then the steward suite and gate are selected too

## Boundaries & Constraints

**Always:**
- Skip a lane only where CI's own rule, read from the workflow files at run time, skips it; a lane that cannot decide runs.
- Read the diff against `refs/remotes/origin/main`, never the short `origin/main`.
- Model the `pull_request` event against `main` — the event that gates a PR.
- The per-lane verdicts stay the lanes' own: a stricter-than-CI lane stays stricter (`detectors-ci` reds locally on any finding, where `detectors.yml`'s sweep is advisory on the runner apart from `cfe_rebuild_guard_check` and `ledger-regression`).

**Never:**
- Do not copy a path list, a station list or a lane-to-workflow table into steward code or data.
- Do not edit a workflow file to make it easier to read — the workflows belong to their own Specs (`spec-pyforge-core` for `pyforge-station-tests.yml`, `spec-coverage-gate-independence` for `coverage-gates.yml`, CAP-153 for `lint-types.yml`).
- Do not run lanes concurrently (Story 71.3).
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| one station | marshal files only | core + marshal suite + marshal gate + lint-types + always-on lanes | — |
| shared surface | `pixi.toml` | every lane but the eight coverage gates | `coverage-gates.yml` does not trigger on `pixi.toml` |
| CFE only | `.claude/skills/conda-forge-expert/**` | `test-ci` + always-on lanes | — |
| Dream only | `docs/dreams/*.md` | the four always-on lanes | — |
| no base | `refs/remotes/origin/main` absent | every lane | journaled reason |
| unknown rule | `paths-ignore`, unrecognised `if:` or matrix | that lane runs | journaled rule |
| `changes` step fails | non-zero exit or unreadable output | its workflow's lanes run | journaled |
| dirty tree | untracked station file | that station's lanes added | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-steward` CAP-159 (FR-32).
Dream: `docs/dreams/pyforge-steward.md` § Realization log → *2026-09-27 — Proposed: the preflight answers in under a minute*.
Ledger key: `71-2-the-preflight-runs-the-lanes-ci-would-run-for-the-diff-read-from-the-workflow-files`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- On a marshal-only branch, `pixi run -e pyforge-guild pr-preflight` — expected: the journal line lists 12 selected lanes and names the rule that skipped each of the other 16.
