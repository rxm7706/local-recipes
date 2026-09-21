---
title: '24.1: The evaluator and the thresholds move out of marshal''s package, together'
type: 'feature'
created: '2026-09-16'
status: 'done'
baseline_revision: '2f98ede57d5ebb7df285bbd1383782cf6a7c86af'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** coverage_gate.py and coverage_thresholds.toml ship inside marshal, so a three-line [stations.marshal] edit lowers the floor that reds marshal's own PRs with no Doctor verdict.

**Approach:** Move evaluator and thresholds together out of pyforge.marshal. Re-point every caller. Amend the AD-3/AD-4 contract in the same change. Floors stay byte-identical. No pyforge.<station> module is the evaluator of any station's CI gate.

## Boundaries & Constraints

**Always:**
- Evaluator and thresholds move together, never CAP-2 alone.
- Effective floors are byte-identical before and after.
- docs/governance/coverage-thresholds.toml carries the governance-act $comment.

**Never:**
- Do not leave the evaluator inside any pyforge.<station> package.
- Do not change any station's floor as a side effect.
- Do not invent a pyforge-gates ninth package.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| after move | import pyforge.marshal.coverage_gate | resolves nowhere | n/a |
| CI tasks | eight coverage-gate pixi tasks | call the new home; same floors | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-coverage-gate-independence CAP-1 CAP-2`.
Surface: pyforge/marshal/coverage_gate.py and coverage_thresholds.toml removed; docs/governance/coverage-thresholds.toml; evaluator outside every pyforge.<station> package; scripts/coverage_gates_ci.py; scripts/run_station_coverage_gate.py; .github/workflows/coverage-gates.yml; eight pyforge-<station>-coverage-gate tasks; marshal AD-3/AD-4 import-linter contract and marshal tests for the old module..
Ledger key: `24-1-the-evaluator-and-the-thresholds-move-out-of-marshals-package-together`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-24-1-the-evaluator-and-the-thresholds-move-out-of-marshals-package-together.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

## Review Triage Log

### 2026-09-20 — Review pass
- verdicts: 9 findings — high 0, medium 1, low 7, false 1, maybe-false 0
- findings:
  - `low` `patch` blind-hunter: `scripts/coverage_gate.py:603` `--thresholds` argparse help text still said "defaults to packaged coverage_thresholds.toml" after the move — verified stale (file is no longer packaged; new home is `docs/governance/coverage-thresholds.toml`). Fixed: help string now names the new path.
  - `low` `patch` blind-hunter: `docs/governance/spec-coverage-gate-independence/SPEC.md` frontmatter `updated: "2026-09-14"` was unchanged despite this diff materially rewriting `surface:` (dated 2026-09-20 in its own comment) — verified stale. Fixed: bumped to `"2026-09-20"`.
  - `low` `patch` blind-hunter: `spec-pyforge-testing-charter/.memlog.md` frontmatter `updated: 2026-09-20T09:35` was unchanged despite a new appended event, unlike the sibling `spec-pyforge-marshal/.memlog.md` which correctly bumped its own `updated:` for an analogous append in the same diff — verified stale. Fixed: bumped to `2026-09-20T19:52`.
  - `low` `patch` blind-hunter: `spec-pyforge-marshal/.memlog.md`'s reconcile entry named two of four moved test files in abbreviated form (missing the `src/shared/packages/pyforge-marshal/` prefix) — verified live via `python -m pyforge.doctor.sources spec-surface`, which reported `drift-presumed: warn` for exactly those two paths. Fixed: appended a follow-up memlog entry naming both paths in full; re-run of the same live check shows zero `drift-presumed` findings.
  - `false` `reject` blind-hunter: claimed `sprint-status-ledger.yaml`/`epics.md` Story 24.1 still reading `backlog` risks a marshal drain re-dispatching a mid-flight story. Refuted: ledger/epics status promotion is explicitly owned by the separate landing process (marshal `dispatch_land` / `sprint-ledger-sync`, spec-pyforge-marshal:CAP-261; AGENTS.md: "never hand-edit `sprint-status-ledger.yaml`"), not by this build-auto dev/review pass — the dispatch branch/worktree already existing is what prevents duplicate dispatch, not the ledger field, and this workflow's own steps never touch that file.
  - `low` `reject` blind-hunter: claimed the spec's own `## Verification` section names only the doctor suite and doesn't exercise the marshal suite or the relocated `tests/scripts/` files. Real as a textual fact, but its only fix is editing this build's spec — auto-rejected per the standing rule (reject any finding whose fix is to edit this build's spec). Verification was practically broadened anyway during this pass: the marshal suite, `tests/scripts`, `lint-types`, and `detectors-ci` were all run and read directly alongside the spec's own named command.
  - `low` `patch` blind-hunter: `tests/scripts/test_coverage_gates_ci_driver.py` used `src/shared/packages/pyforge-marshal/src/pyforge/marshal/coverage_gate.py` — the exact file this diff deletes — as its example "touched module" fixture string; mechanically harmless (a monkeypatched string) but a confusing stale reference. Verified. Fixed: swapped the example to `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/main.py`, a path confirmed to still exist.
  - `low` `patch` edge-case-hunter: `tests/scripts/test_coverage_gate_names_module.py`, `test_coverage_gate_ast_fingerprint.py`, `test_coverage_gate_module_floors.py`, and `src/shared/packages/pyforge-marshal/tests/meta/test_dispatch_supervisor_main_coverage_floor.py` each call `importlib.util.spec_from_file_location(...)` then `module_from_spec()`/`exec_module()` with no guard against a `None` return, unlike the sibling `test_coverage_gates_ci_driver.py::_load_driver()`'s `assert spec and spec.loader` — verified by reading all four helpers. Fixed: added the same guard to all four.
  - `medium` `patch` verification-gap (pre-verified per layer rule): `scripts/run_station_coverage_gate.py` received the identical evaluator-import repoint as `scripts/coverage_gates_ci.py`, but unlike its sibling (covered by `test_coverage_gates_ci_driver.py`), no test anywhere loads or executes it — a future change to its `_SCRIPTS_DIR` computation could silently break all eight `pyforge-<station>-test-coverage` operator tasks with zero automated signal; confirmed no test references this file before or after this diff, and confirmed the live task (`pyforge-doctor-test-coverage`) currently runs correctly. Fixed: added `tests/scripts/test_run_station_coverage_gate.py` mirroring the sibling's loader-test shape.

Intent-alignment layer reported no defect (strictly descriptive, per its own instructions): it confirmed this diff implements Story 24.1's Given/When/Then point for point, and that the Problem statement's broader "no Doctor verdict" framing is scoped to Stories 24.2/24.3 (both `backlog`, not this story) rather than a gap in this diff. No finding to route.

## Auto Run Result

**Summary:** `pyforge.marshal.coverage_gate` (evaluator) and `pyforge.marshal.coverage_thresholds.toml` moved together to `scripts/coverage_gate.py` and `docs/governance/coverage-thresholds.toml`, outside every `pyforge.<station>` package (spec-coverage-gate-independence CAP-1/CAP-2). Every caller re-pointed; marshal's AD-3 import-linter contract amended in the same change; effective floors byte-identical (80/70 defaults, no station overrides, no module exceptions) before and after; no `pyforge-gates` ninth package invented.

**Files changed:**
- `scripts/coverage_gate.py` (new home; moved from `pyforge/marshal/coverage_gate.py`) — evaluator logic unchanged except `default_thresholds_path()`, the CLI `prog=`, and the `--thresholds` help string, all repointed to the new location.
- `docs/governance/coverage-thresholds.toml` (new home; moved from `pyforge/marshal/coverage_thresholds.toml`) — governance-act comment header prepended; `[defaults]`/no-override data byte-identical.
- `scripts/coverage_gates_ci.py`, `scripts/run_station_coverage_gate.py` — evaluator import repointed to the `scripts/` sibling via an explicit `sys.path` insert of their own directory.
- `.github/workflows/coverage-gates.yml` — trigger paths and the shared-surface diff check gained the two new paths; the "Named-module fixture proof" step moved from `matrix.station == 'marshal'` to `== 'doctor'` (the mechanism owner).
- `src/shared/packages/pyforge-marshal/pyproject.toml` — AD-3 `source_modules` drops `pyforge.marshal.coverage_gate`; the `coverage_thresholds.toml` wheel force-include dropped.
- `src/shared/packages/pyforge-marshal/tests/meta/test_ad3_ad4_import_linter.py` — matching literal updated; gained `test_old_coverage_gate_module_path_resolves_nowhere` (Matrix Test Audit, closes the "resolves nowhere" I/O row).
- `src/shared/packages/pyforge-marshal/tests/meta/test_dispatch_supervisor_main_coverage_floor.py` — now dynamic-loads `scripts/coverage_gate.py` via `importlib` instead of importing the removed package path; gained the `assert spec and spec.loader` guard (review patch).
- `tests/scripts/test_coverage_gate_{names_module,ast_fingerprint,module_floors}.py`, `tests/scripts/test_coverage_gates_ci_driver.py` — moved out of marshal's own suite (`tests/meta`/`tests/unit`) into `tests/scripts/`, converted to the repo's `importlib.util.spec_from_file_location` loading idiom; each `_load_coverage_gate()` helper gained the `assert spec and spec.loader` guard (review patch); the driver test's stale fixture-path example corrected (review patch).
- `tests/scripts/test_run_station_coverage_gate.py` (new) — closes the verification-gap finding: mirrors `test_coverage_gates_ci_driver.py`'s loader shape against `scripts/run_station_coverage_gate.py`.
- `docs/governance/spec-coverage-gate-independence/SPEC.md`, its `.memlog.md`, `spec-pyforge-marshal/.memlog.md`, `spec-pyforge-testing-charter/.memlog.md` — surface declared, reconcile entries recorded (incl. two follow-up entries from review patches), stale `updated:` frontmatter corrected (review patches).
- `scripts/spec_surface_allowlist.txt` — `scripts/coverage_gate.py` allowlisted (the owning Spec is guild-owned under `docs/governance/` and cannot declare a surface for `spec_surface_check.py`'s own `SPEC_GLOB`, same shape as `chain_sprawl_baseline.py`).

**Review findings breakdown** (9 total; full evidence in the Review Triage Log above):
- Patched (7): stale `--thresholds` CLI help text; stale `SPEC.md` `updated:` frontmatter; stale testing-charter memlog `updated:` frontmatter; two memlog-named paths corrected to full form (closing a live `drift-presumed: warn` pair); stale fixture-path example in `test_coverage_gates_ci_driver.py`; missing `assert spec and spec.loader` guard in four loader helpers; missing test coverage for `run_station_coverage_gate.py`'s repointed import (medium — new `tests/scripts/test_run_station_coverage_gate.py`).
- Rejected — false (1): claimed stale ledger/epics `backlog` status risks duplicate re-dispatch; refuted — ledger/epics promotion is owned by the separate landing process (spec-pyforge-marshal:CAP-261), never by this dev/review workflow.
- Rejected — low, spec-edit rule (1): claimed the spec's own `## Verification` section under-scopes the actual surface; real as a textual fact, but its only fix is editing this build's spec (auto-reject rule) — mitigated in practice by running the marshal suite, `tests/scripts`, `lint-types`, and `detectors-ci` directly during this pass.
- No `intent_gap` or `bad_spec` findings; no review-loop iteration triggered.

**Follow-up review recommendation:** `false`. Only one `medium` entry was patched (the missing test coverage) and zero `high` entries — below the "two or more medium" / "any high" threshold for a first pass.

**Verification performed:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` (the spec's own Verification command) — 1889 passed, 1 skipped.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 8447 passed, 1 skipped, 12 deselected (one unrelated flake on `test_wrapped_launch_keeps_a_fallback_dir_cli_reachable`, a timing-sensitive subprocess test in `test_harness_bmadbuild.py` untouched by this diff, reproduced clean in isolation and on a contention-free re-run of the full suite).
- `pixi run -e pyforge-ci pyforge-doctor-scripts-test` (`tests/scripts`) — 591 passed, 5 skipped.
- `pixi run -e pyforge-guild lint-types` — ruff / ruff-format / mypy / target-version / precommit-config clean across all ten packages.
- `pixi run -e pyforge-guild detectors-ci` — exit 0, no findings (`spec-surface` included).
- `python scripts/spec_surface_reconcile.py` — `OK: every tracked file governed or allowlisted; no drift.` — the S-13.7 producer guard; per this dispatch's explicit instruction, `--write-baseline` was never run by this session (reverted twice after the implementation subagent ran it unprompted); reconciliation rests solely on the memlog entries named above, for the landing step to stamp.
- `pixi run -e pyforge-guild pyforge-station-coverage-gates` (all eight stations) and `python scripts/coverage_gate.py show-thresholds` — ran clean end-to-end through the new home; floors identical (80/70) across all eight stations, confirming the I/O matrix's second row.
- `python -m pyforge.doctor.sources spec-surface` (direct, WARN-inclusive) — re-run after the review patch: zero `drift-presumed` findings remain.

**Residual risks:** none identified as unverified. Stories 24.2 (structural import-linter contract) and 24.3 (surface reconciliation handoff for the two `scripts/` drivers) are separate, dependent, `backlog` stories per `epics.md` — intentionally out of this story's scope, not a gap in this diff.

