---
title: 'Lock engine adapter and provenance'
type: 'feature'
created: '2026-08-14'
status: 'done'
baseline_revision: '4219f1dea4d7f61ce8fa7c70c53053d4c44232d3'
final_revision: '718df8222f'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `mason environment` (Epic 4) needs a lock engine, but no adapter exists yet --
`environment.py` is still a docstring-only stub, and nothing in the codebase wraps `conda-lock`,
the tool that will span conda and pip via its own vendored solver.

**Approach:** Author `engines/condalock.py` implementing the S-3.1 `EngineAdapter` protocol
(`name`, `probe()`) plus its one operation, `lock()`, mirroring `engines/pep517.py`'s shape exactly.
`lock()` threads its own probed engine name/version onto its result (the first adapter result shape
in this codebase to do so) and, live-verified against the installed `conda-lock` binary, embeds that
same identity into the produced lockfile's own provenance via `--mdy`.

## Boundaries & Constraints

**Always:**
- `condalock.py` implements `engines.EngineAdapter` structurally: module-level `name = "conda-lock"`
  and `probe() -> str | None` delegating to `probe_engine`, mirroring `engines/pep517.py`/
  `engines/twine.py`'s exact shape.
- `lock()` calls `require_engine("conda-lock")` as its first action, before any subprocess spawn or
  filesystem write, capturing the returned version for the result and the provenance file.
- `manifest_paths` becomes one repeated `-f <path>` per entry; `platforms` becomes one repeated
  `-p <platform>` per entry (`conda-lock lock`'s own `-f`/`-p` options are both `multiple=True`,
  live-verified against installed `conda-lock 4.0.2`). Omitting `platforms` passes no `-p` flag at
  all, letting conda-lock's own default apply (FR-27) -- Mason never invents one.
- Before invoking, write a small JSON file naming this adapter's own `name`/probed version to a
  `tempfile`-managed path, pass it via `--mdy <path>`, and remove it after the child exits (success
  or failure alike) -- live-verified: `conda-lock lock --mdy meta.json ...` merges that file's
  contents into the produced lockfile's `metadata.custom_metadata` block verbatim (FR-29's "where
  the format allows").
- Subprocess invocation: list argv, never `shell=True`, `stdout=subprocess.PIPE`, `stderr=None`
  (inherited -- live-verified `conda-lock` writes every progress/diagnostic line to stderr and
  nothing to stdout on both success and failure, mirroring `engines.pep517.build`'s identical
  STREAM-adjacent CAPTURE-mode choice), `text=True, encoding="utf-8", errors="replace"`, mandatory
  `timeout=` (default `_CONDA_LOCK_TIMEOUT_SECONDS = 600.0`, mirroring
  `_PEP517_BUILD_TIMEOUT_SECONDS`'s "solving is closer to compiling from source than uploading a
  file" rationale), `check=False`.
- A non-zero returncode is DATA on `CondaLockResult`, never raised (AD-4) -- live-verified a failed
  solve exits non-zero with a traceback on stderr, the routine expected outcome of resolving a real
  dependency graph.
- `Mason` itself performs no dependency resolution anywhere (spec AC3) -- `condalock.py` only
  assembles argv and reports the child's outcome.

**Block If:** a live grep of `engines/`/`errors.py` at execution time shows `condalock.py` or
`EnvironmentLockTimeoutError` already defined (a concurrent story landed first) -- reconcile with an
operator rather than overwriting. OQ-E3/PRD OQ-4 ("conda-lock or pixi.lock") is resolved by the
epics document's own concrete Story 4.1 text (`engines/condalock.py`, not a choice deferred to this
story) plus this spec's own live investigation; no further human decision is needed.

**Never:**
- No changes to `environment.py` (still a docstring-only stub per its own header -- Story 4.3's
  scope), `cli.py`, or `models.py` (`LockResult`, the Structural Seed's named use-case-level
  aggregate, is Story 4.3's own shape built from this adapter's `CondaLockResult`, not this story's).
- No `pixi.toml` change -- `conda-lock = ">=4.0.2,<4.1"` and `CONDA_LOCK_VERSION_RANGE` already
  exist from Story 3.1.
- No manifest discovery (Story 4.2), no `--output`/`--platform` CLI flags (Story 4.3), no lock
  staleness checking (Story 4.4).
- No `packaging`-based version comparison or range-gating inside `lock()` -- mirrors
  `require_engine`'s own "is it here, not is it the right version" boundary.
- No pre-validation of `output_path`'s parent directory -- a missing directory surfaces as
  conda-lock's own non-zero returncode (AD-4), never a Mason-side check.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| conda-lock absent | `lock(...)` called, not on PATH | Raises before any subprocess spawn or temp-file write | `EngineAbsentError` naming `conda-lock` + `conda-lock` package hint |
| Successful solve | manifests resolve cleanly | `CondaLockResult(returncode=0, lockfile_path=output_path, engine_name="conda-lock", engine_version=<probed>, stdout=...)` | No error expected |
| Failed solve | conda-lock exits non-zero (conflict/missing spec) | `CondaLockResult(returncode!=0, lockfile_path=None, engine_name/engine_version still populated, stdout=...)` | No error expected -- returncode is DATA (AD-4) |
| Solve exceeds timeout | child runs past `timeout` | Metadata temp file still removed | `EnvironmentLockTimeoutError` naming the elapsed timeout |
| No `--platform` given | `platforms=()` | Argv carries zero `-p` flags | No error expected |
| One or more platforms | `platforms=("linux-64", "osx-arm64")` | One `-p <platform>` per entry, in order | No error expected |
| Multiple manifests | `manifest_paths=("environment.yml", "pyproject.toml")` | One `-f <path>` per entry, in order | No error expected |

</intent-contract>

## Code Map

- `src/pyforge/mason/engines/condalock.py` -- new; `name`, `probe()`, `CondaLockResult`, `lock()`.
- `src/pyforge/mason/errors.py` -- add `EnvironmentLockTimeoutError`.
- `tests/unit/test_engines_condalock.py` -- new; mirrors `test_engines_pep517.py`'s coverage shape.
- `tests/unit/test_errors.py` -- extend with `EnvironmentLockTimeoutError` coverage.
- `src/pyforge/mason/engines/pep517.py` -- read-only reference for the adapter shape/rationale this
  story mirrors; not imported or edited.
- `src/pyforge/mason/errors.py::ShipUploadTimeoutError` -- read-only reference for the single-
  `timeout`-argument error shape this story's new class mirrors.

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/mason/errors.py` -- add `EnvironmentLockTimeoutError(MasonError)`: identifier
  `environment:lock-timeout`, single `timeout: float` constructor argument (mirrors
  `ShipUploadTimeoutError`'s shape exactly -- only `condalock.lock()` ever raises it, so no second
  `engine` argument is needed the way `PackageBuildTimeoutError` needs one), with a `__reduce__`
  override for deepcopy/pickle round-trip matching every existing timeout error's precedent.
- [x] `src/pyforge/mason/engines/condalock.py` -- new module: `name = "conda-lock"`; `probe()`
  delegating to `probe_engine`; `CondaLockResult` frozen dataclass (`returncode: int`,
  `lockfile_path: str | None`, `engine_name: str`, `engine_version: str | None`, `stdout: str`);
  `lock(manifest_paths: Sequence[str], output_path: str, *, platforms: Sequence[str] = (),
  timeout: float | None = None) -> CondaLockResult` -- gates via `require_engine("conda-lock")`,
  builds argv with repeated `-f`/`-p`, writes the `--mdy` provenance JSON to a `tempfile.mkstemp`
  path (removed in a `finally`), translates `TimeoutExpired` to `EnvironmentLockTimeoutError`.
- [x] `tests/unit/test_engines_condalock.py` -- new: `probe()` delegation; engine-absence gate
  (`require_engine` raises before `subprocess.run`/tempfile write); argv shape (`-f`/`-p` repeated
  correctly, `--lockfile`, `--mdy` present, `stdout`/`stderr`/`text`/`encoding`/`errors`/`check`
  kwargs); default vs. explicit `timeout`; `TimeoutExpired` -> `EnvironmentLockTimeoutError`
  translation; happy-path and failed-solve `CondaLockResult` shapes from the I/O matrix; a
  `subprocess.run` side-effect that reads the `--mdy` file's path from the captured argv and asserts
  its JSON content before returning a fake completed process.
- [x] `tests/unit/test_errors.py` -- extend with `EnvironmentLockTimeoutError` coverage: identifier,
  stored `timeout`, message content, `MasonError` subclass-ness, `str()` format, deepcopy/pickle
  round-trip -- matching `ShipUploadTimeoutError`'s existing test shape.

**Acceptance Criteria:**
- Given `engines/condalock.py`, when it is authored, then `pyforge.mason.engines.condalock`
  structurally satisfies `engines.EngineAdapter` (`isinstance(condalock, EngineAdapter)` holds).
- Given a successful `lock()` call, when its `CondaLockResult` is inspected, then `engine_name`/
  `engine_version` are populated -- so a future renderer (Story 4.3, `dataclasses.asdict`) surfaces
  "engine name and version ... in the output" (FR-29) with no `render.py` change required.
- Given a successful `lock()` call, when the produced lockfile at `output_path` is inspected, then
  its `metadata.custom_metadata` block contains the engine's name and version (live-verified `--mdy`
  mechanism).
- Given the Mason codebase, when it is inspected, then it contains no dependency-resolution logic
  (spec AC3) -- `condalock.py` only assembles argv and reports outcomes.
- Given `tests/meta/test_dependency_direction.py` and `tests/meta/test_adapter_sole_caller.py`, when
  they run against the tree with `condalock.py` added, then they still pass unmodified --
  `engines/*.py`'s existing subprocess-import allowlist already covers this new file.

## Spec Change Log

## Review Triage Log

### 2026-08-14 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 1, low 2)
- defer: 1: (high 0, medium 0, low 1)
- reject: 9: (high 0, medium 0, low 9)
- addressed_findings:
  - `[medium]` `[patch]` `engines/condalock.py::lock()`'s `--mdy` metadata-file write (`tempfile.mkstemp`/`os.fdopen`/`json.dump`) ran outside the `try/finally` that unlinks it, so a write failure would orphan the just-created temp file; and the bare `os.unlink(metadata_path)` in `finally` had no exception guard, so a cleanup failure (e.g. a lingering Windows file handle right after a timeout-killed child, per NFR-12) could replace a real propagating `EnvironmentLockTimeoutError` -- restructured into one flat `try/except TimeoutExpired/finally` covering the write through the subprocess call, with `os.unlink` wrapped in its own `try/except OSError: pass`; also flattens the previously-redundant nested `try/try/finally` into a single block. Live-verified end-to-end against the real `conda-lock` binary after the change: correct `metadata.custom_metadata` output, no leaked temp file.
  - `[low]` `[patch]` `CondaLockResult.engine_version: str | None` allows `None` (a present-but-unparseable `conda-lock` binary, per `require_engine`'s own documented contract) but no test exercised that branch -- added `test_lock_with_an_unparseable_engine_version_reports_none`, asserting `engine_version is None` and that the `--mdy` JSON write still succeeds (`null` value) without crashing.
  - `[low]` `[patch]` No test covered `manifest_paths=()` even though the symmetric `platforms=()` case was explicitly tested -- added `test_lock_with_no_manifest_paths_carries_zero_dash_f_flags`, confirming the existing pass-through behavior (zero `-f` flags, deferring to conda-lock's own manifest auto-discovery) mirrors the already-spec'd `platforms` omission precedent.
  - Deferred: `DW-4-1-1` -- the `__reduce__`-plus-comment boilerplate `EnvironmentLockTimeoutError` repeats is now duplicated across ~12 `MasonError` subclasses; a shared mixin would remove it but is a repo-wide `errors.py` refactor outside this story's surgical scope.
  - Rejected (noise, or matches deliberate existing precedent, no action): the `EnvironmentLockTimeoutError` message's "not a currently configurable v1 knob" phrasing is claimed misleading given `lock()`'s own `timeout` parameter -- identical wording already exists verbatim in `ShipUploadTimeoutError`/`ShipChannelUploadTimeoutError`/`PackageBuildTimeoutError`, referring to the absence of a CLI/env v1 knob (AD-13's closed set), not the Python parameter; the `stdout`-only-capture "diagnostic text" rationale is undermined by conda-lock writing diagnostics to stderr -- mirrors `engines.pep517.build`'s identical, already-reviewed STREAM-adjacent design (live terminal streaming IS the diagnostic surface, per Story 3.2); the `--mdy` provenance merge is asserted only by prose since every unit test mocks `subprocess.run` -- matches AD-16's unit-tier-never-invokes-a-real-engine design (this repo has no integration/e2e tier yet per `test-architecture.md`), and was independently live-verified against the real binary both during spec authoring and after the patch above; a TOCTOU gap between `require_engine`'s probe and `subprocess.run` (raw unwrapped `OSError` if the binary vanishes from PATH in between) matches `engines.twine.upload`'s identical, unaddressed precedent; tests hardcoding the literal `"conda-lock"`/`"lock"` argv strings instead of referencing `condalock._BINARY_NAME` matches `test_engines_pep517.py`'s own established literal-hardcoding convention exactly; no pre-validation of a stale/partial lockfile or missing parent directory at `output_path` matches this spec's own explicit Never boundary; no validation against manifest/platform values starting with `-` (argv-injection-shaped input) matches every sibling adapter's identical unvalidated pass-through (`twine.upload(paths)` included); no wiring into `environment.py`/a dispatcher matches this spec's own explicit Never boundary (Story 4.3's scope); a claim that `timeout<=0` raises a raw `ValueError` instead of the documented `EnvironmentLockTimeoutError` was empirically disproven (`subprocess.run(timeout=0)`/`timeout=-1` both correctly raise `TimeoutExpired`, already caught and translated).

## Design Notes

Live-verified against the installed `conda-lock 4.0.2` (matches `pixi.toml`'s pinned range):
`conda-lock lock -f environment.yml -p linux-64 --mdy meta.json --lockfile conda-lock.yml` produced
a `metadata.custom_metadata` block in the output YAML containing exactly the key/value pairs from
`meta.json`, and all progress/diagnostic text (`"Locking dependencies for [...]"`,
`INFO:conda_lock.conda_solver:...`) went to stderr with stdout empty. A forced solver failure
(a nonexistent package name) exited `1` with a Python traceback on stderr and nothing useful on
stdout -- confirms the "returncode is DATA" (AD-4) treatment, not a raised exception, matches
`pep517.build`'s precedent exactly.

`os.fdopen(tempfile.mkstemp(...)[0], "w")` inside a `with` block closes the metadata file before
`subprocess.run` spawns the child (NFR-12: Windows disallows a second process opening a file another
process still holds open) -- the same close-before-spawn discipline every cross-platform-safe
tempfile pattern in this codebase's sibling packages already follows.

`CondaLockResult` carrying `engine_name`/`engine_version` (rather than leaving them implicit, as
every other adapter's result shape does) is a deliberate, story-specific choice: FR-29's whole point
is that Mason *reports* which engine ran, so this is the one adapter whose caller genuinely cannot
already know that from context.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

**2026-08-14 -- dev-verify repair pass.** The prior session's implementation (`91ba8e22bd`, all
tasks/ACs already satisfied, review already triaged) landed clean but failed the harness's own
S-13.7 deterministic verify step: `python scripts/spec_surface_reconcile.py` gated on drift because
`condalock.py`/`errors.py` and their tests changed under `spec-pyforge-mason`'s governed surface
without that spec's `.memlog.md` naming the change. No code or `<intent-contract>` change was
needed or made -- this was a governance-bookkeeping gap, not an implementation defect. Repair:
appended a `(change)`/`(event)` pair to
`_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/.memlog.md` naming
the four changed paths (mirroring the S-3.4/S-3.5 dev-verify-repair precedent already recorded
there), then re-stamped the baseline via
`python scripts/spec_surface_check.py --write-baseline --spec pyforge-mason/spec-pyforge-mason`.
Committed as `718df8222f`.

**Verification performed:**
- `python scripts/spec_surface_reconcile.py` -- now exits 0 (`OK: every tracked file governed or
  allowlisted; no drift`), previously exited 1 with 4 drift findings.
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` -- 1187 passed, 1 deselected (unchanged
  from before the repair).

**Residual risks:** none identified. The reconciliation only touches
`spec-pyforge-mason/.memlog.md` and `scripts/.spec-surface-baseline.json`; no other spec's baseline
entry moved.
