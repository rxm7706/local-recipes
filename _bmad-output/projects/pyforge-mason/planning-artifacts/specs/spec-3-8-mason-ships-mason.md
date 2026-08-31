---
title: 'Mason ships Mason'
type: 'feature'
created: '2026-08-14'
status: 'done'
baseline_revision: 'dd984f4434bd4543f649328e37b43d13c17b26b3'
final_revision: 'dd94e716fccd9e4f3e1b61c47809c1b95798ce3f'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/src/shared/packages/pyforge-mason/src/pyforge/mason/package.py'
  - '{project-root}/src/shared/packages/pyforge-mason/tests/integration/test_package_build.py'
warnings: []
---

<intent-contract>

## Intent

**Problem:** FR-24/SM-1 requires proving Mason can ship itself. The build half is already proven for
real (Story 3.2's `test_package_build_self_hosting_produces_real_versioned_artifacts`, confirmed
green 2026-08-14). No test exercises the real, non-mocked `ship()` dry-run path against Mason's own
project -- every existing `ship()`/`ship_pypi` test mocks the build/upload engines.

**Approach:** Add one `slow`-marked real integration test (mirrors Story 3.2's
`test_package_build.py` precedent) running `package.ship(...)` for real, `confirm=False`, against
`src/shared/packages/pyforge-mason/` itself, proving the dry-run plan correctly names real wheel/sdist
artifacts for both the `pypi-test` rehearsal and `pypi` targets. The real, credentialed publish
(`--yes`, real TestPyPI-then-PyPI upload) is an operator action outside this run's authority --
**disclosed, user-directed scope boundary (2026-08-14): the operator chose "prove the mechanism;
defer the live publish"** over authorizing a real, irreversible publish of `pyforge-mason` (currently
`v0.1.0`) with no credentials available in this environment anyway.

## Boundaries & Constraints

**Always:**
- New file `tests/integration/test_package_ship.py`, `@pytest.mark.slow` (needs real
  `pyproject-build`/`pixi` on `PATH`; mirrors `test_package_build.py`'s `PACKAGE_ROOT` derivation:
  `Path(pyforge.mason.__file__).resolve().parent.parent.parent.parent`, never a path hardcoded
  relative to the test file).
- Calls `package.ship("pypi-test,pypi", confirm=False, environ={}, target="library",
  recipe_path=None, cfe_root_arg=None, cfe_python_arg=None, cfe_timeout_arg=None,
  start_directory=PACKAGE_ROOT)` for real -- no mocking of `build`, `pep517`, or `pixi`.
- Asserts: a 2-tuple of `NOT_ATTEMPTED` results in input order (`pypi-test` then `pypi` -- no
  reordering, matches `parse_ship_targets`'s documented rule); the `pypi` message contains
  "irreversible", the `pypi-test` message does not; both messages name real, existing wheel/sdist
  paths (`_describe_artifact`'s `repr(path)` branch, not its `"no {label} was built"` placeholder).
- Zero credentials needed (the dry-run path never checks `TWINE_USERNAME`/`TWINE_PASSWORD` -- that
  check lives inside `ship_pypi`, reached only when `confirm=True`), zero network calls, zero
  uploads -- entirely safe and reversible, matching `test_package_build.py`'s own risk profile.

**Block If:** none -- this is exactly the scope the operator selected (2026-08-14 AskUserQuestion:
"Scope to mechanism-proof only"). No unattended decision point remains.

**Never:**
- No real credentialed publish (`confirm=True`/`--yes` against real TestPyPI/PyPI) is executed by
  this story. Explicit, disclosed scope boundary (operator direction, 2026-08-14), consistent with
  Story 3.9's own prior disclosure ("Story 3.8 ... is out of scope [for 3.9] -- this story only
  builds the mechanism ... not the act of running it for a real release"). SM-1's literal "published"
  outcome is NOT claimed achieved by this spec.
- No change to `package.py`, `cli.py`, `models.py`, or any engine -- the entire ship mechanism
  (Stories 3.1-3.7, 3.9) is already complete, tested, and CLI-wired; this story adds test coverage
  only.
- No `pyproject.toml` version bump, no `TWINE_*`/PyPI token handling, no `.pypirc`, no CI release
  job -- release timing and versioning are the operator's own decision, out of this spec's remit.
- No re-proof of FR-24's build half -- Story 3.2's own real self-hosting build test already covers it
  (confirmed green, re-run 2026-08-14); duplicating it here is redundant coverage.
- No new unit-level "credential missing" coverage -- `tests/unit/test_package.py` already covers
  `ship_pypi`'s credential-check-before-build ordering and `ship()`'s per-target `MasonError`-to-
  `FAILED` conversion exhaustively with mocked engines; a "real project path, mocked build" variant
  would add no new proof.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Real self-hosting dry-run, `pypi-test` + `pypi` | `ship("pypi-test,pypi", confirm=False, environ={}, ..., start_directory=<real pyforge-mason root>)` | both `NOT_ATTEMPTED`, real order preserved; `pypi` message states irreversibility, `pypi-test` does not; both name real wheel/sdist paths | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-mason/tests/integration/test_package_ship.py` -- NEW. Real,
  non-mocked proof of the `ship()` dry-run plan against `src/shared/packages/pyforge-mason/` itself
  (the `ship` counterpart to `test_package_build.py`'s existing `build` proof).

## Tasks & Acceptance

**Execution:**
- [x] `tests/integration/test_package_ship.py` -- new, `@pytest.mark.slow`; derive `PACKAGE_ROOT` via
  the same technique as `test_package_build.py`; call `package.ship("pypi-test,pypi", confirm=False,
  environ={}, target="library", recipe_path=None, cfe_root_arg=None, cfe_python_arg=None,
  cfe_timeout_arg=None, start_directory=PACKAGE_ROOT)`; assert the returned tuple's length, order,
  states, and message content per the Always boundary and I/O matrix row.

**Acceptance Criteria:**
- Given `src/shared/packages/pyforge-mason/`, when `mason package build` runs (Story 3.2's own
  already-green real self-hosting test), then the produced `.conda`, wheel, and sdist match the
  repository's existing hand-run `pyforge-mason-build` triad -- SM-1's build half, already satisfied,
  re-verified 2026-08-14.
- Given the same project, when `mason package ship --to pypi-test,pypi` runs as a real (non-mocked)
  dry-run, then the printed plan correctly names both targets' real wheel/sdist artifacts, and only
  the `pypi` target's message states the upload is irreversible.
- Given this story's disclosed scope boundary, when SM-1's literal "Mason publishes itself" outcome
  is checked, then it is NOT claimed achieved here -- the ship mechanism is proven real and correct
  end-to-end short of the credentialed upload; the actual publish is a separately-tracked operator
  action (see Design Notes runbook).

## Spec Change Log

## Review Triage Log

### 2026-08-14 — Review pass 1
- intent_gap: 0
- bad_spec: 0
- patch: 2: (medium 1, low 1)
- defer: 1: (low 1)
- reject: 7: (low 7)
- addressed_findings:
  - `[medium]` `[patch]` `ship()`'s dry-run branch builds both engines unconditionally (neither
    target is `conda-forge`), but `plan_ship`'s PYPI/PYPI_TEST messages never reference `conda_path`
    -- a real `pixi build` regression reached via `ship()` was invisible to every assertion. Raised
    independently by both Blind Hunter and Edge Case Hunter. Fixed: added `dist-conda/*.conda`
    directory + glob assertions mirroring the existing wheel/sdist pattern.
  - `[low]` `[patch]` the docstring did not disclaim that requesting `pypi-test,pypi` evokes but does
    not exercise the FR-24/FR-50/AD-26 rehearsal gate (that logic lives only in `confirm=True`, never
    reached by a dry run). Raised by Blind Hunter. Fixed: added a docstring paragraph clarifying the
    gate is out of this test's reach and is covered by existing mocked unit coverage instead.
- **Deferred** (tracked station `pyforge-mason`, base id `DW-3-8`; full entry in `deferred-work.md`):
  - `[low]` `[defer]` **`DW-3-8-1`** -- root `pixi.toml`'s `pyforge-mason-test-slow` task description
    text is stale ("collects zero tests until Story 5.3..."), already inaccurate since Story 3.2's
    slow test landed and now doubly so with this story's second slow test. Raised by Blind Hunter.
    Pre-existing drift, not introduced by this story; a one-line `pixi.toml` fix outside this story's
    disclosed one-file scope.
- **Rejected** (matches established precedent, spec-directed, speculative, or already addressed by a
  stronger existing assertion):
  - `[low]` `[reject]` the spec's Design Notes runbook (the operator's path to completing SM-1 for
    real) lives only in the gitignored `implementation-artifacts/` tree, not yet promoted to tracked
    `planning-artifacts/specs/`. Matches this repo's own established convention that story-spec
    promotion happens AFTER merge, not during dev -- not a defect in this diff.
  - `[low]` `[reject]` the final `dist/` glob checks alone don't prove *this* invocation built
    anything (a stale artifact from an earlier run could satisfy them). Verified: the stronger
    message-content assertions (`"no wheel/sdist was built" not in message`) are read directly from
    THIS call's own freshly-returned `build_result` via `plan_ship`, not from a directory listing --
    they are dispositive independent of staleness; the glob checks are redundant confirmation, not
    the load-bearing proof.
  - `[low]` `[reject]` no isolation guards `dist/`/`dist-conda/` against a hypothetical future
    parallel test run (`pytest-xdist` is a listed dependency). Speculative -- the slow suite is not
    run with parallelism today, and the identical exposure already exists, unflagged, in the accepted
    `test_package_build.py` precedent; Simplicity First, not designing for a hypothetical.
  - `[low]` `[reject]` "zero network calls" (inherited from the spec) is pedantically imprecise since
    real `pyproject-build`/`pixi build` subprocesses aren't guaranteed network-isolated. Verified: the
    claim is correctly scoped to `ship()`/`plan_ship()`'s own Python, as the finding itself
    acknowledges; no functional consequence.
  - `[low]` `[reject]` failure diagnostics are weaker than `test_package_build.py`'s own direct
    `pep517_returncode`/`pixi_returncode` assertions, since `ship()` never exposes its internal
    `PackageBuildResult`. Matches this story's own explicit, disclosed Never boundary (no `package.py`
    change); duplicating a full `build()` call independently to recover those fields would be
    wasteful and blur what this test is proving.
  - `[low]` `[reject]` no accounting for `.whl`/`.tar.gz` accumulation across repeated local runs
    (version-suffix drift). Inapplicable to `pyforge-mason` itself -- its version is static
    (`hatchling`, no VCS-derived dynamic versioning), the same reasoning already recorded in
    `DW-3-9-1`.
  - `[low]` `[reject]` the scope caveat (mechanism proven, real publish deferred) isn't fully
    self-contained without the tracked spec. Verified: the test's own docstring already states this
    explicitly ("short of the real, credentialed, irreversible publish, which is a separately-tracked
    operator action") -- already addressed in the diff itself, redundant with the finding above.

## Design Notes

**Operator runbook to complete SM-1 for real** (not run by this spec): from
`src/shared/packages/pyforge-mason/`, `TWINE_USERNAME=__token__ TWINE_PASSWORD=<pypi-token> mason
package ship --to pypi-test,pypi --yes`. The rehearsal gate (Story 3.9, FR-24/FR-50) guarantees
`pypi-test` reaches `terminal` before `pypi` is attempted for real. Publishing `pyforge-mason`
(currently `v0.1.0`) to the public PyPI index is irreversible; this environment has no
`TWINE_USERNAME`/`TWINE_PASSWORD` set, and the operator explicitly deferred authorizing the live
publish during this run (2026-08-14).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Summary:** Story 3.8's ship mechanism was already 100% complete (Epic 3's other 8 stories, all
`done`). This run's worktree branch was stale -- it forked before Stories 3.6/3.7/3.9 were recovered
and hand-landed onto `origin/main` (PR #483) -- so step 1 fast-forwarded it (lossless, zero unique
commits) before anything else. Investigation then found AC1's literal outcome (real, credentialed
PyPI publish) requires an irreversible external action this sandbox has no credentials for and
should not perform unattended; the operator was asked and chose "prove the mechanism, defer the live
publish" (2026-08-14). The spec was scoped accordingly: one new real, non-mocked integration test
proving `mason package ship`'s dry-run plan against `src/shared/packages/pyforge-mason/` itself is
correct, complementing Story 3.2's already-green real build-parity test.

**Files changed:**
- `src/shared/packages/pyforge-mason/tests/integration/test_package_ship.py` -- NEW. Real,
  `@pytest.mark.slow` proof that `package.ship("pypi-test,pypi", confirm=False, ...)` against the
  real `pyforge-mason` project produces a correct dry-run plan naming real wheel/sdist/conda
  artifacts, with the irreversibility claim exclusive to the `pypi` target.

**Review findings:** 2 patched (1 medium: real `.conda`/`pixi build` output was unverified,
independently raised by both reviewers; 1 low: docstring didn't disclaim the rehearsal gate is
untested here), 1 deferred (`DW-3-8-1`, pre-existing stale `pixi.toml` task description), 7 rejected
(established precedent / speculative / already covered by a stronger existing assertion). Full
detail in `## Review Triage Log` above.

**Verification performed:** `pixi run -e pyforge-mason pyforge-mason-test-slow` (2 passed, both
self-hosting tests) and `pixi run --frozen -e pyforge-mason pyforge-mason-test` (1385 passed, 0
regressions), both re-run independently after the patch pass.

**Residual risk:** SM-1's literal "Mason ships Mason" outcome (real PyPI publish) is NOT achieved by
this run -- explicit, disclosed, operator-approved scope boundary. The operator runbook to complete
it for real lives in this spec's own Design Notes section and needs promotion to tracked
`planning-artifacts/specs/` after merge, per this repo's standing convention.
