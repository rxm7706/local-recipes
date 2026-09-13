---
spec: scribe-recall-mode-wiring
status: ready
owner-dream: docs/dreams/scribe-recall-mode-wiring.md
surface:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/planning_graph.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_planning_graph.py
  - src/shared/packages/django-pyforge/src/django_pyforge/assertion/client.py
  - src/platform/tests/test_scribe_recall_argv.py
  - AGENTS.md
  - .cursor/rules/scribe-recall.mdc
companions: []
sources:
  - ../../../../../../docs/dreams/scribe-recall-mode-wiring.md
  - ../spec-scribe-recall-modes/SPEC.md
  - ../spec-scribe-portal-recall-defaults/SPEC.md
open_questions: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate.

# SPEC — Planning retrieve names `--mode planning`

## Why

Story 16.1 shipped `--mode`. Story 12.1 locked “no `--kind`” and
left modes unwired. Marshal retrieve still scores the default bag.

## Capabilities

- **CAP-1**
  - **intent:** Marshal planning-graph retrieve always names the
    planning surface.
  - **success:** `render_scribe_recall_argv` appends `--mode planning`
    by default, may still append `--scope`, never appends `--kind`,
    and does not default to `--mode code`.
- **CAP-2**
  - **intent:** The portal recall job may name a mode from its
    payload; it does not invent `--kind`.
  - **success:** `recall_cli_argv` with no `mode` has neither
    `--mode` nor `--kind`. `mode=planning|memory|code` appends that
    `--mode`.
- **CAP-3**
  - **intent:** Session agents use `--mode planning` for decisions.
  - **success:** `AGENTS.md` session path and
    `.cursor/rules/scribe-recall.mdc` show `--mode planning` on the
    decision command.

## Constraints

- Do not overload `answer(..., mode=)` (lexical / semantic).
- Do not force portal to planning.
- Story 12.1 no-`--kind` lock stays.

## Non-goals

- Semantic as default.
- Portal UI.

## Success signal

A scoped Marshal retrieve argv is
`scribe recall <q> --mode planning --scope <slug>`.
