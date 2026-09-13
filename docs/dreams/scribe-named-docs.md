---
title: How-tos and the library catalog are in the graph; the rest of docs/ is not
type: dream
owner: scribe
status: specified
---

# How-tos and the library catalog are in the graph; the rest of docs/ is not

## The Dream

Active Dreams already compile. Agents still ask “which pixi task?” and
“is this library in the catalog?” Those answers live in named Diátaxis
how-tos and in `library-llms-full.md`. Opening `docs/**` would drown
recall in dreams, legacy specs, governance, intake, and explanation
novels.

The Dream is **named extras only**. How-to guides join as ordinary
`doc` nodes. The library catalog joins as a heading extract — the 73k
file stays SoT on disk.

## What it looks like when real

- `docs/how-to/pixi-tasks.md` compiles as one `doc:` node with its
  body (each how-to is small).
- `docs/how-to/README.md` does not.
- `docs/reference/library-llms-full.md` compiles as a pointer whose
  text lists the `##` sections and does not contain a unique sentence
  from the catalog body.
- `docs/explanation/`, `docs/tutorials/`, `docs/specs/`,
  `docs/governance/` stay out.
- A missing `docs/how-to/` or missing catalog file is zero extra nodes
  and no warning.

## Constraints / Non-goals

- Never `docs/**`. Dreams stay on the existing CAP-3 surface.
- Do not ingest the wholesale library catalog body.
- Do not add cocoindex to compile. Do not open CAP-8 graphify targets.

## Kinships

[[pyforge-scribe]] · [[scribe-knowledge-layers]] ·
[[scribe-planning-pointers]]

## Realization log

- **2026-09-13** — Hoisted parked CAP-13. Spec
  `spec-scribe-named-docs`; Epic 14 Story 14.1.
