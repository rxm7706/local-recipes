---
title: 'mason package build'
type: 'feature'
created: '2026-08-13'
status: 'done'
baseline_revision: '124e8ba98cdf1b88add6cc2c2ee6ff1a767e9ea6'
final_revision: '65a59d72602a114a46ae4084ac93b5cd731d7b56'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/src/shared/packages/pyforge-mason/src/pyforge/mason/cfe.py'
  - '{project-root}/src/shared/packages/pyforge-mason/src/pyforge/mason/engines/__init__.py'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `mason package build` (FR-15, FR-21, FR-22) does not exist yet -- CFE has no wheel
build, PyPI packaging, or `.conda` build anywhere, so a user has no single command to produce
distributable artifacts from a project, and `package.py`/`engines/pep517.py`/`engines/pixi.py` are
all unwritten (`package.py` is an import-safety stub only).

**Approach:** Add `package.py::build()`, a CFE-independent use-case that drives two new engine
adapters -- `engines/pep517.py` (wheel+sdist via `python -m build --no-isolation`) and
`engines/pixi.py` (`.conda` via `pixi build`) -- both using Story 3.1's `require_engine`/
`EngineAdapter` protocol, and wire `mason package build PROJECT_PATH [--target library]` into
`cli.py` mirroring `recipe build`'s parser/dispatch shape.

## Boundaries & Constraints

**Always:**
- Artifacts land at `<PROJECT_PATH>/dist/` (wheel+sdist) and `<PROJECT_PATH>/dist-conda/`
  (`.conda`) -- byte-identical directory names to the existing hand-run root `pixi.toml` tasks
  (`pyforge-mason-build-dist`/`-conda`), since FR-24 requires the two to be equivalent.
- Both engine calls run with `cwd=PROJECT_PATH` (`pixi build` has no `--manifest-path` flag, per
  root `pixi.toml`'s own comment) and go through `require_engine("build")`/`require_engine("pixi")`
  first, so an absent engine raises `EngineAbsentError` before any subprocess spawns.
- `package.py` contains **zero** reference to `cfe` -- not even a lazy/nested import (unlike
  `package.py`'s future `conda-forge` ship target, `build()` has no CFE involvement at all) --
  `tests/meta/test_capability_tiers.py` already guards this file.
- `--target` accepts only `library` (default), via `choices=("library",)` on the argparse flag,
  mirroring `--format`'s existing choices pattern -- no new error class needed.
- No Mason-side existence/validity check on `PROJECT_PATH` (AD-1, mirrors `recipe build`'s
  `recipe_path`): the wrapped tool reports its own failure via its returncode.
- A non-zero engine build returncode is DATA on the result, never raised -- mirrors `recipe
  build`'s established "delegated returncode is data" precedent; the CLI branch still reports
  `EXIT_OK`.
- After both builds run, if `wheel_version` and `conda_version` are both non-`None` and disagree,
  raise `PackageVersionMismatchError` (`package:version-mismatch`) naming both values (FR-22) --
  before the function returns a result.
- Each engine subprocess call uses `stderr=None` (inherited) so the child's build output streams
  live to the user's stderr with zero buffering, satisfying AD-25's STREAM-mode rule without
  porting `cfe.run_streamed`'s threaded reader; `stdout` is captured (`PIPE`) so it never reaches
  Mason's own stdout, preserving AD-8's single-JSON-document guarantee under `--format json`.

**Block If:** a live check shows `pixi build`'s actual CLI contract against this member's
`pixi.toml` no longer matches the existing hand-run `pyforge-mason-build-conda` task's flags/`cwd`
assumption above -- that assumption is inherited from already-committed tooling, not this story's
own decision, so a mismatch needs an operator call.

**Never:**
- No upload/ship logic (`twine`, `pixi publish`, staged-recipes submission) -- Stories 3.3-3.9.
- No `--to`/`--ship` flag or `ShipTargetResult`/`ShipReceipt` involvement -- this story adds only
  `build()`, never `ship()`.
- No `application`/`binary` `--target` values (FR-21's v2 scope).
- `engines/pep517.py`/`engines/pixi.py` never import `cfe.run_streamed` (CFE-independence must hold
  at the import-graph level, per `cfe.py`'s own module docstring).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | `mason package build <path>`, both engines on PATH, builds succeed | `wheel_path`/`sdist_path`/`conda_path` all set, `wheel_version == conda_version`, `EXIT_OK` | No error expected |
| Engine absent | `pixi` (or `build`) not on PATH | Nothing built | `EngineAbsentError` (`engine:absent`), `EXIT_FAILED` |
| Version mismatch | wheel version `0.1.0`, conda version `0.2.0` | Aborts, both values shown | `PackageVersionMismatchError` (`package:version-mismatch`), `EXIT_FAILED` |
| One engine's build fails | `pyproject-build` exits 1 | `pep517_returncode != 0`, that artifact path `None`, other engine still runs | No exception -- `EXIT_OK`, failure is data |
| Invalid `--target` | `--target application` | Rejected, message names `library` as the v1 set | argparse usage error, `EXIT_USAGE` |
| CFE root entirely absent | no CFE anywhere on filesystem, no `--cfe-root`/`MASON_CFE_ROOT` | Build still succeeds | No error expected |

</intent-contract>

## Code Map

- `src/pyforge/mason/errors.py` -- add `PackageVersionMismatchError(MasonError)`.
- `src/pyforge/mason/models.py` -- add `PackageBuildResult` frozen dataclass.
- `src/pyforge/mason/engines/pep517.py` -- new adapter (wheel+sdist).
- `src/pyforge/mason/engines/pixi.py` -- new adapter (`.conda`).
- `src/pyforge/mason/package.py` -- add `build()`, replacing the docstring-only stub's body.
- `src/pyforge/mason/cli.py` -- register `package build` verb (parser ~after line 541, dispatch
  ~after line 654, mirroring `recipe build`'s exact shape); refresh `_noun_verbs["package"].metavar`.
- Root `pixi.toml` `pyforge-mason-build*` tasks -- read-only reference for the exact commands/`cwd`/
  output-dir names this story's engines must reproduce; not edited.

## Tasks & Acceptance

**Execution:**
- [x] `errors.py` -- add `PackageVersionMismatchError` (ctor `(wheel_version: str, conda_version: str)`, identifier `package:version-mismatch`, `__reduce__` override) -- mirrors `EngineAbsentError`'s validated-args + `__reduce__` pattern.
- [x] `models.py` -- add `PackageBuildResult(target, project_path, wheel_path, sdist_path, conda_path, wheel_version, conda_version, pep517_returncode, pixi_returncode)`, all-scalar frozen dataclass.
- [x] `engines/pep517.py` -- adapter with `name = "build"`, `probe()`, and a build operation: `require_engine("build")` then `["pyproject-build", "--no-isolation", "--outdir", f"{project_path}/dist"]`, `cwd=project_path`, `stdout=PIPE, stderr=None`, mandatory timeout; parse produced wheel/sdist versions via `packaging.utils.parse_wheel_filename`/`parse_sdist_filename`.
- [x] `engines/pixi.py` -- adapter with `name = "pixi"`, `probe()`, and a build operation: `require_engine("pixi")` then `["pixi", "build", "--output-dir", f"{project_path}/dist-conda"]`, same subprocess shape; parse the produced `.conda` filename's version via `stem.removesuffix(".conda").rsplit("-", 2)`.
- [x] `package.py` -- `build(project_path: str, *, target: str = "library") -> PackageBuildResult`: calls both adapters, compares versions when both present, raises `PackageVersionMismatchError` on mismatch; zero `cfe` reference anywhere in the file.
- [x] `cli.py` -- register `mason package build PROJECT_PATH [--target {library}]`; dispatch renders via `render.write(fmt, sys.stdout, "package build", "ok", dataclasses.asdict(result), [])` and returns `EXIT_OK`, letting `EngineAbsentError`/`PackageVersionMismatchError` propagate to `main()`'s existing `except MasonError` (`EXIT_FAILED`).
- [x] `tests/unit/test_errors.py` -- extend with `PackageVersionMismatchError` coverage (identifier, message, deepcopy/pickle round-trip).
- [x] `tests/unit/test_package.py` -- replace the import-only stub's test with `build()` coverage (mocked adapters): happy path, version mismatch, one engine absent.
- [x] `tests/unit/test_engines_pep517.py`, `tests/unit/test_engines_pixi.py` -- new; mock `subprocess.run`/`shutil.which` on each adapter's own module namespace (mirrors `test_engines.py`'s convention), covering the I/O matrix's per-engine rows.
- [x] `tests/unit/test_cli.py` -- extend with `package build` parser/dispatch coverage, including `--target` choices rejection.
- [x] `tests/integration/test_package_build.py` -- new (first file in this dir); `slow`-marked real `mason package build` run against `src/shared/packages/pyforge-mason/` itself, asserting its three artifacts match `pixi run -e pyforge-mason pyforge-mason-build`'s own output (FR-24's build half).

**Acceptance Criteria:**
- Given both engines on `PATH`, when `mason package build <path>` runs, then `EXIT_OK` and the JSON `data` carries non-null `wheel_path`/`sdist_path`/`conda_path`.
- Given no CFE anywhere on the filesystem, when `mason package build` runs, then it still succeeds -- proving zero `cfe` reference in the code path.
- Given `mason package build` run against `src/shared/packages/pyforge-mason/` itself, when compared to the existing hand-run `pyforge-mason-build` task's output, then the artifacts are equivalent (same versions, same `dist/`/`dist-conda/` directories).
- Given `--format json`, when `mason package build` runs, then stdout carries exactly one JSON document and all engine build output appears only on stderr.

## Design Notes

STREAM mode without porting `cfe.run_streamed`: since only one pipe (`stdout`) is captured and
`stderr` is inherited (not a pipe Mason reads at all), there is no two-pipe deadlock risk, so a
plain `subprocess.run(argv, cwd=project_path, stdout=subprocess.PIPE, stderr=None, timeout=...,
check=False)` already satisfies AD-25 -- the child's stderr IS the terminal, forwarded with zero
buffering. `subprocess.run`'s own timeout handling kills+reaps the child, mirroring `run_streamed`'s
guarantee, without its threaded-reader machinery.

`.conda` filename version parsing (conda package/version/build-string fields never contain a
literal `-`, so this is safe even though `pyforge-mason` itself has a dash):
```python
stem = conda_path.name.removesuffix(".conda")
name, version, build_string = stem.rsplit("-", 2)
```

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 0, medium 4, low 3)
- defer: 0
- reject: 8
- addressed_findings:
  - `[medium]` `[patch]` The FR-22 mismatch check compared a PEP-440-canonicalized wheel version against a raw, unparsed `.conda` filename version segment via `!=`, violating the architecture's own Consistency Conventions ("Versions are strings, compared via `packaging.version`, never string-compared") -- added `package.py::_versions_disagree()`, comparing via `packaging.version.Version` with a raw-string fallback on `InvalidVersion`.
  - `[medium]` `[patch]` Neither `engines/pep517.py::build()` nor `engines/pixi.py::build()` caught `subprocess.TimeoutExpired`, unlike every other subprocess boundary in this package (`cfe.py`'s adapters) -- a build exceeding the 600s timeout crashed past `main()`'s `except MasonError` handler with a raw traceback. Added `PackageBuildTimeoutError` (`package:build-timeout`) and wired the translation into both adapters.
  - `[medium]` `[patch]` `Path(project_path).resolve()` (in `package.py`) and `subprocess.run(cwd=project_path)` (in both engines) could raise raw `OSError`/`ValueError` for an invalid project path (nonexistent directory, unreadable parent, null byte) -- not the "wrapped tool reports its own failure via returncode" case the spec's Always boundary describes, since the tool never starts. Added `PackageProjectPathError` (`package:project-path-invalid`) and wired the translation into `package.py` and both engines.
  - `[medium]` `[patch]` `Pep517BuildResult`/`PixiBuildResult`/`PackageBuildResult` discarded captured build stdout entirely, unlike the sibling `models.BuildResult`'s established `stdout` field precedent -- a build failure investigated outside a live terminal (CI, a captured run) had zero diagnostic text beyond a bare returncode. Added `stdout`/`pep517_stdout`/`pixi_stdout` fields, populated via `text=True, encoding="utf-8", errors="replace"` on both `subprocess.run` calls.
  - `[low]` `[patch]` `engines/pixi.py`'s `.conda` filename parse accepted an empty version segment (a 3-part split from a malformed filename like `pkg--0_0.conda`) as a valid, non-`None` `conda_version`, which could then trip `PackageVersionMismatchError`'s own empty-string constructor guard, raising a bare `ValueError` instead of the intended `MasonError` -- added a non-empty check, degrading to `None` (unparseable) like every other malformed case in that module.
  - `[low]` `[patch]` `PackageVersionMismatchError` named only the two disagreeing version strings, not where the two already-built, already-on-disk artifacts live -- extended the constructor to also carry `wheel_path`/`conda_path`, included in the message.
  - `[low]` `[patch]` `tests/integration/test_package_build.py`'s docstring claimed the produced argv is "byte-identical" to the hand-run `pyforge-mason-build-conda`/`-dist` pixi tasks; it is not (absolute vs. relative `--outdir`/`--output-dir`, functionally equivalent given matching `cwd`, never actually diffed against the reference task) -- corrected the wording.
  - Rejected (noise or matches deliberate spec/precedent, no action): FR-22 comparing wheel-vs-conda only, never wheel-vs-sdist (FR-22's literal scope); `_newest()`'s mtime tie-break under a same-timestamp collision (low-confidence, requires two artifacts sharing sub-second mtime in a single build invocation); `--target`'s zero degrees of freedom in v1 called "over-engineered" (directly required by FR-21's scaffolding-for-v2 design); an empty-string `project_path` silently resolving to cwd (matches every sibling verb's own zero-path-interpretation precedent, AD-1); a TOCTOU window between `glob()` and the later `.stat()`/parse (unrealistic in this CLI's single-threaded, single-invocation flow); `target` having no defensive validation at the Python-API level beyond `cli.py`'s `choices=` (the field has zero operational effect -- it is only ever echoed into the result -- so defensive validation would add ceremony without preventing any real failure, unlike `build_docker`'s `config`, which IS used to construct an argv element); `--cfe-timeout` being silently accepted but ignored by `package build` (matches the already-established AD-13 precedent that engine timeouts are a non-configurable v1 knob, mirroring `probe_engine`'s own fixed, non-configurable timeout).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Summary:** Story 3.2 (`package.py::build()` plus the `engines/pep517.py`/`engines/pixi.py`
adapters and the `mason package build` CLI verb) was already fully implemented, reviewed (7
patches applied, 8 rejected -- see Review Triage Log above), and committed as `4b0c3014f1` by the
prior session. That commit landed without a matching entry in `spec-pyforge-mason`'s
`.memlog.md`, so bmad-loop's own S-13.7 verify gate (`python scripts/spec_surface_reconcile.py`)
failed on 12 governed files (`cli.py`, `engines/pep517.py`, `engines/pixi.py`, `errors.py`,
`models.py`, `package.py` and their six test files) changing without the Spec's memlog moving --
the exact repair shape every prior mason story (S-1.10 through S-3.1) has hit and fixed the same
way. This resume session repaired it: no code or intent-contract changes, only spec-surface
bookkeeping.

**Files changed (this repair pass):**
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/.memlog.md` --
  new `(change)`/`(event)` entries naming the 12 governed paths S-3.2 touched.
- `scripts/.spec-surface-baseline.json` -- re-stamped via `spec_surface_check.py --write-baseline
  --spec pyforge-mason/spec-pyforge-mason` after the memlog entry landed.
- Committed as `65a59d7260` on top of the story's own `4b0c3014f1`.

**Review findings breakdown:** unchanged from the prior session's pass -- 7 patch (0 high, 4
medium, 3 low), 8 reject, 0 intent_gap, 0 bad_spec, 0 defer. No new review pass was run for this
repair: it touches only spec-governance bookkeeping outside the reviewed code diff.

**Follow-up review recommendation:** `false` -- no functional code changed in this pass.

**Verification performed:**
- `python scripts/spec_surface_reconcile.py` -- was failing (`rc=1`, 12 gating `[drift]`
  findings); now `OK: every tracked file governed or allowlisted; no drift.` (`rc=0`).
- `pixi run -e pyforge-mason pyforge-mason-test` -- 1050 passed, 1 deselected.
- `pixi run -e pyforge-mason pyforge-mason-test-slow` -- 1 passed (the new
  `tests/integration/test_package_build.py` self-hosting test), 1050 deselected.
- `pixi run -e pyforge-mason pyforge-mason-build` -- both the conda artifact and the wheel+sdist
  built successfully.

**Residual risks:** none identified. The repair is governance bookkeeping only; the underlying
implementation and its review were already complete and unchanged.

