---
sources:
  - docs/governance/pin-policy.yaml
  - docs/governance/pin-policy.schema.json
  - docs/governance/realization-register.yaml
  - docs/governance/realization-register.schema.json
  - src/shared/packages/pyforge-steward/src/pyforge/steward/estate.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/estate_reconcile.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/estate_realize.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/estate_verify.py
  - scripts/pin_policy_check.py
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/release-cadence.md
verified: 2026-10-24
---

# How to refresh the estate

Library pins and BMAD floors in `pixi.toml` / `pixi.lock` used to move through a six-step hand
sequence (upgrade, update, install, then regenerate derived files and run suites from memory). That
path is retired: one policy file, one steward duty, and six verbs in order.

This guide is the operator and agent entry point. For BMAD core releases after a refresh, continue
with `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/release-cadence.md`
(steps 1–9); step 7 already hands pixi floor bumps to `estate refresh` and `estate realize`.

## When a refresh is due

Run a dry plan at least monthly, or whenever `pixi.toml` pins need to move:

```bash
pixi run -e pyforge-steward pyforge steward estate plan
```

`plan --due` exits non-zero when the last journal under `.steward/estate-refresh/` is older than
30 days or missing — the cadence gate for scheduled refreshes.

```bash
pixi run -e pyforge-steward pyforge steward estate plan --due
```

Use `plan --json` when you need machine-readable moves, the BMAD table (pinned / installed /
latest), and days since the last journal.

## Pin policy (`docs/governance/pin-policy.yaml`)

Every held package is declared once: `hold` (`never-move` | `cap` | `channel` | `exact` |
`floor-only`), the clause to keep (`cap: "<3"`, `channel: SelfExplainML`, `exact: "4.2.1.*"`, …),
`features` (`*` or a list), `reason`, `authority`, `owner`, and `until` (condition or date that
retires the row). Defaults: `pinning_strategy: latest-up`, `floors_never_lower: true`.

- **Add a hold** — append a row with a real `authority` (Story, CAP, gotcha, or `fnd:CAP-12`) and
  an `until` that says when the row may leave the file.
- **Retire a hold** — delete the row only after its `until` is satisfied; run
  `python scripts/pin_policy_check.py --check` so nothing still depends on the old exclusion.

The canonical upgrade command is **rendered** from the policy: every held package, whatever its
`hold`, becomes an `--exclude` flag, so the upgrade solves with each cap, exact pin and channel
table still in place. Do not maintain a parallel exclude list in comments:

```bash
python scripts/pin_policy_check.py --render-command
```

`pixi.toml` carries one pointer line at the workspace dependency block; `pin-policy-check` (in
`detectors-ci` and `pr-preflight`) reds a stale pointer or an undeclared hold.

## Realization register (`docs/governance/realization-register.yaml`)

Some packages have side effects beyond the pixi environment (BMAD core apply, skf update, caveman
hooks, pre-commit, CLIs, services, import-probed platform libraries). Each row declares `class`
(`installer-tree` | `module` | `harness` | `kit` | `hooks` | `pin-sites` | `cli` | `service` |
`import`), optional `realize` argv (with `operator_gate: true` when it rewrites installer-owned
files), `probe`, and `test`.

- **Add a row** when a new library must be re-applied or probed after its pin moves; keep
  `realization-register-check` green.
- **Retire a row** when the library no longer needs a post-refresh realize/probe path.

## The six verbs (order)

All commands use `pixi run -e pyforge-steward pyforge steward estate …` from the repo root on a
**feature branch** with a **clean tree** (refresh refuses `main` or dirty metadata).

| Verb | Who | Purpose |
| --- | --- | --- |
| `plan` | agents and operators | Dry-run moves through the policy; `--due` for cadence |
| `refresh` | **operator** | Rendered upgrade, loss detection + restore, re-lock, fan-out, journal |
| `realize` | operator `--yes`; agents **`--plan` only** | Re-apply register rows whose packages moved |
| `reconcile` | **operator** | Regenerate derived surfaces, run checks, memlog + scoped spec-surface stamps |
| `verify` | **operator** (default); agents only inside a dispatched landing worktree per station policy | Prove the lock in a **detached worktree** |
| `status` | agents and operators | Read the last journal (or `--all`) |

Session hooks deny agents `pixi update` / `pixi add`; **`estate refresh --transitive`** (which runs
`pixi update`) and **`estate realize --yes`** are operator-only for the same reason.

### 1. `plan`

See above. Resolve any `held-by` rows before an operator runs `refresh`.

### 2. `refresh`

```bash
pixi run -e pyforge-steward pyforge steward estate refresh
```

After upgrade, `pin_policy_check --diff` judges cap loss, flattened channel tables, lowered floors,
and moved never-move packages. A lowered floor means the upgrade raised another package past what the
old floor allows, so `refresh` resets `pixi.toml` and `pixi.lock` to the base, excludes the package it
lowered, and runs the upgrade again (up to four rounds; the journal's `converge` block names each
package it excluded). `pin_policy_restore` then rewrites any declaration still lost;
`pixi lock` re-solves; **`pin_policy_check --fan-out`** compares station `pyproject.toml` /
package pins to the lock. A red fan-out names the **station and file** — fix that pin on that
station's story; the refresh must not land a lock that violates a station range.

Optional operator-only transitive re-solve:

```bash
pixi run -e pyforge-steward pyforge steward estate refresh --transitive
```

Journal path: `.steward/estate-refresh/<date>.json` (suffix `-2`, … if needed). It records moves,
restored losses, fan-out, `realize_due`, and BMAD pinned vs installed.

### 3. `realize`

List due rows (agents stop here):

```bash
pixi run -e pyforge-steward pyforge steward estate realize --plan
```

Operator re-applies side effects:

```bash
pixi run -e pyforge-steward pyforge steward estate realize --yes
```

Use `--all` to walk every register row (operator gates still apply without `--yes`).

### 4. `reconcile`

Regenerates, in order: `environment.yaml`, library-catalog floors (`llms_full_check --fix-floors`),
BMAD-estate catalog (`scribe catalog bmad-estate --write`), env matrix, generated docs
(`docs-environments`, `docs-pixi-tasks`), optional `bump-pixi-version` / `generate-bmad-suite` when
the journal says those packages moved — then runs gating checks (`llms-full-check`, `bmad-estate-check`,
`pin-policy-check`, `pixi lock --check`, …). It appends **spec-surface memlog events** for every
governed path that moved and runs **scoped** `spec_surface_check.py --write-baseline --spec …` (never
a bare global stamp).

The checks and the BMAD-estate catalog run in the `pyforge-guild` env as it is installed
(`pixi run --as-is`), so install that env first. A generator that fails reds the run (exit 1) after
the other generators, the checks and the stamps have run, and the summary names it first; only a
failed `generate-bmad-suite` stops the run early.

```bash
pixi run -e pyforge-steward pyforge steward estate reconcile
```

For hand-edited docs outside `reconcile`, follow [Reconcile spec surface drift](reconcile-spec-surface.md).

### 5. `verify`

Proves the batch in `.steward/estate-verify/worktree` — never the operator's working tree.

**Default tier** (when `--env` is omitted): Guild, core, testing-kit, all eight station envs,
`platform-ci-test`, `pyforge-foundry-full`. **`--all`** installs every `[environments]` entry;
environments excluded for the current platform are recorded as **lock-solved** (journal names
`osx-arm64` / `win-64` explicitly).

CI lanes for a `pixi.toml` / `pixi.lock` change are selected from workflow path filters; paused
lanes honor repo variables (`PAUSE_CONTAINER_BUILDS`, `PAUSE_PLATFORM_CONTAINER_BUILDS`, …) unless
`--ignore-ci-pauses`. **Manual rows** (not run by default): atlas browser gate (`CI=1` atlas tests),
herald browser check, scribe Postgres (`scribe-pg-up` then scribe tests).

```bash
pixi run -e pyforge-steward pyforge steward estate verify
pixi run -e pyforge-steward pyforge steward estate verify --all
pixi run -e pyforge-steward pyforge steward estate verify --env pyforge-guild --lane detectors-ci
```

`--lane` runs that lane plus every lane it depends on, dependencies first. A register probe whose
env this run did not install reads `skipped`, never red (`--all` installs every env). A red row in the
journal carries the last lines the step printed.

Use `--budget-minutes` to cap long `pixi install --frozen` rows; `--keep` leaves the worktree path
in the summary.

### 6. `status`

```bash
pixi run -e pyforge-steward pyforge steward estate status
pixi run -e pyforge-steward pyforge steward estate status --json
```

Shows the latest journal, fan-out verdict, and per-platform verify summaries when present.

## Landing the PR

Any change outside `recipes/` needs the **`maintenance`** label. Merge with a subject Marshal can
read for landing evidence, for example `Merge dispatch/pyforge-steward/100.6 into main`.

Before push on a branch that touches shared pins:

```bash
pixi run -e pyforge-guild pyforge-station-tests
pixi run -e pyforge-guild pr-preflight
```

A refresh PR typically carries **lock-solved** confirmation for `osx-arm64` and `win-64` plus a
green **`estate verify`** on the operator's platform (`linux-64` here).

## After a dispatched agent run

Agents may run `plan` and document `realize --plan` output; they must not run `refresh`,
`reconcile`, `verify`, `realize --yes`, or `refresh --transitive`. The operator on the landing
branch finishes: any due `realize --yes`, `reconcile`, full `verify`, fan-out greens, then push and
open the PR with the label and memlog/scoped stamps `reconcile` did not cover (for example
docs-only follow-ups).
