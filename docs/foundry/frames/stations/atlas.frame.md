---
type: frame
identifier: pyforge/atlas
license: https://www.apache.org/licenses/LICENSE-2.0
name: PyForge Atlas
description: Station Frame for Atlas — Kedro/Dagster/DuckDB factory intelligence. Load when running atlas pipelines, listing catalog datasets, or reading the atlas MCP surface.
visibility: private
version: 0.1.0
scope: station
maintainer:
  - atlas
inherits:
  - pyforge/company
---

# Atlas

- Grammar: `pyforge atlas …` and `POST /stations/atlas/mcp`. Do not import `pyforge.atlas` internals.
- Provides data; Warden consumes it. Does not replace `conda-forge-expert` or `cf-atlas-legacy`.
- Run from repo root. Unknown MCP pipeline names fail closed.
- Dashboard structural checks stay advisory measurement unless a named gate already owns them.
