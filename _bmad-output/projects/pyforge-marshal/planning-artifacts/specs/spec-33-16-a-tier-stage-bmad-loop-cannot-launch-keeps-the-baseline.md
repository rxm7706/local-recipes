---
title: "33.16: A tier stage bmad-loop cannot launch keeps the baseline"
type: 'fix'
created: '2026-11-04'
status: 'done'
baseline_revision: 'ee1a85bdff'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-113-17-drift-refuses-a-model-a-spin-session-can-run-on.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/tier_routing.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** On the seven stations with no `model_cost_catalog`, a `marshal factory spin` launch with a declared difficulty
writes a Cursor model under the `claude` adapter: 21 of the 33 renders of the live policies, `composer-2.5-fast` or
`composer-2.5` in `[adapter.dev]` or `[adapter.review]`. bmad-loop has no Cursor adapter, and `claude --model composer-2.5-fast`
exits 1 with `unrecognized_model`, so the session cannot start. The fail-safe asks only the catalog who owns a model, so it is
silent on those stations, although every one of those tier stages names `harness = "cursor"`. On marshal the catalog catches
it, but the run journal still records the Cursor model in `resolved_models` while the session runs on `sonnet`.

**Approach:** Availability belongs to the resolver. `resolve_tier_launch` already takes a `check_profile` predicate that no
caller passed. `resolve_bmadloop_tier_launch` passes one: a harness with no entry in `BMADLOOP_ADAPTER_BY_PROFILE` is
unavailable. A `dev` stage then falls through to its next launchable candidate, a stage left with none keeps the baseline,
and `resolved_models` names no model on such a harness. Spin, the render's own fallback and `spin_models` all use it, so they cannot
disagree. A `fix` under CAP-79 and CAP-87: no CAP, no flag.

Ledger key: `33-16-a-tier-stage-bmad-loop-cannot-launch-keeps-the-baseline`. Type / Effort / Deps: fix / S / none.

## Acceptance Criteria

- **AC1 — Unavailable to bmad-loop.** `resolve_bmadloop_tier_launch` resolves no stage for a candidate on `cursor` or `devin`,
  and `resolved_models` is empty for such a tier. A harness with a bmad-loop adapter resolves as before.
- **AC2 — Fall-through works.** A list-form `dev` stage of a Cursor candidate then a Claude candidate resolves to the Claude
  candidate. A `review` stage holds to its first candidate's model, so the same list keeps the review baseline.
- **AC3 — The baseline, with no catalog.** With no catalog, a Cursor tier renders `[adapter].model` and `[adapter.review].model`
  at their baselines and writes no `[adapter.dev]`, whether the render resolves the tier itself or spin hands it the resolution.
- **AC4 — The journal tells the truth.** Spin's journaled `resolved_models` is empty for a Cursor tier, and the
  `policy.toml` spin writes holds the baselines.
- **AC5 — The live policies.** Across all eight stations and every tier, the spin render holds no Cursor model, and marshal's
  `frontier` tier still renders `claude-fable-5-1`.
- **AC6 — Dispatch does not change.** `resolve_tier_harness` still resolves the Cursor model: `marshal factory dispatch`
  launches Cursor itself.
- **AC7 — The contract follows.** CAP-79 and CAP-87 name the rule, and the scoped stamp lands.

## Boundaries & Constraints

- The cost of the fix: on the seven stations a declared difficulty now runs `sonnet` dev and `opus` review, where it used to
  fail at launch. That is what those stations already run with no declared difficulty, and what marshal runs today. The token
  ceilings in `[limits]` do not change.
- A bare-string stage names no harness, so only a declared catalog can place it, and on a catalog-less station it still
  renders. CAP-78 keeps bare Cursor strings out of the eight maps, and AC5's test reds if one lands.
- A mixed tier is out of scope: `test_render_policy_toml_differs_with_cross_provider_tier_resolution` pins a `claude` review
  stage's model under a `gemini` adapter, and a `dev` stage that falls through to `gemini` flips the adapter while the
  `[adapter]` baselines stay Claude aliases. bmad-loop can carry a per-stage `[adapter.review] name`, which the render does
  not write. No live tier mixes harnesses.
- Retry escalation now reaches these tiers: `[adapter.dev]` used to shadow the `[adapter].model` it patches. A retried story
  on the seven stations moves from `sonnet` to `opus`.
- Spin raises no new finding. The operator sees an empty `resolved_models` and the journaled `to_model`.

## Binding

- spec-pyforge-marshal CAP-79, CAP-87; Epic 33 (Story 33.15 minted the Cursor tiers).

## Verification

```bash
pixi run --frozen -e pyforge-marshal pyforge-marshal-test
```

</intent-contract>

## Spec Change Log

- 2026-11-04: minted `done` from the probe Story 113.17 ran over the live policies; landed in its own PR.
- 2026-11-04: independent review (a fresh reviewer, on the diff against this spec) passed the fix, with findings. Fixed here:
  the bare-string exception and the `review` stage's fall-through were missing from the claims; the render's third branch,
  which could no longer write anything, is deleted; the live test now fails a station that composes no tier map, checks the
  adapter name and `triage`, and reads `frontier`'s model from the policy; the render docstring names the rule. Not taken: a
  second filter in the render for a caller that hands it a dispatch resolution, because only spin and `spin_models` pass one.
