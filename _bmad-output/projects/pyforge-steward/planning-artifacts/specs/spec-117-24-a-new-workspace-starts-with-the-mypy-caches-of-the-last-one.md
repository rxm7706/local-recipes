---
title: '117.24: A new workspace starts with the mypy caches of the last one'
type: 'chore'
created: '2026-11-26'
status: 'done'
story: 117-24-a-new-workspace-starts-with-the-mypy-caches-of-the-last-one
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py'
  - 'src/shared/packages/pyforge-steward/tests/unit/test_workspace_mypy_caches.py'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
  - scripts/lint_types.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** A worktree made by `workspace start` has no mypy cache. Its first preflight's mypy lanes took 48.8 s (`pyforge-foundry-full`) and 30.4 s (`pyforge-guild`), against 3.5 to 4.5 s warm: the 40 s between the two passes of a steward touched run. `scripts/lint_types.py` keeps one cache per package per environment, `src/shared/packages/<package>/.mypy_cache/<environment>/`. The primary checkout, where `start` runs and no lane runs, holds none of those, so `start` has nothing to copy from it today.

**Approach:** `workspace clean`, before it removes a worktree, copies that worktree's per-environment mypy caches into the checkout it runs from, replacing the copy there. `workspace start`, after `git worktree add`, copies the checkout's caches into the new worktree. mypy checks each cached module against its source's hash when the path or mtime differ, so a copied entry is reused only where the source is the same. A cache is only ever copied: two worktrees never share one directory.

Ledger key: `117-24-a-new-workspace-starts-with-the-mypy-caches-of-the-last-one`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 and CAP-159 (the preflight answers within its budget; realized, no text change).
- spec-pyforge-steward CAP-104 (`workspace start`) and CAP-107 (`workspace clean`; no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Copy only `src/shared/packages/*/.mypy_cache/<environment>/` directories: the caches `scripts/lint_types.py` writes.
- A failed copy is reported and never fails `start` or `clean`.
- `clean` copies before it removes or archives the worktree, and only from a worktree it is about to remove.

**Never:**
- Never point two worktrees at one cache directory (mypy's cache is not safe for concurrent writers).
- Never copy into a worktree `start` did not just create.

## Acceptance Criteria

**Given** a checkout whose packages hold per-environment mypy caches
**When** `workspace start` creates a worktree
**Then** the new worktree holds a copy of each, and mypy in the new worktree reuses them

- **AC1 — The unit tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-test
  ```

- **AC2 — A worktree started after the change runs its mypy lane warm.** Expected: the lane takes seconds, not tens of seconds.

  ```bash
  pixi run --frozen -e pyforge-guild python scripts/lint_types.py mypy
  ```

</intent-contract>

## Result (2026-11-26)

- `workspace.py` gains `mypy_cache_dirs` (each `src/shared/packages/<package>/.mypy_cache/<environment>/` holding a Python-version directory; the version directories of mypy's default layout are left alone) and `copy_mypy_caches` (each cache copied to a staging name beside its target and renamed into place; a package the target lacks is skipped; a failure is returned, never raised). `start_workspace` copies the checkout's caches into the new worktree after recording it. `clean` copies a worktree's caches into the checkout before `git worktree remove`, on both the archive path and the `--delete` path. A failed copy is printed to stderr and the verb goes on.
- The packages root comes from `root_layout.STATION_PACKAGES`, as `test_portability.py` requires, and `oracle-map.md` names the new test module under CAP-104..CAP-108.
- AC2, measured in a fresh worktree on this machine: the two mypy lanes took 27.8 s (`pyforge-guild`) and 47.3 s (`pyforge-foundry-full`) cold. With the caches removed and 20 copied from another worktree at a nearby commit (0.5 s), they took 3.4 and 4.2 s; warm, 2.3 and 2.8 s. In a scratch clone seeded the same way, the first touched preflight of a herald-only change ran its mypy lanes in 4.6 and 3.6 s.
- The primary checkout holds no per-environment cache until the first `workspace clean` after this lands, so the first `start` after landing still begins cold; every later one begins warm.
- AC1: `pyforge-steward-test` and `pyforge-steward-live-test` exit 0.
