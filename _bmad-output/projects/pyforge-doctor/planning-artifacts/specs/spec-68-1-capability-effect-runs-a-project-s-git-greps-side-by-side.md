---
title: '68.1: Capability-effect runs a project''s git greps side by side'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 68-1-capability-effect-runs-a-project-s-git-greps-side-by-side
spec: spec-pyforge-doctor
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/capability_effect.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_capability_effect_caller_reach.py'
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - docs/dreams/pyforge-doctor.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The `capability-effect` detector took 15.6 s alone and 76.7 s inside `detectors-ci`. Its live test, `test_live_fleet_proves_capability_effect_no_caller_finding`, took 22.7 s here and 17.5 s on CI, and was doctor's longest live test. 14 of the detector's 15.6 s are 45 `git grep` subprocesses, one per symbol named on a cited CAP surface, each over the whole tree, run in turn.

**Approach:** `_prefetch_symbol_greps` runs the greps of a project's symbols not yet in the cache side by side (up to 8 at once). Each runs exactly as `_git_grep_symbol_lines` runs it, into a cache of its own, and the results then fill the shared cache. Every later lookup reads the same hits it read before.

Ledger key: `68-1-capability-effect-runs-a-project-s-git-greps-side-by-side`.

### Living CAP citations

- spec-pyforge-steward:CAP-175 (the preflight and a PR's CI answer within a measured budget; realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- The detector's findings stay line for line the same, and each grep keeps its arguments and its exit-code handling.

**Never:**
- Never share a cache between threads while they write it.

## Acceptance Criteria

**Given** the fleet
**When** the detector runs
**Then** its findings equal the serial version's, in less time

- **AC1 — The caller-reach tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-doctor python -m pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_capability_effect_caller_reach.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_capability_effect_caller_reach.py -q
  ```

</intent-contract>

## Result (2026-11-27)

- The detector takes 6.8 s alone, from 15.6 s, and prints the same 901 finding lines (`diff` of the two outputs is empty).
- `test_live_fleet_proves_capability_effect_no_caller_finding` takes 5.77 s, from 22.7 s.
- `test_prefetched_greps_fill_the_cache_as_serial_lookups_would` holds that the prefetch greps each uncached symbol once, keeps a failed grep's `None`, leaves a cached symbol alone, and fills the cache as serial lookups would.
- AC1: 33 passed.
