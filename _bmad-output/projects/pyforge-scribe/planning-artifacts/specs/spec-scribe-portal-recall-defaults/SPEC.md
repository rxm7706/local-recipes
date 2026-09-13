---
spec: scribe-portal-recall-defaults
status: ready
owner-dream: docs/dreams/scribe-portal-recall-defaults.md
surface:
  - src/shared/packages/django-pyforge/src/django_pyforge/assertion/client.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/planning_graph.py
  - .cursor/rules/scribe-recall.mdc
companions: []
sources:
  - ../../../../../../docs/dreams/scribe-portal-recall-defaults.md
  - ../spec-scribe-knowledge-layers/later-caps.md
open_questions: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate.

# SPEC — Portal and Marshal inherit default recall

## Why

CAP-4 lives in `answer()`. CAP-5 lives in `AGENTS.md`. The portal job and
Marshal retrieve already shell `scribe recall`. Nothing stops them from
adding `--kind code`. Cursor does not name the session path.

## Capabilities

- **CAP-1**
  - **intent:** Every wired recall door uses the CLI default bag (no
    `--kind`). Cursor has a durable pointer to the AGENTS session path.
  - **success:** Portal `_grammar_recall` argv is only the binary,
    `scribe`/`recall`, and the query. `render_scribe_recall_argv` may
    append `--scope` only. `.cursor/rules/scribe-recall.mdc` exists
    outside `bmad:context` and names `scribe recall`.

## Constraints

- Do not redesign django-scribe. Do not import `pyforge.scribe` there.
- Do not add recall modes (CAP-11).

## Non-goals

- Portal UI. Semantic default. Codegraph replacement.

## Success signal

A test fails if either argv builder grows `--kind`.

## Assumptions

- Both doors already call the CLI without `--kind`; this story locks that.
