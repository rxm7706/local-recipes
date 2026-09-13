---
spec: dispatch-tier-routing-fails-safe
status: shipped
created: "2026-09-12"
updated: "2026-09-12"
owner-dream: docs/dreams/dispatch-tier-routing-fails-safe.md
surface:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/tier_routing.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml
  - _bmad-output/projects/pyforge-herald/planning-artifacts/marshal-policy.toml
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/marshal-policy.toml
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/marshal-policy.toml
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/marshal-policy.toml
  - _bmad-output/projects/pyforge-mason/planning-artifacts/marshal-policy.toml
  - _bmad-output/projects/pyforge-warden/planning-artifacts/marshal-policy.toml
  - _bmad-output/projects/pyforge-steward/planning-artifacts/marshal-policy.toml
companions: []
sources:
  - ../../../../../../docs/dreams/dispatch-tier-routing-fails-safe.md
open_questions: []
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for
> what to build, test, and validate. `owner-dream` carries the narrative rationale this
> contract intentionally omits.

# SPEC — Dispatch tier-routing resolver fails safe, and fleet-wide defaults stop pointing at a dead harness

## Why

**A pain to solve, live and confirmed.** Marshal's FR-51 model-tier-batching resolver
(`resolve_tier_launch`) can silently produce a hybrid, broken dispatch launch: a real,
working adapter binary (`claude`) paired with another provider's model string
(`composer-2.5-fast`, Cursor's) that adapter was never meant to receive. Confirmed
2026-09-12 by direct execution of the resolver against the live pyforge-marshal policy:
`model_tier_map.heavy.dev = "composer-2.5-fast"` (a bare string, no `harness` key, present
in **all eight** stations' `marshal-policy.toml`) resolves to `harness=None`, so
`spin.py` falls back to the base `claude` adapter name but still writes the Cursor model
into `[adapter.dev].model`. The resulting `claude --model composer-2.5-fast` launch
crashes instantly (0 tokens spent); tmux's `pipe-pane` races the dying window (a race
bmad-loop's own source documents as tolerated, non-fatal); the story is reported merely
"deferred" — no signal anywhere names a policy misconfiguration as the cause. This
silently broke three consecutive dispatch attempts for one story before being traced to
ground truth. Compounding it: Cursor is independently, permanently confirmed dead for
headless dispatch fleet-wide (`spec-28-29-wire-is-dead-for-cursor-...`, shipped
2026-09-10) — so the tier map has pointed every heavy/medium/easy-tier dispatch at a
target that can never work, since at least commit `5e7f8cac4b` (a long-standing latent
defect, not a new regression).

## Capabilities

- **CAP-1**
  - **intent:** The tier-routing resolver never writes a dev/review stage model override
    unless that model's harness is genuinely dispatchable in the current loop home — an
    unresolvable or non-dispatchable harness must fall through to the full baseline
    (`[adapter]`/`[adapter.review]`) rather than partially apply.
  - **success:** A synthetic fixture whose `model_tier_map` stage candidate names a model
    with no resolvable harness (or a harness whose `adapter_binary` check fails) produces
    either the full, unmodified baseline `[adapter]`/`[adapter.review]` config with zero
    stage-level override written, or a distinct, loud finding — never a written
    `[adapter.<stage>].model` that does not belong to the adapter that will actually
    launch.
- **CAP-2**
  - **intent:** Fleet-wide, `model_tier_map`'s heavy/medium/easy `dev`/`review` entries
    resolve to the same models the plain baseline already uses, so no story's dispatch is
    silently routed through a harness (Cursor) that cannot work headlessly.
  - **success:** Re-running the same direct `resolve_tier_launch` / `render_policy_toml`
    probe that found the bug, against all eight stations, shows every governing
    difficulty (heavy, medium, easy) launching with the exact same adapter and model an
    untagged (unmapped-difficulty) story already uses today.

## Constraints

- Never touch `model_cost_catalog`, its pricing display, or the `context.*` compression
  layers — scope is the dev/review model-tier ROUTING resolver and its current default
  config values only.
- Never make a Copilot (or any other harness) adoption decision here — that stays a
  separate, explicit operator call, per `spec-28-29`'s own recorded finding (a live
  2026-08-27 quota failure plus real wrap-composition rework cost, not a free lunch).
- Any FUTURE `model_tier_map` stage entry naming a model from a non-default-adapter
  provider must use the explicit `{harness = "...", model = "..."}` inline-table form
  (already supported by `tier_routing.py::parse_stage_entry`) — the bare-string shorthand
  is reserved for models belonging to the base `[adapter].name`'s own provider, closing
  the exact ambiguity that let Cursor's model land on the `claude` adapter unnoticed.
- Marshal owns the resolver code (`core/tier_routing.py`, `adapters/harness_bmadloop.py`,
  `cli/spin.py`); the eight per-station `marshal-policy.toml` files are data, corrected
  by the same mechanical value change once the resolver-side contract is settled.

## Non-goals

- Deciding whether or when Copilot (or any other harness) becomes a real, live second
  dispatch target — deferred to a separate, explicit operator decision.
- Building the per-station opt-in rollout or preflight-liveness-check machinery for a
  future second harness — follow-on work once a harness is genuinely viable, not scoped
  here.
- Retroactively auditing every historical dispatch that may have silently hit this bug
  before now — this Spec fixes the mechanism and the config going forward, not a history
  audit of past runs.

## Success signal

A `marshal factory spin` on any station, whose governing difficulty resolves to
heavy/medium/easy, launches with the exact same adapter and model an untagged story
already uses — fleet-wide, provable by re-running the same direct resolver probe used to
find the bug. A synthetic unresolvable-harness fixture never again produces a mismatched
stage override.
