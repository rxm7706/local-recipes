---
name: pyforge-scribe
description: >
  Captures team-memory decisions into .claude/memory, compiles the scribe
  knowledge graph, and recalls cited answers via the scribe CLI. Use when
  writing or retrieving team memory, running scribe capture / graph compile /
  recall, or working in src/shared/packages/pyforge-scribe/. Do not import
  pyforge.scribe internals; the CLI is the public contract. Do not use for
  conda-forge recipe authoring (conda-forge-expert) or station personas.
---

# pyforge-scribe

## Overview

Compiles `src/shared/packages/pyforge-scribe/` (PyPI `pyforge-scribe` 0.1.0) as an
agentskills.io content skill for the **scribe** station. Source: local path
`src/shared/packages/pyforge-scribe` @ commit `a5e9dad59ab` (`source_ref: local`).
Forge tier: **Quick** (SKF `skf-extract-public-api` + source-reading; T1-low).
4 CLI exports documented (`capture_cmd`, `graph_compile`, `recall_cmd`, `main`).
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

**Compile** (`scribe graph compile [--nightly]`) [SRC:src/pyforge/scribe/cli.py:L251-L269]:
full rebuild of the graph; never prompts.

**Recall** (`scribe recall <query>`) [SRC:src/pyforge/scribe/cli.py:L272-L285]:
prints the answer plus `[source: …]` when grounded, else `no grounded answer found`.

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
| `graph_compile` | Rebuild compiled graph | `--nightly` |
| `recall_cmd` | Cited recall over compiled graph | `query` |
| `capture` | Append-only write under memory_root | `memory_root`, `capture_type`, `text` |
| `compile_graph` | Full graph rebuild via GraphStore port | `memory_root`, `repo_root`, `nightly` |
| `answer` | Lexical (default) or semantic recall | `query`, `store`, `repo_root`, `mode` |
| `open_graph_store` | Factory; default flat-file plugin | `store_path` |

## Key Exports

Public SKF extract of `cli.py` (Quick mode): `capture_cmd`, `graph_compile`,
`recall_cmd`, `main` [SRC:src/pyforge/scribe/cli.py]. Console script:
`scribe = pyforge.scribe.cli:main` [SRC:pyproject.toml:L25-L26].

## Usage

Always invoke `scribe` from repo root. Do not `from pyforge.scribe import capture`
in other stations. Graph engine is selected via `pyforge.core.hooks` plugins
(`scribe-graphstore-flatfile`, `scribe-graphstore-pg`) — callers use
`open_graph_store`, not a driver client [SRC:src/pyforge/scribe/graph_store_plugins.py:L1-L8].

## Key Types

**`CaptureType`** [SRC:src/pyforge/scribe/models.py:L34-L37] — `feedback` |
`project` | `reference` (`CAPTURE_TYPES`).

**`CaptureResult`** [SRC:src/pyforge/scribe/capture.py:L46] — `record`, `path`,
`memory_index_line`.

**`RecallAnswer`** [SRC:src/pyforge/scribe/recall.py:L56] — `grounded`, `text`,
`citation`, `node_id`. `grounded=False` is the explicit miss, never fabricated
prose.

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
scribe graph compile [--nightly]
scribe recall <query>
```

`--promote` and `--transcripts` are mutually exclusive with each other and with
`--type`/`--text` (exit 2) [SRC:src/pyforge/scribe/cli.py:L110-L132].

<!-- [MANUAL:api-notes] -->
<!-- Add custom notes here. This section is preserved during skill updates. -->
<!-- [/MANUAL:api-notes] -->
