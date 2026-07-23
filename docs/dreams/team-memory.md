---
title: Team memory — what the team knows, the agents know
type: dream
owner: scribe
status: seeded
---

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
  truth; Dreams ([[ecosystem-crew]]) for aspirations; specs for contracts.
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
