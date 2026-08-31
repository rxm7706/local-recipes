---
title: 'Extract the build-engine hook'
type: 'feature'
created: '2026-08-24'
status: 'done'
baseline_revision: 'e96b852227b36bb28cbc62cd44dd5071057081fe'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/src/shared/packages/pyforge-core/src/pyforge/core/hooks.py'
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-32-1-shared-hook-spec-and-plugin-registration-in-pyforge-core.md'
warnings: []
---

<intent-contract>

## Intent

**Problem:** Mason's native recipe build is wired to today's rattler-build path (CFE `build_native`) with no FR-43 hook spec, so swapping to conda-build (or a sandbox) would fork the mason process. A green mason build must not be treated as a Warden PR-gate verdict.

**Approach:** Publish `pyforge.mason.build_engine` (owner `mason`) on `pyforge.core.hooks`. Register rattler-build as the default plugin and conda-build as an alternate. Native `recipe.build` selects one plugin and runs `around`; today's backend stays the default `next`. Do not rewrite conda-forge-expert.

## Boundaries & Constraints

**Always:** Consume `pyforge.core.hooks` (`HookSpec`, `HookPlugin`, `PluginRegistry`, `publish_verdict`). Canonical entry-point group is `pyforge.core.hooks` only. Default engine name is `rattler-build`. Native `recipe.build` goes through plugin `around` whose default `next` is existing `cfe.build_native`. Write this spec under `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/` literally. `BMAD_ACTIVE_PROJECT=pyforge-mason` only.

**Block If:** Implementing the hook would require editing `.claude/skills/conda-forge-expert/` or CFE scripts (`native-build.sh`, `build-locally.py`).

**Never:** A parallel `pyforge.mason.hooks` / `pyforge.mason.plugins` group. Rewriting conda-forge-expert. Publishing a mason build outcome via `publish_verdict` for a Warden-owned spec (or any non-mason owner). Docker/`--docker` path changes. CLI engine-select flags. Real conda-build/rattler-build subprocesses in this story's new tests. Scorecard metrics.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Default plugin | In-tree registry, no engine name | Selected plugin is rattler-build (`is_default`) | No error |
| Alternate register | Extra plugin with same spec, `engine_name="sandbox"`, registered in-process | `select(..., name="sandbox")` returns that plugin; mason process not forked | Unknown name → `PluginError` |
| Entry points | mason `pyproject.toml` group `pyforge.core.hooks` | Names `rattler-build` and `conda-build` plugins; no `pyforge.mason.hooks` | Conformance scan stays green |
| Around next | Default plugin `call("around", {next})` | `next` runs; context `engine` is `rattler-build` | Missing `next`: still invoked |
| Not a PR verdict | Successful build object + `publish_verdict(HookSpec(pyforge.warden.pr_gate, warden), mason plugin, …)` | `SecondVerdictError`; build result is not a Warden verdict | Owner-matched publish only for mason's own spec |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-core/src/pyforge/core/hooks.py` -- **read-only** FR-43 API (`HookSpec`, `PluginRegistry`, `publish_verdict`, `SecondVerdictError`, `ENTRY_POINT_GROUP`, `HOOK_POINTS`).
- `src/shared/packages/pyforge-mason/src/pyforge/mason/engines/build_hooks.py` -- **new** mason process hook: `BUILD_ENGINE_HOOK_SPEC`, `RattlerBuildPlugin`, `CondaBuildPlugin`, `build_engine_registry()`, `select_build_engine_plugin()`.
- `src/shared/packages/pyforge-mason/pyproject.toml` -- `[project.entry-points."pyforge.core.hooks"]` for both plugins (quoted group name).
- `src/shared/packages/pyforge-mason/src/pyforge/mason/recipe.py` -- native `build()` selects default plugin and `call("around", …)` with `next` bound to current `cfe.build_native`; docker branch unchanged.
- `src/shared/packages/pyforge-mason/src/pyforge/mason/cfe.py` -- **read-only**; still the sole CFE caller (AD-3).
- `src/shared/packages/pyforge-mason/tests/unit/test_build_hooks.py` -- **new**; cover I/O matrix.
- `src/shared/packages/pyforge-mason/tests/unit/test_recipe.py` -- native `build()` still returns fixture `BuildResult`; engine stamped rattler-build via hook.
- `src/shared/packages/pyforge-core/tests/meta/test_plugin_registration_conformance.py` -- **read-only**; mason must not add a parallel group.
- `.claude/skills/conda-forge-expert/` -- **do not touch**.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-mason/src/pyforge/mason/engines/build_hooks.py` -- add hook spec + two plugins + select/registry helpers (engines port, AD-12).
- `src/shared/packages/pyforge-mason/pyproject.toml` -- declare both plugins on `pyforge.core.hooks`.
- `src/shared/packages/pyforge-mason/src/pyforge/mason/recipe.py` -- wrap native build in default-plugin `around`.
- `src/shared/packages/pyforge-mason/tests/unit/test_build_hooks.py` -- unit-test the I/O matrix.
- `src/shared/packages/pyforge-mason/tests/unit/test_recipe.py` -- keep native/docker fixture round-trips green.

**Acceptance Criteria:**
- Given the replaceable build-engine layer, when the hook spec lands, then today's rattler-build backend is the default plugin.
- Given an alternate engine plugin registered on the same spec in-process, when selected by name, then it runs without forking the mason process.
- Given a successful mason build result, when a plugin would publish it as a PR quality-gate verdict (`pyforge.warden.pr_gate` / owner `warden`), then `SecondVerdictError` is raised.
- Given mason `pyproject.toml`, when scanned, then plugins register on `pyforge.core.hooks` only.

## Design Notes

Select **one** plugin, then `call` it. Do not `PluginRegistry.invoke` every build-engine plugin (that would run rattler-build and conda-build together). `engine_name` is mason-local; FR-43 `HookPlugin` stays `hook_spec` / `owner` / `call`.

Default `around` calls `context["next"]` so today's CFE native path stays the backend. conda-build is registered so an operator can select it later; this story does not spawn `conda-build`.

Plugin classes are required by `HookPlugin` (same shape as `DummyPlugin`); they live under `engines/` so the use-case layer stays subprocess-free.

## Spec Change Log

## Review Triage Log

### 2026-08-24 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 9: (high 0, medium 3, low 6)
- defer: 0
- reject: 14
- addressed_findings:
  - `[medium]` `[patch]` Restored standalone `test_build_docker_happy_path_against_fake_cfe_root`; native hook spy no longer swallows docker coverage.
  - `[medium]` `[patch]` `_BuildEnginePlugin.call` raises `PluginError` on unknown hook points (`HOOK_POINTS`).
  - `[medium]` `[patch]` `select_build_engine_plugin` raises when more than one `is_default` plugin is registered.
  - `[low]` `[patch]` Removed unused `PluginRegistry` import and leftover `Any`/`MutableMapping` imports in `test_build_hooks.py`.
  - `[low]` `[patch]` Removed duplicate `assert result.mode == "native"`.
  - `[low]` `[patch]` Module docstring cites FR-45, not FR-43.
  - `[low]` `[patch]` Alternate conda-build test asserts `engine_name == "conda-build"`.
  - `[low]` `[patch]` `_SandboxPlugin` subclasses `_BuildEnginePlugin` instead of copying `call`.
  - `[low]` `[patch]` Verification commands include the core plugin-registration conformance scan.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

Summary: Extracted mason's native build engine onto `pyforge.core.hooks` as `pyforge.mason.build_engine` (owner mason). rattler-build is the default plugin; conda-build is registered as an alternate. Native `recipe.build` runs default-plugin `around` with today's `cfe.build_native` as `next`. A mason `BuildResult` cannot be published as a Warden PR-gate verdict. conda-forge-expert was not rewritten.

Files changed:
- `src/shared/packages/pyforge-mason/src/pyforge/mason/engines/build_hooks.py` — hook spec, plugins, select/registry
- `src/shared/packages/pyforge-mason/pyproject.toml` — both plugins on `pyforge.core.hooks`
- `src/shared/packages/pyforge-mason/src/pyforge/mason/recipe.py` — native path through default plugin `around`
- `src/shared/packages/pyforge-mason/tests/unit/test_build_hooks.py` — I/O matrix
- `src/shared/packages/pyforge-mason/tests/unit/test_recipe.py` — native stamp + restored docker happy path
- this spec

Review: 9 patches (3 medium, 6 low; follow-up score 15). 0 deferred. Rejected live conda-build spawn, CLI engine flags, `load_entry_points` of the whole shared group (parallel-station risk), `BuildResult.engine`, calling `publish_verdict` from `recipe.build`, docker-through-hook, and treating pid-equality as insufficient for the in-process register AC.

Verification: focused 202 passed; full mason `-m "not slow"` 1553 passed, 3 deselected.

Residual: selecting `conda-build` is registry-only this story; `recipe.build` always uses the default plugin. A real conda-build backend is later work.
