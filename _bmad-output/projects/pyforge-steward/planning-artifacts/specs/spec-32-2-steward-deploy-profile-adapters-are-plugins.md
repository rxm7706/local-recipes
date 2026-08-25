---
title: Steward deploy-profile adapters are plugins
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-25'
baseline_revision: ce01ee04d6f35157974b29f959d477164301dca5
review_loop_iteration: 0
followup_review_recommended: true
context:
  - src/shared/packages/pyforge-core/src/pyforge/core/hooks.py
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-32-1-shared-hook-spec-and-plugin-registration-in-pyforge-core.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/deploy.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Harness, Splunk, StorageGRID, EPLX GHA, Tachyon, and Jira are named as Steward deploy-profile backends, but they are not plugins on the FR-43 contract. Swapping a vendor would fork the Golden Path instead of registering a replacement.

**Approach:** Publish Steward's deploy-profile `HookSpec` on `pyforge.core.hooks`. Register today's six backends as default plugins. Optional vendors (including Tachyon) stay off the Golden Path Pixi task and local/CI. None of these plugins publishes a PR quality-gate verdict (Warden owns that).

## Boundaries & Constraints

**Always:** Consume `pyforge.core.hooks` (`HookSpec`, `HookPlugin`, `PluginRegistry`, `publish_verdict`, `SecondVerdictError`, `ENTRY_POINT_GROUP`). Canonical group is `pyforge.core.hooks` only. Golden Path Pixi task remains `pyforge-steward-test` (do not rename). Write this spec under `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` — never `scripts/bmad-switch`. Tachyon is a production LLM adapter plugin (`required_in_ci=False`).

**Block If:** S-32.1 symbols (`HookSpec`, `PluginRegistry`, `SecondVerdictError`, `publish_verdict`) are missing from installed `pyforge.core.hooks`.

**Never:** A parallel `pyforge.steward.hooks` / `pyforge.steward.plugins` group. `import pluggy`. Vendor SDKs as package or pixi-feature deps. `pyforge.*` under `src/platform/`. Rewriting `deploy.py` dashboard/perimeter/static verbs. Warden Epic 9 scanners or a competing PR-gate verdict. Changing Pixi task names, Golden Path artifact identity, parent infra kinds, or host import boundary. Stories 12-7, 26-3, 26-4, 27.x.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Default plugins | In-tree registry / steward `pyproject.toml` | Six plugins on `pyforge.steward.deploy_profile`, owner `steward`: harness, splunk, storagegrid, eplx-gha, tachyon, jira | No error |
| Optional vendor off | `run_golden_path(enabled=())` or omit one vendor id | Golden Path succeeds; omitted plugin is not invoked | No error |
| Tachyon not in CI | Default Golden Path / `pyforge-steward-test` cmd and steward feature deps | Tachyon not required; `required_in_ci` is false | No error |
| Alternate vendor | Extra plugin same spec, `plugin_id="alt-cd"` registered in-process | Selected without forking steward | Unknown id → `PluginError` |
| Second verdict | Default plugin `publish_verdict` on Warden `pyforge.warden.pr_gate` | `SecondVerdictError` | Owner-matched steward spec allowed |
| No PR-gate publish | `deploy_profiles.py` sources | Never calls `publish_verdict` | AST pin |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-core/src/pyforge/core/hooks.py` — **read-only** FR-43 API.
- `src/shared/packages/pyforge-core/tests/meta/test_plugin_registration_conformance.py` — **read-only**; no parallel steward group.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy.py` — **read-only**. Today's dashboard/perimeter/static duty stays; this story does not fork it into vendor CD.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy_profiles.py` — **new**. `DEPLOY_PROFILE_HOOK_SPEC`, six default plugins, `register_default_deploy_profile_plugins`, `select_deploy_profile_plugin`, `run_golden_path`. Record-only `around` unless `context["backends"][plugin_id]` is a callable inject.
- `src/shared/packages/pyforge-steward/pyproject.toml` — `[project.entry-points."pyforge.core.hooks"]` for the six defaults. No new runtime deps.
- `src/shared/packages/pyforge-steward/tests/unit/test_deploy_profile_plugins.py` — **new**. I/O matrix + pixi Golden Path task/deps scan.
- `pixi.toml` `[feature.pyforge-steward.tasks.pyforge-steward-test]` — **read-only** Golden Path Pixi task (pytest; no vendor requirement).
- `src/platform/` — **do not add** `pyforge.*`.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy_profiles.py` -- hook spec + six default plugins + Golden Path runner -- FR-45 surface
- `src/shared/packages/pyforge-steward/pyproject.toml` -- declare six plugins on `pyforge.core.hooks`
- `src/shared/packages/pyforge-steward/tests/unit/test_deploy_profile_plugins.py` -- I/O matrix + optional-vendor Golden Path pins

**Acceptance Criteria:**
- Given today's deploy/profile backends, when they are extracted, then each registers as a default plugin on the FR-43 contract (`pyforge.core.hooks`, spec `pyforge.steward.deploy_profile`).
- Given an optional vendor plugin disabled, when the Golden Path Pixi task / `run_golden_path` runs, then it does not fail.
- Given local/CI, when Tachyon is absent, then the Golden Path still succeeds (Tachyon remains a production LLM adapter plugin).
- Given any of these plugins, when they would publish a PR quality-gate verdict, then `SecondVerdictError` is raised and sources never call `publish_verdict`.

## Design Notes

All six shipped plugins are **optional at runtime** (`optional=True`). They are **default** in the sense that Steward ships them registered; they are not required to run the Golden Path. `run_golden_path(enabled=())` is the CI/local default: register defaults, invoke none of the vendors, succeed. `select_deploy_profile_plugin(plugin_id=...)` swaps a vendor without a process fork.

Tachyon's `required_in_ci` is False. Do not add a Tachyon client to dependencies.

Do not `PluginRegistry.invoke` every vendor on Golden Path — that would require them. Select/enable explicitly.

Do not close estate-wide `DW-OM-2026-08-24` from this story.

## Verification

**Commands:**
- `pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_deploy_profile_plugins.py -q` -- expected: all pass
- `pixi run -e pyforge-core pytest src/shared/packages/pyforge-core/tests/meta/test_plugin_registration_conformance.py -q` -- expected: pass (canonical group only)
- `pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests -q` -- expected: pass

## Spec Change Log

## Review Triage Log

### 2026-08-25 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 2, low 1)
- defer: 0
- reject: 12
- addressed_findings:
  - `[medium]` `[patch]` `run_golden_path` no longer ignores unknown `enabled` ids; raises `PluginError`
  - `[medium]` `[patch]` a caller-supplied registry is not re-seeded with the six defaults
  - `[low]` `[patch]` pixi.toml walk-up requires repo-root `CLAUDE.md` so the member-package pixi.toml is not used

## Auto Run Result

Status: done

Summary: Steward deploy-profile adapters (Harness, Splunk, StorageGRID, EPLX GHA, Tachyon, Jira) register as default plugins on `pyforge.core.hooks` (`pyforge.steward.deploy_profile`, owner steward). Optional vendors including Tachyon are not required for the Golden Path Pixi task (`pyforge-steward-test`) or local/CI. None of these plugins publishes a Warden PR-gate verdict.

Files changed:
- `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy_profiles.py` — hook spec, six default plugins, select + Golden Path runner
- `src/shared/packages/pyforge-steward/pyproject.toml` — six entry points on `pyforge.core.hooks`
- `src/shared/packages/pyforge-steward/tests/unit/test_deploy_profile_plugins.py` — I/O matrix
- this spec

Review: 3 patches (2 medium, 1 low; follow-up score 7). 0 deferred. Rejected rewriting `deploy.py`, adding vendor SDKs, renaming Pixi tasks, `load_entry_points` as the Golden Path path (would load every station's hooks), a CLI verb, and closing `DW-OM-2026-08-24`.

Verification:
- `test_deploy_profile_plugins.py` — 26 passed
- `test_plugin_registration_conformance.py` — 10 passed
- `pyforge-steward/tests` — 964 passed, 1 skipped (pre-patch; focused 26 after patches)

Residual: `run_golden_path` is in-process register, not wheel entry-point load. Real vendor backends remain injectable stubs. Estate `DW-OM-2026-08-24` left open.
