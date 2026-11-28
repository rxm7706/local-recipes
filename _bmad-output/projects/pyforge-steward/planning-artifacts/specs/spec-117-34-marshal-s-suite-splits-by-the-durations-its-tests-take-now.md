---
title: '117.34: Marshal''s suite splits by the durations its tests take now'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 117-34-marshal-s-suite-splits-by-the-durations-its-tests-take-now
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'tests/durations/pyforge-marshal.json'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `marshal-test` runs four shards, split by pytest-split from `tests/durations/pyforge-marshal.json`. Over nine CI runs on 2026-11-27 its shards averaged about 53, 67, 47 and 63 s of tests, and the slowest set the job (up to 84 s of tests and 106 s in all). The same split shows locally at four workers (20, 28, 18 and 24 s), so the cause is the file, not the runner. Stored on 2026-11-25, it sums to 732 s where the suite now takes 239 s. Tests made faster since still weigh their old times: the seed-engine copier tests went from 5 s to 1 s, and the real-git landing tests from 2 s to 0.3 s. Scored by fresh times, the file's split gives the shards 47, 77, 46 and 68 s of work.

**Approach:** store the file again from empty: `--store-durations` into a new path, under `pyforge-marshal-test` with `PYTEST_XDIST_AUTO_NUM_WORKERS=4`, so the xdist group suffixes are recorded. Then replace the tracked file with it.

Ledger key: `117-34-marshal-s-suite-splits-by-the-durations-its-tests-take-now`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- The same tests run, each in one shard.

**Never:**
- Never change a test, a job or a lane.

## Acceptance Criteria

**Given** marshal's collected unit and meta tests
**When** pytest-split splits them four ways by the new file
**Then** each shard holds about the same work, and every test is in exactly one shard

- **AC1 — The four groups pass and hold every collected test once.** Run `PYTEST_ADDOPTS="--splits 4 --group <n> --durations-path tests/durations/pyforge-marshal.json" pixi run --frozen -e pyforge-marshal pyforge-marshal-test` for n from 1 to 4. Expected: each exits 0, and the passed and skipped counts sum to the 13,791 collected tests.

- **AC2 — The durations-files test passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_durations_files.py -q
  ```

</intent-contract>

## Result (2026-11-27)

- Scored by fresh times, the new file's split gives the shards 59.6, 59.5, 59.5 and 59.4 s of work.
- Locally at four workers the four groups take 25.1, 24.1, 22.2 and 22.4 s, where they took 20.4, 27.9, 17.7 and 24.4 s. The file had known all but 10 of the 13,791 tests, so the change is in the weights, not the coverage.
- AC1: the four groups pass and hold 13,791 tests, each once.
