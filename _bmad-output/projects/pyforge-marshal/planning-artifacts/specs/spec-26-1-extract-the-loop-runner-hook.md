---
title: 'Extract the loop/runner hook'
type: 'feature'
created: '2026-08-24'
status: 'done'
baseline_revision: 'e96b852227b36bb28cbc62cd44dd5071057081fe'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-32-1-shared-hook-spec-and-plugin-registration-in-pyforge-core.md'
  - src/shared/packages/pyforge-core/src/pyforge/core/hooks.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Marshal's loop runner (`BmadLoopHarness`) and ACP adapter seam are hard-wired in-process. Swapping a runner or ACP adapter today means forking marshal instead of registering a plugin on the shared contract.

**Approach:** Consume steward S-32.1 (`pyforge.core.hooks`) on the existing Epic 14 `pyforge-core` floor. Publish marshal's loop/runner `HookSpec`; today's `BmadLoopHarness` is the default plugin on `pyforge.core.hooks`. An alternate runner/ACP plugin registers on the same group without a marshal fork. A passed loop is not a Warden PR-gate verdict.

## Boundaries & Constraints

**Always:** Use `PluginRegistry` / `ENTRY_POINT_GROUP = "pyforge.core.hooks"` from `pyforge.core.hooks` — do not mint a second floor, a ninth package, or a `pyforge.marshal.hooks` group. Default plugin id is `bmad-loop`; in-tree fallback constructs `BmadLoopHarness()` when that id is absent from a loaded registry. `resolve_loop_runner` is the production default factory for injected `HarnessPort` (keep `cli/main.py` constructing `BmadLoopHarness()` so `--version` tests can still monkeypatch that name). Loop/story success must not call `publish_verdict` for a spec marshal does not own. AD-3 stays: only `adapters/harness_bmadloop.py` imports `bmad_loop`. Write specs under `_bmad-output/projects/pyforge-marshal/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` — never `scripts/bmad-switch`.

**Block If:** S-32.1 symbols (`HookSpec`, `PluginRegistry`, `SecondVerdictError`, `publish_verdict`) are missing from installed `pyforge.core.hooks`.

**Never:** Warden Epic 9 scanners or a competing CI/PR-gate verdict; steward 32.2 deploy-profile plugins; minting another shared package; `import pluggy`; supervisor ingest into Canopy Epic 21; rewriting `bmad-loop` itself; scorecard metrics.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Default plugin | Fresh `PluginRegistry`; `resolve_loop_runner()` | Returns a `BmadLoopHarness` whose `hook_spec`/`owner`/`plugin_id` are `pyforge.marshal.loop_runner` / `marshal` / `bmad-loop` | No error |
| Named before/after/around | Default plugin registered; `invoke` each point with marshal spec name | Plugin `call` runs at that point; `around` may run `context["next"]` | Unknown point → `PluginError` |
| Alternate registers | Second `HookPlugin` with same spec, `plugin_id="alt-runner"` registered in-process | `resolve_loop_runner(plugin_id="alt-runner")` returns it; marshal package is not forked | Missing id → in-tree `BmadLoopHarness()` |
| Entry-point group | Marshal `pyproject.toml` | Declares `bmad-loop` under `pyforge.core.hooks` only | Parallel `pyforge.marshal.hooks` fails core conformance |
| Second verdict | Default plugin `publish_verdict` on `HookSpec(name="pyforge.warden.pr_gate", owner="warden")` | Raises `SecondVerdictError` | Owner-matched marshal spec is allowed |
| Loop pass ≠ Warden | `harness_bmadloop.py` sources | No `publish_verdict` call | AST/unit pin |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-core/src/pyforge/core/hooks.py` — **read-only.** `HookSpec`, `HookPlugin`, `PluginRegistry`, `ENTRY_POINT_GROUP`, `HOOK_POINTS`, `publish_verdict`, `SecondVerdictError`. Consume; do not fork.
- `src/shared/packages/pyforge-core/tests/meta/test_plugin_registration_conformance.py` — **read-only.** Flags `pyforge.<station>.hooks` other than `pyforge.core.hooks`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` — `BmadLoopHarness` (~L851) is today's runner and the default plugin: add `hook_spec`, `owner`, `plugin_id`, `call`; add `LOOP_RUNNER_HOOK_SPEC`, `DEFAULT_LOOP_RUNNER_PLUGIN_ID`, `resolve_loop_runner()`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/harness.py` — **read-only** `HarnessPort` shape. Resolver returns this port; do not add a second harness protocol.
- `src/shared/packages/pyforge-marshal/pyproject.toml` — `[project.entry-points."pyforge.core.hooks"]` `bmad-loop = "pyforge.marshal.adapters.harness_bmadloop:BmadLoopHarness"`. `pyforge-core` already in `dependencies`. No new group. AD-3 import-linter unchanged.
- Production defaults `else BmadLoopHarness()` → `else resolve_loop_runner()` in `cli/{init,spin,status,land,deploy,retire,adapters}.py` and `supervisor/__main__.py`. Leave `cli/main.py` `_version_text` on `BmadLoopHarness()` (monkeypatch).
- `src/shared/packages/pyforge-marshal/tests/unit/test_loop_runner_hook.py` — **new.** Matrix rows.
- `src/shared/packages/pyforge-core/src/pyforge/core/` — **do not add files.** Epic 14 floor already exists.

## Tasks & Acceptance

**Execution:**
- `adapters/harness_bmadloop.py` -- plugin attributes + `call` + `resolve_loop_runner` -- default plugin on S-32.1
- `pyproject.toml` -- `pyforge.core.hooks` entry point `bmad-loop` -- install-time registration
- `cli/{init,spin,status,land,deploy,retire,adapters}.py` + `supervisor/__main__.py` -- default `HarnessPort` via resolver -- swap without fork
- `tests/unit/test_loop_runner_hook.py` -- matrix coverage -- registration, invoke, second-verdict, no Warden publish

**Acceptance Criteria:**
- Given today's runner, when the hook spec lands, then it is the default plugin on `pyforge.core.hooks` (`plugin_id=bmad-loop`).
- Given an alternate runner plugin registered on the same spec, when `resolve_loop_runner(plugin_id=...)` runs, then it is selected without a marshal process fork.
- Given a passed loop, when verdict publish is attempted for a Warden-owned spec, then `SecondVerdictError` is raised and harness sources never call `publish_verdict`.

## Spec Change Log

## Review Triage Log

### 2026-08-24 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 0, low 3)
- defer: 0
- reject: 0
- addressed_findings:
  - `[low]` `[patch]` `BmadLoopHarness.call` now records `self.calls` so before/after invoke is asserted, not only around+next
  - `[low]` `[patch]` `resolve_loop_runner` uses `getattr(plugin, "hook_spec", None)` so a stub missing the attribute falls through to the in-tree default
  - `[low]` `[patch]` marshal `pyproject.toml` entry-point table comments that this is the S-32.1 group, not a parallel marshal loader

## Auto Run Result

Status: done

Summary: Today's `BmadLoopHarness` is the default `pyforge.core.hooks` plugin (`plugin_id=bmad-loop`, spec `pyforge.marshal.loop_runner`). Production CLI/supervisor defaults use `resolve_loop_runner()`. An alternate plugin can register on the same group without a marshal fork. A passed loop is not a Warden PR-gate verdict (`SecondVerdictError`; harness never calls `publish_verdict`). Consumes S-32.1 / Epic 14 floor; no ninth package.

Files changed:
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` — plugin attrs, `call`, `resolve_loop_runner`
- `src/shared/packages/pyforge-marshal/pyproject.toml` — `pyforge.core.hooks` entry point `bmad-loop`
- `cli/{init,spin,status,land,deploy,retire,adapters}.py`, `supervisor/__main__.py` — default harness via resolver
- `tests/unit/test_loop_runner_hook.py` — I/O matrix
- this spec

Review: 3 low patches applied. Rejected CLI plugin selector, wrapping production spin in `invoke`, ACP extract as a second spec, swallowing `load_entry_points` errors, and editing read-only `ports/harness.py`. Follow-up score: 3 low → false.

Verification:
- `test_loop_runner_hook.py` — 8 passed
- `test_plugin_registration_conformance.py` + `test_leaf_constraint.py` — 34 passed
- Implementer: marshal `-m "not slow"` — 6299 passed; version/preflight/harness slice — 61 passed

Residual: `resolve_loop_runner()` with no registry still fails closed if a declared `pyforge.core.hooks` entry point is broken (S-32.1 atomic load). Alternate `plugin_id` need not implement full `HarnessPort`. Estate `DW-OM-2026-08-24` left open.

## Design Notes

One marshal `HookSpec`: name `pyforge.marshal.loop_runner`, owner `marshal`. An ACP-backed alternate is another plugin on that spec (`plugin_id` distinct), not a second loader and not a Warden scanner. `PluginRegistry` does not store entry-point names — `plugin_id` on the marshal plugin is the selector. `load_entry_points` still loads core's dummy (`pyforge.core.example`); `resolve_loop_runner` filters by marshal spec name. In-tree `register(BmadLoopHarness())` is idempotent and keeps unit tests working when the wheel's entry point is not visible.

Do not close estate-wide `DW-OM-2026-08-24` from this station-only story.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
