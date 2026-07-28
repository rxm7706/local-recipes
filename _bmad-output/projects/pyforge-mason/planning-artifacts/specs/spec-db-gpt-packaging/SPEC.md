---
id: SPEC-db-gpt-packaging
spec: db-gpt-packaging
status: archived
archived-reason: terminal
owner-dream: docs/dreams/db-gpt-packaging.md
surface: []          # archived — no live surface; see § What carries forward
sources:
  - ../../../../../../docs/dreams/db-gpt-packaging.md
open_questions: []
---

> **Retirement record.** This Dream is `status: archived` (`terminal`). Charter §5 requires
> every Dream to carry a Spec, archived included: a retirement record is how the next reader
> learns from the decision instead of rediscovering the idea. It states what was contracted,
> why it ended, and what survives — not a plan for work that will not happen.

# db-gpt-packaging — retirement record

## Why it was contracted

Get **DB-GPT** — an agentic data-application framework with a large native dependency
closure — installable from conda-forge, along with the five prerequisites nobody had
packaged.

## Why it ended

**Terminal (delivered) 2026-07-01.** All five prerequisites merged; db-gpt itself landed
via external PR #33883 under the consume-not-submit convention. The local mirror at
`recipes/db-gpt/` reflects that PR.

## What carries forward

Closed by delivery, not abandonment. The five prerequisite recipes are the durable
outcome — each is now available to any downstream packaging effort.

## Non-goals

- **Reviving this Dream as written.** Its intent was absorbed, delivered or blocked; the
  successor named above is where the work lives now.
- **Treating this record as a backlog item.** Archived Dreams are excluded from the Backlog
  board by design.

## Success signal

A reader arriving at this Dream learns in one page why it stopped and where its intent went,
without re-deriving the decision or re-opening a closed question.
