---
id: SPEC-microsoft-org-sweep
spec: microsoft-org-sweep
status: archived
archived-reason: absorbed
owner-dream: docs/dreams/microsoft-org-sweep.md
surface: []          # archived — no live surface; see § What carries forward
sources:
  - ../../../../../../docs/dreams/microsoft-org-sweep.md
open_questions: []
---

> **Retirement record.** This Dream is `status: archived` (`absorbed`). Charter §5 requires
> every Dream to carry a Spec, archived included: a retirement record is how the next reader
> learns from the decision instead of rediscovering the idea. It states what was contracted,
> why it ended, and what survives — not a plan for work that will not happen.

# microsoft-org-sweep — retirement record

## Why it was contracted

Take one high-value upstream org — `github.com/microsoft/*` — walk every repo it
publishes, and answer exhaustively: **what is missing from conda-forge that ought to be
there?** A systematic sweep, not a hand-picked wishlist.

## Why it ended

**Absorbed 2026-06** into the upstream-discovery surface ([[upstream-discovery]],
`spec-upstream-discovery`), where the org-audit shape became one of two tracks over a
shared classifier rather than a one-off sweep frozen at a June 2026 snapshot.

## What carries forward

~10–14 candidate recipes across 3 waves were identified and are recorded in
`spec-upstream-discovery`'s `org-audit-precedent.md`. **Re-verify with `lookup_feedstock`
before treating that list as live** — candidates ship independently.

## Non-goals

- **Reviving this Dream as written.** Its intent was absorbed, delivered or blocked; the
  successor named above is where the work lives now.
- **Treating this record as a backlog item.** Archived Dreams are excluded from the Backlog
  board by design.

## Success signal

A reader arriving at this Dream learns in one page why it stopped and where its intent went,
without re-deriving the decision or re-opening a closed question.
