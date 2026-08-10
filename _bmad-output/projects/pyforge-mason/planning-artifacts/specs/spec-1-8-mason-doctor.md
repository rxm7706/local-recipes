---
title: '`mason doctor`'
type: 'feature'
created: '2026-08-09'
status: 'done'
baseline_revision: 'd93479d1b107df142c9ba401ab9c6c95ec010aab'
final_revision: '05e404797c9435f4dde6f9bb42a409c5003284be'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `cli.py`'s `doctor` branch is still Story 1.4's placeholder (`"not implemented yet"`);
nothing composes Stories 1.5-1.7's resolution/probe outcomes into the real self-diagnosis FR-34
promises, and nothing reports engine presence/version at all.

**Approach:** Add `doctor.py` exposing `build_report(cfe_root_arg, cfe_python_arg, environ,
start_directory) -> DoctorReport` that composes `resolve.resolve_cfe_root`,
`resolve.resolve_cfe_interpreter`, and a lazily-imported `cfe.probe_import_floor` into one frozen
dataclass (mason version, CFE root+step, interpreter+step, import-floor status, unavailable verbs,
engine statuses), never raising. Engine presence/version needs a real subprocess call
(`--version`), which AD-2's already-enforced allowlist restricts to `cli.py`/`cfe.py`/`engines/*.py`
-- so this story also seeds a minimal `engines/__init__.py` (`EngineStatus`, `probe_known_engines()`
for `pixi`/`twine`/`conda-lock`/`build`) scoped to presence+version only; Story 3.1 ("Engine protocol
and provisioning") owns the full AD-12 protocol, typed absent-error, and pixi.toml version-range
sync on top of this seed. Wire `cli.py`'s doctor branch to call `build_report` and render
`dataclasses.asdict(report)`.

## Boundaries & Constraints

**Always:** `doctor.py` never raises and `cli.py`'s doctor branch keeps returning `EXIT_OK`
unconditionally, even with CFE/engines absent (FR-34, AD-6). `doctor.py` imports `cfe` lazily
(inside `build_report`, not at module level) -- AD-6 -- and calls only the non-raising
`probe_import_floor`/`resolve_cfe_root`/`resolve_cfe_interpreter`, never `ensure_import_floor`/
`ensure_cfe_root`. `engines/__init__.py` is the only new file besides `doctor.py` that may
`import subprocess` (AD-2's existing allowlist already covers `engines/*.py` -- verify
`tests/meta/test_dependency_direction.py` still passes unedited). Engine PATH lookups use
`shutil.which`; a probe that finds nothing on PATH reports `available=False, version=None` and
never raises or blocks doctor's report. `unavailable_verbs` names `"recipe"` when the CFE root is
unresolved OR the import floor has any gap (both structurally block Epic 2's not-yet-built
`recipe.py`); `package`/`environment` are never listed (AD-6: CFE-independent). `DoctorReport` and
`EngineStatus` are `@dataclass(frozen=True)` (Consistency Conventions). Extend
`tests/meta/test_capability_tiers.py`'s `_GUARDED_FILENAMES` to include `"doctor.py"` -- AD-6's own
text names it as CFE-independent alongside `package.py`/`environment.py`, and this story is what
gives that guard something real to scan.

**Block If:** none identified -- FR-34, AD-2, AD-6, AD-8, AD-12 (partial), and the existing
`resolve.py`/`cfe.py`/`cli.py`/`render.py` conventions fully specify this work.

**Never:** build AD-12's full Engine protocol (typed `engine:absent`-style error, per-engine
`.build()`/`.upload()`/`.lock()` "operation" methods, `pep517.py`/`twine.py`/`pixi.py`/
`condalock.py` adapter files, pixi.toml version-range declarations + the sync meta-test) --
Story 3.1's exclusive scope; this story's `engines/__init__.py` is a probe-only seed it extends.
Wire any `recipe`/`package`/`environment` verb into `cli.py` -- none exists yet. Compute
`unavailable_verbs` from engine presence -- no verb consuming an engine exists yet (Epic 3/4).
Add `packaging`-based version comparison or parsing -- doctor reports each engine's raw
`--version` output verbatim, never parses/validates it. Create a `models.py` -- every prior
story's dataclass (`ImportFloorResult`, `ResolvedCfeRoot`, `ResolvedCfeInterpreter`) lives in its
owning module; `DoctorReport` follows that precedent in `doctor.py`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| CFE root resolved, floor satisfied | `resolve_cfe_root` returns a real step; `probe_import_floor` returns `missing=()` | `unavailable_verbs == ()`; report's `cfe_import_floor_satisfied is True` | none |
| CFE root unresolved | `resolve_cfe_root` returns `STEP_NOT_FOUND` | `cfe_root is None`; `unavailable_verbs == ("recipe",)` | none -- `build_report` still returns |
| CFE root resolved, floor missing some modules | `probe_import_floor` returns non-empty `missing` | `cfe_import_floor_satisfied is False`; `unavailable_verbs == ("recipe",)` | none |
| Engine on PATH, `--version` succeeds | `shutil.which` finds it; `subprocess.run` returns code 0 with stdout | `EngineStatus(available=True, version=<first non-empty line of stdout/stderr>)` | none |
| Engine not on PATH | `shutil.which` returns `None` | `EngineStatus(available=False, version=None)` | none -- no subprocess attempted |
| Engine on PATH but `--version` errors/times out | `subprocess.run` raises `OSError`/`UnicodeDecodeError`/`TimeoutExpired`, or returns non-zero with empty output | `EngineStatus(available=True, version=None)` | caught, never propagates |
| `mason doctor --format json` | any state above | one JSON document: `schema_version`, `command="doctor"`, `status="ok"`, `data=dataclasses.asdict(report)`, `errors=[]` | none |
| `mason doctor` (text format) | any state above | `EXIT_OK`; stdout contains `doctor: ok` plus one line per report field | none |

</intent-contract>

## Code Map

(paths relative to `src/shared/packages/pyforge-mason/`)

- `src/pyforge/mason/doctor.py` (new) -- `DoctorReport` dataclass + `build_report()`, composing
  `resolve.py`/`cfe.py`/`engines/__init__.py`'s outcomes; never raises.
- `src/pyforge/mason/engines/__init__.py` (new) -- `EngineStatus` dataclass, `probe_known_engines()`
  covering `pixi`/`twine`/`conda-lock`/`build` (binary `pyproject-build`); PATH+`--version` only.
- `src/pyforge/mason/cli.py` (extend) -- import `doctor`, `dataclasses`, `os` (already imported),
  `Path`; replace the doctor branch's stub `data` dict with `doctor.build_report(...)` +
  `dataclasses.asdict(report)`.
- `src/pyforge/mason/resolve.py` (docstring only) -- correct the stale forward-reference comment
  claiming `cli.py` calls `resolve_cfe_root`; `doctor.py` is the actual call site.
- `tests/meta/test_capability_tiers.py` (extend) -- add `"doctor.py"` to `_GUARDED_FILENAMES`.
- `tests/unit/test_doctor.py` (new) -- `build_report` for every I/O-matrix row.
- `tests/unit/test_engines.py` (new) -- `probe_known_engines`/probe helper for every engine
  I/O-matrix row, `subprocess.run`/`shutil.which` mocked (mirrors `test_cfe.py`'s pattern).
- `tests/unit/test_cli.py` (extend) -- replace the four stub-era doctor assertions
  (`test_doctor_invocation_stubs_and_succeeds`, `test_doctor_json_format_emits_the_envelope`,
  `test_doctor_env_var_selects_json_format_without_the_flag`,
  `test_doctor_invalid_env_format_falls_back_to_text`) with real-report assertions, mocking
  `doctor.build_report`.

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/mason/engines/__init__.py` (new) -- `EngineStatus(name, available, version)`
  frozen dataclass; `_KNOWN_ENGINES` table mapping display name -> PATH binary
  (`pixi`->`pixi`, `twine`->`twine`, `conda-lock`->`conda-lock`, `build`->`pyproject-build`);
  `probe_engine(name, binary)` (shutil.which, then `[path, "--version"]` with a timeout,
  `capture_output=True`, `text=True`, `check=False`, catching `OSError`/`UnicodeDecodeError`/
  `subprocess.TimeoutExpired`) and `probe_known_engines() -> tuple[EngineStatus, ...]` -- FR-34,
  AD-2, AD-12 (partial).
- [x] `src/pyforge/mason/doctor.py` (new) -- `DoctorReport` frozen dataclass (see fields in I/O
  matrix + Boundaries) and `build_report(cfe_root_arg, cfe_python_arg, environ, start_directory)`:
  calls `resolve.resolve_cfe_root`/`resolve.resolve_cfe_interpreter` (module-level import, pure),
  lazily imports `cfe` inside the function body to call `cfe.probe_import_floor`, computes
  `unavailable_verbs`, calls `engines.probe_known_engines()` -- FR-34, AD-5, AD-6.
- [x] `src/pyforge/mason/cli.py` -- import `dataclasses`, `Path` from `pathlib`, `doctor` from `.`;
  in the `ns.noun == "doctor"` branch, replace the stub dict with
  `doctor.build_report(getattr(ns, "cfe_root", None), getattr(ns, "cfe_python", None), os.environ,
  Path.cwd())` and pass `dataclasses.asdict(report)` to `render.write` -- FR-34, AD-8.
- [x] `src/pyforge/mason/resolve.py` -- correct the module docstring's stale claim that `cli.py`
  calls `resolve_cfe_root`; name `doctor.py` instead.
- [x] `tests/meta/test_capability_tiers.py` -- add `"doctor.py"` to `_GUARDED_FILENAMES`; add a
  regression fixture proving the detector still fires/permits for a synthetic `doctor.py`.
- [x] `tests/unit/test_engines.py` (new) -- every I/O-matrix engine row: present+version-parses,
  absent, present-but-`--version`-fails/times out; assert `subprocess.run` invoked with list argv,
  no `shell=True`, a timeout.
- [x] `tests/unit/test_doctor.py` (new) -- every I/O-matrix `build_report` row via monkeypatching
  `resolve.resolve_cfe_root`/`resolve_cfe_interpreter`, `cfe.probe_import_floor`, and
  `engines.probe_known_engines`; assert `build_report` never raises for any input combination.
- [x] `tests/unit/test_cli.py` -- replace the four listed stub-era doctor tests: text mode reports
  real fields (mock `doctor.build_report` to return a fixed `DoctorReport`), JSON mode's `data`
  matches `dataclasses.asdict()` of that same report, `status` stays `"ok"` and `errors == []`
  regardless of CFE/engine gaps.

**Acceptance Criteria:**
- Given `mason doctor` runs, when the report is built, then it names the Mason version, the
  resolved CFE root and which step found it, the selected interpreter and import-floor status, and
  every known engine's presence and version.
- Given no CFE installation, when `mason doctor` runs, then it exits `0`, reports the gap, and
  states `"recipe"` as an unavailable verb.
- Given `--format json`, when `mason doctor` runs, then stdout carries exactly one JSON document
  conforming to the five-key envelope, with `status == "ok"` and `errors == []` regardless of
  CFE/engine gaps.

## Spec Change Log

## Review Triage Log

### 2026-08-09 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5 (medium: 2, low: 3)
- defer: 4 (medium: 2, low: 2)
- reject: 5
- addressed_findings:
  - `[medium]` `[patch]` Both Blind Hunter and Edge Case Hunter's separate passes independently
    surfaced testing/reliability issues; Blind Hunter found `probe_engine`'s "first non-empty
    line" version heuristic garbles the real `twine` binary's `--version` banner, which wraps
    across multiple lines mid-word (verified live: `twine version 7.0.0 (...requests-` /
    `toolbelt: 1.0.0...)`), truncating the reported version mid-word. Replaced the first-line
    extraction with full-stripped-output capture (`_stripped_or_none`, preserving interior
    newlines) so a wrapped banner survives intact; added a regression test reproducing the exact
    twine banner shape.
  - `[medium]` `[patch]` Blind Hunter found `test_build_report_never_raises_against_a_real_
    unresolved_environment` performs live, unmocked `shutil.which`/`subprocess.run` calls via
    `engines.probe_known_engines()` reading the real process `PATH` -- the one test in the suite
    that doesn't follow AD-16's hermetic-test convention every sibling test observes, risking
    flakiness on a runner with a slow/hung PATH entry. Pointed `PATH` at an empty directory via
    `monkeypatch.setenv`, keeping `resolve.py`'s chains and `cfe.py`'s real subprocess probe
    (invoked by full `sys.executable` path, unaffected by `PATH`) genuinely unmocked.
  - `[low]` `[patch]` Blind Hunter found `doctor.py`'s module docstring misattributes the
    `dataclasses.asdict(report)` call to `render.py::render_json`, when `cli.py` is the actual
    call site (`render.py` only ever receives a plain `Mapping`). Corrected the attribution.
  - `[low]` `[patch]` Blind Hunter found `test_doctor_calls_build_report_with_flags_environ_and_
    cwd`'s own docstring claims to prove `os.environ` is passed through, but no assertion checked
    `call_args.args[2]`. Added `assert args[2] is os.environ`.
  - `[low]` `[patch]` Blind Hunter found no test exercises `main()` with `--cfe-python` explicitly
    given end-to-end (only its absent-flag default was covered, asymmetric with `--cfe-root`).
    Extended the existing test to pass both flags together and added a second test proving the
    absent-flag case still resolves to `None`.
- Deferred findings (4, logged to `deferred-work.md`): `render_text`'s shallow rendering makes
  `mason doctor`'s default-format `engines` field an unreadable one-line tuple-of-dicts `repr()`
  (pre-existing Story 1.4 limitation, first exposed by doctor's nested data -- medium); no overall
  time budget across the four sequential engine probes plus the import-floor probe, up to ~1
  minute worst case with a hung binary (deliberate scope boundary, not this story's spec -- medium);
  `cfe.probe_import_floor`'s process-lifetime `lru_cache` (Story 1.6) means a long-lived process
  keeps reporting stale floor status (pre-existing, rare -- low); `resolve_cfe_root`'s explicit
  flag/env steps (Story 1.5) don't validate the CFE marker directory exists, so a bogus
  `--cfe-root` is reported "resolved" by doctor (pre-existing, documented in `resolve.py`'s own
  docstring, but works against the epic's "truth about what it cannot do" framing -- low).

**Rejected findings (5):** Edge Case Hunter's `Path.cwd()`-raises-`OSError`-if-cwd-is-deleted
scenario in `cli.py` -- the existing generic `except Exception` handler in `main()` (AD-7) already
projects any such unanticipated exception to `EXIT_FAILED` with a full traceback, which is the
documented, correct behavior for a machine-is-falling-apart edge case, not a gap FR-34's
always-`EXIT_OK` guarantee (which is specifically about CFE/engine gaps, not OS-level failures)
was meant to cover. Blind Hunter's observation that `build_report` always probes the import floor
even when the CFE root is already unresolved -- this is the story's own documented, deliberate
design choice (see `doctor.py`'s module docstring): interpreter floor-readiness is independently
useful diagnostic information regardless of whether CFE's on-disk location is known. Blind
Hunter's note that `probe_engine` conflates "tool doesn't support `--version`" with "probe
failed" -- explicitly an accepted limitation of this story's minimal probe-only seed (already
documented in the module docstring), and all four current known engines support `--version`, so
no live engine hits this. Blind Hunter's suggestion for a meta-test guarding `DoctorReport`'s
future JSON-serializability -- the current shape is already proven serializable end-to-end by
`test_doctor_json_mode_data_matches_dataclasses_asdict_of_the_report`'s full `json.dumps`/
`json.loads` round-trip; guarding against a hypothetical future non-serializable field is
speculative test infrastructure beyond this story's scope. Blind Hunter's note that this PR needs
the repo's `maintenance` label since it touches nothing under `recipes/` -- not applicable at this
step, which only commits locally and does not open or update a PR.

## Design Notes

`engines/__init__.py`'s `probe_known_engines()` is deliberately NOT the AD-12 "one protocol" adapter
registry -- it exists only because AD-2's subprocess allowlist (`cli.py`, `cfe.py`, `engines/*.py`)
gives `doctor.py` no other legal way to obtain a real `--version` string, and FR-34's own
consequence list requires one. Story 3.1 ("Engine protocol and provisioning") is chartered
separately for the typed absent-error, the `name`/`probe()`/operation protocol, per-engine adapter
files, and the pixi.toml version-range + sync meta-test; it extends this file rather than
recreating it, mirroring how Story 1.6 extended `resolve.py` and Story 1.7 extended `cfe.py`.

`build`'s PATH binary is `pyproject-build`, not `build` -- the `build` PyPI/conda package's
`console_scripts` entry point is named `pyproject-build` (`build.__main__:entrypoint`); there is no
bare `build` executable. Verified live: `pyproject-build --version` prints `build 1.5.0 (...)`.

`doctor.py` imports `cfe` lazily (function-body, not module-level) per AD-6's text naming
`doctor.py` alongside `package.py`/`environment.py` as CFE-independent -- `probe_import_floor`
itself never raises (Story 1.6), so this satisfies "must never fail because CFE is unresolvable"
even though the import happens.

## Verification

**Commands:**
- `pixi run -e pyforge-mason pyforge-mason-test` -- expected: full suite green (existing tests
  updated for the real doctor output, plus every new test listed above).

## Auto Run Result

Status: done

- **Implemented change:** `pyforge.mason.doctor.build_report()` composes `resolve.py`'s two pure
  chains, `cfe.py`'s non-raising import-floor probe (lazily imported per AD-6), and a new
  probe-only `pyforge.mason.engines` seed (PATH + `--version` for `pixi`/`twine`/`conda-lock`/
  `build`) into one frozen `DoctorReport`, never raising. `cli.py`'s `doctor` branch now calls it
  and renders `dataclasses.asdict(report)`, replacing the Story 1.4 `"not implemented yet"` stub.
- **Files changed:**
  - `src/shared/packages/pyforge-mason/src/pyforge/mason/doctor.py` (new) -- `DoctorReport` +
    `build_report()`.
  - `src/shared/packages/pyforge-mason/src/pyforge/mason/engines/__init__.py` (new) --
    `EngineStatus` + `probe_engine()`/`probe_known_engines()`, a minimal AD-12 seed (Story 3.1
    owns the full protocol).
  - `src/pyforge/mason/cli.py` -- wired the doctor branch to `doctor.build_report()`.
  - `src/pyforge/mason/resolve.py` -- corrected a stale docstring claim about the `resolve_cfe_root`
    call site.
  - `tests/meta/test_capability_tiers.py` -- `doctor.py` added to the AD-6 module-level-`cfe`-import
    guard.
  - `tests/unit/test_doctor.py`, `test_engines.py` (new) -- full I/O-matrix coverage.
  - `tests/unit/test_cli.py` -- the four Story-1.4-era doctor stub tests replaced with real-report
    assertions.
- **Review findings breakdown:** 2 independent reviewers (Blind Hunter, Edge Case Hunter, no
  shared context) surfaced 14 distinct findings after dedup -- 5 patches applied (2 medium: a
  real `twine --version` banner was garbled mid-word by a first-line-only version-capture
  heuristic, now captures the full stripped output verbatim with a regression test reproducing
  the exact banner shape; one test performed live unmocked `PATH` lookups in violation of the
  suite's AD-16 hermetic-test convention, now isolated via a monkeypatched empty `PATH`. 3 low:
  a docstring misattributed which module calls `dataclasses.asdict`, a test's docstring claimed
  an assertion it didn't make, and `--cfe-python`'s end-to-end pass-through was untested — all
  fixed), 4 deferred (a pre-existing `render_text` nested-data formatting limitation first exposed
  by doctor's richer data; no time budget across the sequential engine + floor probes; a
  pre-existing `lru_cache` staleness risk in long-lived processes; a pre-existing unvalidated-path
  gap in `resolve_cfe_root`'s explicit flag/env steps), 5 rejected (an OS-level `Path.cwd()`
  failure already handled correctly by existing generic exception handling; a documented
  deliberate design choice to always probe the import floor; a documented, currently-inert
  probe-failure-mode limitation; a speculative future-proofing test ask already covered by an
  existing round-trip test; a PR-process note not applicable to a local-commit-only step). See the
  Review Triage Log for the full audit trail.
- **Follow-up review recommendation:** false -- both medium findings were confined to this
  story's own brand-new code (a probe-only module with no downstream consumers yet beyond
  doctor's own report, and a test-only hermeticity fix with zero production-code impact), the
  three low findings were localized doc/test-coverage fixes, no security/data-safety/exit-code
  contract behavior changed, and every patched behavior now has dedicated regression coverage
  (236 passing tests, up from 234 after initial implementation, up from the pre-story baseline
  of 196).
- **Verification:** `pixi run -e pyforge-mason pyforge-mason-test` -> 236 passed.
- **Residual risks:** none beyond the four deferred, pre-existing/scope-boundary items logged to
  `deferred-work.md` -- none of them block Story 1.8's own FR-34 acceptance criteria, which are
  fully met.
