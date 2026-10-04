---
title: "41.5: A new story reopens its done epic without reading as a ledger regression"
type: 'fix'
created: '2026-10-04'
status: 'done'
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

**Approach:** in both sources, an `epic-N` key that leaves `done` is not a regression when the newer side holds a story of epic N that is absent from the older side and is not `done`. That is a story just added to the epic. The newer side must also read the epic `in-progress`, the only value the roll-up writes for that reopen. In every other case the epic key is still judged as today: a bad roll-up with no new story, a deleted epic key, or an epic going non-done because one of its own `done` stories regressed. A story key that leaves `done` is still always a regression. Keep the predicate in one place and have both sources use it. Correct the finding text so it no longer calls every key a story key.

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

- 2026-10-04 — Built by hand in the chain PR, so marshal Story 85.4 can reopen Epic 85. `epic_reopened_by_new_story` in `sources/ledger.py` is shared by `ledger-regression` and `MARSHAL_DURABILITY`. Gates, local, read from exit codes:
  - `pyforge-doctor-test`: 3266 passed.
  - `lint-types`: rc 0.
  - `spec-surface-check`: rc 0, after memlog reconciles and scoped stamps of `spec-pyforge-doctor`, `spec-pyforge-core` and `spec-pyforge-marshal`.
  - `ledger-regression-check` on the branch that reopens marshal `epic-85`: rc 0, where it was rc 2 before the change.
  - Mutation: removing the rule from `_check`, removing it from `marshal.gather`, or dropping the not-done clause each fails a test.
  - An independent review ran next; see the entry below.

### 2026-10-04 — Independent review (adversarial, on 0c52d32115); verdict SEND BACK; fixed on the branch
- verdicts: 4 findings — high 1, medium 1, low 2, false 0. Mutants: 8 of 10 killed; the two survivors showed the test gaps in findings 1 and 4. All three 2026-10-03 bad roll-ups replay as `done-key-regressed`.
- findings:
  - `[high]` `[fix]` `sources/marshal.py`: `after.get(k) not in TERMINAL` is also true for a deleted key, so `MARSHAL_DURABILITY` excused a deleted `epic-N` beside a new story. That breaks this spec's Never list. Fixed: the shared predicate excuses an epic only when `after` reads it `in-progress`, and a deleted key reads `None`. Test: `test_durability_still_reports_a_deleted_epic_key_beside_a_new_story`.
  - `[medium]` `[fix]` The predicate ignored the epic's new value, so `done -> backlog` (the 2026-10-03 bad-roll-up value) or `done -> blocked` beside a new story was excused. The roll-up writes only `in-progress` for this reopen. Fixed by the same `in-progress` requirement. Test: `test_a_reopen_to_a_value_the_roll_up_never_writes_is_still_a_regression` (backlog, blocked).
  - `[low]` `[fix]` A re-key line `X -> Y` whose `X` survives at head dropped `X` from the remapped base, so `X` looked new and reopened its epic. Fixed in two places:
    - the predicate receives every base key under both its own name and its re-keyed one;
    - such a line is now `rekey-map-dangling` (`X still in HEAD`), so the story's own regression, hidden by the remap since Story 25.3, is no longer silent.
    Test: `test_a_re_key_line_whose_old_key_survives_neither_hides_the_story_nor_reopens_the_epic`.
  - `[low]` `[fix]` The `not in before` clause was unpinned. Test: `test_an_epic_reopened_by_its_own_story_regressing_reports_both_keys` (keys `9-2-second`, `epic-9`).
- re-verification after the fixes:
  - `pyforge-doctor-test`: 3271 passed.
  - `lint-types`: rc 0.
  - Mutants: dropping the `in-progress` clause, the `not in before` clause, the base-key union, or the surviving-old-key dangling rule each fails a test.
  - Replaying `1be676d263`, `fd328844d6` and `cc137c9faa` still reports `done-key-regressed`, naming `epic-66`, `epic-35` and `epic-17`.

### 2026-10-04 — Re-review of the fixes (same reviewer, on 6bc284269d); verdict SEND BACK on one new finding; fixed with the reviewer's verified change
- verdicts: findings 1–4 confirmed fixed (P1–P4 now FAIL as intended; M4 and M10 killed). New: high 1.
- findings:
  - `[high]` `[fix]` The new surviving-old-key `rekey-map-dangling` rule also flagged renumbering chains. In a compaction such as `epic-13 -> epic-12` with `epic-12 -> epic-11`, the old key survives as another line's new name. Replaying the real atlas fold `rekey-2026-09-17.md` (91 lines) over its branch and merge ranges gave 20 false dangling lines; the other 8 real maps were unaffected. Fixed: a surviving old key that is also a target in the map is a chain, not a copy (`old not in mapping.values()`). That clause also covers identity lines, so the redundant `old != new` guard is gone. Tests: `test_a_renumbering_chain_in_a_fold_map_is_not_dangling` and `test_an_identity_line_in_a_fold_map_is_not_dangling`.
  - `[low]` `[accept]` Mutant N2 (raw base keys only) survives and is harmless. The re-keyed names only decide whether a not-done story moved into a done epic by a map excuses that epic's reopen; the union is the conservative choice.
  - `[low]` `[accept]` A story's regression behind a copy line surfaces as the `rekey-map-dangling` FAIL, not as a `done-key-regressed` key. The lane goes red either way.
- re-verification after the fix:
  - `pyforge-doctor-test`: 3273 passed.
  - `lint-types`: rc 0.
  - Mutant: dropping the chain clause fails a test.
  - Replay: the atlas fold ranges (`86d1cdf3ee`, `93bcba96dc`) read `ok`. `1be676d263`, `fd328844d6` and `cc137c9faa` still read `done-key-regressed`. The reviewer had run the same change over all 18 real-map ranges: all `ok`.
