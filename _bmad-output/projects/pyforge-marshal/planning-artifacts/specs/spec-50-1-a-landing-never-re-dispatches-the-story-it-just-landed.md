---
title: '50.1: A landing never re-dispatches the story it just landed'
type: 'fix'
created: '2026-09-18'
status: 'done'
baseline_revision: 'ed367a47d8fb4e2da2275f1f0504e5084840d7c2'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the campaign cycles every 60 s and, on 2026-09-18, four times in a row saw a story neither live nor `done` inside the ~45 s between session exit and ledger promotion (`fleet-drain-runs/…151925342Z-82ce96c8`: `in-flight` 16:19:45Z → `dispatched` 16:20:47Z → `blocked … ended 'failed'` 16:21:47Z, `complete=true`)

**Approach:** a station whose most recent run's supervisor is alive but has not journaled `dispatch-completion` (or has journaled `dispatch-land` but the tracked ledger has not yet moved) reads as in flight, and a most-recent run that is a self-refusal of the already-merged kind (zero changed paths, session log names the merged PR / `done` spec) classifies as an advance reason

## Boundaries & Constraints

**Always:**
- the campaign reports `in-flight` for that cycle and chains the next ready story on the following one, and a fixture journal replaying the herald sequence completes the campaign with the next story `dispatched` rather than the same story `blocked`
- a genuine failed dispatch with zero changed paths and no merged evidence still blocks exactly as today (mutation test: removing the advance classification re-blocks the fixture)

**Never:**
- Do not make the supervisor trust a session's self-report, add a second gate, or re-attribute landed history — the Epic 50 HARD boundaries in `epics.md` bind.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the 2026-09-18 fixture | the real run/journal named in the Given | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-244`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` (the fleet cycle: `_live_dispatch_story_keys` / `_station_block_evidence` / `_classify_attempt`), `.../core/dispatch_fleet.py` (`plan_station_queue`, `classify_fleet_block`, the harness-done advance reason), `.../dispatch_supervisor/__main__.py` (only if a "session exited, finalize pending" journal fact is needed), tests.
Ledger key: `50-1-a-landing-never-re-dispatches-the-story-it-just-landed`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-50-1-a-landing-never-re-dispatches-the-story-it-just-landed.md`.

## Code Map

- `.../core/dispatch_fleet.py:66-71` -- `HARNESS_DONE_ADVANCE_CODE` + `is_harness_done_advance_reason`. The ONE existing advance-reason family; both new pure predicates land beside it.
- `.../core/dispatch_fleet.py:704-706` -- inside `plan_station_queue`: `if is_harness_done_advance_reason(reason): skipped.append(...)`. The single line that makes an advance reason skip under **every** mode. Part B widens exactly this test.
- `.../core/dispatch_fleet.py:159-167` -- `TERMINAL_STATION_STATUSES`; `IN_FLIGHT` is deliberately absent, so a station reported `IN_FLIGHT` keeps `campaign_complete()` False. Part A needs no change here — it reuses that status.
- `.../cli/dispatch.py:1374-1453` -- `station_story_block_facts`: the derived-block probe. Only a `FAILED` most-recent run reaches the block branch; it already reads `session.log` (line 1408) and `changed_path_count` (1423) and hands both to `classify_dispatch_block`. **Part B's insertion point is immediately before that `classify_dispatch_block` call** — reading the session log HERE is established, in-bounds precedent, and is not the supervisor's verdict.
- `.../cli/dispatch.py:890-940` -- `resolve_dispatch_session_verdict`: CAP-2's completion judgment. Reads `session_pid` only, never `supervisor_pid`. **Read-only for this story** — the HARD boundary keeps the verdict on git+process facts.
- `.../cli/dispatch.py:3275-3310` -- `execute_fleet_cycle`'s per-station body: `backlog` → `effective_policy` → `_station_blocked_map` → `plan_station_queue`. Part A's check goes between `effective_policy` and `_station_blocked_map`.
- `.../cli/dispatch.py:3311-3336` -- the `plan.skipped` reporting loop; `basis` already branches on `is_harness_done_advance_reason`. Part B adds the already-landed branch; the emitted code stays `MRS-DRAIN-004` (no new finding code — same precedent as harness-done).
- `.../cli/dispatch.py:3410-3435` -- the wave path's existing station-level `IN_FLIGHT` result + `MRS-DRAIN-006` WARN. Part A mirrors this shape verbatim.
- `.../cli/dispatch.py:748` `latest_dispatch_run_dir` / `.../cli/dispatch.py:780-887` `gather_dispatch_journal_facts` -- the most-recent-run walk and the facts it already yields: `story_key`, `supervisor_pid`, `completion_verdict`, `landing_verdict`. **All four already journaled** (verified against the real run `pyforge-marshal-20260918T192013577Z-6d43d408`).
- `.../cli/dispatch.py:1269-1301` -- `spin`'s in-flight probe already treats a live `supervisor_pid` as in flight. Precedent for Part A; the dispatch path simply never learned it.
- `.../core/dispatch_supervisor_state.py:29-35` -- `landing_journal_indicates_complete`. Reused as-is for Part A's clause (b).
- `.../core/dispatch_retry.py:50-69` -- `classify_dispatch_block`. Unchanged; Part B runs *before* it so the already-landed shape is never re-classified as TRANSIENT (which would re-dispatch) or TERMINAL (which blocks).
- `.../dispatch_supervisor/__main__.py` -- **not touched.** The spec's "only if" clause does not fire: `supervisor_pid`, absent `dispatch-completion`, and the `dispatch-land` verdict are all already on the journal.
- `tests/unit/test_dispatch_fleet.py:375-520` -- `FakeFs` / `FakeVcs` / `FakeProcess` / `FakeHarness`; `:534` `_seed_live_dispatch_journal`; `:973` `_seed_failed_dispatch_with_verify`; `:586` `_cycle`; `:2707` `_seed_done_worktree_spec`. `FakeProcess.is_alive` ignores its pid — Part A's fixture needs per-pid liveness.
- `tests/unit/test_dispatch_fleet.py:2763-2807` -- `test_harness_done_040_advances_to_next_backlog_same_cycle`: the assertion shape Part B's fixture copies (`harness.dispatched == [(slug, next)]`, `complete is False`, `MRS-DRAIN-004`).

## Tasks & Acceptance

**Execution:**
- `.../core/dispatch_fleet.py` -- add pure `is_finalize_pending(*, supervisor_alive, completion_journaled, landing_complete, story_on_backlog) -> bool` (False unless `story_on_backlog`; then True when `landing_complete`, else `supervisor_alive and not completion_journaled`) -- Part A's decision, kept pure so the ledger fact and the process fact meet in one testable place.
- `.../core/dispatch_fleet.py` -- add `ALREADY_LANDED_ADVANCE_PREFIX` (a plain sentinel, NOT an `MRS-` code — nothing is refused here) plus pure `is_already_landed_self_refusal(*, changed_path_count, session_log) -> bool`: True only when `changed_path_count == 0` AND the log carries merged evidence (`already merged` / `already landed` / `already_landed` / build-auto's `follow-up not recommended` HALT wording, or a PR reference — `/pull/<n>` or `#<n>` — on a line that also says `merged`) -- Part B's classifier.
- `.../core/dispatch_fleet.py` -- add `is_advance_reason(reason)` covering both `HARNESS_DONE_ADVANCE_CODE` and `ALREADY_LANDED_ADVANCE_PREFIX`; switch `plan_station_queue`'s skip test to it; extend that function's docstring bullet -- one widened test, so an already-landed head skips under every mode exactly as 040 does.
- `.../cli/dispatch.py` -- add `station_finalize_pending_story(*, fs, process, repo_root, slug, backlog, effective_policy) -> tuple[str, str] | None`: walk `latest_dispatch_run_dir`, gather journal facts, feed `is_finalize_pending`, return `(story_key, evidence)` -- Part A's impure half; the only new I/O, and it reads facts the journal already has.
- `.../cli/dispatch.py` -- in `execute_fleet_cycle`, call it after `effective_policy` is composed and before `_station_blocked_map`; on a hit append a `StationCycleStatus.IN_FLIGHT` `StationCycleResult` naming the story + evidence, a `MRS-DRAIN-006` WARN, and `continue` -- the station reports in-flight for that cycle, provisions nothing, and stays non-terminal so the campaign runs again.
- `.../cli/dispatch.py` -- in `station_story_block_facts`, immediately before `classify_dispatch_block`, return `StationBlockEvidence(reason=f"{ALREADY_LANDED_ADVANCE_PREFIX}: …", block_class=STORY)` when `is_already_landed_self_refusal` holds -- Part B's wire-up, ahead of the transient/terminal split so the shape is never re-dispatched *or* blocked.
- `.../cli/dispatch.py` -- in the `plan.skipped` reporting loop, add an already-landed `basis` branch -- the skip is named for what it is, not mislabelled "blocked".
- `tests/unit/test_dispatch_fleet.py` -- extend `FakeProcess` with an optional `alive_pids` (default keeps today's flat `alive` behaviour byte-identical); add `_seed_finalize_pending_journal` and `_seed_already_landed_self_refusal` seeders -- fixtures for the two new shapes.
- `tests/unit/test_dispatch_fleet.py` -- unit-test both pure predicates and the I/O-matrix edge cases (supervisor alive/dead × completion journaled/not × landing complete/not × story on/off backlog; zero/non-zero changed paths × merged/absent evidence), the three herald cycles, the end-to-end replay, the still-blocks case, and the mutation test -- the AC's own evidence.

**Acceptance Criteria:**
- Given a station whose most recent run journaled `dispatch-land` `landed` with the story still `backlog` on the tracked ledger, when a `drain_to_zero` cycle runs, then the station reports `in-flight`, `harness.dispatched == []`, and `report.complete is False`.
- Given a station whose most recent run has a live `supervisor_pid`, a dead `session_pid`, no `dispatch-completion` entry, and no git progress, when a cycle runs, then the station reports `in-flight` rather than blocking on a `failed` verdict.
- Given the same station once the ledger promotes that story to `done`, when the next cycle runs, then finalize-pending no longer fires and the next ready story dispatches.
- Given a three-cycle replay of herald's 2026-09-18 sequence, when the campaign runs, then it ends with the NEXT story `dispatched` and never the same story `blocked`.
- Given a genuine failed dispatch with zero changed paths and no merged evidence, when a `drain_to_zero` cycle runs, then the station is `blocked` exactly as today; and with `is_already_landed_self_refusal` stubbed False (mutation), the already-landed fixture re-blocks.
- Given `pyforge-marshal`'s existing suite, when it runs, then every pre-existing fleet/dispatch test stays green — `resolve_dispatch_session_verdict`, `judge_dispatch_completion`, and `dispatch_supervisor/__main__.py` are unmodified.

## Spec Change Log

## Review Triage Log

## Design Notes

**Why this is not "trusting a self-report".** The Epic 50 HARD boundary binds the *supervisor's completion verdict* — `judge_dispatch_completion` / `resolve_dispatch_session_verdict` stay on git + process facts, and this story does not touch either. Part B changes only the **campaign's block classification**, a layer that already reads `session.log` today (`station_story_block_facts` → `classify_dispatch_block(session_log=…)`). The session is not being believed about whether it succeeded; the *campaign* is deciding whether to halt a station or step past a head it has independent reason (zero changed paths) to think is already landed. Git remains the sole authority for merged facts, and no landed history is re-attributed.

**Why the window exists, mechanically.** Two distinct holes, one per Part:

- *Part A.* `resolve_dispatch_session_verdict` consults `session_pid` only. When the session exits and `dispatch_land`/`dispatch_land_finalize` are still running under a live `supervisor_pid`, either the run has a `landing_verdict` of `landed` → `COMPLETED` (so `station_story_block_facts` returns `None` → no block → **re-dispatch**), or it has neither → zero git progress → `FAILED` → **block**. Both are wrong while the ledger still says `backlog`: the correct reading is "in flight". `spin` already reasons this way (`cli/dispatch.py:1275`); dispatch did not.
- *Part B.* The re-dispatched session provisions a fresh worktree from *local* `main`, which still lags the just-pushed merge, so the spec there still reads `ready` and Story 29.2's `blocks_harness_relaunch` short-circuit never fires. The session runs, discovers the work is already merged, refuses itself, and exits with zero changed paths → `FAILED` → `TERMINAL` → `MRS-DRAIN-005`, `complete=true`, campaign over.

**Advance, not block, not transient.** Part B deliberately runs *before* `classify_dispatch_block`. TRANSIENT would mean "re-dispatch it" — that is the loop itself. TERMINAL means "halt the station". An already-landed head is neither: it needs the same treatment `MRS-DISP-040` already gets, which is why the change is one widened predicate at `plan_station_queue:704` rather than a new branch:

```python
ADVANCE_REASON_PREFIXES = (HARNESS_DONE_ADVANCE_CODE, ALREADY_LANDED_ADVANCE_PREFIX)

def is_advance_reason(reason: str) -> bool:
    return any(reason.startswith(prefix) for prefix in ADVANCE_REASON_PREFIXES)
```

**No new finding code.** Harness-done skips already surface as `MRS-DRAIN-004` with a distinguishing `basis` string; already-landed skips follow that precedent, and Part A reuses `MRS-DRAIN-006` ("no dispatch this cycle"). This keeps `core/findings.py` and `core/verdict.py` — both outside the declared surface — untouched.

**Self-limiting by construction.** Part A cannot wedge a station: clause (a) requires a *live* supervisor (a supervisor that dies without journaling completion is not pending), and both clauses require the story to still be on the tracked backlog, so ledger promotion ends the condition on the very next cycle.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- A fixture journal replaying herald's 2026-09-18 sequence (`fleet-drain-runs/…151925342Z-82ce96c8`) completes with the NEXT story `dispatched`, never the same story `blocked`; a genuine failed dispatch with no merged evidence still blocks (mutation test).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `a3037fa3fd` (2026-09-18, "Merge pyforge-marshal/50-1 into main"). Ledger row `50-1-a-landing-never-re-dispatches-the-story-it-just-landed: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-50-1-a-landing-never-re-dispatches-the-story-it-just-landed.md`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py`, `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_fleet.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `in-progress` → `done` (ledger row `50-1-a-landing-never-re-dispatches-the-story-it-just-landed: done`).
- `## Auto Run Result` reconstructed from git (none survived).
