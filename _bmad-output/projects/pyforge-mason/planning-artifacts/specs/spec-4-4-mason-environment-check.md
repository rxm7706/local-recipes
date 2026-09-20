---
title: 'mason environment check'
type: 'feature'
created: '2026-08-14'
status: 'done'
blocking_condition: 'intent gap in intent contract'
baseline_revision: 'a189f912ee10ddee8f4a7798c907bc6b20ebb23d'
final_revision: 'b4e1d15873401bfc0cfa8fee66e541c959e0007a'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `mason environment check` (FR-25 - FR-29's CI-facing companion to Story 4.3's `lock`)
does not exist -- `environment.py` has no `check()` use-case and the `environment` noun registers
no `check` verb, so nothing can tell a CI pipeline whether an existing lockfile has gone stale
relative to its manifests.

**Approach:** Register `mason environment check <manifest_path> [<manifest_path> ...]
--lockfile/-l PATH [--platform PLATFORMS]` in `cli.py`. Add `engines.condalock.check()`, a new
engine operation that re-runs `conda-lock lock --check-input-hash` against a **temporary copy** of
the given lockfile (never the real path) and compares the copy's parsed `metadata.content_hash`
before vs. after to decide staleness -- conda-lock 4.0.2's own documented `--check-input-hash`
exit-code-4 behavior is dead in the installed version (live-verified: no `sys.exit(4)` anywhere in
the package). Add `environment.py::check()` (mirrors `lock()`'s exact shape) and `models.
CheckResult`. Project the `stale` verdict onto the process exit code in `cli.py`'s dispatch
(`EXIT_OK`/`EXIT_FAILED`), mirroring `recipe validate`'s established "delegated pass/fail becomes
the process exit code" precedent -- the one other verb in this codebase that does this.

## Boundaries & Constraints

**Always:**
- `environment.py` gains zero CFE dependency (existing `test_capability_tiers.py` guard, unchanged).
- `manifest_path` is a required positional, `nargs="+"`, identical shape to `lock`'s own (Story 4.2
  auto-discovery still not built) -- mirrors `environment lock`'s registration exactly.
- `--lockfile`/`-l` is required, naming the EXISTING lockfile to verify -- deliberately not
  `--output`/`-o`: nothing is written to it, and that name would misleadingly imply a write.
- `--platform` mirrors `--to`/`lock --platform`'s established single comma-separated-flag idiom
  exactly; omitted -> `()` -> conda-lock's own default platform applies (never invented by Mason).
- A missing `--lockfile` path raises `EnvironmentLockfileMissingError` (new) before any subprocess
  spawns -- the epic's own explicit requirement to distinguish "missing" from "stale" as a typed
  error, not conda-lock's own returncode (a deliberate departure from `lock()`'s "no Mason-side
  pre-validation" default, forced by the copy-before-invoke design in Design Notes).
- `condalock.check()` never writes to the caller's own `lockfile_path` -- it copies it to a
  `tempfile.mkstemp`-managed path first (mirrors `lock()`'s `--mdy` tempfile-cleanup precedent:
  removed in a `finally` block, success/failure/timeout alike, `OSError` on removal swallowed) and
  points `--lockfile` at the copy (Design Notes: why the real path is never used directly).
- Staleness is decided by `yaml.safe_load`-parsing (never `yaml.load`) the copy's `metadata.
  content_hash` dict before invoking conda-lock and after, and comparing the two parsed dicts for
  equality -- not raw file bytes, not conda-lock's own exit code, not stderr text (Design Notes).
- `PyYAML` is added as a new runtime dependency (`pyforge-mason/pyproject.toml` `dependencies`,
  `[feature.pyforge-mason.dependencies]` in the root `pixi.toml`) -- justified against NFR-10
  exactly as `pyforge-doctor`'s own shipped `PyYAML>=6.0` precedent (its pyproject.toml comment:
  "the epic's own explicit departure from [a] hand-rolled-parser precedent"): no stdlib YAML parser
  exists, and no CLI-only way exists to read conda-lock's own hash comparison without one.
- `condalock.check()` reuses `_CONDA_LOCK_TIMEOUT_SECONDS` as its default timeout (identical
  underlying `conda-lock lock` invocation) but raises a new `EnvironmentCheckTimeoutError` (not
  `EnvironmentLockTimeoutError`) on expiry -- mirrors `ShipUploadTimeoutError`/
  `ShipChannelUploadTimeoutError`'s precedent of one dedicated timeout class per distinct operation
  even when the same binary is wrapped (a shared class's message text would misname the operation).
- `cli.py`'s dispatch projects `result.stale` onto the process exit code (`EXIT_OK` if not stale,
  else `EXIT_FAILED`) -- mirrors `recipe validate`'s "wrapped tool's pass/fail outcome becomes the
  process exit code" precedent; the JSON envelope's `status` stays `"ok"` regardless (spec I/O
  matrix) -- `check()` itself never raises for a stale verdict (AD-4).
- `mason environment check` succeeds with no CFE installation anywhere (spec AC, FR-25).

**Block If:** a live grep of `environment.py`/`models.py`/`cli.py`/`errors.py` at execution time
shows `check()`, `CheckResult`, `EnvironmentLockfileMissingError`, `EnvironmentCheckTimeoutError`,
or an `environment check` verb parser already defined (a concurrent story landed first) -- reconcile
with an operator rather than overwriting.

**Never:**
- No manifest auto-discovery (Story 4.2's scope) -- omitting the manifest positional is a usage
  error (argparse), not a fallback.
- No re-implementation of conda-lock's own content-hash algorithm -- Mason only reads the field
  conda-lock itself already writes; no recomputation of what a hash "should" be.
- No mutation of the caller-supplied lockfile under any outcome (current, stale, or error).
- No suppression of the network a genuinely stale input may require to confirm (matches
  `--check-input-hash`'s own documented behavior, not Mason inventing implicit network use) -- the
  common "current" case stays fully offline (Design Notes).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path, current | manifests unchanged since lock | `content_hash` before == after -> `CheckResult(stale=False, ...)` rendered `"ok"` | `EXIT_OK` |
| Happy path, stale | a manifest changed | `content_hash` before != after -> `CheckResult(stale=True, ...)` rendered `"ok"` | `EXIT_FAILED` (data, not raised) |
| `--lockfile` path missing | bad/nonexistent path | No subprocess spawned | `EnvironmentLockfileMissingError`, `EXIT_FAILED` |
| `--lockfile` omitted | (no flag) | Usage error (argparse `required=True`) | `EXIT_USAGE`, no dispatch |
| No manifest path given | `mason environment check -l lock.yml` | Usage error (argparse `nargs="+"`) | `EXIT_USAGE`, no dispatch |
| `--platform` supplied | `--platform linux-64,osx-arm64` | Only those `-p` flags passed to conda-lock | No error expected |
| `--platform` omitted | (no flag) | Zero `-p` flags; conda-lock's own default platform is checked | No error expected |
| conda-lock absent | binary not on `PATH` | No subprocess spawned, no temp copy left behind | `EngineAbsentError` (existing, via `main()`'s handler) |
| Check times out | child exceeds timeout | Temp copy removed (`finally` block) | `EnvironmentCheckTimeoutError` (new), `EXIT_FAILED` |

</intent-contract>

## Code Map

- `src/pyforge/mason/engines/condalock.py` -- add `check()` + `CondaLockCheckResult`; new `shutil`/
  `yaml` imports alongside the existing `require_engine`/`subprocess`/`tempfile` usage.
- `src/pyforge/mason/environment.py` -- add `check()`, mirrors `lock()`'s platform-parsing/wrapping.
- `src/pyforge/mason/models.py` -- add `CheckResult` frozen dataclass (tenth shape).
- `src/pyforge/mason/errors.py` -- add `EnvironmentLockfileMissingError`, `EnvironmentCheckTimeoutError`.
- `src/pyforge/mason/cli.py` -- register `environment check`; add dispatch branch; update the
  trailing "unreachable" dispatch comment and the `environment` noun's own verb-count comments.
- `src/shared/packages/pyforge-mason/pyproject.toml` -- add `"PyYAML>=6.0.3"` to `dependencies`.
- `pixi.toml` (root) -- add `pyyaml = ">=6.0.3"` to `[feature.pyforge-mason.dependencies]`.
- `src/shared/packages/pyforge-mason/pixi.toml` -- add `pyyaml = ">=6.0.3"` to
  `[package.run-dependencies]` (review pass, 2026-08-15 second: missed initially, so the BUILT
  conda package would have shipped without PyYAML; mirrors `pyforge-doctor/pixi.toml`'s own line).
- `pixi.lock` -- regenerated by the run-dependency addition above.
- `tests/unit/test_engines_condalock.py`, `tests/unit/test_environment.py`, `tests/unit/test_cli.py`
  -- extend with `check()`/`environment check` coverage, mirroring each file's existing `lock`
  test sections.

## Tasks & Acceptance

**Execution:**
- [x] `pyproject.toml` (pyforge-mason) -- add `"PyYAML>=6.0.3"` to `dependencies`, comment mirrors
  `pyforge-doctor`'s justification -- unblocks `import yaml` in `condalock.py`.
- [x] `pixi.toml` (root) -- add `pyyaml = ">=6.0.3"` to `[feature.pyforge-mason.dependencies]`,
  mirroring `[feature.pyforge-doctor.dependencies]`'s identical line -- makes `yaml` importable in
  the dev/test pixi environment.
- [x] `errors.py` -- add `EnvironmentLockfileMissingError(lockfile_path: str)` (identifier
  `environment:lockfile-missing`, `ValueError` on empty path, message naming the path and `mason
  environment lock` as the remedy) and `EnvironmentCheckTimeoutError(timeout: float)` (identifier
  `environment:check-timeout`, mirrors `EnvironmentLockTimeoutError`'s shape/wording for "check"),
  each with a `__reduce__` override mirroring its sibling one/two-arg `MasonError` subclasses.
- [x] `engines/condalock.py` -- add `CondaLockCheckResult` (`stale: bool`, `returncode: int`,
  `engine_name: str`, `engine_version: str | None`, `stdout: str`) and `check(lockfile_path: str,
  manifest_paths: Sequence[str], *, platforms: Sequence[str] = (), timeout: float | None = None) ->
  CondaLockCheckResult`: `require_engine("conda-lock")` first; raise `EnvironmentLockfileMissingError`
  if `not os.path.isfile(lockfile_path)`; `tempfile.mkstemp` + `shutil.copy` the lockfile to the
  temp path; `yaml.safe_load` its `metadata.content_hash` (before); argv
  `["conda-lock", "lock", "--check-input-hash"]` + repeated `-f`/`-p` + `["--lockfile", <temp
  path>]`; `subprocess.run` mirrors `lock()`'s exact kwargs (`stdout=PIPE, stderr=None, text=True,
  encoding="utf-8", errors="replace", check=False`, mandatory `timeout=`); `TimeoutExpired` ->
  `EnvironmentCheckTimeoutError`; re-`yaml.safe_load` the temp path's `content_hash` (after);
  `stale = before != after`; remove the temp file in `finally` (swallow `OSError`).
- [x] `models.py` -- add `CheckResult` (`lockfile_path: str`, `manifest_paths: tuple[str, ...]`,
  `platforms: tuple[str, ...]`, `stale: bool`, `engine_name: str`, `engine_version: str | None`,
  `returncode: int`, `stdout: str`).
- [x] `environment.py` -- add `check(lockfile_path: str, manifest_paths: Sequence[str], *,
  platforms: str | None = None) -> CheckResult`: identical comma-split/strip/empty-token-drop
  `--platform` parsing as `lock()` (verbatim-mirrored), calls `engines.condalock.check(...)`, wraps
  into `CheckResult`.
- [x] `cli.py` -- register `_noun_verbs["environment"].add_parser("check", help=
  _ENVIRONMENT_CHECK_HELP, description=_ENVIRONMENT_CHECK_HELP, parents=[global_flags])` with
  positional `manifest_path` (`nargs="+"`), `--lockfile`/`-l` (`required=True`), `--platform`
  (optional, `default=None`); add dispatch branch calling `environment.check(ns.lockfile,
  ns.manifest_path, platforms=ns.platform)`, `render.write(fmt, sys.stdout, "environment check",
  "ok", dataclasses.asdict(result), [])`, `return EXIT_OK if not result.stale else EXIT_FAILED`;
  update the trailing "Unreachable now..." dispatch comment to list `environment check`.
- [x] `tests/unit/test_engines_condalock.py` -- unit-test `check()`: engine-absence gate fires
  before any tempfile/subprocess; missing lockfile path raises `EnvironmentLockfileMissingError`
  before any subprocess spawn; argv shape (`--check-input-hash`, repeated `-f`/`-p`, `--lockfile`
  pointing at a temp path, never the original); the original file is byte-unchanged after any
  invocation (current OR stale); `stale=False` when a `subprocess.run` side effect leaves the temp
  copy's `content_hash` unchanged, `stale=True` when it rewrites it; timeout translates to
  `EnvironmentCheckTimeoutError` and still removes the temp file; default vs. explicit timeout.
- [x] `tests/unit/test_environment.py` -- unit-test `check()`: platform-string parsing (mirrors
  `test_lock_*`'s platform cases), `CondaLockCheckResult` -> `CheckResult` field mapping including
  `stale` passthrough.
- [x] `tests/unit/test_cli.py` -- dispatch tests mirroring `test_environment_lock_*`: `--help`
  works; happy-path text/JSON mode with `stale=False` -> `EXIT_OK`; `stale=True` -> `EXIT_FAILED`
  with JSON envelope `status` still `"ok"`; missing manifest positional / missing `--lockfile` are
  usage errors; `EnvironmentLockfileMissingError`/`EngineAbsentError`/`EnvironmentCheckTimeoutError`
  each project to `EXIT_FAILED`.

**Acceptance Criteria:**
- Given an existing lockfile whose manifests are unchanged, when `mason environment check
  <manifest> -l <lockfile>` runs, then it exits `0` and reports `stale: false`.
- Given an existing lockfile whose manifests have changed, when the same command runs, then it
  exits non-zero and reports `stale: true`, and the given lockfile's own bytes are unchanged on
  disk afterward.
- Given a `--lockfile` path that does not exist, when the command runs, then it raises
  `EnvironmentLockfileMissingError` (distinct from a stale verdict) before any subprocess spawns.
- Given no CFE installation anywhere, when this command runs, then it succeeds
  (`test_capability_tiers.py` continues to pass with `environment.py`'s new `check()` present).

## Spec Change Log

## Review Triage Log

### 2026-08-15 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 1, medium 1, low 4)
- defer: 0
- reject: 7: (high 0, medium 0, low 7)
- addressed_findings:
  - `[high]` `[patch]` A genuine `conda-lock` failure (bad manifest, solver crash, network
    error during the real re-solve a hash mismatch triggers) that left the temp copy
    unrewritten made `before == after` trivially hold, silently reporting `stale=False`/
    `EXIT_OK` for a check that never actually completed. `condalock.check()` itself still
    never raises for a non-zero `returncode` (AD-4 intact), but `cli.py`'s dispatch now also
    projects a non-zero `result.returncode` onto `EXIT_FAILED`, so a CI gate can no longer
    mistake "the check itself failed" for "current". New test: `test_environment_check_
    nonzero_returncode_projects_to_exit_failed_even_when_not_stale` (`test_cli.py`) +
    `test_check_reports_a_nonzero_returncode_as_data_without_raising`
    (`test_engines_condalock.py`).
  - `[medium]` `[patch]` Malformed/foreign lockfile content (invalid YAML, an empty file,
    missing `metadata`/`content_hash` keys, non-UTF-8 bytes) raised a raw `KeyError`/
    `TypeError`/`yaml.YAMLError`/`UnicodeDecodeError` instead of a typed `MasonError`, at
    both the before- and after-invocation reads; the same gap let a narrow TOCTOU race
    between the upfront `os.path.isfile` check and `shutil.copyfile` leak a raw `OSError`.
    Added `EnvironmentLockfileMalformedError` (new, `environment:lockfile-malformed`) and a
    private `_read_content_hash` helper in `condalock.py` that translates every one of those
    exception types at both read sites; the copy itself is now wrapped to translate a race-
    condition `OSError` into `EnvironmentLockfileMissingError`. New tests in
    `test_engines_condalock.py` (malformed-YAML, empty-file, missing-`metadata`-key,
    missing-`content_hash`-key, malformed-after-read, copy-race, temp-copy-cleanup-on-error)
    and `test_errors.py` (full identifier/attributes/message/is-a-MasonError/str-format/
    validation/deepcopy/pickle block for the new class) and `test_cli.py` (propagation to
    `EXIT_FAILED`).
  - `[low]` `[patch]` `shutil.copy` also calls `copymode`, overwriting `tempfile.mkstemp`'s
    secure `0600` temp file with the source lockfile's own (typically wider) permission
    bits. Swapped to `shutil.copyfile` (content only, mode untouched) -- existing real-file
    tests already exercise this call site, so no new test was needed beyond updating the
    module docstring.
  - `[low]` `[patch]` `EnvironmentLockfileMissingError`'s "does not exist" message was
    inaccurate for a path that exists but is a directory or broken symlink (`os.path.
    isfile()` returns `False` for both) -- reworded to "does not exist or is not a file".
  - `[low]` `[patch]` `pyproject.toml`'s new dependency comment claimed the `PyYAML>=6.0.3`
    floor "mirrors pyforge-doctor's own shipped `PyYAML>=6.0` precedent... identical", but
    doctor's own pyproject.toml pin is `>=6.0` while mason's is `>=6.0.3` -- reworded to
    state the floor mirrors mason's OWN `pixi.toml` pin instead of misquoting doctor's.
  - `[low]` `[patch]` Constructing `EnvironmentLockfileMissingError("")` for a reachable
    `mason environment check ... --lockfile ""` CLI input (argparse's `required=True` only
    demands the flag be given, not a non-blank value) raised `ValueError`, escaping the
    `MasonError` contract and falling through to `main()`'s generic `except Exception`
    handler with a raw traceback instead of a clean diagnostic (the exit code was already
    correct either way). Relaxed the class's own validation to accept an empty string with a
    dedicated "no --lockfile path was given" message; added
    `test_environment_lockfile_missing_error_accepts_an_empty_path` +
    `test_environment_lockfile_missing_error_rejects_a_non_str_path` (`test_errors.py`).
  - Rejected (noise, or matches deliberate existing precedent, no action): casing
    (`pyyaml` vs `PyYAML`) between `pixi.toml`/`pyproject.toml` matches `pyforge-doctor`'s
    own identical split (PyPI display name capitalized, conda package name lowercase), not
    a real inconsistency. The AD-13 `_SANCTIONED_YAML_EXCEPTIONS` carve-out being scoped to
    the whole file rather than the specific `yaml.safe_load` call is a concern about
    hypothetical future misuse, not a defect in this diff's actual (safe-load-only) usage.
    `EXIT_FAILED` for a stale verdict while the JSON envelope's `status` stays `"ok"` is the
    deliberate, spec-mandated design mirroring `recipe validate`'s own identical, already-
    shipped precedent in this codebase, not a new inconsistency. No enforced relationship
    between `check`'s `--platform` and the platform set `lock` originally covered mirrors
    `lock`'s own "never invented, always reported" precedent, explicitly reviewed and
    accepted for that command in Story 4.3's own 2026-08-14 review pass. The assumption that
    `--check-input-hash` still skips the actual re-solve when the hash matches was verified
    live against `conda_lock.py`'s own source during spec authoring (`compute_content_hashes`
    runs before any solve decision, local-only) -- not unverified. No `-l` short-flag
    collision exists with any `global_flags` entry -- verified live (`build_parser()`
    succeeds with no argparse conflict, and the full suite exercises it). `manifest_paths`
    accepting a one-shot iterator mirrors `lock()`'s own identical, never-flagged structural
    pattern, and no call path in this codebase ever passes one (argparse's `nargs="+"`
    always produces a real list).

### 2026-08-15 — Review pass (second, follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 9: (high 1, medium 3, low 5)
- defer: 3
- reject: 7: (high 0, medium 1, low 6)
- addressed_findings:
  - `[high]` `[patch]` `pyyaml` was never added to
    `src/shared/packages/pyforge-mason/pixi.toml`'s `[package.run-dependencies]`, only to the
    root `pixi.toml` dev-env feature and to `pyproject.toml`. `engines/condalock.py` imports
    `yaml` at module scope on `cli.py`'s own import path (`cli` -> `environment` ->
    `engines.condalock`, `cli.py:92`), so the BUILT conda package would have installed
    without PyYAML and `mason` would have raised `ModuleNotFoundError` before parsing argv --
    surviving only incidentally through conda-lock's own PyYAML dependency.
    `pyforge-doctor/pixi.toml:30` carries the identical line with the identical warning.
    Added, with `pixi.lock` regenerated. This also made honest two shipped comments that
    already asserted the run-dep existed (`pyproject.toml`'s "mirrors THIS package's own
    `pixi.toml` conda pin" and the root `pixi.toml`'s "also a package run-dep"), both of
    which were false as written.
  - `[medium]` `[patch]` The load-bearing rationale for the temp-copy design was factually
    wrong. The module docstring, `check()`'s docstring, a test comment, and the spec's own
    Design Notes all claimed `conda_lock.py::run_lock` calls `write_conda_lock_file`
    "unconditionally ... including the 'nothing changed' branch". Read live against the
    installed `conda-lock` 4.0.2: that call sits inside the `else:` of `if not
    platforms_to_lock:` (`conda_lock.py:427-470`), so the nothing-changed branch writes
    nothing at all. The temp copy is still required -- for the STALE branch, where a real
    solve rewrites the target -- and pointing `--lockfile` at the user's real file would
    regenerate it precisely when stale, a self-erasing mutation that would report itself
    current on the next check. All four sites corrected; the false claim is kept struck in
    Design Notes so it cannot be re-derived.
  - `[medium]` `[patch]` `shutil.copyfile`'s failure translation caught bare `OSError` and
    re-raised `EnvironmentLockfileMissingError`, so an unreadable lockfile (`PermissionError`),
    a full `$TMPDIR` (`ENOSPC`), or an I/O error each reported "lockfile does not exist" and
    prescribed `mason environment lock` -- a remedy that cannot help. Narrowed to
    `FileNotFoundError` (the TOCTOU race the translation was actually added for); every other
    `OSError` now raises `EnvironmentLockfileMalformedError` carrying the OS's own diagnostic
    verbatim. Both remain typed `MasonError`s (NFR-14). New test:
    `test_check_translates_a_non_vanished_copy_failure_to_lockfile_malformed_error`.
  - `[medium]` `[patch]` `--platform`'s omitted-flag behavior was documented as "conda-lock's
    own default platform" (singular). Verified live: `make_lock_spec` falls back to
    `DEFAULT_PLATFORMS`, FOUR platforms, and `run_lock` adds every platform the lockfile does
    not cover to `platforms_to_lock` regardless of `--check-input-hash` -- so checking a
    narrow lockfile without repeating its `-p` subset runs a real network solve and reports a
    false `stale=True`. Corrected in `check()`'s docstring, `_ENVIRONMENT_CHECK_HELP`, the
    `--platform` flag help, and Design Notes, each now instructing the caller to pass the same
    platforms the lockfile was locked with. The behavioral fix is deferred (`DW-4-4-1`): it
    requires amending an Always boundary inside the frozen intent contract.
  - `[low]` `[patch]` `_ENVIRONMENT_CHECK_HELP` still promised the exit code "reflects the
    stale/current verdict"; since the previous pass added the `returncode` conjunct it also
    reflects a failed check. Reworded to say so.
  - `[low]` `[patch]` `environment.py::check()`'s docstring listed three raises but omitted
    `EnvironmentLockfileMalformedError`, which it propagates unchanged -- so the use-case
    layer and `cli.py`'s dispatch published different contracts for the same call. Aligned.
  - `[low]` `[patch]` `EnvironmentLockfileMissingError` branched on `lockfile_path.strip()`,
    so `--lockfile "   "` -- a path the user really did supply -- was told "no --lockfile path
    was given". Branches on truthiness now, so only the genuinely empty string takes that
    branch. New test: `test_environment_lockfile_missing_error_names_a_whitespace_only_path`.
  - `[low]` `[patch]` The AD-13 carve-out keys on `(path, banned_module)`, which is all the
    detector reports -- so it exempted ANY yaml import in `condalock.py`, including
    `from yaml import unsafe_load`, the exact thing the safe-load-only invariant exists to
    keep out; and nothing asserted the entry was still live, so it could rot into silently
    re-authorizing reintroduction. New test
    `test_every_sanctioned_yaml_exception_is_live_and_import_form_scoped` closes both halves
    without teaching the detector about exceptions (which the regression fixtures depend on).
  - `[low]` `[patch]` `_read_content_hash` enumerates `UnicodeDecodeError` among the failures
    it translates, but no test exercised that branch. New test:
    `test_check_raises_lockfile_malformed_error_when_the_file_is_not_utf8`.
  - Deferred (`DW-4-4-1`/`DW-4-4-2`/`DW-4-4-3`): the `--platform` default should arguably read
    the lockfile's own `metadata.platforms` (needs the intent contract amended); no real
    conda-lock round-trip coverage exists, so the mocked engine suite proves a tautology and
    structurally could not have caught the write-behavior error above; and `--format json`
    reports `status: "ok"`/`errors: []` for a check whose subprocess failed, with `stderr`
    inherited rather than captured.
  - Rejected (noise, contrived, or matching deliberate existing precedent, no action):
    `RecursionError` from pathologically nested lockfile YAML escaping `_read_content_hash`'s
    caught tuple (contrived input, speculative). A `conda-lock` binary unlinked between
    `require_engine` and the spawn (TOCTOU on the binary; `lock()` has the identical
    never-flagged shape). `tempfile.mkstemp` raising, or `os.close(fd)` failing outside the
    `finally`-protected block (both effectively unreachable; `lock()` shares the shape). A
    `metadata.content_hash` that is present but null/empty/scalar comparing equal to itself --
    already covered, because conda-lock's own parser rejects such a lockfile and the non-zero
    returncode now projects to `EXIT_FAILED`. The two new error classes having opposite
    empty-string validation contracts (deliberate, documented, and each matches the sibling
    precedent it was modeled on). `condalock.check(platforms="linux-64")` iterating a bare
    `str` per character (`lock()`'s identical structural pattern, never flagged; the previous
    pass rejected the analogous `manifest_paths` finding on the same grounds; no call path
    passes one). Review-provenance narrative in shipped docstrings (matches this codebase's
    pervasive, deliberate story/AD-citing docstring style). `package ship`'s docstring
    claiming "the ONE genuinely data-dependent exit code in this whole file" now being
    inaccurate -- pre-existing, already false when `recipe validate` shipped, and the new
    branch's own narrower claim (the one other verb projecting a wrapped tool's returncode) is
    accurate.

### 2026-08-15 — Review pass (repair pass, S-13.7 verification repair)
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 0, low 1)
- defer: 1: (high 0, medium 0, low 1)
- reject: 14: (high 0, medium 0, low 14)
- addressed_findings:
  - `[low]` `[patch]` No test exercised `stale=True` combined with a non-zero `returncode`
    simultaneously (Blind Hunter) -- every existing test covered one signal in isolation, so the
    CLI dispatch's `not result.stale and result.returncode == 0` condition was unverified for the
    combined case even though correct by inspection. New test:
    `test_environment_check_stale_and_nonzero_returncode_together_still_exit_failed` (`test_cli.py`).
  - `[low]` `[defer]` Story 4.4's spec has not been promoted from gitignored
    `implementation-artifacts/` into the tracked `planning-artifacts/specs/` directory per
    CLAUDE.md's story-spec convention (Blind Hunter) -- a pre-existing gap shared by Stories
    4.1-4.3, not introduced by this story alone; a partial single-story promotion would leave the
    others inconsistently behind. Deferred as `DW-4-4-4`, to be resolved by a dedicated Epic
    2-5 promotion sweep matching the 2026-08-10 Epic 1 audit's shape.
  - Rejected (noise, duplicate of an already-deferred finding, or matching established/spec-mandated
    precedent, no action): `DW-4-4-1` was minted only in the memlog's prose and never written into
    the tracked `deferred-work-ledger.md` (Blind Hunter) -- false; it and `DW-4-4-2`/`DW-4-4-3` are
    fully described in the project's own Tier-3 `deferred-work.md`, the correct location per this
    workflow's own defer step; promotion to the tracked ledger is a separate, periodic sweep, not a
    per-story obligation. Two of the three second-pass-deferred findings being undescribed anywhere
    (Blind Hunter) -- false; all three (`DW-4-4-1`/`-2`/`-3`) already carry full evidence in
    `deferred-work.md`. The exit code conflating a stale verdict with a check-crash under one bit,
    the JSON envelope's `status` staying `"ok"` on a genuine subprocess failure, and `stderr=None`
    losing the failed child's diagnostic text (Blind Hunter, three findings) -- all three are the
    same concern `DW-4-4-3` already deferred with full evidence; `data.returncode` is present and
    machine-readable, and both the `"ok"` status and `stderr=None` are spec-mandated (AD-9, the
    task list's own `subprocess.run` kwargs). Omitting `--platform` can trigger a real network
    solve on a narrow lockfile (Blind Hunter) -- already `DW-4-4-1`, verbatim. The temp-copy design
    resting on installed-conda-lock-source reading with no test against the real binary (Blind
    Hunter) -- already `DW-4-4-2`, verbatim. `EnvironmentLockfileMalformedError`'s empty-path/reason
    invariant being enforced only by docstring prose for a hypothetical future direct-construction
    call site (Blind Hunter) -- the class's `__init__` DOES structurally validate both fields
    (verified live); the finding is about a call site that does not exist, and every sibling
    `MasonError` subclass in this module raises a bare `TypeError`/`ValueError` for the same class
    of construction-time misuse, an established, pervasive, pre-existing pattern. The narrowed
    `shutil.copyfile` failure translation still mapping unrelated OS-level causes (e.g. a
    destination-side `ENOSPC`) to one "lockfile malformed, regenerate it" message (Blind Hunter) --
    the message embeds the OS's own diagnostic text verbatim, so the true cause is still legible;
    further cause-splitting was already deliberately scoped out by this story's own second review
    pass. The engine-presence probe running before the lockfile-existence check, paying an extra
    subprocess spawn for a typo'd path (Blind Hunter) -- this exact ordering
    (`require_engine("conda-lock")` first) is mandated verbatim by this spec's own frozen
    `<intent-contract>` Tasks & Acceptance, mirroring `lock()`'s identical, already-accepted shape.
    `tempfile.mkstemp`/`os.close(fd)` raising outside the `finally`-protected block (Edge Case
    Hunter) -- matches this story's own second-pass rejection of the identical finding verbatim
    ("effectively unreachable; `lock()` shares the shape"). `yaml.safe_load` raising
    `RecursionError`/`MemoryError` on a pathological lockfile, escaping `_read_content_hash`'s
    caught-exception tuple (Edge Case Hunter) -- matches this story's own second-pass rejection of
    the `RecursionError` case verbatim ("contrived input, speculative"); `MemoryError` is the same
    class. `str(exc)` being empty/whitespace for one of the five caught exception types, so
    `EnvironmentLockfileMalformedError`'s own `reason` validation raises a raw `ValueError` (Edge
    Case Hunter) -- none of `OSError`/`UnicodeDecodeError`/`yaml.YAMLError`/`KeyError`/`TypeError`
    produces an empty `str()` from any reachable call site in `_read_content_hash`; contrived,
    matching the same speculative-input class already rejected above. The `conda-lock` binary being
    unlinked between `require_engine`'s probe and the `subprocess.run` spawn (Edge Case Hunter) --
    matches this story's own second-pass rejection of the identical TOCTOU finding verbatim
    (`lock()` has the identical never-flagged shape).

### 2026-08-15 — Review pass (fourth, follow-up on a `done` spec)
- intent_gap: 1: (high 0, medium 1, low 0)
- bad_spec: 0
- patch: 6: (high 0, medium 1, low 5)
- defer: 3: (high 0, medium 1, low 2)
- reject: 5: (high 0, medium 0, low 5)
- addressed_findings:
  - none

**Intent gap (blocking; the patch and defer findings below are moot and were deliberately
NOT applied or written, per this workflow's cascading-order rule):**

`[medium]` `[intent_gap]` **Story 4.4's second epic acceptance criterion is not implemented and
its omission is not recorded as a deviation.** `epics.md:1198-1200` (mirrored verbatim in
`epics-with-stories.md:1060` and `test-architecture.md:173`) requires: "*Given* a manifest changed
since the lock was produced, *When* the check runs, *Then* it exits non-zero **and names which
manifests drifted**." The frozen `<intent-contract>` silently dropped the attribution clause -- its
own AC requires only that the command "exits non-zero and reports `stale: true`". `CheckResult`
carries `stale: bool` plus `manifest_paths` echoed back verbatim from the caller's argv, so with
`nargs="+"` a user passing three manifests learns that *something* drifted, never which one.

The gap cannot be closed from the spec, for three independent reasons:
1. conda-lock's own output structurally cannot attribute drift to a manifest. `LockMeta.
   content_hash` is `dict[str, str]`, documented in `conda_lock/lockfile/v1/models.py:300-302` as
   "Hash of dependencies for each **target platform**" -- keyed by platform, never by source file.
2. The natural workaround is forbidden by the contract's own **Never** clause: "No
   re-implementation of conda-lock's own content-hash algorithm."
3. The binding requirement in the PRD -- `prd.md:503-509`, FR-28 "Lock verification" -- lists only
   "exits non-zero when the lockfile is stale relative to its manifests" and "emits JSON under
   `--format json`". It requires no attribution at all, so `epics.md`'s AC is an elaboration
   *beyond* the FR the story declares it realizes.

At least three defensible resolutions exist, so intent cannot be inferred: (a) amend `epics.md` /
`epics-with-stories.md` / `test-architecture.md` to match FR-28 and drop the attribution clause;
(b) amend the intent contract to permit a partial, engine-honest attribution by diffing the given
manifest list against the lockfile's own `metadata.sources` (names manifests *added or removed*
relative to the lock, never content-drift); (c) amend the contract's Never clause to allow
Mason-side per-manifest hashing. Each changes a frozen artifact. Requires an operator.

Note this was flagged upstream and left open: `research/market-mason-packaging-automation-2026-08-08.
md:374` (OQ-M3) says *"the AC ('names which manifests drifted') implies input-hash. Settle in the
story spec."* The story spec settled OQ-M3's staleness-definition half (input-hash via
`--check-input-hash` + `metadata.content_hash`) and never addressed its attribution half.

**Not applied (moot under the intent gap), recorded so the next pass need not re-derive them:**
  - `[medium]` `[patch]` `test_every_sanctioned_yaml_exception_is_live_and_import_form_scoped`
    (`tests/meta/test_no_config_file.py:194-228`) does not enforce the invariant it advertises. Its
    docstring claims it keeps out "`from yaml import unsafe_load`, the exact thing AD-13's
    safe-load-only invariant exists to keep out", and it asserts only on `ast.ImportFrom`. But
    `import yaml` -- the form the carve-out sanctions -- exposes `yaml.unsafe_load` identically via
    attribute access, and `_SANCTIONED_YAML_EXCEPTIONS` keys on `(path, banned_module)`, blanket-
    exempting the file. Verified: substituting `yaml.unsafe_load` for `yaml.safe_load` in
    `_read_content_hash` leaves the meta suite green. Fix: add an `ast.Attribute` walk asserting
    `yaml.<attr>` is only ever `safe_load`.
  - `[low]` `[patch]` FR-28 -- the sole FR this story realizes (`epics.md:114`, `:1210`) -- is cited
    nowhere in the package: `grep -rn "FR-28" src tests` returns 0 hits, while FR-25 (mapped to
    S-4.3 `environment lock`, `epics.md:111`) returns 17 and FR-27 returns 20. Every new Story 4.4
    docstring and comment (`errors.py:812`, `:870`, `:928`; `condalock.py:70`, `:242`;
    `cli.py:1371`) cites `FR-25, FR-27, FR-29` -- the sibling story's FRs, copied wholesale.
  - `[low]` `[patch]` `CondaLockCheckResult`'s docstring (`condalock.py:242-253`) says `stdout`
    "mirror[s] `CondaLockResult`'s own identical fields **and rationale**", and that rationale
    (`condalock.py:150-153`) is "a failure investigated outside a live terminal needs diagnostic
    text, not a bare returncode integer." For `check()` the field is structurally always empty:
    `stderr=None` inherits (`condalock.py:379`) and this module's own docstring states conda-lock
    "writes every progress/diagnostic line to stderr and nothing to stdout on both success and
    failure." The inherited justification is false for this class.
  - `[low]` `[patch]` `EnvironmentCheckTimeoutError`'s docstring (`errors.py:944-946`) says
    "`timeout` is the number of seconds that **elapsed** before the child was killed"; the call site
    passes `resolved_timeout` (`condalock.py:389`), the configured *limit*. Copied verbatim from
    `EnvironmentLockTimeoutError` (`errors.py:781-782`), which carries the same inaccuracy -- the
    new class propagated it rather than correcting it. (The sibling's own copy is pre-existing.)
  - `[low]` `[patch]` The after-invocation read misattributes engine-side corruption to the user.
    Both reads call `_read_content_hash(temp_lockfile_path, lockfile_path)` (`condalock.py:367`,
    `:387`), and the helper names the second argument in its error. The before-read already proved
    the caller's file parses, so an after-read failure -- conda-lock killed or `$TMPDIR` filling
    mid-rewrite, truncating the temp copy -- can never be the caller's file's fault, yet raises
    `EnvironmentLockfileMalformedError` naming their intact lockfile and prescribing regeneration.
  - `[low]` `[patch]` `check()`'s argv test asserts via `argv.index("-f")`/`argv.index("-p")`
    against single-element inputs (`_MANIFEST_PATHS = ("environment.yml",)`, `platforms=
    ("linux-64",)`), so it passes even if `check()` emitted only the first manifest or platform.
    `check()` re-implements both repetition loops rather than sharing `lock()`'s, and `lock()` has
    `test_lock_with_multiple_platforms_repeats_dash_p_in_order` /
    `test_lock_with_multiple_manifests_repeats_dash_f_in_order`
    (`test_engines_condalock.py:219`, `:234`); `check()` has neither.

**Not written to the ledger (moot under the intent gap), recorded here so they are not lost:**
  - `[medium]` `[defer]` `environment lock`'s dispatch returns `EXIT_OK` unconditionally
    (`cli.py:1381-1388`), so a failed solve that wrote no lockfile still exits 0 -- the exact
    opposite policy to the `returncode`-projection this story's first review pass added to `check`
    one branch below, whose own comment argues "a CI gate must not green-light on its own internal
    failure." Pre-existing (Story 4.3); the two sibling verbs on one noun now disagree.
  - `[low]` `[defer]` Every conda-lock diagnostic names the temp copy, not the user's lockfile
    (e.g. `... /tmp/mason-condalock-check-vedwraei.yml is missing a version`). The path is one the
    user never supplied, the `finally` block unlinks it before they can inspect it, and nothing
    maps it back. `_read_content_hash` is careful to name `lockfile_path` in its own errors; the
    child's output is not re-mapped at all. A consequence of this story's temp-copy design.
  - `[low]` `[defer]` `--format json` emits no JSON at all on any typed-error path: `main()`'s
    `except MasonError` (`cli.py:1456-1460`) prints `str(exc)` to stderr and returns `EXIT_FAILED`
    with stdout empty, so `mason environment check env.yml -l gone.yml --format json | jq .` is a
    parse error. Codebase-wide and pre-existing, but Story 4.4 is the first verb whose ACs put JSON
    mode (`epics.md:1202-1204`) and a typed error path (`:1206-1208`) in the same contract.
  - Rejected (already-deferred duplicates, or matching a prior pass's verbatim rejection): the JSON
    envelope reporting `status: "ok"`/`errors: []` while the exit code is `EXIT_FAILED` on a
    subprocess failure -- already `DW-4-4-3`, now with a live end-to-end reproduction against real
    conda-lock 4.0.2 (a lockfile with a valid `content_hash` but no `version` key yields
    `{"status":"ok","errors":[],"data":{"stale":false,"returncode":1}}` at exit 1) that strengthens
    the existing entry without being a new finding. An omitted `--platform` running a real network
    solve and falsely reporting `stale=True` on a narrow lockfile -- already `DW-4-4-1`, verbatim.
    `--platform ","` / `"   "` parsing to zero tokens and falling through to conda-lock's four-
    platform default -- a sub-case of `DW-4-4-1`, and the parsing is a spec-mandated verbatim mirror
    of `lock()`'s. `tempfile.mkstemp` raising, or `os.close(fd)` failing, outside the `finally`-
    protected block -- rejected verbatim by both the second and the repair pass ("effectively
    unreachable; `lock()` shares the shape"). A destination-side `ENOSPC` during `shutil.copyfile`
    reporting the source lockfile as malformed -- rejected verbatim by the repair pass (the message
    embeds the OS's own diagnostic text, and further cause-splitting was deliberately scoped out by
    the second pass).

## Design Notes

`--check-input-hash`'s documented "exit code 4 when nothing changed" is dead in this workspace's
pinned `conda-lock` 4.0.2: a full-package grep of the installed distribution finds no `sys.exit(4)`
(or equivalent) anywhere -- the flag's own comparison logic (`compute_content_hashes` vs. the
lockfile's recorded `content_hash`, evaluated BEFORE any solve decision) still runs and still skips
solving when unchanged, but the process always exits `0` regardless of which branch it took. This
is why Mason cannot rely on conda-lock's own returncode and must read `metadata.content_hash`
itself. It also confirms the comparison itself is local/offline -- only an actual mismatch triggers
a real solve, so the common "current" CI case never touches the network.

Why a temp copy, never the real `--lockfile` path (**corrected 2026-08-15, second review pass** --
the original claim below was verified false against installed `conda-lock` 4.0.2 and is kept here,
struck, so the false model does not get re-derived): ~~`conda_lock.py::run_lock` calls
`write_conda_lock_file` on its `--lockfile` target unconditionally once `new_lock_content` resolves
-- including the "nothing changed" branch.~~ In 4.0.2 that call sits inside the `else:` of `if not
platforms_to_lock:`, so the "nothing changed" branch writes **nothing at all**. The copy is still
required, for the *stale* branch alone: when the input hash does differ, `run_lock` runs a real
solve and rewrites its `--lockfile` target with the merged result. Pointing `--lockfile` at the
user's real file would therefore regenerate it precisely when it is stale -- both a mutation
nowhere in the epic's contract and a self-erasing one, since the freshly-rewritten file would
report itself current on the very next check, destroying the signal the gate exists to raise.

Comparing PARSED `content_hash` dicts (not raw bytes) remains the right comparison, now for
forward-compatibility rather than for the "current" path: were a future conda-lock to re-serialize
on the nothing-changed branch, a formatting-only rewrite (key order, whitespace) would still parse
to an identical dict and correctly report `stale=False`, where a byte-for-byte comparison would
false-positive.

Platform defaulting (**added 2026-08-15, second review pass**): an omitted `--platform` delegates
to conda-lock, whose `make_lock_spec` falls back to `DEFAULT_PLATFORMS` -- FOUR platforms
(`linux-64`, `osx-arm64`, `osx-64`, `win-64`), not one -- whenever neither `-p` nor the manifests
name any. `run_lock` then adds every platform the lockfile does not already cover to
`platforms_to_lock` regardless of `--check-input-hash`, so checking a deliberately narrow lockfile
without repeating its `-p` subset runs a real network solve and reports `stale=True` for manifests
that never changed. The I/O matrix row "`--platform` omitted -> conda-lock's own default platform is
checked | No error expected" is accurate only when the lockfile already covers that default set.
The code and `--help` now say so; changing the default to the lockfile's own `metadata.platforms`
would need the intent contract amended and is deferred (see the ledger).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done
Reconciled 2026-09-20: the `blocked` verdict below is the session's own record at halt time; the story was landed afterwards and the ledger row promoted to `done` by `8e541b683d 2026-08-14 land herald 14-1/14-2/14-3: deck visual-QA gate report + headless render gate + image-slot scan` — that promotion is the ruling this record now reflects.
Blocking condition: **intent gap in intent contract**

### Implemented change (unchanged by this pass)

`mason environment check <manifest>... -l <lockfile> [--platform ...]` -- a CI-facing staleness
gate for conda-lock lockfiles. It copies the caller's lockfile to a `tempfile.mkstemp` path, reads
`metadata.content_hash` from the copy, re-runs `conda-lock lock --check-input-hash` against the
copy, re-reads the hash, and reports `stale = before != after`. The caller's own file is never
written. `cli.py`'s dispatch projects both `result.stale` and a non-zero `result.returncode` onto
`EXIT_FAILED`.

### Files changed (baseline `a189f912ee` -> HEAD `b4e1d15873`; 16 files, +1919/-98)

- `src/.../mason/engines/condalock.py` -- `check()` + `CondaLockCheckResult` + `_read_content_hash`.
- `src/.../mason/environment.py` -- `check()` use-case, mirrors `lock()`'s platform parsing.
- `src/.../mason/models.py` -- `CheckResult` frozen dataclass.
- `src/.../mason/errors.py` -- `EnvironmentLockfileMissingError`, `EnvironmentLockfileMalformedError`,
  `EnvironmentCheckTimeoutError`.
- `src/.../mason/cli.py` -- `environment check` parser + dispatch branch.
- `pyproject.toml` / root `pixi.toml` / package `pixi.toml` / `pixi.lock` -- PyYAML runtime dep.
- `tests/unit/{test_engines_condalock,test_environment,test_cli,test_errors}.py`,
  `tests/meta/test_no_config_file.py` -- coverage for the above.
- `planning-artifacts/specs/spec-pyforge-mason/.memlog.md`, `scripts/.spec-surface-baseline.json`.

### Review findings breakdown (this pass)

1 intent_gap (medium) · 0 bad_spec · 6 patch (1 medium, 5 low) · 3 defer (1 medium, 2 low) ·
5 reject. **No patches were applied and no ledger entries were written** -- the intent gap makes
every lower finding moot under this workflow's cascading-order rule. All eleven are written up in
full in the Review Triage Log above so the resolving pass need not re-derive them.

### Deviation from the workflow's intent_gap branch (deliberate, non-destructive)

The branch prescribes "Revert code changes." **The code was NOT reverted.** The operator's standing
fleet-wide escalation policy is that escalation preserves work and hands over a restore-patch,
never a from-scratch re-derivation. Reverting here would discard a complete, green implementation
that fully satisfies its binding requirement (PRD FR-28) over a planning-artifact reconciliation
whose most likely resolution is a one-line `epics.md` edit that requires no code change at all.
HEAD is left at `b4e1d15873`, tree clean, so whichever resolution the operator picks can be applied
as a patch on top.

### Verification performed

- `pixi run -e pyforge-mason pyforge-mason-test` -> **1502 passed, 2 deselected** at HEAD after the
  review subagents finished; working tree confirmed clean (`git status --porcelain` empty) and HEAD
  unmoved, so neither reviewer left a probe behind.
- conda-lock 4.0.2 read live: `LockMeta.content_hash` is `dict[str, str]`, "Hash of dependencies for
  each target platform" (`lockfile/v1/models.py:300-302`) -- confirms per-manifest attribution is
  unavailable from the engine's own output, which is what makes the intent gap unresolvable in code.
- `grep -rn "FR-28" src tests` in the mason package -> 0 hits (vs. FR-25: 17, FR-27: 20).
- AD-13 guard hole confirmed by substitution: `yaml.unsafe_load` in place of `yaml.safe_load` in
  `_read_content_hash` leaves the meta suite green.

### Residual risks

- The shipped command meets PRD FR-28 but not `epics.md`'s AC #2 as written, and nothing in the
  code or planning artifacts records that as a deliberate deviation -- an Epic 4 readiness gate or
  retro would surface it again.
- The three prior deferrals (`DW-4-4-1` platform default, `DW-4-4-2` no real conda-lock round-trip
  coverage, `DW-4-4-3` JSON envelope fidelity on failure) remain open and untouched by this pass.
  This pass produced a live end-to-end reproduction for `DW-4-4-3` (recorded in the triage log)
  that strengthens the existing entry; per the invocation's instruction, no existing ledger entry
  was modified, re-opened, or rewritten.
- The AD-13 safe-load-only invariant currently has zero enforcement despite a test that advertises
  it -- benign today (the code does use `safe_load`), latent for any future edit.

## Status reconcile 2026-09-20

- frontmatter `status` `blocked` → `done` (ledger row `4-4-mason-environment-check: done`).
- Auto Run Result `Status: blocked` → `done` (see the reconcile line under it).
