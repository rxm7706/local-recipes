---
title: "A done spec HALTs unless follow-up is true"
type: "fix"
created: "2026-09-02"
status: "done"
updated: "2026-09-02"
review_loop_iteration: 0
followup_review_recommended: false
difficulty: small
context:
  - "_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md"
  - "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-single-story-dispatch/SPEC.md"
  - "docs/dreams/marshal-single-story-dispatch.md"
  - ".claude/skills/bmad-build-auto/step-01-clarify-and-route.md"
  - ".claude/skills/bmad-build-auto/step-04-review.md"
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Step 1 of `bmad-build-auto` treats `status: done` as “start a
fresh review” and resets `review_loop_iteration` to `0`. Step 4 writes
`followup_review_recommended: false` and never reads it. A 0-patch pass still
commits the spec. Steward 41.2 and mason 13.2 each produced a pile of
confirmatory write-backs.

**Approach:** Honor the flag in step 1. Cap follow-up at one. Do not commit
when the pass applied 0 patches. Touch only the in-repo skill copy.

## Acceptance Criteria

- Given `status: done` and `followup_review_recommended: false`, when
  `bmad-build-auto` is invoked on that spec, then it HALTs `done` with no
  step-04 review and no new commit.
- Given `status: done` and `followup_review_recommended: true`, when invoked,
  then at most one follow-up review runs and the flag is then `false`.
- Given a review pass with 0 findings triaged `patch`, when finalize runs,
  then `{spec_file}` is not committed solely as a write-back.
- Given the vendored `bmad_loop` tree, when this story lands, then it is
  unchanged.

## Boundaries & Constraints

**Never:** `scripts/bmad-switch`. Shrink `max_followup_reviews`. Edit
`bmad_loop` package sources. Re-open Epic 22.

Ledger key: `29-1-done-spec-halts-unless-followup-is-true`.

</intent-contract>

## Tasks

- [x] Step 1: `done` + `followup_review_recommended: false` → HALT `done`.
- [x] Step 1: `done` + `true` → one follow-up; force flag false afterward.
- [x] Step 4: 0-patch → do not commit a spec-only write-back.
- [x] Ledger `29-1-done-spec-halts-unless-followup-is-true` → `done`.

## Verification

Skill text names the HALT and the 0-patch no-commit rule. Grep the in-repo
skill: `done` + `false` HALTs; it no longer unconditionally EARLY EXITs to
step-04.

## Auto Run Result

Status: done

Summary: Local `bmad-build-auto` step-01 reads `followup_review_recommended`.
`done`+`false` HALTs with no edit/commit. `done`+`true` consumes the flag
then allows one review. Step-04 skips spec-only 0-patch commits and forces
the flag false after a done-spec follow-up. Vendored `bmad_loop` untouched.

Files changed:
- `.claude/skills/bmad-build-auto/step-01-clarify-and-route.md`
- `.claude/skills/bmad-build-auto/step-04-review.md`
- `.claude/skills/bmad-build-auto/spec-template.md`

Verification: `rg 'follow-up not recommended' .claude/skills/bmad-build-auto/step-01-clarify-and-route.md` matches; no remaining `fresh review pass` string.

## Source

Dream addendum 2026-09-02. CAP-11 harness half. Change proposal:
`sprint-change-proposal-2026-09-02-done-spec-review-loop.md`.
