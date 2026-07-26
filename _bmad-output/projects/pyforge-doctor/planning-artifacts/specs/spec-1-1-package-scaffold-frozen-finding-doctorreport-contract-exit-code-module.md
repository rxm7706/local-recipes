---
title: 'Package scaffold, frozen Finding/DoctorReport contract & exit-code module'
type: 'feature'
created: '2026-07-25'
status: 'done'
baseline_revision: '65d51974cfd81eb1cc303158bbed00470edfa28b'
final_revision: 'efe4681d2e1fd4b70ce7e62335c486fbd6188c0d'
review_loop_iteration: 0
followup_review_recommended: false
context: [
  '{project-root}/src/shared/packages/pyforge-warden/src/pyforge/warden/models.py',
  '{project-root}/src/shared/packages/pyforge-warden/src/pyforge/warden/verdict.py',
  '{project-root}/src/shared/packages/pyforge-warden/tests/meta/test_verdict_sole_ownership.py',
  '{project-root}/src/shared/packages/pyforge-warden/pyproject.toml',
  '{project-root}/src/shared/packages/pyforge-warden/pixi.toml',
]
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `src/shared/packages/pyforge-doctor/` does not exist. No later Epic 1/2/3 story can add a check, gather filter, or verb until the `Finding`/`Source`/`DoctorStatus`/`DoctorReport` contract and Doctor's own exit-code module are frozen and unit-proven.

**Approach:** Scaffold `pyforge-doctor` mirroring `pyforge-warden`'s exact package layout and idioms (pyproject.toml shape, `src/pyforge/doctor/`, per-package `pixi.toml`, `tests/{unit,meta,fixtures}/`, `scripts/`), then define `models.py` (closed `DoctorStatus`/`Source`/`Partition` enums, `Finding`/`Prescription`/`DoctorReport` dataclasses) and `verdict.py` (sole exit-code projection, domain `{0, 2, 130}`), plus a committed JSON Schema for `DoctorReport`. Wire the root `pixi.toml` `[feature.pyforge-doctor.*]` block + `pyforge-doctor` environment so `pixi run -e pyforge-doctor pyforge-doctor-test` (the bmad-loop verify command) becomes real.

## Boundaries & Constraints

**Always:**
- Mirror `pyforge-warden`'s layout and idioms exactly (StrEnum status/source types, frozen-dataclass `__post_init__` coercion/validation pattern, `jsonschema`-validated packaged schema, per-package `pixi.toml` `[package]` table, root `pixi.toml` `[feature.<pkg>.*]` block + lean `no-default-feature` environment) — do not invent new conventions this sibling package doesn't already establish.
- `DoctorStatus` (`ok`/`warn`/`fail`), `Source` (7 members: `warden-doctor`, `staleness-report`, `cve-watcher`, `behind-upstream`, `feedstock-health`, `release-cadence`, `env-hygiene`), and `Partition` (`actionable`/`blocked`/`accepted-risk`) are closed `StrEnum`s.
- Doctor's exit-code domain is exactly `{0, 2, 130}` — `1` never appears anywhere under `pyforge.doctor`. A `warn` Finding never changes the exit code.
- `src/pyforge/doctor/__init__.py` stays empty (no `__version__` constant) — the version string the `--version` stub prints lives in `__main__.py` instead, duplicating `pyproject.toml`'s version literal (acceptable at scaffold stage; unlike warden, whose `__init__.py` is not required to stay empty).
- `DoctorReport.prescriptions` is present (a list, possibly empty) only when `verb == "diagnose"`; for `check`/`monitor` it is absent from both the Python model (`None`) and the serialized JSON (key omitted, never `null`).
- The root `pixi.toml` environment name `pyforge-doctor` and task name `pyforge-doctor-test` are load-bearing for `.bmad-loop/policy.toml`'s `[verify]` command — must match those two strings exactly.
- A meta-test proves NFR-1 (nothing under `pyforge.doctor` writes outside a `tempfile`-scoped path) even though nothing gathers real Findings yet, and a meta-test proves `verdict.py` is the sole module containing an exit-primitive call with a guarded `{0,2,130}` literal — both mirroring `pyforge-warden/tests/meta/test_verdict_sole_ownership.py`'s AST-scan technique, including a non-vacuous "guard is alive" positive test.

**Block If:** `src/shared/packages/pyforge-doctor/` already exists with content that conflicts with this scaffold, or the root `pixi.toml` already contains a `[feature.pyforge-doctor.*]` block that conflicts with the shape mirrored from `[feature.pyforge-warden.*]`.

**Never:** No `sources/`, `checks/`, `cli_bridge.py`, `normalize.py`, `prescribe.py`, or `cli.py` modules — those belong to Stories 1.2–1.5 and Epic 3. No `check`/`monitor`/`diagnose` subcommand dispatch in `__main__.py` yet, only `--version`/`--help`. No `--fix`/mutating actuator. Never import `pyforge.warden.models`/`verdict`/`ErrorKind` — Doctor's taxonomy structurally mirrors warden's, it never imports from it (AD-3).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Valid Finding | `Finding(source=Source.ENV_HYGIENE, check="x", status=DoctorStatus.WARN, message="m", evidence={})` | Constructs successfully | No error expected |
| Unknown status | `Finding(status="critical", ...)` | Rejected at construction | `ValueError`, never silently coerced |
| Unknown source | `Finding(source="not-a-source", ...)` | Rejected at construction | `ValueError` |
| check/monitor report | `DoctorReport(verb="check", prescriptions=None, ...)` | Serializes with no `prescriptions` key | No error expected |
| diagnose report, empty prescriptions | `DoctorReport(verb="diagnose", prescriptions=[], ...)` | Serializes with `"prescriptions": []` | No error expected |
| diagnose report missing prescriptions | `DoctorReport(verb="diagnose", prescriptions=None, ...)` | Rejected at construction | `ValueError` |
| check report with prescriptions set | `DoctorReport(verb="check", prescriptions=[...], ...)` | Rejected at construction | `ValueError` |
| All-ok/warn findings | `verdict` over findings with only `ok`/`warn` statuses | Exit code `0` | No error expected |
| One fail present | `verdict` over findings incl. one `fail` (any number of `ok`/`warn` alongside) | Exit code `2` | No error expected |
| Minimal check-verb JSON | `{schema_version:1, verb:"check", generated_at:..., findings:[]}` | Validates against packaged `report-schema.json` | No error expected |
| Minimal diagnose-verb JSON | `{..., verb:"diagnose", findings:[], prescriptions:[]}` | Validates against packaged `report-schema.json` | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-warden/{pyproject.toml,pixi.toml,src/pyforge/warden/{models.py,verdict.py,cli.py,__init__.py},tests/meta/test_verdict_sole_ownership.py}` -- the exact structural/idiom reference this story mirrors; open before writing the new package.
- `pixi.toml` (root) lines ~124-147 (`[environments]`) and ~1041-1088 (`[feature.pyforge-warden.*]`) -- template for the new `[feature.pyforge-doctor.*]` block + environment entry.
- `.bmad-loop/policy.toml` `[verify]` -- confirms the exact required env/task names (`pyforge-doctor`, `pyforge-doctor-test`).
- `_bmad-output/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md` §Consistency Conventions / §Structural Seed / §Deferred -- source of the `DoctorReport`/`Prescription` envelope shape and confirmation this story owns the `pixi.toml` edit.

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-doctor/pyproject.toml` -- new manifest mirroring warden's shape (hatchling backend, `name = "pyforge-doctor"`, `requires-python = ">=3.14"`, lean `dependencies` incl. `jsonschema` for schema validation, `optional-dependencies.gate = ["pyforge-warden"]`, `[project.scripts] doctor = "pyforge.doctor.__main__:main"`, `[tool.hatch.build.targets.wheel] packages = ["src/pyforge"]`) -- AD-1's extra + the package identity.
- [x] `src/shared/packages/pyforge-doctor/pixi.toml` -- new per-package `[package]` manifest mirroring warden's (`pixi-build-python` backend, `python >=3.14` host-dependency) -- required for the root `pixi.toml` path dependency to build.
- [x] `src/shared/packages/pyforge-doctor/README.md`, `.gitignore` -- minimal, mirroring warden's -- structural parity per AC1.
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__init__.py` -- empty file -- AC1 literal requirement.
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py` -- argparse stub supporting only `--version`/`--help`, `main(argv=None) -> int` entry -- AC1's `doctor --version`/`--help` requirement; no subcommand dispatch yet.
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` -- `DoctorStatus`, `Source`, `Partition` StrEnums; `Finding` (`source`, `check`, `status`, `message`, `evidence: dict`), `Prescription` (`finding_ref`, `partition`, `rank`, `rank_factors`, `action`, `root_cause` -- `rank`/`rank_factors` left `None`-able, Epic 3 populates them), `DoctorReport` dataclasses with `__post_init__` validation (status/source closure, `prescriptions`-vs-`verb` coherence) -- AC2/AC3, AD-3.
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/verdict.py` -- sole exit-code projection over a `list[Finding]` (or `DoctorReport`), domain `{0, 2, 130}` -- AC4, AD-2.
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/report-schema.json` -- committed JSON Schema for the `DoctorReport` envelope, incl. the `verb`-conditional `prescriptions` rule -- AC3, NFR-5.
- [x] `src/shared/packages/pyforge-doctor/tests/unit/{test_models.py,test_verdict.py,test_main_stub.py}` -- cover every I/O-matrix row above plus the `--version`/`--help` smoke test.
- [x] `src/shared/packages/pyforge-doctor/tests/meta/{test_verdict_sole_ownership.py,test_read_only_guard.py}` -- AC4/AC5 static guards, each with a non-vacuous "guard is alive" positive test mirroring warden's.
- [x] `src/shared/packages/pyforge-doctor/tests/fixtures/{minimal_check_report.json,minimal_diagnose_report.json}` -- minimal example `DoctorReport` documents the schema test validates.
- [x] `src/shared/packages/pyforge-doctor/scripts/` -- create the directory (mirrors warden's layout); no script content required this story.
- [x] `pixi.toml` (root) -- add `[feature.pyforge-doctor.dependencies]` (path dep + hatchling/python-build/pytest), `[feature.pyforge-doctor.tasks.pyforge-doctor-test]` (`pytest src/shared/packages/pyforge-doctor/tests -q`), `pyforge-doctor-build-{conda,dist,build}` tasks, and a `pyforge-doctor = { features = ["pyforge-doctor"], no-default-feature = true }` entry in `[environments]` -- mirrors `[feature.pyforge-warden.*]` verbatim; unblocks the bmad-loop verify command.

**Acceptance Criteria:**
- Given `src/shared/packages/pyforge-doctor/` did not exist, when the scaffold lands, then its layout is structurally identical in shape to `pyforge-warden`'s (same top-level entries, same `tests/{unit,meta,fixtures}/` split).
- Given the new package, when `pixi run -e pyforge-doctor pyforge-doctor-test` runs, then it passes (env + task both real, mirroring warden's).
- Given the meta-test suite, when it runs, then both the sole-ownership exit-code guard and the NFR-1 read-only guard pass, and each has a positive "guard fires when violated" proof, not just an absence-of-failure proof.
- Given the root `pixi.toml`, when inspected, then `[environments]` contains a `pyforge-doctor` entry with `no-default-feature = true`, matching the `pyforge-warden`/`pyforge-atlas` pattern already established.

## Design Notes

Mirror warden's frozen-dataclass coercion idiom exactly — validation happens in `__post_init__` via `object.__setattr__` re-assignment through the enum constructor, so an invalid raw value fails loudly at construction rather than silently:

```python
@dataclass(frozen=True)
class Finding:
    source: Source
    check: str
    status: DoctorStatus
    message: str
    evidence: dict

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", Source(self.source))
        object.__setattr__(self, "status", DoctorStatus(self.status))
```

The console-script command name is `doctor` (not `pyforge-doctor`) — the architecture spine's Structural Seed annotates `__main__.py` as the "`doctor` console-script entrypoint", the PRD consistently writes `doctor check`/`doctor monitor`/`doctor diagnose`, and this matches warden's own `pyforge-warden` package → `warden` command precedent. Epics.md Story 1.1's AC1 phrase "a `pyforge-doctor --version`/`--help` stub runs" refers informally to the package, not a literal executable name.

## Verification

**Commands:**
- `pixi run -e pyforge-doctor pyforge-doctor-test` -- expected: full unit + meta suite passes (this is `.bmad-loop/policy.toml`'s `[verify]` gate).
- `pixi run -e pyforge-doctor doctor --version` and `... doctor --help` -- expected: exit `0`, prints version/usage text, no traceback.

## Review Triage Log

### 2026-07-25 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 12: (high 0, medium 7, low 5)
- defer: 2: (high 0, medium 0, low 2)
- reject: 7
- addressed_findings:
  - `medium` `patch` No meta-test enforced AD-3's "Doctor never imports pyforge.warden" invariant (only prose) — added `tests/meta/test_no_warden_import.py`, AST-scanning the installed package with a non-vacuous "guard fires on synthetic violation" positive test.
  - `medium` `patch` `Finding.evidence`/`Prescription.rank_factors` were plain mutable dicts stored by reference inside `frozen=True` dataclasses (mutable after construction despite the "frozen contract" docstring claim) — both now shallow-copied in `__post_init__`; added defensive-copy tests.
  - `medium` `patch` `Prescription.to_json_dict()` was never exercised by a real instance in any test (every diagnose-report test used an empty `prescriptions` list) — added a round-trip test through a real `DoctorReport(verb="diagnose", ...)`, validated against `#/$defs/prescription` in the packaged schema.
  - `medium` `patch` The `KeyboardInterrupt` → `EXIT_SIGINT` branch in `__main__.main()` had zero coverage — added a test that mocks `argparse.ArgumentParser.parse_args` to raise `KeyboardInterrupt` and asserts `main()` returns 130.
  - `medium` `patch` `DoctorReport.__post_init__` accepted `schema_version <= 0` despite `report-schema.json` declaring `"minimum": 1` — added a construction-time bounds check + two rejection tests (mirrors the "fail loud at construction" philosophy already used for status/source).
  - `medium` `patch` `Finding.evidence` accepted `None`/non-dict values, which would only fail later at schema-validation time (`type: object`) instead of at construction — added an `isinstance` check + rejection test.
  - `medium` `patch` The NFR-1 read-only guard's `open(...)` detector only matched the builtin `Name` form, missing attribute-form write opens (`Path(...).open("w")`) — extended `_open_call_violations` to also scan `ast.Attribute` calls with `attr == "open"` (correcting the mode-arg index, which differs between the two call shapes), plus a synthetic-violation test and two new benign-call regression tests.
  - `low` `patch` `Source`'s docstring miscounted its own membership ("four atlas Watch axes" vs. the real 5) — corrected the docstring.
  - `low` `patch` `pyproject.toml`'s `gate` extra comment implied `pip install pyforge-doctor[gate]` works outside this monorepo and that the extra is already "installed by default in the in-repo pixi env" — neither is true yet (pyforge-warden isn't published to PyPI; the root `pixi.toml`'s `[feature.pyforge-doctor.*]` block doesn't wire it in, on purpose, since no code imports `pyforge.warden` until Story 1.2) — rewrote the comment to state the current scaffold-stage status accurately.
  - `low` `patch` A test name (`test_exit_code_domain_is_exactly_zero_two_onethirty_over_all_combinations`) implied coverage of all three `{0, 2, 130}` domain values, but `exit_code_for` can only ever return `0` or `2` — renamed to `test_exit_code_for_stays_in_zero_or_two_over_all_finding_combinations` with a clarifying docstring.
  - `low` `patch` `__main__.main()`'s `SystemExit` handler returned any int code verbatim, including a hypothetical future value outside `{0, 2, 130}` — clamped the fallback to `2` (defense in depth; not reachable with the current argparse config, but cheap insurance for AD-2's stated domain).
  - `low` `defer` Three-tier `hatchling` version-pin incoherence (unconstrained / `>=1.31.0` / `"*"` across the three manifests) — pre-existing in `pyforge-warden`'s own files, faithfully mirrored; a cross-package fix, not this story's to make unilaterally. Logged in `deferred-work.md`.
  - `low` `defer` The sole-ownership guard's AST detector only matches `ast.Call` nodes, missing a bare `raise SystemExit` (no parens/args) — an inherited limitation of the exemplar `pyforge-warden` technique itself (already documented as "best-effort" there), not introduced by this story. Logged in `deferred-work.md`.

Rejected (noise or already-settled by the frozen spec, dropped silently): schema packaging into the wheel is already proven both by an `importlib.resources`-based test and by the implementation pass's manual wheel-install verification (no further automated proof needed at scaffold stage); `requires-python = ">=3.14"` and the hand-duplicated `__version__` are both explicit, deliberate choices stated in this spec's own (read-only) `<intent-contract>` and Design Notes, not implementation deviations; the empty `scripts/.gitkeep` placeholder is exactly what Task list item for `scripts/` asked for; and four caller-misuse edge cases in `verdict.py`/`models.py` (non-`Finding` iterables, `None` arguments) match `pyforge-warden`'s own established non-coercing design and aren't exercised by any I/O-matrix row.

**Verification note (environmental, not a story defect):** the exact `[verify]` command above cannot run to completion in this bmad-loop worktree — `pixi-build-python 0.8.3` panics on build-metadata queries once the worktree path exceeds ~250 chars (this worktree is 204 chars; nested build paths push it over). Confirmed pre-existing and unrelated to this story's changes: the untouched sibling `pyforge-warden` env hits the identical panic in this same worktree (`pixi run -e pyforge-warden pyforge-warden-test`). Same failure class already recorded for `pyforge-warden`'s own Story 1.1. Substitute verification stands in for the primary command: `PYTHONPATH=src python3 -m pytest tests -q`, a clean `python -m build --no-isolation --wheel`, and running the real installed `doctor` console script end to end. Full diagnosis + orchestrator-level recommendation recorded in `{implementation_artifacts}/deferred-work.md`. (This note carries the diagnosis forward from the lost pass described in the Spec Change Log below — the environmental facts still hold, but the "35/35 passed" result itself must be reproduced fresh by this pass, not assumed.)

## Auto Run Result

Status: `done`

**Summary of implemented change:** Scaffolded `src/shared/packages/pyforge-doctor/`, mirroring `pyforge-warden`'s package layout and idioms exactly: closed `DoctorStatus`/`Source`/`Partition` `StrEnum`s, frozen `Finding`/`Prescription`/`DoctorReport` dataclasses with `__post_init__` validation (enum coercion, verb/prescriptions coherence, `evidence`/`rank_factors` type-checked + defensively copied, `schema_version >= 1`), `verdict.py` as the sole exit-code projection over the closed `{0, 2, 130}` domain, a packaged JSON Schema for the `DoctorReport` envelope, an argparse `--version`/`--help`-only CLI stub, two AST-based meta-test guards (AD-2 exit-code sole ownership, extended with a new AD-3 no-warden-import guard and a hardened NFR-1 read-only guard), and the root `pixi.toml` `[feature.pyforge-doctor.*]` wiring + `pyforge-doctor` environment.

**Files changed:** see commit `efe4681d2e1fd4b70ce7e62335c486fbd6188c0d` (19 files, 1630 insertions) — `pixi.toml` (root, edited) + 18 new files under `src/shared/packages/pyforge-doctor/` (package manifests, `src/pyforge/doctor/{__init__,__main__,models,verdict,data/report-schema.json}`, `tests/{unit,meta,fixtures}/*`, `scripts/.gitkeep`, `README.md`, `.gitignore`).

**Review findings breakdown:** 21 findings from two independent reviewers (Blind Hunter + Edge Case Hunter) — 12 patched (7 medium, 5 low; see Review Triage Log above for the itemized list), 2 deferred to `deferred-work.md` (pre-existing cross-package issues, not this story's to fix), 7 rejected (spec-sanctioned decisions or caller-misuse edge cases matching `pyforge-warden`'s own established design).

**Follow-up review recommendation:** `false` — all 12 patches are localized, additive hardening (extra construction-time validation, two new meta-tests, doc/test-naming fixes); none change any previously-tested behavior (full suite re-verified green after every patch), none touch the `<intent-contract>`, and none carry security/data/API-surface risk.

**Verification performed:** `PYTHONPATH=src python3 -m pytest tests -q` → 69/69 passed (56 from the initial implementation pass + 13 added during review triage). `python3 -m build --no-isolation --wheel` → clean wheel containing `data/report-schema.json`, empty `__init__.py`, and `entry_points.txt` with `doctor = pyforge.doctor.__main__:main` (verified during the implementation pass; unaffected by the review-triage patches). Installed-wheel console-script check (`doctor --version`/`--help`/no-args/`--bogus`) all exited within `{0, 2, 130}` with no tracebacks. The real loop verify command (`pixi run --frozen -e pyforge-doctor pyforge-doctor-test`) could not run to completion in this worktree — see the Verification note above and the environmental deferred-work entry.

**Residual risks:**
1. **High-likelihood orchestrator rollback risk (see `deferred-work.md`):** this worktree's path (239 bytes) exceeds the known ~173-byte `pixi-build-python` panic threshold (`project_bmad_loop_worktree_path_length_limit.md`, corroborated by a concurrent pyforge-herald session the same day). bmad-loop's own post-session `--frozen` verify re-check is expected to hit this same panic, which the orchestrator currently classifies as a *code* failure (not `env_fault`) and may roll this branch back to baseline a third time. **Recovery, if that happens: `git merge --ff-only efe4681d2e1fd4b70ce7e62335c486fbd6188c0d` onto the reset branch** — this commit's parent is the baseline, so it is a fast-forward, not a re-derivation. Do this before re-implementing anything.
2. Two deferred, cross-package hardening gaps logged in `deferred-work.md` (hatchling version-pin incoherence; the sole-ownership guard's blind spot for a bare `raise SystemExit`) — both pre-existing in the `pyforge-warden` exemplar this story mirrors, not introduced here.

## Spec Change Log

### 2026-07-25 — Re-derivation after worktree rollback lost the implementation
A prior dev-auto pass in this same run/worktree completed this story's full implementation and verification (all tasks, all AC, 35/35 substitute-verification tests passing per the note above) and advanced status to `in-review`, but the session crossed the per-session token-budget cap before committing (`ATTENTION` log: "weighted spend 4065507 crossed the 4000000 per-session cap"). The new package was entirely untracked, so the subsequent worktree rollback (`scm.rollback_on_failure: true`) discarded it with no trace beyond a dangling `git stash` object holding only a 39-line `pixi.toml` diff (the tracked-file half; `git stash` without `-u` never captured the untracked package tree). Confirmed via: no commit in this branch touches `pyforge-doctor` code; `src/shared/packages/pyforge-doctor/` absent from disk; `sprint-status.yaml` still lists this story `backlog`. Resetting `status` to `in-progress` and unchecking all Tasks & Acceptance boxes below so this pass re-derives the code faithfully from the (unchanged, still-correct) `<intent-contract>` and Code Map/Design Notes rather than trusting stale completion markers. KEEP: the package layout, module boundaries, and verification-substitute approach documented above matched the spec exactly on the lost pass — re-derive them as written, no redesign needed.
