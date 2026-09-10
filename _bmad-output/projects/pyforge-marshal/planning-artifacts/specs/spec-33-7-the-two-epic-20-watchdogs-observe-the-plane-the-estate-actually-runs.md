---
title: 'The two Epic-20 watchdogs observe the plane the estate actually runs'
type: 'fix'
created: '2026-09-09'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
final_revision: 'd421b19cf592418703746528f8aadb0099c3120'
context:
  - spec-bmad-loop-baseline-drift/SPEC.md
  - spec-bmad-loop-intent-gap-work-preservation/SPEC.md
  - spec-marshal-token-economy/SPEC.md
warnings: []
deferred: []
baseline_revision: '9109bb0f8e381c9db6de3f051d4c02fbe51e604c'
---

<intent-contract>

## Intent

**Problem:** `scripts/bmad_loop_baseline_drift_check.py` and `scripts/missing_preserve_check.py` scan only `~/.bmad-loops/<slug>/.bmad-loop/runs/` (and loop-home marshal journals). The live engine is `marshal factory dispatch`, whose journals live under `_bmad-output/projects/<slug>/implementation-artifacts/dispatch-runs/`. With loop homes dormant since 2026-08-22, both detectors exit 0 "OK" over an empty observation plane — a false green per `pixi.toml:1033`.

**Approach:** Teach each detector to examine **both** planes (legacy loop-home and in-repo dispatch-runs), classify observability per plane, and exit **2** (`could-not-observe`) when neither plane has any run to examine — never 0 on vacuum.

## Boundaries & Constraints

**Always:** Keep `DETECTOR = {"scope": "runtime"}`; never import `bmad_loop` or `pyforge.marshal`. Preserve existing finding semantics and exit 0/1 behavior when at least one plane has runs. Name the reason on exit 2. Module-level `LOOP_ROOT` and `REPO` stay monkeypatchable for tests.

**Never:** Move detectors into `pyforge.doctor.sources`; change CAP-1/CAP-3 finding shapes; or treat "loop root missing" as clean silence.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| EMPTY_PLANES | Neither loop-home nor dispatch-runs has any run directory | Exit 2, message names `could-not-observe` and both planes | Never exit 0 |
| LOOP_ONLY_CLEAN | Loop-home runs exist, no drift/preserve gaps | Exit 0 OK | No error |
| DISPATCH_ONLY_CLEAN | Dispatch-runs journals exist, no findings | Exit 0 OK | No error |
| DRIFT_FIRE | Baseline-drift defer in either plane, story not done in ledger | Exit 1 with finding | Unchanged CAP-1 shape |
| MISSING_PRESERVE_FIRE | Intent-gap halt without artifact in either plane | Exit 1 with finding | Unchanged CAP-3 shape |
| RECOVERED_SILENT | Drift defer present but ledger marks story done | Exit 0 | Unchanged |

</intent-contract>

## Code Map

- `scripts/bmad_loop_baseline_drift_check.py:72,:142` — `LOOP_ROOT` loop-home scan only; `:178-180` false-green when missing
- `scripts/missing_preserve_check.py:61,:84-103` — `_iter_marshal_journals` reads loop-home Tier-3 `runs/` only; `:266-268` false-green when missing
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py:127-135` — canonical `dispatch-runs/` path shape (reference only, do not import)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_preserve.py:19-21` — dispatch failed patch layout `run_dir/failed/<story>/changes.patch`
- `tests/scripts/test_bmad_loop_baseline_drift_check.py` — extend with EMPTY_PLANES exit-2 + dispatch-plane drift test
- `tests/scripts/test_missing_preserve_check.py` — extend with EMPTY_PLANES exit-2 + dispatch-plane journal test
- `scripts/detectors.py:34-43` — exit 2 = could-not-run contract (unchanged; detectors must emit rc 2)

## Tasks & Acceptance

**Execution:**
- `scripts/bmad_loop_baseline_drift_check.py` — add dispatch-runs scan under `REPO/_bmad-output/projects/*/implementation-artifacts/dispatch-runs/*/journal.jsonl`; return observability metadata; exit 2 when zero runs on both planes
- `scripts/missing_preserve_check.py` — add `_iter_dispatch_journals(repo)` for dispatch-runs; resolve preserve artifacts relative to run_dir; exit 2 when zero runs on both planes
- `tests/scripts/test_bmad_loop_baseline_drift_check.py` — test empty both planes → exit 2; test drift in dispatch-runs → exit 1
- `tests/scripts/test_missing_preserve_check.py` — test empty both planes → exit 2; test missing preserve in dispatch-runs → exit 1

**Acceptance Criteria:**
- Given neither loop-home nor dispatch-runs contains any run directory, when either detector runs, then it exits 2 with a message naming could-not-observe — never 0
- Given a baseline-drift defer journal under dispatch-runs and the story is not done in the tracked ledger, when baseline-drift-check runs, then it exits 1 naming the story and baselines
- Given an intent-gap escalation without preserve artifact under dispatch-runs, when missing-preserve-check runs, then it exits 1 with a missing-preserve finding
- Given a clean journal on at least one plane, when either detector runs, then it exits 0 (not 2)

## Spec Change Log

## Review Triage Log

### 2026-09-09 — Review pass
- verdicts: 3 findings — high 0, medium 0, low 1, false 2, maybe-false 0
- findings:
  - `[false]` `[reject]` fleet_picture baseline_drift_findings only accepts exit 0/1 — exit 2 already raises CalledProcessError and degrades ATTENTION correctly per existing try/except
  - `[false]` `[reject]` duplicate code between detectors for dispatch iteration — intentional detector isolation per Story 20.1/20.5 placement decision
  - `[low]` `[reject]` `--json` could-not-observe emits object not array — acceptable for machine consumers distinguishing empty-findings from unobservable

## Auto Run Result

Status: done

**Summary:** Both Epic-20 runtime watchdogs (`baseline-drift-check`, `missing-preserve-check`) now scan loop-home `.bmad-loop/runs/` and in-repo `dispatch-runs/` journals. When neither plane has runs to examine they exit 2 with `could-not-observe` instead of false-green 0.

**Files changed:**
- `scripts/bmad_loop_baseline_drift_check.py` — dual-plane scan + observability exit 2
- `scripts/missing_preserve_check.py` — dispatch-runs journals + run_dir-aware preserve lookup + exit 2
- `tests/scripts/test_bmad_loop_baseline_drift_check.py` — EMPTY_PLANES + dispatch drift tests
- `tests/scripts/test_missing_preserve_check.py` — EMPTY_PLANES + dispatch missing/present tests
- `tests/scripts/test_fleet_picture_baseline_drift_attention.py` — tuple unpack fix
- `spec-33-7-…md` — story contract
- `sprint-status-ledger.yaml` — 33-7 → done

**Review:** 0 patches applied; 3 findings rejected as false/low.

**Verification:** `pytest tests/scripts/test_bmad_loop_baseline_drift_check.py tests/scripts/test_missing_preserve_check.py -q` → 21 passed.

**Residual risks:** Live estate may still exit 2 until dispatch-runs accumulate journals — that is the intended honest signal, not a regression.

## Verification

**Commands:**
- `pixi run -e local-recipes python -m pytest tests/scripts/test_bmad_loop_baseline_drift_check.py tests/scripts/test_missing_preserve_check.py -q` — expected: all pass
