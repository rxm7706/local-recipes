---
title: "99.9: The CI pause dry-run test carries its own clock"
type: 'fix'
created: '2026-11-04'
status: 'done'
baseline_revision: '9c04677719'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
  - src/shared/packages/pyforge-steward/tests/unit/test_ci_pause.py
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** `test_main_pause_dry_run_no_live_gh` passes `--review-by 2026-11-01` through `main` and leaves `CiDeps.now` at
its default, the real clock. `run_pause` refuses a `review_by` in the past, so since 2026-11-02 the test exits 3
(`ci pause: refused — review_by 2026-11-01 is in the past`) and `pyforge-steward-live-test` is red on `main` with no code
change. The preflight of the parked EGM stories found it on 2026-11-04.

**Approach:** the test's `CiDeps` injects `now=lambda: datetime(2026, 10, 13, tzinfo=timezone.utc)`, the clock every sibling
test in the file already uses. `ci.py` does not move; the refusal stays. A `fix` under CAP-166: no CAP, no flag.

Ledger key: `99-9-the-ci-pause-dry-run-test-carries-its-own-clock`. Type / Effort / Deps: fix / XS / —.

## Acceptance Criteria

- **AC1 — The test holds its own clock.** `test_main_pause_dry_run_no_live_gh` passes on any calendar date, and its
  assertions do not change.
- **AC2 — The refusal stands.** `src/shared/packages/pyforge-steward/src/pyforge/steward/ci.py` does not change.
- **AC3 — Green.** `pixi run --frozen -e pyforge-steward pyforge-steward-live-test` passes.

## Boundaries & Constraints

- One test only; no other test, no runtime code.

## Binding

- spec-pyforge-steward CAP-166 (FR-39); Epic 99. The fix lands in the done epic (operator 2026-10-04) and at `done`, so
  `epic-99` stays `done`.

## Verification

```bash
pixi run --frozen -e pyforge-steward pyforge-steward-live-test
```

</intent-contract>

## Spec Change Log

- 2026-11-04: minted `done` from the preflight of the parked EGM stories, where the expired test blocked the merge bar;
  landed in that PR.

## Run results

- 2026-11-04: one `CiDeps` argument added; the full preflight of the landing PR records the lane.

## Review Triage Log

- 2026-11-04 — independent review (separate agent, read-only): clean. The injected `now` reaches the run through the patched `_production_deps`; assertions and `ci.py` are unchanged; every sibling `CiDeps` in the file injects `now`, so the epics block and the Dream entry hold.
