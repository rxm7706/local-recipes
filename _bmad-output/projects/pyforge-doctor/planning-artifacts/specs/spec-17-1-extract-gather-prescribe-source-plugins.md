---
title: 'Extract gather/prescribe source plugins'
type: 'feature'
created: '2026-08-24'
status: 'done'
baseline_commit: 'e96b852227b36bb28cbc62cd44dd5071057081fe'
baseline_revision: 'e96b852227b36bb28cbc62cd44dd5071057081fe'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/_bmad-output/projects/pyforge-doctor/implementation-artifacts/epic-17-context.md'
  - '{project-root}/src/shared/packages/pyforge-core/src/pyforge/core/hooks.py'
warnings: []
deferred:
  - summary: >-
      Live hygiene true-positive test fails because the cited herald fixture
      is now referenced by spec-9-2; not caused by 17.1.
    evidence: |-
      pyforge-doctor-test: test_live_repo_gather_surfaces_at_least_one_true_positive_naming_a_non_warden_station
      asserts the fixture is unreferenced; spec-9-2 now names it. Unrelated to
      hooks.py / diagnose plugin wiring.
    location: >-
      src/shared/packages/pyforge-doctor/tests/unit/test_sources_hygiene.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** Doctor's gather backends and prescribe pipeline are hard-wired in the station. Swapping a diagnosis source or remedy actuator would fork Doctor instead of replacing a plugin on the shared contract.

**Approach:** Publish Doctor-owned gather and prescribe hook specs on `pyforge.core.hooks`, register today's backends as the default plugins, and route `diagnose` gather/prescribe through that registry. Findings stay advisory or Warden inputs — never a competing PR verdict.

## Boundaries & Constraints

**Always:**
- Consume `pyforge.core.hooks` (`HookSpec`, `HookPlugin`, `PluginRegistry`, `publish_verdict`). Do not ship a second loader or a `pyforge.doctor.hooks` / `pyforge.doctor.plugins` entry-point group.
- Two process specs, owner `"doctor"`: `pyforge.doctor.gather` and `pyforge.doctor.prescribe`.
- Today's backends are the default plugins: diagnose gather (`atlas.gather` for `_DEFAULT_DIAGNOSE_AXES`, plus `warden.gather` + `env_hygiene.gather` when the target is a real directory) and the existing `prescribe` pipeline (`partition` / `rank` / `name_root_cause` / `recommend_safe_upgrade`).
- Plugins call those backends live on the modules CLI tests already monkeypatch — no import-time bind of `gather`.
- `prescribe.py`'s sanctioned import surface is unchanged (AD-4). Hook types live in a new `hooks.py`.
- Default plugins never call `publish_verdict` for a spec they do not own. Doctor findings remain `Finding` / `Prescription` / `DoctorReport` data (operability exit `{0, 2, 130}`). They are not a Warden PR-gate verdict.
- `invoke(..., spec_name=)` always names Doctor's spec so the in-tree core dummy is never run.

**Block If:** none.

**Never:**
- Warden Epic 9 / FR-44 PR-gate scanners; steward 32.2 deploy-profile plugins; peer FR-45 extractions; scorecard metrics; canopy portal/MCP/chrome; rewriting gather/prescribe heuristics; adding pluggy; importing `pyforge.warden` from `hooks.py`; changing Pixi task names or `verdict.py` sole-ownership.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Default plugins registered | `default_registry()` or entry-point names in doctor `pyproject.toml` | Plugins for `pyforge.doctor.gather` and `pyforge.doctor.prescribe`, owner `doctor` | n/a |
| Diagnose gather via plugin | `around` with `diagnose_target`, `directory_checks=False`, stubbed `atlas.gather` | Same findings as today's `_run_diagnose` atlas loop | Backend errors unchanged |
| Directory checks | `directory_checks=True`, real dir path | Atlas findings plus warden + env_hygiene gathers | Same as CLI |
| Prescribe via plugin | `around` with already-gathered `findings` | Same `Prescription` tuple as `_build_prescriptions` | n/a |
| Second verdict | Doctor plugin + `publish_verdict` on a warden-owned `HookSpec` | `SecondVerdictError` | Fail loud |
| Parallel group | Doctor `pyproject.toml` | Only canonical `pyforge.core.hooks` (plus existing non-pyforge groups if any) | Conformance must stay green |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-core/src/pyforge/core/hooks.py` — **read-only** contract: `HookSpec`, `PluginRegistry`, `ENTRY_POINT_GROUP`, `publish_verdict`, `SecondVerdictError`, `invoke(..., spec_name=)`.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/hooks.py` — **new**. `GATHER_HOOK_SPEC`, `PRESCRIBE_HOOK_SPEC`, `DefaultGatherPlugin`, `DefaultPrescribePlugin`, `default_registry()`, `gather_for_diagnose()`, `build_prescriptions()`. Call `atlas.gather` / `warden.gather` / `env_hygiene.gather` and `prescribe.*` live. Do not import subprocess/mcp/pyforge.warden.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py` — `_run_diagnose` / `_build_prescriptions` delegate to `hooks.gather_for_diagnose` / `hooks.build_prescriptions`. Keep `_DEFAULT_DIAGNOSE_AXES`, text/JSON emit, score.grade, directory detection. `_action_text` can move with prescriptions or stay imported by hooks.
- `src/shared/packages/pyforge-doctor/pyproject.toml` — `[project.entry-points."pyforge.core.hooks"]` `doctor-gather` / `doctor-prescribe` pointing at the two default plugin classes. No `pyforge.doctor.*` group.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/prescribe.py` — **read-only**.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/verdict.py` — **read-only**.
- `src/shared/packages/pyforge-doctor/tests/unit/test_hooks_plugins.py` — **new**. I/O matrix; stub atlas/warden/env like `test_cli_diagnose.py`.
- `src/shared/packages/pyforge-doctor/tests/unit/test_cli_diagnose.py` — existing stubs must still pass after CLI delegates to hooks (live module calls).
- `src/shared/packages/pyforge-core/tests/meta/test_plugin_registration_conformance.py` — **read-only**; doctor must not trip it.

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/hooks.py` — add specs + default plugins + diagnose/prescribe helpers — FR-45 surface
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py` — route diagnose gather/prescribe through helpers — no heuristic rewrite
- [x] `src/shared/packages/pyforge-doctor/pyproject.toml` — declare default plugins on `pyforge.core.hooks`
- [x] `src/shared/packages/pyforge-doctor/tests/unit/test_hooks_plugins.py` — cover I/O matrix

**Acceptance Criteria:**
- Given today's diagnose gather/prescribe backends, when the hook spec lands, then they are the default plugins on `pyforge.core.hooks` for `pyforge.doctor.gather` and `pyforge.doctor.prescribe`.
- Given a plugin that would publish a verdict for a Warden-owned hook spec, when `publish_verdict` runs, then `SecondVerdictError` is raised and Doctor findings remain advisory report data, not a competing PR verdict.
- Given `doctor diagnose --target` (with and without `--prescribe`), when the CLI runs, then behavior matches the frozen Story 3.4 envelope (findings, empty-or-populated prescriptions, directory checks).

## Design Notes

`DefaultGatherPlugin.call("around", context)` reads `diagnose_target` and `directory_checks`; writes `context["findings"]`. `DefaultPrescribePlugin.call("around", context)` reads `findings`; writes `context["prescriptions"]`. Helpers construct a registry, `register` the defaults (idempotent), then `invoke("around", ..., spec_name=...)`. Entry-point load is optional extra coverage; in-process register is the CLI path so tests do not depend on a rebuilt wheel.

A Warden `HookSpec` used in tests is synthetic (`name="pyforge.warden.pr-gate"`, `owner="warden"`) — this story does not publish Warden's FR-44 spec.

## Verification

**Commands:**
- `pixi run -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_hooks_plugins.py src/shared/packages/pyforge-doctor/tests/unit/test_cli_diagnose.py src/shared/packages/pyforge-doctor/tests/meta/test_prescribe_pure_function.py -q` -- expected: all pass
- `pixi run -e pyforge-core pytest src/shared/packages/pyforge-core/tests/meta/test_plugin_registration_conformance.py -q` -- expected: pass (no parallel doctor group)
- `pixi run -e pyforge-doctor pyforge-doctor-test` -- expected: suite green (one pre-existing hygiene live-fixture fail is deferred)

## Spec Change Log

## Review Triage Log

### 2026-08-24 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 1, low 2)
- defer: 1: (high 0, medium 0, low 1)
- reject: 12
- addressed_findings:
  - `[medium]` `[patch]` directory-check test now asserts atlas findings are kept, not only warden/env
  - `[low]` `[patch]` AST no-publish scan also flags `Attribute` `publish_verdict`
  - `[low]` `[patch]` empty `axes` in context no longer silently falls back via `or`

## Auto Run Result

Status: done

Summary: Diagnose gather/prescribe now run as default plugins on `pyforge.core.hooks` (`pyforge.doctor.gather` / `pyforge.doctor.prescribe`, owner doctor). Today's atlas + directory-gated warden/env_hygiene gather and the existing prescribe pipeline are the defaults. Findings stay report data; publishing a Warden-owned verdict raises `SecondVerdictError`. Not a PR-gate epic.

Files changed:
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/hooks.py` — specs, default plugins, CLI helpers
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py` — diagnose delegates to helpers
- `src/shared/packages/pyforge-doctor/pyproject.toml` — `pyforge.core.hooks` entry points
- `src/shared/packages/pyforge-doctor/tests/unit/test_hooks_plugins.py` — I/O matrix
- this spec

Review: 3 patches applied (1 medium, 2 low; follow-up score 5). 1 deferred (pre-existing hygiene fixture). Rejected per-source plugins, check/monitor rewiring, runtime `load_entry_points` as CLI path (spec: in-process register), Warden FR-44 wiring, and treating two process points as an FR-45 violation.

Verification: focused hooks/diagnose/prescribe-purity 39 passed; core conformance 10 passed. Full `pyforge-doctor-test` 1307 passed, 2 skipped, 1 failed (deferred hygiene live fixture).

Residual: CLI does not call `load_entry_points` (declared in pyproject; swap still means replacing `DefaultGatherPlugin`). Check/monitor remain direct gathers.
