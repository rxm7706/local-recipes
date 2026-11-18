---
title: '125.1: Steward''s suite and the preflight module run on a macOS laptop'
type: 'fix'
created: '2026-11-17'
status: 'done'
story: 125-1-steward-s-suite-and-the-preflight-module-run-on-a-macos-laptop
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # tests, a gate's own module and the scripts a gate runs; a gated gate is a silent green (roster list)
surface:
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py'
  - 'src/shared/packages/pyforge-steward/tests/**'
  - 'scripts/platform-ci-local.sh'
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

**Problem:** `mypy` reds both environments on `os.sched_getaffinity`; ten workspace tests need a non-UTF-8 name APFS refuses or git's trampoline panics on; four `test_pages_release.py` tests run a workflow snippet that calls GNU `find -printf`; six `platform-ci-local` tests need `flock`, which macOS does not ship.

**Approach:** The preflight module reads the core count without a Linux-only attribute, each test that needs a host capability probes for it, and the lock in `scripts/platform-ci-local.sh` works where `flock` is absent or the tests say the host lacks it.

Ledger key: `125-1-steward-s-suite-and-the-preflight-module-run-on-a-macos-laptop`.

### Living CAP citations

- **`spec-pyforge-steward` CAP-175** — the preflight and a PR's CI answer within a measured budget; this story realizes "answers" on the documented laptop platform, with no capability text change.

## Boundaries & Constraints

**Always:**
- Guard by probing the capability a test needs; name the missing capability in the reason.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never skip by platform name, weaken an assertion that holds on Linux, or change `pixi.toml` / `pixi.lock`.

## Acceptance Criteria

**Given** `mypy` reds both environments on `os.sched_getaffinity`; ten workspace tests need a non-UTF-8 name APFS refuses or git's trampoline panics on; four `test_pages_release.py` tests run a workflow snippet that calls GNU `find -printf`; six `platform-ci-local` tests need `flock`, which macOS does not ship
**When** the preflight module reads the core count without a Linux-only attribute, each test that needs a host capability probes for it, and the lock in `scripts/platform-ci-local.sh` works where `flock` is absent or the tests say the host lacks it
**Then** `pyforge-steward-test`, `pyforge-steward-live-test` and both `mypy` lanes exit 0 on macOS and are unchanged on Linux; no test is skipped by platform name
**And** every guard is a capability probe with a reason that names the missing capability

- **AC1 — The lanes this story names pass on the laptop.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-test && pixi run --frozen -e pyforge-steward pyforge-steward-live-test && pixi run --frozen -e pyforge-guild mypy
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-175 (realizes: the preflight answers; no text change); FR-49 ← CAP-175; no AD moves.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-11-17 (the laptop preflight) entry.
- Epic: Epic 125, minted with this story.
- Ledger key: `125-1-steward-s-suite-and-the-preflight-module-run-on-a-macos-laptop` (`backlog`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."125"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-17: minted from the station Dream's 2026-11-17 entry (the laptop preflight) and the operator's ruling of the same date.
