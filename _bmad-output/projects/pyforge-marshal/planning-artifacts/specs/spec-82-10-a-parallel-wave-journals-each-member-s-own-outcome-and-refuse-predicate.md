---
title: '82.10: A parallel wave journals each member''s own outcome and refuse predicate'
type: 'fix'
created: '2026-10-02'
status: 'in-progress'
baseline_revision: '719fee16261b0a3b0e454a3f78f5d85a51a05b9a'
review_loop_iteration: 0
followup_review_recommended: false
warnings: [oversized]
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
deferred: []
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

- No review has run yet.
