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
`src/shared/packages/pyforge-doctor` @ commit `b69fd81eb8` (`source_ref: local`).
Forge tier: **Quick** (SKF `skf-extract-public-api` + source-reading; T1-low).
First compiled from `865b95dc951c` (Story 29.1); recompiled in place at 0.1.0 on
2026-11-12 (steward Story 29.5, with the EGM audit of 2026-11-05's DOC-R-F2 carried)
from the scope widened with `sources/__main__.py` (the sources dispatcher), the
station contract `contract.md` as a doc source, and the real `doctor --help`, the way
Story 29.1 and atlas Stories 33.1 and 33.2 did.
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

**The public contract** is
`_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/contract.md`
(spec-pyforge-doctor:CAP-97): every verb path and option of `doctor` and of the
sources dispatcher, the MCP tools django-doctor serves, the feature-flag keys (none),
the environment variables, the exit codes and every Source with its check codes. The
MCP tool names and exit codes in this skill are rows of that file; where they differ,
the contract and the code win.

## Quick Start

Run from the repository root via FR-13 grammar (never a hardcoded absolute
path) [SRC:src/pyforge/doctor/__main__.py:L104-L109]:

```bash
pixi run -e pyforge-guild doctor --version
pixi run -e pyforge-guild pyforge doctor check
pixi run -e pyforge-guild pyforge doctor monitor --fleet
pixi run -e pyforge-guild pyforge doctor diagnose --target <feedstock>
pixi run -e pyforge-guild pyforge doctor backlog-intake 13.1
pixi run -e pyforge-guild python -m pyforge.doctor.sources chain-completeness
```

**Check** (`doctor check [path]`) [SRC:src/pyforge/doctor/__main__.py:L110-L207]:
pre-flight engines / env hygiene / opt-in durability / bmad-core /
sibling-dreams; `--scope repo|runtime|all`, `--list` prints the check catalog and
runs nothing. `--json` emits one schema-valid `DoctorReport`.

**Monitor** (`doctor monitor --fleet`) [SRC:src/pyforge/doctor/__main__.py:L213-L261]:
`--fleet` is required. Default `--watch` axes: `staleness,cve` (also `abandonment`,
`adoption`, `behind-upstream`); `--target MAINTAINER` scopes them; `--surface PATH`
also writes the fleet-health surface file.

**Diagnose** (`doctor diagnose --target … [--prescribe]`)
[SRC:src/pyforge/doctor/__main__.py:L264-L291]: gather one feedstock or maintainer
(an existing directory also gets the engines and env checks); `--prescribe`
partitions, ranks and names a root cause; without it, findings are reported but not
partitioned.

**Backlog intake** (`doctor backlog-intake <identifier> [path]`)
[SRC:src/pyforge/doctor/__main__.py:L294-L312] [SRC:src/pyforge/doctor/__main__.py:L922-L936]:
scans every station's tracked `deferred-work-ledger.md`, fleet wide, for entries
naming one epic (`13`) or story (`13.1` or `13-1`, optionally prefixed `Epic ` or
`Story `); the identifier is validated before any scan, and `path` defaults to `.`.

**Flags kill-switch** (`doctor flags kill-switch --flag KEY --reason TEXT
[--flags-path PATH]`) [SRC:src/pyforge/doctor/__main__.py:L314-L338]
[SRC:src/pyforge/doctor/__main__.py:L889-L919]: Doctor's one actuator. It edits the
flag tree itself (`flags.json`, resolved through `django_pyforge.flags` unless
`--flags-path` names it), disables one flag and records the kill-switch metric with
the reason; exit 2 when the tree or the key cannot be found. It writes: run it only on
the operator's ask. It is never part of `check` or `monitor`.

**Sources dispatcher** (`python -m pyforge.doctor.sources <source> [--json]`)
[SRC:src/pyforge/doctor/sources/__main__.py:L200-L212]: runs one ported Source against
the current working directory (no target argument), the way the `*-check` pixi tasks
and `scripts/detectors.py` run it. The sources are the keys of `DISPATCH`
[SRC:src/pyforge/doctor/sources/__main__.py:L90] — `chain-completeness`,
`dream-chain`, `story-status`, `ledger-regression`, `spec-surface`,
`deferred-work`, `bmad-drift`, `writer-lock` and the rest; `--help` lists them all.
Mode flags apply to one source each: `--groundtruth` (`bmad-drift`), `--dreams`
(`dream-chain`), `--layers --project SLUG` (`chain-completeness`), `--base`/`--head`
(`ledger-regression`, `ledger-direction`), `--inv` (`dream-chain`,
`chain-completeness`). A source that measured nothing reports `unmeasured` WARNs and
exits 0.

<!-- [MANUAL:additional-notes] -->
Findings stay advisory. Do not treat a Doctor exit code as a second PR
verdict. Do not replace conda-forge-expert.
<!-- [/MANUAL:additional-notes] -->

## Station MCP runner

What `POST /stations/doctor/mcp` runs, as the code stands (`contract.md` § *MCP
tools*; django-doctor hosts it, and its runner is doctor's row of django-pyforge's
closed verb table; this package serves no MCP itself):

| Tool | Role |
|---|---|
| `start_scan` | Starts a scan job on the supervisor and returns a handle. |
| `get_scan` | Reads a scan job's state and result. |
| `run_scan` | The runner the supervisor calls; not called directly. |

The runner runs one verb: `doctor diagnose --target <target> --json` in
`pyforge-guild`, where the target is one name, and counts exits 0 and 2 as a result
(a `fail` finding is a result, not a crash). It runs nothing else: no `check`,
`monitor`, `backlog-intake`, no `flags kill-switch` and no sources dispatcher.

## Common Workflows

**Pre-flight:** `pyforge doctor check [path] [--json]` → `main` dispatches
`_run_check` [SRC:src/pyforge/doctor/__main__.py:L510] [SRC:src/pyforge/doctor/__main__.py:L708].

**Fleet pulse:** `pyforge doctor monitor --fleet [--watch AXIS[,AXIS…]]`
[SRC:src/pyforge/doctor/__main__.py:L213-L226].

**One target:** `pyforge doctor diagnose --target TARGET [--prescribe]`
[SRC:src/pyforge/doctor/__main__.py:L264-L286].

**Planning detector, one source:** `python -m pyforge.doctor.sources <source> --json`.

**Exit projection:** any `fail` finding → exit `2`; `warn` never changes
the exit code; empty findings → `0` [SRC:src/pyforge/doctor/verdict.py:L4-L10].
That process exit is operability, not a GitHub PR gate.

## Key API Summary

| Function | Purpose | Key params |
|---|---|---|
| `main` | CLI entry (`doctor` console script) | `argv` |
| `exit_code_for` | Project findings to `{0, 2, 130}` | `findings` / `DoctorReport` |
| `DISPATCH` | the sources dispatcher's name → gather table | `source` |

## Key Exports

Public SKF extract of `__main__.py` (Quick mode): `main`
[SRC:src/pyforge/doctor/__main__.py:L510]. Console script:
`doctor = pyforge.doctor.__main__:main` [SRC:pyproject.toml:L46-L47].
Unified grammar is `pyforge doctor …` (FR-13), not a second public
`doctor` binary contract for personas.

## Usage

Always invoke via `pyforge doctor` from repo root. Do not
`from pyforge.doctor import …` in other stations. Personas emit grammar
and `POST /stations/doctor/mcp` only.

Exit codes (`contract.md` § *Exit codes*; `verdict.exit_code_for` is the one
projection, a closed domain `{0, 2, 130}`) [SRC:src/pyforge/doctor/verdict.py:L4-L10]:
`0` no `fail` finding (a `warn` never changes the exit) · `2` at least one `fail`
finding, a usage error or a refused actuator · `130` interrupted. Doctor never exits
`1`: that is warden's policy rung. The aggregate `{0, 1, 2}` of
`scripts/detectors.py` is not Doctor's.

## Key Types

**`Finding`** [SRC:src/pyforge/doctor/models.py:L424-L435] — `source`,
`check`, `status`, `message`, `evidence`. Advisory signal, not a PR
verdict.

**`DoctorReport`** — schema-validated envelope of findings (+ optional
prescriptions).

## Architecture at a Glance

- **CLI** — sole public contract [SRC:src/pyforge/doctor/__main__.py:L1-L33].
- **Verdict** — sole owner of exit-code projection; operability not policy
  [SRC:src/pyforge/doctor/verdict.py:L1-L16].
- **Sources** — one `gather(target)` per Source; the dispatcher runs one at a time
  [SRC:src/pyforge/doctor/sources/__main__.py:L1-L20].
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
doctor flags kill-switch --flag KEY --reason TEXT [--flags-path PATH]
python -m pyforge.doctor.sources <source> [--json] [--groundtruth] [--dreams]
             [--layers --project SLUG] [--base REV] [--head REV] [--inv INV...]
```

`--version` is top-level only [SRC:src/pyforge/doctor/__main__.py:L208-L211].

<!-- [MANUAL:api-notes] -->
Do not implement the Wave B portal pulse in this skill. Do not add
`pyforge.*` under `src/platform/`.
<!-- [/MANUAL:api-notes] -->
