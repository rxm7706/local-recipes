---
name: pyforge-atlas
description: >
  Kedro/Dagster/DuckDB factory intelligence for conda-forge (pyforge.atlas).
  Use when running atlas pipelines, listing catalog datasets, or reading
  the station MCP surface. Invoke via `pyforge atlas …` (FR-13) — do not
  import pyforge.atlas internals. Do not use for conda-forge recipe
  authoring (conda-forge-expert) or the legacy orchestrator skill
  (cf-atlas-legacy). Do not use for station personas (bmad-agent-atlas).
---

# pyforge-atlas

## Overview

Compiles `src/shared/packages/pyforge-atlas/` (PyPI `pyforge-atlas` 0.1.0) as an
agentskills.io content skill for the **atlas** station. Source: local path
`src/shared/packages/pyforge-atlas` @ commit `865b95dc951c` (`source_ref: local`).
Forge tier: **Quick** (SKF `skf-extract-public-api` + source-reading; T1-low).
Public CLI export documented (`main`). Package `__init__.py` pins pandas
`future.infer_string` and exports `__version__` only
[SRC:src/pyforge/atlas/__init__.py:L34]. This skill is **not** `cf-atlas-legacy`
and does **not** replace `conda-forge-expert`.

## Description

Kedro/Dagster/DuckDB data-pipeline migration of the `cf_atlas` orchestrator —
the `pyforge.atlas` namespace package beside `pyforge.warden`
[SRC:pyproject.toml:L8]. Atlas **provides data**; Warden uses it. Agents act
through FR-13 grammar (`pyforge atlas …`) and FR-11 MCP
(`POST /stations/atlas/mcp`).

## Quick Start

Run from the repository root (never a hardcoded absolute path)
[SRC:README.md:L21]:

```bash
pyforge atlas --version
pyforge atlas run --pipeline core
pyforge atlas catalog list
```

`pyforge atlas …` is unified dispatch onto the `pyforge-atlas` console script
[SRC:pyproject.toml:L87-L88]. `--version` is intercepted before Kedro import
and prints `pyforge-atlas <version>` [SRC:src/pyforge/atlas/__main__.py:L47-L49].
Any other argv is forwarded to Kedro `find_run_command` after
`configure_project("pyforge.atlas")` [SRC:src/pyforge/atlas/__main__.py:L51-L64].

<!-- [MANUAL:additional-notes] -->
<!-- CAP-15: personas consult this skill; they must not freelance the filesystem. -->
<!-- [/MANUAL:additional-notes] -->

## Common Workflows

**Version check:** `main(["--version"])` [SRC:src/pyforge/atlas/__main__.py:L10]
prints one line and returns without loading Kedro.

**Pipeline run (CLI):** `pyforge atlas run --pipeline <name>` — same execution
plane as MCP `run_pipeline` (AD-23). Registered names live in `PIPELINE_NAMES`
[SRC:src/pyforge/atlas/mcp/tools.py:L38-L47].

**Catalog list (CLI):** `pyforge atlas catalog list` — Kedro catalog keys.

**MCP read/trigger:** `run_pipeline`, `read_dataset`, `list_pipelines`,
`list_datasets` [SRC:src/pyforge/atlas/mcp/tools.py:L57-L201]. Host face is
`POST /stations/atlas/mcp`, not ad-hoc HTTP.

## Key API Summary

| Function | Purpose | Key params |
|---|---|---|
| `main` | Kedro CLI entry (`pyforge-atlas` / `python -m pyforge.atlas`) | argv / `--version` |
| `run_pipeline` | Trigger one registered pipeline via KedroSession | `name` |
| `read_dataset` | Load one catalog dataset with provenance envelope | dataset name |
| `list_pipelines` | Offline registry mirror of pipeline names | — |
| `list_datasets` | Catalog keys from a bootstrapped session | — |
| `query_vizro_ai` | NL field over BSL (MCP) | `query` |
| `query_trending_candidates` | Read classified trending list (MCP) | filters |

## Key Exports

Public SKF extract of `__main__.py` (Quick mode): `main`
[SRC:src/pyforge/atlas/__main__.py:L10]. Console script:
`pyforge-atlas = pyforge.atlas.__main__:main` [SRC:pyproject.toml:L87-L88].
MCP surface re-exports from `mcp/tools.py` [SRC:src/pyforge/atlas/mcp/__init__.py:L31-L50].

## Usage

Always invoke via `pyforge atlas …` from repo root. Do not
`from pyforge.atlas import …` in other stations for station work. Do not
point agents at `cf-atlas-legacy` for this package. Do not author recipes
here — that remains `conda-forge-expert`.

## Key Types

**`AtlasMCPError`** [SRC:src/pyforge/atlas/mcp/tools.py:L50-L54] — invalid
MCP-surface request (unknown pipeline).

**`PIPELINE_NAMES`** [SRC:src/pyforge/atlas/mcp/tools.py:L38-L47] — static
registry mirror (`core`, `vcs_health`, `pypi_intelligence`, `vulnerability`,
`seed_gaps`, `universal_sbom`, `derived_artifacts`, `upstream_discovery`).

## Architecture at a Glance

- **CLI** — `main` intercepts `--version`, then Kedro project CLI
  [SRC:src/pyforge/atlas/__main__.py:L10-L64].
- **MCP** — thin tools over Kedro session/catalog; not `kedro-mcp`
  [SRC:src/pyforge/atlas/mcp/__init__.py:L1-L21].
- **Pipelines** — Kedro packages under `pipelines/`; Vizro stays off the host
  portal (story 19.2 / DW-H3 are out of this skill's compile).

## CLI

```text
pyforge atlas --version
pyforge atlas run --pipeline <name>
pyforge atlas catalog list
```

Unknown pipelines on the MCP trigger raise `AtlasMCPError`
[SRC:src/pyforge/atlas/mcp/tools.py:L70-L71].

<!-- [MANUAL:api-notes] -->
<!-- Add custom notes here. This section is preserved during skill updates. -->
<!-- [/MANUAL:api-notes] -->
