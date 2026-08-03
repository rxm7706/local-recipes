---
title: Refreshing every loop-home from main is a hand-run ritual
type: dream
owner: marshal
status: dreamt
---

# Refreshing every loop-home from main is a hand-run ritual

## The Dream

Keeping all 8 station loop-homes current with `main` is two directions, and
only one is automated. **Push** (a loop-home's own new commits reaching
origin) already has a real watcher — `scripts/loop_push_watch.py`
(`loop-push-watch` pixi task): runs on an interval for as long as any
bmad-loop engine is live, pushes every station + per-story worktree branch,
exits on its own. Found live this session: it was never actually running —
every push this session happened because a human (or agent) asked "is
anything ahead of origin?" and pushed by hand, the exact blind spot the
watcher exists to close.

**Pull** (main's new merges reaching each station's `loop/pyforge-<station>`
branch) has no automation at all. Every refresh this session was the same
manual sequence, repeated after nearly every PR merge: `git fetch origin
main`, then for each of 8 homes, `git merge --ff-only origin/main` — and
critically, a judgment call every single time on what a merge failure
*means*: a clean fast-forward (safe, just do it); a station with an ACTIVE
run (never touch, verify the root checkout is a separate git worktree from
any live session first); or a station diverged with old pre-squash-merge
history already redundant on `main` (needs a human confirmation before
force-pushing origin, verified by cross-checking one sample commit against
main's history each time). That third case happened twice this session
(doctor/herald/mason/scribe/steward, twice) — the same five stations, the
same reasoning, re-derived from scratch each time because nothing recorded
the verdict from the first pass.

## What it looks like when real

- `loop-push-watch` (and `dashboard-watch`, same gap) runs automatically
  alongside any fleet launch, not only when someone remembers to start it —
  ideally the same launch step that starts a `bmad-loop run` also ensures
  both watchers are live, rather than three separate things (the run, the
  push watcher, the dashboard watcher) a human has to remember to start
  together. A launch runbook or `.claude/skills/bmad-loop-setup/SKILL.md`
  itself naming both watchers as required companions would close most of the
  gap even without full automation.
- `unpushed-work-check` (the detector half) runs on the same standing
  check-in cadence the story-status/loop-stall detectors already get, not
  only when someone thinks to ask — so a watcher outage is caught by the
  second line of defense within one cycle, not discovered days later.
- A pixi task (or a `marshal` CLI subcommand, once one exists — see
  `docs/dreams/one-front-door.md`) does the pull side: fetch `main`,
  fast-forward every loop-home that can be fast-forwarded cleanly, and for
  each one, report rather than guess:
  - clean fast-forward → done, pushed, one line of output;
  - a live tmux session for that station → skipped, named explicitly, never
    touched;
  - genuine divergence (unique commits on the loop-home not reachable from
    main, e.g. an unlanded story merge) → reported, not touched, exactly the
    marshal case this session hit twice (Story 2.2, then Story 2.4, each
    correctly left alone until its own landing PR merged);
  - stale/redundant divergence (loop-home's unique commits are already on
    `main` under a different, squash-merged commit) → reported with the
    evidence (which commit, which PR it matches), but **the force-push
    itself stays a human decision** — this is not a case to fully automate
    away, only to stop re-deriving from scratch.
- The "already verified redundant" verdict for a specific set of stale
  commits, once given, doesn't need re-verifying next time the same commits
  show up stale again — either the force-push actually happens (closing the
  loop for good) or the verdict is recorded somewhere durable enough that a
  second pass doesn't repeat the archaeology.

## What is real

- `loop_push_watch.py` exists, is a registered pixi task, and was
  **confirmed not running** for this entire session (`ps aux` came back
  empty) — started manually as a side effect of writing this Dream.
- **Root cause, investigated**: nothing starts it automatically. It is
  designed to "run for as long as any bmad-loop engine is running, then EXIT
  on its own" — but that lifecycle only closes the *stopping* half; nothing
  opens it. `bmad-loop run` does not spawn it as a companion process, and
  `.claude/skills/bmad-loop-setup/SKILL.md` — the skill that documents
  installing and using the orchestrator — describes the engine itself in
  detail but says nothing about starting `loop-push-watch` (or
  `dashboard-watch`) alongside a run. It is a fully manual, separate
  `pixi run` invocation that nothing in the launch path or its documentation
  prompts anyone to make. Every story launch this session (2.1 through 2.5)
  went through `bmad-loop run` directly, with no separate step to start the
  watcher — so it never had a chance to start.
- **`dashboard-watch` has the identical gap** — also a registered pixi task,
  also confirmed not running (`ps aux` empty). Same root cause: no
  auto-start, nothing in the launch documentation names it as a required
  companion.
- **The second line of defense was also dormant.** `unpushed-work-check`
  (the detector that finds the *symptom* — dangling/unreachable commits —
  after the fact, distinct from `loop-push-watch`'s *prevention*) had not
  been run at any point this session either. Running it live during this
  investigation returned **28 findings**: 12 unpushed local branches on the
  main checkout (pre-existing, from earlier sessions, a separate cleanup
  backlog) and 16 dangling commits — several of them exactly the exposure
  `loop-push-watch` exists to prevent, including a `WIP on
  bmad-loop/20260803-023308-65b7/2-4-doc-only-story-classification` commit
  from this session's own Story 2.4 dev pass. Three independent safety
  layers (prevention watcher, symptom detector, and the human noticing) were
  all silent at once; only the third one — this conversation's own review —
  caught it, days-late.
- No equivalent to `loop-push-watch` exists for the pull direction. Every
  refresh this session (main → all 8 loop-homes) was hand-run, multiple
  times, including the divergence triage described above.
- The doctor/herald/mason/scribe/steward stale-history case was
  independently re-verified twice this session with the same conclusion —
  concrete evidence the "re-derive the verdict every time" cost is real, not
  hypothetical.

## Constraints

- Never auto-force-push. Detecting "this divergence looks stale and
  redundant" is exactly the kind of judgment call this repo's Git Safety
  Protocol treats as needing a human decision — automation should make that
  decision fast and evidence-backed, not make it unattended.
- Must detect a live tmux session (or equivalently, an active run in that
  station's `.bmad-loop/runs/*/state.json`) before touching a loop-home's
  root checkout, and must distinguish that root checkout from any per-story
  worktree branched off it (confirmed this session: the root checkout and an
  active worktree are separate git worktrees on separate branches — updating
  the root is safe even while a worktree-branch session is live).

## Non-goals

- Not a request to make the loop itself push at its own stage boundaries
  (`loop_push_watch.py`'s own docstring already names that as the durable
  fix, upstream, out of this repo's hands — this Dream is about running the
  stopgap that already exists, plus building the missing pull-side half).

## Realization log

- **2026-08-03** — Captured after refreshing main + all 8 station branches
  by hand for the second time in one session, including re-deriving the same
  stale-history verdict for 5 stations a second time. `loop-push-watch`
  started as an immediate, no-design-needed fix for half the problem; the
  pull-side automation is the open half this Dream exists to eventually
  close.
- **2026-08-03** — User asked why `loop-push-watch` wasn't running, treating
  the omission itself as a bug worth investigating, not just a missed step.
  Root cause found: no auto-start exists anywhere (not in `bmad-loop run`,
  not in the setup skill's documentation), so it is 100% opt-in and nothing
  prompts anyone to opt in. `dashboard-watch` has the identical gap.
  `unpushed-work-check`, the detector meant to catch the resulting exposure
  even if the watcher is down, had also not been run all session — live run
  returned 28 findings, including a dangling WIP commit from this session's
  own Story 2.4 dev pass. All three safety layers (prevention, detection,
  human review) were silent simultaneously; only the third caught it, late.
  Findings folded into "What is real" above.
