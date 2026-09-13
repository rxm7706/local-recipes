---
title: Every recall door uses the same default bag
type: dream
owner: scribe
status: specified
---

# Every recall door uses the same default bag

## The Dream

`AGENTS.md` already tells a session to run `scribe recall` without
`--kind`. The portal job and Marshal planning-graph already shell that
CLI. Nothing locks them to inherit CAP-4. A future argv tweak could
pass `--kind code` and put graphify back in the default bag. Cursor
only has the Dream-tier rule; it does not name recall.

The Dream is **one default at every door**. Portal `scribe/recall` and
Marshal `scribe recall` do not pass `--kind`. Cursor has a thin always-on
rule that points at the AGENTS session path. No portal redesign.

## What it looks like when real

- `_grammar_recall` argv is `scribe recall <query>` (or `pyforge scribe
  recall <query>`), never `--kind`.
- `render_scribe_recall_argv` may add `--scope` only.
- `.cursor/rules/scribe-recall.mdc` points at `AGENTS.md` § Scribe recall.

## Constraints / Non-goals

- Do not redesign django-scribe UI. Do not invent recall modes (CAP-11).
- Do not import `pyforge.scribe` from the portal.

## Kinships

[[pyforge-scribe]] · [[scribe-knowledge-layers]]

## Realization log

- **2026-09-13** — Hoisted parked CAP-12. Spec
  `spec-scribe-portal-recall-defaults`; Epic 12 Story 12.1.
- **2026-09-13** — CAP-1 realized in Story 12.1.
