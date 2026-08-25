---
title: 'Liquibase on the channel (operator gate)'
type: 'chore'
created: '2026-08-25'
status: 'done'
baseline_revision: '1e3c1f95dbd0ead43ad389d2497cda3c63079bcc'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-unifying-strategy-2026-08-24/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-unifying-strategy-2026-08-24/prd.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** CAP-9 / FR-21 cannot start production DDL until Liquibase 5.0.4+ with a vendored PostgreSQL JDBC driver is on the platform env the image consumes. Recipe authoring is operator-owned and already published on SelfExplainML.

**Approach:** Declare `liquibase >=5.0.4` and `liquibase-postgresql >=42.7.13` on `[feature.python-agent-platform]` (same env as 26.3; inherited by `platform-dev`), prove the env solves, and add a policy test that reds if the liquibase pin vanishes or the lock selects `<5.0.4`.

## Boundaries & Constraints

**Always:** Pins live on `feature.python-agent-platform.dependencies` so both `python-agent-platform` and composed `platform-dev` consume them. Workspace channels stay `conda-forge` + `SelfExplainML`. Do not rebuild published packages (`liquibase` 5.0.4; `liquibase-postgresql` 42.7.13 with JDBC under `share/liquibase/lib`). Spec path is `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward`. After `pixi.toml` change: `pixi project export conda-environment -e build > environment.yaml` and update `pixi.lock`. Cite FR-21 / canopy AD-16.

**Block If:** `pixi install -e python-agent-platform` cannot solve from those channels without authoring or rebuilding recipes.

**Never:** Author or rebuild recipes. Introduce a new Containerfile/image. Helm Job / DML-only app role (Story 27.2). `sqlmigrate` CI gate (27.3). Test-runner rewrite (27.4). Start 27-2, 27-3, 27-4, or 12-7. `import pyforge` under `src/platform/`. `scripts/bmad-switch`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy pins | Live `pixi.toml` python-agent-platform deps | `liquibase` is `>=5.0.4`; `liquibase-postgresql` is `>=42.7.13` | Missing name fails the test |
| Liquibase pin removed | Same table with `liquibase` deleted | Assertion fails | Named missing package |
| JDBC pin removed | Same table with `liquibase-postgresql` deleted | Assertion fails | Named missing package |
| Loose liquibase floor | `liquibase` spec is `>=5.0.3` | Assertion fails | Must keep `>=5.0.4` |
| Lock liquibase 5.0.4+ | `pixi.lock` python-agent-platform URLs | Every `liquibase` version is `>=5.0.4`; JDBC package present | Missing liquibase fails |
| Lock liquibase 5.0.3 | Synthetic lock URL for 5.0.3 | Assertion fails | Must not select `<5.0.4` |

</intent-contract>

## Code Map

- `pixi.toml` -- `[feature.python-agent-platform.dependencies]` after the 26.3 OpenFeature pins; `platform-dev` env already composes this feature; do not duplicate pins on `[feature.platform-dev]` or `platform-ci-test` (Liquibase is a CLI, not a pytest import)
- `pixi.lock` -- `environments.python-agent-platform` (and `platform-dev` after compose) package URLs
- `environment.yaml` -- regenerate from `build` env only (CLAUDE.md always-on rule)
- `docs/reference/library-llms-full.md` -- mention `liquibase` / `liquibase-postgresql` so `llms-full-check` sees the new names
- `src/platform/tests/policy/readers.py` -- reuse `pixi_manifest()` + `pixi_env_conda_urls()`
- `src/platform/tests/policy/test_liquibase_channel_policy.py` -- NEW: matrix above; parse lock versions with the exact package name (hyphenated `liquibase-postgresql` must not split on the inner hyphen)
- Never: `src/platform/deploy/charts/` Job templates; `sqlmigrate`; test-runner; `src/platform/**` importing `pyforge.*`; `recipes/`

## Tasks & Acceptance

**Execution:**
- `pixi.toml` -- pin `liquibase = ">=5.0.4"` and `liquibase-postgresql = ">=42.7.13"` on python-agent-platform
- `pixi.lock` -- `pixi install -e python-agent-platform` must exit 0
- `environment.yaml` -- `pixi project export conda-environment -e build > environment.yaml`
- `docs/reference/library-llms-full.md` -- document the two names
- `src/platform/tests/policy/test_liquibase_channel_policy.py` -- pins + lock version gate including synthetic failure cases

**Acceptance Criteria:**
- Given the package on the channel the platform env consumes, when the env solves, then S-27.2 may start.
- Given `pixi install -e python-agent-platform`, when it runs, then it exits 0 with Liquibase 5.0.4+ and vendored PostgreSQL JDBC from SelfExplainML.
- Given the policy suite, when the liquibase pin vanishes or the lock selects `<5.0.4`, then the test fails.

## Spec Change Log

## Review Triage Log

### 2026-08-25 — Implementation self-review (dispatch; no nested reviewers)

- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none. Confirmed: no recipes/, no Containerfile, no Helm Job, no `import pyforge` under `src/platform/`. `pixi install -e python-agent-platform` exit 0; lock selects liquibase 5.0.4 + liquibase-postgresql 42.7.13 (SelfExplainML). Policy 6/6 green. `environment.yaml` re-exported; `build` env unchanged so the file is byte-identical.

## Design Notes

The host image builder runs `pixi install --frozen -e python-agent-platform` (`src/platform/Containerfile`). `platform-dev` already composes that feature, so one pin table covers image + local Tier-1. Published: `liquibase` 5.0.4 (`run: openjdk >=17` from conda-forge); `liquibase-postgresql` 42.7.13 (JDBC vendored into `share/liquibase/lib` for the air gap). FR-21's live `runInTransaction=false` demonstration is Story 27.2, not this gate. `openjdk` is a run-dep of the liquibase package — do not add a second JDK pin unless the solve requires it.

## Verification

**Commands:**
- `pixi install -e python-agent-platform` -- expected: exit 0
- `pixi project export conda-environment -e build > environment.yaml` -- expected: derived file committed
- `pixi run -e platform-ci-test -- python -m pytest src/platform/tests/policy/test_liquibase_channel_policy.py -v` -- expected: all pass (cwd may be `src/platform`)
- `pixi run -e local-recipes llms-full-check` -- expected: no new undocumented-dep for liquibase names (pre-existing catalog truncation is out of this story)

## Auto Run Result

Status: done

`pixi install -e python-agent-platform` exit 0. Lock selects `liquibase` 5.0.4 and `liquibase-postgresql` 42.7.13 from SelfExplainML. Policy suite 6/6 green. Did not start 27-2.
