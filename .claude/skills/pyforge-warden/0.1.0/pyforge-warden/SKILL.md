---
name: pyforge-warden
description: >
  Runs the warden dependency-hygiene and vulnerability gate via the warden
  CLI (scan / scan --doctor). Use when scanning Python/Conda/Pixi manifests,
  checking the scanner environment, or working in src/shared/packages/pyforge-warden/.
  Do not import pyforge.warden internals; the CLI is the public contract.
  Do not invent a second PR-gate verdict. Do not use for conda-forge recipe
  authoring (conda-forge-expert) or station personas.
---

# pyforge-warden

## Overview

Compiles `src/shared/packages/pyforge-warden/` (PyPI `pyforge-warden` 0.1.0) as an
agentskills.io content skill for the **warden** station. Source: local path
`src/shared/packages/pyforge-warden` @ commit `865b95dc951` (`source_ref: local`).
Forge tier: **Quick** (SKF `skf-extract-public-api` + source-reading; T1-low).
CLI export documented (`main`). Verdict projection (`compose`, `exit_code_for`,
`match_level_rung`) is owned by `verdict.py` and is invoked only by the CLI —
agents must not call those functions to publish a second PR-gate.
The package `__init__.py` exports only `__version__` — other components
integrate via the CLI, never by importing internal modules
[SRC:src/pyforge/warden/__init__.py:L12].

## Description

Unified dependency-hygiene + vulnerability scanner that orchestrates deptry
and osv-scanner over Python / Conda / Pixi manifests, emitting one
schema-validated `ComplianceReport` and a strict CI/CD exit-code gate
[SRC:pyproject.toml:L8].

## Quick Start

Run from the repository root (never a hardcoded absolute path)
[SRC:README.md:L18-L22]:

```bash
pixi run -e pyforge-warden warden scan .
pixi run -e pyforge-warden warden scan . --warn-only
pixi run -e pyforge-warden warden scan --doctor
```

FR-13 unified dispatch (same argv after the station token)
[SRC:src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py:L123-L129]:

```bash
pyforge warden scan .
pyforge warden scan --doctor
```

**Scan** (`warden scan [path]`) [SRC:src/pyforge/warden/cli.py:L453-L460]:
scan a project directory and emit the compliance report. Default path is `.`.
`--format json` puts exactly one schema-valid report on stdout
[SRC:src/pyforge/warden/cli.py:L462-L470]. `--warn-only` is the non-blocking
on-ramp [SRC:src/pyforge/warden/cli.py:L647-L663].

**Doctor** (`warden scan --doctor`) [SRC:src/pyforge/warden/cli.py:L665-L674]:
environment self-check only (engines, offline OSV DB, feed caches). Exits 0
when healthy else 2; never 1 — doctor reports operability, not policy.

<!-- [MANUAL:additional-notes] -->
The CLI (via `verdict.exit_code_for`) is the sole PR-gate publisher. Do not
recompute status or exit codes. Do not import `pyforge.warden`.
<!-- [/MANUAL:additional-notes] -->

## Common Workflows

**Default gate:** `main(["scan", "."])` [SRC:src/pyforge/warden/cli.py:L736]
→ `_run_scan` [SRC:src/pyforge/warden/cli.py:L1060]. Exit codes come only from
`exit_code_for` [SRC:src/pyforge/warden/verdict.py:L109].

**Adopt without blocking:** `warden scan . --warn-only`.

**Prove the install:** `warden scan --doctor` → `_run_doctor`
[SRC:src/pyforge/warden/cli.py:L845].

## Key API Summary

| Function | Purpose | Key params |
|---|---|---|
| `main` | argparse entry (`warden` console script) | `argv` after the script name |
| `_run_scan` | project scan + report emission | parsed `scan` args |
| `_run_doctor` | environment self-check | parsed `scan` args with `--doctor` |
| `compose` | lattice compose (CLI-owned; do not call) | rungs |
| `exit_code_for` | exit projection (CLI-owned; do not call) | status, knobs |
| `match_level_rung` | CVE-match → rung (CLI-owned; do not call) | level |

## Key Exports

Public SKF extract of `cli.py` (Quick mode): `main`
[SRC:src/pyforge/warden/cli.py]. Console script:
`warden = pyforge.warden.cli:main` [SRC:pyproject.toml:L30-L31].
Dispatch maps station token `warden` to that script
[SRC:src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py:L44-L51].

## Usage

Always invoke `warden` (or `pyforge warden`) from repo root. Do not
`from pyforge.warden import compose` / `exit_code_for` in other stations or
in a persona. The persona relays CLI/MCP output; it does not publish a
second PR-gate verdict.

`--doctor` is a flag on `scan`, not a second subcommand
[SRC:src/pyforge/warden/cli.py:L665].

## Key Types

**`Status`** — seven-rung lattice owned by `verdict.py`
[SRC:src/pyforge/warden/verdict.py:L3-L9]. Other modules feed rungs; only
`verdict.py` projects exit codes.

**`ComplianceReport`** — schema-validated stdout contract under `--format json`
[SRC:src/pyforge/warden/cli.py:L31-L33].

## Architecture at a Glance

- **CLI** — sole public contract; `prog` is `warden` [SRC:src/pyforge/warden/report.py:L193].
- **Scan** — discovery → extract → engines → policy → report.
- **Verdict** — sole owner of lattice + exit projection
  [SRC:src/pyforge/warden/verdict.py:L1-L21].
- **Doctor** — operability, never a project policy verdict
  [SRC:src/pyforge/warden/cli.py:L665-L674].

## CLI

```text
warden --version
warden scan [path] [--format text|json] [--warn-only] [--doctor]
warden scan [path] --sbom-output PATH
pyforge warden scan [path]
pyforge warden scan --doctor
```

`[project.scripts]` name is `warden`; FR-13 grammar is `pyforge warden …`
(never a second public grammar that skips `pyforge`).

<!-- [MANUAL:api-notes] -->
<!-- Add custom notes here. This section is preserved during skill updates. -->
<!-- [/MANUAL:api-notes] -->
