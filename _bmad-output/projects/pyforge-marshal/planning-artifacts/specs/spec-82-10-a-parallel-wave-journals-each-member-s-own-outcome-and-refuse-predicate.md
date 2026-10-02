---
title: '82.10: A parallel wave journals each member''s own outcome and refuse predicate'
type: 'fix'
created: '2026-10-02'
status: 'done'
baseline_revision: '719fee16261b0a3b0e454a3f78f5d85a51a05b9a'
review_loop_iteration: 0
followup_review_recommended: false
warnings: [oversized]
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
deferred:
  - summary: >-
      A member refused in one cycle and cleared by re-preflight stays a block in every later fold, because
      `_campaign_blocked_from_journal` never retracts a block on a later DISPATCHED or IN_FLIGHT outcome for the same story.
    evidence: |-
      Edge Case Hunter, review of Story 82.10 (2026-10-02). The fold only adds a block from each REFUSED outcome. The same
      holds for every aggregate REFUSED row journaled before this story, so it predates it; member outcomes inherit it.
      Retracting changes fold semantics for every row and is its own CAP-135 story. What would settle it: a two-cycle test
      where a refused story's spec lands, re-preflight clears it, it dispatches, and the third cycle's fold is asserted
      to carry no block for it.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
    severity: low
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `cli/dispatch.py::execute_fleet_cycle` (`:4550`) runs a station's wave member by member (`:4845-4936`) but
journals one `StationCycleResult` per station (`:4959-4970`) with `story=primary_story` and `detail=last_detail`. Re-verified
at HEAD a7cdb91fe4:

- The station reads DISPATCHED when any member dispatched (`:4938-4945`), and a refuse predicate is computed only when the
  station reads REFUSED (`:4946-4958`). A refused primary beside a dispatched sibling therefore leaves no REFUSED row and no
  predicate; the refusal lives only in the in-memory `campaign_blocked` (`:4886`), while the next cycle, a separate process,
  rebuilds blocks from REFUSED journal rows alone (`_campaign_blocked_from_journal`, `:4989-5027`). The refusal is lost and
  re-preflight rate-limiting is bypassed (DW-FU-28-18-7).
- With two refused members, the gate is parsed from `last_detail` (whichever member wrote a detail last) while the
  predicate is computed for `primary_story` (`:4948-4957`), so the predicate can describe another story's gate, and the
  second story's block is never journaled. No test covers a mixed-refuse wave (DW-FU-28-18-8).

Both entries carry `severity: medium` in the ledger; they ride in Phase 2 because they share this code with the empty-wave
crash Story 81.1 fixed (DW-marshal-65-1-3, already `resolved` and not part of this story).

**Approach:**

- The cycle keeps one outcome per wave member: each member's story, status and detail, and for a refused member at a
  re-preflightable gate, the predicate computed from that member's own detail for that member's own story.
- The station's aggregate row stays as it is for every consumer that reads it (campaign completion, `unresolved`, the
  summary); the member outcomes ride beside it in the same journal entry.
- `_campaign_blocked_from_journal` rebuilds a block and predicate from every refused member outcome, whatever the station's
  aggregate status.

Ledger key: `82-10-a-parallel-wave-journals-each-member-s-own-outcome-and-refuse-predicate`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-135 (re-preflight when the refuse predicate can change, from `spec-marshal-drain-self-resolution`
  CAP-1) with Story 28.18, and Story 22.7 (the fleet cycle). Defects of shipped behaviour, so no new CAP; no flag.

## Acceptance Criteria

- Given a parallel wave whose primary is refused at a re-preflightable gate and whose second member dispatches When the cycle journals Then the entry carries the primary's refused member outcome with its own detail and predicate
- Given that journal When the next cycle runs `_campaign_blocked_from_journal` Then the primary's block and predicate are rebuilt
- Given a wave with two members refused at different gates When the cycle journals Then each refused member's predicate is computed from its own detail for its own story
- Given a single-story wave When the cycle journals Then the station row reads exactly as today
- Given the journal reduced back to the one aggregate row When the new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Campaign state lives in the journal, never in a driver's memory. Older journals without member outcomes still
fold. Close DW-FU-28-18-7 and DW-FU-28-18-8 in `deferred-work-ledger.md` when the story lands (status `closed`, a
`resolved:` line naming this story).

**Never:** Do not change which stories a wave admits or the order it launches them. Do not change `drain --plan`'s output.
Do not change the station-level status vocabulary.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` -- `execute_fleet_cycle`'s dispatch loop (`while pending:`) already sees every member's `(story, status, detail)`; it folds them into `dispatched_any` / `refused_any` / `last_detail` and keeps nothing per member. `_predicate_payload` / `_predicate_from_payload` (next to each other) are the one payload codec; `_campaign_blocked_from_journal` folds only rows whose station status is REFUSED, keyed on the row's `story`. `_journal_fleet_cycle` writes `result.to_payload()` per station, so nothing there changes.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py` -- `StationCycleResult` (row shape and `to_payload`), with `FOLLOWUP_REVIEWS_PAYLOAD_KEY` as the precedent for a key written only when non-empty. `campaign_complete` / `unresolved_stations` / `followups_launched` read the aggregate row only; none changes.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_re_preflight.py` -- read-only: `parse_refuse_gate`, `is_re_preflightable_gate`, `compute_refuse_predicate` stay the one owner of the predicate; `reconcile_station_re_preflight` consumes the blocks and predicates the fold returns.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/drain_plan.py` -- read-only: `drain --plan` never builds a `StationCycleResult`, so its output cannot move.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_fleet.py` -- `_cycle` (serial default; `policy_flags={"dispatch": {"max_parallel": 2}}` for a wave), `FakeFs`, the 33.8 two-member wave test (a recording `dispatch_once` stub returning `DispatchAttempt`), and the over-threshold journal round trip (`_journal_fleet_cycle` then `_campaign_blocked_from_journal`) are the fixtures to reuse.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` -- close DW-FU-28-18-7 and DW-FU-28-18-8 (`status: closed`, a `resolved:` line naming Story 82.10).

## Tasks & Acceptance

**Execution:**
- `core/dispatch_fleet.py` -- add a frozen `MemberOutcome` (story, status, detail, optional refuse predicate) and `StationCycleResult.members`; `to_payload` writes a `members` list only when non-empty -- a row with no members is byte-identical to today's
- `cli/dispatch.py` -- `_member_outcome` builds one member's outcome and, for a refused member at a re-preflightable gate, its predicate from that member's own detail and story; the dispatch loop records one outcome per attempted member, on the `except` path too
- `cli/dispatch.py` -- after the loop the station's aggregate status, story and detail stay as they are; its predicate is the primary member's own (the old `last_detail` + `primary_story` pairing described another story's gate); `members` is set only when more than one story was attempted
- `cli/dispatch.py` -- `_campaign_blocked_from_journal` reads a row's member outcomes when it has any, else the row itself, and rebuilds a block and predicate from every REFUSED one whatever the station's status
- `tests/unit/test_dispatch_fleet.py` -- one test per intent AC: refused primary beside a dispatched sibling (journal entry, then the next cycle's rebuild); two members refused at different gates (each predicate from its own detail and story); single-story rows unchanged; an older journal without members still folds; the same journal reduced to the aggregate row loses the block (mutation)
- `deferred-work-ledger.md` -- close the two rows

**Acceptance Criteria:** the five in the intent contract.

## Spec Change Log

## Design Notes

- Members are written only when a station attempted more than one story. A single-story wave and every serial cycle that attempts one story journal the row they do today; the aggregate row is the one outcome, and the fold reads it.
- A row that carries members is folded from them alone: the aggregate row's `story` is the primary and its `detail` is the last member's, so reading both would pin one story's block to another story's detail.
- The aggregate predicate follows the primary member. With the aggregate REFUSED every attempted member was refused, the primary included, so this is the old value where the old value was right and the primary's own where it described another story's gate.
- The fold keeps today's rule that a journaled block is rebuilt on every later tick; re-preflight (`reconcile_station_re_preflight`) and the merged-on-main prune still decide when it clears.

## Binding

Parent: Story 28.18 (`spec-pyforge-marshal` CAP-135) and Story 22.7; a defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 entry.
Ledger key: `82-10-a-parallel-wave-journals-each-member-s-own-outcome-and-refuse-predicate`.
Ledger status at mint: `backlog`.
Deps: —.
Closes: DW-FU-28-18-7, DW-FU-28-18-8.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

## Review Triage Log

### 2026-10-02 — Review pass
- verdicts: 21 findings — high 0, medium 3, low 15, false 3, maybe-false 0
- findings:
  - `[low]` `[reject]` Blind Hunter: the text summary and drain output show a refused primary beside a dispatched sibling as `dispatched`, and the non-plan drain JSON gains a `members` key — the intent keeps the aggregate row "as it is for every consumer that reads it (campaign completion, `unresolved`, the summary)"; the added key is additive and nothing reads it but the fold.
  - `[low]` `[patch]` Blind Hunter: the tests cover only a refused primary; the mirror (a dispatched primary beside a refused non-primary member), a three-member wave and an IN_FLIGHT member are absent — the mirror is the same defect as DW-FU-28-18-7 and gets a test; the fold reads each member's own status, so a third member or an IN_FLIGHT one runs the same `!= REFUSED` check and adds no new path. Fix applied: `test_a_dispatched_primary_beside_a_refused_second_member_journals_only_the_seconds_block_and_predicate`.
  - `[medium]` `[patch]` Blind Hunter: nothing tests the serial harness-done advance, where `members` is populated outside a parallel wave — carried with the verification-gap finding below (same root cause).
  - `[low]` `[reject]` Blind Hunter: `members or [row]` falls back to the aggregate row when every member entry is malformed — `StationCycleResult.to_payload` writes `members` only as a non-empty list of dicts, so no journal this code wrote can reach the fallback; a guard would add a branch for a hand-corrupted journal.
  - `[low]` `[reject]` Blind Hunter: no test sends a member-bearing row through the AD-30 sidecar threshold — the sidecar is applied to the whole entry payload (`prepare_for_write`) and resolved before the fold reads it, so `members` is one more list inside a payload the existing over-threshold test already round-trips.
  - `[low]` `[reject]` Blind Hunter: a member whose dispatch raised beside a dispatched sibling is now a journaled block where the old row read DISPATCHED and the next tick retried it — the intent mandates a block from every refused member, and a raise alone in a station already journals REFUSED and persists the same block; recorded under Residual risks.
  - `[low]` `[reject]` Blind Hunter: the mutation test strips `members` at write time, not in the fold, and cites another test by its full name — AC5 reduces the journal to the aggregate row, which is exactly this mutation; the other new tests fail under it too (checked, see Auto Run Result).
  - `[low]` `[reject]` Blind Hunter: the two-cycle drain test asserts only strings, and the sibling's non-relaunch is incidental to the blocked head — the load-bearing assertion is that the refused primary is not launched again, and `MRS-DRAIN-017` is what carries the rate-limit.
  - `[low]` `[reject]` Blind Hunter: `_member_outcome` has three near-identical call sites, the except-path call can never produce a predicate and the helper uses `assert gate is not None` — cosmetic; the assert is the old code's own narrowing carried over unchanged.
  - `[false]` `[reject]` Blind Hunter: the aggregate `detail` carries the primary's refusal text under a DISPATCHED status — `detail=last_detail` is today's behaviour and the intent keeps the aggregate row as it is; nothing new happens at that location.
  - `[low]` `[reject]` Blind Hunter: the `members` payload key has no documentation beyond the memlog — marshal ships no frozen report schema (`verdict.py` only), `followup_reviews` has the same record, and the Code Map and the ledger `resolved:` lines name the key.
  - `[low]` `[reject]` Edge Case Hunter: `compute_refuse_predicate` raising `OSError` inside `_member_outcome` aborts the cycle mid-wave — the old code called the same function after the loop, so the same raise lost the same results; EACCES on a tracked spec is not a case anyone showed the program can reach, and the guard adds a branch.
  - `[low]` `[defer]` Edge Case Hunter: a member refused in cycle N and cleared by re-preflight in cycle N+1 is rebuilt as a block by every later fold, because the fold never retracts on a later DISPATCHED outcome — the same shape holds for every aggregate REFUSED row journaled today, so it predates this story; retracting is a change to fold semantics for every row and belongs to its own CAP-135 story. Deferred.
  - `[false]` `[reject]` Edge Case Hunter: for a two-member serial cycle whose head is refused at a non-re-preflightable gate and whose follow-up is refused at a re-preflightable one, the aggregate `refuse_predicate` drops to `None` — `_campaign_blocked_from_journal` folds a row that carries members from the members alone, and no other reader of the aggregate predicate exists (searched `src/` for `refuse_predicate`), so the drop changes nothing observable.
  - `[medium]` `[patch]` Verification Gap: a serial two-story cycle (the `MRS-DISP-040` harness-done advance) now journals `members` and the next cycle's fold persists the refused head as a block, with no test on the row or the fold — the block matches the documented design (`core/dispatch_fleet.py::plan_station_queue`: 040 "is recorded as a campaign block so the same story is never relaunched") and the Boundaries rule that campaign state lives in the journal. Fix applied: `test_harness_done_040_serial_advance_journals_the_refused_head_and_the_dispatched_next_as_members` pins the row and the fold.
  - `[medium]` `[patch]` Intent Alignment: the diff reads "wave" as every cycle that attempts more than one story, the serial advance included, which the intent's own tests do not exercise — carried with the verification-gap finding above (same root cause, same test).
  - `[low]` `[reject]` Intent Alignment: the MRS-DISP-005 missing-spec escalation scan (`gather_fleet_missing_spec_escalations`) is a second reader of the fold and now sees member-derived blocks, with no test — the fold's contract is the one the intent changes; that reader keeps its own tests and now sees the refusal it was written to see (Story 28.19).
  - `[low]` `[patch]` Intent Alignment: the first criterion says the entry carries the member's own detail and predicate, and the test checked the journaled `members` payload only for story and status — the round trip was pinned through the fold, but the payload assertion is two lines. Fix applied: the test asserts the refused member's `detail` and `refuse_predicate` in the payload.
  - `[low]` `[reject]` Intent Alignment: the sidecar path is not exercised with a member-bearing row — carried with the Blind Hunter sidecar row above.
  - `[low]` `[reject]` Intent Alignment: the non-plan `factory drain` output gains a `members` key — carried with the Blind Hunter summary row above.
  - `[false]` `[reject]` Intent Alignment: the aggregate predicate in the two-refused case is now the primary's own, which the intent does not specify — the old pairing (the last member's gate, the primary's story) is the defect DW-FU-28-18-8 names, and the intent is silent only on what replaces it; no reader consumes it for a members-bearing row (carried with the Edge Case Hunter row above).

## Auto Run Result

Status: done

**Summary.** A station row whose wave attempted more than one story now carries a `members` list beside its unchanged aggregate fields: each member's story, status and detail, and for a REFUSED member at a re-preflightable gate the refuse predicate computed from that member's own detail for that member's own story. `_campaign_blocked_from_journal` folds a row that has members from them alone and rebuilds a block and predicate from every REFUSED one, whatever the station's aggregate status; a row without members (an older journal, a single-story cycle) folds as before. The aggregate status vocabulary, the wave's admission and order, and `drain --plan` are untouched. The aggregate `refuse_predicate` of a REFUSED station is now the primary member's own, where it used to pair the last member's gate with the primary's story.

**Files changed.**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py` -- frozen `MemberOutcome`, `StationCycleResult.members`, `MEMBERS_PAYLOAD_KEY`; `members` is written only when non-empty.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` -- `_member_outcome`; the dispatch loop records one outcome per attempted member (the `except` path too); `_campaign_blocked_from_journal` folds member outcomes.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_fleet.py` -- ten new tests (13 cases): refused primary beside a dispatched sibling, the next cycle's rebuild, a two-cycle drain that rate-limits (`MRS-DRAIN-017`), two members refused at different gates, the mirror (dispatched primary, refused second), a raised dispatch, the serial `MRS-DISP-040` advance, single-story rows unchanged, an older journal, and the aggregate-row mutation.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` -- DW-FU-28-18-7 and DW-FU-28-18-8 `status: closed` with a `resolved:` line naming Story 82.10.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md`, `.../spec-pyforge-core/.memlog.md` -- the surface reconcile naming every governed path changed. No baseline stamped.

**Review findings.** 21 findings, patches applied 3 entries (the serial `MRS-DISP-040` advance test, the mirror test, the journaled-payload assertions; all tests, no source change), 1 deferred (the fold never retracts a block on a later DISPATCHED outcome; pre-existing, in `deferred:`), and every other finding rejected with its reason in the Review Triage Log. Patched entries by verdict: high 0, medium 1, low 2.

**Follow-up review recommended:** `false` -- no patched entry was `high` and only one was `medium`; the patches added tests and no behaviour.

**Verification performed.**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 10074 passed, 1 skipped, 14 deselected (exit 0, read from the exit-code file).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- 130 passed, 3 skipped (exit 0).
- `pixi run --frozen -e pyforge-guild lint-types` -- exit 0 (ruff, format, mypy).
- `pixi run --frozen -e pyforge-guild spec-surface-check` -- ok, no drift (stale-glob warnings only, none on files this story touched); `python scripts/spec_surface_reconcile.py` -- exit 0.
- Mutation, run from outside the worktree with a pytest plugin that drops `members` from every journaled row: 8 of the 13 new test cases fail; the 5 that pass are the single-story and older-journal cases, which carry no members by design.

**Residual risks.**
- A member whose dispatch raised beside a dispatched sibling is now a journaled block; before, the next tick retried it. A raise alone in a station already persisted the same block, and the intent asks for a block from every refused member, but a transient error in a wave now needs the same clearing (the merged-on-main prune or an operator) as a single-story one.
- A serial cycle that attempts two stories (the `MRS-DISP-040` harness-done advance) now journals `members`, so the refused head's block survives the process; before, a dispatched follow-on dropped it and the head's land-only attempt re-ran each tick. This matches the documented design (`plan_station_queue`: a 040 head is a campaign block so the same story is never relaunched) and is pinned by a test.
- `pr-preflight` was not run: the story's own `verify_commands`, `lint-types`, `spec-surface-check` and the reconcile guard were. The touched-module coverage floors are unchecked.
