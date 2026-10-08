---
title: "22.21: A story that recommends a follow-up review lands with its row"
type: 'fix'
created: '2026-10-08'
status: 'done'
baseline_revision: '998c231f2fa072bca46bfb31f8ae98e63afff370'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-66-1-finalize-carries-a-recommended-follow-up-review-into-the-deferred-work-ledger.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-66-2-every-landed-follow-up-recommendation-is-backfilled-and-held-by-a-meta-test.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-73-1-a-follow-up-review-run-is-judged-and-landed-by-its-own-branch.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-80-1-a-dispatch-landing-waits-for-its-pr-s-checks-and-refuses-on-a-red-one.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/deferred_work.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_harness_done.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py
  - src/shared/packages/pyforge-marshal/tests/meta/test_followup_review_carried.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** a story whose own review pass leaves `followup_review_recommended: true` on its `done` spec cannot land.
The check that gates its landing is red because of that same recommendation.

- **The invariant and who writes it.** Story 66.2's meta-test
  `src/shared/packages/pyforge-marshal/tests/meta/test_followup_review_carried.py::test_no_done_and_flagged_spec_is_uncarried_across_the_eight_projects`
  requires a carrying row in the station's `deferred-work-ledger.md` for every tracked spec that reads `status: done`
  with the flag true. The predicate is `core/deferred_work.followup_review_orphans`, and the carrying row is a
  `### DW-…:` heading with `origin: dispatch-followup-review` or `review-budget-followup`. Story 66.1's row
  `DW-FRR-<story>` is written only by `dispatch_land_finalize`
  (`_followup_review_carry` about :638-:676, `_carry_followup_row` about :177-:219), after `forge.merge_pr` has
  merged. So the PR's own tree carries the spec without the row, `marshal-test` fails on it, and Story 80.1's check
  wait refuses the landing with `MRS-DISP-056`. The row that would fix this is written only after a merge that never
  happens.
- **Why it repeats.** The worktree spec reads `done` with the flag true. `core/dispatch_harness_done.blocks_harness_relaunch`
  lets that pairing through to a fresh session (marshal Story 29.2), and Story 83.7's refused-landing land-only rule
  applies only to `in-progress` and `in-review`. So every re-dispatch launched another full session, verified again,
  and was refused again on the same check.
- **The live case.** Herald 29.2, PR #1912, branch `dispatch/pyforge-herald/29.2`, 2026-10-07 and 2026-10-08:
  - The review pass in run `pyforge-herald-20261007T201712812Z-6830d48e` set the spec `done` with
    `followup_review_recommended: true` (`6f45b96f11`). The session added the key above the template's `false` line,
    so the frontmatter holds both. `core/dispatch_harness_done._frontmatter_scalar` reads the first, `true`.
  - Run `pyforge-herald-20261007T233819056Z-d9c1131d` launched another session and was refused at verification
    (`MRS-GATE-015`, `platform-ci-local`).
  - Run `pyforge-herald-20261008T043732276Z-071a3953` launched another session and verified. Its landing was then
    refused with `MRS-DISP-056`: head `1e547caf07`, `marshal-test` failure, `uncarried follow-up recommendations:
    [('pyforge-herald', 'spec-29-2-the-published-exports-are-listed-and-streamed-behind-the-herald-role.md')]`.
  - An operator added `DW-FRR-29-2` on the branch by hand (`4d40fc9b4a`, "herald 29.2: carry the follow-up review
    recommendation as DW-FRR-29-2"). The next run (`pyforge-herald-20261008T045221736Z-1186c21d`) verified and landed
    (`cb46142c8d`). Finalize found the row already on `origin/main` and added nothing: `main` holds exactly one
    `DW-FRR-29-2`, `status: open`.

**Approach:** the landing writes the row on the branch before CI sees it. This is the first of the two options the
operator named. The other was a meta-test exemption for the open PR's own story.

- In `dispatch_land.py` `execute_dispatch_land` (about :1151), after `may_attempt_dispatch_landing` allows a landing
  (about :1392) and before the landing's push (about :1401):
  - read the story spec the landing already resolved (`story_spec_text`, or the worktree spec at about :1249-:1258)
    and its repo-relative path;
  - build `deferred_work.followup_review_candidate(spec_text, key, spec_rel)`. It returns a candidate only for a spec
    that reads `done` with the flag an explicit truthy, through the same readers the meta-test's predicate uses
    (`parse_spec_status`, `followup_review_recommended`);
  - read the branch's `_bmad-output/projects/<slug>/planning-artifacts/deferred-work-ledger.md` in the worktree, and
    keep the candidate only if `deferred_work.followup_review_to_promote(candidate, ledger_text)` returns it (no row
    is headed `DW-FRR-<story>` yet, open or closed);
  - append `deferred_work.render_followup_review_entry(row, promoted_date=<today>, promoted_label=…,
    landing_evidence=…)` with `deferred_work.append_ledger_entry`. The label and evidence name the dispatch landing,
    not finalize. Then commit only that file on the branch with a `marshal:` subject that names the row id.
- The landing's existing push then carries the commit. Every later step works on a head that already holds the row:
  the PR, the spec-surface reconcile, Story 80.1's check wait and the merge.
- Nothing else changes. Finalize's carry stays as the post-merge backstop (a landing by any other route still gets its
  row), and it is idempotent: it finds the row on `origin/main` and publishes nothing. Finalize still closes the row
  when a follow-up review run lands (Story 73.1, `_close_followup_row`).

**Why this option, not a meta-test exemption.**
- The invariant then holds on every tree: the PR head, the merge result and `main`. Nothing on `main` waits for a
  post-merge step that can be skipped (finalize's carry skips with an `MRS-DISP-047` WARN when the tip moved or the
  ledger cannot be read).
- An exemption would have to work out "the open PR's own story" from CI context. It would weaken the one check that
  holds CAP-275's success clause, and `main` could still red between the merge and finalize.
- The landing already owns the write path, the date and the commit. The row is the one the operator wrote by hand,
  which landed clean.

Ledger key: `22-21-a-story-that-recommends-a-follow-up-review-lands-with-its-row`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-marshal` CAP-275 (FR-221): Story 66.1's `DW-FRR-<story>` carry and Story
  66.2's meta-test that holds it. The carry runs on CAP-162's dispatch landing (← `spec-marshal-single-story-dispatch`
  CAP-4; Story 22.4), ahead of CAP-284's check wait (Story 80.1). CAP-281's close of a follow-up review run's row
  (Story 73.1) and its drain gate (Story 73.2) are unchanged. CAP-275's intent and success (exactly one row per story,
  a second carry adds nothing, the meta-test finds no orphan) are unchanged; only the place the row is first written
  moves ahead of CI. No new CAP.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-08 (verify and landing order).

## Acceptance Criteria

- **A done, flagged story lands with its row.** Given a real-git fixture: a dispatch branch whose story spec reads
  `status: done` with `followup_review_recommended: true`, and whose station ledger heads no `DW-FRR-<story>` row.
  When `execute_dispatch_land` lands it with a verified verdict and a fake forge whose checks are green Then:
  - one commit on the branch, made before the first push, adds exactly one `### DW-FRR-<story>:` row with
    `origin: dispatch-followup-review`, `source_spec` naming the spec, `location:` its repo path, `severity: low` and
    `status: open`;
  - the pushed head's tree has no orphan: `followup_review_orphans` over that spec and that ledger returns False;
  - the merge goes ahead with the pushed head's sha.
- **Finalize adds nothing after it.** Given the merged result of the first criterion When `finalize_dispatch_land`
  carries follow-up rows Then it publishes no ledger commit for that story, and `origin/main`'s ledger heads exactly
  one `DW-FRR-<story>`, `status: open`.
- **A re-landing does not duplicate.** Given the first criterion's branch after a refused landing (for example a red
  check, `MRS-DISP-056`) When `execute_dispatch_land` runs again Then it makes no new ledger commit, and the ledger
  still heads exactly one `DW-FRR-<story>`.
- **An existing row is respected.** Given a branch ledger that already heads `DW-FRR-<story>` (an operator's hand row,
  the herald 29.2 shape, or a closed row) When the landing runs Then it writes nothing. A ledger that heads only a
  longer id with the same prefix (`DW-FRR-51-20`, for story 51.2) still gains `DW-FRR-51-2`.
- **Not a candidate.** Given a spec whose status is not `done`, or whose flag is false, absent or unreadable When the
  landing runs Then it writes nothing, and the landing is otherwise unchanged.
- **A follow-up review run.** Given a follow-up review run (Story 73.1) whose branch ledger already holds the open row
  When it lands Then the landing writes nothing, and finalize closes the row as today.
- **No ledger.** Given a station whose branch has no tracked `deferred-work-ledger.md` When the landing runs Then it
  creates no ledger, writes no row, and adds one `MRS-DISP-047` WARN naming the path. The landing goes on.
- **A write that fails.** Given the ledger cannot be read or written, or its commit fails When the landing runs Then
  it refuses with `MRS-DISP-017` naming the ledger and the error, before anything is pushed and with no merge.
- **Mutation.** Given the branch write removed When the station suite runs Then the first criterion's test fails,
  because `followup_review_orphans` reports the spec on the pushed head.

## Boundaries & Constraints

**Always:**
- The row comes only from the shipped pure functions in `core/deferred_work.py` (`followup_review_candidate`,
  `followup_review_to_promote`, `render_followup_review_entry`, `append_ledger_entry`). Its id, origin, severity and
  shape are Story 66.1's, never a second renderer.
- Write and commit before the landing's push, so the head whose checks the landing waits on carries the row.
- Finalize's post-merge carry and close stay. The carry is the backstop, and the close is Story 73.1's.
- Name every changed governed path on the memlogs of the Specs that govern it, then stamp those Specs scoped
  (`spec-pyforge-marshal` and the co-governor `spec-pyforge-core`; AGENTS.md pre-PR item 5).

**Never:**
- Never exempt any spec in the meta-test or in `followup_review_orphans`.
- Never write a second row for a story whose id already heads a row, and never create a ledger that does not exist.
- Never write the row from the session's prompt or the harness, and never change the spec's flag or status.
- Never change the relaunch rule (`blocks_harness_relaunch`, Story 83.7's refused-landing statuses). With the row on
  the branch, the refusal that kept relaunching herald 29.2 is gone. A relaunch after any other refused landing of a
  `done`, flagged spec is unchanged, and is not chained here.

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-08 (verify and landing order) entry.
- Epic: Epic 22 (a fix joins its own epic, which stays `in-progress`; doctor Story 41.5).
- Ledger key: `22-21-a-story-that-recommends-a-follow-up-review-lands-with-its-row`.
- Ledger status at mint: `backlog`.
- Deps: none.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- Mutation: remove the branch write from `execute_dispatch_land` and re-run the station suite. The done-and-flagged landing test fails on the orphan. Restore it.
- On the next dispatch of a story whose review pass recommends a follow-up review, the PR head carries `DW-FRR-<story>`, `marshal-test` is green, the landing merges without a hand row, and `main` heads exactly one open `DW-FRR-<story>`.
- `pixi run --frozen -e pyforge-guild spec-surface-check`: exit 0 after the memlog reconciles and scoped stamps.

## Review Triage Log

### 2026-10-08 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (none — implementation matches acceptance criteria; review performed against diff and AC)

## Auto Run Result

Status: done

Summary: `execute_dispatch_land` now appends `DW-FRR-<story>` to the station deferred-work ledger on the dispatch branch and commits it after `may_attempt_dispatch_landing` and before the landing push, using the Story 66.1 pure helpers in `core/deferred_work.py`. Finalize carry remains the post-merge backstop.

Files changed:
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py` — pre-push follow-up row carry
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_landing.py` — Story 22.21 acceptance fixtures

Review: 0 patches; nothing deferred.

Follow-up review recommended: false

Verification:
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 11852 passed
- `pixi run --frozen -e pyforge-guild lint-types` — exit 0
- `python scripts/spec_surface_reconcile.py` — exit 0 after memlog reconcile
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — 1 pre-existing failure (`pyforge-herald` conda run-deps vs pyproject; unrelated to this diff)
