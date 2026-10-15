---
sources:
  - docs/governance/ci-surfaces.yaml
  - docs/governance/ci-surfaces.schema.json
  - scripts/ci_surface_gates.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/ci.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_ci.py
verified: 2026-10-15
---

# How to pause and resume CI surfaces

GitHub Actions jobs in this repo read pause switches from repository variables. The inventory,
naming rules, and gate fragments all come from one tracked registry:
`docs/governance/ci-surfaces.yaml` (validated by `docs/governance/ci-surfaces.schema.json`).

Use this guide when you need to see what is paused, flip a switch safely, or understand how local
preflight mirrors CI.

## Registry and naming

Each row describes a workflow, job, step, or local twin with:

- `switch` — repo variable name (`PAUSE_*` for pause-by-default surfaces, `ENABLE_*` for opt-ins,
  or `null` when the workflow is dispatch-only or manually parked).
- `state` — `live`, `paused`, `opt-in-off`, `paused-manually`, or `retired`.
- `reason`, `review_by`, `paused_since`, `paused_by` — metadata for paused rows.
- `grandfathered_names` in the registry header — six legacy variable names that predate the
  `PAUSE_*` convention but remain valid.

Workflow jobs that run on `push`, `pull_request`, or `schedule` include a rendered `if:` fragment
from `scripts/ci_surface_gates.py --render`. `detectors-ci` runs `--check` so drift is caught before
merge.

**Master switch:** `PAUSE_ALL_CI` — when `true`, every gated job skips unless the run is
`workflow_dispatch`. `pyforge steward ci status --json` always includes a `master:PAUSE_ALL_CI`
row: while the master is on it reads `drift` (undeclared pause), and every workflow job whose
`if:` reads the master reads `paused` with `paused_by_master: true` on that surface row (the
machine-readable flag; `detail` carries the human text). Surfaces the master does not gate, and
rows whose own switch already pauses them, keep their previous verdict.

**Dispatch carve-out:** `workflow_dispatch` runs ignore pause variables by design (operator
intentional runs). Scheduled and PR/push runs honor pauses.

## Read path — `pyforge steward ci status`

```bash
pixi run -e pyforge-steward pyforge steward ci status
pixi run -e pyforge-steward pyforge steward ci status --json
```

The duty merges the registry with live `gh variable list` and GitHub Actions workflow state. Verdicts
include `live`, `paused`, `opt-in-off`, `paused-manually`, `retired`, `drift`, `stuck`, and
`overdue`. It refuses to report success on an unauthenticated GitHub probe at 0/60 rate limit.

It exits 0 when every surface was read, with the `--json` envelope on stdout. A `retired` row's runs are never read,
so its `last_green_run` is empty. When a live surface's run list cannot be read, the read is partial: the exit code
is 1, that row's `last_green_run` reads `unknown`, and the `--json` envelope still prints on stdout with
`partial: true` and one `run_list_errors` entry per failed workflow. Exit 3 is a refusal, with one line on stderr.

Refresh the local variable snapshot used by preflight (stale after 24 hours):

```bash
pixi run -e pyforge-steward pyforge steward ci vars --refresh
```

## Write path — `pyforge steward ci pause|resume`

Default is dry-run (no `gh` writes, no registry commit):

```bash
pixi run -e pyforge-steward pyforge steward ci pause <surface-id|switch> \
  --reason "…" --review-by 2026-11-01
pixi run -e pyforge-steward pyforge steward ci resume <surface-id|switch>
```

Add `--yes` to apply: sets the repo variable (operator-only outward action), updates the registry
row, appends `.steward/ci-pauses.log`, and runs `scribe capture --type project`.

Pausing a row with `gate: true` (for example `detectors` or `lint-types`) requires
`--i-am-removing-a-merge-gate` after reading the warning — you are turning off a merge gate.

Disabling a workflow in the GitHub UI without a matching `paused-manually` or `retired` registry row
is drift; fix it with `ci pause` / `ci resume` or by updating the registry and re-enabling through
the sanctioned path.

## Local twins and preflight

`pixi run -e pyforge-guild pr-preflight` and the pre-push hook print a banner for lanes paused in
CI and skip those lanes by default. Run the full local twin anyway when you need proof:

```bash
pixi run -e pyforge-guild pr-preflight -- --ignore-ci-pauses
```

`platform-ci-local` and `pyforge-steward-guild-image-build` always run requested stages but still
print the pause banner.

## Weekly canary

`.github/workflows/ci-canary.yml` builds each paused `cost: high` surface once per week (and on
`workflow_dispatch`), gated by `PAUSE_CI_CANARY` like other workflows. `steward ci status` uses the
canary's last green run when judging paused expensive jobs.

## Related checks

```bash
pixi run -e pyforge-guild ci-surface-gates-check
python scripts/ci_surface_gates.py --check --live   # operator, after landing
```

Intake background: `docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md`.
