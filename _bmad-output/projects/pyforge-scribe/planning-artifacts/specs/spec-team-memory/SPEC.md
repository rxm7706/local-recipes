---
id: SPEC-team-memory
spec: team-memory
status: specified
owner-dream: docs/dreams/team-memory.md
surface:
  - .claude/memory/**
sources:
  - ../../../../../../docs/dreams/team-memory.md
open_questions: []
---

> **Canonical contract.** This SPEC is the complete contract for what to build, test and
> validate. Source documents in frontmatter are traceability only.

# team-memory

## Why

Today's memory is **personal**: each operator's auto-memory lives outside the repo,
invisible to teammates and to other agents. This Dream is a shared, version-controlled
memory layer — `.claude/memory/` in the repo — where corrections, conventions and hard-won
context accumulate as **team property**, so any agent, any operator, any session starts
already knowing what the team knows.

Inherited from [[sentinel]]'s knowledge-graph core when that Dream was absorbed 2026-07-25.

## Capabilities

- **MEM-1 — memory is committed, not personal.** *Success:* an entry written by one operator is present for every other operator and agent on the next clone.
- **MEM-2 — recall is scoped, not a dump.** *Success:* a session surfaces the entries relevant to its task rather than the whole store.
- **MEM-3 — entries carry provenance.** *Success:* every entry records when it was written and what it was learned from, so a stale one is visibly stale.

## Constraints

- **The Dream is Tier 0 and this Spec is Tier 2.** Where they differ, the Dream is the
  intent and this contract is what was agreed to build from it.
- **Ownership does not move with the work.** Chains stay filed with the owning station
  (Charter §5), whatever surface the work touches.

## Non-goals

- **Replacing per-operator auto-memory.** The personal layer stays; this is the shared one beside it.
- **A knowledge graph as a first deliverable.** The graph is [[pyforge-scribe]]'s; this is the substrate it compiles from.

## Success signal

A new clone starts knowing the team's conventions without anyone re-explaining them, and a
wrong entry is correctable in review like any other tracked file.
