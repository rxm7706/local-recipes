---
spec: htap-query-plane
status: archived
archived-reason: absorbed
owner-dream: docs/dreams/htap-query-plane.md
surface: []          # archived — no live surface; see § What carries forward
sources:
  - ../../../../../../docs/dreams/htap-query-plane.md
open_questions: []
---

> **Retirement record.** This Dream is `status: archived` (`absorbed`). Charter §5 requires
> every Dream to carry a Spec, archived included: a retirement record is how the next reader
> learns from the decision instead of rediscovering the idea. It states what was contracted,
> why it ended, and what survives — not a plan for work that will not happen.

# htap-query-plane — retirement record

## Why it was contracted

One hybrid transactional / analytical query plane for every station and every
agent: DuckDB as the only analytical engine (live read-only Postgres attach,
Parquet cache, `vss` vectors), Kedro as the only writer of derived layers,
stations and agents as clients, no OLTP DSN for agent SQL. The Canopy had
unified chrome, identity, CLI, and the event bus; it had not unified where a
question goes.

## Why it ended

**Absorbed 2026-08-26, the same day it was captured.** The operator ruled it
is not a sibling chain: the query plane is `docs/dreams/pyforge-unifying-strategy.md`
Grounding + § *The query plane*. Steward still owns the through-line; Atlas
still owns the engine. A second Dream → Spec → CAP program would mint
`pyforge-htap` and split the canopy contract.

## What carries forward

The capture file stays as a pointer. Binding a capability is a later
`bmad-correct-course` on `spec-pyforge-unifying-strategy` — that pass mints
the CAP and open questions. This record does **not** mint one.

## Non-goals

- **Running `bmad-spec` against `docs/dreams/htap-query-plane.md`.** The
  parent Dream is the contract surface.
- **Treating this record as a backlog item.** Archived Dreams are excluded
  from the Backlog board by design.
- **Silent CAP-19 on the Canopy SPEC.** Closeout 2026-08-26 stamped that
  SPEC `shipped` without a query-plane CAP.

## Success signal

A reader arriving at this Dream learns it is absorbed, where the narrative
lives, and that a future CAP is a correct-course — not a second station.
`dream-chain-check` treats the chain as complete.
