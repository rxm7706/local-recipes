---
title: 'Story 5.1: CFE-independence test'
type: 'feature'
created: '2026-08-15'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
difficulty: ''
baseline_revision: 'a723618553eeaeff2efa9512a621ad7f6351c486'
final_revision: '1ba459f414881a480066c91455f7ab32dac1adb9'
---

<intent-contract>

## Intent

**Problem:** Mason's central guarantee -- that `mason package` and `mason environment` work with
no conda-forge-expert (CFE) installation present, with exactly one named exception -- is stated in
FR-44/FR-5 and AD-6 but has no automated proof. Nothing today runs the full non-`recipe` verb
surface with the CFE root guaranteed unresolvable and checks it behaves normally.

**Approach:** Add `tests/meta/test_cfe_independence.py`: one behavioral (not AST-based) test suite
that drives every `mason package` and `mason environment` verb with the CFE root guaranteed
unresolvable (no `--cfe-root`, no `MASON_CFE_ROOT`, cwd with no `.claude/scripts/conda-forge-expert/`
marker upward), asserting each behaves normally, except the `conda-forge` ship target -- named in a
one-entry allow-list -- which must fail specifically with the FR-5 `CfeUnresolvedError`
(identifier `"cfe:unresolved"`), never merely "fail somehow."

## Boundaries & Constraints

**Always:**
- Cover the full non-CFE verb surface: `package.build()`, `package.ship()` exercised across
  `pypi`, `channel:<name>`, and `conda-forge` targets in the same multi-target invocation, plus
  `environment.lock()` and `environment.check()`.
- Force CFE unresolvable the same way `test_package.py::test_ship_conda_forge_raises_cfe_unresolved_when_root_is_not_found`
  and `test_recipe.py` already do: no `cfe_root_arg`, an `environ` mapping with no `MASON_CFE_ROOT`
  key, and a `start_directory` (a `tmp_path`, or `monkeypatch.chdir` to one) with no
  `.claude/scripts/conda-forge-expert/` marker anywhere upward. Do NOT use the `fake_cfe_root`
  fixture (`tests/conftest.py`) -- it provides a *present* fake root, the opposite of this test.
- Define the allow-list as one explicit named constant (e.g. a module-level frozenset/tuple
  containing only `"conda-forge"`) that the test iterates against. A blanket "except where CFE is
  needed" conditional is forbidden -- adding a second entry must require editing this file.
- Ship `conda-forge` with `confirm=True` (real-ship path) and a non-blank `recipe_path`
  (e.g. `str(tmp_path / "recipes" / "some-pkg")`) -- `ship_conda_forge` checks `recipe_path`
  presence BEFORE resolving the CFE root, so an empty/`None` `recipe_path` raises
  `ShipCondaForgeRecipeMissingError` instead, the wrong error for this test's purpose. The
  dry-run path (`confirm=False`) with only-`conda-forge` requested never calls `ship_conda_forge`
  at all (a placeholder build result short-circuits it) -- must not be used to drive this assertion.
- Assert the `conda-forge` target's `ShipTargetResult` has `state is ShipState.FAILED` and its
  `message` contains the `CfeUnresolvedError` identifier `"cfe:unresolved"` (from
  `str(CfeUnresolvedError())`) -- `ship()`'s `_ship_one` closure catches `CfeUnresolvedError` (a
  `MasonError`) into that result; it is never a raised exception at this layer.
- Mock/patch the engine layer (`pep517.build`, `pixi.build`, `twine.upload`, `pixi.upload`,
  `engines.condalock.lock`/`.check`) exactly as `tests/unit/test_package.py` /
  `tests/unit/test_environment.py` already do, so this test proves CFE-independence, not
  network/tooling availability (NFR-5 offline-safe).
- Include a test asserting `import pyforge.mason.package` and `import pyforge.mason.environment`
  succeed with no CFE marker reachable from cwd.
- Register in the default (non-`slow`) test task -- no real CFE or real subprocess involved.

**Block If:** none identified -- the scope, allow-list membership, and error identity are all
already fixed by FR-44/FR-5 and existing code; nothing here requires a human decision.

**Never:**
- Never use a real conda-forge-expert installation or `fake_cfe_root` fixture in this file.
- Never assert only "the conda-forge target failed" without checking it failed for the FR-5 reason
  specifically (that is the whole point of AC3).
- Never widen the allow-list to more than one entry, and never express it as a conditional instead
  of a named collection.
- Out of scope: `mason recipe` verbs (CFE-dependent by design, not covered by FR-44), the
  delegation-fidelity test (Story 5.3), the governance/commit-range test (Story 5.2).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `package build`, no CFE | `package.build(project_path)`, engines mocked, CFE unresolvable | Returns a normal `PackageBuildResult`; never touches CFE | No error expected |
| `package ship --to pypi,channel:acme,conda-forge`, no CFE | `package.ship(...)`, `confirm=True`, engines mocked, non-blank `recipe_path`, CFE unresolvable | Returns a 3-tuple: `pypi` and `channel:acme` results `TERMINAL`; `conda-forge` result `FAILED` | `conda-forge`'s `message` contains `"cfe:unresolved"`; the other two show no such failure |
| `environment lock`, no CFE | `environment.lock(manifests, output_path=...)`, condalock mocked, CFE unresolvable | Returns a normal `LockResult`; never touches CFE | No error expected |
| `environment check`, no CFE | `environment.check(manifests, lockfile_path=...)`, condalock mocked, CFE unresolvable | Returns a normal `CheckResult`; never touches CFE | No error expected |
| Module imports, no CFE | `import pyforge.mason.package`; `import pyforge.mason.environment` | Both succeed | No error expected |
| Allow-list shape | Static read of the allow-list constant in the test file | Exactly one entry, `"conda-forge"` | Test fails if the constant has 0 or >1 entries |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-mason/tests/meta/test_cfe_independence.py` -- NEW, this story's entire deliverable.
- `src/shared/packages/pyforge-mason/src/pyforge/mason/package.py` -- `build()` (L197), `ship()` (L827, multi-target dispatcher, catches `MasonError` per-target in `_ship_one`, L961), `ship_conda_forge()` (L719, raises `CfeUnresolvedError` when `resolve_cfe_root` finds no root -- AFTER its own `recipe_path`-blank check), `parse_ship_targets()` (L273, comma-separated `--to` syntax: `"pypi"`, `"pypi-test"`, `"conda-forge"`, `"channel:<name>"`).
- `src/shared/packages/pyforge-mason/src/pyforge/mason/environment.py` -- `lock()` (L102), `check()` (L150); neither has any CFE parameter at all.
- `src/shared/packages/pyforge-mason/src/pyforge/mason/errors.py` -- `CfeUnresolvedError` (`class CfeUnresolvedError(MasonError)`, ~L99): zero-arg constructor, `identifier = "cfe:unresolved"`, fixed message; `str(exc) == "cfe:unresolved: <fixed message>"`.
- `src/shared/packages/pyforge-mason/src/pyforge/mason/resolve.py` -- `resolve_cfe_root(explicit, environ, start_directory)`, the pure resolution chain this test forces to its not-found terminal state.
- `src/shared/packages/pyforge-mason/src/pyforge/mason/models.py` -- `ShipTargetResult(target, state, reference, message)`, `ShipState` (`NOT_ATTEMPTED`/`FAILED`/`PENDING`/`TERMINAL`), `ShipReceipt`, `LockResult`, `CheckResult`.
- `src/shared/packages/pyforge-mason/tests/unit/test_package.py` -- reference pattern: engine-mocking style (`patch("pyforge.mason.package.pep517.build", ...)` etc.), and `test_ship_conda_forge_raises_cfe_unresolved_when_root_is_not_found` (~L1144) for the exact "force CFE unresolvable" shape.
- `src/shared/packages/pyforge-mason/tests/unit/test_environment.py` -- reference pattern for mocking `engines.condalock`.
- `src/shared/packages/pyforge-mason/tests/meta/test_capability_tiers.py` -- sibling meta-test (AST-based, different technique) enforcing AD-6's "no module-level `cfe` import" invariant; read for house style (module docstring rationale, `PKG_ROOT` resolution pattern) even though this new test is behavioral, not AST-based.
- `src/shared/packages/pyforge-mason/tests/conftest.py` -- `fake_cfe_root` fixture exists here but must NOT be used by this test (it supplies a present root).
- `pixi.toml` (repo root, ~L211) -- `pyforge-mason-test` task (`pytest ... -m "not slow"`, the default loop this new file must run under un-marked).

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-mason/tests/meta/test_cfe_independence.py` -- create the test module with a module docstring explaining FR-44/FR-5's guarantee and why this is behavioral rather than AST-based -- establishes the file.
- [x] Same file -- define the one-entry allow-list constant plus a test asserting its shape (exactly one entry, `"conda-forge"`) -- makes AC2's review-gate structural, not just a comment.
- [x] Same file -- add a helper (fixture or local function) that builds a guaranteed-CFE-unresolvable `environ`/`start_directory` pair from `tmp_path`, without a `.claude/scripts/conda-forge-expert/` marker anywhere upward -- shared setup for every scenario below, avoids duplicating the "how" five times.
- [x] Same file -- test `package.build()` runs normally with CFE unresolvable, engines mocked -- covers AC1 for `package build`.
- [x] Same file -- test `package.ship("pypi,channel:acme,conda-forge", confirm=True, ...)` in one invocation: `pypi`/`channel:acme` succeed (`TERMINAL`), `conda-forge` fails with `state is FAILED` and `"cfe:unresolved"` in `message` -- covers AC1 (non-excepted targets), AC2 (allow-list use), AC3 (FR-5-specific failure).
- [x] Same file -- test `environment.lock()` and `environment.check()` run normally with CFE unresolvable, `engines.condalock` mocked -- covers AC1 for `environment`.
- [x] Same file -- test `import pyforge.mason.package` and `import pyforge.mason.environment` succeed with no CFE marker reachable -- covers AC4.
- [x] `pixi.toml` -- verify (no edit expected) that `pyforge-mason-test` already collects `tests/meta/` without a `slow` marker on the new file -- confirms the new tests run in the default loop.

**Acceptance Criteria:**
- Given `tests/meta/test_cfe_independence.py`, when it runs, then every `mason package` and every
  `mason environment` verb executes with the CFE root guaranteed unresolvable and each behaves
  normally, except the one allow-listed `conda-forge` ship target.
- Given the allow-list, when read, then it contains exactly one entry (`"conda-forge"`) and is not
  expressed as a conditional; a test in the file fails if a second entry is added without a
  corresponding code change to the test itself.
- Given the `conda-forge` ship target run without CFE, when it executes inside the same
  multi-target invocation as other targets, then the test asserts its `ShipTargetResult` is
  `FAILED` with `"cfe:unresolved"` in its message, and that every other target in that same
  invocation is `TERMINAL`.
- Given the same test file, when module imports are checked, then `pyforge.mason.package` and
  `pyforge.mason.environment` import successfully with no CFE on the filesystem.
- Given `pixi run -e local-recipes pyforge-mason-test` (or the pyforge-mason project's own default
  test task), when it runs, then the new file's tests are collected and pass without the `slow`
  marker.

## Spec Change Log

## Review Triage Log

### 2026-08-15 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 0, medium 1, low 3)
- defer: 0
- reject: 8: (high 0, medium 0, low 8)
- addressed_findings:
  - `[medium]` `[patch]` AC4's two "module imports successfully with no CFE reachable" tests were
    vacuous: `pyforge.mason.package`/`.environment` are already imported at this file's own top
    (module scope, collection time), so a bare `import` statement inside the test body was a
    `sys.modules` cache hit re-executing nothing -- the tests could never fail regardless of
    whether import genuinely depends on CFE (confirmed independently by both reviewers). Fixed by
    replacing the bare `import` with `importlib.reload(package)`/`importlib.reload(environment)`,
    which genuinely re-executes each module's top-level code while the `cfe_unresolvable` fixture
    has the process cwd `monkeypatch.chdir`'d to a marker-less `tmp_path` -- a real dynamic check.
  - `[low]` `[patch]` `test_environment_lock_...`/`test_environment_check_...` wrote real
    manifest/lockfile file content (`write_text(...)`) that was never read, since
    `engines.condalock.lock`/`.check` are fully mocked and `environment.py`'s own `lock()`/`check()`
    do no existence pre-validation (confirmed against `environment.py`'s own docstrings). Removed
    the unnecessary file writes; the tests now use bare path strings.
  - `[low]` `[patch]` The module docstring overclaimed that `environment.lock()`/`.check()`'s
    coverage "patches `resolve_cfe_root` ... and asserts it is never called" -- only the `build()`
    test does this; `environment.py` does not even import `resolve_cfe_root` (confirmed by reading
    the source), so that claim was flatly wrong for `lock()`/`check()`. The same paragraph also
    overclaimed exhaustive ship-target coverage ("every OTHER ship target") when `pypi-test` is not
    separately exercised. Corrected both claims in the module docstring; declined to add `pypi-test`
    coverage itself since it runs through the identical `ship_pypi()` call as `pypi` with no
    CFE-related branch of its own, so `pypi`'s coverage already establishes the same guarantee.
  - `[low]` `[reject]` "Circular allow-list test" (the structural test asserts a constant local to
    this file, nothing in `package.py` reads it) -- by design: FR-44/AC2 explicitly requires the
    allow-list and its one-entry guard to live in the test file itself as the review gate ("adding a
    second entry requires editing the test"), not to be enforced by production code.
  - `[low]` `[reject]` `proj.mkdir()` in the `build()` test called "unnecessary" -- matches
    `tests/unit/test_package.py`'s own established `proj = tmp_path / "proj"; proj.mkdir()`
    precedent verbatim; consistent with house style, not extraneous.
  - `[low]` `[reject]` `ship()`'s dry-run (`confirm=False`) path called an uncovered gap -- out of
    scope for this story: the dry-run path never calls `ship_conda_forge()` (a placeholder build
    result short-circuits it per `ship()`'s own docstring), so it never resolves CFE at all and
    would prove nothing about CFE-independence specifically.
  - `[low]` `[reject]` Hardcoded credential-shaped literals (`"acme-secret"`, `"pypi-secret"`)
    flagged as scanner-bait -- confirmed identical to `tests/unit/test_package.py`'s own established
    `_SHIP_ENVIRON`/`_SHIP_CHANNEL_ENVIRON` literals (`"pypi-secret"`, `"prefix-secret"`); matches
    house convention exactly.
  - `[low]` `[reject]` Verbose module docstring / high doc-to-code ratio, and FR/AD spec citations
    not independently cross-checked against a resolvable artifact -- both match this codebase's
    pervasive, established documentation style throughout `package.py`/`environment.py`/`errors.py`.
  - `[low]` `[reject]` Fixture's CFE-unresolvable self-check only runs once at fixture setup, not
    re-verified mid-test -- speculative: no current test in this file creates a CFE marker mid-test,
    so there is nothing for a re-check to catch today.

## Design Notes

The FR-5 error is reused, not new: `ship_conda_forge()` raises the same `CfeUnresolvedError` that
`cfe.py::ensure_cfe_root()` raises elsewhere -- there is no separate "ship-context" error class.
`ship()`'s `_ship_one` closure catches every `MasonError` subclass (including `CfeUnresolvedError`)
per-target, so `EXIT_CFE_UNAVAILABLE` never surfaces from a `ship()`-driven invocation even for a
lone `--to conda-forge` -- this is documented as the one surprising exit-code behavior in
`package.py`'s own `ship()` docstring. Consequently this test must inspect the returned
`ShipTargetResult` tuple, not use `pytest.raises`, for the `conda-forge` scenario. (A DIRECT call to
`ship_conda_forge()` alone, bypassing `ship()`, would raise `CfeUnresolvedError` -- that lower-level
behavior is already covered by `test_package.py` and is not this story's job to re-test; this
story's job is the verb-surface-level behavior a `mason package ship` invocation actually produces.)

## Verification

**Commands:**
- `pixi run -e pyforge-mason pyforge-mason-test` -- expected: the suite is green, including the new
  `tests/meta/test_cfe_independence.py` file, with zero tests skipped/xfailed in it.
- `pixi run -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/meta/test_cfe_independence.py -v`
  -- expected: every test in the new file passes.

## Auto Run Result

Status: done

**Summary:** Added `tests/meta/test_cfe_independence.py`, proving FR-44/FR-5: every `mason package`
(`build`, `ship` across `pypi`/`channel:<name>`/`conda-forge`) and `mason environment` (`lock`,
`check`) verb runs normally with the CFE root guaranteed unresolvable, except the one allow-listed
`conda-forge` ship target, which is asserted to fail specifically with `CfeUnresolvedError`
(`"cfe:unresolved"`) inside the same multi-target invocation where the other targets succeed. A
review pass found the AC4 "module imports with no CFE" tests were vacuous (cached-import no-op) and
fixed them with `importlib.reload()`; two smaller docstring/setup cleanups were also applied.

**Files changed:**
- `src/shared/packages/pyforge-mason/tests/meta/test_cfe_independence.py` -- new file, 7 tests: the
  allow-list shape guard, `package.build()`, the multi-target `package.ship()` scenario,
  `environment.lock()`/`.check()`, and the two (fixed) CFE-unresolvable import-reload tests.

**Review findings breakdown:** 12 findings from Blind Hunter + Edge Case Hunter (run in parallel,
no shared context), deduplicated. 4 patched (1 medium, 3 low) -- see Review Triage Log for detail.
8 rejected as noise (by-design allow-list shape, precedent-matching test setup, out-of-scope
dry-run coverage, precedent-matching credential literals, house-style documentation density,
speculative fixture re-check). 0 deferred, 0 intent gaps, 0 bad-spec loopbacks.

**Verification performed:** `pixi run -e pyforge-mason pyforge-mason-test` (full suite, run
independently three times across implementation/pre-review/post-patch) -- 1532 passed, 2 deselected
(pre-existing `slow`-marked tests, unrelated) every time. `ruff check` clean after one auto-fix
(import grouping). No manual inspection required beyond the review pass above.

**Residual risks:** None identified that block this story. `pypi-test`'s CFE-independence rests on
the "identical code path as `pypi`" argument (verified against source, not separately exercised) --
acceptable since `ship_pypi()` has no CFE-related branching regardless of `repository_url`. Story
5.2 (governance/commit-range test) and 5.3 (delegation-fidelity test) remain separate, unstarted
stories in this epic.
