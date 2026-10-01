---
title: '67.1: A landed dispatch reads completed when the primary checkout cannot be fast-forwarded'
type: 'fix'
created: '2026-09-28'
status: 'done'
baseline_revision: 'dfe299d099c11500a0fbfa46abe2c1727a5ac5d0'
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

**Problem:** After the dispatch supervisor lands a story from its terminal branch (`_land_or_journal_block` in `run_dispatch_supervisor`), it re-reads the repository facts (`gather_dispatch_git_facts`) and re-resolves the session verdict from them alone (`resolve_terminal_session_verdict`). Those facts read merge evidence from LOCAL `main` (`_MERGE_INTO = "main"`: `is_branch_merged(into="main")` and `commit_subjects(local_branch_ref("main"))`), and a retired dispatch branch never reads merged. With the session ended and HEAD moved, a land the repository does not yet show on local `main` resolves `STOPPED_EXTERNALLY`. The supervisor writes `dispatch-completion` `stopped_externally` / `external-operator-stop` in the same tick. `marshal status` reads a journaled completion before the landing, and `fleet-picture` and `core/status.py` treat that as a terminal failure. Every land did exactly this until Story 51.9 (merge `df813208e9`), whose finalize now fast-forwards the primary checkout's `main` before the supervisor's re-read. The verdict still rests on that fast-forward. Finalize skips it for a dirty primary, and `_resync_home_branch` refuses a primary that is not at `main`'s own tip or whose fetch or fast-forward fails. Probed 2026-09-28 on the current tree: the shape of `test_supervisor_finalizes_verifies_and_lands_a_finished_harness_session` (finalize → verify → land, local `main` without the merge) writes `stopped_externally` after a journaled `landed` outcome. The test passes only because it asserts that some completion was published.

**Approach:** the terminal-branch re-resolution reads the supervisor's own journal first, the rule the loop head and the post-finalize re-read already apply through `_landing_succeeded` (→ `core/dispatch_supervisor_state.landing_journal_indicates_complete`), and the rule `marshal status` applies in `resolve_dispatch_session_verdict`. A `dispatch-land` OUTCOME for this run journaled `ok` with verdict `landed` or `already_landed` resolves `COMPLETED`, which carries `stop_reason: null`. Only without one does the verdict come from `resolve_terminal_session_verdict`. The three supervisor sites may share one small helper. `gather_dispatch_git_facts`, its local-`main` base and the completion INTENT's recorded `story_merged_on_main` / `branch_merged` stay as they are: the journal decides the process verdict, and git keeps the repository facts (AD-33). The LIVE-branch land site is left alone: a marshal-initiated stop keeps it `LIVE`, and the next tick completes it through the loop head's read.

Ledger key: `67-1-a-landed-dispatch-reads-completed-when-the-primary-checkout-cannot-be-fast-forwarded`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / XS / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-276 (FR-222).

## Acceptance Criteria

- Given a run whose session has ended, whose verification is `verified`, and whose land the supervisor journals `landed` while the dispatch branch is retired and local `main`'s subjects lack the merge When `run_dispatch_supervisor` runs against fakes Then it journals `dispatch-completion` with verdict `completed` and `stop_reason: null` and publishes `completed`
- Given the same run with the dispatch branch still present When the supervisor runs Then it completes the same way
- Given the same run whose repository re-read after the land raises `VcsCommandError` When the supervisor runs Then it still journals `completed` (the journal check reads no repository fact)
- Given the new check removed When that fixture runs Then the completion reads `stopped_externally` and the test fails (mutation)
- Given a land journaled `refused`, or a land OUTCOME journaled not `ok` When the supervisor re-resolves Then the verdict comes from repository facts exactly as today
- Given `test_supervisor_finalizes_verifies_and_lands_a_finished_harness_session` When it runs Then it asserts the published verdict is `completed`
- Given `test_supervisor_lands_from_the_live_branch_then_completes` When it runs Then it passes unchanged
- Given the completion INTENT of a landed run When it is read Then `story_merged_on_main` and `branch_merged` are the repository facts as gathered, not overwritten from the journal

## Boundaries & Constraints

**Always:** Implement only the Surface named in `epics.md` Story 67.1. Read the landing through `_landing_succeeded` / `landing_journal_indicates_complete`, the one rule already in use; never a second predicate.

**Never:**
- Do not change `gather_dispatch_git_facts`, `_MERGE_INTO` or any repository-fact read.
- Do not write a repository fact from the journal (AD-33).
- Do not change the LIVE-branch land site or the loop's land trigger, the stuck-land retry, `supervisor_should_exit`, finalize or the resync.
- Do not rewrite historical completions.
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`; do not run `scripts/bmad-switch`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| landed, primary not fast-forwarded | land OUTCOME `landed`, `ok`; branch retired; local `main` lacks the merge | `completed`, `stop_reason: null` | none |
| landed, branch present | same, branch still present | `completed` | none |
| already landed | land OUTCOME `already_landed`, `ok` | `completed` | none |
| land refused | land OUTCOME `refused` | verdict from repository facts, as today | none |
| land not ok | land OUTCOME `ok: false` | verdict from repository facts, as today | none |
| primary fast-forwarded | local `main` shows the merge | `completed` (unchanged) | none |
| repository read fails after land | land OUTCOME `landed`, `ok`; `VcsCommandError` on the re-read | `completed` (the journal check needs no repository read) | the repository facts recorded are the ones gathered before the land |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py` -- `run_dispatch_supervisor`: the terminal-branch land site (`_land_or_journal_block` → re-fold → `gather_dispatch_git_facts` → `resolve_terminal_session_verdict`) is the one changed site. The loop head and the post-finalize re-read already read `_landing_succeeded(folded, run_id)` first; the LIVE-branch land site is left alone.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py` -- `_landing_outcome_verdict` / `_landing_succeeded`: the one rule reused (→ `core/dispatch_supervisor_state.landing_journal_indicates_complete`); `_run_and_journal_landing` journals `ok = (verdict == LANDED)`, so refused / skipped / already-landed supervisor lands journal `ok: false` and fall to repository facts.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_main_loop.py` -- supervisor main-loop tests over fakes (`FakeVcs`, `FakeFs`, `FakePublisher`, `_patch_landing`); the land-shape test and the new landed, already-landed, failing-re-read and not-ok-land tests live here.
- Read-only: `gather_dispatch_git_facts`, `_MERGE_INTO`, `core/supervise.py::resolve_terminal_session_verdict`, `cli/dispatch.py::resolve_dispatch_session_verdict`.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py` -- after the terminal-site re-read (outside its `try`), a `_landing_succeeded(folded, run_id)` journal wins as `COMPLETED` -- the journal decides the process verdict, git keeps the facts
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_main_loop.py` -- assert `completed` in the land-shape test; add landed (branch retired / present), already-landed, repository-re-read-fails and not-ok-land (refused / skipped) tests covering every matrix row

Acceptance Criteria: as stated in the `<intent-contract>` above.

## Spec Change Log

## Review Triage Log

### 2026-10-01 — Review pass
- verdicts: 21 findings — high 0, medium 0, low 16, false 5, maybe-false 0
- findings:
  - `[low]` `[patch]` Blind: the already-landed test uses a journal shape the supervisor never writes (`_AlreadyLandedOkFs`) — verified: `_run_and_journal_landing` journals `ok = (verdict == LANDED)`, so the row is reachable only through the shim; the contract row stays, and the shim's docstring now says so instead of naming a writer
  - `[low]` `[patch]` Blind: the not-ok-land test asserts only `!= completed` and never isolates the `ok` gate — patched: it now pins `stopped_externally` / `external-operator-stop`, the verdict the repository facts give today; the `ok` gate itself is the pre-existing `_landing_outcome_verdict`, already pinned by `test_landing_outcome_verdict_ignores_a_not_ok_outcome`
  - `[low]` `[patch]` Blind: the repository-re-read-fails test never checks the facts recorded — patched: it reads the completion INTENT and asserts baseline and current head, `story_merged_on_main` and `branch_merged` are the pre-land values
  - `[low]` `[patch]` Blind: `_LandedRepositoryReadFailsVcs` duplicates `_HeadShaFailsOnceJournaledVcs` — patched: the new class is deleted; the existing double (`marker=KIND_DISPATCH_LAND`, unlimited refusals) is reused
  - `[low]` `[patch]` Blind: `_completion_outcome` / `_completion_intent` are copy-paste with a bare `dict` annotation — patched: one `_completion_payload(fs, run_dir, phase)` over `Phase`
  - `[low]` `[reject]` Blind: the override is a third copy of the journal-first rule, and no shared helper was extracted — the contract says the sites "may" share one; the override must sit outside the re-read's `try` (AC 3), so a helper would also rewrite the loop head and the post-finalize re-read, two untouched sites, for no behaviour change
  - `[low]` `[reject]` Blind: the Code Map says "three new tests", the spec Change/Triage logs are empty — the fix is to edit this build's spec; the Code Map wording is count-free now and this log and `## Auto Run Result` carry the verification
  - `[false]` `[reject]` Blind: two matrix rows have no new explicit test — "primary fast-forwarded" is covered by `test_supervisor_exits_completed_once_the_story_is_merged_on_main`, and the LIVE-branch land test asserts `publisher.heartbeats == ["handle-1"]` and the completed verdict, so both are pinned
  - `[false]` `[reject]` Edge: the post-land `fs.read_text(journal_path)` could return `None`, leaving `folded` stale — the supervisor just appended to that file in the same process; a missing journal would have refused the append, and the same guard shape is at every re-fold site
  - `[low]` `[reject]` Edge: the land merged but the dispatch-land OUTCOME append raised `FsError` (swallowed), so no journal says landed — real (`__main__.py:1176-1181`) and pre-existing, but an append failure on the run's own journal is unlikely, and the fix (returning the landing verdict through `_land_or_journal_block`) is a second signal beside the one predicate the contract requires
  - `[low]` `[reject]` Edge: the LIVE-branch land site has no journal-first override, so a persistent post-land read failure never terminalizes — the contract leaves that site alone by name, and a gather that fails every tick blocks every verdict at the loop head, before this change
  - `[low]` `[patch]` Edge: the already-landed matrix row is tested only through the shim — same root cause as the first finding; docstring corrected
  - `[low]` `[reject]` Edge: the contract's claim that the next tick completes a LIVE-branch land never reaches the journal check when the head gather keeps failing — same root cause as the LIVE-branch finding above; excluded by the contract
  - `[low]` `[patch]` Edge: the negative test is only `!= completed` — same root cause as the second finding; patched
  - `[low]` `[patch]` Verification-gap: the `_AlreadyLandedOkFs` docstring names "the dispatch CLI" as the writer — verified: only `_journal_dispatch_land` writes `dispatch-land` entries (`cli/dispatch.py:1198` reads); docstring corrected, no test changed
  - `[low]` `[patch]` Intent-alignment: `already_landed` is covered only through a synthetic writer — same root cause as the first finding
  - `[low]` `[reject]` Intent-alignment: no test pairs `landed`/`already_landed` with `ok: false` — the `ok` gate is pre-existing and pinned by `test_landing_outcome_verdict_ignores_a_not_ok_outcome`; the diff does not change it
  - `[false]` `[reject]` Intent-alignment: the mutation criterion is realised by failures, not by a dedicated test — the criterion asks that removing the check fail the fixture; run twice, the removal reds five tests, each `'stopped_externally' == 'completed'`
  - `[low]` `[reject]` Intent-alignment: the INTENT facts are asserted only where they read `False` — the override never writes a fact; a `True` fixture needs a merged-on-main run, which never reaches the land site
  - `[false]` `[reject]` Intent-alignment: other repository reads raising are not tested separately — every repository read is inside `gather_dispatch_git_facts`, behind the one `try`; the override sits outside it
  - `[false]` `[reject]` Intent-alignment: staged changes outside the production surface — the harness checkpoint stages them; the review diff excludes the spec by design

## Source

Contract authored from `docs/dreams/pyforge-marshal.md`'s 2026-09-19 (the third drain, in flight) Realization-log entry, item (2), and `spec-pyforge-marshal` CAP-276 with its 2026-09-28 direction entry in the Spec's `.memlog.md` (the file:line evidence, the dispatch-run journal survey and the probe), decomposed the same session as Epic 67's mint.

## Binding

Parent Spec capability: `spec-pyforge-marshal` CAP-276 (FR-222).
Dream: `docs/dreams/pyforge-marshal.md` § Realization log → *2026-09-19 (the third drain, in flight)*, item (2), and its *Decomposed 2026-09-28* note.
Ledger key: `67-1-a-landed-dispatch-reads-completed-when-the-primary-checkout-cannot-be-fast-forwarded`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

## Auto Run Result

Status: done
Blocking condition: none

**Summary.** The terminal-branch land site in `run_dispatch_supervisor` now resolves `COMPLETED` (`stop_reason: null`) when `_landing_succeeded(folded, run_id)` reads a journaled `landed` / `already_landed` land OUTCOME for the run. The check sits after the repository re-read and outside its `try`, so a failing re-read still completes. `gather_dispatch_git_facts`, the completion INTENT facts and the LIVE-branch land site are unchanged.

**Files changed.**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py` -- the journal-first override at the terminal land site (7 lines).
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_main_loop.py` -- the land-shape test asserts `completed`; new tests for a landed run (branch retired / present), a failing repository re-read, an `already_landed` ok outcome and a land that is not ok (refused / skipped).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` and `.../spec-pyforge-core/.memlog.md` -- surface-reconcile entries naming both changed paths.

**Review.** 21 findings: 5 patch entries applied (all `low`, all test-only), 0 deferred, 16 rejected with their reasons in the Review Triage Log. Patched counts by verdict: high 0, medium 0, low 5. No `bad_spec` or `intent_gap` loopback.

**Follow-up review recommended:** `false` -- no high patch, fewer than two medium patches.

**Verification.**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- exit 0, 9428 passed, 1 skipped, 12 deselected.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` -- exit 0.
- Mutation: replacing the override condition with `if False:` reds five tests, each `'stopped_externally' == 'completed'`; the fix is restored.
- Red first: the four new `completed` assertions failed on the unfixed tree; the two not-ok-land tests passed on both trees, as the contract requires.
- `python scripts/spec_surface_reconcile.py` and `spec-surface-check` -- exit 0 after the memlog entries; no baseline was stamped.

**Process deviation.** Step 3 calls for an implementation subagent. The implementation and its tests were written inline in this session, test-first, before the planning bookkeeping. Review (step 4) ran as four independent subagents against the diff, so implementation and review stayed separate.

**Residual risks.**
- A transient `FsError` while journaling the land OUTCOME still leaves a landed run reading `stopped_externally`; pre-existing, outside this contract's one-predicate rule (see the Review Triage Log).
- An `already_landed` outcome journaled `ok` is not something the supervisor writes itself (`ok = verdict == LANDED`); that row is pinned through a test shim, not through the supervisor's own journaling.
