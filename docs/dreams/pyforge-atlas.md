---
title: Atlas — the map that maintains itself
type: dream
owner: atlas
status: realized
---

# Atlas — the intelligence layer an agent workforce can maintain

## The Dream

The Navigator's dream: **chart the dependencies, map the world, define the
floor** — and make the map maintainable by agents, not heroes. The original
cf_atlas was a ~10,000-line hand-rolled orchestrator: 23 phases whose data
lineage lived in one developer's head. The dream was its rebirth as declarative
dataflow — a DAG small enough, pure enough, and contract-guarded enough that an
autonomous agent can add phase 24 without hand-wiring a single checkpoint.

## What is real

- **Kedro + Dagster + DuckDB** migration SHIPPED: waves 0 + A–H, all 32 stories,
  PRs #58–#105, driven end-to-end by bmad-loop ([[pyforge-marshal]]) — spec
  `cfe-atlas-datapipeline-kedro-migration.md`, shipped 2026-07-18 (CFE v8.79.0).
- Boring Semantic Layer models, the Vizro dashboard (28 CLIs → pages), Vizro-AI
  NL interface as an MCP tool, A2A interfaces, OpenLineage + OTel, DuckDB VSS,
  Pyodide/WASM compilation, Dagster sensors, and the Wave-H agno wiki crews.
- The intelligence signals that feed [[packaging-factory]]: staleness,
  feedstock-health, CVE watch, release cadence, adoption, velocity, readiness.

## Lineage

Atlas's stack is a direct descendant of [[sentinel]] (§19 Kedro · §20 Dagster ·
§27 BSL · §24 OTel/OpenLineage · §26 La Suite) — the ancestor dreamed the stack;
Atlas built it against the conda-forge domain. It also realized two 2026-04-25
roadmap wishes: the unified DAG orchestrator and the interactive dashboard.

## Remaining

- The 8 per-epic retrospectives (marked optional in sprint-status).
- The 2026-07-19 artifact-truncation incident is reconciled (2026-07-23) — on
  resume, trust only canonical hyphenated files; see the fork README in the
  project dir.

## Realization log

- **2026-06-20 → 07-16** — spec authored and analyzed (v5.6).
- **2026-07-17 → 07-18** — planned and BUILT via bmad-loop; shipped.
- **2026-07-23** — Dream retro-seeded; chapter deck `presentations/pyforge-atlas/`.
- **2026-07-23 (gist audit)** — grounding: the Ecosystem Health Report v2 (Basilisk §6) is atlas-intelligence output (`docs/intake/gists/conda-forge-python-ecosystem-health-report-v2-…/`); LF AI & Data landscape kept as reference.
