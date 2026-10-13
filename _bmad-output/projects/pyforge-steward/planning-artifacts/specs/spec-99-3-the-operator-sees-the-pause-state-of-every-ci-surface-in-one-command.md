---
title: '99.3: The operator sees the pause state of every CI surface in one command'
type: 'feature'
created: '2026-10-13'
status: 'ready-for-dev'
baseline_revision: '233e07909b5f7e89e49744cdeb642cdc0985b177'
flag:
  key: pyforge.steward.ci_pause_control       # new; minted by this story (one flag per CAP: 99.4 and 99.5 reuse it)
  provider: openfeature-file                  # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through Epic 76's overlay
  scope: global                               # v1 is global only
  fallback: every steward ci verb refuses naming the flag; the registry and its check (Stories 99.1, 99.2) are flag-free and unchanged
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-99-1-the-ci-surfaces-are-declared-once-and-the-workflows-are-judged-against-them.md
  - docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md
  - docs/governance/ci-surfaces.yaml
  - scripts/ci_surface_gates.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  - src/platform/config/flags.json
  - docs/governance/flag-inventory/pyforge-steward.md
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Nothing reports which CI surfaces are paused, since when, why or until when. The Pages deploy sat in
`waiting` from 2026-10-06 to 2026-10-12 unseen (`docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md` § 1.4), two
pauses carry no review date in any machine-readable place, and Doctor, Herald and Marshal have nothing to read.

**Approach:** A `ci` duty in the steward package with two read verbs, `status` and `vars`, a shipped frozen schema
for `status --json`, and a gitignored snapshot of the repository variables. Steward reaches GitHub through `gh` by
subprocess (AD-1); `main()` owns the exit code (AD-8).

- **Inputs, all through `gh`.** `gh api rate_limit` first: an unauthenticated `gh` or a core limit at 0 refuses with
  a documented exit code, never a green table. Then `gh variable list --repo rxm7706/local-recipes --json
  name,value,updatedAt`; `gh api repos/rxm7706/local-recipes/actions/workflows` (each workflow's `state`); the last 20
  runs per workflow (`gh run list --workflow <file> --limit 20 --json conclusion,status,createdAt,event`); pending
  deployments for the deploy rows (`gh api repos/rxm7706/local-recipes/actions/runs/<id>/pending_deployments` for a
  run in `waiting`). The registry is Story 99.1's `docs/governance/ci-surfaces.yaml`, read through the same loader
  `scripts/ci_surface_gates.py` uses (import the module's loader or shell to it; never a second parser).
- **One row per surface:** `id`, switch, declared `state`, live value of the switch, `paused_since`, `review_by` with
  days left or `overdue`, owner, last green run, and one verdict: `live`, `paused`, `opt-in-off`, `paused-manually`,
  `retired`, `drift` (the live value or workflow state differs from the declared one, or a `disabled_manually`
  workflow has no row), `stuck` (a deployment `waiting` over 24 h, or five or more consecutive `cancelled` runs —
  the row's `stuck_rules`), `overdue` (`review_by` passed). Precedence when several apply: `drift`, `stuck`,
  `overdue`, then the state verdict.
- **`--json`.** Validates against `src/pyforge/steward/data/ci-status-schema.json`
  (`$id: urn:local-recipes:pyforge-steward:ci-status-schema`, additive changes only): `{fetched_at, repo,
  rate_limit, rows[]}`. It is the one shape Doctor, Herald and Marshal consume.
- **`ci vars --refresh`.** Writes `.steward/ci-vars.json` (`{fetched_at, repo, variables: {NAME: value}}`), gitignored;
  `ci vars` without `--refresh` prints the snapshot and its age. Story 99.5 reads it.
- **Flag.** `pyforge.steward.ci_pause_control` in `src/platform/config/flags.json` and `flag-overlays.json` (dev on),
  read through `pyforge.core.flags.read_boolean`; off, both verbs refuse naming the flag. The flag inventory row
  lands with the story.
- **Duty count.** `DUTIES` grows by one; `tests/unit/test_cli.py` and `tests/unit/test_restore_duty.py` move with it
  (28 after Story 100.2's `estate`, so 29 here; read the live count, never assume it).

Ledger key: `99-3-the-operator-sees-the-pause-state-of-every-ci-surface-in-one-command`.
Type / Effort / Deps: feature / M / S-99.1.

### Living CAP citations

- **`spec-pyforge-steward` CAP-166** (FR-39): `steward ci status` and `ci vars`, the schema, the snapshot.
- **AD-1** (`gh` by subprocess), **AD-7** (one duty, `DutyResult`), **AD-8** (exit codes). Team memory: an
  unauthenticated GitHub probe fails open, so the rate-limit read comes first.
- **Flag:** `pyforge.steward.ci_pause_control` (new).
- **Origin.** The 2026-10-12 Dream entry; rulings Q1, Q5, Q8.

## Acceptance Criteria

- **AC1 — Verdicts.** On a recorded `gh` fixture (variables, workflow states, 20 runs each, one pending deployment),
  `ci status` yields: the two live pauses `paused` with their `review_by`; the four opt-ins `opt-in-off`; a replay of
  the 2026-10-06 waiting deploy `stuck`; a five-cancelled streak `stuck`; a live value the registry declares
  otherwise `drift`; a `disabled_manually` workflow with no row `drift` naming it; an elapsed `review_by` `overdue`.
- **AC2 — Refusals.** An unauthenticated `gh` and a rate limit of 0 each exit with the documented refusal code and
  print no table; the flag off makes both verbs refuse naming the flag.
- **AC3 — Schema.** `ci status --json` on the fixture validates against the shipped schema; a schema test pins `$id`.
- **AC4 — Snapshot.** `ci vars --refresh` on the fixture writes `.steward/ci-vars.json` with `fetched_at`; `.gitignore`
  lists the file; `ci vars` prints the snapshot's age.
- **AC5 — Duty count.** Both count assertions move by one and pass; `steward --help` lists `ci`.
- **AC6 — Nothing live.** No test calls a live `gh`; a fake subprocess records every argv.

## Boundaries & Constraints

- Read-only: no `gh variable set|delete`, no workflow enable or disable (Story 99.4 writes, operator-only).
- No second registry parser; no copy of the switch convention in the duty.
- Doctor, Herald and Marshal read `ci status --json` on their own chains and never import `pyforge.steward`.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| a variable the registry does not name | `drift` row for the unregistered name |
| a `retired` row whose workflow file still exists | `drift` |
| `gh run list` fails for one workflow | that row's last-green is `unknown`, others still print, exit reflects the partial read |
| `review_by` today | 0 days left, not overdue |
| `--json` with the flag off | refusal, no JSON |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-166 (FR-39), minted 2026-10-12.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-12 (ci pause control plane) entry.
- Epic: Epic 99, Stories 99.1–99.7.
- Ledger key: `99-3-the-operator-sees-the-pause-state-of-every-ci-surface-in-one-command`.
- Ledger status at mint: `backlog`.
- Deps: S-99.1. `marshal factory dispatch` stamps `baseline_revision` with the launch commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."99"`.
- Specced 2026-10-13 from the epic's text and Story 99.1's spec; the implementing session reads the landed registry
  and checker first and follows them where they differ.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_ci_status.py -q` — expected: pass (AC1–AC4, AC6).
- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_cli.py src/shared/packages/pyforge-steward/tests/unit/test_restore_duty.py -q` — expected: pass (AC5).
- `pixi run --frozen -e pyforge-guild detectors-ci` and `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.
- Operator, after landing, with `gh` authenticated: `pixi run --frozen -e pyforge-steward pyforge steward ci status` — expected: exit 0 and the two live pauses read `paused`.

## Spec Change Log

- 2026-10-13: specced from Epic 99's Story 99.3 text ahead of Story 99.1's landing so the steward chain runs
  unattended (operator direction 2026-10-13). Flag block written as the six-field mapping the flag gate requires.
