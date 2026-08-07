---
title: 'Health scoring -- `pyforge.doctor.score.grade` (FR-10, AD-7)'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: [
  '{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md',
  '{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md',
  '{project-root}/_bmad-output/projects/pyforge-doctor/implementation-artifacts/spec-3-4-doctor-diagnose-target-prescribe-cli-wiring-json.md',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/prescribe.py',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py',
]
warnings: []
baseline_revision: 'HEAD at Story 4.1 start (after Epics 1-3 shipped)'
---

<intent-contract>

## Intent

**Problem:** Doctor gathers rich per-Finding data (Epic 1's `check` filter, Epic 2's `atlas` filter) but has no single at-a-glance verdict -- an operator has to re-read every individual Finding to judge whether a target is healthy.

**Approach:** A new `pyforge.doctor.score` module, pure over an already-gathered `list[Finding]` (AD-7, mirrors `prescribe.py`'s own AD-4 discipline exactly -- same meta-test technique). Groups Findings by their own `Source` tag (one "axis" per Source present -- deliberately NOT a hardcoded staleness/cve/abandonment list, so Story 4.3's `ADOPTION` source is graded automatically with zero changes here), computes a per-axis letter grade from ok/warn/fail counts, and composites to the WORST axis grade. An axis whose gather itself failed (the `sources/atlas.py` `_one_fail_finding` sentinel shape) grades `incomplete`, and poisons the whole composite to `incomplete` too. Wired into the CLI at the `diagnose` verb only (the "per dependency" framing fits a single target, not a fleet-wide `monitor`), always computed (cheap, pure), added to `DoctorReport` as new optional `grade`/`axis_scores` fields.

## Boundaries & Constraints

**Always:**
- `doctor.score` is 100% pure: zero subprocess/MCP imports, enforced by `test_score_pure_function.py`'s AST scan (mirrors `test_prescribe_pure_function.py`'s AD-4 guard verbatim, applied to `score.py`). Sanctioned import surface: `__future__`, `dataclasses`, `enum`, `collections.abc`, `..models`.
- Deterministic: no wall-clock read anywhere in `grade()`'s call path -- the same `list[Finding]` passed twice returns a byte-identical `GradeResult` (proven by `test_grade_is_deterministic_across_two_calls`).
- An axis whose gather degraded to `sources/atlas.py`'s `_one_fail_finding` sentinel (`check == "doctor.sources.atlas"`, `evidence == {}`) grades `Grade.INCOMPLETE`, never a computed letter standing in for missing data -- and poisons the WHOLE composite to `incomplete`.
- An empty `findings` sequence also grades `incomplete` (nothing to grade -- a default `A` would misrepresent "nothing was checked" as "everything passed").
- `--json` on `diagnose` includes both `grade` and `axis_scores` in the `DoctorReport` (FR-9 parity); the human-readable render shows the equivalent grade line + per-axis breakdown.

**Never:**
- Never a new gather path or a fourth scanning instrument -- `score.grade` consumes only Findings the caller already gathered.
- Never silently drop an incomplete axis from the composite to "just grade what we have."
- Never let a `warn`-only axis compute the same grade as an all-`ok` axis (majority-warn -> `C`, minority-warn -> `B`; majority-fail -> `F`, minority-fail -> `D`).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Empty findings | `grade([])` | `Grade.INCOMPLETE`, `axis_scores=()` | No error |
| All-OK single axis | 3 OK Findings, one Source | `Grade.A` | No error |
| Majority-WARN axis | 2/3 WARN | `Grade.C` | No error |
| Minority-WARN axis | 1/3 WARN | `Grade.B` | No error |
| Majority-FAIL axis | 2/3 FAIL | `Grade.F` | No error |
| Minority-FAIL axis | 1/3 FAIL | `Grade.D` | No error |
| Multi-axis, one worse than another | staleness=A, cve=F | Composite `F` (worst wins, never averaged) | No error |
| One axis's gather failed (sentinel Finding) | e.g. cve axis timed out, staleness succeeded | Composite `incomplete`; `axis_scores` still records the healthy axis's real grade, not discarded | No error |
| `diagnose --json` | Any run | `grade`/`axis_scores` present in the envelope | Schema-validated before stdout |
| `check`/`monitor --json` | Any run | Neither `grade` nor `axis_scores` key present (not wired for these verbs) | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/score.py` -- NEW. `Grade` (`StrEnum`), `AxisScore`, `GradeResult` dataclasses; `grade(findings)` pure function.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` -- EDIT. `DoctorReport` gains optional `grade: str | None`/`axis_scores: tuple[dict, ...] | None` fields (stored as already-serialized plain data, never `doctor.score`'s own types, to avoid a reverse import).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/report-schema.json` -- EDIT. Adds optional top-level `grade`/`axis_scores` properties + `#/$defs/axis_score`.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py` -- EDIT. `_run_diagnose` always computes `score.grade(findings)`; `_emit_json`/`_emit_text` gain an optional `grade_result` keyword.
- `src/shared/packages/pyforge-doctor/tests/meta/test_score_pure_function.py` -- NEW. AD-7 AST-scan guard, mirrors `test_prescribe_pure_function.py`.
- `src/shared/packages/pyforge-doctor/tests/unit/test_score.py` -- NEW. Full AC matrix.
- `src/shared/packages/pyforge-doctor/tests/unit/test_cli_diagnose.py` -- EDIT. `--json`/text grade-wiring tests.
- `src/shared/packages/pyforge-doctor/tests/unit/test_models.py` -- EDIT. `test_source_has_exactly_seven_members` renamed/extended to eight (Story 4.3's `ADOPTION` addition landed in the same pass; see that story's spec).

## Design Notes

**Why `grade`/`axis_scores` live in `models.py` as plain `str`/`dict`, not `doctor.score`'s own `Grade`/`AxisScore` types:** `models.py` is Doctor's frozen taxonomy module (AD-3) and must not import `doctor.score` (a reverse dependency onto a module that itself depends on `models`). Storing already-serialized data keeps `models.py`'s own import surface untouched.

**Why grading is wired into `diagnose` only, not `check`/`monitor`:** FR-10's own framing is "a composite health grade per DEPENDENCY" -- `diagnose --target` is the one verb scoped to a single target; `check`/`monitor` are pre-flight/fleet-wide and don't have an obvious "one grade" semantic without inventing one the AC doesn't ask for. `DoctorReport.grade`/`axis_scores` are deliberately NOT verb-coupled at the model-validation level (unlike `prescriptions`), so a future verb can carry a grade too without another `models.py` edit.

**Why composite = worst axis, not an average:** Simplicity First for a v1.x synthesis layer with no calibration data yet; a fleet is only as healthy as its worst-scoring axis -- averaging would let a bad `cve` axis hide behind a healthy `staleness` axis, misrepresenting risk.

**Why an axis's incomplete-gather detection reads `Finding.check == "doctor.sources.atlas"`, a duplicated literal from `sources/atlas.py`'s `_one_fail_finding` default:** AD-7 forbids `doctor.score` from importing `sources.atlas` (a subprocess/MCP-capable module) into a pure-function guard's own import surface. Mirrors `prescribe.py`'s own `_UNKNOWN_FEEDSTOCK_CHECK` duplicated-literal precedent for the identical reason. Known, documented scope limit: `checks.registry`'s own all-or-nothing degrade sentinel (`_gather_engines`) uses a DIFFERENT check-name shape and is NOT detected as "incomplete" by this module -- out of scope for this story (FR-10's AC3 example is specifically an atlas axis timeout).

## Verification

- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`

**Actual results (2026-08-07):** full suite green after all four Epic 4 stories landed together (see the sibling specs' own Verification sections for the running total). `test_score.py` (13 tests) + `test_score_pure_function.py` (16 tests) both pass in isolation.

## Review Triage Log

### 2026-08-07 -- Self-review pass (adversarial re-read of the diff)

- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0

Checked specifically for: exception handling (`grade()` has no exception surface at all -- pure dict/tuple/comprehension work over already-validated `Finding` objects); silent drops (every axis present in the input is represented in `axis_scores`, including incomplete ones -- proven by `test_one_axis_gather_failure_poisons_the_whole_composite` asserting the healthy axis's real grade is STILL recorded); docstring-vs-behavior drift (re-read `grade()`'s docstring against the implementation -- matches, including the "unreachable via `grade()` itself" note on `_axis_grade`'s `total == 0` branch); non-determinism (grepped the whole module for `datetime`/`time`/`random`/`uuid` -- none present; `sorted(by_source, key=...)` uses only the input's own `Source.value` strings, not insertion order, so `axis_scores` ordering is itself deterministic regardless of gather order); AD-7 pure-function guard (meta-test passes and positively proves the detector fires on synthetic subprocess/mcp imports, not just vacuously).

**Follow-up review recommendation: false** -- a genuinely new but narrow, well-isolated pure-function module with no external I/O surface to get wrong.

</intent-contract>
