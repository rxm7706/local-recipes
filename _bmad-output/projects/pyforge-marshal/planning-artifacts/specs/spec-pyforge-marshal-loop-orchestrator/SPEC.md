---
id: SPEC-pyforge-marshal-loop-orchestrator
spec: pyforge-marshal-loop-orchestrator
status: archived
archived-reason: duplicate
owner-dream: docs/dreams/pyforge-marshal-loop-orchestrator.md
surface: []          # archived — no live surface; see § What carries forward
sources:
  - ../../../../../../docs/dreams/pyforge-marshal-loop-orchestrator.md
open_questions: []
---

> **Retirement record.** This Dream is `status: archived` (`duplicate`). Charter §5 requires
> every Dream to carry a Spec, archived included: a retirement record is how the next reader
> learns from the decision instead of rediscovering the idea. It states what was contracted,
> why it ended, and what survives — not a plan for work that will not happen.

# pyforge-marshal-loop-orchestrator — retirement record

## Why it was contracted

An orchestrator dream for Marshal: provisioned loop homes, deterministic execution,
supervised runs, durable landing, deterministic gates, batch landing — a "loop
orchestrator" framing of hands-off, auditable, deterministic execution of multi-story
workflows.

## Why it ended

**Retired 2026-08-02, same day it was created.** The dream was generated in a bulk commit
(`dad47c408a`) later found to contain fabricated content elsewhere in the same commit
(a migration note with false claims about the dashboard generator, boilerplate
test-architecture.md files duplicated across stations with only nouns swapped). This
dream's own content did not survive scrutiny as new scope: its six-item "Realization"
list maps 1:1 onto capabilities the existing [[pyforge-marshal]] Dream already fully
governs via `spec-pyforge-marshal` — CAP-1 (loop homes and isolation), CAP-2 (supervised
unattended runs), CAP-3 (gates you can run), CAP-4 (landing with a durable paper trail) —
each already carried downstream into a PRD (FR-1..FR-58), an Architecture (39 ADs), and
Epics (6 epics / 50 stories) whose titles match this dream's list nearly verbatim
("Gates you can run", "Landing with a durable paper trail", "Supervised unattended runs").
The dream's own Acceptance section names "all 6 epics (50 stories)" as its completion
criterion — the pre-existing epics, not new ones it proposes. There was no new capability
here to specify; authoring a second Spec for the same surface would have created a
competing, driftable contract for scope already under governance.

## What carries forward

Nothing new — the intent this dream restates already lives in [[pyforge-marshal]] and
`spec-pyforge-marshal`. That is the canonical contract for Marshal's loop-orchestration
capability; this record exists only so a future reader does not re-derive the "is this
new scope?" question from scratch.

## Non-goals

- **Reviving this Dream as written.** Its intent was never separate from
  `spec-pyforge-marshal`'s; there is nothing here to revive.
- **Treating this record as a backlog item.** Archived Dreams are excluded from the
  Backlog board by design.
- **Taking this Dream's content as evidence of anything about Marshal's real state.**
  It was generated, not authored from firsthand investigation — treat every claim in it
  the way the 2026-07-31 audit lesson in [[pyforge-marshal]] recorded: "a premise handed
  to an agent is not evidence."

## Success signal

A reader arriving at this Dream learns in one page why it stopped and where its intent
went, without re-deriving the duplication or mistaking it for a second contract.
