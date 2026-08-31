---
title: 'The pypi ship target'
type: 'feature'
created: '2026-08-13'
status: 'done'
baseline_revision: '3d3a378feafa452641bb398920a80326f9841648'
final_revision: '9aedef7da2f86bd85908e68f480d1f98d11e8ceb'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/src/shared/packages/pyforge-mason/src/pyforge/mason/engines/pep517.py'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `package.py` can build a wheel+sdist (Story 3.2) and plan a `pypi` ship as a dry run
(Story 3.3), but nothing actually uploads to PyPI yet -- there is no `twine` engine adapter and no
function that builds, checks credentials, and ships a real release (FR-16, FR-20, AD-9, AD-14).

**Approach:** Add `engines/twine.py` (an `EngineAdapter`-shaped `upload()` wrapping `twine upload`)
and `package.py::ship_pypi()`, which checks PyPI credential presence in the caller's `environ`
*before* calling `build()` (FR-15, reused not duplicated), then uploads the produced wheel+sdist
via the new adapter and returns a `ShipTargetResult`. Two new `MasonError` subclasses:
`ShipCredentialMissingError` (`ship:credential-missing`) and `ShipUploadTimeoutError`
(`ship:upload-timeout`).

## Boundaries & Constraints

**Always:**
- `ship_pypi(project_path, *, environ, target="library")` checks `TWINE_USERNAME` and
  `TWINE_PASSWORD` are both present and non-empty (stripped) in `environ` as its FIRST action,
  before calling `build()` -- architecture AD-14: "Credential presence is validated before any
  artifact is built." Only presence is checked; the values themselves are never read into a
  variable used for anything but the truthiness check, never logged, never stored on a returned
  object (NFR-2).
- On missing credentials, raises `ShipCredentialMissingError` naming which of
  `TWINE_USERNAME`/`TWINE_PASSWORD` are absent -- mirrors `EngineAbsentError`/`CfeUnresolvedError`'s
  precedent (a structural precondition is RAISED, not returned as data), consistent with
  `require_engine`'s identical treatment of "engine absent" one layer down.
- When credentials are present, `ship_pypi` calls `package.py::build(project_path, target=target)`
  unconditionally (FR-15 reused, never duplicated) then, only if BOTH `wheel_path` and `sdist_path`
  are non-`None`, calls `engines.twine.upload((wheel_path, sdist_path))`.
- `engines/twine.py::upload(paths, *, timeout=None)` mirrors `engines/pep517.py`/`engines/pixi.py`'s
  own shape exactly: module-level `name`/`probe()`, `require_engine("twine")` gate before any
  subprocess spawns, list argv, `stdout=subprocess.PIPE`, `stderr=None`, `text=True,
  encoding="utf-8", errors="replace"`, `timeout=`, `check=False` -- no `env=` kwarg at all (the
  child inherits the real process environment automatically; this is how the credential values
  themselves reach `twine`, never touched or copied by Mason -- AD-14, and the ONLY sanctioned
  `env=` override sites are two calls inside `cfe.py`, per `tests/meta/test_credential_isolation.py`
  Guard 3a). Argv is `["twine", "upload", "--non-interactive", "--disable-progress-bar", *paths]`
  -- `--non-interactive` is defense-in-depth so a spawned child can never block on a stdin prompt
  (every subprocess call in this codebase carries a `timeout=`); `--disable-progress-bar` keeps
  captured stdout deterministic (twine's `rich` console force-enables ANSI/live-rendering even when
  not a TTY -- verified live against the installed `twine 7.0.0` binary).
- `upload()`'s captured stdout has ANSI escape sequences (`\x1b\[[0-9;]*m`) stripped before being
  stored on `TwineUploadResult.stdout` or scanned for a URL -- verified live: a failed `twine
  upload` of a nonexistent file writes `\x1b[31mERROR   \x1b[0m ...` to stdout (twine `rich.
  reconfigure(force_terminal=True)`), never to stderr.
- On a zero returncode, `upload()` extracts the release URL from the ANSI-stripped stdout by
  matching twine's own `"View at:\n<url>"` block (`twine.commands.upload.upload`'s literal
  `print("\n[green]View at:")` followed by one `print(url)` per release URL -- confirmed by reading
  the installed twine source at `commands/upload.py`/`repository.py::release_urls`; a single `twine
  upload wheel sdist` call for the same package+version yields exactly one URL, since
  `release_urls` is a `Set[str]` keyed by name+version). `TwineUploadResult.url` is `None` when no
  match is found -- a genuine zero-returncode success (state is driven by `returncode`, never
  gated on whether the URL happened to parse).
- `ship_pypi` returns `ShipTargetResult(target="pypi", state=ShipState.TERMINAL,
  reference=upload_result.url, message=upload_result.stdout)` on a zero `upload()` returncode, or
  `state=ShipState.FAILED, reference=None, message=<the wrapped tool's own stdout, verbatim>` when
  either the build produced no wheel/sdist (nonzero `pep517_returncode` or nothing discoverable) or
  `upload()`'s returncode is nonzero -- AD-4: a tool that RAN but failed is data, never raised (this
  mirrors `recipe.py::submit()`'s own data-vs-raise split, and `ShipTargetResult.message`'s own
  "wrapped tool's own field, verbatim, no Mason re-authoring" docstring contract).
- `EngineAbsentError` (twine not on `PATH`), `ShipUploadTimeoutError` (upload exceeds timeout), and
  anything `build()` itself already raises (`PackageVersionMismatchError`, `PackageProjectPathError`,
  `EngineAbsentError` from either build engine) propagate un-caught out of `ship_pypi` -- these are
  structural preconditions, not this call's own execution outcome (same split `build()` already
  established for its own two engines).
- Zero `cfe` reference anywhere touched by this story (AD-6, `tests/meta/test_capability_tiers.py`
  already guards `package.py`); `ship_pypi` works with no CFE installation anywhere (AC4).

**Block If:** a live grep of `package.py`/`errors.py`/`engines/` at execution time shows
`ship_pypi`, `ShipCredentialMissingError`, `ShipUploadTimeoutError`, or `engines/twine.py` already
defined (a concurrent story landed first) -- reconcile with an operator rather than overwriting.

**Never:**
- No CLI flag, verb, or `main()` dispatch wiring -- `cli.py` is untouched (Story 3.9's scope, per
  epic-3-context Cross-Story Dependencies).
- No `pypi-test`/repository-selection parameter anywhere in this story's own surface, and no
  TestPyPI vocabulary (Story 3.9/FR-50's scope) -- `engines/twine.py::upload` takes no
  `repository_url`/`repository` argument; AD-26's "identical code path, differing only in
  repository configuration" is Story 3.9's own knob to add to this adapter when it lands.
- No `ShipReceipt` aggregate, no multi-target orchestration, no idempotence/"already shipped?"
  interrogation (FR-18/AD-10, Story 3.7's scope) -- `ship_pypi` always uploads when called; whether
  it is safe to call again is a later story's concern.
- No replication of twine's full credential-resolution chain (`.pypirc`, keyring) -- the precondition
  check is exactly `TWINE_USERNAME`+`TWINE_PASSWORD` presence (FR-20: "the standard environment
  variables the chosen uploader honours"), not a general "would twine succeed?" oracle.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Missing both credentials | `environ` has neither `TWINE_USERNAME` nor `TWINE_PASSWORD` | `build()` and `engines.twine.upload()` are never called | `ShipCredentialMissingError` naming both |
| One credential missing | `TWINE_USERNAME` set, `TWINE_PASSWORD` absent/empty | `build()` never called | `ShipCredentialMissingError` naming `TWINE_PASSWORD` |
| Happy path | Both creds present; `build()`/`upload()` mocked to succeed | `ShipTargetResult(target="pypi", state=TERMINAL, reference=<url>, message=<stdout>)` | No error expected |
| Build produces no wheel/sdist | Both creds present; mocked `build()` returns `wheel_path=None` | `engines.twine.upload` is never called | `ShipTargetResult(state=FAILED, reference=None, message=...)` |
| Upload fails (nonzero returncode) | Both creds present; build succeeds; mocked `upload()` returns `returncode=1` | No exception | `ShipTargetResult(state=FAILED, reference=None, message=<stdout>)` |
| Upload times out | `subprocess.run` raises `TimeoutExpired` | Propagates | `ShipUploadTimeoutError` |
| twine absent from `PATH` | `require_engine("twine")` raises | Propagates before any subprocess spawns | `EngineAbsentError` |
| ANSI-coded stdout | Canned stdout containing `\x1b[31m`/`\x1b[0m` around a `View at:` block | Stripped before storage and URL match | No error expected |

</intent-contract>

## Code Map

- `src/pyforge/mason/engines/twine.py` (NEW) -- `name`, `probe()`, `TwineUploadResult` (frozen
  dataclass: `returncode`, `url`, `stdout`), `upload()`.
- `src/pyforge/mason/errors.py` -- add `ShipCredentialMissingError(missing: Sequence[str])` and
  `ShipUploadTimeoutError(timeout: float)`.
- `src/pyforge/mason/package.py` -- add `ship_pypi(project_path, *, environ, target="library")`.
- `tests/unit/test_engines_twine.py` (NEW) -- mirrors `test_engines_pep517.py`'s structure.
- `tests/unit/test_errors.py` -- extend with both new error classes.
- `tests/unit/test_package.py` -- extend with `ship_pypi` coverage.

## Tasks & Acceptance

**Execution:**
- [x] `errors.py` -- add `ShipCredentialMissingError(missing: Sequence[str])`: identifier
  `ship:credential-missing`, message names every entry in `missing` (e.g. `"TWINE_USERNAME,
  TWINE_PASSWORD"`), raises `ValueError` on an empty `missing` (mirrors `CfeImportFloorError`'s
  validation rigor), stores `missing` as a `tuple`, `__reduce__` returning
  `(self.__class__, (self.missing,))`.
- [x] `errors.py` -- add `ShipUploadTimeoutError(timeout: float)`: identifier `ship:upload-timeout`,
  message names `timeout` and states no per-upload timeout override exists in v1 (mirrors
  `PackageBuildTimeoutError`'s exact shape), `__reduce__` returning `(self.__class__,
  (self.timeout,))`.
- [x] `engines/twine.py` -- `name = "twine"`; `probe()` delegates to `probe_engine("twine",
  "twine")`; `TwineUploadResult` frozen dataclass; `upload(paths: Sequence[str], *, timeout:
  float | None = None) -> TwineUploadResult` -- `require_engine("twine")` first, then
  `subprocess.run(["twine", "upload", "--non-interactive", "--disable-progress-bar", *paths],
  stdout=subprocess.PIPE, stderr=None, text=True, encoding="utf-8", errors="replace",
  timeout=resolved_timeout, check=False)`; translate `subprocess.TimeoutExpired` to
  `ShipUploadTimeoutError(timeout=resolved_timeout)`; strip ANSI escapes from stdout; on
  `returncode == 0`, extract the URL following a `"View at:"` line (`None` if no match); return
  `TwineUploadResult(returncode, url, stripped_stdout)`.
- [x] `package.py` -- add `ship_pypi(project_path: str, *, environ: Mapping[str, str], target: str
  = "library") -> ShipTargetResult`: check `TWINE_USERNAME`/`TWINE_PASSWORD` presence in `environ`
  first, raising `ShipCredentialMissingError` naming whichever are absent/empty; else call
  `build(project_path, target=target)`; if `wheel_path`/`sdist_path` are both non-`None`, call
  `twine.upload((wheel_path, sdist_path))` and map its `returncode` to `TERMINAL`/`FAILED` per the
  I/O matrix; else return a `FAILED` result directly without calling `twine.upload`.
- [x] `tests/unit/test_engines_twine.py` -- `probe()` delegation; engine-absence gate (no
  subprocess spawned); invocation shape (argv, `stdout=PIPE`, `stderr=None`, no `env=` kwarg,
  `timeout` default/override); `TimeoutExpired` -> `ShipUploadTimeoutError`; ANSI-stripped
  `"View at:"` URL extraction on success; `url=None` on a zero-returncode stdout with no `"View
  at:"` block; failure (nonzero returncode) leaves `url=None` and preserves stdout.
- [x] `tests/unit/test_errors.py` -- both new classes: identifier, message content, `__reduce__`
  round-trip (deepcopy/pickle), empty-`missing`/non-str-`missing`-item rejection for
  `ShipCredentialMissingError`.
- [x] `tests/unit/test_package.py` -- `ship_pypi`: missing-credential cases raise before `build`/
  `twine.upload` are called (mock both, assert `not called`); happy path (mocked `build`/`upload`,
  correct `ShipTargetResult`); build-produced-nothing path (`twine.upload` not called, `FAILED`
  result); upload-failure path (`FAILED`, `reference=None`); `EngineAbsentError`/
  `PackageVersionMismatchError` from `build()` propagate un-caught.

**Acceptance Criteria:**
- Given the `pypi` target with valid credentials and artifacts, when `ship_pypi` executes, then the
  wheel and sdist are uploaded via `engines.twine.upload` and the result is a `ShipTargetResult`
  with `state=TERMINAL` and a URL `reference`.
- Given missing `TWINE_USERNAME`/`TWINE_PASSWORD`, when `ship_pypi` is called, then
  `ShipCredentialMissingError` is raised before `build()` or `twine.upload()` are ever called.
- Given credentials present, when `ship_pypi` runs, then no credential value is read into any
  variable beyond the presence check, stored on a returned object, or passed as an explicit `env=`
  override -- the subprocess inherits them via the normal, un-mutated process environment.
- Given no CFE installation anywhere, when `ship_pypi` runs (with `twine`/`build`/`pixi` present),
  then it succeeds -- `package.py` carries no `cfe` reference of any kind.

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 0, low 1)
- defer: 1: (high 0, medium 1, low 0)
- reject: 14: (high 0, medium 0, low 14)
- addressed_findings:
  - `[low]` `[patch]` `test_ship_pypi_forwards_an_explicit_target` passed `target="library"` -- identical
    to the default -- proving nothing about forwarding; changed to a distinct value
    (`"not-the-default"`) and asserted `build()` was called with that exact value.
  - Deferred as `DW-3-4-1`: `ship_pypi` unconditionally calls `build()`, which (Story 3.2's own
    pre-existing, unchanged design) always runs the pixi `.conda` engine too, so an `EngineAbsentError`
    from `pixi` specifically -- not just a genuine wheel/conda version mismatch -- can block an
    otherwise-ready PyPI-only ship. Root cause lives in Story 3.2's `build()`, reused here per FR-16's
    own "reuse FR-15, don't duplicate" mandate; not this story's to fix.
  - Rejected (noise, or matches deliberate spec/architecture/precedent, no action): credential-check
    `environ` param vs. the subprocess's inherited real `os.environ` being formally decoupled (by
    design -- AD-14 + `test_credential_isolation.py` Guard 3a permit exactly two `env=` override
    sites, both in `cfe.py`; adding a third here to thread `environ` explicitly would violate that
    guard); `target` param name colliding with `ShipTargetResult.target`'s different meaning (mirrors
    `build()`'s own pre-existing, already-shipped parameter name -- renaming here would be the
    inconsistent choice); a claimed "stale `dist/` artifact from a prior successful build could be
    uploaded when the current build fails" -- factually false, verified by reading `pep517.py`:
    `wheel_path`/`sdist_path` are forced to `None` unconditionally on any nonzero `pep517_returncode`,
    never attempting discovery; no `--skip-existing`/idempotent-retry handling (explicit spec Never
    boundary -- FR-18/AD-10 idempotence is Story 3.7's scope); `ShipUploadTimeoutError`'s `timeout`
    parameter carrying no bounds validation (matches `engines.pep517.build`/`engines.pixi.build`'s own
    unvalidated `timeout` parameter -- no such validation exists anywhere in this codebase's engine
    adapters); a claim that `twine`'s `_KNOWN_ENGINES`/`_ENGINE_CONDA_PACKAGES` registration was
    unverified -- independently confirmed already present (Story 3.1) by reading `engines/__init__.py`
    directly, and by the green `require_engine("twine")` test coverage; real process stderr not
    captured from the `twine` subprocess -- matches `engines.pep517`/`engines.pixi`'s identical
    `stderr=None` shape and AD-25's own architecture text ("streamed child output always targets
    stderr... so stdout's single-JSON-document guarantee holds"), and live-verified: the real installed
    `twine 7.0.0` writes 100% of its own diagnostics (including its `ERROR` path) to stdout, never
    stderr; no `.pypirc`/keyring credential-resolution support (explicit spec Never boundary: "the
    precondition check is exactly `TWINE_USERNAME`+`TWINE_PASSWORD` presence... not a general 'would
    twine succeed?' oracle"); `_VIEW_AT_URL_PATTERN` only capturing the first "View at:" URL -- provably
    unreachable via `ship_pypi`'s own single call site (`twine.upload((wheel_path, sdist_path))`,
    always the same package name+version, and `release_urls` is a `Set[str]` keyed by name+version, so
    exactly one URL is ever produced for that call shape) -- matches Story 3.3's own precedent for
    "no current caller passes anything but X" findings; FR/AD/NFR citations in the new docstrings
    being "unverified" -- each was independently confirmed against `ARCHITECTURE-SPINE.md`/`prd.md`
    during spec authoring; `environ[name] = None` (explicit, not absent) causing `AttributeError` from
    `.strip()` instead of a typed error, and `missing`/`paths` accepting a bare `str` (itself a
    `Sequence[str]`) and silently iterating its characters -- both match Story 3.3's own explicitly
    logged precedent (`parse_ship_targets(None)` raising `AttributeError`, accepted as "no current
    caller passes anything but a `str`... this story adds no CLI wiring at all") and, for `missing`,
    mirror the identical pre-existing gap already present in `CfeImportFloorError` (Story 1.x,
    unchanged); incomplete ANSI stripping (only SGR codes, not cursor-visibility/erase-line/OSC-8
    hyperlink sequences) -- verified moot: `--disable-progress-bar` already suppresses Rich's Live
    rendering (the source of cursor/erase-line codes) and twine's own `cli.py::configure_output()`
    already sets `highlight=False` (foreclosing auto-hyperlink wrapping around a printed URL), and the
    live-captured real `twine` failure output examined during spec authoring showed only plain SGR
    codes, consistent with both.

## Design Notes

`ship_pypi` does its OWN `build()` call rather than accepting an already-built `PackageBuildResult`
(unlike `plan_ship`): AC2 requires the credential check to run before ANY artifact is built, which
is only satisfiable if this function owns the "check, then build, then upload" sequence itself for
a standalone invocation. Story 3.9's multi-target orchestrator may later call `ship_pypi` once per
`--to pypi` (accepting the minor redundancy of `build()` re-running per target if the user also
requested `channel:<name>`/`conda-forge` in the same invocation) or refactor to share one
`PackageBuildResult` -- that composition choice belongs to 3.9, not this story (mirrors how Story
3.3's `plan_ship` was written for reuse without knowing exactly how 3.9 would call it).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

**Summary:** Implemented and reviewed in the prior session (commit `bd75129eca`): the `engines/twine.py`
upload adapter and `package.py::ship_pypi()`, plus `ShipCredentialMissingError`/`ShipUploadTimeoutError`.
That session's own bmad-loop landing gate (`scripts/spec_surface_reconcile.py`, the S-13.7 spec-surface
drift check) then failed deterministic verification because the story commit landed with no matching
entry in the owning Spec's `.memlog.md` (`_bmad-output/projects/pyforge-mason/planning-artifacts/
specs/spec-pyforge-mason/.memlog.md`) -- a recurring, previously-documented pattern for this Spec (see
that memlog's S-3.1/S-3.2/S-3.3 entries), not a defect in the story's code or intent contract. This
resume repaired it by reconciling: named the six changed paths in `.memlog.md` and re-stamped the
drift baseline (`python scripts/spec_surface_check.py --write-baseline --spec
pyforge-mason/spec-pyforge-mason`), matching the exact procedure every prior mason story in this Spec
used. No production or test code changed in this pass.

**Files changed (this repair pass only):**
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/.memlog.md` -- new
  `(change)`/`(event)` entries naming Story 3.4's six governed paths.
- `scripts/.spec-surface-baseline.json` -- re-stamped for `pyforge-mason/spec-pyforge-mason` only
  (scoped `--spec`, no other Spec's pending drift accepted).

**Review findings (from the prior session's pass, unchanged by this repair):** 1 patch (low, fixed),
1 deferred (`DW-3-4-1`, low, not this story's root cause), 14 rejected. See `## Review Triage Log`.

**Verification performed:**
- `python scripts/spec_surface_reconcile.py` -- now exits 0 (`OK: every tracked file governed or
  allowlisted; no drift`); previously failed with 6 gating `[drift]` findings against this Spec.
- `pixi run -e pyforge-mason pyforge-mason-test` -- 1126 passed, 1 deselected. No regression.
- Reconciliation commit `9aedef7da2` on top of the story commit `bd75129eca`, both on
  `bmad-loop/20260813-145934-3eb0/3-4-the-pypi-ship-target`. Not pushed.

**Residual risks:** None new. `DW-3-4-1` (ship_pypi's build() reuse also runs the pixi `.conda` engine,
so a pixi-only `EngineAbsentError` can block an otherwise-ready PyPI-only ship) remains open on the
deferred-work ledger, root-caused in Story 3.2, out of this story's scope.

