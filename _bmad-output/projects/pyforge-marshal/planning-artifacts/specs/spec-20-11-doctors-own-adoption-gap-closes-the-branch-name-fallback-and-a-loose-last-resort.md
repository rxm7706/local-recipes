---
title: "Doctor's own adoption gap closes -- the branch-name fallback and a loose last resort"
type: bug
created: '2026-08-28'
status: done
updated: '2026-08-28'
baseline_revision: 6f2ae94e5d1e0be7e9186c6db07bfad2cbca7c9d
review_loop_iteration: 0
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-landing-evidence-grammar/SPEC.md
warnings: []
deferred:
  - summary: >-
      Route 4's station+key co-occurrence check has no adjacency/context requirement -- the
      station word and the numeric key only need to both appear somewhere in the same commit
      subject, independently, which could in principle pick up an unrelated small number (a
      version string, a count) alongside a station name.
    evidence: |-
      Review-pass finding (Blind Hunter layer, 2026-08-28): searched this repo's actual commit
      history for such collisions and found none live. Risk is further bounded by (a) the
      digit-boundary guards correctly protecting timestamp/hash blobs in bmad-loop run IDs
      (verified: internal digits of a run id like 20260822-170016 never satisfy the negative
      lookaround on either side, since neighboring characters within the blob are themselves
      digits), and (b) this repo's commit conventions being structured/bot-generated rather than
      free text. Acknowledged as an inherent property of a deliberately-loose, advisory-only
      last resort (per its own docstring) rather than something to further tighten now.
    location: >-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py
      (_loose_subject_key_match)
    severity: low
---

<intent-contract>

## Intent

**Problem:** A fleet-wide hygiene sweep (2026-08-28) ran `story-status-check` and found 25
standing FAILs across four stations (doctor 6, marshal 10, mason 7, steward 2). Per this repo's
own established caution (auto-memory `feedback_story_status_check_route3_false_positives.md`,
itself documenting 3 earlier live false positives closed by Story 20.9), every FAIL was verified
by hand before touching anything: `git log --all` for candidate landing commits, then
`git merge-base --is-ancestor <sha> main` on each. All 25 were genuinely landed. Two distinct
root causes, both in doctor's own port of the shared grammar (`sources/marshal.py`), neither in
`pyforge.core.landing_evidence` or `pyforge.marshal.core.promotion`:

1. Doctor's Routes 2/3 (`_keys_from_merge_subjects`, `_keys_from_main_commits`) never tried
   `classify_branch_name`'s `land/<station>-<epic>-<seq>` / `bmad-loop/<run>/<key>` branch-name
   grammars when a GitHub PR merge subject's captured branch didn't carry a station/dispatch
   prefix. `pyforge.marshal.core.promotion._classify_merge_subject` (Story 20.10's own
   implementation) already has this exact fallback, with a docstring explaining precisely this
   gap; doctor's Story 20.9 port never picked it up.
2. A real, irreducible tail of hand-authored landing commits (`"<station>: promote story
   <e>.<s> to done in the tracked ledger"`, `"land <station> <e1>.<s1>+<e2>.<s2> (N stories):
   ..."`, etc.) matches no anchored grammar shape at all, and adding a bespoke regex per phrasing
   is unbounded — a new one will always exist.

**Approach:** (1) add the same `classify_branch_name` fallback doctor is missing, mirroring
`promotion.py::_classify_merge_subject`'s own pattern exactly (doctor cannot import
`pyforge.marshal`, so the small GitHub-PR-subject regex is duplicated locally with a comment
explaining why, the same way `promotion.py` duplicates it from `landing_evidence.py`'s own
private regex). (2) Add ONE additional, deliberately loose "Route 4" scoped ONLY to
`gather_story_status`: does any commit subject mention the station name AND the exact numeric
key together, in any phrasing, with digit-boundary correctness (so "11.10" never satisfies a
search for "11-1")? This route is never wired into the shared `pyforge.core.landing_evidence`
module and cannot loosen any safety-critical consumer (marshal's zombie-redispatch refusal,
`marshal retire`'s branch-deletion safety) — it only affects doctor's own advisory FAIL/OK
finding.

## Acceptance Criteria

- **Given** the live repo **Then** all 25 standing false positives (doctor 6-9, 6-11, 9-3, 11-1,
  11-2, 11-3; marshal 1-6, 3-12, 3-13, 5-8, 8-3, 8-4, 9-1, 9-3, 9-5, 10-3; mason 2-4, 2-5, 2-6,
  3-8, 3-9, 4-4, 5-4; steward 8-7, 9-7) go green with no per-story whitelist.
- **Given** a genuinely-unlanded story **Then** it still fails exactly as today — pinned by
  dedicated negative tests: an unrelated branch name (no grammar match, no key co-occurrence), a
  co-occurring key belonging to a DIFFERENT, longer number (digit-boundary), and a co-occurring
  key with no station word present.
- **Given** this fix **Then** zero changes to `pyforge.core.landing_evidence` or
  `pyforge.marshal.core.promotion` — confirmed by diff.

## Boundaries & Constraints

**Always:**
- Fix scoped to `pyforge-doctor`'s own `sources/marshal.py` only.
- The branch-name fallback mirrors `promotion.py::_classify_merge_subject`'s existing, already-
  shipped pattern exactly (same private-regex-duplication rationale, same `classify_branch_name`
  call) — not a new design.
- Route 4 (loose co-occurrence) is the LAST resort, tried only after all grammar-based routes
  fail, and only inside `gather_story_status` — never exported for another consumer to import.
- Add regression tests pinning both the branch-name fallback and Route 4, including negative
  cases, so neither the specific bug nor a false-negative regression can silently recur.

**Never:**
- Never modify `pyforge.core.landing_evidence` or `pyforge.marshal.core.promotion` — this
  story's whole point is that the shared grammar and marshal's own adoption of it are already
  correct; only doctor's port was incomplete.
- Never import `pyforge.marshal` from this module (the classifier-independence rule this
  module's own docstring documents at length).
- Never widen Route 4 beyond doctor's own advisory `story-status` finding.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `land/<station>-<epic>-<seq>` branch wrapped in a GitHub PR merge subject | `Merge pull request #N from owner/land/doctor-6-9-ledger` | Suppressed (OK) | — |
| Bare `bmad-loop/<run>/<key>` branch wrapped in a GitHub PR merge subject | `Merge pull request #N from owner/bmad-loop/<run>/8-2-region-parser` | Suppressed (OK) | — |
| An unrelated branch, no key co-occurrence anywhere | `Merge pull request #N from owner/maintenance/doctor-ledger-sync` | Still FAIL | never silently suppressed |
| Hand-authored commit, station + exact key co-occur | `"doctor: promote story 11.1 to done..."` | Suppressed (OK), via Route 4 | — |
| Hand-authored commit, a LONGER key collides with a shorter search | `"doctor: promote story 11.10..."` searched for key `11-1` | Still FAIL | digit-boundary guard |
| Co-occurring key, wrong station | `"marshal: promote story 11.1..."` for a `doctor` key | Still FAIL | station word required |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py` — imports
  `classify_branch_name` alongside the existing `pyforge.core.landing_evidence` imports; adds
  `_GITHUB_MERGE_SUBJECT_RE` (duplicated from the shared module, mirroring
  `promotion.py`'s own precedent), `_branch_name_fallback_key`, `_loose_subject_key_match`; wires
  both into `_keys_from_merge_subjects` (Route 2) / `_keys_from_main_commits` (Route 3) and the
  main loop in `gather_story_status` (new Route 4, tried after Route 3).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py` (read-only
  reference) — `_classify_merge_subject`'s existing branch-name-fallback pattern, mirrored
  exactly.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_marshal_story_status.py` — new
  tests: `test_land_branch_wrapped_in_a_github_pr_subject_suppresses_the_false_green`,
  `test_bmadloop_branch_wrapped_in_a_github_pr_subject_suppresses_the_false_green`,
  `test_an_unrelated_pr_branch_does_not_suppress`,
  `test_loose_co_occurrence_suppresses_a_hand_authored_landing_commit`,
  `test_loose_co_occurrence_does_not_confuse_a_longer_key`,
  `test_loose_co_occurrence_requires_the_station_too`.

## Implementation record — 2026-08-28

**Shape as built.** `_branch_name_fallback_key(subject, project_slug)`: matches the GitHub-PR
merge-subject shape locally (duplicated regex, per the module's own independence rule), extracts
the branch, and tries `classify_branch_name` on it -- the exact fallback
`promotion.py::_classify_merge_subject` already ships. Wired as a final parser tried in
`_keys_from_merge_subjects`'s existing per-subject loop, and as a fallback after
`classify_commit` in `_keys_from_main_commits`. `_loose_subject_key_match(subjects, station=,
key_ref=)`: word-bounded station-name regex AND a digit-boundary-guarded `epic[.-]seq` regex
(negative lookaround on both sides so "11.1" never matches inside "11.10" or "111.1"), searched
against both the all-refs subject pool and the main-commits pool already fetched by Routes 2/3 --
no new git call. Wired as Route 4 in `gather_story_status`'s main loop, tried only after Route 3
fails.

**Verification:**
- `python -m pyforge.doctor.sources story-status` on the live repo -- 25 FAILs -> 0, confirmed
  before/after.
- `pixi run --frozen -e pyforge-doctor pytest tests/unit/test_sources_marshal_story_status.py`
  -- 37 passed (31 pre-existing + 6 new), including the negative cases.
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- 1294 passed, 3 failed (all 3
  confirmed pre-existing/unrelated via `git stash`: a repo-wide SKF-marker meta-test, a speed-
  budget flake, a discovery-walk test picking up unrelated worktrees on disk).
- `git diff --stat -- src/shared/packages/pyforge-core src/shared/packages/pyforge-marshal` --
  empty; confirms the AC's "zero changes to the shared grammar or marshal's own adoption" claim.

## Review Triage Log

### 2026-08-28 — Review pass

Two review layers run in parallel: a Blind Hunter / Edge Case Hunter pass (regex correctness,
false-negative risk against real repo history, `_branch_name_fallback_key` edge cases, the
"zero shared-package changes" claim) and a Verification Gap pass (independently re-deriving
every claim: re-running the detector live, re-verifying 4 of the 25 landings from scratch,
re-running both test suites, re-confirming the package-isolation diff).

- intent_gap: 0
- bad_spec: 0
- patch: 1 (high 0, medium 1, low 0)
- defer: 1 (high 0, medium 0, low 1)
- reject: 0
- addressed_findings:
  - `[medium]` `[patch]` `_loose_subject_key_match`'s key regex was built from `key_ref.epic`/
    `key_ref.seq` only, silently dropping `key_ref.suffix` — a commit naming the bare key
    ("11.1") would equally satisfy a search for its lettered split-story sibling ("11-1a"), and
    vice versa. Verified by the reviewer as a direct code trace (not yet a live false negative —
    no suffix-lettered key currently exists in this repo's tracked history that would trigger
    it), but a real gap against the code's own "EXACT epic.seq pair" docstring claim. Fixed:
    the regex now includes the literal suffix when present, with a widened trailing lookahead
    (`(?![\da-zA-Z])`, not just `(?!\d)`) so a bare-key search can't match inside a longer
    lettered key either. 3 new regression tests pin both directions plus the positive
    exact-suffix-match case.
  - `[low]` `[defer]` Route 4's station+key co-occurrence has no adjacency/context requirement
    — the station word and the numeric key only need to both appear somewhere in the same
    subject, independently, which could in principle pick up an unrelated small number (a
    version string, a count) alongside a station name. The reviewer searched this repo's actual
    commit history for such collisions and found none live; the risk is further bounded by (a)
    the digit-boundary guards correctly protecting timestamp/hash blobs in bmad-loop run IDs,
    and (b) this repo's commit conventions being structured/bot-generated rather than free text.
    Acknowledged as an inherent property of a deliberately-loose, advisory-only last resort
    (per its own docstring) rather than something to further tighten now — recorded here rather
    than silently accepted.
- Independently reconfirmed, no discrepancy found: the live detector genuinely reports 0 FAILs
  (was 25) on the current tree; 4 of the 25 landings re-verified from scratch via
  `git log --all` + `git merge-base --is-ancestor` (doctor 11-1, marshal 8-3, mason 3-8 — the
  exact branch-name-fallback scenario, wrapped in a `bmad-loop/<run>/<key>` branch — and steward
  9-7); both test suites' real pass/fail counts match this spec's own claims exactly, including
  independently re-confirming via `git stash` that all 3 full-suite failures are pre-existing;
  `git diff --stat -- src/shared/packages/pyforge-core src/shared/packages/pyforge-marshal`
  independently re-run and confirmed empty.

## Auto Run Result

Status: done

**Summary:** Closed doctor's own incomplete adoption (Story 20.9) of the shared
landing-evidence grammar, found live during a fleet-wide hygiene sweep that turned up 25
`story-status` false-positive FAILs across doctor/marshal/mason/steward — every one confirmed
by hand as a genuine landing before any code changed. Two fixes, both entirely local to
`pyforge-doctor`'s own port (`sources/marshal.py`), zero changes to the shared
`pyforge.core.landing_evidence` grammar or `pyforge.marshal.core.promotion` (Story 20.10's own,
already-correct adoption): (1) a `classify_branch_name` fallback mirroring
`promotion.py::_classify_merge_subject`'s existing pattern, closing the `land/`/`bmad-loop/`
branch-name gap; (2) a new, deliberately loose, doctor-local-only "Route 4" — station name +
exact numeric key co-occurring anywhere in a commit subject — closing the residual tail of
hand-authored landing phrasings no fixed grammar can enumerate. Two review layers found one
real gap (the suffix-dropping regex bug, patched) and one acknowledged, bounded, low-severity
design property (Route 4's lack of adjacency requirement, deferred with reasoning).

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py` — the fix:
  `classify_branch_name` import, `_GITHUB_MERGE_SUBJECT_RE` (duplicated, same rationale as
  `promotion.py`'s own copy), `_branch_name_fallback_key`, `_loose_subject_key_match`, wired
  into `_keys_from_merge_subjects`, `_keys_from_main_commits`, and a new Route 4 in
  `gather_story_status`'s main loop.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_marshal_story_status.py` — 9 new
  tests (6 initial + 3 from the review-pass suffix fix): the branch-name fallback (positive +
  negative), Route 4 (positive + 2 negatives: wrong station, longer/shorter key), and the
  suffix-correctness trio (bare-vs-suffixed both directions + exact-suffix positive case).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-landing-evidence-grammar/SPEC.md`
  — new CAP-4.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md` — new Story 20.11.
- This spec file (new).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml` — ledger
  key added (dispatcher finalize, flipped to `done` alongside this file's own `status` field).

**Review findings breakdown:** 2 review layers run in parallel. 1 `patch` (medium) — the
suffix-dropping regex bug, corrected with 3 new regression tests. 1 `defer` (low) — Route 4's
inherent lack of adjacency requirement, bounded and acknowledged rather than further narrowed.
0 `reject`.

**Follow-up review recommendation:** `true`. This fix touches an advisory detector every
station's ledger integrity indirectly depends on for catching REAL false-dones; worth a second
look once a few more real landings have run against it in the wild, matching the numeric-
threshold convention this campaign's sibling stories already use (1 medium patch alone crosses
that bar: `3*1 = 3`... below 5, but the low-severity deferred item plus the detector's own
history of 4 prior false-positive rounds argues for the same caution regardless of the raw
score).

**Verification performed:**
- `python -m pyforge.doctor.sources story-status` on the live repo — 25 FAILs → 0, before and
  after, independently re-confirmed by both review layers (one re-derived the pre-fix 25 via
  `git stash`, the other re-ran post-fix directly).
- `pixi run --frozen -e pyforge-doctor pytest tests/unit/test_sources_marshal_story_status.py`
  — 40 passed (31 pre-existing + 9 new).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — 1297 passed, 3 failed, all 3
  independently reconfirmed pre-existing via `git stash` by the review pass.
- `git diff --stat -- src/shared/packages/pyforge-core src/shared/packages/pyforge-marshal` —
  empty, confirmed twice independently.
- 4 of the 25 landings re-verified from scratch by the review pass (not just trusted from this
  story's own account): doctor 11-1, marshal 8-3, mason 3-8 (the exact branch-fallback
  scenario), steward 9-7 — all genuine ancestors of `main`.

**Residual risks:** Route 4's lack of an adjacency/context requirement (deferred item above) —
low severity, no live collision found in this repo's actual history, bounded by digit-boundary
guards and this repo's structured commit conventions. Landing (git commit beyond this session's
working tree, the ledger flip for key
`20-11-doctors-own-adoption-gap-closes-the-branch-name-fallback-and-a-loose-last-resort`, and
the `maintenance` PR label — this touches `src/` and `_bmad-output/`, never `recipes/**`) is the
dispatcher's, matching every other story landed this session.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).
