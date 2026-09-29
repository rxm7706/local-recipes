---
name: bmad-sprint-ledger-query
description: "Pluggable, extensible, hookable, feature-flagged Sprint Ledger Query & Telemetry Reporting engine across all eight PyForge stations."
---

# BMAD Skill: Sprint Ledger Query & Telemetry (`bmad-sprint-ledger-query`)

Query, inspect, audit, and export estate sprint ledgers -- each station's TRACKED `planning-artifacts/sprint-status-ledger.yaml` and `epics.md` -- across all eight PyForge stations (`pyforge-steward`, `pyforge-marshal`, `pyforge-scribe`, `pyforge-herald`, `pyforge-atlas`, `pyforge-doctor`, `pyforge-warden`, `pyforge-mason`). This skill wraps the `steward ledger-query` duty; it re-implements nothing. Counts agree with `fleet_scan.parse_sprint_status` (the reader of record); `fleet-picture`, `story-status` and the doctor detectors stay authoritative -- this is a query/export surface, never a second verdict.

## Quick Invocations

```bash
# 1. Summary of estate completion (per-station done / backlog / blocked)
pixi run -e pyforge-guild sprint-ledger-query -- --format summary

# 2. Table view of unimplemented stories (status != done)
pixi run -e pyforge-guild sprint-ledger-query -- --unimplemented --format table

# 3. 3-Way Sync Matrix (Ledger ↔ Jira ↔ GitHub) to detect unlinked stories -- flag-gated
pixi run -e pyforge-guild sprint-ledger-query -- --unlinked --format sync-matrix --flag enable_jira_github_matrix=true

# 4. JSON for bmad-dashboard, written to a path YOU choose (stdout stays empty; confirmation on stderr)
pixi run -e pyforge-guild sprint-ledger-query -- --format json --output /tmp/ledger-query.json

# 5. Steward-shaped records payload for PyForge Atlas -- flag-gated; Atlas declares its own catalog entry
pixi run -e pyforge-guild sprint-ledger-query -- --format atlas-dataset --flag enable_vizro_dataset=true

# 6. Herald facts-ledger YAML (deck/persona/derived_at/tree/facts[...]) -- flag-gated
pixi run -e pyforge-guild sprint-ledger-query -- --format herald-facts --flag enable_herald_facts=true

# 7. Self-contained HTML dossier -- flag-gated
pixi run -e pyforge-guild sprint-ledger-query -- --format static-dossier --flag enable_dossier_export=true --output /tmp/dossier.html

# 8. Mint Work Passport UUIDs and sync to PostgreSQL -- flag-gated; needs django (see below)
pixi run -e pyforge-steward sprint-ledger-postgres-sync -- --flag enable_postgres_sync=true
```

Filters compose: `--station <dir under _bmad-output/projects/>`, `--status a,b` (known: backlog, in-progress, done, blocked, optional, in-review, review, ready-for-dev, ready), `--unimplemented` (status != done), `--unlinked` (missing Jira key or GitHub item id), `--epic ID` (one epic within the scanned stations), `--search TERM` (title / story id / Jira key), `--ready` (`next == ready`, exactly `get_runnable_backlog()`'s predicate), `--running` (`next == running`, a live dispatch or loop run confirmed on that story's station). An unknown station or status is refused naming the known set.

## The `next` field -- done / running / ready / waits-on / blocked / ? (Story 65.2, CAP-150)

Every story the engine returns carries `next`: `done`, `running` (a live dispatch or loop run is on this story's station), `ready` (backlog, every declared dep `done` -- `get_runnable_backlog()`'s own predicate), `waits on 1.2[, …]` (bare canonical dep keys, never an `S-` prefix, naming the unmet deps), `blocked`, `?` (the running fact was unavailable), or the ledger's own status verbatim for anything outside this enum (e.g. `in-review`, or an `in-progress` story marshal did not corroborate -- a literal ledger status of `ready` or `in-progress` is one such passthrough, never conflated with the computed value: `--ready`/`--running` and the `next_ready`/`next_running` counts always pair the string with its owning status, `backlog`/`in-progress`). `table`, `markdown` and `json` all carry it; `summary` adds per-station `ready N, running N` counts.

The `running` fact comes from ONE `marshal watch --fleet --format json` call per query (through `pyforge.core.process`, never a `pyforge.marshal` import, never a read of marshal's journal) and is **this checkout's own** -- marshal's Tier-3 run state is per clone, so two worktrees can disagree. When `marshal` is absent or the call fails, every `next` that would read `running` instead reads `?`, with one warning; every other column and the exit code are unaffected (fail-open, never a gate).

## No cross-station writes by default

No formatter writes into another station's tree (`presentations/`, `_bmad-output/projects/pyforge-atlas/`, `docs/dashboard/`). The payload goes to stdout, or to the one path you pass with `--output PATH` -- and then ONLY to that file: stdout is empty and one confirmation line goes to stderr, so a machine consumer never sees a mixed stream. A write failure returns a non-zero exit. When a Herald / Atlas consumer story declares a target path, pass it explicitly.

## Feature flags

Every optional integration sits behind a flag (default OFF); asking for a gated formatter or action with its flag off exits 1 with `flag <name> is off (set FLAGS_<NAME>=true, flags.json, or --flag <name>=true)` and writes nothing.

| Flag | Gates |
|---|---|
| `enable_jira_github_matrix` | `--format sync-matrix`, `jira-csv`, `github-json` |
| `enable_herald_facts` | `--format herald-facts` |
| `enable_vizro_dataset` | `--format atlas-dataset` |
| `enable_dossier_export` | `--format static-dossier` |
| `enable_postgres_sync` | `--sync-postgres` |

Resolution order (`eval_flag()`; no OpenFeature SDK -- file / env / CLI only): (1) `--flag name=value` (repeatable; `true/1/yes/on` and `false/0/no/off` are coerced), (2) `FLAGS_<NAME>` in the environment (an empty value counts as unset), (3) `<repo-root>/.steward/flags.json` -- entries are bare values or `{"state": "ENABLED"|"DISABLED", "value": ...}`, `DISABLED` is false regardless of `value`, (4) the default. `markdown`, `summary`, `json` and `table` are never gated.

## `--sync-postgres`

Requires the `pyforge-steward[dashboard]` extra with configured Django settings (`DJANGO_SETTINGS_MODULE`), which is why the `sprint-ledger-postgres-sync` pixi task lives in the `pyforge-steward` feature (invocation 8) and not in `guild-tasks`: no env carrying `guild-tasks` (`pyforge-guild`, `default`, `local-recipes`) has django, so there it could only ever refuse. The sync result (`success` / `refused` / `fallback_payload` / `error`) goes to stderr and `DutyResult.details["sync"]`, never stdout; anything but `success` exits 1. Aliases entered in the admin (`jira_key`, `github_item_id`) survive a sync that carries none.

## Available Formatters

- `markdown`: Human-readable Markdown report with summary table and story list.
- `summary`: Estate line plus one line per station (done / backlog / blocked / in-progress / optional / ready / running).
- `json`: Machine-readable JSON conforming to `$id: urn:local-recipes:pyforge-steward:sprint-ledger-query-schema` (shipped as `pyforge/steward/data/sprint-ledger-query.schema.json`).
- `table`: ASCII formatted grid table.
- `sync-matrix`: 3-way alignment table comparing Ledger ↔ Jira ↔ GitHub statuses. *(flag-gated)*
- `herald-facts`: Herald's facts-ledger YAML shape -- `deck` / `persona` / `derived_at` / `tree` / `facts[{id, value, source, method, shown_as}]`. *(flag-gated)*
- `atlas-dataset`: Steward-shaped records JSON for Atlas's Vizro connector; claims no Atlas catalog dataset name (steward exports, Atlas renders). *(flag-gated)*
- `static-dossier`: Self-contained HTML dossier (every field HTML-escaped). *(flag-gated)*
- `jira-csv`: Bulk import CSV format for Jira Cloud. *(flag-gated)*
- `github-json`: GraphQL item payload format for GitHub Projects V2. *(flag-gated)*

## Python Engine API

```python
from pyforge.steward.sprint_ledger_query import SprintLedgerQueryEngine, get_runnable_backlog

engine = SprintLedgerQueryEngine()          # root defaults to the repo root, never cwd

# Query unimplemented stories for a station (a pre_query hook may mutate the filters)
result = engine.query(station="pyforge-steward", unimplemented_only=True)

# Export as JSON (library API is ungated; the CLI duty applies the flags)
json_output = engine.export(result, format_name="json")

# Select runnable backlog stories for PyForge Marshal dispatch -- marshal's
# Deps grammar (S-46.4 / bare 46.4 / `steward S-32.1 (note)` / the `—`,
# `none`, `n/a` sentinels), done keyed by (station, story_id)
runnable_stories = get_runnable_backlog(engine, station="pyforge-steward")

# `next` is always computed, offline by default (in-progress reads optimistic
# "running", no I/O). Pass resolve_running=True for the corroborated fact --
# ONE `marshal watch --fleet` call, fail-open to "?" -- the CLI duty always
# does this; a bare library caller opts in.
corroborated = engine.query(station="pyforge-steward", resolve_running=True)
[s.next for s in corroborated.stories]

# Plugins: engine.formatters.register(QueryFormatterPlugin), engine.sources.register(LedgerSourcePlugin),
# engine.hooks.register(LedgerQueryHook) -- a duplicate formatter/source name raises ValueError.
```
