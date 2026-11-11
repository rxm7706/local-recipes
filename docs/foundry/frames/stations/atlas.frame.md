---
type: frame
identifier: pyforge/atlas
license: https://www.apache.org/licenses/LICENSE-2.0
name: PyForge Atlas
description: Station Frame for Atlas — Kedro/Dagster/DuckDB factory intelligence. Load when running atlas pipelines, listing catalog datasets, or reading the atlas MCP surface.
visibility: private
version: 0.2.0
scope: station
maintainer:
  - atlas
inherits:
  - pyforge/company
---

# Atlas

- Seed: `docs/dreams/pyforge-atlas.md`
- Seed: `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/.memlog.md`
- Derived: `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md`, `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/contract.md`
- Grammar: `pyforge atlas …` and `POST /stations/atlas/mcp`. Do not import `pyforge.atlas` internals.
- Run from repo root under `-e pyforge-atlas`. The data root, flag keys, exit domain and MCP tools are the ones `contract.md` lists. Unknown MCP pipeline names fail closed.
- Provides data; Warden consumes it. Does not replace `conda-forge-expert`.
- Dashboard structural checks stay advisory measurement unless a named gate already owns them.
