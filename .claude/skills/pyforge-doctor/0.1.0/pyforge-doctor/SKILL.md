---
name: pyforge-doctor
description: >
  Pre-flight and fleet-watch diagnostics via the doctor CLI (check,
  monitor, diagnose, backlog-intake). Use when running pyforge doctor
  grammar, POST /stations/doctor/mcp, or working in
  src/shared/packages/pyforge-doctor/. Findings stay advisory or Warden
  inputs — not a second PR gate. Do not import pyforge.doctor internals.
  Do not use for conda-forge recipe authoring (conda-forge-expert) or
  station personas.
---

# pyforge-doctor

## Overview

Compiles `src/shared/packages/pyforge-doctor/` (PyPI `pyforge-doctor` 0.1.0) as an
agentskills.io content skill for the **doctor** station. Source: local path
`src/shared/packages/pyforge-doctor` @ commit `865b95dc951c` (`source_ref: local`).
Forge tier: **Quick** (SKF `skf-extract-public-api` + source-reading; T1-low).
Public extract: `main`. Console script: `doctor = pyforge.doctor.__main__:main`
[SRC:pyproject.toml:L46-L47]. Package `__init__.py` is empty — other components
integrate via the CLI, never by importing internal modules
[SRC:src/pyforge/doctor/__init__.py].

Doctor reports **operability, not policy**. Findings stay **advisory** or
Warden *inputs* — they are **not a second PR gate** and never a competing PR
verdict [SRC:src/pyforge/doctor/verdict.py:L1-L9].

## Description

Pre-flight + fleet-watch diagnostics CLI consolidating pyforge-warden +
cf_atlas signals into one schema-validated `DoctorReport`
[SRC:pyproject.toml:L8].

## Quick Start

Run from the repository root via FR-13 grammar (never a hardcoded absolute
path) [SRC:src/pyforge/doctor/__main__.py:L106-L110]:

```bash
pixi run -e pyforge-doctor doctor --version
pyforge doctor check
pyforge doctor monitor --fleet
pyforge doctor diagnose --target <feedstock>
```

**Check** (`doctor check`) [SRC:src/pyforge/doctor/__main__.py:L116-L214]:
pre-flight engines / env hygiene / opt-in durability / bmad-core /
sibling-dreams. `--json` emits one schema-valid `DoctorReport`.

**Monitor** (`doctor monitor --fleet`) [SRC:src/pyforge/doctor/__main__.py:L220-L268]:
`--fleet` is required. Default `--watch` axes: `staleness,cve`.

**Diagnose** (`doctor diagnose --target … [--prescribe]`)
[SRC:src/pyforge/doctor/__main__.py:L271-L298]: gather one target; `--prescribe`
partitions/ranks; without it, findings are reported but not partitioned.

**Backlog intake** (`doctor backlog-intake <identifier>`)
[SRC:src/pyforge/doctor/__main__.py:L301-L325]: scan deferred-work ledgers.

<!-- [MANUAL:additional-notes] -->
Findings stay advisory. Do not treat a Doctor exit code as a second PR
verdict. Do not replace conda-forge-expert.
<!-- [/MANUAL:additional-notes] -->

## Common Workflows

**Pre-flight:** `pyforge doctor check [path] [--json]` → `main` dispatches
`_run_check` [SRC:src/pyforge/doctor/__main__.py:L502-L560].

**Fleet pulse:** `pyforge doctor monitor --fleet [--watch AXIS[,AXIS…]]`
[SRC:src/pyforge/doctor/__main__.py:L220-L233].

**One target:** `pyforge doctor diagnose --target TARGET [--prescribe]`
[SRC:src/pyforge/doctor/__main__.py:L271-L293].

**Exit projection:** any `fail` finding → exit `2`; `warn` never changes
the exit code; empty findings → `0` [SRC:src/pyforge/doctor/verdict.py:L6-L9].
That process exit is operability, not a GitHub PR gate.

## Key API Summary

| Function | Purpose | Key params |
|---|---|---|
| `main` | CLI entry (`doctor` console script) | `argv` |
| `exit_code_for` | Project findings to `{0, 2, 130}` | `findings` / `DoctorReport` |

## Key Exports

Public SKF extract of `__main__.py` (Quick mode): `main`
[SRC:src/pyforge/doctor/__main__.py:L502]. Console script:
`doctor = pyforge.doctor.__main__:main` [SRC:pyproject.toml:L46-L47].
Unified grammar is `pyforge doctor …` (FR-13), not a second public
`doctor` binary contract for personas.

## Usage

Always invoke via `pyforge doctor` from repo root. Do not
`from pyforge.doctor import …` in other stations. Personas emit grammar
and `POST /stations/doctor/mcp` only.

## Key Types

**`Finding`** [SRC:src/pyforge/doctor/models.py:L237-L248] — `source`,
`check`, `status`, `message`, `evidence`. Advisory signal, not a PR
verdict.

**`DoctorReport`** — schema-validated envelope of findings (+ optional
prescriptions).

## Architecture at a Glance

- **CLI** — sole public contract [SRC:src/pyforge/doctor/__main__.py:L1-L33].
- **Verdict** — sole owner of exit-code projection; operability not policy
  [SRC:src/pyforge/doctor/verdict.py:L1-L16].
- **Gather plugins** — `doctor-gather` / `doctor-prescribe` entry points
  [SRC:pyproject.toml:L49-L51].

## CLI

```text
doctor --version
doctor check [path] [--engines [NAME]] [--env [NAME]] [--durability]
             [--bmad-core] [--sibling-dreams] [--scope repo|runtime|all]
             [--list] [--json]
doctor monitor --fleet [--watch AXIS[,AXIS...]] [--target MAINTAINER]
               [--source SOURCE] [--json] [--surface PATH]
doctor diagnose --target TARGET [--prescribe] [--json]
doctor backlog-intake <identifier> [path] [--json]
```

`--version` is top-level only [SRC:src/pyforge/doctor/__main__.py:L215-L218].

<!-- [MANUAL:api-notes] -->
Do not implement the Wave B portal pulse in this skill. Do not add
`pyforge.*` under `src/platform/`.
<!-- [/MANUAL:api-notes] -->
