---
title: 'Map existing Kedro hooks to CAP-18'
type: 'chore'
created: '2026-08-24'
status: 'done'
baseline_revision: e96b852227b36bb28cbc62cd44dd5071057081fe
review_loop_iteration: 0
followup_review_recommended: true
context:
  - src/shared/packages/pyforge-core/src/pyforge/core/hooks.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/settings.py
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-32-1-shared-hook-spec-and-plugin-registration-in-pyforge-core.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Atlas already runs Kedro pipeline/project hooks, but they are not named on the shared `pyforge.core.hooks` contract (FR-43). Without a map, a later story will grow a second plugin API or a pipeline PR-gate.

**Approach:** Audit the live Kedro hook surfaces onto FR-43. Register today's four `settings.HOOKS` backends as default `pyforge.core.hooks` plugins. Do not rebuild Kedro. Explicit N/A with reason for points that do not map.

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-atlas/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-atlas`. Keep `settings.HOOKS` the Kedro runtime (same four classes, same `@hook_impl` methods). Canonical group is `pyforge.core.hooks` only. Owner of atlas process specs is `atlas`. Warden remains the sole PR quality-gate verdict.

**Block If:** A change would replace Kedro's hook manager, add `import pluggy` in atlas sources, add a `pyforge.atlas.hooks` / `pyforge.atlas.plugins` entry-point group, or introduce a CI job that publishes pipeline PR pass/fail beside Warden.

**Never:** Rebuild the pipeline. Grow a pipeline PR-gate book. Publish a competing PR verdict from an atlas plugin. Change TTL/admission/observability/validation behaviour. Touch other stations' ledgers. Run `scripts/bmad-switch` or `bmad-loop`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Complete map | Kedro `hooks.specs` methods + atlas `@hook_impl` | Every spec method is mapped or N/A-with-reason; mapped methods match live `settings.HOOKS` | Incomplete table fails the unit test |
| Default plugins | Installed `pyforge.core.hooks` entry points | Four backends load as default plugins; `invoke(..., spec_name=atlas spec)` runs `before`/`after` | Unknown point → `PluginError`; dummy not invoked |
| Around N/A | `invoke("around", spec_name=atlas spec)` | Plugin no-ops (may call `context["next"]`); Kedro is not wrapped | Not an error |
| Second verdict | Atlas plugin `publish_verdict` for a Warden-owned spec | `SecondVerdictError` | Owner-matched atlas spec is allowed |
| No PR-gate job | `.github/workflows/` + atlas pixi tasks | No new atlas job publishes PR pass/fail beside Warden | Adding such a workflow fails the guard test |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-core/src/pyforge/core/hooks.py` — **read-only** FR-43: `HookSpec`, `HookPlugin`, `PluginRegistry`, `HOOK_POINTS` (`before`/`after`/`around`), `ENTRY_POINT_GROUP`, `publish_verdict` / `SecondVerdictError`. `invoke` requires `spec_name`.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/settings.py:54-59` — live runtime: `HOOKS = (ProjectHooks(), AtlasObservabilityHooks(), DataValidationHooks(), RunAdmissionHooks())`. **Do not reorder to "fix" CAP-18.** Admission ordering stays `tryfirst` in `admission.py`.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/hooks.py:45-57` — `ProjectHooks.after_catalog_created`
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/observability.py` — `before/after_pipeline_run`, `on_pipeline_error`, `before/after_node_run`, `on_node_error`
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/validation.py` — `DataValidationHooks.after_node_run` only
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/admission.py` — `before/after_pipeline_run`, `on_pipeline_error` with `tryfirst=True`
- Kedro 1.5 `kedro.framework.hooks.specs` — **12** methods on the five `*Specs` classes (catalog 1, dataset 4, context 1, node 3, pipeline 3). Completeness is vs the live module, not a hardcoded count. Atlas implements 7 `@hook_impl`s (5 map to FR-43 `before`/`after`; 2 `on_*_error` are N/A as FR-43 points).
- `src/shared/packages/pyforge-atlas/pyproject.toml` — already depends on `pyforge-core`; **add** `[project.entry-points."pyforge.core.hooks"]` only (never `pyforge.atlas.hooks`)
- `src/shared/packages/pyforge-core/tests/meta/test_plugin_registration_conformance.py` — sibling scan; atlas must not `import pluggy` or declare a parallel group
- `src/shared/packages/pyforge-atlas/tests/catalog/test_no_inline_io.py` — new module is auto-scanned; no dagster/`kedro_mcp`/HTTP clients
- `.github/workflows/` — **read-only**; do not add an atlas PR-gate workflow

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/cap18.py` -- mapping table + HookSpec constants + thin HookPlugin wrappers for the four live backends -- FR-43 registration without replacing Kedro
- `src/shared/packages/pyforge-atlas/pyproject.toml` -- declare default plugins on `pyforge.core.hooks`
- `src/shared/packages/pyforge-atlas/tests/test_cap18_kedro_hook_map.py` -- cover the I/O matrix (completeness, entry-point load, around no-op, second-verdict, no PR-gate job)

**Acceptance Criteria:**
- Given the live Kedro hook surfaces, when the audit completes, then each named Kedro spec method is mapped to the FR-43 contract or an explicit N/A with reason.
- Given today's backends (`ProjectHooks`, `AtlasObservabilityHooks`, `DataValidationHooks`, `RunAdmissionHooks`), when entry points load, then they remain the default plugins and `settings.HOOKS` still instantiates those same classes.
- Given an atlas plugin, when it would publish a PR pass/fail for a process Warden owns, then `SecondVerdictError` is raised.
- Given CI and pixi tasks, when inspected, then no atlas job publishes a PR pass/fail beside Warden.

## Design Notes

Three atlas-owned specs: `pyforge.atlas.catalog`, `pyforge.atlas.pipeline`, `pyforge.atlas.node`. Kedro `before_*` → `before`; `after_*` → `after`. `around` is N/A: Kedro has no around; wrapping the manager would rebuild Kedro. `on_pipeline_error` / `on_node_error` are N/A as FR-43 points (not in `HOOK_POINTS`); they stay on the existing Kedro backends. Dataset load/save and `after_context_created` are N/A: unused in atlas (TTL uses `after_catalog_created`). Observability spans pipeline + node, so two plugin instances wrap the same backend class (protocol is one `hook_spec` per plugin). `call()` must not require a live Kedro session for the audit tests; do not change hook behaviour.

## Spec Change Log

- 2026-08-24 — Review pass 1: completeness is vs live `*Specs` (12 methods on Kedro 1.5, not a hardcoded 13); dataset N/A reason records the node-hook bypass.

## Review Triage Log

### 2026-08-24 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 0, medium 3, low 3)
- defer: 0
- reject: 18
- addressed_findings:
  - `[medium]` `[patch]` walk every live Kedro `*Specs` class, not a hardcoded five-name tuple
  - `[medium]` `[patch]` every atlas `@hook_impl` must appear on `KEDRO_HOOK_MAP`
  - `[medium]` `[patch]` N/A rows that name backends still `hasattr` those methods
  - `[low]` `[patch]` Code Map count is 12 live Kedro 1.5 methods, not 13
  - `[low]` `[patch]` dataset N/A reason records the node-hook bypass
  - `[low]` `[patch]` loaded atlas plugins' `hook_spec` set equals `ATLAS_HOOK_SPECS`

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

Summary: Audit-only map of live Kedro hook specs onto `pyforge.core.hooks`. Today's four `settings.HOOKS` backends are default plugins. Kedro dispatch is unchanged. No pipeline PR-gate job.

Files changed:
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/cap18.py` — mapping table + FR-43 wrappers
- `src/shared/packages/pyforge-atlas/pyproject.toml` — `pyforge.core.hooks` entry points
- `src/shared/packages/pyforge-atlas/tests/test_cap18_kedro_hook_map.py` — I/O matrix
- this spec

Review: 6 patches (3 medium, 3 low; follow-up score 12). 0 deferred. Rejected rebuilding Kedro, wiring `call()` into `@hook_impl`, mapping third-party kedro-viz plugins, and treating the regex PR-gate guard as a live CI job.

Verification: `test_cap18_kedro_hook_map.py` 10 passed; `test_hooks.py` + `test_admission.py` 115 passed.

Residual: FR-43 `invoke` is registration, not the Kedro hook manager. Entry-point plugin instances are not the `settings.HOOKS` objects.
