---
title: '99.1: The CI surfaces are declared once and the workflows are judged against them'
type: 'feature'
created: '2026-10-12'
status: 'in-progress'
baseline_revision: '735c01371935ea844eb12f8ab180cd2083460335'
flag-exempt: detector-or-gate   # a registry check; a gated gate reports a silent green (spec-feature-flag-governance Q2)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md
  - docs/dreams/pyforge-steward.md
  - .github/workflows/pyforge-station-tests.yml
  - .github/workflows/platform-ci.yml
  - scripts/protected_refs_ruleset_check.py
  - scripts/detectors.py
  - docs/governance/guild-roster.json
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The repository's CI pause switches are repository variables that only workflow comments document, and
nothing reads, lists or judges them. Line numbers below are at `938380474e`.

- **What gates what today.** `PAUSE_CONTAINER_BUILDS` gates `guild-container` (`pyforge-station-tests.yml:683`).
  `PAUSE_PLATFORM_CONTAINER_BUILDS` gates `container` and `container-dbgpt` on push and PR (`platform-ci.yml:339-341`,
  `:849-851`); `golden-path-promotion` (`:742`) skips with `container` through `needs:`. Four opt-ins gate on push and
  PR: `PLATFORM_CI_AIR_GAP_PARITY`, `PLATFORM_CI_GKE_PORTABILITY_SMOKE`, `PLATFORM_CI_OCP_PORTABILITY_SMOKE` (each its
  own job, `:1070`, `:1330`, `:1547`, and together `build-platform-image`, `:266-278`), and
  `PLATFORM_CI_PUSH_REGISTRY`, a **step-level** switch in `golden-path-promotion` (`:807`). `PLATFORM_CI_REGISTRY`
  (`:809`) is a **value**, not a switch. Live on 2026-10-12: the two pauses are `true` (set 2026-10-04 and
  2026-10-09), the four opt-ins are unset, and `ACTIONS_ENABLED` was deleted the same day.
- **The rest.** 23 workflow files hold 57 jobs. Six workflows are `disabled_manually` in the GitHub UI since
  2026-08-24 12:06–12:07 (`test-all`, `kedro-viz-publish`, `staged-recipes-linter`, `linter_issue_comment`,
  `reusable-staged-recipes-linter`, `reusable-staged-recipes-linter-selftest`). `platform-deploy` and
  `sync-pypi-mappings` are `workflow_dispatch`-only; `test-linux`, `test-macos` and `test-windows` carry only
  `workflow_call` and `workflow_dispatch`. The other twelve active workflows run on push, PR or schedule: 33 jobs, of which
  only the seven above read a switch.

**Approach:** One tracked registry, `docs/governance/ci-surfaces.yaml`, with a JSON Schema beside it,
`docs/governance/ci-surfaces.schema.json`, and one checker, `scripts/ci_surface_gates.py`, in the shape of
`scripts/protected_refs_ruleset_check.py` (offline by default; a live mode that reads GitHub through `gh`).

- **Registry shape.** Top level: `version`, `conventions` (`pause_prefix: PAUSE_`, `enable_prefix: ENABLE_`,
  `master: PAUSE_ALL_CI`, `dispatch_ignores_pauses: true`), `grandfathered_names` (the six existing names, ruling Q7),
  and `surfaces`. A surface row has `id`, `workflow`, `kind` (`workflow` | `ci-job` | `ci-step` | `scheduled` |
  `local-stage`), `job` and `step` where the kind needs them, `cost` (`low` | `medium` | `high`), `gate` (bool: pausing
  it removes a merge gate), `switch` (a variable name or `null`), `switch_class` (`pause` | `enable` | `value`),
  `state` (`live` | `paused` | `opt-in-off` | `paused-manually` | `retired`), `owner`, and, when `state` is `paused`,
  `paused_since`, `paused_by`, `reason`, `review_by`; optional `local_twin`, `canary`, `transitive` (ids of surfaces
  that skip with this one), `stuck_rules`, `retired_on`.
- **Seeding.** One `workflow` row per workflow file (23); one `ci-job` or `ci-step` row per job or step that reads a
  `vars.*` term today (seven jobs, one step); a `value` row for `PLATFORM_CI_REGISTRY`; `switch: null` on
  `workflow_dispatch`-only and `workflow_call`-only workflows; `paused-manually` on the six UI-disabled workflows with
  `reason: not recorded (asked 2026-10-12)` until the operator answers the Spec's open question; the two live pauses
  as `paused`, `paused_by: operator`, their set dates, the reasons in their workflow comments, and `review_by:
  2026-11-01` (ruling Q8); `transitive: [platform-ci.golden-path-promotion]` on `platform-ci.container`;
  `stuck_rules` on `dashboard.deploy` (a deployment `waiting` over 24 h; five or more consecutive `cancelled` runs).
- **Offline check (`--check`, the default).** Parse every `.github/workflows/*.yml`; collect each `vars.<NAME>`
  reference with its workflow, job, step and comparison. Findings: a referenced name no row declares; a row whose
  declared switch its job's or step's `if:` does not read; a switch name that is neither `PAUSE_*`, `ENABLE_*` nor
  grandfathered; a comparison other than `!= 'true'` for a pause or `== 'true'` for an enable (a `value` row is
  declared, never compared); a registry row naming a workflow file or job that does not exist; a schema violation.
  Exit 0 clean, 1 with findings (each naming workflow, job, step, switch), 2 when it cannot read the tree.
- **Live check (`--check --live`).** Adds one rule from `gh api repos/<repo>/actions/workflows`: a workflow whose
  state is `disabled_manually` with no row in `paused-manually` or `retired` state, and a row declaring
  `paused-manually` whose workflow is `active`. It reads `gh api rate_limit` first and exits 2, never 0, when `gh` is
  unauthenticated or the core limit is exhausted. Never part of `detectors-ci`.
- **Wiring.** A `ci-surface-gates-check` pixi task in the Guild tasks feature runs the offline mode; `scripts/detectors.py`
  gains one repo-scope entry for it, so `detectors-ci` and `pr-preflight` run it; `docs/reference/detectors.md` is
  regenerated by its own generator, never by hand.

Ledger key: `99-1-the-ci-surfaces-are-declared-once-and-the-workflows-are-judged-against-them`.
Type / Effort / Deps: feature / M / none.

### Living CAP citations

- **`spec-pyforge-steward` CAP-166** (FR-39): this story builds the registry, its schema, the convention's check and
  the live mode; Story 99.2 adds the fragments and the completeness rule, 99.3 the status duty.
- **AD-1** (wrap, never reimplement): the live mode shells out to `gh`; no HTTP client. **AD-8** does not bind a
  `scripts/` checker, but its exit codes follow the repo convention: 0 clean, 1 findings, 2 cannot observe.
- **Flag:** `flag-exempt: detector-or-gate`. It judges and never changes behaviour; a flag-gated gate would report a
  silent green.
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, 2026-10-12 (ci pause control plane), and
  `docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md`; the operator's rulings Q1–Q8, recorded verbatim in the
  `spec-pyforge-steward` memlog.

## Acceptance Criteria

- **AC1 — Seeded and clean.** `docs/governance/ci-surfaces.yaml` validates against the schema and holds every row
  the Approach's Seeding list names; `python scripts/ci_surface_gates.py --check` exits 0 on the tree.
- **AC2 — Each offline rule reds.** On a fixture tree per rule, `--check` exits 1 naming the workflow, job (and step)
  and switch: an unregistered `vars.PAUSE_FOO`; a `ci-job` row whose job's `if:` no longer reads its switch; a switch
  `SKIP_FOO` outside both prefixes and the grandfather list; `vars.PAUSE_FOO == 'false'`; a row naming a job that does
  not exist; a `paused` row missing `review_by`. Each fixture fails alone; together they yield six findings.
- **AC3 — The value and the step.** `PLATFORM_CI_REGISTRY` is a `value` row and yields no comparison finding;
  `PLATFORM_CI_PUSH_REGISTRY` is a `ci-step` row and is judged against its step's `if:`, not the job's.
- **AC4 — Live mode.** With a recorded `gh` fixture whose workflow list matches the registry, `--check --live` exits 0;
  with one more `disabled_manually` workflow it exits 1 naming it; with a registry row `paused-manually` whose workflow
  is `active` it exits 1 naming it; with `gh` failing or `rate_limit` at 0 it exits 2. No test calls a live `gh`.
- **AC5 — Wired.** `pixi run --frozen -e pyforge-guild ci-surface-gates-check` exits 0; `scripts/detectors.py` lists
  it once among the repo-scope detectors; `detectors-ci` runs it and stays green; `docs/reference/detectors.md` matches
  its generator.
- **AC6 — Nothing else moves.** No workflow file changes; no repository variable is read or written outside
  `--live`'s read-only calls; the protected-refs check and every existing detector keep their exit codes.

## Boundaries & Constraints

- No workflow file edits: the fragments and the completeness rule are Story 99.2's.
- No outward write of any kind; `--live` is read-only (`gh api` GETs).
- The registry is the one declared source (the `guild-roster.json` / `rulesets/protected-refs.json` shape); the
  checker holds no copy of the grandfather list or the prefixes, and a unit test reds a hard-coded copy.
- The offline mode needs no network and no `gh`; it must pass in CI's fresh clone.
- Python from the Guild environment only; PyYAML and jsonschema are already available there (check
  `docs/reference/library-llms-full.md` before importing anything else).

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| Tree at `938380474e` with the seeded registry | `--check` exit 0 |
| `if: ${{ vars.PAUSE_X != 'true' }}` (wrapped in `${{ }}`) | parsed the same as the bare form |
| Multi-line folded `if: >-` with two `vars.*` terms | both terms collected with their own comparisons |
| `vars.X` inside `env:` or `with:` (not an `if:`) | collected; must be a declared `value` row or a finding |
| A `workflow_call`-only workflow | its jobs are judged through the caller's row, never their own trigger |
| Registry row for a workflow file that was deleted | finding: row names a missing workflow |
| `gh` unauthenticated or rate limit 0 under `--live` | exit 2, message names the cause |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-166 (FR-39), minted 2026-10-12.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-12 (ci pause control plane) entry.
- Epic: Epic 99 (new), Stories 99.1–99.7. `epic-99` and `epic-99-retrospective` are minted with it.
- Ledger key: `99-1-the-ci-surfaces-are-declared-once-and-the-workflows-are-judged-against-them`.
- Ledger status at mint: `backlog`.
- Deps: none. Story 99.2 (fragments and the declared-state resolver) and Story 99.3 (`ci status`) build on it.
- Surface: `marshal-policy.toml` `[epic_surfaces]."99"` (added with this mint).
- Minted 2026-10-12 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-guild ci-surface-gates-check` — expected: exit 0 (AC1, AC5). This story creates the
  task, so it is never a launch-bound gate: `verify_commands` holds only the station suite (MRS-GATE-011).
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_ci_surface_gates.py -q` — expected: pass (AC2–AC4).
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass (the CI `scripts-suite` twin).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0 (AC5).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python3 scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.
- Operator, after landing, with `gh` authenticated: `python scripts/ci_surface_gates.py --check --live` — expected: exit 0 (the six UI-disabled workflows match their seeded `paused-manually` rows).

## Spec Change Log

- 2026-10-12: minted with CAP-166 / FR-39 and Epic 99 from the Dream entry of that date and the operator's rulings
  Q1–Q8. `type: feature`, `flag-exempt: detector-or-gate`. The `disabled_manually` rule runs only in `--live` (memlog
  decision of 2026-10-12: it needs the Actions API, so it never joins the offline `detectors-ci` leg).
- 2026-10-13: `ci-surface-gates-check` moved from the dispatch gates (`**Commands:**`) to *Run before the push*.
  `marshal factory dispatch` refused the launch with MRS-GATE-011: the command is not among steward's
  `verify_commands`, and it cannot be, because this story creates the task. The check still runs before the push, and
  AC1 and AC5 are unchanged.
