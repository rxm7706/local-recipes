---
title: 'Story 9.2: Current scanners become optional plugins'
type: 'feature'
created: '2026-08-24'
status: 'done'
baseline_revision: '4a07ba8fcac6c3ed1a41ac407a3aa247c6586d75'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/src/shared/packages/pyforge-core/src/pyforge/core/hooks.py'
  - '{project-root}/src/shared/packages/pyforge-warden/src/pyforge/warden/hooks.py'
  - '{project-root}/_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-9-1-warden-publishes-the-pr-gate-hook-book.md'
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Today's engines are still a hard-wired `register_engine` list, and commercial scanners (Checkmarx, Sonar, Black Duck, GHAS, profile-local) have no plugin shape — enabling Checkmarx still looks like a fork.

**Approach:** Wrap shipped engines as the default plugin bundle on the 9.1 PR-gate book (`pyforge.core.hooks` only). Register named commercial scanners as optional plugins. Enabling an optional scanner may add findings; it must not replace the Warden verdict. A successful scan is not a competing PR-gate.

## Boundaries & Constraints

**Always:**
- Consume `HookSpec` / `HookPlugin` / `PluginRegistry` / `ENTRY_POINT_GROUP` / `publish_verdict` / `SecondVerdictError` from `pyforge.core.hooks`. Do not mint a second loader.
- Default bundle = today's registered engines: Null, Deptry, OSV, License, Currency. Wrap factories; do not rewrite engine classes.
- Optional ids: `checkmarx`, `sonar`, `blackduck`, `ghas`, `profile-local`. Default scan does not require them.
- `select_scanner_plugins` returns defaults plus only *enabled* optionals. Missing/not-enabled optional → omitted, not an error (Story 9.3 owns the fail-if-absence-is-failure test).
- Scan/aggregate plugins contribute findings or engine factories. Only `publish_pr_gate_verdict` (owner `warden`) publishes the PR-gate verdict. `verdict.py` stays sole lattice + `exit_code_for`.
- In-tree `scanner_plugin_registry()` — do not `load_entry_points()` the whole shared group in `_run_scan` (other stations' plugins would load).
- Write this spec under `_bmad-output/projects/pyforge-warden/planning-artifacts/specs/` literally. `BMAD_ACTIVE_PROJECT=pyforge-warden`. Never `scripts/bmad-switch` or `bmad-loop`.

**Block If:** Story 9.1 `PR_GATE_SCAN` / `PR_GATE_AGGREGATE` / `PR_GATE_VERDICT` missing, or a change would add `pluggy` / `pyforge.warden.hooks`.

**Never:**
- Claim Story 9.3 done (default green without Checkmarx as the CI gate test). A hook for 9.3 is allowed.
- Rewrite Epics 1–8 engines as a new product. Do not replace `register_engine` / the thread-pool seam.
- Let an optional plugin `publish_verdict` on `PR_GATE_VERDICT`. Do not treat a plugin scan success as a second PR pass/fail.
- Real Checkmarx/Sonar/Black Duck/GHAS subprocesses or vendor SDKs.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Default bundle | Fresh in-tree registry; `select_scanner_plugins()` | Plugins for Null/Deptry/OSV/License/Currency; each `is_default`; factories match `engine_factories()` | No error |
| Optional not required | No optional enabled | Selected set has none of checkmarx/sonar/blackduck/ghas/profile-local | No error; not a failed run |
| Enable optional | `enabled_optional=("checkmarx",)` | Selected set includes Checkmarx plugin; `plugin_findings` can grow vs default-only | Unknown id → `PluginError` |
| Entry points | Warden `pyproject.toml` | Default + optional plugins on `pyforge.core.hooks` only | Parallel `pyforge.warden.hooks` fails meta |
| Findings ≠ verdict | Enabled Checkmarx plugin calls `publish_verdict(PR_GATE_VERDICT, …)` | `SecondVerdictError`; findings may still exist | Owner-matched Warden publish still allowed |
| Scan success ≠ gate | Optional plugin `call("around")` returns success | Does not become `publish_pr_gate_verdict`; CLI still composes via `verdict.py` | — |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-core/src/pyforge/core/hooks.py` — **READ-ONLY** FR-43 loader.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/hooks.py` — **READ-ONLY** 9.1 book (`PR_GATE_*`, `invoke_pr_gate`, `publish_pr_gate_verdict`).
- `src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py` — **READ-ONLY** engine classes + `register_engine` / `engine_factories` (lines 184–215, 1876–1880). Plugins wrap factories.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/scanner_plugins.py` — **NEW**: `EngineScanPlugin` wrappers (`scanner_id`, `is_default`, `factory`), optional stub plugins, `OPTIONAL_SCANNER_IDS`, `scanner_plugin_registry()`, `select_scanner_plugins()`, `enabled_optional_from_environ()`. Default plugins `hook_spec=PR_GATE_SCAN.name`, `owner="warden"`. Optionals `owner` = scanner id, `is_default=False`; `around` appends to `context["plugin_findings"]` when enabled.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py` — `_run_scan` engine list from `select_scanner_plugins()` default factories (keep hygiene filter + thread pool). Invoke `PR_GATE_SCAN`/`PR_GATE_AGGREGATE` `around` with `plugin_findings`; merge extra findings. After lattice compose, `publish_pr_gate_verdict(status)` — do not let plugins set exit codes. Optional enable via `WARDEN_OPTIONAL_SCANNERS` (comma-separated ids).
- `src/shared/packages/pyforge-warden/src/pyforge/warden/verdict.py` — **READ-ONLY**.
- `src/shared/packages/pyforge-warden/pyproject.toml` — `[project.entry-points."pyforge.core.hooks"]` for default + five optional plugins. No parallel group.
- `src/shared/packages/pyforge-warden/README.md` — default bundle vs optional; enabling changes findings not the verdict owner; 9.3 still owns absence-as-failure CI test.
- `src/shared/packages/pyforge-warden/tests/unit/test_scanner_plugins.py` — **NEW**: I/O matrix.
- `src/shared/packages/pyforge-warden/tests/meta/test_pr_gate_plugin_registration.py` — still forbids parallel group; allow canonical `pyforge.core.hooks` entries.
- `src/shared/packages/pyforge-core/tests/meta/test_plugin_registration_conformance.py` — **READ-ONLY**.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-warden/src/pyforge/warden/scanner_plugins.py` — wrap engines; optional stubs; select/registry
- `src/shared/packages/pyforge-warden/pyproject.toml` — declare plugins on `pyforge.core.hooks`
- `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py` — select default factories; invoke scan/aggregate; merge optional findings; publish Warden verdict only
- `src/shared/packages/pyforge-warden/README.md` — document bundle vs optional
- `src/shared/packages/pyforge-warden/tests/unit/test_scanner_plugins.py` — cover I/O matrix

**Acceptance Criteria:**
- Given shipped Warden scanners, when extracted, then each registers as a plugin and today's set is the default plugin bundle.
- Given Checkmarx/Sonar/Black Duck/GHAS/profile-local, when a default Warden run is selected, then those plugins are optional and not required.
- Given an enabled optional scanner, when it contributes findings, then it cannot replace the Warden verdict with a second pass/fail.
- Given a successful optional-plugin scan, when the PR-gate is composed, then that success is not a competing PR-gate.

## Design Notes

Keep `register_engine` as the in-tree factory list. Each default plugin holds the same factory object so `_run_scan` can still skip `DeptryEngine` when hygiene is not applicable.

```python
class EngineScanPlugin:
    hook_spec = PR_GATE_SCAN.name
    owner = "warden"
    is_default = True
    factory: Callable[[], Engine]  # NullEngine, DeptryEngine, ...
```

Optional stubs share one `around` that, if `scanner_id` is in `context["enabled_optional"]`, appends a finding dict to `context["plugin_findings"]`. They never call `publish_verdict`. Hook for 9.3: `optional_absent_is_not_failure` is implied by omit-not-error; do not add the 9.3 negative test here.

Do not `PluginRegistry.invoke` every scan plugin as the engine runner — that would skip the existing seam. Select factories from default plugins, run the existing pool, then `invoke_pr_gate` for optional `around` on scan then aggregate.

## Spec Change Log

- 2026-08-24: Implemented default-bundle wrappers + optional stubs; CLI selects factories from in-tree plugins (live `register_engine` list), invokes scan/aggregate `around`, merges `plugin_findings`, publishes Warden verdict only.

## Review Triage Log

### 2026-08-24 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 0, medium 3, low 4)
- defer: 0
- reject: 18
- addressed_findings:
  - `[medium]` `[patch]` `_run_scan` with `WARDEN_OPTIONAL_SCANNERS=checkmarx` now asserted on `main` JSON findings
  - `[medium]` `[patch]` unknown optional id is a typed `CONFIG_VALIDATION` error, not a last-resort traceback
  - `[medium]` `[patch]` `coerce_plugin_finding` maps missing keys / `Finding` construction failures to `PluginError`
  - `[low]` `[patch]` `OPTIONAL_ABSENT_IS_NOT_FAILURE` now gates omit-not-error vs raise
  - `[low]` `[patch]` optional entry-point names prefixed `warden-*` to avoid shared-group collisions
  - `[low]` `[patch]` optional `around` guards non-list `plugin_findings`
  - `[low]` `[patch]` README status no longer claims "all 31 stories / E1–E6" while describing Epic 9

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

Summary: Shipped engines wrap as the default plugin bundle on `pyforge.core.hooks`. Optional Checkmarx/Sonar/Black Duck/GHAS/profile-local stubs can add findings when `WARDEN_OPTIONAL_SCANNERS` enables them; they cannot publish the PR-gate verdict. `register_engine` remains the live factory list. Story 9.3 is not claimed.

Files changed:
- `src/shared/packages/pyforge-warden/src/pyforge/warden/scanner_plugins.py` — default wrappers + optional stubs + select/registry
- `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py` — in-tree plugin select, scan/aggregate around, merge findings, Warden-only verdict publish
- `src/shared/packages/pyforge-warden/pyproject.toml` — plugins on `pyforge.core.hooks` only
- `src/shared/packages/pyforge-warden/README.md` — default bundle vs optional
- `src/shared/packages/pyforge-warden/tests/unit/test_scanner_plugins.py` — I/O matrix + CLI path
- `src/shared/packages/pyforge-warden/tests/unit/test_hooks.py` — dummy isolation after Warden entry points
- `src/shared/packages/pyforge-warden/tests/meta/test_pr_gate_plugin_registration.py` — canonical group must be declared
- this spec

Review: 7 patches (3 medium, 4 low; follow-up score 13). 0 deferred. Rejected loading the whole shared group in `_run_scan`, rewriting `register_engine`/engines, vendor SDKs, claiming 9.3, argparse flags, waiver participation for stub findings, and aggregate-shaped plugins.

Verification: focused scanner/hooks/meta tests 34 passed; core plugin-registration conformance 10 passed. `pyforge-warden-test` 2045 passed, 11 deselected.

Residual: optional findings merge after policy/waivers (report extras, not lattice rungs). Named entry-point classes vs live `engine_factories()` wrappers can still drift. Third-party scanners still register in-process, not via `load_entry_points` on the scan path.
