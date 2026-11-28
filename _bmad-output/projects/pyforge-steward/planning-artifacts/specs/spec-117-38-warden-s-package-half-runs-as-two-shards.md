---
title: '117.38: Warden''s package half runs as two shards'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 117-38-warden-s-package-half-runs-as-two-shards
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - '.github/workflows/pyforge-station-tests.yml'
  - 'tests/durations/pyforge-warden.json'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `warden-test` is one job of 88 to 92 s, 55 to 65 s of it the suite (108 summed seconds on the runner). The other long station suites run in shards (Story 117.10).

**Approach:** run it as two shards, the way `steward-test` runs:
- a `group: [1, 2]` matrix, with `PYTEST_ADDOPTS: --splits 2 --group ${{ matrix.group }} --durations-path tests/durations/pyforge-warden.json`;
- the file written from the runner's times (Story 117.35);
- each shard renames and uploads its coverage report as `warden-unit-<group>`;
- `warden-gate` reads `warden-unit*.json`.

Ledger key: `117-38-warden-s-package-half-runs-as-two-shards`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Every test runs, in exactly one shard; the gate judges both shards' reports with the live half's.

**Never:**
- Never change the local task: the preflight runs it unsharded.

## Acceptance Criteria

**Given** warden's package half
**When** it runs as two shards by the runner-timed file
**Then** each shard holds about half the suite, and `warden-gate` passes on the merged reports
**And** `tests/scripts/test_durations_files.py` finds the file the workflow names

- **AC1 — The durations-files test passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_durations_files.py -q
  ```

- **AC2 — A dispatched run.** Expected: both `warden-test` shards and `warden-gate` pass.

</intent-contract>

## Result (2026-11-27)

Scored by the runner's times, the two shards hold 55 and 53 s of the suite's 108 summed seconds.
