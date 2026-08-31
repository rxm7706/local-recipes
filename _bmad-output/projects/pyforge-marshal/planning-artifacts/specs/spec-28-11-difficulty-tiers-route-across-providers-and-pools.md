---
title: 'Difficulty tiers route across providers and pools (Story 28.11, Epic 28)'
type: 'feature'
created: '2026-08-30'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: heavy
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/model-economics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings:
  - This story extends the FR-51 seam's vocabulary. It must not mint a second
    model-selection mechanism, and it must respect spec-adaptive-model-tiering's shipped
    constraints (run-level batching; escalation is floor-raise only). Routing is a
    launch-time decision, never a mid-run model change.
  - The Copilot subscription is Pro today with a downgrade pending (operator clarification
    2026-08-30): while Pro lasts its premium-request quota can drive the copilot harness as
    a secondary pool, but routing must not depend on it persisting — when the downgrade
    lands it becomes inline/chat only and stops being a story-session harness. Treat it as
    a fall-through candidate, never a preferred pool.
---

<intent-contract>

## Intent

**Problem:** The tier map's current vocabulary maps difficulty to a bare model alias
within one harness. The estate's real price ladder spans providers — economy-class input
is ~50× cheaper than frontier-class — and some tokens are effectively pre-paid
(Cursor Ultra / Claude Max subscription allowances), but nothing can express "easy stories
go to the cheap provider, drain the flat-rate pool first."

**Approach:** Extend the `model_tier_map` stage-entry vocabulary so an entry can name a
(harness profile, model) pair, and teach launch resolution (spin and dispatch — one
composition site, Story 28.1's discipline) to apply it: resolve difficulty → tier →
(harness, model), prefer subscription-marked pools (catalog from Story 28.10) before
metered API, journal which pool served, fall through when a pool is exhausted or
unavailable. The class ladder (easy → economy, medium → standard, heavy → frontier) is
data in `model-economics.md`, not code.

## Acceptance Criteria

- Given a populated cross-provider tier map, when a story with a declared difficulty
  launches on either engine, then the launched (harness, model) pair matches the map —
  proven by a rendered-launch diff with and without the declaration.
- Given a tier whose preferred pool is subscription-marked, when the launch resolves, then
  that pool is preferred, the serving pool is journaled, and an exhausted/unavailable pool
  falls through to the next preference — never a blocked run.
- Given the implementation, when inspected, then resolution flows through the existing
  FR-51 seam (`model_tier_map` → difficulty resolution → rendered launch) — no second
  selection mechanism, run-level batching unchanged (a mixed batch is reported, never
  silently split).
- Given any routing outcome, when the review stage resolves, then it never lands below the
  policy-declared review floor, and no escalation path introduced here downgrades a model
  (spec-adaptive-model-tiering constraint).

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger
key `28-11-difficulty-tiers-route-across-providers-and-pools`.

**Block If:** A change would re-implement Story 6.1's difficulty-resolution chain, select a
model outside the FR-51 seam, or change a model mid-run.

**Never:** Routing review below the declared review floor. A preferred-pool dependency on
the transitional Copilot Pro plan (fall-through candidate only; post-downgrade it exits the
routing table). A live pool-balance query to a provider (pool exhaustion is observed from
launch failures / declared limits, not scraped).

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` (`model_tier_map` vocabulary + validator `_valid_model_tier_map`)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py` (`_resolve_model_tiering`) + `core/dispatch.py`/`cli/dispatch.py` (`resolve_dispatch_model` — note its `next(iter(tier_map))` unmapped-difficulty fallback; keep spin/dispatch agreement, see marshal-policy.toml's 2026-08-30 medium-entry comment)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_profile.py` + `data/harness_profiles/*.toml` (the harness half of the pair)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` (`render_policy_toml` tier-batching)

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated
(rendered-launch diff, pool preference + fallthrough, FR-51-seam-only, review-floor hold).
Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 28.11 and spec-marshal-token-economy CAP-12. Deps S-28.10 (catalog
carries pool membership). The concrete candidates per class live in `model-economics.md` §
The difficulty ladder — treat them as the operator's declared data; the code knows classes
and pairs, never vendor SKU lists. A (harness, model) pair that names a harness with no
installed CLI degrades with a named finding at admission (same doctrine as the layer
degradation in Story 28.1–28.3), never a mid-run surprise.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, including this story's own new/updated test coverage.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (no undeclared dependency surface).

## Spec Change Log

- 2026-08-30: drafted from the operator's 2026 model/cost catalog (CAP-12 minted same day; multi-provider + subscription-pool routing over the existing FR-51 seam)
