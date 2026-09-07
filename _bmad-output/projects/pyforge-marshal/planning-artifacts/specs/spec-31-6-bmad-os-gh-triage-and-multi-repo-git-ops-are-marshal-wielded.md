---
title: 'bmad-os-gh-triage and multi-repo-git-ops are marshal-wielded'
type: 'chore'
created: '2026-09-07'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
deferred:
  - summary: >-
      The new `note:` field on DW-HYGIENE-2026-09-05-1 is not in pyforge-doctor's chain.py
      `_KNOWN_FIELD_KEYS` closed vocabulary, so `classify_tier3_entries` silently folds it into
      the preceding `evidence:` field instead of keeping it as its own field.
    evidence: |-
      Verified real (edge-case-hunter finding, independently confirmed): `_KNOWN_FIELD_KEYS` in
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py:1967-1971 lists
      source_spec/summary/evidence/origin/location/severity/reason/status/resolution/decision/
      seen-again/promoted/found_by/raised/verified -- no `note`. But this is pre-existing, not
      introduced by this story: two unrelated prior entries in the same ledger already use a
      `note:` field the same way (DW-SURFACE-2026-08-08-1 and -2, both pre-dating this diff), so
      the parser gap already existed and this story's usage merely follows established (if
      imperfect) local convention rather than worsening it. Fixing the parser's vocabulary is a
      pyforge-doctor change, out of this XS docs story's scope.
    location: >-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py:1967
    severity: low
baseline_revision: '317228f3a382bc11453440362726c4ae6d84374c'
---

<intent-contract>

## Intent

**Problem:** Steward has installed `bmad-os-gh-triage` (utility-skills, 46.2) and `multi-repo-git-ops`
(labs, 46.5), but only `bmad-os-gh-triage` has a routing line in marshal's persona skill; the
`multi-repo-git-ops` half of AD-2 routing (CAP-3) is still unlanded, and `DW-HYGIENE-2026-09-05-1`'s
open question -- whether `multi-repo-git-ops` covers the `marshal sweep` worktree/branch-hygiene
wish -- is unanswered.

**Approach:** Add one routing line to `bmad-agent-marshal/SKILL.md` naming both skills with the
story's own wording. Remove the now-stale `multi-repo-git-ops` entry from steward's AD-2 carve-out
set (its own docstring invites this the day the cited story lands the mention). Answer the
DW-HYGIENE question in the ledger: this repo has no `.gitmodules` (verified), so `multi-repo-git-ops`
(a submodule-branching/sync tool) structurally does not cover worktree/branch *retirement*
heuristics -- record that finding, do not resolve or close the DW item.

## Boundaries & Constraints

**Always:** Use the story's literal wording for the persona routing line. Leave `adoption-register.md`
§ 2 rows and the `AGENTS.md` pointer line untouched -- both already satisfy this story's Given/Then
(verified: rows 38/45 already name marshal + this story; `AGENTS.md:41` already carries the one
pointer line). Leave `CLAUDE.md` untouched. Leave the DW-HYGIENE-2026-09-05-1 entry's `status: open`
unchanged -- this story only answers the coverage question, it does not resolve the wish.

**Never:** Do not hand-edit `adoption-register.md` §2 rows (no change needed -- they are already
correct). Do not touch the Story 46.5 historical narrative paragraph in
`test_adoption_register.py`'s module docstring (lines 1-34) -- it is a dated, append-style record of
what was true at 46.5; correct only the *operative* carve-out comment/dict that describes today's
state. Do not build a `marshal sweep` verb or any new detector -- DW-HYGIENE-2026-09-05-1 stays a
future story's scope.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| AD-2 meta-test, both skills present | `.claude/skills/bmad-os-gh-triage/` and `.claude/skills/multi-repo-git-ops/` both exist; marshal persona mentions both; no other station persona mentions either | `test_skill_routing_matches_ad2_for_every_currently_provisioned_row` passes with the positive assertion now exercised for `multi-repo-git-ops` too (carve-out removed) | A regression (another persona accidentally mentioning either name) fails the exclusivity assertion, not silently passes |
| DW-HYGIENE-2026-09-05-1 coverage question | Ledger entry with `status: open`, no prior answer to the coverage question | A new note is appended answering "no coverage" with the `.gitmodules` evidence; `status` stays `open` | N/A |

</intent-contract>

## Code Map

- `.claude/skills/bmad-agent-marshal/SKILL.md` -- `## Utility skill routing (AD-2)` section (currently
  one line: "Marshal wields `bmad-os-gh-triage` (bmad-utility-skills; see adoption-register.md § 2).").
  Extend to also name `multi-repo-git-ops` (bmad-labs-skills) with the story's literal guidance text.
- `src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py:224-228` --
  `_ROUTING_STORY_NOT_YET_LANDED` dict currently carries `"multi-repo-git-ops": "marshal 31.6"`
  alongside `mcp-builder`/`slides-generator`. Remove that one entry (this story is landing the
  persona mention today) and trim the comment block above it (lines 207-223) so it names only the
  two still-unlanded siblings. Do not touch the module docstring's dated Story 46.5 paragraph
  (lines 25-33) -- historical record, not the operative state.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md`
  §2 lines 38 and 45 -- already name marshal + "marshal 31.6" for both skills; confirmed no edit
  needed (read verbatim before writing this spec).
- `AGENTS.md:41` -- already carries the one pointer line to the register § 2; confirmed no edit
  needed.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` lines 5817-5822
  (`DW-HYGIENE-2026-09-05-1`) -- append one `note:` line under the existing entry answering the
  coverage question (repo has no `.gitmodules`, confirmed via `git submodule status`;
  `multi-repo-git-ops`'s own SKILL.md description scopes it to submodule branching/commit/push/sync
  across a parent + service repos -- a different concern from the wish's KEEP/PRUNE/DELETE worktree
  and merged-branch retirement heuristics). `status: open` stays unchanged.
- `.claude/skills/multi-repo-git-ops/SKILL.md` and `.claude/skills/bmad-os-gh-triage/SKILL.md` --
  read for their real descriptions (confirmed: gh-triage = PR/issue triage via `gh` CLI;
  multi-repo-git-ops = submodule-based multi-repo branch/commit/push/sync) to ground the DW-HYGIENE
  answer and the routing line's phrasing.

## Tasks & Acceptance

**Execution:**
- `.claude/skills/bmad-agent-marshal/SKILL.md` -- replace the `## Utility skill routing (AD-2)`
  section's single line with text naming both skills and the story's exact guidance ("reach for
  `bmad-os-gh-triage` for PR/issue triage and `multi-repo-git-ops` for cross-repo landings (never for
  a `marshal land` the harness owns)") -- grounds marshal's use of each skill.
- `src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py` -- remove the
  `"multi-repo-git-ops": "marshal 31.6"` entry from `_ROUTING_STORY_NOT_YET_LANDED`; update the
  comment above the dict to name only the two remaining not-yet-landed skills and note that
  `multi-repo-git-ops` was removed 2026-09-07 by marshal 31.6.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` -- append a
  `note:` line to the `DW-HYGIENE-2026-09-05-1` entry recording the coverage finding (no, for the
  stated reasons); `status` unchanged.

**Acceptance Criteria:**
- Given the two skills installed by steward, when the marshal persona is read, then it names both
  `bmad-os-gh-triage` (PR/issue triage) and `multi-repo-git-ops` (cross-repo landings, never for a
  `marshal land` the harness owns).
- Given `adoption-register.md` § 2, when the two rows are read, then each names exactly one
  wielding station (marshal) and the story id -- already true, unchanged by this story.
- Given `pyforge-steward-test`'s `tests/meta/test_adoption_register.py`, when it runs after this
  story's edits, then `test_skill_routing_matches_ad2_for_every_currently_provisioned_row` and
  `test_multi_and_all_stations_rows_are_exempt_from_single_station_assertion` both pass, with the
  positive per-station assertion now exercised for `multi-repo-git-ops` (carve-out removed).
- Given `CLAUDE.md`, when this story's diff is inspected, then `CLAUDE.md` is byte-for-byte
  unchanged.
- Given `DW-HYGIENE-2026-09-05-1`'s open coverage question, when this story closes, then the ledger
  entry carries a note stating whether `multi-repo-git-ops` covers the `marshal sweep` wish, with
  its supporting evidence, and `status` is unchanged (`open`).

## Spec Change Log

## Review Triage Log

### 2026-09-07 — Review pass
- verdicts: 10 findings — high 0, medium 1, low 5, false 4, maybe-false 0
- findings:
  - `[false]` `[reject]` (blind-hunter) module docstring (lines 25-33, untouched) still says `multi-repo-git-ops` is "not-yet-landed... marshal 31.6" — evidence: this is a dated `Story 46.5 update:` historical narrative paragraph, exactly like every `(event)` entry in every `.memlog.md` in this fleet — append-only, never rewritten as later stories change the described reality. The operative comment immediately above `_ROUTING_STORY_NOT_YET_LANDED` (the one that actually governs today's behavior) was correctly updated. A dated historical paragraph reading differently from current state is the intended shape of this convention, not a defect; this story's own spec explicitly named this file as a "Never touch" boundary for exactly this reason.
  - `[false]` `[reject]` (verification-gap, same claim as above) same docstring-staleness claim, framed as "directly contradicts the diff's own updated comment a few lines below it" — evidence: same refutation — two dated narrations of the same fact at different points in time are not a contradiction under this repo's established append-only historical-log convention (confirmed against dozens of precedent entries in `spec-bmad-suite-lifecycle/.memlog.md` and this same test file's own prior `Story 46.1`/`Story 46.5` paragraphs, neither of which was ever rewritten when later stories superseded them).
  - `[false]` `[reject]` (blind-hunter) `sprint-status-ledger.yaml:173` still reads `blocked` for `31-6-...`, not flipped to `done` — evidence: refuted by two sibling stories in the identical situation — `31-4-...` and `31-5-...` are both `status: 'done'` in their own spec files yet both still read `backlog` in the live ledger today. `spec-marshal-single-story-dispatch`'s own Design Notes confirm CAP-4 "already triggers `sprint-ledger-sync` on every landing" — the ledger flip is a separate, land-time-triggered mechanism, never part of a story's own dev-loop diff.
  - `[false]` `[reject]` (verification-gap, same claim as above) same sprint-ledger claim, framed as "the diff does not flip the marshal ledger's status... despite its dependency being resolved" — evidence: same refutation as above (separate ledger-sync mechanism, confirmed via sibling stories 31-4/31-5's identical unflipped state).
  - `[medium]` `[patch]` (blind-hunter) no memlog entry anywhere records this story's landing, unlike every sibling sub-story of Epic 46/47 (46.1-46.5, each with a dated `(event)` entry in `spec-bmad-suite-lifecycle/.memlog.md`) and marshal's own Story 31.5 (which relayed to the same file) — evidence: confirmed by reading the memlog before this pass — no line mentioned `31.6` or `marshal`. Action: appended a new `(event)` entry to `spec-bmad-suite-lifecycle/.memlog.md` (the direct governing spec of CAP-3) recording the persona-routing closure, the steward-test carve-out removal, and the DW-HYGIENE answer, via `memlog.py append` so formatting/`touch()` semantics match every prior entry exactly (frontmatter `updated:` auto-bumped).
  - `[low]` `[reject]` (blind-hunter) the new persona routing line commits marshal to `multi-repo-git-ops` with no caveat that this repo currently has zero `.gitmodules`/submodules, so the routing structurally never fires today — evidence: real but not worth fixing — this story's own spec Boundaries mandate using the epics.md story's literal AC wording verbatim for this line; adding a caveat would deviate from that mandated text, adds complexity (a guard clause) rather than a direct fix, and no harmful outcome occurs (marshal simply won't invoke a skill whose precondition isn't met; the routing line is deliberately general/future-facing exactly like the sibling `bmad-os-gh-triage` clause beside it).
  - `[low]` `[reject]` (blind-hunter) grammar nitpick: "never for a `marshal land` the harness owns" reads awkwardly ("a `marshal land`" as a countable noun) — evidence: this exact phrase is lifted verbatim from `epics.md:4655`'s own Given/When/Then acceptance text, which this story's spec Boundaries explicitly mandate reproducing literally; changing it would be a deviation from spec-mandated wording for a cosmetic nitpick, not a fix.
  - `[low]` `[patch]` (blind-hunter) the test-file comment above `_ROUTING_STORY_NOT_YET_LANDED` lost precision when trimmed — it previously cited exact register row numbers ("rows 43-45") for the three carved-out names but was generalized to a vague "rows" after removing `multi-repo-git-ops`, instead of being updated to the two remaining rows' real numbers — evidence: confirmed against `adoption-register.md` § 2 today (`mcp-builder` = row 43, `slides-generator` = row 44, unchanged). Action: restored "rows 43-44" in the comment.
  - `[low]` `[reject]` (blind-hunter) both edited comment blocks are dense, single run-on sentences bundling several distinct facts, harder to scan than shorter statements — evidence: real stylistic observation but the fix requires restructuring prose (more than a direct correction/deletion), and it is unlikely a developer would be materially harmed reading this in everyday use — matches the existing density of every sibling `## Utility skill routing (AD-2)` line in this same file family (e.g. `bmad-agent-steward`'s two-pipeline routing sentence added by Story 46.4), so this is consistent with, not worse than, established local style.
  - `[low]` `[defer]` (edge-case-hunter) the new `note:` field on `DW-HYGIENE-2026-09-05-1` is not in pyforge-doctor's `chain.py` `_KNOWN_FIELD_KEYS` closed vocabulary, so `classify_tier3_entries` silently folds it into the preceding `evidence:` field — evidence: verified real (`_KNOWN_FIELD_KEYS` at `chain.py:1967-1971` has no `note`), but pre-existing and not introduced by this story — two unrelated entries earlier in the same ledger (`DW-SURFACE-2026-08-08-1`, `-2`) already use a `note:` field the identical way, unrelated to this diff. Recorded in this spec's frontmatter `deferred:` list; fixing the parser's vocabulary is a pyforge-doctor change, out of this XS docs story's scope.

## Design Notes

**Why remove the steward carve-out entry from a marshal story:** `_ROUTING_STORY_NOT_YET_LANDED`'s
own comment says "Remove a name from this set the same day its own cited story lands the persona
mention, never before" -- it names `marshal 31.6` as the cited story for `multi-repo-git-ops`
specifically. Steward's own prior stories (46.4, 46.5) removed their own analogous carve-out
entries directly in the landing story rather than via a memlog relay, since this is a mechanical,
self-referential test fixture (not a governed narrative doc like `cutover-readiness.md`, which
*is* relayed via memlog per Story 31.5's precedent). The exclusivity half of the check already runs
unconditionally regardless of the carve-out, so removing the entry only makes the check strictly
more thorough, never less safe.

**Why the DW-HYGIENE answer is "no coverage," not a new capability:** `multi-repo-git-ops`'s own
SKILL.md scopes it to git-submodule multi-repo systems (branch/commit/push/sync across a parent +
service repos it discovers from `.gitmodules`). This repo has no `.gitmodules` -- confirmed via
`git submodule status`. `DW-HYGIENE-2026-09-05-1`'s wish is a structurally different concern:
classifying and retiring worktrees/branches of the *same* repo (KEEP/PRUNE/DELETE by merge status,
ledger status, live-process detection). Recording "no" is itself the deliverable the story's
Given/When/Then asks for -- it does not imply building anything new.

## Verification

**Commands:**
- `pixi run -e pyforge-steward pyforge-steward-test -k test_adoption_register` -- expected: all
  tests in that file pass, including the two AD-2 tests now exercising `multi-repo-git-ops`'s
  positive branch.
- `pixi run -e pyforge-marshal pyforge-marshal-test` -- expected: full suite green (this story
  touches no marshal source, but confirms no regression).
- `git diff --stat 317228f3a382bc11453440362726c4ae6d84374c -- CLAUDE.md` -- expected: empty output
  (file untouched).
- `python3 -c "t=open('_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md').read(); assert 'multi-repo-git-ops' in t and 'bmad-os-gh-triage' in t"` -- expected: no assertion error (rows already present, confirming no accidental edit was needed there).

**Manual checks (if no CLI):**
- Read `.claude/skills/bmad-agent-marshal/SKILL.md`'s `## Utility skill routing (AD-2)` section and
  confirm it names both skills with the story's guidance wording.
- Read the `DW-HYGIENE-2026-09-05-1` entry in `deferred-work-ledger.md` and confirm the new note
  states plainly whether `multi-repo-git-ops` covers the wish, with evidence, and `status: open` is
  unchanged.

## Auto Run Result

**Summary:** Landed CAP-3's marshal-side skill routing: `bmad-agent-marshal/SKILL.md` now names
both `bmad-os-gh-triage` (PR/issue triage) and `multi-repo-git-ops` (cross-repo landings, never for
`marshal land`), using the story's own literal AC wording. Removed the now-stale
`multi-repo-git-ops` carve-out from `pyforge-steward`'s AD-2 test fixture, so
`test_skill_routing_matches_ad2_for_every_currently_provisioned_row` now genuinely exercises the
positive per-station assertion for that skill (verified directly, not vacuously). Answered
`DW-HYGIENE-2026-09-05-1`'s open coverage question in the deferred-work ledger: `multi-repo-git-ops`
does NOT cover the `marshal sweep` worktree/branch-retirement wish (this repo has no `.gitmodules`;
the skill's own scope is submodule branch/commit/push/sync, a different concern from worktree/branch
retirement heuristics) — `status: open` left unchanged. Review added a memlog entry recording this
landing (mirroring every sibling Epic 46/47 sub-story) and restored precise register-row citations
in the test file's comment.

**Files changed:**
- `.claude/skills/bmad-agent-marshal/SKILL.md` — extended the `## Utility skill routing (AD-2)` line
  to name both skills with the story's literal guidance wording.
- `src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py` — removed
  `"multi-repo-git-ops": "marshal 31.6"` from `_ROUTING_STORY_NOT_YET_LANDED`; updated the comment
  above it to name only the two remaining not-yet-landed skills with accurate register row numbers
  (43-44); left the dated Story-46.5 module-docstring paragraph untouched (historical record).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` — appended a
  `note:` line to `DW-HYGIENE-2026-09-05-1` answering the coverage question (no); `status: open`
  unchanged.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/.memlog.md`
  — new `(event)` entry recording this story's landing (review-triggered patch); frontmatter
  `updated:` auto-bumped by `memlog.py append`.
- This spec file — `deferred:` gained one item (the pre-existing `note:` field-key gap in
  pyforge-doctor's `chain.py`, not caused by this story).

Confirmed unchanged (per the spec's own Code Map claims, verified before and after implementation):
`adoption-register.md` § 2 rows 38/45, `AGENTS.md:41`, `CLAUDE.md` (byte-for-byte, confirmed via
empty `git diff --stat`), `sprint-status-ledger.yaml` (deliberately not flipped — a separate,
land-time `sprint-ledger-sync` mechanism per `spec-marshal-single-story-dispatch` CAP-4, confirmed
by two sibling stories 31-4/31-5 in the identical unflipped state despite being `done`).

**Review findings breakdown** (10 findings across blind-hunter, edge-case-hunter, verification-gap,
intent-alignment [0 findings, descriptive only, confirmed no material divergence]; full evidence in
`## Review Triage Log`):
- **Patched** (2 entries, both `low`/`medium`, not `high`): `medium` — no memlog entry recorded this
  landing (fixed: appended to `spec-bmad-suite-lifecycle/.memlog.md`); `low` — the test-file
  comment's register-row citation was generalized to a vague "rows" instead of the two remaining
  rows' real numbers (fixed: restored "rows 43-44").
- **Deferred** (1 entry, `low`, in this spec's frontmatter `deferred:`): the new `note:` field on
  `DW-HYGIENE-2026-09-05-1` isn't in pyforge-doctor's `chain.py` closed field-key vocabulary —
  verified pre-existing (two unrelated ledger entries already use `note:` the same way), not caused
  by this story.
- **Rejected** (7 entries, all `false` or `low`): two duplicate-root-cause pairs both `false` —
  the module docstring's dated "Story 46.5 update" paragraph reading differently from current state
  (this repo's universal append-only historical-log convention, not a defect) and the sprint ledger
  not being flipped to `done` (a separate land-time `sprint-ledger-sync` mechanism, confirmed via
  two sibling stories in the identical state); three `low` — a missing "never fires without
  submodules" caveat on the routing line, a grammar nitpick, and dense run-on sentence style — all
  rejected because fixing them would deviate from the story's own spec-mandated literal AC wording,
  or the fix is disproportionate to a cosmetic/negligible real-world impact.

**Follow-up review recommendation:** `false` — this pass patched one `medium` and one `low` entry;
per the first-pass rule, `true` requires either a patched `high` or two-or-more patched `medium`
entries, neither of which occurred here.

**Verification performed:**
- `pixi run -e pyforge-steward pyforge-steward-test -k test_adoption_register` — 7 passed, 1 skipped
  (pre-existing, environment-dependent, unrelated), re-run after the patch round.
- `pixi run -e pyforge-steward pyforge-steward-test` (full suite) — 1158 passed, 3 skipped, re-run
  after the patch round.
- `pixi run -e pyforge-marshal pyforge-marshal-test` (full suite) — 7510 passed, 12 deselected,
  re-run after the patch round.
- `git diff --stat <baseline> -- CLAUDE.md` — empty, confirmed twice (before and after the patch
  round).
- Directly exercised the AD-2 helper functions (`_station_shape`, `_persona_mentions`) against the
  live tree for `multi-repo-git-ops` — confirmed the positive per-station assertion is genuinely
  satisfied, not vacuously skipped.
- Confirmed `git submodule status` is empty and no `.gitmodules` exists in the repo root (grounds
  the DW-HYGIENE answer).
- Frontmatter of both edited memlog-adjacent files (this spec's `deferred:`, `spec-bmad-suite-lifecycle/.memlog.md`'s `updated:`) parses as valid YAML after the edits.

**Residual risks:** none beyond the recorded deferred item (pre-existing, low severity, out of
pyforge-marshal's scope to fix). The story deliberately leaves `DW-HYGIENE-2026-09-05-1` open and
builds no `marshal sweep` verb, matching its explicit "Never" boundary.
