---
id: SPEC-copilot-cli-packaging
spec: copilot-cli-packaging
status: archived
archived-reason: blocked
owner-dream: docs/dreams/copilot-cli-packaging.md
surface: []          # archived — no live surface; see § What carries forward
sources:
  - ../../../../../../docs/dreams/copilot-cli-packaging.md
open_questions: []
---

> **Retirement record.** This Dream is `status: archived` (`blocked`). Charter §5 requires
> every Dream to carry a Spec, archived included: a retirement record is how the next reader
> learns from the decision instead of rediscovering the idea. It states what was contracted,
> why it ended, and what survives — not a plan for work that will not happen.

# copilot-cli-packaging — retirement record

## Why it was contracted

Package GitHub's **Copilot CLI** for conda-forge, so the agent tooling the factory itself
leans on installs the same way everything else does.

## Why it ended

**Blocked, not abandoned.** staged-recipes #32522 was rejected on the **LICENSE.md §2
redistribution clause** — a legal constraint, not a technical one. No amount of recipe work
resolves it; the upstream terms forbid the redistribution conda-forge requires.

## What carries forward

Reopen only if upstream relicenses. The recipe work itself was sound and is recoverable
from the PR. Recorded so the next person does not re-derive the same rejection.

## Non-goals

- **Reviving this Dream as written.** Its intent was absorbed, delivered or blocked; the
  successor named above is where the work lives now.
- **Treating this record as a backlog item.** Archived Dreams are excluded from the Backlog
  board by design.

## Success signal

A reader arriving at this Dream learns in one page why it stopped and where its intent went,
without re-deriving the decision or re-opening a closed question.
