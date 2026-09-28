---
title: '67.1: A landed dispatch reads completed when the primary checkout cannot be fast-forwarded'
type: 'fix'
created: '2026-09-28'
status: 'backlog'
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
