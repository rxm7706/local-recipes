---
title: 'Story 2.5: mason recipe validate'
type: 'feature'
created: '2026-08-13'
status: 'done'
baseline_revision: '4a7b049904ec0a289681eff68d73cab2a4f931ce'
final_revision: '4edeb666fceadd614836a1802085d5ff139cf7a5'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: []
---

<intent-contract>

## Intent

**Problem:** `mason recipe` has no `validate` verb yet -- a user cannot check a recipe against
conda-forge policy before burning CI time on a build, even though `cfe.py`'s `validate_recipe`
adapter (Story 2.1's `_CFE_SCRIPTS` table) already exists and is unused.

**Approach:** Add `recipe.py::validate()`, mirroring `diagnose()`'s composition shape exactly (no
import-floor gate: the wrapped validator's only third-party import, PyYAML, already degrades to an
honest failure on its own), and wire `mason recipe validate <recipe_path>` in `cli.py`. Unlike
every sibling verb, this verb's own process exit code reflects the wrapped validator's pass/fail
outcome (FR-8) -- `cli.py`'s dispatch branch alone makes this projection.

## Boundaries & Constraints

**Always:** `validate()` composes `resolve_cfe_root` -> `cfe.ensure_cfe_root` -> `resolve_cfe_interpreter`
-> `cfe.validate_recipe`, exactly like `diagnose()`. `recipe_path` passes through with no existence
check or interpretation (AD-1). Args are `["--json", recipe_path]` (mirrors `scan()`'s own
`--json` forcing) -- without it the wrapped script prints human text, leaving `CfeResult.json_body`
empty. `validate()` returns the raw `CfeResult` verbatim (spec Never boundary, like
`diagnose()`/`optimize()`/`scan()`/`update()`) -- no reinterpretation, no new dataclass, so CFE's
identifiers are preserved verbatim in the rendered output. Only `cli.py`'s `recipe validate`
dispatch branch projects `CfeResult.returncode` onto the process exit code (`EXIT_OK` when zero,
else `EXIT_FAILED`) -- the one verb where this happens; every sibling verb always reports
`EXIT_OK` regardless of the wrapped tool's own outcome. This does not violate AD-4 ("a non-zero
return code is data, not an exception") -- that rule binds `recipe.py`/`cfe.py`, which still never
raise for a validation failure; the projection is `cli.py`'s own dispatch-time decision, the layer
AD-7 already assigns exit-code ownership to. The JSON envelope's `status` field stays `"ok"`
regardless of the recipe's pass/fail outcome (mirrors every sibling verb) -- only the process exit
code carries the validation-outcome signal.

**Block If:** N/A -- FR-8 plus the `diagnose()`/`scan()` precedents fully determine the scope.

**Never:** No Mason-side severity policy, filtering, renumbering, or re-wording of CFE's findings
(AD-1). No `--strict`/warnings-as-errors flag on Mason's own CLI (out of AC scope; a user wanting
that invokes CFE's validator directly). No import-floor probe/gate (mirrors `diagnose()`'s
exemption, not `optimize()`/`scan()`'s scoped-probe pattern).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Recipe validates cleanly | CFE's validator reports `passed: true` | Process exits `0`; findings in `data.json_body` | N/A |
| Recipe has validation errors | CFE's validator reports `passed: false` with `errors` | Process exits non-zero (`EXIT_FAILED`); `data.json_body.errors` holds CFE's messages verbatim | N/A |
| `--format json` | `--format json` flag given | `data` = `dataclasses.asdict(CfeResult)` incl. parsed `json_body`; `status` stays `"ok"` regardless of pass/fail | N/A |
| CFE root unresolved | no `--cfe-root`/`MASON_CFE_ROOT`/discoverable marker | `CfeUnresolvedError` raised before any subprocess spawns | `EXIT_CFE_UNAVAILABLE`, message on stderr |
| CFE subprocess exceeds its timeout | `--cfe-timeout` elapses before completion | `CfeTimeoutError` propagates from `cfe.validate_recipe` | `EXIT_FAILED`, message on stderr, no orphaned process |

</intent-contract>

## Code Map

(paths relative to `src/shared/packages/pyforge-mason/`)

- `src/pyforge/mason/recipe.py` -- add `validate()` in epic-canonical position (between `new()` and
  `build()`); mirrors `diagnose()`'s composition shape; add its module-docstring paragraph in the
  same position. No `cfe.py` change needed -- Story 2.1 already added the `validate_recipe` adapter.
- `src/pyforge/mason/cli.py` -- register the `recipe validate <recipe_path>` verb parser (epic-canonical
  position, between `new_parser` and `recipe_build_parser`); add its dispatch branch in the same
  position, projecting `result.returncode` onto `EXIT_OK`/`EXIT_FAILED`; update the "Unreachable now
  for every verb-noun pair except..." comment's verb list and count (seven -> eight).
- `src/pyforge/mason/exit_codes.py` -- one-line addition to `EXIT_FAILED`'s docstring noting this
  new call site (mirrors `EXIT_CFE_UNAVAILABLE`'s "first produced by Story X" style).
- `tests/unit/test_recipe.py` -- `validate()`'s test block, epic-canonical position between `new()`'s
  and `build()`'s blocks.
- `tests/unit/test_cli.py` -- `recipe validate`'s test block, epic-canonical position between `new`'s
  and `diagnose`'s blocks; update the existing verb-metavar regression test's expected string.

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/mason/recipe.py` -- add `validate()` (resolve root -> `ensure_cfe_root` -> resolve
  interpreter -> `cfe.validate_recipe(["--json", recipe_path], ...)`, no import-floor gate, returns
  `CfeResult` verbatim) + docstring paragraph -- FR-8.
- [x] `src/pyforge/mason/cli.py` -- register `validate_parser` (single `recipe_path` positional,
  `parents=[global_flags]`); add the `recipe`/`validate` dispatch branch calling `recipe.validate(...)`,
  rendering via `render.write(..., "ok", dataclasses.asdict(result), [])`, then returning `EXIT_OK`
  if `result.returncode == 0` else `EXIT_FAILED`; update the unreachable-branch comment -- FR-8.
- [x] `src/pyforge/mason/exit_codes.py` -- extend `EXIT_FAILED`'s docstring with this new origin.
- [x] `tests/unit/test_recipe.py` -- `validate()` composition tests (args incl. `--json`, timeout
  forwarding, verbatim `CfeResult` return, no `ensure_import_floor` call), `CfeUnresolvedError`
  propagation (mocked and real unresolved-root, subprocess-never-spawns), and two real-fixture
  round trips against `fake_cfe_root` (a passing canned result and a failing one via
  `MASON_FIXTURE_STDOUT`/`MASON_FIXTURE_EXIT_CODE`) -- FR-8.
- [x] `tests/unit/test_cli.py` -- `recipe validate` dispatch tests (`--help`, required positional,
  text/JSON rendering, flags/environ/cwd passthrough, `--cfe-timeout` resolution,
  `CfeUnresolvedError` -> `EXIT_CFE_UNAVAILABLE`, `CfeTimeoutError` -> `EXIT_FAILED`), the
  differentiating pair (passing canned result -> `EXIT_OK`; failing canned result -> `EXIT_FAILED`
  while `status` stays `"ok"`), and the verb-metavar regression test update -- FR-8.

**Acceptance Criteria:**
- Given a recipe with validation failures, when `mason recipe validate` runs, then the process exit
  code is non-zero.
- Given a recipe that validates cleanly, when `mason recipe validate` runs, then the process exit
  code is `0`.
- Given validation findings, when they are rendered, then CFE's identifiers are preserved verbatim
  -- never renumbered, reworded, or re-severitied.
- Given `--format json`, when validation runs, then findings appear in the `data` field of the
  FR-31 envelope.
- Given the CFE root cannot be resolved, when `mason recipe validate` runs, then it exits
  `EXIT_CFE_UNAVAILABLE` with no subprocess spawned.

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1 (medium: 1)
- defer: 4 (medium: 2, low: 2)
- reject: 6
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter found every failing-`CfeResult` assertion in `test_cli.py`/`test_recipe.py` forced `--format json`, leaving `recipe validate`'s default text-mode rendering of a failing result untested -- added `test_recipe_validate_failing_cfe_result_text_mode_still_renders_ok_and_exits_failed` asserting `EXIT_FAILED` plus the rendered text body, with no JSON flag. Suite now 992 passed (was 991).



The exit-code projection is the one non-obvious decision here: every sibling verb
(`build`/`diagnose`/`optimize`/`scan`/`submit`/`update`) always returns `EXIT_OK` from `cli.py`
regardless of the wrapped tool's own outcome ("the gap is data," `doctor`'s established precedent).
FR-8 explicitly breaks that pattern for `validate` alone -- it exists so `mason recipe validate`
composes as a CI/shell gate (PRD: "catch problems before a build burns CI time"), which requires a
real process exit code, not just JSON data a caller must parse. This is scoped to `cli.py`'s
dispatch branch only; `recipe.py::validate()` itself still returns data, never raises, for a
validation failure -- identical to every sibling verb and to AD-4's rule.

## Verification

**Commands:**
- `pixi run -e pyforge-mason pyforge-mason-test` -- expected: full suite green, all new tests
  included, none marked `slow`.

## Auto Run Result

**Status:** done

**Summary:** Added `mason recipe validate <recipe_path>` (FR-8), the fifth `recipe` verb in the
repo's story order but landed after `build`/`diagnose`/`optimize`/`scan`/`submit`/`update` already
shipped, inserted at its epic-canonical position (between `new` and `build`) in every file. Mirrors
`diagnose()`'s composition shape (resolve root -> `ensure_cfe_root` -> resolve interpreter -> call
the CFE port), no import-floor gate, `["--json", recipe_path]` args mirroring `scan()`'s own
`--json` forcing. The one behavioral departure from every sibling verb: `cli.py`'s `recipe validate`
dispatch branch alone projects `CfeResult.returncode` onto the process exit code (`EXIT_OK`/
`EXIT_FAILED`) instead of always reporting `EXIT_OK`, so the command composes as a CI/shell gate,
while the JSON envelope's `status` field still always reads `"ok"`.

**Files changed:**
- `src/pyforge/mason/recipe.py` -- new `validate()` + module-docstring paragraph.
- `src/pyforge/mason/cli.py` -- `validate_parser` registration, `_RECIPE_VALIDATE_HELP`, the
  `recipe`/`validate` dispatch branch (the exit-code projection), unreachable-branch comment update.
- `src/pyforge/mason/exit_codes.py` -- `EXIT_FAILED` docstring extended with this new origin.
- `tests/unit/test_recipe.py` -- 12 new `validate()` unit tests.
- `tests/unit/test_cli.py` -- 18 new `recipe validate` dispatch tests (17 from implementation + 1
  review-pass patch) + the verb-metavar regression test updated.

**Review findings breakdown:** 1 patch applied (failing-result text-mode rendering was untested --
fixed, suite 991 -> 992 passed); 4 deferred to the ledger (`DW-2-5-1`..`DW-2-5-4`: `EXIT_FAILED`
conflates two outcome kinds -- an AD-7 taxonomy question, not this story's to decide alone;
hand-maintained verb-ordinal comments have no mechanical guard -- pre-existing pattern; no test
sweeps every sibling verb to structurally prove the "always EXIT_OK" invariant this story's
docstrings lean on; a leading-`-` `recipe_path` could be misparsed by CFE's own `argparse`, an
exposure inherited unchanged from `scan()`'s identical Story 2.8 precedent); 6 rejected (extensive
docstring rationale duplication across files -- matches every sibling verb's established style;
`_RECIPE_VALIDATE_HELP`'s density -- matches `scan`/`submit`'s own parenthetical-caveat style; no
`--strict` flag -- the spec's own Never boundary deliberately excluded it; duplicated hand-written
JSON fixture payloads -- matches every existing `_FIXED_*_RESULT` fixture in the file; no bad-path
end-to-end test -- the fixture stub ignores argv content entirely, so it would test nothing new; no
flag-passthrough test on the failing-result path -- passthrough assertions are orthogonal to the
mocked return value's content).

**Verification:** `pixi run -e pyforge-mason pyforge-mason-test` -- **992 passed**, 0 failed, no new
test marked `slow`. `git diff --stat` confirms exactly the five intended files changed.

**Residual risks:** None blocking. The four deferred items are genuine but pre-existing or
architecture-scoped (see breakdown above) -- none is a regression or a gap this story introduced in
isolation.
