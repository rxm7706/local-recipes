---
title: 'Story 8.4: The baseline re-stamps so a second run is a no-op'
type: 'feature'
created: '2026-08-15'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
baseline_revision: '058228f5d0b9e27c60705113c89a053feaa24d70'
final_revision: 'b70a02bae1'
---

<intent-contract>

## Intent

**Problem:** Story 8.3's `--fix` promotes orphans into the tracked ledger
but never touches `scripts/.deferred-work-baseline.json` (CAP-3's
grandfather mechanism, Story 7.2). Tier-3 itself is deliberately never
mutated, so `tier3-entry-unidentified` (`_anonymous(t3_path)[count:]`,
purely positional against the stamped `count`) stays exactly as red after a
successful `--fix` run as before it -- the promoted entries now have a
tracked twin (clearing `tier3-only-deferral`), but the baseline has no idea
anything changed.

**Approach:** After `deferred_work_promote.py --fix` successfully writes a
project's promotions, re-stamp that SAME project's baseline count to its
current `_anonymous()` count -- reusing `scripts/deferred_work_baseline.py`'s
own already-tested `--write-baseline --project SLUG` scoped-stamp logic
(import its reusable pieces; both are plain stdlib-only `scripts/*.py`
files, no install-free tension). Since Tier-3 is untouched, "current count"
after a successful promotion equals the total anonymous-entry count for
that project, so the position-based slice `[count:]` returns empty --
`tier3-entry-unidentified` clears for that project. A project where `--fix`
found nothing to promote, or aborted on a collision, gets its baseline left
untouched -- nothing was written, nothing should be re-grandfathered.

## Boundaries & Constraints

**Always:** Re-stamp ONLY projects where `--fix` actually wrote a
promotion in THIS run (`promoted_count > 0` and the ledger write
succeeded) -- reuse `deferred_work_baseline.py`'s `_live_state()`/scoped
`--project` merge-write logic (import, don't duplicate a second copy of
already-tested stamping code) rather than reimplementing baseline JSON
merge semantics. The re-stamp write is a SEPARATE file write from the
ledger write (two different files can't share one atomic operation) but
happens in the same script run, immediately after that project's ledger
write succeeds. A second `--fix` invocation against the SAME (untouched)
Tier-3 content must be a true no-op: 0 new ledger writes (already
guaranteed by Story 8.3's own duplicate-summary collision guard -- the
re-classified orphans' summaries now match their own just-promoted tracked
twins and the batch correctly aborts) and 0 baseline writes (nothing to
promote this time, so the "only re-stamp on a successful write" rule keeps
the baseline untouched too).

**Block If:** the baseline re-stamp write fails after the ledger write
already succeeded -- this must be reported as a distinct, visible partial-
outcome warning (promotion succeeded, baseline re-stamp did not, naming the
manual fallback command), never silently swallowed and never used to roll
back or invalidate the already-successful ledger write.

**Never:** touch a project's baseline count when `--fix` promoted nothing
for it this run (no orphans found, or the batch aborted on a collision) --
that would silently re-grandfather a genuinely still-open backlog, hiding
real findings. Reimplement `deferred_work_baseline.py`'s JSON merge-write
logic a second time -- import its reusable pieces instead. Change
`_anonymous()`'s own counting logic (still the older, less-precise
heuristic Story 8.1 deliberately left untouched) -- this story only stamps
whatever count it currently reports, correctly or not; fixing that
heuristic is a separate, unclaimed future concern.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Successful promotion | `--fix` promotes N>0 orphans for a project | that project's baseline count re-stamped to its current `_anonymous()` count; `tier3-entry-unidentified` clears for it | none |
| No orphans found | `--fix` finds 0 orphans for a project | baseline untouched for that project | none |
| Collision abort | `--fix` aborts a project's batch (duplicate id/summary) | baseline untouched for that project | non-zero exit, as today |
| Immediate re-run | `--fix` run a second time against the same Tier-3 content | 0 new ledger writes (existing collision guard fires), 0 baseline writes (nothing newly promoted) | exit reflects the no-op, not an error |
| Baseline write fails after ledger write succeeds | e.g. permission error on `scripts/.deferred-work-baseline.json` | promotion outcome still reported as success; a separate, clearly-labeled baseline-restamp-failed warning names the manual fallback | non-fatal to the run |
| Multi-project run | some projects promote, others don't | only the projects that actually promoted get their baseline touched | independent per project, matching Story 8.3's own isolation |

</intent-contract>

## Code Map

- `scripts/deferred_work_promote.py` -- import `deferred_work_baseline`'s reusable stamping pieces; after a project's successful ledger write, call the scoped re-stamp for that project slug.
- `scripts/deferred_work_baseline.py` -- if `_live_state()`/the scoped-merge-write logic isn't already cleanly reusable as an importable function (it currently lives inline in `main()`), factor out the minimum needed (e.g. a `stamp_project(slug) -> None` or equivalent) without changing its own CLI behavior.
- `tests/scripts/test_deferred_work_promote.py` -- new tests for the re-stamp-on-success / no-restamp-on-no-op-or-abort behavior and the immediate-second-run-is-a-no-op property.

## Tasks & Acceptance

**Execution:**
- [x] `scripts/deferred_work_baseline.py` -- factor out a reusable function performing the scoped `--project SLUG` stamp (read current `_anonymous()` count, merge into the existing baseline JSON, write) without changing the script's own CLI/output; the CLI's `--write-baseline --project` path calls the same function.
- [x] `scripts/deferred_work_promote.py` -- import that function; after each project's ledger write succeeds (`promoted_count > 0`), call it for that project slug. Wrap the re-stamp call so a failure there reports a distinct warning and does not affect the already-reported promotion success.
- [x] `tests/scripts/test_deferred_work_promote.py` -- add: a successful promotion re-stamps the baseline to the project's current `_anonymous()` count and `tier3-entry-unidentified` (verified via `chain.py`'s own `_anonymous(t3_path)[new_count:]`) is empty afterward; a no-orphans project's baseline is untouched (byte-identical); a collision-aborted project's baseline is untouched; running `--fix` twice in a row against the same fixture produces 0 ledger writes and 0 baseline writes on the second run; a simulated baseline-write failure (e.g. a read-only baseline file) still reports the ledger promotion as successful with a separate, clearly-labeled warning.

**Acceptance Criteria:**
- Given a project with real orphans and no collisions, when `--fix` runs, then its baseline count updates to match its current `_anonymous()` count and `tier3-entry-unidentified` reports zero findings for that project immediately after.
- Given the same fixture, when `--fix` runs a second time immediately after, then it makes zero writes to either the tracked ledger or the baseline file for that project.
- Given a project whose batch aborts on a collision, when `--fix` runs, then its baseline file is byte-identical before and after -- no findings are silently hidden for backlog that was never actually promoted.

## Spec Change Log

(none yet)

## Review Triage Log

### 2026-08-15 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 13 (high 3, medium 5, low 5)
- defer: 1 (high 1)
- reject: 1 (low 1)
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter found `stamp_projects()` writes the baseline via plain `write_text`, while this same script's ledger write uses `tempfile.mkstemp`+`os.replace` specifically to avoid crash-mid-write corruption of durable content -- and Story 8.4 makes this exact non-atomic write happen AUTOMATICALLY on every successful `--fix` (not just a rare manual CLI call). Compounded by `chain.py::_load_deferred_work_baseline` treating the file as one atomic blob -- a single corrupted write disables the Tier-3-anonymous check for ALL 8 projects, not just the one being stamped. Fixed: `stamp_projects()` now writes via the same `tempfile`+`os.replace` pattern as the ledger.
  - `[high]` `[patch]` Blind Hunter found a failed baseline restamp never changes the process exit code -- `_Outcome.status` stays `"promoted"` and `main()` only sets a non-zero exit on `"aborted"`, so a caller checking only exit code (CI, cron) never learns the manual fallback is needed, silently breaking the "next --fix is a no-op" guarantee for that project. Fixed: `main()`'s overall exit code is now non-zero whenever ANY project had a baseline-restamp warning, even if every ledger write succeeded; each project's own "promoted" status text is unchanged.
  - `[high]` `[patch]` Edge Case Hunter found, live-verified, that `deferred_work_promote.py` now hard-imports `deferred_work_baseline` at module load -- if that sibling file is ever missing/unimportable (e.g. a script copied standalone without its sibling), even a bare invocation or `--help` crashes with a raw traceback instead of the intended usage text. Fixed: the import is wrapped, degrading gracefully with a clear message if the sibling module can't be loaded, rather than crashing before argument parsing even runs.
  - `[medium]` `[patch]` Edge Case Hunter found `stamp_projects()`'s read-merge-write has no re-check against concurrent mutation, the same race class Story 8.3's own review found and fixed for the ledger write (a re-read-and-compare guard immediately before the write, narrowing rather than eliminating the window -- no OS-level locking precedent exists anywhere in this repo). Fixed: applied the identical guard to `stamp_projects()`.
  - `[medium]` `[patch]` Blind Hunter found that in a sequential multi-project run, a pre-existing corrupted baseline (not caused by this run) surfaces as a misleading "baseline re-stamp failed" warning on whichever project's stamp call happens to read it first, indistinguishable from a failure THAT project's own write caused. Fixed: the warning message now names whether the failure came from reading the existing baseline vs. writing the update, so an operator isn't misled about which project's action is actually implicated.
  - `[medium]` `[patch]` Edge Case Hunter found `main()`'s CLI path only catches `ValueError` around the (now-refactored) stamp call, so an `OSError`/`PermissionError`/`IsADirectoryError` crashes with an unhandled traceback instead of the intended graceful exit-2 path. Fixed: widened to catch the same exception classes `_promote_project`'s own per-project boundary already handles.
  - `[medium]` `[patch]` Blind Hunter found `stamp_projects()` triggers a full fleet re-scan (`_live_state()` parses every project's Tier-3 file) even though only one named slug's count is used -- and this now runs once per successfully-promoted project in a single `--fix` invocation, multiplying an expensive scan (marshal's Tier-3 file alone carries 200+ entries) by N. Fixed: added a targeted single-project anonymous-count helper `stamp_projects` uses internally, reserving the full `_live_state()` scan for the unknown-project validation path (which genuinely needs to see every known project) and the bare CLI all-projects path (unchanged).
  - `[medium]` `[patch]` Blind Hunter found no test asserts the actual CONTENT of a multi-project single-invocation restamp (two sequential read-merge-write cycles against the shared file, exactly what a real unscoped `--fix` run does) -- only that a later run is idempotent. Fixed: added an explicit assertion that both projects' counts are correct after the first run.
  - `[low]` `[patch]` Blind Hunter found the refactor's "byte-identical" docstring claim is empirically false for one edge case (unknown-project name against an already-corrupted baseline) -- reproduced: the old code crashed with an uncaught `JSONDecodeError`, the new code cleanly reports "unknown project" and exits 2. An improvement, but the docstring overclaims. Fixed: docstring now says "behavior-preserving for known-good inputs, and incidentally more robust against a pre-existing corrupted baseline on this one validation-order edge case" rather than "byte-identical."
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter (independently) found stale help/usage text in both scripts: `deferred_work_baseline.py`'s bare-invocation message still says "No detector reads this file yet" (false since Story 7.3) and now also fails to mention this file gets written automatically by `--fix`; `deferred_work_promote.py`'s own usage text still says it "never" touches the grandfather baseline. Fixed both, plus the existing test that had locked in the stale claim as a passing assertion.
  - `[low]` `[patch]` Edge Case Hunter found `stamp_projects()` called with an empty slugs iterable would still perform a needless read/merge/write (or create an empty baseline file where none existed) -- no current caller does this, but cheap to guard. Fixed: early-returns `{}` for an empty input.
  - `[low]` `[patch]` Blind Hunter found `stamp_projects()`'s "known project" set now comes from a second, separate `_live_state()`-derived call rather than one shared with `main()`'s bare path -- functionally fine today but rests on an undocumented "no concurrent mutation of `_bmad-output/projects/` mid-run" assumption the bare path's own adjacent comment already names explicitly. Fixed: added the same comment near the new call site.
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter (independently) found the simulated-permission-failure test (`chmod(0o555)`) is not portable to a root-run CI/container environment, where chmod doesn't block writes -- would silently fail to exercise the path it claims to cover. Fixed: added an `os.geteuid() == 0` skip guard, matching the reviewers' own suggested fix.
  - `[high]` `[defer]` Edge Case Hunter found, live-verified, a real design flaw in Story 8.3's own collision-detection (pre-existing, not caused by this story's diff, surfaced incidentally by 8.4's lifecycle testing): once a project has been promoted once, any genuinely NEW orphan added to Tier-3 later gets permanently blocked, because the whole-batch-abort guard fires on the OLD, already-promoted entry's now-expected collision against its own tracked twin -- there is currently no way to promote just the new entries while skipping the old, already-handled one. Logged as a deferred-work entry (see `DW-FU-8-4` minted below) rather than fixed here -- a proper fix needs a redesign of the batch-abort semantics into a per-entry skip/promote model, which is a real, separate future story's scope, not a patch to this one.
  - `[low]` `[reject]` Blind Hunter found `stamp_projects()`/`_anonymous()` inherits the already-known, already-logged `_anonymous()` swallow-bug (`DW-FU-8-1`, filed during Story 8.1), meaning "promoted" and "grandfathered" are now provably divergent definitions for a quantified slice of the real fleet (marshal's 9 affected headers). Rejected as a NEW finding: this is the same already-tracked defect's downstream consequence, and both Story 8.1's and this story's own Boundaries explicitly forbid touching `_anonymous()`'s counting logic. Noted as a residual risk pointing back to `DW-FU-8-1`, not re-logged as a duplicate entry.

## Design Notes

This closes the loop CAP-6/CAP-7 together describe as one operator-facing
guarantee ("`--fix` fully clears the fleet's findings, and running it twice
is a no-op"), split across Stories 8.3 (the write) and 8.4 (the baseline)
per the epic's own sequencing. Story 8.3's spec already corrected the
epics.md claim that `--fix` alone clears `tier3-entry-unidentified` --
this story is where that correction resolves: the combination of both
stories is what the fleet-level success signal actually needs.

Reusing `deferred_work_baseline.py`'s own scoped-stamp logic (rather than a
third implementation of "read anonymous count, merge into baseline JSON")
matters for a subtle correctness reason: that logic already handles the
MERGE-never-rebuild discipline (a worktree that can't see every project's
Tier-3 scratch must never silently drop an already-stamped, currently-
invisible project's baseline entry) -- a bug class its own module docstring
records being reproduced live during that story's own review. Reimplementing
it here would risk reintroducing exactly that.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Summary.** Wired `scripts/deferred_work_baseline.py`'s scoped `--project` stamping into
`scripts/deferred_work_promote.py --fix`'s successful-promotion path, factoring the stamp
logic into a reusable `stamp_projects()` so a second, immediate `--fix` run against unchanged
Tier-3 content is a true no-op (0 writes to either the tracked ledger or the baseline file).
Epic 8 (doctor's legacy deferred-work backlog) is now complete: Story 8.1's classifier, 8.2's
minting, 8.3's promotion, and this story's baseline lockstep together deliver the fleet-level
guarantee CAP-6/CAP-7 describe.

Adversarial review found the refactor's own "byte-identical" claim was empirically false in
one edge case (an improvement, not a regression -- the old code crashed on a corrupted
baseline plus an unknown project name; the new code cleanly reports the unknown project) and
three real HIGH-severity robustness gaps: the baseline write itself was non-atomic while the
SAME script's ledger write already used a safer pattern, now running automatically on every
successful `--fix` instead of a rare manual call; a failed baseline restamp never affected the
process exit code, so an automated caller checking only exit status would never learn the
manual fallback was needed; and a hard, unconditional import of the sibling module meant even
a bare `--help` invocation would crash if that sibling were ever missing. All three fixed and
re-verified live (atomic write with no stray temp files; exit code now reflects a restamp
warning even when the ledger write succeeded; graceful degradation confirmed by literally
removing the sibling module and re-running). Five medium and five low fixes closed the
remaining gaps (a concurrent-write race guard matching Story 8.3's own precedent, clearer
read-vs-write failure messaging, broader exception handling, a wasteful full-fleet re-scan
narrowed to the target project, a missing content-correctness test, stale docs/help text, and
test portability).

**Real, pre-existing design flaw discovered and deferred, not fixed here.** Edge Case Hunter
live-verified that Story 8.3's own whole-batch-abort collision guard (already merged) means
once a project has been promoted once, any genuinely NEW orphan added later is permanently
blocked -- the old, already-promoted entry's now-expected collision against its own tracked
twin aborts the whole batch, with no way to promote just the new entries. Confirmed live: all
8 real fleet projects currently have at least one such collision and would abort a bare
`--fix` today. Logged as `DW-FU-8-4` rather than fixed here -- this needs a per-entry
skip/promote redesign, a real future story's scope, not a patch to this one.

**Files changed:**
- `scripts/deferred_work_baseline.py` -- `stamp_projects()` rewritten (atomic write, race guard, targeted per-project lookup, distinct failure messaging, empty-input guard); `main()` widened exception handling; corrected docstring/help text.
- `scripts/deferred_work_promote.py` -- graceful sibling-import degradation; `_Outcome` gained a `baseline_warning` flag feeding `main()`'s exit code; corrected usage text.
- `tests/scripts/test_deferred_work_promote.py` -- content-correctness assertion added; permission test made root-safe.
- `tests/scripts/test_deferred_work_baseline.py` -- stale-text test updated to match corrected wording.
- `_bmad-output/projects/pyforge-doctor/implementation-artifacts/deferred-work.md` -- 1 new entry (`DW-FU-8-4`, the batch-abort design flaw, out of scope for this story).

**Review findings breakdown** (Blind Hunter + Edge Case Hunter, deduplicated): 0 intent_gap, 0 bad_spec, 13 patch (3 high / 5 medium / 5 low, all applied and re-verified), 1 defer (high -- a real, live-confirmed pre-existing flaw in already-merged Story 8.3 code), 1 reject (an already-tracked, explicitly out-of-scope `_anonymous()` defect, `DW-FU-8-1`).

**Follow-up review recommendation:** `true`. Three HIGH findings on new code (one an actual production-crash bug, live-verified) plus a real, high-severity pre-existing defect uncovered in already-shipped Story 8.3 code -- this combination, on a mutation script writing durable content, clears the bar for an independent follow-up pass, and the newly-filed `DW-FU-8-4` needs a deliberate future look regardless.

**Verification performed:** `pytest tests/scripts/test_deferred_work_promote.py tests/scripts/test_deferred_work_baseline.py -v` -> 42 passed. `pixi run -e pyforge-doctor pyforge-doctor-test` -> 907 passed, 2 skipped (unaffected). All HIGH fixes re-verified live, not just via synthetic tests.

**Residual risks:** `DW-FU-8-4` (the batch-abort design flaw) affects all 8 real fleet projects today -- a bare fleet-wide `--fix` run would currently abort everywhere rather than promoting anything, until that redesign lands. The already-known `_anonymous()` swallow-bug (`DW-FU-8-1`) means "promoted" and "grandfathered" are provably divergent definitions for a quantified slice of the fleet (marshal's 9 affected headers) -- unresolved, explicitly out of scope for both this story and Story 8.1.
