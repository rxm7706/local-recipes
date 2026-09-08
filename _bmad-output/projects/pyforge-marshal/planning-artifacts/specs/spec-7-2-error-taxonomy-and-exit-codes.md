---
title: 'Story 7.2: Error taxonomy and exit codes'
type: 'feature'
created: '2026-08-13'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '55c0e5eb218df2a086277cf2b4070f536f43a6c9'
final_revision: 'c592cb0794'
context:
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** No module under `pyforge.marshal.seed` has a shared exception taxonomy or exit-code
mapping yet, but Story 7.3 (`seed/fs.py`'s `NeverWriteViolation`) is blocked on exactly this
(architecture: "`fs` imports nothing from the package except `errors`"), and FR-126 requires a
closed hierarchy mapped to distinct exit codes rather than each module minting its own ad-hoc
exception shape.

**Approach:** Add `seed/errors.py`: a `SeedError` root (mixing in this repo's shared
`PyforgeError`, Story 14.3 convention) carrying a `message` and a required `remedy` string, plus
six leaf subclasses each pinning one `exit_code` class attribute per the epics AC's table. A unit
test enumerates `SeedError.__subclasses__()` and asserts the six-member exit-code set is exactly
right, so a future subclass added without an `exit_code` fails the build. A `tests/meta/` AST scan
asserts no module under `seed/` raises a bare `Exception` or `SystemExit`.

## Boundaries & Constraints

**Always:**
- `SeedError(PyforgeError, Exception)` is the taxonomy root: `__init__(self, message: str, *,
  remedy: str) -> None`, both required non-blank strings (raises `ValueError` — a locally
  constructed value, not a `SeedError` itself — for either being missing/blank, matching
  `MasonError`'s existing "construction-time validation" convention in this codebase).
- Exactly six leaf subclasses, one per non-success outcome in the epics AC's table, each pinning a
  `ClassVar[int]` `exit_code` and nothing else (no added fields, no overridden `__init__`):
  `ConformanceFailure` (1), `UsageError` (2), `PreconditionFailure` (3), `NeverWriteViolation`
  (4), `StateInvalid` (5), `InternalError` (10). `0` (success) is not an exception and has no
  class.
- `seed/errors.py` imports nothing from `pyforge.marshal` except (transitively, via
  `pyforge.core.errors`) — i.e. it imports `PyforgeError` from `pyforge.core.errors` and nothing
  else from any `pyforge.marshal.*` module (architecture: "No upward imports. `fs` imports
  nothing from the package except `errors`" — `errors` itself is the floor of that chain and
  must not create a cycle back into anything it will be imported by).
- The unit test enumerates `SeedError.__subclasses__()` directly (no separate registry) and
  asserts: exactly six classes, each has an `exit_code` `int` attribute, and the collected set of
  `exit_code` values equals `{1, 2, 3, 4, 5, 10}` with no duplicates — so adding a seventh
  subclass without setting `exit_code` raises `AttributeError` inside the test and adding one that
  reuses an existing code fails the set-equality/duplicate assertion.
- The `tests/meta/` guard walks every `.py` file under
  `src/pyforge/marshal/seed/` with `ast.parse` + `ast.walk`, flags any `Raise` node whose
  exception expression is a bare `Exception(...)`/`Exception` call/name or any `SystemExit`
  usage, and asserts the flagged set is empty (mirrors this package's existing AST-meta-test style
  — `tests/meta/test_ad3_ad4_import_linter.py`, `test_ad26_seed_field_access_guard.py`).

**Block If:** None — the epics AC's table, the architecture's import-direction rule, and this
repo's own `PyforgeError`/`MasonError` precedent fully specify the shape; no decision here
requires human input.

**Never:**
- No concrete raise site for any of the six leaves — the modules that actually detect a
  conformance failure, a bad CLI argument, a dirty worktree, etc. are later stories (`verbs/`,
  `cli/seed.py`); this story only pins the taxonomy machinery, exactly as Story 7.4 pinned
  `ManifestError` without wiring it to this taxonomy yet.
- No `cli/main.py` or `cli/seed.py` exit-code dispatch (mapping a caught `SeedError` to
  `sys.exit(exc.exit_code)`) — that CLI-integration wiring is a future verb/CLI story's surface,
  not this one's (`seed/errors.py` has no CLI dependency).
- No changes to `pyforge.core.errors` (`PyforgeError` itself) or to any existing
  `pyforge.marshal.seed.*` module's own local exception class (`MarkerError`, `RegionParseError`,
  `ManifestError`) — none of them adopt `SeedError` in this story; that re-parenting, if ever
  done, is separate follow-up work outside this story's Surface.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Valid construction | `NeverWriteViolation("blocked", remedy="loosen the never-write set")` | instance with `.exit_code == 4`, `str(exc)` containing the message | No error |
| Blank message | `UsageError("", remedy="fix the flag")` | -- | `ValueError` |
| Blank remedy | `UsageError("bad flag", remedy="   ")` | -- | `ValueError` |
| Hierarchy enumeration | `SeedError.__subclasses__()` | exactly 6 classes, `exit_code` set `== {1,2,3,4,5,10}` | No error |
| Bare `Exception`/`SystemExit` raised anywhere under `seed/` | AST scan of every `seed/**/*.py` | empty flagged set | Test failure if non-empty |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/errors.py` -- NEW, this story's
  Surface: `SeedError` and the six leaf exception classes.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_errors.py` -- NEW, covers the I/O
  Matrix's construction/validation rows plus the hierarchy-enumeration assertion.
- `src/shared/packages/pyforge-marshal/tests/meta/test_seed_no_bare_exception.py` -- NEW, the AST
  bare-`Exception`/`SystemExit` guard.

## Tasks & Acceptance

**Execution:**
- [x] `seed/errors.py` -- add `SeedError(PyforgeError, Exception)` with `message`/`remedy`
  validation in `__init__` -- the taxonomy root every leaf inherits
- [x] same file -- add the six leaf classes (`ConformanceFailure=1`, `UsageError=2`,
  `PreconditionFailure=3`, `NeverWriteViolation=4`, `StateInvalid=5`, `InternalError=10`), each a
  one-line `class X(SeedError): exit_code = N` -- the closed, exit-code-mapped hierarchy FR-126
  requires
- [x] `tests/unit/test_seed_errors.py` -- cover every I/O Matrix row, including the
  `__subclasses__()` enumeration asserting the exact six-member `exit_code` set
- [x] `tests/meta/test_seed_no_bare_exception.py` -- AST-walk every file under `seed/`, assert no
  bare `Exception`/`SystemExit` raise site

**Acceptance Criteria:**
- Given `pyforge.marshal.seed.errors`, when any of the six leaf classes is constructed with a
  non-blank message and a non-blank remedy, then the instance carries `.exit_code` (the value the
  epics AC's table pins for that class) and `.remedy`.
- Given a blank or missing `message`/`remedy`, when a `SeedError` subclass is constructed, then it
  raises `ValueError`.
- Given `SeedError.__subclasses__()`, when a test enumerates it, then it finds exactly six classes
  whose `exit_code` values are exactly `{1, 2, 3, 4, 5, 10}` with no duplicates.
- Given every `.py` file under `src/pyforge/marshal/seed/`, when the AST meta-test scans it, then
  no file raises a bare `Exception` or `SystemExit`.

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 1, medium 1, low 4)
- defer: 0
- reject: 6
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (independently): every `SeedError`
    leaf crashed on `pickle`/`copy.deepcopy` -- `remedy`'s keyword-only constructor breaks
    `Exception.__reduce__`'s default `cls(*self.args)` reconstruction. Confirmed by direct
    execution before fixing (`TypeError: SeedError.__init__() takes 2 positional arguments
    but 3 were given`), and this diff's own docstring cited `CfeUnresolvedError`/
    `CfeTimeoutError` as precedent for exactly this failure mode without applying the
    lesson. Added `SeedError.__reduce__` returning a module-level `_reconstruct_seed_error`
    reconstructor (one override on the shared base covers all six leaves, since they share
    an identical signature) plus parametrized `test_survives_deepcopy`/
    `test_survives_pickle_round_trip` across all six leaves.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independently): the
    closed-hierarchy test read `SeedError.__subclasses__()` directly, a process-wide,
    mutable registry -- any other test module defining a `SeedError` subclass elsewhere in
    the suite would silently pollute the six-member count. Added `_taxonomy_leaves()`,
    filtering by `__module__ == SeedError.__module__`, and routed both hierarchy tests
    through it.
  - `[low]` `[patch]` Blind Hunter: `isinstance(leaf.exit_code, int)` passes for `bool`
    (a `Python` `int` subclass), so an accidental `exit_code = True` would silently collide
    with real code `1`. Changed to `type(leaf.exit_code) is int`.
  - `[low]` `[patch]` Blind Hunter: the module docstring attributed the closed six-member
    hierarchy to FR-126 verbatim (FR-126 itself only requires exit codes "distinct and
    documented per failure mode") and cited AD-61's own prose for the `fs`-imports-only-
    `errors` sentence, which actually lives in the architecture's separate Module
    Dependency Rules list. Reworded both citations to point at their real source.
  - `[low]` `[patch]` Blind Hunter: `SeedError`'s docstring claimed it is "never raised
    directly," contradicted by this story's own tests (`test_seed_error_is_raisable`,
    `test_seed_error_itself_validates_blank_message_and_remedy`), which raise it directly
    on purpose. Reworded to state direct instantiation is permitted, not enforced.
  - `[low]` `[patch]` Blind Hunter: `class SeedError(PyforgeError, Exception)` repeats
    `Exception` unexplained, an unflagged deviation from the cited `MasonError` precedent
    (which declares only `(PyforgeError)`). Verified against
    `adapters/fs_local.py::FsError`, an existing class in this SAME package using the
    identical `(PyforgeError, Exception)` shape with an explanatory comment ("`Exception`
    stays in the MRO") -- added the matching comment here rather than dropping the base,
    since the double-base is the correct, established local convention.
  - `[reject]` Blind Hunter: the epics AC's "no module raises a bare `Exception`/
    `SystemExit` outside `cli.py`" names a file (`cli.py`) that isn't `cli/seed.py`'s
    actual path and sits outside `seed/` entirely. True, but purely informational for
    whichever future story adds CLI-level scanning -- no code or spec change in
    `seed/errors.py` follows from it.
  - `[reject]` Blind Hunter: blank-message/blank-remedy validation is only tested via
    `UsageError` and the base `SeedError`, not parametrized across all six leaves. All six
    leaves share `SeedError.__init__` verbatim with zero overrides, so a per-leaf
    parametrization would re-test Python's own inheritance mechanism, not this module's
    logic -- the same class of reject this epic's own Story 8.2 review already established
    for "would test the stdlib, not this module."
  - `[reject]` Blind Hunter + Edge Case Hunter (independently): the AST bare-exception
    guard does not detect a qualified (`builtins.Exception`) or aliased-import raise. Real,
    but the guard's own docstring already documents it as a best-effort STATIC check with
    stated bounds, mirroring this package's existing `test_ad23_inline_key_format_guard.py`
    /`test_ad26_seed_field_access_guard.py` guards, which carry the identical class of
    documented gap rather than exhaustive evasion-proofing.
  - `[reject]` Blind Hunter: `seed/model/manifest.py`'s already-landed `ManifestError`
    (Story 7.4) is a sibling family root, not a `SeedError` subclass, so it already bypasses
    the "closed taxonomy" this story establishes, with no forcing function to ever
    reconcile the two shapes. Real, but explicitly out of this story's Never boundary ("No
    changes to ... any existing `pyforge.marshal.seed.*` module's own local exception
    class") -- Story 7.4 pinned `ManifestError` under the identical "wire it to the shared
    taxonomy later" deferral this story's own docstring cites as precedent.
  - `[reject]` Edge Case Hunter: a zero-width/non-standard whitespace `message`/`remedy`
    (e.g. U+200B) passes the blank check. Real but disproportionate: both fields are always
    literal string constants at every call site in this codebase (never user input), so
    there is no plausible path to an adversarial zero-width string reaching this
    constructor.
  - `[reject]` Edge Case Hunter: add a `TypeError` guard forbidding direct `SeedError(...)`
    instantiation. Rejected as contradicting this story's own deliberate test design
    (`test_seed_error_is_raisable`, `test_seed_error_itself_validates_blank_message_and_remedy`
    both raise it directly on purpose) -- the underlying docstring inconsistency this
    finding also points at was already resolved by rewording the docstring (see the
    "never raised directly" patch above) rather than adding enforcement.

## Design Notes

**Why six flat leaves, not a deeper hierarchy.** The epics AC names exactly six exit codes (1,
2, 3, 4, 5, 10) with no sub-categorization, and "exactly one exception type from a closed
hierarchy is raised" reads most naturally as one flat layer under the root — a deeper hierarchy
would let a caller catch an intermediate class covering more than one exit code, which is the
ambiguity "exactly one exception type ... mapped to a distinct exit code" exists to rule out.

**Why `remedy` is required at construction, not optional.** NFR-M3 ("remedy per finding") and the
epics AC ("every exception carries a remedy string") both read as an invariant of the type, not a
per-call convenience — matching `MasonError`'s existing precedent of validating its own required
fields (`identifier`, `message`) at `__init__` time rather than leaving them optional.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expect all tests pass, including
  the two new test files.
- `pixi run -e local-recipes ruff check src/shared/packages/pyforge-marshal` -- expect no new
  finding categories.
- `pixi run -e local-recipes pyright src/shared/packages/pyforge-marshal` -- expect no growth
  beyond the existing accepted baseline.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`
  -- expect all contracts pass.

## Auto Run Result

Status: done

Summary: implemented `seed/errors.py` -- the closed, six-member `seed` exit-code taxonomy
(`SeedError` root + `ConformanceFailure`/`UsageError`/`PreconditionFailure`/
`NeverWriteViolation`/`StateInvalid`/`InternalError`, exit codes 1/2/3/4/5/10), each requiring a
non-blank `message` and `remedy` at construction. One review pass (parallel Blind Hunter + Edge
Case Hunter) found a real high-severity pickle/deepcopy crash bug plus five lower-severity
issues, all fixed in this same pass.

Files changed:
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/errors.py` -- new: `SeedError`,
  six leaf classes, `_reconstruct_seed_error` (review-driven `__reduce__` fix), plus two
  citation/wording docstring corrections.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_errors.py` -- new: construction,
  validation, hierarchy-enumeration (via a review-driven `_taxonomy_leaves()` module filter),
  and pickle/deepcopy round-trip tests (review-driven, parametrized across all six leaves).
- `src/shared/packages/pyforge-marshal/tests/meta/test_seed_no_bare_exception.py` -- new: AST
  scan asserting no bare `Exception`/`SystemExit` raise site under `seed/`.

Review findings breakdown: 6 patch (1 high, 1 medium, 4 low -- all applied), 0 defer, 6 reject
(all independently verified as either out of this story's Never boundary, already-established
project precedent for a documented best-effort guard's bounds, disproportionate for
compile-time-constant string arguments, or resolved via a docstring reword rather than the
reviewer's suggested runtime enforcement). See Review Triage Log above for full reasoning.

Follow-up review recommended: **false**. The high-severity fix (`__reduce__`) is a single,
well-isolated method addition with full round-trip test coverage (12 new parametrized tests)
proving correctness; the other five patches are docstring rewording or a test-only filter change
-- none touch the construction-time validation logic itself, which was already fully tested
before this review pass.

Verification performed:
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 3735 passed, 9 deselected (42 in
  `test_seed_errors.py`, up from the pre-review-pass 28; plus the meta test file).
- `pixi run -e local-recipes ruff check` scoped to all three new/changed files -- `All checks
  passed!`.
- `pixi run -e local-recipes pyright` scoped to `seed/errors.py` -- `0 errors, 0 warnings, 0
  informations`.
- `pixi run --frozen -e pyforge-marshal lint-imports --config .../pyproject.toml --no-cache` --
  `Contracts: 3 kept, 0 broken`.
- The pickle/deepcopy bug reproduced by direct execution before the fix
  (`TypeError: SeedError.__init__() takes 2 positional arguments but 3 were given`) and
  confirmed absent after, via both the ad hoc repro and the new parametrized test suite.

Residual risks: none blocking. The six rejected findings are recorded above with their reasoning
in case a future story's real-world usage proves one wrong (in particular, if `seed/verbs/` or
`cli/seed.py` ever re-parents `ManifestError` onto `SeedError`, that reconciliation should also
audit whether `MarkerError`/`RegionParseError`/`FsError` follow).
