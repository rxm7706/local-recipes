---
title: "89.1: A re-dispatch never lands a story whose review failed"
type: 'fix'
created: '2026-10-10'
status: 'in-progress'
baseline_revision: '1382b713fe6e08eb09b41d81816463fefa9e17f9'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-29-2-harness-done-is-cap-4-only-never-another-session.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-83-7-a-re-dispatch-after-a-refused-landing-lands-the-existing-branch-without-a-new-session.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-83-10-a-verification-refusal-never-relaunches-a-fresh-session-or-raises-the-model.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-83-18-a-re-dispatched-send-back-waits-for-its-landing-review.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-79-1-a-landing-promotes-the-story-s-tier-3-feed-row-and-its-tracked-spec-not-only-the-ledger-twin.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_harness_done.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_retry.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/drain_plan.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/vcs.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py
  - .claude/skills/bmad-build-auto/step-04-review.md
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** a single-story re-dispatch landed steward Story 87.3 after an independent review had failed it, and the
landing's finalize then marked its spec `done`. Marshal's land-only path reads the latest run's journal and the
worktree spec's `status:`, and nothing else the reviewer wrote. Line numbers below are at `a8eae09dce`.

**The 87.3 sequence (evidence):**
- **First run.** Dispatch run `pyforge-steward-20261010T154144466Z-88c00f58` (Tier-3 journal under steward's
  `implementation-artifacts/dispatch-runs/`):
  - verification refused at `MRS-GATE-015` on `platform-ci-local -- --test` (16:04:53Z);
  - the one verify-fix turn hit its 900 s budget, `MRS-DISP-059` (16:19:55Z);
  - `dispatch-completion` verdict `failed`, with `final_revision` `dd20cb0857` (16:19:56Z).
- **The failed review.** The operator fixed two problems by hand on the branch (`07a668d7ab`, `cc506e7a33`), merged
  `origin/main` into it (`ec1978f4f8`), and recorded an independent review in the tracked spec (`3f9295e784`):
  `status: 'in-progress'`, `review_loop_iteration: 1`, and a `## Review Triage Log` entry headed
  "2026-10-10 — Independent review, iteration 1: FAIL (3 high, 3 medium)", whose items are all open.
- **The re-dispatch.** `marshal factory dispatch pyforge-steward 87-3-…` ran `dispatch_once`
  (`cli/dispatch.py:3153`-`:3244`):
  - `should_take_harness_done_land_only` (`:3182`; `core/dispatch_harness_done.py:192`-`:213`) returned false: the
    spec is not `done`, and the run journaled no `dispatch-land`.
  - `should_take_verification_refusal_land_only` (`:3192`; `:216`-`:251`, Story 83.10) returned true: the run failed
    on a verification refusal, the worktree head had moved past `dd20cb0857`, and `in-progress` is one of
    `_REFUSED_LANDING_LAND_ONLY_STATUSES` (`:145`).
  - `_attempt_harness_done_cap4` (`:3203`) re-verified (journaled `verified` in the same run dir by writer
    `dispatch-land-2915024`, 19:51:15Z) and merged the branch head: `85e70dedf5` "Merge pyforge-steward/87-3 into
    main".
- **The promotion.** `dispatch_land_finalize`'s `_promote_tracked_spec` (`__main__.py:750`-`:846`) read the spec on
  `origin/main` at `in-progress`, which is in `PRE_DONE_SPEC_STATUSES` (`core/promotion.py:634`). It published
  `a8eae09dce` "marshal: promote story 87.3's tracked spec to done", and the ledger key went to `done` (`67efacdf08`).
- **The cost.** A forward that lets a client reach the sidecar's unauthenticated MCP faces reached `main` and was
  marked done. The operator turned its flag OFF everywhere and minted steward Story 87.4 to close the findings.

**Why the rule missed it.** Story 83.10 reads a moved head as "the operator fixed the branch", and Story 83.7 reads
`in-progress` as "where a session stopped". On 2026-10-02 that was right: marshal 82.5's operator fixed the branch by
hand and left its spec at `in-progress` (83.7's evidence). On 2026-10-10 the same two facts meant the opposite: the
operator had sent the story back. The status cannot tell the two apart. The review entry can.

**Approach:** the land-only path lands only work its spec says is finished and whose latest review did not fail.
Otherwise it refuses by name and tells the operator how to go on.
- **One gate, after the land-only decision.** When either land-only decision is true, a new pure function in
  `core/dispatch_harness_done.py` judges the worktree's tracked spec. `cli/dispatch.py` and `cli/drain_plan.py` both
  call it, so the plan and the dispatch agree, as Story 83.7 required. It refuses when:
  - the spec's `status:` is not `in-review` or `done`; or
  - the latest entry of its `## Review Triage Log` records a failed review; or
  - either fact cannot be read (AD-8: unevaluable is failure).

  `should_take_harness_done_land_only` and `should_take_verification_refusal_land_only` keep their signatures and
  their tests.
- **A failed review, read the way reviewers write it.** An entry is a `### ` heading inside `## Review Triage Log`,
  up to the next `## ` heading. It records a failed review when its heading holds the word `FAIL` in capitals, or the
  phrase `sent back` in any case. Both forms are in tracked specs today ("Review 1 — … — FAIL (1 high, 2 medium)",
  "Landing review (operator session) — sent back").
  - A `[patch]` tag alone is not read as an open finding. `bmad-build-auto` writes the same tag on patches it has
    already applied (`step-04-review.md`, the entry format and its "action taken for patches"), so only the
    heading's verdict counts.
  - `send-back` alone is not read as a verdict either: passing entries use it ("Review pass (send-back guard)").
- **"Latest" is git's order, not the file's.** The latest entry is the one whose heading line git added last on the
  tree being judged, as `git blame` reports it. An uncommitted heading is newer than any committed one. When several
  headings share the newest commit, the latest is a failed review if any of them is (AD-8).
  - Tracked specs hold both orders: harness passes are appended (step-04), and the 2026-10-03 operator reviews were
    written above older entries (83.7's spec). So position cannot say which is newest. AD-33 makes git the authority
    for repository facts.
  - A harness `Review pass` entry added after a failed review is the latest entry, and it is not a failed review. So a
    story sent back, re-implemented and reviewed again lands as before.
- **The refusal.** A new ERROR finding, `MRS-DISP-063` (the next free code at mint; registered in `core/findings.py`
  and `core/verdict.py`):
  - The message names the story, the spec's status and, when there is one, the failed entry's heading.
  - It says how to go on: to resume implementation, set the spec's `status:` to `ready-for-dev` and re-dispatch;
    to land finished work, set `in-review` (or `done`) once its review passes.
  - The dispatch stops before `_attempt_harness_done_cap4`: no verification, push, PR, merge or finalize, and no
    session launch. It exits non-zero.
  - It is journaled in the story's latest run dir as a `dispatch-blocked` INTENT and OUTCOME pair, the kind Story
    51.4 uses for a stop before verify and land. The payload holds the code, the status, the heading or `null`, and
    the worktree head. It is never a `dispatch-land` entry, because a refused `dispatch-land` would arm Story 83.7's
    land-only rule and Story 83.4's station hold.
  - `marshal factory drain --plan` reports the same story as refused with `MRS-DISP-063`, not as land-only.
- **Refuse, not resume, per the marshal spine.**
  - AD-8: after a finished run whose head moved, `in-progress` cannot say "finished, status not yet moved" (82.5)
    from "sent back" (87.3). Landing would merge 87.3's work. Launching would spend a full session on 82.5's finished
    work, the cost Story 83.7 removed. Only a refusal is right in both cases.
  - AD-75: a session is launched once per invocation, from the status the operator set. Stories 83.7 and 83.10
    already make `ready-for-dev` or `draft` the one send-back that launches a session. The message points at that
    switch instead of adding a second one.
  - AD-32: the Review Triage Log is prose a session or an operator wrote. It may stop a landing. It never starts a
    session.
  - Story 51.4's `MRS-DISP-045` is the precedent: a `blocked` spec is never relaunched without an operator decision.
- **The finalize never promotes past a failed review.** Before `_promote_tracked_spec` writes anything, it reads the
  latest Review Triage Log entry of the spec at `origin/main` by the same rule, ordered by `git blame` at
  `origin/main`. If that entry records a failed review, it publishes nothing for the spec or its epics **Status:**
  line. It returns an `MRS-DISP-047` WARN naming the path and the heading. The sprint ledger's promotion is unchanged:
  the merge is a git fact (AD-33), and the ledger records it.
- **Unchanged:** a story with no earlier run launches a session; the supervisor's own verify and land of a run it
  supervised; a send-back to `ready-for-dev` or `draft`; Story 73.1's follow-up review run; Story 83.18's hold rules
  (`landing_review:`, `--hold-landing`); Story 51.4's `blocked` refusal.

Ledger key: `89-1-a-re-dispatch-never-lands-a-story-whose-review-failed`.
Type / Effort / Deps: fix / M / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-marshal` CAP-169 (← `spec-marshal-single-story-dispatch` CAP-11): Story
  29.2's land-only path for a session-terminal story, extended by Story 83.7 (a refused landing), Story 83.10 (a
  verification refusal on a moved head) and Story 83.18 (a held landing). The finalize half is CAP-229 (promotion
  runs on landing), realized for the tracked spec by Story 79.1. This story fixes their realization, so it mints no
  CAP and changes no `SPEC.md`.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag: it restores intended behaviour, and a
  flag would keep the defect reachable.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-10 (a failed review landed). Operator ruling
  2026-10-10, verbatim label: "Yes, mint it (Recommended)".

## Acceptance Criteria

Every test builds a real temporary git repo for the worktree (the existing `vcs`/`repo` fixtures) and a fixture run
journal in the run-dir shape `dispatch_once` reads. The forge, the harness and the verification are fakes that
record every call.

- **AC1 — The 87.3 sequence refuses.**
  - **Given** a fixture journal shaped like run `pyforge-steward-20261010T154144466Z-88c00f58`: a launch INTENT, a
    `dispatch-verification` refused at `MRS-GATE-015`, a `dispatch-verify-fix` OUTCOME `MRS-DISP-059`, a
    `dispatch-completion` verdict `failed`, and a `dispatch-timing` `final_revision` X.
  - **And** a worktree whose head is a later commit that sets the tracked spec to `status: 'in-progress'` and
    `review_loop_iteration: 1`, and adds the heading "2026-10-10 — Independent review, iteration 1: FAIL (3 high, 3
    medium)".
  - **When** `marshal factory dispatch` runs for that story **Then** the envelope carries `MRS-DISP-063` and the
    command exits non-zero. The message names `in-progress`, the heading, and both ways on.
  - The fakes record no verification, no push, no PR call and no merge, and no session is launched (no
    `dispatch-launch` INTENT). The run dir gains one `dispatch-blocked` INTENT and OUTCOME pair carrying
    `MRS-DISP-063` and no `dispatch-land` entry.
  - `marshal factory drain --plan` lists the story as refused with `MRS-DISP-063`, `land_only` false.
- **AC2 — Status alone refuses.** With the same journal:
  - a spec at `in-progress` with an empty Review Triage Log refuses with `MRS-DISP-063`;
  - so does a spec at `in-progress` after a refused `dispatch-land` (Story 83.7's shape) or a `held-for-review`
    one (Story 83.18's shape);
  - a spec at `in-review` with no failed entry takes the land-only path as today, in all three shapes.
- **AC3 — A failed review refuses whatever the status.** A spec at `in-review`, and separately at `done`, whose
  latest entry records a failed review (`FAIL`, and separately `sent back`) refuses with `MRS-DISP-063`.
- **AC4 — Latest means git's order.**
  - **Given** a failed-review heading committed first and a harness `### <date> — Review pass` heading committed
    later, written below it **Then** the land-only path proceeds.
  - **Given** the same two headings, with the failed one committed later but written above the older `Review pass`
    **Then** it refuses.
  - **Given** the failed heading uncommitted in the worktree **Then** it refuses.
  - **Given** two headings added by one commit, one failed **Then** it refuses.
  - **Given** a heading that carries `[patch]` rows but neither `FAIL` nor `sent back` **Then** it is not a failed
    review.
- **AC5 — The send-back still launches a session.** **Given** AC1's journal and the spec moved to `ready-for-dev`
  (or `draft`) **When** the story is dispatched **Then** a session launches as today, with no `MRS-DISP-063`.
- **AC6 — The finalize never promotes past a failed review.**
  - **Given** a merged story whose tracked spec on `origin/main` reads `in-progress` and whose latest entry is AC1's
    heading **When** `dispatch_land_finalize` runs **Then** `_promote_tracked_spec` publishes no commit, the spec and
    its epics **Status:** line are unchanged on `origin/main`, and an `MRS-DISP-047` WARN names the spec path and the
    heading. The ledger promotion still runs.
  - **Given** the same spec with a later `Review pass` entry **Then** it is promoted to `done` as today.
- **AC7 — The first run is unchanged.** A story with no earlier run launches a session. The supervisor's verify and
  land of a run it supervised, and its own finalize, behave as before. Every existing test in the marshal suite
  passes, with exactly two exceptions: `test_in_progress_spec_with_refused_landing_journal_is_land_only` and
  `test_in_progress_spec_with_held_landing_journal_is_land_only` (`tests/unit/test_dispatch.py`). They now expect
  `MRS-DISP-063`, and twins at `in-review` keep the land-only coverage of Stories 83.7 and 83.18. The pure-function
  tests of `test_dispatch_harness_done.py` and `test_dispatch_retry_83_10.py` pass unchanged.
- **AC8 — Mutation.**
  - Dropping the status check fails AC2.
  - Dropping the Review Triage Log check fails AC3.
  - Ordering entries by their position in the file fails AC4's second case.
  - Calling the gate from only one of `cli/dispatch.py` and `cli/drain_plan.py` fails AC1's plan assertion.
  - Dropping the finalize check fails AC6.

## Boundaries & Constraints

**Always:**
- Keep one gate, in `core/dispatch_harness_done.py`, pure (AD-4). The impure edge reads the spec, the journal and git.
- Read the order of the Review Triage Log's headings from git through the VcsPort, never from file position.
- Journal every refusal in the story's latest run dir before returning (AD-6, write before act).
- Reconcile every governed path the change touches on the memlogs of the Specs that govern it, then stamp those Specs
  scoped: `spec-pyforge-marshal`, and `spec-pyforge-core` for the ports and the adapter, plus every co-governor
  `spec-surface-check` names (AGENTS.md pre-PR item 5).

**Never:**
- Never land, push, open or merge a PR, finalize, or launch a session for a refused story.
- Never journal the refusal as a `dispatch-land` entry, and never let it trip Story 83.4's station hold.
- Never edit a story spec's status, its Review Triage Log or its ledger key to get past the gate.
- Never read a `[patch]` tag as an open finding, or `send-back` alone as a verdict.
- Never change the supervisor's first-run landing, Story 83.18's hold, or the sprint ledger's promotion.

**Residual risk:**
- A reviewer who records a failure without `FAIL` or `sent back` in the heading is not seen by the review check. The
  status check still refuses unless the spec reads `in-review` or `done`.
- A session that finished its work but left the spec at `in-progress` (82.5's shape) now needs the operator to set
  `in-review` before a land-only re-dispatch. That one edit is the price of never guessing.
- A heading line edited later (a typo fix) becomes the newest entry. If it is a failed review the gate refuses, which
  is safe; if it is an older passing entry, it can hide a failed one. Reviewers append new entries rather than edit
  old ones.

## I/O & Edge-Case Matrix

| Latest run | Worktree spec | Latest triage entry | At `a8eae09dce` | After |
|---|---|---|---|---|
| verification refused, head moved | `in-progress` | FAIL | land-only: merged, then promoted to `done` | `MRS-DISP-063`, nothing landed |
| verification refused, head moved | `in-review` | Review pass | land-only | land-only, unchanged |
| verification refused, head moved | `in-review` | FAIL or sent back | land-only | `MRS-DISP-063` |
| refused or held `dispatch-land` | `in-progress` | none | land-only | `MRS-DISP-063`, naming both ways on |
| refused or held `dispatch-land` | `in-review` | none | land-only | land-only, unchanged |
| harness done | `done`, no follow-up | FAIL | land-only | `MRS-DISP-063` |
| any | `ready-for-dev` or `draft` | any | session launches | unchanged |
| none | any | any | session launches | unchanged |
| finalize after any merge | spec on `origin/main` | FAIL | promoted to `done` | not promoted; `MRS-DISP-047` WARN |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-10 (a failed review landed) entry.
- Epic: Epic 89 (a new fix epic, because Epics 29, 79 and 83, which shipped the land-only path and the promotion, are
  `done`).
- Ledger key: `89-1-a-re-dispatch-never-lands-a-story-whose-review-failed`.
- Ledger status at mint: `backlog`.
- Deps: none.
- Related: steward Story 87.4 closes 87.3's review findings. This story stops the same landing from happening again.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- `pixi run --frozen -e pyforge-core pyforge-core-test` — expected: pass (the VcsPort changes; `spec-pyforge-core`
  co-governs it).
- Mutation: restore the land-only path without the gate and re-run the new tests. AC1 to AC3 fail. Restore it.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconciles and scoped
  stamps.
- On the next re-dispatch of a story whose spec reads `in-progress` after a finished run, the command exits non-zero
  with `MRS-DISP-063`, and its latest run's `journal.jsonl` holds the `dispatch-blocked` pair.

## Named, not fixed here

- **The land-only path journals no `dispatch-land` outcome.** On 87.3's re-dispatch the run dir gained the land-only
  verification (Story 22.17) but no record of the merge. Only the supervisor journals `dispatch-land`. This story
  journals its refusal, and leaves the landing's own journal as it is.
