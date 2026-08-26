---
name: pyforge-herald
description: >
  Seeds, pulls, and reports Claude Design deck bridge state via the herald
  CLI. Use when running herald deck seed / pull / status, or working in
  src/shared/packages/pyforge-herald/. Do not import pyforge.herald
  internals; the CLI is the public contract. Do not use for conda-forge
  recipe authoring (conda-forge-expert) or Lane 1 CMS (steward).
---

# pyforge-herald

## Overview

Compiles `src/shared/packages/pyforge-herald/` (PyPI `pyforge-herald` 0.1.0) as an
agentskills.io content skill for the **herald** station. Source: local path
`src/shared/packages/pyforge-herald` @ commit `865b95dc951` (`source_ref: local`).
Forge tier: **Quick** (SKF `skf-extract-public-api` + source-reading; T1-low).
2 CLI exports documented (`main`, `dispatch`).
The package `__init__.py` exports only `__version__` — other components integrate
via the CLI, never by importing internal modules [SRC:src/pyforge/herald/__init__.py:L12].

## Description

Dream-to-deck bridge CLI that seeds, pulls, and syncs Claude Design decks
against this repo's `docs/dreams/` and `presentations/` trees via the
`herald deck` subcommands [SRC:pyproject.toml:L8].

## Quick Start

Run from the repository root (never a hardcoded absolute path)
[SRC:src/pyforge/herald/cli.py:L201-L216]:

```bash
pixi run -e pyforge-herald herald deck seed <slug>
pixi run -e pyforge-herald herald deck pull <slug>
pixi run -e pyforge-herald herald deck status [slug]
```

Unified grammar for Path B is `pyforge herald …` (same argv after `pyforge`).

**Seed** (`herald deck seed <slug>`) [SRC:src/pyforge/herald/cli.py:L230-L247]:
seed a deck slug into Claude Design (CAP-1).

**Pull** (`herald deck pull <slug>`) [SRC:src/pyforge/herald/cli.py:L248-L277]:
pull a deck prototype from Claude Design into the repo (CAP-2).

**Status** (`herald deck status [slug]`) [SRC:src/pyforge/herald/cli.py:L278-L293]:
print one JSON array of bridge state for one slug or every known deck (CAP-3)
[SRC:src/pyforge/herald/cli.py:L877-L912].

<!-- [MANUAL:additional-notes] -->
<!-- Add custom notes here. This section is preserved during skill updates. -->
<!-- [/MANUAL:additional-notes] -->

## Common Workflows

**Seed then inspect:** `herald deck seed <slug>` then `herald deck status <slug>`.

**Pull a settled edit:** `herald deck pull <slug>` then `herald deck status <slug>`
to read `stale_mirror` / `sync` in the JSON report.

## Key API Summary

| Function | Purpose | Key params |
|---|---|---|
| `main` | Argparse entry (`herald` console script) | `argv` |
| `dispatch` | Sole `HeraldError` catch point (AD-6) | `operation`, `json_output` |
| `_run_deck_seed` | CAP-1 seed | `args.slug` |
| `_run_deck_pull` | CAP-2 pull | `args.slug`, `--commit`, `--target` |
| `_run_deck_status` | CAP-3 JSON status | `args.slug` optional |

## Key Exports

Public SKF extract of `cli.py` (Quick mode): `main`, `dispatch`
[SRC:src/pyforge/herald/cli.py]. Console script:
`herald = pyforge.herald.cli:main` [SRC:pyproject.toml:L63-L64].
Top-level commands: `deck`, `progress`, `success`, `notice`, `scheduler`
[SRC:src/pyforge/herald/cli.py:L80].

## Usage

Always invoke `herald` from repo root. Do not `from pyforge.herald import …`
in other stations or under `src/platform/`. Agents acting as the herald
persona must emit FR-13 `pyforge herald …` or FR-11 `POST /stations/herald/mcp`.
Lane 1 CMS stays steward.

## Key Types

**`TOOL_NAME`** [SRC:src/pyforge/herald/cli.py:L78] — `"herald"`.

**`TOP_LEVEL_COMMANDS`** [SRC:src/pyforge/herald/cli.py:L80] —
`deck`, `progress`, `success`, `notice`, `scheduler`.

## Architecture at a Glance

- **Deck** — seed / pull / status / watch / push against Claude Design
  [SRC:src/pyforge/herald/cli.py:L226-L228].
- **Status** — machine-readable JSON array only; no extra prose line
  [SRC:src/pyforge/herald/cli.py:L884-L887].
- **CLI** — sole public contract; `__init__` exports `__version__` only
  [SRC:src/pyforge/herald/__init__.py:L12].

## CLI

```text
herald --version
herald deck seed <slug>
herald deck pull <slug> [--commit] [--target prototype]
herald deck status [slug]
```

Parser `prog` is `herald` [SRC:src/pyforge/herald/cli.py:L202].

<!-- [MANUAL:api-notes] -->
<!-- Add custom notes here. This section is preserved during skill updates. -->
<!-- [/MANUAL:api-notes] -->
