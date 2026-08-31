---
title: 'mason environment lock'
type: 'feature'
created: '2026-08-14'
status: 'done'
baseline_revision: '64e717d13554938e03ceac5a6a98c2aae407b957'
final_revision: 'f003a34c2f5417e56819d5b16e59ec65352ee1dd'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `environment.py` is still a docstring-only stub and the `environment` noun registers
no verbs; there is no way to actually produce a lockfile from Story 4.1's `engines/condalock.py`
adapter.

**Approach:** Register `mason environment lock <manifest_path> [<manifest_path> ...] --output/-o
PATH [--platform PLATFORMS]` in `cli.py`, add `environment.py::lock()` as the thin orchestration
use-case calling `engines.condalock.lock()`, and add `models.LockResult` as its return shape --
mirroring `package.py::build()` / `PackageBuildResult`'s established engine-wrapping precedent
exactly. Story 4.2 (manifest auto-discovery) is not yet built, so this story requires manifest
paths explicitly as positionals; that positional's `nargs` narrows to allow omission once 4.2 lands.

## Boundaries & Constraints

**Always:**
- `environment.py` gains zero CFE dependency of any kind (`tests/meta/test_capability_tiers.py`
  already guards this file: no module-level `cfe` import, anywhere). Importing
  `engines.condalock` at module level is fine -- that module itself has no CFE dependency.
- `manifest_path` is a required positional, `nargs="+"` (argparse itself enforces "at least one" --
  no custom Mason error needed), named to signal Story 4.2 will later relax it to `nargs="*"` plus
  a discovery fallback. Mirrors `recipe_path`/`project_path`'s single-positional precedent, extended
  to plural.
- `--output`/`-o` is required, mirrors `recipe new --output`'s exact registration shape (Story 2.4).
- `--platform` is optional, a single comma-separated string flag (mirrors `--to`'s established
  "repeatable via comma-separation" idiom -- no `action="append"` precedent exists anywhere in
  `cli.py`). `cli.py` passes the raw string (or `None`) straight through; splitting/stripping into a
  tuple happens inside `environment.py::lock()`, mirroring `package.ship()`'s own
  raw-string-in/parsed-in-the-use-case-layer split for `--to` (package.py:307). No validation against
  a closed platform vocabulary -- Mason does not know every valid conda subdir; an invalid token
  surfaces as conda-lock's own non-zero returncode (AD-4), never a Mason-side check.
- `lock()` performs no pre-validation of manifest-path existence or `--output`'s parent directory --
  mirrors spec-4-1's own explicit precedent (`condalock.lock()` docstring) that a bad path surfaces
  as conda-lock's own non-zero returncode, never a Mason-side check.
- A non-zero delegated `condalock.lock()` returncode is DATA on `LockResult`, never raised (AD-4) --
  the dispatch branch always reports `"ok"`/`EXIT_OK` for a Mason-successful invocation, mirroring
  `package build`'s identical precedent.
- `EngineAbsentError`/`EnvironmentLockTimeoutError` (already defined, Story 4.1) propagate unchanged
  to `main()`'s existing top-level `except MasonError` handler -- no new handling in this dispatch
  branch.
- `models.LockResult`: `@dataclass(frozen=True)` in `models.py` (AD-8), mirrors `PackageBuildResult`'s
  plain-fields shape -- `manifest_paths: tuple[str, ...]`, `output_path: str`,
  `platforms: tuple[str, ...]`, `engine_name: str`, `engine_version: str | None`, `returncode: int`.
- `mason environment lock` succeeds with no CFE installation anywhere (spec AC, FR-25).

**Block If:** a live grep of `environment.py`/`models.py`/`cli.py` at execution time shows `lock()`,
`LockResult`, or an `environment lock` verb parser already defined (a concurrent story landed first)
-- reconcile with an operator rather than overwriting.

**Never:**
- No manifest auto-discovery in this story (Story 4.2's scope) -- omitting the manifest positional
  is a usage error (argparse), not a fallback to discovery.
- No lock-staleness checking (Story 4.4's scope).
- No `packaging`-based platform-string validation, no closed platform enum.
- No change to `engines/condalock.py` (Story 4.1, already landed and reviewed) beyond what its own
  existing `lock()` signature already supports.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path, one manifest | `mason environment lock environment.yml -o lock.yml` | `LockResult(returncode=0, ...)` rendered `"ok"` | No error expected |
| Multiple manifests | `... env.yml pyproject.toml -o lock.yml` | Both paths passed to `condalock.lock()` in order | No error expected |
| `--platform` supplied | `--platform linux-64,osx-arm64` | Split into `("linux-64", "osx-arm64")`, passed through | No error expected |
| `--platform` omitted | (no flag) | `platforms=()`; conda-lock's own default applies | No error expected |
| No manifest path given | `mason environment lock -o lock.yml` | Usage error (argparse `nargs="+"`) | `EXIT_USAGE`, no dispatch |
| `--output` omitted | (no flag) | Usage error (argparse `required=True`) | `EXIT_USAGE`, no dispatch |
| conda-lock absent | binary not on `PATH` | No lockfile written | `EngineAbsentError` (existing, via `main()`'s handler) |
| Solve fails | conda-lock exits non-zero | `LockResult(returncode!=0, ...)` still rendered `"ok"`/`EXIT_OK` (AD-4) | No error expected |
| Solve times out | child exceeds timeout | Metadata temp file removed (existing 4.1 behavior) | `EnvironmentLockTimeoutError` (existing, via `main()`'s handler) |

</intent-contract>

## Code Map

- `src/pyforge/mason/environment.py` -- add `lock()` use-case function.
- `src/pyforge/mason/models.py` -- add `LockResult` frozen dataclass.
- `src/pyforge/mason/cli.py` -- register `environment lock` verb parser; add dispatch branch.
- `src/pyforge/mason/engines/condalock.py` -- read-only; `lock()`/`CondaLockResult` this story calls.
- `src/pyforge/mason/package.py::build()` (lines 197-253) -- read-only reference for the
  engine-wrapping use-case shape this story mirrors.
- `src/pyforge/mason/package.py` (~line 307) -- read-only reference for the raw-string-in/
  parsed-in-the-use-case-layer comma-split pattern `--platform` mirrors.
- `tests/unit/test_environment.py` -- extend with `lock()` coverage (`LockResult`'s own coverage
  comes from here, not `test_models.py` -- mirrors `PackageBuildResult`'s precedent: composite
  orchestration results are covered via their use-case's tests, not a dedicated model test; only the
  primitive/enum-like models in `test_models.py` (`CfeResult`, `DoctorReport`, `ShipState`, ...) get
  direct construct/frozen/equality tests there).
- `tests/unit/test_cli.py` -- extend with `environment lock` dispatch coverage, mirroring
  `test_package_build_*` (lines 2533-2586).

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/mason/models.py` -- add `LockResult` frozen dataclass (fields per Always boundary).
- [x] `src/pyforge/mason/environment.py` -- add `lock(manifest_paths: Sequence[str], output_path: str,
  *, platforms: str | None = None) -> LockResult`: splits/strips `platforms` on `,` into a tuple
  (empty/`None` -> `()`, no validation), calls `engines.condalock.lock(manifest_paths, output_path,
  platforms=<parsed tuple>)`, wraps the returned `CondaLockResult` into `LockResult`.
- [x] `src/pyforge/mason/cli.py` -- register `_noun_verbs["environment"].add_parser("lock", ...,
  parents=[global_flags])` with positional `manifest_path` (`nargs="+"`) and `--output`/`-o`
  (`required=True`) and `--platform` (optional, `default=None`); add dispatch branch
  `if ns.noun == "environment" and ns.verb == "lock":` calling `environment.lock(ns.manifest_path,
  ns.output, platforms=ns.platform)` and `render.write(fmt, sys.stdout, "environment lock", "ok",
  dataclasses.asdict(result), [])`, returning `EXIT_OK`.
- [x] `tests/unit/test_environment.py` -- unit-test `lock()`: platform-string parsing (comma-split,
  omitted, empty), `CondaLockResult` -> `LockResult` field mapping, non-zero returncode passed
  through as data.
- [x] `tests/unit/test_cli.py` -- dispatch tests mirroring `test_package_build_*`: `--help` works;
  happy path text mode; happy path JSON mode (`_json_roundtripped` equality, mirroring
  `test_doctor_*`'s own tuple-field JSON precedent, not raw `dataclasses.asdict` -- `LockResult`
  carries tuple fields, which round-trip to JSON lists); missing manifest positional is a usage
  error; missing `--output` is a usage error; failed child still renders `ok`; `EngineAbsentError`
  propagation to `EXIT_FAILED` (extra, mirrors `test_package_build_engine_absent_error_*`).

**Acceptance Criteria:**
- Given `mason environment lock <manifest> -o <path>`, when it runs, then solving is delegated to
  `engines.condalock.lock()` and the result is rendered.
- Given `--platform` supplied one or more comma-separated values, when the command runs, then the
  lock covers exactly those platforms.
- Given no `--platform`, when the command runs, then `platforms=()` is passed through and
  conda-lock's own default applies (never invented by Mason).
- Given no CFE installation anywhere, when this command runs, then it succeeds
  (`test_capability_tiers.py` continues to pass with `environment.py` populated).

## Spec Change Log

## Review Triage Log

### 2026-08-15 — Review pass (verification-repair)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 13: (high 0, medium 0, low 13)
- addressed_findings:
  - none
- context: This pass reviewed the diff since `baseline_revision`, which now also includes a
  repair commit (`f003a34c2f`) that stamps a missing spec-surface baseline for the unrelated
  `spec-django-accelerator-framework` (a pre-existing landing-gap on `main`, same fix already
  merged there via PR #507/`491b4f693a`) -- required so this branch's own `spec_surface_reconcile.py`
  verify gate passes; it does not touch this story's `<intent-contract>` or any mason file. Blind
  Hunter + Edge Case Hunter found 13 total findings, all rejected: 2 were artifacts of the
  reviewer-prompt's own diff summarization (an elided `...` placeholder standing in for the real
  120-entry baseline JSON, and a miscounted "129" in that same placeholder comment -- verified live:
  the real file is valid JSON with exactly 120 entries, matching both the memlog's own count and the
  original verify failure's "120 file(s)"); 1 was a pre-existing constant (`_ENV_FORMAT`) the
  reviewer couldn't see outside the diff, confirmed already defined at `cli.py:154` and used
  identically by every other verb; 1 (bundling the unrelated repair into this story's branch) is
  inherent to the repair task as instructed (fix verification without touching the frozen intent
  contract) and is already kept surgical via a separate, independently revertable commit; 1
  (django-accelerator memlog timestamp `T01:45` vs. "landed 2026-08-14" elsewhere) is byte-for-byte
  copied from the already-reviewed, already-merged upstream fix, not new content; the remaining 7
  (singular `manifest_path` naming, inline dispatch vs. a `_dispatch_package_ship`-style helper, the
  near-vacuous `--help` assertion, no pre-validation of manifest-path existence, silently-dropped
  empty `--platform` tokens, no reported default when `--platform` is omitted, `--output`/manifest
  collision and duplicate-manifest-path guards) each either restate a Boundary already fixed by the
  spec's own frozen `<intent-contract>` (verbatim: `manifest_path` naming, no Mason-side
  pre-validation of paths, no closed platform vocabulary, comma-split-and-drop-empty parsing, `--to`'s
  established single-flag/no-dedup idiom) or duplicate a finding the 2026-08-14 pass already
  triaged and rejected with matching reasoning (the vacuous `--help` assertion, the unreported
  `--platform` default, duplicate-token non-dedup).

### 2026-08-14 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 0, medium 1, low 3)
- defer: 1: (high 0, medium 0, low 1)
- reject: 8: (high 0, medium 0, low 8)
- addressed_findings:
  - `[medium]` `[patch]` `models.LockResult` omitted `stdout`, the delegated `conda-lock`
    subprocess's captured diagnostic text -- a failed solve (`condalock.py`'s own docstring calls
    this "the routine expected outcome") left the CLI user with only `returncode: 1` and no way to
    see why, despite `LockResult`'s own docstring claiming to mirror `PackageBuildResult`, which
    DOES carry `pep517_stdout`/`pixi_stdout` for exactly this reason. Added `stdout: str` to
    `LockResult`, threaded `result.stdout` through in `environment.py::lock()`, and extended
    `test_environment.py`/`test_cli.py` fixtures and assertions to cover it (including a rendered
    failure-diagnostic-visible assertion in `test_environment_lock_failed_child_still_renders_ok`).
  - `[low]` `[patch]` No test exercised `EnvironmentLockTimeoutError` propagating through `main()`
    to `EXIT_FAILED`, despite both `cli.py`'s dispatch comment and `environment.py`'s docstring
    naming it alongside `EngineAbsentError` as the two errors `lock()` can raise, and only the
    latter being tested -- added `test_environment_lock_timeout_error_projects_to_exit_failed`.
  - `[low]` `[patch]` No test verified a non-empty `platforms` tuple survives `LockResult` ->
    JSON rendering (every existing dispatch test used a fixture with `platforms=()`, even the one
    supplying `--platform` on the command line, which only asserted the raw unparsed string reached
    the mock) -- added `_FIXED_LOCK_RESULT_WITH_PLATFORMS` and
    `test_environment_lock_renders_populated_platforms`.
  - `[low]` `[patch]` `test_environment_lock_missing_manifest_path_is_a_usage_error` asserted only
    the exit code and that the mock wasn't called, unlike its sibling
    `test_environment_lock_missing_output_is_a_usage_error` (added in the same hunk), which also
    asserts `--output` appears in stderr -- added an `assert "MANIFEST_PATH" in err` to match.
  - Deferred: `DW-4-3-1` -- `mason environment lock --help` still advertises
    `--cfe-root`/`--cfe-python`/`--cfe-timeout` despite the command's own help text declaring it
    "CFE-independent" (`parents=[global_flags]` bundles CFE flags with the genuinely shared ones);
    pre-existing on `package build` too (Story 3.2), so a proper fix is a `global_flags`-parent
    split touching both verbs at once, not a per-verb patch here.
  - Rejected (noise, or matches deliberate existing precedent, no action): omitting `--platform`
    renders `platforms: []` rather than the engine's actual resolved default -- `conda-lock`'s own
    stdout is empty and stderr is uncaptured on success (Story 4.1's own live-verified precedent),
    so there is no data anywhere in the call chain from which the true default could be recovered
    without changing `engines/condalock.py`, which this story's own Never boundary forbids; `--to`'s
    own established idiom already treats "reported" as "the caller's own input echoed back," matching
    this design exactly. `LockResult.output_path` is not nulled to `None` on a failed solve (unlike
    `PackageBuildResult`'s discovery-based path fields) -- deliberate: `output_path` is a static echo
    of the caller's own `--output` value (which the caller already knows), not a filesystem-discovery
    result, and `returncode` already fully disambiguates success/failure per this codebase's AD-4
    discipline throughout. Duplicate `--platform` tokens (`linux-64,linux-64`) are neither
    deduplicated nor rejected -- matches `package.py`'s own `--to` parser precedent, whose docstring
    explicitly leaves "what duplicate means" undecided by design. A manifest path or platform value
    starting with `-` is misparsed by argparse -- matches spec-4-1's own already-reviewed, rejected
    precedent ("matches every sibling adapter's identical unvalidated pass-through"). No CLI-level
    `--timeout` override exists for `condalock.lock()`'s own `timeout` parameter -- `errors.py`'s
    own `EnvironmentLockTimeoutError` docstring already states this is deliberate v1 scope ("v1
    exposes no per-lock timeout override... the message says so rather than pointing at a knob that
    does not exist"), and no story/epic AC requests one. `environment.lock()` performs no defensive
    check that `manifest_paths` is non-empty when called directly (bypassing the CLI's `nargs="+"`)
    -- matches this codebase's established "CLI boundary enforces its own constraints, the use-case
    layer trusts its sole caller" pattern (no other use-case function in this package re-validates
    argparse-guaranteed invariants), and an empty list would reach `condalock.lock()`'s own
    non-zero-returncode-as-data handling regardless. `test_environment_lock_help_works`'s
    `assert "lock" in ...` is a near-vacuous assertion -- matches `test_package_build_help_works`'s
    own identical, already-shipped assertion shape verbatim.

## Design Notes

`--platform`'s comma-separated-single-flag shape (not `action="append"`) is a direct match to
`--to`'s already-established idiom (`package ship --to pypi,conda-forge`) -- introducing a second,
inconsistent "repeatable" convention (`action="append"`) into the same CLI would violate this
codebase's own precedent even though `action="append"` is otherwise a more common argparse idiom.

`LockResult` is a new `models.py` shape rather than passing `CondaLockResult` straight to
`dataclasses.asdict()`, because `CondaLockResult` (an engine-layer shape) doesn't carry the
orchestration-level context (`manifest_paths`, `platforms` as actually requested) that the rendered
output needs -- mirrors `package.py::build()` wrapping `pep517`/`pixi` engine results into
`PackageBuildResult` rather than rendering an engine result directly.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Summary:** This session resumed a spec whose implementation and first review pass (2026-08-14)
were already complete and committed (`8d43c27537`), but whose deterministic verification
(`python scripts/spec_surface_reconcile.py`, one of bmad-loop's S-13.7 verify commands) failed.
The failure was `[drift-blind]`/`[no-baseline]` on a completely unrelated spec,
`pyforge-mason/spec-django-accelerator-framework` (surface `src/platform/**` +
`pyforge-steward`'s dashboard package), which landed on `main` at `f150dce382` with no
`.memlog.md` and no baseline stamp -- a pre-existing landing gap, not anything caused by this
story. The identical fix had already been reviewed and merged into `main` via PR #507
(`491b4f693a`, after this branch's `baseline_revision`); this session replicated that same,
already-reviewed fix into this branch so its own verify gate passes, without touching this
story's `<intent-contract>` or any mason file.

**Files changed (this session, commit `f003a34c2f`):**
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-django-accelerator-framework/.memlog.md` (new) -- reconciliation memlog naming the governed surface, byte-identical to the already-merged upstream fix.
- `scripts/.spec-surface-baseline.json` -- scoped baseline stamp for `pyforge-mason/spec-django-accelerator-framework` only (`--spec`-scoped `--write-baseline`, never a full unscoped stamp).

No mason source file (`cli.py`, `environment.py`, `models.py`, test files) was touched in this
session -- those were already complete and reviewed in the prior pass (commit `8d43c27537`).

**Review findings breakdown (this pass):** 0 patches, 0 deferred, 13 rejected (see Review Triage
Log 2026-08-15 entry for full reasoning per finding). Two rejected findings were artifacts of the
reviewer-prompt's own diff summarization, not real defects (verified live: the baseline JSON is
valid with exactly 120 entries, matching the memlog and the original verify failure's own count).
The remaining 11 either restate a Boundary already fixed by the frozen `<intent-contract>` or
duplicate a finding the 2026-08-14 pass already triaged and rejected with matching reasoning.

**Verification performed:**
- `python scripts/spec_surface_reconcile.py` -- now exits 0 (`OK: every tracked file governed or allowlisted; no drift.`), reproduced from a failing state before the repair.
- `pixi run -e pyforge-mason pyforge-mason-test` -- 1427 passed, 2 deselected (full suite, including the `test_capability_tiers`/`test_dependency_direction` meta tests named in this spec's own Verification section).

**Residual risks:** None identified for this story's own scope. The `spec-django-accelerator-framework` baseline stamp is a mechanical hash-of-current-disk-state operation (same mechanism used throughout this repo's spec-surface governance); it does not and cannot itself verify that the governed `src/platform/**`/dashboard trees are semantically correct, only that they now have a tracked baseline to drift-check against going forward -- this matches the already-accepted precedent from PR #507 exactly and is out of this story's scope to further verify.

