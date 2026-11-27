---
title: '117.29: Lint and types restores mypy caches from an older lock'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 117-29-lint-and-types-restores-mypy-caches-from-an-older-lock
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - '.github/workflows/lint-types.yml'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - scripts/lint_types.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Lint and types restores per-package mypy caches with a key and one restore key that both carry `pixi.lock`'s hash. A PR that moves the lock therefore finds no cache and runs mypy cold: 58 s for `pyforge-foundry-full`. The workflow took 157 to 178 s on PRs #2415 and #2417, against 77 to 102 s on runs that kept the lock.

**Approach:** A last restore key, `mypy-<os>-`, takes main's newest cache whatever its lock. mypy re-checks every cached module against its source's hash and drops an entry its version or options no longer match, so a cache from an older lock is safe to start from. Main still saves only under the full key.

Ledger key: `117-29-lint-and-types-restores-mypy-caches-from-an-older-lock`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- mypy's verdict is the same with or without a restored cache.

**Never:**
- Never save a cache from a pull request (Story 117.18).

## Acceptance Criteria

**Given** a PR that moves `pixi.lock`
**When** Lint and types runs
**Then** its cache step restores main's newest mypy cache, and mypy passes as it does cold

- **AC1 — The workflow names the fallback.** Expected: one line.

  ```bash
  grep -c '            mypy-${{ runner.os }}-$' .github/workflows/lint-types.yml
  ```

- **AC2 — On the next lock-moving PR, the restore step reports a hit on a restore key.**

</intent-contract>

## Result (2026-11-27)

- The restore step's keys are now the full key, the same-lock prefix, and `mypy-${{ runner.os }}-`. AC1: one line.
- AC2 is read from the next PR that moves the lock; this PR leaves the lock as it is.
