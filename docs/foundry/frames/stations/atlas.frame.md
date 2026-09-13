---
type: frame [0.2]
name: pyforge-atlas
description: Station Frame for Atlas — Kedro/Dagster/DuckDB factory intelligence. Load when running atlas pipelines, listing catalog datasets, or reading the atlas MCP surface.
visibility: private
owner: atlas
version: 0.1.0
scope: station
inherits: pyforge
---

# Atlas

- Grammar: `pyforge atlas …` and `POST /stations/atlas/mcp`. Do not import `pyforge.atlas` internals.
- Provides data; Warden consumes it. Does not replace `conda-forge-expert` or `cf-atlas-legacy`.
- Run from repo root. Unknown MCP pipeline names fail closed.
- Dashboard structural checks stay advisory measurement unless a named gate already owns them.
