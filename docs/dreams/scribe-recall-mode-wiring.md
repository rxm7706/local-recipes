---
title: Planning retrieve names --mode planning
type: dream
owner: scribe
status: specified   # 2026-09-13 — Story 18.1 implements CAP-1..3 on this PR
---

# Planning retrieve names --mode planning

## The Dream

`--mode planning|memory|code` exists on the CLI. Marshal retrieve and
session agents still inherit the default bag, so planning questions
compete with memory and commits. Portal Story 12.1 locked “no
`--kind`” and left modes out on purpose.

The Dream is **wired modes**. Marshal planning-graph retrieve always
passes `--mode planning`. Session agents use `--mode planning` for
decisions. Portal may pass `--mode` from the payload; it does not
invent `--kind`.

## What it looks like when real

- `render_scribe_recall_argv` includes `--mode planning`.
- It still never includes `--kind`.
- It never defaults to `--mode code`.
- `AGENTS.md` session path shows `--mode planning` on the decision
  command.

## Constraints / Non-goals

- Do not change internal `answer(..., mode=)` lexical/semantic.
- Do not make semantic ranking the default.
- Portal stays optional-mode, not forced planning.

## Kinships

[[pyforge-scribe]] · [[scribe-recall-modes]] ·
[[scribe-portal-recall-defaults]]

## Realization log

- **2026-09-13** — Specified as `spec-scribe-recall-mode-wiring`. Story
  18.1 wires Marshal retrieve and the session decision command.
