---
title: '50.3: `--harness` outranks a dead tier-map harness'
type: 'fix'
created: '2026-09-18'
status: 'in-progress'
baseline_revision: '2f2f407d94ea9e563113c3d8aee5f1f0ade0fa02'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** on 2026-09-18 `marshal factory drain --station herald --harness claude` launched `pyforge-herald-20260918T132400673Z-194af3a0` on cursor/grok-4.6 because the station's `[model_tier_map.medium] dev = { harness = "cursor", … }` led the walk regardless of the flag, cursor's authcheck passed, and the session died in three seconds

**Approach:** an explicit `--harness` (the composed `harness_preference` flag layer, not the policy layer) is present, the walk starts from the flag's profiles and a tier-map harness the flag does not name contributes nothing, and the model is resolved for the harness actually chosen — the tier map's model for that harness when it names one, else the harness's own default — never a foreign model id

## Boundaries & Constraints

**Always:**
- the launch journal records `harness_profile: claude`, `model: sonnet` for the fixture, and without the flag the resolution is byte-identical to today's (tier map leads)
- the fails-safe guard (`provider_declaring_model` mismatch drops the override) is exercised by a test where the flag names claude and the tier map names only a Cursor model

**Never:**
- Do not make the supervisor trust a session's self-report, add a second gate, or re-attribute landed history — the Epic 50 HARD boundaries in `epics.md` bind.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the 2026-09-18 fixture | the real run/journal named in the Given | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-246`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` (the Story 28.11 walk-order block: tier-map harness leads unless an explicit `--harness` flag names a different profile), `.../core/tier_routing.py` (`resolve_tier_launch` takes the flag as an exclusion/override), `.../core/dispatch.py::resolve_tier_harness`, tests with herald's pre-#1458 `marshal-policy.toml` as a fixture.
Ledger key: `50-3-harness-outranks-a-dead-tier-map-harness`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-50-3-harness-outranks-a-dead-tier-map-harness.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- Against herald's pre-#1458 policy fixture, `--harness claude` yields `harness_profile: claude`, `model: sonnet`; without the flag the resolution is byte-identical to today's; the MRS-DISP-043 fails-safe is exercised.
