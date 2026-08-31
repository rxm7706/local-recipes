---
title: 'OpenFeature packages on the channel (operator gate)'
type: 'chore'
created: '2026-08-25'
status: 'done'
baseline_revision: '62db654dd3b2cf4b1396ad7fd3f102603573c1db'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-unifying-strategy-2026-08-24/ARCHITECTURE-SPINE.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** CAP-13 cannot evaluate flags inside the air gap until OpenFeature libraries and a `cachebox` 5.x pin are on the platform env the image and host consume. Recipe authoring is operator-owned and already published.

**Approach:** Declare the four OpenFeature packages plus `cachebox >=5.1,<6` on `[feature.python-agent-platform]` (inherited by `platform-dev`), prove the env solves, and add a policy test that reds if those pins vanish or the lock selects cachebox 6.

## Boundaries & Constraints

**Always:** Pins live on `feature.python-agent-platform.dependencies` so both `python-agent-platform` and composed `platform-dev` consume them. Workspace channels stay `conda-forge` + `SelfExplainML`. `cachebox` must stay `>=5.1,<6` (conda-forge 5.2.3; do not take 6.x). `openfeature-provider-flagd` must stay `>=0.5.0,<0.5.1` (SelfExplainML 0.5.0 / protobuf 6.x; 0.5.2 needs protobuf 7 and cannot solve with `a2a-sdk`). Spec path is `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward`. After `pixi.toml` change: `pixi project export conda-environment -e build > environment.yaml` and update `pixi.lock`. Cite FR-33 / canopy AD-16.

**Block If:** `pixi install -e python-agent-platform` cannot solve from those channels without authoring or rebuilding recipes.

**Never:** Author or rebuild recipes (`recipes/openfeature-*`, cachebox feedstock). Implement FILE provider / `flags.json` (Story 26.4). Start 26-4 or any 27.x story. `import pyforge` under `src/platform/`. `scripts/bmad-switch`. Pull `cachebox` 6.x.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy pins | Live `pixi.toml` python-agent-platform deps | Four OpenFeature names present; `cachebox` is `>=5.1,<6` | Missing name fails the test |
| Pin removed | Same table with one OpenFeature key deleted | Assertion fails | Named missing package |
| Cachebox 6 spec | `cachebox` spec allows 6.x | Assertion fails | Must keep `<6` |
| Lock cachebox 5 | `pixi.lock` python-agent-platform URLs | Every `cachebox` version is `>=5.1` and `<6` | Missing cachebox fails |
| Lock provider 0.5.0 | `pixi.lock` python-agent-platform URLs | Every `openfeature-provider-flagd` version is `>=0.5.0` and `<0.5.1` | Missing or 0.5.2 fails |
| Provider 0.5.2 spec | `openfeature-provider-flagd` spec allows 0.5.2 | Assertion fails | Must keep `<0.5.1` |

</intent-contract>

## Code Map

- `pixi.toml` -- `[feature.python-agent-platform.dependencies]` (~line 172); `platform-dev` env composes this feature (~line 738); do not duplicate pins on `[feature.platform-dev]`
- `pixi.lock` -- `environments.python-agent-platform` (and `platform-dev` after compose) package URLs
- `environment.yaml` -- regenerate from `build` env only (CLAUDE.md always-on rule)
- `docs/reference/library-llms-full.md` -- mention new dep names so `llms-full-check` stays clean
- `src/platform/tests/policy/readers.py` -- `pixi_manifest()`; add `PIXI_LOCK` + env URL helper
- `src/platform/tests/policy/test_openfeature_channel_policy.py` -- NEW: matrix above; Platform CI `pytest tests/policy`
- Never: `src/platform/config/flags.json`; OpenFeature FILE provider wiring; `src/platform/**` importing `pyforge.*`

## Tasks & Acceptance

**Execution:**
- `pixi.toml` -- pin the four OpenFeature packages + `cachebox = ">=5.1,<6"` on python-agent-platform
- `pixi.lock` -- `pixi install -e python-agent-platform` must exit 0
- `environment.yaml` -- `pixi project export conda-environment -e build > environment.yaml`
- `docs/reference/library-llms-full.md` -- document the five names
- `src/platform/tests/policy/test_openfeature_channel_policy.py` -- pins + lock version gate including synthetic failure cases

**Acceptance Criteria:**
- Given those packages on the platform channel, when the env solves, then S-26.4 may start.
- Given `pixi install -e python-agent-platform`, when it runs, then it exits 0 with OpenFeature from SelfExplainML and cachebox 5.x from conda-forge.
- Given the policy suite, when an OpenFeature pin is removed or cachebox 6 is selected, then the test fails.

## Spec Change Log

- 2026-08-25: Operator published `openfeature-provider-flagd` 0.5.0 (protobuf 6.x) to SelfExplainML. Pin is `>=0.5.0,<0.5.1` so 0.5.2 cannot be selected.

## Design Notes

The host image builder runs `pixi install --frozen -e python-agent-platform` (`src/platform/Containerfile`). `platform-dev` already composes that feature, so one pin table covers image + local Tier-1. Published floors: `openfeature-sdk` 0.10.0, `openfeature-flagd-api` 1.0.0, `openfeature-flagd-core` 1.0.0, `openfeature-provider-flagd` **0.5.0** (`>=0.5.0,<0.5.1`; protobuf 6.33.x — 0.5.2 is on the channel but must not be selected), `cachebox` 5.2.3. Transitive `hatch-protobuf` / `panzi-json-logic` are not declared here unless the solve requires them.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Review Triage Log

### 2026-08-25 — Implementation halt (no review loop)

Env did not solve with provider 0.5.2 vs `a2a-sdk` protobuf `<7`.

### 2026-08-25 — Resume after protobuf unblock

- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

## Auto Run Result

Status: done

`pixi install -e python-agent-platform` exit 0. Lock selects `openfeature-provider-flagd` 0.5.0 (SelfExplainML) and `cachebox` 5.2.3 (conda-forge). Policy suite 7/7 green. Did not start 26-4.
