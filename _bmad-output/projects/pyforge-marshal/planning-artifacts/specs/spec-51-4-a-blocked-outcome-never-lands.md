---
title: '51.4: A blocked outcome never lands'
type: 'fix'
created: '2026-09-19'
status: 'done'
baseline_revision: '1ff4b6d212084d74e3be6112221a4261822d74f0'
review_loop_iteration: 0
followup_review_recommended: true
context: []
deferred:
  - summary: >-
      The supervisor-crash unsupervised-recovery path (dispatch_survival.py)
      cannot recognize a narration-only diff as no-progress because
      DispatchCompletionInput has no spec_relative_path field.
    evidence: |-
      derive_supervision_state/reconcile_unsupervised_verdict build
      DispatchCompletionInput(session_alive=session_alive, git=git) with no
      spec_relative_path, unlike the 4 correctly-threaded
      resolve_terminal_session_verdict call sites in
      dispatch_supervisor/__main__.py and the cli/dispatch.py fix landed in
      this pass. What would settle whether this reaches an actual wrongful
      landing (medium/high) versus a merely different in-flight status: a
      live-fire test that kills the supervisor process mid-run with a
      narration-only diff staged and traces whether recovery treats it as
      progress through to an actual land attempt.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_survival.py:89-104,113-118
    severity: medium (unverified)
  - summary: >-
      KIND_DISPATCH_BLOCKED journal entries are write-only; nothing reads
      them back, so a block reason is unrecoverable once the worktree that
      backs the live spec re-read is already cleaned up.
    evidence: |-
      Unlike KIND_DISPATCH_FINALIZE, which has a dedicated reader in
      dispatch_supervisor_finalize.py, no code folds or reads
      KIND_DISPATCH_BLOCKED entries. station_story_block_facts's blocked
      detection depends entirely on a live re-read of the worktree spec; once
      the worktree is removed, spec_text is None and the blocked branch is
      silently skipped with no journal fallback. The Approach clause commits
      only to journaling the reason, not to a reader, so this is out of this
      story's bound intent -- real future hardening, not a defect in what was
      built.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py::_journal_dispatch_blocked
    severity: medium
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** doctor 27.3's session found an intent gap, reverted to baseline and set `blocked`; marshal landed the empty branch (PR #1476) and promoted `27-3 → done` — the truth was written above the Auto Run Result by hand and the story re-minted as 27.4→27.5

**Approach:** the supervisor's finalize sequence stops before verify and land on a `blocked` spec, journals `dispatch-blocked` with the spec's own reason, and the campaign records a station block rather than an advance

## Boundaries & Constraints

**Always:**
- the 27.3 fixture (empty diff against baseline + `status: blocked`) produces no PR and its tracked ledger row never reads `done`; the campaign fact names the reason
- an implementation with changed paths lands exactly as today (existing fixtures), and removing the status read re-lands the 27.3 fixture (mutation test)

**Never:**
- Do not make the supervisor trust a session's self-report, perform the merge marshal only materialises, add a second gate or verdict owner, move a primary checkout that is not a clean `main`, or re-attribute landed history — the Epic 51/52 HARD boundaries in `epics.md` bind.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the named fixture | the real run/journal/PR named in the Given | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-252`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py` (`_run_supervisor_finalize_sequence` and the run-loop land trigger read the worktree spec's `status:` before verify/land), `.../core/dispatch_completion.py::has_git_progress` (a revert-to-baseline plus a status flip is not progress), `.../core/dispatch_harness_done.py::parse_spec_status` (reused; the pre-launch guard treats `blocked` as not relaunchable without an operator decision), `.../core/dispatch_landing.py` (a `blocked` verdict), `.../cli/dispatch.py:: station_story_block_facts` + `.../core/dispatch_fleet.py` (the block reason; `NON_IMPLEMENT_STATUSES` already lists `blocked`), tests.
Ledger key: `51-4-a-blocked-outcome-never-lands`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` (51.x) or a hand-driven `bmad-build-auto` (52.x) can resolve `spec-51-4-a-blocked-outcome-never-lands.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- The Then/And of Story 51.4 in `epics.md` hold on the named fixture; the mutation or byte-identical check named there is run, not inferred.

## Review Triage Log

### 2026-09-19 — Review pass
- verdicts: 23 findings — high 3, medium 7, low 9, false 2, maybe-false 2
- findings:
  - `[high]` `[patch]` Blind Hunter: `cli/dispatch.py::resolve_dispatch_session_verdict` never threads `spec_relative_path` into its `resolve_terminal_session_verdict` call, unlike the 4 call sites already fixed in `dispatch_supervisor/__main__.py` — traced directly: for a narration-only (spec-only) diff, `has_git_progress` here sees the spec file as real progress, so `station_story_block_facts` (the campaign-facing reporter the Approach names) can resolve LIVE/STOPPED_EXTERNALLY instead of FAILED, skipping the new blocked-branch entirely for the retrospective read path. Fixed by resolving `spec_relative_path` before this call (same pattern as the other 4 sites) and adding a test that doesn't pre-seed `completion_verdict`.
  - `[medium]` `[patch]` Blind Hunter: `DispatchLandingVerdict.BLOCKED` is defined but never constructed or returned anywhere (confirmed by grep) — contradicts the spec's own Binding claim that `dispatch_landing.py` carries "a blocked verdict"; the real mechanism is the parallel `KIND_DISPATCH_BLOCKED` journal kind. Fixed by deleting the dead member.
  - `[low]` `[patch]` Blind Hunter: the new `spec_status == "blocked"` check in `station_story_block_facts` runs before the pre-existing "Story 50.1 Part B" already-landed self-refusal check — for a worktree that is both already-landed and carries a stale `blocked` spec, the reported reason is less accurate (cosmetic only; both paths still refuse). Fixed by reordering.
  - `[medium]` `[defer]` Blind Hunter: `KIND_DISPATCH_BLOCKED` journal entries are write-only — nothing reads them back, unlike `KIND_DISPATCH_FINALIZE`'s dedicated reader in `dispatch_supervisor_finalize.py`. The Approach only commits to journaling the reason, not to a reader, so this is real but outside the bound intent; deferred as future hardening (see `deferred:` below).
  - `[low]` `[patch]` Blind Hunter: the new `MRS-DISP-045` finding message uses a Unicode em dash (`—`) where the rest of this diff and the project convention use plain `" -- "`. Fixed by swapping the character.
  - `[low]` `[reject]` Blind Hunter: `station_story_block_facts`'s spec-path resolution and `dispatch_supervisor/__main__.py::_worktree_story_spec` independently implement similar worktree-relocated-spec-path logic. Real duplication but both independently verified correct today; proper fix is a shared-helper extraction — non-trivial, better as separate follow-up, not worth fixing now.
  - `[false]` Blind Hunter: `parse_blocking_condition`'s frontmatter-scalar branch (`blocking_condition:` key) has no producer anywhere in the repo — refuted as a defect: it is dead but harmless defensive/forward-compatible code, not a situation the function mishandles.
  - `[low]` `[patch]` Blind Hunter: same root cause as the check-ordering finding above (station_story_block_facts precedence) — shares that fix.
  - `[high]` `[patch]` Edge Case Hunter: same root cause as the un-threaded `spec_relative_path` finding above (`cli/dispatch.py:942`) — shares that fix.
  - `[low]` `[reject]` Edge Case Hunter: `station_story_block_facts:1493,1553` — a worktree spec reading `status: blocked` alongside genuinely unrelated real changed files never enters the `if verdict == FAILED` branch (verdict can resolve LIVE/STOPPED_EXTERNALLY instead), so the blocked-branch is skipped. Verified reachable, but the intent-contract's own Always clause scopes only to the empty-diff (27.3) and, via the Matrix's pointer to epics.md, the narration-only (51.3) fixtures — a blocked-status-plus-real-changes combination is named by neither. Doesn't risk a wrongful landing (LIVE/STOPPED_EXTERNALLY don't drive the land trigger). Fix would require moving the blocked-check outside the verdict gate entirely — not a direct correction.
  - `[maybe-false]` `[defer]` Edge Case Hunter: `dispatch_survival.py`'s unsupervised-recovery path (`derive_supervision_state`/`reconcile_unsupervised_verdict`) builds `DispatchCompletionInput` with no `spec_relative_path` field at all, so a supervisor-process crash coinciding with a narration-only diff can't be recognized as no-progress there. Could not establish whether this actually reaches a wrongful landing versus just a different in-flight status; if true this would be medium. What would settle it: a live-fire test that kills the supervisor process mid-run with a narration-only diff staged and observes whether recovery treats it as progress through to an actual land attempt.
  - `[low]` `[patch]` Edge Case Hunter: `dispatch_supervisor/__main__.py:1580`'s `has_git_progress(git_facts)` (the preserve-worktree decision after a FAILED verdict) omits `spec_relative_path`, unlike the 4 `resolve_terminal_session_verdict` call sites in the same file — self-contradictory when verdict was FAILED precisely because there was no progress, since this call would still say there was. Cosmetic (only affects whether a hollow worktree is needlessly preserved for inspection). Fixed by threading the same kwarg.
  - `[low]` `[patch]` Edge Case Hunter: `parse_blocking_condition`'s body-line regex uses `.search()`, returning only the first "Blocking condition:" line when a spec body has more than one, possibly a stale earlier reason. Fixed by taking the last match instead.
  - `[low]` `[patch]` Edge Case Hunter: `parse_blocking_condition`'s `.strip("*")` only strips edge asterisks and stops at the first non-matching character, so a bold-wrapped value ending in punctuation (e.g. `**reason**.`) leaves the trailing `**` in place — plausible given the function's own docstring says the value is "sometimes" bold-wrapped. Fixed by stripping all asterisks from the value rather than edge-only.
  - `[low]` `[reject]` Edge Case Hunter: `spec_relative_path` is resolved once before the tick loop rather than re-resolved each tick, so it could go stale if the worktree's spec-glob match changed mid-run. Requires the worktree's own spec-file set to change during a single dispatch session — not a realistic operational scenario; not worth adding re-resolution overhead for it.
  - `[medium]` `[defer]` Edge Case Hunter: same root cause as the write-only journal finding above — if the worktree is already removed by the time a retrospective re-derivation runs, the live spec re-read the blocked-check depends on returns nothing and the block reason is unrecoverable from journal history either, since nothing reads `KIND_DISPATCH_BLOCKED` entries back. Shares that defer.
  - `[medium]` `[patch]` Edge Case Hunter: restates the dead `DispatchLandingVerdict.BLOCKED` claim above (also traced independently via `dispatch_landing.py:16-27` against the Binding text) — shares that fix.
  - `[high]` `[patch]` Verification Gap Reviewer: the new `dispatch_once` pre-launch guard (`MRS-DISP-045`, cli/dispatch.py ~2196-2217) has no test that invokes `dispatch_once` directly — confirmed by grep: `MRS-DISP-045` appears only in `test_findings.py`'s static registered-codes list, and `test_dispatch_fleet.py`'s `dispatch_once` monkeypatch tests don't exercise a blocked-spec scenario. This guard is the sole mechanism preventing an uncontrolled relaunch of a blocked story (the Never clause's "do not trust a session's self-report" territory), and a regression here would go completely undetected. Fixed by adding a direct test.
  - `[medium]` `[patch]` Verification Gap Reviewer (Other findings): restates the dead `DispatchLandingVerdict.BLOCKED` claim above — shares that fix.
  - `[maybe-false]` Verification Gap Reviewer (Other findings): restates the un-threaded `spec_relative_path` claim above but explicitly declined to file it as a hard gap, unable to construct a concrete reachable regression from its own layer's remit — folded into the high-verdict group above on the strength of the other three layers' concrete traces; this member's own verdict stays maybe-false per its filed hedge.
  - `[false]` `[reject]` Intent Alignment Auditor: flagged that the literal `<intent-contract>` prose (Problem/Approach) only narrates the 27.3 empty-diff case while the diff implements the wider epics.md-informed (narration-only/51.3) reading too — verified this is not a divergence: the Matrix's "the named fixture" row and the Verification section's manual check both explicitly point to epics.md's Given/Then as the source of record, which names both fixtures, so the diff's wider scope is the correctly bound reading, not an overreach.
  - `[medium]` `[patch]` Intent Alignment Auditor: restates the dead `DispatchLandingVerdict.BLOCKED` claim above — shares that fix.
  - `[medium]` `[patch]` Intent Alignment Auditor: observed that the new fleet test for the hollow/51.3 case (`test_a_narration_only_diff_after_a_harness_ceiling_is_transient_not_blocked`) pre-seeds `completion_verdict` directly, short-circuiting before `resolve_dispatch_session_verdict`/`resolve_terminal_session_verdict` ever run — so the real derivation path for the case this story exists to fix is untested. Same fix as the un-threaded `spec_relative_path` group: the new test added there must not pre-seed `completion_verdict`.

## Auto Run Result

**Summary:** the supervisor's finalize sequence and the campaign's block-fact reporter now stop before verify/land on a worktree spec left `status: blocked` (the 27.3 incident's shape) and correctly distinguish that from a narration-only diff (a session that only rewrote its own tracked spec, e.g. after hitting the harness's background-task ceiling — the 51.3 incident), which stays TRANSIENT and re-dispatchable. `has_git_progress` now treats a diff that collapses to just the tracked spec file as no progress; a new `dispatch_once` pre-launch guard (`MRS-DISP-045`) refuses to relaunch `bmad-build-auto` on a `blocked` spec without an operator decision, mirroring the existing `done`/CAP-4-only guard (`MRS-DISP-040`). The review pass completed the `spec_relative_path` threading this pattern requires across the remaining call sites, removed a dead enum member the Binding text had claimed was live, fixed two `parse_blocking_condition` parsing bugs, and added the direct `dispatch_once` test the new guard lacked.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py` — new `KIND_DISPATCH_BLOCKED` journal kind.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_completion.py` — `is_spec_only_narration` + `has_git_progress(..., spec_relative_path=...)`: a diff that collapses to just the tracked spec file is not progress.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_harness_done.py` — `parse_blocking_condition` reads a spec's stated blocking reason (frontmatter scalar or body line); review pass fixed it to take the last "Blocking condition:" match (not the first) and strip all asterisks (not just edge ones).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_landing.py` — review pass: deleted the dead, never-constructed `DispatchLandingVerdict.BLOCKED` enum member.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` — registered `MRS-DISP-045`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_session.py` — new `HarnessSessionOutcome.BACKGROUND_TASK_CEILING`, classified as transient (the 51.3 incident's harness-side signal).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/supervise.py` — `resolve_terminal_session_verdict` grew a `spec_relative_path` parameter, threaded into its two `has_git_progress` calls.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py` — `MRS-DISP-045` classified at the same ERROR tier as `MRS-DISP-040`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` — `station_story_block_facts` resolves `spec_status`/`spec_relative_path` unconditionally (review pass: moved before verdict resolution, and reordered so the already-landed self-refusal check runs before the blocked check); `resolve_dispatch_session_verdict` threads `spec_relative_path` (review pass); new `dispatch_once` pre-launch guard emits `MRS-DISP-045` and returns without relaunch when the live worktree spec reads `status: blocked` (review pass: em dash swapped for plain `--`).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py` — the finalize sequence's land trigger and 4 `resolve_terminal_session_verdict` call sites thread `spec_relative_path`; `_journal_dispatch_blocked` records the block reason; review pass threaded the 5th, previously-missed `has_git_progress` call (the FAILED-verdict preserve-worktree decision) the same way.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch.py` — review pass: new `test_blocked_spec_does_not_relaunch_harness` exercising `dispatch_once`'s `MRS-DISP-045` guard directly.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_fleet.py` — fleet-cycle fixtures for the 27.3 blocked-station case and the 51.3 narration-only-transient case, the latter derived through the real `resolve_dispatch_session_verdict` path (no pre-seeded `completion_verdict`).
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_spec_block.py` — new unit-test file for the supervisor finalize-sequence's blocked short-circuit.
- `src/shared/packages/pyforge-marshal/tests/unit/test_findings.py` — static registration coverage for `MRS-DISP-045`.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-51-4-a-blocked-outcome-never-lands.md` — this file: Review Triage Log, `deferred` entries, this Auto Run Result.

**Review findings breakdown** (23 findings from 4 layers, grouped by shared root cause into 15 entries):
- **Patched (8 entries):**
  - `high` — `cli/dispatch.py::resolve_dispatch_session_verdict` didn't thread `spec_relative_path` into its `resolve_terminal_session_verdict` call, unlike the 4 already-fixed sites in `dispatch_supervisor/__main__.py` — a narration-only diff could resolve LIVE/STOPPED_EXTERNALLY instead of FAILED for the campaign-facing reporter. Fixed the threading and added a test that derives the verdict rather than pre-seeding it (Blind Hunter + Edge Case Hunter + Verification Gap + Intent Alignment Auditor, one shared root cause).
  - `medium` — `DispatchLandingVerdict.BLOCKED` was defined but never constructed or returned, contradicting the Binding text's claim. Deleted the dead member (Blind Hunter + Edge Case Hunter + Verification Gap + Intent Alignment Auditor).
  - `low` — the new `blocked`-status check in `station_story_block_facts` ran before the pre-existing already-landed self-refusal check. Reordered (Blind Hunter, 2 rows sharing one fix).
  - `low` — `MRS-DISP-045`'s message used a Unicode em dash where the rest of the diff uses plain `--`. Swapped the character (Blind Hunter).
  - `low` — `dispatch_supervisor/__main__.py:1580`'s `has_git_progress` call (the FAILED-verdict preserve-worktree decision) omitted `spec_relative_path`, unlike its 4 siblings. Threaded the kwarg (Edge Case Hunter).
  - `low` — `parse_blocking_condition`'s body-line regex took the first "Blocking condition:" match instead of the last. Switched to the last match (Edge Case Hunter).
  - `low` — `parse_blocking_condition`'s `.strip("*")` only stripped edge asterisks, leaving a trailing `**` when the bold-wrapped value ends in punctuation. Strip all asterisks instead (Edge Case Hunter).
  - `high` — the new `dispatch_once` pre-launch guard (`MRS-DISP-045`) had no test invoking `dispatch_once` directly. Added `test_blocked_spec_does_not_relaunch_harness` (Verification Gap Reviewer).
- **Deferred (2 entries — recorded in frontmatter `deferred`):**
  - `medium (unverified)` — `dispatch_survival.py`'s unsupervised-recovery path builds `DispatchCompletionInput` with no `spec_relative_path`, so a supervisor-crash mid-run with a narration-only diff staged can't be recognized as no-progress there; could not establish whether this reaches an actual wrongful landing (Edge Case Hunter, maybe-false).
  - `medium` — `KIND_DISPATCH_BLOCKED` journal entries are write-only; nothing reads them back, so the block reason is unrecoverable once the backing worktree is cleaned up. Real but outside the Approach's bound intent (which commits only to journaling, not to a reader) — future hardening (Blind Hunter + Edge Case Hunter).
- **Rejected (5 entries):**
  - `false` — `parse_blocking_condition`'s frontmatter-scalar branch has no producer anywhere in the repo. Refuted: dead but harmless forward-compatible code, not a mishandled situation (Blind Hunter).
  - `low` — `station_story_block_facts` and `_worktree_story_spec` independently implement similar worktree-relocated-spec-path logic. Real duplication, both verified correct; a shared-helper extraction is non-trivial, better as a separate follow-up (Blind Hunter).
  - `low` — a worktree spec reading `status: blocked` alongside genuinely unrelated real changed files never enters the blocked branch (verdict resolves LIVE/STOPPED_EXTERNALLY instead). Verified reachable, but named by neither the intent-contract's Always clause nor the Matrix's epics.md fixtures, and doesn't risk a wrongful landing; the fix would require moving the check outside the verdict gate entirely — not a direct correction (Edge Case Hunter).
  - `low` — `spec_relative_path` is resolved once before the tick loop rather than re-resolved each tick. Requires the worktree's own spec-file set to change mid-session — not a realistic operational scenario (Edge Case Hunter).
  - `false` — the `<intent-contract>` prose only narrates the 27.3 empty-diff case while the diff also implements the 51.3 narration-only case. Verified this is the correctly bound reading: the Matrix and Verification section both point to epics.md's Given/Then, which names both fixtures (Intent Alignment Auditor).

**Follow-up review recommendation:** `true`. Two entries this pass were patched at `high` (the `spec_relative_path` threading in `resolve_dispatch_session_verdict`, and the new `MRS-DISP-045` direct test) — either alone meets the threshold. Named unverified risk: the `spec_relative_path` threading is now consistent across `dispatch_supervisor/__main__.py`'s 5 call sites and `cli/dispatch.py`'s campaign-facing reporter, but the composed behavior — a real `bmad-build-auto` session hitting the harness's background-task ceiling, then the supervisor and the fleet-drain campaign both correctly classifying the resulting narration-only diff as TRANSIENT rather than BLOCKED — has only been exercised through fixture-level unit and fleet-cycle tests, never a live session. A follow-up pass should confirm no other `has_git_progress`/`resolve_terminal_session_verdict` call site in the codebase remains unthreaded, and that a real end-to-end run reproduces the 51.3 incident's recovery correctly.

**Verification performed:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 8270 passed, 1 skipped, 12 deselected. Exit 0.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — 130 passed, 3 skipped. Exit 0.
- Manual: the Then/And of Story 51.4 in `epics.md` hold on the named fixtures — covered by `test_a_deliberate_blocked_spec_status_blocks_its_station_naming_the_reason` (27.3 shape) and `test_a_narration_only_diff_after_a_harness_ceiling_is_transient_not_blocked` (51.3 shape) in `test_dispatch_fleet.py`, plus the new `test_blocked_spec_does_not_relaunch_harness` for the `dispatch_once` pre-launch guard.

**Residual risks:** the two deferred items above — `dispatch_survival.py`'s un-threaded unsupervised-recovery path (medium, unverified — needs a live-fire supervisor-crash test to confirm reachability) and the write-only `KIND_DISPATCH_BLOCKED` journal (medium — no reader exists yet, so a block reason is unrecoverable once its backing worktree is cleaned up).
