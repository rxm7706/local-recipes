---
title: FR-51's model tiering is fully wired and never turned on
type: dream
owner: marshal
status: archived   # 2026-09-16 — folded into [[marshal-token-economy]] (operator-ruled
                   # token-savings consolidation: one starting point). Was `realized`.
---

# FR-51's model tiering is fully wired and never turned on

> **Consolidated into [[marshal-token-economy]] on 2026-09-16** (§ *Fold
> (2026-09-16) — the token-savings Dreams come home*). This file is archived in
> place: its **Spec stays live and remains the contract** — archiving the Dream
> tier never retires the chain below it. Kept, not deleted, so the reasoning
> that produced the Spec is still readable.

## The Dream

Every `bmad-loop`-driven dev pass in every loop home runs on the SAME model,
`sonnet`, and every review pass runs on the SAME model, `opus` — a flat,
repo-wide assignment baked into Marshal's own rendered policy template
(`adapters/harness_bmadloop.py:278` `[adapter] model = "sonnet"`, `:290`
`[adapter.review] model = "opus"`, with the comment "review misses ship
false-greens; strongest model where it pays"). That comment states the real
economics: some work is worth the stronger, more expensive model and some
is not. Today Marshal cannot tell the two apart per story — every story
pays the same review cost and gets the same dev capability, whether it is
a one-line doc fix or a foundation story touching six modules.

This is not a missing mechanism. FR-51 ("A story's declared difficulty
selects the model tier without a between-batch config edit",
`prds/prd-pyforge-marshal-2026-07-25/prd.md:769-776`) shipped completely:
`core/policy.py`'s `model_tier_map` field (`:272` default `{}`, `:480-498`
`_valid_model_tier_map`'s validator — `Mapping[difficulty, Mapping[stage in
{dev, review, triage}, model]]`) composes through the same four-layer
precedence as every other policy key. `adapters/harness_bmadloop.py`'s
`render_policy_toml` (`:373-461`) applies FR-51 tier-batching at `:450-459`:
when a `difficulty` is given and present in the map, it writes
`[adapter.<stage>].model` for each mapped stage. Story 6.1 (FR-48/FR-51/
AD-19) closed what its own spec called "the final gap" — nothing resolved
which difficulty a real story declared. `core/spec_difficulty.py` parses a
story spec's `difficulty:` frontmatter; `cli/spin.py::_story_declared_difficulty`
(`:420-474`) reads it per story, `_resolve_governing_difficulty` (`:477-533`)
picks the one difficulty that governs a launch (the harness supports only
run-level model selection, so a mixed batch is never split), and
`_resolve_model_tiering` (`:536+`) resolves per-stage models and writes the
tiered `policy.toml` before `bmad-loop run` is spawned. The whole chain is
real, tested, and wired into `marshal factory spin`.

And nothing has ever fed it. Confirmed by grep across every one of the 8
loop-home projects: zero story specs anywhere declare a `difficulty:`
value. Zero `marshal-policy.toml` files populate `model_tier_map` with a
real entry — every one of the 8 carries the identical placeholder comment
(`_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml:16-23`):
*"`model_tier_map` — it maps DIFFICULTY CLASS to {stage: model} ... the
vocabulary does not exist yet ... Populate when FR-51 tier-batching lands."*
That comment was true when written and has been stale since Story 6.1
shipped (`implementation-readiness-report-2026-08-01.md`) — nobody
revisited it once the vocabulary it was waiting on actually landed. FR-51's
own text anticipated this exact steady state and named it explicitly:
*"Difficulty is read from the story's declaration; an undeclared story
takes the mechanical default."* Every story today is the undeclared case —
by omission, not by decision.

A second, related gap: nothing escalates a model mid-story based on how
the attempt is actually going. `max_dev_attempts` and `max_review_cycles`
are flat ceilings (`core/policy.py` defaults `2`/`3`) regardless of
trajectory — there is no "attempt 1 struggled on sonnet, try attempt 2 on
opus" and no "review keeps finding issues, escalate the review model
further." This is absent on both sides of the seam: Marshal resolves a
tier once per launch, before `bmad-loop run` is ever spawned, never
per-attempt; and the vendored `bmad_loop` 0.9.0 engine itself only couples
`task.attempt` to a budget check (`escalation.py:68`
`budget_left = task.attempt < policy.limits.max_dev_attempts`) — nothing
in the engine re-selects a model based on attempt count. A story that is
visibly struggling pays the same model cost on its last attempt as its
first.

## What it looks like when real

- At least one project's `marshal-policy.toml` carries a real
  `model_tier_map` (real difficulty classes mapped to real per-stage
  models), and at least one story carries a real declared `difficulty:`
  value that measurably changes what `render_policy_toml` writes —
  provable by diffing a rendered `policy.toml` with and without the
  declaration.
- Some convention exists for a story to acquire a difficulty at all —
  authored (a human or `bmad-create-story` names it against a stated
  rubric) or derived (a heuristic over spec size / epic / prior attempt
  history, the same signals FR-14's budget advisory already reasons
  about). Which one is a downstream design decision, not settled here.
- A story that is genuinely struggling — repeated dev attempts, repeated
  review cycles — can get bumped to a stronger model without an operator
  hand-editing the rendered policy mid-run and relaunching. The bump is a
  floor-raise on top of whatever the declared tier already picked, never a
  silent downgrade.
- The run-level batching granularity FR-51 already accepted as v1 behavior
  (one difficulty governs a whole launch; a mismatched story is reported,
  never silently ignored — `upstream-register.json`'s own
  `per-story-model-tiering` entry) is not relitigated here.

## Constraints

- No new tiering *mechanism*. `model_tier_map`'s shape, `render_policy_toml`'s
  tier-batching, and `cli/spin.py`'s difficulty-resolution chain are already
  built and correct — this Dream is about feeding them real data and closing
  the retry-side gap, not rebuilding what Story 6.1 shipped.
- Whatever triggers a retry escalation must be derived from journal/attempt
  facts the fold already accumulates (AD-26), never a new hand-maintained
  flag — the same discipline every other supervisor-facing signal in this
  codebase already follows.
- A model change, declared or escalated, is journaled with the same
  intent/outcome discipline (AD-28) every other supervisor action already
  uses — never a silent substitution an operator has to notice by reading a
  transcript.

## Realization log

- **2026-08-11** — Captured during an investigation into why bmad-loop-driven
  unattended runs cost more and move slower than a single supervised
  `bmad-quick-dev` session, and what Marshal itself could do about it. Direct
  read of `core/policy.py`, `adapters/harness_bmadloop.py`, `cli/spin.py`, and
  `core/spec_difficulty.py` confirmed FR-51's full consumption chain (Story
  6.1) is built, tested, and wired into `marshal factory spin` — the gap is
  purely on the input side. Grep across every loop-home project's
  `marshal-policy.toml` and every story spec under
  `_bmad-output/projects/*/planning-artifacts/specs/*.md` returned zero real
  `model_tier_map` entries and zero `difficulty:` declarations. The retry/
  escalation half was confirmed absent in both Marshal's own code and the
  vendored `bmad_loop==0.9.0` package
  (`.pixi/envs/local-recipes/lib/python3.14/site-packages/bmad_loop/escalation.py:68`).
  No existing FR, story, or `upstream-register.json` entry covers either gap.
  Queued as a Dream rather than patched by hand — `core/policy.py`,
  `adapters/harness_bmadloop.py`, and `cli/spin.py` were deliberately left
  untouched pending the Spec/story chain.
- **2026-08-14** — Realized — decomposed 2026-08-11 as Stories 3.11 (FR-182) and 3.12 (FR-183), both shipped and ledger-done; `marshal-policy.toml` now carries real `model_tier_map` entries. Status flipped and FR-182/183 backfilled into the PRD by the 2026-08-14 dream-backlog chain audit. Residual is operational adoption: stories declaring `difficulty:`.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — Status kept `realized`; the
  **facts around it are corrected, and CAP-2 is the live gap.** CAP-1 **is fed** since 2026-08-13
  (Story 3.11): 57 story specs across six stations declare a `difficulty:` (marshal 41, atlas 4,
  doctor 4, mason 4, scribe 3, steward 1), `marshal-policy.toml:326-336` and pyforge-atlas's
  `:168-178` carry real `model_tier_map` tables, and two live dispatch journals resolved
  `"model": "composer-2.5-fast"` (marshal 28.24 on 2026-09-02; atlas 21.9 on 2026-09-01) through
  `core/dispatch.py:220-232 resolve_dispatch_model` at `cli/dispatch.py:1400`. The claim that "no
  story declares a `difficulty:` and no project populates a tier map" — carried in this Dream's
  README row and in the Unifying Strategy's realization table — is false as of today.
  **What is genuinely unrealized:** six of eight stations have no tier map and journal `"model":
  null` (verified on mason 13.1, 2026-09-02 and steward 43.6, 2026-09-03), and **CAP-2's
  retry-triggered floor-raise is unreachable** — `cli/spin.py:2268-2277 _apply_retry_escalation`
  fires only in `run_resume`, while `cli/dispatch.py` and `core/dispatch.py` contain no floor-raise
  call at all. `marshal factory dispatch` has been the live engine since ~2026-08-22. Both halves are
  marshal **Story 33.6**. Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.
- **2026-09-16** — Folded into [[marshal-token-economy]] (operator-ruled token-savings
  consolidation) and archived in place. Prior status: `realized`. The Spec
  (`spec-adaptive-model-tiering`) stays live and remains the contract; the
  narrative continues in the parent's § Fold (2026-09-16).
