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
`src/shared/packages/pyforge-scribe` @ commit `b69fd81eb8` (`source_ref: local`).
Forge tier: **Quick** (SKF `skf-extract-public-api` + source-reading; T1-low).
First compiled from `a5e9dad59ab` (Story 29.1); recompiled in place at 0.1.0 on
2026-11-01 (steward Story 29.4) from the widened scope (`catalog.py`, the
`scribe catalog` command's module), and again on 2026-11-12 (steward Story 29.5,
the fixes the EGM audit of 2026-11-05 accepted: SCR-R-F3, with SCR-R-F1 carried)
from the scope widened with `models.py` and `graph_store_plane.py`, the staleness
docstrings scribe Story 33.2 corrected, the station contract `contract.md` as a doc
source, and the real `scribe --help`, the way Story 29.1 and atlas Stories 33.1
and 33.2 did.
9 CLI exports documented (`capture_cmd`, `graph_compile`, `recall_cmd`, `index_build`,
`index_report`, `index_move_list`, `index_refresh`, `catalog_bmad_estate`, `main`).
The package `__init__.py` exports only `__version__` — other components integrate
via the CLI, never by importing internal modules [SRC:src/pyforge/scribe/__init__.py:L9-L14].

## Description

Direct-capture CLI for checked-in team memory (`.claude/memory/`) — append-only
write path for team-relevant decisions, ADRs, and project state
[SRC:pyproject.toml:L8].

**The public contract** is
`_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/contract.md`
(spec-pyforge-scribe:CAP-4): every CLI verb path and flag, the MCP tools, the
feature-flag key, every environment variable and every exit code. The MCP tool
names, exit codes and flag key in this skill are rows of that file; where they
differ, the contract and the code win.

## Quick Start

Run from the repository root (never a hardcoded absolute path)
[SRC:src/pyforge/scribe/cli.py:L81-L84]. `scribe capture`, `scribe recall` and
`scribe catalog` run from the session default environment, `pyforge-guild`,
which carries the core package; `scribe graph compile` with an extra, `scribe
index …` and the station suite run in `-e pyforge-scribe`, which adds the heavy
compile extras [SRC:README.md:L28-L33]:

```bash
pixi run -e pyforge-guild scribe capture --type project --text "..."
pixi run -e pyforge-scribe scribe graph compile
pixi run -e pyforge-guild scribe recall "why did we pin typer"
pixi run -e pyforge-scribe scribe index build            # graphify extra, explicit
pixi run -e pyforge-scribe scribe index report            # GRAPH_REPORT + God nodes
pixi run -e pyforge-scribe scribe index refresh           # cocoindex incremental refresh
pixi run -e pyforge-guild scribe catalog bmad-estate --write   # regenerate the BMAD-estate catalog
pixi run -e pyforge-guild scribe catalog bmad-estate --check   # exit 1 on drift
```

**Capture** (`scribe capture`) [SRC:src/pyforge/scribe/cli.py:L110-L175]:
`--type` is `feedback` | `project` | `reference` and `--text` is required unless
`--promote` or `--transcripts` is set. Writes under `.claude/memory/<type>/` and
prints `captured: <path>`.

**Compile** (`scribe graph compile [--nightly]`) [SRC:src/pyforge/scribe/cli.py:L294-L321]:
full rebuild of the graph; never prompts; an overlapping run against the same store
skips with exit 0. When `SCRIBE_GRAPHIFY_EXTRA` is truthy, also ingests the named
graphify target list (`src/shared/packages/`, `src/platform/`, `scripts/` — Story
15.1) through the graphify extra (Story 6.1) as an optional compile source -- off by
default (air-gap). Never `recipes/` or the repo root.

**Staleness** (Story 6.3 and 8.4, spec-pyforge-scribe:CAP-11 and CAP-26)
[SRC:src/pyforge/scribe/models.py:L145-L157] [SRC:src/pyforge/scribe/compile.py:L61-L69]:
the compile clock is the store's `compiled_at`, the moment the compile started —
never a node's `valid_from`. `scribe graph compile` sets `stale: true` on a current
node whose citation's source file has a git commit authored after `compiled_at`, with
no `supersedes:` edge naming it — a git-timestamp comparison only, no LLM call. `scribe
recall` never serves a stale node, and at recall time it also withholds a current node
whose source gained a commit after the store's `compiled_at` (where the store keeps
one; the flat-file store does), so a commit landed between nightlies is never served
before the next compile flags it [SRC:src/pyforge/scribe/recall.py:L295-L296]. That
recall-time withhold does not set `GraphNode.stale`; a consumer gets fresh answers by
calling `scribe recall`, never by reading the compiled graph's `stale` bits.

**Recall** (`scribe recall <query>`) [SRC:src/pyforge/scribe/cli.py:L324]:
prints the answer plus `[source: …]` when grounded, else `no grounded answer found`.
Default omits `kind=code`; `--kind` selects kinds (Story 8.5). `--mode`
planning|memory|code is the named bag (Story 16.1), exclusive with `--kind`.
`--scope`
admits that project's planning tree plus `presentations/<scope>/facts.yaml`
(Story 9.1). `--semantic` selects ranking (pgvector driver only), not the bag.

**Index** (`scribe index build|report|move-list|refresh`, Story 6.1) -- the graphify
`compile_surface` extra's explicit verbs [SRC:src/pyforge/scribe/cli.py:L415-L435]:
- `scribe index build [--target PATH]`: ingests `PATH`, or with no `--target` walks
  the named list (`src/shared/packages`, `src/platform`, `scripts`; never `recipes/`),
  with graphifyy and writes `code`-kind `GraphNode`s through the SAME persist port
  `scribe graph compile` uses -- never a parallel store. Requires the
  `pyforge-scribe[graphify]` extra installed; exits 2 with a clear message
  otherwise. Does not consult `SCRIBE_GRAPHIFY_EXTRA` -- invoking it is itself the
  deliberate opt-in.
- `scribe index report [--target PATH]`: writes a GRAPH_REPORT-style summary
  (node/edge counts, God-node findings via `graphify.god_nodes`) to
  `.claude/data/pyforge-scribe/graph-report.md` (derived, gitignored); the same
  target rule as `build`.
- `scribe index move-list`: **retired with spec-pyforge-scribe:CAP-34 (2026-11-10)**;
  the verb stays listed until a Story removes it. It scans for the foundry-cutover
  move-list signals and writes `.claude/data/pyforge-scribe/move-list.json` (derived,
  gitignored). Do not build on it.
- `scribe index refresh [--target PATH] [--declare MANIFEST]` (Story 6.2, the
  cocoindex `compile_surface` incremental-ingest extra): with `SCRIBE_COCOINDEX_EXTRA`
  unset/falsy (default), behaves exactly like `index build` + `index move-list` run
  back to back -- both derived artifacts fully recomputed every invocation, no
  fingerprint index touched. With `SCRIBE_COCOINDEX_EXTRA` truthy, an artifact whose
  declared sources are unchanged since the last `index refresh` is skipped entirely
  -- its previously-written output is left untouched -- and only a changed artifact
  is recomputed. Prints `refreshed: <names>; skipped (unchanged): <names>`.
  `--declare <manifest>` (`{"artifacts": [{"name", "sources", "output"}, …]}`) tracks
  a caller's own registrations instead and never consults the switch: it only answers
  whether the declared sources changed [SRC:src/pyforge/scribe/cli.py:L493-L494].

Consumers (marshal's planning-corpus retrieval and freshness checks) bind to this
grammar only -- never to `pyforge.scribe.extras` internals.

**Catalog** (`scribe catalog bmad-estate [--write | --check]`, Story 24.1,
spec-pyforge-scribe:CAP-32) [SRC:src/pyforge/scribe/cli.py:L673-L718]: derived
catalogs, generated from in-tree sources and never hand-written. `bmad-estate` reads
the installed manifests, every `.claude/skills/*/SKILL.md` frontmatter,
`bmad-help.csv`, `suite-members.yaml` joined with steward's adoption register, the
`bmad-*` pins in `pixi.toml`, the marshal harness range and the release-cadence steps
-- offline, no station internals [SRC:src/pyforge/scribe/catalog.py:L1-L30].
Without a flag it prints the rendered catalog; `--write` renders
`docs/reference/bmad-estate-llms-full.md`; `--check` compares each section's
digest against a fresh derive and names the drifted section with its sources.
Exit 0 rendered / current, 1 drift (`--check`), 2 a source cannot be read or
`--write` and `--check` were both given. Behind the kill switch
`pyforge.scribe.bmad_estate_catalog` (default on; off keeps the verb listed,
marked disabled, and refuses with exit 2) [SRC:src/pyforge/scribe/cli.py:L644-L647].
The `bmad-estate-check` detector runs the same check; a station skill whose
frontmatter `description` moves reds it until the catalog is re-rendered.

<!-- [MANUAL:additional-notes] -->
Frame store (steward Story 53.2 pointer only): Company + eight station Frames live in `docs/foundry/frames/` in git — do not graph-ingest them unless a later Spec says so.
Session-close ritual, every harness: `scribe capture` (AGENTS.md § Team memory), not restated here.
<!-- [/MANUAL:additional-notes] -->

<!-- [MANUAL:station-mcp] -->
Station host: scribe's MCP face is `POST /stations/scribe/mcp` on the platform host. How to start the host, get the
assertion it accepts and send a request: `docs/how-to/reach-a-station-mcp-endpoint.md`.
<!-- [/MANUAL:station-mcp] -->

## Station MCP runner

What `POST /stations/scribe/mcp` runs, as the code stands (`contract.md` § *MCP
tools*; the host code is django-scribe's `mcp_asgi.py` and django-pyforge's closed
verb table; this package ships no MCP server):

| Tool | Kind | Takes | What it does |
|---|---|---|---|
| `start_recall` | MCP tool | `target` (the query), `assertion` | Starts a supervised recall run and returns `{"handle": …}` at once. |
| `get_recall` | MCP tool | `handle`, `assertion` | Returns the supervisor's record of that run. |
| `run_recall` | supervisor runner, not an MCP tool | the `start_recall` payload | Runs `scribe recall -- <query>` in `pyforge-guild`, passing `SCRIBE_GRAPH_DSN` through. |

A query is 1 to 2000 characters with no control character; anything else is refused
before a run starts. The runner runs `scribe recall` and nothing else: no `capture`,
`graph compile`, `index` or `catalog` verb is reachable through the face.

## Common Workflows

**Direct capture:** `scribe capture --type <t> --text "…"` → `capture_cmd`
[SRC:src/pyforge/scribe/cli.py:L111] → one file under `.claude/memory/<type>/` and an
index line on `MEMORY.md`.

**Promote user-local memory:** `scribe capture --promote` → proposal, then
`typer.confirm`, then the promotion [SRC:src/pyforge/scribe/cli.py:L178-L206].
Zero writes before confirm.

**Transcript harvest:** `scribe capture --transcripts` → proposal, then confirm, then
one capture per candidate [SRC:src/pyforge/scribe/cli.py:L231-L274]. Does not mutate
transcript files.

**Rebuild then query:** `scribe graph compile` → `graph_compile`
[SRC:src/pyforge/scribe/cli.py:L295], then `scribe recall "<query>"` → `recall_cmd`
[SRC:src/pyforge/scribe/cli.py:L325].

**Estate catalog:** `scribe catalog bmad-estate --check` → `catalog_bmad_estate`
[SRC:src/pyforge/scribe/cli.py:L674]; on drift, `--write` re-renders it.

## Key API Summary

The CLI verbs, the only public surface (the functions behind them are internals):

| Function | Verb | Key params |
|---|---|---|
| `main` | `scribe` (Typer entry, console script) | — |
| `capture_cmd` | `scribe capture` | `--type`, `--text`, `--promote`, `--transcripts`, `--source` |
| `graph_compile` | `scribe graph compile` | `--nightly` |
| `recall_cmd` | `scribe recall` | `query`, `--semantic`, `--scope`, `--kind`, `--mode` |
| `index_build` | `scribe index build` | `--target` |
| `index_report` | `scribe index report` | `--target` |
| `index_move_list` | `scribe index move-list` (retired, spec-pyforge-scribe:CAP-34) | — |
| `index_refresh` | `scribe index refresh` | `--target`, `--declare` |
| `catalog_bmad_estate` | `scribe catalog bmad-estate` | `--write`, `--check`, `--root`, `--output`, `--pipeline-truth` |

## Key Exports

Public SKF extract of `cli.py` (Quick mode): `capture_cmd`, `graph_compile`,
`recall_cmd`, `index_build`, `index_report`, `index_move_list`,
`index_refresh`, `catalog_bmad_estate`, `main` [SRC:src/pyforge/scribe/cli.py]. Console script:
`scribe = pyforge.scribe.cli:main` [SRC:pyproject.toml:L38].

## Usage

Always invoke `scribe` from repo root. Do not `from pyforge.scribe import capture`
in other stations. The graph engine is selected by owner through `pyforge.core.hooks`
plugins on the hook `pyforge.scribe.graph_store`, read from `PYFORGE_GRAPHSTORE_OWNER`
[SRC:src/pyforge/scribe/graph_store_plugins.py:L29-L62]: `scribe` (default, the flat
file), `steward` (PostgreSQL with pgvector, `SCRIBE_GRAPH_DSN` or `DATABASE_URL`) or
`atlas` (the query plane, `PlaneGraphStorePlugin` over the DuckDB file
`QUERY_PLANE_DUCKDB` names) [SRC:src/pyforge/scribe/graph_store_plane.py:L1-L6].
Callers never import a driver client.

The graphify `compile_surface` extra (Story 6.1) is off by default
(`SCRIBE_GRAPHIFY_EXTRA` unset/falsy) — `graphifyy` is imported lazily and only
inside `pyforge.scribe.extras.graphify`; install it via the `pyforge-scribe[graphify]`
optional dependency. Consumers bind to the `scribe index …` CLI grammar, never to
`pyforge.scribe.extras` internals.

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

Exit codes (`contract.md` § *Exit codes*): `0` success (also `--version`, a scan with
nothing to write or declined, a `graph compile` skipped because a run is in progress,
`catalog bmad-estate --check` current) · `1` `catalog bmad-estate --check` found drift
· `2` usage or could-not-run (Click's usage error, mutually exclusive flags, a missing
`--type`/`--text`, an unknown `--mode`, a missing extra, an unreadable source, the
kill switch off).

## Key Types

**`CaptureType`** [SRC:src/pyforge/scribe/models.py:L34-L37] — `feedback` |
`project` | `reference` (`CAPTURE_TYPES`).

**`CaptureResult`** [SRC:src/pyforge/scribe/capture.py:L46] — `record`, `path`,
`memory_index_line`.

**`RecallAnswer`** [SRC:src/pyforge/scribe/recall.py:L119] — `grounded`, `text`,
`citation`, `node_id`. `grounded=False` is the explicit miss, never fabricated
prose.

**`GraphNode`** [SRC:src/pyforge/scribe/models.py:L126] — `id`, `kind`, `title`,
`text`, `citation`, `valid_from`, `valid_until`, `superseded_by`, `stale`
(Story 6.3). `is_current` is `valid_until is None`. `stale` is set by the compile
against the store's `compiled_at`, only on a current node; recall's own withhold
covers commits after it.

## Architecture at a Glance

- **Capture** — only write path into `.claude/memory/<type>/` plus `MEMORY.md` index
  [SRC:src/pyforge/scribe/capture.py:L1-L18].
- **Compile** — derived read-model; full rebuild; GraphStore port, not a raw engine
  [SRC:src/pyforge/scribe/compile.py:L1-L103].
- **Recall** — queries compiled projection only; citation must resolve
  [SRC:src/pyforge/scribe/recall.py:L1-L32].
- **Catalog** — derives, never decides; offline; structured digests per section
  [SRC:src/pyforge/scribe/catalog.py:L1-L30].
- **CLI** — sole public contract [SRC:src/pyforge/scribe/cli.py:L1-L12].

## CLI

```text
scribe --version
scribe capture --type <feedback|project|reference> --text "<raw>"
scribe capture --promote [--source PATH]
scribe capture --transcripts [--source PATH]
scribe graph compile [--nightly]
scribe recall <query> [--semantic] [--scope SLUG] [--kind KIND]… [--mode planning|memory|code]
scribe index build [--target PATH]
scribe index report [--target PATH]
scribe index move-list
scribe index refresh [--target PATH] [--declare MANIFEST]
scribe catalog bmad-estate [--write | --check] [--root PATH] [--output PATH] [--pipeline-truth PATH]
```

`--promote` and `--transcripts` are mutually exclusive with each other and with
`--type`/`--text` (exit 2) [SRC:src/pyforge/scribe/cli.py:L146-L159].

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
