---
title: '73.2: A drain schedules the follow-up review a landed story recommended'
type: 'feature'
created: '2026-09-28'
status: 'backlog'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-73-1-a-follow-up-review-run-is-judged-and-landed-by-its-own-branch.md
warnings:
  - 'Story 66.2 backfills a DW-FRR row for every landed story still carrying the flag (181 uncarried of 210 measured on 2026-09-28). Once 66.2 and this story land, a drain_to_zero campaign queues every qualifying follow-up after the backlog; the wave size is an operator decision recorded as an open question at the mint.'
deferred: []
---

<intent-contract>

## Intent

**Problem:** a drain never dispatches a `done` key: `core/dispatch_fleet.NON_IMPLEMENT_STATUSES` holds `done` (`:61`) and `station_backlog` drops it (`:565`), and `factory drain --stories` refuses one with `MRS-DISP-032` (`cli/dispatch.py:4315-4331`). So an open `DW-FRR-<story>` row (CAP-275, Story 66.1) waits for a hand dispatch forever, even once Story 73.1 makes a follow-up run judged and landed by its own branch.

**Approach:**
- A pure function in `core/dispatch_fleet.py` builds a station's follow-up queue from (a) the open `DW-FRR` rows parsed from its tracked `deferred-work-ledger.md` (`origin: dispatch-followup-review`, `status: open`, through Story 73.1's parser in `core/deferred_work.py`) and (b) each row's story spec state on `origin/main` (`parse_spec_status` and `followup_review_recommended`). A row is a candidate only when the spec reads `done` with the flag true; an open row whose spec no longer qualifies is returned as stale.
- The drain cycle (`cli/dispatch.py`, where it builds each station's backlog) reads the ledger and each row's spec at `origin/main` (`dispatch_core.spec_text_at_ref`), and appends the candidates' story keys after the station's implementable backlog, in ledger order, before `plan_station_queue`. Mode accounting, declared skips, `_station_blocked_map` and campaign blocks apply to a follow-up exactly as to any story; the launch is Story 73.1's `dispatch_once` path.
- Every guard that advances past a merged key (Story 50.1 Part B's already-landed advance; `_reconcile_blocked_against_main`'s merged prune) judges a follow-up entry by its row, not by the story's first merge: a follow-up whose row is open is not "already landed".
- Stale rows are named in the cycle's findings (a WARN naming the row and why it is not dispatched) and never dispatched.
- `--stories` is unchanged (it still refuses a `done` key).

Ledger key: `73-2-a-drain-schedules-the-follow-up-review-a-landed-story-recommended`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / 73.1.

### Living CAP citations

- `spec-pyforge-marshal` CAP-281 (FR-228).
- Kinship: `spec-pyforge-marshal` CAP-274 (Story 65.1: `drain --plan` computes each station's queue through the same functions, so it lists the follow-ups and stale rows this story adds; `drain --plan` is not built here); CAP-275 (Stories 66.1, 66.2, the rows).

## Acceptance Criteria

- Given a station with an empty implementable backlog, an open `DW-FRR-51-2` row and 51.2's spec on `origin/main` reading `done` with the flag true When a drain cycle runs Then it dispatches one follow-up review run for 51.2 through `dispatch_once`
- Given that run landed and its row closed (Story 73.1) When the next cycle runs Then nothing is dispatched for 51.2
- Given a non-empty implementable backlog When the cycle plans Then the follow-up queues after the backlog
- Given a closed `DW-FRR-51-2` row, or an open row whose spec reads the flag false, or a `done` spec with no row When a cycle runs Then nothing is dispatched for 51.2, and the open-but-stale row is named in a WARN finding
- Given a follow-up run that failed When the next cycle plans Then it is a campaign block like any story's (not re-dispatched in the same campaign)
- Given the ledger twin When any of the above runs Then `51-2` reads `done` before, during and after, and no ledger key is added or flipped
- Given Story 65.1's `drain --plan` is present When it runs on the first fixture Then it lists the 51.2 follow-up (and names a stale row)
- Given the row gate removed (candidates taken from specs alone) When the second-cycle fixture runs Then 51.2 is dispatched again and the test fails (mutation)

## Boundaries & Constraints

**Always:** Implement only the Surface named in `epics.md` Story 73.2. Gate every follow-up on its row's state; read spec state from `origin/main`. Keep queue selection pure in `core/` (AD-4). Queue follow-ups after the implementable backlog.

**Never:**
- Do not put a `done` key back in `station_backlog`'s implementable set or flip any ledger key.
- Do not dispatch a follow-up whose row is closed or absent, or whose spec no longer reads `done` with the flag true.
- Do not change `--stories`, `plan_station_queue`'s mode semantics or `dispatch_once` (Story 73.1 owns the launch).
- Do not build `drain --plan` here (Story 65.1).
- Do not hand-edit `sprint-status-ledger.yaml`, `deferred-work-ledger.md` or `SPEC.md`; do not run `scripts/bmad-switch`.

Co-governing Specs: `spec-pyforge-marshal` (owner of `src/shared/packages/pyforge-marshal/**`) and `spec-pyforge-core` (co-governs every station's `src/`) — reconcile each one the spec-surface detector names.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| open row, qualifying spec | backlog empty | one follow-up dispatched | none |
| row closed after landing | next cycle | nothing for that story | none |
| backlog non-empty | open row | follow-up after the backlog | none |
| stale row | open, spec flag false | not dispatched; WARN names the row | none |
| no row | spec `done`, flag true | not dispatched (no row, no gate) | none |
| failed follow-up | campaign block | not re-dispatched this campaign | as any story |
| ledger unreadable | deferred-work ledger unreadable | no follow-ups this cycle for that station | WARN naming the path |

</intent-contract>

## Source

Contract authored from the operator's 2026-09-28 direction, `docs/dreams/pyforge-marshal.md`'s 2026-09-28 entry (*a drain runs the follow-up review a landed story recommended*) and `spec-pyforge-marshal` CAP-281 with its 2026-09-28 direction entry in the Spec's `.memlog.md`, decomposed the same session as Epic 73's mint.

## Binding

Parent Spec capability: `spec-pyforge-marshal` CAP-281 (FR-228).
Ledger key: `73-2-a-drain-schedules-the-follow-up-review-a-landed-story-recommended`.
Ledger status at mint: `backlog`.
Deps: Story 73.1 (the launch marker, the run semantics and the row close; scheduling before them would spend sessions that read finished at once and never land, and the open row would respawn them each campaign). Story 66.1 transitively, through 73.1.
Policy: no `[epic_surfaces]` entry; the Surface is inside marshal's default surface.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
