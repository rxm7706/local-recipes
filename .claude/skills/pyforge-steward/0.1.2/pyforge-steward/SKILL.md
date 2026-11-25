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
`src/shared/packages/pyforge-steward` @ commit `2e2ceaba98` (`source_ref: local`).
Forge tier: **Forge** (SKF `skf-extract-public-api` over ast-grep 0.45.3; T1).
First compiled from `865b95dc951` (Story 33.1); recompiled in place at 0.1.0 on
2026-11-01 (steward Story 29.4) and again on 2026-11-12 (steward Story 29.5, the
fixes the EGM audit of 2026-11-05 accepted: STW-R-F4, STW-R-F7, with STW-R-F5
carried) from the scope widened with `pages_duty.py` and `cutover.py`, the station
contract `contract.md` as a doc source, and the real `steward --help`, the way
Story 29.1 and atlas Stories 33.1 and 33.2 did.
Rebuilt as 0.1.1 on 2026-11-18 with skf-update-skill at Forge tier over ast-grep
0.45.3 (steward Story 126.5): a full re-extraction at `424ce69fc2`.
Updated to 0.1.2 on 2026-11-25 by skf-update-skill at the same tier (steward
Epic 135, spec-pyforge-steward:CAP-183), from the source at `2e2ceaba98`: the
scope gained `bootstrap.py` and `machine.py`, the modules behind `init`,
`shell-init`, `setup`, `initrepo` and `validate-fast`.
86 exports documented from 9 modules (`build_parser`, `resolve_duty` and `main`
among them); each is listed in Full API Reference.
The package `__init__.py` exports only `__version__` — other components integrate
via the CLI, never by importing internal modules [SRC:src/pyforge/steward/__init__.py:L10-L22].

## Description

The Provisioner's CLI — credential lifecycle, deployment, provisioning and budget
duties for the factory's platform layer [SRC:pyproject.toml:L8]. README names the
verbs `steward keys / deploy / provision / budget / sync / workspace` and the estate,
CI pauses, Pages and the preflight [SRC:README.md:L5-L6]; the parser registers 31
duties [SRC:src/pyforge/steward/cli.py:L74-L106]. `main()` is the sole owner of the
process exit code (steward's AD-8) [SRC:src/pyforge/steward/cli.py:L1-L7].

**The public contract** is
`_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/contract.md`
(spec-pyforge-steward:CAP-179): every verb path and flag, the retired verbs, the MCP
tools and targets, every feature-flag key, environment variable and exit code
[SRC:README.md:L10-L13]. The MCP tool names, exit codes and flag keys in this skill
are rows of that file; where they differ, the contract and the code win.

## Quick Start

Run from the repository root (never a hardcoded absolute path). `pyforge-guild`,
the session default environment, carries steward; on a laptop the SBOM
`pixi install -e pyforge-foundry-full` includes it too. Unified grammar is
`pyforge steward …`; the console script is `steward`
[SRC:pyproject.toml:L53]:

```bash
pixi run -e pyforge-guild steward --version
pixi run -e pyforge-guild pyforge steward init
pixi run -e pyforge-guild steward keys list
pixi run -e pyforge-guild steward provision --list
pixi run -e pyforge-guild steward budget show
pixi run -e pyforge-guild pyforge steward workspace start <slug>
pixi run -e pyforge-guild pyforge steward estate plan --due
pixi run -e pyforge-guild pyforge steward ci status
pixi run -e pyforge-guild pyforge steward preflight verify-deferred --since YYYY-MM-DD
pixi run -e pyforge-guild pyforge steward cutover plan --check
```

**Keys** (`steward keys`) [SRC:src/pyforge/steward/cli.py:L492]:
encrypt/decrypt/rotate/list/audit/revoke/exec — credential lifecycle. `exec`
runs a command with a scoped GitHub Enterprise token in its environment (the
only delivery path), behind the flag `pyforge.steward.ghe_fleet_credentials`
[SRC:src/pyforge/steward/cli.py:L482-L489]. That flag is off in every
environment, so `keys exec` refuses until the operator flips it.

**Provision** (`steward provision --list`) [SRC:src/pyforge/steward/cli.py:L1202]:
list pixi environments; `--list-modules` / `--module` / `--prove-class-path` /
`--plugin` / `--skill` / `--env` / `--runner` / `--json` / `--verify` are
flags on the duty, not nested verbs.

**Budget** (`steward budget set|show|check`) [SRC:src/pyforge/steward/cli.py:L1276]:
machine-readable ceiling; `check` exits 3 (`EXIT_BUDGET_NOT_CONFIGURED`) when no
metered spend source is configured, the only answer v1 gives
[SRC:src/pyforge/steward/cli.py:L30-L38].

**Estate** (`steward estate plan|refresh|reconcile|verify|realize|status`)
[SRC:src/pyforge/steward/cli.py:L1503]:
policy-driven estate pin refresh [SRC:src/pyforge/steward/estate.py:L1-L6]. `plan` is the dry run: with `--due` it exits 1
when the last journal is older than 30 days or absent (overdue) and 0 within
cadence, and it exits 3 when its pixi upgrade dry run fails, on every path and
ahead of `--due` [SRC:src/pyforge/steward/estate.py:L445-L460]; `refresh` runs the
upgrade, restores losses, re-locks and journals (exit 3 on a dirty tree, on `main`,
or when a step refuses); `reconcile` regenerates the derived surfaces
(`environment.yaml` after a `pixi.toml` change) and reconciles spec-surface drift
(exit 1 when a gating check fails); `verify` installs the default tier in a
detached worktree and runs the CI lanes; `realize` re-applies side-effect installs
(agents: `--plan` only); `status` prints the last journal. Behind the flag
`pyforge.steward.estate_refresh`: every estate verb exits 3 while it is off
[SRC:src/pyforge/steward/estate.py:L27-L28].

**CI** (`steward ci status|vars|pause|resume`) [SRC:src/pyforge/steward/cli.py:L1399]
[SRC:src/pyforge/steward/ci.py:L1-L4]: CI pause visibility. `status` (`--json`)
reports the pause state of every CI surface (exit 1 on a partial read, with the
envelope still printed); `vars` reads or refreshes the gitignored ci-vars snapshot;
`pause` / `resume` are dry runs unless `--yes` (exit 1 when `gh variable set` or
`delete` fails). Behind the flag `pyforge.steward.ci_pause_control`: exit 3 while
it is off, or when gh cannot read [SRC:src/pyforge/steward/ci.py:L22]
[SRC:src/pyforge/steward/ci.py:L31-L32].

**Pages** (`steward pages build|deploy|status`) [SRC:src/pyforge/steward/cli.py:L1439]
[SRC:src/pyforge/steward/pages_duty.py:L1-L5]: the one Pages workflow — `build`
writes the fleet board's input and runs `pages-check`, `deploy` runs `pages.yml`,
`status` reads the live root and the last run. Behind the flag
`pyforge.steward.pages_duty`: exit 3 while it is off, refused before any subprocess
[SRC:src/pyforge/steward/pages_duty.py:L42-L43].

**Preflight** (`steward preflight verify-deferred [--since YYYY-MM-DD]`)
[SRC:src/pyforge/steward/cli.py:L1485] [SRC:src/pyforge/steward/preflight_verify.py:L1-L13]:
the pre-push preflight's catch-up. Lists every run that left lanes to CI
(touched scope) and every push that skipped the preflight, then runs the full
preflight on HEAD: exit 0 green, 1 red, 3 could not run (no `pixi`, or the
preflight's configuration error), 130 interrupted
[SRC:src/pyforge/steward/preflight_verify.py:L33-L34].

**Cutover** (`steward cutover plan|flip`) [SRC:src/pyforge/steward/cli.py:L667-L710]
[SRC:src/pyforge/steward/cutover.py:L1-L9]: `plan` generates (`--regenerate`,
`--append`, behind the kill switch `pyforge.steward.cutover_ledger_write`) or
validates (`--check`, the default: writes nothing, exits 1 on a finding) the
capability ledger `docs/foundry/capability-ledger.yaml`; `flip --to
{local-recipes,foundry}` sets `pyforge.cutover_root` and is refused while a Marshal
loop runs: a run state under the loop home (`BMAD_LOOP_HOME_ROOT`, else
`~/.bmad-loops`) or under the checkout's own `.bmad-loop/runs/` that does not show
its run over, which the refusal names [AST:src/pyforge/steward/cutover.py:L185].
The operator flips the root by hand; an agent runs `plan --check`. The
verb that copied trees into foundry is retired (Story 121.2): the parser has only
`plan` and `flip`, and a retired verb is a usage error (exit 2).

**Init** (`steward init [--profile NAME] [--class CLASS] [--deep] [--list] [--repo PATH] [--json]`)
[SRC:src/pyforge/steward/cli.py:L408-L446] [SRC:src/pyforge/steward/machine.py:L1-L23]:
machine readiness, one verdict per profile. The profiles are `desktop` (the
default), `container`, `pod`, `ocp` and `nkp`, each run with the profiles it
requires; `--profile` is repeatable and takes `all`. The checks are rows of
`docs/governance/machine-readiness.yaml`, and each one that is not ok prints
`remedy (agent|operator): <command>` [SRC:README.md:L24-L33]. `--class`
(repeatable: `software`, `configuration`, `environment`, `usable`) runs only the
checks of that class with every check one of them needs, and a narrowed run is not
the profile's verdict; `--deep` also runs the checks marked deep (ask a cluster,
start one throwaway linux/amd64 container, which pulls one small image), which
otherwise report skipped and never block; `--list` prints the profiles and their
checks and probes nothing; `--repo` names the checkout to judge. Read-only: it
installs nothing and writes nothing, and a probe inside an environment runs
`pixi run --as-is`. Exit 0 when every chosen profile is ready, 1 when one is not
(or is unsupported on this platform), 2 for an unknown profile, 3 when the data
file is missing or invalid [SRC:src/pyforge/steward/machine.py:L50-L53].
`validate-fast` and `initrepo` gate on the desktop profile's software rows (pixi,
git, gh); a container engine belongs to the `container` profile and is never a
prerequisite of desktop work [SRC:src/pyforge/steward/bootstrap.py:L1-L19]. The
`--json` document is `contract.md` § *The `init` report*; the walk-through is
`docs/tutorials/onboard-a-machine.md`.

**Feature flags.** Each flag above is read through `pyforge.core.flags` from
`src/platform/config/flags.json`; its default per environment (dev, staging,
production) is that tree's `defaultVariant` composed with
`src/platform/config/flag-overlays.json`. A duty whose flag is off stays listed in
`--help`, marked `[disabled: flag … is off]`. Each key, its default and its reader
are rows of `contract.md` § *Feature-flag keys*.

<!-- [MANUAL:additional-notes] -->
**Track** (`steward track assemble --run-dir DIR --out PATH`) (Story 53.3 / hub:CAP-3):
write one tracked `track.json` from a run dir. Field list is marshal-relayed
(`TRACK_FIELDS`); this duty is the Track writer. Not a detector.
<!-- [/MANUAL:additional-notes] -->

<!-- [MANUAL:station-mcp] -->
Station host: steward's MCP face is `POST /stations/steward/mcp` on the platform host. How to start the host, get the
assertion it accepts and send a request: `docs/how-to/reach-a-station-mcp-endpoint.md`.
<!-- [/MANUAL:station-mcp] -->

## Station MCP runner

What `POST /stations/steward/mcp` runs, as the code stands (`contract.md` § *MCP
face*; the closed verb table is django-pyforge's `station_cli.py`, the host code
django-steward's `mcp_asgi.py`; this package ships no MCP server):

| Name | Kind | Runs |
|---|---|---|
| `start_duty` | MCP tool | Takes `target` and `assertion`; starts a supervised run and returns `{"handle": …}` at once. |
| `get_duty` | MCP tool | Takes `handle` and `assertion`; returns the supervisor's record of that run. |
| `run_duty` | supervisor runner, not an MCP tool | The closed table's steward row, behind the kill switch `pyforge.steward.start_tool_cli`. |
| `ci-status` | target | `steward ci status --json` |
| `estate-plan` | target | `steward estate plan --json` |
| `estate-status` | target | `steward estate status --json` |

It runs those three read-only targets and nothing else, in `pyforge-guild`, and
counts exits 0 and 1 as a result. No other duty or verb is reachable through the
face: no `estate refresh`, `ci pause`, `keys`, `deploy`, `pages` or `cutover`. Any
other target is refused before anything runs.

## Common Workflows

**Dispatch:** `main(argv)` [AST:src/pyforge/steward/cli.py:L2035] parses with
`build_parser()` [AST:src/pyforge/steward/cli.py:L338] then
`resolve_duty(ns.duty).run(ns)` [AST:src/pyforge/steward/cli.py:L1889]. A duty
returns `DutyResult` and never calls `sys.exit()` [SRC:src/pyforge/steward/interfaces.py:L7-L9].

**Machine readiness:** `pyforge steward init [--profile NAME]` → `InitDuty`
[AST:src/pyforge/steward/bootstrap.py:L291], which returns `run_init(ns)`
[AST:src/pyforge/steward/machine.py:L1277]. Each check that is not ok names its
remedy and who may run it (`agent` or `operator`).

**List environments:** `steward provision --list [--json]`.

**Credential list:** `steward keys list`.

**Pipeline truth:** `steward suite` (Epic 15).

**Landing worktree:** `pyforge steward workspace start <slug>` / `status` /
`clean` [SRC:src/pyforge/steward/cli.py:L1326] — preferred over a hand-run
`git worktree add`.

**Estate refresh:** `pyforge steward estate plan --due`, then `refresh`, then
`reconcile` → `EstateDuty` [AST:src/pyforge/steward/estate.py:L748].

**CI pause inventory:** `pyforge steward ci status` → `CiDuty`
[AST:src/pyforge/steward/ci.py:L1367].

**Deferred lanes:** `pyforge steward preflight verify-deferred` → `PreflightDuty`
[AST:src/pyforge/steward/preflight_verify.py:L227].

**Pages:** `pyforge steward pages status` → `PagesDuty`
[AST:src/pyforge/steward/pages_duty.py:L526].

**Capability ledger:** `pyforge steward cutover plan --check` → `CutoverDuty`
[AST:src/pyforge/steward/cutover.py:L271].

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
| `PagesDuty` | `pages` duty: build / deploy / status | `ns.pages_verb` |
| `CutoverDuty` | `cutover` duty: plan / flip | `ns.cutover_verb` |
| `InitDuty` | `init` duty: one readiness verdict per chosen profile | `--profile`, `--class`, `--deep`, `--list`, `--repo` |

## Key Exports

Public SKF extract of `cli.py` (Forge tier, ast-grep): `retrofit_help`,
`retrofit_verb_path`, `require_retrofit_flags`, `build_parser`, `resolve_duty`,
`main` [AST:src/pyforge/steward/cli.py:L302]. Console script:
`steward = pyforge.steward.cli:main` [SRC:pyproject.toml:L53].

Registered duties [SRC:src/pyforge/steward/cli.py:L74-L106], one line each from
`steward --help`:

| Duty | Purpose |
|---|---|
| `keys` | credential lifecycle — encrypt / decrypt / rotate / list / audit / revoke / exec |
| `deploy` | perimeter manifests, the static-export publish, and the NKP bring-up on kind (`deploy nic`, behind `pyforge.steward.nkp_deploy`) |
| `provision` | environment and substrate provisioning (flags, not nested verbs) |
| `budget` | cost budgeting and enforcement (`set` / `show` / `check`) |
| `sync` | GitHub Projects V2 ⇄ Jira Cloud reconciliation |
| `workspace` | story-scoped scratch worktrees — `start` / `ls` / `status` / `clean` |
| `upgrade` | BMAD-METHOD core upgrade — pre-flight, deliberate `--apply`, clobber re-apply, pin fan-out, prove-landed (`bmad-core` / `pin-fan-out` / `prove-landed` / `verify`) |
| `suite` | bmad-suite channel product — `pipeline-truth`, `advance` |
| `init` | machine readiness — one verdict per profile (`desktop`, `container`, `pod`, `ocp`, `nkp`) from the checks of `docs/governance/machine-readiness.yaml`, each failing check with its remedy and who may run it; read-only (`--profile` / `--class` / `--deep` / `--list` / `--repo`; exits 0 / 1 / 2 / 3) |
| `shell-init` | emit an idempotent PATH/completions/env shell snippet |
| `setup` | machine bootstrap — clone, `pixi install`, pre-commit hooks |
| `initrepo` | onboard a pixi checkout — scaffold `pyforge.toml`, materialize env, run `validate-fast` |
| `validate-fast` | fast green gate — prerequisites (the desktop profile's software rows: pixi, git, gh), `environment.yaml` sync, steward CLI smoke |
| `restore` | PostgreSQL restore drill — scratch DB plus manifest count assertions (`--drill --backup-path`) |
| `revoke` | stop one runaway subject — revoke its queued Celery tasks, cancel its live supervisor runs (`--sub`) |
| `track` | assemble one tracked `track.json` per run; not a detector |
| `guards` | Hub Guard library — catalog, spec lacking, source-ground; never a PR verdict |
| `cutover` | the capability ledger's generator and validator (`plan`) and the root-of-record flag (`flip`) |
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
through canopy:FR-13 grammar (one entry point) and the canopy:FR-11 station MCP
endpoint — this content skill is consulted, not a license to import internals
(steward's AD-7, the `Duty` protocol).

Exit codes [SRC:src/pyforge/steward/cli.py:L24-L44] [SRC:README.md:L40-L43], the rows
of `contract.md` § *Exit codes*:

| Code | Meaning |
|---|---|
| `0` | the duty ran and reported ok (also `--help`, `--version`) |
| `1` | a duty ran and reported not ok — the only legitimate 1: `init` with a chosen profile not ready (or unsupported on this platform), `estate plan --due` overdue, `ci status` on a partial read, `cutover plan --check` with a finding, `estate reconcile` with a failed gating check, `ci pause`/`resume --yes` when gh fails |
| `2` | usage: an argparse error, a retired verb, `init --profile` with a profile the data file does not define, a kill switch or other flag-gated verb whose flag is off (`ci`, `pages` and `estate` refuse with `3` instead) |
| `3` | a duty's documented refusal: `init` when `docs/governance/machine-readiness.yaml` is missing or invalid; `budget check` not configured; `ci` with `ci_pause_control` off or gh unable to read; `pages` with `pages_duty` off; `estate` with `estate_refresh` off, a failed `plan` dry run, or a refused `refresh`; `preflight verify-deferred` could not run |
| `70` | internal error — an exception escaped a duty, or a `SystemExit` carried an integer outside this table; a crash is never reported as `1` |
| `130` | interrupted (128 + SIGINT) |

`steward deploy nic` and `steward keys exec` pass their child's own non-zero exit
through.

## Key Types

**`DutyResult`** [AST:src/pyforge/steward/interfaces.py:L20] — frozen
`ok`, `summary`, `details`. Optional `details["exit_code"]` is a request;
only `main()` acts on it.

**`Duty`** [AST:src/pyforge/steward/interfaces.py:L29] — Protocol with
`name` and `run(ns) -> DutyResult`.

**`NullDuty`** [AST:src/pyforge/steward/interfaces.py:L39] — seam for an
unregistered name; registered duties are real implementations
[SRC:src/pyforge/steward/cli.py:L2032].

## Architecture at a Glance

- **CLI** — sole public contract and sole exit-code owner
  [SRC:src/pyforge/steward/cli.py:L1-L7].
- **Duty** — unit of platform work; returns evidence, never exits
  [SRC:src/pyforge/steward/interfaces.py:L1-L9].
- **Resolve** — lazy imports so `steward --help` does not load keys/sync
  checkout guards [SRC:src/pyforge/steward/cli.py:L482-L486].

## CLI

```text
steward --version
steward keys encrypt --recipient RECIPIENT --output OUTPUT file
steward keys decrypt --identity IDENTITY --output OUTPUT file
steward keys rotate --scope SCOPE --new-identity NEW_IDENTITY [--inventory INVENTORY]
steward keys list [--inventory INVENTORY] [--json]
steward keys audit [--drift] [--path PATH] [--secrets PATH] [--inventory INVENTORY]
steward keys revoke --scope SCOPE [--inventory INVENTORY]
steward keys exec --scope {ghe-fleet-read,ghe-fleet-pr-draft} [--approval REF] [--inventory INVENTORY] ...
steward deploy …
steward provision [--list-modules] [--module NAME] [--prove-class-path] [--plugin NAME] [--skill NAME] [--env NAME] [--runner {bmad-loop}] [--list] [--json] [--verify]
steward budget set --cap CAP
steward budget show [--json]
steward budget check
steward sync …
steward workspace start [--from BRANCH] [--json] slug
steward workspace ls [--json]
steward workspace status [--json] [slug]
steward workspace clean [--merged-only] [--delete] [--json] [slug]
steward upgrade bmad-core --target X.Y.Z [--apply] [--branch NAME] [--installer BIN] [--no-shims] [--json] [--package-root DIR] [--installed-package-root DIR] [--catalog-dir DIR] [--repo-root DIR] [--installed-version X.Y.Z]
steward upgrade pin-fan-out --package {bmad-loop,bmad-method} --from X.Y.Z --to X.Y.Z [--repo-root DIR] [--loops-home DIR] [--json]
steward upgrade prove-landed [--repo-root DIR] [--loops-home DIR] [--no-init] [--json]
steward upgrade verify [--repo-root DIR] [--loops-home DIR] [--no-init] [--json]
steward suite …
steward init [--json] [--profile NAME] [--class {software,configuration,environment,usable}] [--deep] [--list] [--repo PATH]
steward shell-init [--json]
steward setup [--json] [--url URL] [--dest PATH] [--env NAME]
steward initrepo|validate-fast [--json] [--repo PATH] [--env NAME]
steward restore [--drill] --backup-path PATH
steward revoke --sub ID [--python BIN]
steward estate {plan [--json] [--due],refresh [--transitive],reconcile,verify [--env NAME] [--lane NAME] [--probe PACKAGE] [--all] [--keep] [--ignore-ci-pauses] [--budget-minutes N],realize [--plan] [--yes] [--all] [--journal PATH],status [--json] [--all]}
steward ci {status [--json],vars [--refresh],pause --reason REASON --review-by YYYY-MM-DD [--yes] [--i-am-removing-a-merge-gate] <target>,resume [--yes] <target>}
steward preflight verify-deferred [--since YYYY-MM-DD]
steward pages build [--json] [--dry-run] [--stamp] [--site-url URL]
steward pages deploy [--dry-run] [--wait]
steward pages status [--json] [--site-url URL]
steward cutover {plan [--regenerate|--append|--check] [--ledger PATH] [--json],flip --to {local-recipes,foundry} [--flags PATH]}
steward guards|ledger-query|catalog|measure|load|passport|glass|quarantine|session|deck-drift …
```

<!-- [MANUAL:api-notes] -->
steward track assemble --run-dir DIR --out PATH
<!-- [/MANUAL:api-notes] -->

## Full API Reference

Every export the Forge extraction found in the brief's scope, by module, in source
order: signature, one line, citation. This lists what the code defines; other
components still act through the CLI (see Usage).

### `src/pyforge/steward/cli.py`

- `def retrofit_help(path: tuple[str, ...], text: str) -> str` — `text` marked disabled for each OFF switch that gates the duty or sub-verb at `path`. [AST:src/pyforge/steward/cli.py:L302]
- `def retrofit_verb_path(ns: argparse.Namespace) -> tuple[str, ...]` — the invoked path: the duty plus its `<duty>_verb` sub-verb when the parser set one. [AST:src/pyforge/steward/cli.py:L315]
- `def require_retrofit_flags(ns: argparse.Namespace) -> None` — raises `FlagOff` naming the first OFF switch that gates the invoked duty; returns when every one reads ON. [AST:src/pyforge/steward/cli.py:L324]
- `def build_parser() -> argparse.ArgumentParser` — the `prog="steward"` parser, one subparser per name in `DUTIES`. [AST:src/pyforge/steward/cli.py:L338]
- `def resolve_duty(name: str) -> Duty` — the duty implementation for `name`. [AST:src/pyforge/steward/cli.py:L1889]
- `def main(argv: Sequence[str] | None = None) -> int` — parses, checks the invoked duty's kill switches, runs `resolve_duty(ns.duty).run(ns)` and returns the exit code; a `SystemExit` with an integer outside the documented codes returns 70. [AST:src/pyforge/steward/cli.py:L2035]

### `src/pyforge/steward/interfaces.py`

- `class DutyResult` — what a duty returns, frozen: `ok: bool`, `summary: str`, `details: dict[str, object]`. [AST:src/pyforge/steward/interfaces.py:L20]
- `class Duty(Protocol)` — structural contract every duty satisfies: `name: str` and `run(ns: argparse.Namespace) -> DutyResult`. [AST:src/pyforge/steward/interfaces.py:L29]
- `class NullDuty` — the null engine: satisfies `Duty` and does nothing; built with `name: str`. [AST:src/pyforge/steward/interfaces.py:L39]

### `src/pyforge/steward/ci.py`

- `class CiDeps` — dataclass of the duty's seams: `root: Path`, `runner: SubprocessRunner`, `repo: str`, `flag_on`, `now`, `registry_path: Path | None`. [AST:src/pyforge/steward/ci.py:L57]
- `def run_status(deps: CiDeps, *, json_out: bool) -> DutyResult` — the `ci status` verb. [AST:src/pyforge/steward/ci.py:L918]
- `def run_vars(deps: CiDeps, *, refresh: bool) -> DutyResult` — the `ci vars` verb. [AST:src/pyforge/steward/ci.py:L991]
- `def run_pause(deps: CiDeps, *, target: str, reason: str, review_by: str, yes: bool, remove_merge_gate: bool) -> DutyResult` — the `ci pause` verb. [AST:src/pyforge/steward/ci.py:L1164]
- `def run_resume(deps: CiDeps, *, target: str, yes: bool) -> DutyResult` — the `ci resume` verb. [AST:src/pyforge/steward/ci.py:L1278]
- `class CiDuty` — `name = "ci"`; `run(ns)` dispatches on `ns.ci_verb` to the four functions above. [AST:src/pyforge/steward/ci.py:L1367]

### `src/pyforge/steward/cutover.py`

- `def plan(ns: argparse.Namespace, root: Path) -> DutyResult` — `steward cutover plan`: `--check` (the default) judges the ledger and writes nothing; `--regenerate` and `--append` write it unless the kill switch reads off. [AST:src/pyforge/steward/cutover.py:L110]
- `def running_loop_states(home: Path | None = None, repo_root: Path | None = None) -> list[Path]` — every state file that does not show its loop over, sorted: read under the loop home (`home`, else `BMAD_LOOP_HOME_ROOT`, else `~/.bmad-loops`) and, when `repo_root` is given, under that checkout's `.bmad-loop/runs/`. [AST:src/pyforge/steward/cutover.py:L185]
- `def loops_running(home: Path | None = None) -> bool` — whether any loop under the loop home is not shown over (`running_loop_states`). [AST:src/pyforge/steward/cutover.py:L206]
- `def flip_root(flags_path: Path, target: str, realization: Path, *, loop_home: Path | None = None, repo_root: Path | None = None) -> None` — sets the root-of-record flag's `defaultVariant` to `target`; raises `CutoverRootError` on an unknown variant or while a loop runs, naming the running state file. [AST:src/pyforge/steward/cutover.py:L211]
- `class CutoverDuty` — `name = "cutover"`; `run(ns)` sends `plan` to `plan` and `flip` to `flip_root`. [AST:src/pyforge/steward/cutover.py:L271]

### `src/pyforge/steward/estate.py`

- `class EstateDeps` — injectable seams for unit tests: `root`, `runner`, `branch`, `dirty`, `head_sha`, `platform`, `flag_on`, `bmad_latest`, `now`, `enforce_require: bool`. [AST:src/pyforge/steward/estate.py:L46]
- `def run_plan(deps: EstateDeps, *, json_out: bool, due_only: bool) -> DutyResult` — the `estate plan` verb. [AST:src/pyforge/steward/estate.py:L439]
- `def run_refresh(deps: EstateDeps, *, transitive: bool) -> DutyResult` — the `estate refresh` verb. [AST:src/pyforge/steward/estate.py:L603]
- `def run_status(deps: EstateDeps, *, json_out: bool, show_all: bool) -> DutyResult` — the `estate status` verb. [AST:src/pyforge/steward/estate.py:L720]
- `class EstateDuty` — `name = "estate"`; `run(ns)` dispatches on `ns.estate_verb`. [AST:src/pyforge/steward/estate.py:L748]

### `src/pyforge/steward/pages_duty.py`

- `class PagesDeps` — everything a verb reaches outside itself: `root`, `runner`, `flag_on`, `registry_verdict`, `write_fleet_status`, `now`, `sleep`. [AST:src/pyforge/steward/pages_duty.py:L112]
- `def head_commit_time(root: Path) -> str | None` — `git log -1 --format=%cI HEAD` at `root`, or `None` when `root` is not a git checkout. [AST:src/pyforge/steward/pages_duty.py:L126]
- `def write_fleet_status(root: Path) -> Path` — writes the fleet board's input from the tracked ledgers, stamped with HEAD's commit time. [AST:src/pyforge/steward/pages_duty.py:L144]
- `def ci_registry_verdict(root: Path, runner: SubprocessRunner) -> tuple[str | None, str]` — the `pages` row's verdict through `ci status`'s reader, or why it is unavailable. [AST:src/pyforge/steward/pages_duty.py:L160]
- `def run_build(deps: PagesDeps, *, json_out: bool = False, dry_run: bool = False, stamp: bool = False, site_url: str | None = None) -> DutyResult` — the `pages build` verb. [AST:src/pyforge/steward/pages_duty.py:L248]
- `def run_deploy(deps: PagesDeps, *, dry_run: bool = False, wait: bool = False) -> DutyResult` — the `pages deploy` verb. [AST:src/pyforge/steward/pages_duty.py:L342]
- `def run_status(deps: PagesDeps, *, json_out: bool = False, site_url: str | None = None) -> DutyResult` — the `pages status` verb. [AST:src/pyforge/steward/pages_duty.py:L501]
- `class PagesDuty` — `name = "pages"`; `run(ns)` dispatches on `ns.pages_verb`. [AST:src/pyforge/steward/pages_duty.py:L526]

### `src/pyforge/steward/preflight_verify.py`

- `class Owed` — one run or push whose lanes were never run locally: `when`, `where`, `head`, `lanes`, `why` (each `str`) and `line() -> str`. [AST:src/pyforge/steward/preflight_verify.py:L52]
- `class VerifyDeps` — what the duty reads and runs: `root: Path`, `runner`, `out`, `err`, `environ`, `head`. [AST:src/pyforge/steward/preflight_verify.py:L70]
- `def deferred_runs(path: Path, since: date | None) -> tuple[list[Owed], list[str]]` — every journaled run record on or after `since` (UTC) whose `deferred` list is not empty. [AST:src/pyforge/steward/preflight_verify.py:L91]
- `def skipped_pushes(path: Path, since: date | None) -> tuple[list[Owed], list[str]]` — every skip-log line on or after `since` (UTC), branch deletes left out. [AST:src/pyforge/steward/preflight_verify.py:L138]
- `def full_preflight_env(base: Mapping[str, str]) -> dict[str, str]` — the hook's environment for the preflight, with the scope forced to `full`. [AST:src/pyforge/steward/preflight_verify.py:L166]
- `def verify_deferred(deps: VerifyDeps, *, since: date | None) -> DutyResult` — lists what was left to CI since `since`, then runs the full preflight on HEAD. [AST:src/pyforge/steward/preflight_verify.py:L173]
- `class PreflightDuty` — `steward preflight`: one verb, `verify-deferred`. [AST:src/pyforge/steward/preflight_verify.py:L227]

### `src/pyforge/steward/bootstrap.py`

- `class PrereqResult` — one prerequisite row, frozen: `name`, `ok`, `found`, `required`, `remedy` and `to_dict()`; carries a remedy name whenever `ok` is false. [AST:src/pyforge/steward/bootstrap.py:L73]
- `def repo_root() -> Path` — walks up from this module to the local-recipes checkout root; raises `RuntimeError` outside one. [AST:src/pyforge/steward/bootstrap.py:L92]
- `def pixi_floor_version(*, root: Path | None = None) -> str` — the pixi floor from `pixi.toml`'s `requires-pixi`, the registry's own source. [AST:src/pyforge/steward/bootstrap.py:L105]
- `def check_prereq(name: str, *, pixi_floor: str, remedies: dict[str, dict[str, str]] | None = None) -> PrereqResult` — checks one prerequisite and attaches a named remedy on failure (from `remedies`, else the code table). [AST:src/pyforge/steward/bootstrap.py:L157]
- `def prereq_names(root: Path) -> tuple[str, ...]` — the tools `gather_prereqs` checks: the data file's default-profile software rows, else the code's own order (pixi, git, gh). [AST:src/pyforge/steward/bootstrap.py:L210]
- `def prereq_remedies(root: Path) -> dict[str, dict[str, str]]` — each prerequisite's named remedies from its desktop row, else the code table. [AST:src/pyforge/steward/bootstrap.py:L230]
- `def gather_prereqs(*, root: Path | None = None) -> tuple[PrereqResult, ...]` — one `check_prereq` result per default-profile software tool, against the pixi floor. [AST:src/pyforge/steward/bootstrap.py:L237]
- `def shell_init_script(*, root: Path | None = None) -> str` — the idempotent shell snippet: `PYFORGE_REPO_ROOT`, `~/.pixi/bin` on `PATH`, and a bash completion over the parser's duty names. [AST:src/pyforge/steward/bootstrap.py:L245]
- `def shell_init_payload(*, root: Path | None = None) -> dict[str, object]` — the `--json` form: `path_prepend`, `env`, `completions`, `script`. [AST:src/pyforge/steward/bootstrap.py:L270]
- `def format_shell_init(*, as_json: bool, root: Path | None = None) -> str` — the payload as JSON, or the script. [AST:src/pyforge/steward/bootstrap.py:L285]
- `class InitDuty` — `name = "init"`; `run(ns)` returns `machine.run_init(ns)`. [AST:src/pyforge/steward/bootstrap.py:L291]
- `class ShellInitDuty` — `name = "shell-init"`; `run(ns)` emits the snippet for `eval`. [AST:src/pyforge/steward/bootstrap.py:L302]
- `class SetupStep` — one idempotent bootstrap step, frozen: `name`, `ok`, `detail`, `remedy` and `to_dict()`. [AST:src/pyforge/steward/bootstrap.py:L319]
- `def setup_steps(*, dest: Path, url: str | None, env: str) -> tuple[SetupStep, ...]` — clone (when missing), pixi install, and hooks; idempotent. [AST:src/pyforge/steward/bootstrap.py:L366]
- `def format_setup_report(steps: tuple[SetupStep, ...], *, as_json: bool) -> str` — the `setup` report: text ending `steward setup: PASS` or `FAIL`, or JSON (`ok`, `steps`). [AST:src/pyforge/steward/bootstrap.py:L457]
- `def scaffold_pyforge_toml(*, root: Path) -> bool` — writes a minimal `pyforge.toml` when absent; true when it created one. [AST:src/pyforge/steward/bootstrap.py:L471]
- `class ValidateFastStep` — one gate step: `name`, `ok`, `detail`, `remedy` and `to_dict()`. [AST:src/pyforge/steward/bootstrap.py:L484]
- `def validate_fast_steps(*, root: Path, env: str) -> tuple[ValidateFastStep, ...]` — the fast gate, stopping at the first failure: prerequisites, `environment.yaml` sync (skipped when the file is absent), `steward --version` in `env`. [AST:src/pyforge/steward/bootstrap.py:L499]
- `def format_validate_fast_report(steps: tuple[ValidateFastStep, ...], *, as_json: bool) -> str` — the gate report: text ending `steward validate-fast: PASS` or `FAIL`, or JSON (`ok`, `steps`). [AST:src/pyforge/steward/bootstrap.py:L572]
- `def initrepo_steps(*, root: Path, env: str) -> tuple[SetupStep | ValidateFastStep, ...]` — onboards a checkout: the pixi project check, the `pyforge.toml` scaffold, `pixi install -e <env>`, then the `validate-fast` steps. [AST:src/pyforge/steward/bootstrap.py:L586]
- `def format_initrepo_report(steps: tuple[SetupStep | ValidateFastStep, ...], *, as_json: bool) -> str` — the onboard report: text ending `steward initrepo: PASS` or `FAIL`, or JSON (`ok`, `steps`). [AST:src/pyforge/steward/bootstrap.py:L626]
- `class SetupDuty` — `name = "setup"`; `run(ns)` runs `setup_steps` for `--dest`, `--url` and `--env`. [AST:src/pyforge/steward/bootstrap.py:L647]
- `class InitRepoDuty` — `name = "initrepo"`; `run(ns)` runs `initrepo_steps` for `--repo` and `--env`. [AST:src/pyforge/steward/bootstrap.py:L665]
- `class ValidateFastDuty` — `name = "validate-fast"`; `run(ns)` runs `validate_fast_steps` for `--repo` and `--env`. [AST:src/pyforge/steward/bootstrap.py:L682]

### `src/pyforge/steward/machine.py`

- `class DataFileError(PyforgeError, Exception)` — the data file is absent, unreadable or breaks its schema; the verb cannot judge. [AST:src/pyforge/steward/machine.py:L118]
- `def host_platform(system: str | None = None, machine: str | None = None) -> str` — this machine as a pixi platform name (`osx-arm64`, `linux-64`, `win-64`, …). [AST:src/pyforge/steward/machine.py:L140]
- `class MachineDeps` — everything a probe reaches outside the module, each field replaced in unit tests: `root`, `runner`, `which`, `platform`, `environ`, `home`, `session_findings`, `register_row`, `register_probe`, `env_sync`, `lane_environments`, `pixi_floor`. [AST:src/pyforge/steward/machine.py:L214]
- `def production_deps(root: Path) -> MachineDeps` — `MachineDeps(root=root)`, every other seam at its default. [AST:src/pyforge/steward/machine.py:L231]
- `def validate_data(doc: object) -> list[str]` — every way `doc` breaks the data file's contract, as sentences; empty when it holds. [AST:src/pyforge/steward/machine.py:L352]
- `def load_data(root: Path) -> dict[str, Any]` — the data file under `root`, validated; raises `DataFileError` when it is absent, unreadable or invalid. [AST:src/pyforge/steward/machine.py:L462]
- `def profile_closure(data: Mapping[str, Any], chosen: Sequence[str]) -> list[str]` — `chosen` and every profile they require, each once, a required profile before the one that requires it. [AST:src/pyforge/steward/machine.py:L481]
- `def desktop_software_rows(root: Path) -> tuple[tuple[str, dict[str, Any]], ...]` — each tool the default profile's software rows name, in file order, with its row's remedy. [AST:src/pyforge/steward/machine.py:L505]
- `def desktop_software_tools(root: Path) -> tuple[str, ...]` — those tools' names, in file order: what `gather_prereqs` checks. [AST:src/pyforge/steward/machine.py:L517]
- `class Outcome` — what one probe found: `status`, `detail`, `found`, `required`, `composes`, `tool`, `missing`. [AST:src/pyforge/steward/machine.py:L526]
- `class CheckResult` — one row's result: `row`, `status`, `detail`, `found`, `required`, `composes`, `missing`, with the properties `id` and `advisory`. [AST:src/pyforge/steward/machine.py:L539]
- `def select_rows(data: Mapping[str, Any], profiles: Sequence[str], classes: Sequence[str] | None) -> list[dict[str, Any]]` — the rows of `profiles` in file order, narrowed to `classes`, plus every row one of them needs. [AST:src/pyforge/steward/machine.py:L984]
- `class ProfileVerdict` — one profile's verdict: `id`, `title`, `chosen`, `supported`, `ready`, `requires`, `reason`, `counts`, `classes`; `narrowed` is true under `--class`. [AST:src/pyforge/steward/machine.py:L1001]
- `class Report` — `platform`, `root`, `profiles`, `checks`, `found`; `ok` is true when every chosen profile is ready. [AST:src/pyforge/steward/machine.py:L1019]
- `def run_checks(data: dict[str, Any], deps: MachineDeps, *, chosen: Sequence[str], classes: Sequence[str] | None = None, deep: bool = False) -> Report` — runs the rows of `chosen` and of the profiles they require, and judges each profile. [AST:src/pyforge/steward/machine.py:L1041]
- `def remedy_commands(row: Mapping[str, Any], missing: Sequence[str], found: Mapping[str, str]) -> list[str]` — the row's remedy as exact commands: `{env}` once per missing environment, `{found:<id>}` filled in. [AST:src/pyforge/steward/machine.py:L1095]
- `def legacy_prereqs(report: Report) -> list[dict[str, object]]` — the `prereqs` array `init --json` carried before the profiles: the default profile's software tools. [AST:src/pyforge/steward/machine.py:L1142]
- `def report_payload(report: Report) -> dict[str, object]` — the `--json` document: `ok`, `platform`, `root`, `data`, `profiles`, `checks`, `prereqs`. [AST:src/pyforge/steward/machine.py:L1165]
- `def format_report(report: Report) -> str` — the text report: each profile's checks, each failed or blocked one with its `remedy (who): command` lines, then one `steward init: <profile> READY` or `NOT READY` line per chosen profile. [AST:src/pyforge/steward/machine.py:L1190]
- `def listing_payload(data: Mapping[str, Any], profiles: Sequence[str]) -> dict[str, object]` — the `--list --json` document: `data`, `profiles`, `checks`. [AST:src/pyforge/steward/machine.py:L1224]
- `def format_listing(data: Mapping[str, Any], profiles: Sequence[str]) -> str` — the `--list` text: each profile with its checks and their remedies; nothing is probed. [AST:src/pyforge/steward/machine.py:L1256]
- `def run_init(ns: argparse.Namespace, *, deps: MachineDeps | None = None) -> DutyResult` — `steward init`: loads the data file, runs the chosen profiles' rows and reports; asks for exit 3 when the data file cannot be loaded and 2 for an unknown profile; never exits. [AST:src/pyforge/steward/machine.py:L1277]
