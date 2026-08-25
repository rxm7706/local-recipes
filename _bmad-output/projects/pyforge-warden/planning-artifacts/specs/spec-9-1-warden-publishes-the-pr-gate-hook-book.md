---
title: 'Story 9.1: Warden publishes the PR-gate hook book'
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
deferred: []
---

<intent-contract>

## Intent

**Problem:** Scanner authors who want Checkmarx/Sonar/GHAS on the PR gate currently have to fork Warden, because this station has not published named hook specs on the shared FR-43 API.

**Approach:** Consume `pyforge.core.hooks` (steward 32.1). Publish Warden-owned `HookSpec`s for scan / aggregate / verdict. Plugins register through `pyforge.core.hooks` only. The Warden verdict remains the only PR quality-gate pass/fail.

## Boundaries & Constraints

**Always:**
- Import `HookSpec`, `HookPlugin`, `PluginRegistry`, `ENTRY_POINT_GROUP`, `HOOK_POINTS`, `publish_verdict`, `SecondVerdictError` from `pyforge.core.hooks`. Do not copy the loader.
- Spec owner is `"warden"` for every PR-gate spec. Scanner plugins may attach to scan/aggregate by matching `hook_spec`; they must not own the verdict spec.
- `publish_pr_gate_verdict` uses an in-tree owner plugin (`owner="warden"`) so only Warden can publish the gate verdict.
- `verdict.py` stays sole owner of lattice + `exit_code_for`. Hooks do not project exits.
- Existing `engines.py` `register_engine` (lines 184–215) stays the in-tree engine factory list.

**Block If:** Steward 32.1 `pyforge.core.hooks` is missing from this checkout, or a change would add pluggy / a third-party plugin runtime to pyforge-warden.

**Never:**
- Do not mint `pyforge.warden.hooks` / `pyforge.warden.plugins` entry-point groups or import `pluggy`.
- Do not extract Deptry/OSV/license/currency engines into plugins (Story 9.2).
- Do not treat “green without Checkmarx” as this story’s whole deliverable (Story 9.3).
- Do not publish a competing PR quality-gate verdict. Do not edit `verdict.py`, `engines.py` engine classes, or the CLI scan loop.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Hook book | Import `pyforge.warden.hooks` | Three specs: scan, aggregate, verdict; each `owner="warden"` | — |
| Invoke named points | Plugin registered for `PR_GATE_SCAN` via `PluginRegistry.register` | `invoke_pr_gate` runs it at before/after/around | Unknown point → `PluginError` from core |
| Canonical group | Warden `pyproject.toml` | No `pyforge.warden.(hooks\|plugins)` group; registration group is `ENTRY_POINT_GROUP` (`pyforge.core.hooks`) | Parallel group = test failure |
| Owner-matched verdict | `WardenVerdictOwner` + `publish_pr_gate_verdict("ok")` | Returns `"ok"` | — |
| Competing verdict | Plugin with `owner!="warden"` or `hook_spec!=` verdict name calls `publish_verdict(PR_GATE_VERDICT, …)` | Raises `SecondVerdictError` | Subclass of `PluginError` / `PyforgeError` |
| Empty registry | No PR-gate plugins registered | `invoke_pr_gate` returns `[]`; in-tree engines unchanged | Missing scanner ≠ this story |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-warden/src/pyforge/warden/hooks.py` — **NEW**: `PR_GATE_SCAN` / `PR_GATE_AGGREGATE` / `PR_GATE_VERDICT` (`HookSpec`), `PR_GATE_HOOK_SPECS`, `WardenVerdictOwner`, `pr_gate_registry()`, `invoke_pr_gate()`, `publish_pr_gate_verdict()`. Re-export `ENTRY_POINT_GROUP`. Consume core; do not reimplement `PluginRegistry`.
- `src/shared/packages/pyforge-core/src/pyforge/core/hooks.py` — **READ-ONLY**: `HookSpec` (name+owner), `PluginRegistry.register`/`load_entry_points`/`invoke(..., spec_name=)`, `publish_verdict` / `SecondVerdictError`, `ENTRY_POINT_GROUP = "pyforge.core.hooks"`, `HOOK_POINTS`.
- `src/shared/packages/pyforge-warden/pyproject.toml` — **READ-ONLY** except a comment if needed: `pyforge-core` already in `dependencies`; do **not** add `[project.entry-points."pyforge.warden.hooks"]`. Canonical group only.
- `src/shared/packages/pyforge-warden/README.md` — document the PR-gate hook book: three spec names, `pyforge.core.hooks` registration, no second verdict, engines stay in-tree until 9.2.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py:184-215` — **READ-ONLY**: `register_engine` / `engine_factories` / `registered_engines`. Not a process-hook loader; 9.2 wraps these.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/verdict.py` — **READ-ONLY**: sole `compose` / `exit_code_for`. Do not import hooks here.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py` — **READ-ONLY** this story. Do not wire `load_entry_points` into `_run_scan` (9.2).
- `src/shared/packages/pyforge-warden/tests/unit/test_hooks.py` — **NEW**: I/O matrix.
- `src/shared/packages/pyforge-warden/tests/meta/test_pr_gate_plugin_registration.py` — **NEW**: pyproject has no parallel group; `hooks.py` does not import `pluggy`; `ENTRY_POINT_GROUP` is the core canonical string.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-warden/src/pyforge/warden/hooks.py` — add the hook book + thin wrappers over core
- `src/shared/packages/pyforge-warden/README.md` — document spec names, registration group, second-verdict rule
- `src/shared/packages/pyforge-warden/tests/unit/test_hooks.py` — cover I/O matrix rows
- `src/shared/packages/pyforge-warden/tests/meta/test_pr_gate_plugin_registration.py` — fail a parallel loader / pluggy import

**Acceptance Criteria:**
- Given the FR-43 contract, when this story completes, then Warden documents hook specs for scan / aggregate / verdict (or equivalent named points).
- Given a scanner plugin, when it registers, then it uses `pyforge.core.hooks` (`PluginRegistry` / `ENTRY_POINT_GROUP`), not a Warden-only second loader.
- Given a plugin that does not own the Warden verdict spec, when it publishes a PR-gate verdict, then `SecondVerdictError` is raised; owner-matched Warden publish is allowed.
- Given shipped engines, when 9.1 lands, then `register_engine` still lists them in `engines.py` (not extracted).

## Design Notes

Spec names (stable for 9.2 plugins):

```python
PR_GATE_SCAN = HookSpec(name="pyforge.warden.pr_gate.scan", owner="warden")
PR_GATE_AGGREGATE = HookSpec(name="pyforge.warden.pr_gate.aggregate", owner="warden")
PR_GATE_VERDICT = HookSpec(name="pyforge.warden.pr_gate.verdict", owner="warden")
```

`invoke_pr_gate(spec, point, context, *, registry=)` calls `registry.invoke(point, context, spec_name=spec.name)`. Default registry is empty unless the caller `register`s or `load_entry_points()`. `load_entry_points` will also see core’s dummy (`pyforge.core.example`); Warden invoke uses its own `spec_name`, so the dummy never runs on the PR gate.

`WardenVerdictOwner` is identity for `publish_verdict`, not a scanner. A Checkmarx-shaped plugin uses `hook_spec=PR_GATE_SCAN.name` and `owner="checkmarx"` so invoke can run it later (9.2) while `publish_verdict(PR_GATE_VERDICT, that_plugin, …)` always fails.

## Spec Change Log

## Review Triage Log

### 2026-08-24 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 0, medium 3, low 5)
- defer: 0
- reject: 22
- addressed_findings:
  - `[medium]` `[patch]` `invoke_pr_gate` raises `PluginError` when spec is not in `PR_GATE_HOOK_SPECS`; unit test added
  - `[medium]` `[patch]` scan plugin is not invoked on aggregate/verdict (spec isolation)
  - `[medium]` `[patch]` dummy-exclusion test now asserts core's DummyPlugin actually loaded
  - `[low]` `[patch]` README: Epic 9 status, CLI not wired yet, scanner-author HookPlugin + `pyforge.core.hooks` example
  - `[low]` `[patch]` `WardenVerdictOwner.owner` reads `PR_GATE_VERDICT.owner`
  - `[low]` `[patch]` default `pr_gate_registry()` empty invoke covered
  - `[low]` `[patch]` meta detector flags an empty parallel group table

## Verification

**Commands:**
- `pixi run -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/unit/test_hooks.py src/shared/packages/pyforge-warden/tests/meta/test_pr_gate_plugin_registration.py src/shared/packages/pyforge-warden/tests/meta/test_verdict_sole_ownership.py -q` -- expected: all pass
- `pixi run -e pyforge-warden pyforge-warden-test` -- expected: default suite (`not slow`) still green

## Auto Run Result

Status: done

Summary: Warden publishes PR-gate `HookSpec`s for scan / aggregate / verdict on `pyforge.core.hooks`. Plugins register through the shared loader; a foreign plugin cannot publish the gate verdict. In-tree engines stay in `engines.py`. CLI scan loop unwired until 9.2.

Files changed:
- `src/shared/packages/pyforge-warden/src/pyforge/warden/hooks.py` — hook book + thin core wrappers
- `src/shared/packages/pyforge-warden/README.md` — documented specs, registration group, scanner-author example
- `src/shared/packages/pyforge-warden/pyproject.toml` — comment forbidding a parallel group
- `src/shared/packages/pyforge-warden/tests/unit/test_hooks.py` — I/O matrix
- `src/shared/packages/pyforge-warden/tests/meta/test_pr_gate_plugin_registration.py` — no second loader
- this spec

Review: 8 patches applied (3 medium, 5 low; follow-up score 14). 0 deferred. Rejected CLI wiring, Warden entry-point plugins, engine extraction, Checkmarx-green as this story, `__init__` re-export, and competing-verdict via a second wrapper.

Verification: focused hooks/meta/sole-ownership tests 121 passed. `pyforge-warden-test` 2029 passed, 11 deselected.

Residual: `invoke_pr_gate` is not wired into `_run_scan` (Story 9.2). Default registry is a process singleton; tests pass isolated registries. Follow-up review recommended (patched medium+low score ≥ 5).
