---
title: Single-story dispatch is a marshal verb, not a session's discipline
type: dream
owner: marshal
status: realized
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
  - story-spec promotion to tracked `planning-artifacts/specs/`; scoped
  `sprint-ledger-sync` + `story-status-check` in the same commit.
- **Fleet drain playbook (2026-08-22/23):** eight-station campaign documented in
  `spec-marshal-single-story-dispatch/fleet-drain-playbook.md` (marshal-owned companion);
  interim runner at `.cursor/pyforge-fleet-drain/`. Merge-in-agent fleet-wide since
  2026-08-23. Six stations drained; marshal + steward backlog remain — the playbook is
  the acceptance oracle for Epic 22 CAP-7 until `marshal factory dispatch --fleet` ships.

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

## Addendum (2026-08-31) — station-scoped and sequence-scoped dispatch

**Problem:** `dispatch <slug> <story>` launches exactly one story and returns — no
chaining. `drain --mode <mode>` chains automatically (CAP-7) but is fleet-wide only: its
six flags (`--mode`, `--leave-remaining`, `--once`, `--max-cycles`, `--tick-seconds`,
`--campaign`) carry no station filter — confirmed against `cli/dispatch.py`'s own
argparse definition — so it always reads every station's ordered backlog and launches one
story per station in parallel. There is no way to drain just one station to zero without
touching every other station's backlog too, and no way to hand marshal an explicit ordered
list of stories to run, overriding the ledger's own order, for a single targeted push.

**Motivating incident (2026-08-31):** wanted to complete just `pyforge-scribe`'s 2
remaining backlog stories — identified that session as the fleet's smallest,
highest-leverage remaining chunk (the only cross-station `Deps:` link in the entire
remaining backlog) — without disturbing atlas's or marshal's own in-flight backlogs. No
CLI primitive existed for it: the only options were fleet-wide `drain` (wrong scope) or
two manual `dispatch` calls with a human/agent polling for landing in between, forfeiting
`drain`'s chaining/preflight/campaign-journal machinery for no reason but scope.

**Approach:** extend the dispatch surface, don't fork it — CAP-7's chaining, preflight,
and campaign-journal machinery is exactly what a station-scoped drain needs too; the only
missing dimension is *which stories, on which stations*, handed as an override to the same
per-station ordered-backlog reader CAP-7 already owns:

1. **Station-scoped drain.** `marshal factory drain --mode <mode> --station <slug>` (or a
   sibling `dispatch-station <slug> --mode <mode>`) restricts the campaign to exactly one
   station's own backlog — same chaining/preflight/journal, one station instead of eight.
2. **Explicit sequence.** `marshal factory dispatch <slug> --stories <key1>,<key2>,...`
   chains a caller-supplied ordered list instead of the ledger's own backlog order — for
   prioritizing specific stories (today's scribe 6.2-then-6.3 finding) without editing
   `fleet-drain-queue.yaml`'s `order_overrides` for a one-off push. Every named key is
   validated against the station's actual backlog before anything launches — an unknown or
   already-done key refuses loudly, never silently skips.

**Non-goals:** not a new landing/verification mechanism (reuses `execute_dispatch_land` /
CAP-2 / CAP-4 unchanged); not a replacement for fleet-wide `drain`, which stays the
default for "drain everything."

Lands as a new CAP (CAP-10) in `spec-marshal-single-story-dispatch` when specced.

## Addendum (2026-09-02) — a `done` spec must not review-loop

**Problem:** `drain_to_zero` + `bmad-build-auto` can spend an afternoon writing
confirmatory review commits after the story is already `status: done`. Each
commit retriggers Cursor Auto-review. CAP-4 never flips the ledger, so the
fleet supervisor launches another session. The loop is not a reviewer flood; it
is the same story re-entered as a “fresh review.”

**Motivating incidents (2026-09-02):**

- Steward **41.2** ([#1017](https://github.com/rxm7706/local-recipes/pull/1017)):
  implementation done by review pass 4; passes 5–27 were 0-patch spec
  write-backs. Merge was `DIRTY` vs `main`. Fleet kept re-dispatching.
- Mason **13.2**: implementation + three real patches landed on the worktree;
  **18** confirmatory write-backs followed. **No PR** was opened. Ledger on
  `main` stayed `backlog`. Same loop.

**Two stacked causes:**

1. **Harness.** `.claude/skills/bmad-build-auto/step-01-clarify-and-route.md`
   routes `status: done` to a fresh step-04 review and resets
   `review_loop_iteration` to `0`. Step 4 writes
   `followup_review_recommended: false` and **never reads it** on the next
   start. The 5-iteration cap applies only to `bad_spec` loopbacks. Step 4
   commits the spec even when the pass applied 0 patches.
2. **Marshal.** Fleet drain treats ledger `backlog` on `main` as “dispatch
   again.” A harness halt of `done` does not make CAP-4 the *only* next step.
   Land fail (conflicts, no PR) does not park the story — it re-invokes the
   harness. `limits.max_followup_reviews` in loop `policy.toml` is not on this
   cursor dispatch path.

**Approach:** one new CAP (CAP-11), two stories — do not fork drain:

1. **Harness contract (local skill only).** `done` +
   `followup_review_recommended: false` → HALT `done` immediately (no review,
   no spec commit). `done` + `true` → at most one follow-up, then force the
   flag false. A 0-patch review pass must not commit. The vendored `bmad_loop`
   package stays unmodified. This amends the earlier “do not change
   `bmad-build-auto`” non-goal for the **in-repo skill copy only**.
2. **Dispatch terminal.** After the harness exits `done`, marshal runs CAP-4
   only (open/merge PR, ledger promote). It must not start another
   `bmad-build-auto` for that story. CAP-4 fail (conflicts, no PR, dirty)
   → CHAIN / `awaiting-operator` naming the PR or worktree. Never re-dispatch
   the harness until the operator unparks.

**Non-goals:** not a new landing path; not shrinking `max_followup_reviews`
(`docs/dreams/risk-tiered-review-depth.md`); not
`marshal-dependency-aware-dispatch` (Deps: / SIGTERM).

Lands as CAP-11 in `spec-marshal-single-story-dispatch`, Epic 29.

## Realization log

- **2026-08-21** — Seeded `dreamt` (`a17626226b`); `spec-marshal-single-story-dispatch` derived under
  pyforge-marshal the same day (`8add322204`).
- **2026-08-31** — Addendum: station-scoped and sequence-scoped dispatch.
- **2026-09-02** — Addendum: a `done` spec must not review-loop — contracted as CAP-11 in the Spec
  (`1763820bee`), Epic 29. Spec status `in-progress`.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — **`specified` → `realized`,
  verified in effect at fleet scale.** CAP-1..11 decompose to Epic 22 (22.1–22.11) and Epic 29
  (29.1–29.2), all `done`; the drain campaigns and `fleet-drain-playbook.md` are the live exercise.
  Spec `in-progress` → `shipped` with `open_questions: []`. All five questions closed:
  **OQ-1** verb = `marshal factory dispatch`, no `marshal dev` family — now a cross-package constant
  (`pyforge-core/.../landing_evidence.py:50`), so renaming would break doctor's grammar; PRD Q-15
  inherits it. **OQ-2** launch = profile-driven, shipped as Story 22.8 — with a **new Constraint**
  recorded: a dispatched session is never launched from a fork subagent (`bmad-build-auto`'s
  mandatory subagents break inside one); the profile mechanism does not enforce it. **OQ-3**
  (operator) the enforceable budget signal is wall-clock + idle-strand via the dispatch supervisor;
  token ceilings stay advisory until Epic 33's benchmark exists. **OQ-4** disjointness compares
  DECLARED surfaces only — and within-station fan-out is impossible until story specs declare their
  own `surface:`. **OQ-5** completion detection shipped as a *sibling* supervisor
  (`dispatch_supervisor/__main__.py`), neither a generalized supervisor nor Story 3.4's sidecar.
  **Consequence carried forward:** two supervisors now write run state, which is exactly why the
  CAP-17 publishing seam must be one publisher (`spec-marshal-token-economy` CAP-18, Story 33.4).
  Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.
