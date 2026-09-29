---
title: 'mason recipe new'
type: 'feature'
created: '2026-08-11'
status: 'done'
baseline_revision: '257094dcc2cf99a95c8553b6c05ae3cc09fe876f'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
  - '{project-root}/_bmad-output/projects/pyforge-mason/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Epic 2's CFE port (Story 2.1) and seam guard (2.2) exist, but no verb is registered
under `mason recipe` yet -- `cli.py`'s dispatch still hits `# Unreachable in Story 1.2`. FR-7 needs
the first real one: generate a recipe from PyPI/GitHub/CRAN/npm through CFE's `recipe-generator.py`,
with zero recipe knowledge added in Mason.

**Approach:** Add a third `_CFE_SCRIPTS` entry (`"generate_recipe": "recipe-generator.py"`) and a
`generate_recipe` adapter in `cfe.py`; a new `recipe.py` use-case module (`new`) that resolves CFE,
forwards the user's source/package/output verbatim to the adapter, and raises a typed error on a
non-zero CFE exit; and a `recipe new` verb in `cli.py` with a required mutually-exclusive
`--from-pypi`/`--from-github`/`--from-cran`/`--from-npm` group plus a required `--output`.

## Boundaries & Constraints

**Always:**
- `--from-pypi`/`--from-github`/`--from-cran`/`--from-npm`'s value and `--output`'s value are
  forwarded to CFE unmodified as `[source, package, "--output", output]` (`source` is CFE's own
  subcommand name -- `pypi`/`github`/`cran`/`npm` -- selected by which flag the user gave; this is
  command routing, not recipe knowledge). No parsing of embedded `==`/`@` version specs, no path
  transformation.
- `--output` is required on Mason's `recipe new` (FR-7: output lands "at a user-specified path");
  CFE's own omitted-`--output` default (`recipes/<name>`) is never exercised through Mason.
- A non-zero `CfeResult.returncode` from `generate_recipe` raises `RecipeGenerationError`, embedding
  CFE's own `stdout` (falling back to `stderr`) verbatim -- the real script prints `Error: <e>` to
  stdout, not stderr, on failure.
- `recipe.py::new` composes `resolve.py`'s pure chains with `cfe.py`'s raising siblings
  (`ensure_cfe_root`, `ensure_import_floor`) directly, mirroring `doctor.build_report`'s parameter
  shape but raising instead of degrading. `cli.py`'s existing `main()` exception handling needs no
  change: `CfeUnresolvedError` hits its dedicated branch; `CfeImportFloorError`/`CfeTimeoutError`/
  `RecipeGenerationError` all hit the generic `MasonError` branch.
- Update both existing two-entry `_CFE_SCRIPTS`-shape assertions to the new three-entry set:
  `test_cfe_scripts_table_has_exactly_the_two_story_1_9_fixture_entries` (`test_cfe.py`) and
  `test_parse_cfe_script_filenames_reads_the_real_cfe_py` (`test_adapter_sole_caller.py`) both
  hardcode `{"validate_recipe.py", "submit_pr.py"}` and fail otherwise.

**Block If:** None identified -- the source-to-subcommand mapping, output-path semantics, and
generation-failure error shape are resolved above from the real `recipe-generator.py` script's
actual CLI/output behavior (read directly, not guessed).

**Never:**
- No secondary per-source flags: GitHub's `--version`, CRAN's `--universe`/`--tree`, npm's
  `--source-mode`/`--prepare-fix`/`--test-mode`/`--no-third-party-licenses`/`--validate`/
  `--feedstock-mode`, or PyPI's `--format legacy` -- out of this story's AC scope.
- No `cpan`/`luarocks`/`template` source flags -- not named in FR-7.
- No parsing of `CfeResult.stdout` to extract the written recipe path (e.g. scraping the
  `"Generated: "` line) -- that would itself be Mason-side interpretation of CFE's own output,
  exactly what the "no rewriting" AC forbids. `CfeResult.json_body` is always `None` for this
  adapter (the wrapped script has no `--json` mode); callers use `returncode`/`stdout`/`stderr`.
- No change to `main()`'s exception-handling branches.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | `recipe new --from-pypi requests --output recipes/requests`, CFE resolved, exit 0 | `recipe.new` returns `CfeResult(returncode=0, ...)`; `cli.py` renders `"recipe new"`/`"ok"` with `dataclasses.asdict(result)` as `data` | No error |
| Other sources | `--from-github`/`--from-cran`/`--from-npm` in place of `--from-pypi` | Adapter args become `["github", ...]`/`["cran", ...]`/`["npm", ...]` respectively | No error |
| No `--from-*` given | bare `recipe new --output x` | argparse usage error (mutually exclusive group `required=True`) | EXIT_USAGE, stderr |
| Two `--from-*` given | `--from-pypi a --from-github b` | argparse usage error | EXIT_USAGE, stderr |
| `--output` omitted | `recipe new --from-pypi requests` | argparse usage error (`--output` required) | EXIT_USAGE, stderr |
| CFE generation fails | fixture `MASON_FIXTURE_EXIT_CODE=1`, `MASON_FIXTURE_STDOUT="Error: no such package"` | `recipe.new` raises `RecipeGenerationError(source="pypi", cfe_message="Error: no such package")` | EXIT_FAILED, stderr, `main()`'s generic `MasonError` branch |
| CFE root unresolved | no `--cfe-root`/env/marker found | `ensure_cfe_root` raises `CfeUnresolvedError` before any subprocess spawns | EXIT_CFE_UNAVAILABLE |
| CFE subprocess times out | `generate_recipe` exceeds `_GENERATE_RECIPE_TIMEOUT_SECONDS` | `CfeTimeoutError` (already raised by `_invoke_captured`, unchanged) | EXIT_FAILED, stderr |

</intent-contract>

## Code Map

- `src/pyforge/mason/errors.py` -- add `RecipeGenerationError` (FR-7's typed generation-failure error).
- `src/pyforge/mason/cfe.py` -- add `_CFE_SCRIPTS["generate_recipe"]`, `_GENERATE_RECIPE_TIMEOUT_SECONDS`,
  and the `generate_recipe` adapter function.
- `src/pyforge/mason/recipe.py` (new) -- the CFE-dependent use-case module; `new()` composes
  resolution + the adapter, raising on failure.
- `src/pyforge/mason/cli.py` -- register the `recipe new` verb (mutually exclusive `--from-*` group
  + required `--output`) in `build_parser()`; wire its dispatch in `main()`, replacing the
  `# Unreachable in Story 1.2` fallthrough.
- `tests/fixtures/fake_cfe_root/.claude/scripts/conda-forge-expert/recipe-generator.py` (new) --
  fake stub for real-subprocess fixture tests, same 8-line shape as `validate_recipe.py`.
- `tests/unit/test_cfe.py` -- `generate_recipe` adapter coverage (argv-shape mock, real-fixture
  round-trip, default-timeout, table-entry); update the two-entry table assertion.
- `tests/meta/test_adapter_sole_caller.py` -- update `test_parse_cfe_script_filenames_reads_the_real_cfe_py`
  to the new three-entry set.
- `tests/unit/test_recipe.py` (new) -- `recipe.new()` use-case coverage: happy path per source,
  generation-failure error, CFE-unresolved/import-floor-missing propagation.
- `tests/unit/test_cli.py` -- end-to-end `recipe new` verb-dispatch coverage (text/JSON happy path,
  error path, the three usage-error cases from the I/O matrix).

## Tasks & Acceptance

**Execution:**
- [x] `errors.py` -- add `RecipeGenerationError(source: str, cfe_message: str)`, identifier
  `recipe:generation-failed`, message `f"recipe generation from {source} failed: {cfe_message}"`,
  with a `__reduce__` override (mirrors `CfeTimeoutError`'s, since its constructor args don't match
  `MasonError.__init__`'s `self.args`) -- FR-7.
- [x] `cfe.py` -- add `_CFE_SCRIPTS["generate_recipe"] = "recipe-generator.py"`; update the table's
  docstring (no longer "two entries only" for this mapping); add `_GENERATE_RECIPE_TIMEOUT_SECONDS`
  (240.0 -- exceeds `recipe-generator.py`'s own internal 180s `_run_rattler_generate` subprocess
  timeout for CRAN/CPAN/LuaRocks, with headroom proportional to `submit_pr`'s 300s); add
  `generate_recipe(args, *, root, interpreter, timeout=None) -> CfeResult` calling
  `_invoke_captured("generate_recipe", ...)`, mirroring `validate_recipe`'s exact shape -- FR-7.
- [x] `recipe.py` (new) -- `new(source, package, output, *, cfe_root_arg, cfe_python_arg,
  cfe_timeout_arg, environ, start_directory) -> CfeResult`: resolve root/interpreter, call
  `cfe.ensure_cfe_root`/`cfe.ensure_import_floor`, invoke `cfe.generate_recipe([source, package,
  "--output", output], ...)`, raise `RecipeGenerationError` when `returncode != 0` (message from
  `stdout.strip() or stderr.strip() or` a bare-returncode fallback), else return the `CfeResult`
  unchanged -- FR-7.
- [x] `cli.py` -- add `recipe` to the top-of-file `from . import __version__, doctor, render` line.
  In `build_parser()`, capture the `recipe` noun's `add_subparsers()` return and add a `new` verb:
  mutually exclusive group (`required=True`) of `--from-pypi`/`--from-github`/`--from-cran`/
  `--from-npm` (each a plain string), plus `--output`/`-o` (`required=True`, plain string). In
  `main()`, before the `# Unreachable in Story 1.2` block, dispatch `ns.noun == "recipe" and ns.verb
  == "new"` to `recipe.new(...)`, then `render.write(fmt, sys.stdout, "recipe new", "ok",
  dataclasses.asdict(result), [])` and return `EXIT_OK` -- FR-7, AD-8.
- [x] `tests/fixtures/.../recipe-generator.py` (new) -- stub emitting
  `_stub_support.emit("Fetching info for demo...\nGenerated: recipes/demo/recipe.yaml\n")`,
  identical shape to `validate_recipe.py`.
- [x] `test_cfe.py` -- update the exactly-two-entries assertion to include `"generate_recipe":
  "recipe-generator.py"`; add: argv-shape mock test (`["pypi", "requests", "--output", "x"]` reaches
  `subprocess.run` unmodified, `env` absent/`None`), real-fixture round-trip (`json_body is None`,
  `stdout`/`returncode` match the fixture), default-timeout test, timeout-error test -- FR-4, FR-7,
  AD-14.
- [x] `test_adapter_sole_caller.py` -- update `test_parse_cfe_script_filenames_reads_the_real_cfe_py`'s
  expected `frozenset` to include `"recipe-generator.py"`.
- [x] `test_recipe.py` (new) -- `new()` against `fake_cfe_root`: one happy-path test per source
  (`pypi`/`github`/`cran`/`npm`) asserting the adapter argv's first element; a
  `MASON_FIXTURE_EXIT_CODE=1` test asserting `RecipeGenerationError` carries the fixture's stdout;
  a not-found `root` test asserting `CfeUnresolvedError` propagates before any subprocess spawns --
  FR-7.
- [x] `test_cli.py` -- `main(["recipe", "new", "--from-pypi", "requests", "--output", "x", ...])`
  happy path (text and `--format json`, mocking `pyforge.mason.cli.recipe.new`); the three usage-error
  cases (no source flag, two source flags, no `--output`) asserting `EXIT_USAGE`; a
  `RecipeGenerationError`-raising mock asserting `EXIT_FAILED` and the message on stderr -- FR-7.

**Acceptance Criteria:**
- Given `mason recipe new --from-pypi <name> --output <path>`, when it runs against a resolvable CFE
  root, then the `generate_recipe` adapter invokes `recipe-generator.py pypi <name> --output <path>`
  and the rendered result's `stdout`/`returncode` are CFE's own, unmodified.
- Given `--from-github`/`--from-cran`/`--from-npm`, when each is used, then the matching CFE
  subcommand (`github`/`cran`/`npm`) is invoked in `args[0]`.
- Given the generated result, when compared to `CfeResult`'s raw fields, then Mason has applied no
  field defaults, no rewriting, and no normalization of its own (the fixture round-trip test proves
  byte-identical `stdout`).
- Given a generation failure reported by CFE (non-zero exit), when it surfaces, then
  `RecipeGenerationError` is raised carrying CFE's own message text verbatim.
- Given none, more than one, or a `--from-*` flag with no `--output`, when `recipe new` is invoked,
  then argparse rejects it with a usage error before any CFE resolution is attempted.

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass

- intent_gap: 1 (high 1)
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

**Context:** this pass reviewed a recovery of the story's original implementation attempt. The
code had been fully implemented and reviewed-ready as of 2026-08-11 (this spec's frontmatter
already carried `status: in-review` with every task checked), but the working tree was lost to
worktree teardown before it landed -- the code existed only in a dangling git commit
(`c82a78e5aa`, now preserved at tag `rescue/mason-2-4-attempt-snapshot`) that no branch pointed
to. Stories 2.6-2.10 built `recipe.py`/`cli.py`/`cfe.py` from scratch afterward, unaware 2.4
existed, and landed first. This pass recovered the lost commit, hand-reconciled every conflict
against the current (post-2.6-2.10) code, confirmed the full suite green
(`pixi run --frozen -e pyforge-mason pyforge-mason-test`: 966/966), then ran the standard
Blind Hunter + Edge Case Hunter review pass against the reconciled diff.

**intent_gap (HIGH) — `new()`'s unconditional `cfe.ensure_import_floor()` call is overly broad
for what `recipe-generator.py` actually needs, and the flaw is inside `<intent-contract>`:**
Both reviewers independently converged on the same finding. The spec's own Boundaries &
Constraints ("Always") explicitly instructs: "`recipe.py::new` composes `resolve.py`'s pure
chains with `cfe.py`'s raising siblings (`ensure_cfe_root`, `ensure_import_floor`) directly" --
and `"Block If: None identified"` declares this fully resolved, no human judgment needed. The
code correctly implements this instruction. But `ensure_import_floor` gates on CFE's *entire*
6-package import floor (`pyyaml`/`requests`/`packaging`/`truststore`/`ruamel.yaml`/
`conda-forge-metadata`), while the real wrapped script (`recipe-generator.py`) only ever imports
`truststore` and `requests`, both already guarded by its own `try/except ImportError` with
graceful degradation -- it never imports `pyyaml`/`packaging`/`ruamel.yaml`/
`conda-forge-metadata` at all, and the `cran`/`cpan`/`luarocks` paths need none of the floor
(they shell out to `rattler-build generate-recipe`). A `recipe new --from-cran/--from-npm/
--from-github` call can be spuriously rejected with `CfeImportFloorError` solely because the
interpreter lacks a package the operation never touches.

This is the identical defect class Story 2.8's own dev session hit and escalated for
`optimize()`/`scan()` (see that story's run history) -- resolved there by scoping the gate to a
relevant subset (`_OPTIMIZE_RELEVANT_FLOOR`/`_SCAN_RELEVANT_FLOOR`) rather than calling the
whole-floor `ensure_import_floor`. `new()`'s spec was authored before that precedent existed
and was never updated. Because the root cause (the "Always: call `ensure_import_floor`"
instruction) is inside `<intent-contract>`, this cannot be self-amended per this workflow's
rules -- it needs a human decision on the correct scoped-floor subset (candidate: `("requests",)`,
mirroring `_SCAN_RELEVANT_FLOOR`'s shape) and whether `cran`/`cpan`/`luarocks` sources should
skip the gate entirely, mirroring `diagnose()`/`build()`/`submit()`/`update()`'s "already
handles it" exemption for their own stdlib-only/self-degrading wrapped scripts.

**Other findings surfaced this pass, not yet triaged (moot per the cascading rule while the
intent_gap above is open — re-surface on the next review pass once resolved):**
- (Edge Case Hunter, MEDIUM) `cli.py`'s `recipe new` dispatch selects a `--from-*` value by
  `is not None`, not truthiness: `--from-pypi ""` or `--output ""`/`"   "` is accepted and
  forwarded to CFE unmodified, unlike `recipe build`'s `--config` (which normalizes a
  whitespace-only value to absent). Surfaces as a less-specific CFE-authored error rather than
  Mason's own usage diagnostic.
- (Blind Hunter, LOW) `cli.py`'s module docstring undercounts `submit`/`update`'s verb-
  registration ordinal by one ("a fifth verb" / "a sixth verb" should read sixth/seventh) --
  a pre-existing off-by-one this pass's uniform +1 shift (for `new` becoming verb #1) preserved
  instead of correcting; contradicted by this same diff's own `test_cli.py` edit, which states
  the correct cumulative counts.
- (Blind Hunter, LOW) `cfe.py`'s module docstring places the new "Story 2.4 adds `generate_recipe`"
  paragraph after the Story 2.10 paragraph in the file's top narrative section (out of
  chronological order) -- inconsistent with every other touched file's docstring, which was
  correctly reordered to place Story 2.4 first, and inconsistent with this same docstring's own
  second passage (the `_CFE_SCRIPTS` table walkthrough), which is correctly ordered.
- (Edge Case Hunter, LOW) Repeating the same `--from-*` flag (`--from-pypi a --from-pypi b`) is
  accepted by argparse's mutual-exclusion check (which only fires across *different* group
  members) and silently keeps the last value -- standard `argparse` `store` semantics, not
  obviously a defect, but undiagnosed if unwanted.

**Action taken:** code changes reverted to `baseline_revision` (`257094dcc2cf99a95c8553b6c05ae3cc09fe876f`)
-- `git status` confirmed clean after the revert. The full reconciled diff is preserved, not
discarded, at `{implementation_artifacts}/preserved/spec-2-4-attempt-1-tracked.patch` (verified
`git apply --check --3way`-clean against current baseline), and the original lost commit remains
tagged at `rescue/mason-2-4-attempt-snapshot` for provenance.

## Design Notes

**Why `--output` is required, not passed through as optional:** FR-7 frames the feature as "output at
a user-specified path" -- letting it fall through to CFE's own omitted-`--output` default
(`recipes/<lowercased-name>`) would mean Mason's CLI contract depends on a CFE-side naming policy that
could change independently. Requiring it is CLI ergonomics (PRD: "Mason contributes verb design,
argument ergonomics"), not recipe knowledge.

**Why `CfeResult` is reused as-is instead of a new model:** the wrapped script has no `--json` output
mode (unlike `validate_recipe.py`/`submit_pr.py`), so `json_body` is always `None` here. Inventing a
`RecipeGenerationResult` wrapper around a result that has nothing beyond `CfeResult`'s own four fields
would be speculative structure with no present consumer -- `models.py`'s own docstring names only
`ShipReceipt`/`ShipTargetResult`/`LockResult` as pending additions, not a recipe-new-specific shape.

**Why `source` in adapter args isn't "recipe knowledge":** AD-1 bans recipe *semantics* -- gotchas,
pins, format-field defaults, policy constants. `source` is CFE's own subcommand vocabulary
(`pypi`/`github`/`cran`/`npm`), selected 1:1 from which `--from-*` flag the user gave; Mason adds no
judgment about what any of those words mean.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Status:** done
Reconciled 2026-09-20: the `blocked` verdict below is the session's own record at halt time; the story was landed afterwards and the ledger row promoted to `done` by `10caebb31d 2026-08-13 mason: sync ledger + dashboard + spec-surface for story 2-4` — that promotion is the ruling this record now reflects.

**Blocking condition:** intent gap in intent contract

**Summary:** This spec's frontmatter already read `status: in-review` with every task checked
when this run picked it up, but no code implementing it existed anywhere in the tracked history
-- the sprint-status ledger still listed `2-4-mason-recipe-new: backlog`. Investigation found the
original implementation as a dangling, unreachable git commit (`c82a78e5aa`, "attempt worktree
snapshot", authored by the loop harness on 2026-08-11 -- an interrupted-session safety-net commit
never pushed to any branch), orphaned when Stories 2.6-2.10 built `recipe.py`/`cli.py`/`cfe.py`
from scratch afterward and landed first, unaware 2.4's work existed. This run recovered that
commit (tagged `rescue/mason-2-4-attempt-snapshot` for provenance), cherry-picked it onto current
main, and hand-reconciled every conflict against the code stories 2.6-2.10 had since added.

**Files changed (in the reconciled attempt, reverted this pass -- see Action taken):**
- `src/pyforge/mason/errors.py` -- `RecipeGenerationError` (new, typed generation-failure error).
- `src/pyforge/mason/cfe.py` -- `_CFE_SCRIPTS["generate_recipe"]` (tenth entry, alongside the nine
  stories 2.6-2.10 already added), `_GENERATE_RECIPE_TIMEOUT_SECONDS`, `generate_recipe()` adapter.
- `src/pyforge/mason/recipe.py` -- `new()` (the story's use-case function), inserted first among
  the six verbs now present (build/diagnose/optimize/scan/submit/update), module docstring
  reordered to narrate Story 2.4 before 2.6-2.10.
- `src/pyforge/mason/cli.py` -- `recipe new` verb registered first in the noun's verb list
  (mutually exclusive `--from-pypi`/`--from-github`/`--from-cran`/`--from-npm` group + required
  `--output`), dispatch branch added, module docstring/help-text-constant/"Unreachable" comment
  updated to match.
- `tests/fixtures/fake_cfe_root/.claude/scripts/conda-forge-expert/recipe-generator.py` -- new
  fixture stub (added cleanly, no conflict).
- `tests/meta/test_adapter_sole_caller.py`, `tests/unit/test_cfe.py`, `tests/unit/test_cli.py`,
  `tests/unit/test_recipe.py` -- table/frozenset-shape assertions widened to the current entry
  counts (nine to ten scripts, six to seven verbs); one drifted assertion
  (`test_recipe_diagnose_verb_metavar_reflects_the_registered_verb`'s exact metavar string) needed
  a one-line fix since `new` becoming the first verb shifted it.

**Review findings breakdown:** Blind Hunter + Edge Case Hunter ran in parallel against the
reconciled diff (`git diff 257094dcc2cf99a95c8553b6c05ae3cc09fe876f..<reconciliation-commit>`).
Both independently converged on one HIGH finding whose root cause sits inside `<intent-contract>`
(the spec's own "Always" boundary mandates the exact call that causes it) -- see the Review Triage
Log above for full detail. Per this workflow's rules, a finding rooted inside `<intent-contract>`
cannot be self-amended; it is recorded as `intent_gap` and this run halts rather than looping back
through re-implementation. Four additional lower-severity findings (one MEDIUM, three LOW) were
also surfaced but are moot for this pass under the cascading rule (intent_gap present -> lower
findings not individually triaged) -- see the Review Triage Log for all four, so they are not lost
when this spec is next picked up.

**Verification performed:** `pixi run --frozen -e pyforge-mason pyforge-mason-test` on the
reconciled diff (before reverting): 966/966 passed, zero regressions against the pre-existing
suite. `git apply --check --3way` confirmed the preserved patch still applies cleanly to the
post-revert baseline.

**Follow-up review recommendation:** not applicable -- this pass ended in `blocked`, not `done`.

**Action taken:** code reverted to `baseline_revision` (`257094dcc2cf99a95c8553b6c05ae3cc09fe876f`)
-- `git status` confirmed clean after the revert. The full reconciled diff is preserved, not
discarded, at `{implementation_artifacts}/preserved/spec-2-4-attempt-1-tracked.patch`, and the
original lost commit remains tagged at `rescue/mason-2-4-attempt-snapshot`.

**Residual risks:**
- The recovered work sits entirely in local, unpushed git state (a local tag plus a local branch
  commit reachable via reflog only after the reset). Neither is pushed to `origin`; a fresh clone
  or a pruned local repo would lose them. Recommend pushing the tag (`git push origin
  rescue/mason-2-4-attempt-snapshot`) as a durability measure independent of resolving the
  intent-contract question.
- The recommended fix (scope the import-floor gate to `("requests",)`, mirroring
  `_SCAN_RELEVANT_FLOOR`'s shape, and/or skip the gate entirely for `cran`/`cpan`/`luarocks`
  sources) is a strong candidate based on precedent (Story 2.8's identical, already-resolved
  escalation for `optimize()`/`scan()`) but was deliberately left for human sign-off, not
  pre-applied to `<intent-contract>`, per this workflow's rules.
- The sprint-status ledger (`_bmad-output/projects/pyforge-mason/planning-artifacts/
  sprint-status-ledger.yaml`) was not touched this pass; it still correctly reads
  `2-4-mason-recipe-new: backlog` (unchanged, since no code landed).

## Status reconcile 2026-09-20

- frontmatter `status` `blocked` → `done` (ledger row `2-4-mason-recipe-new: done`).
- Auto Run Result `Status: blocked` → `done` (see the reconcile line under it).
