---
title: '128.1: The platform suite and its checks run on a macOS laptop'
type: 'fix'
created: '2026-11-21'
status: 'done'
story: 128-1-the-platform-suite-and-its-checks-run-on-a-macos-laptop
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # tests, a gate's own module and the scripts a gate runs; a gated gate is a silent green (roster list)
surface:
  - 'pixi.toml'
  - 'pixi.lock'
  - 'environment.yaml'
  - 'docs/reference/environments.md'
  - 'src/shared/packages/django-pyforge/**'
  - 'src/platform/tests/**'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The `platform-ci-test` environment solves for linux-64 only, so a macOS laptop cannot run the platform suite, its mypy step or the rest of Platform CI's `checks` job before a push.

**Approach:** The environment also solves for macOS, carries the `host-tools` git, the station CLI's tracked-recipe lookup finds the host environment's git first, and the promotion tests read the scanned environment's Python version.

Ledger key: `128-1-the-platform-suite-and-its-checks-run-on-a-macos-laptop`.

### Living CAP citations

- spec-pyforge-steward CAP-175 and CAP-5 (realized, no text change); FR-49 ← CAP-175; no AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Write `pixi.lock` only with the pixi version the workspace pins (0.80.0).

**Never:**
- Never move another environment's pin, let the station CLI inherit a caller's `PATH`, or weaken an assertion that holds on Linux.

## Acceptance Criteria

**Given** the `platform-ci-test` environment solves for linux-64 only, so a macOS laptop cannot run the platform suite, its mypy step or the rest of Platform CI's `checks` job before a push
**When** the environment also solves for macOS, carries the `host-tools` git, the station CLI's tracked-recipe lookup finds the host environment's git first, and the promotion tests read the scanned environment's Python version
**Then** Platform CI's `checks` job (system checks, ruff, ruff format, mypy, the policy suite, the sqlmigrate extraction) and its suite run green on macOS from `-e platform-ci-test`, apart from the herald browser check where no Playwright Chromium is installed; no other environment's pins move
**And** Linux CI stays green

- **AC1 — Platform CI's checks pass on macOS.** Expected: exit 0 for each, from `src/platform/` in `-e platform-ci-test` with PostgreSQL 17 and Redis reachable.

  ```bash
  python manage.py check && ruff check . && ruff format --check . && mypy platformapp config tests && python -m pytest tests/policy && python -m db.sqlmigrate_extraction
  ```

- **AC2 — The suite passes on macOS** apart from the herald browser check when no Playwright Chromium is installed.

  ```bash
  python -m pytest -n 4 --dist loadgroup
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-175 and CAP-5 (realized, no text change); FR-49 ← CAP-175; no AD moves.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the second 2026-11-21 entry; operator, 2026-11-21: "why - The platform suite and its mypy step, which can't run on this Mac, cant we fix this".
- Epic: Epic 128, minted with this story.
- Ledger key: `128-1-the-platform-suite-and-its-checks-run-on-a-macos-laptop` (`done`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."128"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-21: minted from the station Dream's second 2026-11-21 entry and the operator, 2026-11-21: "why - The platform suite and its mypy step, which can't run on this Mac, cant we fix this".
- 2026-11-21 (later): done on branch `corridor-platform-host-2026-11-21` (PR #2375). On macOS against PostgreSQL 17.11 and Redis: every `checks` step exits 0, including mypy; the suite reads 1,496 passed and 1 failed, the herald browser check, for want of a Playwright Chromium. Before this story the same tests could not run at all here, and on `main` nine of them failed.
