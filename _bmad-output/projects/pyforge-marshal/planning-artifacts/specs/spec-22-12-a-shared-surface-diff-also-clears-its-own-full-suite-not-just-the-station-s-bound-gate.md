---
title: A shared-surface diff also clears its own full suite, not just the station's bound gate
type: feature
created: '2026-09-11'
status: in-progress
updated: '2026-09-11'
baseline_revision: 8365d1f0f5e62fb810f113fa719ad4def5d46c4a
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-single-story-dispatch/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-22-3-verification-is-the-product-no-landing-on-a-self-report.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** CAP-3's bound per-station verify command is a floor, not a ceiling. A dispatch whose diff touches the shared Django host (`src/platform/`) can pass its station-bound gate while shipping defects only caught by the platform's full CI test suite — live on steward Story 49.14 rescue (2026-09-10/11).

**Approach:** Reuse the `changed` diff `evaluate_dispatch_verification` already reads for scope. When any changed path is under hardcoded `src/platform/`, run the station-bound commands first (unchanged), then additionally run `pixi run -e local-recipes platform-ci-local -- --test` via the same `ProcessPort` + `classify_outcome` path. Failures emit a new `MRS-GATE-015` finding (GATE_FAILED), distinct from station-bound `MRS-GATE-001`. Pure detection helpers live in `core/gate.py` alongside existing gate classifiers.

## Boundaries & Constraints

**Always:** Station-bound `MRS-GATE-010`/`011` verify commands run first and unchanged. Cross-surface gate keys on diff paths under `src/platform/` only — never on which station dispatched. Shared directory prefix is hardcoded (CAP-12 non-goal against reopening per-station binding).

**Never:** Cross-surface failure downgraded to advisory or silently skipped. Cross-surface check does not replace station-bound gate. Do not make `platform-ci-local` configurable per station.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| STATION_ONLY_DIFF | Changed files only under station package tree | Station verify runs; cross-surface command not invoked; no `MRS-GATE-015` | No error expected |
| PLATFORM_DIFF_PASS | Changed files include `src/platform/...`; platform-ci-local exits 0 | Station verify + cross-surface both run; verification VERIFIED if no other findings | No error expected |
| PLATFORM_DIFF_FAIL | Changed files include `src/platform/...`; station verify green; platform-ci-local exits non-zero | `MRS-GATE-015` GATE_FAILED; verification REFUSED | Named refusal, not landing |
| CROSS_STATION_BAR | Two stories from different stations, both diff `src/platform/` | Identical cross-surface command and finding shape | No station-specific bypass |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py` — `evaluate_dispatch_verification`: after existing station verify + scope + reclassify, invoke cross-surface command when `gate.changed_files_touch_shared_surface(changed)`; record in envelope `data["cross_surface_check"]`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py` — pure helpers: `SHARED_SURFACE_PREFIX`, `changed_files_touch_shared_surface`, `shared_surface_verify_command`, `cross_surface_failure_code` (`MRS-GATE-015`); use existing `classify_outcome` for run results.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` — register `MRS-GATE-015`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py` — classify `MRS-GATE-015` as `Verdict.GATE_FAILED` (same rung as `MRS-GATE-001`, never WARN).
- `src/shared/packages/pyforge-marshal/tests/unit/test_findings.py` — add `MRS-GATE-015` to expected registry set.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verification.py` — unit tests for matrix rows via `FakeProcess`/`FakeVcs` (extend `FakeProcess` to recognize platform-ci-local token signature).

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py` — add shared-surface prefix detection + command constant + `MRS-GATE-015` code constant — pure helpers for dispatch_verify.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py` — wire additive cross-surface verify after station commands when diff touches `src/platform/` — CAP-12 driver.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` — register `MRS-GATE-015`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py` — map `MRS-GATE-015` → `GATE_FAILED`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verification.py` — matrix coverage + 49.14-style fixture (bound green, platform red → REFUSED naming `MRS-GATE-015`).
- `src/shared/packages/pyforge-marshal/tests/unit/test_findings.py` — registry membership for `MRS-GATE-015`.

**Acceptance Criteria:**
- Given a diff touching only the dispatch station's package, when verification runs, then behavior matches pre-22.12 (no cross-surface command, no `MRS-GATE-015`).
- Given a diff touching `src/platform/`, when verification runs, then station-bound verify runs first and `platform-ci-local -- --test` additionally runs.
- Given the 49.14 replay (station verify green, platform suite red), when verification runs, then verdict is REFUSED with `MRS-GATE-015`, not VERIFIED.
- Given two dispatches from different stations with platform diffs, when verification runs, then both use the same cross-surface command and finding code.

## Verification

**Commands:**
- `pixi run -e pyforge-marshal pyforge-marshal-test` — expected: all unit tests pass including new cross-surface cases.
