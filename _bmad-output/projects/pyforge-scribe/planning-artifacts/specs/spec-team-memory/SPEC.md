---
id: SPEC-team-memory
spec: team-memory
status: archived
archived-reason: absorbed
owner-dream: docs/dreams/team-memory.md
surface: []          # archived — no live surface; see § What carries forward
sources:
  - ../../../../../../docs/dreams/team-memory.md
open_questions: []
---

> **Retirement record.** This Dream is `status: archived` (`absorbed`). Charter §5 requires
> every Dream to carry a Spec, archived included: a retirement record is how the next reader
> learns from the decision instead of rediscovering the idea. It states what was contracted,
> why it ended, and what survives — not a plan for work that will not happen.

# team-memory — retirement record

## Why it was contracted

A shared, version-controlled memory layer for the whole team: today's memory is personal —
each operator's Claude Code auto-memory lives outside the repo, invisible to teammates and to
other agents. This Dream proposed `.claude/memory/` in the repo itself, where corrections,
conventions, and hard-won context accumulate as team property, so any agent, any operator, any
session starts already knowing what the team knows. Its Spec contracted three capabilities —
**MEM-1** (memory is committed, not personal: an entry one operator writes is present for
every other operator and agent on the next clone), **MEM-2** (recall is scoped, not a dump: a
session surfaces the entries relevant to its task, not the whole store), **MEM-3** (entries
carry provenance: every entry records when it was written and what it was learned from, so a
stale one is visibly stale) — and named the legacy 10-waved-story `docs/specs/claude-team-memory.md`
spec as its unstarted implementation. Inherited from [[sentinel]]'s knowledge-graph core when
that Dream was absorbed 2026-07-25.

## Why it ended

**Consolidated 2026-08-02.** This Dream and Scribe's constitutive Dream
(`docs/dreams/pyforge-scribe.md`) were tracked as two separate active Dreams under the same
owner for the same surface — the exact split the 2026-08-02 consolidation pass exists to
close. team-memory's legacy 10-story spec was already absorbed as Scribe's Wave 1 foundation
back on 2026-07-25 (`spec-pyforge-scribe`'s own Why section: "fully absorbs the
validated-but-unstarted legacy `claude-team-memory` spec ... as its Wave 1 foundation"), and
Epic 1 ("Team Memory — Capture & Promotion") already carries its full 10-story scope reshaped
into 5 stories (1.1–1.5) — 3 of which are shipped as of this consolidation (1.1 package
scaffold + direct capture, 1.2 `CLAUDE.md` wiring, 1.3 promotion workflow). What remained
outstanding was this Dream's own MEM-1/MEM-2/MEM-3 framing, checked against `spec-pyforge-scribe`
capability-by-capability rather than assumed identical:

- **MEM-1** (committed, not personal) — covered by CAP-1 (`scribe capture` writes into
  `.claude/memory/`, git-tracked) and AD-1 (append-only, capture is the only mutation path).
- **MEM-2** (recall is scoped, not a dump) — covered by CAP-3 (`scribe recall <query>` returns
  one grounded, cited answer to a specific query, not the whole graph) and the pre-existing
  `MEMORY.md` 200-line-index convention (FR-2), which is itself already a scoping mechanism.
- **MEM-3** (entries carry provenance, so a stale one is visibly stale) — no exact match, but
  substantially covered: CAP-2's success criterion requires "every node is traceable to its
  source file/commit" (git-native provenance, stronger than a hand-maintained date field), and
  the Non-goals explicitly reserve a compile-time staleness signal ("Scribe may surface a
  staleness signal at compile time but never auto-deletes") without committing to
  entry-level auto-scoring, which this Dream never asked for either.

No capability here was genuinely absent from `spec-pyforge-scribe` — the distinguishing
nuance in MEM-2's "scoped, not a dump" and MEM-3's "provenance/staleness" framing was folded
into the fresh `docs/dreams/pyforge-scribe.md`'s "What it looks like when real" section so the
emphasis is not lost, but no new capability ID was needed. This is a different finding from
this session's other Scribe retirement (`spec-pyforge-scribe-team-memory`, `duplicate`): that
dream was a same-day fabrication restating existing scope with nothing new to carry; this one
is the genuine, pre-existing seed that Scribe's Wave 1 was already built from — its content is
absorbed, not discarded as spurious.

## What carries forward

Epic 1 is real and 3/5 stories shipped; `.claude/memory/` is live in this repo today
(`feedback/`, `project/`, `reference/`, `MEMORY.md`, `README.md`). `spec-pyforge-scribe`
(CAP-1..CAP-4, AD-1..AD-9) is the sole canonical contract for this surface going forward — the
MEM-1/MEM-2/MEM-3 vocabulary itself does not carry forward as separate identifiers, since each
maps onto an existing CAP/AD/FR one-to-one (see above) and duplicating the ID space would
create two names for one thing.

## Non-goals

- **Reviving this Dream as written.** Its intent was absorbed; the successor named above is
  where the work — and the remaining Epic 1/Epic 2 backlog — lives now.
- **Treating this record as a backlog item.** Archived Dreams are excluded from the Backlog
  board by design.
- **Minting new capability IDs for MEM-1/MEM-2/MEM-3.** Each already has a home in
  `spec-pyforge-scribe`'s CAP/AD/FR space (see § Why it ended); re-deriving them as new
  requirements would duplicate, not add, contract.

## Success signal

A reader arriving at this Dream learns in one page why it stopped, which capability in
`spec-pyforge-scribe` each of its three MEM items maps to, and where the remaining real work
(Epic 1 Stories 1.4–1.5, all of Epic 2) actually lives — without re-deriving the "is this
still separate scope?" question from scratch.
