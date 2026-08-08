---
title: Scribe — the inward voice
type: dream
owner: scribe
status: realized
---

# Scribe — capture the decision, keep the graph, answer from memory

## The Dream

The Chronicler's dream: **what the team knows, every agent and every session
knows.** Where Herald tells the world, Scribe tells the team — every decision,
rejected tradeoff, and 3am runbook captured as it happens, curated so it stays
true, compiled into a knowledge graph, and answerable on demand. Adopted
2026-07-23 when the ownership audit found the knowledge station unowned — the
exact disease [[sentinel]] diagnosed in 2026-04: *knowledge is lossy; the
graph is there; nobody writes it down.*

## What it owns

- **Team memory** — the shared, version-controlled `.claude/memory/` layer and
  the `scribe capture` / `scribe capture --promote` workflow that fills it.
  [[team-memory]]'s own Dream (its Spec: MEM-1 committed-not-personal, MEM-2
  scoped recall, MEM-3 entries-carry-provenance) and the legacy 10-story
  `claude-team-memory` spec it pointed to are both fully folded into this
  Dream and `spec-pyforge-scribe` — there is no separate team-memory scope
  left to track outside this file.
- **[[sentinel]]'s unbuilt core** — the team knowledge graph, compiled nightly
  from the tools the team already uses (git history, memlogs, retros,
  CHANGELOGs, `docs/dreams/`) and queryable via `scribe recall`. This is Wave
  2 and has not started.
- Curation surfaces Scribe is scoped to grow into once the graph exists: the
  Dreams index, doc/ADR hygiene, wikis (the atlas Wave-H Karpathy wiki +
  agno crews are Scribe-station machinery), the library catalog's freshness.

## What it looks like when real

- `scribe capture` records a decision the moment it happens, straight into
  `.claude/memory/`; `scribe capture --promote` scans a contributor's
  personal auto-memory, proposes which entries are team-relevant ("would a
  day-1 contributor benefit from this rule?"), rewrites them in team voice,
  and never silently promotes — every promotion is proposed, then confirmed.
- Recall is scoped, not a dump: a session asks `scribe recall "why did we
  drop Kùzu?"` and gets one grounded, cited answer, not the whole store — the
  same answer for any operator or concurrent agent worktree, since the
  compiled graph is the single shared source, never per-session state.
- Nothing is fabricated: every `recall` response carries a citation
  resolvable to a real file or commit, or an explicit "no grounded answer
  found." A superseding capture invalidates a prior record rather than
  deleting it, so history survives — every graph node traces back to the
  source file or commit that produced it, and a stale entry stays visibly,
  not silently, stale.
- Air-gapped by construction: capture, compile, and recall make zero
  outbound network calls by default.

## What is real

Package scaffolded at `src/shared/packages/pyforge-scribe/` (CLI `scribe`,
module `pyforge.scribe`). Epic 1 (Team Memory — Capture & Promotion) is 3 of
5 stories done: 1.1 package scaffold + direct `scribe capture` into
`.claude/memory/`, 1.2 the `CLAUDE.md` `@import` wiring that puts team memory
in every session's context, 1.3 the `scribe capture --promote`
proposal-then-confirm workflow with team-voice rewrite. 1.4 (pointer-stub
write-back + idempotent re-invocation) and 1.5 (seed-promoting the two real
BMAD↔CFE feedback entries by invoking the tool itself, not by hand) are still
backlog. Epic 2 (Knowledge Graph — Compile & Recall) — the `GraphStore` port,
nightly compile, fact supersession, `scribe recall` — is untouched: all 4
stories backlog. 3 of 9 stories complete overall. Spec: `spec-pyforge-scribe`
(CAP-1..CAP-4, AD-1..AD-9). `.claude/memory/` itself is already live in this
repo today — `feedback/`, `project/`, `reference/` subdirectories, a
`MEMORY.md` index, a `README.md` documenting the schema.
