---
title: 'Adaptive tiering is fed on all eight stations, and the floor-raise reaches dispatch'
type: 'feature'
created: '2026-09-09'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: true
final_revision: '63e9987529c90e150cb46e703075c0b1f9231304'
context:
  - ../../../../../../_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-adaptive-model-tiering/SPEC.md
  - ../../../../../../_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/SPEC.md
warnings: []
deferred: []
baseline_revision: '78fc2be72b980c64725efdb6764e1f74e57d7e32'
---

<intent-contract>

## Intent

**Problem:** CAP-1 tiering works on marshal and atlas but six stations ship empty `model_tier_map` tables, so factory dispatch resolves `"model": null` for their stories. CAP-2 floor-raise exists only on spin resume (`_apply_retry_escalation`); factory dispatch never raises a struggling story's model on retry.

**Approach:** Copy marshal's canonical `model_tier_map` into the six remaining station policy files (last in file). Wire dispatch retry escalation by counting prior failed runs for the story, comparing to `max_dev_attempts`, floor-raising dev→review model at launch, and journaling `escalated`/`from_model`/`to_model` on the dispatch-launch intent. Fix the three specs with empty `difficulty:` frontmatter.

## Boundaries & Constraints

**Always:** Reuse Story 6.1/3.11/3.12 tier resolution and `evaluate_retry_escalation`'s `>= max_dev_attempts` threshold semantics — never re-implement spin's on-disk policy.toml write path on dispatch (dispatch has no loop-home policy file). Floor-raise only, never downgrade. `model_tier_map` must remain the last tables in each marshal-policy.toml.

**Never:** Change vendored bmad_loop, rewrite `render_policy_toml` tier batching, or add per-story mid-run model switching.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Tier map populated | Station policy has `model_tier_map`, story declares `difficulty: medium` | `resolve_dispatch_model` returns non-null dev model from map | No error |
| Tier map empty | No `model_tier_map` in station policy | Model resolves null (unchanged baseline) | No error |
| First dispatch | Zero prior failed runs for story | Base dev model, `escalated: false` in journal | No error |
| Struggling retry | Prior failed runs ≥ `max_dev_attempts`, dev≠review models | Launch model is review tier; journal `escalated: true`, `from_model`, `to_model` | No error |
| Already escalated | Base dev already equals review model | No escalation; journal omits escalation detail | No error |
| Empty difficulty spec | Frontmatter `difficulty: ''` | Treated as undeclared by regex — spec corrected to real value | Lint via corrected specs |

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-{doctor,herald,mason,scribe,steward,warden}/planning-artifacts/marshal-policy.toml` — append canonical `[model_tier_map.*]` block last; update stale "ABSENT" comment
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml:358-367` — canonical tier map to copy
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_retry.py` — add pure `apply_dispatch_retry_floor_raise` + `should_dispatch_retry_escalate`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py:220-232` — extend launch model resolution with optional escalation inputs
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py:536-547,1390-1402,1685-1695` — count prior failures, apply escalation, journal payload
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py:1898-2022` — read-only reference for spin parity
- `tests/unit/test_dispatch.py` — dispatch escalation integration tests
- `tests/unit/test_dispatch_retry.py` — pure escalation unit tests (new or extend)
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-11-{1,2,3}-*.md:10` — fix empty `difficulty:`

## Tasks & Acceptance

**Execution:**
- `_bmad-output/projects/pyforge-{doctor,herald,mason,scribe,steward,warden}/planning-artifacts/marshal-policy.toml` — append `[model_tier_map.heavy/medium/easy]` matching marshal — CAP-1 fleet adoption
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_retry.py` — pure floor-raise helpers — CAP-2 dispatch path
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py` — escalation-aware model resolution — single owner for dispatch model pick
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` — count prior failed runs, wire escalation, journal fields — live dispatch surface
- `tests/unit/test_dispatch_retry.py` — unit tests for pure helpers — matrix coverage
- `tests/unit/test_dispatch.py` — end-to-end dispatch_once escalation journal test — AC proof
- `spec-11-1`, `spec-11-2`, `spec-11-3` frontmatter — set `difficulty: medium` — empty difficulty hygiene

**Acceptance Criteria:**
- Given any of the eight stations with a populated `model_tier_map` and a story declaring a mapped difficulty, when factory dispatch resolves the launch model, then the model is non-null from the tier map
- Given a story with prior failed dispatch attempts ≥ `max_dev_attempts` and dev≠review models in the tier map, when factory dispatch launches again, then the launch model is the review-tier model and the dispatch-launch intent journals `escalated: true` with `from_model` and `to_model`
- Given spec-11-1/11-2/11-3, when difficulty frontmatter is read, then no spec carries `difficulty: ''`

## Spec Change Log

## Review Triage Log

### 2026-09-09 — Review pass
- verdicts: 12 findings — high 0, medium 4, low 3, false 2, maybe-false 3
- findings:
  - `[medium]` `[patch]` Failure count must reset after a COMPLETED dispatch — fixed `_count_prior_failed_dispatch_attempts` to stop at last success
  - `[medium]` `[patch]` CAP-1 needed compose-path proof — added `test_newly_fed_station_policies_compose_non_null_dispatch_model`
  - `[medium]` `[patch]` Missing first-attempt non-escalation test — added `test_dispatch_does_not_escalate_on_first_attempt`
  - `[medium]` `[patch]` Stale `model_tier_map` ABSENT header comments — updated six station policy headers
  - `[low]` `[patch]` Type guards on escalation threshold inputs — hardened `should_dispatch_retry_escalate`
  - `[low]` `[reject]` Journal omits `escalated: false` on non-escalated launches — intentional omission matches spin payload shape
  - `[low]` `[reject]` spec-33-6 lacks own `difficulty:` — story spec is orchestration metadata, not a dispatched story
  - `[false]` `[reject]` Review-cycle ceiling missing — dispatch CAP-2 deliberately uses failed-run count only per spec boundaries
  - `[false]` `[reject]` `escalated_stories` missing — dispatch has no deferred-story snapshot; not applicable
  - `[maybe-false]` `[defer]` Virtual FsPort without on-disk run dirs — production dispatch uses LocalFs; revisit if port tests expand
  - `[maybe-false]` `[defer]` Double journal scan per launch — optimization only; behavior correct
  - `[maybe-false]` `[defer]` Other fleet specs still carry empty difficulty — out of story scope (only 11-1/2/3 required)

## Auto Run Result

Status: done

**Summary:** Story 33.6 lands CAP-1 fleet tier-map adoption on six stations and wires CAP-2 dispatch retry floor-raise (dev→review) with journal evidence, plus empty-difficulty fixes on spec-11-1/2/3.

**Files changed:**
- Six station `marshal-policy.toml` files — canonical `[model_tier_map.*]` blocks appended last
- `core/dispatch_retry.py` — pure escalation helpers
- `core/dispatch.py` — `resolve_dispatch_model_with_retry_escalation`
- `cli/dispatch.py` — prior-failure counting (reset on COMPLETED) and launch journaling
- `tests/unit/test_dispatch_retry.py` — new unit + compose regression tests
- `tests/unit/test_dispatch.py` — escalation integration tests
- `spec-11-1/2/3` — `difficulty: medium`
- `spec-33-6-…md` — story contract + review artifacts

**Review:** 4 patches applied (4 medium); 3 rejected; 3 deferred.

**Follow-up review recommended:** true — three medium patches landed on first pass (failure-streak reset, compose-path CAP-1 proof, first-attempt baseline test); unverified risk that real multi-run dispatch journals always record COMPLETED/FAILED verdicts consistently across harness profiles.

**Verification:** 24 targeted pytest cases passed (`test_dispatch_retry.py` + dispatch escalation tests).

**Residual risks:** Review-cycle axis and `escalated_stories` remain spin-only by design; fleet-wide empty `difficulty:` beyond spec-11 trio not addressed.

## Verification

**Commands:**
- `pixi run -e pyforge-marshal pyforge-marshal-test -- tests/unit/test_policy.py -k model_tier_map -v` — expected: policy composition still green
