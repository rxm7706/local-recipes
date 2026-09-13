---
spec: cursor-native-tier-map
status: ready
created: "2026-09-13"
updated: "2026-09-13"
owner-dream: docs/dreams/cursor-native-tier-map.md
surface:
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
  - ../../../../../../docs/dreams/cursor-native-tier-map.md
open_questions: []
---

> **Canonical contract.** Derived 2026-09-13 from `.memlog.md`. Do not hand-edit.

# SPEC — The tier map names Cursor models with an explicit harness

## Why

**A mandate to meet.** The four-verb campaign runs in Cursor. The fleet
`model_tier_map` still says bare `sonnet` / `opus` (the 2026-09-12
fail-safe revert). That is honest for a Claude adapter and silent about
the Cursor Ultra ladder this IDE actually uses. Unattended `factory drain`
must not start until the map uses the explicit `{ harness, model }` form
for Cursor names, so a composer/grok string cannot land on
`claude --model` (the 28.29 / fails-safe incident).

## Capabilities

- **CAP-1**
  - **intent:** All eight stations' `model_tier_map` easy/medium/heavy
    stages name Cursor-catalogued models as inline tables with
    `harness = "cursor"`.
  - **success:** `parse_stage_entry` on each stage yields
    `StageCandidate(harness="cursor", model=…)` where `model` is one of
    `composer-2.5`, `composer-2.5-fast`, `grok-4.6`. No bare Cursor
    model string remains in those maps.
- **CAP-2**
  - **intent:** The fail-safe stays: a Cursor-catalogued model is never
    written onto a `claude` adapter.
  - **success:** Existing provider-mismatch tests remain green.

## Constraints

- Bare-string shorthand stays reserved for the base `[adapter]` provider.
- Do not invoke `marshal factory drain` to land this Spec.
- Do not change `[context]` layers, `dispatch.max_parallel`, or Story 33.11.
- Do not flip Epic 44 `blocked` keys.

## Non-goals

- Repairing Cursor headless dispatch (28.29).
- Live price fetch. Adding `grok-4.6` from the 2026-08-30 snapshot is in scope.

## Success signal

Eight `marshal-policy.toml` files declare the Cursor Ultra ladder as
inline tables; a Claude-adapter render still uses the sonnet/opus
baseline; this IDE is the executor until a later Story proves drain.

## Assumptions

- Easy = `composer-2.5`, medium = `grok-4.6`, heavy = `composer-2.5-fast`
  (catalogued spend / wall-clock), matching the campaign's Cursor class
  table.
