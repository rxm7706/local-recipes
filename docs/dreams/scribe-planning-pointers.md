---
title: '"Where is the PRD?" is a pointer, not forty-six thousand tokens'
type: dream
owner: scribe
status: archived
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-scribe]]** on 2026-09-17 (one-chain-per-station scribe fold).

# "Where is the PRD?" is a pointer, not forty-six thousand tokens

## The Dream

Folder SPECs and in-flight story specs already compile. The planning
novels — Brief, PRD, Architecture spine, `epics.md` — do not. An agent
asking where the PRD lives should get a path, a status, and the FR/AD
list. Serving the wholesale body recreates the token failure Marshal
already forbids (`*prd*` / `*epic*` loads).

The Dream is **pointer or extract**. One `doc` node per named artifact.
Title, path, status. FR / AD / epic-and-story headings when they are
there. Never the prose.

## What it looks like when real

- `planning-artifacts/prds/<chain>/prd.md` compiles as a pointer whose
  text names `FR-1` … and never contains a unique sentence from the
  body.
- Canonical `epics.md` compiles the same way (Epic / Story headings
  only). `epics-<chain>.md` stays out.
- Architecture is the spine (`ARCHITECTURE-SPINE.md` or a root
  `architecture.md`), not the adjacent novels.
- A missing planning tree is zero nodes and no warning.

## Constraints / Non-goals

- Do not ingest wholesale PRD / epics / architecture bodies.
- Do not compile research, addenda, test-architecture, or folder
  `SPEC.md` here (already CAP-3 / CAP-6).
- Do not add cocoindex to compile. Do not open `docs/**`.

## Kinships

[[pyforge-scribe]] · [[scribe-knowledge-layers]] ·
[[scribe-in-flight-story-specs]] · [[marshal-token-economy]]

## Realization log

- **2026-09-13** — Hoisted parked CAP-7. Spec
  `spec-scribe-planning-pointers`; Epic 13 Story 13.1.
