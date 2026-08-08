---
spec: sprint-status-auto-promote
status: draft
owner-dream: docs/dreams/sprint-status-auto-promote.md
surface:
  - scripts/promote_sprint_status.py
  - docs/dashboard/generate.py
sources:
  - ../../../../../../docs/dreams/sprint-status-auto-promote.md
open_questions:
  - "Trigger mechanism unchosen: the Dream names three (standing check-in step, post-landing hook keyed off a run's state.json / loop-home merge, scheduled task) and picks none; the hook shape decides whether this lands as a marshal deploy/land step or a repo-level script"
  - "Landing surface for the promoted diff: the ledger and data.js are tracked, so an automated promotion still produces a commit that must reach main — via a maintenance PR, folded into marshal land, or direct — undecided"
  - "Detector home: extend dashboard_drift_check.py vs. a new landed-but-unpromoted detector registered alongside forward_dependency_check.py"
---

# SPEC — sprint-status auto-promote

## Why

A story landing on a loop-home branch does not, by itself, update the tracked
ledger or the dashboard. Two manual commands must run afterward —
`scripts/promote_sprint_status.py` (Tier-3 `sprint-status.yaml` →
tracked `planning-artifacts/sprint-status-ledger.yaml`) and
`docs/dashboard/generate.py --source sprint-status` — and nothing enforces or
detects that they haven't. Three live incidents in one session (Stories 2.1,
2.4, and the `8-5` block fix) all had the same shape: story done, dashboard
stale, caught only because a human asked why. The trigger today is "someone
noticed," and this Spec makes it structural.

## Capabilities

- **CAP-1 — promotion runs on landing, not on memory.** Intent: a story
  landing (merge commit on a loop-home branch / a run's `state.json` marking
  it `done`) mechanically triggers `promote_sprint_status.py` +
  `generate.py --source sprint-status`, instead of both being remembered
  steps. At minimum the recurring status check-in runs both as a standing
  step every cycle; the full form is a post-landing hook so no check-in is
  needed at all. Success: a landed story is reflected in the tracked ledger
  and `data.js` within one check-in cycle (hook form: without any human
  action), never sitting stale until someone asks.
- **CAP-2 — staleness is detectable on its own.** Intent: a detector (new,
  or an extension of `dashboard_drift_check.py`) compares each project's
  landed reality against its tracked ledger / `data.js` statuses and fails
  loudly on a landed-but-unpromoted story — the check
  `forward_dependency_check.py` performed once by accident for `8-5` becomes
  designed-for. Success: recreating any of the three incident states makes
  the detector exit non-zero and name the stale story; a promoted state
  passes clean.
- **CAP-3 — the check is real, never approximated.** Intent: no
  freshness heuristic ("looked recent enough", mtime, last-run timestamp)
  ever substitutes for actually running the promotion/comparison — staleness
  is undetectable without the check, which is the whole point. Success: the
  automation's skip conditions are only "no upstream change" (the existing
  idempotence of `promote_sprint_status.py`) or the CAP-4 race guard, never
  a time-based guess.
- **CAP-4 — never races the orchestrator.** Intent: promotion for a story
  never runs *during* an active bmad-loop session for that story — the
  loop-home's Tier-3 feed is the orchestrator's single-writer surface while
  a run is live. The trigger is landing, not a mid-run poll. Success: with a
  run live, the automation defers or scopes around that run's project;
  promotion fires only once the story has landed.

## Constraints

- `promote_sprint_status.py` and `generate.py` already compute the right
  thing; this Spec changes only *when* they run. No change to what either
  produces (the ledger's shared-shape header contract, `data.js`'s
  data/shell split).
- Hand-curated content is inviolate: `data.js` narrative fields (titles,
  timing, gatenotes, roadmap) survive any automated regeneration
  byte-identical — the generator's existing rule (statuses + dreams list +
  timestamp only) binds the automation too. The ledger is GENERATED and
  wholly machine-owned, but its landing on `main` follows repo convention
  (non-recipe diff ⇒ `maintenance` label if it goes via PR); automation must
  not silently push tracked files outside the agreed landing path.
- `sprint-status` mode can *downgrade* (it mirrors the Tier-3 feed, which
  may lag a project not currently loop-driven); automated runs must not turn
  that into silent regression on `main` — a downgrade in the produced diff
  is surfaced, not auto-landed unreviewed.
- Detector and promotion must work per-project: one project's live run
  (CAP-4 deferral) must not block promoting another project's landed story.

## Non-goals

- Story-**spec** promotion (Tier-3 → tracked `planning-artifacts/specs/`
  after merge, the CLAUDE.md durable-specs convention) — that is
  spec-4-1-story-spec-promotion's contract, not this one. This Spec is
  sprint-status + dashboard only.
- Changing the dashboard's two-mode design (`git` CI mode stays done-only,
  upgrade-only, hands-off) or the ledger's role as the deploy-time truth.
- Real-time status: "within one check-in cycle / on landing" is the bar, not
  seconds-fresh.

## Success signal

After a story lands on a loop-home branch, the tracked ledger and `data.js`
reflect it without any human noticing staleness first; and if the promotion
mechanism itself ever breaks, the CAP-2 detector — runnable standalone and in
the standard check suite — fails and names the stale story instead of the
dashboard quietly lying.
