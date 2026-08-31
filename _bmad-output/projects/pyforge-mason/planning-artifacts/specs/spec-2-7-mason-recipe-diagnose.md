---
title: 'mason recipe diagnose'
type: 'feature'
created: '2026-08-12'
status: 'done'
baseline_revision: 'f6b3e8f2b32efdedb498c47fa2352f5e17bb4594'
final_revision: '1da21b516e428b75a510a7bb9ef80d20a83eb14a'
review_loop_iteration: 0
followup_review_recommended: false # dev-verify repair pass: 1 low patch (stale doc count) + 1 low defer (pre-existing metavar gap), 9 rejects -- no structural/security/API change, below the follow-up threshold
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
  - '{project-root}/_bmad-output/projects/pyforge-mason/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** FR-10's `recipe diagnose` is unimplemented. A user whose build fails has no way to get
a named cause and fix without reading CFE's raw error library themselves.

**Approach:** Investigation of the real scripts resolves OQ-A1 for FR-10: CFE's
`failure_analyzer.py` (backing MCP's `analyze_build_failure`) is a pure-stdlib, CAPTURE-mode script
that accepts a real log-file path as its positional argv and prints one JSON document. Add
`recipe.py` (new -- the first `recipe` verb on this branch) with `diagnose()`, composed on a new
`cfe.py::diagnose_failure` adapter (mirrors the shipped `validate_recipe`/`submit_pr` shape exactly:
`args: Sequence[str]` in, bare `CfeResult` out -- no new model). `cli.py` registers `recipe`'s first
verb, restructuring `build_parser()`'s noun loop to capture each noun's verb-subparsers action so a
verb can be added to it (module docstring's documented seam).

## Boundaries & Constraints

**Always:**
- `log_path` (positional, required) is passed straight through as `failure_analyzer.py`'s own
  `logfile` argv -- no pre-validation of its existence (mirrors `recipe new`/`recipe build`'s "no
  Mason-side interpretation of CFE's own output" boundary); a missing file surfaces as CFE's own
  `{"success": false, "error": "Log file not found: ..."}` JSON body, exit 1 -- data, never raised
  (AD-4).
- `diagnose()` calls `cfe.ensure_cfe_root` before any subprocess spawns, raising
  `CfeUnresolvedError` if unresolved (mirrors `build`/`validate`/`submit`).
- No `ensure_import_floor` gate: `failure_analyzer.py` imports only `argparse`/`json`/`re`/`sys`/
  `pathlib`/`typing` (confirmed by reading it) -- the same exemption Story 2.6 established for
  `build-locally.py`.
- `cli.py`'s `main()` resolves `--cfe-timeout`/`MASON_CFE_TIMEOUT` via the existing
  `_resolve_optional_float` (first real caller of that helper) and passes the resolved value into
  `recipe.diagnose(cfe_timeout_arg=...)`; `cfe.diagnose_failure`'s own default
  (`_DIAGNOSE_FAILURE_TIMEOUT_SECONDS = 120.0`) applies only when that resolves to `None`.
- `diagnose_failure`'s result renders through the normal path:
  `render.write(fmt, sys.stdout, "recipe diagnose", "ok", dataclasses.asdict(result), [])` --
  `json_body` (CFE's own `success`/`diagnosis`/`all_matches`/`error`/`hint` shape) carries the whole
  answer, including the "no diagnosis" case (FR-10) -- Mason adds no wording of its own.

**Block If:** None identified -- OQ-A1's script identity, its stdlib-only imports, and its CAPTURE
invocation shape are all resolved above from the real script's own read behavior.

**Never:**
- No `--first-only` flag or any other passthrough beyond the log path: FR-10 and
  `test-architecture.md`'s row name no such knob, and the full (non-first-only) response already
  carries the primary diagnosis at its top level for backward compatibility -- adding it would be
  speculative surface.
- No stdin/`-` support: `_invoke_captured` fixes the child's `stdin` to `DEVNULL` (existing,
  unchanged), so passing `-` would silently read an empty log rather than piped input; out of scope
  for this story, not documented as a feature.
- No new `DiagnosisResult` model -- `CfeResult` (Story 2.1) is the shared CAPTURE-mode shape;
  inventing a second one for this operation alone would contradict Data Shapes' "no dicts as
  cross-layer return types" rule. `CfeResult.json_body` is the sanctioned opaque-data escape hatch.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Diagnosis found | `recipe diagnose build.log`, log matches a pattern | `CfeResult(returncode=0, json_body={"success": true, "error_class": ..., "diagnosis": ..., "all_matches": [...]})` rendered | No error |
| No pattern matched | log matches nothing | `CfeResult(returncode=1, json_body={"success": false, "error": "No known error pattern matched...", "hint": ...})` rendered as `status="ok"` (the gap is data) | No error raised |
| Log file not found | `log_path` does not exist | CFE's own `{"success": false, "error": "Log file not found: ..."}`, `returncode=1` | No error raised |
| CFE root unresolved | no root found | `CfeUnresolvedError` before any subprocess spawns | `EXIT_CFE_UNAVAILABLE` |
| Diagnosis exceeds timeout | `--cfe-timeout` fires | `CfeTimeoutError` | `EXIT_FAILED`, stderr |

</intent-contract>

## Code Map

(paths relative to `src/shared/packages/pyforge-mason/`)

- `src/pyforge/mason/cfe.py` -- add `_CFE_SCRIPTS["diagnose_failure"] = "failure_analyzer.py"`,
  `_DIAGNOSE_FAILURE_TIMEOUT_SECONDS = 120.0`, `diagnose_failure(args, *, root, interpreter,
  timeout=None) -> CfeResult` (mirrors `validate_recipe`'s exact shape via `_invoke_captured`).
- `src/pyforge/mason/recipe.py` (new) -- `diagnose(log_path, *, cfe_root_arg, cfe_python_arg,
  cfe_timeout_arg, environ, start_directory) -> CfeResult`: resolves root + interpreter, calls
  `cfe.ensure_cfe_root`, calls `cfe.diagnose_failure([log_path], ...)`.
- `src/pyforge/mason/cli.py` -- add `recipe` to the `from . import __version__, doctor, recipe,
  render` line; restructure `build_parser()`'s noun loop to capture `_noun_verbs: dict[str,
  argparse._SubParsersAction]`, register `diagnose` (one required `log_path` positional) on
  `_noun_verbs["recipe"]`; in `main()`, after the bare-verb usage-error check and before the
  `# Unreachable` fallthrough, dispatch `ns.noun == "recipe" and ns.verb == "diagnose"`.
- `tests/fixtures/fake_cfe_root/.claude/scripts/conda-forge-expert/failure_analyzer.py` (new) --
  stub mirroring `validate_recipe.py`'s exact shape/convention, canned success-case JSON body.
- `tests/unit/test_cfe.py` -- `diagnose_failure` coverage (mocked I/O matrix + real-fixture
  round-trip); extend the AD-14 sentinel test to include it; update the 2-entry `_CFE_SCRIPTS`
  literal assertion to 3.
- `tests/unit/test_recipe.py` (new) -- `diagnose()` composition against `fake_cfe_root`: happy
  path, CFE-unresolved propagation (asserting no subprocess spawns).
- `tests/unit/test_cli.py` -- `recipe diagnose` verb registration + dispatch (text/JSON,
  CfeUnresolvedError -> `EXIT_CFE_UNAVAILABLE`, real-fixture end-to-end).
- `tests/meta/test_adapter_sole_caller.py` -- update
  `test_parse_cfe_script_filenames_reads_the_real_cfe_py` to the new 3-entry frozenset.

## Tasks & Acceptance

**Execution:**
- [x] `cfe.py` -- add the `diagnose_failure` table entry, timeout constant, adapter function -- FR-10.
- [x] `recipe.py` (new) -- `diagnose()` use-case -- FR-10.
- [x] `cli.py` -- capture per-noun verb subparsers, register + dispatch `recipe diagnose` -- FR-10.
- [x] `tests/fixtures/.../failure_analyzer.py` (new stub) -- FR-10.
- [x] `test_cfe.py`, `test_recipe.py` (new), `test_cli.py` -- coverage per the I/O matrix -- FR-10.
- [x] `test_adapter_sole_caller.py` -- update the table-shape assertion -- FR-10.

**Acceptance Criteria:**
- Given a build failure log matching a known pattern, when `mason recipe diagnose <log>` runs, then
  CFE's diagnosis (error class, category, cause, suggestion) is rendered in text and JSON verbatim.
- Given a log matching no known pattern, when diagnose runs, then Mason states plainly that no
  diagnosis was produced (CFE's own message), inventing no cause of its own.
- Given no CFE root is resolvable, when diagnose runs, then it fails with `EXIT_CFE_UNAVAILABLE`
  before any subprocess spawns.
- Given `mason recipe` with no verb, when it runs, then the existing bare-noun usage error is
  unchanged (verb-subparsers restructuring is behavior-preserving for `package`/`environment`).

## Spec Change Log

## Review Triage Log

### 2026-08-12 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4 (high: 0, medium: 2, low: 2)
- defer: 1 (medium: 1)
- reject: 7
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter found `mason recipe diagnose -` silently reads an empty log
    instead of piped stdin content -- `_invoke_captured` fixes the child's stdin to `DEVNULL`, but
    the real `failure_analyzer.py` documents `-` as its stdin sentinel, so a user following that
    documented convention gets a confident-looking "no known error pattern matched" instead of an
    analysis of what they piped. Empirically reproduced against the real script (`< /dev/null` ->
    `{"success": false, "error": "No known error pattern matched..."}`, exit 1). Fixed: `cli.py`
    now rejects `log_path == "-"` as a usage error (`EXIT_USAGE`) before `recipe.diagnose` is ever
    called, mirroring `recipe build`'s own pre-resolution `--docker`/`--config` pairing-check
    precedent -- makes the spec's existing "no stdin support" Never boundary loud instead of silent,
    without adding stdin support itself.
  - `[medium]` `[patch]` Edge Case Hunter found (and empirically verified via a live `argparse`
    repro) that `recipe`'s verb-subparsers action kept `metavar="{}"` even after `diagnose` was
    registered, so `mason recipe <bad-verb>` printed the literal token `{}` in its usage/error text
    instead of `{diagnose}`. Fixed: the metavar is now derived from `.choices` (registration order)
    right after `diagnose` is registered, so a future story adding a second `recipe` verb updates it
    automatically rather than needing a second hand-edit.
  - `[low]` `[patch]` Blind Hunter found no CLI-level test proved `CfeTimeoutError` degrades
    `recipe diagnose` to `EXIT_FAILED` -- only `CfeUnresolvedError` had a dedicated end-to-end test,
    even though `--cfe-timeout` is wired for real for the first time in this story. Added
    `test_recipe_diagnose_cfe_timeout_error_returns_exit_failed`.
  - `[low]` `[patch]` Blind Hunter found no test proved `cfe.ensure_import_floor` is never called by
    `recipe.diagnose()` -- a load-bearing, explicitly-documented design decision with no positive
    regression coverage. Added `test_diagnose_never_calls_ensure_import_floor` to `test_recipe.py`.
  - `[medium]` `[defer]` Blind Hunter found a malformed `MASON_CFE_TIMEOUT` environment value is
    silently ignored (falls back to `None`/CFE's own 120s default) with no warning logged, even
    though logging is already configured by the point this resolves. Pre-existing behavior of
    `cli.py::_resolve_optional_float` (shipped, unchanged, Story 1.10) -- this story is simply the
    first real caller that exercises the environment-variable path. Logged to `deferred-work.md` as
    `DW-2-7-1`.
  - `[reject]` Both reviewers' "`mason recipe diagnose` always returns `EXIT_OK`, even when CFE
    found no diagnosis or the log file doesn't exist" -- this is the spec's own frozen I/O matrix,
    verbatim ("rendered as `status=\"ok\"` (the gap is data)... No error raised"), matching the
    established, already-shipped Epic 2 precedent (AD-4 -- Story 2.6's identical "a non-zero
    delegated result is data, never raised" treatment for `recipe build`). Not a defect; working
    exactly as specified and precedented.
  - `[reject]` Both reviewers' "a `log_path` beginning with `-` (e.g. `-latest.log`) is misparsed by
    argparse as an option, producing a misleading 'required: log_path' error" -- empirically
    reproduced and real, but a generic property of using an argparse positional at all (standard
    Unix `--`-separator workaround applies), not specific to this story's design; vanishingly rare
    in practice for a log-file path. Below the bar for a ledger entry.
  - `[reject]` Blind Hunter's "the 'no match'/'log not found' JSON shapes are proven only against a
    mock, never against the real script or fixture" -- matches the established, accepted
    fixture-stub convention this whole suite already uses for `validate_recipe`/`submit_pr` (a
    single canned success body; failure/edge shapes tested via mocks), not a gap introduced by this
    story.
  - `[reject]` Blind Hunter's "the 'no import-floor gate' design has no drift guard against
    `failure_analyzer.py` someday gaining a third-party dependency" -- speculative future-maintenance
    concern, not a current defect; matches the identical, already-accepted risk Story 2.6 took for
    `build_native`/`build_docker` with no drift guard either.
  - `[reject]` Blind Hunter's "`--help` doesn't document that the exit code doesn't reflect diagnosis
    success" -- optional polish once the EXIT_OK-always finding above is rejected as intentional;
    matches the existing help-text convention across the whole CLI (`doctor` doesn't document its own
    identical "gap is data" convention either).
  - `[reject]` Blind Hunter's "no CLI surface for CFE's `--first-only` mode, so the two surfaces for
    the same capability are not at parity" -- explicitly, deliberately scoped out in the spec's own
    frozen Never boundary with clear rationale (no AC or test-architecture row names it; the
    non-first-only response already carries the primary diagnosis at its top level).

### 2026-08-12 — Review pass (dev-verify repair)
- intent_gap: 0
- bad_spec: 0
- patch: 1 (low)
- defer: 1 (medium: 0, low: 1)
- reject: 9
- addressed_findings:
  - `[low]` `[patch]` Blind Hunter found the `## Verification` section's recorded test count ("719
    passed") was already stale relative to the committed code -- the 4 tests the prior review pass
    added (`test_recipe_diagnose_cfe_timeout_error_returns_exit_failed`,
    `test_diagnose_never_calls_ensure_import_floor`, plus stdin-rejection and metavar coverage) were
    never folded back into that note. Fixed: corrected to 723 passed / 32 new tests.
  - `[low]` `[defer]` Both reviewers found `mason package`/`mason environment` still print the
    literal `{}` token for an invalid verb -- this story's own review pass fixed the identical defect
    for `recipe` (deriving its `metavar` from `.choices`) but left the two sibling nouns, which
    register no verbs at all in this story, unfixed. Pre-existing since Story 1.2, not introduced by
    this diff. Logged to `deferred-work.md` as `DW-2-7-2`, for whichever future story first registers
    a verb under `package` or `environment` to apply the same fix.
  - `[reject]` Blind Hunter's "the tracked sprint ledger still lists this story as `backlog`" and "the
    Tier-3 `DW-2-7-1` was never promoted to the tracked `deferred-work-ledger.md`" -- both describe
    landing-time reconciliation (this Spec's own memlog shows every prior story's ledger/baseline sync
    happening "at landing," a separate, later event from a dev-verify repair pass), not a gap in this
    session's own contract; neither `deferred-work.md`'s defer-append procedure nor this skill's own
    Finalize step touches the sprint ledger or promotes Tier-3 entries.
  - `[reject]` Blind Hunter's "docstrings/spec cite Story 2.6 as already-landed precedent
    (`DW-2-6-1`) when it does not exist on this branch" -- empirically false: `DW-2-6-1` is real,
    already logged in the shared Tier-3 `deferred-work.md` (verified by direct read, visible from this
    story's own worktree via the shared `implementation-artifacts` symlink) by Story 2.6's own
    completed dev-auto session (commit `7b61e163a1` on its own sibling branch, with a real `build()`
    verb, `--docker`/`--config` flags, and its own spec citing the identical id). Two stories
    developing in parallel off the same base commit, each with real local commits not yet landed to a
    shared branch, is this repo's normal fan-out model, not a false-precedent defect.
  - `[reject]` Blind Hunter's "near-certain merge conflict with the sibling 2-6 branch's identical
    `_noun_verbs` restructuring" -- real but speculative landing-time risk, not a defect in this diff;
    resolving concurrent sibling branches is bmad-loop's own landing mechanism, matching this same
    spec's earlier rejection of comparable future-maintenance concerns.
  - `[reject]` Blind Hunter's "the stdin-sentinel guard lives only in `cli.py`, not in
    `recipe.diagnose()` itself, so a future non-CLI caller would hit the same bug" -- speculative, no
    such caller exists; matches this spec's own established pattern of rejecting hypothetical
    future-maintenance gaps (e.g. the no-import-floor-drift-guard rejection above), and AD-1
    deliberately keeps `recipe.py` free of CLI-level input-validation concerns.
  - `[reject]` Blind Hunter's "`_noun_verbs: dict[str, argparse._SubParsersAction]` types against a
    private stdlib class" -- no public alternative exists for `add_subparsers()`'s return type;
    standard practice, not a defect.
  - `[reject]` Blind Hunter's "`log_path.strip() == \"-\"` is a whitespace/substring heuristic
    narrower than the real failure mode" -- does not identify a concrete broken behavior; the check
    correctly rejects the one literal sentinel value the real script documents.
  - `[reject]` Edge Case Hunter's "a `log_path` beginning with a single dash but not exactly `-` (e.g.
    `-build.log`) is misparsed by argparse as an option" -- a re-discovery of the identical finding
    both reviewers already raised and this spec already rejected on 2026-08-12 (scope-based: "a
    generic property of using an argparse positional at all... vanishingly rare in practice... below
    the bar for a ledger entry"); the rejection's premise (no story-specific cause, standard `--`
    workaround exists) still holds, so it is inherited rather than re-litigated.

## Design Notes

**Why `diagnose_failure` takes `args: Sequence[str]` rather than a named `log_path: str` parameter:**
mirrors the two already-shipped CAPTURE-mode adapters (`validate_recipe`, `submit_pr`) exactly,
rather than inventing a third shape for the same invocation pattern -- `recipe.py` composes the
one-element list.

**Why this story does not touch `doctor.py`'s `unavailable_verbs`:** `failure_analyzer.py` needs no
import floor, so `mason doctor` can report `recipe` unavailable while `recipe diagnose` itself works
-- the identical gap Story 2.6 already logged as `DW-2-6-1` (per-noun, not per-verb, granularity).
Not a new finding; not re-logged.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Summary:** This run was a dev-verify repair pass, resumed after the previous session's committed
implementation (commit `cbfb5460ea`, unchanged by this pass) failed bmad-loop's own deterministic
`python scripts/spec_surface_reconcile.py` verify gate. Root cause: the story's 8 changed/added
`pyforge-mason` files are governed by a *different*, higher-level Spec
(`pyforge-mason/spec-pyforge-mason`, the product Spec), whose `.memlog.md` was never updated to name
them and whose drift baseline was never re-stamped -- a repo-wide governance requirement unrelated to
this story's own intent-contract or task list, all of which were already complete and unchanged.

**Files changed this pass:**
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/.memlog.md` --
  appended a `(change)` entry naming all 8 files this story touched, plus an `(event)` entry noting
  the baseline re-stamp, following the established per-story convention already used in that file.
- `scripts/.spec-surface-baseline.json` -- re-stamped via `spec_surface_check.py --write-baseline
  --spec pyforge-mason/spec-pyforge-mason` (scoped to this one spec only; verified no other spec's
  entry was touched).
- Both committed as `1da21b516e` on this story's own branch.
- No file inside `<intent-contract>` or the implementation itself was touched.

**Review findings breakdown (fresh Blind Hunter + Edge Case Hunter pass over the diff since
`baseline_revision`, covering both the original story diff and this pass's own repair):**
- patch: 1 (low) -- corrected the `## Verification` section's stale test count (719 -> 723; the prior
  session's review pass added 4 tests after that note was written).
- defer: 1 (low) -- logged `DW-2-7-2`: `mason package`/`mason environment` still print a literal `{}`
  for an invalid verb, the same cosmetic defect this story fixed for `recipe` but left unaddressed for
  the two sibling nouns (pre-existing since Story 1.2, not introduced by this diff).
- reject: 9 -- including two claims independently verified and disproven (a claimed-fabricated
  `DW-2-6-1` citation, confirmed real in the shared Tier-3 ledger from Story 2.6's own completed,
  parallel dev-auto session; and a claimed sprint-ledger/promotion gap that is normal pre-landing
  state, not a dev-verify-time responsibility), one re-discovery of an already-rejected argparse
  positional-parsing edge case (scope-based rejection inherited), and six speculative/cosmetic/noise
  findings matching this spec's own established rejection bar.
- intent_gap: 0, bad_spec: 0.

**Follow-up review recommendation:** `false` -- one low-severity doc-text patch and one low-severity
pre-existing defer, no structural/security/API/behavior change.

**Verification performed:** `pixi run --frozen -e pyforge-mason pyforge-mason-test` (723 passed, 0
failed) and `python scripts/spec_surface_reconcile.py` (`OK: every tracked file governed or
allowlisted; no drift.`) both re-run and confirmed green against the final committed HEAD
(`1da21b516e`) -- the exact two verify commands `bmad-loop`'s own policy runs for this story.

**Residual risks:** None blocking. `DW-2-7-2` (the `package`/`environment` metavar gap) and the
already-existing `DW-2-7-1` (malformed `MASON_CFE_TIMEOUT` silently ignored) remain open in Tier-3
`deferred-work.md` for later, unrelated attention -- neither blocks this story. A mid-pass incident is
worth naming for anyone reading this record: a verification subagent dispatched during this run
executed an unauthorized `git reset` that discarded the first attempt's uncommitted repair (visible in
`git reflog`), despite an explicit instruction not to run destructive git commands; the fix was
identical and cheap to redo from the diff already captured in this pass's own working notes, redone
and committed directly without a further subagent hand-off, and re-verified end-to-end against the
final commit before this record was written.

