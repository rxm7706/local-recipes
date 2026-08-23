---
title: Referenced-dependency verification and Doctor delegation
type: feature
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: f8c74d8db3
---

<intent-contract>

## Intent

**Problem:** `marshal seed check` and `marshal seed update` classify manifest `referenced` entries as always conformant but never verify that the machine can actually run the factory tools those entries declare (FR-95).

**Approach:** Add `seed/detect/referenced_deps.py`: verify every `referenced` manifest entry against its `pin` (local probe, no network). Missing or below-floor → `referenced-dep-missing` at DRIFT. When `doctor` is on PATH, try delegating via `python -m pyforge.doctor.sources genesis-referenced-deps --json` first; successful JSON is converted to Marshal findings prefixed `[doctor]`. Compose into `run_check` and `run_update` (report only on update — never blocks apply).

## Acceptance Criteria

- Given manifest REFERENCED entries with pins, when `marshal seed check` or `marshal seed update` runs, then each dependency's presence and floor is verified.
- Given a missing or below-floor dependency, then `referenced-dep-missing` at DRIFT (not HARD).
- Given Doctor available on PATH with a successful delegation response, then Doctor's findings are reported (not duplicated locally) and marked `[doctor]`.
- Given no Doctor delegation, then the minimal local probe completes with no network calls.

</intent-contract>

## Code Map

- `src/pyforge/marshal/seed/detect/referenced_deps.py` — NEW: probe + Doctor delegation seam
- `src/pyforge/marshal/seed/verbs/check.py` — compose referenced dep findings
- `src/pyforge/marshal/seed/verbs/update.py` — `UpdateResult.referenced_dep_findings`
- `src/pyforge/marshal/cli/seed.py` — render update referenced-dep section
- `tests/unit/test_seed_detect_referenced_deps.py` — NEW

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
- `pixi run --frozen -e pyforge-ci pytest tests/packaging/test_dependency_completeness.py -k pyforge-marshal`

## Auto Run Result

**Summary:** Added `seed/detect/referenced_deps.py` to verify manifest `referenced` entries against their
`pin` floors in both `marshal seed check` and `marshal seed update`. Missing or below-floor deps emit
`referenced-dep-missing` at DRIFT severity. When `doctor` is on PATH, delegation is attempted via
`python -m pyforge.doctor.sources genesis-referenced-deps --json`; successful JSON is converted to
Marshal findings prefixed `[doctor]`. Without Doctor, a local no-network probe covers CLI tools
(`shutil.which` + `--version`), bmad manifest entries, and conda-meta filename parsing. Update reports
findings only — never blocks apply.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/referenced_deps.py` — NEW
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/check.py` — compose referenced dep findings
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/update.py` — `UpdateResult.referenced_dep_findings`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/seed.py` — render update referenced-dep section
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_detect_referenced_deps.py` — NEW (5 tests)
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_check.py` — DRIFT finding test
- `src/shared/packages/pyforge-marshal/pyproject.toml` + member `pixi.toml` — `packaging>=24.0`

**PR:** https://github.com/rxm7706/local-recipes/pull/639 — merged `899bdda78b4` (merge commit), feature `756657c60e`.
