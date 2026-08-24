---
title: 'Story 7.1: The seed module tree inside pyforge-marshal'
type: 'feature'
created: '2026-08-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: '184aec727e0939ece618d47f691c1ef4c6493a8e'
final_revision: 'ff99e1e0962cc9198de53bbc99abd744181a02bf'
---

<intent-contract>

## Intent

**Problem:** Every later seed-installer story (error taxonomy, write guard, manifest, verbs,
Copier engine) needs a stable, importable home, but no `pyforge.marshal.seed` subpackage and
no `marshal seed` CLI entry point exist yet. Naming was contested until the 2026-08-10
correct-course settled it: the installer lives *inside* `pyforge-marshal` — no new package,
no second binary, no revival of the retired `genesis` name as a binding identifier.

**Approach:** Scaffold `src/pyforge/marshal/seed/` as eleven empty `__init__.py`-stub
subpackages per architecture § 4's module tree, add `cli/seed.py` as a new noun-group
subparser (mirroring `cli/gate.py`'s nested-verb shape) wired into `main.py`'s existing
14-subparser tree, with six verb stubs (`init`, `adopt`, `check`, `update`, `explain`,
`version` — the exact files architecture § 4 names under `verbs/`) that each report
"not implemented" and exit cleanly. No real detect/plan/apply/Copier logic lands here.

## Boundaries & Constraints

**Always:**
- Every new subpackage under `seed/` (`model/`, `state/`, `regions/`, `detect/`, `plan/`,
  `apply/`, `engine/`, `derive/`, `migrate/`, `verbs/`, `templates/`) contains only an
  `__init__.py`, matching this package's existing empty/docstring-only convention — no logic.
- `cli/seed.py` registers `add_seed_subparser(subparsers)` on the SAME `subparsers` object
  `main.py` passes to the other 14 noun groups, with `seed_subparsers =
  parser.add_subparsers(dest="seed_command", required=True)` and one nested `add_parser` per
  verb — mirrors `cli/gate.py`'s nested `evaluate` action exactly (`gate_subparsers`, same
  shape).
- Each of the six verb stubs prints a message naming the verb as not yet implemented and
  returns `EXIT_OK`, imported from `core/verdict.py` (never a new exit-code literal — `seed`'s
  own exit-code taxonomy is Story 7.2, gated on pyforge-core landing first).
- `main.py` gains one new import (`from . import seed as seed_cli`) and one new
  `seed_cli.add_seed_subparser(subparsers)` call alongside the other 14; extend its module
  docstring's per-command list with this story's entry, following that docstring's existing
  convention.
- `import pyforge.marshal.seed` succeeds with zero import-time side effects, in the lean
  `pyforge-marshal` pixi environment.
- `pyforge` stays an implicit namespace package (no `src/pyforge/__init__.py` exists or is
  added); no `pyproject.toml` edit is needed — `packages = ["src/pyforge"]` auto-discovers.
- Add `tests/unit/test_seed_scaffold.py` (named in the story's own Surface line) as one smoke
  test, mirroring `tests/unit/test_cli.py`'s import/`capsys` style.

**Block If:** none identified — the module tree, verb names, and wiring pattern are fully
specified by architecture § 4 and AD-70.

**Never:**
- No Copier import, no manifest/model/state/detect/plan/apply/engine/derive/migrate logic —
  those belong to Stories 7.2–7.6 and Epics 8–12.
- No new console script, no typer/rich (AD-51/AD-70) — `marshal seed` renders through the
  same argparse tree every other subcommand uses.
- No root `pixi.toml` wiring (the `copier` dependency, `environment.yaml` regeneration, PR
  gates) — that is Story 12.1's scope, explicitly deferred by the epics doc.
- No binding use of the name `genesis` anywhere in code, CLI text, or state — it survives only
  as historical prose in already-existing docs.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Verb stub invoked | `marshal seed init` (and `adopt`/`check`/`update`/`explain`/`version`) | Prints a message naming the verb as not implemented; returns 0 | No error expected |
| No verb given | `marshal seed` | argparse usage error (nested subparsers `required=True`) | Exit 2 (`EXIT_USAGE`) |
| Unknown verb | `marshal seed bogus` | argparse "invalid choice" usage error | Exit 2 (`EXIT_USAGE`) |
| Package import | `python -c "import pyforge.marshal.seed"` in the lean `pyforge-marshal` env | Succeeds, no output, no side effects | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/seed.py` -- NEW: registers the
  `seed` noun-group subparser with six nested verb stubs; mirrors `cli/gate.py`'s
  `add_gate_subparser` shape.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/main.py` -- add the `seed_cli`
  import and `add_seed_subparser` call alongside the other 14 (`_build_parser`, ~line 232-256);
  extend the module docstring's per-command changelog with this story's entry.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/__init__.py` -- NEW, empty.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/{model,state,regions,detect,plan,apply,engine,derive,migrate,verbs,templates}/__init__.py`
  -- NEW, 11 empty stub subpackages, exactly the architecture § 4 tree.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_scaffold.py` -- NEW smoke test:
  import succeeds; each of the six verbs returns 0 and names itself in output; bare `marshal
  seed` and an unknown verb both return the usage exit code.

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/marshal/seed/__init__.py` + the 11 subpackage `__init__.py` stubs -- create
  the empty scaffold -- gives every later story a stable importable home
- [x] `src/pyforge/marshal/cli/seed.py` -- add `add_seed_subparser` with nested
  `seed_command` subparsers for `init`/`adopt`/`check`/`update`/`explain`/`version`, each
  `set_defaults(handler=...)` to a stub returning `EXIT_OK` after printing a
  not-implemented message naming itself -- gives the CLI surface AD-70 requires without
  building any real verb logic
- [x] `src/pyforge/marshal/cli/main.py` -- import `seed_cli` and call
  `seed_cli.add_seed_subparser(subparsers)` alongside the existing 14; extend the module
  docstring's changelog -- wires `marshal seed` onto the shipped tree
- [x] `tests/unit/test_seed_scaffold.py` -- one smoke test file covering the I/O matrix above
  -- proves the scaffold and stub verbs work end to end

**Acceptance Criteria:**
- Given the existing `pyforge-marshal` workspace member, when `src/pyforge/marshal/seed/` is
  scaffolded and the member's test task runs, then all eleven subpackages exist as
  `__init__.py` stubs matching architecture § 4's tree
- Given the shipped argparse tree, when `marshal seed <verb>` is invoked for any of the six
  named verbs, then it reports not-implemented cleanly and exits 0 — no new console script, no
  typer
- Given the lean `pyforge-marshal` pixi environment, when `import pyforge.marshal.seed` runs,
  then it succeeds
- Given the existing test suite, when the member's test task runs with the new scaffold smoke
  test added, then the whole suite stays green
- Given the new tree, when ruff and pyright run against it, then both are clean

## Spec Change Log

## Review Triage Log

### 2026-08-10 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 1, low 4)
- defer: 0
- reject: 5: (high 0, medium 0, low 5)
- addressed_findings:
  - `[medium]` `[patch]` Edge Case Hunter: no test individually imported the 11 architecture § 4 subpackages (`model`/`state`/`regions`/`detect`/`plan`/`apply`/`engine`/`derive`/`migrate`/`verbs`/`templates`) -- a typo in any directory name would pass the suite silently despite violating the AC. Added `test_each_architecture_subpackage_imports`, parametrized over all 11.
  - `[low]` `[patch]` Blind Hunter: none of the six new verb subparsers set `description=`, unlike `cli/gate.py`'s established convention. Added a one-line stub description to each of the six `add_parser` calls in `cli/seed.py`.
  - `[low]` `[patch]` Blind Hunter: `test_seed_verb_stub_exits_zero_and_names_itself`'s `assert verb in captured.out` is near-tautological (the substring is guaranteed by the very f-string that produces the message). Replaced with an exact-string equality check against the full stub message.
  - `[low]` `[patch]` Blind Hunter: `cli/seed.py`'s module docstring overclaimed that the six verb names are "the exact files architecture § 4 names under `seed/verbs/`" when they are stub functions in this module, not yet split into that package. Reworded for accuracy.
  - `[low]` `[patch]` Blind Hunter: the noun-group `description=` in `cli/seed.py` named only "Stories 7.2-7.6" while `main.py`'s module docstring names "Stories 7.2-7.6 and Epics 8-12" for the same scope -- the two disagreed. Aligned both to "Stories 7.2-7.6 and Epics 8-12."
  - `[reject]` Blind Hunter: claimed `test_seed_scaffold.py` fails `ruff check` on rule I001 (import-sort). Verified false: `ruff check` (repo config) and `ruff check --isolated` both report "All checks passed!" -- ruff's default rule set (E4/E7/E9/F) does not enable `I` (isort) rules at all.
  - `[reject]` Edge Case Hunter: claimed `seed init`/`seed adopt` could error before reaching the stub handler via the pre-dispatch `_resolve_context` step. Verified false by reading `main.py`: `_resolve_context` is only invoked when `"context" in inspect.signature(handler).parameters` (`main.py:362`) -- none of the six new stub handlers declare a `context` parameter, so it is never called for them.
  - `[reject]` Blind Hunter: claimed the 11 new empty `__init__.py` files break codebase convention ("every other module carries a substantial docstring"). Verified false against the actual precedent the spec cites: `core/__init__.py` and other existing subpackage markers are themselves 0-byte empty files -- this matches, not breaks, established convention.
  - `[reject]` Blind Hunter: flagged `marshal seed check` vs. the pre-existing `marshal check` as a naming collision with no cross-reference in either `--help`. This is architecture's own already-decided, already-documented design (AD-54, "verb collision closed") -- not a defect introduced by this story, and out of this story's scope to add cross-referencing UX polish.
  - `[reject]` Blind Hunter: flagged `seed/templates/__init__.py` as turning `templates/` into an importable package, in tension with architecture's "templates/ is data, never imported as code" rule. `templates/` is one of the 11 subpackages the AC itself explicitly requires as an `__init__.py` stub -- not a defect introduced by this story's implementation choices, and no code anywhere imports names from it.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expect all tests pass,
  including the new `test_seed_scaffold.py`
- `pixi run --frozen -e pyforge-marshal python -c "import pyforge.marshal.seed"` -- expect
  exit 0, no output
- `pixi run -e local-recipes ruff check src/shared/packages/pyforge-marshal` -- expect zero
  findings
- `pixi run -e local-recipes pyright src/shared/packages/pyforge-marshal` -- expect zero
  findings
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`
  -- expect all contracts pass (AD-3/AD-4/AD-9 unaffected by this story's additive-only
  changes)

## Auto Run Result

Status: done

**Summary:** Scaffolded `src/pyforge/marshal/seed/` as eleven empty `__init__.py`-stub
subpackages (`model/state/regions/detect/plan/apply/engine/derive/migrate/verbs/templates`,
plus the package root) matching architecture § 4's module tree, and wired `marshal seed
<verb>` as the CLI's 15th noun-group subparser (AD-70), with six stub verbs
(`init`/`adopt`/`check`/`update`/`explain`/`version`) that each print a not-yet-implemented
message and exit 0. No real detect/plan/apply/Copier logic lands here — that's Stories
7.2–7.6 and Epics 8-12.

**Files changed:**
- `src/pyforge/marshal/cli/seed.py` (new) -- `add_seed_subparser` + six verb stubs, mirrors
  `cli/gate.py`'s nested-subparser shape
- `src/pyforge/marshal/seed/__init__.py` + 11 sub-subpackage `__init__.py`s (new, empty) --
  the architecture § 4 scaffold
- `src/pyforge/marshal/cli/main.py` -- wires `seed` as the 15th subparser; extends the
  module docstring's per-command changelog
- `tests/unit/test_seed_scaffold.py` (new) -- import smoke test, per-subpackage import
  coverage (all 11), per-verb exit/message coverage, bare/unknown-verb usage-error coverage
- `pyproject.toml` + `tests/meta/test_ad3_ad4_import_linter.py` -- added
  `pyforge.marshal.seed` to the AD-3 import-linter contract's `source_modules`, required by
  that contract's own self-maintaining coverage meta-test
- `tests/unit/test_cli.py` -- extended the `--help` subcommand-choices assertion string with
  `seed`, following the same precedent every prior subcommand addition set

**Review findings breakdown:** 2 reviewers (Blind Hunter, Edge Case Hunter) in parallel, no
shared context. 9 raw findings, deduplicated to 9 distinct issues. 5 patched (1 medium: test
coverage gap for the 11 subpackages; 4 low: missing verb `description=` fields, a tautological
test assertion, a docstring overclaim, an inter-docstring wording inconsistency). 4 rejected
after independent verification proved them false or out of this story's scope (a claimed ruff
I001 finding contradicted by two live `ruff check` runs; a claimed `_resolve_context`
pre-dispatch hazard contradicted by reading `main.py`'s actual `inspect.signature` gate; a
claimed empty-`__init__.py` convention break contradicted by the actual `core/__init__.py`
precedent; and two already-decided architecture concerns — the `seed check`/`check` naming
split (AD-54) and `templates/`'s spec-mandated `__init__.py` — that are not defects introduced
by this story). 0 deferred, 0 intent gaps, 0 bad-spec loopbacks.

**Follow-up review recommendation:** false. All five patches were narrow and localized
(docstring wording, missing help text, one test-quality strengthening, one test-coverage
addition) with no behavior, API, security, or data-model impact.

**Verification performed:**
- `pyforge-marshal-test`: 3257 passed, 9 deselected (up from 3246 pre-patch; the 11 new
  per-subpackage import tests added the delta)
- `import pyforge.marshal.seed`: exit 0, no output
- `ruff check` on the new/changed tree: all checks passed (verified both under repo config
  and `--isolated`, since one reviewer's claim needed direct empirical refutation)
- `pyright` on the new/changed tree: 0 errors, 0 warnings, 0 informations
- `lint-imports --config .../pyproject.toml --no-cache`: 3 kept, 0 broken (AD-3/AD-4/AD-9)
- Live CLI spot-check: `marshal seed init --help` renders its new stub description correctly

**Residual risks:** None identified. The scaffold is inert (empty subpackages, stub verbs
returning `EXIT_OK`) so there is no runtime behavior surface beyond what the tests already
cover exhaustively. Story 7.2 will need to replace each verb stub's body with real dispatch
logic and introduce `seed`'s own exit-code taxonomy — that migration is out of this story's
scope by design.
