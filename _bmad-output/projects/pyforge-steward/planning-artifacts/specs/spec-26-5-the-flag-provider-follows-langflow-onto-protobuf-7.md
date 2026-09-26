---
title: 'The flag provider follows langflow onto protobuf 7'
type: 'chore'
created: '2026-09-26'
status: 'done'
baseline_revision: '1206f34bc0b2cb39b1104d40e1009532b08424f9'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-26-3-openfeature-packages-on-the-channel-operator-gate.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** Story 26.3 held `openfeature-provider-flagd` at `>=0.5.0,<0.5.1` because 0.5.2 is the protobuf-7 build and langflow's `a2a-sdk` then capped protobuf below 7. The 2026-09-26 `pixi upgrade` pass raised langflow to `>=1.12.3`, whose closure (openlayer -> pyarrow -> libabseil 20260526) is protobuf-7-only. With the 0.5.0 pin the `platform-dev` / `python-agent-platform` solve fails; with 0.5.2 it succeeds (protobuf 7.35.1, a2a-sdk 1.1.5).

**Approach:** Operator decision 2026-09-26: keep langflow `>=1.12.3` and move the provider to `>=0.5.2`. Flip the 26.3 policy test's provider expectation (spec and lock) from "0.5.0 only" to "0.5.2 or later"; everything else 26.3 asserts stays.

## Boundaries & Constraints

**Always:** Pins stay on `[feature.python-agent-platform.dependencies]`. `cachebox` stays `>=5.2.3,<6`. The four OpenFeature packages stay required. Cite canopy:FR-33 / canopy:AD-16.

**Never:** Author or rebuild recipes. Touch Story 26.4's FILE provider. Change the Liquibase policy (Story 27.1): `liquibase-postgresql >=42.7.13` stays, because conda-forge's same-named 5.0.4 package is Liquibase's dialect extension and carries no JDBC driver.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Provider spec | Live `pixi.toml` python-agent-platform deps | `openfeature-provider-flagd` is `>=0.5.2` | Any other spec fails |
| Spec admits 0.5.0 | Spec `>=0.5.0` | Assertion fails | Must require the protobuf-7 build |
| Lock provider | `pixi.lock` python-agent-platform URLs | Every provider version is `>=0.5.2` | Missing or 0.5.0 fails |
| Lock selects 0.5.0 | A locked 0.5.0 URL | Assertion fails | Names 0.5.0 |

</intent-contract>

## Code Map

- `pixi.toml` -- `[feature.python-agent-platform.dependencies]`: `openfeature-provider-flagd = ">=0.5.2"`, langflow `>=1.12.3`
- `pixi.lock` -- `python-agent-platform` / `platform-dev` resolve provider 0.5.2 and langflow 1.12.3
- `src/platform/tests/policy/test_openfeature_channel_policy.py` -- `PROVIDER_SPEC = ">=0.5.2"`; `_assert_lock_provider_is_052_or_later`; drift tests now red on 0.5.0
- `docs/reference/library-llms-full.md` -- provider entry `(>=0.5.2)`

## Tasks & Acceptance

**Execution:**
- Policy test and provider pin updated as above.

**Acceptance:**
- `pixi run -e pyforge-guild platform-ci-local --test`: the Policy suite passes.
- `pixi lock` solves every environment.

## Outcome

Landed with rxm7706/local-recipes PR #1610 (conda-forge graduations and floor refresh). The Policy suite passes locally.
