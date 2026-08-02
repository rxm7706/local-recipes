---
id: SPEC-pyforge-atlas-intelligence-platform
spec: pyforge-atlas-intelligence-platform
status: archived
archived-reason: duplicate
owner-dream: docs/dreams/pyforge-atlas-intelligence-platform.md
surface: []          # archived — no live surface; see § What carries forward
sources:
  - ../../../../../../docs/dreams/pyforge-atlas-intelligence-platform.md
open_questions: []
---

> **Retirement record.** This Dream is `status: archived` (`duplicate`). Charter §5 requires
> every Dream to carry a Spec, archived included: a retirement record is how the next reader
> learns from the decision instead of rediscovering the idea. It states what was contracted,
> why it ended, and what survives — not a plan for work that will not happen.

# pyforge-atlas-intelligence-platform — retirement record

## Why it was contracted

A vision for Atlas as the factory's intelligence backbone: a discovery engine (8-signal
trending-candidate classifier), a schema evolution layer, a Kedro/Dagster phase orchestrator,
DuckDB-backed analytics, a determinism contract, and air-gap deployability.

## Why it ended

**Retired 2026-08-02, same day it was created.** The dream was generated in a bulk commit
(`dad47c408a`) later found to contain fabricated content elsewhere in the same commit (a
false sprint-status-ledger migration note, boilerplate `test-architecture.md` files
duplicated across six stations, and two sibling duplicate dreams —
`pyforge-marshal-loop-orchestrator` and `pyforge-mason-recipe-validator` — both retired the
same way earlier this session). This dream's content does not survive scrutiny as new scope:
every item in its "Realization" list is already shipped, not proposed, by
[[pyforge-atlas]]'s real 38-story, 11-wave chain — Phase Orchestrator maps to Wave C
("Integrate kedro-dagster for scheduling + execution"); DuckDB Analytics maps to Wave F
Story F1, verbatim ("DuckDB consolidation + prove the cold-start claim"); Discovery Engine
and Schema Evolution map to Wave B/H's pipeline porting and Wave I's post-audit schema
truth-up; air-gap capability is already implemented repo-wide via the `<HOST>_BASE_URL`
redirect pattern (`project-context.md` § Air-Gapped / Enterprise). Its own "Acceptance"
section names criteria already met — "all 15 phases ported," "schema v29→v30 migration
tested," "dashboards consuming cf_atlas data live" — describing a station that is, as of
this session, 100% code-complete (38/38 stories), carries 930 real collected tests, and has
a delivered retro. There was no new capability here to specify.

## What carries forward

Nothing new — the intent this dream restates already lives in [[pyforge-atlas]] and its
shipped chain. That is the canonical contract for Atlas's intelligence-platform capability;
this record exists only so a future reader does not re-derive the "is this new scope?"
question from scratch.

## Non-goals

- **Reviving this Dream as written.** Its intent was never separate from
  `pyforge-atlas`'s already-shipped scope; there is nothing here to revive.
- **Treating this record as a backlog item.** Archived Dreams are excluded from the
  Backlog board by design.
- **Taking this Dream's content as evidence of anything about Atlas's real state.** It was
  generated, not authored from firsthand investigation of the shipped code — same lesson as
  `pyforge-marshal`'s 2026-07-31 audit finding: "a premise handed to an agent is not
  evidence."

## Success signal

A reader arriving at this Dream learns in one page why it stopped and where its intent
went, without re-deriving the duplication or mistaking it for a second contract on a
station that is already done.
