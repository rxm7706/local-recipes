---
spec: pyforge-atlas
status: shipped
owner-dream: docs/dreams/pyforge-atlas.md
program: regenerable-factory (Wave 5 chain-verify)
surface:
  - src/**
  - conf/**
companions:
  - ../../prds                 # adopted: the PRD set (authoritative)
  - ../../architecture         # adopted: the architecture set (authoritative)
  - ../../epics.md             # adopted: epics/stories record
open_questions: []
---

# SPEC — pyforge-atlas (chain-verify kernel)

## Why

The atlas Kedro/Dagster/DuckDB migration shipped with a full BMAD chain
(PRD, architecture, epics; 32 stories merged, PRs #58–#105). This kernel adds
the one missing piece — a machine-readable surface manifest — binding
`src/**` + `conf/**` into the repo-wide `spec_surface_check`, so future atlas
code changes must move this project's contract. It adds NO new contract
content; the adopted companions remain authoritative.

## Capabilities

- **CAP-1 — surface binding.** Intent: the migration's code surface is
  governed; a change without contract movement is a checker finding.
  Success: `spec_surface_check` lists `spec-pyforge-atlas` with src/conf
  files governed; drift arm active (memlog mode).

## Constraints

- Changes to atlas behavior flow through the pyforge-atlas BMAD project
  (stories/correct-course), not through this kernel.

## Non-goals

- Restating the PRD/architecture.

## Success signal

Checker green with the atlas surface governed; the next atlas story's merge
moves this project's artifacts alongside the code.
