---
title: "83.14: A manual merge mid-dispatch never strands the session's fixes"
type: 'fix'
created: '2026-10-03'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_completion.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** On 2026-10-03 the operator merged PRs #1773 (83.10) and #1764 (83.4) by hand while their re-dispatches were running. Each supervisor then read `story_merged_on_main` as true, declared the run `completed` and exited: one session kept running unsupervised, and the fix commits it made were never verified or pushed; the operator landed them through new PRs. The same read treats a story whose earlier branch head merged as finished even though the live branch has new commits.

**Approach:** A run's completion keys on its own branch: a story counts as merged for this run only when the run's current branch head (not an earlier head of the same branch) is on `main`. When an earlier head merged but the session is still live or the branch has commits past the merged head, the supervisor keeps supervising, then verifies and opens a new PR for the remaining commits instead of declaring completion.

Ledger key: `83-14-a-manual-merge-mid-dispatch-never-strands-the-session-s-fixes`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- the dispatch completion read (`story_merged_on_main`, Story 22.10's real-divergence rule). A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a dispatch whose branch's earlier head was merged by hand while the session is still live When the supervisor ticks Then it keeps supervising the session, and does not declare the run completed
- Given the session then finishes with commits past the merged head When the supervisor finalizes Then it verifies those commits and opens a new PR for them (landing subject `Merge <slug>/<key> into main`), never leaving them unpushed
- Given the run's own current head is on `main` When the supervisor ticks Then it completes as today
- Given the rule removed When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Decide from git facts about the run's own head. Journal the decision.

**Never:** Never leave a live session unsupervised. Never exit with unpushed commits on the story branch.

</intent-contract>

## Binding

Parent: Story 51.2 / Story 22.10 (completion and merge detection).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (night, later) entry.
Ledger key: `83-14-a-manual-merge-mid-dispatch-never-strands-the-session-s-fixes`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 at the operator's request.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
