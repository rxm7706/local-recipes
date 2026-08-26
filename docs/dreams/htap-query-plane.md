---
title: One HTAP query plane for every station and every agent
type: dream
owner: steward
status: archived
archived-reason: absorbed
---

> **Absorbed 2026-08-26** into
> [`pyforge-unifying-strategy.md`](pyforge-unifying-strategy.md) § *The query
> plane* (Grounding: not a sibling chain). Steward still owns the through-line;
> Atlas still owns the engine. Do not run `bmad-spec` against this file. Bind
> the capability by correct-course on `spec-pyforge-unifying-strategy` when
> the operator is ready — this capture does not mint a CAP by existing.

# One HTAP query plane for every station and every agent

## The Dream

The narrative lives on the Unifying Strategy. In one line: PyForge already
unified chrome, identity, CLI, and the event bus; it had not unified where a
question goes. One DuckDB HTAP plane (live read-only Postgres attach, Parquet
cache, `vss` vectors) is the canopy data contract. Stations reimplement onto
it. Agents do not get the OLTP DSN.

## Realization log

- **2026-08-26** — Captured as a standalone Dream, then absorbed the same
  day (operator: add it to the Unifying Strategy). Full text is the parent
  section, not a second chain.
