---
title: 'Story 7.4: One severity, both sides'
type: 'feature'
created: '2026-08-13'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
final_revision: 'f5f4b1bea1aaa4fc6fb4dbaa7d6075c33dcd7137'
baseline_revision: 'aa2dcc756b60e3ec5b7685cbca44bfe579ecdce6'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-7-context.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `chain.py`'s two anonymous-entry finding kinds -- `ledger-entry-unidentified`
(tracked side) and `tier3-entry-unidentified` (Tier-3 side, Story 7.3, just landed) -- already
resolve to the same `DoctorStatus.FAIL` by construction (neither finding-building branch in
`_check_project_deferred_work` sets the `"warn"` key), but no test asserts this parity within one
run. CAP-2's closing AC requires proof, not an unasserted coincidence a future one-sided edit
(e.g. adding `"warn"` to only one branch) could silently break.

**Approach:** Add one test to the existing suite that plants an anonymous entry on the tracked
ledger AND on the Tier-3 file for the same project in a single `gather_deferred_work` run, then
asserts both resulting findings carry the same `.status`.

## Boundaries & Constraints

**Always:** Reuse the existing `_write_tier3`/`_write_tracked`/`_write_baseline` fixture helpers
in `test_sources_chain_deferred_work.py` unchanged -- no new fixture machinery. If the test
reveals an actual asymmetry (it should not -- both branches already omit `"warn"`), fix it with
the minimal change (never set `"warn"` on either), never restructure
`_check_project_deferred_work`'s finding-building shape. Every change under
`src/shared/packages/pyforge-doctor/**` is governed by `spec-pyforge-doctor`'s surface glob:
append a dated `.memlog.md` entry naming the changed paths and re-stamp `python
scripts/spec_surface_check.py --write-baseline --spec spec-pyforge-doctor` before landing (the
same S-13.7 convention every prior Epic 6/7 story on this Spec follows, most recently Story 7.3).

**Block If:** None -- this is a proof-only addition against already-landed, already-symmetric
behavior; no undecided design question remains.

**Never:** No mutation-proof test here (CAP-2's mutation-proof standard was already met on both
sides individually by earlier stories and Story 7.3 -- this story's own AC is parity, not
mutation). No change to `_anonymous()`/`_ENTRY_RE`/`_ANON_RE`. No new `Source` member or CLI verb.
No triage of which anonymous entries are worth keeping (epic-wide non-goal).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Anonymous entry on each side, same project | tracked ledger has one anonymous entry (no `## DW-<id>` heading); Tier-3 file (past the baseline count) has one anonymous entry too | `gather_deferred_work` returns one `ledger-entry-unidentified` FAIL and one `tier3-entry-unidentified` FAIL; both `.status is DoctorStatus.FAIL` | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` -- add one
  test that plants an anonymous entry via both `_write_tracked` and `_write_tier3` for the same
  project, calls `chain.gather_deferred_work` once, and asserts the two resulting findings'
  `.status` values are equal (and both `DoctorStatus.FAIL`) -- closes CAP-2's closing AC.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py:1485-1517` -- inspect
  only; both `_check_project_deferred_work` branches already omit `"warn"`, so no production
  change is expected. Touch only if the new test surfaces a real asymmetry.
- `_bmad-output/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md` -- append the dated
  Story 7.4 landing entry (spec-surface reconciliation), matching Story 7.3's own entry format.
- `scripts/.spec-surface-baseline.json` -- re-stamped by the write-baseline command below; not
  hand-edited.

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` -- add
  `test_ledger_and_tier3_anonymous_entries_carry_the_same_severity` (or an equally descriptive
  name) per the I/O matrix row -- proves CAP-2's closing AC with a real assertion, not an
  inference from reading the code.
- [x] `_bmad-output/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md` -- append a dated
  entry naming the changed paths -- required before `spec_surface_reconcile.py` will pass.
- [x] Run `python scripts/spec_surface_check.py --write-baseline --spec spec-pyforge-doctor` --
  re-stamps the governed-file baseline to match this story's diff.

**Acceptance Criteria:**
- Given a project with one anonymous entry in its tracked ledger and one anonymous entry in its
  Tier-3 file (positioned past the grandfather baseline count), when `gather_deferred_work` runs,
  then it produces one `ledger-entry-unidentified` finding and one `tier3-entry-unidentified`
  finding whose `.status` values are equal.
- Given the real repo state (Story 7.3 already landed, unchanged since), when `pixi run -e
  pyforge-doctor pyforge-doctor-test` runs, then the full suite passes with exactly one new test
  added.

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2 (high 0, medium 0, low 2)
- defer: 0
- reject: 7 (high 0, medium 0, low 7)
- addressed_findings:
  - `low` `patch` Both reviewers (Blind Hunter, Edge Case Hunter) independently found the new test's two `next(f for f in findings if f.check == ...)` lookups have no diagnostic guard -- a future regression that drops one finding kind entirely would fail with a bare `StopIteration` instead of a message naming the missing kind. Fixed: added `assert {"ledger-entry-unidentified", "tier3-entry-unidentified"} <= kinds, ...` before the `next()` calls.
  - `low` `patch` Blind Hunter found the `.memlog.md` entry's claim that `_gather_deferred_work`'s severity ternary is "the only place severity is decided for every finding kind in this module" overstates scope -- the identical ternary is independently duplicated in `_gather_dream_chain` (chain.py:654) and `_gather_spec_surface` (chain.py:1302), so the guarantee this story's test pins does not extend module-wide. Fixed: reworded the memlog note to scope the claim to the deferred-work check and name the two other duplicated sites.
- Rejected (7): `sprint-status.yaml`/`sprint-status-ledger.yaml` still show 7-3/7-4 as backlog despite landed code (Blind Hunter) -- investigated: the tracked ledger is updated by a separate "land doctor <story>" commit outside this workflow's scope (confirmed via `git log`; e.g. `4a19edecbd land doctor 7-2 ...`), the same pattern every prior 7.x story already follows -- `[low]`. Fixture text is hand-duplicated from two existing tests rather than factored into a shared constant (Blind Hunter) -- every existing test in this file already writes its own literal fixture strings with no shared constants; not a deviation this story introduced -- `[low]`. Proof-by-inspection rather than proof-by-mutation (Blind Hunter) -- the spec's own `<intent-contract>` Never clause explicitly excludes a mutation-proof test for this story ("this story's own AC is parity, not mutation") -- `[low]`. No uniqueness check on either `next()` match (both reviewers) -- matches the existing convention of every sibling test in this file (e.g. `test_anonymous_ledger_entry_reports_fail`), not a new gap -- `[low]`. No assertion on the planted entries' `.evidence["id"]` (Blind Hunter) -- already covered by pre-existing, unrelated tests (`test_anonymous_tier3_entries_beyond_baseline_are_reported_fail`, `test_anonymous_ledger_entry_reports_fail`); duplicating it here is outside this story's severity-parity AC -- `[low]`. Missing PR-gate `maintenance`-label reminder (Blind Hunter) -- true but not actionable inside this workflow, which commits locally and never opens a PR -- `[low]`. Redundant status assertions before the equality check (Blind Hunter) -- reviewer's own note calls it harmless, kept intentionally for a clearer divergence message -- `[low]`.

## Design Notes

**Why no production change is expected.** Both finding-building branches in
`_check_project_deferred_work` (chain.py:1485-1517) build their dict without a `"warn"` key, and
`_gather_deferred_work`'s single status-assignment line (`DoctorStatus.WARN if item.get("warn")
else DoctorStatus.FAIL`) is shared by every finding kind in this module -- there is exactly one
place severity is decided, and it already treats both kinds identically. This story's job is to
pin that fact with a test, the same way `test_sources_ledger.py::
test_both_warn_paths_carry_the_same_evidence_keys` already pins a parity claim across two
WARN-producing scenarios in a sibling source module.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks (if no CLI):**
- `git diff --stat` touches only the test file and `spec-pyforge-doctor/.memlog.md` (+ the
  re-stamped baseline JSON) -- no `chain.py` change unless the test surfaced a real asymmetry.

## Auto Run Result

Status: done

**Summary.** Added one test, `test_ledger_and_tier3_anonymous_entries_carry_the_same_severity`,
proving CAP-2's closing AC: the tracked-side `ledger-entry-unidentified` finding and the
Tier-3-side `tier3-entry-unidentified` finding (Story 7.3) already resolve to the identical
`DoctorStatus.FAIL` within one `gather_deferred_work` run. Investigation confirmed no production
asymmetry existed -- both finding-building branches in `_check_project_deferred_work` already
omit the `"warn"` key -- so `chain.py` was inspected but not changed, per the spec's own boundary.

**Files changed:**
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` -- added
  the parity test under a new "Story 7.4" section, with a diagnostic membership assertion added
  during review before the `next()` lookups.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md`
  -- dated Story 7.4 landing entry, S-13.7 spec-surface reconciliation, corrected during review to
  scope its severity-centralization claim to the deferred-work check rather than the whole module.
- `scripts/.spec-surface-baseline.json` -- re-stamped for `pyforge-doctor/spec-pyforge-doctor`
  (the working invocation needs the `pyforge-doctor/` project prefix; a bare `spec-pyforge-doctor`
  is rejected as unknown -- confirmed live against `spec_surface_check.py`'s own error output).

**Review findings breakdown:** 9 total (0 intent_gap, 0 bad_spec) -- 2 patch (both low: missing
diagnostic before two `next()` lookups that could fail with a bare `StopIteration`, and an
overstated "only place severity is decided" memlog claim that ignored two other duplicated
severity ternaries elsewhere in `chain.py`), 0 defer, 7 reject (stale sprint-status ledger fields
owned by a separate landing process, fixture-literal duplication matching the file's own existing
convention, a proof-by-inspection critique the spec's own Never clause explicitly excludes, a
missing uniqueness check matching every sibling test's convention, a missing id/evidence
assertion already covered by other pre-existing tests, a PR-gate reminder outside this
commit-only workflow's scope, and a self-acknowledged-harmless redundant assertion).

**Verification performed:** `pixi run -e pyforge-doctor pyforge-doctor-test` -- 853 passed, 1
skipped (852 -> 853, exactly one new test), re-verified after the review-pass patches.
`python scripts/spec_surface_reconcile.py` -- `OK: every tracked file governed or allowlisted; no
drift.` `git status --short` / `git diff --stat` -- only the three expected files changed; no
`chain.py` diff, confirming the "no production change expected" boundary held.

**Residual risks:** none identified beyond the rejected findings above, all judged non-blocking
for this story's narrow scope.
