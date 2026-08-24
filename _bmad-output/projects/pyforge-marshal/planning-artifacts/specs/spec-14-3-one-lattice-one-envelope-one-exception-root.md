---
title: 'Story 14.3: One lattice, one envelope, one exception root'
type: 'feature'
created: '2026-08-13'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/planning-artifacts/specs/spec-pyforge-core/SPEC.md']
warnings: ['oversized']
baseline_revision: '7712f80083329577ef6df81749c25b2333e05358'
final_revision: '4c0f893964aed97db09fc37f0ec527458785f322'
---

<intent-contract>

## Intent

**Problem:** Three primitives are redeclared per station with no shared home: a verdict/exit-code
lattice (warden, doctor, marshal each hand-roll rank+exit-domain bookkeeping; herald hand-rolls an
isinstance exit dispatch; doctor's "subset of warden" claim lives only in a docstring), a report
envelope (warden 22 KB / doctor 4.5 KB / marshal `envelope.v1.json` 4.3 KB — no field, type, or
`additionalProperties` policy is shared across all three), and an exception root (herald's and
mason's own roots, plus 44 scattered `*Error` classes — the Dream's "12-13" census figure is stale;
this session recounted directly) sharing no common ancestor anywhere in warden/marshal/atlas.

**Approach:** Add three leaf-respecting primitives to `pyforge-core` (`verdict.Lattice` + a generic
exception-dispatch helper; `report.BASE_ENVELOPE_SCHEMA` + a pure dict-`compose` helper — no
`jsonschema` import in `pyforge-core`, which would violate CAP-1's stdlib-only leaf constraint;
`errors.PyforgeError`, a bare marker base). Each station's own domain data (its enum members, its
own schema file, its own exception subclasses and their custom constructors) stays exactly where it
is — only the shared BOOKKEEPING/MACHINERY collapses. Doctor's narrowing becomes a real, tested
computation instead of a docstring claim. `pyforge-core` becomes a run-dependency of doctor and
mason for the first time (both were untouched by Story 14.2).

## Boundaries & Constraints

**Always:**
- **`pyforge-core` stays a leaf (CAP-1) — this is the design constraint that shapes everything
  below.** `tests/meta/test_leaf_constraint.py` forbids any import in `src/pyforge/core` that is
  neither stdlib nor `pyforge.core` itself. `jsonschema` is third-party, so `pyforge.core.report`
  may ship schema DATA and pure dict-composition helpers but must never call `jsonschema.validate`
  itself — that call stays in each station's own code, which already depends on `jsonschema`
  (warden, doctor; marshal only in tests today, see CAP-4 below).
- **CAP-3 — `pyforge.core.verdict.Lattice(order: tuple, exit_by_member: Mapping)`**, generic over
  any hashable member type (no `enum` import needed — works against any station's `StrEnum`
  without pyforge-core naming it). Provides `.rank(member) -> int` (replaces every station's own
  `{m: i for i, m in enumerate(order)}` dict-comprehension), `.exit_codes -> frozenset[int]`
  (`frozenset(exit_by_member.values())`, replacing every station's own hand-typed/computed domain
  literal), and `.narrows(other: Lattice) -> bool` (`self.exit_codes <= other.exit_codes`) — the
  concrete mechanism that turns doctor's docstring claim into a computed fact.
  - `warden/verdict.py`: build `_LATTICE = Lattice(order=_RUNG_ORDER, exit_by_member=_EXIT_BY_STATUS)`;
    every internal use of `_RANK[...]` becomes `_LATTICE.rank(...)`; `models.py`'s hand-typed
    `_VALID_EXIT_CODES = frozenset({0, 1, 2, 130})` becomes `_LATTICE.exit_codes | {EXIT_SIGINT}`
    (same numbers, now derived not duplicated). Public names (`EXIT_SIGINT`, `exit_code_for`,
    every `Status` member) are UNCHANGED — this is a private-implementation swap only.
  - `marshal/core/verdict.py`: identical pattern — `LATTICE_ORDER`/`_RANK`/`GUARDED_EXIT_CODES`'s
    hand computation (`frozenset(_EXIT_BY_VERDICT.values()) | {EXIT_OK, EXIT_USAGE, EXIT_SIGINT}`)
    delegates to a `Lattice` built from `LATTICE_ORDER`/`_EXIT_BY_VERDICT`. `_RELAY_PASSTHROUGH` is
    NOT touched (out of scope — see Never).
  - `doctor/verdict.py`: build a `Lattice` from an explicit rank order (`FAIL, WARN, OK` — doctor's
    own `exit_code_for` stays its existing any-fail predicate, UNCHANGED; it does not need to
    consult `.rank()`, only `.exit_codes` and the new narrows test need the instance) with
    `exit_by_member={FAIL: 2, WARN: 0, OK: 0}`. **The narrows check CANNOT live in doctor's
    production code**: `tests/meta/test_no_warden_import.py` (AD-3) forbids any doctor module
    except `sources/warden.py` from importing `pyforge.warden`, and `sources/warden.py`'s own
    guard (`test_sources_warden_no_subprocess.py`) restricts even THAT file to
    `pyforge.warden.engines` only — never `pyforge.warden.verdict`. So the narrows proof is a NEW
    TEST FILE (`tests/meta/test_verdict_narrows_warden.py`, not scanned by the AD-3 guard, which
    only scans the installed `pyforge.doctor` package) importing both `pyforge.doctor.verdict` and
    `pyforge.warden.verdict` directly — this is safe because the root `pixi.toml`'s
    `[feature.pyforge-doctor.dependencies]` already resolves `pyforge-warden` in-repo at feature
    level (AD-1, the existing `gate` extra wiring) for exactly this kind of test use, without doctor
    ever declaring warden as a `pyproject.toml` run-dependency.
  - `herald/errors.py`: `exit_code_for`'s hand-rolled most-specific-first isinstance loop over
    `_EXIT_BY_ERROR` delegates to a new `pyforge.core.verdict.dispatch_exit_code(exc, table,
    default)` generic helper (same isinstance-ordered-tuple algorithm, extracted once); the
    `_EXIT_BY_ERROR` table itself (station-specific data) stays in herald.
  - **Atlas is explicitly NOT touched under CAP-3** — see Never.
- **CAP-4 — `pyforge.core.report.BASE_ENVELOPE_SCHEMA: dict`** (draft 2020-12, matching all three
  stations' existing `$schema`), requiring only that `schema_version` is present (no type
  constraint — warden's is a pattern-matched string, doctor's and marshal's are integers, so the
  base cannot type it without breaking one of them) and `findings` is present and is an array (the
  one field every station's finding-list already satisfies). `pyforge.core.report.compose(base,
  station_schema) -> dict` is a pure `{"allOf": [base, station_schema]}` dict merge — no `$ref`,
  no schema registry, no cross-package URI resolution; each station's EXISTING schema file is
  embedded verbatim, unmodified, as the second `allOf` branch, so every payload that validated
  before still validates (the base only adds already-satisfied presence checks).
  - `warden/report.py::render_json`: its existing `jsonschema.Draft202012Validator(_packaged_schema()).validate(document)`
    call validates against `compose(BASE_ENVELOPE_SCHEMA, _packaged_schema())` instead.
  - `doctor/__main__.py::_emit_json`: same swap for its `jsonschema.validate(document, _report_schema())` call.
  - `marshal` validates `envelope.v1.json` only in tests today (no production `jsonschema` import) —
    its 5 test call sites (`test_model.py`, `test_cli.py` ×3, `test_init.py`, `test_spin.py`,
    `test_status.py`) wrap their existing schema load with `compose(...)` the same way.
  - Each station's own `additionalProperties` policy (warden/doctor open, marshal `false`) is
    UNCHANGED — the base never declares `additionalProperties`, so it can neither open nor close
    what each station already decided.
- **CAP-5 — `pyforge.core.errors.PyforgeError(Exception)`**, a bare marker with no `__init__`
  override (matches herald's own `HeraldError` shape exactly) so it never interferes with any
  subclass's own constructor — critical for mason's `CfeUnresolvedError`/`CfeTimeoutError`, which
  carry custom `__init__`/`__reduce__` signatures that must survive unchanged.
  - `herald/errors.py`: `HeraldError(Exception)` → `HeraldError(PyforgeError)`. 13 existing
    subclasses re-parent transitively; no other herald file changes.
  - `mason/errors.py`: `MasonError(Exception)` → `MasonError(PyforgeError)`. 3 subclasses re-parent
    transitively; their custom `__init__`/`__reduce__` overrides are untouched.
  - **37 scattered family-root classes gain `PyforgeError` as an additional base** (multiple
    inheritance where the current base is a stdlib type other than bare `Exception`, e.g.
    `class FsError(PyforgeError, Exception)` unchanged shape since `Exception` was already the
    base; `class WaiverError(PyforgeError, ValueError)` for the 21 classes currently subclassing
    `ValueError`/`RuntimeError`/other non-`Exception` stdlib types) — preserving every existing
    `except <ThatClass>` / `except (ThatClass, ...)` / `except ValueError` (etc.) site UNCHANGED,
    since the original base is still in the MRO. Exact roster (file : class : current base):
    - **warden** (8 roots): `sbom.py:93 SbomValidationError(Exception)`; `config.py:200
      _ConfigError(ValueError)`; `actuator.py:118 ForgeResolutionError(RuntimeError)`,
      `actuator.py:122 ForgeResponseError(RuntimeError)`, `actuator.py:127
      _BranchExistsError(RuntimeError)`; `waiver.py:136 WaiverError(ValueError)`,
      `waiver.py:154 BaselineError(ValueError)`; `extract/__init__.py:38
      UnparsableManifestError(ValueError)`.
    - **marshal** (16 roots): `spec_surface.py:57 SurfaceParseError(ValueError)`;
      `seed/model/manifest.py:99 ManifestError(Exception)`; `seed/model/version.py:74
      InvalidVersionError(ValueError)`; `adapters/vcs_git.py:82 VcsCommandError(Exception)`;
      `core/identity.py:66 MalformedStoryKeyError(ValueError)`, `core/identity.py:72
      MergeSubjectConformanceError(ValueError)`; `adapters/process_posix.py:51
      ProcessError(Exception)`; `adapters/fs_local.py:63 FsError(Exception)`;
      `core/spec_difficulty.py:99 DifficultyParseError(ValueError)`; `cli/config.py:373
      PolicyIOError(Exception)`; `core/findings.py:1458
      UnregisteredFindingCodeError(ValueError)`; `cli/adapters.py:1422
      _SmokeProvisionError(Exception)`; `adapters/harness_bmadloop.py:476
      HarnessPolicyWriteError(Exception)`, `adapters/harness_bmadloop.py:750
      HarnessError(Exception)`; `ports/forge.py:103 ForgeCommandError(Exception)`;
      `core/journal.py:908 _SidecarUnresolved(ValueError)`. (`DirectoryAlreadyExistsError` at
      `fs_local.py:73` is a CHILD of `FsError`, not a root — re-parents transitively, no edit.)
    - **atlas** (13 roots): `datasets/request_datasets.py:283
      PhasePCostAbort(RuntimeError)`; `mcp/tools.py:49 AtlasMCPError(RuntimeError)`;
      `rag/store.py:58 VssNotProvisionedError(RuntimeError)`; `a2a/transport.py:43
      A2ATransportError(RuntimeError)`; `a2a/schema.py:43 A2ADecodeError(ValueError)`;
      `factory/lasuite.py:103 LaSuiteError(RuntimeError)`; `validation.py:98
      DataContractViolation(RuntimeError)`; `datasets/rate_limit.py:254
      FetchError(RuntimeError)`; `publish/emitter.py:81
      ManifestChecksumError(RuntimeError)`; `pipelines/universal_sbom/nodes.py:38
      StaleUniverseError(RuntimeError)`; `admission.py:138 AdmissionConfigError(ValueError)`,
      `admission.py:147 RunAdmissionRejected(RuntimeError)`;
      `pipelines/universal_sbom/gate.py:101 GateDependencyMissing(RuntimeError)`.
  - `pyforge-core/tests/meta/test_exception_root_sole_ownership.py` (CAP-7): AST-scan every
    sibling station's source tree (derived roster, mirrors `test_atomic_write_sole_ownership.py`)
    for a class definition whose base list includes one of a stated, bounded stdlib-exception
    allowlist (`Exception`, `ValueError`, `RuntimeError`, `OSError`, `TypeError`, `KeyError`,
    `LookupError`) but does NOT also include `PyforgeError` (by name, or by inheriting — same
    file only — from a local class whose own bases already include it); flag as a violation.
    Proven non-vacuous against a synthetic `class FooError(Exception): pass` fixture and a
    negative check against a real re-parented class. Bounded (stated, not aspirational, matching
    `test_leaf_constraint.py`'s own convention): cross-file base resolution beyond one hop is out
    of scope — the runtime `issubclass` pins in each station's own tests (below) are the
    behavioral backstop.
- **New pyforge-core dependents.** `doctor` and `mason` gain `pyforge-core` as a real
  `[project].dependencies` / `[package.run-dependencies]` entry for the first time (Story 14.2
  wired atlas/herald/marshal/scribe/steward/warden; doctor and mason had zero atomic-write copies
  so were untouched then). 3-manifest pattern per station (verified working in 14.2): member
  `pyproject.toml` `dependencies` gains `"pyforge-core"`; member `pixi.toml`
  `[package.run-dependencies]` gains `pyforge-core = { path = "../pyforge-core" }`; root
  `pixi.toml`'s `[feature.pyforge-doctor.dependencies]` / `[feature.pyforge-mason.dependencies]`
  gains `pyforge-core = { path = "src/shared/packages/pyforge-core" }`.
- `pixi.toml` changed → regenerate `environment.yaml` (repo-wide ungated rule).
- Every existing pinned exit-code/hierarchy test continues to pass UNCHANGED: warden's
  `LOCKED_EXIT_TABLE`, doctor's `test_verdict.py`, marshal's `test_ad8_*` closed-lattice proof,
  herald's `test_conflict_errors_are_not_transport_errors`/`test_transport_errors_and_every_subclass_map_to_4`
  /`test_a_bare_herald_error_falls_back_to_1`, mason's `issubclass(MasonError, Exception)` +
  `__reduce__` round-trip pins, marshal's `test_findings.py`/`test_seed_model_version.py`
  /`test_identity.py` issubclass pins, marshal's `test_fs_local.py` negative
  `DirectoryAlreadyExistsError` pin, atlas's `test_validation_hook.py` isinstance pin — none of
  these assertions change; they are the regression net for CAP-5's "no `except` clause widens"
  requirement.

**Block If:** none identified — CAP-3/4/5's shape, the leaf-constraint implications for CAP-4's
design, and the full census (lattice declarations, schema fields, exception classes + their catch
sites) are fully specified by SPEC-pyforge-core CAP-3/4/5, AD-67/AD-68, and this session's own
investigation.

**Never:**
- **No change to CAP-6 (subprocess guard)** — Story 14.4, out of scope.
- **Atlas is NOT touched under CAP-3.** It owns no lattice-declaration machinery: `gate.py`'s own
  docstring already states "Exit codes are SOLE-OWNED by `pyforge.warden.verdict`" and imports
  warden's `verdict`/`models`/`report` lazily via the existing `[gate]` extra — there is nothing to
  retire. `trending_candidates/handoff_main.py`'s 4 literal `return 0/1/2/130` statements are a
  separate, already-documented NFR-6 CLI contract (module docstring names the exact meaning of each
  code) that happens to reuse warden's exact 4-value domain — not a redeclared lattice, no rank
  table, no exit-mapping dict to extract. The Dream/Spec's "5 declarations (atlas, doctor, herald,
  marshal, warden)" census over-counts atlas; corrected here the same way Story 14.2 corrected its
  own 18-file-vs-20-copy count.
- **No change to any enum's MEMBERS or any station's actual returned exit-code VALUES.** `Status`,
  `DoctorStatus`, `Verdict` keep their exact members; `EXIT_SIGINT`/`EXIT_USAGE`/every
  `_EXIT_BY_*` mapping's values are byte-for-byte unchanged — only the RANK/DOMAIN BOOKKEEPING
  moves to the shared primitive.
- **No change to `marshal`'s `_RELAY_PASSTHROUGH`** — its "strict subset of `GUARDED_EXIT_CODES`"
  relationship stays comment-documented, not type-enforced; not named by CAP-3's stated success
  criteria, out of scope for this story.
- **No change to any station's schema FILE content** (required fields, `additionalProperties`
  policy, `$defs`) — `compose()` embeds each file verbatim; CAP-4 adds a joint presence check, it
  does not rewrite anyone's contract.
- **No `jsonschema` import anywhere under `pyforge-core/src/`** — would violate CAP-1's leaf
  constraint (a real, enforced meta-test, not a style preference).
- **No change to any of the 44 scattered exception classes' custom `__init__`, `__reduce__`,
  message formatting, or attributes** (e.g. `MergeSubjectConformanceError.finding`,
  `DataContractViolation.dataset/.violations/.alert`, `FetchError.key/.status`) — only the class
  statement's base-list changes.
- **No deprecation window anywhere** — CAP-3/4/5's retirements land in this story, not alongside a
  parallel path.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Lattice rank | `Lattice(order=(A,B,C), exit_by_member={A:2,B:1,C:0}).rank(B)` | `1` | No error expected |
| Lattice exit_codes | same instance | `.exit_codes == frozenset({0,1,2})` | No error expected |
| Doctor narrows warden | `DOCTOR_LATTICE.narrows(WARDEN_LATTICE)` in the new test | `True` (`{0,2,130} <= {0,1,2,130}`) | Test fails loudly if a future edit breaks the subset relationship |
| Marshal does NOT narrow warden | `MARSHAL_LATTICE.narrows(WARDEN_LATTICE)` (not asserted true anywhere — informational) | `False` (`{0,1,2,3,4,130}` is not `<= {0,1,2,130}`) | Not an error; marshal is a separate domain, not required to narrow |
| Herald dispatch, matched subclass | `dispatch_exit_code(SeedConflictError(...), _EXIT_BY_ERROR, default=1)` | `3` (most-specific-first isinstance match) | No error expected |
| Herald dispatch, unmapped subclass | `dispatch_exit_code(HeraldError("x"), _EXIT_BY_ERROR, default=1)` | `1` (falls through to default) | No error expected |
| compose() shape | `compose(BASE_ENVELOPE_SCHEMA, {"type": "object", "required": ["x"]})` | `{"allOf": [BASE_ENVELOPE_SCHEMA, {"type": "object", "required": ["x"]}]}` | No error expected |
| Composed validation, real warden report | A real `ComplianceReport.to_json_dict()` fixture validated against `compose(BASE, warden_schema)` | Validates (unchanged from validating against `warden_schema` alone) | `ValidationError` would indicate a regression |
| Composed validation, missing findings | A document missing `findings` entirely | `ValidationError` from the BASE branch alone, even before the station branch is checked | Raised as `jsonschema.exceptions.ValidationError` |
| Exception re-parent, stdlib base preserved | `raise FsError("x")` caught by `except (FsError, OSError)` (an existing `adapters.py` site) | Still caught — `FsError` still `isinstance`s as `Exception`/its original base | No behavior change |
| Exception re-parent, new capability | `except PyforgeError` (a NEW catch form, not present before this story) | Catches any of the 39 re-parented classes plus herald's/mason's 16 subclasses | Proves CAP-5's stated success signal |
| Exception sole-ownership guard, synthetic violation | A synthetic fixture `class FooError(Exception): pass` fed to the detector | Flagged as a violation | Guard is alive, not vacuous |
| Exception sole-ownership guard, real re-parented class | `FsError(PyforgeError, Exception)`'s real body fed to the detector | NOT flagged | Guard does not false-positive on the story's own fix |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-core/src/pyforge/core/verdict.py` -- NEW: `Lattice` (generic
  `order`+`exit_by_member` → `.rank`/`.exit_codes`/`.narrows`) and `dispatch_exit_code(exc, table,
  default)` (herald's most-specific-first isinstance algorithm, generalized). Zero non-stdlib
  imports.
- `src/shared/packages/pyforge-core/src/pyforge/core/report.py` -- NEW: `BASE_ENVELOPE_SCHEMA: dict`
  + `compose(base, station_schema) -> dict`. No `jsonschema` import.
- `src/shared/packages/pyforge-core/src/pyforge/core/errors.py` -- NEW: `PyforgeError(Exception)`,
  bare marker.
- `src/shared/packages/pyforge-core/tests/unit/test_verdict.py`,
  `tests/unit/test_report.py`, `tests/unit/test_errors.py` -- NEW: primitive-level unit tests for
  the three modules above (see I/O matrix).
- `src/shared/packages/pyforge-core/tests/meta/test_exception_root_sole_ownership.py` -- NEW:
  CAP-7 fleet-wide guard for CAP-5 (see Boundaries).
- `src/shared/packages/pyforge-core/tests/meta/test_verdict_lattice_sole_ownership.py` -- NEW:
  CAP-7 fleet-wide guard for CAP-3, scanning for the `{k: i for i, k in enumerate(seq)}`
  rank-dict-comprehension shape outside `pyforge-core`, proven non-vacuous against a synthetic
  fixture (the real instances are retired by this same story, so no real positive remains to
  scan).
- `src/shared/packages/pyforge-warden/src/pyforge/warden/verdict.py` -- retire `_RANK`'s hand
  computation via `Lattice`; keep `_RUNG_ORDER`/`_EXIT_BY_STATUS`/`EXIT_SIGINT`/`exit_code_for`
  public shape unchanged.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/models.py` -- `_VALID_EXIT_CODES` becomes
  `_LATTICE.exit_codes | {EXIT_SIGINT}` (same values, now derived).
- `src/shared/packages/pyforge-warden/src/pyforge/warden/report.py` -- `render_json` validates
  against `compose(BASE_ENVELOPE_SCHEMA, _packaged_schema())`.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/{sbom.py,config.py,actuator.py,waiver.py,extract/__init__.py}`
  -- 8 family-root exception classes gain `PyforgeError` as an added base (see Boundaries roster).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/verdict.py` -- build a `Lattice` from
  doctor's 3-member domain; `exit_code_for`'s own predicate logic UNCHANGED.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py` -- `_emit_json` validates
  against `compose(BASE_ENVELOPE_SCHEMA, _report_schema())`.
- `src/shared/packages/pyforge-doctor/tests/meta/test_verdict_narrows_warden.py` -- NEW: the
  enforced doctor-narrows-warden test (see Boundaries; imports both stations' `verdict` modules
  directly, not scanned by the AD-3 no-warden-import guard since that guard only scans installed
  production `pyforge.doctor`).
- `src/shared/packages/pyforge-doctor/{pyproject.toml,pixi.toml}` -- add `pyforge-core` as a real
  run-dependency (3-manifest pattern).
- `src/shared/packages/pyforge-herald/src/pyforge/herald/errors.py` -- `HeraldError(Exception)` →
  `HeraldError(PyforgeError)`; `exit_code_for` delegates to `pyforge.core.verdict.dispatch_exit_code`.
- `src/shared/packages/pyforge-mason/src/pyforge/mason/errors.py` -- `MasonError(Exception)` →
  `MasonError(PyforgeError)`.
- `src/shared/packages/pyforge-mason/{pyproject.toml,pixi.toml}` -- add `pyforge-core` as a real
  run-dependency.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py` -- retire
  `LATTICE_ORDER`/`_RANK`/`GUARDED_EXIT_CODES`'s hand computation via `Lattice`; `_RELAY_PASSTHROUGH`
  untouched.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/{spec_surface.py,seed/model/manifest.py,seed/model/version.py,adapters/vcs_git.py,core/identity.py,adapters/process_posix.py,adapters/fs_local.py,core/spec_difficulty.py,cli/config.py,core/findings.py,cli/adapters.py,adapters/harness_bmadloop.py,ports/forge.py,core/journal.py}`
  -- 16 family-root exception classes gain `PyforgeError` (see Boundaries roster).
- `src/shared/packages/pyforge-marshal/tests/unit/{test_model.py,test_cli.py,test_init.py,test_spin.py,test_status.py}`
  -- wrap `envelope.v1.json` validation with `compose(...)`.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/{datasets/request_datasets.py,mcp/tools.py,rag/store.py,a2a/transport.py,a2a/schema.py,factory/lasuite.py,validation.py,datasets/rate_limit.py,publish/emitter.py,pipelines/universal_sbom/nodes.py,admission.py,pipelines/universal_sbom/gate.py}`
  -- 13 family-root exception classes gain `PyforgeError` (see Boundaries roster).
- `pixi.toml` (root) -- add `pyforge-core` to `[feature.pyforge-doctor.dependencies]` and
  `[feature.pyforge-mason.dependencies]`.
- `environment.yaml` -- regenerate.
- One captured-real-report fixture per station (`pyforge-warden/tests/fixtures/`,
  `pyforge-doctor/tests/fixtures/` alongside its existing minimal stubs,
  `pyforge-marshal/tests/fixtures/`) -- built from each station's own real report-producing test
  helper (warden's `make_report`, doctor's existing fixtures extended, a real marshal `Envelope`),
  validated against `compose(BASE_ENVELOPE_SCHEMA, <station schema>)`.
- `tests/packaging/test_dependency_completeness.py` -- no code change expected (its
  `_run_dep_spec_str()` path-dict normalization already shipped in Story 14.2); re-run to confirm
  doctor's and mason's new `pyforge-core` entries compare clean.

## Tasks & Acceptance

**Execution:**
- [x] `pyforge-core/src/pyforge/core/verdict.py` + `tests/unit/test_verdict.py` -- implement
  `Lattice`/`dispatch_exit_code` in isolation -- establishes the shared primitive before any
  station points at it
- [x] `pyforge-core/src/pyforge/core/report.py` + `tests/unit/test_report.py` -- implement
  `BASE_ENVELOPE_SCHEMA`/`compose` in isolation, no `jsonschema` import
- [x] `pyforge-core/src/pyforge/core/errors.py` + `tests/unit/test_errors.py` -- implement
  `PyforgeError` in isolation
- [x] `pyforge-core/tests/meta/test_verdict_lattice_sole_ownership.py` -- CAP-7 guard for CAP-3,
  proven non-vacuous on a synthetic fixture
- [x] `pyforge-core/tests/meta/test_exception_root_sole_ownership.py` -- CAP-7 guard for CAP-5,
  proven non-vacuous on a synthetic fixture and non-firing on a real re-parented class
- [x] `pyforge-doctor` + `pyforge-mason` 3-manifest `pyforge-core` wiring + root `pixi.toml` +
  `environment.yaml` regeneration, `pixi install -e pyforge-doctor` / `-e pyforge-mason` clean
  resolve -- unblocks every remaining task below
- [x] Wire warden's verdict lattice to `Lattice` (`verdict.py` + `models.py`'s
  `_VALID_EXIT_CODES`); `pyforge-warden-test` green
- [x] Wire doctor's verdict lattice to `Lattice` + add `tests/meta/test_verdict_narrows_warden.py`
  proving `{0,2,130} <= {0,1,2,130}`; `pyforge-doctor-test` green
- [x] Wire marshal's verdict lattice to `Lattice` (`core/verdict.py`); `pyforge-marshal-test` green
- [x] Wire herald's `exit_code_for` to `dispatch_exit_code`; `pyforge-herald-test` green
- [x] Update warden's `report.py::render_json` and doctor's `__main__.py::_emit_json` to validate
  via `compose(...)`; both stations' test suites green
- [x] Update marshal's 5 test call sites to validate `envelope.v1.json` via `compose(...)`;
  `pyforge-marshal-test` green
- [x] Capture one real report fixture per station (warden, doctor, marshal) and assert it validates
  against `compose(BASE_ENVELOPE_SCHEMA, <station schema>)`
- [x] Re-parent herald's `HeraldError` and mason's `MasonError` to `PyforgeError`; both stations'
  full test suites green (mason's `__reduce__` round-trip pins especially)
- [x] Re-parent warden's 8 family-root exception classes to include `PyforgeError`;
  `pyforge-warden-test` green
- [x] Re-parent marshal's 16 family-root exception classes to include `PyforgeError`;
  `pyforge-marshal-test` green
- [x] Re-parent atlas's 13 family-root exception classes to include `PyforgeError`; atlas's
  relevant test suites green (`test_validation_hook.py`'s isinstance pin especially)
- [x] `environment.yaml` -- final regenerate + commit if any further `pixi.toml` edit occurred

**Acceptance Criteria:**
- Given warden's, doctor's, and marshal's verdict lattices, when this story lands, then all three
  build their rank/exit-domain bookkeeping from `pyforge.core.verdict.Lattice`, and a grep for a
  second `{x: i for i, x in enumerate(...)}` rank-comprehension outside `pyforge-core` returns
  nothing.
- Given doctor's and warden's lattices, when `tests/meta/test_verdict_narrows_warden.py` runs, then
  `DOCTOR_LATTICE.narrows(WARDEN_LATTICE)` is asserted `True` by a real computation, not a
  docstring.
- Given each of warden/doctor/marshal/herald's own existing exit-code test suites, when they run
  after the refactor, then all pinned exit-code values (warden's `LOCKED_EXIT_TABLE`, doctor's
  `{0,2}` predicate tests, marshal's `test_ad8_*` closed-lattice proof, herald's
  `test_conflict_errors_map_to_3`/`test_transport_errors_and_every_subclass_map_to_4`
  /`test_a_bare_herald_error_falls_back_to_1`) pass unchanged.
- Given a real captured report from each of warden/doctor/marshal, when validated against
  `pyforge.core.report.compose(BASE_ENVELOPE_SCHEMA, <that station's own schema>)`, then validation
  passes with no consumer-visible change to any station's schema file content.
- Given any of the 39 re-parented exception classes (herald's `HeraldError`, mason's `MasonError`,
  and the 37 scattered family roots), when raised, then every existing `except <ThatClass>` /
  `except (ThatClass, ...)` / `except <original stdlib base>` site across the repo still catches it
  (proven by each affected station's full existing test suite passing unchanged), AND `except
  PyforgeError` newly catches it too.
- Given the exception sole-ownership meta-test, when it scans every sibling station, then it fires
  on a synthetic `class FooError(Exception): pass` fixture and does not fire on any real
  re-parented class in the fleet.
- Given doctor's and mason's `pixi.toml`/`pyproject.toml`, when inspected, then each declares
  `pyforge-core` as a real run-dependency, matching the 3-manifest pattern Story 14.2 verified.
- Given root `pixi.toml` changed, when `pixi project export conda-environment -e build` runs, then
  the regenerated `environment.yaml` is committed alongside it.

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (low 3)
- defer: 1: (low 1)
- reject: 13: (low 11, medium 2)
- addressed_findings:
  - `[low]` `[patch]` Blind Hunter: `test_verdict_lattice_sole_ownership.py` and
    `test_exception_root_sole_ownership.py` (this story's own new files) duplicated
    `_sibling_station_dirs()`/`_station_source_files()`/`_parse()` verbatim from the
    pre-existing `test_atomic_write_sole_ownership.py` (Story 14.2) — three copies of the
    same station-enumeration/parse logic. Extracted to a new `tests/meta/conftest.py`
    (`sibling_station_dirs`/`station_source_files`/`parse_module`, each taking an optional
    `exclude` set); all three meta-test files now import from it. Re-verified: pytest's
    default "prepend" import mode (no `__init__.py` in `tests/`) puts each test file's own
    directory on `sys.path`, so a bare `from conftest import ...` resolves correctly —
    confirmed by running `test_verdict_lattice_sole_ownership.py` alone before touching the
    other two files. `pyforge-core-test`: 848 passed (847 + 1 new test, unaffected by this
    extraction).
  - `[low]` `[patch]` Edge Case Hunter: `Lattice.__init__` performed no validation that
    `order` contains no duplicate members — a duplicate would silently let the last
    occurrence's rank win via the underlying `enumerate` + dict-comprehension, producing an
    ambiguous rank with no error, at odds with this codebase's fail-loud convention. Added a
    `ValueError` guard in `__init__` plus a regression test
    (`test_lattice_rejects_a_duplicate_order_member`). No real caller has a duplicate today
    (verified: none of warden's/doctor's/marshal's real `order` tuples repeat a member), so
    this is defensive-only, not a live-bug fix.
  - `[low]` `[patch]` Edge Case Hunter, confirmed by reproduction (`jsonschema.validators.validator_for`
    on a schema with no top-level `$schema` still resolved to `Draft202012Validator` in the
    installed `jsonschema==4.26.0` today, so there is currently zero behavioral difference —
    but the inconsistency is real and would silently start mattering if that library default
    ever changes): doctor's `_emit_json` validated via bare `jsonschema.validate(document,
    compose(...))`, relying on default-draft auto-detection since `compose()`'s output
    carries no top-level `$schema` (only the nested base branch does) — unlike warden's
    parallel call site, which pins `jsonschema.Draft202012Validator(...)` explicitly. Pinned
    doctor's call site the same way. `pyforge-doctor-test`: 845 passed, 1 skipped (unchanged
    pass count).
  - `[low]` `[defer]` Blind Hunter: the new exception-root sole-ownership guard's
    `_OUT_OF_SCOPE_STATIONS = {"pyforge-doctor", "pyforge-steward"}` exclusion is real and
    already documented in the test's own module docstring (both stations carry real,
    un-reparented `*Error` roots today — `doctor/cli_bridge.py::CliBridgeError`,
    `doctor/sources/atlas.py::_FetchFailed`, and seven roots across steward) that this
    story's Boundaries roster never named and this story does not touch, mirroring CAP-3's
    own precedent of an explicit atlas exclusion. Not a defect in this story's own scope —
    logged to the deferred-work ledger for a future CAP-5-extension story to pick up.
- rejected (13, with reasoning):
  - `[medium]` Blind Hunter's `compose()`/`allOf`-nesting-breaks-`$ref`/`$defs`-resolution
    concern — empirically DISPROVEN by direct reproduction: every station's schema
    (`warden`, `doctor`, `marshal`) declares its own top-level `$id`, which anchors
    `#/$defs/...` resolution to that schema's own resource regardless of `allOf` nesting
    depth (this is exactly what `$id` is for). Ran `jsonschema.validate` against a real
    `compose(BASE_ENVELOPE_SCHEMA, envelope.v1.json)` with both a valid and a
    deliberately-invalid `findings[0].severity` — the invalid one was correctly rejected via
    the `$ref`'d `#/$defs/finding` branch, proving resolution works.
  - `[medium]` Blind Hunter's `pyforge.core.report.compose()` vs. pre-existing
    `pyforge.warden.verdict.compose()` naming-collision concern — real (confirmed: warden's
    `report.py` already needed `import ... as compose_envelope_schema` to avoid shadowing
    its own `verdict.compose`), but already correctly and safely resolved via that alias at
    the one place a genuine collision exists; marshal's test files' `policy.compose` uses are
    all function-local imports that Python scopes correctly (no runtime ambiguity, verified:
    full marshal/warden/doctor suites green). A source-level rename would touch 11 files
    across 5 packages for a cosmetic clarity gain with zero functional benefit — disproportionate
    to a low-severity, already-mitigated finding (Simplicity First).
  - `[low]` CAP-5 exception re-parenting adds no `except PyforgeError` consumer yet (Blind
    Hunter) — this is the approved SPEC-pyforge-core CAP-5's own explicit shape (a shared
    root FOR future consumption, not this story's job to consume); not a defect this story's
    implementation introduced.
  - `[low]` Doctor's `LATTICE` not coupled to `exit_code_for`'s body, risking future drift
    (Blind Hunter) — verified `LATTICE.exit_by_member` already references the SAME named
    `_EXIT_FAIL`/`_EXIT_OK` constants `exit_code_for` returns (not duplicated literals); the
    spec's own Design Notes already deliberately decided against routing `exit_code_for`
    through `Lattice.rank()` (doctor's projection isn't rank-based) — re-litigating an
    already-justified, explicit design decision.
  - `[low]` `Lattice.rank()` raises a bare `KeyError` for an unranked member (Edge Case
    Hunter) — idiomatic dict-lookup-miss behavior, not a materially unclear failure mode; no
    caller in this diff ever calls `.rank()` with an unranked member.
  - `[low]` `dispatch_exit_code` trusts the caller's table ordering with no validation (Edge
    Case Hunter) — this is herald's own PRE-EXISTING isinstance-loop characteristic, extracted
    byte-for-byte per the spec's explicit mandate; not a new gap introduced by this story.
  - `[low]` AST guard alias-evasion (`from pyforge.core.errors import PyforgeError as _PE`
    would evade `_base_name`'s literal-name match) and the 7-name stdlib allowlist's
    incompleteness (e.g. `FileNotFoundError`) — both already explicitly disclosed as stated,
    bounded limitations in the guard's own module docstring, mirroring
    `test_leaf_constraint.py`'s established "Bounded (stated, not aspirational)" convention;
    neither is exercised by any of the 39 real re-parented classes in this diff (all use the
    unaliased literal name; none currently subclass a name outside the 7-item allowlist).
  - `[low]` Verdict-lattice guard's narrow `_RANK`-literal-name-only detection and
    single-target-`Name`-assignment-only AST shape (Blind Hunter + Edge Case Hunter) — both
    already explicitly disclosed as stated bounds in the guard's own module docstring,
    mirroring `test_atomic_write_sole_ownership.py`'s own precedent of a narrow, name-shaped
    heuristic added specifically to avoid firing on an unrelated real pattern
    (`marshal/core/status.py::_PHASE_RANK`).
  - `[low]` No try/except around `read_text`/`ast.parse` in the two new meta tests (Edge Case
    Hunter) — matches the identical, pre-existing convention in every sibling meta test
    (`test_leaf_constraint.py`, `test_atomic_write_sole_ownership.py`), not a new gap.
  - `[low]` Same-named `ClassDef`s colliding in the exception guard's same-file fixpoint set
    (Edge Case Hunter) — theoretical; two classes sharing one name in one file is a pre-existing
    Python anti-pattern unrelated to this guard, and no real file in the fleet does this.
  - `[low]` Deletion check: warden's `models.py::_VALID_EXIT_CODES` removed with no alias
    (Edge Case Hunter) — verified safe: only a comment now references the old name, no other
    module or test imports it.
  - `[low]` Re-parenting pattern (multiple-inheritance vs. single-base) not centrally
    documented (Blind Hunter) — already adequately covered by `pyforge.core.errors`'s own
    module docstring ("each re-parented class keeps its original stdlib base in its MRO via
    multiple inheritance").

## Design Notes

**Why `pyforge-core` ships schema DATA and a pure dict-`compose` helper for CAP-4, never a
`jsonschema.validate` call.** CAP-1's leaf constraint (`test_leaf_constraint.py`) fails the build on
any non-stdlib import under `src/pyforge/core`, and `jsonschema` is third-party. The alternative
considered — a proper `$ref`-based schema composition, where each station's schema references
`pyforge-core`'s base by URI — would require a cross-package schema registry/resolver
(`jsonschema`'s `referencing` library) wired into every validate call site, real infrastructure this
story does not need: `compose()`'s `{"allOf": [base, station]}` achieves the identical validation
outcome (a document must satisfy both) as a pure, stdlib-safe dict merge, with each station's
existing schema embedded verbatim rather than referenced.

**Why doctor's `exit_code_for` predicate logic is NOT rewritten to consult `Lattice.rank()`.**
Doctor's real projection (`any fail → 2, else → 0`) is not rank-based at all — it is a closed
2-valued domain that doesn't need a total ordering to compute. Forcing it through `.rank()` would
be a cosmetic, unrequested rewrite of correct, working logic (Simplicity First / Surgical Changes).
What CAP-3 requires or doctor is the shared DOMAIN DECLARATION (`.exit_codes`) and the narrows
proof — both achieved without touching `exit_code_for`'s body.

**Why the doctor-narrows-warden proof is test-only, never a production import.** Doctor's own AD-3
one-way-dependency guard (`test_no_warden_import.py`) is a HARD existing invariant restricting
`pyforge.warden` imports in production doctor code to one file (`sources/warden.py`), itself further
restricted to `pyforge.warden.engines` only. A verdict-lattice narrows check needs
`pyforge.warden.verdict`, which no production import path can reach. The enforced check therefore
lives in a new test file — this is consistent with every other "enforced, not asserted" claim in
this Spec family (CAP-7's sole-ownership guards are themselves all test-only, never production
runtime assertions).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-core pyforge-core-test` -- new `Lattice`/`compose`/`PyforgeError`
  primitives + both new sole-ownership meta-tests green
- `pixi install -e pyforge-doctor && pixi install -e pyforge-mason` -- clean resolve with the new
  `pyforge-core` path dependency
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` -- lattice + report + exception changes
  green
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- lattice + narrows test + report +
  new dependency wiring green
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- lattice + envelope test wrapping +
  exception changes green
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- dispatch delegation + exception
  re-parent green
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` -- exception re-parent + new dependency
  wiring green
- `pixi run --frozen -e pyforge-atlas kedro-test` -- 13 exception re-parents green (pre-existing
  unrelated failures noted in Story 14.2's own verification are not this story's to fix)
- `grep -rn "for .*, .* in enumerate(" src/shared/packages --include="*.py" | grep -v pyforge-core/`
  -- manually inspect any hit for the specific rank-comprehension shape; expect none matching the
  retired pattern
- `python3 -m pytest tests/packaging/test_dependency_completeness.py -q` -- doctor's and mason's
  new `pyforge-core` entries compare clean against the existing path-dict normalization
- `pixi project export conda-environment -e build > environment.yaml && git diff --stat environment.yaml`
  -- commit if it reports a diff
- `pixi run -e local-recipes ruff check src/shared/packages/pyforge-core` -- expect zero findings
  on the new `verdict.py`/`report.py`/`errors.py` modules

**Manual checks (if no CLI):**
- Confirm doctor's and mason's `pixi.toml`/`pyproject.toml` `pyforge-core` entries follow the same
  shape as the 6 stations Story 14.2 already wired.

## Auto Run Result

**Summary.** This session resumed a spec whose implementation, review (Review Triage Log above:
0 intent_gap, 0 bad_spec, 3 patch, 1 defer, 13 reject) and commit (`1bd8c8a2de`) were already
complete from a prior session — every Task & Acceptance box was already `[x]` and `final_revision`
was already stamped. The one open item was the harness's own deterministic verify gate:
`python scripts/spec_surface_reconcile.py` failed with 40 gating `[drift]` findings, because the
story's 40 governed-file changes span 7 owning Specs whose `.memlog.md` files never named the
changed paths (the same S-13.7 gap already recorded multiple times in this fleet's history — see
e.g. spec-pyforge-marshal's own "Surface reconcile" sections for stories 14-2, 3-12/3-13, 2-8,
3-11, 5-10). This session's only job was that repair: no source or test code changed, and
`<intent-contract>` was not touched.

**Files changed this session** (8 total; see `git diff --stat 7712f80083 4c0f893964`):
- `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-herald-moments-2-4-live-backend/.memlog.md`
  and `spec-pyforge-herald/.memlog.md` — name `pyforge-herald/src/pyforge/herald/errors.py`
  (`HeraldError` re-parent to `PyforgeError` + `exit_code_for` delegates to `dispatch_exit_code`).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-adaptive-model-tiering/.memlog.md`
  — names `adapters/harness_bmadloop.py` and `core/spec_difficulty.py` (their family-root
  exceptions re-parented).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-horizontal-run-concurrency/.memlog.md`
  — names `adapters/harness_bmadloop.py`.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md` —
  names root `pixi.toml` plus the 10 new/changed `pyforge-core` verdict/report/errors/test paths
  (CAP-3/CAP-4/CAP-5/CAP-7, this story's own capability home).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md`
  — names all 21 governed marshal paths this story moved (the `Lattice` wiring in `core/verdict.py`,
  the 5 test call sites wrapped with `compose(...)` plus the new captured-envelope fixture, and the
  16 family-root exception classes across 14 files that gained `PyforgeError`).
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/.memlog.md` —
  names `pixi.toml`, `pyproject.toml` (new `pyforge-core` run-dependency) and
  `src/pyforge/mason/errors.py` (`MasonError` re-parent).
- `scripts/.spec-surface-baseline.json` — re-stamped via
  `python scripts/spec_surface_check.py --write-baseline --spec <name>` for exactly those 7 specs
  (never the unscoped form, which would have accepted every other spec's own pending drift as
  correct).

**Review findings breakdown.** None — this pass performed no review (Blind Hunter/Edge Case
Hunter were not invoked); it is a mechanical reconciliation of already-reviewed, already-shipped
code against the deterministic drift gate. The Review Triage Log above is unchanged from the prior
session.

**Follow-up review recommendation:** `false` — no code changed, nothing for a reviewer to look at
that the prior 3-pass review did not already see.

**Verification performed** (all commands actually run this session, on the repair commit
`4c0f893964`):
- `python3 scripts/spec_surface_reconcile.py` → `OK: every tracked file governed or allowlisted;
  no drift.` (rc=0; was rc=1 with 40 findings at session start)
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` → 3598 passed, 9 deselected
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` → 74 passed
- `pixi project export conda-environment -e build` re-run and diffed against the committed
  `environment.yaml` → byte-identical, no commit needed (root `pixi.toml`'s two-line change was
  already reflected)
- `git status --short` → clean

**Residual risks.** None identified. The reconciliation is bookkeeping-only and does not touch any
of the fleet's `except` clauses, exit-code tables, or schema files that CAP-3/CAP-4/CAP-5's own
regression net (named in the Boundaries section above) guards.

