---
name: pyforge-atlas
description: >
  Kedro/Dagster/DuckDB factory intelligence for conda-forge (pyforge.atlas).
  Use when running atlas pipelines, listing catalog datasets, or reading
  the station MCP surface. Invoke via `pyforge atlas …` (canopy:FR-13) — do not
  import pyforge.atlas internals. Do not use for conda-forge recipe
  authoring (conda-forge-expert) or the legacy orchestrator skill
  (cf-atlas-legacy). Do not use for station personas (bmad-agent-atlas).
---

# pyforge-atlas

## Overview

Compiles `src/shared/packages/pyforge-atlas/` (PyPI `pyforge-atlas` 0.1.0) as an
agentskills.io content skill for the **atlas** station. Source: local path
`src/shared/packages/pyforge-atlas` @ commit `5f22584869` (`source_ref: local`).
Forge tier: **Forge** (SKF `skf-extract-public-api` over ast-grep 0.45.3; T1 where a
recipe matched, T1-low where an export was read by eye).
Public CLI export documented (`main`). Package `__init__.py` pins pandas
`future.infer_string` and exports `__version__` only
[SRC:src/pyforge/atlas/__init__.py:L34]. First compiled from `865b95dc951c`; the
source line citations and `provenance-map.json`'s `source_line`s were re-pointed
by hand on 2026-10-18 (atlas Story 33.1) against that story's landing tree, and the
`mcp/tools.py` ones again on 2026-10-25 (atlas Story 33.2). Recompiled in place at
0.1.0 on 2026-11-01 (steward Story 29.4) from the widened scope (`mcp/server.py`,
where the MCP tools register) and the real `pyforge atlas --help`, the same way, and
again on 2026-11-12 (steward Story 29.5, the fix the EGM audit of 2026-11-05 accepted:
ATL-R-F1) with `provenance.py` in scope and the station contract `contract.md` as a
doc source; every line citation is re-pointed against that tree.
Rebuilt as 0.1.1 on 2026-11-25 (steward Story 136.10) with `skf-update-skill` at Forge
tier over ast-grep 0.45.3, at `5f22584869`: the first Forge-tier build, over the whole
scope the brief names, with the requirement and capability ids cited in qualified form.
30 exports documented: 15 the extract matched (`main` and `discover_cli_verbs` in
`__main__.py`, `build_server` in `mcp/server.py`, the six `mcp/tools.py` functions and
`AtlasMCPError`, and `provenance.py`'s `ProvenanceInfo` with its four functions) and 15
read by eye (the thirteen MCP tools, which are nested in `build_server`, `PIPELINE_NAMES`
and `__version__`); § *Full API Reference* and § *Full Type Definitions* list them.
This skill is **not** `cf-atlas-legacy`
and does **not** replace `conda-forge-expert`.

## Description

Kedro/Dagster/DuckDB data-pipeline migration of the `cf_atlas` orchestrator —
the `pyforge.atlas` namespace package beside `pyforge.warden`
[SRC:pyproject.toml:L8]. Atlas **provides data**; Warden uses it. Agents act
through canopy:FR-13 grammar (`pyforge atlas …`) and canopy:FR-11 MCP
(`POST /stations/atlas/mcp`).

**The public contract** is
`_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/contract.md`
(spec-pyforge-atlas:CAP-73): every CLI verb and option, every MCP tool, every
feature-flag key with its default per environment, every environment variable, every
exit code and what the package reads outside itself. The MCP tool names, exit codes
and flag keys in this skill are rows of that file; where they differ, the contract
and the code win.

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
[SRC:pyproject.toml:L85]. `--version` is intercepted before Kedro import
and prints `pyforge-atlas <version>` [SRC:src/pyforge/atlas/__main__.py:L129-L131].
Any other argv goes to Kedro's project command group (`run`, `ipython`,
`package`) after `bootstrap_project(PROJECT_ROOT)`; each command runs with the
atlas member dir as its cwd, the root the MCP face uses, and the caller's cwd
comes back afterwards [SRC:src/pyforge/atlas/__main__.py:L145-L170], so a
relative path passed to `run` resolves against the member dir: pass absolute
paths [SRC:README.md:L32-L36]. A bare `pyforge atlas` lists the commands and
runs nothing.

<!-- [MANUAL:additional-notes] -->
<!-- spec-pyforge-unifying-strategy:CAP-15: personas consult this skill; they must not freelance the filesystem. -->
**Freshness** (EGM audit 2026-11-05 ATL-R-F1): `read_atlas_dataset` returns each dataset with its build-provenance
envelope. Read how fresh the data is from the envelope's `build_stamp` (and `build_stamp_newest`), never from the read
time; atlas reports the timestamps and computes no staleness verdict for you.
**Credentialed fetches:** `PYFORGE_ATLAS_CREDENTIALED=1` is the operator's per-run opt-in for a fetch that carries a
credential; an agent never sets it. Without it those datasets keep their uncredentialed path and can stay stale.
<!-- [/MANUAL:additional-notes] -->


<!-- [MANUAL:station-mcp] -->
Station host: atlas's MCP face is `POST /stations/atlas/mcp` on the platform host. How to start the host, get the
assertion it accepts and send a request: `docs/how-to/reach-a-station-mcp-endpoint.md`.
<!-- [/MANUAL:station-mcp] -->


## Station MCP runner

What `POST /stations/atlas/mcp` runs, as the code stands (`contract.md` § *MCP tools*
and § *The HTTP face*; django-atlas hosts it around this package's `build_server()`):
the thirteen MCP tools (§ *Common Workflows*), plus two supervisor tools, `start_run_pipeline` (takes a
pipeline `name` and an `assertion`, returns a handle at once) and `get_run` (reads that
run). The supervisor runner behind `start_run_pipeline` is `run_pipeline`, not an MCP
tool: it runs one of the eight `PIPELINE_NAMES` through `KedroSession.run`, the same
plane as `pyforge atlas run`. Every `run_*` tool refuses while the kill switch
`pyforge.atlas.agent_pipeline_tools` is off, and `universal_sbom` while
`pyforge.atlas.manifest_inventory` is off; an unknown name raises `AtlasMCPError`.
Nothing else is reachable through the face: not the four CLI-only pipelines, not
`ipython` or `package`, and none of the `tools/` scripts or the query plane's
`duckdb-server`.

## Common Workflows

**Version check:** `main(["--version"])` [AST:src/pyforge/atlas/__main__.py:L92]
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
[AST:src/pyforge/atlas/mcp/server.py:L49-L145]: `run_core_pipeline`,
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

Public SKF extract over the brief's scope (Forge tier, ast-grep): `main`
[AST:src/pyforge/atlas/__main__.py:L92] and `discover_cli_verbs`, `build_server`, the
`mcp/tools.py` functions and `provenance.py` (§ *Full API Reference*). Console script:
`pyforge-atlas = pyforge.atlas.__main__:main` [SRC:pyproject.toml:L85].
The thirteen MCP tools register in `build_server` [AST:src/pyforge/atlas/mcp/server.py:L49];
the package re-exports the `mcp/tools.py` functions they delegate to
[SRC:src/pyforge/atlas/mcp/__init__.py:L31-L50].

## Usage

Always invoke via `pyforge atlas …` from repo root. Do not
`from pyforge.atlas import …` in other stations for station work. Do not
point agents at `cf-atlas-legacy` for this package. Do not author recipes
here — that remains `conda-forge-expert`.

Exit codes (`contract.md` § *Exit codes*; the frozen domain is spec-pyforge-atlas:CAP-13):
`pyforge atlas` exits `0` on success and `--version`, `2` on a kill-switch refusal
before Kedro runs, and otherwise Click's own codes (`1` a failed or aborted command,
`2` usage). The station's gate domain is `0` pass, `1` policy fail (an indeterminate
result maps to `1`), `2` error, `130` interrupted.

## Key Types

**`AtlasMCPError`** [AST:src/pyforge/atlas/mcp/tools.py:L111-L115] — invalid
MCP-surface request (unknown pipeline).

**`PIPELINE_NAMES`** [SRC:src/pyforge/atlas/mcp/tools.py:L99-L108] — static
mirror of the eight MCP-triggerable pipelines (`core`, `vcs_health`, `pypi_intelligence`, `vulnerability`,
`seed_gaps`, `universal_sbom`, `derived_artifacts`, `upstream_discovery`).

## Architecture at a Glance

- **CLI** — `main` intercepts `--version`, then Kedro's project command group
  [AST:src/pyforge/atlas/__main__.py:L92-L170].
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

## Full API Reference

The 13 functions the extract found and the 13 MCP tools read by eye, as the source
declares them, for reading the code. Other stations, personas and `src/platform/` do not
import them: `pyforge atlas …` and the station MCP face are the contract (§ *Usage*).

### `__main__.py`

- `discover_cli_verbs() -> frozenset[str]` — Return Kedro project command names for
  `pyforge.atlas` at runtime. [AST:src/pyforge/atlas/__main__.py:L18]
- `main(*args, **kwargs) -> Any` — the console script's entry; the source gives it no
  docstring. [AST:src/pyforge/atlas/__main__.py:L92]

### `mcp/server.py`

- `build_server(name: str = "pyforge-atlas-atlas")` — Build the official MCP server
  exposing the thin B3 surface. [AST:src/pyforge/atlas/mcp/server.py:L49]

The thirteen MCP tools are functions nested in `build_server`, each registered with
`@mcp.tool()` and read by eye:

- `run_core_pipeline() -> dict` [SRC:src/pyforge/atlas/mcp/server.py:L56]
- `run_vcs_health_pipeline() -> dict` [SRC:src/pyforge/atlas/mcp/server.py:L61]
- `run_pypi_intelligence_pipeline() -> dict` [SRC:src/pyforge/atlas/mcp/server.py:L66]
- `run_vulnerability_pipeline() -> dict` [SRC:src/pyforge/atlas/mcp/server.py:L71]
- `run_seed_gaps_pipeline() -> dict` [SRC:src/pyforge/atlas/mcp/server.py:L76]
- `run_universal_sbom_pipeline() -> dict` [SRC:src/pyforge/atlas/mcp/server.py:L81]
- `run_derived_artifacts_pipeline() -> dict` [SRC:src/pyforge/atlas/mcp/server.py:L86]
- `run_upstream_discovery_pipeline() -> dict` [SRC:src/pyforge/atlas/mcp/server.py:L91]
- `read_atlas_dataset(name: str)` — Read a catalog dataset, stamped with its own build
  provenance (AD-17). [SRC:src/pyforge/atlas/mcp/server.py:L96]
- `list_atlas_pipelines() -> list[str]` [SRC:src/pyforge/atlas/mcp/server.py:L106]
- `list_atlas_datasets() -> list[str]` [SRC:src/pyforge/atlas/mcp/server.py:L111]
- `query_vizro_ai(query: str) -> dict` [SRC:src/pyforge/atlas/mcp/server.py:L116]
- `query_trending_candidates(period: str = "weekly", tier: str = "1,2", top: int = 25,
  not_on_cf: bool = True, min_stars: int = 500) -> dict`
  [SRC:src/pyforge/atlas/mcp/server.py:L124]

### `mcp/tools.py`

- `run_pipeline(name: str, *, project_path: Path | str | None = None, extra_params:
  dict[str, Any] | None = None, env: str | None = None) -> dict[str, Any]` — Trigger the
  named MCP-triggerable pipeline (one of `PIPELINE_NAMES`) through the ONE execution plane
  (AD-23): `KedroSession.run(pipeline_name=...)`. [AST:src/pyforge/atlas/mcp/tools.py:L128]
- `read_dataset(name: str, *, project_path: Path | str | None = None, env: str | None =
  None) -> dict[str, Any]` — `catalog.load(<name>)` + a JSON-serializable coercion,
  wrapped in a build-provenance envelope (AD-7, AD-17).
  [AST:src/pyforge/atlas/mcp/tools.py:L155]
- `query_vizro_ai(query: str, *, env: Mapping[str, str] | None = None) -> dict[str, Any]`
  — Natural-language -> Vizro chart/insight over the BSL knowledge graph (D3, FR-9).
  [AST:src/pyforge/atlas/mcp/tools.py:L218]
- `query_trending_candidates(period: str = "weekly", tier: str = "1,2", top: int = 25,
  not_on_cf: bool = True, min_stars: int = 500, *, project_path: Path | str | None = None,
  env: str | None = None) -> dict[str, Any]` — thin delegation to the
  `trending_candidates` seam (AD-7). [AST:src/pyforge/atlas/mcp/tools.py:L231]
- `list_pipelines(*, project_path: Path | str | None = None, env: str | None = None) ->
  list[str]` — The MCP-triggerable pipeline names, served from the static mirror
  (`PIPELINE_NAMES`). [AST:src/pyforge/atlas/mcp/tools.py:L257]
- `list_datasets(*, project_path: Path | str | None = None, env: str | None = None) ->
  list[str]` — The declared catalog dataset names.
  [AST:src/pyforge/atlas/mcp/tools.py:L268]

### `provenance.py`

- `resolve_for_file(path: str | os.PathLike[str]) -> ProvenanceInfo` — `file-mtime`
  provenance: the materialized file's own mtime, or `unavailable` when the file does not
  (yet) exist. [AST:src/pyforge/atlas/provenance.py:L94]
- `resolve_for_snapshot_history(path: str | os.PathLike[str], column: str =
  "snapshot_at") -> ProvenanceInfo` — `snapshot-at` provenance for a
  `SnapshotHistoryDataset`: the latest snapshot's own recorded time, never the store
  file's mtime. [AST:src/pyforge/atlas/provenance.py:L140]
- `resolve_for_catalog_dataset(catalog: Any, name: str, loaded_value: Any) ->
  ProvenanceInfo` — Dispatch on `catalog[name]`'s actual TYPE to derive `loaded_value`'s
  genuine provenance. [AST:src/pyforge/atlas/provenance.py:L253]
- `load_with_provenance(catalog: Any, name: str) -> tuple[Any, ProvenanceInfo]` — Load
  `name` from `catalog` AND resolve its provenance in ONE function.
  [AST:src/pyforge/atlas/provenance.py:L326]

## Full Type Definitions

- `class AtlasMCPError(PyforgeError, RuntimeError)` — Raised for invalid MCP-surface
  requests (e.g. an unknown pipeline). [AST:src/pyforge/atlas/mcp/tools.py:L111]
- `class ProvenanceInfo` — The provenance verdict for one dataset read: a KIND +
  timestamp(s), or an honest `unavailable` + reason; never a computed staleness verdict.
  Fields: `kind: str`, `build_stamp: str | None`, `build_stamp_newest: str | None =
  None`, `reason: str | None = None`. [AST:src/pyforge/atlas/provenance.py:L63]
- `PIPELINE_NAMES` — the tuple of the eight MCP-triggerable pipeline names (§ *Key
  Types*), read by eye. [SRC:src/pyforge/atlas/mcp/tools.py:L99]
- `__version__ = "0.1.0"`, read by eye. [SRC:src/pyforge/atlas/__init__.py:L34]
