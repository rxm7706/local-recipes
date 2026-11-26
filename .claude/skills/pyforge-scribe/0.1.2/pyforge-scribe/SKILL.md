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
`src/shared/packages/pyforge-scribe` @ commit `5f22584869` (`source_ref: local`).
Forge tier: **Forge** (SKF `skf-extract-public-api` over ast-grep 0.45.3; T1).
First compiled from `a5e9dad59ab` (Story 29.1); recompiled in place at 0.1.0 on
2026-11-01 (steward Story 29.4) from the widened scope (`catalog.py`, the
`scribe catalog` command's module), and again on 2026-11-12 (steward Story 29.5,
the fixes the EGM audit of 2026-11-05 accepted: SCR-R-F3, with SCR-R-F1 carried)
from the scope widened with `models.py` and `graph_store_plane.py`, the staleness
docstrings scribe Story 33.2 corrected, the station contract `contract.md` as a doc
source, and the real `scribe --help`, the way Story 29.1 and atlas Stories 33.1
and 33.2 did.
Rebuilt as 0.1.1 on 2026-11-25 (steward Story 134.3) with `skf-update-skill` at Forge
tier over ast-grep 0.45.3, at `21087f55c9`: the first Forge-tier build, over the whole
scope the brief names, and the compile time every shipped store keeps, after scribe
Story 35.1.
Updated to 0.1.2 on 2026-11-25 (steward Story 136.10) by `skf-update-skill` at the same
tier, from the source at `5f22584869`: no export and no in-scope file changed; the brief
this skill is built from cites the capability id in qualified form.
51 exports documented (36 functions, 15 classes; T1, with the signature of
`index_move_list` carried at T1-low from the 0.1.0 map): the nine CLI functions
(`capture_cmd`, `graph_compile`, `recall_cmd`, `index_build`, `index_report`,
`index_move_list`, `index_refresh`, `catalog_bmad_estate`, `main`) and
`mark_retrofit_help` in `cli.py`, the rest in `capture.py`, `catalog.py`, `compile.py`,
`graph_store_plane.py`, `graph_store_plugins.py`, `models.py` and `recall.py`
(§ *Full API Reference*, § *Full Type Definitions*).
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
[SRC:src/pyforge/scribe/cli.py:L82-L85]. `scribe capture`, `scribe recall` and
`scribe catalog` run from the session default environment, `pyforge-guild`,
which carries the core package; `scribe graph compile` with an extra, `scribe
index …` and the station suite run in `-e pyforge-scribe`, which adds the heavy
compile extras [SRC:README.md:L29-L34]:

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

**Capture** (`scribe capture`) [SRC:src/pyforge/scribe/cli.py:L111-L176]:
`--type` is `feedback` | `project` | `reference` and `--text` is required unless
`--promote` or `--transcripts` is set. Writes under `.claude/memory/<type>/` and
prints `captured: <path>`.

**Compile** (`scribe graph compile [--nightly]`) [SRC:src/pyforge/scribe/cli.py:L299-L326]:
full rebuild of the graph; never prompts; an overlapping run against the same store
skips with exit 0. When `SCRIBE_GRAPHIFY_EXTRA` is truthy, also ingests the named
graphify target list (`src/shared/packages/`, `src/platform/`, `scripts/` — Story
15.1) through the graphify extra (Story 6.1) as an optional compile source -- off by
default (air-gap). Never `recipes/` or the repo root.

**Staleness** (Story 6.3 and 8.4, spec-pyforge-scribe:CAP-11 and CAP-26)
[SRC:src/pyforge/scribe/models.py:L152-L165] [SRC:src/pyforge/scribe/compile.py:L61-L73]:
the compile clock is the store's `compiled_at`, the moment the compile started —
never a node's `valid_from`. `scribe graph compile` sets `stale: true` on a current
node whose citation's source file has a git commit authored after `compiled_at`, with
no `supersedes:` edge naming it — a git-timestamp comparison only, no LLM call. `scribe
recall` never serves a stale node, and at recall time it also withholds a current node
whose source gained a commit after the store's `compiled_at`, so a commit landed
between nightlies is never served before the next compile flags it
[SRC:src/pyforge/scribe/recall.py:L295-L302]. Every shipped store keeps the compile
time: the flat file as the `compiled_at` key of its JSON document, the PostgreSQL and
plane stores as one reserved row of the node relation they already have (id
`COMPILED_AT_ROW_ID`, `scribe:compiled_at`; never a column, never a node: a store
refuses a `GraphNode` under that id) [SRC:src/pyforge/scribe/models.py:L125-L130]. A
third-party store with no `compiled_at` degrades to the stored `stale` bit alone. That
recall-time withhold does not set `GraphNode.stale`; a consumer gets fresh answers by
calling `scribe recall`, never by reading the compiled graph's `stale` bits.

**Recall** (`scribe recall <query>`) [SRC:src/pyforge/scribe/cli.py:L329]:
prints the answer plus `[source: …]` when grounded, else `no grounded answer found`.
Default omits `kind=code`; `--kind` selects kinds (Story 8.5). `--mode`
planning|memory|code is the named bag (Story 16.1), exclusive with `--kind`.
`--scope`
admits that project's planning tree plus `presentations/<scope>/facts.yaml`
(Story 9.1). `--semantic` selects ranking (pgvector driver only), not the bag.

**Index** (`scribe index build|report|move-list|refresh`, Story 6.1) -- the graphify
`compile_surface` extra's explicit verbs [SRC:src/pyforge/scribe/cli.py:L420-L440]:
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
  whether the declared sources changed [SRC:src/pyforge/scribe/cli.py:L498-L499].
  The graphify-ingest artifact's fingerprinted sources are `--target` alone when
  given, else every directory of the named list that exists
  [SRC:src/pyforge/scribe/cli.py:L541-L547].

Consumers (marshal's planning-corpus retrieval and freshness checks) bind to this
grammar only -- never to `pyforge.scribe.extras` internals.

**Catalog** (`scribe catalog bmad-estate [--write | --check]`, Story 24.1,
spec-pyforge-scribe:CAP-32) [SRC:src/pyforge/scribe/cli.py:L684-L729]: derived
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
marked disabled, and refuses with exit 2) [SRC:src/pyforge/scribe/cli.py:L655-L658].
The `bmad-estate-check` detector runs the same check; a station skill whose
frontmatter `description` moves reds it until the catalog is re-rendered.

**Call paths** (for reading the code; other stations call the CLI, never these functions):
- `capture_cmd` writes each record through `capture(memory_root, capture_type, text)`
  [SRC:src/pyforge/scribe/cli.py:L172].
- `graph_compile` calls `compile_graph(memory_root=..., repo_root=..., nightly=...)`
  [SRC:src/pyforge/scribe/cli.py:L311], which opens the store with
  `open_graph_store(store_path or default_store_path(repo_root))`
  [SRC:src/pyforge/scribe/compile.py:L237] and reads each memory file with
  `parse_capture_file(path)` [SRC:src/pyforge/scribe/compile.py:L384].
- `recall_cmd` opens `open_graph_store(default_store_path(repo_root))` and calls
  `answer(query, store, repo_root=..., mode=..., scope=..., kinds=..., surface=...)`
  [SRC:src/pyforge/scribe/cli.py:L373-L382]. `answer` takes its kind bag from
  `resolve_recall_selection(kinds=..., surface=...)` [SRC:src/pyforge/scribe/recall.py:L235],
  which falls back to `resolve_recall_kinds(kinds)` [SRC:src/pyforge/scribe/recall.py:L196],
  and withholds a node whose source `source_committed_after(repo_root, node, compiled_at)`
  reports changed [SRC:src/pyforge/scribe/recall.py:L295-L302].
- `index_build` reports the nodes it wrote to `default_store_path(repo_root)`
  [SRC:src/pyforge/scribe/cli.py:L436]; `index_report` writes the graph report
  [AST:src/pyforge/scribe/cli.py:L440-L451]; `index_move_list` and `index_refresh` both run
  the move-list scan [SRC:src/pyforge/scribe/cli.py:L461] [SRC:src/pyforge/scribe/cli.py:L533].
- `catalog_bmad_estate` calls `check(root, catalog=..., pipeline_truth=...)` for `--check`,
  `write(root, output=..., pipeline_truth=...)` for `--write`, else
  `render(derive(root, pipeline_truth=...))` [SRC:src/pyforge/scribe/cli.py:L714-L726].
  `derive` reads its sources with `read_installed`, `read_help`, `read_skills`, `read_members`,
  `read_register`, `read_pins`, `read_recipe_versions`, `read_harness_range`,
  `read_cadence_steps` and, given `--pipeline-truth`, `read_pipeline_truth`, then runs
  `find_disagreements` [AST:src/pyforge/scribe/catalog.py:L624-L645]; `render` stamps each
  section's `digests(estate)` [SRC:src/pyforge/scribe/catalog.py:L695]; `check` compares
  `recorded_digests(text)` with `digests(estate)` [SRC:src/pyforge/scribe/catalog.py:L905-L907].
- `main(argv)` calls `mark_retrofit_help()` when `-h` or `--help` is among the tokens, then runs
  the Typer app [SRC:src/pyforge/scribe/cli.py:L742-L745].

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
[AST:src/pyforge/scribe/cli.py:L112] → one file under `.claude/memory/<type>/` and an
index line on `MEMORY.md`.

**Promote user-local memory:** `scribe capture --promote` → proposal, then
`typer.confirm`, then the promotion [SRC:src/pyforge/scribe/cli.py:L179-L211].
Zero writes before confirm.

**Transcript harvest:** `scribe capture --transcripts` → proposal, then confirm, then
one capture per candidate [SRC:src/pyforge/scribe/cli.py:L236-L279]. Does not mutate
transcript files.

**Rebuild then query:** `scribe graph compile` → `graph_compile`
[AST:src/pyforge/scribe/cli.py:L300], then `scribe recall "<query>"` → `recall_cmd`
[AST:src/pyforge/scribe/cli.py:L330].

**Estate catalog:** `scribe catalog bmad-estate --check` → `catalog_bmad_estate`
[AST:src/pyforge/scribe/cli.py:L685]; on drift, `--write` re-renders it.

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

Public SKF extract (`skf-extract-public-api`, ast-grep), 51 exports. The nine CLI
functions are `capture_cmd`, `graph_compile`, `recall_cmd`, `index_build`,
`index_report`, `index_move_list`, `index_refresh`, `catalog_bmad_estate` and `main`
[SRC:src/pyforge/scribe/cli.py]; the other 42 are in § *Full API Reference* and
§ *Full Type Definitions*. Console script:
`scribe = pyforge.scribe.cli:main` [SRC:pyproject.toml:L38].

## Usage

Always invoke `scribe` from repo root. Do not `from pyforge.scribe import capture`
in other stations. The graph engine is selected by owner through `pyforge.core.hooks`
plugins on the hook `pyforge.scribe.graph_store`, read from `PYFORGE_GRAPHSTORE_OWNER`
[AST:src/pyforge/scribe/graph_store_plugins.py:L29-L62]: `scribe` (default, the flat
file), `steward` (PostgreSQL with pgvector, `SCRIBE_GRAPH_DSN` or `DATABASE_URL`,
passed whole with its query string, so `sslmode` and the other libpq parameters reach
the driver [SRC:src/pyforge/scribe/graph_store_plugins.py:L67-L71]) or
`atlas` (the query plane, `PlaneGraphStorePlugin` over the DuckDB file
`QUERY_PLANE_DUCKDB` names) [SRC:src/pyforge/scribe/graph_store_plane.py:L1-L11].
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
`--type`/`--text`, an unknown `--mode`, a missing extra, an unreadable source, a
capture or graph-store lock that timed out, a graph-store owner with no registered
plugin, the kill switch off).

## Key Types

**`CaptureType`** [SRC:src/pyforge/scribe/models.py:L34-L37] — `feedback` |
`project` | `reference` (`CAPTURE_TYPES`).

**`CaptureResult`** [AST:src/pyforge/scribe/capture.py:L46] — `record`, `path`,
`memory_index_line`.

**`RecallAnswer`** [AST:src/pyforge/scribe/recall.py:L119] — `grounded`, `text`,
`citation`, `node_id`. `grounded=False` is the explicit miss, never fabricated
prose.

**`GraphNode`** [AST:src/pyforge/scribe/models.py:L133] — `id`, `kind`, `title`,
`text`, `citation`, `valid_from`, `valid_until`, `superseded_by`, `stale`
(Story 6.3). `is_current` is `valid_until is None`. `stale` is set by the compile
against the store's `compiled_at`, only on a current node; recall's own withhold
covers commits after it.

## Architecture at a Glance

- **Capture** — only write path into `.claude/memory/<type>/` plus `MEMORY.md` index
  [SRC:src/pyforge/scribe/capture.py:L1-L18].
- **Compile** — derived read-model; full rebuild; GraphStore port, not a raw engine
  [SRC:src/pyforge/scribe/compile.py:L1-L107].
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
`--type`/`--text` (exit 2) [SRC:src/pyforge/scribe/cli.py:L147-L160].

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

## Full API Reference

The 36 functions the extract found, as the source declares them, for reading the code. Other
stations and `src/platform/` do not import them: the CLI is the contract (§ *Usage*).

### `capture.py`

- `capture(memory_root: Path, capture_type: CaptureType, text: str, *, slug: str | None = None,
  description: str | None = None, supersedes: str | None = None) -> CaptureResult` — Append one
  new record under `memory_root/<capture_type>/` (AD-1/AD-2/FR-7).
  [AST:src/pyforge/scribe/capture.py:L54]

### `catalog.py`

- `check(root: Path, *, catalog: Path | None = None, pipeline_truth: Path | None = None) ->
  list[str]` — Return one finding per drifted section (empty means current); raises
  CatalogSourceError. [AST:src/pyforge/scribe/catalog.py:L899]
- `derive(root: Path, *, pipeline_truth: Path | None = None) -> Estate` — Read every source and
  assemble the facts; raises CatalogSourceError when one cannot be read.
  [AST:src/pyforge/scribe/catalog.py:L624]
- `digests(estate: Estate) -> dict[str, str]` — the source gives it no docstring.
  [AST:src/pyforge/scribe/catalog.py:L653]
- `find_disagreements(estate: Estate) -> list[Disagreement]` — the source gives it no docstring.
  [AST:src/pyforge/scribe/catalog.py:L603]
- `read_cadence_steps(root: Path) -> list[str]` — the source gives it no docstring.
  [AST:src/pyforge/scribe/catalog.py:L571]
- `read_harness_range(root: Path) -> str` — the source gives it no docstring.
  [AST:src/pyforge/scribe/catalog.py:L564]
- `read_help(root: Path) -> tuple[list[dict[str, str]], dict[str, str]]` — the source gives it
  no docstring. [AST:src/pyforge/scribe/catalog.py:L344]
- `read_installed(root: Path) -> dict[str, object]` — the source gives it no docstring.
  [AST:src/pyforge/scribe/catalog.py:L272]
- `read_members(root: Path) -> list[Member]` — the source gives it no docstring.
  [AST:src/pyforge/scribe/catalog.py:L444]
- `read_pins(root: Path) -> dict[str, dict[str, str]]` — the source gives it no docstring.
  [AST:src/pyforge/scribe/catalog.py:L540]
- `read_pipeline_truth(path: Path) -> dict[str, dict[str, str]]` — the source gives it no
  docstring. [AST:src/pyforge/scribe/catalog.py:L578]
- `read_recipe_versions(root: Path, names: list[str]) -> dict[str, str]` — the source gives it
  no docstring. [AST:src/pyforge/scribe/catalog.py:L550]
- `read_register(root: Path) -> tuple[dict[str, RegisterRow], list[RoutingRow]]` — the source
  gives it no docstring. [AST:src/pyforge/scribe/catalog.py:L492]
- `read_skills(root: Path, help_modules: dict[str, str]) -> tuple[list[Skill], list[str]]` — the
  source gives it no docstring. [AST:src/pyforge/scribe/catalog.py:L411]
- `recorded_digests(text: str) -> dict[str, str]` — the source gives it no docstring.
  [AST:src/pyforge/scribe/catalog.py:L895]
- `render(estate: Estate, *, today: date | None = None) -> str` — the source gives it no
  docstring. [AST:src/pyforge/scribe/catalog.py:L675]
- `write(root: Path, *, output: Path | None = None, pipeline_truth: Path | None = None, today:
  date | None = None ) -> Path` — Render the catalog into `output` (default: the committed path)
  and return the path. [AST:src/pyforge/scribe/catalog.py:L872]

### `cli.py`

- `capture_cmd` — the `scribe capture` command; its options are the ones § *CLI* lists.
  [AST:src/pyforge/scribe/cli.py:L112]
- `catalog_bmad_estate` — the `scribe catalog bmad-estate` command; its options are the ones §
  *CLI* lists. [AST:src/pyforge/scribe/cli.py:L685]
- `graph_compile` — the `scribe graph compile` command; its options are the ones § *CLI* lists.
  [AST:src/pyforge/scribe/cli.py:L300]
- `index_build` — the `scribe index build` command; its options are the ones § *CLI* lists.
  [AST:src/pyforge/scribe/cli.py:L421]
- `index_move_list() -> None` — the retired `scribe index move-list` command
  (spec-pyforge-scribe:CAP-34); it takes no option. [AST:src/pyforge/scribe/cli.py:L455]
- `index_refresh` — the `scribe index refresh` command; its options are the ones § *CLI* lists.
  [AST:src/pyforge/scribe/cli.py:L499]
- `index_report` — the `scribe index report` command; its options are the ones § *CLI* lists.
  [AST:src/pyforge/scribe/cli.py:L440]
- `main(argv: list[str] | None = None) -> int | None` — Run the CLI on `argv` (`sys.argv[1:]`
  when None); Click exits through `SystemExit`; the entry behind the `scribe` console script.
  [AST:src/pyforge/scribe/cli.py:L737]
- `mark_retrofit_help() -> None` — Mark `catalog bmad-estate` disabled in `--help` while its
  switch reads OFF (called from `main`). [AST:src/pyforge/scribe/cli.py:L672]
- `recall_cmd` — the `scribe recall` command; its options are the ones § *CLI* lists.
  [AST:src/pyforge/scribe/cli.py:L330]

### `compile.py`

- `compile_graph(*, memory_root: Path, repo_root: Path, store: GraphStore | None = None,
  store_path: Path | None = None, nightly: bool = False, max_commits: int =
  _DEFAULT_MAX_COMMITS, transcript_root: Path | None = None, compiled_at: datetime | None =
  None) -> CompileResult` — Rebuild the compiled graph from scratch from the seven named
  surfaces. [AST:src/pyforge/scribe/compile.py:L203]
- `default_store_path(repo_root: Path) -> Path` — The default `GraphStore` location --
  `.claude/data/` is already blanket-gitignored (`.gitignore:718`); the compiled graph is a
  derived, disposable artifact (AD-1), never tracked alongside `.claude/memory/`'s
  intentionally-checked-in entries. [AST:src/pyforge/scribe/compile.py:L195]
- `source_committed_after(repo_root: Path, node: GraphNode, compiled_at: datetime) -> bool` —
  True when this node's git-trackable source has a commit after `compiled_at` (Story 11.1).
  [AST:src/pyforge/scribe/compile.py:L1155]

### `graph_store_plugins.py`

- `open_graph_store(store_path: Path, *, registry: PluginRegistry | None = None, owner: str |
  None = None) -> GraphStore` — Return a `GraphStore` from the plugin matching `owner`.
  [AST:src/pyforge/scribe/graph_store_plugins.py:L29]

### `models.py`

- `parse_capture_file(path: Path) -> "CaptureRecord"` — Parse a whole
  `.claude/memory/<type>/*.md` file written by `to_frontmatter()`.
  [AST:src/pyforge/scribe/models.py:L183]

### `recall.py`

- `answer(query: str, store: GraphStore, *, repo_root: Path, mode: str = "lexical", scope: str |
  None = None, kinds: frozenset[str] | None = None, surface: str | None = None) -> RecallAnswer`
  — Deterministic, cited retrieval over the compiled graph (AD-6/AD-8).
  [AST:src/pyforge/scribe/recall.py:L199]
- `resolve_recall_kinds(kinds: frozenset[str] | None) -> frozenset[str]` — `None` is the default
  bag (no `code`). [AST:src/pyforge/scribe/recall.py:L162]
- `resolve_recall_selection(*, kinds: frozenset[str] | None = None, surface: str | None = None)
  -> frozenset[str]` — Resolve `--mode` or `--kind` to a kind bag (Story 16.1).
  [AST:src/pyforge/scribe/recall.py:L179]

## Full Type Definitions

The 15 classes. A line lists the class's fields and methods as the source declares them.

### `capture.py`

- `class CaptureResult` — What `capture()` did, for the CLI layer to report back: `record:
  CaptureRecord`, `path: Path`, `memory_index_line: str`.
  [AST:src/pyforge/scribe/capture.py:L46]

### `catalog.py`

- `class CatalogSourceError(PyforgeError, RuntimeError)` — A source the catalog derives from
  cannot be read (exit 2, never a false green). [AST:src/pyforge/scribe/catalog.py:L131]
- `class Disagreement` — the source gives it no docstring: `member: str`, `versions: dict[str,
  str]`. [AST:src/pyforge/scribe/catalog.py:L173]
- `class Estate` — Every derived fact, grouped by the section that renders it: `installed:
  dict[str, object] = field(default_factory=dict)`, `skills: list[Skill] =
  field(default_factory=list)`, `skill_dirs_without_skill_md: list[str] =
  field(default_factory=list)`, `help_rows: list[dict[str, str]] = field(default_factory=list)`,
  `module_docs: dict[str, str] = field(default_factory=dict)`, `members: list[Member] =
  field(default_factory=list)`, `register: dict[str, RegisterRow] =
  field(default_factory=dict)`, `routing: list[RoutingRow] = field(default_factory=list)`,
  `pins: dict[str, dict[str, str]] = field(default_factory=dict)`, `recipe_versions: dict[str,
  str] = field(default_factory=dict)`, `disagreements: list[Disagreement] =
  field(default_factory=list)`, `harness_range: str = ''`, ….
  [AST:src/pyforge/scribe/catalog.py:L179]
- `class Member` — the source gives it no docstring: `name: str`, `description: str`, `notes:
  str`, `deprecated: bool`. [AST:src/pyforge/scribe/catalog.py:L144]
- `class RegisterRow` — the source gives it no docstring: `member: str`, `version: str`,
  `install_class: str`, `wired: str`, `verdict: str`, `wielder: str`, `provisioning: str`,
  `hazards: str`, `story: str`. [AST:src/pyforge/scribe/catalog.py:L152]
- `class RoutingRow` — the source gives it no docstring: `skills: str`, `member: str`, `station:
  str`, `story: str`. [AST:src/pyforge/scribe/catalog.py:L165]
- `class Skill` — the source gives it no docstring: `name: str`, `family: str`, `description:
  str`, `path: str`. [AST:src/pyforge/scribe/catalog.py:L136]

### `compile.py`

- `class CompileInProgressError(PyforgeError, RuntimeError)` — Another `scribe graph compile`
  currently holds this store's lock (Story 3.3). [AST:src/pyforge/scribe/compile.py:L177]
- `class CompileResult` — What `compile_graph()` did, for the CLI layer to report back:
  `node_count: int`, `invalidated_count: int`, `stale_count: int`, `store_path: Path`,
  `warnings: tuple[str, ...]`. [AST:src/pyforge/scribe/compile.py:L185]

### `graph_store_plane.py`

- `class PlaneGraphStore` — Concrete `GraphStore`: `def __init__(self, plane_path: Path,
  store_path: Path, *, write: bool = True) -> None`, `def _open_plane(self, path: Path, *, write:
  bool)`, `def _ensure_tables(self) -> None`, `def _load(self) -> None`, `def reset(self) ->
  None`, `def upsert_node(self, node: GraphNodeModel) -> None`, `def invalidate_edge(self,
  node_id: str, *, ended_at: datetime, superseded_by: str) -> None`, `def
  query_by_citation(self, citation: str) -> list[GraphNodeModel]`, `def iter_nodes(self) ->
  Iterator[GraphNodeModel]`, `def query_similar(self, query: str, *, limit: int=8) ->
  list[GraphNodeModel]`, `def commit(self) -> None`, `def close(self) -> None`.
  [AST:src/pyforge/scribe/graph_store_plane.py:L40]
- `class PlaneGraphStorePlugin` — CAP-18 adapter: `hook_spec: str = GRAPHSTORE_HOOK_SPEC.name`,
  `owner: str = PLANE_GRAPHSTORE_OWNER`, `def call(self, point: str, context:
  MutableMapping[str, Any]) -> Any`. [AST:src/pyforge/scribe/graph_store_plane.py:L195]

### `models.py`

- `class CaptureRecord(BaseModel)` — One immutable, append-only team-memory capture (AD-1): `id:
  str = Field(default_factory=lambda: uuid.uuid4().hex)`, `type: CaptureType`, `name: str`,
  `description: str`, `text: str`, `supersedes: Optional[str] = None`, `captured_at: datetime =
  Field(default_factory=lambda: datetime.now(timezone.utc))`, `source: str = 'scribe capture'`,
  `def to_frontmatter(self) -> str`, `def from_frontmatter(cls, frontmatter: str, *, text:
  str='') -> 'CaptureRecord'`. [AST:src/pyforge/scribe/models.py:L40]
- `class GraphNode(BaseModel)` — One compiled knowledge-graph fact (Story 2.1/2.2, AD-1/AD-5):
  `id: str`, `kind: GraphNodeKind`, `title: str`, `text: str`, `citation: str`, `valid_from:
  datetime`, `valid_until: Optional[datetime] = None`, `superseded_by: Optional[str] = None`,
  `stale: bool = False`, `def is_current(self) -> bool`. [AST:src/pyforge/scribe/models.py:L133]

### `recall.py`

- `class RecallAnswer` — One `scribe recall` result: `grounded: bool`, `text: str`, `citation:
  str | None`, `node_id: str | None`. [AST:src/pyforge/scribe/recall.py:L119]
