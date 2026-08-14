---
spec: adaptive-model-tiering
status: shipped
owner-dream: docs/dreams/adaptive-model-tiering.md
surface:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/spec_difficulty.py
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml
sources:
  - ../../../../../../docs/dreams/adaptive-model-tiering.md
open_questions:
  - "Which signal decides a story's difficulty when nobody hand-authors one: an authored convention (a human or bmad-create-story names it against a stated rubric) or a derived heuristic (spec size / epic / prior attempt history)? Left to the downstream story."
  - "Does CAP-2 need Marshal to intervene mid-run (kill+relaunch the harness session under a re-rendered policy), or can it work entirely through the existing deferral-then-resume path (Story 3.7), where cli/spin.py::run_resume already re-resolves and re-renders model tiering before detach-launching 'bmad-loop resume'? Determines whether CAP-2 is a live in-run mechanic or a resume-time one."
  - "What attempt-count or review-cycle threshold should trigger a retry escalation, and is it a fixed default or itself policy-configurable?"
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what
> to build, test, and validate. `docs/dreams/adaptive-model-tiering.md` is listed in `sources:`
> for narrative rationale this contract intentionally omits.

# FR-51's model tiering is fully wired and never turned on

## Why

A pain to solve. Every `bmad-loop` dev pass in every loop home runs on the same flat model
(`sonnet`), every review pass on the same flat model (`opus`) —
`adapters/harness_bmadloop.py:278,290` — regardless of how hard a story actually is or how a
given attempt is going. FR-51's full consumption chain to fix this already shipped (Story 6.1):
`core/policy.py`'s `model_tier_map` (`:272,480-498`), `render_policy_toml`'s tier-batching
(`harness_bmadloop.py:450-459`), and `cli/spin.py`'s difficulty resolution
(`_story_declared_difficulty`/`_resolve_governing_difficulty`/`_resolve_model_tiering`,
`:420-533+`) are built, tested, and wired into `marshal factory spin`. But grep across every
one of the 8 loop-home projects' `marshal-policy.toml` and every story spec finds zero real
`model_tier_map` entries and zero declared `difficulty:` values — the mechanism has never been
fed. A related gap: nothing escalates a struggling story's model on retry — `max_dev_attempts`/
`max_review_cycles` are flat ceilings with no "attempt 2 gets a stronger model" path, in either
Marshal or the vendored `bmad_loop==0.9.0` engine (`escalation.py:68` only gates a budget check
on attempt count).

## Capabilities

- **CAP-1**
  - **intent:** A project's `model_tier_map`, once populated with real `{difficulty:
    {stage: model}}` entries, and a story that declares a real `difficulty:` value, together
    determine the model `render_policy_toml` writes for that launch.
  - **success:** Given a project with a populated `model_tier_map` and an in-scope story
    declaring a difficulty present in that map, the rendered `policy.toml` differs from the
    undeclared baseline in exactly the mapped stages — provable by diffing rendered output with
    and without the declaration.
- **CAP-2**
  - **intent:** A story showing it is genuinely struggling (repeated dev attempts, repeated
    review cycles) gets a floor-raised model without an operator hand-editing `policy.toml` and
    relaunching.
  - **success:** Given a story that exhausts an attempt/cycle threshold, its next attempt runs
    under a model at least as strong as its declared tier (or the baseline, if undeclared) — and
    the change is journaled with the same intent/outcome discipline every other supervisor
    action uses.

## Constraints

- **Always:** treat the existing tiering mechanism (`model_tier_map`'s shape, tier-batching,
  `cli/spin.py`'s resolution chain) as complete and correct — build on it, never re-implement it.
- **Always:** one difficulty governs a whole launch (FR-51's run-level batching); a mismatched
  story in a batch is reported, never silently ignored (`_resolve_governing_difficulty`'s
  existing behavior) — this Spec does not ask for per-story mid-run granularity.
- **Always:** a retry-escalation trigger is derived from journal/attempt facts the fold already
  accumulates (AD-26) — never a new hand-maintained flag.
- **Always:** an escalation is a floor-raise only, on top of whatever the declared tier already
  picked — never a downgrade.

## Non-goals

- **Not** a new tiering mechanism, a new policy key shape, or a rewrite of Story 6.1's
  resolution chain.
- **Not** a per-story (sub-launch) model selection — `bmad_loop` supports run-level selection
  only (FR-51's own v1 assumption, `upstream-register.json`'s `per-story-model-tiering` entry);
  unchanged here.
- **Not** a prescription of how a story acquires a difficulty (authored vs. heuristic) — a
  downstream story's design call.
- **Not** a change to the vendored `bmad_loop` package.

## Success signal

A project (starting with `pyforge-marshal` itself) has a real, non-empty `model_tier_map` in
its tracked `marshal-policy.toml`, and at least one story has declared a real `difficulty:`
value whose resolution is visible in a rendered `policy.toml` and journaled at launch. A story
that struggles through repeated attempts is demonstrably running its later attempt(s) under a
stronger model than its first, journaled, without any operator hand-edit.

## Open Questions

- Which signal decides a story's difficulty when nobody hand-authors one: an authored convention
  or a derived heuristic? Left to the downstream story.
- Does CAP-2 need Marshal to intervene mid-run, or can it work through the existing
  deferral-then-resume path (Story 3.7), where `run_resume` already re-resolves and re-renders
  model tiering before relaunching? Determines whether CAP-2 is a live in-run mechanic or a
  resume-time one.
- What attempt/cycle threshold triggers a retry escalation, and is it fixed or policy-configurable?
