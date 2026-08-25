---
title: Shared hook-spec and plugin registration in pyforge-core
type: feature
created: '2026-08-24'
status: done
updated: '2026-08-24'
context:
  - src/shared/packages/pyforge-core/README.md
  - src/shared/packages/pyforge-core/tests/meta/test_leaf_constraint.py
warnings: []
baseline_revision: a253cc8751
review_loop_iteration: 0
followup_review_recommended: true
deferred:
  - summary: >-
      pyforge-core-test reports 9 pre-existing sole-ownership failures in
      sibling marshal/steward/herald trees, unrelated to hooks.py.
    evidence: |-
      Failures are in test_atomic_write_sole_ownership,
      test_exception_root_sole_ownership, and test_process_sole_ownership
      against marshal/steward/herald sources that this story did not edit.
    location: >-
      src/shared/packages/pyforge-core/tests/meta/
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Eight stations will extract process layers (Warden PR-gate, build engine, runner, GraphStore, exporters, deploy profiles, Kedro). Without one API they invent eight plugin loaders.

**Approach:** Land the shared hook-spec documentation shape plus plugin registration in `src/shared/packages/pyforge-core/` only. Station packages consume it; they do not ship a second loader. No ninth package.

## Acceptance Criteria

- Given a dummy plugin declared against the published API, when the loader runs, then the plugin is invoked at a named `before` / `after` / `around` (or equivalent documented) point.
- Given a station package that ships a parallel registration mechanism for the same class of extension, when the conformance check runs, then it fails.
- Given the published contract, when a plugin would publish a second verdict for a process another owner specified, then that is forbidden (documented and enforced).
- Given the contract, when listing non-plugin surfaces, then Pixi task names, Golden Path artifact identity, parent infra kinds, host import boundary (`pyforge.*` under `src/platform/`), and the Warden verdict itself are named as **not** plugin surfaces.

## Boundaries & Constraints

**Always:** `pyforge.core` is stdlib-only (README + `tests/meta/test_leaf_constraint.py`). Loader uses stdlib (`importlib`, `importlib.metadata` entry points). Extend existing primitives; do not fork a second core. Write specs under `_bmad-output/projects/pyforge-steward/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`.

**Block If:** A change would add a third-party runtime dep (pluggy, setuptools) to pyforge-core, or `import pyforge.<station>`.

**Never:** Warden Epic 9 scanners; steward 32.2 deploy-profile plugins; peer FR-45 extractions (atlas 18.1 Kedro audit, mason 10.1, marshal 26.1, doctor 17.1, herald 16.1, scribe 4.1); scorecard/metrics; chrome (18-1 already shipped). Do not drain other stories.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Dummy before/after/around | Dummy registered for `pyforge.core.example`; invoke each point | Dummy `call` runs at that point; `around` may invoke `context["next"]` | Unknown point → `PluginError` |
| Entry-point load | Installed distribution declares group `pyforge.core.hooks` | Loader instantiates and registers the dummy | Bad target → `PluginError`, no silent skip of a declared name |
| Second verdict | Plugin writes a verdict for a `HookSpec` it does not own | Raise `SecondVerdictError` (subclass of `PyforgeError`) | Owner-matched publish is allowed |
| Parallel loader | Station `pyproject.toml` has entry-point group `pyforge.<station>.hooks` (not `pyforge.core.hooks`) | Conformance check fails | Canonical group alone is allowed |
| Non-plugin surfaces | Contract / module constants | Five named exclusions present | Missing name fails the unit test |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-core/src/pyforge/core/hooks.py` — **new** `HookSpec`, `HookPlugin` protocol, `PluginRegistry`, `DummyPlugin`, `ENTRY_POINT_GROUP = "pyforge.core.hooks"`, `HOOK_POINTS`, `NOT_PLUGIN_SURFACES`, `PluginError` / `SecondVerdictError` (from `errors.PyforgeError`)
- `src/shared/packages/pyforge-core/src/pyforge/core/errors.py` — existing root; hook errors subclass it, do not invent a second root
- `src/shared/packages/pyforge-core/src/pyforge/core/__init__.py` — package docstring only if needed; keep leaf
- `src/shared/packages/pyforge-core/pyproject.toml` — `dependencies = []` stays empty; `[project.entry-points."pyforge.core.hooks"]` dummy = `pyforge.core.hooks:DummyPlugin`
- `src/shared/packages/pyforge-core/README.md` — document hook-spec shape, entry-point group, non-plugin surfaces, second-verdict rule; restyle status past 14.1 empty scaffold
- `src/shared/packages/pyforge-core/tests/unit/test_hooks.py` — dummy invoke + entry-point load + second-verdict + unknown point
- `src/shared/packages/pyforge-core/tests/meta/test_plugin_registration_conformance.py` — scan sibling `pyproject.toml` for parallel `pyforge.<name>.(hooks|plugins)` groups; synthetic-violation fixture (non-vacuous); allow only `pyforge.core.hooks`
- `src/shared/packages/pyforge-core/tests/meta/test_leaf_constraint.py` — **read-only** unless a new import fails it (`importlib.metadata` is stdlib)
- `src/shared/packages/pyforge-core/tests/meta/conftest.py` — reuse `PACKAGES_ROOT` / `sibling_station_dirs`
- Existing `atomic_write.py`, `verdict.py`, `report.py`, `process.py`, `landing_evidence.py` — **do not fork**

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-core/src/pyforge/core/hooks.py` — add stdlib loader + hook-spec types + dummy — FR-43 surface
- `src/shared/packages/pyforge-core/pyproject.toml` — declare dummy entry point; keep `dependencies = []`
- `src/shared/packages/pyforge-core/README.md` — contract docs (shape, non-plugin surfaces, no second verdict)
- `src/shared/packages/pyforge-core/tests/unit/test_hooks.py` — cover I/O matrix rows
- `src/shared/packages/pyforge-core/tests/meta/test_plugin_registration_conformance.py` — fail parallel station loaders; non-vacuous synthetic

**Acceptance Criteria:**
- Given a dummy plugin declared against the published API, when the loader runs, then it is invoked at named before/after/around points.
- Given a station package that ships a parallel registration mechanism for the same class of extension, when the conformance check runs, then it fails.
- Given a plugin that publishes a second verdict for a process another owner specified, when `publish_verdict` (or equivalent) is called, then `SecondVerdictError` is raised.
- Given the contract documentation and `NOT_PLUGIN_SURFACES`, when read, then Pixi task names, Golden Path artifact identity, parent infra kinds, host import boundary, and the Warden verdict are listed as not plugin surfaces.

## Design Notes

Canonical entry-point group is `pyforge.core.hooks` only. Loader: `importlib.metadata.entry_points(group=...)` then load/instantiate. Do not add pluggy.

`around`: plugin `call("around", context)` may run `context["next"](context)` to continue the chain; if `next` is absent, `around` is still invoked (documented equivalent).

`invoke(point, context, *, spec_name=)` requires `spec_name` so a station never accidentally runs the in-tree dummy. `register` requires `owner` as well as `call`/`hook_spec`; `load_entry_points` commits only after every name loads (atomic). Duplicate register of the same class+spec+owner is idempotent.

Conformance is a **best-effort static** scan of sibling station `pyproject.toml` files (and optional `[project.entry-points.*]` tables) plus an AST scan for `import pluggy`. Dynamic loaders and pytest/django plugin groups are out of scope. Parallel means another `pyforge.<token>.hooks` or `pyforge.<token>.plugins` group.

## Spec Change Log

## Review Triage Log

### 2026-08-24 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 0, medium 3, low 3)
- defer: 1: (high 0, medium 1, low 0)
- reject: 12
- addressed_findings:
  - `[medium]` `[patch]` require `owner` on register/_as_plugin
  - `[medium]` `[patch]` require `spec_name` on invoke so the dummy is not run by accident
  - `[medium]` `[patch]` scan sibling sources for `import pluggy`
  - `[low]` `[patch]` atomic load_entry_points + idempotent register
  - `[low]` `[patch]` refresh stale pyproject.toml leaf comment
  - `[low]` `[patch]` README documents required spec_name and dummy scope

## Verification

**Commands:**
- `pixi run -e pyforge-core pyforge-core-test` -- expected: new hooks + conformance + leaf constraint pass. Pre-existing sibling sole-ownership failures may remain (deferred).
- `pixi run -e pyforge-core pytest src/shared/packages/pyforge-core/tests/unit/test_hooks.py src/shared/packages/pyforge-core/tests/meta/test_plugin_registration_conformance.py src/shared/packages/pyforge-core/tests/meta/test_leaf_constraint.py -q` -- expected: all pass

## Auto Run Result

Status: done

Summary: Landed `pyforge.core.hooks` (HookSpec, PluginRegistry, DummyPlugin, stdlib entry-point group `pyforge.core.hooks`, `publish_verdict` / `SecondVerdictError`) plus conformance checks. No ninth package. No station process extractions.

Files changed:
- `src/shared/packages/pyforge-core/src/pyforge/core/hooks.py` — shared loader
- `src/shared/packages/pyforge-core/pyproject.toml` — dummy entry point
- `src/shared/packages/pyforge-core/README.md` — contract docs
- `src/shared/packages/pyforge-core/src/pyforge/core/__init__.py` — package docstring
- `src/shared/packages/pyforge-core/tests/unit/test_hooks.py` — I/O matrix
- `src/shared/packages/pyforge-core/tests/meta/test_plugin_registration_conformance.py` — parallel-loader guard
- this spec

Review: 6 patches applied (3 medium, 3 low; follow-up score 12). 1 deferred (pre-existing sole-ownership reds). Rejected package re-exports, version bump, onion around-chain, tying publish_verdict to the verdict lattice, and station consumption (Never list).

Verification: focused hooks/conformance/leaf tests 49 passed. Full `pyforge-core-test` still has 9 pre-existing sibling sole-ownership failures.

Residual: stations do not yet consume the API (32.2 / FR-45 / Warden 9).
