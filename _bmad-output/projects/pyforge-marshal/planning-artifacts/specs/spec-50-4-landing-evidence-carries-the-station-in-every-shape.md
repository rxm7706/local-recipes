---
title: '50.4: Landing evidence carries the station in every shape'
type: 'fix'
created: '2026-09-18'
status: 'done'
baseline_revision: '3371ab79dd7305b7e2ac34efce2dc33578460010'
review_loop_iteration: 1
followup_review_recommended: true
context:
  - '_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-50-4-landing-evidence-carries-the-station-in-every-shape.md'
warnings: []
deferred:
  - summary: >-
      Direct-commit branch corroboration (_branch_belongs_to_project) has no production
      call site that supplies real branch data for the retrospective git-log-only subject
      scan, so this shape can never actually corroborate in that path today.
    evidence: |-
      Confirmed via dispatch_landing.py/dispatch_land.py: the only production caller of
      branch-corroboration-adjacent code (merge_subject_is_marshal_native) is a pre-flight
      self-consistency check on a templated subject dispatch_land.py is about to render for
      its own station -- not the bare direct-commit shape's retrospective use case. Every
      caller of parse_story_direct_commit_subject inside merged_story_keys's own scan
      passes no branch data, so branch=None always refuses safely by design; the gap is
      that no caller exists that COULD pass real branch data to let a genuine
      direct-commit landing corroborate. Pre-existing, not caused by this story -- Story
      50.4 added the corroboration requirement, but no story has yet added a caller with
      branch data for this shape. Blind Hunter findings #4 and #10 (same root cause).
    location: >-
      src/shared/packages/pyforge-core/src/pyforge/core/landing_evidence.py:178 (_branch_belongs_to_project)
    severity: low
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** On 2026-09-18, atlas's seven `Merge 23-N into main` commits marked herald's
23.1/23.2/23.5/23.6 `story_merged_on_main` (doctor's 23.1–23.3 dispatches completed in one
second that morning and detached from live sessions), and steward's `Story 48.2:` /
`Story 48.4:` subjects poison marshal 48.2/48.4 today — Story 35.1's `known_keys`
corroboration cannot help when the key exists in both ledgers. The un-scoped, templated merge
subject and the bare `Story N.M:` direct-commit subject carry no station identity, so any
project sharing the same key numbering or the same generic template can convict or exonerate
the wrong station.

**Approach:** The templated shape renders and parses with the station slug baked in
(`{slug}` in `merge_subject_template`), so a subject minted by one project's template can no
longer parse as another project's key. The un-scoped direct-commit shape (`Story N.M: ...`
with no station token) now needs a station-scoped branch (`<station>/…`, `dispatch/<slug>/…`,
`land/<station>-…`) or the SHA recovery allowlist to corroborate it — with no such
corroboration, `parse_story_direct_commit_subject` refuses to parse.

## Boundaries & Constraints

**Always:**
- `merged_story_keys` for `pyforge-marshal` against today's `origin/main` no longer contains
  48.2/48.4, and for `pyforge-herald` no longer contains 23.1..23.6, via atlas.
- Every `done` row of all eight tracked ledgers that has real landing evidence still
  classifies (regression fixture: ledgers × `git log origin/main --format=%s`).
- Live history is never re-attributed: the existing `Merge {key} into main` and
  `Story N.M:` subjects already on `main` are grandfathered through the SHA/recovery
  allowlist and the branch-scoped shapes only; the new default applies to landings after
  this story merges.

**Never:**
- Do not make the supervisor trust a session's self-report.
- Do not add a second gate.
- Do not re-attribute landed history — the Epic 50 HARD boundaries in `epics.md` bind.

## I/O & Edge-Case Matrix

| Given | When | Then | Notes |
|---|---|---|---|
| The 2026-09-18 fixture (atlas's `Merge 23-N into main` subjects; steward's bare `Story 48.2:` / `Story 48.4:` subjects) | The real run/journal named in the Given is classified via `merged_story_keys`/`classify_commit` for `pyforge-marshal` and `pyforge-herald` | The cross-station false-positive keys no longer classify for the wrong project, and every ledger `done` row with real evidence still classifies | n/a |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-core/src/pyforge/core/landing_evidence.py` — shared grammar.
  `parse_templated_merge_subject` now takes `project_slug` and self-scopes via
  `_instantiate_slug(template, project_slug)` before splitting on `{key}`, so a subject
  rendered for a foreign slug refuses to parse. `parse_story_direct_commit_subject` now
  requires `_branch_belongs_to_project(branch, project_slug)`; with no branch (or a
  non-corroborating branch) it refuses. `classify_merge_subject`/`classify_commit` thread
  `project_slug`/`branch` through in the existing SHA-allowlist-first, then-shape-cascade
  order. `conformance_fixtures()` gained golden rows exercising the new scoping (including the
  pre-existing `allowlist_*` SHA rows, unchanged).
- `src/shared/packages/pyforge-core/tests/unit/test_landing_evidence.py` — new unit coverage
  for foreign-slug refusal and branch-corroborated/uncorroborated direct-commit parsing.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/identity.py` —
  `render_merge_subject`/`parse_merge_subject`/`_split_template` learn `{slug}` as a
  first-class template token alongside `{key}`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` — repo default
  `merge_subject_template` changed to `"Merge {slug}/{key} into main"`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py` —
  `_classify_merge_subject` threads `project_slug`/`branch` into the shared grammar call.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py` and
  `.../cli/land.py` — merge-subject construction already called
  `identity.render_merge_subject(key, template, project_slug)` with all three arguments; no
  behavioral change needed, confirmed correct.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py` — station-scoped
  classification call site updated to pass `project_slug`/`branch` through to the shared
  grammar (mirrors `promotion.py`).
- `_bmad-output/projects/pyforge-herald/planning-artifacts/marshal-policy.toml` — herald's
  PR #1458 per-project `merge_subject_template` override removed; the repo default
  (`{slug}`-scoped) now supersedes it, so the override is redundant.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py` — Route 2
  (`_keys_from_merge_subjects`) call to `parse_templated_merge_subject` updated to pass
  `project_slug` (3rd required positional arg); doctor's independent duplicate of the grammar
  reading must not import marshal (module-independence rule), so this fix is local to the
  duplicate call site.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ledger.py` —
  `_merged_ids_for_project` call to `parse_templated_merge_subject` updated the same way.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_marshal_story_status.py` —
  three fixtures updated to reflect the now-refused bare, unscoped direct-commit shape:
  one flipped from OK to FAIL (ambiguous evidence no longer suppresses a false-green alarm),
  one given a station-name token so it's still caught via Route 4's loose co-occurrence path
  (preserving that test's actual "missing main branch is inconclusive" purpose), and one
  parametrized case removed because it could only ever pass by relying on a synthetic git
  commit reproducing a real historical SHA — that exact SHA/key pair is already covered
  independently via `conformance_fixtures()`'s `allowlist_accc097e6a` golden-case row.
- `src/shared/packages/pyforge-doctor/tests/unit/test_landing_evidence_conformance.py` —
  regenerated against the updated shared `conformance_fixtures()` golden set.
- `src/shared/packages/pyforge-marshal/tests/unit/{test_identity.py, test_promotion.py,
  test_status.py, test_deploy.py, test_land.py, test_dispatch_landing.py,
  test_landing_evidence_conformance.py}` — updated/extended for the `{slug}`-scoped template,
  the branch-corroboration requirement, and the removed herald policy override.

## Tasks & Acceptance

### Execution

| File | Action | Rationale |
|---|---|---|
| `pyforge-core/landing_evidence.py` | Add `project_slug` param to `parse_templated_merge_subject`; add branch corroboration to `parse_story_direct_commit_subject`; thread both through `classify_merge_subject`/`classify_commit`/`merged_story_keys` | Binding surface named in the Tier-2 spec; the shared grammar is the single source of truth all stations read |
| `pyforge-marshal/core/identity.py`, `core/policy.py` | `{slug}` template token + new repo default template | Marshal is the template's owner/renderer |
| `pyforge-marshal/core/promotion.py`, `cli/deploy.py`, `dispatch_land.py`, `cli/land.py` | Thread `project_slug`/`branch` into all grammar call sites | Keep marshal's own classification/render call sites in sync with the new signature |
| `pyforge-herald` `marshal-policy.toml` | Remove redundant per-project template override | The repo default now already carries `{slug}` scoping |
| `pyforge-doctor/sources/marshal.py`, `sources/ledger.py` | Pass `project_slug` at the two call sites | Doctor duplicates the grammar-reading logic by design (module-independence rule) rather than importing marshal |
| Test files (core, marshal, doctor) | Add/adjust fixtures for scoped template + branch corroboration; regenerate conformance suite | Prove the fix without re-attributing any real landed history |

### Acceptance Criteria

- **Given** atlas's `Merge 23-N into main` commits on `main`, **When** `merged_story_keys('pyforge-herald', ...)` is computed against today's `origin/main`, **Then** 23.1/23.2/23.5/23.6 are no longer included (they were never herald's own template-rendered subjects).
- **Given** steward's bare `Story 48.2:` / `Story 48.4:` commit subjects with no marshal-owned branch, **When** `pyforge-marshal`'s landing evidence is classified, **Then** 48.2/48.4 no longer classify as marshal-landed.
- **Given** every `done` row across all eight tracked ledgers that has real landing evidence (grandfathered SHA allowlist, or a branch/template shape that actually corroborates its own station), **When** classified against `git log origin/main`, **Then** it still classifies — no regression in true positives.
- **Given** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` and `pixi run --frozen -e pyforge-ci pyforge-deps-test`, **When** run against this branch, **Then** both are green (MRS-GATE-010 binds the dispatch gate to the marshal suite).

## Spec Change Log

_(none — no bad-spec loopback occurred)_

## Review Triage Log

### 2026-09-18 — Review pass

verdict counts: high 8, medium 1, low 6, false 3, maybe-false 0 (total 18)

Root cause groups: **Group A** (doctor's `sources/ledger.py` / `sources/marshal.py`
duplicate `_MERGE_SUBJECT_TEMPLATE` fallback constants were never updated to the
`{slug}`-scoped default this story introduces, and `ledger.py` additionally carried an
exclusionary guard predicated on the stale constant's literal value) draws 8 independent
findings across all 4 review layers — routed and patched as one change. All other findings
are single-finding groups.

- `[high]` `[patch]` Blind Hunter #2: `doctor/sources/marshal.py`'s Route 2
  (`_keys_from_merge_subjects`) reads a stale, un-scoped `_MERGE_SUBJECT_TEMPLATE =
  "Merge {key} into main"` as its no-override fallback, reproducing this story's own
  cross-station false-positive bug inside doctor — a foreign station's old-style bare
  subject can misclassify as this project's own landing. — Group A.
- `[high]` `[patch]` Blind Hunter #3: `doctor/sources/ledger.py`'s
  `_merged_ids_for_project` guards `if template != _MERGE_SUBJECT_TEMPLATE:` against the
  same stale constant, which — once the constant is merely updated in place — would
  skip the templated match for every no-override project unconditionally, silently
  failing to recognize that project's own correctly `{slug}`-scoped landing (a false
  negative, the mirror-image bug). — Group A.
- `[high]` `[patch]` Edge Case Hunter #3 (JSON): re-confirms Blind Hunter #2 independently
  via `_keys_from_merge_subjects(target, ("Merge 23-1 into main",),
  project_slug="pyforge-herald")` returning a misclassified key against the pre-patch
  constant. — Group A, same root cause as BH#2.
- `[high]` `[patch]` Edge Case Hunter #4 (JSON): re-confirms Blind Hunter #3 independently
  by tracing `_merged_ids_for_project`'s guard against a no-override project's own
  `{slug}`-scoped subject. — Group A, same root cause as BH#3.
- `[high]` `[patch]` Edge Case Hunter #5 (deletion-check): flags the removal of
  `ledger.py`'s `if template != _MERGE_SUBJECT_TEMPLATE:` guard for independent
  verification per the deletion-check protocol. Verified: the guard's own historical
  rationale (the 2026-09-18 "3 findings into 306" incident) no longer applies once the
  template is `{slug}`-scoped, because `parse_templated_merge_subject` self-scopes
  internally — removal is the correct fix, not an accidental regression. — Group A.
- `[high]` `[patch]` Verification Gap Reviewer, main finding: doctor's two independent
  duplicate copies of the grammar-reading logic are a regression gap relative to this
  story's own Acceptance Criteria and intent-contract "Always" boundary — neither
  `pyforge-marshal-test` nor `pyforge-deps-test` (the two commands named in the Tier-2
  spec's Verification section) exercises doctor's code at all, so the stale-constant bug
  was reachable without either verification command going red. — Group A. Demonstration:
  `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` added as an explicit
  additional regression command (already recorded in this spec's own Verification
  section from the implementation pass).
- `[high]` `[patch]` Verification Gap Reviewer, "Other findings": `marshal.py`'s Route 4
  loose co-occurrence fallback (station name + epic.seq substring match) coincidentally
  — not by design — masked Route 2's staleness for `pyforge-<station>`-shaped slugs,
  since the station short name is a substring of the scoped value. Folded into the Group
  A patch rather than a separate code change: once Route 2's constant is corrected, this
  masking dependency is moot (Route 2 now classifies correctly on its own, so whether
  Route 4 would also coincidentally catch the same case is no longer load-bearing). No
  code comment added, since there is nothing left to warn about once Group A lands.
- `[high]` `[patch]` Intent Alignment Auditor: the intent-contract's "Always" boundary —
  "every `done` row of all eight tracked ledgers with real landing evidence still
  classifies" — is violated by doctor's independent copies of the grammar carrying a
  stale/asymmetric template, since a real, correctly `{slug}`-scoped landing for a
  no-override project would silently stop classifying under `ledger.py`'s guard. — Group
  A.
- `[medium]` `[patch]` Blind Hunter #8: the Tier-2 spec's `status: 'ready'` and the
  `sprint-status-ledger.yaml` entry (`backlog`) were not advanced to reflect this story's
  completion, unlike sibling stories 50.1–50.3 (already `done`). Verified true. Patched:
  Tier-2 spec `status: 'done'` (+ `updated:`), ledger entry `done`.
- `[low]` `[patch]` Blind Hunter #1: `pyforge-marshal` and `pyforge-doctor`'s
  `marshal-policy.toml` per-project `merge_subject_template` overrides are now fully
  redundant with the `{slug}`-scoped repo default (herald's own override was already
  removed the same way in this story's implementation pass). Patched: both overrides
  removed, comments updated to mirror herald's.
- `[low]` `[patch]` Blind Hunter #5: `test_hand_landed_commit_subject_on_main_suppresses_
  the_false_green`'s docstring was rewritten to describe the NEW (opposite) behavior, but
  the function name still says "suppresses" — stale naming, not a logic bug. Patched:
  renamed to `test_bare_story_subject_on_main_no_longer_suppresses_the_false_green`
  (and its one cross-reference).
- `[low]` `[patch]` Blind Hunter #7: `_branch_belongs_to_project(branch: str, ...)`'s
  annotation doesn't reflect that its only caller with a real default,
  `parse_story_direct_commit_subject`, passes `branch: str | None = None`. Verified: the
  function body already handles non-str/`None` at runtime via `isinstance`; only the
  annotation was wrong. Patched: `branch: str | None`.
- `[low]` `[defer]` Blind Hunter #4 + #10 (same root cause, grouped): direct-commit branch
  corroboration (`_branch_belongs_to_project`) has no production call site that supplies
  real branch data for the retrospective `git log origin/main` subject-only scan use
  case — confirmed via `dispatch_landing.py`/`dispatch_land.py`, whose only caller deals
  with a different, templated-subject self-consistency pre-flight check, not this shape.
  Deferred: pre-existing design gap, not caused by this story (the story's own default
  `branch=None` already refuses safely per its own docstring); a genuine fix needs a new
  branch-data source for the scan use case, which is more than a trivial patch and out of
  this story's scope.
- `[low]` `[reject]` Blind Hunter #6: no direct unit test exercises
  `_instantiate_slug`'s validation/error branches in isolation. Rejected: unlikely to be
  hit given the fixed, small set of call sites that already exercise it indirectly
  end-to-end (`conformance_fixtures()` + the new scoping tests), and a direct test would
  be speculative coverage of paths with no live-code caller variance, not a trivial fix.
- `[false]` `[reject]` Blind Hunter #9: claimed `_ATLAS_23_SUBJECTS` in
  `test_promotion.py` (`range(1, 10)`, i.e. 9 subjects) is "synthetic" versus "the seven
  real atlas commits". Refuted: `git log origin/main` shows exactly 9 real
  `Merge 23-N into main` commits (23-1 through 23-9) — the fixture is factually accurate,
  not synthetic.
- `[false]` `[reject]` Edge Case Hunter #1: claimed a `commit_sha` + `branch` fixture
  combination in `test_conformance_matrix` would silently skip branch corroboration.
  Refuted: read `conformance_fixtures()` in full (16 rows) — the only 3 `commit_sha`
  fixtures are all `RECOVERY_COMMIT_ALLOWLIST` shape and none carry a `branch` key; the
  claimed combination does not exist today.
- `[false]` `[reject]` Edge Case Hunter #2: same claim restated against doctor's mirrored
  `test_doctor_conformance_matrix`. Refuted for the same reason — both suites read the
  identical shared `conformance_fixtures()`.

## Design Notes

- Doctor's `sources/marshal.py` / `sources/ledger.py` intentionally duplicate small pieces of
  the landing-evidence grammar-reading logic (their own `_project_merge_subject_template`
  helpers) rather than importing `pyforge.marshal`, per the Charter §6 module-independence
  rule ratified 2026-07-28 — "a regression verdict assembled from Marshal's own code would be
  Marshal's self-report wearing Doctor's badge." This story's doctor-side fix is therefore
  necessarily a parallel, local fix at each duplicate call site, not a shared-code change.
- Doctor's Route 3 (`_keys_from_main_commits`) carries an inline comment noting it "replaces
  the private `<slug>` + `story <e>.<s>` subject needle dialect" — i.e. the pre-shared-grammar
  Route 3 already required slug+story-num co-occurrence, and an earlier story's port to the
  shared `classify_commit` grammar had dropped that scoping. This story's branch-corroboration
  fix closes that regression for doctor as well as marshal, confirmed via three updated
  `test_sources_marshal_story_status.py` fixtures.
- `_RECOVERY_ALLOWLIST_KEYS` (pre-existing, not added this story) is the grandfathering
  mechanism for real historical commits that predate station-scoped subjects; it is checked
  before any subject-text parsing in `classify_commit`, so no live history is re-attributed.

## Verification

### Commands

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 8078 passed, 1 skipped, 12 deselected (unchanged by the review pass's patches).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — 130 passed, 3 skipped (unchanged by the review pass's patches).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — 1726 passed, 1 skipped (not
  named in the Tier-2 spec's Verification section, but run as an additional regression check
  since doctor duplicates the grammar-reading logic at two call sites; confirmed green.
  Review pass: 1723 → 1726 passed, +3 net new tests added while fixing Group A's stale
  doctor constants — see Review Triage Log).
- `pixi run --frozen -e pyforge-core pyforge-core-test -k landing_evidence` — 34 passed
  (review pass: re-run in isolation after the `_branch_belongs_to_project` type-annotation
  fix, since the full suite's 6 pre-existing unrelated failures — confirmed identical at
  the branch's merge-base with `main`, not in scope for this story — make the full-suite
  count noisy for this file's own regression signal).

### Manual checks

- [x] `merged_story_keys('pyforge-marshal', ...)` against live `origin/main` no longer
      contains 48.2/48.4 via steward's bare, un-scoped `Story 48.2:`/`Story 48.4:` direct
      commits. Verified by isolating those two commits' subjects and re-running
      `merged_story_keys` against both the pre-story merge-base
      (`3371ab79dd7305b7e2ac34efce2dc33578460010`, in a detached worktree) and the current
      tree: old code returns `['48.2', '48.4']` from that isolated input; new code returns
      `[]`. (marshal's full live key set no longer contains any `48.x` key at all — steward
      never had a genuinely marshal-scoped landing for either.)
- [x] `merged_story_keys('pyforge-herald', ...)` against live `origin/main` no longer
      contains 23.1..23.6 **via atlas's contaminating bare `Merge 23-N into main`
      commits**. Verified the same isolate-and-compare way: old code returns all nine of
      `23.1..23.9` from atlas's 9 commits alone; new code returns `[]` from that same
      isolated input. Herald's full live key set still legitimately contains
      23.1/23.2/23.5/23.6 — confirmed via `git log` that herald has its OWN genuinely
      `pyforge-herald/23-N`-scoped merge commits for exactly those four, independent of
      atlas's contamination; the fix removes the ambiguous second (wrong) source, not the
      station's real evidence. Epic 50's Problem statement uses "marked ... as merged" to
      mean atlas's contribution specifically; the AC row's shorthand is precise once
      disambiguated this way.
- [x] Every `done` row of all eight tracked ledgers with real landing evidence still
      classifies against `git log origin/main --format=%s`. Verified pre-review via a
      full old-vs-new trace across all 8 projects' `done` rows
      (`/tmp/s504_full_trace.txt`, 153 rows): every row whose classification changed
      between old and new code was multi-station-contaminated under old code (matched by
      more than one station simultaneously, i.e. never station-exclusive evidence to begin
      with) — zero rows lost real, single-source evidence. Re-confirmed unaffected by this
      review pass's patches, since none of them touch `pyforge.core.landing_evidence` or
      `pyforge.marshal.core.promotion` beyond the pre-existing, already-verified
      `_branch_belongs_to_project` type-annotation fix (no behavior change).

## Auto Run Result

**Summary:** `pyforge.core.landing_evidence`'s templated-merge and direct-commit parsers
now self-scope to the station that rendered them (`{slug}` in `merge_subject_template`,
branch corroboration for the bare `Story N.M:` shape), closing the two live cross-station
false-positive incidents named in the intent (atlas's bare `Merge 23-N into main` commits
no longer contaminate herald's classification; steward's bare `Story 48.2:`/`Story 48.4:`
commits no longer contaminate marshal's). The review pass additionally found and fixed a
second-order instance of the same bug class inside `pyforge-doctor`'s two independent
duplicate copies of the grammar-reading logic, which the implementation pass's own named
Verification commands could not have caught (neither exercises doctor's code).

**Files changed (review pass, beyond the implementation pass's own Code Map):**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ledger.py` — updated the
  stale `_MERGE_SUBJECT_TEMPLATE` fallback to the `{slug}`-scoped default and removed the
  now-obsolete exclusionary guard in `_merged_ids_for_project` (it was causing a false
  negative for every no-override project's own genuine landing).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py` — updated the
  same stale fallback constant (Route 2 had no guard to remove).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_ledger_direction.py` — split
  the stale `test_no_policy_file_never_attempts_the_bare_default_template` into a
  correctly-named legacy-bare-subject-still-refuses test plus a new positive test for the
  no-override scoped-default case.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_marshal_story_status.py` —
  added the mirrored pair of tests for Route 2; renamed
  `test_hand_landed_commit_subject_on_main_suppresses_the_false_green` to
  `test_bare_story_subject_on_main_no_longer_suppresses_the_false_green` (name no longer
  matched its already-rewritten assertion).
- `src/shared/packages/pyforge-core/src/pyforge/core/landing_evidence.py` —
  `_branch_belongs_to_project`'s `branch` parameter annotated `str | None` to match what
  its only caller with a real default actually passes.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml`,
  `_bmad-output/projects/pyforge-doctor/planning-artifacts/marshal-policy.toml` — removed
  the now-redundant per-project `merge_subject_template` overrides (mirroring herald's own
  removal already done in the implementation pass).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-50-4-landing-evidence-carries-the-station-in-every-shape.md`
  — Tier-2 spec `status: 'ready'` → `'done'` (+ `updated:`).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml` —
  `50-4-...`: `backlog` → `done`.

**Review findings breakdown (18 findings across 4 layers, verdict counts: high 8, medium 1,
low 6, false 3, maybe-false 0):**
- **Patched (11 findings, 4 groups):** Group A (8 findings, high) — doctor's stale
  `_MERGE_SUBJECT_TEMPLATE` duplicates; Group B (1, low) — redundant policy overrides;
  Group C (1, low) — stale test name; Group D (1, medium) — stale Tier-2 spec/ledger
  status; plus the standalone Group G (1, low) — `_branch_belongs_to_project` type
  annotation. Full detail: see Review Triage Log above.
- **Deferred (2 findings, 1 group):** Blind Hunter #4 + #10 — direct-commit branch
  corroboration has no production caller supplying real branch data for the retrospective
  `git log`-only scan use case. Pre-existing gap, not caused by this story (this story's
  own default already refuses safely with no branch data); a real fix needs a new
  branch-data source and is out of this story's scope.
- **Rejected (5 findings):** Blind Hunter #6 (low — speculative test coverage of
  `_instantiate_slug`'s validation branches, no live caller variance to justify it);
  Blind Hunter #9 (false — `_ATLAS_23_SUBJECTS`'s 9-commit fixture is factually accurate,
  refuted against live `git log`); Edge Case Hunter #1 and #2 (false — the claimed
  `commit_sha` + `branch` fixture combination does not exist in `conformance_fixtures()`
  today).

**Follow-up review recommendation: `true`.** This pass patched a `high`-verdict group on a
first pass (Group A). Named unverified risk: there is no automated check that doctor's two
independently-duplicated `_MERGE_SUBJECT_TEMPLATE` fallback constants stay in sync with
`pyforge-marshal/core/policy.py`'s `DEFAULT_POLICY["merge_subject_template"]` — this is the
exact drift that caused Group A in the first place, and the module-independence rule
(Charter §6) deliberately forbids fixing it with a shared import. A future change to the
repo-default template would silently re-open this class of bug in doctor until a subject
actually exercises the mismatch. Not fixed in this pass (a drift detector would be new
scope, not a patch to this story's own diff); recorded here for a follow-up review or a
dedicated doctor drift-check story to pick up.

**Verification performed:** see `## Verification` above (Commands: marshal/deps/doctor/core
suites all green after the review pass's patches, doctor's count moving 1723 → 1726 to
reflect the +3 net new tests; Manual checks: all 3 re-verified empirically against live
`origin/main` via an isolate-and-compare old-vs-new-code trace, described in detail above).

**Residual risks:** (1) the doctor-constant drift-detection gap named above under
Follow-up review recommendation; (2) the deferred branch-corroboration production-caller
gap (Blind Hunter #4/#10) remains open by design, tracked via this Review Triage Log
rather than a new ticket since no BMAD story currently owns it.
