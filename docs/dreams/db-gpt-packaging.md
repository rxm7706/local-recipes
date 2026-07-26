---
title: DB-GPT on conda-forge — the multi-output agent stack
type: dream
owner: mason
status: archived
archived-reason: terminal
---

# DB-GPT on conda-forge

## The Dream

Get **DB-GPT** — an agentic data application framework with a large native
dependency closure — installable from conda-forge, along with the five
prerequisites it needed that nobody had packaged.

## Why it was archived

**Terminal: delivered, but not by us.** All five prerequisites we authored
merged. DB-GPT itself arrived through an *independent* submission
(staged-recipes **#33883**, 8 outputs including `dbgpt-acc-flash-attn`) that
consumed our patches — so the outcome landed while our own submission became
redundant. Per the consume-not-submit rule (CFE **G58**: check
`lookup_feedstock` before submitting), the correct move was to stand down rather
than open a competing PR. `recipes/db-gpt/` mirrors the merged shape (v0.8.1,
green 8/8) for local use.

This is a **success recorded as an archive** — the dream was realized, the
effort was not.

## Kinships

[[packaging-factory]] (the practice) · [[pyforge-mason]] (the station).
Spec: `docs/specs/db-gpt-conda-forge.md` (TERMINAL — do not re-run BMAD on it).

## Realization log

- **2026-07-01** — all 5 prerequisites merged; db-gpt delivered via #33883.
- **2026-07-25** — **ARCHIVED (terminal)** during the Dream-lifecycle
  reconciliation; formerly a hardcoded console entry with no Dream file behind it.
