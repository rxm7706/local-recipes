---
title: 'Engine protocol and provisioning'
type: 'feature'
created: '2026-08-13'
status: 'done'
baseline_revision: '257094dcc2cf99a95c8553b6c05ae3cc09fe876f'
final_revision: 'b22f1d4571'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** Every future ship/build/lock engine (`pixi`, `twine`, `conda-lock`, `build`) needs
identical PATH-discovery, absence-handling, and version-provisioning treatment, but
`engines/__init__.py` today is only Story 1.8's read-only, never-raising probe seed — there is no
adapter protocol, no typed absence error, and no version-range provisioning tying `pixi.toml` to
in-code constants.

**Approach:** Extend `engines/__init__.py` with a minimal `name`+`probe()` adapter protocol and a
new raising entry point that turns an absent engine into a typed `EngineAbsentError`; declare each
of the four known engines as a conda run-dependency with an evidence-backed version range in the
member `pixi.toml`, mirrored by in-code `SpecifierSet` constants and kept in sync by a meta-test
ported from `pyforge-warden`.

## Boundaries & Constraints

**Always:**
- Engine discovery stays PATH-only (`shutil.which`); nothing is downloaded, installed, or fetched
  at runtime (NFR-7).
- `EngineStatus`, `_KNOWN_ENGINES`, `probe_engine`, and `probe_known_engines` keep their exact
  existing signatures and never-raising behavior — `doctor.py`'s composition (`build_report` calling
  `probe_known_engines()`) is untouched by this story.
- The new absence error is a `MasonError` subclass in `errors.py` using the identifier
  `engine:absent` (already reserved in `errors.py`'s docstring and covered by
  `test_errors.py::test_valid_identifiers_from_the_architecture_spine`), following the same
  per-call-data constructor shape as `CfeImportFloorError` (validated, non-empty fields; message
  states what's missing and how to fix it, per NFR-14).
- Every engine version range added to `pixi.toml`'s `[package.run-dependencies]` has a
  `packaging.specifiers.SpecifierSet` mirror in `engines/__init__.py`, verified by a new
  `tests/meta/test_engine_version_range_sync.py` ported from
  `src/shared/packages/pyforge-warden/tests/meta/test_engine_version_range_sync.py` — both sides
  normalized through `SpecifierSet` before `str()` comparison (never a raw-string comparison, which
  would false-fail on the repo's own conventional specifier reordering).
- Version ranges are evidence-backed, one tested minor wide (`>=X.Y.Z,<X.(Y+1)`, the repo-wide
  convention), not widened "to be safe": live-verified in this environment — `pixi` 0.76.2, `twine`
  7.0.0, `conda-lock` 4.0.2, `build` (`pyproject-build` binary, conda package `python-build`) 1.5.0.

**Block If:** the member `pixi.toml`'s dependency solve fails after adding the four engines as
run-dependencies (a genuine conflict with an existing workspace pin) — do not loosen, remove, or
work around a conflicting engine pin without operator input.

**Never:**
- No adapter modules for the operations themselves — `engines/pep517.py`, `engines/twine.py`,
  `engines/pixi.py` (Stories 3.2/3.4/3.5), and `engines/condalock.py` (Story 4.1) are out of scope.
- No change to `doctor.py`'s composition logic or `DoctorReport.engines`'s field shape.
- No `packaging`-based version validation inside `probe_engine`/`probe_known_engines` — that
  read-only path stays "report verbatim, never parsed" per its own docstring; range-checking lives
  only in the new raising entry point.
- No reuse of `cfe.py`'s CFE-specific machinery (`_CFE_SCRIPTS`, CFE-root resolution) — engines are
  a sibling seam, never dependent on the CFE port.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Engine present, version parses | `require_engine("twine")`, `twine` on PATH, `--version` succeeds | Returns the version string | No error expected |
| Engine present, version unreadable | `require_engine("pixi")`, on PATH but `--version` times out/errors/empty output | Returns `None` (presence, not parseability, is what's required) | No error expected |
| Engine absent | `require_engine("conda-lock")`, not on PATH | Raises `EngineAbsentError` naming the engine and how to provision it | `engine:absent`, message names engine + provisioning hint |
| `pixi.toml` range drifts from the in-code constant | A range is edited in one place only | `test_engine_version_range_sync.py` fails | Meta-test failure names both sides |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-mason/src/pyforge/mason/engines/__init__.py` -- extend with an
  adapter protocol (`name`, `probe() -> str | None`), the four version-range constants, and the
  raising engine-required entry point; keep the existing probe-only seed unchanged.
- `src/shared/packages/pyforge-mason/src/pyforge/mason/errors.py` -- add `EngineAbsentError`.
- `src/shared/packages/pyforge-mason/pixi.toml` -- add `pixi`, `twine`, `conda-lock`, `python-build`
  to `[package.run-dependencies]` as version ranges.
- `src/shared/packages/pyforge-mason/tests/meta/test_engine_version_range_sync.py` -- new; port of
  `src/shared/packages/pyforge-warden/tests/meta/test_engine_version_range_sync.py`.
- `src/shared/packages/pyforge-mason/tests/unit/test_engines.py` -- extend with the new
  protocol/entry-point/error coverage.
- `src/shared/packages/pyforge-mason/tests/unit/test_errors.py` -- extend with `EngineAbsentError`
  coverage (identifier, message contents, `MasonError` subclass).
- `src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py` -- read-only reference for the
  `DEPTRY_VERSION_RANGE`-style constant pattern; not imported or edited.

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-mason/src/pyforge/mason/errors.py` -- add `EngineAbsentError(MasonError)` taking the engine's display name and a provisioning hint (e.g. the conda package name), identifier `engine:absent`, message naming both -- new engine-adapter operations (future stories) raise this instead of a raw `FileNotFoundError`.
- [x] `src/shared/packages/pyforge-mason/src/pyforge/mason/engines/__init__.py` -- add a `Protocol` (`name: str`, `def probe(self) -> str | None`) documenting the shared adapter shape every future `engines/*.py` module implements alongside its own operation method(s); add `PIXI_VERSION_RANGE`/`TWINE_VERSION_RANGE`/`CONDA_LOCK_VERSION_RANGE`/`PYTHON_BUILD_VERSION_RANGE` `SpecifierSet` constants (evidence: 0.76.2/7.0.0/4.0.2/1.5.0); add a `require_engine(name: str) -> str | None` entry point that probes via the existing `probe_engine`/`_KNOWN_ENGINES` machinery and raises `EngineAbsentError` when absent, returning the version (possibly `None`) when present.
- [x] `src/shared/packages/pyforge-mason/pixi.toml` -- add the four engines to `[package.run-dependencies]` with the same ranges as the in-code constants.
- [x] `src/shared/packages/pyforge-mason/tests/meta/test_engine_version_range_sync.py` -- new; port pyforge-warden's pattern: `SpecifierSet`-normalized comparison per engine, a "range not an exact pin" test, an "evidence version is inside range" test, and a "range doesn't silently widen to the next untested minor" test.
- [x] `src/shared/packages/pyforge-mason/tests/unit/test_engines.py` -- cover the I/O matrix above for `require_engine` (present+parses, present+unparseable, absent) using the file's existing `shutil.which`/`subprocess.run` mocking convention.
- [x] `src/shared/packages/pyforge-mason/tests/unit/test_errors.py` -- cover `EngineAbsentError`'s identifier, stored attributes, message content, and `MasonError` subclass-ness, matching `CfeImportFloorError`'s existing test shape.

**Acceptance Criteria:**
- Given `engines/__init__.py`, when the protocol is defined, then it declares `name` and
  `probe() -> str | None` as the shared adapter contract.
- Given an engine name not on `PATH`, when `require_engine` is called for it, then it raises
  `EngineAbsentError` naming the engine and how to provision it -- never a raw `FileNotFoundError`.
- Given the member `pixi.toml`, when inspected, then `pixi`, `twine`, `conda-lock`, and
  `python-build` are each a conda run-dependency with a version range, not an exact pin.
- Given `pixi.toml`'s engine ranges and `engines/__init__.py`'s `SpecifierSet` constants, when
  `test_engine_version_range_sync.py` runs, then it fails if the two diverge.
- Given `doctor.py`, when this story lands, then `build_report`'s call to `probe_known_engines()`
  and `DoctorReport.engines`'s shape are unchanged.

## Design Notes

`require_engine` is deliberately the ONLY raising surface this story adds — `probe_engine`/
`probe_known_engines` stay non-raising for `doctor.py`'s read-only diagnostic use. Future stories
(3.2 build engines, 3.4/3.5 upload engines, 4.1 lock engine) call `require_engine` at the top of
their operation methods rather than re-implementing absence handling.

Example shape (illustrative, not prescriptive):
```python
def require_engine(name: str) -> str | None:
    status = probe_engine(name, _KNOWN_ENGINES[name])
    if not status.available:
        raise EngineAbsentError(name, _ENGINE_CONDA_PACKAGES[name])
    return status.version
```

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 2, low 3)
- defer: 1: (high 0, medium 0, low 1)
- reject: 5: (high 0, medium 0, low 5)
- addressed_findings:
  - `[medium]` `[patch]` `EngineAbsentError` had no `__reduce__` override, so `deepcopy`/`pickle` corrupted its `.args`/`repr()` on round-trip (message/identifier/name survived via `__dict__` restore, verified live) -- added the override mirroring `CfeTimeoutError`'s, plus deepcopy/pickle round-trip tests in `test_errors.py`.
  - `[medium]` `[patch]` `require_engine`'s `_ENGINE_CONDA_PACKAGES[name]` lookup was unguarded against future drift from `_KNOWN_ENGINES` (a raw `KeyError` would leak for a legitimately-known, legitimately-absent future engine if one dict were updated without the other) -- added `test_known_engines_and_conda_packages_share_the_same_key_set` in `test_engines.py`.
  - `[low]` `[patch]` `EngineAdapter` lacked `@runtime_checkable`, unlike every structural `Protocol` in `pyforge-warden` (6/6) -- added the decorator plus an `isinstance()` coverage test.
  - `[low]` `[patch]` The module and `EngineAdapter` docstrings misattributed Story 3.5's channel-publish target to `twine.py` (twine has no `.conda`/channel concept) -- corrected the story-to-file mapping in both docstrings to name `pixi.py`.
  - `[low]` `[patch]` `test_require_engine_never_leaks_a_raw_file_not_found_error` was functionally identical to `test_require_engine_raises_engine_absent_error_when_not_on_path` and its docstring overclaimed TOCTOU coverage that `probe_engine`'s existing fold-into-`available=True` absorbs before reaching `require_engine`'s raising branch -- removed the redundant/misleading test.
  - Rejected (noise, no action): a diff-construction artifact flagging `pixi.lock` as "omitted" (it was excluded from the review diff as generated noise, not from the actual change -- confirmed already regenerated and staged in the working tree); a suggestion to consolidate three remaining `require_engine`-absence tests (each asserts a materially different attribute, not pure duplication); an odd-phrasing nit citing Story 3.2 twice; a suggestion that `_minor_range`'s AD-1 guard workaround should have used a deny-list allowlist entry instead (independently verified as a legitimate, precedented technique -- the guard's own docstring documents this exact category of fix for an f-string-split value, and the produced `SpecifierSet` is byte-identical to the literal form); `EngineAbsentError` not stripping validated-but-unstripped `name`/`conda_package` before storing (matches `MasonError.message`'s own established validate-via-`.strip()`-but-store-raw convention, not a new inconsistency).
  - `[low]` `[defer]` `CfeImportFloorError` (Story 1.6, pre-existing) has the identical missing-`__reduce__` gap as the medium finding above, surfaced incidentally while fixing `EngineAbsentError`'s copy -- logged as `DW-3-1-1` in the deferred-work ledger; not this story's code.

## Verification

**Commands:**
- `pixi run -e pyforge-mason pyforge-mason-test` -- expected: all unit + meta tests pass, including
  the new `test_engine_version_range_sync.py` and the extended `test_engines.py`/`test_errors.py`.
- `pixi run -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/unit/test_doctor.py -q`
  -- expected: unchanged, confirms `doctor.py`'s composition is untouched.

## Auto Run Result

Status: done

**Summary:** Story 3.1 (engine protocol and provisioning) landed via commit `005845c1de` --
implementation and the same-session review pass (5 patches applied, 1 deferred as `DW-3-1-1`, 5
rejected; see Review Triage Log above) were already complete and committed. This bmad-dev-auto
resume repaired a deterministic-verification failure that surfaced *after* that commit: the
repo-wide S-13.7 verify gate (`python scripts/spec_surface_reconcile.py`) failed with 8 `[drift]`
findings because the governing `spec-pyforge-mason` Spec's `.memlog.md` had not been updated to
name the files this story changed -- a reconciliation step distinct from, and outside, this
story's own `<intent-contract>`.

**Files changed by this repair pass** (no production or test code touched):
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/.memlog.md` --
  appended a `(change)` entry naming all 8 paths Story 3.1 touched, plus an `(event)` entry
  recording the baseline re-stamp.
- `scripts/.spec-surface-baseline.json` -- re-stamped for `pyforge-mason/spec-pyforge-mason` only
  (`python scripts/spec_surface_check.py --write-baseline --spec pyforge-mason/spec-pyforge-mason`),
  via commit `b22f1d4571`.

**Review findings breakdown:** unchanged from the prior session's pass -- see Review Triage Log
above (patch 5, defer 1, reject 5, intent_gap 0, bad_spec 0). This repair pass introduced no new
code, so no new review pass was run against it.

**Verification performed:**
- `python scripts/spec_surface_reconcile.py` -- FAIL (8 `[drift]` findings) before the memlog fix;
  `OK: every tracked file governed or allowlisted; no drift.` (exit 0) after.
- `pixi run -e pyforge-mason pyforge-mason-test` -- 970 passed, both before and after the repair
  (confirms the repair touched no test-affecting code).
- `pixi run -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/unit/test_doctor.py -q`
  -- 22 passed, unchanged, confirming `doctor.py`'s composition is untouched.

**Residual risks:** None identified. The `<intent-contract>` was not modified. `DW-3-1-1`
(`CfeImportFloorError`'s pre-existing missing `__reduce__`, Story 1.6) remains open on the
deferred-work ledger as recorded in the Review Triage Log; it is out of scope for this story.

