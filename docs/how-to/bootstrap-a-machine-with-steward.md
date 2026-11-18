---
sources:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/bootstrap.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/session.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/contract.md
verified: 2026-11-18
---

# How to bootstrap a machine with steward

Use steward's bootstrap duties to check a machine's prerequisites, set up a checkout, wire your shell, and confirm a session is ready to work.

## When to use this

- You are on a new machine, or a machine that has not run PyForge before.
- You have a fresh clone and want to know it is healthy before you change anything.
- You are starting a session and want one verdict on its preconditions.
- A tool cannot find `pixi` or the repository root from your shell.

## When to skip this

- You only need a scratch worktree on a machine that already works. Use `pyforge steward workspace start`; see [Manage worktrees with BMAD](manage-worktrees-with-bmad.md).

:::note
**Prerequisites.** `pixi` must be installed for any of these to run, and a checkout must exist for all but the first clone. Run from the repository root. The commands below use `-e pyforge-guild`, the session default environment, which carries steward.
:::

## The duties at a glance

| Duty | Writes? | What it does |
| --- | --- | --- |
| `steward init` | No | Reports the `pixi`, `git`, `gh` and `podman` prerequisites, each with a named remedy. |
| `steward shell-init` | No | Prints a shell snippet for `eval`. |
| `steward validate-fast` | Not executed here | The fast gate: prerequisites, `environment.yaml` sync, a steward CLI smoke. |
| `steward session check` | No | One verdict over the seven session preconditions. |
| `steward setup` | Yes | Clones when the destination is missing, runs `pixi install`, installs the pre-commit hooks. |
| `steward initrepo` | Yes | Scaffolds `pyforge.toml` when absent, materializes the environment, runs `validate-fast`. |

## Steps

### 1. Check the machine's prerequisites

```bash
pixi run -e pyforge-guild pyforge steward init
```

```text
steward init: prereq report
  ok   pixi: 0.81.0 (floor >= 0.80.0)
  ok   git: 2.56.0
  ok   gh: 2.102.0
  FAIL podman: install-podman: https://podman.io/docs/installation
steward init: FAIL
```

Each `FAIL` line names its remedy. The pixi floor is read from the repository's own `requires-pixi` pin. The duty exits `0` when every prerequisite is met and `1` when one is not. Add `--json` for a machine-readable report.

### 2. Set up the checkout

```bash
pixi run -e pyforge-guild pyforge steward setup --env pyforge-guild
```

`setup` clones the repository when `--dest` does not exist (from `--url`, which defaults to the local-recipes GitHub URL), runs `pixi install` for the environment, and installs the pre-commit hooks. `--dest` defaults to the current repository root.

`--env` defaults to `pyforge-guild`; the commands on this page pass it so the environment is on the line. `--env local-recipes` materializes the 10 GB recipe-factory environment instead: use it only for recipe work.

:::caution
Do not run `setup` from a linked worktree: git hooks are shared with the primary checkout, so installing them there changes every worktree.
:::

The hook install sits behind the kill switch `pyforge.steward.setup_hooks`.

### 3. Onboard the checkout

```bash
pixi run -e pyforge-guild pyforge steward initrepo --env pyforge-guild
```

`initrepo` writes a minimal `pyforge.toml` when the checkout has none, materializes the environment, then runs `validate-fast`. `--repo PATH` names another pixi project root. `--env` has the same `pyforge-guild` default as `setup`.

### 4. Confirm the checkout is green

```bash
pixi run -e pyforge-guild pyforge steward validate-fast --env pyforge-guild
```

`validate-fast` composes three checks: the prerequisites of step 1, that `environment.yaml` is in sync with `pixi.toml` (the same check as `steward provision --verify`), and a `steward --version` smoke in the named environment. Run it again whenever you want a quick answer to "is this checkout still usable?"

### 5. Wire your shell

```bash
eval "$(pixi run -e pyforge-guild pyforge steward shell-init)"
```

The snippet exports `PYFORGE_REPO_ROOT`, prepends `~/.pixi/bin` to `PATH`, and registers bash completion for `steward`. The completion offers every duty the parser registers: its word list is read from the parser when the snippet is printed, so `steward pr<Tab>` offers `provision` and `preflight`. It completes the console script `steward`, not `pyforge steward`, and only in bash. It is idempotent: evaluating it twice changes nothing more. `shell-init` itself sets nothing; it only prints. To keep the wiring, add the `eval` line to your shell profile yourself.

### 6. Check the session before you work

```bash
pixi run -e pyforge-guild pyforge steward session check
```

```text
steward session check: gate report
  ok   pixi-guild: .../.pixi/envs/pyforge-guild is materialized
  ok   bmad-method: no HARD/FAIL integrity findings (via `pixi run -e pyforge-guild bmad-drift-check`)
  FAIL gh-auth: You are not logged into any GitHub hosts. To log in, run: gh auth login
       remedy: gh auth login
  ...
steward session check: FAIL
```

The seven findings are `pixi-guild`, `bmad-method`, `token-kit`, `gh-auth`, `codegraph-index`, `tier3-feed` and `scribe-recall`. Each failing one prints a `remedy:` line with the command to run. `--project SLUG` names the BMAD project whose Tier-3 sprint feed is checked; without it the duty reads `BMAD_ACTIVE_PROJECT`, then the marker file, and checks nothing when neither names a project. Add `--json` for a machine-readable report.

## How to tell it worked

| Exit | Meaning |
| --- | --- |
| `0` | The duty ran and reported ok. |
| `1` | The duty ran and reported not ok: a prerequisite or precondition failed. |
| `2` | A usage error, or a kill switch that is off. |
| `70` | An internal error. A crash is never reported as `1`. |

A machine is ready when `init`, `validate-fast` and `session check` each exit `0`. Read the exit code directly (`echo $?`), never through a pipe.

## Tips

- `setup` and `initrepo` were not executed for this page; their behaviour is taken from the station contract and `--help`. `validate-fast` was not executed either.
- A failing `gh-auth` also means GitHub probes elsewhere may fail open. Fix it before you trust a drift verdict.
- The full laptop install, with every station, is `pixi install -e pyforge-foundry-full`; [`environments.md`](../reference/environments.md) lists what each environment carries.
- Every flag and exit code is a row of the station contract, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/contract.md`.
