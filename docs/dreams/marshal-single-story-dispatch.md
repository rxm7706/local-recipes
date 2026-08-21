---
title: Single-story dispatch is a marshal verb, not a session's discipline
type: dream
owner: marshal
status: specified
---

# Single-story dispatch is a marshal verb, not a session's discipline

## The Dream

The fastest story-landing pattern this factory has ever run is not a marshal
capability — it is a ritual an interactive session performs by hand. One story
per fresh, worktree-isolated `bmad-dev-auto` agent; wait for its *real*
completion; independently verify (run the tests, read the diff, invoke the
live CLI); land through a PR; only then dispatch the next. On 2026-08-21 that
ritual landed **22 stories across four stations in one session**, where the
preceding `marshal factory spin` pass had stalled at roughly one story per
station on per-run token budgets. The dream is that this pattern becomes a
first-class marshal verb — `marshal factory dispatch <slug> <story>` (or a
`marshal dev` family) — with the ritual's rigor supplied by machinery instead
of by whichever session happens to remember it.

The pattern's speed is not an accident; it is structural. It sidesteps the
orchestrator layer where every documented bmad-loop failure lives: the
stuck-orchestrator baseline drift that permanently defers real reviewed work
(`docs/dreams/bmad-loop-baseline-drift.md`), the feed that reports intent as
fact, interactive-prompt stalls invisible to `status`, the worktree
path-length panic, and the ~600-second watchdog that kills a top-level
orchestrator busy-waiting on its own long-running nested review. And it adds
the one step no self-report can supply: independent verification — which
caught two live-reproducible leaks in a story that had already marked itself
shipped (doctor 12.3, round-4 review).

But run by hand, the pattern has exactly the weaknesses bmad-loop does not:
it dies with the operating session (in-flight agents orphan), it has no
budget ceilings, no resumable journal, no escalation protocol, no
`changes.patch` safety net, and its verification is rigor-by-discipline —
performed only as well as the orchestrating session performs it. The dream is
the best of both: marshal's deterministic governance wrapped around the
dispatch pattern's speed and verification honesty.

## What is real

Marshal already owns every piece of this **except the dispatch driver
itself**:

- **Worktree provisioning** — `marshal init` (Epic 1, shipped) provisions
  isolated homes with marker/symlink/backlink discipline; the Agent-tool
  worktree pattern proved per-story isolation works without a loop home.
- **Gates** — Epic 2 (shipped) provides the runnable gate set a landing must
  clear.
- **Landing paper trail** — Epic 4 (shipped) owns landing, branch retirement,
  and the one-pusher rule.
- **Hand-driven completions are already first-class in the ledger** — Story
  5.9 (FR-186, shipped) makes a story finished outside bmad-loop visible:
  `marshal deploy reconcile-completions` detects it from git and promotes the
  ledger, recording the completion path as `bmad-quick-dev`, distinct from a
  loop completion.
- **Fleet visibility** — Epic 5 (shipped) + `fleet-picture` report per-station
  state; Epic 15 (backlog) mechanizes the surrounding rituals (loop-home
  refresh, ledger promotion at landing).
- **The session-side protocol is documented** and validated at N=22:
  one story per fresh `general-purpose` + worktree-isolated agent running
  `bmad-dev-auto` with `BMAD_ACTIVE_PROJECT` passed per-invocation and
  physical artifact paths (never `bmad-switch` from a parallel agent);
  independent verification before every landing; `gh pr merge --merge`;
  story-spec promotion to tracked `planning-artifacts/specs/`; scoped
  `sprint-ledger-sync` + `story-status-check` in the same commit.

What does **not** exist: any marshal verb that launches, awaits, or judges a
single-story dev-auto session. `marshal factory` today is `spin`/`attach`/
`resume` — bmad-loop only. A repo-wide search of all 21 marshal epics finds
no FR covering the dispatch driver.

## What the Spec must decide

1. **Completion detection must be event-grounded, never busy-waited.** The
   two traps that motivated the session-side rule
   (`feedback_single_story_dispatch_over_backlog_orchestrator`): a top-level
   orchestrator busy-waiting on a nested async agent gets watchdog-killed and
   its child's work discarded; and a "killed"/"failed" notification does not
   mean the agent stopped — one "dead" agent landed two stories after its
   failure notification, and a naive redispatch nearly duplicated the third.
   The marshal-native driver must judge completion from git facts (AD-33:
   commits, merge refs) and running-process facts, not from notifications or
   polling filler.
2. **The verification step is the product.** Self-reports are input, never
   verdicts (the same asymmetry as feed-vs-run). The driver must run the
   story's real test/verify commands itself and read the diff surface before
   any landing — the step that made the hand-run pattern trustworthy.
3. **Wrap-vs-absorb, revisited honestly.** Marshal's PRD resolved
   wrap-vs-absorb in favor of wrapping bmad-loop. This capability is the
   absorb half arriving through the back door: it replaces the orchestrator
   layer (where the documented bugs live) while keeping the dev/review
   session machinery. The Spec must name this and either bound it (dispatch
   as a *sibling* mode beside `spin`, never a replacement) or explicitly
   revise the PRD decision.
4. **Sequencing within a station, parallelism across stations.** The
   validated pattern is one story at a time per station, stations in
   parallel when their surfaces are disjoint. Whether the driver enforces
   disjointness or trusts the operator is a Spec question.
5. **What survives the operator.** Detached-by-default like `spin` (AD-22),
   or attended-by-design? The hand-run pattern's orphan-on-session-death is
   its worst property; the Spec decides how much of bmad-loop's detachment
   (tmux, journal, resume) the driver inherits.
