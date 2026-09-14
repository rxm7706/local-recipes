---
spec: scribe-named-docs
status: ready
owner-dream: docs/dreams/scribe-named-docs.md
surface:
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py
companions: []
sources:
  - ../../../../../../docs/dreams/scribe-named-docs.md
  - ../spec-scribe-knowledge-layers/later-caps.md
open_questions: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate.

# SPEC — Named docs extras, never `docs/**`

## Why

FR-9 already named Dreams. Library and how-to questions still miss
because those files are catalog, not contract, and were left out on
purpose. A wholesale `docs/` walk would compile the wrong layer
(legacy specs, governance, intake). Name the two extras that answer
those questions.

## Capabilities

- **CAP-1**
  - **intent:** Compile each `docs/how-to/*.md` except `README.md` as
    one ordinary `kind=doc` node, and compile
    `docs/reference/library-llms-full.md` as one `kind=doc` **heading
    extract** (`##` section titles only — never the wholesale catalog
    body).
  - **success:** A fixture how-to citation is present and contains a
    unique body token. `docs/how-to/README.md`,
    `docs/explanation/*.md`, and `docs/tutorials/*.md` are absent. The
    library-catalog citation is present, its text lists a `##`
    heading from the fixture, and a unique catalog-body marker is
    absent. A missing `docs/how-to/` or missing catalog file adds no
    node and no warning.

## Constraints

- Never glob `docs/**`.
- How-tos use the existing `_node_from_text_file` path (files are
  under the general doc bound).
- The catalog must not use `_node_from_text_file` (that path would
  keep the 20k header and drop the useful sections).
- Dreams stay on the existing dream surface.

## Non-goals

- Wholesale `docs/`, `recipes/`, presentations export trees.
- cocoindex inside `compile_graph`.
- later-caps:CAP-8 graphify targets; later-caps:CAP-11 recall modes.

## Success signal

A compile against a fixture with one how-to, a how-to README, an
explanation file, and a large catalog (heading + unique body marker)
writes the how-to and the catalog extract only.

## Assumptions

- Diátaxis how-tos live at `docs/how-to/<guide>.md`.
- The library catalog path is `docs/reference/library-llms-full.md`.
