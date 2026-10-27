---
title: Team memory — what the team knows, the agents know
type: dream
owner: scribe
status: archived
archived-reason: absorbed
---

> **Superseded.** This Dream carried Scribe's shared, version-controlled
> memory layer as a standalone contract — MEM-1 (memory is committed, not
> personal), MEM-2 (recall is scoped, not a dump), MEM-3 (entries carry
> provenance, so a stale one is visibly stale) — inherited from [[sentinel]]'s
> knowledge-graph core when that Dream was absorbed 2026-07-25.
> [`docs/dreams/pyforge-scribe.md`](pyforge-scribe.md) (status: specified)
> now carries this scope directly: MEM-1 is `spec-pyforge-scribe`'s CAP-1
> (`scribe capture` / `--promote` into `.claude/memory/`) plus AD-1
> (append-only, git-committed); MEM-2 is CAP-3's grounded, cited `scribe
> recall <query>`; MEM-3 is CAP-2's per-node source/commit traceability plus
> the Non-goals' compile-time staleness signal. The legacy 10-story
> `docs/specs/claude-team-memory.md` spec this Dream pointed to was already
> absorbed as Scribe's Wave 1 foundation on 2026-07-25; Epic 1 is now 3 of 5
> stories shipped (1.1 package scaffold + capture, 1.2 `CLAUDE.md` wiring,
> 1.3 promotion workflow) and `.claude/memory/` is live in this repo today.
> Consolidated into one Dream 2026-08-02 rather than left as a second live
> contract for the same surface. See `spec-team-memory` for the retirement
> record.

# Team memory — memory that belongs to the team, not one session

**Owning station: the Scribe** ([[pyforge-scribe]], adopted 2026-07-23).

## The Dream

Today's memory is personal: each operator's auto-memory lives outside the repo,
invisible to teammates and to other agents. The dream is a **shared,
version-controlled memory layer** — `.claude/memory/` in the repo itself — where
corrections, conventions, and hard-won context accumulate as team property: any
agent, any operator, any session starts already knowing what the team knows.

## What it looks like when real

- A `.claude/memory/` tree + a `team-memory` skill governing recall, writes,
  dedup, and hygiene (10 waved stories in the spec).
- Clean division: personal memory for personal preference; team memory for team
  truth; Dreams ([[pyforge-charter]]) for aspirations; specs for contracts.
- The distillation pipeline (retros, CHANGELOG, memories) feeding one shared
  brain instead of per-operator silos — the practical antidote to the
  "knowledge is lossy" problem [[sentinel]] diagnosed.

## What is real

- Spec ready: `docs/specs/claude-team-memory.md` (10 waved stories, unstarted).
- The *personal* pipeline it generalizes is mature: 30+ auto-memory entries,
  MEMORY.md indexing, retro discipline.

## Realization log

- **2026-07** — spec authored (ready).
- **2026-07-23** — Dream retro-seeded. Kinship: [[sentinel]] dreamed the team
  knowledge graph at product scale; team-memory is the pragmatic first organ.
