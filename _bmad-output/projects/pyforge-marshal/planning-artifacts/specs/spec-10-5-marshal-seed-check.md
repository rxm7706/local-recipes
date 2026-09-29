---
title: 'marshal seed check'
type: 'feature'
created: '2026-08-21'
status: 'done'
baseline_revision: '7e0c58afb801927e17a3a6a4bfea7fca428bddd5'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: [oversized]
---

<intent-contract>

## Intent

**Problem:** `marshal seed check` (`cli/seed.py::run_check`) is a Story-7.1 stub that always
prints "not yet implemented" and exits 0, so nothing can detect when an adopted repo has drifted
from the seed model it installed.

**Approach:** Add `seed/verbs/check.py`, a pure, read-only module that composes the already-landed
detect primitives (`detect.inventory.classify`, `detect.hashes.check_managed_file`/
`check_managed_region`, `detect.optout.classify_regions`/`region_findings`,
`detect.inventory.legacy_findings`) plus a plan build (`plan.build.build_plan`, never
`write_plan`) into one findings list, adds the two currently-unemitted `FindingType` members this
story is the first call site for (`ARTIFACT_MISSING` for every `ArtifactState.ABSENT`
classification, `MODEL_BEHIND` when `state.model_version < manifest.model_version`), and wires
`cli/seed.py::run_check` to call it with `--strict`/`--json` flags, a severity-grouped
human-readable report, and `seed/errors.py`'s own exit-code taxonomy.

## Boundaries & Constraints

**Always:**
- Never call `seed.fs.write`/`replace_span`/`remove`, `plan.build.write_plan`, or any state-write
  path anywhere in the check code path — verified by a write-blocking fixture test.
- Never create `.marshal/` if it is absent.
- `read_state(repo_root)` returning `None` (never-adopted repo) is a normal case, not an error:
  treat every manifest artifact as absent, emit `ARTIFACT_MISSING` findings, do not crash.
- `read_state` raising `StateInvalid` (corrupt/unreadable `.marshal/seed-state.yml`) is caught,
  turned into one `Finding.new(Severity.HARD, FindingType.STATE_INVALID, ...)`, state treated as
  absent for the rest of the run, and the run continues — never a bare traceback.
- `--strict` fails on HARD **and** DRIFT findings; without it, only HARD findings fail.
- `--json` emits the full findings report in a stable, CI-annotatable shape (fixed field order).
- `model_version` is reported as model-behind / current / ahead by comparing
  `manifest.model_version` (bundled, via `model.manifest.load_manifest`) against
  `state.model_version` (repo's recorded value, `ModelVersion`'s existing ordering) when state
  exists; a never-adopted repo reports model-behind (nothing installed yet).
- Every new `Finding` is constructed via `Finding.new(...)` (never bare `Finding(...)`), so
  `remedy` resolves from `REMEDIES`.
- Exit codes come from `seed/errors.py`'s six-leaf taxonomy: 0 clean, `ConformanceFailure` (1) on
  a failing run, `UsageError` (2) on invalid CLI args, `StateInvalid` (5) only if it must
  propagate uncaught (it shouldn't, per the bullet above — reaching this is a bug). Do not add or
  reuse `core/verdict.py`'s MRS lattice for anything except the literal `0` success value.
- Human-readable report groups findings by severity (HARD / DRIFT / INFO) with per-group counts,
  matching `bmad_drift_check.py`'s report shape (severity-grouped, `path: message` lines).
- Completes in under 5 seconds on a `local-recipes`-sized repo — covered by a timed test.
- `seed/verbs/check.py` takes explicit inputs (repo root, manifest, state) and returns a plain
  data shape — no hidden I/O beyond what `read_state`/`classify`/`build_plan` already do — matching
  `preconditions.py`/`skips.py`'s existing pure-function verb-module convention.

**Block If:** none identified — this story only wires already-landed, already-tested detect/plan/
state primitives into a new read-only verb; nothing here requires a decision only a human can
make.

**Never:**
- No writes of any kind, no `.marshal/` creation, no `plan.json` persistence.
- No `--apply`/`--force`/`--yes`/`--skip` flags — those are mutating-verb concerns for
  10.6/10.7, out of scope here.
- No changes to `seed/verbs/preconditions.py` or `seed/verbs/skips.py` (those gate mutating verbs
  only).
- No new `core/verdict.py` exit-code literals.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Never-adopted repo | no `.marshal/seed-state.yml` | every manifest artifact reported `ARTIFACT_MISSING` (HARD); model reported model-behind | no traceback; exit 1 |
| Fully conformant adopted repo | state matches manifest; every managed file/region hash matches | zero findings | exit 0 |
| Hand-edited managed file | recorded `body_sha` mismatch | one HARD finding via `check_managed_file`, names the artifact | exit 1 |
| DRIFT-only findings, no `--strict` | e.g. a `managed-region-missing` DRIFT finding, no HARD findings | findings reported, run still exits 0 | none |
| DRIFT-only findings, `--strict` | same as above | same findings reported | exit 1 |
| Corrupt state file | `.marshal/seed-state.yml` fails schema validation | one `STATE_INVALID` HARD finding; rest of the check still runs against an absent-state view | no traceback; exit 1 |
| `--json` | any state above | JSON report via `Finding.to_json_dict()` per finding, stable field order, includes model-version status | none |
| Repo behind model version | `state.model_version < manifest.model_version` | `MODEL_BEHIND` finding present, message names both versions | reflected in exit code only if it's the sole HARD/DRIFT source per severity chosen for this finding |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/check.py` -- NEW: pure
  findings-composition module; the verb logic (`preconditions.py`/`skips.py`'s existing shape).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/seed.py` -- wire `run_check` to
  the new verb module; add `--strict` (`store_true`) and `--json` (`store_true`) flags to
  `check_parser`; catch `SeedError` leaves and return `exc.exit_code`.
- `.../seed/detect/findings.py` -- reuse `Finding`, `Finding.new`, `Severity`,
  `FindingType.ARTIFACT_MISSING` / `MODEL_BEHIND` / `STATE_INVALID` (defined with `REMEDIES`
  entries already; this story is their first real emission call site).
- `.../seed/detect/inventory.py` -- reuse `classify`, `legacy_findings`, `effective_never_write`.
- `.../seed/detect/hashes.py` -- reuse `check_managed_file`, `check_managed_region`.
- `.../seed/detect/optout.py` -- reuse `classify_regions`, `region_findings`.
- `.../seed/plan/build.py` -- reuse `build_plan` only (never `write_plan`).
- `.../seed/state/store.py` -- reuse `read_state` (returns `None` on absent; raises `StateInvalid`
  on corrupt).
- `.../seed/model/manifest.py`, `.../seed/model/version.py` -- reuse `load_manifest`,
  `ModelVersion` ordering, for the model-behind/current/ahead comparison.
- `.../seed/errors.py` -- reuse `ConformanceFailure`, `UsageError`, `StateInvalid` (no new leaves).
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_check.py` -- NEW.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_cli_seed.py` (or a new
  `test_seed_cli_seed_check.py` if no such file exists yet) -- NEW/extend: `--strict`/`--json`/
  exit-code CLI wiring.
- A timed test asserting the <5s NFR-P1 budget (new file under `tests/unit/` or
  `tests/conformance/`, following `pyforge-warden`'s `time.perf_counter()` pattern as precedent).
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_scaffold.py` -- landing-time edit
  (not foreseen by the original Code Map): Story 7.1's parametrized
  `test_seed_verb_stub_exits_zero_and_names_itself` covered all six seed verbs as stubs;
  `check` is real now, so it moves out of that parametrization into its own
  `test_seed_check_is_no_longer_a_stub` smoke test (dispatched through the real `main()`).

## Tasks & Acceptance

**Execution:**
- [x] `seed/verbs/check.py` -- implement a pure function (e.g. `run_check(repo_root, manifest,
  *, strict=False) -> CheckReport`) composing detect+plan findings, `ARTIFACT_MISSING` for every
  `ArtifactState.ABSENT` classification, `MODEL_BEHIND` from the version comparison, and a
  `STATE_INVALID` finding on a caught `StateInvalid` -- never writes anything.
- [x] `cli/seed.py` -- add `--strict`/`--json` flags to `check_parser`; `run_check(args)` calls
  the verb module, renders the severity-grouped text report or JSON, catches `SeedError` and
  returns `exc.exit_code`.
- [x] `tests/unit/test_seed_verbs_check.py` -- cover every row of the I/O matrix above, including
  the write-blocking fixture (assert no `.marshal/` created, no `fs.write`/`replace_span`/
  `remove` called) and the never-adopted-repo path.
- [x] A <5s timed test for NFR-P1 against a representative repo tree.
- [x] CLI-level test for `--strict`, `--json`, and each exit code (0/1/2).

**Acceptance Criteria:**
- Given an adopted, fully conformant repo, when `marshal seed check` runs, then it exits 0 and
  writes nothing to disk.
- Given a repo with a HARD finding, when `marshal seed check` runs (no `--strict`), then it exits
  1 and the finding is listed under a "HARD" group with a count.
- Given a repo with only DRIFT findings, when run without `--strict`, then it exits 0; when run
  with `--strict`, then it exits 1.
- Given a never-adopted repo, when `marshal seed check` runs, then it reports every manifest
  artifact as absent without raising, and creates no `.marshal/` directory.
- Given `--json`, when `marshal seed check` runs, then stdout is valid JSON containing the full
  findings list and the model-version status.
- Given the repo's `model_version` is behind the bundled manifest's, when `marshal seed check`
  runs, then a `MODEL_BEHIND` finding names both versions.

## Spec Change Log

## Review Triage Log

### 2026-08-21 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 2, medium 3, low 3)
- defer: 2: (high 0, medium 0, low 2)
- reject: 2
- addressed_findings:
  - `[high]` `[patch]` `cli/seed.py::run_check`'s `try`/`except` ended before the `_run_check_verb(...)` call, so a `SeedError` or any unguarded OS-level failure (missing `git`, broken packaged-resource load) escaped as a raw traceback. Widened the `try` to wrap the verb call and added a top-level `except Exception` backstop mapping to `InternalError` (exit 10).
  - `[high]` `[patch]` `--json` was ignored on the `UsageError`/`InternalError` error paths (plain `print(str(...))` regardless of the flag). Added `_print_seed_error`, honoring `--json` on every exit code.
  - `[medium]` `[patch]` The whole-file/region-body hash-check primitive was selected by `entry.artifact_class` (the manifest's CURRENT class) instead of `record.inserted_region_span` (the module's own documented invariant), risking a spurious HARD finding or a silently skipped check if an entry's class is ever reclassified across model versions. Re-keyed the selection on `record.inserted_region_span`, with an `entry.format is None` guard for the now-reclassified case.
  - `[medium]` `[patch]` The `managed_by_id` record lookup matched on `id` alone, never cross-checking `record.path == entry.path` -- the identical trap `detect.optout._claims_region` already documents and was fixed for (AD-55: id is stable, path can move). Added the path-equality gate, dropping a path-mismatched record to "no record" rather than comparing against stale data.
  - `[medium]` `[patch]` The NFR-P1 timed test's fixture (400 flat files, 20 flat sibling dirs, no `.gitignore`) was measurably cheaper to walk than a `local-recipes`-sized repo. Strengthened to a 3-level-deep, ~1200-file tree with a representative multi-pattern `.gitignore`.
  - `[low]` `[patch]` No test exercised a hand-edited hybrid-region body's HARD finding through `run_check`. Added `test_hand_edited_hybrid_region_body_is_one_hard_finding`.
  - `[low]` `[patch]` No test exercised the `STATE_INVALID` degrade path against a hybrid entry. Added `test_corrupt_state_file_with_a_present_hybrid_entry_degrades_cleanly`.
  - `[low]` `[patch]` `test_seed_check_is_no_longer_a_stub` only asserted `exit_code != 0`, not the specific code. Changed to assert `exit_code == ConformanceFailure.exit_code`.
  - `[low]` `[defer]` `verbs/check.py` calls `build_plan` for its `Action` set but never consults the `RepoFingerprint` it also computes, paying for two unused `git` subprocess calls on every check. Logged as `DW-FU-10-5`.
  - `[low]` `[defer]` `CheckReport.findings` has no single ordering rule across per-entry, legacy, and model-version findings; a `--json` consumer assuming entry-order would be surprised, though nothing in the spec promises that order. Logged as `DW-FU-10-5-2`.
  - `[reject]` "Spec's Approach wording easy to misread" -- verified independently correct (`ARTIFACT_MISSING`/`MODEL_BEHIND` predate this story), not a real finding.
  - `[reject]` "Repo behind model version" I/O-matrix row underspecified on severity -- exactly one sensible reading exists (DRIFT: informational drift, not a hard violation) and the implementation already follows it correctly; no actual defect.

Added two new regression tests proving the two `medium` hash-selection/path-cross-check fixes actually work: `test_stale_record_span_is_not_hashed_against_a_reclassified_entrys_whole_file` and `test_record_at_a_stale_path_is_never_hashed_against_the_current_path`. Added `test_json_flag_is_honored_on_the_usage_error_path`, `test_json_flag_is_honored_on_the_internal_error_path`, and `test_an_unanticipated_failure_from_the_verb_is_never_a_traceback` for the two `high` fixes.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: full `pyforge-marshal`
  suite green, including the new `check` tests.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- expected: green (cross-station dependency
  hygiene gate this project's policy requires on every change).

## Auto Run Result

**Summary:** Implemented `marshal seed check` (Story 10.5) -- a read-only conformance verb
composing Epic 9's detect/plan primitives into a `CheckReport`, wired through `cli/seed.py` with
`--strict`/`--json`/`--repo-root` flags and `seed/errors.py`'s six-leaf exit-code taxonomy. One
review pass (Blind Hunter + Edge Case Hunter) found and fixed two HIGH and three MEDIUM
correctness bugs before landing; see the Review Triage Log above for the full breakdown.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/check.py` (new) -- the pure
  verb logic.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/seed.py` (edited) -- CLI wiring,
  `--strict`/`--json`/`--repo-root` flags, exit-code mapping, the widened exception boundary.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_check.py` (new) -- verb-level
  unit tests, I/O matrix coverage, write-blocking + NFR-P1 timed tests.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_cli_seed_check.py` (new) -- CLI-level
  exit-code/flag tests.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_scaffold.py` (edited) -- `check`
  removed from the stub-verb parametrization, given its own smoke test.
- `_bmad-output/projects/pyforge-marshal/implementation-artifacts/deferred-work.md` (new) -- two
  low-severity defer entries (`DW-FU-10-5`, `DW-FU-10-5-2`).

**Review findings breakdown:** 8 patch (2 high, 3 medium, 3 low) -- all auto-fixed with
regression-test proof; 2 defer (both low) -- logged to the Tier-3 deferred-work ledger; 2 reject
(noise); 0 intent_gap; 0 bad_spec.

**Follow-up review recommendation:** `true` -- the two HIGH fixes changed the CLI's exception
boundary and error-path JSON rendering (both first-time-correct-on-review, not obviously so from
reading the original diff), and the two MEDIUM fixes changed core hash-comparison selection logic
in a way that only matters once Epic 11's migration machinery lands; that combination (behavior
change to error handling + a correctness fix whose test coverage is necessarily synthetic today)
is worth one more independent look.

**Verification performed:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 4894
passed, 9 deselected. `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- 84 passed. `ruff
check` clean on all five changed/new files (one pre-existing import-order issue and one
implicit-string-concatenation issue fixed as part of this pass).

**Residual risks:** the two deferred findings (`DW-FU-10-5`, `DW-FU-10-5-2`) are real but
low-severity and explicitly out of scope for this story. The hash-selection/path-cross-check fixes
are currently unreachable via any live CLI flow (no `adopt`/`init`/`update` verb exists yet to
populate `state.managed[]` for real), so their regression tests are necessarily synthetic
(hand-built `SeedState`/`ManagedArtifact` fixtures) rather than end-to-end proof; Epic 11's
migration work should re-verify this logic once real cross-version state exists.

## Status reconcile 2026-09-20

- frontmatter `status` `in-review` → `done` (ledger row `10-5-marshal-seed-check: done`).
