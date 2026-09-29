---
title: '51.11: A session that halts blocked with its verdict uncommitted is a blocked outcome, not an operator stop'
type: 'fix'
created: '2026-09-20'
updated: '2026-09-19'
status: 'done'
baseline_revision: 'c8277c03c117ff4779d54a2ff9d900f519415971'
review_loop_iteration: 1
followup_review_recommended: true
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** doctor Story 26.1's session (run `pyforge-doctor-20260919T233255320Z-8f2b958e`) halted on an intent gap exactly as the workflow prescribes — code reverted, the tracked spec flipped to `status: blocked` with its Review Triage Log and Auto Run Result, the attempt saved to the worktree's Tier-3 as a patch — but left the spec and the revert *uncommitted* and exited. The supervisor saw `session_alive: False` against a HEAD (`678d409fc3`) that still carried two wip commits with real code, wrote `dispatch-finalize ok:false` and `dispatch-completion stop_reason: external-operator-stop`, and never a `dispatch-blocked` row. CAP-252's blocked detection reads committed state only; marshal 51.7's halt was caught only because that session committed the blocked spec first. `fleet-picture` then shows 26.1 `backlog` with no trace of the block, and the triage log lives only in a worktree awaiting teardown.

**Approach:** before classifying an unexplained session exit as `external-operator-stop`, the supervisor reads the worktree's *working-tree* copy of the tracked story spec (`core/dispatch_harness_done.py::parse_spec_status`); on `blocked` with an Auto Run Result it commits the spec and any `*-attempted-change*.patch` under the worktree's Tier-3 onto the dispatch branch, journals `dispatch-blocked` with the spec's blocking condition, preserves the worktree and completes with verdict `blocked`; the primary's tracked twin is promoted to `blocked` so the fleet picture shows it.

## Boundaries & Constraints

**Always:**
- The classifier narrows, never widens: a session that dies with a clean working tree and no terminal spec status still reads `stopped_externally`
- Marshal 51.7's committed-halt path (`dispatch-blocked` from committed state) is byte-identical after this story
- The supervisor never trusts a self-report — it reads the spec file, `git status` and the process; nothing the session prints is evidence
- The record survives worktree teardown: the blocked spec and the patch are on the dispatch branch and the twin is on the primary

**Never:**
- Do not land, merge or promote `done` anything from a blocked exit; do not add a second gate or verdict owner
- Do not delete or reset the worktree — `dispatch-preserve` semantics hold
- Do not re-attribute an operator-killed session as blocked because a stale `blocked` spec happens to sit in the tree from an earlier pass: the Auto Run Result's `baseline_revision` must equal the run's own baseline

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the doctor 26.1 replay | two wip commits with code; working tree = reverted code + spec `status: blocked` (Auto Run Result, `baseline_revision` = run baseline); session gone | `dispatch-blocked` (reason: intent gap), completion verdict `blocked`, a branch commit with the spec + patch, primary twin `blocked` | n/a |
| operator kill | clean working tree, spec `in-progress`, session gone | `stopped_externally` / `external-operator-stop` as today | n/a |
| committed halt (51.7's shape) | HEAD carries the blocked spec, tree clean | unchanged: `dispatch-blocked` as today | n/a |
| stale blocked spec from an earlier pass | spec `blocked` but `baseline_revision` ≠ this run's baseline | `stopped_externally`; journal names the mismatch | advisory note, no block |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-258`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py` (the exit classifier), `core/dispatch_completion.py`, `core/dispatch_landing.py` (twin promotion of a `blocked` tracked spec), `core/dispatch_harness_done.py::parse_spec_status` (reused, not re-implemented), tests with the replay fixture.
Ledger key: `51-11-a-session-that-halts-blocked-with-its-verdict-uncommitted-is-a-blocked-outcome-not-an-operator-stop`.
Minted 2026-09-20 from `epics.md` so `marshal factory dispatch` can resolve this file; dispatch after Story 51.7 lands (shared hub file).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- The Then/And of Story 51.11 in `epics.md` hold on the replay fixture; the fixture's final state is the one recorded in the doctor run's journal, not inferred.

## Review Triage Log

### 2026-09-19 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 1, medium 3)
- defer: 0
- reject: 0
- addressed_findings:
  - `[high]` `[patch]` `MRS-DISP-046` is constructed in the tick loop's `elif stale:` branch but was never added to `findings.REGISTERED_CODES` or `verdict._CLASSIFY_TABLE` — `Finding.__post_init__` would raise `UnregisteredFindingCodeError` the first time a stale blocked-spec baseline mismatch actually occurs, crashing the tick loop instead of emitting the advisory finding. Registered in both tables; roster entry added to `test_registered_codes_contains_the_real_codes`; a direct construction test (`test_stale_blocked_finding_code_is_registered`) closes the gap `_blocked_halt_reason`'s own tests can't reach (that helper only returns the `stale` flag, never constructs the Finding itself).
  - `[medium]` `[patch]` `core/status.py::derive_dispatch_phase`'s terminal-verdict tuple checked only `("failed", "stopped_externally")`, so a dead-tail `blocked` completion fell through to the function's final `return "verifying"` instead of `None` — fleet-picture would show a self-halted blocked story as perpetually verifying, never surfacing the block. Added `"blocked"` to the tuple; regression test `test_blocked_with_dead_tail_is_not_verifying`.
  - `[medium]` `[patch]` The same tuple gap in `core/status.py::_dispatch_terminal_dead_tail` (a second, independent check gating `derive_dispatch_stranded_work`) and its duplicate in `scripts/fleet_picture.py::dispatch_terminal_dead_tail` — both excluded `"blocked"`, so a dead-tail blocked story would never surface as stranded work either. Added `"blocked"` to both tuples; regression tests `test_blocked_verdict_dead_tail_surfaces_stranded_work` and `test_blocked_verdict_dead_tail_is_not_treated_as_active_dispatch`.
  - `[medium]` `[patch]` `_promote_blocked_twin`'s docstring states "Never raises", but its two `fs.read_text` calls (worktree spec, primary spec) were unguarded — `FsError` (permission denied, corrupt encoding — anything other than a plain missing file) would propagate out of this best-effort visibility promotion and unwind the tick loop, contradicting the function's own contract and the story's Boundaries ("the supervisor never trusts a self-report"/narrows-never-widens spirit). Wrapped both calls in `try/except FsError: return`; regression tests `test_promote_blocked_twin_never_raises_on_worktree_read_fs_error` and `test_promote_blocked_twin_never_raises_on_primary_read_fs_error`.

Note on provenance: the review pass that first surfaced these four findings ran in a
delegated implementation subagent; the session lost its live handle to that subagent
across a context compaction before the patches landed. No Tier-3 patch artifact or
transcript for that pass was recoverable in this worktree, so the four findings above
were independently re-derived by reading the committed diff against its own Spec and
verified live (each is a real, reproducible gap, not a restatement of an unseen
transcript) before patching. The interpretive judgment call flagged in the Auto Run
Result's own "Follow-up review recommended" (the `implementation-artifacts/` exclusion
in `_attempted_change_patch_paths`) is unrelated to these four findings and remains
open — this pass did not gain any new information to resolve it.

## Auto Run Result

Status: done

**Summary:** Before classifying an unexplained session exit as `external-operator-stop`, the tick loop now reads the worktree's *working-tree* copy of the tracked story spec. `_blocked_halt_reason` (new) returns the spec's blocking condition only when the spec reads `status: blocked`, carries an `## Auto Run Result` heading, and its `baseline_revision` frontmatter scalar equals the run's own baseline — otherwise it signals `stale` (matrix row 4: advisory `MRS-DISP-046` WARN finding attached to the `dispatch-completion` journal payload, verdict left `stopped_externally`) or no signal at all (rows 2/3, unchanged). On a genuine match (row 1, the doctor 26.1 replay shape), `_commit_and_journal_blocked_halt` commits the worktree's uncommitted changes plus any `*attempted-change*.patch` found outside the backlinked `implementation-artifacts/` Tier-3 store (excluded by construction — that store already survives teardown and must never be git-tracked per AGENTS.md) onto the dispatch branch, journals `dispatch-blocked`, and only then does the caller adopt `verdict = BLOCKED` (narrows, never widens: a commit or journal failure leaves the verdict untouched). `_promote_blocked_twin` best-effort pushes the same spec text onto the primary's tracked twin via `commit_paths_onto_remote_tip` (never a local commit on the shared checkout, per AGENTS.md). Two independently-computed closed terminal-verdict sets (`dispatch_survival.py::derive_supervision_state`, `cli/dispatch.py::resolve_dispatch_session_verdict`) also gained `BLOCKED.value`, or a dead session with committed blocked-halt wip would re-derive as `LIVE`/`STOPPED_EXTERNALLY` on the very next status read — reintroducing the bug this story fixes via a second code path.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_completion.py` — `DispatchSessionVerdict.BLOCKED`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_harness_done.py` — `parse_baseline_revision`, `has_auto_run_result` (reuses the existing frontmatter/banner-tolerant parser, mirrors `supervisor/intent_gap_preserve.py`'s heading regex)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_landing.py` — `blocked_twin_promotion_text` (pure: `None` when the primary is unreadable or already matching)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_survival.py` — `derive_supervision_state`'s terminal-verdict set gains `BLOCKED`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` — `resolve_dispatch_session_verdict`'s terminal-verdict set gains `BLOCKED`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py` — `_blocked_halt_reason`, `_attempted_change_patch_paths`, `_commit_and_journal_blocked_halt`, `_promote_blocked_twin`; wired into the tick loop's `stop_reason` block, gated on `verdict is DispatchSessionVerdict.STOPPED_EXTERNALLY` so Marshal 51.7's already-committed-halt path (never reaches `STOPPED_EXTERNALLY`) is untouched
- Tests: `tests/unit/test_dispatch_supervisor_blocked_halt.py` (new — the replay fixture: all 4 I/O matrix rows against `_blocked_halt_reason`, plus `_attempted_change_patch_paths`/`_commit_and_journal_blocked_halt`/`_promote_blocked_twin`, using the doctor run's own `baseline_revision`), `tests/unit/test_dispatch_completion.py`, `tests/unit/test_dispatch_harness_done.py`, `tests/unit/test_dispatch_landing.py`, `tests/unit/test_dispatch_survival.py`

**Review-pass patches (2026-09-19):**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` — register `MRS-DISP-046`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py` — `_CLASSIFY_TABLE["MRS-DISP-046"] = Verdict.WARN`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py` — `"blocked"` added to the terminal-verdict tuples in `derive_dispatch_phase` and `_dispatch_terminal_dead_tail`
- `scripts/fleet_picture.py` — `"blocked"` added to the same tuple in `dispatch_terminal_dead_tail`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py` — `_promote_blocked_twin`'s two `fs.read_text` calls guarded against `FsError`
- Tests: `tests/unit/test_dispatch_supervisor_blocked_halt.py` (+4: registration + 2 FsError-guard cases), `tests/unit/test_status.py` (+2), `tests/meta/test_fleet_picture_stranded_work.py` (+1), `tests/unit/test_findings.py` (roster entry)

**Verification:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 8329 passed, 1 skipped, 12 deselected (was 8323; +6 new tests). `pixi run --frozen -e pyforge-ci pyforge-deps-test` — 130 passed, 3 skipped. Both exit 0, read directly (never through a pipe).

**Follow-up review recommended:** true — one interpretive judgment call needs a second look. The Intent's `*-attempted-change*.patch` wording, read literally against the worktree's Tier-3, points at the backlinked `implementation-artifacts/` directory that AGENTS.md forbids git-tracking outright ("nothing there may be git-tracked"). The literal string does not appear anywhere else in this repo (it describes an external harness's own artifact naming, not an established local convention), so `_attempted_change_patch_paths` resolves the conflict by *excluding* any match under `implementation-artifacts/` — that patch already survives worktree teardown by virtue of being backlinked to the primary checkout, so nothing is lost, but a patch dropped anywhere else in the worktree (the realistic case this function actually commits) has no such protection and is committed onto the dispatch branch as the Intent describes. A reviewer with visibility into where doctor 26.1's actual patch landed should confirm this reading.

**Residual risks:** (1) the exclusion above — low risk, self-consistent with AGENTS.md's Tier-3 rule, but not verified against the actual doctor 26.1 patch location since that Tier-3 artifact does not exist in this worktree to replay verbatim. (2) No end-to-end test drives `run_dispatch_supervisor`'s full tick loop (no such test exists anywhere in this suite for that ~550-line polling function); coverage is at the level of the four new pure/composable helper functions it calls, which is the same granularity Story 51.4's sibling `test_dispatch_supervisor_spec_block.py` uses for the adjacent block-reason path.

## Status reconcile 2026-09-20

- frontmatter `status` `in-review` → `done` (ledger row `51-11-a-session-that-halts-blocked-with-its-verdict-uncommitted-is-a-blocked-outcome-not-an-operator-stop: done`).
