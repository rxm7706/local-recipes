---
title: 'The model-cost catalog makes spend legible in dollars (Story 28.10, Epic 28)'
type: 'feature'
created: '2026-08-30'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: medium
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/model-economics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** The supervisor tallies weighted tokens, but the operator thinks in dollars.
Worse, the global `cache_read_weight = 0.1` (NFR-14) is exactly right for Anthropic /
OpenAI / Gemini (all publish cache-read at 10% of input) but understates Cursor
first-party models (0.25–0.40) — the tally is silently provider-biased.

**Approach:** Policy gains a declared model-cost catalog (per provider/model: input /
output / cache-read / cache-write per 1M, subscription-pool membership; seed snapshot in
`model-economics.md`). The supervisor's journal entries, `marshal status`, and the CAP-9
benchmark artifact render estimated dollars (declared prices × observed token counts)
alongside weighted tokens. Per-provider token weights derive from the declared ratios,
with today's global constants as the fallback for undeclared providers.

## Acceptance Criteria

- Given a policy with the catalog declared, when the supervisor journals, then per-story
  spend and per-layer savings carry dollar-estimate fields, and `marshal status` renders
  them mid-run.
- Given no catalog declared, when journals or status render, then dollar fields are
  absent — never fabricated, and behavior is byte-identical to today.
- Given a declared provider whose cache-read ratio differs from the global constant, when
  the tally weighs a cache read, then the declared ratio is used — proven by a test
  diffing the weighted totals per provider.
- Given the implementation, when inspected, then no code path fetches prices from a
  network, and no dollar figure feeds a verdict or exit-code change (advisory only).

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger
key `28-10-the-model-cost-catalog-makes-spend-legible-in-dollars`.

**Block If:** A change would fetch prices live, reconcile against a provider billing
dashboard, or turn a dollar figure into a gate.

**Never:** A billing integration. Fabricated estimates for models absent from the catalog
(absent means absent). Rounding that hides the estimate's advisory nature (label estimates
as estimates).

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` (catalog block; composes like every other policy key; `schemas/policy.json`)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/` + `core/supervise.py` (tally weights, journal fields — extends Story 28.4's savings fields)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py` (render)
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/model-economics.md` (seed data, read-only)

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated
(no-catalog byte-identical, per-provider ratio, no-network, advisory-only). Land this spec
in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 28.10 and spec-marshal-token-economy CAP-11. The catalog is declared
policy data with a dated snapshot — the refresh discipline is in `model-economics.md` §
Refresh discipline. Layers on top of Story 28.4's savings fields (deps S-28.1, S-28.4);
Story 28.11 consumes the same catalog for pool-preference routing, so the catalog schema
must carry pool membership even though this story does not route.

## Spec Change Log

- 2026-08-30: drafted from the operator's 2026 model/cost catalog (CAP-11 minted same day; companion model-economics.md is the seed snapshot)
