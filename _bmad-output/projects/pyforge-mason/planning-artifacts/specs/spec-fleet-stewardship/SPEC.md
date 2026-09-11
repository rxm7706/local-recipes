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
  - **verified:** 2026-09-11 — PASS — mechanical re-verification at HEAD b36c8be118: 72 commits touched `recipes/` since 2026-08-10 (Spec claims 70 -- still current, continuous activity); `test_recipe_yaml_parse_audit.py` 6/6 passing.
- **CAP-2 — per-recipe internal metadata.** Intent: every local recipe
  carries the `cfe-*` block (identity, cached decisions, build record,
  cf-status), stripped on push (G60/G62). Success: the cfe meta-tests green;
  strip verified on pushed artifacts.
  - **verified:** 2026-09-11 — PASS (meta-test half only; strip-on-push half not independently re-checked this pass) — mechanical re-verification at HEAD b36c8be118: `test_recipe_yaml_parse_audit.py` (incl. the `cfe-conda-name` duplicate-key guard) 6/6 passing. Did not re-fetch a real published feedstock file to confirm the `cfe-*` block is actually absent post-push this pass -- that half rests on SKILL.md step 8b's documented convention and prior sessions' worked examples, not independently re-verified live here.
- **CAP-3 — the recurring campaigns.** Intent: refresh (Track A/B),
  platform expansion, and failure remediation run as parameterized waves per
  the three adopted workflow specs. Success: each wave's evidence lands in
  the owning spec's Worked Examples / Current State.
  - **verified:** 2026-09-11 — PASS (historical; dormant today, matching the Spec's own 2026-09-09 realization-gate note) — mechanical re-verification at HEAD b36c8be118: confirmed all three adopted workflow specs' last-touch commits still match the documented dates exactly (`feedstock-refresh.md`/`feedstock-failure-remediation.md` at `1aeaf12cee` 2026-07-02, `feedstock-platform-expansion.md` at `1bdd5a2f02` 2026-06-28) -- the dormancy note is still accurate, not stale. The capability's own success criterion (evidence lands when a wave runs) held when waves DID run (Track A Waves B-F, recorded in `feedstock-refresh.md`'s own Current State) -- dormancy is a currency fact already self-documented, not a defect in the capability.

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

## Realization-gate re-read — 2026-09-09

Status stays `shipped` and the Dream stays `realized`. **CAP-1** (local-mirror-first)
and **CAP-2** (`cfe-*` metadata) are exercised continuously — 70 commits touching
`recipes/` since 2026-08-10 across a 7,873-directory tree.

**CAP-3 is DORMANT, and "recurring waves" must not be read as live.** All three
engine specs are untouched since 2026-06/07 — `feedstock-refresh.md` last commit
`1aeaf12cee` (2026-07-02), `feedstock-platform-expansion.md` `1bdd5a2f02`
(2026-06-28), `feedstock-failure-remediation.md` `1aeaf12cee` — Track A Wave H still
lists 179 remaining, and Track B (232) is unstarted.

**Greenfield consequence, consult at 44.8 and not after.** Steward S-44.8 moves only
in-flight and sole-maintainer recipes to `factory/recipes/`; every other `recipes/**`
row reads *stays* and is archived with local-recipes. This Spec's CAP-1 surface is
`recipes/**` with `surface-drift: exempt` — after the cutover most of that surface
lives in an ARCHIVED repo, which changes what "every feedstock we can touch" can mean.
Neither the Dream nor this Spec anticipated it.
