---
title: "90.1: The dispatch supervisor records completion only after the harness session has really exited"
type: 'fix'
created: '2026-10-10'
status: 'done'
baseline_revision: '2578d8a3683dbab9414f221a662ab57f2f2e682a'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-22-2-completion-is-judged-from-git-and-process-facts-and-a-zombie-is-never-redispatched.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-22-10-branch-merged-requires-real-divergence-not-just-ancestry.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-28-24-supervisor-finalizes-when-the-harness-cannot-run-shell.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-51-7-landing-evidence-is-intent-scoped-not-just-station-scoped.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-73-1-a-follow-up-review-run-is-judged-and-landed-by-its-own-branch.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-83-1-dispatch-liveness-proves-a-pid-is-the-session-it-launched.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-83-14-a-manual-merge-mid-dispatch-never-strands-the-session-s-fixes.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_completion.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/supervise.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_supervisor_finalize.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadbuild.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/cursor.toml
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-core/src/pyforge/core/process.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the dispatch supervisor recorded atlas Story 25.1's run `completed` 1.3 seconds after launch, while its
cursor session went on working for six more minutes. The supervisor then exited, so nothing committed, verified,
reviewed or landed that work. Line numbers below are at `bab2162d73`.

**The atlas 25.1 run (evidence).** Run `pyforge-atlas-20261010T232600552Z-1b28d6db`; its Tier-3 journal is under
atlas's `implementation-artifacts/dispatch-runs/`.
- **Launch.** `dispatch-launch` INTENT at 23:26:00.552Z (`baseline_head_sha` `f9c6a87dbe`, `harness_profile`
  `cursor`, `model` `composer-2.5-fast`) and its OUTCOME with `session_pid` 3985988 and `supervisor_pid` 3985989.
- **First tick.** The supervisor attached at 23:26:00.918Z. At 23:26:01.828Z it journaled `dispatch-completion`
  INTENT with `verdict: completed`, `stop_reason: null`, `session_alive: true`, `changed_paths: []`,
  `current_head_sha == baseline_head_sha`, `branch_merged: false` and `story_merged_on_main: true`, then its OUTCOME,
  and a `dispatch-timing` pair with `story_started_at` 23:26:00.552Z, `story_ended_at` 23:26:01.828Z and
  `final_revision == baseline_revision`. Then it returned (`dispatch_supervisor/__main__.py:3064`-`:3070`).
  `dispatch-supervisor.log` is empty. No finalize, verification, push or landing entry follows.
- **The session went on.** The worktree `.worktrees/dispatch-pyforge-atlas-25.1` gained files until about 23:32Z, and
  cursor's `session.log` (written once, at exit) ends with the agent's own summary: the story spec at `in-review`, and
  under "Not done in this session" the step-04 review loop and the commit. The operator committed the session's work
  by hand on the branch at 23:55:10Z (`a54599d024`, 19 files, 869 added lines).

**The defect, precisely.**
1. **A merge that predates the run counted as this run's merge.** `gather_dispatch_git_facts`
   (`dispatch_supervisor/__main__.py:465`-`:560`) scans `origin/main`'s commit subjects. `origin/main` holds
   `56ee2dfbc8` "Merge pull request #1114 from rxm7706/dispatch/pyforge-atlas/25.1", the 2026-09-10 landing of the
   station's earlier Story 25.1 ("retire the second Lane-3 runtime"). Atlas's 2026-09-17 one-chain rekey (`86d1cdf3ee`)
   renamed that story 24.1 and later gave key 25.1 to today's story. A `dispatch/<slug>/<key>` PR-merge subject is trusted without spec
   corroboration (`core/promotion.py`, `_requires_spec_corroboration`, Story 51.7). Replayed with the real classifier
   at `f9c6a87dbe`, it is the one subject that puts `25.1` in the merged keys. Story 83.14's guard,
   `run_head_reached_ref(current_head, origin/main)` (`:552`-`:553`), then passed only because the run had not
   committed: its head was its baseline, which was `origin/main`'s tip. `branch_merged` has refused exactly that trap
   since Story 22.10 (`current_head_sha != baseline_head_sha`, `:527`). `story_merged_on_main` has no such rule.
2. **The judge reads a merge before it reads a live session.** `judge_dispatch_completion`
   (`core/dispatch_completion.py:126`-`:132`) returns `COMPLETED` on `branch_merged or story_merged_on_main` (`:128`)
   before it looks at `session_alive`. `resolve_terminal_session_verdict` (`core/supervise.py:916`-`:954`) sends a live
   session straight to it (`:942`-`:943`). So the tick loop (`:2617`-`:3070`) journaled `completed` with
   `session_alive: true` in the same entry, and returned.
3. **So the finalize never ran.** Story 28.24's finalize (`supervisor_should_finalize_harness_work`,
   `core/dispatch_supervisor_finalize.py:58`-`:75`) needs a dead session and no merge fact (`:67`, `:69`). The
   supervisor never reached a tick where the session was dead, so the dirty worktree was never committed, pushed,
   verified or landed.
4. **Liveness reads the launched pid alone.** `dispatch_session_alive` (`dispatch_verify.py:1095`-`:1098`) delegates to
   `fix_session_alive` (`:1101`-`:1110`): the pid exists, is no zombie and started near the launch. The session is
   launched in its own process group (`start_new_session=True`, `adapters/harness_bmadbuild.py:246`). `cursor-agent`
   is a bash wrapper that `exec`s node, and node runs each tool command as a child. A launched process that exits while
   a child keeps writing reads as dead. In this run the leader was alive at the judgment, so this was not the trigger.
   It is the same class of defect, and the operator's ruling asks for it to be closed.

**The cost.** A session's finished-but-uncommitted work sat in its worktree with no verification, review or landing,
and the run read `completed` to every reader. A completed verdict also lifts Story 22.2's zombie guard, so a second
dispatch of the same story could have launched while the first session was still writing.

**Approach:** a run is complete only after its whole session has exited, and a merge counts only when this run made
it. While the session lives, the supervisor keeps polling.
- **Liveness is the session's process group.** `dispatch_session_alive` reads true while the launched pid passes
  today's check, or while any process remains in the session's process group (the group the launch created, whose id
  is the launched pid) that started at or after the launch, less `PID_START_TOLERANCE_SECONDS` (`core/dispatch.py:144`).
  - A zombie member does not count. A member that started before the launch is a reused id, not the session (Story
    83.1's guard, applied to the group). A group read that cannot answer counts as alive (AD-8: what the supervisor
    cannot settle never reads as done), so the next tick asks again.
  - The read is injectable, so no unit test signals or reads a real host process group (AD-4). It is either a
    marshal port with a POSIX adapter (psutil, already a marshal dependency for supervisor process liveness, may serve)
    or a group read on `pyforge.core.process.ProcessPort`. If it lands on `ProcessPort`, `spec-pyforge-core`
    co-governs it, and every station's `ProcessPort` fake still conforms.
  - Every reader goes through `dispatch_session_alive`, so the tick loop, `cli/dispatch.py`'s
    `_is_dispatch_session_alive` (`:1796`-`:1805`) and `marshal status` all see the group. `fix_session_alive` keeps
    today's leader-only check.
- **No completion while the session lives.** `judge_dispatch_completion` returns `LIVE` while `session_alive` is true,
  whatever the merge facts read. The merge facts decide only once the session has exited. A live session journals a
  heartbeat and the loop polls again.
- **A merge counts only when this run made it.** `story_merged_on_main` is true only once the run's head has moved past
  its launch baseline, the rule `branch_merged` has followed since Story 22.10. At the baseline, Story 83.14's head
  check is trivially true and proves nothing. Story 73.1's follow-up scoping (`merge_subject_ref`) is unchanged.
- **Re-poll, not refuse, per the marshal spine.**
  - AD-75 and AD-9: completion is judged from git and process facts, observed from outside. While the process facts
    say the session lives, no verdict is terminal.
  - AD-33: git owns repository facts, and a merge commit that predates the run is not a fact about this run.
  - AD-8: "is this merge ours?" cannot be settled while the head sits at the baseline, so it reads as not merged,
    never as done.
  - A refusal (a terminal `failed`) would also end supervision while the session writes, stranding its work exactly
    as `completed` did. Re-polling costs one tick, and AD-6 already journals each tick's heartbeat.
- **After the session exits, the normal path runs.** Once the group has exited, the run is judged on its own facts.
  With work left in the worktree (uncommitted changes, or commits past the baseline), Story 28.24's finalize commits on
  the dispatch branch, pushes and verifies, and the landing follows policy and Story 83.18's holds. With no work, the
  run is `failed`, as today.
- **Unchanged:** a session that commits and exits is verified and landed as today. Story 83.14's manual merge mid-run
  keeps supervising. Story 73.1's follow-up review run, Story 85.x's verify-fix turn and its liveness, Story 83.18's
  hold, and every landing and promotion rule stay as they are.

Ledger key: `90-1-the-dispatch-supervisor-records-completion-only-after-the-harness-session-has-really-exited`.
Type / Effort / Deps: fix / M / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-marshal` CAP-160 (← `spec-marshal-single-story-dispatch` CAP-2): Story 22.2's
  completion judgment from git and process facts, the CAP that shipped supervisor completion detection. With it,
  CAP-167 (← `spec-marshal-single-story-dispatch` CAP-9, Story 22.10: a merge fact is never true on ancestry alone),
  whose rule this story extends to `story_merged_on_main`, and CAP-141 (← `spec-marshal-drain-self-resolution` CAP-7,
  Story 28.24: the supervisor finalizes a dirty worktree), which this story makes reachable. It fixes their
  realization, so it mints no CAP and changes no `SPEC.md`.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag: it restores intended behaviour, and a
  flag would keep the defect reachable.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-10 (completed while the session ran). Operator
  ruling 2026-10-10, verbatim label: "Yes, mint it (Recommended)".

## Acceptance Criteria

The supervisor-loop tests use the existing `tests/unit/test_dispatch_supervisor_main_loop.py` fakes and a fixture run
journal in the run-dir shape the supervisor reads. The process-group read is a fake in those tests and real in AC2's.

- **AC1 — The atlas 25.1 sequence never completes while the session lives.**
  - **Given** a fixture journal shaped like run `pyforge-atlas-20261010T232600552Z-1b28d6db` (a launch INTENT and
    OUTCOME with a `session_pid`, then the supervisor's attach), a worktree head equal to the baseline, `origin/main`
    subjects holding "Merge pull request #1114 from rxm7706/dispatch/pyforge-atlas/25.1", and changed paths that grow
    tick by tick.
  - **And** the launched pid already dead, with the session's process group alive for three ticks.
  - **When** the supervisor runs **Then** no `dispatch-completion` or `dispatch-timing` is journaled during those three
    ticks, each journals a heartbeat with `session_alive: true`, and every gathered `story_merged_on_main` is false.
  - **When** the group then exits with the worktree dirty **Then** the finalize is journaled (a `dispatch-finalize`
    INTENT and OUTCOME: commit on the dispatch branch, push, verification). No `dispatch-completion` precedes it, and
    none reads `completed` with a `final_revision` equal to the baseline.
- **AC2 — A launched parent that exits early does not end the session.** A real process test, POSIX only:
  - it launches, with `start_new_session=True` as the harness adapter does, a shell that starts a background child
    appending to a file every 100 ms for about two seconds, and exits at once;
  - after the parent has exited and been reaped, `dispatch_session_alive(pid, launched_at=...)` is true while the file
    still grows;
  - it is false within one second of the child's exit;
  - a fake group whose only member started before the launch, less the tolerance, reads as not alive; a zombie
    member does not count; a group read that raises reads as alive.
- **AC3 — No completion while the session lives, whatever `main` says.**
  - `judge_dispatch_completion` with `session_alive` true returns `LIVE` for every combination of `branch_merged` and
    `story_merged_on_main`; with `session_alive` false it returns what it returns today.
  - `marshal factory dispatch` of the same story while the group lives is refused as a live session, naming the
    evidence (Story 22.2's zombie guard), and `marshal status` shows the run live.
- **AC4 — A merge counts only when this run made it.**
  - **Given** a corroborated merge subject naming the story on `origin/main` **When** the run's head equals its
    baseline **Then** `story_merged_on_main` is false; **When** the head has moved and is on `origin/main` **Then** it
    is true; **When** the head has moved but is not on `origin/main` **Then** it is false (Story 83.14, unchanged).
  - A follow-up review run (Story 73.1) reads the same as today at a moved head.
- **AC5 — After the session exits, the normal path runs.**
  - A session that exits with uncommitted changes and the head at the baseline is finalized (committed, pushed,
    verified), then landed under policy and Story 83.18's holds, through the existing finalize and land code.
  - A session that exits with nothing changed is `failed`, as today.
  - A session that exits with commits past the baseline is verified and landed as today.
- **AC6 — Everything else is unchanged.** Every existing test in the marshal suite passes, with exactly these
  exceptions, each keeping what it tests:
  - `test_gather_git_facts_corroborates_a_station_branch_pr_against_the_tracked_spec`
    (`tests/unit/test_dispatch_supervisor_main_loop.py:987`-`:1011`): its fake head is the baseline, so its `merged`
    case would read false. Its fake head moves off the baseline (`head_sha=_MOVED`); its three assertions stay.
  - `test_a_follow_up_in_the_stories_surviving_pre_merge_worktree_is_scoped_by_the_launch_tip_against_real_git`
    (`:3665`-`:3732`): its normal-run premise is read at the unmoved baseline, and its `verdict()` helper judges a live
    session. The premise is read after a run commit, the verdicts judge an exited session, and one added assertion
    pins that a live session reads `LIVE`.
  - `test_without_the_run_head_gate_the_manual_merge_fixture_reads_completed_on_the_first_tick` (`:3638`-`:3656`):
    with the session alive on the first tick, dropping Story 83.14's head gate no longer completes the run on that
    tick. It now asserts that the run completes only on the tick after the session exits.
  - The dev names any other changed expectation, with its reason, in this spec's Spec Change Log.
- **AC7 — Mutation.**
  - Restoring the merge-first order in `judge_dispatch_completion` fails AC1 and AC3.
  - Dropping the process-group read fails AC2 and AC1.
  - Dropping the divergence rule for `story_merged_on_main` fails AC4's first case and AC1's merge assertion.
  - Skipping the finalize after a dirty exit fails AC5's first case.

## Boundaries & Constraints

**Always:**
- Keep the judgment pure (`core/`, AD-4) and the process and git reads at the impure edge.
- Read the session's process group through an injectable port, never by signalling a real host group from a unit test.
- Journal every tick's heartbeat and every finalize before acting on it (AD-6).
- Reconcile every governed path the change touches on the memlogs of the Specs that govern it, then stamp those Specs
  scoped: `spec-pyforge-marshal`, and `spec-pyforge-core` if `ProcessPort` or its tests change, plus every co-governor
  `spec-surface-check` names (AGENTS.md pre-PR item 5).

**Never:**
- Never journal `dispatch-completion` while any process of the session's group, started at or after the launch, is
  alive.
- Never count a merge fact for a run whose head has not moved past its launch baseline.
- Never read the session's own report (its `session.log`, its spec status) as a liveness or completion fact (AD-9).
- Never signal, stop or kill a session from this change; the supervisor only observes.
- Never change the landing, verification, the verify-fix turn, Story 83.18's hold or Story 89.1's gate.

**Residual risk:**
- A process that leaves the session's group (its own `setsid`, or a daemon that double-forks into a new session) is not
  seen. One that never exits keeps the run live until the operator stops it.
- A group read that keeps failing keeps the run live; it never reads as done.

## I/O & Edge-Case Matrix

| Session processes | Head vs baseline | Merge facts | At `bab2162d73` | After |
|---|---|---|---|---|
| leader alive | equal | a stale subject names the key | `completed` on the first tick; supervisor exits | `LIVE`; heartbeat; poll again |
| leader dead, a child alive | equal, worktree dirty | stale subject | `completed` | `LIVE` until the group exits |
| group exited | equal, worktree dirty | stale subject | `completed`, never finalized | finalize: commit, push, verify, land |
| group exited | equal, worktree clean | stale subject | `completed` | `failed` |
| group exited | moved, on `origin/main` | merged | `completed` | `completed`, unchanged |
| leader alive | moved, on `origin/main` (hand merge) | merged | `completed` | `LIVE` until the session exits, then `completed` |
| group exited | moved, not on `origin/main` | stale subject | verify and land | unchanged |
| a reused id: every group member started before launch | any | any | n/a | not alive |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-10 (completed while the session ran) entry.
- Epic: Epic 90 (a new fix epic, because Epics 22, 28 and 83, which shipped completion judgment, the finalize and the
  head check, are `done`).
- Ledger key: `90-1-the-dispatch-supervisor-records-completion-only-after-the-harness-session-has-really-exited`.
- Ledger status at mint: `backlog`.
- Deps: none.
- Surface: `[epic_surfaces]` `"90"` in `marshal-policy.toml` (the default surface, `pyforge-core`'s `process.py` and its
  tests, and every Spec memlog).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python scripts/spec_surface_reconcile.py` — expected: exit 0 (the derived surface guard).

**Manual checks (not a dispatch gate):**
- `pixi run --frozen -e pyforge-core pyforge-core-test` — expected: pass, if `ProcessPort` or its tests change.
- The four mutations of AC7 — expected: each fails its named test. Restore each.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconciles and scoped
  stamps.
- On the next cursor dispatch, its run's `journal.jsonl` holds no `dispatch-completion` before the session's process
  group has exited, and a session that exits with a dirty worktree is followed by a `dispatch-finalize` pair.

## Named, not fixed here

- **A rekeyed story's earlier landing still reads as a merge of today's key** wherever the merge-subject scan runs
  with no run head to check: the drain's merged-key read (`cli/dispatch.py:4444`) and `marshal status`. For atlas 25.1
  that is `56ee2dfbc8`. This story stops it from completing a run; it does not change those readers.
- **`supervisor_should_exit`'s result is ignored.** Both of the tick loop's final branches return 0
  (`dispatch_supervisor/__main__.py:3064`-`:3070`).
- **The verify-fix turn's liveness stays leader-only** (`fix_session_alive`, `wait_for_process`). The fix turn is
  bounded by its budget and stopped with `terminate_process_group`, which already signals the whole group.

## Review Triage Log

### 2026-10-10 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (none — implementation matches AC1–AC7; verification green)

## Auto Run Result

Status: done

**Summary:** Dispatch completion now treats a live session (leader or process group) as non-terminal, applies the Story 22.10 baseline divergence rule to `story_merged_on_main`, and observes session process groups through an injectable `SessionGroupPort` with a psutil adapter.

**Files changed:**
- `core/dispatch_completion.py` — judge `LIVE` while `session_alive`
- `dispatch_supervisor/__main__.py` — baseline gate on `story_merged_on_main`
- `dispatch_verify.py` — group-aware `dispatch_session_alive`
- `ports/session_group.py`, `adapters/session_group_psutil.py` — injectable group read
- `core/egress.py` — register `SessionGroupPort`
- Unit tests and hermetic `conftest` default for session group

**Review:** No patch/defer items.

**Follow-up review recommended:** false

**Verification:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — pass (12241 passed)
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — pass
- `pixi run --frozen -e pyforge-guild lint-types` — pass
- `python scripts/spec_surface_reconcile.py` — pass (after memlog reconcile on `spec-pyforge-marshal`)

**Residual risk:** Processes that leave the session group remain invisible; unreadable group scans keep the run live (AD-8).

> **Code reverted 2026-10-11** (operator ruling "Revert 90.1 now (Recommended)"). The landed `PsutilSessionGroup`
> asked `psutil.process_iter` for a `pgid` attribute psutil 7.2.2 does not have, so every read raised
> `ValueError`, which this story counts as a live session: every dispatch supervisor launched after the merge
> (`d013fdb9fe`) journaled `session_alive: true` forever and never verified or landed (marshal 47.1 stalled). The merge's
> code and tests were reverted on main; this spec, its memlogs and the ledger key stay as the record. Marshal Story 92.1
> re-lands the completion-after-exit behaviour with a working group read, with its landing held for an independent review.
