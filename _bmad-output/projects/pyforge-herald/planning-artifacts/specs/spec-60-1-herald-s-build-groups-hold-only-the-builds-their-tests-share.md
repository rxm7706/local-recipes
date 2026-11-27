---
title: '60.1: Herald''s build groups hold only the builds their tests share'
type: 'chore'
created: '2026-11-26'
status: 'done'
story: 60-1-herald-s-build-groups-hold-only-the-builds-their-tests-share
spec: spec-pyforge-herald
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-herald/tests/meta/test_agent_surface_and_changes.py'
  - 'src/shared/packages/pyforge-herald/tests/meta/test_one_generator.py'
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
  - docs/dreams/pyforge-steward.md
  - src/shared/packages/pyforge-herald/tests/conftest.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Herald's longest live shard on CI takes 76 to 89 s of tests. A shard's wall is at least its heaviest xdist group on one worker, and `tests/conftest.py` groups a builder module's tests by the module fixtures they share (Story 59.1). Two groups join builds their tests need not share:

- `test_agent_surface_and_changes.py` keeps five builds behind one lazy `build(name)` fixture, so the five run in turn on one worker (52.9 s).
- `test_one_generator.py` joins `built` and `built_with_marketplace` through `test_109_3`, which reads both, and keeps `test_43_5`, which compares `built` with a build of its own, in `built`'s group (47.5 s).

**Approach:**
- Each of the agent-surface module's five builds becomes its own module fixture.
- `test_ac7` and `test_ac6`, which each read two builds, become one test per build, with the same assertions.
- `test_109_3` becomes one test for the flag on and one for the flag off.
- `test_43_5` makes both of its builds itself.

Ledger key: `60-1-herald-s-build-groups-hold-only-the-builds-their-tests-share`.

### Living CAP citations

- spec-pyforge-steward:CAP-175 (realized here; no text change in this station's Spec).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Every assertion a split test made is made by one of the tests that replace it.
- A build's fixture builds what the old fixture built for that name, with the same inputs and flags.

**Never:**
- Never skip, re-mark or delete a test, or weaken a coverage floor.

## Acceptance Criteria

**Given** herald's live half
**When** it runs under xdist
**Then** it passes, and no xdist group of these two modules holds more than one of their builds, except `test_43_5`'s own pair

- **AC1 — Herald's live half passes with every build required.** Expected: exit 0, none skipped for a missing install.

  ```bash
  HERALD_DOCS_SITE_REQUIRED=1 pixi run --frozen -e pyforge-herald pyforge-herald-live-test
  ```

</intent-contract>

## Result (2026-11-26)

- `test_agent_surface_and_changes.py`: each of the five builds is its own module fixture (`full_build`, `one_missing_build`, `no_inputs_build`, `status_off_build`, `no_merges_build`) over one `_CASES` table, with the same inputs and status flag as before.
- `test_ac7` becomes two tests. One covers the full build: every surface, and the runs page. The other covers the status-off build: every surface, no runs page, no `status/`.
- `test_ac6` becomes two tests. One covers one-missing: a single absent input on the runs page, none on the changes page. The other covers no inputs: each page names what is absent, and the feed is empty. Every assertion is kept.
- `test_one_generator.py`: `test_109_3` becomes a flag-on test (`built_with_marketplace`) and a flag-off test (`built`), with the same assertions. `test_43_5` makes its first build itself, as `built` is made, then the second.
- The heaviest herald xdist group falls from 52.9 s to 19.5 s (`test_site_shell.py`'s shell). The agent-surface groups are now at most 8.6 s, and `built`'s is 17.5 s. pytest-split's estimates for the three live shards are 85.1, 85.3 and 84.6 s, so on four workers no group outlasts a shard's share.
- Herald's live half passes with `HERALD_DOCS_SITE_REQUIRED=1`: 825 passed, none skipped (822 before; the three splits add three). On four workers it took 71.9 s, against 86.8 s before the split. The package half passes (1,560 passed).
