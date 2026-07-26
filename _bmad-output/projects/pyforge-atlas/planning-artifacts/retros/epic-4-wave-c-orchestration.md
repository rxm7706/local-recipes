---
doc_type: retrospective
project: pyforge-atlas
epic: 4
wave: C
title: Wave C — Orchestration & Visualization
stories: 2
date: 2026-07-25
basis: reconstructed from tracked evidence (run log, epics.md, PRs #84/#85)
---

# Epic 4 · Wave C — Orchestration & Visualization

**Scope:** C1 kedro-dagster glue + `dagster-dryrun` gate, FR-6 (`166eb42`, #84) ·
C2 kedro-viz behind a pixi `viz` task, FR-6/AC-3 (`d4d7372`, #85).

## What worked

- **`dagster-dryrun` as the gate instead of a live daemon.** The wave proved the
  orchestration *contract* — jobs resolve, assets wire up — without requiring a
  running daemon in CI. This is the pattern that let orchestration ship at all in
  an unattended loop.
- **The deferral was named at the moment it was taken** (`DW-C1-1`, live daemon
  bring-up), not discovered later.
- **C2 behind a task, not a service.** `viz` stays opt-in; nothing in the default
  path depends on a UI process.

## What did not

- **The seam between "dry-run proves it" and "it actually runs" was never
  closed**, and it recurred in Wave G (`DW-G3`) and Wave H (`DW-H4`) as the same
  deferral in three places. By closeout, *live daemon* was deferred three separate
  times without a single owning item.
- **`DW-C1-1` is one of the 45 entries lost** when `deferred-work.md` was
  truncated to 9. The deferral was honest and its record did not survive — which
  is why it resurfaced as an unanswered Spec question a week later.

## Carry-forward

1. **When the same deferral is taken in three waves, promote it once to a
   contract-level item** rather than recording it three times at story level.
   This is now `DC-2` in PRD § 6.4.
2. Dry-run gating is the right default for orchestration under unattended
   execution — reuse it.
