---
name: pyforge-steward
description: >
  Provisioner's station CLI — keys, deploy, provision, budget, sync,
  workspace, upgrade, suite, and machine bootstrap. Use when running
  steward duties, pyforge steward grammar, or working in
  src/shared/packages/pyforge-steward/. Do not import pyforge.steward
  internals; the CLI is the public contract. Do not use for conda-forge
  recipe authoring (conda-forge-expert) or station personas.
---

# pyforge-steward

## Overview

Compiles `src/shared/packages/pyforge-steward/` (PyPI `pyforge-steward` 0.1.0) as an
agentskills.io content skill for the **steward** station. Source: local path
`src/shared/packages/pyforge-steward` @ commit `03a7aff5d9` (`source_ref: local`).
Forge tier: **Quick** (SKF `skf-extract-public-api` + source-reading; T1-low).
First compiled from `865b95dc951` (Story 33.1); recompiled in place at 0.1.0 on
2026-11-01 (steward Story 29.4) from the widened scope (`estate.py`, `ci.py`,
`preflight_verify.py`, the duty modules `cli.py` resolves for `estate`, `ci` and
`preflight`) and the real `steward --help`, the way Story 29.1 and atlas
Stories 33.1 and 33.2 did.
3 CLI exports documented (`build_parser`, `resolve_duty`, `main`).
The package `__init__.py` exports only `__version__` — other components integrate
via the CLI, never by importing internal modules [SRC:src/pyforge/steward/__init__.py:L10-L22].

## Description

The Provisioner's CLI — credential lifecycle, deployment, provisioning and budget
duties for the factory's platform layer [SRC:pyproject.toml:L8]. README names the
core verbs `steward keys / deploy / provision / budget / sync / workspace`
[SRC:README.md:L5]; the parser registers 31 duties [SRC:src/pyforge/steward/cli.py:L68-L100].
`main()` is the sole owner of the process exit code (AD-8)
[SRC:src/pyforge/steward/cli.py:L1-L7].

## Quick Start

Run from the repository root (never a hardcoded absolute path). `pyforge-guild`,
the session default environment, carries steward; on a laptop the SBOM
`pixi install -e pyforge-foundry-full` includes it too. Unified grammar is
`pyforge steward …`; the console script is `steward`
[SRC:pyproject.toml:L53]:

```bash
pixi run -e pyforge-guild steward --version
pixi run -e pyforge-guild steward keys list
pixi run -e pyforge-guild steward provision --list
pixi run -e pyforge-guild steward budget show
pixi run -e pyforge-guild pyforge steward workspace start <slug>
pixi run -e pyforge-guild pyforge steward estate plan --due
pixi run -e pyforge-guild pyforge steward ci status
pixi run -e pyforge-guild pyforge steward preflight verify-deferred --since YYYY-MM-DD
```

**Keys** (`steward keys`) [SRC:src/pyforge/steward/cli.py:L443]:
encrypt/decrypt/rotate/list/audit/revoke/exec — credential lifecycle. `exec`
runs a command with a scoped GitHub Enterprise token in its environment (the
only delivery path), behind the flag `pyforge.steward.ghe_fleet_credentials`
[SRC:src/pyforge/steward/cli.py:L433-L440].

**Provision** (`steward provision --list`) [SRC:src/pyforge/steward/cli.py:L1126]:
list pixi environments; `--list-modules` / `--module` / `--env` / `--verify` are
flags on the duty, not nested verbs.

**Budget** (`steward budget set|show|check`) [SRC:src/pyforge/steward/cli.py:L1200]:
machine-readable ceiling; `check` may request `EXIT_BUDGET_NOT_CONFIGURED` (3)
when no metered source exists [SRC:src/pyforge/steward/cli.py:L30-L38].

**Estate** (`steward estate plan|refresh|reconcile|verify|realize|status`)
[SRC:src/pyforge/steward/cli.py:L1427] [SRC:src/pyforge/steward/estate.py:L1-L6]:
policy-driven estate pin refresh. `plan` is the dry run (`--due` exits non-zero
when the last journal is older than 30 days or absent); `refresh` runs the
upgrade, restores losses, re-locks and journals; `reconcile` regenerates the
derived surfaces (`environment.yaml` after a `pixi.toml` change) and reconciles
spec-surface drift; `verify` installs the default tier in a detached worktree
and runs the CI lanes; `realize` re-applies side-effect installs (agents:
`--plan` only); `status` prints the last journal. Behind the flag
`pyforge.steward.estate_refresh` [SRC:src/pyforge/steward/estate.py:L27].

**CI** (`steward ci status|vars|pause|resume`) [SRC:src/pyforge/steward/cli.py:L1323]
[SRC:src/pyforge/steward/ci.py:L1-L4]: CI pause visibility. `status` (`--json`)
reports the pause state of every CI surface; `vars` reads or refreshes the
gitignored ci-vars snapshot; `pause` / `resume` are dry runs unless `--yes`.
Behind the flag `pyforge.steward.ci_pause_control` [SRC:src/pyforge/steward/ci.py:L21].

**Preflight** (`steward preflight verify-deferred [--since YYYY-MM-DD]`)
[SRC:src/pyforge/steward/cli.py:L1409] [SRC:src/pyforge/steward/preflight_verify.py:L1-L13]:
the pre-push preflight's catch-up. Lists every run that left lanes to CI
(touched scope) and every push that skipped the preflight, then runs the full
preflight on HEAD: exit 0 green, 1 red, 3 could not run.

<!-- [MANUAL:additional-notes] -->
**Track** (`steward track assemble --run-dir DIR --out PATH`) (Story 53.3 / hub:CAP-3):
write one tracked `track.json` from a run dir. Field list is marshal-relayed
(`TRACK_FIELDS`); this duty is the Track writer. Not a detector.
<!-- [/MANUAL:additional-notes] -->

<!-- [MANUAL:station-mcp] -->
Station host: steward's MCP face is `POST /stations/steward/mcp` on the platform host. How to start the host, get the
assertion it accepts and send a request: `docs/how-to/reach-a-station-mcp-endpoint.md`.
<!-- [/MANUAL:station-mcp] -->

## Common Workflows

**Dispatch:** `main(argv)` [SRC:src/pyforge/steward/cli.py:L1958] parses with
`build_parser()` [SRC:src/pyforge/steward/cli.py:L328] then
`resolve_duty(ns.duty).run(ns)` [SRC:src/pyforge/steward/cli.py:L1812]. A duty
returns `DutyResult` and never calls `sys.exit()` [SRC:src/pyforge/steward/interfaces.py:L7-L9].

**List environments:** `steward provision --list [--json]`.

**Credential list:** `steward keys list`.

**Pipeline truth:** `steward suite` (Epic 15).

**Landing worktree:** `pyforge steward workspace start <slug>` / `status` /
`clean` [SRC:src/pyforge/steward/cli.py:L1250] — preferred over a hand-run
`git worktree add`.

**Estate refresh:** `pyforge steward estate plan --due`, then `refresh`, then
`reconcile` → `EstateDuty` [SRC:src/pyforge/steward/estate.py:L744].

**CI pause inventory:** `pyforge steward ci status` → `CiDuty`
[SRC:src/pyforge/steward/ci.py:L1366].

**Deferred lanes:** `pyforge steward preflight verify-deferred` → `PreflightDuty`
[SRC:src/pyforge/steward/preflight_verify.py:L227].

## Key API Summary

| Function | Purpose | Key params |
|---|---|---|
| `main` | Argparse entry (`steward` console script); maps DutyResult to exit codes | `argv` |
| `build_parser` | Builds `prog="steward"` parser and duty subparsers | — |
| `resolve_duty` | Returns the Duty implementation for a registered name | `name` |
| `Duty.run` | Execute a duty; must not raise SystemExit | `ns` |
| `EstateDuty` | `estate` duty: plan / refresh / reconcile / verify / realize / status | `ns.estate_verb` |
| `CiDuty` | `ci` duty: status / vars / pause / resume | `ns.ci_verb` |
| `PreflightDuty` | `preflight verify-deferred`: list deferred lanes, run the full preflight | `--since` |

## Key Exports

Public SKF extract of `cli.py` (Quick mode): `build_parser`, `resolve_duty`,
`main` [SRC:src/pyforge/steward/cli.py]. Console script:
`steward = pyforge.steward.cli:main` [SRC:pyproject.toml:L53].

Registered duties [SRC:src/pyforge/steward/cli.py:L68-L100], one line each from
`steward --help`:

| Duty | Purpose |
|---|---|
| `keys` | credential lifecycle — encrypt / decrypt / rotate / list / audit / revoke / exec |
| `deploy` | perimeter manifests, the static-export publish, and the NKP bring-up on kind (`deploy nic`, behind `pyforge.steward.nkp_deploy`) |
| `provision` | environment and substrate provisioning (flags, not nested verbs) |
| `budget` | cost budgeting and enforcement (`set` / `show` / `check`) |
| `sync` | GitHub Projects V2 ⇄ Jira Cloud reconciliation |
| `workspace` | story-scoped scratch worktrees — `start` / `ls` / `status` / `clean` |
| `upgrade` | BMAD-METHOD core upgrade — pre-flight, deliberate `--apply`, clobber re-apply, pin fan-out, prove-landed |
| `suite` | bmad-suite channel product — `pipeline-truth`, `advance` |
| `init` | machine bootstrap — report pixi/git/gh/podman prerequisites with named remedies |
| `shell-init` | emit an idempotent PATH/completions/env shell snippet |
| `setup` | machine bootstrap — clone, `pixi install`, pre-commit hooks |
| `initrepo` | onboard a pixi checkout — scaffold `pyforge.toml`, materialize env, run `validate-fast` |
| `validate-fast` | fast green gate — prerequisites, `environment.yaml` sync, steward CLI smoke |
| `restore` | PostgreSQL restore drill — scratch DB plus manifest count assertions (`--drill --backup-path`) |
| `revoke` | stop one runaway subject — revoke its queued Celery tasks, cancel its live supervisor runs (`--sub`) |
| `track` | assemble one tracked `track.json` per run; not a detector |
| `guards` | Hub Guard library — catalog, spec lacking, source-ground; never a PR verdict |
| `cutover` | flag-gated cutover plan / apply / flip; the default root stays local-recipes |
| `ledger-query` | estate sprint-ledger query and telemetry reporting (`--ready` / `--running`) |
| `catalog` | estate BMAD catalog — check / list / render / pointers / ship / publish |
| `measure` | Build League measure catalog — check / list |
| `load` | extract corridor — idempotent inbound / outbound file loads |
| `passport` | vendor work-passport identity — a fresh UUID per inbound key |
| `glass` | as-of glass — standup / shipped freshness over the inbound corridor |
| `quarantine` | shelf for inbound rows without a passport |
| `session` | one verdict for the session preconditions (pixi env, bmad-method drift, the token-economy kit, gh auth, the Tier-3 feed, scribe) |
| `deck-drift` | flag silent size / etag drift on a pulled Design deck artifact |
| `estate` | policy-driven estate pin refresh — plan / refresh / reconcile / verify / realize / status |
| `ci` | CI pause visibility — status / vars / pause / resume |
| `pages` | the one Pages workflow — build / deploy / status |
| `preflight` | the pre-push preflight's catch-up — `verify-deferred` |

`guards` is a library (catalog / lacking / source-ground), never a PR verdict.
`steward <duty> --help` names each duty's own verbs and flags; a duty whose
feature flag is off stays listed, marked `[disabled: flag … is off]`.

## Usage

Always invoke `steward` (or `pyforge steward`) from repo root. Do not
`from pyforge.steward import KeysDuty` in other stations. Personas act only
through FR-13 grammar and FR-11 MCP — this content skill is consulted, not a
license to import internals (AD-7).

Exit codes [SRC:src/pyforge/steward/cli.py:L24-L28]: `0` ok · `1` duty failed ·
`2` usage · `70` internal · `130` interrupted. A crash is never reported as `1`.

## Key Types

**`DutyResult`** [SRC:src/pyforge/steward/interfaces.py:L19-L25] — frozen
`ok`, `summary`, `details`. Optional `details["exit_code"]` is a request;
only `main()` acts on it.

**`Duty`** [SRC:src/pyforge/steward/interfaces.py:L28-L36] — Protocol with
`name` and `run(ns) -> DutyResult`.

**`NullDuty`** [SRC:src/pyforge/steward/interfaces.py:L39-L51] — seam for an
unregistered name; registered duties are real implementations
[SRC:src/pyforge/steward/cli.py:L1955].

## Architecture at a Glance

- **CLI** — sole public contract and sole exit-code owner
  [SRC:src/pyforge/steward/cli.py:L1-L7].
- **Duty** — unit of platform work; returns evidence, never exits
  [SRC:src/pyforge/steward/interfaces.py:L1-L9].
- **Resolve** — lazy imports so `steward --help` does not load keys/sync
  checkout guards [SRC:src/pyforge/steward/cli.py:L433-L437].

## CLI

```text
steward --version
steward keys {encrypt,decrypt,rotate,list,audit,revoke,exec}
steward deploy …
steward provision --list [--json]
steward provision --list-modules [--json]
steward budget {set,show,check}
steward sync …
steward workspace {start,ls,status,clean}
steward upgrade …
steward suite …
steward init|shell-init|setup|initrepo|validate-fast [--json]
steward restore --drill --backup-path PATH
steward revoke --sub ID
steward estate {plan [--json] [--due],refresh,reconcile,verify,realize,status}
steward ci {status [--json],vars [--refresh],pause,resume}
steward preflight verify-deferred [--since YYYY-MM-DD]
steward pages {build,deploy,status}
steward guards|cutover|ledger-query|catalog|measure|load|passport|glass|quarantine|session|deck-drift …
```

<!-- [MANUAL:api-notes] -->
steward track assemble --run-dir DIR --out PATH
<!-- [/MANUAL:api-notes] -->
