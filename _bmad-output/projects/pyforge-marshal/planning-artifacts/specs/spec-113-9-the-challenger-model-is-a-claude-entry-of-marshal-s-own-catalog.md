---
title: "113.9: the challenger model is a Claude entry of marshal's own catalog"
type: 'fix'
created: '2026-11-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/model_cost.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/claude.toml
---

<intent-contract>

## Intent

**Problem:** the challenger's model rule fails outside marshal and lets non-Claude ids through. Line numbers are at
`03a7aff5d9`.

- `_cataloged_models` and `render_refusals`
  (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py:172-200`) accept any provider's
  `model_cost_catalog` id, read from the `--project` station's own policy. Only marshal's policy declares a catalog, and
  an empty catalog refuses, so the other seven stations cannot pass the render (EGM audit MAR-M-Z3).
- The challenger always runs on the packaged claude profile, which passes the id verbatim to `claude --model`; a Gemini
  or OpenAI catalog id passes the render and fails at spawn, and no alias (`sonnet`, `opus`, `haiku`, `default`) is
  normalised (MAR-M-D5).
- "The dispatching session's own model" is defined only in code: `session_models`
  (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py:152-164`) reads `model_tier_map` and never
  the `[adapter]` and `[adapter.review]` models (MAR-D-C3).
- The `[challenge]` comment example in `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml:1014`
  names `claude-fable-5-1`, marshal's frontier dev and review model (`:1058-1059`), so the render refuses its own
  documented example.

**Approach:**
- **One catalog, Claude only (operator ruling 2026-11-01).** The challenger reads marshal's own `model_cost_catalog`
  (from `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml`'s composed policy) for every
  `--project`, and `render_refusals` accepts only an id for which `provider_declaring_model(catalog, model)`
  (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/model_cost.py:95`) is `anthropic`, reusing the
  `MRS-DISP-043` precedent. Any other id refuses with the usage code and a reason naming the provider.
- **Aliases.** The id is checked against the claude profile's `[model_list]` aliases
  (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/claude.toml:70-76`) and normalised
  before the same-model check, so an alias of a station model is the station model.
- **Session models.** `session_models` adds the station's `[adapter]` and `[adapter.review]` models to its
  `model_tier_map` models. The dispatch readiness hook compares against the run's resolved launch model, which
  `cli/dispatch.py` passes to `readiness_for_dispatch`.
- **The documented example.** The `marshal-policy.toml` comment names `sonnet-5` (an Anthropic catalog entry). The file
  stays without a `[challenge]` block. It is a governed path: reconcile it on the memlog of every Spec
  `spec-surface-check` names, then stamp each scoped.
- **The contract follows the code.** The memlog events for MAR-M-Z3, MAR-M-D5 and MAR-D-C3 and the operator's decision
  are already on `spec-pyforge-marshal` (commit `7dde4a0202`). Re-derive CAP-299 with `bmad-spec`: the challenger is
  Claude-only on the packaged claude profile (memlog deviation 3), reviewers inherit its `--model`, "session model"
  means the station's `model_tier_map` plus its adapter models, and the repo default never carries `[challenge]`. Then
  the cascade re-stamp and the scoped stamp.
- **`type: fix`, no flag** (`spec-feature-flag-governance` Q1); the block is read only while
  `pyforge.marshal.egm_policy_block` is on.

Ledger key: `113-9-the-challenger-model-is-a-claude-entry-of-marshal-s-own-catalog`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- **`spec-pyforge-marshal` CAP-299** (FR-241): the `[challenge]` block; `model` names a catalog entry and never the
  station's own model.
- This story mints no CAP. Origin: `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md`
  (cluster MAR-CL5; findings MAR-M-Z3, MAR-M-D5, MAR-D-C3); the operator's ruling of 2026-11-01 on the catalog.

## Acceptance Criteria

- **AC1 — Claude only.** A `[challenge].model` naming a Gemini, OpenAI or Cursor catalog id, or an id absent from
  marshal's catalog, refuses at render with the usage code and a reason; an Anthropic catalog id renders
  (`src/shared/packages/pyforge-marshal/tests/unit/test_challenge_core.py`).
- **AC2 — Every station.** A `--project` other than `pyforge-marshal` whose own policy declares no catalog renders with
  an Anthropic id from marshal's catalog (`src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`).
- **AC3 — Never the station's model.** The station's own frontier model, an `[adapter]` or `[adapter.review]` model, and
  an alias that normalises to any of them each refuse; in a dispatch, the run's resolved launch model refuses.
- **AC4 — The example.** The `marshal-policy.toml` comment example names `sonnet-5`, the file carries no `[challenge]`
  block, and `_bmad-output/policy-defaults.toml` carries none.
- **AC5 — The contract.** CAP-299 is re-derived by `bmad-spec` (both self-validate passes logged);
  `spec-surface-check`, `chain-currency-sweep-check` and `chain-completeness-check` exit 0.
- **AC6 — Mutation.** Dropping the provider filter fails AC1's Gemini case; dropping the adapter models from
  `session_models` fails AC3's. Restore each.
- **AC7 — The suites.** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` green.

## Boundaries & Constraints

**Always:**
- Reuse `provider_declaring_model`; never parse the catalog a second way.
- Keep the challenger on the packaged claude profile.

**Ask first:**
- If alias normalisation makes `sonnet-5` collide with a station's adapter model, which Anthropic catalog entry the
  example names instead.

**Never:**
- Never ship a `[challenge]` block in the repo default or in `marshal-policy.toml`; never fall back to the author's
  model; never hand-edit `SPEC.md`.
- A story that fails its independent review twice drops to `backlog` and the landing PR proceeds without it (operator
  ruling 2026-11-01).

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-marshal` CAP-299 (FR-241).

Parent: `spec-pyforge-marshal` CAP-299 (a fix; no CAP minted)

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-11-01 (the audit lands) entry.
- Research: `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md` (MAR-CL5).
- Epic: Epic 113.
- Ledger key: `113-9-the-challenger-model-is-a-claude-entry-of-marshal-s-own-catalog`.
- Deps: —.
- Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py`,
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/model_cost.py`,
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py`,
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py`, their tests,
  `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml` (comment only) and the re-derived
  `SPEC.md`; within `marshal-policy.toml` `[epic_surfaces]."113"`.
- Minted 2026-11-01 by the EGM fleet audit (marshal Story 113.7); implemented in the Story 113.7 landing PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).

**Run before the push:**
- `pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_challenge_core.py src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py` — expected: pass.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Auto Run Result

Status: backlog

Summary: not yet implemented.

## Spec Change Log

- 2026-11-01: minted from the EGM fleet audit (`research/egm-audit-2026-11-01.md`, cluster MAR-CL5: MAR-M-Z3, MAR-M-D5,
  MAR-D-C3) and the operator's ruling of 2026-11-01 (marshal's own `model_cost_catalog` for every `--project`, filtered
  to Anthropic entries; implement in the Story 113.7 landing PR). `type: fix`, no flag, no CAP.

## Review Triage Log

- (none yet)
