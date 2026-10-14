---
title: '99.2: Every CI job carries its pause switch'
type: 'feature'
created: '2026-10-13'
status: 'in-progress'
baseline_revision: 'e564ba8d91bc4196c89f93474f3bca253991a067'
flag-exempt: detector-or-gate   # the gate sweep and its completeness rule; a gated gate reports a silent green (spec-feature-flag-governance Q2)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-99-1-the-ci-surfaces-are-declared-once-and-the-workflows-are-judged-against-them.md
  - docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md
  - docs/governance/ci-surfaces.yaml
  - scripts/ci_surface_gates.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_ci.py
  - .github/workflows/pyforge-station-tests.yml
  - .github/workflows/platform-ci.yml
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** After Story 99.1 the registry names every CI surface and its switch, but only seven jobs and one step
read a switch (`docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md` § 1.1–1.2). About 25 push, pull-request and
scheduled jobs cannot be paused at all, and there is no master switch. Separately, `preflight_ci.py` evaluates a job
`if:` only when it is a `needs.<job>.outputs.<x>` comparison (`_job_holds`); every other condition raises
`_Unevaluable`, the site turns `unknown`, and the lane runs. A sweep that puts a `vars.*` fragment in front of every
job's condition would therefore turn every site `unknown` unless the resolver learns the fragment grammar.

**Approach:** Story 99.1's checker gains a render mode and a completeness rule; `preflight_ci` gains a declared-state
resolver for the fragment grammar.

- **`scripts/ci_surface_gates.py --render`.** For every active workflow (registry `state` other than `retired` and
  `paused-manually`), for every job with a push, pull-request or schedule trigger, write the fragment in front of the
  job's existing condition:
  `github.event_name == 'workflow_dispatch' || (vars.PAUSE_ALL_CI != 'true' && vars.PAUSE_<WORKFLOW> != 'true' [&& vars.PAUSE_<WORKFLOW>_<JOB> != 'true'] && (<existing condition>))`.
  `<WORKFLOW>` is the registry's derived name for the file (upper snake case of the file stem, one rule, in the
  registry's `conventions`). The job-level term appears only on a `cost: high` row (ruling Q2). A job with no
  condition gets `(true)` as its inner term, written as the fragment without the trailing conjunction. The six
  grandfathered names (ruling Q7) keep gating where they gate today: the render adds the convention terms beside
  them, never in place of them. Comments above each `if:` name the registry and the render command. The render is
  idempotent: a second run is byte-identical.
- **Completeness rule in `--check`.** An active push, pull-request or schedule job with no row, or a row whose job
  lacks its fragment, is a finding. With the sweep done, `--check` exits 0 on the tree.
- **Declared-state resolver in `preflight_ci.py`.** A small evaluator for the fragment grammar only: `||`, `&&`,
  parentheses, `==` and `!=` against string literals, the names `github.event_name`, `vars.<NAME>` and the existing
  `needs.<job>.outputs.<x>` form. `vars.X` resolves to the registry's declared state: a `paused` row reads `'true'`,
  any other row and an unregistered name read `''` (GitHub's value for an unset variable). `github.event_name`
  resolves to `'pull_request'` (the preflight models a pull request). Anything outside the grammar keeps today's rule:
  `unknown`, and the lane runs, said so. Story 99.5 later layers the live snapshot on top of this resolver.
- **No lost condition.** Every job's existing condition survives inside the fragment, byte-identical; a test parses
  every workflow before and after and asserts the inner term equals the old condition for every job.

Ledger key: `99-2-every-ci-job-carries-its-pause-switch`.
Type / Effort / Deps: feature / M / S-99.1.

### Living CAP citations

- **`spec-pyforge-steward` CAP-166** (FR-39): the gate sweep, the completeness rule and the declared-state resolver.
- **CAP-159** (lanes are read from the workflows): the resolver keeps lane selection reading the workflow files.
- **AD-1**: the render rewrites workflow files from the registry; it owns no second list. **AD-8** does not bind a
  `scripts/` checker; its exit codes follow the repo convention (0 clean, 1 findings, 2 cannot read).
- **Flag:** `flag-exempt: detector-or-gate`.
- **Origin.** `docs/dreams/pyforge-steward.md`, 2026-10-12 (ci pause control plane); rulings Q1, Q2, Q5, Q7.

## Acceptance Criteria

- **AC1 — Swept.** After `--render`, every push, pull-request and schedule job in every active workflow carries its
  fragment; `python scripts/ci_surface_gates.py --check` exits 0; a second `--render` changes nothing.
- **AC2 — No condition lost.** For every job, the condition inside the fragment equals its pre-sweep condition
  (parsed comparison, recorded fixture of the pre-sweep tree); the six grandfathered switches still gate their jobs.
- **AC3 — Completeness reds.** A fixture workflow with a push job and no row, and a fixture whose row's job lacks its
  fragment, each make `--check` exit 1 naming the workflow and job.
- **AC4 — Resolver.** With the registry's two live pauses, `preflight_ci` evaluates every swept site without an
  `unknown` caused by a `vars.*` or `github.event_name` term; lane selection over the 2026-10-12 fixture diffs is
  identical before and after the sweep; a fixture registry with `PAUSE_ALL_CI` declared `paused` evaluates every job
  to skip, and a `workflow_dispatch` event context evaluates them to run.
- **AC5 — Meta-tests green.** `src/shared/packages/pyforge-steward/tests/meta/test_workflow_path_filters_match.py`
  and `src/shared/packages/pyforge-core/tests/meta/test_conformance_lane_wired.py` pass; every workflow still parses
  as YAML. `actionlint` is not in the estate (`pixi.toml` declares no `actionlint`), so the epic's actionlint clause
  is met by the parse and the meta-tests; the story records that deviation.

## Boundaries & Constraints

- Only `if:` lines and the comments above them change in workflow files; triggers, steps, paths filters and job
  names stay byte-identical.
- No repository variable is read or written; the resolver reads the registry only.
- `workflow_dispatch` ignores every pause (ruling Q5's carve-out).
- No required-status-checks change (ruling Q6).

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| job `if: ${{ needs.changes.outputs.station == 'true' }}` | fragment wraps it; resolver evaluates the inner needs term as today |
| job with no `if:` | fragment with inner `(true)` omitted, still idempotent |
| reusable `workflow_call`-only workflow | not swept; judged through its caller's row (99.1's rule) |
| `golden-path-promotion` (`needs: container`) | swept; still skips transitively with `container` |
| a step-level switch (`PLATFORM_CI_PUSH_REGISTRY`) | untouched; it is a `ci-step` row |
| `vars.PAUSE_X` with no row | `''`, and `--check` reds the unregistered name |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-166 (FR-39), minted 2026-10-12.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-12 (ci pause control plane) entry.
- Epic: Epic 99, Stories 99.1–99.7.
- Ledger key: `99-2-every-ci-job-carries-its-pause-switch`.
- Ledger status at mint: `backlog`.
- Deps: S-99.1. `marshal factory dispatch` stamps `baseline_revision` with the launch commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."99"`.
- Specced 2026-10-13, before Story 99.1 landed, from Story 99.1's spec (the registry shape) and the epic's text; the
  implementing session reads the landed registry and checker first and follows them where they differ.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-guild ci-surface-gates-check` — expected: exit 0 (AC1).
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_ci_surface_gates.py -q` — expected: pass (AC1–AC3).
- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_preflight_ci.py -q` — expected: pass (AC4).
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass.
- `pixi run --frozen -e pyforge-guild detectors-ci` and `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

## Spec Change Log

- 2026-10-13: specced from Epic 99's Story 99.2 text and Story 99.1's spec, ahead of 99.1's landing so the steward
  chain runs unattended (operator direction 2026-10-13). Adds the fragment-grammar resolver detail the epic implies
  (`preflight_ci` evaluates only `needs` comparisons today) and records the missing `actionlint`.
