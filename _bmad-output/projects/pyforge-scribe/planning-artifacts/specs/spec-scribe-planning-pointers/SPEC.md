---
spec: scribe-planning-pointers
status: ready
owner-dream: docs/dreams/scribe-planning-pointers.md
surface:
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py
companions: []
sources:
  - ../../../../../../docs/dreams/scribe-planning-pointers.md
  - ../spec-scribe-knowledge-layers/later-caps.md
open_questions: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate.

# SPEC — Planning pointers, never wholesale bodies

## Why

Agents need to find the Brief, PRD, Architecture spine, and `epics.md`.
Those files are the SoT as files. Compiling their prose blows the token
budget Marshal already refuses. A pointer — title, path, status, and an
ID/heading extract — answers “where is it?” without serving the novel.

## Capabilities

- **CAP-1**
  - **intent:** Compile each named planning artifact as one `kind=doc`
    **pointer** node. Named means, under
    `_bmad-output/projects/<slug>/planning-artifacts/` only:
    `epics.md`; `prd.md` / `PRD.md`; `prds/*/prd.md`;
    `briefs/*/brief.md`; `architecture.md`;
    `architecture/*/ARCHITECTURE-SPINE.md`.
  - **success:** Node `text` is title + path + frontmatter `status` (if
    any) plus an order-preserving unique `FR-*` / `AD-*` list and/or
    `Epic` / `Story` heading lines. A unique sentence that exists only
    in the source body must not appear in `text`. `epics-*.md`,
    architecture novels, addenda, research, and `specs/` are not this
    surface. A missing tree is zero nodes and no warning.

## Constraints

- Do not call `_node_from_text_file` for this surface (that path stores
  the body, truncated).
- Pointer `text` is capped well below the general doc body bound.
- Citation is the repo-relative path so scoped recall already admits
  the planning tree.
- Same persist port as other `doc` nodes.

## Non-goals

- Wholesale `docs/`, `recipes/`, presentations export trees.
- cocoindex inside `compile_graph`.
- CAP-8 graphify targets; CAP-13 extra docs; CAP-11 recall modes.

## Success signal

A compile against a fixture with a large `prd.md` (unique body marker +
`FR-1`) writes one `doc` citation for that path whose text contains
`FR-1` and does not contain the body marker.

## Assumptions

- Estate layout is `briefs/*/brief.md`, `prds/*/prd.md`, and
  `ARCHITECTURE-SPINE.md` (plus occasional root `PRD.md` /
  `architecture.md` / `epics.md`).
