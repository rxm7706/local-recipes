---
title: 'The graduated compression ladder (Story 28.6, Epic 28)'
type: 'feature'
created: '2026-08-30'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: heavy
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/integration-layers.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** A story approaching its token ceiling today has exactly one future: the
stop-retry-defer ladder kills it. There is no softer intervention between "spending
normally" and "dead".

**Approach:** The supervisor gains a compression rung below the existing idle/kill ladder:
as a story's weighted spend approaches its ceiling (threshold from the `[context]` block),
compression aggressiveness is raised, and the model floor may be lowered — only through the
existing FR-51 tiering seam. Escalation is journaled like every other supervisor act.

## Acceptance Criteria

- Given a story crossing the escalation threshold, when the supervisor evaluates the ladder,
  then compression escalation strictly precedes stop-retry-defer — proven by a test on
  ladder ordering.
- Given an escalation, when it applies, then the model floor changes only via the existing
  FR-51 `model_tier_map` seam — no second model-selection mechanism.
- Given any escalation level, when the story proceeds, then no gate or reviewer is skipped
  and the contract artifacts (spec/ACs/verdicts) remain uncompressed.
- Given an escalation event, when it happens, then it is journaled with the threshold facts
  that triggered it.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger
key `28-6-the-graduated-compression-ladder`.

**Block If:** A change would reproduce the `DW-AD23-3` shape (a cap/escalation silently
dropping real reviewer-recommended work), skip review, or bypass the FR-51 seam.

**Never:** Escalation as a kill substitute — the existing ceilings stay the final backstop.
A second model-selection mechanism.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/supervise.py` (idle/budget ladder precedent)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/` (tick)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` (threshold key in the `[context]` block)

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated
(ladder ordering, FR-51-seam-only, no-skip guarantee, journaled escalation). Land this spec
in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 28.6 and spec-marshal-token-economy CAP-8. Sibling to the idle-strand
ladder (Story 3.5) — same graduated-response idiom, new rung. Retry-triggered model
floor-raise (Story 3.12) is the precedent for touching tiering from supervision.

## Spec Change Log

- 2026-08-30: drafted from epics.md Epic 28 for fleet-drain preflight (Dream/Spec chain: docs/dreams/marshal-token-economy.md → spec-marshal-token-economy)
