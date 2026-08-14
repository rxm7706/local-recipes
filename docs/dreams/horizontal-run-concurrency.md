---
title: One story in flight at a time, silently, by an upstream stub
type: dream
owner: marshal
status: realized
---

# One story in flight at a time, silently, by an upstream stub

## The Dream

Every `bmad-loop` run Marshal launches works exactly one story at a time.
Marshal's own rendered policy template hard-codes it:
`adapters/harness_bmadloop.py:320` `max_parallel = 1`, with no comment
explaining why — unlike almost every other line in that template. The
question behind this Dream: is that a Marshal-side default worth revisiting,
or a hard ceiling imposed somewhere else entirely?

It is the latter, confirmed by reading the vendored `bmad_loop==0.9.0`
package directly
(`.pixi/envs/local-recipes/lib/python3.14/site-packages/bmad_loop/policy.py`).
Its own `ScmPolicy.max_parallel` field carries the answer as a comment
(`:448-451`): *"units in flight at once. Parallel fan-out (Phase 5) is not
built yet, so any value > 1 is clamped to 1 in loads() — the knob exists
but is inert until the parallel scheduler lands."* The loader backs that up
in code: `:815-817` raises `PolicyError` if the requested value is `< 1`,
then `:841-842` computes `max_parallel=min(requested_parallel, 1)` — any
value an operator asks for above 1 is silently floored to 1, with no
diagnostic surfaced back. `bmad_loop`'s own shipped policy-template comment
says the same thing in fewer words (`:1077`): *"parallel fan-out unbuilt;
values > 1 clamp to 1."* This is a stub for a feature the engine names and
has not built, not a Marshal-side conservatism. Prior art independently
confirms it: a 2026-07-16 technical-research finding for a different effort
already noted "bmad-loop v0.8.1 executes stories sequentially (`max_parallel
= 1` — fan-out is not a shipped capability)"
(`docs/specs/cfe-atlas-datapipeline-kedro-migration.md:91`) — still true two
minor versions later at 0.9.0.

Marshal's own worktree-per-story isolation already exists —
`adapters/harness_bmadloop.py:309` `isolation = "worktree"`, `:310`
`branch_per = "story"` — but that describes how the ONE story currently in
flight is isolated, not a proof that N stories in flight at once would stay
isolated from each other. Whether the shared journal (`core/journal.py`,
built multi-writer-safe at Story 3.1 for a different reason — many *loop
homes* sharing one store, not many stories inside one run), the supervisor's
idle/budget ladder, and the landing path would all hold under concurrent
dispatch is unverified in either direction, because nothing has ever
attempted it.

This gap is unregistered. Story 6.8's own tracked upstream-contribution
register (`upstream-register.json`) carries 8 entries for known `bmad-loop`
gaps and their Marshal-side workarounds — including the adjacent
"per-story-model-tiering" gap — but none for parallel fan-out. And "vertical
scaling" as a concept the operator asked about does not exist anywhere in
this repo's planning corpus at all (grep across `docs/` and `_bmad-output/`
for "vertical scal"/"horizontal scal" returns zero hits). The closest
analog — escalating a *single* story's model on a struggling retry — is a
different mechanism, captured in the sibling Dream
[[adaptive-model-tiering]], not this one. This Dream is narrowly about
whether, and how, more than one story could ever run inside one launch.

## What it looks like when real

- An operator who sets `scm.max_parallel > 1` (or the equivalent Marshal
  policy key, once one exists) is told the request is inert — a registered
  finding or advisory — instead of it being silently floored with no signal,
  the way it is today.
- The `bmad_loop` parallel-fan-out gap is tracked in the same register Story
  6.8 already maintains, so `marshal upstream` surfaces it the way it
  surfaces the other 8 known gaps, rather than it being invisible to anyone
  who hasn't read the vendored source.
- Marshal's own readiness — whether worktree isolation, the journal, the
  supervisor, and the landing path could actually support N stories in
  flight at once — is assessed and the findings recorded, so the day
  `bmad_loop`'s own Phase 5 scheduler ships, adopting it is a scoped story
  rather than a fresh investigation from zero.
- A downstream story concluding "still blocked, revisit when `bmad_loop`
  ships Phase 5" is an acceptable, complete outcome — this Dream does not
  presuppose that concurrent dispatch ships from Marshal's side at all.

## Constraints

- Marshal must not attempt to build actual concurrent story dispatch while
  `bmad_loop` 0.9.0's own `loads()` clamps `max_parallel` to 1 server-side —
  that would be building against a knob the engine itself defeats
  unconditionally.
- Nothing here touches the vendored `bmad_loop` package itself (AD-2/AD-3's
  wrap-never-fork discipline; `adapters/harness_bmadloop.py` is the one
  seam). If a parallel scheduler ever ships, it ships upstream; Marshal's
  role is to be ready to consume it, not to build one inside the wrapper.
- This is a distinct axis from the cross-project concurrency Marshal already
  supports and measures (multiple loop *homes* running simultaneously,
  `prd.md:927`'s SM-5, currently 7 provisioned) — that capability is
  unaffected and not in scope here.

## Realization log

- **2026-08-11** — Captured during the same cost/speed investigation as
  [[adaptive-model-tiering]]: why bmad-loop-driven unattended runs are
  slower and more expensive than a single supervised session, and what
  Marshal could build to help. Direct read of the vendored
  `bmad_loop==0.9.0` source confirmed `max_parallel` is an inert stub,
  clamped to 1 at policy load regardless of the requested value, with the
  engine's own comments naming the missing piece "Phase 5" and stating it
  is "not built yet." No existing FR, story, or `upstream-register.json`
  entry names this gap. Queued as a Dream rather than patched by hand —
  `adapters/harness_bmadloop.py` and `upstream-register.json` were
  deliberately left untouched pending the Spec/story chain.
- **2026-08-14** — Realized in its own declared scope — Story 3.13 (FR-184) shipped the loud advisory (`MRS-POLICY-007`), the `upstream-register.json` `parallel-fan-out` entry, and the readiness assessment. Actual concurrent dispatch stays parked by this dream's own constraint until upstream `bmad_loop` ships Phase 5; the register tracks that day. Status flipped by the 2026-08-14 audit.
