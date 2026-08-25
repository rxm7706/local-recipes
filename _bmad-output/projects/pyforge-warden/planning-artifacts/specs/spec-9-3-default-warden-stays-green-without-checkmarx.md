---
title: 'Story 9.3: Default Warden stays green without Checkmarx'
type: 'chore'
created: '2026-08-24'
status: 'done'
baseline_revision: 'bf025506f4c325be68b602f69d79ca9f34b63008'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/src/shared/packages/pyforge-warden/src/pyforge/warden/scanner_plugins.py'
  - '{project-root}/src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py'
  - '{project-root}/_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-9-2-current-scanners-become-optional-plugins.md'
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** A default Warden run must stay a green process when Checkmarx (or any other named commercial scanner) is not installed. Missing optional plugins must not be a failed gate; only Warden's own engines may fail the run.

**Approach:** Pin that contract on the CLI surface. A fixture whose plugin registry has no Checkmarx/Sonar/Black Duck/GHAS/profile-local plugin, plus a default `warden scan` (no `WARDEN_OPTIONAL_SCANNERS`), must exit green unless a default-bundle engine fails. Add a test that fails if absence of a named optional plugin is treated as a Warden failure.

## Boundaries & Constraints

**Always:**
- Consume Story 9.2's `OPTIONAL_SCANNER_IDS`, `OPTIONAL_ABSENT_IS_NOT_FAILURE`, `select_scanner_plugins`, and in-tree `scanner_plugin_registry()`. Default run = no `WARDEN_OPTIONAL_SCANNERS` (empty enable list).
- Observed surface is the process: `pyforge.warden.cli.main(["scan", …])` exit code + JSON report `errors` / `status`. Missing Checkmarx is not a failed gate (`CONFIG_VALIDATION` / `PluginError` / non-zero exit caused by optional absence).
- `OPTIONAL_ABSENT_IS_NOT_FAILURE` stays `True`. Default selection remains disjoint from `OPTIONAL_SCANNER_IDS`.
- Write this spec under `_bmad-output/projects/pyforge-warden/planning-artifacts/specs/` literally. `BMAD_ACTIVE_PROJECT=pyforge-warden`. Never `scripts/bmad-switch` or `bmad-loop`.

**Block If:** Story 9.2 `select_scanner_plugins` / `OPTIONAL_SCANNER_IDS` missing from this checkout.

**Never:**
- Require Checkmarx/Sonar/Black Duck/GHAS/profile-local for a default run. Do not vendor SDKs or subprocess those tools.
- Rewrite engines, `verdict.py`, or the 9.1/9.2 hook book. Do not `load_entry_points()` the shared group in `_run_scan`.
- Treat an engine-driven fail (OSV/deptry/license/currency) as this story's green path. Those may still fail the process.
- Claim optional *enablement* (`WARDEN_OPTIONAL_SCANNERS=checkmarx`) as the default run.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Default green, no commercial plugins | Registry fixture with only default-bundle plugins (no Checkmarx or other `OPTIONAL_SCANNER_IDS`); `warden scan` on a clean/`--allow-empty` target; env has no `WARDEN_OPTIONAL_SCANNERS` | Process exit 0; selected plugins disjoint from `OPTIONAL_SCANNER_IDS`; JSON `errors` have no optional-absence / Checkmarx-missing cause | No error expected |
| Absence is not a Warden failure | Same fixture; default select + default CLI | No `PluginError`, no `CONFIG_VALIDATION` whose message is optional-absent / missing Checkmarx; `OPTIONAL_ABSENT_IS_NOT_FAILURE` is True | A regression that treats absence as failure **fails this test** |
| Own engines may still fail | Same no-commercial registry; scan target whose default engines fail the gate (non-green lattice / non-zero `exit_code_for`) | Process not green **because of Warden engines**, not because Checkmarx is missing | Engine/lattice errors allowed; must not add optional-absence errors |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-warden/src/pyforge/warden/scanner_plugins.py` — **KEEP** 9.2 omit-not-error (`OPTIONAL_ABSENT_IS_NOT_FAILURE`, `select_scanner_plugins`). Tiny production change only if CLI needs a named helper so tests can assert absence ≠ failure (do not flip the flag to False).
- `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py` — `_run_scan` (~1324–1342) selects plugins then records `PluginError` as `CONFIG_VALIDATION`. Default path must not record optional-absence when commercial plugins are missing and none are enabled.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/hooks.py` — **READ-ONLY** 9.1 book.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/verdict.py` — **READ-ONLY** lattice + `exit_code_for`.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py` — **READ-ONLY** default bundle.
- `src/shared/packages/pyforge-warden/tests/unit/test_scanner_plugins.py` — **READ-ONLY** 9.2 I/O; do not claim 9.3 done there. New tests live in a 9.3 file.
- `src/shared/packages/pyforge-warden/tests/unit/test_default_warden_without_checkmarx.py` — **NEW**: I/O matrix. Fixture = `PluginRegistry` with only `engine_factories()` wrappers (no `OPTIONAL_SCAN_PLUGINS`). Monkeypatch `scanner_plugin_registry` (or pass that registry into `select_scanner_plugins`). CLI via `main(["scan", …, "--format", "json", "--allow-empty"])` and one engine-fail path. Include an assertion that fails if absence of a named optional is treated as a Warden failure.
- `src/shared/packages/pyforge-warden/README.md` — 9.3 owns the absence-as-failure CI test (update the "still owns" sentence).

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-warden/tests/unit/test_default_warden_without_checkmarx.py` — new file covering the I/O matrix, including the fail-if-absence-is-failure canary
- `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py` — only if default `_run_scan` currently treats missing optionals as failure (it must not)
- `src/shared/packages/pyforge-warden/src/pyforge/warden/scanner_plugins.py` — keep `OPTIONAL_ABSENT_IS_NOT_FAILURE is True`; no 9.2 rewrite
- `src/shared/packages/pyforge-warden/README.md` — document default-green-without-Checkmarx as 9.3's pin

**Acceptance Criteria:**
- Given a fixture with no Checkmarx (or other named commercial) plugin, when default Warden runs, then the process is green unless Warden's own engines fail.
- Given absence of a named optional plugin, when the 9.3 test suite runs, then a test fails if that absence is treated as a Warden failure.
- Given a missing Checkmarx plugin on a default run, when the gate is composed, then missing Checkmarx is not a failed gate.

## Design Notes

Default run means empty `enabled_optional`, not "Checkmarx enabled but missing." 9.2 already omits a missing *enabled* optional; 9.3 pins the **CLI process** when optionals are not in the registry at all.

Canary shape (do not invert production to make it fail):

```python
def test_absence_of_named_optional_is_not_a_warden_failure(...):
    registry = defaults_only_registry()  # no checkmarx/sonar/…
    selected = select_scanner_plugins(registry=registry)
    assert OPTIONAL_ABSENT_IS_NOT_FAILURE is True
    # CLI default scan on that registry: rc == 0; errors do not mention
    # optional absence / missing checkmarx
```

Engine-fail contrast: monkeypatch a default engine `run` to record a failing rung, or scan a known non-green fixture — assert non-zero (or non-clean status) **and** still no optional-absence error.

## Spec Change Log

## Review Triage Log

### 2026-08-24 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 2, low 3)
- defer: 0
- reject: 18
- addressed_findings:
  - `[medium]` `[patch]` Canary now `pytest.fail`s if `select_scanner_plugins` raises `PluginError` on a defaults-only registry
  - `[medium]` `[patch]` Added live in-tree registry CLI test: default scan does not require Checkmarx enabled
  - `[low]` `[patch]` README heading Stories 9.1–9.3
  - `[low]` `[patch]` Deduplicated `_optional_absence_errors` double CONFIG_VALIDATION filter
  - `[low]` `[patch]` Green CLI tests assert JSON `status` is present (not `clean`, which `--allow-empty` does not promise)

## Verification

**Commands:**
- `pixi run -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/unit/test_default_warden_without_checkmarx.py src/shared/packages/pyforge-warden/tests/unit/test_scanner_plugins.py -q` -- expected: all pass
- `pixi run -e pyforge-warden pyforge-warden-test` -- expected: default suite (`not slow`) still green

## Auto Run Result

Status: done

Summary: Default `warden scan` with no `WARDEN_OPTIONAL_SCANNERS` stays process-green when Checkmarx and other named commercial plugins are absent from the registry (and when the shipped in-tree stubs are present but not enabled). Missing Checkmarx is not a failed gate. Warden's own engines may still fail the process.

Files changed:
- `_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-9-3-default-warden-stays-green-without-checkmarx.md` — tracked story spec
- `src/shared/packages/pyforge-warden/tests/unit/test_default_warden_without_checkmarx.py` — I/O matrix + canary + live default scan
- `src/shared/packages/pyforge-warden/README.md` — 9.3 default-green-without-Checkmarx
- `src/shared/packages/pyforge-warden/src/pyforge/warden/scanner_plugins.py` — comment pointing at the 9.3 test

Review: 5 patches (2 medium, 3 low; follow-up score 9). 0 deferred. Rejected enabled-but-missing as the default run, requiring `status: clean` on `--allow-empty`, rewriting `cli.py` fallback/`register` error handling (9.2 pre-existing), vendor SDKs, and treating live stubs as "Checkmarx installed."

Verification: focused 9.2/9.3 tests 17 passed. `pyforge-warden-test` 2049 passed, 11 deselected.

Residual: absence oracle is still partly phrase-based on JSON `errors`; a differently worded optional-required error could slip through unless it also raises `PluginError` from `select_scanner_plugins`.
