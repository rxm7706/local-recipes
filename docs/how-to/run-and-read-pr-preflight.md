---
sources:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_verify.py
  - scripts/pre_push_preflight.sh
  - src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/contract.md
verified: 2026-11-18
---

# How to run and read the pre-push preflight

Use the `pr-preflight` task to run, on your machine, the lanes CI would run for your diff, and use `pyforge steward preflight verify-deferred` to catch up on anything an earlier run left to CI.

## When to use this

- Before you push a branch that touches anything outside `recipes/`.
- A push was refused by the pre-push hook and you want to know why.
- Earlier pushes ran a reduced preflight, or skipped it, and you want everything verified before a landing.
- You need to choose between the fast run and the full one.

## When to skip this

- You only need the detector suite. See [How to run and understand Detectors](run-and-understand-detectors.md).
- A lane is paused in CI and you want to know how preflight treats it. See [How to pause and resume CI surfaces](pause-ci.md) § *Local twins and preflight*.

:::note
**Prerequisites.** Run from the repository root with your changes committed or in the working tree. Run one full preflight at a time per machine: every run's scribe lane uses the one shared Postgres cluster on `127.0.0.1:5433`, so two runs fail each other.
:::

### What a full run needs on your machine

A full-scope run includes three lanes that need something a fresh checkout does not have. Without them the lane is red for a reason that is not your change.

| Lane | Needs | Get it |
| --- | --- | --- |
| `pyforge-scribe-live-test` | The per-user PostgreSQL + pgvector cluster on `127.0.0.1:5433` | `pixi run -e pyforge-scribe-pg scribe-pg-up` (stop it with `scribe-pg-down`, check it with `scribe-pg-status`) |
| `pyforge-atlas-test` (its two dashboard tests) | Playwright's Chromium for the atlas environment | Nothing: the environment carries it (`playwright-chromium`, `playwright-chromium-headless-shell`, from the `SelfExplainML` channel; steward Story 129.1) |
| `pyforge-steward-live-test` (`test_adoption_register.py::test_wired_column_agrees_with_live_pipeline_truth_for_every_row`) | Herald's manticore studio at `$PYFORGE_STUDIO_ROOT` (default `~/pyforge-studio`) | Install it once per machine: [Herald's manticore studio](manticore-studio.md) |

The third row holds wherever the environment variable `CI` is unset. The adoption register records `bmad-manticore` as `wired`, the test compares that with what `steward suite pipeline-truth` finds on this machine, and a machine with no studio answers `unwired`. A CI runner sets `CI` and is exempt; a laptop is not.

The suites probe the host for anything else they need. A test that cannot run here (for example one that needs a file name the filesystem refuses) reports a skip whose reason names the missing capability. It never fails for that, and it never skips by platform name.

### What the preflight cannot see: a lock written by a newer pixi

The preflight runs with the pixi installed on your machine. CI runs the version the workspace pins (`requires-pixi` in `pixi.toml` and the `pixi-version` of each workflow; `pixi run -e pyforge-guild pixi-version-check` lists every site). A `pixi.lock` written by a newer pixi can pass every local lane and still fail CI in seconds with "lock file not up-to-date with the workspace".

When you change dependencies, write the lock with the pinned version and prove it the way CI does:

```bash
pixi exec --spec "pixi=<pinned version>" pixi lock
git clone --shared . /tmp/lock-proof && cd /tmp/lock-proof
pixi exec --spec "pixi=<pinned version>" pixi install -e pyforge-guild --locked
```

The second command must exit 0 in the clean clone. A check in your working checkout proves nothing here, because a cached environment hides the mismatch.

## How the pieces fit

| Piece | What it is |
| --- | --- |
| `pr-preflight` | A pixi task in `pyforge-guild`. It selects the lanes CI would run for the diff, runs them, and journals each lane. |
| The pre-push hook | `scripts/pre_push_preflight.sh`, wired in `.pre-commit-config.yaml`. It runs `pr-preflight` before a push leaves the machine and refuses the push when it is red. |
| `steward preflight verify-deferred` | The catch-up. It lists what earlier runs deferred or skipped, then runs the full preflight on `HEAD`. |

## Steps

### 1. Choose the scope

A run has one of two scopes, chosen by the variable `PYFORGE_PREFLIGHT_SCOPE`:

| Scope | What runs |
| --- | --- |
| `full` | Every lane CI selects for the diff. This is the merge bar. |
| `touched` | Only the lanes the diff changes, five fast detectors in place of `detectors-ci`, and lint and types when Python under `src/` changed. Every other lane is journaled as deferred: CI arbitrates it. |

When the variable is unset, the feature flag `pyforge.steward.preflight_ci_arbitrates` decides: on means `touched`. The flag is on in the `dev` environment, so a bare run on a laptop is a `touched` run.

### 2. Run it

```bash
PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight
pixi run -e pyforge-guild pr-preflight                       # follows the flag
```

The run prints its scope, what chose it, and one line for each deferred lane. Options go after `--`:

| Option | Effect |
| --- | --- |
| `--jobs JOBS` | The most lanes to run at once (default: the logical CPU count). |
| `--keep-going` | Run every selected lane even when one fails. |
| `--ignore-ci-pauses` | Run lanes that are paused in CI anyway. |

### 3. Read the verdict

| Exit | Meaning |
| --- | --- |
| `0` | Every selected lane passed. |
| `1` | A lane failed. |
| `2` | The lane graph or the scope could not be read. |
| `130` | Interrupted; running lanes are stopped. |

Read the exit code directly (`echo $?`), or write the output to a file and read it back. Never read it through a pipe such as `| tail`: a pipe reports the last command's status and turns a red run green.

A green `touched` run is not the merge bar. Its deferred lanes have not run anywhere yet.

### 4. Let the hook run it on push

The hook runs `pixi run --frozen -e pyforge-guild pr-preflight` on every push and refuses a red one. It skips, and journals the skip, for a branch delete, a `dispatch/*` branch, and a push proved to carry only `preserve/` or `archive/` tags.

### 5. Skip it only on purpose

```bash
PYFORGE_PREFLIGHT_SKIP=1 PYFORGE_PREFLIGHT_SKIP_REASON="<why>" git push
```

This is the one opt-out. It writes the time, the pushed refs and commits, and your reason to `.steward/preflight-skips.log`, then lets the push through. Give a reason; without one the journal reads "no reason given".

### 6. Catch up on what was deferred

```bash
pixi run -e pyforge-guild pyforge steward preflight verify-deferred
pixi run -e pyforge-guild pyforge steward preflight verify-deferred --since 2026-11-01
```

The duty lists every journaled run that left lanes to CI and every push that skipped the preflight, then runs the full preflight on `HEAD`. `--since YYYY-MM-DD` limits the list to that UTC date and later; the default is everything journaled.

| Exit | Meaning |
| --- | --- |
| `0` | The full preflight is green. |
| `1` | It is red. |
| `2` | A bad `--since` value. |
| `3` | It could not run: no `pixi` on `PATH`, or the preflight's own configuration error. |
| `130` | Interrupted. |

Run this before a landing when any push since the last full run used the `touched` scope or the skip.

## What you get

| File | Content |
| --- | --- |
| `.steward/preflight-runs.jsonl` | One JSON line per lane and run: wall time, exit code, and the deferred lanes of a `touched` run. |
| `.steward/preflight-skips.log` | One line per skipped push: time, refs, commits, reason. |

Both are gitignored and local to the checkout.

## Tips

- `pr-preflight` does not cover the container lanes, atlas's browser gate, herald's browser check or scribe's Postgres bring-up. Run those by hand when your diff touches them.
- When a scribe lane is red while another preflight is running, rerun it alone (`pixi run -e pyforge-scribe pyforge-scribe-test`) before you treat it as a real failure.
- `pixi run -e pyforge-guild preflight-budget` reads the journal and reports lanes whose median time is over 1.5 times their budget in `docs/governance/preflight-budgets.toml`. It is a warning, never the preflight's verdict.
- `steward preflight verify-deferred` was not executed for this page, because it runs the full preflight; its behaviour is taken from `--help`, the module and the station contract.
- CI's own detectors check is advisory, so a green CI tick is not evidence that the full preflight would pass. The local full run is.
