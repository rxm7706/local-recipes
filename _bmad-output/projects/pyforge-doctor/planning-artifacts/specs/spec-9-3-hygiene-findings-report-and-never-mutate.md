---
title: 'Story 9.3: Hygiene findings report and never mutate'
type: 'feature'
created: '2026-08-15'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
baseline_revision: '9675c3a27000ec2fbc5bff297f5f568d4f183dc9'
final_revision: '1f5260468e17565dd5d27940bcf28076e542fa80'
---

<intent-contract>

## Intent

**Problem:** Story 9.2's hygiene sweep (`sources/hygiene.py::gather`) already names a
concrete `evidence["path"]` for 4 of its 5 finding classes and is already read-only in
practice, but `_check_dead_test_scaffolding`'s `Finding` is the one class missing that
`path` key, and no test yet proves the sweep's own invocation never mutates the tree it
scans — only a static AST guard (`tests/meta/test_read_only_guard.py`) does.

**Approach:** Add the missing `path` to `_check_dead_test_scaffolding`'s evidence dict
(mirroring the other 4 classes' shape), then add a dynamic test that snapshots a fixture
tree's full file set and every file's bytes before and after `gather()` runs and asserts
byte-for-byte equality — the runtime proof CAP-9's own success criterion names explicitly,
complementing (not replacing) the existing static guard.

## Boundaries & Constraints

**Always:**
- Every `Finding` any of the 5 `HygieneFindingKind` classes emits carries an
  `evidence["path"]` string naming the concrete artifact judged — mirrors the 4 classes
  that already do this (`HOLLOW_SPRINT_STATUS`, `README_PLACEHOLDER`, `STALE_DREAM_STATUS`,
  `ORPHAN_FILE`); `DEAD_TEST_SCAFFOLDING` is the one gap this story closes.
- `_check_dead_test_scaffolding`'s path names `"tests"` when the `tests/` directory exists;
  when only a marker file (`pytest.ini`/`playwright.config.ts`) triggered the candidate with
  no `tests/` directory present, the path names that marker file instead.
- `gather()`'s own invocation performs zero filesystem writes — proven both statically
  (existing `test_read_only_guard.py` AST scan, already covers `hygiene.py`, unchanged by
  this story) and dynamically (new byte-for-byte fixture-tree diff test this story adds).

**Block If:** nothing identified — both gaps are mechanical and resolve from Story 9.1/9.2's
own module and this codebase's existing conventions.

**Never:** no `doctor check`/`monitor` CLI wiring (still out of scope, inherited from Story
9.2's own Never clause); no changes to `hygiene_definitions.py`'s five predicates (Story
9.1's frozen, already-reviewed contract); no `--fix`/archive/delete action or any new
mutation capability (CAP-9's own boundary — remediation stays a separate, human-reviewed
commit); no 6th finding class; no evidence key beyond `path` added to any of the 5 classes
(the 4 already-shipped shapes are frozen; don't touch them).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| All 5 classes, synthetic fixture | tmp fixture reproducing every class (existing all-classes fixture) | every one of the 5 findings' `evidence["path"]` is a non-empty string naming a real, existing repo-relative artifact | none |
| `gather()` invocation against that same fixture tree | same fixture, snapshotted before/after | the tree's full relpath set and every file's byte content are identical before and after `gather()` returns | none |
| dead-test-scaffolding, marker-file-only | station has `pytest.ini` at its root, no `tests/` directory | Finding's `evidence["path"] == "pytest.ini"` (not `"tests"`) | none |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/hygiene.py` -- MODIFIED.
  `_check_dead_test_scaffolding`'s `Finding` evidence gains `"path"`.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_hygiene.py` -- MODIFIED.
  Extend the all-5-classes fixture test to assert every finding's `evidence["path"]` is a
  non-empty string; add a new marker-file-only test for the `"pytest.ini"` path case; add a
  new test proving `gather()` never mutates the fixture tree it scans.

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/hygiene.py` --
  `_check_dead_test_scaffolding`: add `"path": "tests" if tests_dir.is_dir() else <matching
  marker filename>` to the finding's evidence dict -- closes the one gap in CAP-9's
  "every finding names the path" requirement.
- [x] `src/shared/packages/pyforge-doctor/tests/unit/test_sources_hygiene.py` -- extend
  `test_gather_emits_exactly_five_findings_for_a_synthetic_all_classes_fixture` with an
  assertion that every finding's `evidence["path"]` is a non-empty string -- mechanically
  enforces the "every finding names the path" requirement across all 5 classes, not just
  the 4 that already had it.
- [x] `src/shared/packages/pyforge-doctor/tests/unit/test_sources_hygiene.py` -- add
  `test_dead_test_scaffolding_path_names_the_marker_file_when_no_tests_dir_exists` -- a
  station with only `pytest.ini` at its root (no `tests/` dir) asserts
  `evidence["path"] == "pytest.ini"`.
- [x] `src/shared/packages/pyforge-doctor/tests/unit/test_sources_hygiene.py` -- add
  `test_gather_never_mutates_the_fixture_tree_it_scans` -- build the all-5-classes fixture,
  snapshot every file's relpath and content before calling `gather()`, call it, re-snapshot
  after, assert both the relpath set and every file's bytes are unchanged -- the dynamic,
  byte-for-byte proof CAP-9's success criterion names explicitly ("the sweep's own
  invocation never mutates a file"), independent of and complementary to the existing
  static AST guard.

**Acceptance Criteria:**
- Given any of the 5 hygiene finding classes, when `gather()` emits an instance, then its
  `evidence["path"]` names a concrete artifact and its `message` explains why that artifact
  was judged an instance of that class — CAP-9's "names the path and the evidence for why"
  wording, now uniformly satisfied across all 5 classes for the first time.
- Given the sweep's own invocation, when it runs against a fixture tree, then no file in
  that tree is created, deleted, or modified — proven by both the pre-existing static guard
  and this story's new dynamic test.
- Given the full `pyforge-doctor` test suite, when it runs after this change, then it passes
  with no regressions (existing evidence-dict assertions on other finding classes are
  unaffected by the additive `"path"` key on `DEAD_TEST_SCAFFOLDING`).

## Spec Change Log

(none yet)

## Review Triage Log

### 2026-08-15 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5 (high 0, medium 1, low 4)
- defer: 1 (high 0, medium 1, low 0)
- reject: 5 (high 0, medium 0, low 5)
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter found the marker-file-only branch's `Finding.message` was a single hardcoded string ("tests/ scaffolding holds no real test_*.py file") reused for both branches, directly contradicting the `evidence["path"]` sitting next to it when only a marker file (e.g. `pytest.ini`) fired with no `tests/` dir present — violating the story's own AC that the message must explain why the path's artifact was judged an instance. Fixed: the message now branches per case (`"tests/ scaffolding holds no real test_*.py file"` vs `"<marker> exists with no real tests/ tree behind it"`).
  - `[low]` `[patch]` Both reviewers independently found `_check_dead_test_scaffolding`'s `else` branch re-derived the matched marker filename via `next(name for name in _TEST_MARKER_FILES if (project_dir / name).is_file())`, redundantly re-scanning what `has_marker` already scanned and risking an uncaught `StopIteration` under a same-pass filesystem state change. Fixed: marker matches are now computed once into `matched_markers` and reused for both the has-a-candidate guard and the evidence path.
  - `[low]` `[patch]` Blind Hunter flagged that the new `path = "tests"` local variable shared its name with the pre-existing `for path in sorted(tests_dir.rglob("*"))` comprehension two lines above — safe (Python 3 comprehension scoping) but a readability trap. Fixed: renamed the new variable to `evidence_path`.
  - `[low]` `[patch]` Blind Hunter found the all-classes fixture test only asserted `evidence["path"]` was a non-empty string, never checking the exact `"tests"` value the story's own I/O matrix and Boundaries explicitly commit to for the common tests_dir-exists case. Fixed: added an exact-value assertion for the `DEAD_TEST_SCAFFOLDING` finding's path.
  - `[low]` `[patch]` Blind Hunter found ~30 lines of near-verbatim fixture-construction duplicated between the all-classes reproduction test and the new never-mutates test. Fixed: extracted a shared `_seed_all_classes_fixture` helper, used by both.

### 2026-08-15 — Review pass (post-recovery)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 3 (high 0, medium 0, low 3)
- addressed_findings:
  - none

This pass re-ran Blind Hunter and Edge Case Hunter (fresh, no shared context) against the
same diff after this worktree's branch was found reset behind a completed, already-reviewed
commit for this story (git history lost by an orchestrator baseline bug, unrelated to this
story's content) and recovered losslessly via `git merge --ff-only` from the run's
`attempt-preserve/20260815-112702-c77e-1f526046` branch — see Design Notes. Both reviewers
independently re-surfaced two items already triaged `reject` in the prior pass above (the
both-markers-present tie-break, and the mutation test's file-content-only vs. metadata
scope), each re-verified against this story's own intent-contract wording rather than
blindly inherited: the "Always" bullet says "the path names *that* marker file" (singular,
no multi-match tie-break implied), and the I/O matrix's mutation-proof scope is explicitly
"the tree's full relpath set and every file's byte content" — metadata/directories were
never in scope. Both confirmed still out-of-scope. One new low-severity observation
(Blind Hunter): `evidence["file_count"]` is hardcoded `0` in the marker-only branch, which
is pre-existing behavior unchanged by this story's diff (not caused by this story) and
already disambiguated by the `evidence["path"]` field this story adds — rejected as
non-actionable rather than deferred.

## Design Notes

**Two independent proofs for "never mutates," not one.** `test_read_only_guard.py` is a
static AST scan proving no write *call site* exists anywhere in `pyforge.doctor` (including
`hygiene.py`, already unexempted). CAP-9's own success criterion asks for something a static
scan cannot show — that a real *invocation* leaves a real tree unchanged — so this story adds
that as a separate, dynamic test rather than treating the static guard as sufficient on its
own.

**Story 9.2's commits landed on this branch via fast-forward merge** (`9a2c3f6100`,
`9675c3a270`, from the sibling worktree's `bmad-loop/.../9-2-the-sweep-runs-against-all-eight-stations`
branch) to satisfy this story's `Deps: S-9.2` — Story 9.2's own landing to `main` is
independently pending (deferred on an unrelated spec-surface governance check, not a code
defect), so this diff's baseline already includes 9.2's two commits.

**Git-history recovery (2026-08-15, post-review).** A later `bmad-dev-auto` invocation for
this same story found this worktree's branch reset back to `51262819e7` — before all three
of the commits above — with the code entirely missing, matching the known
`stuck-orchestrator-baseline` bug pattern (spec artifacts survive outside git behind the
shared `implementation-artifacts` symlink; only the git-tracked commits were lost). The
completed, already-reviewed commit chain was intact on the run's own
`attempt-preserve/20260815-112702-c77e-1f526046` safety-net branch. `git merge-base
--is-ancestor <reset-HEAD> <preserve-tip>` confirmed the reset was a pure rewind (no
divergence), so `git merge --ff-only attempt-preserve/20260815-112702-c77e-1f526046`
recovered all three commits losslessly, byte-for-byte identical to what was originally
reviewed — no re-implementation. See team memory
`project_stuck_orchestrator_baseline_recovery_confirmed.md` for the prior confirmed instance
of this exact recovery.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

**Summary.** Closed the one remaining gap in CAP-9 ("hygiene findings are reported, never
auto-applied"): `_check_dead_test_scaffolding` was the only one of the 5 hygiene finding
classes whose `Finding.evidence` lacked a `"path"` key, and no test yet proved `gather()`'s
own invocation never mutates the tree it scans (only a static AST guard did). Added the
missing `path` (branching on whether a real `tests/` dir exists or only a marker file did),
and a new dynamic test that snapshots a fixture tree's full relpath set and every file's raw
bytes before/after `gather()` runs and asserts byte-for-byte equality.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/hygiene.py` --
  `_check_dead_test_scaffolding` now computes `matched_markers` once (removing a redundant
  re-scan and a `StopIteration` risk found in review), sets `evidence["path"]` to `"tests"`
  or the matching marker filename, and its `message` now correctly describes whichever
  branch actually fired instead of a message hardcoded to the `tests/`-exists case.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_hygiene.py` -- extended the
  all-classes fixture test with a path-presence assertion (all 5 classes) and an exact-value
  assertion (`"tests"` for `DEAD_TEST_SCAFFOLDING`); added
  `test_dead_test_scaffolding_path_names_the_marker_file_when_no_tests_dir_exists`; added
  `test_gather_never_mutates_the_fixture_tree_it_scans` (the dynamic byte-for-byte proof);
  extracted the shared `_seed_all_classes_fixture` helper (review-driven, removed ~30 lines
  of duplication between the two fixture-building tests).

**Review findings breakdown:** patch 5 (medium 1, low 4 -- all applied, see Review Triage
Log above), defer 1 (medium 1 -- `DW-FU-9-3`, a pre-existing Story-9.2-era inconsistency in
which base directory each finding class's `evidence["path"]` is relative to, surfaced
incidentally by this story giving the 5th class a path too), reject 5 (low 5 -- an untested
both-markers-present combination, happy-path-only mutation-test coverage, a
directory-vs-file path-shape observation, "the mutation test proves an invariant that
already trivially held" via the static guard, and file-content-only vs metadata comparison
in the mutation test -- all either out of this story's explicit scope or non-defects).

**Follow-up review recommendation:** `false` -- the review-driven changes are localized to
one function and its tests (a message/evidence consistency fix, a redundant-scan/robustness
fix, a rename, and two test additions), fully covered by the existing and extended test
suite, with no security/data/API/behavior-surface impact beyond the finding's own evidence
shape.

**Verification performed:** `pixi run -e pyforge-doctor pyforge-doctor-test` -- 950 passed,
2 skipped (both pre-existing and unrelated: a missing `playwright` module, and a gitignored
Tier-3 artifact absent in this worktree), 0 failed -- run twice (once after initial
implementation, once after the review-driven patches) with identical results. Independently
re-verified by the orchestrating session (not just the implementation subagent) before and
after the patch pass.

**Residual risks:** `DW-FU-9-3` (deferred above) -- `evidence["path"]` is relative to
`project_dir` for 4 of the 5 finding classes and relative to the repo root for
`stale_dream_status`; a future consumer resolving paths against one fixed base directory
will mis-resolve that one class until reconciled.

**Post-recovery review pass (2026-08-15).** This worktree's branch was found reset behind
the completed work (git history lost to the `stuck-orchestrator-baseline` bug, unrelated to
this story's content) and recovered losslessly via `git merge --ff-only` from the run's
`attempt-preserve/20260815-112702-c77e-1f526046` branch -- see Design Notes. Per the
workflow's routing for a rediscovered `status: done` spec, a fresh independent review pass
re-ran Blind Hunter and Edge Case Hunter against the identical, byte-for-byte-recovered diff.
Both reviewers converged on the same two items already rejected in the prior pass (re-verified
against the intent-contract's own wording, not blindly inherited) plus one new low-severity,
pre-existing, non-actionable observation -- all three rejected, zero patches, zero defers. No
code changes this pass; `final_revision` is unchanged. Test suite independently re-verified
post-recovery: `pixi run -e pyforge-doctor pyforge-doctor-test` -- 949 passed, 2 skipped
(same pre-existing/unrelated skips), 1 failed (`test_check_speed_budget.py`'s 5s CLI-latency
budget, exceeded under this session's heavy concurrent-worktree CPU load -- confirmed flaky
and unrelated to this story: 3/3 passes in isolation, and `doctor check` does not invoke the
hygiene source at all per this story's own Never clause).
