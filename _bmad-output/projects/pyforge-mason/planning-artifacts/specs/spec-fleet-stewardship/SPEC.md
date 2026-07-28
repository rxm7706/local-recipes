---
spec: fleet-stewardship
status: shipped
owner-dream: docs/dreams/fleet-stewardship.md
program: regenerable-factory (Wave 4)
surface:
  - recipes/**
surface-drift: exempt   # recipes are the product line — per-recipe governance is the CFE workflow, not spec re-derivation
companions:
  - ../../../../../../docs/specs/feedstock-platform-expansion.md    # adopted: the per-feedstock procedural core (legacy Tier-1, in force)
  - ../../../../../../docs/specs/feedstock-failure-remediation.md   # adopted: the red-PR remediation loop (legacy Tier-1, in force)
  - ../../../../../../docs/specs/feedstock-refresh.md               # adopted: the two-track bulk refresh campaign (legacy Tier-1, in force)
open_questions: []
---

# SPEC — fleet stewardship (the recipes/ fleet)

## Why

Tend every feedstock we can touch: ~900 local recipe mirrors backing 769+
conda-forge feedstocks — refresh tracks, platform expansion, failure
remediation, recurring waves, never finished. Owner: Mason (Doctor monitors).
The Dream is perpetual; this kernel binds the fleet into the governance map
without freezing a product line that changes by design.

## Capabilities

- **CAP-1 — the local mirror as source of truth.** Intent: every
  `recipes/<name>/` is a faithful, buildable mirror (recipe + conda-forge.yml
  + patches + LICENSE sidecars) edited FIRST, built locally, then pushed to
  fork/feedstock. Success: the local-mirror-first rule holds (auto-memory
  `feedback_local_mirror_first_then_verify_then_push`); the repo-wide
  recipe.yaml parse audit stays green.
- **CAP-2 — per-recipe internal metadata.** Intent: every local recipe
  carries the `cfe-*` block (identity, cached decisions, build record,
  cf-status), stripped on push (G60/G62). Success: the cfe meta-tests green;
  strip verified on pushed artifacts.
- **CAP-3 — the recurring campaigns.** Intent: refresh (Track A/B),
  platform expansion, and failure remediation run as parameterized waves per
  the three adopted workflow specs. Success: each wave's evidence lands in
  the owning spec's Worked Examples / Current State.

## Constraints

- Per-recipe change control is the CFE 10-step loop + its gates — a recipe
  edit never requires touching this kernel (`surface-drift: exempt` above is
  the explicit encoding; coverage still binds).
- CLAUDE.md Rules 1 and 2 apply to every campaign wave.

## Non-goals

- Governing the factory machinery (that is `spec-packaging-factory`).
- Absorbing the three workflow specs' procedures — they stay authoritative
  where they live until their efforts ship.

## Success signal

`spec_surface_check` green with `recipes/**` governed (coverage) and the
drift exemption printed, never silent; campaign waves keep landing evidence
in the adopted specs.
