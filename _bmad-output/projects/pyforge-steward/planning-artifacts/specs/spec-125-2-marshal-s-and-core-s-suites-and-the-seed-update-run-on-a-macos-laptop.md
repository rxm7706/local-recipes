---
title: '125.2: Marshal''s and core''s suites and the seed update run on a macOS laptop'
type: 'fix'
created: '2026-11-17'
status: 'ready-for-dev'
story: 125-2-marshal-s-and-core-s-suites-and-the-seed-update-run-on-a-macos-laptop
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # tests, a gate's own module and the scripts a gate runs; a gated gate is a silent green (roster list)
surface:
  - 'src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/**'
  - 'src/shared/packages/pyforge-marshal/tests/**'
  - 'src/shared/packages/pyforge-core/src/pyforge/core/process.py'
  - 'src/shared/packages/pyforge-core/tests/**'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
  - docs/how-to/run-and-read-pr-preflight.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `marshal seed update` fails with a path that is not in the subpath of its resolved twin when the temporary directory is a symlink; core's `process_start_time` reads `/proc` only, so it returns `None` on macOS and a marshal liveness test fails; one marshal test expects a commit with no identity to fail, which macOS git does not do; one marshal test's `git init` fails.

**Approach:** The seed engine compares resolved paths, core answers a process's start time on macOS as well, and the two tests state what they need of git.

Ledger key: `125-2-marshal-s-and-core-s-suites-and-the-seed-update-run-on-a-macos-laptop`.

### Living CAP citations

- **`spec-pyforge-steward` CAP-175** — the preflight and a PR's CI answer within a measured budget; this story realizes "answers" on the documented laptop platform, with no capability text change.

## Boundaries & Constraints

**Always:**
- Guard by probing the capability a test needs; name the missing capability in the reason.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never skip by platform name, weaken an assertion that holds on Linux, or change `pixi.toml` / `pixi.lock`.

## Acceptance Criteria

**Given** `marshal seed update` fails with a path that is not in the subpath of its resolved twin when the temporary directory is a symlink; core's `process_start_time` reads `/proc` only, so it returns `None` on macOS and a marshal liveness test fails; one marshal test expects a commit with no identity to fail, which macOS git does not do; one marshal test's `git init` fails
**When** the seed engine compares resolved paths, core answers a process's start time on macOS as well, and the two tests state what they need of git
**Then** `pyforge-marshal-test`, `pyforge-marshal-live-test`, `pyforge-core-package-test` and `pyforge-core-live-test` exit 0 on macOS and are unchanged on Linux; `pyforge.core` stays mypy strict
**And** every guard is a capability probe with a reason that names the missing capability

- **AC1 — The lanes this story names pass on the laptop.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-marshal pyforge-marshal-test && pixi run --frozen -e pyforge-core pyforge-core-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-175 (realizes: the preflight answers; no text change); FR-49 ← CAP-175; no AD moves.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-11-17 (the laptop preflight) entry.
- Epic: Epic 125, minted with this story.
- Ledger key: `125-2-marshal-s-and-core-s-suites-and-the-seed-update-run-on-a-macos-laptop` (`backlog`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."125"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-17: minted from the station Dream's 2026-11-17 entry (the laptop preflight) and the operator's ruling of the same date.
