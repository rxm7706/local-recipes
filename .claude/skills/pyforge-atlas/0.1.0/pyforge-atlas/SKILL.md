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
`src/shared/packages/pyforge-atlas` @ commit `03a7aff5d9` (`source_ref: local`).
Forge tier: **Quick** (SKF `skf-extract-public-api` + source-reading; T1-low).
Public CLI export documented (`main`). Package `__init__.py` pins pandas
`future.infer_string` and exports `__version__` only
[SRC:src/pyforge/atlas/__init__.py:L34]. First compiled from `865b95dc951c`; the
`[SRC:…]` line citations and `provenance-map.json`'s `source_line`s were re-pointed
by hand on 2026-10-18 (atlas Story 33.1) against that story's landing tree, and the
`mcp/tools.py` ones again on 2026-10-25 (atlas Story 33.2). Recompiled in place at
0.1.0 on 2026-11-01 (steward Story 29.4) from the widened scope (`mcp/server.py`,
where the MCP tools register) and the real `pyforge atlas --help`, the same way;
every line citation is re-pointed against that tree.
This skill is **not** `cf-atlas-legacy`
and does **not** replace `conda-forge-expert`.

## Description

Kedro/Dagster/DuckDB data-pipeline migration of the `cf_atlas` orchestrator —
the `pyforge.atlas` namespace package beside `pyforge.warden`
[SRC:pyproject.toml:L8]. Atlas **provides data**; Warden uses it. Agents act
through FR-13 grammar (`pyforge atlas …`) and FR-11 MCP
(`POST /stations/atlas/mcp`).

## Quick Start

Run from the repository root (never a hardcoded absolute path), in atlas's own
environment, `-e pyforge-atlas` (the session default `pyforge-guild` does not
carry atlas) [SRC:README.md:L24-L45]:

```bash
pixi run -e pyforge-atlas pyforge atlas --version
pixi run -e pyforge-atlas pyforge atlas run --pipelines core
pixi run -e pyforge-atlas pyforge atlas run --pipelines core,vcs_health
```

`pyforge atlas …` is unified dispatch onto the `pyforge-atlas` console script
[SRC:pyproject.toml:L96]. `--version` is intercepted before Kedro import
and prints `pyforge-atlas <version>` [SRC:src/pyforge/atlas/__main__.py:L129-L131].
Any other argv goes to Kedro's project command group (`run`, `ipython`,
`package`) after `bootstrap_project(PROJECT_ROOT)`; each command runs with the
atlas member dir as its cwd, the root the MCP face uses, and the caller's cwd
comes back afterwards [SRC:src/pyforge/atlas/__main__.py:L145-L170], so a
relative path passed to `run` resolves against the member dir: pass absolute
paths [SRC:README.md:L32-L36]. A bare `pyforge atlas` lists the commands and
runs nothing.

<!-- [MANUAL:additional-notes] -->
<!-- CAP-15: personas consult this skill; they must not freelance the filesystem. -->
<!-- [/MANUAL:additional-notes] -->

<!-- [MANUAL:station-mcp] -->
Station host: atlas's MCP face is `POST /stations/atlas/mcp` on the platform host. How to start the host, get the
assertion it accepts and send a request: `docs/how-to/reach-a-station-mcp-endpoint.md`.
<!-- [/MANUAL:station-mcp] -->

## Common Workflows

**Version check:** `main(["--version"])` [SRC:src/pyforge/atlas/__main__.py:L92]
prints one line and returns without loading Kedro.

**Pipeline run (CLI):** `pyforge atlas run --pipelines <name>[,<name>…]` —
same execution plane as the MCP trigger tools (AD-23). The MCP face registers one
`run_<pipeline>_pipeline` tool for each name in `PIPELINE_NAMES`
[SRC:src/pyforge/atlas/mcp/server.py:L55-L93]
[SRC:src/pyforge/atlas/mcp/tools.py:L99-L108]; the CLI accepts every registered
Kedro pipeline. Kedro 1.6 deprecates the singular `--pipeline`. With the kill
switch `pyforge.atlas.agent_pipeline_tools` off, `run` stays listed, marked
disabled, and refuses with exit 2 [SRC:src/pyforge/atlas/__main__.py:L136-L143].

**Catalog list:** no CLI verb — use the MCP tool `list_atlas_datasets`
[SRC:src/pyforge/atlas/mcp/server.py:L110-L113].

**MCP read/trigger:** the tools `mcp/server.py` registers
[SRC:src/pyforge/atlas/mcp/server.py:L49-L145]: `run_core_pipeline`,
`run_vcs_health_pipeline`, `run_pypi_intelligence_pipeline`,
`run_vulnerability_pipeline`, `run_seed_gaps_pipeline`,
`run_universal_sbom_pipeline`, `run_derived_artifacts_pipeline`,
`run_upstream_discovery_pipeline`, `read_atlas_dataset`,
`list_atlas_pipelines`, `list_atlas_datasets`, `query_vizro_ai` and
`query_trending_candidates`. Each delegates 1:1 to a `mcp/tools.py` function
(`run_pipeline`, `read_dataset`, `list_pipelines`, `list_datasets`, …), which
is the implementation, not the tool name (AD-7)
[SRC:src/pyforge/atlas/mcp/server.py:L1-L10]. Host face is
`POST /stations/atlas/mcp`, not ad-hoc HTTP.

## Key API Summary

| Function | Purpose | Key params |
|---|---|---|
| `main` | Kedro CLI entry (`pyforge-atlas` / `python -m pyforge.atlas`) | argv / `--version` |
| `run_<pipeline>_pipeline` | MCP: trigger one of the eight MCP-triggerable pipelines via KedroSession (`run_core_pipeline` … `run_upstream_discovery_pipeline`) | — |
| `read_atlas_dataset` | MCP: load one catalog dataset with its build-provenance envelope | `name` |
| `list_atlas_pipelines` | MCP: the eight MCP-triggerable pipeline names (the other four are CLI-only) | — |
| `list_atlas_datasets` | MCP: the declared catalog dataset names | — |
| `query_vizro_ai` | MCP: NL query over the BSL knowledge graph | `query` |
| `query_trending_candidates` | MCP: read the classified trending list | `period`, `tier`, `top`, `not_on_cf`, `min_stars` |

## Key Exports

Public SKF extract of `__main__.py` (Quick mode): `main`
[SRC:src/pyforge/atlas/__main__.py:L92]. Console script:
`pyforge-atlas = pyforge.atlas.__main__:main` [SRC:pyproject.toml:L96].
The MCP tools register in `build_server` [SRC:src/pyforge/atlas/mcp/server.py:L49];
the package re-exports the `mcp/tools.py` functions they delegate to
[SRC:src/pyforge/atlas/mcp/__init__.py:L31-L50].

## Usage

Always invoke via `pyforge atlas …` from repo root. Do not
`from pyforge.atlas import …` in other stations for station work. Do not
point agents at `cf-atlas-legacy` for this package. Do not author recipes
here — that remains `conda-forge-expert`.

## Key Types

**`AtlasMCPError`** [SRC:src/pyforge/atlas/mcp/tools.py:L111-L115] — invalid
MCP-surface request (unknown pipeline).

**`PIPELINE_NAMES`** [SRC:src/pyforge/atlas/mcp/tools.py:L99-L108] — static
mirror of the eight MCP-triggerable pipelines (`core`, `vcs_health`, `pypi_intelligence`, `vulnerability`,
`seed_gaps`, `universal_sbom`, `derived_artifacts`, `upstream_discovery`).

## Architecture at a Glance

- **CLI** — `main` intercepts `--version`, then Kedro's project command group
  [SRC:src/pyforge/atlas/__main__.py:L92-L170].
- **MCP** — thin tools over Kedro session/catalog; not `kedro-mcp`
  [SRC:src/pyforge/atlas/mcp/__init__.py:L1-L21]; registered by the official
  `mcp` SDK, imported lazily in `build_server` [SRC:src/pyforge/atlas/mcp/server.py:L1-L10].
- **Pipelines** — Kedro packages under `pipelines/`; Vizro stays off the host
  portal (story 19.2 / DW-H3 are out of this skill's compile).

## CLI

```text
pyforge atlas --version
pyforge atlas run --pipelines <name>[,<name>…]
pyforge atlas run
pyforge-atlas ipython          # the binary directly: the pyforge front door has no stdin
pyforge atlas package
```

`run` with no `--pipelines` runs the whole `__default__` DAG. Unknown pipelines
on the MCP trigger raise `AtlasMCPError`
[SRC:src/pyforge/atlas/mcp/tools.py:L141-L142].

<!-- [MANUAL:api-notes] -->
<!-- Add custom notes here. This section is preserved during skill updates. -->
<!-- [/MANUAL:api-notes] -->
