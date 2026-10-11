---
title: "92.1: The dispatch supervisor reads session liveness correctly and never treats a vanished worktree as live"
type: 'fix'
created: '2026-10-10'
status: 'in-progress'
baseline_revision: '6b5182c155fa451b9d5af75f8945e57537166a33'
review_loop_iteration: 0
followup_review_recommended: false
landing_review: 'required'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-90-1-the-dispatch-supervisor-records-completion-only-after-the-harness-session-has-really-exited.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-83-1-dispatch-liveness-proves-a-pid-is-the-session-it-launched.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-22-2-completion-is-judged-from-git-and-process-facts-and-a-zombie-is-never-redispatched.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-22-10-branch-merged-requires-real-divergence-not-just-ancestry.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-28-24-supervisor-finalizes-when-the-harness-cannot-run-shell.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-83-14-a-manual-merge-mid-dispatch-never-strands-the-session-s-fixes.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-73-1-a-follow-up-review-run-is-judged-and-landed-by-its-own-branch.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-22-5-one-story-in-flight-per-station-stations-in-parallel-overlap-is-loud.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-28-16-parallel-dispatch-fan-out-when-deps-and-surfaces-are-disjoint.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-83-4-a-serial-campaign-holds-the-next-overlapping-story-while-a-refused-story-is-unlanded.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-83-18-a-re-dispatched-send-back-waits-for-its-landing-review.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_completion.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/supervise.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_supervisor_finalize.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/egress.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadbuild.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_harness_done.py
  - src/shared/packages/pyforge-core/src/pyforge/core/process.py
  - scripts/fleet_picture.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 90.1's code has been reverted. This story lands its behaviour again, in a form that works: the
supervisor records completion only after the harness session's whole process group has exited. It also closes the
crash 90.1 exposed, where a run whose worktree had vanished was read as live.

**Where the line numbers point.** The 90.1 revert, merged as `a085cd0344` (PR #2106), restores
`dispatch_verify.py`, `core/dispatch_completion.py`, `core/egress.py` and `dispatch_supervisor/__main__.py` to their
content before 90.1's merge `d013fdb9fe`. That content is byte-identical to `bab2162d73`, as are `core/supervise.py` and
`tests/unit/test_dispatch_supervisor_main_loop.py` (checked: no diff between `bab2162d73` and `a085cd0344` for any of
them). So their line numbers below are at `bab2162d73`, the commit Story 90.1's spec cites, and hold on `main` at
`a085cd0344`. Every other file is untouched by 90.1 and the revert, and its line numbers are at `909a725e16`, unchanged
at `a085cd0344`.

**The operator's rulings.**
- 2026-10-11, verbatim: "Revert 90.1 now (Recommended)". A hotfix (branch `hotfix-revert-901-2026-10-11`, PR #2106,
  merged as `a085cd0344`) reverted the code and tests of merge `d013fdb9fe`:
  - `adapters/session_group_psutil.py` and `ports/session_group.py` are removed;
  - `core/dispatch_completion.py`, `core/egress.py`, `dispatch_supervisor/__main__.py` and `dispatch_verify.py` are
    restored;
  - the related tests are removed or restored.
  
  90.1's spec, its memlog entries and its `done` ledger key stay, and its spec carries a dated "Code reverted
  2026-10-11" note.
  After the revert, liveness is leader-pid only again (Story 83.1). A completion verdict reads merge facts before
  `session_alive` again. `story_merged_on_main` again has no divergence rule.
- 2026-10-11, verbatim: "Retitle (Recommended)". This story takes the title above.

**What 90.1 was for, and is owed again** (`spec-90-1-…` § Intent, at `bab2162d73`).
- Atlas Story 25.1's run `pyforge-atlas-20261010T232600552Z-1b28d6db` was journaled `completed` 1.3 s after launch,
  while its cursor session kept writing for six more minutes. Three defects caused it:
  - `gather_dispatch_git_facts` (`dispatch_supervisor/__main__.py:465`-`:560`) counted a 2026-09-10 merge of a rekeyed
    story as this run's, because `story_merged_on_main` lacks Story 22.10's divergence rule.
  - `judge_dispatch_completion` (`core/dispatch_completion.py:126`-`:132`) returns `COMPLETED` on a merge fact before
    it reads `session_alive`.
  - `dispatch_session_alive` (`dispatch_verify.py:1095`-`:1098`) reads the launched pid alone, though the session runs
    in its own process group (`start_new_session=True`, `adapters/harness_bmadbuild.py:246`).
- So Story 28.24's finalize (`core/dispatch_supervisor_finalize.py:58`-`:75`) never ran.

**Why 90.1's code had to go (evidence, at `909a725e16`, before the revert).**
- **The group read always failed.** `PsutilSessionGroup` called `psutil.process_iter(["pid", "pgid", "create_time",
  "status"])`. psutil has no `pgid` attribute, and on the pinned psutil 7.2.2 the call raises `ValueError: invalid attr
  name 'pgid'` every time. 90.1 counted that read error as alive. So every session whose leader had exited read as
  alive, for good. Replayed on the host with the real adapters, `dispatch_session_alive` was true in two cases:
  - pid 63830, the 2026-10-04 marshal 86.6 run; the host booted on 2026-10-06, so that process is long gone;
  - pid 4000000, which never existed.
  
  The leader-only check returned false for both.
- **Its tests could not see it.** The adapter tests replaced `psutil.process_iter` with fakes that yield a `pgid` key.
  The real-process test asserted only the live half, which the error path satisfied. No test pinned 90.1's own AC2
  clause "false within one second of the child's exit".
- **Its member rule was narrower than its spec.** A group member counted only if it started within
  `PID_START_TOLERANCE_SECONDS` (30 s, `core/dispatch.py:144`) of the launch, on either side. 90.1's spec said "at or
  after the launch".
- **The 47.1 launch crashed.** The primary fast-forwarded to 90.1 at 03:02:45Z on 2026-10-11, and by 03:07Z marshal
  47.1's launch had crashed:
  1. `station_in_flight_conflict` (`cli/dispatch.py:2173`) read the stale 86.6 run as `LIVE`, through
     `resolve_dispatch_session_verdict` (`:1808`, called at `:2221`).
  2. `_live_dispatch_evidence` (`:1875`, called at `:2239`) called `gather_dispatch_git_facts` with no `try` (`:1905`).
  3. `worktree_head_sha` (`adapters/vcs_git.py:1434`) raised `VcsCommandError: git rev-parse HEAD failed in
     .worktrees/dispatch-pyforge-marshal-86.6`, a worktree an operator sweep had removed.
  
  The operator quarantined 51 such runs, listed in each station's `implementation-artifacts/dispatch-runs-quarantine/README.md`:

  | Station | Runs |
  |---|---|
  | marshal | 21 |
  | atlas | 15 |
  | scribe | 4 |
  | steward | 4 |
  | doctor | 3 |
  | herald | 2 |
  | mason | 2 |
- **The relaunched 47.1 stalled.** Run `pyforge-marshal-20261011T030728372Z-51af3462` (`session_pid` 1225664,
  supervisor 1225665) wrote `session.log` at exit, at 03:11:29Z. Its spec read `done` and its work was committed
  (`10e26d2003`). Its supervisor journaled 324 `session_alive: true` heartbeats, from 03:07:29Z until 08:35:29Z, when it
  stopped. It neither verified nor landed, and 47.1's key still reads `backlog`.
- **The vanished-worktree crash outlives the revert.** With leader-only liveness, the 86.6 run reads as dead and the
  guard skips it. But any run whose pid reads alive and whose worktree is gone still reaches the uncaught
  `VcsCommandError`: for example, a reused pid whose start time cannot be read, which Story 83.1's check lets through
  (`pid_start_matches_launch`, `core/dispatch.py:144`-`:156`). The 2026-10-02 quarantine (`README.txt`: two 28.4 runs
  whose pids had become Firefox thread ids) was that class.

**Approach:**
- **Re-land 90.1's completion rule, unchanged in substance** (its spec § Approach):
  - `judge_dispatch_completion` returns `LIVE` while the session lives, whatever the merge facts read.
  - `story_merged_on_main` counts only once the run's head has moved past its launch baseline, as `branch_merged`
    does since Story 22.10.
  - After the group exits with work in the worktree, Story 28.24's finalize commits, pushes and verifies, and the
    landing follows policy and Story 83.18's holds.
- **Read the process group with calls that exist.**
  - Membership is read per process with `os.getpgid(pid)`, over `psutil.pids()` or the `/proc` listing, or with
    psutil APIs that exist in 7.2.2. Never through a `pgid` attribute.
  - A process that exits during the scan (`NoSuchProcess`, `ProcessLookupError`) is skipped, not an error. A zombie
    does not count.
  - The read sits behind an injectable port, a marshal port with an adapter or a group read on
    `pyforge.core.process.ProcessPort`, so no unit test signals or reads a real host group (AD-4). The real adapter
    is also tested on the host.
- **Membership: started at or after the launch.**
  - A non-zombie member counts when its start time is at or after the run's launch, with no upper bound.
  - The comparison allows `PID_START_TOLERANCE_SECONDS` below the launch time for clock granularity, the same
    allowance Story 83.1 gives the leader. psutil derives `create_time` from the kernel's boot time, which is kept in
    whole seconds.
  - A member that started earlier is another process, not the session.
  - The leader keeps Story 83.1's two-sided check.
- **A read error is never "alive". The fallback is the leader, with its identity checked.** When the group read
  raises, that tick's answer comes from the launched pid alone:
  - it must exist and not be a zombie;
  - its identity must match the launch: its `create_time` within Story 83.1's window, or, when `create_time` cannot be
    read, a cmdline that names the run's harness `binary` from its profile;
  - a pid that fails the identity check is not the session.
  
  The fallback is bounded by the leader's own life, so a read that keeps failing ends when the leader exits. The
  supervisor's heartbeat journals `session_liveness_error` with the message, and `marshal status` shows it.

  This replaces 90.1's rule that an unanswerable group read counts as alive, per the 2026-10-11 ruling. AD-8 still
  holds for what the supervisor decides on: the identity-checked leader is a settled fact, and a stale group read is
  not.
- **A vanished worktree is never live.** A run with a recorded `worktree_path` that no longer exists, and with no
  `dispatch-completion` outcome and no completed landing, is stale:
  - `resolve_dispatch_session_verdict` checks for it first, ahead of the open-fix-turn rule (`cli/dispatch.py:1841`),
    and returns a non-live verdict for it;
  - `station_in_flight_conflict` never refuses on it (no `MRS-DISP-011`, `021`, `034` or `035`); it adds an
    `MRS-DISP-064` WARN, the next free code at mint, naming the run dir, its story, the missing worktree and the
    remedy;
  - none of these raises on it: `_live_dispatch_evidence`, `_dispatch_git_facts_for_journal` (`:2093`),
    `_live_dispatch_story_keys` (`:1989`), `list_live_dispatch_stories` (`cli/status.py:886`) or
    `_merge_dispatch_overlay` (`cli/status.py:921`). A `VcsCommandError` from `gather_dispatch_git_facts` outside the
    supervisor's own tick means "no git facts", reported, not raised.
- **Stale runs are reported, never moved.**
  - `marshal status` (text and `--format json`) lists each stale run on its station's row, under
    `dispatch_stale_runs`, with its run id, story, worktree path and remedy.
  - The remedy reads: move the run dir to `_bmad-output/projects/<slug>/implementation-artifacts/dispatch-runs-quarantine/`
    and list it in that directory's `README.md`; moving it back reverses it.
  - `scripts/fleet_picture.py` shows one ATTENTION `watch` line per station from that field.
  - Marshal never moves, deletes or rewrites a run dir.
- **The landing waits for an independent review.** This uses marshal Story 83.18's hold, unchanged:
  - The frontmatter above declares `landing_review: 'required'`. Marshal reads it with `parse_landing_review` and
    `landing_review_requires_hold` (`core/dispatch_harness_done.py:151`-`:159`), and `resolve_hold_dispatch_landing`
    turns it into a hold.
  - The operator also dispatches with `--hold-landing`:
    `pixi run -e pyforge-guild marshal factory dispatch pyforge-marshal 92.1 --hold-landing`. The flag is journaled
    on the launch INTENT under `hold_landing` (`HOLD_LANDING_PAYLOAD_KEY`).
  - Held, a verified run pushes its branch, opens its PR as a draft and journals a `dispatch-land` verdict
    `held-for-review`. It merges nothing.
  - A separate agent, not the implementing session, reviews the diff against this spec and appends its verdict to this
    spec's `## Review Triage Log`.
  - If the review passes, the operator sets `landing_review: 'passed'` (or marks the PR ready for review) and
    `status: 'in-review'`, then re-dispatches. Story 83.7's land-only path lands the story, and Story 89.1's gate
    allows it.
  - If the review fails, its entry carries `FAIL`, the story goes back to `ready-for-dev`, and nothing lands.
- **Unchanged:**
  - a live session in an existing worktree reads `LIVE`, as before;
  - Story 83.1's leader check, Story 22.2's zombie guard and Story 28.16's parallel narrowing;
  - Story 83.4's refused-landing hold;
  - Story 83.14's manual merge, Story 73.1's follow-up scoping, and the verify-fix turn and its leader-only liveness;
  - every landing and promotion rule.

Ledger key: `92-1-the-dispatch-supervisor-reads-session-liveness-correctly-and-never-treats-a-vanished-worktree-as-live`.
Type / Effort / Deps: fix / L / none (the 90.1 revert it builds on is on `main` as `a085cd0344`).

### Story 90.1's acceptance criteria, re-landed

Story 90.1's spec (`spec-90-1-the-dispatch-supervisor-records-completion-only-after-the-harness-session-has-really-exited.md`)
stays `done`, but its code was reverted on 2026-10-11. This table maps each of its ACs to this spec.

| 90.1 AC | Still valid? | Here |
|---|---|---|
| AC1: the atlas 25.1 sequence never completes while the session lives | yes | AC1 |
| AC2: a launched parent that exits early does not end the session | yes, except its last clause ("a group read that raises reads as alive"), which the 2026-10-11 ruling replaces | AC2; the replacement is AC3 |
| AC3: no completion while the session lives, whatever `main` says | yes | AC5 |
| AC4: a merge counts only when this run made it | yes | AC6 |
| AC5: after the session exits, the normal path runs | yes | AC7 |
| AC6: everything else unchanged; three named tests change expectation | yes; the revert restored those three tests' old expectations, so they change again | AC10 |
| AC7: four mutations | yes | AC11, with new mutations |

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-marshal` CAP-160 (← `spec-marshal-single-story-dispatch` CAP-2): Story 22.2's
  completion judgment and zombie guard, whose liveness read Story 83.1 hardened, and which Story 90.1 extended before
  its code was reverted. With it:
  - CAP-167 (← CAP-9, Story 22.10's divergence rule), which this story extends to `story_merged_on_main` again;
  - CAP-141 (← `spec-marshal-drain-self-resolution` CAP-7, Story 28.24's finalize), which this story makes reachable
    again;
  - CAP-163 (← CAP-5, Story 22.5's one-in-flight guard, narrowed by Story 28.16), which must neither refuse nor crash
    on a stale run;
  - CAP-5 (fleet visibility: anything needing a human surfaced first), under which `marshal status` and
    `fleet-picture` report a stale run.
  
  This story fixes their realization, so it mints no CAP and changes no `SPEC.md`.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag. It restores intended behaviour, and a
  flag would keep a run's completion reachable while its session still writes.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, the 2026-10-10 (a dead run read as live) entry. The
  operator's rulings, verbatim: 2026-10-10 "yes mint both stories"; 2026-10-11 "Revert 90.1 now (Recommended)" and
  "Retitle (Recommended)".

## Acceptance Criteria

The supervisor-loop tests use the fakes in `tests/unit/test_dispatch_supervisor_main_loop.py` and fixture journals in
the run-dir shape the supervisor reads. The real process tests are POSIX only and run against the host's real psutil
7.2.2. They never monkeypatch `psutil`.

- **AC1 — The atlas 25.1 sequence never completes while the session lives** (90.1 AC1).
  - **Given** a fixture journal shaped like run `pyforge-atlas-20261010T232600552Z-1b28d6db`, a worktree head equal to
    the baseline, `origin/main` subjects holding "Merge pull request #1114 from rxm7706/dispatch/pyforge-atlas/25.1",
    and changed paths that grow tick by tick.
  - **And** the launched pid already dead, with the session's process group alive for three ticks.
  - **When** the supervisor runs **Then** no `dispatch-completion` or `dispatch-timing` entry is journaled during those
    three ticks. Each tick journals a heartbeat with `session_alive: true`, and every gathered `story_merged_on_main`
    is false.
  - **When** the group then exits with the worktree dirty **Then** a `dispatch-finalize` INTENT and OUTCOME are
    journaled, and no `completed` verdict with a `final_revision` equal to the baseline precedes them.
- **AC2 — The whole process group is read, on the real host** (90.1 AC2, with its exit half).
  - A real session is launched with `start_new_session=True`, as the harness adapter does. Its leader exits at once
    while a child appends to a file every 100 ms for about two seconds.
    - `dispatch_session_alive` is true while the file grows.
    - It is false within one second of the child's exit.
  - A child started more than `PID_START_TOLERANCE_SECONDS` after the launch keeps the session alive. The test may
    move `launched_at` back rather than sleep.
  - The real adapter, called on the test's own group, raises nothing and yields that group's live members.
  - `dispatch_session_alive` is false for a pid that does not exist, with a launch an hour ago.
  - With fakes: a member that started before the launch, less the allowance, reads not alive, and a zombie member
    does not count.
- **AC3 — A read error falls back to the identity-checked leader, never to "alive"** (replaces 90.1 AC2's last clause).
  With a group port that raises on every read:
  - a leader that exists, is not a zombie and started inside Story 83.1's window reads alive;
  - a leader that has exited reads not alive;
  - a pid whose `create_time` is outside the window reads not alive (a reused pid);
  - a pid whose `create_time` cannot be read and whose cmdline does not name the profile's `binary` reads not alive;
  - each supervisor heartbeat carries `session_liveness_error` with the message, and `marshal status --format json`
    shows it on the run's row.
- **AC4 — The 2026-10-11 stall does not recur.**
  - **Given** a supervisor-loop run shaped like `pyforge-marshal-20261011T030728372Z-51af3462`: the session's spec
    reads `done`, its head has moved past the baseline, its worktree is clean, and its group read raises on every
    tick.
  - **When** the leader exits **Then** the next tick journals `session_alive: false` and no later
    `session_alive: true` heartbeat. The run goes on to verification and to a landing under policy, as any finished
    session does: held for review when its spec or launch asks for it, otherwise landed.
  - The same holds with a working group read once the last group member has exited.
- **AC5 — No completion while the session lives, whatever `main` says** (90.1 AC3).
  - `judge_dispatch_completion` returns `LIVE` while `session_alive` is true, for every combination of
    `branch_merged` and `story_merged_on_main`. While it is false, the verdict is what it was before 90.1.
  - `marshal factory dispatch` of the same story while the group lives is refused as a live session, naming the
    evidence (Story 22.2's zombie guard), and `marshal status` shows the run live.
- **AC6 — A merge counts only when this run made it** (90.1 AC4).
  - **Given** a corroborated merge subject naming the story on `origin/main`:
    - with the run's head equal to its baseline, `story_merged_on_main` is false;
    - with the head moved and on `origin/main`, it is true;
    - with the head moved but not on `origin/main`, it is false (Story 83.14, unchanged).
  - A follow-up review run (Story 73.1) reads the same as before at a moved head.
- **AC7 — After the session exits, the normal path runs** (90.1 AC5).
  - A session that exits with uncommitted changes and its head at the baseline is finalized (committed, pushed and
    verified), then landed under policy and Story 83.18's holds.
  - A session that exits with nothing changed is `failed`.
  - A session that exits with commits past the baseline is verified and landed as before.
- **AC8 — A vanished worktree is never live** (the 47.1 crash).
  - **Given** a fixture run dir shaped like `pyforge-marshal-20261004T165202766Z-fc6ece35`:
    - a `dispatch-launch` INTENT with a `worktree_path` under `tmp_path` that does not exist, and a
      `baseline_head_sha`;
    - its OUTCOMEs, with `session_pid` 63830 and `supervisor_pid` 63831;
    - attach heartbeats and a `dispatch-push` pair, and no `dispatch-completion`.
  - **And** a candidate story with another key, a process fake on which pid 63830 reads alive (a reused pid whose
    start time cannot be read), and the real git adapter on a `tmp_path` repository.
  - **When** `station_in_flight_conflict` runs **Then** it raises nothing and returns no conflict for the stale run. It
    reports an `MRS-DISP-064` WARN naming the run dir, `86.6`, the missing worktree and the quarantine remedy.
  - **And** on the code before this story the same fixture raises `VcsCommandError`. The test names the commit it
    reproduces.
  - **And** none of these reads the run as `LIVE` or raises: `resolve_dispatch_session_verdict`,
    `_live_dispatch_story_keys`, `list_live_dispatch_stories` and `_merge_dispatch_overlay`. With the candidate's key
    `86.6`, there is no `MRS-DISP-011`.
- **AC9 — A stale run is reported, not blocking.**
  - `marshal status` (text and `--format json`) lists the AC8 run under `dispatch_stale_runs`, with its run id, story,
    worktree path and the remedy naming `implementation-artifacts/dispatch-runs-quarantine/` and its `README.md`. The
    station's state does not read `running` because of it.
  - `fleet-picture`'s ATTENTION block shows one `watch` line for the station, naming the count and the quarantine
    directory. A marshal meta test beside `tests/meta/test_fleet_picture_stranded_work.py` pins it.
  - `marshal factory dispatch` of any story on that station is not refused because of the stale run.
  - No reader moves, deletes or rewrites a run dir.
- **AC10 — Everything else is unchanged** (90.1 AC6). Every marshal test that exists after the revert passes, with
  these named exceptions, each keeping what it tests. The revert restored the first three to their expectations before
  90.1; they change again as 90.1's spec describes (line numbers at `bab2162d73`, in
  `tests/unit/test_dispatch_supervisor_main_loop.py`):
  - `test_gather_git_facts_corroborates_a_station_branch_pr_against_the_tracked_spec` (`:987`): its fake head moves
    off the baseline, and its three assertions stay.
  - `test_a_follow_up_in_the_stories_surviving_pre_merge_worktree_is_scoped_by_the_launch_tip_against_real_git`
    (`:3665`): its premise is read after a run commit, its verdicts judge an exited session, and one added assertion
    pins that a live session reads `LIVE`.
  - `test_without_the_run_head_gate_the_manual_merge_fixture_reads_completed_on_the_first_tick` (`:3638`): it now
    asserts that the run completes only on the tick after the session exits.
  
  The dev names any other changed expectation, with its reason, in this spec's Spec Change Log.
- **AC11 — Mutation.**
  - Restoring the merge-first order in `judge_dispatch_completion` fails AC1 and AC5.
  - Dropping the group read fails AC2 and AC1.
  - Reading membership through a `pgid` attribute fails AC2's real-host cases.
  - Restoring a two-sided start window for members fails AC2's late-child case.
  - Counting a read error as alive fails AC3 and AC4.
  - Dropping the identity check from the fallback fails AC3's reused-pid case.
  - Dropping the divergence rule for `story_merged_on_main` fails AC6's first case and AC1's merge assertion.
  - Skipping the finalize after a dirty exit fails AC7's first case.
  - Dropping the vanished-worktree rule, or letting `_live_dispatch_evidence` raise again, fails AC8.

## Boundaries & Constraints

**Always:**
- Keep the judgments pure (`core/`, AD-4), and keep the process, filesystem and git reads at the impure edge behind
  ports.
- Test the real group read on the host as well as through fakes.
- Journal every tick's heartbeat, and every finalize before acting on it (AD-6).
- Keep `landing_review: 'required'` in this spec's frontmatter until the operator releases the hold.
- Reconcile every governed path the change touches on the memlogs of the Specs that govern it, then stamp those Specs
  scoped: `spec-pyforge-marshal`, `spec-pyforge-core` if `ProcessPort`, its tests or a core-governed adapter change,
  and every co-governor `spec-surface-check` names (AGENTS.md pre-PR item 5).

**Never:**
- Never journal `dispatch-completion` while any member of the session's group that started at or after the launch is
  alive.
- Never count a group read error as a live session. Its answer is the identity-checked leader.
- Never read membership through a `pgid` attribute or any other attribute psutil 7.2.2 does not provide.
- Never read a run whose recorded worktree is missing as `LIVE`, and never let a reader raise on it.
- Never move, delete or rewrite a run dir, a journal or a quarantine `README.md`. The operator quarantines.
- Never signal, stop or kill a process from this change. Liveness only observes.
- Never change verification, the verify-fix turn, Story 83.18's hold or Story 89.1's gate.

**Residual risk:**
- A process that leaves the session's group (its own `setsid`, or a daemon that double-forks) is not seen.
- While the group read keeps failing, a child that outlives its leader is not seen, and the run is judged on the
  leader. The heartbeat names the error.
- A session whose worktree was removed while its processes still run is reported stale, not live. The report says
  that its leader still reads alive, so the operator can stop it.

## I/O & Edge-Case Matrix

| Completion outcome | Worktree | Leader | Group read | Before this story | After |
|---|---|---|---|---|---|
| none | present | alive | members alive | `LIVE` | `LIVE` |
| none | present | dead | a child started 5 min after launch is alive | 90.1: alive only via the read error; after the revert: dead, and completion may be recorded mid-session | `LIVE` until the child exits |
| none | present | dead | group empty | 90.1: `LIVE` forever (the 47.1 stall) | dead; judged, finalized or landed |
| none | present | dead | the read raises | 90.1: `LIVE` forever | dead (the fallback); `session_liveness_error` journaled |
| none | present | a reused pid (create_time outside the window) | the read raises | 90.1: `LIVE` | dead |
| none | missing | dead or a reused pid | any | `LIVE` or a launch crash on `VcsCommandError` | stale; `MRS-DISP-064` WARN; dispatch proceeds |
| completed / failed | any | any | any | that verdict | that verdict, unchanged |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-10 (a dead run read as live) entry, with its
  2026-10-11 rulings.
- Epic: Epic 92, a new fix epic. Epics 22, 83 and 90, which shipped the guard, the leader check and the group read,
  are `done`, and Epic 90's key never moves.
- Ledger key: `92-1-the-dispatch-supervisor-reads-session-liveness-correctly-and-never-treats-a-vanished-worktree-as-live`.
- Ledger status at mint: `backlog`.
- Deps: none. It builds on the 90.1 revert (branch `hotfix-revert-901-2026-10-11`, PR #2106, reverting
  `d013fdb9fe`), which is on `main` as `a085cd0344`.
- Surface: `[epic_surfaces]` `"92"` in `marshal-policy.toml`. It holds the default surface, `pyforge-core`'s
  `process.py` and its tests, `scripts/fleet_picture.py`, and every Spec memlog.
- Landing: held for an independent review by marshal Story 83.18's mechanism (`landing_review: 'required'` above, and
  `--hold-landing` at dispatch). It is released only after that review passes.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python scripts/spec_surface_reconcile.py` — expected: exit 0 (the derived surface guard).

**Manual checks (not a dispatch gate):**
- `pixi run --frozen -e pyforge-core pyforge-core-test` — expected: pass, if `ProcessPort` or its tests change.
- The mutations of AC11 — expected: each fails its named test. Restore each.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconciles and the
  scoped stamps.
- On the host:
  - `dispatch_session_alive(PosixProcess(), 63830, launched_at=<2026-10-04T16:52:02.938Z>)` reads false.
  - Moving one quarantined run dir back into `dispatch-runs/` makes `marshal status` list it as stale, and
    `marshal factory dispatch` still launches. Move the dir back to quarantine afterwards.
- On the next cursor or claude dispatch, these hold:
  - no `dispatch-completion` is journaled before the session's group has exited;
  - a session that exits with a dirty worktree is followed by a `dispatch-finalize` pair;
  - no `session_alive: true` heartbeat follows the exit.
- This story's own dispatch stops at a draft PR (`dispatch-land` verdict `held-for-review`), and the independent
  review is recorded in `## Review Triage Log` before the hold is released.

## Named, not fixed here

- **The 51 quarantined runs stay quarantined.** Moving them back is the operator's call once this lands. Nothing here
  depends on it.
- **Marshal 47.1's finished work** (run `pyforge-marshal-20261011T030728372Z-51af3462`, branch head `10e26d2003`, its
  supervisor stopped at 08:35:29Z) is the operator's to land. The revert and this story fix the read for later runs.
- **A rekeyed story's earlier landing still reads as merged** in the drain's merged-key read (`cli/dispatch.py`) and
  in `marshal status`. 90.1 named this, and it is unchanged here.
- **`supervisor_should_exit`'s result is ignored.** 90.1 named this, and it is unchanged here.
- **The verify-fix turn's liveness stays leader-only.** The fix turn is bounded by its budget and stopped with
  `terminate_process_group`.
