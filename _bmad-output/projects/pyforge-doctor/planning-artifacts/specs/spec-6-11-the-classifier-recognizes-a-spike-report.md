---
title: 'Story 6.11: The classifier recognizes a spike report'
type: 'change'
created: '2026-08-11'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 'f6b3e8f2b32efdedb498c47fa2352f5e17bb4594'
final_revision: 'c9e59028ff'
context:
  - '{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-bmad-drift-new-artifact-shape/SPEC.md'
  - '{project-root}/_bmad-output/implementation-artifacts/epic-6-context.md'
  - '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py'
  - '{project-root}/src/shared/packages/pyforge-doctor/tests/unit/test_sources_factory.py'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `pyforge.doctor.sources.factory::classify()` has no rule for a design-spike's
PASS/FAIL report filed at a project's `planning-artifacts/` root (e.g.
`spike-0-copier-api-fit-report.md`, PR #427, Marshal Story 7.6). It falls through to
`UNKNOWN`, and `check_coverage` HARD-fails it as `uncovered` — the third time an
unrecognized-but-legitimate shape has tripped this detector (fourteen shapes 2026-07-28,
eleven more 2026-08-08).

**Approach:** Add one dated classification rule to `classify()`, in the same place and
comment convention as the prior two carve-outs, recognizing `planning-artifacts/spike-<N>-
<slug>-report.md` at the project root.

## Boundaries & Constraints

**Always:** `check_coverage`'s fail-closed default is unchanged — a file matching no rule,
including a spike-report look-alike outside the agreed pattern, still HARD-fails as
`uncovered`. The new rule recognizes exactly this one shape, nothing wider.

**Block If:** none identified — this is a single-file, single-rule, precedented change with
a resolvable design decision (exact pattern scope), not a human decision.

**Never:** do not touch `check_coverage`'s walk/fail-closed logic, do not add a general
new-shape-tolerance mechanism, do not import `pyforge.marshal` or any station package (the
classifier's independence rule, Story 6.10, is untouched by this work).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Real spike report | `planning-artifacts/spike-0-copier-api-fit-report.md` | `classify()` returns a named (non-`UNKNOWN`) classification; `check_coverage` reports no `uncovered` finding for it | No error expected |
| Future spike report | `planning-artifacts/spike-2-some-other-thing-report.md` | Same rule matches (pattern generalizes over the spike index and slug, not hard-coded to `spike-0`) | No error expected |
| Look-alike outside the pattern | e.g. `planning-artifacts/spike-copier-api-fit-report.md` (no numeric index) | Still falls through to `UNKNOWN`; `check_coverage` still HARD-fails it as `uncovered` | Fail-closed preserved, no exception |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py` (`classify()`, ~line 1057) -- add one dated `re.fullmatch` rule for `planning-artifacts/spike-\d+-[a-z0-9-]+-report\.md`, placed immediately before the terminal `return "UNKNOWN"`, following the file's own established dated-comment convention (names this story and the 2026-08-11 incident, mirrors the 2026-07-28/2026-08-08 blocks above it).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_factory.py` (§ coverage, near `test_uncovered_file_reports_fail`) -- add tests proving the real shape is recognized and a look-alike still HARD-fails, using the file's existing `_bootstrap`/`factory.gather` pattern (mirrors `test_spec_indexed_in_claude_md_is_not_flagged` for the positive case, `test_uncovered_file_reports_fail` for the negative case).
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-bmad-drift-new-artifact-shape/{SPEC.md,.memlog.md}` -- this story's own upstream Tier-2 Spec, whose `surface:` names `factory.py`; editing that file without reconciling trips `pixi -e local-recipes detectors-ci`'s `spec-surface` drift check (discovered live during this pass, not anticipated at planning time -- see Design Notes).
- `scripts/.spec-surface-baseline.json` -- re-stamped, scoped to only this spec (`--spec pyforge-doctor/spec-bmad-drift-new-artifact-shape`), after the memlog reconciliation.

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py` -- add the `spike-<N>-<slug>-report.md` classification rule with a dated comment -- closes the third occurrence of this exact class of gap.
- [x] `src/shared/packages/pyforge-doctor/tests/unit/test_sources_factory.py` -- add a test that a spike-report file (matching the real `spike-0-copier-api-fit-report.md` shape, plus a second index to prove the pattern isn't hard-coded to `spike-0`) is classified and does not trip `uncovered` -- covers the I/O Matrix's happy-path rows.
- [x] `src/shared/packages/pyforge-doctor/tests/unit/test_sources_factory.py` -- add a test that a spike-report look-alike outside the agreed pattern (e.g. missing the numeric index) still HARD-fails as `uncovered` -- covers the I/O Matrix's error-case row and proves the fail-closed default survives.
- [x] `spec-bmad-drift-new-artifact-shape`'s `.memlog.md` -- reconcile by naming the changed surface (`factory.py`), resolve its open question, flip `SPEC.md` `status` to `shipped` and `open_questions` to `[]`, then `python scripts/spec_surface_check.py --write-baseline --spec pyforge-doctor/spec-bmad-drift-new-artifact-shape` -- closes the `spec-surface` drift this change would otherwise leave red.

**Acceptance Criteria:**
- Given a file under a project's `planning-artifacts/` root matching `spike-<N>-<slug>-report.md`, when `classify()` runs, then it returns a named classification instead of `UNKNOWN`, with a dated comment recording this story and the 2026-08-11 incident.
- Given `check_coverage` runs against the live `pyforge-marshal` tree (which carries `planning-artifacts/spike-0-copier-api-fit-report.md` today), then it reports zero `uncovered` findings for that file, and `pixi run -e local-recipes detectors-ci` reports clean for `bmad-drift`.
- Given a file that still matches no rule at all, including a spike-report look-alike outside the agreed pattern, when `check_coverage` runs, then it still HARD-fails as `uncovered`, exactly as before.

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1 (medium 1)
- defer: 1 (low 1)
- reject: 12 (low 12)
- addressed_findings:
  - `[medium]` `[patch]` `SPEC.md`'s body still carried a `## Open Questions` section with the
    exact question the frontmatter had just resolved to `open_questions: []` -- a
    self-contradiction in the file this same story reconciles and calls "the canonical,
    preservation-validated contract." Removed the stale body section to match the empty
    frontmatter list, matching the convention of every other resolved-to-`[]` spec in the
    fleet (they omit the section entirely rather than leaving it empty).

Rejected (12, all low): a claimed lowercase-vs-`Spike-1`/`Spike-2` capitalization mismatch
(the real precedent file and this story's own I/O matrix are lowercase throughout; `Spike-N`
only ever appears as a human-readable story *title* in `epics.md`, never as a filename); the
`planning-artifacts/` root-scoping boundary being "asserted not tested" (the regex's character
class excludes `/`, so nesting cannot match under `re.fullmatch` -- already structurally
enforced, just untested); an unconstrained slug segment (`spike-0-report-report.md`) and a
"decorative" index grouping -- both intentional per this spec's own Design Notes, which
generalize over the index and slug together as one unit; an unevidenced-but-independently-
reverified "verified live" memlog claim (re-ran `check_coverage` and `detectors-ci` myself
during this pass and confirmed the claim true); a housekeeping blank-line report the reviewing
agent itself withdrew as not a real defect; and five case/underscore/missing-slug/non-integer-
index/missing-suffix naming variants from Edge Case Hunter -- all correctly fail-closed to
`UNKNOWN`/`uncovered` exactly as this story's own Boundaries & Constraints require ("recognizes
exactly this one shape, nothing wider") and its Non-goals disclaim ("not an attempt to pre-empt
every artifact shape a future BMAD effort might invent").

Deferred (`DW-FU-6-11`, low): no test in `test_sources_factory.py` asserts `classify()`'s
literal return string for any rule, including the new one -- a pre-existing gap across the
whole file (every prior rule has the same gap), not a regression this story introduced, and out
of its Boundaries & Constraints (this story's tests follow the file's own existing pattern).

### 2026-08-13 — Review pass (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 13 (low 13)
- addressed_findings:
  - none

Rejected (13, all low): a claim that the appended memlog's "detectors-ci reports clean for
bmad-drift" line now reads false -- true only because an unrelated file
(`planning-artifacts/parallel-fan-out-readiness-assessment.md`) landed on main after this
story's fix, exactly the finding this spec's own Design Notes and Residual Risks already name
(independently re-verified live via `pixi run -e local-recipes detectors-ci`: the spike-0
report itself is the only thing this story owns, and it is no longer uncovered); `DW-FU-6-11`
not yet promoted to the tracked ledger -- the documented, expected state of a freshly minted
defer, already called out in Residual Risks; a duplicate observation that no test asserts
`classify()`'s literal return string -- the same substance as the already-deferred
`DW-FU-6-11`, not a new gap; a claim that the `archive:spike-report` category is unverified by
any consumer -- true of every one of the six prior `archive:*` rules already in this file
(`change-history`, `research`, `retros`, `prfaq`, `campaign`), independently confirmed by grep,
not a new inconsistency this diff introduced; an unverifiable-provenance claim about the
byte-for-byte recovery -- independently disproven: the fast-forwarded commit traces to an
`attempt-preserve/` branch whose parent is this worktree's own prior HEAD, confirmed via `git
merge-base`; a cosmetic note that three prose sources (commit subject, code comment, memlog)
narrate the incident without cross-referencing; six naming-variant/behavioral edge cases
(uppercase/underscored slug, no descriptive slug, a `-v2`/`-final` suffix after `report`, a
nested subdirectory placement, and classifying by filename alone irrespective of file content)
-- all correctly fail-closed to `UNKNOWN`/`uncovered`, or are out of scope per this story's own
Boundaries & Constraints ("recognizes exactly this one shape, nothing wider" / "do not add a
general new-shape-tolerance mechanism"), mirroring the prior pass's identical rejections of the
same class of finding; and a test-style nit about repeating a literal filename three times
instead of a shared constant -- independently confirmed as the file's own universal existing
convention (every other coverage test in the file does the same, e.g. lines 213, 512, 581,
672).

## Design Notes

**Pattern scope (the open design decision).** The upstream Spec
(`spec-bmad-drift-new-artifact-shape`) leaves the exact rule scope open: literally
`spike-0-...-report.md`, or a pattern anticipating future `spike-1`/`spike-2` reports under
the same convention. This spec resolves it: `planning-artifacts/spike-\d+-[a-z0-9-]+-
report\.md` — generalizing over the numeric spike index and the descriptive slug, since the
convention this file already follows for every prior carve-out (the 6.10-sharded-station
block, the 2026-08-08 block) generalizes over the varying part of a shape rather than
hard-coding the one instance seen. A `spike-0`-only literal would trip `uncovered` again the
moment `spike-1-...-report.md` is written, defeating the purpose of a durable rule.

**The spec-surface reconciliation was not anticipated at planning time.** The upstream Tier-2
Spec (`spec-bmad-drift-new-artifact-shape`) declares `factory.py` as its own governed
`surface:`. Editing that file without updating the Spec's `.memlog.md` trips a SEPARATE
detector (`spec-surface`, distinct from `bmad-drift`, the one this story is actually about) as
`drift: fail` — discovered live via `pixi run -e local-recipes detectors-ci` after the core fix
was verified working. This is the repo's own spec-driven-development enforcement working as
intended (a governed file changed, its Spec must say so), not a defect in the fix. Reconciled by
naming the changed path in the Spec's memlog, resolving its now-answered open question, marking
it `shipped` (a 1:1 Spec-to-story mapping, fully implemented), and re-stamping
`scripts/.spec-surface-baseline.json` scoped to only this one Spec (never a bare
`--write-baseline`, which would also accept four unrelated `drift-presumed` findings on other
specs as correct — out of this story's scope, left untouched).

**One pre-existing, out-of-scope `detectors-ci` finding remains.** `chain-completeness`'s
`spec-not-decomposed: pyforge-marshal` fires both before and after this change (verified via
`git stash`) — an unrelated Marshal-owned Spec backlog item, not caused by or related to this
story's surface.

**Recovered from a destructive re-arm reset (2026-08-13).** This story's prior run
(`bmad-loop/20260811-191742-ef77`) implemented and verified the change on 2026-08-11, but its
worktree hit `rearm_escalation`'s destructive default (documented fleet-wide:
`reference/bmad-loop-escalation-and-landing-traps.md` trap 1), which resets the tree to the
story's baseline with committed work not consulted. The current run's fresh worktree started
from that same baseline with `factory.py` unchanged and the spec still claiming `in-review`/all
tasks done — a real desync between the (persistent, Tier-3-backlinked) spec and the (per-worktree)
code. The lost work was not actually gone: `git stash` creates a commit per stash, and `git fsck
--unreachable` surfaced three dangling `WIP on bmad-loop/20260811-191742-ef77/...` merge commits
in the shared object store, the newest (`152db6a0`, 2026-08-11 22:17:45) carrying the complete,
correct implementation matching this spec's Code Map exactly (factory.py +11, test file +52,
the Spec-surface reconciliation, all as designed). Restored by copying each file's content from
that commit into the working tree and re-running `spec_surface_check.py --write-baseline --spec
pyforge-doctor/spec-bmad-drift-new-artifact-shape` (rather than trusting the stash's own stamped
hashes, which could have drifted). No code was re-derived or reinterpreted -- this is the
original 2026-08-11 work, recovered byte-for-byte.

**A second, unrelated `uncovered` finding exists on the live tree, out of this story's scope.**
`check_coverage`/`detectors-ci`'s `bmad-drift` now finds
`planning-artifacts/parallel-fan-out-readiness-assessment.md` uncovered in `pyforge-marshal` --
a different artifact shape that landed via unrelated main-branch history between this story's
2026-08-11 baseline and today. Confirmed the spike-0 report itself is no longer uncovered
(the one thing this story owns); the new finding is a fourth instance of the same recurring
class of gap this story fixes a third instance of, but for a different filename shape, and is
left untouched per this story's own Boundaries & Constraints ("recognizes exactly this one
shape, nothing wider").

**A second, independent re-arm reset hit the same story (2026-08-13).** This run
(`bmad-loop/20260813-094917-9bba`) opened on a fresh worktree at the fleet's current HEAD, with
the spec still claiming `status: done` from the 2026-08-11 recovery above -- but `factory.py`
and the test file on disk had no trace of the `spike-report` rule (grep for `spike` in either
file returned nothing), confirming the same destructive reset had recurred on a *second*,
independent worktree for this story. As before, the work was not actually gone: an
`attempt-preserve/20260813-094917-9bba-c9e59028` branch existed in the shared object store,
carrying commit `c9e59028ff` ("doctor: classifier recognizes the spike-report artifact shape
(Story 6.11)") -- itself the byte-for-byte 2026-08-11 recovery, re-committed. `git merge-base`
confirmed this commit's sole parent was this worktree's own HEAD (`257094dcc2`), i.e. a clean
fast-forward, not a divergent rewrite -- so `git merge --ff-only` restored it with no conflict
resolution and no re-derivation. This matches the fleet-wide standing policy (non-destructive
recovery from a preserved branch, never a from-scratch re-implementation) and the exact
procedure the 2026-08-11 recovery already established for this same story.

## Verification

**Commands (all re-run 2026-08-13 against the restored code):**
- `pixi run -e pyforge-doctor pyforge-doctor-test` -- **845 passed, 1 skipped**, including the
  three new spike-report tests.
- `python -m pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_factory.py -v`
  -- every test passed individually (inspected by name, not just the aggregate count).
- `check_coverage` against the live tree -- the only `uncovered` finding is
  `planning-artifacts/parallel-fan-out-readiness-assessment.md` (unrelated, see Design Notes);
  `spike-0-copier-api-fit-report.md` is absent from the list, confirming CAP-1.
- `pixi run -e local-recipes detectors-ci` -- `bmad-drift`'s `uncovered` fail is now for the
  unrelated finding above, not the spike-0 report; `spec-surface` and `deferred-work`'s prior
  state both pass (the new `deferred-work: tier3-only-deferral` fail for `DW-FU-6-11` is the
  documented, expected state of a freshly minted defer awaiting manual promotion -- see `DW-5`
  and the multiple `DW-FU-7-1-*` entries recording the same mechanism).

**Manual checks:**
- Confirmed the new regex is anchored with `re.fullmatch` (not `re.match`/`re.search`), matching
  the file's own convention for every other rule in `classify()`.

## Auto Run Result

Status: `done`

**Summary.** `pyforge.doctor.sources.factory::classify()` gained one dated `re.fullmatch` rule
recognizing a design-spike's PASS/FAIL report filed at a project's `planning-artifacts/` root
(`spike-<N>-<slug>-report.md`), closing the third occurrence of this class of `uncovered` gap.
The upstream Tier-2 Spec (`spec-bmad-drift-new-artifact-shape`) was reconciled to `shipped`.
The implementation was not newly written in either pass -- it was recovered non-destructively
twice: first byte-for-byte from a dangling `git stash` commit (2026-08-11 recovery), then this
pass, fast-forwarded from an `attempt-preserve/` branch after an independent second
`rearm_escalation` reset hit this story's worktree again (see Design Notes for both incidents).
This pass's own work was: restoring the code via fast-forward merge, re-verifying every claim
in the existing spec live, and running a fresh adversarial + edge-case review pass.

**Files changed (cumulative, across both recoveries):**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py` -- new
  `archive:spike-report` classification rule.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_factory.py` -- three new tests
  (real shape classified, a second spike index also classified, a look-alike missing the
  numeric index still hard-fails).
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-bmad-drift-new-artifact-shape/{SPEC.md,.memlog.md}`
  -- reconciled to `status: shipped`, open question resolved; the first pass additionally
  removed a stale `## Open Questions` body section left behind after the frontmatter was
  cleared.
- `scripts/.spec-surface-baseline.json` -- re-stamped for this one Spec only.
- This spec file -- a second Review Triage Log entry and Design Notes entry recording this
  pass's independent re-arm recovery and review.

**Review findings breakdown (this pass, 2026-08-13 follow-up):** 0 `patch`, 0 `defer`, 13
`reject`ed -- every finding from Blind Hunter and Edge Case Hunter independently re-verified
and traced to either (a) an already-disclosed, out-of-scope fact in this spec's own Design
Notes/Residual Risks, (b) a duplicate of the already-deferred `DW-FU-6-11`, (c) a naming-variant
edge case explicitly excluded by this story's own Boundaries & Constraints, or (d) a pattern
already established by six prior rules / the test file's own existing convention (confirmed by
grep in each case; see Review Triage Log for the full breakdown). Cumulative across both review
passes: 1 `patch`, 1 `defer` (`DW-FU-6-11`), 25 `reject`ed.

**Follow-up review recommendation:** `false` -- this pass made no code or spec-contract changes
(only a documentation-only triage-log/design-notes append after a non-destructive code
recovery); nothing here warrants an independent follow-up pass.

**Verification performed:** full `pyforge-doctor` suite re-run this pass (845 passed, 1
skipped); live `pixi run -e local-recipes detectors-ci` re-run this pass, confirming
`bmad-drift`'s only `uncovered` finding is the pre-existing, unrelated
`parallel-fan-out-readiness-assessment.md`, not the spike-0 report; `git merge-base` confirmed
the fast-forward recovery was non-divergent. See `## Verification` above for the first pass's
commands.

**Residual risks:**
- `DW-FU-6-11` (deferred, see above) is `tier3-only-deferral`-red in `detectors-ci` until
  manually promoted to the tracked ledger -- the documented, expected state for a freshly
  minted defer (matches `DW-5` and the `DW-FU-7-1-*` entries), not a new problem.
- `planning-artifacts/parallel-fan-out-readiness-assessment.md` is a second, unrelated
  `uncovered` finding on the live tree (introduced by unrelated main-branch history after this
  story's baseline) -- out of this story's scope per its own Boundaries & Constraints, but a
  same-shaped future story.
- Two pre-existing, out-of-scope `detectors-ci` findings remain unchanged by this story:
  `chain-completeness`'s `spec-not-decomposed: pyforge-marshal`, and `llms_full_check`'s 34-item
  pin-catalog drift.
- This story's worktree has now hit the destructive `rearm_escalation` reset twice
  independently. Both times the work was recoverable because a preserve branch or dangling
  stash existed, but per the fleet-wide standing policy, a *third* escalation on the same story
  is a signal a resume cannot fix and should stop for the operator rather than attempt a third
  automatic recovery.

