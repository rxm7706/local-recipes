---
title: '51.4: A blocked outcome never lands'
type: 'fix'
created: '2026-09-19'
status: 'in-review'
baseline_revision: '1ff4b6d212084d74e3be6112221a4261822d74f0'
review_loop_iteration: 0
followup_review_recommended: false
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
