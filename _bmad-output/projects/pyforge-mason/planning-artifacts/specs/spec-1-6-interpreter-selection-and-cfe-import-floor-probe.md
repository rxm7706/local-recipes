---
title: 'Interpreter selection and CFE import-floor probe'
type: 'feature'
created: '2026-08-09'
status: 'done'
baseline_revision: 'f021a361a2c47836aa707dcb671c674014e4d8b9'
final_revision: '9a16ab71ae'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Mason has no way to pick a Python interpreter capable of running CFE scripts, or to
know in advance whether that interpreter has CFE's import floor -- a lean `pyforge-mason`-only
environment's own `sys.executable` is wrong for this (D-7), and a naive `import` probe would leak a
raw subprocess `ImportError` traceback straight at the user.

**Approach:** Extend `resolve.py` (Story 1.5's pattern) with a second pure chain,
`resolve_cfe_interpreter`, choosing `--cfe-python` -> `MASON_CFE_PYTHON` -> `sys.executable`. Seed a
new `cfe.py` -- the file AD-3/AD-4 reserve as the sole CFE-subprocess caller, extended fully by
Story 2.1 -- with a subprocess-based, process-lifetime-cached probe of the six-module import floor,
and a typed `CfeImportFloorError`. Not wired into `cli.py`: no CFE-dependent command exists yet to
call it (mirrors Story 1.5).

## Boundaries & Constraints

**Always:** `resolve_cfe_interpreter(explicit, environ)` in `resolve.py` is pure -- no
filesystem/network/subprocess -- and never raises; `sys.executable` is a guaranteed-match terminal
step, so there is no not-found case. Reuse the existing `STEP_FLAG`/`STEP_ENVIRONMENT` constants
(same semantics as the root chain); add `STEP_RUNNING_INTERPRETER` for the `sys.executable`
fallback. The import-floor probe lives in `cfe.py`, not `resolve.py` -- AD-5 forbids process spawns
in `resolve.py`, and `tests/meta/test_dependency_direction.py`'s AD-2 allowlist permits `import
subprocess` only in `cli.py`/`cfe.py`/`engines/*.py`; the architecture's CFE-seam-to-FR mapping
table already assigns FR-1..FR-6 (which includes FR-3) to `cfe.py` and `resolve.py` together.
`probe_import_floor(interpreter: str) -> ImportFloorResult` is cached for the process lifetime
(`functools.lru_cache`), invokes the interpreter as `[interpreter, "-c", script]` (list argv, never
`shell=True`, a timeout), and the probe script wraps each module's import in try/except so no raw
`ImportError` traceback ever reaches stdout/stderr. Missing modules are reported by their pip/conda
distribution name (e.g. `pyyaml`), not their import name (`yaml`) -- the floor's
distribution-name -> import-name pairs (`pyyaml`->`yaml`, `requests`->`requests`,
`packaging`->`packaging`, `truststore`->`truststore`, `ruamel.yaml`->`ruamel.yaml`,
`conda-forge-metadata`->`conda_forge_metadata`) are exact and load-bearing -- PyYAML's import name is
`yaml`, not `pyyaml`. `ensure_import_floor(interpreter: str) -> None` raises `CfeImportFloorError`
(identifier `cfe:import-floor-missing`) naming every missing module and the interpreter path when
`probe_import_floor` reports any gap.

**Block If:** none identified -- FR-3, D-7, AD-2/3/5, and the existing
`resolve.py`/`cli.py`/`errors.py`/`exit_codes.py` conventions fully specify this work.

**Never:** Wire `cli.py` to call `resolve_cfe_interpreter`, `probe_import_floor`, or
`ensure_import_floor` -- no CFE-dependent verb exists yet (Epic 2); that wiring belongs to whichever
story first implements one. Add a `--cfe-timeout`/`MASON_CFE_TIMEOUT` flag or read one from
`os.environ` -- that knob is Story 1.10's; use a private module-level timeout constant in `cfe.py`
for now. Build `cfe.py`'s full CFE-script adapter table, `CfeResult`, or JSON-stdout extraction --
that is Story 2.1's larger scope; this story seeds the file with only the interpreter-floor probe.
Validate that the selected interpreter path exists as a file before probing -- an unusable path is
indistinguishable from a spawn failure and both fold into "floor unsatisfied" via the same
`OSError`/`TimeoutExpired` handling, without a second error type.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Flag wins over env and default | `explicit="/x/py"`, `environ={"MASON_CFE_PYTHON": "/y/py"}` | `path="/x/py"`, `step=STEP_FLAG` | none |
| Env wins over `sys.executable` | `explicit=None`, `environ={"MASON_CFE_PYTHON": "/y/py"}` | `path="/y/py"`, `step=STEP_ENVIRONMENT` | none |
| Whitespace-only flag/env falls through | `explicit="  "`, `environ={"MASON_CFE_PYTHON": ""}` | `path=sys.executable`, `step=STEP_RUNNING_INTERPRETER` | none |
| Nothing given at all | `explicit=None`, `environ={}` | `path=sys.executable`, `step=STEP_RUNNING_INTERPRETER` | none |
| Full floor importable | probed interpreter has all 6 modules | `ImportFloorResult(interpreter=X, missing=())`; `ensure_import_floor` returns `None` | none |
| Partial floor missing | probe reports `truststore` and `ruamel.yaml` absent | `missing=("truststore", "ruamel.yaml")` in floor order; `ensure_import_floor` raises `CfeImportFloorError` naming both plus `interpreter` | typed error, no traceback |
| Second probe of the same interpreter in one process | `probe_import_floor` called twice, same `interpreter` string | subprocess spawned once; second call returns the cached result | none |
| Interpreter cannot be spawned at all | `interpreter` path does not exist / not executable | `subprocess.run` raises `OSError`; caught, every floor module reported missing | typed error via `ensure_import_floor`, no raw `OSError`/traceback surfaced |

</intent-contract>

## Code Map

(paths relative to `src/shared/packages/pyforge-mason/`)

- `src/pyforge/mason/resolve.py` (extend) -- add the pure interpreter-selection chain:
  `ResolvedCfeInterpreter`, `STEP_RUNNING_INTERPRETER`, `_ENV_CFE_PYTHON`, `resolve_cfe_interpreter`.
- `src/pyforge/mason/errors.py` (extend) -- add `CfeImportFloorError(MasonError)`.
- `src/pyforge/mason/cfe.py` (new) -- `CFE_IMPORT_FLOOR` (distribution -> import name),
  `ImportFloorResult`, `probe_import_floor` (cached, subprocess-based), `ensure_import_floor` (raises
  `CfeImportFloorError`). Seeds the file AD-3/AD-4 reserve; Story 2.1 extends it.
- `tests/unit/test_resolve.py` (extend) -- `resolve_cfe_interpreter` coverage mirroring the existing
  root-chain test style.
- `tests/unit/test_errors.py` (extend) -- `CfeImportFloorError`'s identifier and message.
- `tests/unit/test_cfe.py` (new) -- `probe_import_floor` (mocked `subprocess.run`), caching,
  `ensure_import_floor`, the `OSError`/timeout fold-into-missing path.

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/mason/resolve.py` -- add `ResolvedCfeInterpreter` (`@dataclass(frozen=True)`,
  `path: str`, `step: str`), `STEP_RUNNING_INTERPRETER = "running-interpreter"`, private
  `_ENV_CFE_PYTHON = "MASON_CFE_PYTHON"`, and `resolve_cfe_interpreter(explicit: str | None, environ:
  Mapping[str, str]) -> ResolvedCfeInterpreter` implementing flag -> env -> `sys.executable`, reusing
  `STEP_FLAG`/`STEP_ENVIRONMENT` -- FR-3, D-7, AD-5.
- [x] `src/pyforge/mason/errors.py` -- add `CfeImportFloorError(MasonError)`: constructor
  `(missing: Sequence[str], interpreter: str)`, identifier `cfe:import-floor-missing`, message naming
  every missing module and the interpreter path -- FR-3, NFR-14.
- [x] `src/pyforge/mason/cfe.py` -- create the module: `CFE_IMPORT_FLOOR` (ordered
  distribution->import-name pairs for `pyyaml`/`requests`/`packaging`/`truststore`/`ruamel.yaml`/
  `conda-forge-metadata`), `ImportFloorResult` (`@dataclass(frozen=True)`, `interpreter: str`,
  `missing: tuple[str, ...]`), a private probe-script builder wrapping each module's import in
  try/except, `probe_import_floor(interpreter: str) -> ImportFloorResult` (`functools.lru_cache`-
  wrapped, `subprocess.run` with list argv/timeout/`check=False`, `OSError`/`TimeoutExpired` folded
  into all-missing), and `ensure_import_floor(interpreter: str) -> None` raising
  `CfeImportFloorError` when `missing` is non-empty -- FR-3, D-7, AD-2, AD-3.
- [x] `tests/unit/test_resolve.py` -- cover every interpreter-selection I/O-matrix row plus
  flag-only/env-only variants and a frozen-immutability check for `ResolvedCfeInterpreter`.
- [x] `tests/unit/test_errors.py` -- `CfeImportFloorError`'s identifier, and that its message
  contains every missing module name and the interpreter path.
- [x] `tests/unit/test_cfe.py` -- cover every probe I/O-matrix row via a mocked `subprocess.run`,
  plus the caching row (assert the mock is called once across two `probe_import_floor` calls with the
  same interpreter, using `.cache_clear()` for test isolation), and `ensure_import_floor`'s
  raise/no-raise paths.

**Acceptance Criteria:**
- Given `resolve.py`, when the interpreter is selected, then the chain is `--cfe-python` ->
  `MASON_CFE_PYTHON` -> `sys.executable`, first match wins.
- Given a selected interpreter, when the CFE import floor is probed, then `pyyaml`, `requests`,
  `packaging`, `truststore`, `ruamel.yaml`, and `conda-forge-metadata` are each checked for
  importability under that interpreter, and the probe result is cached for the process lifetime.
- Given an interpreter missing part of the floor, when `ensure_import_floor` is called, then a typed
  error names the missing modules and the interpreter path, and no raw `ImportError` traceback from
  the probe subprocess reaches the caller.

## Spec Change Log

## Review Triage Log

### 2026-08-09 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7 (medium: 4, low: 3)
- defer: 0
- reject: 3
- addressed_findings:
  - `[medium]` `[patch]` Both Blind Hunter and Edge Case Hunter independently found that the probe
    script's `except ImportError:` only catches `ImportError` -- a corrupted install failing an
    import with a different exception (`SyntaxError`, `AttributeError`, ...) would propagate
    uncaught and abort probing of every module after it in `CFE_IMPORT_FLOOR`'s order. Broadened to
    `except Exception:` in `_build_probe_script`; added
    `test_build_probe_script_reports_missing_for_a_module_that_does_not_exist` (a real, non-mocked
    execution proving a genuinely-missing module still yields a clean `:missing` line, not a
    traceback).
  - `[medium]` `[patch]` Both reviewers independently found that `probe_import_floor` only caught
    `OSError`/`subprocess.TimeoutExpired`, leaving `UnicodeDecodeError` (raised by `subprocess.run`
    when a candidate interpreter's stdout can't be decoded as text) to propagate raw -- exactly the
    "no raw traceback reaches the user" failure this module exists to prevent, just via a different
    exception type. Added `UnicodeDecodeError` to the caught-exceptions tuple, folded into
    all-missing like the other two.
  - `[medium]` `[patch]` Both reviewers independently found that `CfeImportFloorError`'s docstring
    claims "never constructed with an empty `missing`" as an invariant, but the constructor
    performed zero validation -- unlike `MasonError.__init__`, which is scrupulous about validating
    both fields. `CfeImportFloorError(missing=(), ...)` silently produced an incoherent message
    ("...import floor: ", nothing listed). Added a `ValueError` guard matching `MasonError`'s
    validation rigor; added `test_cfe_import_floor_error_rejects_empty_missing`.
  - `[medium]` `[patch]` Blind Hunter found that `_build_probe_script()`'s actual generated source
    was never exercised by the test suite -- every test mocks `subprocess.run` wholesale, so a
    regression in the f-string/`repr()`/print logic would ship with a fully green suite. Added
    `test_build_probe_script_actually_runs_correctly_under_a_real_interpreter` (executes the real
    generated script under `sys.executable`, asserts marker format) and the missing-module
    real-execution test above.
  - `[low]` `[patch]` Blind Hunter found `CfeImportFloorError.__init__` stores `self.missing =
    missing` as whatever `Sequence` was passed, not coerced to `tuple`, unlike every other shape in
    this story. Now coerces via `tuple(missing)`; added
    `test_cfe_import_floor_error_coerces_missing_to_a_tuple`.
  - `[low]` `[patch]` Tidied `probe_import_floor`'s stdout parsing from suffix-based
    `rsplit(":", 1)`/`endswith` matching to exact `f"{import_name}:ok" in stdout_lines` membership
    checks against `CFE_IMPORT_FLOOR`'s known names -- clearer and more directly tied to the known
    floor than string-suffix parsing, though on inspection the original `rsplit(":", 1)` already
    handled an embedded colon correctly (splits at the *last* colon), so this is a clarity
    improvement, not a fix for an exploitable bug as first suspected.
  - `[low]` `[patch]` Blind Hunter found `resolve_cfe_interpreter("", {})` (empty string, distinct
    from whitespace) was exercised only by the never-raises parametrization, which asserts no crash
    but never the actual outcome. Added
    `test_interpreter_empty_string_flag_and_env_fall_through` asserting the fall-through to
    `sys.executable`. Also added `test_ensure_import_floor_reuses_probe_import_floor_cache` (Blind
    Hunter: the caching guarantee was proven only via direct `probe_import_floor` calls, never
    through `ensure_import_floor`, its actual second public entry point) and
    `test_nonzero_returncode_with_partial_output_still_credits_printed_modules` (Edge Case Hunter:
    the realistic manifestation of the cascading-crash scenario -- a subprocess that exits non-zero
    after printing some but not all `:ok` lines -- had zero direct test coverage despite already
    being handled correctly by the existing `check=False` design).

**Rejected findings (3):** `ImportFloorResult` folding "interpreter cannot be spawned at all" and
"interpreter runs but is genuinely missing packages" into the same `missing` shape, with no way for
a future caller to distinguish them (Blind Hunter) -- this is exactly what the spec's Boundaries
mandate verbatim ("both fold into 'floor unsatisfied' via the same `OSError`/`TimeoutExpired`
handling, without a second error type"); a Story 2.1 concern at most, not this story's. The
process-lifetime cache having no public invalidation path (Blind Hunter) -- "cached for the process
lifetime" is the AC's literal requirement, and the hypothetical (a caller installing packages into
the probed interpreter mid-process) is speculative future-proofing with no story-level driver.
`sys.executable` theoretically being an empty string inside an embedded/frozen CPython interpreter
per CPython docs (Edge Case Hunter) -- Mason is an installed CLI entry point (`pyproject.toml`
`[project.scripts]`), never an embedded runtime; this scenario has no realistic path to occurring in
Mason's actual deployment model.

## Design Notes

The import-floor probe cannot live in `resolve.py` despite the AC's "Given `resolve.py`" framing on
the selection half: checking importability under a *different* interpreter than the one currently
running requires spawning that interpreter, which AD-5 forbids in `resolve.py` and
`tests/meta/test_dependency_direction.py` structurally enforces (only `cli.py`/`cfe.py`/
`engines/*.py` may `import subprocess`). The architecture's own CFE-seam-to-FR mapping table already
assigns FR-1..FR-6 to `cfe.py` *and* `resolve.py` together, and the AC's second Given-clause (the
probe) drops the "Given `resolve.py`" anchor the first one (selection) has -- so this split is the
intended reading, not a deviation. `cfe.py` is created here at minimal scope (constants, one probe
function, one raising helper) rather than left for Story 2.1, since AD-2's subprocess allowlist gives
this story no other legal home for the probe; Story 2.1 extends the same file with the script-adapter
table without needing to create it from scratch.

`ResolvedCfeInterpreter.path` is `str`, not `Path` (unlike `ResolvedCfeRoot.root`) -- it mirrors
`sys.executable`'s own type and is passed straight through to `subprocess.run`'s argv, never
filesystem-joined.

`_PROBE_TIMEOUT_SECONDS` is a private constant, not a configurable knob, because
`--cfe-timeout`/`MASON_CFE_TIMEOUT` is Story 1.10's closed v1 knob (AD-13) -- wiring it here would
add a flag half a story early.

## Verification

**Commands:**
- `pixi run -e pyforge-mason pyforge-mason-test` -- expected: full suite green (existing + new
  `test_cfe.py`, extended `test_resolve.py`/`test_errors.py`).

## Auto Run Result

Status: done

- **Implemented change:** added the interpreter-selection chain (`resolve_cfe_interpreter`,
  `ResolvedCfeInterpreter`, `STEP_RUNNING_INTERPRETER`) to `resolve.py`, seeded a new `cfe.py` with
  the CFE import-floor probe (`CFE_IMPORT_FLOOR`, `ImportFloorResult`, `probe_import_floor`,
  `ensure_import_floor`), and added `CfeImportFloorError` to `errors.py` -- FR-3, D-7, AD-2, AD-3,
  AD-5. Not wired into `cli.py`: no CFE-dependent command exists yet to call it (mirrors Story 1.5).
- **Files changed:**
  - `src/shared/packages/pyforge-mason/src/pyforge/mason/resolve.py` -- added the pure
    `resolve_cfe_interpreter` chain alongside the existing root-resolution chain.
  - `src/shared/packages/pyforge-mason/src/pyforge/mason/cfe.py` (new) -- the CFE port, seeded
    minimally: import-floor constant, probe (subprocess-based, cached, hardened during review to
    catch any import-time exception and `UnicodeDecodeError`, not just `ImportError`/`OSError`/
    `TimeoutExpired`), and the raising helper.
  - `src/shared/packages/pyforge-mason/src/pyforge/mason/errors.py` -- added `CfeImportFloorError`,
    hardened during review to validate non-empty `missing` and coerce it to a `tuple`.
  - `src/shared/packages/pyforge-mason/tests/unit/test_resolve.py`,
    `tests/unit/test_errors.py`, `tests/unit/test_cfe.py` (new) -- full coverage of both chains, the
    probe (including two real, non-mocked interpreter executions), and the error class, plus the
    review-driven regression tests listed in the triage log.
- **Review findings breakdown:** 2 independent reviewers (Blind Hunter, Edge Case Hunter, no shared
  context) surfaced 10 distinct findings after dedup -- 7 patches applied (4 medium: broadened
  exception handling in the probe script, caught `UnicodeDecodeError`, validated
  `CfeImportFloorError`'s `missing`, added a real-execution test for the probe script; 3 low: tuple
  coercion, clarity-only parsing tidy-up, two test-coverage gaps closed), 0 deferred, 3 rejected
  (two spec-mandated-verbatim design choices, one deployment-model-unrealistic edge case). See the
  Review Triage Log for the full audit trail.
- **Follow-up review recommendation:** false -- all 7 patches are localized to one new, still-unwired
  module (`cfe.py`) plus one new error class; none touches an existing live caller, a public API
  contract, or a security/data-impact surface, and each patched behavior now has dedicated test
  coverage (10 new tests added during the review pass alone).
- **Verification:** `pixi run -e pyforge-mason pyforge-mason-test` -> 170 passed (full suite: 163
  after initial implementation + 7 new tests added during the review pass covering every patched
  finding).
- **Residual risks:** none identified beyond the rejected findings' explicitly out-of-scope items
  (spawn-failure and genuinely-missing-package are deliberately indistinguishable in
  `ImportFloorResult`, by spec design -- Story 2.1 or whichever story first wires a CFE-dependent
  command may want to reconsider this if a distinct user-facing message for each becomes valuable).
