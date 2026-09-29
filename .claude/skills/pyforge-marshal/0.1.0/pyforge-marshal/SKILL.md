---
name: pyforge-marshal
description: >
  Deterministic BMAD-loop supervisor: fleet status, loop homes, detector
  check, and Genesis seed via the marshal CLI. Use when running marshal
  status / homes / check / seed, or working in src/shared/packages/pyforge-marshal/.
  Do not import pyforge.marshal internals; the CLI is the public contract.
  Do not use for conda-forge recipe authoring (conda-forge-expert) or station personas.
---

# pyforge-marshal

## Overview

Compiles `src/shared/packages/pyforge-marshal/` (PyPI `pyforge-marshal` 0.1.0) as an
agentskills.io content skill for the **marshal** station. Source: local path
`src/shared/packages/pyforge-marshal` @ commit `865b95dc951` (`source_ref: local`).
Forge tier: **Quick** (SKF `skf-extract-public-api` + source-reading; T1-low).
Quick extract of `cli/main.py` documents `main` (console script
`marshal = pyforge.marshal.cli.main:main`) [SRC:src/pyforge/marshal/cli/main.py:L323]
[SRC:pyproject.toml:L42-L43]. The package `__init__.py` is empty — other
components integrate via the CLI, never by importing internal modules
[SRC:src/pyforge/marshal/__init__.py].

## Description

Deterministic BMAD-loop supervisor: wraps bmad-loop with gates-as-objects,
run supervision, landing, fleet status, and adapter portability
[SRC:pyproject.toml:L8]. Genesis (`marshal seed …`) installs the operating
model; Marshal operates it [SRC:README.md:L8-L10].

## Quick Start

Run from the repository root (never a hardcoded absolute path)
[SRC:src/pyforge/marshal/cli/main.py:L241-L244]:

```bash
pixi run -e pyforge-marshal marshal status
pixi run -e pyforge-marshal marshal homes
pixi run -e pyforge-marshal marshal check
pixi run -e pyforge-marshal marshal seed check --repo-root .
```

**Status** (`marshal status`) [SRC:src/pyforge/marshal/cli/status.py:L279-L305]:
one row per loop home (runtime state, current story, elapsed, budget) from
journals — never a hand-maintained story feed [SRC:src/pyforge/marshal/cli/status.py:L1-L8].
`--project SLUG` scopes the fleet; `--run RUN_ID` needs `--project`.

**Homes** (`marshal homes`) [SRC:src/pyforge/marshal/cli/init.py:L287-L307]:
lists every discovered `loop/<slug>` worktree and verifies isolation. Read-only.

**Check** (`marshal check`) [SRC:src/pyforge/marshal/cli/check.py:L88-L108]:
routes to `scripts/detectors.py` (`--scope repo|runtime|all`, default `all`).

**Seed check** (`marshal seed check`) [SRC:src/pyforge/marshal/cli/seed.py:L413]:
read-only Genesis conformance report. Seven verbs total:
`init`/`adopt`/`check`/`update`/`explain`/`version`/`kit`.

**Seed kit** (`marshal seed kit`) [SRC:src/pyforge/marshal/cli/seed.py:L945]:
provisions a LOOP HOME's token-economy kit (caveman skill + articulate
carve-out, CCR store dir, codegraph index), each gated by its own
`[context]` layer. Dry-run by default, `--apply` provisions; exits 0 on
every completed run -- an unavailable instrument skips its layer with a
named finding and never blocks.

<!-- [MANUAL:additional-notes] -->
<!-- Persona grammar is `pyforge marshal …` (FR-13), not the `marshal` binary. -->
<!-- Track writer is `steward track assemble` (Story 53.3); marshal supplies field enumeration, not track.json. -->
<!-- Session-close ritual, every harness: `scribe capture` (AGENTS.md § Team memory), not restated here. -->
<!-- [/MANUAL:additional-notes] -->

## Common Workflows

**Fleet snapshot:** `run_status` [SRC:src/pyforge/marshal/cli/status.py:L1149]
via `_build_parser` → `status` handler [SRC:src/pyforge/marshal/cli/main.py:L241].

**Isolation audit:** `run_homes` [SRC:src/pyforge/marshal/cli/init.py:L1015]
after `add_homes_subparser` [SRC:src/pyforge/marshal/cli/init.py:L287].

**Detector front door:** `run_check` [SRC:src/pyforge/marshal/cli/check.py:L201]
with `--scope` mirrored from `scripts/detectors.py`.

**Genesis conformance:** `marshal seed check --repo-root .` then optional
`marshal seed adopt` / `marshal seed update` [SRC:README.md:L25-L35].

**Loop-home kit:** `marshal seed kit --repo-root <home> --apply` (or let
`marshal preflight` do it) -- Story 28.3's per-home token-economy kit.

## Key API Summary

| Function | Purpose | Key params |
|---|---|---|
| `main` | argparse entry (`marshal` console script) | `argv` |
| `run_status` | Fleet-wide runtime status | `--project`, `--run` |
| `run_homes` | List loop homes + isolation | `--format` |
| `run_check` | Detector registry front door | `--scope`, `--project` |
| `run_check` (seed) | Genesis read-only check | `--repo-root`, `--project`, `--strict` |
| `run_kit` (seed) | Provision a loop home's token-economy kit | `--repo-root`, `--project`, `--apply` |

## Key Exports

Public SKF extract of `cli/main.py` (Quick mode): `main`
[SRC:src/pyforge/marshal/cli/main.py:L323]. Console script:
`marshal = pyforge.marshal.cli.main:main` [SRC:pyproject.toml:L42-L43].
Handlers used by the core CLI tasks are documented from source-reading
(`run_status`, `run_homes`, `run_check`).

## Usage

Always invoke `marshal` from repo root. Do not
`from pyforge.marshal import …` in other stations. Unified grammar for
personas is `pyforge marshal …` — do not treat the `marshal` binary as a
second public grammar. Do not implement bmad-loop → supervisor ingest here.

## Key Types

**`MarshalContext`** [SRC:src/pyforge/marshal/cli/main.py:L273-L320] —
resolved once at the front door when `--project` is present (`slug`,
`loop_home`, composed `policy`, optional `story`).

**Exit domain** [SRC:src/pyforge/marshal/cli/main.py:L323-L336] —
`main` returns an int in the frozen `{0, 1, 2, 3, 4, 130}` set (AD-7).

## Architecture at a Glance

- **CLI front door** — `main` builds the subparser tree and relays handler
  exit codes [SRC:src/pyforge/marshal/cli/main.py:L241-L270].
- **Status** — runtime state from journals, not sprint-status.yaml
  [SRC:src/pyforge/marshal/cli/status.py:L1-L8].
- **Homes** — structural isolation of loop worktrees
  [SRC:src/pyforge/marshal/cli/init.py:L287-L298].
- **Check** — existing detector registry, not a second engine
  [SRC:src/pyforge/marshal/cli/check.py:L88-L99].
- **CLI** — sole public contract [SRC:src/pyforge/marshal/cli/main.py:L1-L7].

## CLI

```text
marshal --version
marshal status [--project SLUG] [--run RUN_ID]
marshal homes [--format text|json]
marshal check [--scope repo|runtime|all] [--project SLUG]
marshal seed check --repo-root .
marshal seed init <PATH> --slug <SLUG>
marshal seed adopt --repo-root . [--apply --yes]
marshal seed kit --repo-root <LOOP-HOME> [--apply]
```

Bare `marshal` prints usage and exits 0 [SRC:src/pyforge/marshal/cli/main.py:L345-L352].

<!-- [MANUAL:api-notes] -->
<!-- Add custom notes here. This section is preserved during skill updates. -->
<!-- [/MANUAL:api-notes] -->
