---
spec: durable-runs
status: archived
archived-reason: absorbed
owner-dream: docs/dreams/durable-runs.md
surface: []          # archived — no live surface of its own; see § What carries forward
companions: []
sources:
  - ../../../../../../docs/dreams/durable-runs.md
open_questions: []
---

> **Retirement record.** This Dream is `status: archived` (`absorbed`). Charter §5 requires
> every Dream to carry a Spec, archived included. It states what was contracted, why it
> ended, and what survives — not a plan for work that will not happen.

# durable-runs — retirement record

## Why it was contracted

An unattended factory that can lose its own output is not autonomous, it is lucky. Measured
2026-07-31: 6 station loop branches on no remote, ~5,150 lines on rescue branches, one
734-line story unpushed six days, 156 dangling commits one `git gc` from unrecoverable, and
a 1,748-line commit sitting 40 minutes as local-only. Six capabilities: unpushed-work
detection (CAP-1), an interval-push stopgap (CAP-2), stage-boundary push (CAP-3), durability
wired into fleet launch (CAP-4), durability as a reported fleet-status dimension (CAP-5), and
patch-id-verified branch retirement (CAP-6).

## Why it ended

**Retired 2026-08-02, as part of a dream-consolidation pass — fully decomposed, not a
duplicate.** All six capabilities are accounted for in `spec-pyforge-marshal`'s real PRD:

- **CAP-1** (`scripts/unpushed_work_check.py`) and **CAP-2** (`scripts/loop_push_watch.py`)
  already shipped as standalone repo scripts, outside the `marshal` CLI package surface —
  cited as motivating evidence for FR-61, correctly given no FR number of their own since
  they are not marshal-CLI features.
- **CAP-3** (stage-boundary push) and **CAP-4** (durability wired into fleet launch) →
  **FR-61** (bounded-loss durability).
- **CAP-5** (durability as a reported fleet property) → **FR-62**.
- **CAP-6** (branch retirement, patch-id verified) → **FR-63**.

## What carries forward

Everything — this Dream's real, measured evidence (the 2026-07-31 audit table) is cited
directly in the consolidated `pyforge-marshal.md`. The two shipped scripts
(`unpushed_work_check.py`, `loop_push_watch.py`) remain live, unmodified by this retirement.
FR-61/62/63 in the real PRD are the current, binding contract for everything this Spec
proposed.

## Non-goals

- **Reviving this Dream as written.** Its intent already lives in FR-61/62/63.
- **Treating this record as a backlog item.** Archived Dreams are excluded from the Backlog
  board by design — the backlog items are FR-61/62/63's own stories.

## Success signal

A reader arriving at this Dream learns in one page that all six capabilities landed
somewhere real — two already shipped, four decomposed into FRs — without re-deriving the
mapping or mistaking any of them for a gap.
