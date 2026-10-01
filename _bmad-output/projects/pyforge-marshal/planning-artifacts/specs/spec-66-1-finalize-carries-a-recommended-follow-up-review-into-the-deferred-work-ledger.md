---
title: '66.1: Finalize carries a recommended follow-up review into the deferred-work ledger'
type: 'fix'
created: '2026-09-28'
status: 'in-review'
baseline_revision: 'a240511f5b149a47d6972d4a335f591419d0d840'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** A dispatched `bmad-build-auto` session that ends `done` with `followup_review_recommended: true` has the flag copied into the tracked spec (CAP-250, Story 51.2), and then nothing acts on it. The flag's only reader in marshal is `core/dispatch_harness_done.followup_review_recommended` with `blocks_harness_relaunch`, called once in `cli/dispatch.py` (Story 29.2's land-only rule). That guard matters only when a `done` story is dispatched again, and a drain never does that: `core/dispatch_fleet.NON_IMPLEMENT_STATUSES` holds `done`, `station_backlog` drops it, and `factory drain --stories` refuses a `done` key with `MRS-DISP-032`. Finalize's intake step (`_run_deferred_work_intake` → `scripts/deferred_work_intake.py --fix`) reads only frontmatter `deferred:`. The bmad-loop path has a twin (Story 4.13: an unfinished follow-up is damped into a `review-budget-followup` block that `marshal land` promotes as `DW-FU-<story>`); the dispatch path has none. Story 51.3 then landed on 51.2's files with no review at all (`DW-FU-51-2-1`, hand-filed). Measured 2026-09-28: 210 tracked specs read `done` with the flag true, 181 of them carried by nothing.

**Approach:** finalize carries the recommendation into the station's tracked `deferred-work-ledger.md` at the moment the story lands. After the ledger promotion, `finalize_dispatch_land` reads the landed story's tracked spec on `origin/main` through `dispatch_core.spec_text_at_ref` (the reader it already uses to corroborate). When that spec reads `status: done` and `followup_review_recommended` is an explicit truthy (`core/dispatch_harness_done.followup_review_recommended`), it adds one row. Selection and rendering are pure functions in `core/deferred_work.py`, beside Story 4.13's loop twin:
- the id is `DW-FRR-<epic>-<seq><suffix>` via `core.identity.render_filename_slug` (the `DW-FRR-` prefix is used by no ledger; `DW-FU-<story>` already names spec-deferred and loop rows for the same story, e.g. `DW-FU-51-9`);
- the row carries `source_spec:` (the tracked spec, `planning-artifacts/specs/…` form), `summary:`, `evidence:` (the landing: story key, merge subject or sha when known), `location:` (the tracked spec path), `origin: dispatch-followup-review`, `severity: low` (the loop twin's severity), `promoted:` (date, "dispatch-land finalize") and `status: open`;
- idempotency uses a greedy token match over the ledger text (the `_tracked_promoted_ids` convention), so `DW-FRR-51-20` never hides `DW-FRR-51-2`.

The write happens inside the intake step's existing advisory lock and publish (`commit_paths_onto_remote_tip` onto `origin/main`, the primary's working copy restored), computed from the ledger text that publish replaces, so neither the intake's rows nor the new row can drop the other. An intake refusal or no-op still publishes the row. Finalize's `dispatch-land-finalize-resync` OBSERVATION payload gains the promoted id (`null` when none). A failed read or write is a non-gating `MRS-DISP-047` WARN in that payload, never a landing refusal after the merge.

Ledger key: `66-1-finalize-carries-a-recommended-follow-up-review-into-the-deferred-work-ledger`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-275 (FR-221).

## Acceptance Criteria

- Given 51.2's tracked spec text (`status: done`, `followup_review_recommended: true`) as the landed story's spec on `origin/main` and a fixture ledger with no `DW-FRR-51-2` When `finalize_dispatch_land` runs against fakes Then exactly one `### DW-FRR-51-2:` row is published, carrying `origin: dispatch-followup-review`, `source_spec` naming the spec, `location:` its path, `severity: low` and `status: open`, and the `dispatch-land-finalize-resync` payload names `DW-FRR-51-2`
- Given the ledger that run published When finalize runs again for the same story Then nothing is added and no second publish carries a new row
- Given the same spec with `followup_review_recommended: false`, with the key absent, or with a status other than `done` When finalize runs Then no row is added and the payload's promoted id is `null`
- Given a ledger already holding `DW-FRR-51-20` When 51.2 lands flagged Then `DW-FRR-51-2` is still added
- Given an intake run that also adds rows in the same finalize When both are published Then the published ledger holds the intake's rows and the new row
- Given `commit_paths_onto_remote_tip` raising `VcsCommandError` When finalize runs Then the payload carries a `MRS-DISP-047` WARN naming the failure and finalize's exit code is what it would have been without the flag
- Given the promotion call removed from `finalize_dispatch_land` When the 51.2 fixture runs Then no row is added and the test fails (mutation)

## Boundaries & Constraints

**Always:** Implement only the Surface named in `epics.md` Story 66.1. Keep selection and rendering pure in `core/deferred_work.py` (AD-4); every read and write stays in `dispatch_land_finalize/__main__.py` through its existing ports. Read the flag only through `core/dispatch_harness_done.followup_review_recommended` (explicit truthy only). Publish only onto `origin/main` through `commit_paths_onto_remote_tip`, under the lock the intake step already takes.

**Never:**
- Do not dispatch, schedule or launch a follow-up review; the carry is a tracked row.
- Do not change `scripts/deferred_work_intake.py` (spec-pyforge-doctor governs it) or the loop twin's `review-budget-followup` promotion.
- Do not refuse or fail a landing because the row could not be written; the merge has already happened.
- Do not write the row into the primary checkout's working tree and leave it there.
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`; do not run `scripts/bmad-switch`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| flagged landing | spec `done`, flag `true`, no `DW-FRR-<story>` | one row published; payload names the id | none |
| second finalize | row already present | nothing added | none |
| flag false / absent | spec `done`, flag `false` or missing | nothing added; payload id `null` | none |
| not done | spec `status` other than `done` | nothing added | none |
| id prefix collision | ledger holds `DW-FRR-51-20` | `DW-FRR-51-2` still added | none |
| intake also writes | intake adds rows | one publish holds both | none |
| spec unreadable at `origin/main` | `VcsCommandError` from `spec_text_at_ref` | nothing added | `MRS-DISP-047` WARN in the payload |
| publish fails | `VcsCommandError` from the publish | nothing lands on `origin/main`; primary copy restored | `MRS-DISP-047` WARN; exit code unchanged |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/deferred_work.py` -- Story 4.13's pure loop twin; the new dispatch twin sits beside it: `followup_review_id` (`DW-FRR-<epic>-<seq><suffix>` via `render_filename_slug`), `followup_review_candidate` (spec text -> candidate, reading status through `promotion.read_spec_status` and the flag through `dispatch_harness_done.followup_review_recommended`), `followup_review_to_promote` (greedy `DW-FRR-` token idempotency, `_tracked_followup_review_ids`), `render_followup_review_entry`, `append_ledger_entry`. No I/O, no clock (AD-4).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py` -- `_followup_review_carry` (the read: path through `_local_spec_rel_path`, text through `vcs.file_text_at_ref(ORIGIN_MAIN, ...)`), `_FollowupReviewCarry` (in/out holder), `_run_intake_script` (the intake script run, split out unchanged), `_carry_followup_row`, and `_run_deferred_work_intake(..., followup=)` publishing intake rows and the row in ONE `commit_paths_onto_remote_tip`; `finalize_dispatch_land` gains `clock` and the payload key `followup_review_promoted_id`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py` -- read-only: `story_spec_rel_path` / `spec_text_at_ref` are the spec reader's two halves.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py` -- read-only: `_promote_deferred_work` is the loop twin's impure edge (date from `ClockPort`, blank-line separation) this story mirrors.
- `src/shared/packages/pyforge-marshal/tests/unit/test_deferred_work.py`, `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_land_finalize.py` -- the tests; four existing finalize tests were narrowed (the carry reads the spec once more and warns on the same failed read) and three intake stubs take `**_kwargs`.
- `scripts/deferred_work_intake.py` -- read-only (governed by spec-pyforge-doctor; the Never list).

## Tasks & Acceptance

- [x] `core/deferred_work.py` -- pure candidate / selection / rendering / append functions -- the loop twin's neighbour (AD-4).
- [x] `dispatch_land_finalize/__main__.py` -- carry read after the resync, one locked publish holding intake rows and the row, payload id, WARN-only failures.
- [x] `tests/unit/test_deferred_work.py`, `tests/unit/test_dispatch_land_finalize.py` -- one test per acceptance criterion and I/O-matrix row; the mutation (carry call removed) turns 11 tests red.

## Spec Change Log

_(none -- no bad_spec loopback yet)_

## Review Triage Log

_(no independent review has run yet)_

## Design Notes

- **Where the row is built.** The spec is read in `finalize_dispatch_land` (after the resync, so the primary holds a spec the merged PR added); the row is built and appended INSIDE `_run_deferred_work_intake`'s advisory lock, from the text that step publishes (post-`--fix`, or pre-`--fix` after a refusal). One `commit_paths_onto_remote_tip` therefore holds both, and a refused or no-op intake still publishes the row.
- **The out-parameter.** `_run_deferred_work_intake` keeps its `Finding | None` return (every existing stub and caller depends on it); `_FollowupReviewCarry` carries the id and the one WARN that return has no room for -- the shape `_execute_promotion_plan`'s `findings` / `data` already use.
- **Reader.** `dispatch_core.spec_text_at_ref` is `story_spec_rel_path` + `file_text_at_ref`; the carry calls those two halves so the path resolves through the dispatch worktree as `_promote_tracked_spec` does (the helper `_local_spec_rel_path` is lifted out of it, behaviour unchanged).
- **Base text.** The published text derives from the primary's working copy, as the intake's own publish always has; after finalize's resync that is `origin/main`'s ledger. A concurrent finalize publishing between the resync and the lock could lose its row -- the self-announcing backstop is Doctor's `followup-review-uncarried` source (spec-pyforge-doctor Story 33.1), and a re-run re-carries (idempotent).

## Source

Contract authored from `docs/dreams/pyforge-marshal.md`'s 2026-09-19 (the third drain, in flight) Realization-log entry, item (5) ("`followup_review_recommended: true` carries nothing forward"), and `spec-pyforge-marshal` CAP-275 with its 2026-09-28 direction entry in the Spec's `.memlog.md`, decomposed the same session as Epic 66's mint.

## Binding

Parent Spec capability: `spec-pyforge-marshal` CAP-275 (FR-221).
Dream: `docs/dreams/pyforge-marshal.md` § Realization log → *2026-09-19 (the third drain, in flight)*, item (5), and its *Decomposed 2026-09-28* note.
Ledger key: `66-1-finalize-carries-a-recommended-follow-up-review-into-the-deferred-work-ledger`.
Ledger status at mint: `backlog`.
Deferred-work row this story serves: `DW-FU-51-2-1` (closed by Story 66.2, which mints `DW-FRR-51-2` with this story's renderer).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Manual checks:**
- `pixi run -e pyforge-guild deferred-work-check` — exit 0 after the story lands.
