---
title: 'The conda-forge ship target'
type: 'feature'
created: '2026-08-13'
status: 'done'
baseline_revision: '4219f1dea4d7f61ce8fa7c70c53053d4c44232d3'
final_revision: '1d3385d4a4d662276722ee31a557eb64edac91c3'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/src/shared/packages/pyforge-mason/src/pyforge/mason/recipe.py'
  - '{project-root}/src/shared/packages/pyforge-mason/src/pyforge/mason/doctor.py'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `package.py` has `ship_pypi`/`ship_channel` (Stories 3.4/3.5) but no `conda-forge`
target, and D-10's two shipping preconditions (CFE root resolved; recipe at
`<cfe-root>/recipes/<name>/`) are enforced nowhere and unreported by `mason doctor`.

**Approach:** Add `package.py::ship_conda_forge()`: validate D-10's two preconditions itself
(dedicated errors, one reused `CfeUnresolvedError`), then lazily call the already-built
`recipe.py::submit()` (Story 2.9) and return its `ShipTargetResult` unchanged (AD-11 — one owner,
no reimplementation). Extend `mason doctor` to report both preconditions.

## Boundaries & Constraints

**Always:**
- `ship_conda_forge` never builds anything — conda-forge ships the recipe SOURCE, not a `.conda`
  artifact (matches `plan_ship`'s own `CONDA_FORGE` message, package.py:298-300).
- Calls `recipe.submit(str(recipe_dir), confirm=True, prepare_only=False, cfe_root_arg=...,
  cfe_python_arg=..., cfe_timeout_arg=..., environ=..., start_directory=...)` and returns its
  `ShipTargetResult` verbatim — no second result object is constructed for its success/failure/
  pending paths (AD-11, `models.ShipTargetResult`'s own docstring: "wraps ITS `ShipTargetResult`").
  `submit()` already hardcodes `target="conda-forge"`.
- Recipe location check (D-10): given `recipe_dir = Path(recipe_path).expanduser().resolve()`, must
  equal `resolve_cfe_root(...).root.expanduser().resolve() / "recipes" / recipe_dir.name`. Both
  sides resolved before comparing — `resolve_cfe_root`'s flag/env steps return an un-resolved `Path`
  (resolve.py:124-129), while `recipe_dir` already is one.
- `resolve_cfe_root`/`STEP_NOT_FOUND` import at `package.py` module scope (mirrors `doctor.py`'s own
  precedent — `resolve.py` carries no `cfe` dependency). `recipe` (and therefore `cfe`, imported at
  `recipe.py` module scope) is imported lazily inside `ship_conda_forge`'s body only, never at
  `package.py` module scope (AD-6) — mirrors `doctor.py::build_report`'s lazy `cfe` import.
- Missing/unresolvable structural preconditions RAISE (mirror `ship_pypi`/`ship_channel`'s
  credential-check precedent — a structural precondition is raised, not returned as data): no
  recipe path -> `ShipCondaForgeRecipeMissingError`; CFE root unresolved -> `CfeUnresolvedError`
  (reused, not a new class — its message is already precondition-generic); wrong recipe location ->
  `ShipCondaForgeRecipeLocationError`. A `Path.resolve()` `OSError`/`ValueError` on either
  `recipe_path` or the resolved root returns `ShipTargetResult(FAILED, message=str(exc))` instead —
  mirrors `submit()`'s own established precedent for this exact resolve-failure mode.
- `mason doctor` gains `conda_forge_ship_ready: bool` and `conda_forge_ship_blockers: tuple[str,
  ...]` on `DoctorReport`, computed from the `resolved_root` `build_report` already has: root
  unresolved is one blocker; root resolved but `<root>/recipes` is not a directory is the other
  (doctor has no recipe argument, so precondition #2 is checked structurally, not per-recipe).
  `build_report` still never raises.

**Block If:** none — D-10/FR-23 fully specify both preconditions and the offer-not-generate
behavior; no unattended decision point remains.

**Never:**
- No idempotence/duplicate-PR check (fork search for `add-recipe-<name>`) — AD-10, Story 3.7's scope.
- No interactive prompt and no call to `recipe.new()` — "offers... does not generate silently" is
  satisfied by the raised error's message naming `mason recipe new`; any CLI-level interactive offer
  is Story 3.9's scope (this worktree's `recipe.py` does not even have `new()` yet — landed on `main`
  via PR #465, not yet merged into this loop-home branch — confirming this function must be
  reachable without it).
- No `--to`/`ship` CLI wiring — Story 3.9's scope.
- No `prepare_only` parameter on `ship_conda_forge` — no CLI flag exists yet to set it; hardcoded
  `False`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | valid recipe at `<root>/recipes/foo/`, root resolves | `submit()`'s own `ShipTargetResult` returned unchanged | No error |
| No recipe path | `recipe_path=None` or blank | -- | raises `ShipCondaForgeRecipeMissingError` |
| CFE root unresolved | recipe path given, root doesn't resolve | -- | raises `CfeUnresolvedError` |
| Wrong location | root resolves, recipe outside `<root>/recipes/<name>/` | -- | raises `ShipCondaForgeRecipeLocationError` naming both paths |
| Pathological path | `Path.resolve()` raises `OSError`/`ValueError` | `ShipTargetResult(FAILED, message=str(exc))` | data, not raised |
| `doctor`, root unresolved | -- | `conda_forge_ship_ready=False`, blocker names root | No error |
| `doctor`, root resolved, no `recipes/` dir | -- | `conda_forge_ship_ready=False`, blocker names missing dir | No error |
| `doctor`, both preconditions met | -- | `conda_forge_ship_ready=True`, `conda_forge_ship_blockers=()` | No error |

</intent-contract>

## Code Map

- `src/pyforge/mason/errors.py` -- add `ShipCondaForgeRecipeMissingError` (zero-arg, mirrors
  `CfeUnresolvedError`'s shape/`__reduce__`) and `ShipCondaForgeRecipeLocationError(recipe_path,
  expected_path)` (mirrors `PackageProjectPathError`'s two-arg validation-rigor shape/`__reduce__`).
- `src/pyforge/mason/package.py` -- add `ship_conda_forge(recipe_path, *, environ, cfe_root_arg,
  cfe_python_arg, cfe_timeout_arg, start_directory) -> ShipTargetResult`; add `from .resolve import
  resolve_cfe_root` (module scope, mirrors `doctor.py`).
- `src/pyforge/mason/doctor.py` -- extend `build_report()` to compute `conda_forge_ship_ready`/
  `conda_forge_ship_blockers` from the already-resolved `resolved_root`.
- `src/pyforge/mason/models.py` -- add the two new fields to `DoctorReport` (no defaults, matches
  this file's own no-defaults convention).
- `tests/unit/test_errors.py`, `tests/unit/test_package.py`, `tests/unit/test_doctor.py` -- new
  coverage.
- `tests/unit/test_models.py` (2 sites), `tests/unit/test_cli.py` (1 site) -- update the 3 existing
  direct `DoctorReport(...)` constructions with the two new fields.

## Tasks & Acceptance

**Execution:**
- [x] `errors.py` -- add `ShipCondaForgeRecipeMissingError`: identifier
  `ship:conda-forge-recipe-missing`, fixed message naming `mason recipe new` as the remedy;
  zero-arg constructor; `__reduce__` returning `(self.__class__, ())`.
- [x] `errors.py` -- add `ShipCondaForgeRecipeLocationError(recipe_path: str, expected_path: str)`:
  identifier `ship:conda-forge-recipe-location`, message names both paths and cites D-10; raises
  `ValueError` on an empty/non-str either argument (mirrors `PackageProjectPathError`); `__reduce__`
  returning `(self.__class__, (self.recipe_path, self.expected_path))`.
- [x] `package.py` -- add `ship_conda_forge()`: if `recipe_path` is `None`/blank, raise
  `ShipCondaForgeRecipeMissingError()`. Else call `resolve_cfe_root(cfe_root_arg, environ,
  start_directory)`; if `.root is None`, raise `CfeUnresolvedError()`. Else, inside one
  `try/except (OSError, ValueError)` (returning `ShipTargetResult(target="conda-forge",
  state=ShipState.FAILED, reference=None, message=str(exc))` on failure), resolve both
  `recipe_dir = Path(recipe_path).expanduser().resolve()` and `root_dir =
  resolved_root.root.expanduser().resolve()`; compute `expected_dir = root_dir / "recipes" /
  recipe_dir.name`; if `recipe_dir != expected_dir`, raise `ShipCondaForgeRecipeLocationError(
  str(recipe_dir), str(expected_dir))`. Else `from . import recipe` (lazy) and `return
  recipe.submit(str(recipe_dir), confirm=True, prepare_only=False, cfe_root_arg=cfe_root_arg,
  cfe_python_arg=cfe_python_arg, cfe_timeout_arg=cfe_timeout_arg, environ=environ,
  start_directory=start_directory)`.
- [x] `models.py` -- add `conda_forge_ship_ready: bool` and `conda_forge_ship_blockers:
  tuple[str, ...]` fields to `DoctorReport`.
- [x] `doctor.py` -- in `build_report()`, after computing `resolved_root`, build a blockers list:
  append `"the CFE root is unresolved"` when `resolved_root.step == STEP_NOT_FOUND`; elif
  `not (resolved_root.root / "recipes").is_dir()`, append a message naming the missing directory.
  Pass `conda_forge_ship_ready=not blockers, conda_forge_ship_blockers=tuple(blockers)` into the
  returned `DoctorReport`.
- [x] `tests/unit/test_errors.py` -- both new classes: identifier, message content (recipe-missing
  names `mason recipe new`; recipe-location names both paths), `__reduce__` round-trip
  (deepcopy/pickle), empty/malformed-argument rejection for `ShipCondaForgeRecipeLocationError`.
- [x] `tests/unit/test_package.py` -- `ship_conda_forge`: no-recipe-path raises (`None` and blank
  string) before any resolution happens; CFE-root-unresolved raises `CfeUnresolvedError` (mock
  `resolve_cfe_root`); wrong-location raises `ShipCondaForgeRecipeLocationError` naming both paths,
  no subprocess spawned (patch `pyforge.mason.cfe.subprocess.run`, assert not called); happy path
  (mock `resolve_cfe_root` root resolved, mock `recipe.submit` return value) returns it unchanged;
  a real end-to-end test against the `fake_cfe_root` fixture mirroring
  `test_submit_against_fake_cfe_root_returns_the_fixtures_canned_success` — call `ship_conda_forge`
  with `recipe_path=str(fake_cfe_root / "recipes" / "example-recipe")`,
  `cfe_root_arg=str(fake_cfe_root)`, assert the same canned `PENDING` result `submit()`'s own test
  asserts (no `recipes/` directory needs to exist on disk — matches `submit()`'s established
  no-existence-check precedent, path resolution only).
- [x] `tests/unit/test_doctor.py` -- extend `_build`'s assertions: root unresolved ->
  `conda_forge_ship_ready is False`, blockers non-empty; root resolved + `tmp_path`-backed
  `recipes/` dir present -> `conda_forge_ship_ready is True`, blockers empty; root resolved + no
  `recipes/` dir -> `conda_forge_ship_ready is False`, blockers non-empty.
- [x] `tests/unit/test_models.py`, `tests/unit/test_cli.py` -- add `conda_forge_ship_ready`/
  `conda_forge_ship_blockers` to the 3 existing direct `DoctorReport(...)` literals.

**Acceptance Criteria:**
- Given `--ship conda-forge` with valid preconditions, when it executes, then it calls
  `recipe.py::submit()` and returns its `ShipTargetResult` unchanged.
- Given the codebase is inspected, then `package.py` contains no staged-recipes submission logic
  of its own (no `cfe.submit_pr` call, no CFE-argv construction).
- Given a recipe path supplied by the user, when the target runs, then that recipe is used.
- Given no recipe path, when the target runs, then `ShipCondaForgeRecipeMissingError` is raised
  naming `mason recipe new`, and no CFE subprocess is ever spawned.
- Given an unresolvable CFE root or a recipe outside `<cfe-root>/recipes/<name>/`, when
  `ship_conda_forge` runs, then it raises naming the unmet precondition before any CFE subprocess
  spawns — leaving a caller (a future multi-target dispatcher) free to catch it and continue with
  other targets, mirroring `ship_pypi`'s identical structural-precondition-raises convention.
- Given `mason doctor` runs, then it reports `conda_forge_ship_ready`/`conda_forge_ship_blockers`
  reflecting both D-10 preconditions, and never raises regardless of CFE state.

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass 1
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 2, low 3)
- defer: 1: (low 1)
- reject: 7: (low 7)
- addressed_findings:
  - `[medium]` `[patch]` `doctor.py`'s new `conda_forge_ship_ready`/`conda_forge_ship_blockers`
    check compared `resolved_root.root` directly against `<root>/recipes` without first calling
    `.expanduser().resolve()` on it (unlike `ship_conda_forge()`'s own identical check) -- a
    `--cfe-root ~/my-cfe` or relative `MASON_CFE_ROOT` would misreport `conda_forge_ship_ready
    =False` even when `ship_conda_forge()` itself would succeed against the same input,
    undermining the story's own "a user learns the boundary before attempting a release, not
    during one" guarantee. Raised by Blind Hunter. Fixed: `doctor.py` now resolves `root_dir =
    resolved_root.root.expanduser().resolve()` before the `recipes` check, mirroring `package.py`.
  - `[medium]` `[patch]` `doctor.py`'s new `(resolved_root.root / "recipes").is_dir()` check was
    unguarded -- a `PermissionError` (EACCES) on the stat call would propagate and violate this
    module's own documented "`build_report` never raises" invariant. Raised by Edge Case Hunter.
    Fixed in the same edit as the item above: the check now runs inside a `try/except OSError`,
    treating a stat failure as `not a directory` (a blocker) rather than crashing.
  - `[low]` `[patch]` `errors.py::CfeUnresolvedError`'s docstring named only its original raise
    site (`cfe.py::ensure_cfe_root`), not this diff's new direct raise from
    `package.py::ship_conda_forge` -- inconsistent with this codebase's own exact-call-site-citing
    docstring convention. Raised by Blind Hunter. Fixed: docstring now names both raise sites.
  - `[low]` `[patch]` `package.py::ship_conda_forge`'s `expected_dir = root_dir / "recipes" /
    recipe_dir.name` was composed from an already-resolved `root_dir` but never itself
    re-`.resolve()`d -- if `<root>/recipes` were a symlink, `expected_dir` would not reflect the
    true physical path, risking a false-mismatch against the independently-`.resolve()`d
    `recipe_dir` for an otherwise-valid symlinked placement. Raised by Blind Hunter. Fixed: wrapped
    the composed path in `.resolve()`.
  - `[low]` `[patch]` `tests/unit/test_errors.py` covered `ShipCondaForgeRecipeLocationError`'s
    non-string/empty rejection only for `recipe_path`, not the symmetrically-validated
    `expected_path`. Raised by Blind Hunter. Fixed: added the matching `expected_path` case.
- **Deferred** (tracked station `pyforge-mason`, base id `DW-3-6`; full entry in
  `deferred-work.md`):
  - `[low]` `[defer]` **`DW-3-6-1`** -- `ship_conda_forge`'s `try/except (OSError, ValueError)`
    around `Path(...).expanduser().resolve()` does not catch `RuntimeError`, which
    `Path.expanduser()` raises when `~` can't be resolved (e.g. `HOME` unset) -- the function would
    crash instead of returning a `FAILED` result as its own docstring promises. Raised by Edge Case
    Hunter. Not patched here: this exact gap already exists, identically, in
    `recipe.py::submit()`'s own established precedent (Story 2.9) that this story's own spec
    explicitly instructed mirroring -- fixing only the new copy would diverge from the function it
    was designed to match. Best fixed holistically across both functions in a dedicated pass.
- **Rejected** (matches established precedent or explicitly out of this story's documented scope):
  - `[low]` `[reject]` `ShipCondaForgeRecipeMissingError`'s message names `mason recipe new`,
    which is not registered in this worktree's `cli.py` yet (Story 2.4 landed on `main` via PR
    #465, not yet merged into this loop-home branch -- see spec's `Never` boundary, already
    documented at spec-authoring time). FR-23 itself hardcodes this exact remedy; the message is
    correct per the requirement and will resolve automatically once this branch syncs forward.
  - `[low]` `[reject]` `ship_conda_forge` calls `resolve_cfe_root`/`Path.resolve()` once for its
    own precondition checks, then `recipe.submit()` independently repeats both -- redundant but
    cheap (pure, filesystem-read-only calls), and matches this codebase's established convention
    of calling such pure resolution functions freely rather than threading pre-resolved state
    through layers.
  - `[low]` `[reject]` `mason doctor`'s `conda_forge_ship_ready` checks `<root>/recipes` directory
    existence as a proxy for D-10's second precondition rather than validating any specific
    recipe's placement -- exactly the interpretation the spec's own Design Notes ("Why doctor's
    second precondition is directory-existence, not per-recipe") already reasoned through and
    documented, given `mason doctor` takes no recipe-path argument.
  - `[low]` `[reject]` the AC describing multi-target failure isolation (`conda-forge` fails alone
    while `pypi` continues) is unverified by this diff -- explicitly Story 3.9's scope (no
    orchestrator exists yet); the spec's own Never boundary and Design Notes already state
    `ship_conda_forge` raises structural preconditions, mirroring `ship_pypi`/`ship_channel`'s
    identical convention, leaving isolation to the not-yet-built dispatcher.
  - `[low]` `[reject]` `ship_conda_forge`'s own `if not recipe_path or not recipe_path.strip():`
    does not `isinstance`-check `recipe_path` before use (a non-`str` input raises `AttributeError`
    rather than the intended `MasonError`) -- matches this codebase's established convention that
    function parameters trust their type hints (e.g. `ship_pypi`/`build` do not isinstance-check
    `project_path` either); only error-CLASS constructors isinstance-check their own stored fields,
    which `ShipCondaForgeRecipeLocationError` already does correctly.
  - `[low]` `[reject]` `test_ship_conda_forge_returns_failed_when_path_resolve_raises` patches
    `pyforge.mason.package.Path.resolve` globally (affecting every `Path` instance during the
    `with` block, not just the call under test) -- standard, already-used Python mocking technique
    in this codebase; the test passes correctly and is scoped to one function call with no other
    `Path.resolve()` calls inside it.
  - `[low]` `[reject]` `DoctorReport` gained two new non-optional fields with no compatibility note
    for external consumers -- no such convention exists anywhere in this actively-developing,
    internal-dataclass codebase (every prior field addition, including Story 2.1's own move of
    `DoctorReport` into `models.py`, carried none either).

### 2026-08-13 — Review pass 2 (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 0, medium 2, low 5)
- defer: 1: (medium 1)
- reject: 6: (low 6)
- addressed_findings:
  - `[medium]` `[patch]` `doctor.py::build_report` RAISED `RuntimeError`, breaking its own
    documented "Never raises" invariant. `Path.expanduser()` raises `RuntimeError` -- **not** an
    `OSError` subclass for this failure -- whenever a leading `~`/`~user` cannot be expanded
    (unknown user, or `HOME` unset), and pass 1's own new `except (OSError, ValueError)` did not
    catch it. Reproduced: `build_report(cfe_root_arg="~nosuchuser9/cfe", ...)` raised, which
    `cli.py`'s `doctor` branch does not handle, so it surfaces as a raw traceback -- on exactly the
    broken-environment input `mason doctor` exists to diagnose (violating AD-7/FR-33's
    no-traceback contract). Raised independently by BOTH Blind Hunter and Edge Case Hunter. Fixed:
    `RuntimeError` added to the except tuple; regression test added.
  - `[medium]` `[patch]` The same `RuntimeError` escaped `package.py::ship_conda_forge`, breaking
    its docstring's promise that a resolve failure returns `ShipTargetResult(FAILED)` rather than
    raising. Raised by both hunters. Reproduced via `MASON_CFE_ROOT=~nosuchuser9/cfe`. Patched here
    rather than left to `DW-3-6-1` because that entry's premise is only half-applicable: it defers
    on the grounds that this mirrors `recipe.py::submit()`'s identical pre-existing gap, which
    holds for the `recipe_path` trigger but **not** for `root_dir` -- `submit()` never expands a
    root, so `resolved_root.root.expanduser()` is net-new code from this story with no precedent to
    diverge from (`grep -rn expanduser src/` confirms the root is expanded in exactly two places
    package-wide, both added by this diff). Fixed: `RuntimeError` added to the except tuple; two
    regression tests added (one per trigger). `DW-3-6-1` is left untouched -- the orchestrator owns
    its status, and `submit()`'s own copy of the gap is still unpatched.
  - `[low]` `[patch]` `doctor.py`'s blockers branch guarded only on `step == STEP_NOT_FOUND` while
    the very next statement in the same function still defends the same attribute with `root is not
    None` -- so `ResolvedCfeRoot(root=None, step=STEP_FLAG)` raised `AttributeError`, which the
    except tuple does not catch, again breaking never-raises. Latent (unreachable from
    `resolve_cfe_root` today) but the tests hand-construct `ResolvedCfeRoot`. Raised by both
    hunters. Reproduced. Fixed: the branch now also guards `root is None`; regression test added.
  - `[low]` `[patch]` `doctor.py`'s `except` branch reported the blocker path in a *different
    spelling* than its success branch: resolution and the `is_dir()` stat shared one `try`, so a
    denied stat fell back to the un-resolved root and printed `~/my-cfe/recipes` where every other
    outcome on identical input printed `<home>/my-cfe/recipes`. Raised by Blind Hunter. Fixed: the
    two are now guarded separately (`try`/`except`/`else`), so a denied stat keeps the resolved
    spelling and the raw fallback is used only when resolution itself failed -- when it is the only
    spelling that exists. Test added asserting the exact blocker string.
  - `[low]` `[patch]` `package.py::ship_conda_forge`'s docstring said "Validates D-10's **two**
    shipping preconditions itself, in order" and then enumerated **three** items, and `errors.py`
    numbered the location error the "second shipping precondition" when it is the third and last
    gate -- so a maintainer reading `errors.py` alone would conclude the location check runs before
    root resolution, the reverse of the real ordering (which determines which error a user sees
    when several inputs are wrong at once). Raised by Blind Hunter. Fixed: both docstrings now
    distinguish `ship_conda_forge`'s own precursor gate (#1, recipe path supplied) from D-10's two
    actual preconditions (#2 root, #3 location), and name the real ordering.
  - `[low]` `[patch]` `doctor.py`'s and `models.py`'s new docstrings both claimed the blockers are
    "both of `package.py::ship_conda_forge`'s own shipping preconditions". They are not, and this
    diff's own e2e test proves it: `ship_conda_forge` performs **no** `recipes/` existence check
    (`test_package.py`: "No `recipes/` directory needs to exist on disk"), while doctor's check is
    exactly that -- so the proxy is stricter in one direction, and cannot see precondition #1 or
    #2's per-recipe equality at all. Raised by Blind Hunter. The *behavior* is the spec's own
    documented Design Note (and was correctly rejected in pass 1); only the docstrings' claim of
    equivalence was wrong. Fixed: both now say PROXY and state precisely how it differs.
  - `[low]` `[patch]` `ship_conda_forge` stripped `recipe_path` for its blank test
    (`not recipe_path.strip()`) but passed the **un**stripped value to `Path()` -- so a
    leading-space value such as `"  /abs/foo"` is not absolute (its first path component is the
    spaces) and silently resolved relative to the cwd, producing a location error naming a path the
    user never supplied. Raised by Edge Case Hunter. Fixed: `Path(recipe_path.strip())`, matching
    gate #1's own treatment; regression test added.
- **Deferred** (tracked station `pyforge-mason`, base id `DW-3-6`; full entry in
  `deferred-work.md`):
  - `[medium]` `[defer]` **`DW-3-6-2`** -- `resolve_cfe_root`'s flag/environment steps return the
    CFE root un-expanded and `cfe.py` never expands it either, so a `~`-prefixed root reaches every
    child-process invocation as a literal path that cannot exist. Reproduced against a real
    temporary `HOME`: `build_report(cfe_root_arg="~/mycfe", ...)` reports
    `conda_forge_ship_ready=True` with zero blockers while the script path `cfe.py` composes from
    that same root does not exist. Raised by Blind Hunter. Pre-existing and whole-package (every
    CFE-backed verb has failed this way since the resolution chain shipped); this story merely made
    it visible by adding the only two root-expanding call sites in the package. Not patched: the
    correct fix normalizes the root ONCE at resolution rather than adding a third independent
    expansion per consumer, which changes what every `resolve.py` test asserts and what `mason
    doctor` prints for `cfe_root`. Deliberately not worked around in `doctor.py` either -- removing
    this story's expansion would make doctor disagree with `ship_conda_forge`'s own identical
    resolution and regress the correctly-handled relative-root case.
- **Rejected** (matches established precedent, spec-directed, or explicitly out of scope):
  - `[low]` `[reject]` a symlinked `<root>/recipes/<name>` whose target basename differs would be
    falsely rejected (`recipe_dir.name` becomes the target's name, so `expected_dir` is composed
    from the wrong leaf). Fixing it means comparing `recipe_dir.parent` against
    `(root_dir / "recipes").resolve()` -- a different check from the one the spec's Always boundary
    specifies literally ("must equal `resolve_cfe_root(...).root...resolve() / "recipes" /
    recipe_dir.name`"). Spec-directed; deviating is a spec amendment, not a patch.
  - `[low]` `[reject]` a `recipe_path` naming a file rather than a directory (e.g.
    `<root>/recipes/foo/recipe.yaml`) yields an error telling the user to place the recipe at
    `<root>/recipes/recipe.yaml`. The function correctly REJECTS the input; only the message reads
    oddly, and it does name the two resolved paths accurately, which is what the spec requires.
  - `[low]` `[reject]` `ship_conda_forge` hand-rolls `if resolved_root.root is None: raise
    CfeUnresolvedError()` instead of calling `cfe.py::ensure_cfe_root` (which every other
    CFE-dependent verb uses, and which keys off `step == STEP_NOT_FOUND` instead). The spec's task
    list directs this exact shape verbatim, and routing through `ensure_cfe_root` would pull `cfe`
    further into `package.py`, against AD-6's own grain.
  - `[low]` `[reject]` `"recipes"` is a bare inline literal in `package.py` and `doctor.py`, where
    every other re-declaration of CFE layout knowledge in this package is a named constant carrying
    an AD-2/AD-3 duplication note. Real inconsistency, but the spec directs the literal
    composition, no shared constant exists to reuse (`submit()` deliberately derives
    `recipe_dir.parent` instead), and minting one is a design decision beyond this story.
  - `[low]` `[reject]` `test_ship_conda_forge_returns_failed_when_path_resolve_raises` patches
    `Path.resolve` globally and so cannot tell which of the three resolutions failed. Pass 1
    already rejected the global-patch technique as standard and correctly scoped; the substantive
    half of the finding (no coverage for the exception classes that actually escape) is addressed
    above by the two new `RuntimeError` tests, which are trigger-specific.
  - `[low]` `[reject]` the AC describing multi-target failure isolation is still unverified by this
    diff -- Story 3.9's scope (no orchestrator exists yet). Pass 1 rejected this on scope and the
    reviewer that re-raised it explicitly inherited that rejection; re-confirmed.

### 2026-08-13 — Review pass 3 (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 1, low 2)
- defer: 1: (medium 1)
- reject: 11: (low 11)
- addressed_findings:
  - `[medium]` `[patch]` One `DoctorReport` answered the same question two ways: `build_report`
    set `conda_forge_ship_ready=True` while, three fields away, `unavailable_verbs` named
    `"recipe"` — the very verb `ship_conda_forge` delegates to. `unavailable_verbs` is set when
    `floor_result.missing` is non-empty, but the new blockers list consulted only the root and
    `<root>/recipes`, so an incomplete CFE import floor left both D-10 preconditions met and the
    ship path structurally dead. Raised by Edge Case Hunter. Fixed: an incomplete import floor is
    now a fourth blocker, naming the missing modules and why the verb is unavailable; regression
    test asserts the two fields can no longer disagree.
  - `[low]` `[patch]` `doctor.py` reported an unresolvable CFE root as a missing directory. Pass
    2's `except (OSError, ValueError, RuntimeError)` fell back to the raw spelling and then dropped
    into the shared `is not a directory` blocker, so `--cfe-root ~nosuchuser9/cfe` produced
    `"~nosuchuser9/cfe/recipes is not a directory"` — naming a cause that was not the real one and
    implying a remedy (create that directory) impossible at a path that cannot exist, in the one
    command whose entire job is diagnosis. Raised by Blind Hunter. Fixed: resolution failure now
    emits its own blocker naming the root and the underlying error; the denied-stat path still
    keeps the resolved spelling (pass 2's fix preserved); two tests updated/added.
  - `[low]` `[patch]` Pass 1 added `.resolve()` to `expected_dir` with a symlinked
    `<root>/recipes` as its sole stated justification and shipped it with zero coverage of that
    scenario — `grep -n symlink tests/unit/test_package.py` returned only an `OSError` mock
    string, so a future refactor dropping the `.resolve()` would fail no test. Raised by Blind
    Hunter. Fixed: added a test placing a recipe under a symlinked `recipes` dir and asserting
    `ship_conda_forge` accepts it and forwards the physical path.
- **Deferred** (tracked station `pyforge-mason`, base id `DW-3-6`; full entry in
  `deferred-work.md`):
  - `[medium]` `[defer]` **`DW-3-6-3`** — `resolve.py::resolve_cfe_root`'s cwd-walk step opens with
    a bare, unguarded `start_directory.resolve()`, which sits ABOVE every guard both callers have:
    `build_report` calls it as its first statement and `ship_conda_forge` calls it before entering
    its own `try`. With the process cwd deleted, both raise `FileNotFoundError` — breaking
    `build_report`'s never-raises invariant and `ship_conda_forge`'s FAILED-not-raised promise.
    Reproduced for both functions. Raised by Blind Hunter. Pre-existing, not introduced here:
    `resolve.py` is untouched by this diff (0 lines) and `build_report` already called
    `resolve_cfe_root` before this story; two passes of hardening the code immediately below the
    call merely made the bare call conspicuous. Not patched: the fix belongs in `resolve.py`
    (deciding what a resolution-failed walk returns is a behavior change across every consumer and
    every `resolve.py` test), not in a third per-caller `try` that leaves the other CFE-backed
    verbs exposed. Adjacent to `DW-3-6-2`; both are `resolve_cfe_root` normalization.
- **Rejected** (matches established precedent, spec-directed, or explicitly out of scope):
  - `[low]` `[reject]` `ship_conda_forge` hardcodes `confirm=True`, so the conda-forge ship path
    can never dry-run, and the wrapped CFE script force-pushes and opens a public PR. Verified the
    premise is true, and rejected on two independent grounds: the spec directs `confirm=True`
    verbatim in both its Always boundary and its task list, and it is REQUIRED to reach the epic
    AC's `PENDING` outcome (`recipe.py:480`: `confirm=False` maps to `NOT_ATTEMPTED`). It also
    matches the sibling convention — `ship_pypi` really uploads to PyPI and `ship_channel` really
    uploads to a channel, neither taking a confirm/dry-run parameter. The PRD's "`--dry-run` is
    the default" governs `mason recipe submit`, which retains it. A `--dry-run` on the ship surface
    is Story 3.9's scope, along with the CLI wiring that makes this function reachable at all.
  - `[low]` `[reject]` a recipe reached via a symlink whose target basename differs (e.g.
    `recipes/foo -> recipes/bar`) is accepted and submitted as `bar`, so the user "asks to ship
    `foo` and Mason ships `bar`". This is ordinary `Path.resolve()` semantics: the two names denote
    one directory, and the path the user supplied IS the target. Pass 2 rejected the mirror-image
    half of this same root cause as spec-directed; the spec's Always boundary specifies
    `recipe_dir.name` off the resolved path literally.
  - `[low]` `[reject]` pass 1's `expected_dir.resolve()` "makes D-10 bypassable" — with
    `<root>/recipes` symlinked to `<root>/other`, a recipe at `<root>/other/foo` is accepted.
    That is precisely the case the patch was added for, and it is not a bypass: an operator who
    symlinks `recipes` has chosen that layout, and the recipe genuinely is at `<root>/recipes/foo`
    through it. Comparing both sides physically is the coherent reading of D-10.
  - `[low]` `[reject]` `mason doctor` reports `conda_forge_ship_ready=True` for a `--cfe-root`
    pointing at a non-CFE directory that merely contains `recipes/`, because the marker directory
    is never checked. `resolve.py`'s own docstring states the flag/env steps are deliberately "NOT
    validated against the marker directory"; adding marker validation to doctor alone would make
    it disagree with `ship_conda_forge`'s identical resolution — the exact trap `DW-3-6-2` already
    documents.
  - `[low]` `[reject]` the new `.expanduser().resolve()` resolves a RELATIVE root against the
    process cwd rather than `start_directory`, making that parameter decorative for relative roots
    and routing around AD-5's hermetic-resolution intent. Real, but nil consequence in production
    (`cli.py` passes `Path.cwd()`), and the correct fix is `DW-3-6-2`'s own stated remedy —
    normalize the root ONCE at resolution — not a third per-consumer expansion, which that entry
    explicitly argues against.
  - `[low]` `[reject]` the two denied-stat tests assert a failure mode this interpreter cannot
    produce: on 3.13+ `Path.is_dir()` delegates to `os.path.isdir`, which swallows `OSError`, so
    they pass only because they monkeypatch `Path.is_dir` to raise. True, but the `except OSError`
    guard remains correct for the package's declared 3.12 floor, and forcing an unreachable-on-this-
    version failure via monkeypatch is standard defensive testing, not a defect.
  - `[low]` `[reject]` the AD-16 end-to-end test "cannot tell a live submission from a dry run"
    because the fixture ignores extra argv, and no test asserts what the conda-forge path invokes.
    The premise is wrong: `test_ship_conda_forge_happy_path_returns_recipe_submit_result_unchanged`
    asserts the full delegation contract via `mock_submit.assert_called_once_with(...)`, including
    `confirm=True` and `prepare_only=False`. The delegation boundary is pinned; argv below it is
    `recipe.py::submit()`'s own tested responsibility (AD-11, one owner).
  - `[low]` `[reject]` `ship_conda_forge`'s signature is not call-compatible with `ship_pypi`/
    `ship_channel` (different first positional, four extra required kwargs), so Story 3.9's
    dispatcher must special-case it. Spec-directed — the Code Map names this signature verbatim —
    and the dispatcher does not exist yet; how it normalizes target arguments is 3.9's design.
  - `[low]` `[reject]` `ShipCondaForgeRecipeLocationError`'s docstring "contradicts itself in three
    sentences" by saying "second" then "THIRD". Not a contradiction: the two numbers index
    different sequences — D-10's second PRECONDITION is `ship_conda_forge`'s third GATE — and the
    docstring states that distinction explicitly in the sentence the finding quotes. This is
    exactly what pass 2 added; it reads correctly.
  - `[low]` `[reject]` `Path(recipe_path.strip())` silently rewrites a recipe directory whose name
    ends in whitespace. Deliberate pass-2 trade-off: the strip fixed a real, reachable bug (a
    leading-space path is not absolute and resolved against the cwd, naming a path the user never
    supplied). A directory name with significant trailing whitespace is pathological by comparison.
  - `[low]` `[reject]` `recipe_path="/"` yields an empty `recipe_dir.name`, so the error names
    `<root>/recipes` with the `<name>` segment silently dropped. The function correctly REJECTS the
    input; only the message reads oddly, and it does name both resolved paths accurately — the same
    class of finding, on the same message, that pass 2 already rejected for a file-not-directory
    `recipe_path`.

## Design Notes

**Why "wraps... state=pending" means pass-through, not a hardcoded override:** `submit()` already
returns a `ShipTargetResult` with `target="conda-forge"` baked in, mapped across all of
`NOT_ATTEMPTED`/`FAILED`/`PENDING` depending on the real CFE outcome. `models.ShipTargetResult`'s
own docstring already resolves this: "`package.py`... wraps ITS `ShipTargetResult` -- never produces
a second one." The epic AC's "state = pending" describes the typical confirmed-success outcome, not
a literal override — forcing `PENDING` on every call would misreport a `submit()` failure as pending.

**Why the location check is stricter than `submit()`'s own leniency:** `submit()` (Story 2.9)
already supports an out-of-tree recipe via the `CFE_RECIPES_ROOT` env override (its own docstring).
D-10 deliberately narrows this for the ship-target boundary alone: "Shipping to `conda-forge` works
only from a repository where... the recipe sits at `<cfe-root>/recipes/<name>/`" (PRD D-10) — `mason
recipe submit` stays lenient; `mason package ship --to conda-forge` does not.

**Why doctor's second precondition is directory-existence, not per-recipe:** `mason doctor` takes
no recipe-path argument today, and adding one is out of this story's scope (FR-23/AC6 names no new
CLI flag). Checking `<root>/recipes` exists reports D-10's second precondition at the only
granularity doctor can observe without a recipe argument.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: `done` (review pass 3, follow-up).

**Implemented change (cumulative):** `package.py::ship_conda_forge()` validates D-10's two shipping
preconditions itself (plus a recipe-path precursor gate), then lazily delegates to
`recipe.py::submit()` and returns its `ShipTargetResult` unchanged (AD-11 — one owner, no
reimplementation). `mason doctor` gained `conda_forge_ship_ready`/`conda_forge_ship_blockers`, a
recipe-independent proxy for whether a conda-forge ship could run, without ever raising.

**This pass changed:**
- `src/pyforge/mason/doctor.py` — an incomplete CFE import floor is now a blocker, so
  `conda_forge_ship_ready` can no longer contradict `unavailable_verbs` in the same report; an
  unresolvable root now reports its own cause instead of masquerading as a missing `recipes/`
  directory.
- `src/pyforge/mason/models.py` — `DoctorReport` docstrings updated to state that the proxy covers
  the import floor as well as D-10's two preconditions.
- `tests/unit/test_doctor.py` — 2 new tests (import-floor blocker; unresolvable root is not
  reported as a missing directory), 1 assertion updated for the new blocker text.
- `tests/unit/test_package.py` — 1 new test pinning that a recipe under a symlinked
  `<root>/recipes` is accepted, covering pass 1's previously untested `expected_dir.resolve()`.

**Findings breakdown (pass 3):** 3 patches applied (1 medium, 2 low); 1 deferred (`DW-3-6-3`,
medium — `resolve_cfe_root`'s unguarded `start_directory.resolve()` breaks both callers'
never-raises contracts when the process cwd is deleted; pre-existing, `resolve.py` untouched by
this diff); 11 rejected, all low. No intent gaps and no spec defects — the intent contract held for
a third consecutive pass.

**Verification:** `pixi run -e pyforge-mason pyforge-mason-test` — **1205 passed, 1 deselected**
(1202 before this pass; +3 new tests, 0 failures). Both patched behaviors were reproduced before
patching and are pinned by the new tests. The deferred finding was independently reproduced
(`FileNotFoundError` from both `build_report` and `ship_conda_forge` under a deleted cwd) before
being written to the ledger.

**Residual risks:**
- The import-floor blocker goes beyond the spec's literal two-blocker enumeration in its Always
  boundary. Classified `patch` rather than `bad_spec` because every spec assertion still holds
  (the field reflects both D-10 preconditions; `build_report` still never raises) and the change
  removes a self-contradiction rather than introducing new behavior the spec forbids.
- `ship_conda_forge` remains unreachable from the CLI until Story 3.9 wires `--to conda-forge`.
  Its hardcoded `confirm=True` means the first real caller ships for real; a `--dry-run` surface
  is 3.9's to add (see pass 3's rejects).
- `DW-3-6-1`, `DW-3-6-2` and `DW-3-6-3` all point at `resolve.py` normalization and would sensibly
  be fixed together. Left untouched here — the orchestrator owns their status.

