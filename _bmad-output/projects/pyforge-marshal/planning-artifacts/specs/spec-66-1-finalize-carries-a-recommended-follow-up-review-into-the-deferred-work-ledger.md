---
title: '66.1: Finalize carries a recommended follow-up review into the deferred-work ledger'
type: 'fix'
created: '2026-09-28'
status: 'in-progress'
baseline_revision: 'a240511f5b149a47d6972d4a335f591419d0d840'
review_loop_iteration: 2
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
warnings: []
deferred:
  - summary: >-
      When the deferred-work intake changes a primary ledger copy that differs from origin/main's ledger, its own
      publish still writes that text over the tip, dropping rows another finalize published since.
    evidence: |-
      `commit_paths_onto_remote_tip` writes the caller's whole text over the fetched tip (vcs_git.py, `dest.write_text(content)`),
      and `_run_deferred_work_intake` has always published the primary's post-`--fix` copy. The primary's copy is stale whenever
      finalize skips its resync (dirty or non-main primary). Story 66.1 protects only the follow-up row (it is skipped with a WARN
      in that state); it cannot protect the intake's own rows without a text-merge policy for the append-only ledger, and the
      script that writes them (`scripts/deferred_work_intake.py`, governed by spec-pyforge-doctor) is on this story's Never list.
      Found by the Edge Case Hunter and the Intent Alignment Auditor at review pass 2; pre-existing, not caused by this story.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py
    severity: medium
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

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/deferred_work.py` -- Story 4.13's pure loop twin; the dispatch twin sits beside it: `followup_review_id` (`DW-FRR-<epic>-<seq><suffix>` via `render_filename_slug`), `followup_review_candidate` (spec text -> candidate, status through `promotion.read_spec_status`, flag through `dispatch_harness_done.followup_review_recommended`), `followup_review_to_promote` (greedy `DW-FRR-` token idempotency over the text it is given), `render_followup_review_entry`, `append_ledger_entry`. No I/O, no clock (AD-4).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py` -- the carry read (`_followup_review_carry`), an in/out holder (`_FollowupReviewCarry`: `candidate`, `promoted_date` in; `promoted_id`, `finding` out), the intake script run split out unchanged (`_run_intake_script`), the base-text rule below, and `_run_deferred_work_intake(..., followup=)` publishing intake rows and the row in ONE `commit_paths_onto_remote_tip`; `finalize_dispatch_land` gains `clock: ClockPort | None` and the payload key `followup_review_promoted_id`. `_local_spec_rel_path` is lifted out of `_promote_tracked_spec` (behaviour unchanged) so the carry resolves the spec through the dispatch worktree the same way.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py` -- read-only: `story_spec_rel_path` / `spec_text_at_ref` are the spec reader's two halves.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py` -- read-only: `_promote_deferred_work` is the loop twin's impure edge (date from `ClockPort`, blank-line separation) this story mirrors.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py` -- read-only: `commit_paths_onto_remote_tip` fetches the remote tip and writes the caller's whole-file text over it (`dest.write_text(content)`) -- which is why the base text below matters.
- `src/shared/packages/pyforge-marshal/tests/unit/test_deferred_work.py`, `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_land_finalize.py` -- the tests. Existing finalize tests that stub `_run_deferred_work_intake` with a fixed signature need `**_kwargs`; existing tests that assert an exact finding list or spec-read count around a spec read failure need narrowing, because the carry reads the spec once more and warns on the same failed read (both are required by the contract).
- `scripts/deferred_work_intake.py` -- read-only (governed by spec-pyforge-doctor; the Never list).
- PRIOR DERIVATIONS of this story (reverted at review passes 1 and 2, see the Spec Change Log) are saved as unified diffs; the NEWEST is `/tmp/claude-1000/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes--worktrees-dispatch-pyforge-marshal-66-1/df646cb7-b0d8-4037-837b-9bbf25e1b6de/scratchpad/prior-derivation-66-1-pass2.patch` (it holds everything pass 1's KEEP list names, the pass-1 amendments and the real-git test). The working tree starts at the baseline; reuse what the Spec Change Log's KEEP lists name, and change what each amendment names.

## Tasks & Acceptance

- [x] `core/deferred_work.py` -- the pure candidate / selection / rendering / append functions above (AD-4).
- [x] `dispatch_land_finalize/__main__.py` -- the carry read after the resync, the base-text rule, one locked publish holding intake rows and the row, the payload id, WARN-only failures.
- [x] `tests/unit/test_deferred_work.py`, `tests/unit/test_dispatch_land_finalize.py` -- one test per acceptance criterion and I/O-matrix row, plus a test per rule in Design Notes (each base-text branch, the lock-contended WARN, the refused-intake restore, the both-published labels, the dispatch-worktree-only spec, the heading-only idempotency scan including the live-ledger shape, the status-reader shapes, and the carry's own fetch pinned both ways) and ONE real-git test (the `_git_79` helpers) that finalizes a flagged landing against a real bare `origin`, proving the published ledger is `origin/main`'s text plus the row while the primary's copy is stale. The mutation (carry call removed) must turn the 51.2 fixture red.

## Spec Change Log

### 2026-10-01 -- review pass 1 (bad_spec, `review_loop_iteration` 0 -> 1)

- **Triggering finding** (four review layers converged: Blind Hunter, Edge Case Hunter, Verification Gap, Intent Alignment): the prior derivation built the row and judged idempotency from the PRIMARY's working-copy ledger, then published that whole text. `commit_paths_onto_remote_tip` writes the caller's text over the fetched `origin/main` tip wholesale, so when the primary's copy is stale -- finalize skips its resync on a dirty or non-`main` primary (`vcs.has_uncommitted_changes`, `_resync_home_branch` answering False), or a concurrent finalize published between the resync and the lock -- the publish silently drops every row that landed on `origin/main` since, and a re-run before a resync appends a duplicate row. The contract says the text is "computed from the ledger text that publish replaces"; the Design Notes this spec carried ("Base text") blessed the working copy instead.
- **Amended** (outside the intent-contract): Design Notes -- the base-text rule below replaces "Base text"; Tasks -- the real-git test and one test per rule; Code Map -- the adapter's whole-file write and the prior-derivation pointer. Folded in so the re-derivation carries them (all verified, all small): the lock-contended WARN names the dropped row; a refused or unlaunchable intake script restores a ledger it half-wrote; the commit message, the preflight opt-out reason and the publish-failure WARN name BOTH the intake and the row when both are published; a test where only the dispatch worktree holds the spec.
- **Known-bad state avoided**: base text or idempotency read from the primary's working-tree ledger when the publish replaces `origin/main`'s.
- **KEEP** (worked, survive re-derivation; all in the prior patch): the pure functions' names, shapes and the golden row text; the `_FollowupReviewCarry` in/out holder and `_run_deferred_work_intake`'s unchanged `Finding | None` return; `_run_intake_script` and `_local_spec_rel_path` as extractions; the read after the resync, through `_local_spec_rel_path` + `vcs.file_text_at_ref(ORIGIN_MAIN, ...)` (the two halves of `spec_text_at_ref`, so the dispatch worktree resolves); no gating on landing corroboration (the precondition is the spec on `origin/main` reading done and flagged, which is itself the landing's proof); the payload key `followup_review_promoted_id` (null unless THIS run published the row); the `clock` parameter defaulting to `SystemClock`; the test fixtures (`_frr_*` helpers, `_AddingIntakeProcess`, `_FixedClock`) and the pure-function tests; the narrowing of the four existing tests and the `**_kwargs` on the intake stubs.

### 2026-10-01 -- review pass 2 (bad_spec, `review_loop_iteration` 1 -> 2)

- **Triggering findings** (verified by running the real functions over live data, not from the reviewers' claims): (1) idempotency scanned the whole ledger text for `DW-FRR-` tokens, and the live marshal ledger already holds `DW-FRR-51-2` in PROSE (the `verified:` line of the `DW-FU-51-2-1` row, line 7048), so `followup_review_to_promote` answered None for 51.2 itself -- the story this feature exists for -- and finalize would never carry it; (2) the candidate's status was read through `promotion.read_spec_status`, a strict reader that answers None for 3 of the 224 tracked specs whose flag is true, while the harness guard's own pairing of status and flag (`cli/drain_plan.py:307`, `cli/dispatch.py:2561`) uses `dispatch_harness_done.parse_spec_status` and reads those 3 `done`; the Design Notes left both choices unstated.
- **Amended** (outside the intent-contract): Design Notes gain "Idempotency scope" and "Status reader" below; Tasks name the tests for both, for the carry's own fetch, and for the AC 7 seam; the Code Map points at the newest prior derivation. The contract's "greedy token match over the ledger text" is read as a greedy, boundary-aware match over the ledger's ROW HEADINGS: that is the only reading consistent with the same contract's "row already present" (I/O matrix, AC 2) and with its Problem (51.2 must be carried), and it is the same entry form Doctor's `deferred-work` source parses (`_ENTRY_RE`, `^#{2,4}\s+(DW-...)`). One pre-existing issue found alongside is deferred, not fixed (frontmatter `deferred:`).
- **Known-bad state avoided**: a prose mention of a row id counting as the row; a flagged-and-done spec whose status the strict reader cannot parse being silently dropped.
- **KEEP** (worked in the pass-2 derivation, all in `prior-derivation-66-1-pass2.patch`; survive re-derivation unchanged unless an amendment names them): everything pass 1's KEEP list names; the base-text rule exactly as the Design Notes state it (`_carry_followup_row` with its three branches and its skip WARNs, `_restore_ledger_copy`, `_run_intake_script`); the lock-contended WARN naming the row; the both-published labels; the refused-intake restore; `_local_spec_rel_path`; the `_FrrVcs` / `_AddingIntakeProcess` / `_LedgerLockedFs` fixtures and every test in the pass-2 patch, plus its real-git test.

## Review Triage Log

### 2026-10-01 -- Review pass (pass 2)
- verdicts: 33 findings -- high 3, medium 6, low 20, false 4, maybe-false 0
- correction to pass 1: the row "Blind Hunter 1 `[false]`" (idempotency matches the id in ledger prose) is WRONG. Pass 1 refuted it from a truncated grep of line 7048 that showed only the placeholder `DW-FRR-<story>`. Re-verified this pass by running `followup_review_to_promote` over the live 51.2 spec and the live ledger: it answers None, because line 7048 also holds the literal `DW-FRR-51-2`. That row is superseded by G-A below.
- findings:
  - `[medium]` `[bad_spec]` Blind Hunter 1: status read through `read_spec_status`, flag through the harness reader -- two parsers that disagree; verified over all 224 flagged tracked specs: 3 read None strictly and `done` leniently (`spec-16-1-…`, `spec-16-2-…`, `spec-21-10-…`); G-B. Amendment: Design Notes "Status reader".
  - `[low]` `[reject]` Blind Hunter 2: a ledger row published from another clone between the carry's fetch and the publish's own fetch is overwritten -- real but a millisecond window across hosts, the advisory lock is local by design (the intake's own pre-existing publish has the same window), and closing it means an expected-tip parameter on `commit_paths_onto_remote_tip`, outside this story's surface.
  - `[false]` `[reject]` Blind Hunter 3: the carry is not gated on landing corroboration -- the contract names the exact condition (the spec on origin/main reads `done` and the flag is an explicit truthy), which a mint or fallout PR's spec cannot satisfy; the same refutation as pass 1 for this claim stands (only the idempotency claim above was wrong).
  - `[low]` `[reject]` Blind Hunter 4: a Tier-3-promoted key's spec is not on origin/main yet, so the carry finds none and says nothing -- real for that rarer route (dispatch sessions write the tracked spec), but a WARN here needs a new branch for a state the contract's matrix does not list; not worth the added complexity.
  - `[low]` `[reject]` Blind Hunter 5: `followup_review_promoted_id: null` cannot tell "checked, nothing to do" from "could not check" -- the contract says "null when none"; every could-not-check case carries a WARN.
  - `[low]` `[patch]` Blind Hunter 6: the AC 7 seam test passes whether or not finalize calls the carry -- harmless (the real removal turns 20 tests red) but misleading; fix: record the stub's call and assert it ran once with the story key and worktree.
  - `[low]` `[reject]` Blind Hunter 7: existing tests were loosened (a message-substring filter, `read_calls == [_SPEC_REL_79]`) -- required by the contract (the carry reads the spec once more and warns on the same failed read); isolating them by stubbing the carry would be a larger edit for no behavioural gain.
  - `[low]` `[reject]` Blind Hunter 8: remaining test gaps (an unreachable `base = new_text or ""` branch, flag-value shapes, the `SystemClock` default) -- the readers own the flag shapes, mypy owns the default; the fetch-in-carry gap is logged as Verification Gap 1.
  - `[low]` `[reject]` Blind Hunter 9: `append_ledger_entry` duplicates `cli/land.py`'s inline separation -- making `land.py` call it edits the loop twin's promotion, which the Never list forbids.
  - `[low]` `[reject]` Blind Hunter 10: the row's `evidence:` carries no merge sha and `status: open` has no closer -- "when known" (finalize holds no per-story sha here) and Story 73.1 closes rows.
  - `[false]` `[reject]` Blind Hunter 11: no memlog entry or scoped stamp on the branch -- the surface reconcile is written at finalize (AGENTS pre-PR item 5, this run's instructions), after review; not part of the reviewed code diff.
  - `[high]` `[bad_spec]` Edge Case Hunter 1: the token scan matches a prose mention -- verified live (see the correction); G-A. Amendment: Design Notes "Idempotency scope".
  - `[medium]` `[bad_spec]` Edge Case Hunter 2: status `done # note` / `Done` is silently never carried -- same as Blind Hunter 1; G-B.
  - `[medium]` `[defer]` Edge Case Hunter 3: when the intake changed a primary copy that is not the tip's, the row is skipped but the intake's own publish still writes the stale-based text over the tip -- verified in `_run_deferred_work_intake`; pre-existing (the old publish always did this) and fixing it needs a text-merge policy plus the doctor-governed script; deferred in frontmatter (G-D).
  - `[low]` `[reject]` Edge Case Hunter 4: the carry-fetch-to-publish-fetch window -- same as Blind Hunter 2.
  - `[low]` `[reject]` Edge Case Hunter 5: an `FsError` from the post-refusal re-read or restore escapes finalize -- the same function already reads the ledger (`original_text`) and restores it in its `finally` through the same unguarded calls; no new failure class.
  - `[false]` `[reject]` Edge Case Hunter 6: carry not gated on corroboration -- same as Blind Hunter 3.
  - `[low]` `[reject]` Edge Case Hunter 7: `base = new_text or ""` could replace the ledger with one row if the script deleted the file -- reachable only if `--fix` removes the ledger it just read; the old publish carried the same `or ""`.
  - `[low]` `[reject]` Edge Case Hunter 8 (claim): the spec is read through `_local_spec_rel_path` + `file_text_at_ref`, not `spec_text_at_ref` itself -- those are its two halves; the dispatch-worktree fallback is Story 79.1's precedent and a test covers it.
  - `[high]` `[bad_spec]` Edge Case Hunter 9 (claim): "the `DW-FRR-` prefix is used by no ledger" is false -- the live ledger holds the token in prose; G-A.
  - `[medium]` `[patch]` Verification Gap 1: the carry's own `vcs.fetch` is unpinned -- verified by the reviewer: deleting it, moving it after the read, or swallowing its error each leave all 146 tests green; fix: a fake that serves a stale ledger until `fetch` has run, and a test where the carry's fetch (index 3) raises.
  - `[high]` `[bad_spec]` Verification Gap 2: idempotency matches the id anywhere in the ledger -- verified live; G-A.
  - `[low]` `[patch]` Verification Gap 3: the AC 7 seam test cannot fail on its own -- same as Blind Hunter 6.
  - `[low]` `[reject]` Intent Alignment 1: the spec is read through the two halves of `spec_text_at_ref` -- same as Edge Case Hunter 8.
  - `[low]` `[patch]` Intent Alignment 2: the AC 7 criterion is met by seam stubbing, not call removal -- same as Blind Hunter 6.
  - `[false]` `[reject]` Intent Alignment 3: the carry runs outside the corroboration gate -- same as Blind Hunter 3.
  - `[medium]` `[defer]` Intent Alignment 4: AC 5 ("the published ledger holds the intake's rows and the new row") holds when the primary's copy equals the tip; when it differs and the intake changed it, the row is skipped with a WARN and the intake publishes as it always did -- the same pre-existing issue as Edge Case Hunter 3; G-D.
  - `[low]` `[reject]` Intent Alignment 5: a ledger absent at origin/main skips the row with a WARN -- one row never creates a ledger; no tracked ledger exists in no station.
  - `[low]` `[reject]` Intent Alignment 6: `evidence:` carries only the story key -- same as Blind Hunter 10.
  - `[low]` `[reject]` Intent Alignment 7: no test runs the subprocess entry `main()` with the real process and clock -- `main()` passing no process or clock is covered by the existing argv test; the real-git test covers the publish.
  - `[medium]` `[bad_spec]` Intent Alignment 8: status is read through `read_spec_status`, not the harness's `parse_spec_status` -- same as Blind Hunter 1; G-B.
  - `[low]` `[reject]` Intent Alignment 9: the tip is fetched in `_carry_followup_row` rather than inside the publish -- same as Blind Hunter 2.
  - `[low]` `[reject]` Intent Alignment 10: five existing finalize tests' assertions were edited -- same as Blind Hunter 7.


### 2026-10-01 -- Review pass
- verdicts: 31 findings -- high 6, medium 2, low 15, false 8, maybe-false 0
- findings:
  - `[false]` `[reject]` Blind Hunter 1: the idempotency token scan matches `DW-FRR-51-2` in ledger prose -- the only `DW-FRR` mention in the real ledger (line 7048) is the placeholder `DW-FRR-<story>`, which tokenizes to `DW-FRR` (`<` is outside the token class) and never equals a real id; the whole-text token scan is the contract's stated convention and `deferred_work_check`'s own.
  - `[high]` `[bad_spec]` Blind Hunter 2: the published text derives from a stale primary copy when the resync is skipped, overwriting newer `origin/main` rows or double-adding the row -- verified against `vcs_git.py:1424-1432` (whole-file write over the fetched tip) and `finalize_dispatch_land` (`has_uncommitted_changes` skips the resync); group G1. Amendment: the base-text rule.
  - `[false]` `[reject]` Blind Hunter 3: the carry is not gated on landing corroboration -- its precondition is the spec on `origin/main` reading `status: done` with the flag true, which cannot hold for a story that never landed; the contract names no gate.
  - `[low]` `[reject]` Blind Hunter 4: the Code Map miscounted the narrowed tests and changed stubs -- the fix is to edit this build's spec (rejected by rule); the Code Map is reworded in this amendment anyway.
  - `[low]` `[patch]` Blind Hunter 5: a refused intake script that wrote before failing leaves the primary's ledger as it left it -- real, and pre-existing in the early return; folded into the re-derivation (restore the pre-script text); group G2, moot until re-derived.
  - `[low]` `[patch]` Blind Hunter 6: the lock-contended WARN does not name the dropped follow-up row -- verified in `_run_deferred_work_intake`'s lock `Finding`; folded in (name the row when a carry is pending); G2.
  - `[low]` `[reject]` Blind Hunter 7: `evidence:` names the story key but not the merge subject or sha -- the contract says "when known", and finalize holds no per-story merge sha at that point; the fix would add a subject-matching surface.
  - `[false]` `[reject]` Blind Hunter 8: `summary:` asserts the follow-up review has not run without checking -- a done spec whose flag is still true is exactly the state no follow-up pass has cleared (a follow-up pass leaves it false), and the token check is the "nothing else carries it" check.
  - `[false]` `[reject]` Blind Hunter 9: the mutation criterion is shown by stubbing the carry seam -- the real removal of the call was run (11 tests red incl. the 51.2 fixture); the seam test is a redundant extra, not a substitute.
  - `[low]` `[patch]` Blind Hunter 10: a combined publish is labelled only as the follow-up row (commit message, opt-out reason, failure WARN) -- cosmetic audit-trail error; folded in (name both); G2.
  - `[low]` `[patch]` Blind Hunter 11: untested shapes (a real-git publish of the carry; banner-prefixed or quoted-truthy specs) plus a duplicated fake clock, an out-parameter with two channels, governance loose ends -- the real-git test is added to Tasks; the banner/quoted shapes belong to the mandated readers; the rest is not harmful; memlog entries are written at finalize.
  - `[high]` `[bad_spec]` Edge Case Hunter 1: the carry runs on a stale primary copy when the resync was skipped or failed -- same defect as Blind Hunter 2; G1.
  - `[high]` `[bad_spec]` Edge Case Hunter 2: idempotency is tested against the primary's restored copy, so a second finalize before a resync re-publishes the row -- verified: the copy is restored to its pre-publish text after every publish; G1.
  - `[low]` `[patch]` Edge Case Hunter 3: lock acquisition failure with a carry pending drops the row with only an "intake skipped" WARN -- same as Blind Hunter 6; G2.
  - `[low]` `[patch]` Edge Case Hunter 4: a script that writes the ledger then exits non-zero, with no row publishable, leaves a half-written primary copy -- same as Blind Hunter 5; G2.
  - `[low]` `[reject]` Edge Case Hunter 5: `read_spec_status` is case-sensitive and rejects a trailing comment while the flag parser is tolerant -- it is the one status reader every finalize gate uses; `status: Done` / `done # note` specs are not produced here and the fix would fork the reader.
  - `[false]` `[reject]` Edge Case Hunter 6: a flagged spec not yet done loses its row silently -- the I/O matrix row "not done" says nothing added with no error handling; a WARN would contradict the contract.
  - `[false]` `[reject]` Edge Case Hunter 7: not gated on `landing_corroborated` / the not-done ERROR -- same as Blind Hunter 3.
  - `[low]` `[reject]` Edge Case Hunter 8: `evidence:` carries no landing commit -- same as Blind Hunter 7.
  - `[high]` `[bad_spec]` Edge Case Hunter 9 (claim): "computed from the ledger text that publish replaces" -- the code computes from the primary's copy; G1.
  - `[medium]` `[bad_spec]` Edge Case Hunter 10 (claim): the second-run test hand-seeds the primary copy, hiding that the real flow restores the pre-publish copy -- verified in the test; G1 (the re-derived test seeds `origin/main`'s ledger).
  - `[low]` `[patch]` Edge Case Hunter 11 (claim): the "a refused run leaves the ledger as it read before it" comment is untrue when the script wrote first -- same as Blind Hunter 5; G2.
  - `[low]` `[patch]` Verification Gap 1: no test where only the dispatch worktree holds the spec, though the carry resolves through it -- verified (`_frr_finalize` passes no `worktree`); folded into Tasks; G2.
  - `[high]` `[bad_spec]` Verification Gap 2: idempotency is judged on the primary's working copy, not `origin/main`'s ledger -- G1.
  - `[false]` `[reject]` Verification Gap 3: the mutation test is redundant -- accurate and harmless (see Blind Hunter 9); not a defect.
  - `[high]` `[bad_spec]` Intent Alignment 1: the ledger text the diff reads and its tests exercise is the primary's working-tree file; `origin/main`'s ledger blob is never read -- G1.
  - `[medium]` `[bad_spec]` Intent Alignment 2: the fake read path never serves the ledger at `origin/main`, and the second-run test assumes a resync -- G1.
  - `[low]` `[patch]` Intent Alignment 3: stubbed scan, promotion and resync, and no real-git test of the carry -- folded into Tasks (one real-git test); G2.
  - `[low]` `[reject]` Intent Alignment 4: the spec is read through `_local_spec_rel_path` + `vcs.file_text_at_ref` rather than `spec_text_at_ref` itself -- those are `spec_text_at_ref`'s two halves; the dispatch-worktree fallback is Story 79.1's precedent and the added test covers it.
  - `[false]` `[reject]` Intent Alignment 5: the mutation criterion is met by seam stubbing -- see Blind Hunter 9.
  - `[low]` `[patch]` Intent Alignment 6: failure paths outside the matrix (lock timeout, extra WARNs) -- the lock timeout names the row in the re-derivation (G2); the other WARNs are additive and non-gating.

## Design Notes

- **Where the row is built.** The spec is read in `finalize_dispatch_land` after the resync, so the primary holds a spec the merged PR added; the row is built and appended INSIDE `_run_deferred_work_intake`'s advisory lock. One `commit_paths_onto_remote_tip` therefore holds the intake's rows and the row, and a refused or no-op intake still publishes the row.
- **Base text -- the ledger the publish replaces (review pass 1).** `commit_paths_onto_remote_tip` fetches the remote tip and writes the caller's text over it, so the row is built on `origin/main`'s ledger, never on the primary's possibly stale copy. Under the lock, when a carry is pending and after the intake script has run: `vcs.fetch(root, "origin", "main")`, then `remote_text = vcs.file_text_at_ref(root, ORIGIN_MAIN, <ledger rel path>)`. A `VcsCommandError`, or `remote_text is None` (the ledger is never created for one row), is an `MRS-DISP-047` WARN on `followup.finding` naming the ledger path and the cause, the row is skipped, and the intake's own publish proceeds exactly as it always has. Otherwise the base is: `remote_text` when the intake changed nothing (`new_text == original_text`); `new_text` when the intake changed the primary's copy AND `original_text == remote_text` (its text is a faithful successor of the tip); in the remaining case (the intake changed a primary copy that differs from the tip) the row is skipped with a WARN saying the ledger moved and a re-run of finalize re-carries it -- never a merge of two texts. `followup_review_to_promote` judges idempotency on THAT base; the published text is `append_ledger_entry(base, entry)`; nothing is published when there is nothing to add. The primary's copy is restored exactly as before.
- **The out-parameter.** `_run_deferred_work_intake` keeps its `Finding | None` return (every existing stub and caller depends on it); `_FollowupReviewCarry` carries the id (set only once the row is published) and the one WARN that return has no room for -- the shape `_execute_promotion_plan`'s `findings` / `data` already use.
- **A refused intake.** A refused or unlaunchable script leaves the ledger as the row's pre-script text: if the file now differs from `original_text`, restore it before continuing. The intake's own WARN is returned as before; a publish failure after a refusal goes to `followup.finding`.
- **Lock contention.** When the advisory lock cannot be acquired and a carry is pending, the returned WARN also says the follow-up review row for that story was not carried.
- **Labels.** When both the intake's rows and the row are published, the commit message, the preflight opt-out reason and the publish-failure WARN name both; the opt-out reason keeps naming the story key.
- **Reader.** `dispatch_core.spec_text_at_ref` is `story_spec_rel_path` + `file_text_at_ref`; the carry calls those two halves so the path resolves through the dispatch worktree as `_promote_tracked_spec` does.

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
