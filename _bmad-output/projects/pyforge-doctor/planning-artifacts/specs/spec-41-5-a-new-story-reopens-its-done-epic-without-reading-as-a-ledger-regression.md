---
title: "41.5: A new story reopens its done epic without reading as a ledger regression"
type: 'fix'
created: '2026-10-04'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ledger.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py
  - scripts/promote_sprint_status.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the operator expects a done epic to reopen when a story is added to it. The two ledger tools disagree on that.

- **The sync reopens it.** `sprint-ledger-sync` (`scripts/promote_sprint_status.py` `apply_epic_rollups`, since marshal Story 28.24, 2026-09-10) recomputes every `epic-N` row from its stories. A new `backlog` story under `epic-85: done` therefore writes `epic-85: in-progress`.
- **The guard refuses it.** `ledger-regression` (`src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ledger.py` `_check`, `TERMINAL = {"done"}`; blocking in Detectors since the 2026-09-14 ruling) parses epic keys like story keys. It reports the reopen as `done-key-regressed: 1 story key(s) moved out of done`, which it is not. Measured on 2026-10-04: chaining marshal Story 85.4 under Epic 85 exited 2, with key `epic-85`, `done -> in-progress`.
- **The sibling has the same gap.** `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py` (`MARSHAL_DURABILITY`, working tree against `HEAD`, around :510) would flag the same reopen before the commit.
- **Epic keys still need guarding.** On 2026-10-03, three landing promotions on `main` (`1be676d263`, `fd328844d6`, `cc137c9faa`) dropped `epic-66`, `epic-35` and `epic-17` from `done` to `backlog` while every story in them stayed `done`. Main's Detectors went red on each push. Those were bad roll-ups, and the guard was right.

**Approach:** in both sources, an `epic-N` key that leaves `done` is not a regression when the newer side holds a story of epic N that is absent from the older side and is not `done`. That is a story just added to the epic. In every other case the epic key is still judged as today: a bad roll-up with no new story, a deleted epic key, or an epic going non-done because one of its own `done` stories regressed. A story key that leaves `done` is still always a regression. Keep the predicate in one place and have both sources use it. Correct the finding text so it no longer calls every key a story key.

Ledger key: `41-5-a-new-story-reopens-its-done-epic-without-reading-as-a-ledger-regression`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- The ledger-regression verdict, Story 6.4 (FR-15), and CAP-78 (judged at the merge-base). This is a defect of shipped behaviour, so it mints no new CAP. Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.

## Acceptance Criteria

- Given a base ledger with `epic-9: done` and its stories `done` When the head adds `9-3-new: backlog` and the sync's roll-up `epic-9: in-progress` Then `ledger-regression` reports `ok`
- Given a base ledger with `epic-9: done` and its stories `done` When the head moves `epic-9` to `backlog` with no new story (the 2026-10-03 shape) Then it reports `done-key-regressed` naming `epic-9`
- Given a head that adds a new story to epic 9 and also moves a `done` story of epic 9 out of `done` When it is judged Then the story key is reported; the new story never excuses another story's regression
- Given a new story that is already `done` When the epic leaves `done` anyway Then it is a regression; only a non-done new story reopens an epic
- Given the working tree reopens an epic the same way against `HEAD` When `MARSHAL_DURABILITY` runs Then it reports no regression, and it still reports the bad-roll-up shape
- Given the rule removed from either source When the tests run Then the reopen test fails (mutation)

## Boundaries & Constraints

**Always:**
- Keep `done` monotone for story keys.
- Keep one reopen predicate, shared by both sources.
- Keep the independence rule: read the tracked ledgers only, never `pyforge.marshal`.

**Never:**
- Never exempt epic keys wholesale. Never weaken the check for a story key, a deleted key or a re-key.
- Never change `promote_sprint_status.py`'s roll-up. It already does what the operator expects.

**Overlap:** Story 41.2 also edits `sources/ledger.py` and `sources/marshal.py` (one status parser, one terminal test). Whichever lands second keeps this rule.

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-04 entry.
- Epic: Epic 41.
- Ledger key: `41-5-a-new-story-reopens-its-done-epic-without-reading-as-a-ledger-regression`.
- Ledger status at mint: `backlog`.
- Deps: —.
- Minted 2026-10-04 at the operator's request: "if you add a new story under an epic that is closed or complete it should reopen the epic". Ships in one PR with marshal Story 85.4's chain, which is the first story to reopen a done epic.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild ledger-regression-check` — expected: exit 0 on the branch that reopens marshal `epic-85`.

## Review Triage Log

- No review has run yet.
