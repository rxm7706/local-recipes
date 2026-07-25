---
title: Scribe — the inward voice
type: dream
owner: scribe
status: in-spec
---

# Scribe — capture the decision, keep the graph, answer from memory

## The Dream

The Chronicler's dream: **what the team knows, every agent and every session
knows.** Where Herald tells the world, Scribe tells the team — every decision,
rejected tradeoff, and 3am runbook captured as it happens, curated so it stays
true, compiled into a knowledge graph, and answerable on demand. Adopted
2026-07-23 when the ownership audit found the knowledge station unowned — the
exact disease [[sentinel]] diagnosed: *knowledge is lossy; the graph is there;
nobody writes it down.*

## What it owns

- **[[team-memory]]** — the shared `.claude/memory/` layer + `team-memory` skill.
- **[[sentinel]]'s unbuilt core** — the team knowledge graph compiled nightly
  from the tools the team already uses.
- Curation surfaces: the Dreams index, doc/ADR hygiene, wikis (the atlas Wave-H
  Karpathy wiki + agno crews are Scribe-station machinery), the library catalog's
  freshness.

## What is already Scribe-shaped (the capture habit exists)

- The append-only **memlog** discipline (`bmad-spec`'s `.memlog.md` — canonical,
  derived artifacts re-rendered from it).
- The personal auto-memory pipeline (30+ entries, indexed) — the single-operator
  prototype of team memory.
- Dream **realization logs** — decisions recorded where the aspiration lives.

## Realization log

- **2026-07-23** — persona adopted into [[pyforge-charter]] (crew 6 → 8);
  station assignments recorded in team-memory + sentinel. CLI and chapter deck
  await their turns.
- **2026-07-23 (gist audit)** — the Karpathy knowledge-base method (raw/ → LLM-compiled wiki with backlinks) is the Scribe's compile loop, described: `docs/intake/gists/llm-powered-knowledge-bases-by-andrej-karpathy/`.
