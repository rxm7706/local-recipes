---
title: One owner for “where is this symbol?”
type: dream
owner: scribe
status: specified
---

# One owner for “where is this symbol?”

## The Dream

Agents ask structure questions and get two answers: Scribe `code:`
AST nodes and Marshal `codegraph.db`. That split wastes tokens and
will copy into python-foundry if we move the tree first.

The Dream is **one navigation owner**. Marshal codegraph answers
symbols. Graphify `code:` stays a derived extra for `index report`,
`--mode code`, and the foundry move-list.

## What it looks like when real

- Session instructions say: symbols → codegraph, not
  `scribe recall --mode code`.
- Default recall still omits `code:`.
- Graphify is not deleted.
- Unifying CAP-14 (pgvector / semantic) is a different decision.

## Constraints / Non-goals

- Do not run `codegraph install --target claude` (fights Marshal
  `mcp_servers`).
- Do not nightly-graphify `recipes/` or the repo root.
- Do not flip Epic 44 `blocked` from this Dream.

## Kinships

[[pyforge-scribe]] · [[scribe-knowledge-layers]] ·
[[marshal-token-economy]] · [[intelligence-before-foundry]]

## Realization log

- **2026-09-13** — Operator accepted the CAP-14 (later-caps) ruling.
  Spec `spec-scribe-code-navigation-owner`; Epic 17 Story 17.1.
  Reminted in worktree `hub-scribe-17-mint` (primary untracked drafts
  were not the source of record).
