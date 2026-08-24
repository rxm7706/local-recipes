---
title: 'mason recipe build'
type: 'feature'
created: '2026-08-12'
status: 'done'
baseline_revision: 'f6b3e8f2b32efdedb498c47fa2352f5e17bb4594'
final_revision: '7b61e163a18447fb776bbf53899e85f32c0e4dd6'
review_loop_iteration: 0
followup_review_recommended: false # review pass: 7 localized low/medium patches, no structural or security-behavior change (AD-14 addition is coverage-only) -- judged below the follow-up threshold
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
  - '{project-root}/_bmad-output/projects/pyforge-mason/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** FR-9's `recipe build` is unimplemented, and PRD OQ-8 leaves open whether CFE's Docker/
CI-parity build is adapter-reachable at all ("if no adapter-reachable entry point exists, drop FR-9's
Docker bullet... Revisit: at S-2.6").

**Approach:** Investigation of the real scripts resolves OQ-8: **yes, reachable.** Add `recipe.py::build`
invoking two new STREAM-mode (AD-25) `cfe.py` adapters -- `build_native` (bash `native-build.sh`,
default) and `build_docker` (`build-locally.py`, opt-in `--docker` + required `--config`) -- via
`run_streamed`, reporting a `BuildResult` through the normal render path.

## Boundaries & Constraints

**Always:**
- Native is the default; `--docker` opts into CI-parity, never implicit.
- `--docker` requires `--config`; given without the other, `main()` returns `EXIT_USAGE` before any
  CFE resolution (mirrors `recipe new`'s pre-resolution usage-error precedent).
- Child stderr streams live via `run_streamed` (AD-25) under a mandatory timeout; on expiry,
  `subprocess.TimeoutExpired` is translated to `CfeTimeoutError` (mirroring `_invoke_captured`'s
  translation -- `run_streamed` itself re-raises the bare stdlib exception).
- A non-zero child returncode is DATA on `BuildResult`, never raised (AD-4, mirrors `doctor`'s "the
  gap is data, not a command failure" precedent) -- `cli.py` renders status `"ok"`/`EXIT_OK` for a
  Mason-successful invocation whose delegated build itself failed; `data.returncode` is the signal.
- `native-build.sh` is invoked as `["bash", str(script), recipe_path]` -- through `bash`, not the
  resolved CFE interpreter (it is a bash script) -- a disclosed, isolated exception to
  `_invoke_captured`'s Python-only convention.
- `build-locally.py` resolves at `root / "build-locally.py"` (CFE root's top level), not
  `root/.claude/scripts/conda-forge-expert/` -- confirmed present, confirmed invocable
  (`[interpreter, script, config]`); the one `_CFE_SCRIPTS` entry outside the standard subdirectory.
- `artifact_dir` reports `build_artifacts/<config>/` (documented build-infrastructure convention, not
  recipe knowledge) -- `<config>` from a new pure `resolve.detect_native_build_config()` (native,
  mirrors native-build.sh's own uname case table, non-overridable) or the user's `--config` (docker);
  `None` on an undetected host rather than guessed.

**Block If:** None identified -- OQ-8 reachability, script location, and the error-vs-data philosophy
are all resolved above from the real scripts' own read behavior.

**Never:**
- No `ensure_import_floor` gate for either mode -- neither `native-build.sh` (bash) nor
  `build-locally.py` (stdlib-only argparse/subprocess/platform/glob) needs CFE's Python import floor;
  gating on it would block a build over an unrelated precondition.
- No pre-validation of `recipe_path`'s existence, and no parsing of either script's stdout to extract
  a filename -- mirrors `recipe new`'s "no Mason-side interpretation of CFE's own output" boundary.
- No `--platform`/config override for native mode -- `native-build.sh` has no such flag; exposing one
  would let Mason report a directory the script never actually used.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Native happy path | `recipe build recipes/foo` | `["bash", native-build.sh, "recipes/foo"]` runs via `run_streamed`; `BuildResult(mode="native", config=<detected>, returncode=0, artifact_dir="build_artifacts/<config>")` rendered | No error |
| Native build fails | child exits 1 | Same shape, `returncode=1` | No error raised; failure is data |
| Docker happy path | `recipe build recipes/foo --docker --config linux64` | `[interpreter, build-locally.py, "linux64"]` runs; `BuildResult(mode="docker", config="linux64", ...)` | No error |
| `--docker` without `--config` | `recipe build recipes/foo --docker` | usage error before CFE resolution | `EXIT_USAGE`, stderr |
| `--config` without `--docker` | `recipe build recipes/foo --config linux64` | usage error before CFE resolution | `EXIT_USAGE`, stderr |
| CFE root unresolved | no root found | `CfeUnresolvedError` before any subprocess spawns | `EXIT_CFE_UNAVAILABLE` |
| Build exceeds timeout | `run_streamed` hits `--cfe-timeout` | `CfeTimeoutError`; child killed+reaped (`run_streamed`'s own guarantee) | `EXIT_FAILED`, stderr |
| Unsupported native host | unmapped `platform.system()/machine()` | `config=None`, `artifact_dir=None`; native-build.sh still runs, reports its own failure via returncode | No Mason-level error |

</intent-contract>

## Code Map

(paths relative to `src/shared/packages/pyforge-mason/`)

- `src/pyforge/mason/models.py` -- add `BuildResult` (`mode`, `config: str | None`, `returncode`,
  `stdout`, `artifact_dir: str | None`).
- `src/pyforge/mason/resolve.py` -- add `detect_native_build_config() -> str | None`: pure
  `platform.system()`/`platform.machine()` mapping mirroring `native-build.sh`'s 5-way uname case
  table (linux64/linux_aarch64/osxarm64/osx64/win64); `None` on an unrecognized host, never raises.
- `src/pyforge/mason/cfe.py` -- add `_CFE_SCRIPTS["build_native"] = "native-build.sh"` and
  `["build_docker"] = "build-locally.py"`; `_BUILD_NATIVE_TIMEOUT_SECONDS = 3600.0` /
  `_BUILD_DOCKER_TIMEOUT_SECONDS = 7200.0`; `build_native(recipe_path, *, root, timeout=None,
  stderr_sink=None)` and `build_docker(config, *, root, interpreter, timeout=None,
  stderr_sink=None)` -- both STREAM-mode via `run_streamed`, translating `subprocess.TimeoutExpired`
  to `CfeTimeoutError`, computing `artifact_dir` from the resolved/given config.
- `src/pyforge/mason/recipe.py` (new) -- `build(recipe_path, *, docker, config, cfe_root_arg,
  cfe_python_arg, cfe_timeout_arg, environ, start_directory, stderr_sink=None) -> BuildResult`:
  resolves root (+ interpreter, docker only), calls `cfe.ensure_cfe_root`, dispatches to the adapter.
- `src/pyforge/mason/cli.py` -- add `recipe` to the `from . import __version__, doctor, render` line;
  register `build` verb (`recipe_path` positional, `--docker` store_true, `--config` plain string);
  in `main()`, before the `# Unreachable in Story 1.2` fallthrough, dispatch `noun=="recipe" and
  verb=="build"`: validate `--docker`/`--config` pairing (usage error if mismatched) before calling
  `recipe.build(...)`, then `render.write(fmt, sys.stdout, "recipe build", "ok",
  dataclasses.asdict(result), [])`.
- `tests/fixtures/fake_cfe_root/.claude/scripts/conda-forge-expert/native-build.sh` (new) -- stub
  bash script writing a marker line to stderr and exiting per `MASON_FIXTURE_EXIT_CODE`.
- `tests/fixtures/fake_cfe_root/build-locally.py` (new) -- stub Python script at the fixture root
  (mirrors the real repo-root placement), same env-driven pattern.
- `tests/unit/test_resolve.py` -- `detect_native_build_config` coverage (parametrized over the 5
  known host pairs + one unrecognized pair -> `None`), via `monkeypatch` on `platform.system`/
  `platform.machine`.
- `tests/unit/test_cfe.py` -- `build_native`/`build_docker` coverage: real-fixture round-trip,
  timeout translation, argv-shape (bash-not-interpreter for native).
- `tests/unit/test_recipe.py` (new) -- `build()` against `fake_cfe_root`: native/docker happy paths,
  CFE-unresolved propagation.
- `tests/unit/test_cli.py` -- end-to-end `recipe build` verb dispatch (text/JSON, both usage-error
  cases, a failed-build-still-renders-ok case).
- `tests/meta/test_adapter_sole_caller.py` -- update the `_CFE_SCRIPTS`-shape assertion to the new
  four-entry set.

## Tasks & Acceptance

**Execution:**
- [x] `models.py` -- add `BuildResult` -- FR-9.
- [x] `resolve.py` -- add `detect_native_build_config()` -- FR-9, mirrors `native-build.sh`.
- [x] `cfe.py` -- add the two `_CFE_SCRIPTS` entries, two timeout constants, `build_native`,
  `build_docker` -- FR-9, AD-25, AD-4.
- [x] `recipe.py` (new) -- `build()` use-case -- FR-9.
- [x] `cli.py` -- register `recipe build`, wire dispatch + the `--docker`/`--config` usage check --
  FR-9, AD-8.
- [x] `tests/fixtures/.../native-build.sh` + `tests/fixtures/fake_cfe_root/build-locally.py` (new
  stubs) -- FR-9.
- [x] `test_resolve.py`, `test_cfe.py`, `test_recipe.py` (new), `test_cli.py` -- coverage per the I/O
  matrix -- FR-9.
- [x] `test_adapter_sole_caller.py` -- update the table-shape assertion -- FR-9.

**Acceptance Criteria:**
- Given `mason recipe build <path>`, when it runs, then a native host-platform build runs by default
  via `native-build.sh`, streaming stderr live, with no `--docker` needed.
- Given a Docker/CI-parity build, when the user wants one, then `--docker` (plus required `--config`)
  is the only way to select it -- never implicit, and rejected as a usage error if `--config` is
  missing or given without `--docker`.
- Given a completed build (success or failure), when the result is rendered, then the output artifact
  directory and the exit status are both present in text and JSON forms.
- Given a build that exceeds its timeout, when the timeout fires, then `CfeTimeoutError` surfaces and
  no orphaned process remains.

## Spec Change Log

## Review Triage Log

### 2026-08-12 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7 (high: 0, medium: 2, low: 5)
- defer: 1 (medium: 1)
- reject: 3
- addressed_findings:
  - `[medium]` `[patch]` Both reviewers found the AD-14 credential-isolation sentinel regression test (Story 2.3) is explicitly scoped to `probe_import_floor`/`validate_recipe`/`submit_pr` and was never extended to the two new CFE-invoking call sites this story adds. Added `test_jfrog_credential_sentinel_never_appears_in_build_results` (`test_cfe.py`), mirroring the existing test's positive-control (`MASON_FIXTURE_STDOUT` proves inheritance) + negative-assertion (sentinel absent from `result.stdout`) shape for both `build_native` and `build_docker` against `fake_cfe_root`.
  - `[medium]` `[patch]` Both reviewers found `cfe.build_docker`'s `config` parameter was not defensively validated: a direct caller of the public `recipe.build()`/`cfe.build_docker()` API with `config=None` (or blank) — bypassing `cli.py`'s own pairing check — would hit a raw `TypeError` deep inside `subprocess.Popen` rather than a clean, actionable error, inconsistent with `run_streamed`/`_invoke_captured`'s own established defensive-validation convention. Added an upfront `ValueError` guard in `build_docker` plus a parametrized rejection test (`None`/`""`/`"   "`) asserting no subprocess spawns.
  - `[low]` `[patch]` Edge Case Hunter found `cli.py`'s `--docker`/`--config` pairing check used Python falsiness, so `--docker --config ""` (empty string, explicitly supplied) produced the misleading message "requires --config" identical to omitting the flag. Normalized: a whitespace-only `--config` is now treated as absent, matching `_resolve_str`'s established convention elsewhere in the same file. Added a CLI-level regression test.
  - `[low]` `[patch]` Blind Hunter found no test paired a RECOGNIZED native-build host config with a failed build (`returncode != 0`) — the existing nonzero-exit test used an unrecognized host (`config=None`), so "does `artifact_dir` survive a real build failure" had no dedicated assertion. Added `test_build_native_reports_artifact_dir_even_when_the_build_itself_fails`.
  - `[low]` `[patch]` Blind Hunter found `errors.py`'s `CfeTimeoutError` docstring still described itself as CAPTURE-mode-only (`_invoke_captured`), now stale since this story reuses the same exception for the two new STREAM-mode adapters. Corrected the docstring to name both origins.
  - `[low]` `[patch]` Blind Hunter found `build_native`'s docstring never disclosed that `native-build.sh`'s own `"${@:2}"` rattler-build-flag passthrough (`--test skip`, `--target-platform`, etc.) is unreachable through Mason, leaving it ambiguous whether that was deliberate. Added a docstring note naming it a deliberate scope cut (not in the spec's CLI surface), not an oversight.
  - `[low]` `[patch]` Blind Hunter found `_BUILD_DOCKER_TIMEOUT_SECONDS`'s docstring claimed the 2-hour figure was grounded in "this project's own CI experience" with no benchmark, log, or citation anywhere backing it. Softened to a reasoned justification (Docker mode compiles inside a pulled image on top of the same work the native path performs) without the unverified experiential claim.
  - `[medium]` `[defer]` Both reviewers independently found `doctor.py`'s `unavailable_verbs` marks the whole `"recipe"` noun unavailable on any CFE import-floor gap, which is now factually inaccurate for `recipe build` specifically (needs no import floor per this story's own Design Notes) — a real, if narrow, doctor/actual-behavior mismatch. The root cause (per-noun, not per-verb, granularity) is pre-existing from Story 1.8, predates this story, and fixing it is a doctor.py design question out of proportion to redesign unilaterally in a `recipe build`-scoped story. Logged to `deferred-work.md` as `DW-2-6-1`.
  - `[reject]` Blind Hunter's "STREAM mode's `run_streamed` only forwards stderr live, so if `rattler-build` writes its own build progress to stdout, a real `mason recipe build` would appear silently hung for its whole duration" — reproduced directly rather than inherited: ran `rattler-build build` against a throwaway recipe with stdout/stderr captured separately; 100% of its output (3579 bytes) landed on stderr, 0 bytes on stdout. The concern's premise is empirically false for the actual wrapped tool.
  - `[reject]` Edge Case Hunter's/Blind Hunter's "`_noun_verbs: dict[str, argparse._SubParsersAction]` type-annotates against a private argparse class" — cosmetic only, zero runtime consequence, and Python's argparse has no public alternative type for a subparsers-action return value (a well-known stdlib typing gap); no prior convention in this codebase types this differently since nothing captured this return value before this story.
  - `[reject]` Both reviewers' "`build_docker`'s `artifact_dir` is reported unconditionally from the caller-supplied `--config` even when it doesn't correspond to a real platform variant" — considered and rejected on the merits: `build-locally.py` discovers valid configs dynamically via `.ci_support/*.yaml` (`verify_config`), so validating `--config` against any hardcoded set here would duplicate — and could disagree with — the wrapped tool's own judgment, exactly what the spec's Design Notes already forbid ("Mason adds no branch-name or config-enumeration logic of its own"). The actual consequence is low: an invalid config already produces a non-zero `returncode` plus the wrapped script's own stdout enumerating valid configs, which is the real diagnostic a caller would use.

## Design Notes

**Why a non-zero build return code is data, not a raised error (unlike `recipe new`'s
`RecipeGenerationError`):** a failed build is the routine, expected outcome of the recipe-development
iteration loop this whole product exists to support -- structurally the same as a failed `validate`/
`optimize` finding, not an exceptional input error like "no such PyPI package." `mason doctor`
already establishes the precedent that Mason can complete an operation successfully while the
substance of what it reports is itself a failure.

**Why no `ensure_import_floor` gate:** it exists to protect scripts that import CFE's floor packages
(`pyyaml`, `requests`, ...). `native-build.sh` never runs under any Python interpreter, and
`build-locally.py` imports only `glob`/`os`/`platform`/`subprocess`/`sys`/`argparse` (read directly).
Gating on an unrelated precondition would block a build for no real reason.

**`build-locally.py`'s own preconditions are not re-validated by Mason:** it raises if run from the
`main` branch (`verify_system`) and prompts interactively (reads stdin) when `--config` is omitted
and more than one `.ci_support/*.yaml` exists -- exactly why `--config` is required at Mason's own
CLI layer rather than left to fall through (an interactive prompt against `run_streamed`'s
`stdin=DEVNULL` would hang until the timeout). Both failure modes surface honestly through the
child's own non-zero exit and streamed stderr; Mason adds no branch-name or config-enumeration logic
of its own (would itself be re-deriving the wrapped tool's judgment).

## Verification

**Commands:**
- `pixi run -e pyforge-mason pyforge-mason-test` -- expected: full suite green, including the new
  `build_native`/`build_docker`/`detect_native_build_config`/`recipe.build`/`recipe build`-verb tests
  and the updated `_CFE_SCRIPTS`-shape assertion.

## Auto Run Result

**Status:** done.

**Implemented change.** Resolves PRD OQ-8 (whether CFE's Docker/CI-parity build is adapter-reachable
-- confirmed yes) and adds `mason recipe build`: `recipe.py` (new, the `recipe` noun's first
use-case module) composes two new STREAM-mode (AD-25) `cfe.py` adapters, `build_native` (default,
invokes `native-build.sh` through `bash`) and `build_docker` (`--docker`+required `--config`,
invokes the CFE root's own top-level `build-locally.py` under the resolved interpreter), plus a new
pure `resolve.detect_native_build_config()` and `models.BuildResult`. `cli.py` registers the first
real verb in this package (`recipe build`), wiring a manual `--docker`/`--config` pairing usage
check ahead of any CFE resolution. A non-zero delegated build return code is data on `BuildResult`,
never raised (AD-4), mirroring `doctor`'s "the gap is data" precedent.

**Files changed:**
- `src/pyforge/mason/models.py` -- add `BuildResult`.
- `src/pyforge/mason/resolve.py` -- add `detect_native_build_config()`.
- `src/pyforge/mason/cfe.py` -- add `build_native`/`build_docker`, two `_CFE_SCRIPTS` entries, two
  timeout constants; review pass added a `config` blank-value guard to `build_docker` and corrected
  two docstrings (timeout justification, native passthrough scope-cut disclosure).
- `src/pyforge/mason/recipe.py` (new) -- `build()` use-case.
- `src/pyforge/mason/cli.py` -- register + dispatch `recipe build`; review pass normalized a
  whitespace-only `--config` to "absent."
- `src/pyforge/mason/errors.py` -- review pass corrected `CfeTimeoutError`'s docstring (STREAM-mode
  origin was undocumented).
- `tests/fixtures/fake_cfe_root/.claude/scripts/conda-forge-expert/native-build.sh` (new),
  `tests/fixtures/fake_cfe_root/build-locally.py` (new) -- fixture stubs.
- `tests/unit/test_resolve.py`, `tests/unit/test_cfe.py`, `tests/unit/test_recipe.py` (new),
  `tests/unit/test_cli.py`, `tests/meta/test_adapter_sole_caller.py` -- coverage; review pass added
  an AD-14 sentinel test for the two new adapters, a native-mode known-config-plus-failed-build
  test, a `build_docker` blank-config rejection test, and a CLI-level blank-`--config` test.

**Review findings:** 7 patched (medium 2, low 5), 1 deferred (medium, `DW-2-6-1` --
`doctor.py`'s per-noun `unavailable_verbs` granularity), 3 rejected, 0 intent gaps, 0 spec defects.
Full detail in the Review Triage Log above.

**Verification.** `pixi run --frozen -e pyforge-mason pyforge-mason-test` -> **747 passed** (up from
741 at implementation, +6 from the review pass's new tests). `python scripts/spec_surface_reconcile.py`
-> clean after appending a memlog entry naming every file this pass touched and re-stamping the
baseline (`python scripts/spec_surface_check.py --write-baseline --spec pyforge-mason/spec-pyforge-mason`).
`git status` confirms nothing touched under `.claude/skills/conda-forge-expert/`,
`.claude/scripts/conda-forge-expert/`, or `.claude/tools/conda_forge_server.py` (AD-15 holds).
Empirically verified `rattler-build build` writes 100% of its progress to stderr (0 bytes stdout, one
throwaway-recipe reproduction) while triaging a reviewer concern about STREAM mode's live-forwarding
guarantee for this specific wrapped tool.

**Residual risks.**
- `DW-2-6-1` (deferred): `mason doctor` can report `recipe` unavailable due to an import-floor gap
  that `recipe build` does not actually depend on. `mason recipe build` itself is unaffected; only
  `doctor`'s diagnostic is momentarily misleading for this one verb until a future story revisits
  `doctor.py`'s per-noun granularity.
- `build_docker`'s `--config` is forwarded to the wrapped script without validation against a known
  platform set (deliberate -- see the rejected finding above): an invalid value still produces a
  clear non-zero-exit diagnostic from the wrapped tool itself, just not a Mason-side one.
- No CLI passthrough exists for `native-build.sh`'s own trailing rattler-build flags (`--test skip`,
  `--target-platform`, ...) -- disclosed as a deliberate scope cut, not a defect, in `build_native`'s
  docstring; out of this story's AC.
