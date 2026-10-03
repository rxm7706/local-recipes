---
title: "83.18: A re-dispatched send-back waits for its landing review"
type: 'fix'
created: '2026-10-03'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_harness_done.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** On 2026-10-03 herald Story 35.1 was sent back after a landing review and re-dispatched. Its supervisor verified the second pass and auto-landed it (PR #1796) about seven minutes after CI went green, before the operator reviewed it; the post-landing review found two rows closed on thin evidence, and the follow-ups had to be chained as herald 35.2. Dispatch has no way to say "verify, then wait for the review". The operator's workaround, drafting the PR, turns the landing into a refusal (MRS-DISP-020), and a refused landing with an open PR trips Story 83.4's hold on every overlapping story of that station.

**Approach:** A story spec can declare `landing_review: required` in its frontmatter (the operator's send-back sets it), and `marshal factory dispatch` takes a `--hold-landing` flag. Either holds the landing: the supervisor verifies, pushes, opens (or keeps) the PR as a draft, journals a `dispatch-land` verdict `held-for-review` naming the PR, and exits. A held landing is not a refusal: no MRS-DISP-020, and no Story 83.4 hold. After the review, the operator marks the PR ready (or sets `landing_review: passed`) and re-dispatches; Story 83.7's land-only path then lands it.

Ledger key: `83-18-a-re-dispatched-send-back-waits-for-its-landing-review`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- the dispatch landing path (Stories 51.2, 83.4, 83.7). A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a story spec with `landing_review: required` When dispatch verifies the session's work green Then the PR is a draft, nothing merges, the journal records a `dispatch-land` verdict `held-for-review` naming the PR, and `dispatch status` reports the story as held for review (not refused)
- Given `marshal factory dispatch --hold-landing` on a story with no such key When verification passes Then the landing is held the same way
- Given a held story When another story of that station is dispatched Then Story 83.4's refused-landing hold does not fire for it
- Given a held story whose PR the operator marked ready (or whose spec reads `landing_review: passed`) When it is re-dispatched Then it takes Story 83.7's land-only path and lands with the landing subject `Merge <slug>/<key> into main`
- Given a story with neither the key nor the flag When dispatch runs Then landing is unchanged
- Given the hold rule removed When its new tests run Then they fail (mutation)

## Boundaries & Constraints

**Always:** Journal the hold; keep the PR a draft while held; read the key from the worktree's own spec.

**Never:** Never merge a held story. Never treat a hold as a refusal. Never change landing for a story that asks for no hold.

</intent-contract>

## Binding

Parent: Story 83.7 (land-only re-dispatch) and Story 83.4 (the refused-landing hold).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (night, last) entry.
Ledger key: `83-18-a-re-dispatched-send-back-waits-for-its-landing-review`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 at the operator's request ("yes chain both fixes").

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
