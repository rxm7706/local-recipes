---
title: '73.2: A drain schedules the follow-up review a landed story recommended'
type: 'feature'
created: '2026-09-28'
status: 'in-review'
baseline_revision: 'bb577e29a1159de67ab0b71b55eca5b4673a6304'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-73-1-a-follow-up-review-run-is-judged-and-landed-by-its-own-branch.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py
warnings:
  - oversized
  - 'Story 66.2 backfills a DW-FRR row for every landed story still carrying the flag (181 uncarried of 210 measured on 2026-09-28). The wave size, left open at the mint, was ruled by the operator on 2026-09-28: at most dispatch.max_followup_reviews_per_campaign (default 2) follow-ups per drain campaign, newest landings first; the rest wait for later campaigns, so the backlog drains in about 91 campaigns at the default.'
deferred: []
---

<intent-contract>

## Intent

**Problem:** a drain never dispatches a `done` key: `core/dispatch_fleet.NON_IMPLEMENT_STATUSES` holds `done` (`:61`) and `station_backlog` drops it (`:565`), and `factory drain --stories` refuses one with `MRS-DISP-032` (`cli/dispatch.py:4315-4331`). So an open `DW-FRR-<story>` row (CAP-275, Story 66.1) waits for a hand dispatch forever, even once Story 73.1 makes a follow-up run judged and landed by its own branch. Once Story 66.2's backfill lands, 181 rows open at once (measured 2026-09-28); queued without a bound, one campaign would spend a session on every one of them after the backlog. The operator ruled on 2026-09-28: at most N follow-up reviews per drain campaign, a policy key, default 2, newest landings first; the rest wait for later campaigns. Today the policy's `dispatch` block carries only `max_parallel` (`core/policy.py:626`), and `_valid_dispatch_block` (`:921-933`) rejects any other key.

**Approach:**
- A pure function in `core/dispatch_fleet.py` builds a station's follow-up queue from (a) the open `DW-FRR` rows parsed from its tracked `deferred-work-ledger.md` (`origin: dispatch-followup-review`, `status: open`, through Story 73.1's parser in `core/deferred_work.py`) and (b) each row's story spec state on `origin/main` (`parse_spec_status` and `followup_review_recommended`). A row is a candidate only when the spec reads `done` with the flag true; an open row whose spec no longer qualifies is returned as stale.
- **The per-campaign cap (amended 2026-09-28, operator ruling).** `DEFAULT_POLICY["dispatch"]` (`core/policy.py`) gains `"max_followup_reviews_per_campaign": 2`, and `_valid_dispatch_block` admits it as an optional non-negative integer beside `max_parallel` (0 turns follow-up scheduling off; any other value rejects the block with `MRS-POLICY-002`, as a bad `max_parallel` does; a block that omits it composes the default). The cap bounds a campaign, not a station, so the drain resolves it from the repository's layers — Marshal's default, then `_bmad-output/policy-defaults.toml` — and a station project layer that sets it is named in a WARN finding and not applied.
- A second pure function in `core/dispatch_fleet.py` selects the campaign's follow-ups across every station's candidates: newest landing first, by the position of each story's corroborated merge subject in `commit_subjects(ORIGIN_MAIN)` (newest first; a candidate with none there sorts after every matched one, in ledger order), taking at most the cap minus the follow-ups this campaign already launched. That count comes from the campaign journal's fleet-cycle entries, read the way `_campaign_blocked_from_journal` reads campaign blocks, so the cap holds across every cycle of one campaign. The candidates beyond it are named in one INFO finding (how many wait, and the cap) and wait for a later campaign.
- The drain cycle (`cli/dispatch.py`, where it builds each station's backlog) reads the ledger and each row's spec at `origin/main` (`dispatch_core.spec_text_at_ref`), and appends each station's selected follow-ups after its implementable backlog, newest landing first, before `plan_station_queue`. Mode accounting, declared skips, `_station_blocked_map` and campaign blocks apply to a follow-up exactly as to any story; the launch is Story 73.1's `dispatch_once` path.
- Every guard that advances past a merged key (Story 50.1 Part B's already-landed advance; `_reconcile_blocked_against_main`'s merged prune) judges a follow-up entry by its row, not by the story's first merge: a follow-up whose row is open is not "already landed".
- Stale rows are named in the cycle's findings (a WARN naming the row and why it is not dispatched) and never dispatched.
- `--stories` is unchanged (it still refuses a `done` key).

Ledger key: `73-2-a-drain-schedules-the-follow-up-review-a-landed-story-recommended`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / 73.1.

### Living CAP citations

- `spec-pyforge-marshal` CAP-281 (FR-228; amended 2026-09-28, operator ruling: the per-campaign cap `dispatch.max_followup_reviews_per_campaign`, default 2, newest landings first); CAP-6 (Story 33.8, the `dispatch` policy block the key joins).
- Kinship: `spec-pyforge-doctor:CAP-86` (Doctor checks on every PR that a done story's recommended follow-up review is carried).
- Kinship: `spec-pyforge-marshal` CAP-274 (Story 65.1: `drain --plan` computes each station's queue through the same functions, so it lists the follow-ups and stale rows this story adds; `drain --plan` is not built here); CAP-275 (Stories 66.1, 66.2, the rows).

## Acceptance Criteria

- Given a station with an empty implementable backlog, an open `DW-FRR-51-2` row and 51.2's spec on `origin/main` reading `done` with the flag true When a drain cycle runs Then it dispatches one follow-up review run for 51.2 through `dispatch_once`
- Given that run landed and its row closed (Story 73.1) When the next cycle runs Then nothing is dispatched for 51.2
- Given a non-empty implementable backlog When the cycle plans Then the follow-up queues after the backlog
- Given a closed `DW-FRR-51-2` row, or an open row whose spec reads the flag false, or a `done` spec with no row When a cycle runs Then nothing is dispatched for 51.2, and the open-but-stale row is named in a WARN finding
- Given a follow-up run that failed When the next cycle plans Then it is a campaign block like any story's (not re-dispatched in the same campaign)
- Given the ledger twin When any of the above runs Then `51-2` reads `done` before, during and after, and no ledger key is added or flipped
- Given Story 65.1's `drain --plan` is present When it runs on the first fixture Then it lists the 51.2 follow-up (and names a stale row and how many follow-ups wait)
- Given the row gate removed (candidates taken from specs alone) When the second-cycle fixture runs Then 51.2 is dispatched again and the test fails (mutation)
- Given 181 open qualifying `DW-FRR` rows across the stations' fixture ledgers, each story's corroborated merge subject on `origin/main`, and the default policy When a drain campaign runs its cycles Then it dispatches exactly 2 follow-ups — the two newest landings by merge-subject position — and one INFO finding names 179 waiting with the cap 2 (amended 2026-09-28)
- Given those two follow-ups landed and their rows closed When the next campaign runs Then it dispatches exactly the next 2 newest; given a campaign's first cycle launched 2 When its later cycles plan Then they queue no further follow-up
- Given `max_followup_reviews_per_campaign = 0` under `[dispatch]` in `_bmad-output/policy-defaults.toml` When a campaign runs Then no follow-up is queued and the INFO finding names every qualifying row as waiting
- Given a station's project `marshal-policy.toml` setting `max_followup_reviews_per_campaign` under `[dispatch]` When a campaign runs Then a WARN names that file and the key, and the repository-layer cap applies
- Given `max_followup_reviews_per_campaign = -1` (or a non-integer) in any layer When the policy composes Then the `dispatch` block is rejected with `MRS-POLICY-002`, as a bad `max_parallel` is; a `[dispatch]` block with only `max_parallel` still composes, with the cap at 2
- Given a candidate whose story has no corroborated merge subject on `origin/main` When the campaign selects Then it sorts after every candidate that has one
- Given the cap removed from the selection When the 181-row fixture runs Then more than 2 follow-ups are queued and the test fails (mutation)

## Boundaries & Constraints

**Always:** Implement only the Surface named in `epics.md` Story 73.2. Gate every follow-up on its row's state; read spec state and landing order from `origin/main`. Keep queue selection, the cap and the order pure in `core/` (AD-4). Queue follow-ups after the implementable backlog. Count the cap per campaign, across every station and cycle, from the campaign's own journal.

**Never:**
- Do not put a `done` key back in `station_backlog`'s implementable set or flip any ledger key.
- Do not dispatch a follow-up whose row is closed or absent, or whose spec no longer reads `done` with the flag true.
- Do not queue more follow-ups in one campaign than `dispatch.max_followup_reviews_per_campaign`, and do not let a station's project layer raise or lower it (amended 2026-09-28).
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
| more candidates than the cap | 181 open qualifying rows, default policy | 2 queued, newest landings first; the rest wait | INFO names the waiting count and the cap |
| cap already spent | this campaign launched 2 in an earlier cycle | no further follow-up this campaign | none |
| cap 0 | `[dispatch]` `max_followup_reviews_per_campaign = 0` in the repository defaults | none queued | INFO names the waiting count |
| project layer sets the cap | a station's `marshal-policy.toml` `[dispatch]` | repository-layer cap applies | WARN names the file |
| invalid cap | negative or non-integer | `dispatch` block rejected | `MRS-POLICY-002` |
| no merge subject on `origin/main` | hand-landed under another subject | sorts after every matched candidate, in ledger order | none |

</intent-contract>

## Code Map

Paths sit under `src/shared/packages/pyforge-marshal/src/pyforge/marshal/` (`<pkg>/`); tests under `src/shared/packages/pyforge-marshal/tests/unit/`. The contract's line numbers are stale (re-measured 2026-10-01); anchors here are symbols. Story 73.1 is on this branch.

- `<pkg>/core/policy.py` -- `_DISPATCH_BLOCK_KEYS`, `DEFAULT_POLICY["dispatch"]`, `_valid_dispatch_block`; `_valid_landing_grace_seconds` is the non-negative-int validator with the magnitude probe the new key reuses; `resolve_landing_check_settings` is the pattern for a consumer-side default (`_merge_field` replaces a `dispatch` block whole, so a block omitting the key reads 2 at the consumer). The contract's "carries only `max_parallel`" is stale: Story 80.1 added three `landing_check_*` keys.
- `<pkg>/core/deferred_work.py` -- `_FOLLOWUP_REVIEW_HEADING_RE`, `_open_followup_review_rows`, `open_followup_review_id`, `followup_review_id` (row id `DW-FRR-<hyphen key>`; `normalize` reads it back). The all-rows read joins them (pure, AD-4).
- `<pkg>/core/dispatch_fleet.py` -- `NON_IMPLEMENT_STATUSES` and `station_backlog` stay untouched; `StationCycleResult.to_payload` (journal row), `plan_station_queue` (mode accounting, advance reasons), `FleetCampaignMode`; the candidate, cap-selection and landing-order functions join here (pure).
- `<pkg>/core/promotion.py::corroborated_merged_story_keys` -- one subject in, at most one key out; reuse it per subject to get a key's position (never re-implement the classifier).
- `<pkg>/cli/dispatch.py` -- `plan_station_cycle` (read-only per-station planner shared with `drain --plan`; `backlog` is built here), `StationCyclePlan`, `execute_fleet_cycle` (findings, results, dispatch loop), `_campaign_blocked_from_journal` (the journal-fold pattern for the launched count), `_reconcile_campaign_blocked` (merged prune, reads the whole `origin/main`: Story 73.1's deferred D1), `station_story_block_facts` (Story 50.1 Part B already-landed advance), `_station_blocked_map`, `_compose_policy`, `run_fleet_drain` (`--stories` refusal `MRS-DISP-032` stays), `_derive_followup_review` (Story 73.1: the ledger read at `ORIGIN_MAIN` through `vcs.file_text_at_ref`).
- `<pkg>/cli/drain_plan.py` -- `run_drain_plan` calls `plan_station_cycle` per station; `evaluate_story` refuses `already-landed` from `_StationReads.merged_keys()` (wrong for a follow-up); `_plan_station` payload row and `render_plan_text`.
- `<pkg>/cli/config.py` -- `read_repo_policy_defaults`, `conventional_project_policy_path`, `_read_project_policy`: the repository layer and a station's project layer.
- `<pkg>/core/findings.py` -- registered finding codes; any new code is registered here (prefer an existing `MRS-DRAIN-*` code if one fits).
- `tests/unit/test_dispatch_fleet.py` (fleet fakes, `execute_fleet_cycle`, `run_fleet_drain`), `test_drain_plan.py`, `test_policy.py`, `test_deferred_work.py`.
- Read-only: `sprint-status-ledger.yaml`, `deferred-work-ledger.md`, every `SPEC.md`, `.claude/skills/bmad-build-auto/`.

## Tasks & Acceptance

**Execution:**
- `<pkg>/core/policy.py` -- `dispatch.max_followup_reviews_per_campaign` (default 2, non-negative int; `_valid_followup_review_cap` over `_valid_landing_grace_seconds`), `resolve_followup_review_cap(effective)` (default when absent) -- the operator's per-campaign cap.
- `<pkg>/core/deferred_work.py` -- `open_followup_review_story_keys(ledger_text)`: story keys of rows headed `DW-FRR-<story>` with `origin: dispatch-followup-review` and `status: open`, ledger order -- the row gate.
- `<pkg>/core/dispatch_fleet.py` -- `FollowupCandidate`, `StaleFollowupRow`, `station_followup_queue` (row gate x spec `done` + flag true; the rest of the open rows are stale), `landing_positions` (newest-first position of each corroborated merge subject), `select_campaign_followups` (newest landing first, unmatched after, in ledger order; cap minus launched; the waiting remainder), `StationCycleResult.followup_reviews` (payload key only when non-empty) -- all pure.
- `<pkg>/cli/dispatch.py` -- `plan_followup_reviews` (reads each cycle station's ledger and specs at `origin/main`, the repository-layer cap, the journal's launched count, a project-layer WARN, an unreadable-ledger WARN, the INFO and stale WARN facts), `plan_station_cycle(..., followups=())` appends a station's selected follow-ups after its implementable backlog (never under `--stories`), `execute_fleet_cycle` emits the findings and records the follow-ups it dispatched on the station result, `_followups_launched_from_journal` folds the campaign's fleet-cycle outcomes, `station_story_block_facts` skips the Part B already-landed advance for a follow-up, `_reconcile_campaign_blocked` never prunes a follow-up entry as merged.
- `<pkg>/cli/drain_plan.py` -- `run_drain_plan` plans the same follow-ups, lists them on the station row, names stale rows and the waiting count, and `evaluate_story` no longer refuses a follow-up as `already-landed`.
- Tests (`tests/unit/`): `test_policy.py` (cap default, validation, `[dispatch]` with only `max_parallel`), `test_deferred_work.py` (all-rows read), `test_dispatch_fleet.py` (pure functions, every I/O-matrix row, the 181-row fixture, both mutations, the two-campaign and cap-spent scenarios, the campaign block, the ledger twin), `test_drain_plan.py` (the `--plan` row) -- no ledger key added or flipped in any fixture.
- Spec memlogs -- name every governed path on `spec-pyforge-marshal`'s `.memlog.md` and on each co-governor `spec-surface` names (`uv run _bmad/scripts/memlog.py append`); never `--write-baseline`.

**Acceptance Criteria:**
- Given the change, when the station suite, `lint-types` and `spec_surface_reconcile.py` run, then all pass and the touched modules keep their coverage floors
- Given a normal drain (no `DW-FRR` rows), when a cycle runs, then its findings, results and journal payload are byte-identical to before this story

## Spec Change Log

## Review Triage Log

## Design Notes

- Selection is two-phase: one campaign-wide read (`plan_followup_reviews`) before the per-station loop, then each station's planner receives only its own selected follow-ups. `drain --plan` makes the same read, so the plan cannot drift from the drain.
- A follow-up this campaign already launched stays queued while its row is open and costs no further cap: a live one then reads `in-flight` and a failed one blocks, exactly as any story's. Only new follow-ups spend `cap - launched`.
- Landing order reuses `corroborated_merged_story_keys` one subject at a time; the first index at which a key appears is its newest landing.

## Source

Contract authored from the operator's 2026-09-28 direction, `docs/dreams/pyforge-marshal.md`'s 2026-09-28 entry (*a drain runs the follow-up review a landed story recommended*) and `spec-pyforge-marshal` CAP-281 with its 2026-09-28 direction entry in the Spec's `.memlog.md`, decomposed the same session as Epic 73's mint. Amended the same day from the operator's ruling on the wave size — a per-campaign cap, default 2, newest landings first (the Spec's `.memlog.md` decision entry of 2026-09-28 and CAP-281's amended text).

## Binding

Parent Spec capability: `spec-pyforge-marshal` CAP-281 (FR-228).
Ledger key: `73-2-a-drain-schedules-the-follow-up-review-a-landed-story-recommended`.
Ledger status at mint: `backlog`.
Deps: Story 73.1 (the launch marker, the run semantics and the row close; scheduling before them would spend sessions that read finished at once and never land, and the open row would respawn them each campaign). Story 66.1 transitively, through 73.1.
Amended 2026-09-28 (operator ruling): the per-campaign cap `dispatch.max_followup_reviews_per_campaign`; key, status and Deps kept.
Policy: no `[epic_surfaces]` entry; the Surface, including `core/policy.py`, is inside marshal's default surface.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
