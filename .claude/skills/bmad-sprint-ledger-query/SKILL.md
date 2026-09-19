---
name: bmad-sprint-ledger-query
description: "Pluggable, extensible, hookable, feature-flagged Sprint Ledger Query & Telemetry Reporting engine across all eight PyForge stations."
---

# BMAD Skill: Sprint Ledger Query & Telemetry (`bmad-sprint-ledger-query`)

Query, inspect, audit, and export estate sprint ledgers (`sprint-status-ledger.yaml` & `epics.md`) across all eight PyForge stations (`pyforge-steward`, `pyforge-marshal`, `pyforge-scribe`, `pyforge-herald`, `pyforge-atlas`, `pyforge-doctor`, `pyforge-warden`, `pyforge-mason`).

## Quick Invocations

```bash
# 1. Summary of estate completion
pixi run -e pyforge-guild sprint-ledger-query -- --format summary

# 2. Table view of unimplemented stories (backlog, in-progress, blocked)
pixi run -e pyforge-guild sprint-ledger-query -- --unimplemented --format table

# 3. 3-Way Sync Matrix (Ledger ↔ Jira ↔ GitHub) to detect unlinked stories
pixi run -e pyforge-guild sprint-ledger-query -- --unlinked --format sync-matrix

# 4. Export JSON for bmad-dashboard VS Code Extension / Web
pixi run -e pyforge-guild sprint-ledger-query -- --format json --output _bmad-output/projects/pyforge-steward/data/ledger-query-schema.json

# 5. Export Vizro Dataset for PyForge Atlas
pixi run -e pyforge-guild sprint-ledger-query -- --format atlas-dataset --output _bmad-output/projects/pyforge-atlas/data/sprint_telemetry.json

# 6. Export Herald Facts YAML
pixi run -e pyforge-guild sprint-ledger-query -- --format herald-facts --output presentations/sprint-backlog/facts.yaml

# 7. Mint Work Passport UUIDs and sync to PostgreSQL
pixi run -e pyforge-guild sprint-ledger-postgres-sync
```

## Available Formatters

- `markdown`: Human-readable Markdown report with summary table and story list.
- `summary`: One-line aggregate completion summary.
- `json`: Machine-readable JSON conforming to `$id: urn:local-recipes:pyforge-steward:sprint-ledger-query-schema`.
- `table`: ASCII formatted grid table.
- `sync-matrix`: 3-way alignment table comparing Ledger ↔ Jira ↔ GitHub statuses.
- `herald-facts`: Fact ledger YAML for PyForge Herald presentations.
- `atlas-dataset`: Dataset JSON payload for PyForge Atlas / Vizro dashboards.
- `static-dossier`: Self-contained HTML dossier for GitHub Pages deployment.
- `jira-csv`: Bulk import CSV format for Jira Cloud.
- `github-json`: GraphQL item payload format for GitHub Projects V2.

## Python Engine API

```python
from pyforge.steward.sprint_ledger_query import SprintLedgerQueryEngine, get_runnable_backlog

engine = SprintLedgerQueryEngine()

# Query unimplemented stories for a station
result = engine.query(station="pyforge-steward", unimplemented_only=True)

# Export as JSON
json_output = engine.export(result, format_name="json")

# Select runnable backlog stories for PyForge Marshal dispatch
runnable_stories = get_runnable_backlog(engine, station="pyforge-steward")
```
