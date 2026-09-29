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
`src/shared/packages/pyforge-steward` @ commit `865b95dc951` (`source_ref: local`).
Forge tier: **Quick** (SKF `skf-extract-public-api` + source-reading; T1-low).
3 CLI exports documented (`build_parser`, `resolve_duty`, `main`).
The package `__init__.py` exports only `__version__` — other components integrate
via the CLI, never by importing internal modules [SRC:src/pyforge/steward/__init__.py:L10-L22].

## Description

The Provisioner's CLI — credential lifecycle, deployment, provisioning and budget
duties for the factory's platform layer [SRC:pyproject.toml:L8]. README names the
core verbs `steward keys / deploy / provision / budget / sync / workspace`
[SRC:README.md:L3-L4]. `main()` is the sole owner of the process exit code (AD-8)
[SRC:src/pyforge/steward/cli.py:L1-L7].

## Quick Start

Run from the repository root (never a hardcoded absolute path). Unified grammar
is `pyforge steward …`; the console script is `steward`
[SRC:pyproject.toml:L52-L53]:

```bash
pixi run -e pyforge-steward steward --version
pixi run -e pyforge-steward steward keys list
pixi run -e pyforge-steward steward provision --list
pixi run -e pyforge-steward steward budget show
```

**Keys** (`steward keys`) [SRC:src/pyforge/steward/cli.py:L192-L198]:
encrypt/decrypt/rotate/list/audit/revoke — credential lifecycle.

**Provision** (`steward provision --list`) [SRC:src/pyforge/steward/cli.py:L374-L428]:
list pixi environments; `--list-modules` / `--module` / `--env` / `--verify` are
flags on the duty, not nested verbs.

**Budget** (`steward budget set|show|check`) [SRC:src/pyforge/steward/cli.py:L431-L433]:
machine-readable ceiling; `check` may request `EXIT_BUDGET_NOT_CONFIGURED` (3)
when no metered source exists [SRC:src/pyforge/steward/cli.py:L25-L33].

<!-- [MANUAL:additional-notes] -->
**Track** (`steward track assemble --run-dir DIR --out PATH`) (Story 53.3 / hub:CAP-3):
write one tracked `track.json` from a run dir. Field list is marshal-relayed
(`TRACK_FIELDS`); this duty is the Track writer. Not a detector.
<!-- [/MANUAL:additional-notes] -->

## Common Workflows

**Dispatch:** `main(argv)` [SRC:src/pyforge/steward/cli.py:L891] parses with
`build_parser()` [SRC:src/pyforge/steward/cli.py:L124] then
`resolve_duty(ns.duty).run(ns)` [SRC:src/pyforge/steward/cli.py:L817]. A duty
returns `DutyResult` and never calls `sys.exit()` [SRC:src/pyforge/steward/interfaces.py:L7-L9].

**List environments:** `steward provision --list [--json]`.

**Credential list:** `steward keys list`.

**Pipeline truth:** `steward suite` (Epic 15).

## Key API Summary

| Function | Purpose | Key params |
|---|---|---|
| `main` | Argparse entry (`steward` console script); maps DutyResult to exit codes | `argv` |
| `build_parser` | Builds `prog="steward"` parser and duty subparsers | — |
| `resolve_duty` | Returns the Duty implementation for a registered name | `name` |
| `Duty.run` | Execute a duty; must not raise SystemExit | `ns` |

## Key Exports

Public SKF extract of `cli.py` (Quick mode): `build_parser`, `resolve_duty`,
`main` [SRC:src/pyforge/steward/cli.py]. Console script:
`steward = pyforge.steward.cli:main` [SRC:pyproject.toml:L52-L53].

Registered duties [SRC:src/pyforge/steward/cli.py]: `keys`, `deploy`,
`provision`, `budget`, `sync`, `workspace`, `upgrade`, `suite`, `init`,
`shell-init`, `setup`, `initrepo`, `validate-fast`, `restore`, `revoke`,
`track`, `guards`. `guards` is a library (catalog / lacking / source-ground),
never a PR verdict.

## Usage

Always invoke `steward` (or `pyforge steward`) from repo root. Do not
`from pyforge.steward import KeysDuty` in other stations. Personas act only
through FR-13 grammar and FR-11 MCP — this content skill is consulted, not a
license to import internals (AD-7).

Exit codes [SRC:src/pyforge/steward/cli.py:L19-L23]: `0` ok · `1` duty failed ·
`2` usage · `70` internal · `130` interrupted. A crash is never reported as `1`.

## Key Types

**`DutyResult`** [SRC:src/pyforge/steward/interfaces.py:L19-L25] — frozen
`ok`, `summary`, `details`. Optional `details["exit_code"]` is a request;
only `main()` acts on it.

**`Duty`** [SRC:src/pyforge/steward/interfaces.py:L28-L36] — Protocol with
`name` and `run(ns) -> DutyResult`.

**`NullDuty`** [SRC:src/pyforge/steward/interfaces.py:L39-L51] — seam for an
unregistered name; registered duties are real implementations
[SRC:src/pyforge/steward/cli.py:L826].

## Architecture at a Glance

- **CLI** — sole public contract and sole exit-code owner
  [SRC:src/pyforge/steward/cli.py:L1-L7].
- **Duty** — unit of platform work; returns evidence, never exits
  [SRC:src/pyforge/steward/interfaces.py:L1-L9].
- **Resolve** — lazy imports so `steward --help` does not load keys/sync
  checkout guards [SRC:src/pyforge/steward/cli.py:L844-L850].

## CLI

```text
steward --version
steward keys {encrypt,decrypt,rotate,list,audit,revoke}
steward deploy …
steward provision --list [--json]
steward provision --list-modules [--json]
steward budget {set,show,check}
steward sync …
steward workspace {start,ls,status,clean}
steward upgrade …
steward suite …
steward init|shell-init|setup|initrepo|validate-fast [--json]
```

<!-- [MANUAL:api-notes] -->
steward track assemble --run-dir DIR --out PATH
<!-- [/MANUAL:api-notes] -->
