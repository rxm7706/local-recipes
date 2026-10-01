---
title: "38.5: The detector-aggregate tests run where Doctor's run-deps are installed"
type: 'fix'
created: '2026-10-01'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-38-3-the-fleet-hygiene-sweep-runs-with-the-other-detectors-warn-only.md
  - tests/scripts/test_detectors_doctor_sources.py
  - .github/workflows/detectors.yml
  - pixi.toml
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** Story 38.3 added three tests to `tests/scripts/test_detectors_doctor_sources.py`
(`test_every_doctor_source_task_name_is_a_dispatch_entry`,
`test_a_warn_only_hygiene_source_reads_pass_and_leaves_the_exit_code`,
`test_the_real_hygiene_gather_runs_through_the_aggregate_and_reads_pass`). Each imports Doctor's dispatch table
(`pyforge.doctor.sources.__main__`), which imports `sources/docs_currency.py` (`jsonschema`, `yaml` at module level).
The Detectors workflow's `scripts-suite` job runs `tests/scripts` in `pyforge-ci`, which is stdlib-only by design, so all
three fail there (`ModuleNotFoundError: No module named 'jsonschema'`); `main` went red on that lane at `d6b0a85992`
(run 36844391956). The dispatch landed regardless: `scripts-suite` is not a required check, and `pr-preflight` has no
twin for it.

**Approach:**

- In the three tests, `pytest.importorskip("pyforge.doctor.sources.__main__")` before using the dispatch table, so they
  skip, naming the missing module, where Doctor's run-deps are absent. The file already accepts an unimportable Doctor
  in that lane (`test_main_scope_repo_reports_unknown_rows_and_never_exits_zero_when_unimportable`).
- Add a second step to the Detectors workflow's `scripts-suite` job, installing `pyforge-doctor` beside `pyforge-ci`:
  `pixi run --frozen -e pyforge-doctor python -m pytest tests/scripts/test_detectors_doctor_sources.py -q`, so the three
  run for real in CI. (The `detectors` job's own `detectors` env has no pytest, and adding it would change `pixi.toml`.)

Ledger key: `38-5-the-detector-aggregate-tests-run-where-doctor-s-run-deps-are-installed`.
Type / Effort / Deps: fix / XS / S-38.3.

### Living CAP citations

- CAP-42, CAP-43 (Story 38.3, the hygiene sweep wired in warn-only). A defect of 38.3's tests, so no new CAP;
  `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given the `pyforge-ci` env When `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` runs Then it exits 0 and the three tests report skipped with the missing module named
- Given the `pyforge-doctor` env When `python -m pytest tests/scripts/test_detectors_doctor_sources.py` runs Then every test passes and none skips
- Given the Detectors workflow When its `scripts-suite` job runs Then it runs that file a second time under `pyforge-doctor`

## Boundaries & Constraints

**Always:**
- `pyforge-ci` stays stdlib-only.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not delete or weaken any assertion in the three tests.
- Do not add `jsonschema` or `pyyaml` to `pyforge-ci`.

</intent-contract>

## Binding

Parent capabilities: CAP-42, CAP-43 (defect of Story 38.3's tests; no new CAP).
Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-01 (later) entry.
Ledger key: `38-5-the-detector-aggregate-tests-run-where-doctor-s-run-deps-are-installed`.
Ledger status at mint: `backlog`.
Deps: S-38.3.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: exit 0, the three tests skipped.
- `pixi run --frozen -e pyforge-doctor python -m pytest tests/scripts/test_detectors_doctor_sources.py -q` — expected: all pass, none skipped.

## Review Triage Log

- No independent review ran: an XS hand-landed fix restoring `main`'s red `scripts-suite` lane (a test-guard and one CI
  step, no production code). `followup_review_recommended: true` puts it in the follow-up review queue (marshal CAP-281).

## Auto Run Result

Hand-built in an interactive session after `main`'s Detectors `scripts-suite` went red at `d6b0a85992` (run
36844391956) on Story 38.3's landing. Verification:

- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — exit 0: 1102 passed, 18 skipped (the three guarded
  tests among them).
- `pixi run --frozen -e pyforge-doctor python -m pytest tests/scripts/test_detectors_doctor_sources.py -q` — exit 0:
  19 passed, none skipped.

**Found while here (not fixed by this story):** the dispatch supervisor merged PR #1709 while its `Detectors /
scripts-suite` check was failing, because that check is not required on `main`; and `pr-preflight` has no twin for the
`scripts-suite` lane. Both are reported to the operator (a branch-protection setting and a preflight leg).
