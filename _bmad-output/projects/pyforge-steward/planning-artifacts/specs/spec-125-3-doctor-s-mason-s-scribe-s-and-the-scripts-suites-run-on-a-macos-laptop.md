---
title: '125.3: Doctor''s, mason''s, scribe''s and the scripts suites run on a macOS laptop'
type: 'fix'
created: '2026-11-17'
status: 'ready-for-dev'
story: 125-3-doctor-s-mason-s-scribe-s-and-the-scripts-suites-run-on-a-macos-laptop
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # tests, a gate's own module and the scripts a gate runs; a gated gate is a silent green (roster list)
surface:
  - 'src/shared/packages/pyforge-doctor/tests/**'
  - 'src/shared/packages/pyforge-mason/tests/**'
  - 'src/shared/packages/pyforge-scribe/tests/**'
  - 'tests/scripts/test_scribe_pg.py'
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

**Problem:** One doctor test commits without setting an identity; two mason tests and one `test_scribe_pg.py` test compare `/tmp` with `/private/tmp`; a second `test_scribe_pg.py` test expects a setgid bit macOS does not keep; scribe's non-UTF-8 commit test dies in git's trampoline.

**Approach:** Each test sets the identity it commits under, compares resolved paths, and probes the host for what it needs.

Ledger key: `125-3-doctor-s-mason-s-scribe-s-and-the-scripts-suites-run-on-a-macos-laptop`.

### Living CAP citations

- **`spec-pyforge-steward` CAP-175** — the preflight and a PR's CI answer within a measured budget; this story realizes "answers" on the documented laptop platform, with no capability text change.

## Boundaries & Constraints

**Always:**
- Guard by probing the capability a test needs; name the missing capability in the reason.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never skip by platform name, weaken an assertion that holds on Linux, or change `pixi.toml` / `pixi.lock`.

## Acceptance Criteria

**Given** one doctor test commits without setting an identity; two mason tests and one `test_scribe_pg.py` test compare `/tmp` with `/private/tmp`; a second `test_scribe_pg.py` test expects a setgid bit macOS does not keep; scribe's non-UTF-8 commit test dies in git's trampoline
**When** each test sets the identity it commits under, compares resolved paths, and probes the host for what it needs
**Then** `pyforge-doctor-test`, `pyforge-doctor-live-test`, `pyforge-mason-test`, `pyforge-scribe-test` and `pyforge-doctor-scripts-test` exit 0 on macOS and are unchanged on Linux
**And** every guard is a capability probe with a reason that names the missing capability

- **AC1 — The lanes this story names pass on the laptop.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-doctor pyforge-doctor-live-test && pixi run --frozen -e pyforge-mason pyforge-mason-test && pixi run --frozen -e pyforge-scribe pyforge-scribe-test && pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-175 (realizes: the preflight answers; no text change); FR-49 ← CAP-175; no AD moves.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-11-17 (the laptop preflight) entry.
- Epic: Epic 125, minted with this story.
- Ledger key: `125-3-doctor-s-mason-s-scribe-s-and-the-scripts-suites-run-on-a-macos-laptop` (`backlog`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."125"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-17: minted from the station Dream's 2026-11-17 entry (the laptop preflight) and the operator's ruling of the same date.
