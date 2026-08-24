---
title: 'Manifest discovery'
type: 'feature'
created: '2026-08-15'
status: 'done'
baseline_revision: '51262819e76bde4d19c9511b20925e815b1c0503'
final_revision: '541358ac31565691a7d84ee09ec49627b2c821ba'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `mason environment lock`/`environment check` (Stories 4.3/4.4, both done) require the
caller to name every manifest explicitly (`manifest_path` is `nargs="+"`) -- Mason cannot yet find a
project's manifests on its own, so a user must enumerate `pyproject.toml`/`environment.yml`/
`requirements*.txt`/`pixi.toml` by hand every invocation.

**Approach:** Add `environment.py::discover_manifests(directory)`, a pure function that locates the
four manifest kinds in one directory (never recursive, never walking upward -- unlike `resolve.py`'s
CFE-root walk). `cli.py` calls it only when the `manifest_path` positional is empty (relaxed from
`nargs="+"` to `nargs="*"` on both verbs), against `Path.cwd()`, prints the discovered list to
stderr, then feeds the result into the existing `environment.lock()`/`environment.check()` unchanged.
Explicit `manifest_path` arguments skip discovery entirely -- `lock()`/`check()`'s own signatures do
not change.

## Boundaries & Constraints

**Always:**
- `discover_manifests(directory: Path) -> tuple[str, ...]` lives in `environment.py` (mirrors
  `lock()`/`check()`'s own home), takes an explicit `Path` (no internal `Path.cwd()` call -- mirrors
  `resolve_cfe_root`'s `start_directory` parameter precedent), and is pure: no I/O beyond reading the
  one given directory, never raises for anything except the not-found case below.
- Checks, in this fixed order, each returned as `str(directory / name)`: `pyproject.toml`,
  `environment.yml`, then every `directory.glob("requirements*.txt")` match sorted lexically, then
  `pixi.toml`. Existence is `.is_file()` on the literal names; the glob is the only wildcard (spec
  Intent: "requirements*.txt" is the one pattern in the AC, not a general glob).
- Raises `EnvironmentManifestsNotFoundError(directory, filenames)` (new, `errors.py`) when nothing
  matches -- `directory` is `str(directory)`, `filenames` is exactly the four literal patterns
  searched (`("pyproject.toml", "environment.yml", "requirements*.txt", "pixi.toml")`), in that order
  -- mirrors `ShipCredentialMissingError`'s `Sequence[str]`-field validation-and-`__reduce__` shape.
- `cli.py`'s `environment lock`/`environment check` dispatch: when `ns.manifest_path` is empty,
  call `environment.discover_manifests(Path.cwd())`, print `f"discovered manifests: {', '.join(paths)}"`
  to `sys.stderr` (a plain `print(..., file=sys.stderr)`, not `logging` -- the default `WARNING`
  logging level would silently hide an `INFO`-level notice from a non-`--verbose` run, and this is a
  result the user needs to see, not debug chatter), THEN call `environment.lock()`/`.check()` with
  the discovered tuple. Explicit `manifest_path` arguments never trigger discovery and never print
  this line (spec Intent: "explicit paths override discovery entirely").
- `manifest_path`'s argparse registration on both verbs changes `nargs="+"` to `nargs="*"` only --
  no new flag is added; "a project directory" (AC1) is always `Path.cwd()`, matching `package ship`'s
  identical established precedent (`project_path` is always `Path.cwd()`, never a flag).
- `lock()`/`check()` signatures in `environment.py` do not change -- `cli.py` resolves
  explicit-or-discovered `manifest_paths` before either is called, exactly as their existing
  docstrings already describe the caller's responsibility.

**Block If:** a live grep of `environment.py`/`errors.py` at execution time shows
`discover_manifests`/`EnvironmentManifestsNotFoundError` already defined (a concurrent story landed
first) -- reconcile with an operator rather than overwriting.

**Never:**
- No recursive search, no upward directory walk, no new CLI flag (e.g. `--directory`) for the
  discovery root -- out of scope; `Path.cwd()` is the only root discovery ever searches.
- No change to `LockResult`/`CheckResult` (`models.py`) or to `condalock.py` -- both already carry
  `manifest_paths` and neither needs to know whether that tuple came from discovery or the user.
- No gating of the stderr discovery-notice line behind `--verbose`/`--quiet` -- out of scope for this
  Small story; always printed when discovery runs, never otherwise.
- No pre-validation of `Path.cwd()`'s readability -- an unreadable cwd surfaces as whatever
  `Path.glob`/`Path.is_file` itself raises, uncaught, matching every other path operation in this
  package's "no Mason-side pre-validation" default (spec Always boundary of Stories 4.1/4.3/4.4).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| All four kinds present | dir has `pyproject.toml`, `environment.yml`, `requirements.txt`, `pixi.toml` | Returns all four, in the fixed order, each `str(directory / name)` | No error expected |
| Subset present | dir has only `pixi.toml` | Returns one-element tuple `(str(directory / "pixi.toml"),)` | No error expected |
| Multiple `requirements*.txt` | `requirements.txt` + `requirements-dev.txt` | Both returned, sorted lexically, positioned between `environment.yml` and `pixi.toml` | No error expected |
| Nothing found | empty directory | -- | `EnvironmentManifestsNotFoundError` naming the directory and all four literal patterns |
| `manifest_path` omitted, CLI dispatch | `mason environment lock -o lock.yml` in a dir with manifests | Discovery runs against `Path.cwd()`; discovered list printed to stderr; `environment.lock()` called with the discovered tuple | No error expected |
| `manifest_path` omitted, nothing discoverable | `mason environment lock -o lock.yml` in an empty dir | No stderr discovery line; `EnvironmentManifestsNotFoundError` propagates to `main()`'s `except MasonError` handler | `EXIT_FAILED`, message on stderr, no traceback |
| Explicit `manifest_path` given | `mason environment lock env.yml -o lock.yml` | Discovery never called, no stderr discovery line; `env.yml` passed straight through (unchanged from current behavior) | No error expected |

</intent-contract>

## Code Map

- `src/pyforge/mason/environment.py` -- add `discover_manifests()`; update the module docstring's
  "Manifest auto-discovery (Story 4.2) is not yet built" framing (now built); `lock()`/`check()`
  unchanged.
- `src/pyforge/mason/errors.py` -- add `EnvironmentManifestsNotFoundError`.
- `src/pyforge/mason/cli.py` -- `environment_lock_parser`/`environment_check_parser`'s
  `manifest_path` argument: `nargs="+"` to `nargs="*"`; both `environment lock`/`environment check`
  dispatch branches gain the empty-check to discovery-call-print sequence; the two comment blocks at
  the current `manifest_path` registrations that describe Story 4.2 as future work get corrected.
- `tests/unit/test_environment.py` -- new: `discover_manifests()` coverage (real `tmp_path`, no
  mocking -- mirrors `test_resolve.py`'s style for this codebase's other pure directory-walking
  function).
- `tests/unit/test_cli.py` -- rewrite `test_environment_lock_missing_manifest_path_is_a_usage_error`
  (omitting `manifest_path` is no longer a usage error) and its `environment check` counterpart if
  one exists; add discovery-triggered-path and explicit-path-bypasses-discovery coverage for both
  verbs, patching `pyforge.mason.cli.environment.discover_manifests` (mirrors the existing
  `pyforge.mason.cli.environment.lock`/`.check` patch-target convention -- never touches the real
  filesystem or `Path.cwd()` from a CLI-dispatch-level test).
- `tests/unit/test_errors.py` -- extend with `EnvironmentManifestsNotFoundError` coverage, mirroring
  `ShipCredentialMissingError`'s existing test shape.
- `src/pyforge/mason/resolve.py` -- read-only reference for the "pure function takes an explicit
  directory, caller supplies `Path.cwd()`" shape this story mirrors.

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/mason/errors.py` -- add `EnvironmentManifestsNotFoundError(directory: str,
  filenames: Sequence[str])`: identifier `environment:manifests-not-found`, validates both args
  non-empty (mirrors `PackageProjectPathError`/`ShipCredentialMissingError`'s validation rigor),
  stores `directory`/`filenames` (`filenames` as a `tuple`), message names the directory and lists
  the filenames searched, `__reduce__` returning `(self.__class__, (self.directory, self.filenames))`.
- [x] `src/pyforge/mason/environment.py` -- add `discover_manifests(directory: Path) ->
  tuple[str, ...]` per the Always boundary's fixed-order/glob rules; update the module docstring.
- [x] `src/pyforge/mason/cli.py` -- change both `manifest_path` registrations to `nargs="*"`; in both
  dispatch branches, when `ns.manifest_path` is falsy, call `environment.discover_manifests(Path.cwd())`,
  print the discovery line to `sys.stderr`, use the returned tuple as `manifest_paths` for the
  `environment.lock()`/`.check()` call that follows; correct the two now-stale comment blocks.
- [x] `tests/unit/test_environment.py` -- `discover_manifests()`: all four present; a subset present;
  multiple `requirements*.txt` matches sorted correctly; empty directory raises
  `EnvironmentManifestsNotFoundError` with the right directory and all four literal patterns named.
- [x] `tests/unit/test_cli.py` -- for both `environment lock` and `environment check`: omitted
  `manifest_path` with discovery finding manifests (discovery called, stderr line present, discovered
  tuple passed through to the patched `lock`/`check`, `EXIT_OK`); omitted `manifest_path` with
  discovery raising (no stderr discovery line, `EXIT_FAILED`, no traceback); explicit `manifest_path`
  given (discovery never called, no stderr discovery line, unchanged existing behavior preserved);
  rewrite the now-incorrect `test_environment_lock_missing_manifest_path_is_a_usage_error`.
- [x] `tests/unit/test_errors.py` -- extend with `EnvironmentManifestsNotFoundError`: identifier,
  stored fields, message content, `MasonError` subclass-ness, `str()` format, deepcopy/pickle
  round-trip via `__reduce__`.

**Acceptance Criteria:**
- Given a project directory containing any of the four manifest kinds, when `discover_manifests` runs
  against it, then every present kind is located and returned, `requirements*.txt` matches sorted.
- Given `mason environment lock`/`environment check` invoked with no `manifest_path` arguments, when
  discovery finds manifests in `Path.cwd()`, then the discovered list is printed to stderr before the
  engine call, and that discovered tuple -- not an empty one -- is what `environment.lock()`/
  `.check()` receives.
- Given explicit `manifest_path` arguments, when either verb runs, then `discover_manifests` is never
  called and no discovery line appears on stderr -- unchanged from current (pre-4.2) behavior.
- Given no manifests found by discovery, when either verb runs with `manifest_path` omitted, then the
  process exits `EXIT_FAILED` with `EnvironmentManifestsNotFoundError`'s message on stderr naming the
  searched directory and all four literal patterns, and no traceback.
- Given the Mason codebase, when `tests/meta/test_capability_tiers.py`,
  `tests/meta/test_dependency_direction.py`, and `tests/meta/test_render_ownership.py` run against
  the tree with these changes, then they still pass unmodified -- `discover_manifests` does no
  subprocess/CFE work and the new stderr print targets `sys.stderr`, never `sys.stdout`.

## Spec Change Log

## Review Triage Log

### 2026-08-15 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 0, medium 1, low 3)
- defer: 0
- reject: 8: (high 0, medium 0, low 8)
- addressed_findings:
  - `[medium]` `[patch]` Both reviewers independently found `discover_manifests`'s `requirements*.txt`
    glob branch never called `.is_file()`, unlike the three literal-name checks -- a directory or
    symlink-to-directory matching the glob pattern (e.g. a directory literally named
    `requirements-lock.txt`) was silently accepted and would have been handed straight to
    `condalock.lock()`/`check()`, contradicting the function's own docstring. Empirically confirmed
    before patching. Fixed: added `if path.is_file()` to the glob comprehension.
  - `[low]` `[patch]` Blind Hunter found `_MANIFEST_FILENAMES` (used only for the not-found error
    message) and `discover_manifests`'s actual scan literals had no shared source of truth -- a
    future edit to one could silently drift from the other with no test catching it. Fixed:
    `discover_manifests` now destructures and reads from `_MANIFEST_FILENAMES` itself instead of
    retyping the four names as separate literals (folded into the same edit as the `.is_file()` fix
    above, same function).
  - `[low]` `[patch]` Both reviewers independently found `EnvironmentManifestsNotFoundError.__init__`
    validated `filenames` as a non-empty tuple but never validated that individual entries were
    non-empty strings -- `EnvironmentManifestsNotFoundError("/proj", ("", ""))` constructed
    successfully and produced a garbled message ("looked for , "), deviating from this spec's own
    Always boundary ("mirrors `ShipCredentialMissingError`'s ... validation rigor," which includes
    an identical per-entry check). Empirically confirmed before patching. Fixed: added the elementwise
    `isinstance(item, str) and item.strip()` check, matching `ShipCredentialMissingError`'s exact
    pattern; added `test_environment_manifests_not_found_error_rejects_a_blank_filenames_entry`.
  - `[low]` `[patch]` Blind Hunter found no test invoked the CLI with `--quiet` to confirm the
    discovery notice line still prints, even though the code comment and spec Never boundary both
    claim it is never gated behind `--verbose`/`--quiet`. Fixed: added
    `test_environment_lock_discovery_line_is_not_gated_by_quiet`.
  - Rejected (noise, or matches deliberate existing precedent/spec decision, no action): the
    copy-pasted discovery-dispatch block between `environment lock`/`environment check` in `cli.py`
    instead of a shared helper matches this same file's existing precedent of duplicating logic
    between the two verbs (`--platform` parsing is "verbatim-mirrored" between `lock()`/`check()` per
    Story 4.4's own docstring); the stderr discovery line "bypassing render.py/breaking the JSON
    contract" mischaracterizes the actual contract -- `render.py`'s own guarantee is scoped to
    **stdout** carrying exactly one JSON document under `--format json`, which this change does not
    touch, and the stderr line is a deliberate, spec-mandated design decision (spec Design Notes);
    the `list` vs `tuple` container-type asymmetry between explicit and discovered `manifest_paths`
    has no behavioral consequence -- both `lock()`/`check()` normalize via `tuple(manifest_paths)`
    before constructing their result dataclass; `_MANIFEST_FILENAMES`'s name/docstring ("four literal
    patterns") allegedly misleading a user into creating a file named `requirements*.txt` verbatim
    matches the PRD FR-26 AC's own established wording, not an implementer invention; no test for
    `discover_manifests` against a non-existent/non-directory path was independently investigated by
    Edge Case Hunter and confirmed to degrade gracefully (`.is_file()`/`.glob()` return `False`/empty
    rather than raising), matching this spec's own explicit Never boundary (no pre-validation of
    `Path.cwd()`'s readability); no test for both `-o`/`--lockfile` and `manifest_path` omitted
    together was empirically verified against the live parser -- `argparse`'s `required=True` on the
    flag still fires correctly regardless of the now-optional positional, standard, unchanged
    behavior; `sorted(directory.glob(...))` sorting `Path` objects rather than literal strings has no
    behavioral difference from "sorted lexically" for same-directory siblings (`Path.__lt__` compares
    parts, which reduces to the final-component string for siblings); the module docstring narrating
    Story 4.2 as landing chronologically after Stories 4.3/4.4 is factually accurate, not narrative
    drift -- this spec's own Intent states both were already `done` before this story started.

## Design Notes

The stderr discovery-notice line deliberately bypasses `render.py`/the JSON envelope: `render.py`'s
own docstring guarantees "under `--format json` stdout carries exactly one JSON document," so a
second `render.write()` call before the real result would violate that invariant. `LockResult`/
`CheckResult.manifest_paths` already carries the resolved (explicit-or-discovered) list into the
JSON/text result too -- the stderr line is a human-facing, non-contractual heads-up, not a second
copy of the contract.

`tests/meta/test_render_ownership.py`'s AST guard only forbids **stdout** writes outside
`cli.py`/`render.py` (confirmed by reading its own regression fixtures) -- a `print(...,
file=sys.stderr)` from `cli.py` is unrestricted and does not need a meta-test exemption.

## Verification

**Commands:**
- `pixi run -e pyforge-mason pyforge-mason-test` -- expected: all unit + meta tests pass, including
  the new `discover_manifests`/`EnvironmentManifestsNotFoundError` coverage and the rewritten
  `environment lock`/`environment check` CLI dispatch tests; `test_capability_tiers`/
  `test_dependency_direction`/`test_render_ownership`/`test_no_recipe_knowledge` remain green.

## Auto Run Result

Status: done

**Summary.** Implemented Story 4.2 (Manifest discovery): `environment.py::discover_manifests()`
locates `pyproject.toml`/`environment.yml`/`requirements*.txt`/`pixi.toml` in one directory
(non-recursive, no upward walk). `cli.py`'s `manifest_path` positional on both `environment lock`
and `environment check` relaxed from `nargs="+"` to `nargs="*"`; when omitted, discovery runs
against `Path.cwd()`, the discovered list prints to stderr, and the result feeds unchanged into the
existing `environment.lock()`/`.check()`. Explicit `manifest_path` arguments still bypass discovery
entirely. New `EnvironmentManifestsNotFoundError` names the searched directory and all four patterns
when nothing is found.

**Files changed:**
- `src/pyforge/mason/errors.py` -- new `EnvironmentManifestsNotFoundError`.
- `src/pyforge/mason/environment.py` -- new `discover_manifests()`; updated module docstring.
- `src/pyforge/mason/cli.py` -- `manifest_path` `nargs="+"` to `nargs="*"` on both verbs; discovery
  fallback + stderr notice wired into both dispatch branches; stale comments corrected.
- `tests/unit/test_environment.py` -- 6 new `discover_manifests()` tests (real `tmp_path`, no mocking).
- `tests/unit/test_errors.py` -- 12 new `EnvironmentManifestsNotFoundError` tests.
- `tests/unit/test_cli.py` -- replaced the two now-incorrect usage-error tests with 4 tests per verb
  (discovery-finds-manifests, discovery-raises, explicit-path-bypasses-discovery, `--quiet` coverage).

**Review findings breakdown (Blind Hunter + Edge Case Hunter, run in parallel, no shared context):**
4 patch (1 medium, 3 low), 0 intent_gap, 0 bad_spec, 0 defer, 8 reject. All 4 patches applied:
a real bug (the `requirements*.txt` glob branch skipped the `.is_file()` check the three literal-name
branches had, silently accepting a directory match -- empirically reproduced before fixing);
`discover_manifests` now reads its four names from `_MANIFEST_FILENAMES` instead of duplicating them
as separate literals; `EnvironmentManifestsNotFoundError` gained elementwise non-empty-string
validation on `filenames`, closing a gap against this spec's own "mirrors `ShipCredentialMissingError`'s
validation rigor" boundary; added a `--quiet` test confirming the discovery line is genuinely never
gated. The 8 rejected findings were investigated individually (one empirically re-verified against the
live parser, one against `render.py`'s actual stdout-only contract) and found to be noise, matches for
already-deliberate spec decisions, or matches for existing codebase precedent -- full reasoning in the
Review Triage Log above.

**Follow-up review recommendation:** `false` -- all patches were small, localized, low/medium-severity
fixes within functions the reviewers already covered; volume and consequence do not warrant an
independent follow-up pass.

**Verification performed:**
- `pixi run -e pyforge-mason pyforge-mason-test` -- **1525 passed, 2 deselected** (was 1522 before the
  review-pass patches; +3 for the new `.is_file()`-glob, blank-filenames-entry, and `--quiet` tests).
- `pixi run -e pyforge-mason ruff check` on the six changed files -- 7 pre-existing findings, identical
  before and after this story's changes (verified via `git stash`/`git stash pop`); zero new findings.
- `python scripts/spec_surface_reconcile.py` -- `OK: every tracked file governed or allowlisted; no
  drift.`
- `git status --porcelain` -- confirmed only the 6 intended files under `pyforge-mason` changed; no
  other project's governed surface touched.

**Residual risks:** none identified. This story's own AC5 (meta-test invariants) was verified directly
rather than assumed: `test_capability_tiers`/`test_dependency_direction`/`test_render_ownership`/
`test_no_recipe_knowledge` all pass unmodified with `discover_manifests` and the new error class in
place.
