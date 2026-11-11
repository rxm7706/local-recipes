---
title: "116.4: A package-half test that opens a repository file outside the package fails, wherever the package half runs"
type: 'feature'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a check that judges; nothing a user reaches at runtime (roster flag_exemptions; the exempt form of spec-110-38)
difficulty: medium
story: '116.4'
spec: pyforge-marshal
surface:
  - src/shared/packages/pyforge-marshal/tests/conftest.py
  - src/shared/packages/pyforge-marshal/tests/_support/tree_read_guard.py
  - src/shared/packages/pyforge-marshal/tests/meta/test_tree_read_guard.py
  - src/shared/packages/pyforge-marshal/tests/**/*.py
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - docs/reference/story-spec-flag-block.md
  - src/shared/packages/pyforge-marshal/tests/conftest.py
  - .github/workflows/pyforge-station-tests.yml
  - pixi.toml
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The oracle goal needs a check that runs. Steward's derivation is static and misses runtime reads: code under test that falls back to the checkout reads the repository and no static scan sees it.

**Approach:** Realizes spec-pyforge-marshal:CAP-305's guard clause. `tests/_support/tree_read_guard.py` installs one `sys.addaudithook` per process (xdist workers each load `tests/conftest.py`); the hook returns at once unless armed and the event is `open`, `os.listdir`, `os.scandir` or `glob.glob`. `tests/conftest.py` arms it in hookwrappers around each package-half test's setup, call and teardown (so module fixtures count) and fails the test naming each recorded path. The package directory is the guard file's `parents[2]`; the repository is the nearest ancestor of it holding `.git` (a file in a worktree), or none. Allowed under the repository: the package, `.pixi/`, `.steward/coverage/`, the directories of the installed `pyforge.core` and `pyforge.testing_kit` modules. A subprocess's reads (a test that runs `git -C <repo>`) are not seen: steward's static derivation stays the guard for those. A module the guard names is marked or fixed exactly as Stories 116.2 and 116.3 do. The off-tree copy run is one-time evidence recorded here, not a lane: an unsharded package-half run would exceed the 15-minute marshal-gate job, and running the shards from a copy would turn coverage.py's file keys absolute.

Ledger key: `116-4-a-package-half-test-that-opens-a-repository-file-outside-the-package-fails-wherever-the-package-half-runs`. Type / Effort / Deps: feature / M / S-116.3.

## Boundaries & Constraints

**Always:**
- A `live_tree` test is never armed; with no repository around the package the guard is inert.
- The guard runs inside the lanes that already run the package half (CI `marshal-test` shards, the pr-preflight marshal lane), at no extra suite run.

**Never:**
- No new lane and no new pixi task.
- Never skip or re-mark a test to quiet the guard.

## Acceptance Criteria

- **AC1 — The classifier and the hook: a read of `<repo>/scripts/x.py`, `<repo>/_bmad-output/...` or `<repo>/src/shared/packages/pyforge-doctor/...` is recorded; a read under the package, a tmp dir, `<repo>/.pixi/`, the installed pyforge-core or pyforge-testing-kit source, or outside the repository is not; a live_tree test is never armed; with no repository around the package the guard is inert.**

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/meta/test_tree_read_guard.py -q
  ```

  Expected: exit 0.

- **AC2 — The guard runs in the package half and the half passes with it.**

  ```bash
  pixi run --frozen -e pyforge-marshal pyforge-marshal-test
  ```

  Expected: exit 0, and the run's header line names the guard (`tree-read guard: armed`).

- **AC3 — The lanes that run it: CI job `marshal-test` and the pr-preflight marshal lane both run `pyforge-marshal-test`.**

  ```bash
  grep -c 'pixi run --frozen -e pyforge-marshal pyforge-marshal-test' .github/workflows/pyforge-station-tests.yml && grep -c 'task = "pyforge-marshal-test"' pixi.toml
  ```

  Expected: each prints 1 or more.

- **AC4 — One-time evidence, recorded in this spec: the package half run from a copy of the package outside the repository passes.**

  ```bash
  R=$PWD; D=$(mktemp -d) && cp -r src/shared/packages/pyforge-marshal/tests src/shared/packages/pyforge-marshal/pyproject.toml $D/ && (cd $D && pixi run --manifest-path $R/pixi.toml --frozen -e pyforge-marshal python -m pytest tests/unit tests/meta -q -p no:cacheprovider -m 'not slow and not live_tree')
  ```

  Expected: exit 0.

- **AC5 — Lint and types hold.**

  ```bash
  pixi run -e pyforge-guild lint-types
  ```

  Expected: exit 0.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal:CAP-305` (memlog 2026-11-10; rendered by Story 114.1). FR-247 (written by Story 114.1).

- Epic: Epic 116 (`_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `### Story 116.4: A package-half test that opens a repository file outside the package fails, wherever the package half runs`).
- Dream: `docs/dreams/pyforge-marshal.md`, 2026-11-10 — The Spec says what marshal is, and its roots come from one place.
- Rulings: `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda.

## Notes

- Shares the glob over marshal's tests with Stories 116.2 and 116.3, hence the dependency on Story 116.3.

## Spec Change Log

- 2026-11-10: minted at `backlog` by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10) and the memlog entries of `spec-pyforge-marshal` came first; `SPEC.md` is rendered by Story 114.1.
