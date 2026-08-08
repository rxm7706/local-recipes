---
title: The dashboard goes stale because promotion is a remembered step
type: dream
owner: marshal
status: archived
---

# The dashboard goes stale because promotion is a remembered step

> **Consolidated into [[pyforge-marshal]] on 2026-08-08** (§ *Eight more, consolidated
> here*). This file is archived in place: its **Spec stays live and remains the
> contract** — archiving the Dream tier never retires the chain below it. Kept, not
> deleted, so the reasoning that produced the Spec is still readable.

## The Dream

A story landing on a loop-home's branch does not, by itself, make the
dashboard or the tracked ledger show it as done. Two separate manual steps
have to run afterward: `python3 scripts/promote_sprint_status.py` (copies the
loop-home's live Tier-3 `sprint-status.yaml` into the tracked
`sprint-status-ledger.yaml`) and `python3 docs/dashboard/generate.py
--source sprint-status` (regenerates `data.js` from the current state).
Nothing enforces that either happens, and nothing reminds anyone they
haven't — the dashboard just quietly keeps showing whatever story was
in-flight the last time someone happened to run both.

Live cost the same session, three separate times: Story 2.1 landed, the
dashboard kept showing it running until the user asked why; the `8-5` block
fix landed on the loop-home feed but the tracked ledger promotion was
forgotten until the forward-dependency detector itself caught the gap; Story
2.4 landed, the dashboard again kept showing it running. Each time the fix
was the same two commands and a small `maintenance` PR — a real fix, but a
repeated one, because the trigger to run it was "a human noticed and asked,"
not anything structural.

This Dream is the idea already named out loud mid-session: fold promotion
into the standard check-in habit, or better, make it automatic — a story
landing should be the trigger, not a periodic poll that depends on someone
remembering.

## What it looks like when real

- A story landing (merge commit appears on a loop-home's branch) is never
  more than one check-in cycle away from being reflected in both the tracked
  ledger and the dashboard — today it can silently sit stale indefinitely.
- The recurring status check-in routine runs `promote_sprint_status.py` +
  the dashboard regen as a standing step every time, not only when someone
  separately remembers to ask "does the dashboard match reality?"
- Ideally this stops being a remembered step at all: a git hook, a
  `bmad-loop` lifecycle hook (post-merge-to-loop-home), or a scheduled task
  runs the promotion automatically whenever a run's `state.json` marks a
  story `done`, so a human never has to notice the staleness to begin with.
- A detector exists (or `dashboard_drift_check.py` is extended) to catch a
  landed-but-unpromoted story on its own, the same way
  `forward_dependency_check.py` caught the `8-5` promotion gap as a side
  effect of an unrelated check — that was luck, not design; this Dream is
  about not needing the luck.

## What is real

- Three live incidents this session, all the same shape: story lands on the
  loop-home branch, dashboard/tracked-ledger stay stale until a human
  notices and asks. Fixed each time with `promote_sprint_status.py` +
  `docs/dashboard/generate.py --source sprint-status` + a small
  `maintenance` PR (PRs #236 [closed, superseded by later work before it
  merged], #240, and the inline fix folded into PR #237's own diff for the
  `8-5` case).
- No automation exists yet for any of the three options above (check-in
  habit, git hook, drift detector) — this Dream captures the idea, not an
  implementation.

## Constraints

- Never silently skip a promotion because it "looked recent enough" — the
  whole point is that staleness is currently undetectable without running
  the check, so an automated version must actually run the check, not
  approximate it.
- Whatever automates this must not run *during* an active bmad-loop session
  for the same story it would be promoting — the loop-home's Tier-3 feed is
  the orchestrator's own write surface while a run is live (per
  `bmad_loop.sprintstatus`'s own docstring: "the orchestrator is the single
  writer... so the no-races invariant holds"); promotion should trigger on
  landing, not poll mid-run.

## Non-goals

- Not a request to change what `promote_sprint_status.py` or the dashboard
  generator actually compute — both already do the right thing when run;
  the gap is entirely about *when* they run.

## Realization log

- **2026-08-03** — Captured after the third same-session incident of the
  dashboard reading stale after a story landed (2.1, the `8-5` block fix,
  2.4), each caught only because the user asked "why does the dashboard
  still show X running." Not yet acted on.
