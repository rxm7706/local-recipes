---
id: SPEC-sentinel
spec: sentinel
status: archived
archived-reason: absorbed
owner-dream: docs/dreams/sentinel.md
surface: []          # archived — no live surface; see § What carries forward
sources:
  - ../../../../../../docs/dreams/sentinel.md
open_questions: []
---

> **Retirement record.** This Dream is `status: archived` (`absorbed`). Charter §5 requires
> every Dream to carry a Spec, archived included: a retirement record is how the next reader
> learns from the decision instead of rediscovering the idea. It states what was contracted,
> why it ended, and what survives — not a plan for work that will not happen.

# sentinel — retirement record

## Why it was contracted

The ancestor Dream (2026-04-18/19, predating the PyForge model): **Sentinel, the AI
Software Factory.** Its diagnosis — an engineer touches six tools in the first hour, and the
knowledge the team runs on (the *why* of a change, the rejected alternative) lives nowhere
durable.

## Why it ended

**Absorbed 2026-07-25.** The persona's charter passed to the Scribe station
([[pyforge-scribe]]); its knowledge-graph core became [[team-memory]]. The prototype
survives at `src/sentinel/` and is deliberately ungoverned until Scribe absorbs it.

## What carries forward

The diagnosis outlived the design and is now Scribe's mandate. Live residue: `src/sentinel/`
plus `conf/base/knowledge.yml`, both allowlisted rather than spec-governed — a knowing
exception recorded in `scripts/spec_surface_allowlist.txt`.

## Non-goals

- **Reviving this Dream as written.** Its intent was absorbed, delivered or blocked; the
  successor named above is where the work lives now.
- **Treating this record as a backlog item.** Archived Dreams are excluded from the Backlog
  board by design.

## Success signal

A reader arriving at this Dream learns in one page why it stopped and where its intent went,
without re-deriving the decision or re-opening a closed question.
