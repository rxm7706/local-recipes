---
name: pyforge-scribe
description: >
  Captures team-memory decisions into .claude/memory, compiles the scribe
  knowledge graph (optionally through the graphify compile_surface extra),
  and recalls cited answers via the scribe CLI. Use when writing or
  retrieving team memory, running scribe capture / graph compile / recall /
  index, or working in src/shared/packages/pyforge-scribe/. Do not import
  pyforge.scribe internals (including pyforge.scribe.extras.graphify); the
  CLI is the public contract. Do not use for conda-forge recipe authoring
  (conda-forge-expert) or station personas.
---

# pyforge-scribe

## Overview

Compiles `src/shared/packages/pyforge-scribe/` (PyPI `pyforge-scribe` 0.1.0) as an
agentskills.io content skill for the **scribe** station. Source: local path
`src/shared/packages/pyforge-scribe` @ commit `a5e9dad59ab` (`source_ref: local`).
Forge tier: **Quick** (SKF `skf-extract-public-api` + source-reading; T1-low).
6 CLI exports documented (`capture_cmd`, `graph_compile`, `recall_cmd`,
`index_report`, `index_move_list`, `main`).
The package `__init__.py` exports only `__version__` — other components integrate
via the CLI, never by importing internal modules [SRC:src/pyforge/scribe/__init__.py:L9-L14].

## Description

Direct-capture CLI for checked-in team memory (`.claude/memory/`) — append-only
write path for team-relevant decisions, ADRs, and project state
[SRC:pyproject.toml:L8].

## Quick Start

Run from the repository root (never a hardcoded absolute path)
[SRC:src/pyforge/scribe/cli.py:L44-L47]:

```bash
pixi run -e pyforge-scribe scribe capture --type project --text "..."
pixi run -e pyforge-scribe scribe graph compile
pixi run -e pyforge-scribe scribe recall "why did we pin typer"
```

**Capture** (`scribe capture`) [SRC:src/pyforge/scribe/cli.py:L73-L139]:
`--type` is `feedback` | `project` | `reference` and `--text` is required unless
`--promote` or `--transcripts` is set. Writes under `.claude/memory/<type>/` and
prints `captured: <path>`.

**Compile** (`scribe graph compile [--nightly] [--extra/--no-extra]`)
[SRC:src/pyforge/scribe/cli.py:L271-L293]: full rebuild of the graph; never
prompts. `--extra`/`--no-extra` overrides the graphify compile_surface extra
(Story 6.1) for this run; omitted, it consults `SCRIBE_GRAPHIFY_EXTRA` (off
by default, air-gap).

**Recall** (`scribe recall <query>`) [SRC:src/pyforge/scribe/cli.py:L368-L381]:
prints the answer plus `[source: …]` when grounded, else `no grounded answer found`.

**Index** (`scribe index report [--path PATH]` / `scribe index move-list`)
[SRC:src/pyforge/scribe/cli.py:L321-L367]: the graphify extra's report
verbs (Story 6.1). `report` writes a GRAPH_REPORT-style summary (node/edge
counts + god-node findings) to
`.claude/data/pyforge-scribe/graphify/GRAPH_REPORT.md`; `move-list` writes
the foundry-cutover move list (host `import pyforge.*` sites, `sys.path`
inserts, `five_tier` roots, CFE callers) to
`.claude/data/pyforge-scribe/graphify/move-list.json`. Both are derived,
gitignored artifacts — like `graph.json` — never a foundry-root
`graphify-out/`. Invoking `scribe index …` IS the opt-in: unlike
`graph compile`'s automatic fan-in, these verbs do not consult
`SCRIBE_GRAPHIFY_EXTRA`. `report` requires the optional
`pyforge-scribe[graphify]` dependency (`graphifyy`) installed; `move-list`
is a pure text scan and needs nothing extra.

<!-- [MANUAL:additional-notes] -->
<!-- Add custom notes here. This section is preserved during skill updates. -->
<!-- [/MANUAL:additional-notes] -->

## Common Workflows

**Direct capture:** `capture_cmd` → `capture(memory_root, capture_type, text)`
[SRC:src/pyforge/scribe/capture.py:L54] → index line on `MEMORY.md`.

**Promote user-local memory:** `scribe capture --promote` → `classify_and_draft`
then `typer.confirm` then `apply_promotion` [SRC:src/pyforge/scribe/cli.py:L142-L169].
Zero writes before confirm.

**Transcript harvest:** `scribe capture --transcripts` → `scan_transcripts` then
confirm then `capture()` per candidate [SRC:src/pyforge/scribe/cli.py:L195-L230].
Does not mutate transcript files.

**Rebuild then query:** `compile_graph(...)` [SRC:src/pyforge/scribe/compile.py:L99]
then `open_graph_store` [SRC:src/pyforge/scribe/graph_store_plugins.py:L27] then
`answer(query, store, repo_root=...)` [SRC:src/pyforge/scribe/recall.py:L71].

## Key API Summary

| Function | Purpose | Key params |
|---|---|---|
| `main` | Typer entry (`scribe` console script) | — |
| `capture_cmd` | CLI capture / promote / transcripts | `--type`, `--text`, `--promote`, `--transcripts` |
| `graph_compile` | Rebuild compiled graph | `--nightly`, `--extra`/`--no-extra` |
| `recall_cmd` | Cited recall over compiled graph | `query` |
| `index_report` | CLI: graphify GRAPH_REPORT-style summary | `--path` |
| `index_move_list` | CLI: foundry-cutover move list | — |
| `capture` | Append-only write under memory_root | `memory_root`, `capture_type`, `text` |
| `compile_graph` | Full graph rebuild via GraphStore port + optional graphify surface | `memory_root`, `repo_root`, `nightly`, `graphify_extra`, `graphify_root` |
| `answer` | Lexical (default) or semantic recall | `query`, `store`, `repo_root`, `mode` |
| `open_graph_store` | Factory; default flat-file plugin | `store_path` |
| `graphify_extra_enabled` | Off-by-default gate (SCRIBE_GRAPHIFY_EXTRA) | `override` |
| `ingest_graphify_surface` | AST code-structure nodes (kind="code") | `scan_root`, `repo_root`, `cache_dir` |
| `build_graphify_report` | GRAPH_REPORT-style summary + god nodes | `scan_root`, `repo_root`, `cache_dir`, `top_n` |
| `scan_move_list` | Foundry-cutover move-list findings | `repo_root` |

## Key Exports

Public SKF extract of `cli.py` (Quick mode): `capture_cmd`, `graph_compile`,
`recall_cmd`, `index_report`, `index_move_list`, `main`
[SRC:src/pyforge/scribe/cli.py]. Console script:
`scribe = pyforge.scribe.cli:main` [SRC:pyproject.toml:L25-L26].

## Usage

Always invoke `scribe` from repo root. Do not `from pyforge.scribe import capture`
in other stations. Graph engine is selected via `pyforge.core.hooks` plugins
(`scribe-graphstore-flatfile`, `scribe-graphstore-pg`) — callers use
`open_graph_store`, not a driver client [SRC:src/pyforge/scribe/graph_store_plugins.py:L1-L8].

The graphify `compile_surface` extra (Story 6.1) is off by default (air-gap)
and consumers bind to this declared `scribe index …` grammar, not to
`pyforge.scribe.extras.graphify` internals — this is the grammar the
marshal Story 28.9 planning-corpus consumer (still `status:
ready-for-dev`, unimplemented as of this story) and the foundry-cutover
move-list are meant to bind to
[SRC:src/pyforge/scribe/extras/graphify.py:L1-L40]. `graphify`
(conda-forge `graphifyy`, PyPI extra `pyforge-scribe[graphify]`) is imported
ONLY inside that one module, and only inside a function — a lean
`pyforge-scribe` install (the package is not a hard pixi run-dep of that
environment) works unmodified without it.

## Key Types

**`CaptureType`** [SRC:src/pyforge/scribe/models.py:L34-L37] — `feedback` |
`project` | `reference` (`CAPTURE_TYPES`).

**`CaptureResult`** [SRC:src/pyforge/scribe/capture.py:L46] — `record`, `path`,
`memory_index_line`.

**`RecallAnswer`** [SRC:src/pyforge/scribe/recall.py:L56] — `grounded`, `text`,
`citation`, `node_id`. `grounded=False` is the explicit miss, never fabricated
prose.

**`GraphifyIngestResult`** [SRC:src/pyforge/scribe/extras/graphify.py:L163-L168]
— `nodes` (kind="code" `GraphNode`s), `warnings`; what `ingest_graphify_surface`
returns for `compile.py` to upsert through the `GraphStore` port.

**`GraphifyReport`** [SRC:src/pyforge/scribe/extras/graphify.py:L226-L236] —
`summary_markdown`, `god_nodes`, `node_count`, `edge_count`, `warnings`; what
`build_graphify_report`/`scribe index report` produce.

**`MoveListFinding`** [SRC:src/pyforge/scribe/extras/graphify.py:L314-L318] —
`category`, `path`, `line`, `snippet`; one `scan_move_list`/`scribe index
move-list` hit (`host_import_pyforge` | `sys_path_insert` | `five_tier_root`
| `cfe_caller`).

## Architecture at a Glance

- **Capture** — only write path into `.claude/memory/<type>/` plus `MEMORY.md` index
  [SRC:src/pyforge/scribe/capture.py:L1-L18].
- **Compile** — derived read-model; full rebuild; GraphStore port, not a raw engine
  [SRC:src/pyforge/scribe/compile.py:L4-L11].
- **Recall** — queries compiled projection only; citation must resolve
  [SRC:src/pyforge/scribe/recall.py:L3-L16].
- **CLI** — sole public contract [SRC:src/pyforge/scribe/cli.py:L1-L9].

## CLI

```text
scribe --version
scribe capture --type <feedback|project|reference> --text "<raw>"
scribe capture --promote [--source PATH]
scribe capture --transcripts [--source PATH]
scribe graph compile [--nightly] [--extra | --no-extra]
scribe index report [--path PATH]
scribe index move-list
scribe recall <query>
```

`--promote` and `--transcripts` are mutually exclusive with each other and with
`--type`/`--text` (exit 2) [SRC:src/pyforge/scribe/cli.py:L110-L132].

`scribe index report` requires the optional `graphify` dependency
(`pyforge-scribe[graphify]`); it exits 2 with a clear message when absent,
never an unguarded traceback. `scribe index move-list` has no such
dependency. Neither writes a foundry-root `graphify-out/` — both land under
`.claude/data/pyforge-scribe/graphify/` (derived, gitignored, like `graph.json`).

<!-- [MANUAL:api-notes] -->
<!-- Add custom notes here. This section is preserved during skill updates. -->
<!-- [/MANUAL:api-notes] -->
