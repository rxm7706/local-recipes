---
title: 'Story 2.5: mason recipe validate'
type: 'feature'
created: '2026-08-13'
status: 'done'
baseline_revision: '257094dcc2cf99a95c8553b6c05ae3cc09fe876f'
final_revision: '2ed191de0bfaeb814ff605b7eec41112e992cdae'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
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
`diagnose()`/`optimize()`/`scan()`/`update()`) -- no reinterpretation, no new dataclass. Only
`cli.py`'s `recipe validate` dispatch branch projects `CfeResult.returncode` onto the process exit
code (`EXIT_OK` when zero, else `EXIT_FAILED`) -- the one verb where this happens; every sibling
verb always reports `EXIT_OK` regardless of the wrapped tool's own outcome. This does not violate
AD-4 ("a non-zero return code is data, not an exception") -- that rule binds `recipe.py`/`cfe.py`,
which still never raise for a validation failure; the projection is `cli.py`'s own dispatch-time
decision (AD-7's exit-code ownership). The JSON envelope's `status` field stays `"ok"` regardless
of the recipe's pass/fail outcome -- only the process exit code carries the validation signal.
`validate` is Story 2.5 -- numerically the earliest recipe verb in this file, so it takes the
**first** position (before `build`) in `recipe.py`, `cli.py`'s parser registrations, and every
ordinal reference in both module docstrings, matching how Story 2.4's `new()` was reconciled to
the first position ahead of `build` elsewhere in this same codebase's history when it landed out
of chronological order.

**Block If:** N/A -- FR-8 plus the `diagnose()`/`scan()` precedents fully determine the scope.

**Never:** No Mason-side severity policy, filtering, renumbering, or re-wording of CFE's findings
(AD-1). No `--strict`/warnings-as-errors flag on Mason's own CLI (out of AC scope; a user wanting
that invokes CFE's validator directly). No import-floor probe/gate (mirrors `diagnose()`'s
exemption, not `optimize()`/`scan()`'s scoped-probe pattern). No touch to `cfe.py` -- Story 2.1
already added the `validate_recipe` adapter unchanged.

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

- `src/pyforge/mason/recipe.py` -- insert `validate()` as the **first** verb function (immediately
  before `build()` at current line 193); insert its module-docstring paragraph immediately before
  the existing "Story 2.6 creates this module..." paragraph. No `cfe.py` change needed.
- `src/pyforge/mason/cli.py` -- add `_RECIPE_VALIDATE_HELP` (between `_DOCTOR_HELP` and
  `_RECIPE_BUILD_HELP`); register `validate_parser` on `_noun_verbs["recipe"]` immediately before
  `recipe_build_parser` (current line 424); add its dispatch branch immediately before the `build`
  branch (current line 611), projecting `result.returncode` onto `EXIT_OK`/`EXIT_FAILED`; rewrite
  the module docstring's ordinal narrative (`validate` becomes "the first real verb"; `build`
  becomes the next entry in an unbroken paragraph with `diagnose`/`optimize`/`scan`; `submit`
  becomes "a fifth verb"; `update` becomes "a sixth verb") -- mirrors exactly how this same file's
  history reconciled Story 2.4's `new()` into the first position. Update the "Unreachable now for
  every verb-noun pair except..." comment to list `recipe validate` first and count seven verbs.
- `src/pyforge/mason/exit_codes.py` -- one-line addition to `EXIT_FAILED`'s docstring noting this
  new, non-`MasonError`-driven call site (a wrapped tool's own returncode projected directly).
- `tests/unit/test_recipe.py` -- `validate()`'s test block, inserted before `diagnose()`'s block
  (mirrors `diagnose()`'s composition-test shape: argv/timeout passthrough, verbatim-return,
  `ensure_import_floor` never called, `CfeUnresolvedError` propagation, two real-fixture round
  trips against `fake_cfe_root` using `MASON_FIXTURE_STDOUT`/`MASON_FIXTURE_EXIT_CODE` for the
  failing-result case -- the existing `validate_recipe.py` stub only emits a canned passing body).
- `tests/unit/test_cli.py` -- `recipe validate`'s dispatch test block, inserted before `recipe
  build`'s block; the differentiating pair (passing canned result -> `EXIT_OK`; failing canned
  result -> `EXIT_FAILED` while `status` stays `"ok"`, in both text and `--format json` modes); the
  verb-metavar regression test's expected string updated to
  `"{validate,build,diagnose,optimize,scan,submit,update}"` and its docstring's ordinal narrative
  updated to match.

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/mason/recipe.py` -- add `validate()` (resolve root -> `ensure_cfe_root` ->
  resolve interpreter -> `cfe.validate_recipe(["--json", recipe_path], ...)`, no import-floor
  gate, returns `CfeResult` verbatim) + docstring paragraph, both in first position -- FR-8.
- [x] `src/pyforge/mason/cli.py` -- register `validate_parser` (single `recipe_path` positional,
  `parents=[global_flags]`) in first position; add the `recipe`/`validate` dispatch branch calling
  `recipe.validate(...)`, rendering via `render.write(..., "ok", dataclasses.asdict(result), [])`,
  then returning `EXIT_OK` if `result.returncode == 0` else `EXIT_FAILED`; rewrite the module
  docstring's ordinal narrative and the unreachable-branch comment -- FR-8.
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
- defer: 3 (medium: 1, low: 2)
- reject: 5
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter flagged the module docstrings' "...Story 2.4's `new()`...
    elsewhere" phrasing as ambiguous -- a reader of only this branch/file has no way to tell
    "elsewhere" means a different branch's git history, not code present here (this worktree's
    baseline predates `new()`'s landing). Reworded both `recipe.py`'s and `cli.py`'s docstrings to
    state explicitly that `new()` is not present in this file and the reconciliation happened on
    `main` after an analogous out-of-order landing. Suite still 971 passed.

## Design Notes

**Why `validate` takes the first position, not the end:** `recipe.py`/`cli.py` order verbs by
story number, not landing order (each function is preceded by a "Story N.M adds..." docstring
paragraph). Story 2.5 precedes Story 2.6 (`build`), so it belongs first, even though this story is
implemented after `build`/`diagnose`/`optimize`/`scan`/`submit`/`update` already shipped. This
codebase already has a live precedent for exactly this situation: Story 2.4's `new()` was
implemented, lost, and recovered after 2.6-2.10 had already landed; when reconciled, it was placed
first (ahead of `build`), and every ordinal reference in `cli.py`'s module docstring was rewritten
accordingly ("Story 2.4 registers the first real verb"; `submit` shifted from "a fourth verb" to "a
fifth verb"; `update` from "a fifth verb" to "a sixth verb"). This story's own worktree baseline
predates that `new()` reconciliation, so `validate` becomes this worktree's own first verb, and the
same shift applies one level down: `submit` moves from "a fourth verb" to "a fifth verb", `update`
from "a fifth verb" to "a sixth verb".

The exit-code projection is the one non-obvious behavioral decision: every sibling verb
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

**Summary:** Added `mason recipe validate <recipe_path>` (FR-8), inserted as the numerically-first
`recipe` verb (Story 2.5 precedes Stories 2.6-2.10) even though it lands after
`build`/`diagnose`/`optimize`/`scan`/`submit`/`update` in this worktree -- mirroring the same
out-of-order reconciliation this repository's `main` branch already applied to Story 2.4's `new()`
elsewhere. Mirrors `diagnose()`'s composition shape (resolve root -> `ensure_cfe_root` -> resolve
interpreter -> call the CFE port), no import-floor gate, `["--json", recipe_path]` args mirroring
`scan()`'s own `--json` forcing. The one behavioral departure from every sibling verb: `cli.py`'s
`recipe validate` dispatch branch alone projects `CfeResult.returncode` onto the process exit code
(`EXIT_OK`/`EXIT_FAILED`) instead of always reporting `EXIT_OK`, so the command composes as a
CI/shell gate, while the JSON envelope's `status` field still always reads `"ok"`.

**Note on this run's baseline:** a prior dev-auto attempt at this same story (against an earlier
baseline, `4a7b049904ec`) had already fully implemented and reviewed this feature, but the
orchestrator rolled it back after detecting that baseline had gone stale (mason's `cli.py`/`recipe.py`
changed materially in the interim from Stories 2.6-2.10 landing) -- that attempt's 52 commits are
preserved at `attempt-preserve/20260813-145934-3eb0-4edeb666` for reference, not merged. This run
re-implemented the story fresh against the current baseline (`257094dcc2cf`) rather than reapplying
that patch (a `git apply --check --3way` confirmed it no longer applies cleanly to `cli.py`/`recipe.py`).

**Files changed:**
- `src/pyforge/mason/recipe.py` -- new `validate()` in first position + module-docstring paragraph;
  `build()`'s paragraph adjusted to note it now follows `validate()`.
- `src/pyforge/mason/cli.py` -- `_RECIPE_VALIDATE_HELP`, `validate_parser` registration (first
  position), the `recipe`/`validate` dispatch branch (the exit-code projection), module-docstring
  ordinal rewrite (`submit` "fourth"->"fifth", `update` "fifth"->"sixth"), unreachable-branch
  comment update (six verbs -> seven, `validate` listed first).
- `src/pyforge/mason/exit_codes.py` -- `EXIT_FAILED` docstring extended with this new,
  non-`MasonError`-driven origin.
- `tests/unit/test_recipe.py` -- 10 new `validate()` unit tests (composition, `CfeUnresolvedError`
  propagation, two real-fixture round trips).
- `tests/unit/test_cli.py` -- 16 new `recipe validate` dispatch tests, incl. the differentiating
  exit-code-projection pair in both text and `--format json` modes, plus the pre-existing
  verb-metavar regression test updated to the new seven-verb order.

**Review findings breakdown:** 1 patch applied (a Blind Hunter clarity finding -- the module
docstrings' "...Story 2.4's `new()`... elsewhere" phrasing didn't disclose that `new()` isn't
present in this file/branch; reworded in both `recipe.py` and `cli.py`). 3 deferred, all matching
substance already recorded in `deferred-work.md` by the prior (code-rolled-back but
ledger-preserved) attempt at this exact story, so no new entries were minted: `EXIT_FAILED`
conflates a validation failure with a Mason-side error (`DW-2-5-1`); the hand-maintained
verb-registration ordinal comments have no mechanical drift guard (`DW-2-5-2`); a leading-`-`
`recipe_path` could be misparsed by CFE's own `argparse`, inherited unchanged from `scan()`'s
identical Story 2.8 exposure (`DW-2-5-4`). 5 rejected: this diff will conflict with Story 2.4's
`new()` when landed against current `main` (expected -- reconciliation at landing time, same as
2.4's own precedent, not a defect of this diff); `--format text` renders the JSON body as a dict
repr (inherited unchanged from `scan()`'s identical established pattern, not new here); the JSON
envelope's `status` field always reads `"ok"` (explicit, deliberate spec Always/I-O-matrix
behavior); no test exercises the real production `validate_recipe.py` end-to-end (matches the
existing whole-suite convention -- every sibling verb's tests are equally mock/fixture-only); no
`--strict`/`--quiet` passthrough (explicit spec Never boundary).

**Verification:** `pixi run -e pyforge-mason pyforge-mason-test` -- **971 passed**, 0 failed, no new
test marked `slow`. `git diff --stat` confirms exactly the five intended files changed.

**Residual risks:** None blocking this story's own scope. The three deferred items are pre-existing/
architecture-scoped (see breakdown above), already tracked. The rejected merge-conflict-with-2.4
finding is a real, expected reconciliation task for whoever lands this branch against current
`main` (which already carries Story 2.4's `new()` in this same first-verb position) -- not a defect
in this diff, but worth flagging explicitly for the landing step.
