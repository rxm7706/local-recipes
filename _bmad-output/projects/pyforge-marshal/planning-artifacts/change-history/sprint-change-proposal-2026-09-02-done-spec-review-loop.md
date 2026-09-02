---
date: 2026-09-02
trigger: docs/dreams/marshal-single-story-dispatch.md
kind: addendum
---

# Sprint Change Proposal — Done-spec must not review-loop (CAP-11)

## Why

2026-09-02 `drain_to_zero` (cursor) re-ran `bmad-build-auto` on already-`done`
specs. Steward 41.2 wrote 27 review commits while PR #1017 was DIRTY. Mason
13.2 wrote 18 review commits and never opened a PR. `followup_review_recommended:
false` was ignored. Ledger on `main` stayed `backlog`, so the fleet supervisor
kept launching.

## Adjustment

**Direct** — Dream addendum 2026-09-02; CAP-11 on
`spec-marshal-single-story-dispatch`; Epic 29 Stories **29.1–29.2**; ledger
`backlog`; queue after 28.24.

**v1 locks:**

- Local `.claude/skills/bmad-build-auto/` is in scope. Vendored `bmad_loop` is not.
- `done` + `followup_review_recommended: false` → HALT, no commit.
- `done` + `true` → one follow-up, then force false.
- 0-patch review → no commit.
- Harness `done` → CAP-4 only. Land fail → escalate, never another session.

## Out of scope

Shrinking `max_followup_reviews`. Deps:/SIGTERM (`marshal-dependency-aware-dispatch`).
A second landing path.
