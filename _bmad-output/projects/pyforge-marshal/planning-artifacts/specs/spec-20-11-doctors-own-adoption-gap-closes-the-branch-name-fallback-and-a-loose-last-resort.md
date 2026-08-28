---
title: "Doctor's own adoption gap closes -- the branch-name fallback and a loose last resort"
type: bug
created: '2026-08-28'
status: in-review
updated: '2026-08-28'
baseline_revision: 6f2ae94e5d1e0be7e9186c6db07bfad2cbca7c9d
review_loop_iteration: 0
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-landing-evidence-grammar/SPEC.md
warnings: []
deferred: []
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

(pending adversarial review)

## Auto Run Result

(pending adversarial review)
