---
title: 'Degradation when CFE is unavailable'
type: 'feature'
created: '2026-08-09'
status: 'done'
baseline_revision: 'effbbe5ef993bb46ceab9d682ce4a080ef23d6ec'
review_loop_iteration: 0
followup_review_recommended: false
final_revision: 'a28d1214e04216684803b5a3257cb871f30bc74e'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** No CFE-not-found error exists yet, so nothing maps "CFE root unresolvable" to
`EXIT_CFE_UNAVAILABLE` (3, already defined in `exit_codes.py`) or explains how to fix it; and
`package.py`/`environment.py` do not exist yet, so AD-6's "these must never depend on CFE" claim is
unproven and unenforced.

**Approach:** Add `CfeUnresolvedError` (identifier `cfe:unresolved`) to `errors.py` and
`ensure_cfe_root(resolved) -> None` to `cfe.py` (raises when `resolved.step == STEP_NOT_FOUND`,
mirroring Story 1.6's `ensure_import_floor`); wire a `CfeUnresolvedError` branch into `cli.py`'s
`main()` ahead of the generic `MasonError` catch, mapping it to `EXIT_CFE_UNAVAILABLE`. Seed
`package.py`/`environment.py` as minimal stub modules with zero CFE import, and add an AST meta-test
proving neither ever gains a module-level one.

## Boundaries & Constraints

**Always:** `CfeUnresolvedError` identifier is exactly `cfe:unresolved` (matches
`test_cli.py`'s existing forward-reference comment); `ensure_cfe_root(resolved: ResolvedCfeRoot) ->
None` takes the already-computed outcome and never re-resolves (`resolve.py`'s own docstring: "a
later caller... never needs to re-resolve"); in `cli.py`'s `main()`, `except CfeUnresolvedError`
must be listed *before* `except MasonError` (it is a subclass; Python matches the first listing) and
follows the identical print-to-stderr/no-traceback pattern already used for `MasonError`; the new
AD-6 meta-test scans only the direct children of each file's `ast.Module` body for a `cfe` import
(`import cfe`/`from . import cfe`/`from .cfe import ...`) -- never `ast.walk`, which also descends
into function bodies and would wrongly forbid the *lazy* import AD-6 explicitly permits for
`package.py`'s future conda-forge ship target (Epic 3); `package.py`/`environment.py` are seeded as
docstring-only stub modules.

**Block If:** none identified -- FR-5, D-2, AD-5/AD-6/AD-7, and the existing
`resolve.py`/`cfe.py`/`errors.py`/`exit_codes.py`/`cli.py` conventions fully specify this work.

**Never:** wire any `recipe`/`package`/`environment` verb into `cli.py`'s subparsers -- no verb
exists yet (Epics 2-4 own that); create `recipe.py` -- Epic 2's CFE-port story owns it; give
`package.py`/`environment.py` any real build/ship/lock logic -- Epic 3/4 scope, this story proves
only the import-safety invariant; call `resolve_cfe_root` from inside `ensure_cfe_root` -- it must
accept the pre-computed `ResolvedCfeRoot`, not re-derive it; add a `--cfe-timeout`-style new flag or
touch `_resolve_str`/`_resolve_bool` -- out of scope.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| CFE root resolved via any real step | `resolved.step` in `{flag, environment, cwd-walk}` | `ensure_cfe_root(resolved)` returns `None` | none |
| CFE root unresolved | `resolved.step == STEP_NOT_FOUND` | `ensure_cfe_root(resolved)` raises `CfeUnresolvedError` | typed error, no traceback |
| `CfeUnresolvedError` raised inside `main()`'s try block | monkeypatched, mirrors existing synthetic-`MasonError` test | `main()` returns `EXIT_CFE_UNAVAILABLE` (3); stderr message names all four step names (`flag`, `environment`, `cwd-walk`, `not-found`) and how to satisfy the first three (`--cfe-root`, `MASON_CFE_ROOT`, run from within/below a `.claude/scripts/conda-forge-expert/` tree) | typed error, no traceback |
| A non-CFE `MasonError` raised inside `main()` (regression guard) | e.g. `MasonError("test:injected-failure", ...)` | `main()` still returns `EXIT_FAILED` (1), unchanged | typed error, no traceback |
| `package.py`/`environment.py` carry a module-level `cfe` import (synthetic fixture) | AST tree with `import cfe` at file scope | AD-6 meta-test detector flags the file | n/a (test infra) |
| `package.py`/`environment.py` carry only a lazy, function-body `cfe` import (synthetic fixture) | AST tree with `import cfe` nested inside a `def` | AD-6 meta-test detector does not flag it -- lazy import permitted | n/a |
| Real import of the seeded modules | no CFE anywhere on the filesystem | `import pyforge.mason.package` / `import pyforge.mason.environment` succeeds, no exception | none |

</intent-contract>

## Code Map

(paths relative to `src/shared/packages/pyforge-mason/`)

- `src/pyforge/mason/errors.py` (extend) -- add `CfeUnresolvedError(MasonError)`.
- `src/pyforge/mason/cfe.py` (extend) -- add `ensure_cfe_root`, importing `ResolvedCfeRoot`/`STEP_NOT_FOUND` from `.resolve`.
- `src/pyforge/mason/cli.py` (extend) -- import `CfeUnresolvedError`, `EXIT_CFE_UNAVAILABLE`; add the new `except` branch in `main()`.
- `src/pyforge/mason/package.py` (new) -- minimal seed, no CFE import.
- `src/pyforge/mason/environment.py` (new) -- minimal seed, no CFE import.
- `tests/meta/test_capability_tiers.py` (new) -- AD-6 module-level-`cfe`-import guard for `package.py`/`environment.py`.
- `tests/unit/test_errors.py` (extend) -- `CfeUnresolvedError` coverage.
- `tests/unit/test_cfe.py` (extend) -- `ensure_cfe_root` coverage.
- `tests/unit/test_cli.py` (extend) -- `main()`'s new exception branch + regression test.
- `tests/unit/test_package.py`, `tests/unit/test_environment.py` (new, minimal) -- bare-import success.

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/mason/errors.py` -- add `CfeUnresolvedError(MasonError)`: no-argument constructor,
  identifier `cfe:unresolved`, a static message naming all four `resolve.py` step names (`flag`,
  `environment`, `cwd-walk`, `not-found`) and how to satisfy the first three (`--cfe-root` flag,
  `MASON_CFE_ROOT` environment variable, run `mason` from within or below a directory containing
  `.claude/scripts/conda-forge-expert/`) -- FR-5, D-2, NFR-14.
- [x] `src/pyforge/mason/cfe.py` -- add `ensure_cfe_root(resolved: ResolvedCfeRoot) -> None`
  (imports `ResolvedCfeRoot`, `STEP_NOT_FOUND` from `.resolve`): raises `CfeUnresolvedError()` when
  `resolved.step == STEP_NOT_FOUND`, otherwise returns `None` -- FR-5, AD-5, AD-6.
- [x] `src/pyforge/mason/cli.py` -- import `CfeUnresolvedError` from `.errors` and
  `EXIT_CFE_UNAVAILABLE` from `.exit_codes`; add `except CfeUnresolvedError as exc:` in `main()`,
  positioned before the existing `except MasonError` branch, printing `str(exc)` to stderr and
  returning `EXIT_CFE_UNAVAILABLE` -- FR-5, AD-7.
- [x] `src/pyforge/mason/package.py` (new) -- module docstring only, stating Epic 3 supplies real
  content and this story exists solely to prove the AD-6 import-safety invariant; no CFE import --
  FR-5, AD-6.
- [x] `src/pyforge/mason/environment.py` (new) -- same pattern, referencing Epic 4 -- FR-5, AD-6.
- [x] `tests/meta/test_capability_tiers.py` (new) -- AST-based AD-6 guard scanning `package.py` and
  `environment.py` for a module-level `cfe` import (direct `ast.Module.body` children only, so a
  future lazy import nested inside a function is not flagged); include synthetic-tree regression
  fixtures proving the detector fires on a module-level violation and permits a lazy one, mirroring
  `test_dependency_direction.py`'s rigor (unreadable/non-UTF-8/invalid-syntax handling not required
  here -- only the module-level-vs-nested distinction is novel).
- [x] `tests/unit/test_errors.py` -- `CfeUnresolvedError`'s identifier, and that its message contains
  all four step names and satisfaction guidance for the first three.
- [x] `tests/unit/test_cfe.py` -- `ensure_cfe_root` for every I/O-matrix row it covers (each matching
  step -> no raise; `STEP_NOT_FOUND` -> raises `CfeUnresolvedError`).
- [x] `tests/unit/test_cli.py` -- a `CfeUnresolvedError` raised inside `main()`'s try block returns
  `EXIT_CFE_UNAVAILABLE`, message on stderr, no traceback (mirrors the existing synthetic-`MasonError`
  monkeypatch test); plus a regression test that a non-CFE `MasonError` still returns `EXIT_FAILED`.
- [x] `tests/unit/test_package.py`, `tests/unit/test_environment.py` (new) -- `import
  pyforge.mason.package` / `import pyforge.mason.environment` succeeds without raising.

**Acceptance Criteria:**
- Given an unresolvable CFE root, when `CfeUnresolvedError` is the failure that reaches `main()`'s
  handler, then the process exits `3` (`EXIT_CFE_UNAVAILABLE`) with a message naming all four
  resolution steps and how to satisfy each, and no Python traceback is printed. (Proven at the
  `main()`/error-handling level; no `recipe` verb exists yet to dispatch through -- Epic 2 wires the
  call site that raises this error for real.)
- Given AD-6, when `package.py`/`environment.py` are inspected, then neither carries a module-level
  `cfe` import, and `import pyforge.mason.package` (and `environment`) succeeds with no CFE
  installation anywhere on the filesystem.
- Given the existing generic `MasonError` handling in `main()`, when a non-CFE `MasonError` is
  raised, then `main()` still returns `EXIT_FAILED` unchanged.

## Spec Change Log

## Review Triage Log

### 2026-08-09 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6 (medium: 1, low: 5)
- defer: 0
- reject: 4
- addressed_findings:
  - `[medium]` `[patch]` Both Blind Hunter and Edge Case Hunter independently found the new AD-6
    meta-test's `_has_module_level_cfe_import` bypassable: it recognized only `import cfe`/
    `from . import cfe`/`from .cfe import ...`, missing dotted-absolute forms (`import
    pyforge.mason.cfe`, `from pyforge.mason import cfe`) and a module-level `cfe` import nested
    inside a top-level `try`/`if`/`with` block (still eager at import time, but not a direct child
    of `tree.body`). Rewrote the detector to recognize dotted names ending in `.cfe` and to
    recursively scan compound-statement bodies (`Try`/`If`/`With`/handlers) while still refusing to
    descend into `FunctionDef`/`AsyncFunctionDef`/`ClassDef` (preserving the lazy-import exception
    AD-6 requires); added five regression tests covering each bypass form plus the still-permitted
    lazy case.
  - `[low]` `[patch]` Blind Hunter found `CfeUnresolvedError`'s message logically incoherent:
    "none of the four resolution steps matched (flag, environment, cwd-walk, not-found)" lists
    `not-found` as one of the steps that could "match," when it is by definition the fallback
    produced because none of the other three matched. Reworded to state the three discoverable
    steps did not match and name `not-found` as the resulting state, not a candidate match.
  - `[low]` `[patch]` Blind Hunter found `CfeUnresolvedError` breaks the standard exception
    pickle/deepcopy protocol: `Exception.__reduce__` reconstructs via `cls(*self.args)`, but
    `MasonError.__init__` sets `self.args = (identifier, message)` while `CfeUnresolvedError`'s
    constructor takes zero arguments, so `copy.deepcopy`/`pickle` round-tripping raises a
    confusing secondary `TypeError` instead of preserving the original error. Added
    `__reduce__` returning `(self.__class__, ())`; added a round-trip regression test.
  - `[low]` `[patch]` Blind Hunter found `test_ensure_cfe_root_never_re_resolves` monkeypatches
    `pyforge.mason.resolve.resolve_cfe_root`, a name `cfe.py` never imports today -- the classic
    patch-where-it's-used-not-where-it's-defined gap, so the test would not catch the realistic
    regression (a future `from .resolve import resolve_cfe_root` added to `cfe.py` and called
    unqualified). Replaced with a structural assertion that `cfe.py`'s own module namespace never
    binds a `resolve_cfe_root` name at all.
  - `[low]` `[patch]` Blind Hunter found the new `test_non_cfe_mason_error_in_main_still_returns_
    exit_failed` a verbatim duplicate of the pre-existing
    `test_mason_error_raised_in_main_prints_message_and_returns_exit_failed` (same monkeypatch,
    identifier, message, and assertions) -- zero new coverage. Removed the duplicate; the AC it
    was meant to cover is already proven by the pre-existing test.
  - `[low]` `[patch]` Blind Hunter found `.claude/scripts/conda-forge-expert/` duplicated as a bare
    string literal in `errors.py`'s new message with no explanatory comment, unlike the codebase's
    established convention of calling out intentional literal duplication (`_ENV_CFE_ROOT`/
    `_ENV_CFE_PYTHON`). Added a comment noting AD-2 forbids `errors.py` from importing `resolve.py`'s
    `_CFE_MARKER` (leaf-module dependency direction), so this is the same sanctioned duplication
    pattern, not an oversight.

**Rejected findings (4):** `ensure_cfe_root` never being called from a real dispatch path and the
degradation behavior for `mason recipe` not being demonstrated end-to-end (Blind Hunter) -- this is
the spec's own explicit, epics.md-grounded scope: no `recipe` verb exists yet (Epic 2 wires the real
call site), mirroring Stories 1.5/1.6's identical "not wired into cli.py" precedent; the spec's own
Acceptance Criteria says as much verbatim. A claim that no story-spec document exists for Story 1.7,
including the gitignored `implementation-artifacts/` (Blind Hunter) -- factually false:
`_bmad-output/implementation-artifacts/spec-1-7-degradation-when-cfe-is-unavailable.md` exists,
158 lines, non-empty; the reviewer evidently did not traverse the Tier-3 backlink symlink to the
physical location outside this worktree. `test_package.py`/`test_environment.py` not isolating a
"no CFE anywhere" environment before asserting import success (Blind Hunter) -- both modules are
docstring-only with zero filesystem access at import time, so the claim they're meant to prove
cannot structurally fail regardless of ambient CFE presence; isolating an environment that cannot
cause a failure is speculative complexity this story's minimal-stub scope doesn't warrant.
`ensure_cfe_root(None)` / a `resolved` lacking `.step` producing an unguarded `AttributeError`
(Edge Case Hunter) -- `ensure_cfe_root` is an internal-only helper never crossing a system boundary
(its sole future caller is Mason's own `cli.py`, always passing a real `resolve_cfe_root()` output);
adding defensive validation against a misuse mode with no realistic caller mirrors the exact kind of
speculative guard Story 1.6's own Rejected findings already ruled out for an analogous case.

## Design Notes

`ensure_cfe_root` lives in `cfe.py`, not `resolve.py`, mirroring Story 1.6's `ensure_import_floor`
split: `resolve.py`'s own docstring and every existing test treat `resolve_cfe_root` as a function
that "never raises," and the Capability -> Architecture map's "CFE seam (FR-1 - FR-6)" row already
assigns FR-5 to `cfe.py` and `resolve.py` together, not to a not-yet-existing `recipe.py`.

The AD-6 guard must NOT reuse `test_dependency_direction.py`'s `ast.walk(tree)` approach verbatim --
that walks every descendant node including inside function bodies, which is correct for AD-2's
blanket subprocess ban but wrong here: AD-6's own text permits `package.py` to import `cfe` "lazily,"
and a Epic-3 conda-forge ship target doing exactly that must not fail this story's guard. Scan only
`tree.body` (the `Module` node's direct children) instead.

`CfeUnresolvedError` takes no constructor arguments, unlike `CfeImportFloorError`: there is no
per-call variable data to report (the four steps either matched or did not; nothing about *which*
value was tried is meaningful once resolution has already failed), so a fixed message needs no
fields to build from -- the pre-computed `ResolvedCfeRoot` is only ever consulted by `ensure_cfe_root`
to decide *whether* to raise, not to parameterize the message.

## Verification

**Commands:**
- `pixi run -e pyforge-mason pyforge-mason-test` -- expected: full suite green (existing tests
  unchanged in outcome, plus every new test listed above).

## Auto Run Result

Status: done

- **Implemented change:** added `CfeUnresolvedError` (identifier `cfe:unresolved`, fixed message
  naming all four `resolve.py` step names and how to satisfy the first three) to `errors.py`;
  `ensure_cfe_root(resolved) -> None` to `cfe.py`, raising when `resolved.step == STEP_NOT_FOUND`
  without ever re-resolving; a new `except CfeUnresolvedError` branch in `cli.py`'s `main()` ahead
  of the generic `MasonError` catch, mapping to `EXIT_CFE_UNAVAILABLE` (3); and docstring-only seed
  modules `package.py`/`environment.py` plus an AST meta-test (`test_capability_tiers.py`) proving
  neither ever carries a module-level `cfe` import -- FR-5, D-2, AD-5, AD-6, AD-7.
- **Files changed:**
  - `src/shared/packages/pyforge-mason/src/pyforge/mason/errors.py` -- added `CfeUnresolvedError`,
    hardened during review with a coherent message and `__reduce__` for pickle/deepcopy safety.
  - `src/shared/packages/pyforge-mason/src/pyforge/mason/cfe.py` -- added `ensure_cfe_root`.
  - `src/shared/packages/pyforge-mason/src/pyforge/mason/cli.py` -- wired the new exception branch
    into `main()`, positioned before the existing generic `MasonError` branch.
  - `src/shared/packages/pyforge-mason/src/pyforge/mason/package.py`,
    `environment.py` (new) -- minimal seed modules, zero CFE import.
  - `src/shared/packages/pyforge-mason/tests/meta/test_capability_tiers.py` (new) -- the AD-6
    guard, hardened during review to catch dotted/absolute-form imports and imports nested inside
    top-level `try`/`if`/`with` blocks, while still permitting a genuinely lazy function-body import.
  - `tests/unit/test_errors.py`, `test_cfe.py`, `test_cli.py`, `test_package.py`,
    `test_environment.py` -- full coverage of the new error, `ensure_cfe_root`, `main()`'s new
    branch, and bare-import success, plus the review-driven regression tests listed in the triage log.
- **Review findings breakdown:** 2 independent reviewers (Blind Hunter, Edge Case Hunter, no shared
  context) surfaced 10 distinct findings after dedup -- 6 patches applied (1 medium: the AD-6
  meta-test's AST detector was bypassable via dotted-absolute imports and try/if/with-nested
  imports, now closed with 3 new regression tests; 5 low: incoherent error-message wording, a
  pickle/deepcopy protocol break, an ineffective monkeypatch-based regression test replaced with a
  structural one, a duplicate test removed, an undocumented literal duplication now commented),
  0 deferred, 4 rejected (one spec-mandated-verbatim scope claim, one factually-incorrect "no spec
  exists" claim, one speculative environment-isolation ask against code with zero filesystem access,
  one speculative internal-misuse guard with no realistic caller). See the Review Triage Log for the
  full audit trail.
- **Follow-up review recommendation:** false -- the one medium finding was confined to a brand-new,
  test-only AST detector (no production runtime behavior, security, or data-impact surface), the
  other five were low-severity localized fixes (message wording, a pickle edge case, test hygiene),
  and every patched behavior now has dedicated regression coverage (196 passing tests, up from 192
  before the review pass).
- **Verification:** `pixi run -e pyforge-mason pyforge-mason-test` -> 196 passed (full suite: 192
  after initial implementation + 4 net new tests added during the review pass, after removing 1
  duplicate).
- **Residual risks:** none identified beyond the rejected findings' explicitly out-of-scope items
  (the CFE-unavailable exit-3 path is proven at the `main()`/error-handling level only -- no
  `recipe` verb exists yet to dispatch through it for real; Epic 2 wires that call site and inherits
  this story's typed error and exit-code mapping unchanged).
