---
id: SPEC-artifact-console
spec: artifact-console
status: archived
archived-reason: retired
owner-dream: docs/dreams/artifact-console.md
surface: []          # archived — no live surface; see § What carries forward
sources:
  - ../../../../../../docs/dreams/artifact-console.md
open_questions: []
---

> **Retirement record.** This Dream is `status: archived` (`retired`). Charter §5 requires
> every Dream to carry a Spec, archived included: a retirement record is how the next reader
> learns from the decision instead of rediscovering the idea. It states what was contracted,
> why it ended, and what survives — not a plan for work that will not happen.

# artifact-console — retirement record

## Why it was contracted

One page showing the whole factory at a glance — every project, every story, what shipped
and what is in flight — published as a **claude.ai Artifact**, shareable by link and
updatable conversationally, with no repo, build step or hosting.

## Why it ended

**Retired 2026-07.** Replaced by the GitHub Pages console ([[factory-console]]), which
reaches the same goal from a durable source: state derived from `sprint-status.yaml` and
Dream frontmatter rather than kept current by conversation. The Artifact approach could not
guarantee the derivation — an artifact edited in chat is hand-maintained by construction,
which is exactly the property [[factory-console]] forbids.

## What carries forward

The idea was right and the substrate was wrong. What carries forward: *one page, whole
factory, shareable link* — delivered by `docs/dashboard/` and now gated on attribution
(Charter §7).

## Non-goals

- **Reviving this Dream as written.** Its intent was absorbed, delivered or blocked; the
  successor named above is where the work lives now.
- **Treating this record as a backlog item.** Archived Dreams are excluded from the Backlog
  board by design.

## Success signal

A reader arriving at this Dream learns in one page why it stopped and where its intent went,
without re-deriving the decision or re-opening a closed question.
