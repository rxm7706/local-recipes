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
8 CLI exports documented (`capture_cmd`, `graph_compile`, `recall_cmd`, `index_build`,
`index_report`, `index_move_list`, `index_refresh`, `main`).
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
pixi run -e pyforge-scribe scribe index build            # graphify extra, explicit
pixi run -e pyforge-scribe scribe index report            # GRAPH_REPORT + God nodes
pixi run -e pyforge-scribe scribe index move-list          # foundry-cutover move list
pixi run -e pyforge-scribe scribe index refresh            # cocoindex incremental refresh
```

**Capture** (`scribe capture`) [SRC:src/pyforge/scribe/cli.py:L73-L139]:
`--type` is `feedback` | `project` | `reference` and `--text` is required unless
`--promote` or `--transcripts` is set. Writes under `.claude/memory/<type>/` and
prints `captured: <path>`.

**Compile** (`scribe graph compile [--nightly]`) [SRC:src/pyforge/scribe/cli.py:L251-L269]:
full rebuild of the graph; never prompts. When `SCRIBE_GRAPHIFY_EXTRA` is truthy,
also ingests the named graphify target list (`src/shared/packages/`,
`src/platform/`, `scripts/` — Story 15.1) through the graphify extra
(Story 6.1) as an optional compile source -- off by default (air-gap). Never
`recipes/` or the repo root. Every current node
also gets a `stale` flag (Story 6.3, CAP-13): `true` when its citation's source
file has a git commit postdating the node's own `valid_from` with no `supersedes:`
edge naming it -- a git-timestamp comparison only, no LLM call. `scribe recall`
never serves a stale node; external consumers (e.g. marshal's planning-graph
retrieval) reading `GraphNode.stale` from the compiled graph must fall back to
their own non-graph path instead of serving it.

**Recall** (`scribe recall <query>`) [SRC:src/pyforge/scribe/cli.py]:
prints the answer plus `[source: …]` when grounded, else `no grounded answer found`.
Default omits `kind=code`; `--kind` selects kinds (Story 8.5). `--mode`
planning|memory|code is the named bag (Story 16.1), exclusive with `--kind`.
`--scope`
admits that project's planning tree plus `presentations/<scope>/facts.yaml`
(Story 9.1).

**Index** (`scribe index build|report|move-list`, Story 6.1) -- the graphify
`compile_surface` extra's explicit verbs:
- `scribe index build [--target PATH]`: ingests `PATH` (default
  `src/shared/packages/`) with graphifyy and writes `code`-kind `GraphNode`s
  through the SAME persist port `scribe graph compile` uses -- never a parallel
  store. Requires the `pyforge-scribe[graphify]` extra installed; exits 2 with a
  clear message otherwise. Does not consult `SCRIBE_GRAPHIFY_EXTRA` -- invoking
  it is itself the deliberate opt-in.
- `scribe index report [--target PATH]`: writes a GRAPH_REPORT-style summary
  (node/edge counts, God-node findings via `graphify.god_nodes`) to
  `.claude/data/pyforge-scribe/graph-report.md` (derived, gitignored).
- `scribe index move-list`: scans for the foundry-cutover move-list signals
  (host `import pyforge.*` sites, `sys.path` inserts, `five_tier` roots, CFE
  callers) and writes `.claude/data/pyforge-scribe/move-list.json` (derived,
  gitignored). Independent of graphifyy -- always available.
- `scribe index refresh [--target PATH]` (Story 6.2, the cocoindex
  `compile_surface` incremental-ingest extra): with `SCRIBE_COCOINDEX_EXTRA`
  unset/falsy (default), behaves exactly like `index build` + `index
  move-list` run back to back -- both derived artifacts fully recomputed
  every invocation, no fingerprint index touched. With `SCRIBE_COCOINDEX_EXTRA`
  truthy, an artifact whose declared sources are unchanged since the last
  `index refresh` is skipped entirely -- its previously-written output is
  left untouched -- and only a changed artifact is recomputed. Prints
  `refreshed: <names>; skipped (unchanged): <names>`. This is the GENERIC
  "declare sources -> derived artifact" surface (`pyforge.scribe.extras.
  cocoindex_flow.DerivedArtifact` / `refresh_incremental`) -- Story 6.1's
  graphify ingest + move list are its first two registrations, not a
  special case. A future consumer (marshal Story 28.8's epic-context/
  continuity freshness) binds to this `scribe index refresh`-shaped CLI
  grammar only, never to `pyforge.scribe.extras.cocoindex_flow` internals.

Consumers (foundry-cutover move-list, marshal Story 28.9's planning-corpus
retrieval, and, later, marshal Story 28.8's freshness check) bind to this
grammar only -- never to `pyforge.scribe.extras` internals.

<!-- [MANUAL:additional-notes] -->
Frame store (steward Story 53.2 pointer only): Company + eight station Frames live in `docs/foundry/frames/` in git — do not graph-ingest them unless a later Spec says so.
Session-close ritual, every harness: `scribe capture` (AGENTS.md § Team memory), not restated here.
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
| `index_build` | Explicit graphify ingest through the persist port | `--target` |
| `index_report` | GRAPH_REPORT-style summary + God nodes | `--target` |
| `index_move_list` | Foundry-cutover move-list scan | — |
| `index_refresh` | Incremental refresh of both Story 6.1 artifacts (Story 6.2) | `--target` |
| `capture` | Append-only write under memory_root | `memory_root`, `capture_type`, `text` |
| `compile_graph` | Full graph rebuild via GraphStore port | `memory_root`, `repo_root`, `nightly` |
| `answer` | Lexical (default) or semantic recall | `query`, `store`, `repo_root`, `mode` |
| `open_graph_store` | Factory; default flat-file plugin | `store_path` |
| `ingest_repo` | graphify extra: folder -> `GraphNode`s | `repo_root`, `target`, `warnings` |
| `scan_move_list` | Move-list signal scan (no graphifyy needed) | `repo_root` |
| `refresh_incremental` | cocoindex extra: skip-if-unchanged over declared artifacts | `repo_root`, `artifacts`, `index_path`, `warnings` |

## Key Exports

Public SKF extract of `cli.py` (Quick mode): `capture_cmd`, `graph_compile`,
`recall_cmd`, `index_build`, `index_report`, `index_move_list`,
`index_refresh`, `main` [SRC:src/pyforge/scribe/cli.py]. Console script:
`scribe = pyforge.scribe.cli:main` [SRC:pyproject.toml:L25-L26].

## Usage

Always invoke `scribe` from repo root. Do not `from pyforge.scribe import capture`
in other stations. Graph engine is selected via `pyforge.core.hooks` plugins
(`scribe-graphstore-flatfile`, `scribe-graphstore-pg`) — callers use
`open_graph_store`, not a driver client [SRC:src/pyforge/scribe/graph_store_plugins.py:L1-L8].

The graphify `compile_surface` extra (Story 6.1) is off by default
(`SCRIBE_GRAPHIFY_EXTRA` unset/falsy) — `graphifyy` is imported lazily and only
inside `pyforge.scribe.extras.graphify`; install it via the `pyforge-scribe[graphify]`
optional dependency. Consumers (foundry-cutover move-list, marshal Story 28.9) bind to
the `scribe index …` CLI grammar, never to `pyforge.scribe.extras` internals.

The cocoindex `compile_surface` incremental-ingest extra (Story 6.2) is off by
default (`SCRIBE_COCOINDEX_EXTRA` unset/falsy) — `cocoindex` is imported lazily
and only inside `pyforge.scribe.extras.cocoindex_flow`, which calls only its
standalone `memo_fingerprint` primitive, never the reactive App/Runner/component
runtime (that would make scribe a long-running daemon it does not own). Install
it via the `pyforge-scribe[cocoindex]` optional dependency. It does not hook into
`scribe graph compile` (`compile_graph()`'s full-reset-then-rebuild contract is
incompatible with a "skip if unchanged" step — see `compile.py`'s own docstring);
its home is `scribe index refresh`. Consumers bind to that CLI grammar's exit
code and `refreshed: …; skipped (unchanged): …` output, never to
`pyforge.scribe.extras.cocoindex_flow` internals.

## Key Types

**`CaptureType`** [SRC:src/pyforge/scribe/models.py:L34-L37] — `feedback` |
`project` | `reference` (`CAPTURE_TYPES`).

**`CaptureResult`** [SRC:src/pyforge/scribe/capture.py:L46] — `record`, `path`,
`memory_index_line`.

**`RecallAnswer`** [SRC:src/pyforge/scribe/recall.py:L56] — `grounded`, `text`,
`citation`, `node_id`. `grounded=False` is the explicit miss, never fabricated
prose.

**`GraphNode`** [SRC:src/pyforge/scribe/models.py:L128] — `id`, `kind`, `title`,
`text`, `citation`, `valid_from`, `valid_until`, `superseded_by`, `stale`
(Story 6.3). `is_current` is `valid_until is None`. `stale` is set only on a
current node; external consumers reading the compiled graph must treat
`stale: true` as a signal to fall back to their own non-graph path, never
serve it as current.

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
scribe index build [--target PATH]
scribe index report [--target PATH]
scribe index move-list
scribe index refresh [--target PATH]
```

`--promote` and `--transcripts` are mutually exclusive with each other and with
`--type`/`--text` (exit 2) [SRC:src/pyforge/scribe/cli.py:L110-L132].

`scribe index build`/`report` exit 2 if graphifyy is not installed
(`GraphifyUnavailableError`); `scribe index move-list` never depends on
graphifyy [SRC:src/pyforge/scribe/extras/graphify.py].

`scribe index refresh` also exits 2 on `GraphifyUnavailableError` (its
graphify-ingest artifact still needs graphifyy); `cocoindex` itself is
required only when `SCRIBE_COCOINDEX_EXTRA` is truthy, raising
`CocoindexUnavailableError` if missing
[SRC:src/pyforge/scribe/extras/cocoindex_flow.py].

<!-- [MANUAL:api-notes] -->
<!-- Add custom notes here. This section is preserved during skill updates. -->
<!-- [/MANUAL:api-notes] -->
