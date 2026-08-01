<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-04 -->
---
title: 'Error taxonomy and exit-code contract'
type: 'feature'
created: '2026-07-30'
status: in-review
baseline_revision: 'b9d28c704527c15c9cbdb259199f339e7ffa3dd9'
final_revision: 'a889753d71c21d95a9e49e54fa1b337075f83b78'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `cli.py` hardcodes its own exit-code constants, including `EXIT_INTERNAL = 70` for
unanticipated exceptions — contradicting AD-7/FR-33's mandated `1` — and there is no typed-error
taxonomy: an anticipated failure cannot yet be raised as anything a caller can branch on by
identifier instead of grepping message text.

**Approach:** Add `exit_codes.py` as the sole owner of the five-code contract (`0/1/2/3/130`) and
`errors.py`'s `MasonError` base class carrying a validated colon-delimited identifier. Move
`cli.py`'s exit-code constants into `exit_codes.py`, add a `MasonError` handler to `main()` ahead
of the generic exception catch, and correct the unanticipated-exception code from `70` to `1`.

## Boundaries & Constraints

**Always:** `exit_codes.py` defines exactly `EXIT_OK=0`, `EXIT_FAILED=1`, `EXIT_USAGE=2`,
`EXIT_CFE_UNAVAILABLE=3`, `EXIT_INTERRUPTED=130` — no other module defines an `EXIT_*` name (new
AST static check, mirroring `test_dependency_direction.py`'s pattern). `MasonError(identifier,
message)` validates `identifier` against `^[a-z0-9]+(-[a-z0-9]+)*:[a-z0-9]+(-[a-z0-9]+)*$` (the
architecture spine's `cfe:unresolved`/`ship:credential-missing`/`engine:absent` shape), stores
both, and `__str__` returns `"identifier: message"`. `main()`'s except-clause order stays
`KeyboardInterrupt` -> `SystemExit` -> `MasonError` -> `Exception` (`MasonError` must precede the
bare `Exception` catch, since it's a subclass). Unanticipated exceptions still print the full
traceback to stderr, now returning `EXIT_FAILED` (1). `errors.py`/`exit_codes.py` hold no
behaviour beyond the taxonomy/constants (AD-1: shared shapes, no behaviour).

**Block If:** none identified — epics.md's Story 1.3 AC plus AD-7 fully specify this work.

**Never:** Add concrete `MasonError` subclasses or raise sites for `cfe:unresolved` /
`ship:credential-missing` / `engine:absent` — those belong to the stories that implement CFE
resolution (1.5–1.7), credentials (2.3/3.4), and engines (3.1/4.1); this story ships the taxonomy
machinery only, proven via a test-injected `MasonError`. Touch `models.py` (doesn't exist; later
epics' scope). Add the AD-2 "errors/exit_codes import nothing from Mason" guard — that sub-rule is
owned by S-1.2 (done) / S-2.2 per the epic's AD ownership table, not S-1.3. Route error messages
through `render.py` — that's Story 1.4.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Anticipated failure | a `MasonError` is raised inside `main()`'s try block | `"identifier: message"` printed to stderr | exit `EXIT_FAILED` (1) |
| Malformed identifier | `MasonError("Bad Id", "msg")` | raises `ValueError` at construction | n/a |
| Unanticipated exception | a `RuntimeError` escapes | full traceback on stderr | exit `EXIT_FAILED` (1), not the old `70` |
| Rogue `EXIT_*` constant | any `.py` under `src/pyforge/mason/` other than `exit_codes.py` defines an `EXIT_*` name | new meta test fails | n/a |

</intent-contract>

## Code Map

(paths relative to `src/shared/packages/pyforge-mason/`)

- `src/pyforge/mason/exit_codes.py` (new) -- sole exit-code owner (AD-7); the 5 named constants.
- `src/pyforge/mason/errors.py` (new) -- `MasonError` taxonomy root (AD-7).
- `src/pyforge/mason/cli.py` -- drop inline `EXIT_OK`/`EXIT_USAGE`/`EXIT_INTERRUPTED`/`EXIT_INTERNAL`; import from `exit_codes`; add a `MasonError` handler; generic handler now returns `EXIT_FAILED`.
- `tests/unit/test_exit_codes.py` (new) -- pins the 5 exact values.
- `tests/unit/test_errors.py` (new) -- construction, identifier validation, `__str__`.
- `tests/unit/test_cli.py` -- import source moves to `exit_codes`; rewrite the unanticipated-exception test; add a `MasonError`-during-dispatch test.
- `tests/meta/test_exit_code_ownership.py` (new) -- AST static check, mirrors `test_dependency_direction.py`.

## Tasks & Acceptance

**Execution:**
- [x] `exit_codes.py` -- create the module: `EXIT_OK=0`, `EXIT_FAILED=1`, `EXIT_USAGE=2`, `EXIT_CFE_UNAVAILABLE=3`, `EXIT_INTERRUPTED=130`, each documented -- FR-32, AD-7.
- [x] `errors.py` -- create `MasonError(Exception)` with `identifier`/`message` attributes, regex-validated identifier (raise `ValueError` on mismatch), `__str__` -- FR-33, AD-7.
- [x] `cli.py` -- replace the inline `EXIT_*` block with `from .exit_codes import ...`; add `except MasonError as exc: print(str(exc), file=sys.stderr); return EXIT_FAILED` ahead of the generic `except Exception`; that generic handler now returns `EXIT_FAILED` -- FR-33, AD-7.
- [x] `tests/unit/test_exit_codes.py` -- assert the 5 exact integer values.
- [x] `tests/unit/test_errors.py` -- valid + invalid identifier construction, `__str__` format.
- [x] `tests/unit/test_cli.py` -- update the exit-code import source; replace `test_unexpected_exception_never_returns_bare_1` with a test asserting `rc == EXIT_FAILED` and traceback text on stderr; add a monkeypatch test (same pattern as the existing `KeyboardInterrupt`/`RuntimeError` cases) proving a `MasonError` raised during dispatch prints its message and returns `EXIT_FAILED`.
- [x] `tests/meta/test_exit_code_ownership.py` -- AST scan asserting no `.py` file under `src/pyforge/mason/` other than `exit_codes.py` defines a module-level `EXIT_*` name; `tmp_path` regression fixtures proving the detector both fires and permits the owner file, mirroring `test_dependency_direction.py`'s rigor.

**Acceptance Criteria:**
- Given `errors.py`, when an anticipated failure occurs, then a `MasonError` is raised carrying a stable colon-delimited identifier, and the message states what failed and what to do next.
- Given `exit_codes.py`, when any command terminates, then the exit code comes only from that module (`0`/`1`/`2`/`3`/`130`), and a static check confirms no other module produces one.
- Given argparse's own `SystemExit`, when `--help` or a usage error triggers it, then it surfaces as `0` or `2` respectively and never collides with a real failure code (unchanged existing behavior — regression-covered by the existing `test_version_is_reported`/`test_help_lists_the_whole_surface`/`test_bare_noun_is_a_usage_error` tests, now importing from `exit_codes`).
- Given an unanticipated exception, when it escapes a command, then the process exits `1` with the traceback on stderr, never the interpreter default.

## Spec Change Log

## Review Triage Log

### 2026-07-30 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5 (medium: 3, low: 2)
- defer: 2
- reject: 6
- addressed_findings:
  - `[medium]` `[patch]` `test_exit_code_ownership.py`'s AST scanner only recognized a bare
    `ast.Name` assignment target, so a tuple/list-unpacking assignment (e.g.
    `EXIT_ROGUE, _ = 99, None`) could define a rogue `EXIT_*` name undetected — a real hole in the
    guard this story exists to build (confirmed by direct execution). Fixed
    `_module_level_exit_names` to `ast.walk()` each target instead of type-checking it directly;
    added a regression fixture proving the tuple-unpacking case is now caught.
  - `[medium]` `[patch]` `MasonError.__init__` accepted an empty `message`, producing a truncated
    `"identifier: "` diagnostic that contradicts the class's own "states what failed and what to
    do next" contract (NFR-14). Added a non-empty-message check raising `ValueError`; added a
    regression test.
  - `[medium]` `[patch]` `MasonError(None, "msg")` (a non-`str` identifier) raised a raw
    `TypeError` from the regex engine instead of the documented `ValueError`. Added an
    `isinstance` check ahead of the regex match; added a regression test.
  - `[low]` `[patch]` The identifier regex anchored with `$`, which in Python also matches just
    before a single trailing newline, letting a malformed identifier like `"cfe:unresolved\n"`
    pass validation. Changed the anchor to `\Z`; added a regression case.
  - `[low]` `[patch]` `test_mason_error_during_dispatch_prints_message_and_returns_exit_failed`'s
    name implied it exercised noun/verb dispatch, which doesn't exist yet this story (it
    monkeypatches `build_parser`, the same pattern as the `KeyboardInterrupt`/`RuntimeError`
    tests). Renamed to `test_mason_error_raised_in_main_prints_message_and_returns_exit_failed`
    and clarified the docstring.

**Deferred findings (2 — pre-existing, not caused by this story, logged to
`{implementation_artifacts}/deferred-work.md`):** `cli.py`'s stderr writes (old and new) are
unguarded against `OSError`/`BrokenPipeError` — a whole-file pass, not a one-off fix to the new
`MasonError` handler alone. `test_exit_code_ownership.py`'s `_find_rogue_exit_code_owners` calls
`path.resolve()` before its `try`/`except OSError` guard, identically to the pre-existing
`test_dependency_direction.py` pattern it deliberately mirrors — fixing only the new file would be
inconsistent with its sibling.

**Rejected findings (6 — out of this story's scope, already addressed elsewhere in the diff, or
not actually ambiguous; dropped silently per instructions, listed here only for this pass's audit
trail):** `MasonError` lacking a per-instance/subclass exit-code hook for a future CFE-unavailable
(exit `3`) vs. everything-else (exit `1`) distinction — explicitly Story 1.7's job per this spec's
`Never` boundary and Design Notes, not a defect in this story's delivered scope. Duplicated
AST-scanning boilerplate between `test_dependency_direction.py` and the new
`test_exit_code_ownership.py` — deliberate mirroring per the spec's own Code Map instruction, and
premature to extract a shared helper for two call sites. The new `MasonError` handler printing via
a plain `print()` rather than through `render.py` — explicitly out of scope per this spec's `Never`
boundary ("that's Story 1.4"). The claim that `test_exit_code_ownership.py`'s "mirrors
`test_dependency_direction.py`" docstring is overstated — the approach (AST-based, resolved-path
comparison, `tmp_path` regression fixtures, clean-`AssertionError` failure handling) is
substantively identical; the tuple-unpacking gap this pass patched only makes the claim more true.
The `EXIT_INTERNAL=70 -> EXIT_FAILED=1` behavior change being "undocumented" — it is stated in the
spec's Intent/Design Notes and in `exit_codes.py`'s own `EXIT_FAILED` docstring. The identifier
regex's one-colon (two-segment) shape being an "unstated cap" — it is the exact regex given
verbatim in this spec's `Boundaries & Constraints`, and matches every example
(`cfe:unresolved`/`ship:credential-missing`/`engine:absent`) in the architecture spine.

### 2026-07-30 — Review pass (follow-up, fresh pass on the done spec)
- intent_gap: 0
- bad_spec: 0
- patch: 6 (medium 1, low 5)
- defer: 0
- reject: 9
- addressed_findings:
  - `[medium]` `[patch]` The AD-7 ownership scanner iterated only `tree.body` for
    `Assign`/`AnnAssign`, so every nested or indirect module-level binding escaped it:
    `if sys.platform == "win32": EXIT_WIN = 75` (the most realistic drift vector), walrus
    (`EXIT_W := 9`), bindings inside module-level `try`/`for`/`while`/`with`, `except ... as`,
    `AugAssign`, `def`/`class` names, and `import ... as EXIT_X` (empirically probed by the
    reviewer: six escape vectors, zero detections). Rewrote `_module_level_exit_names` as a
    recursive statement walk that skips function/class/lambda scopes, recognizes every
    `Name`-Store binding plus except-as/def/class/import-alias forms, and exempts exactly one
    sanctioned binding — un-renamed `from <...>.exit_codes import EXIT_X` consumption (which the
    real `cli.py` depends on). Added 15 regression fixture params (13 escape vectors that must be
    flagged + the canonical-import and scope-exclusion cases that must not).
  - `[low]` `[patch]` `MasonError("cfe:unresolved", "   ")` passed the prior pass's
    non-empty-message check and produced the same truncated diagnostic the check exists to
    prevent (NFR-14). Tightened to `isinstance(str)` + `.strip()`; whitespace-only now raises
    `ValueError`; parametrized regression tests added.
  - `[low]` `[patch]` `message` was not type-validated while `identifier` was (the prior pass's
    asymmetry): `MasonError("cfe:unresolved", 123)` was accepted and stored an int. Same
    `isinstance` guard now covers it; regression test added.
  - `[low]` `[patch]` Three new-in-this-story doc surfaces overclaimed the contract the adjacent
    code keeps: `exit_codes.py`'s module docstring said `main()` returns "exclusively" the five
    names (the pre-existing, spec-pinned `SystemExit` passthrough forwards argparse's own integer
    codes verbatim), `EXIT_USAGE`'s docstring omitted the non-int-`SystemExit` fallback path that
    also produces it, and `cli.py`'s header comment said "the five possible codes … only imports
    the names it uses" (it imports four, and the passthrough exists). All three reworded to state
    the actual behavior; no runtime change (the passthrough itself is Story-1.2 behavior the AC
    pins as "unchanged existing").
  - `[low]` `[patch]` The `MasonError`-projection test pinned `cfe:unresolved` -> `EXIT_FAILED`
    (1) — the one identifier family Story 1.7 will map to `EXIT_CFE_UNAVAILABLE` (3), guaranteeing
    that exact test breaks later. Switched the fixture to a synthetic `test:injected-failure`
    identifier and documented why in the test docstring.
  - `[low]` `[patch]` `test_cli.py`'s module docstring still labeled the file "Story 1.2" after
    this story rewrote its imports and added two 1.3 tests. Updated to cover both stories.

**Deferred findings (0 new):** the two reviewer-resurfaced residuals (unguarded stderr writes in
`cli.py`; `path.resolve()` ahead of the `OSError` guard in the meta test) are the exact two
entries this spec's first pass already logged to `{implementation_artifacts}/deferred-work.md` —
per the orchestrator's instruction the ledger takes new entries only, so nothing was appended.

**Rejected findings (9 — dropped silently per instructions, listed only for this pass's audit
trail):** the claim that the static check under-delivers the AC's "no other module produces an
exit code" (the spec's `Always` clause defines the check precisely as `EXIT_*`-name ownership via
AST — call/raise/return-flow analysis is beyond the contracted scope). The `SystemExit`
passthrough behavior itself (spec AC pins argparse `SystemExit` handling as "unchanged existing
behavior"; only its documentation was corrected). `MasonError`/`EXIT_*` not re-exported from the
package `__init__` (not in this spec's Code Map; the package's public import surface belongs to
later stories). The guard scanning only `src/pyforge/mason/` (matches the spec's edge-case matrix
verbatim). The `EXIT_FAILED` docstring's `EXIT_INTERNAL`-history note being "changelog narrative"
(deliberate — the prior pass's rejection of the "undocumented behavior change" finding cites that
very docstring). The identifier regex accepting all-digit segments like `0:0` (the regex is
spec-verbatim; identifiers-are-API makes unilateral tightening a contract deviation). Mapping
`cfe:*` to exit 3 now / `EXIT_CFE_UNAVAILABLE` unreachable (explicitly Story 1.7 per the `Never`
boundary; already adjudicated by the first pass). JSON-format-aware error rendering (explicitly
Story 1.4 per the `Never` boundary). The two already-deferred residuals re-surfaced by the
reviewers (already in the ledger; see above).

## Design Notes

No concrete `MasonError` raise site exists yet — no recipe/ship/engine logic lands until Epics
2–4. This mirrors Story 1.2's "vacuous but real" pattern for the AD-2 subprocess guard: the
taxonomy and `main()` wiring are pinned now via a monkeypatch-injected `MasonError` in tests, and
later stories raise real instances without touching `main()` again. `EXIT_CFE_UNAVAILABLE` is
defined but unused until Story 1.7 wires actual CFE-unavailable detection — this story only
guarantees the constant exists with the right value. `EXIT_FAILED` replaces the current
EX_SOFTWARE-derived `EXIT_INTERNAL = 70`, which predates and contradicts AD-7/FR-33's mandated
`1` — Story 1.2's own spec flagged this as a pre-existing discrepancy explicitly deferred here.

## Verification

**Commands:**
- `pixi run -e pyforge-mason pyforge-mason-test` -- expected: full suite green (existing + new tests).

