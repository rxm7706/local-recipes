---
title: '81.1: A drain cycle whose wave holds every story reports held instead of crashing'
type: 'fix'
created: '2026-10-01'
status: 'in-review'
baseline_revision: 'f73e1f3680068a50352326b7848ba17638756f87'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** `cli/dispatch.py::execute_fleet_cycle` builds a station's cycle result from the queue walk's outcome when no
story was dispatched: `dispatch_fleet.StationCycleStatus(plan.outcome.value)`. The queue walk can answer
`StationQueueOutcome.DISPATCH` ("a story is eligible") while the parallel wave then holds every candidate out because their
declared Deps are not all done. `StationCycleStatus` has no `dispatch` value, so the cycle raises
`ValueError: 'dispatch' is not a valid StationCycleStatus` and the operator sees a traceback, not the reason. Found
2026-10-01: `marshal factory dispatch pyforge-marshal --stories 73.1,73.2` crashed this way while 73.1 waited on 66.1;
`drain --plan` reported the same state correctly as `held` (MRS-DRAINPLAN-004). Latent since 2026-09-01.

**Approach:**

- A held wave is reported as held: the station's cycle result reads a `held` status (added to `StationCycleStatus`) and a
  WARN finding names each held story with its unmet Deps, in the words `drain --plan` uses.
- Any queue outcome that has no cycle-status twin is mapped explicitly, never through `StationCycleStatus(value)`.

Ledger key: `81-1-a-drain-cycle-whose-wave-holds-every-story-reports-held-instead-of-crashing`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- Story 22.7 (the fleet-wide drain cycle) and Story 65.1 (`spec-pyforge-marshal` CAP-274, `drain --plan`'s `held`
  outcome). A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a station whose queue walk picks a story and a parallel wave that holds every candidate for unmet Deps When `execute_fleet_cycle` runs Then the station result reads `held`, a WARN names each held story and its unmet Deps, and no exception escapes
- Given the same state When `marshal factory dispatch <slug> --stories <keys>` runs Then it exits through its normal verdict and reports the held stories
- Given a wave that admits at least one story When the cycle runs Then the result is unchanged (`dispatched`)
- Given the explicit mapping replaced by `StationCycleStatus(plan.outcome.value)` When the new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Report a held story; never dispatch it early. Keep the queue walk and the wave planner pure.

**Never:** Do not change which stories a wave admits. Do not change `drain --plan`'s output.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` -- `execute_fleet_cycle`: two sites built the cycle status as `StationCycleStatus(plan.outcome.value)` (no next story; empty wave). The empty-wave one crashes on `DISPATCH`. `plan_station_cycle` / `StationCyclePlan` hold the facts (`wave`, `deps_graph`, `statuses`, `stories_to_dispatch`); `skip_basis` is the precedent for a helper the cycle and `drain --plan` share.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py` -- `StationQueueOutcome`, `StationCycleStatus`, `TERMINAL_STATION_STATUSES`, `campaign_complete` / `unresolved_stations` (the only status consumers: a terminal status stops the campaign supervisor).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_prelaunch.py` -- `unmet_deps` (pure Deps readiness); the home of the shared held-reason wording.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/drain_plan.py` -- `_held_reason` and the `held` rows: read-only evidence of the wording to keep; its output must not change.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` / `core/verdict.py` -- `MRS-DRAIN-016` (a story refused from a wave, dep-unmet included) is `WARN`; reused, so no new code to register.
- `src/shared/packages/pyforge-marshal/tests/unit/test_drain_plan.py` / `test_dispatch_fleet.py` -- cycle fixtures (`_run_one_cycle`, `_seed_unmet_deps`, `_plan`) and the core-level status tests.

## Tasks & Acceptance

**Execution:**
- `core/dispatch_fleet.py` -- add `StationCycleStatus.HELD`, make it terminal, and add `idle_station_status(outcome)`, an explicit total mapping from every `StationQueueOutcome` (`DISPATCH` -> `HELD`) -- the enum lookup is the defect
- `core/dispatch_prelaunch.py` -- add `held_reason(story, statuses, graph, wave)`, the one wording of why the wave holds a story out -- `drain --plan` and the cycle must not drift
- `cli/dispatch.py` -- add `wave_held_stories(cycle)`; map both idle sites through `idle_station_status`; on an empty wave report `held`, with one `MRS-DRAIN-016` WARN per held story the refusal loop has not already named, and the held stories and reasons in `detail`
- `cli/drain_plan.py` -- delegate `_held_reason` and the held-story selection to the shared helpers, output unchanged
- `tests/unit/test_drain_plan.py`, `tests/unit/test_dispatch_fleet.py` -- tests for each Acceptance Criterion, the mapping's totality and the terminal status
- `spec-marshal-single-story-dispatch/fleet-drain-playbook.md` -- the campaign exit criteria list `held` among the terminal statuses

**Acceptance Criteria:**
- Given an empty wave on an eligible head, when `execute_fleet_cycle` runs, then the station reads `held`, a WARN names the story and its unmet Deps, and no exception escapes
- Given the same state, when `factory dispatch <slug> --stories <keys>` runs, then it exits through its normal verdict, spawns no campaign supervisor, and reports the held stories
- Given a wave that admits a story, when the cycle runs, then it reads `dispatched` with no held finding
- Given the enum lookup restored at the empty-wave site, when the new tests run, then they fail

## Spec Change Log

## Design Notes

`held` is terminal. A held station only moves once a Dep lands outside its own drain, which a supervisor tick cannot cause; left non-terminal, the campaign would poll a station that cannot progress. A station still working elsewhere in the fleet keeps the campaign going, and every cycle re-plans every station, so a Dep that lands is picked up. `MRS-DRAIN-016` is reused rather than minting a code: its registry text already covers a story held from a wave for unmet Deps.

## Binding

Parent: Story 22.7's fleet cycle and Story 65.1 (CAP-274); defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-01 (evening) entry.
Ledger key: `81-1-a-drain-cycle-whose-wave-holds-every-story-reports-held-instead-of-crashing`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-01 by operator ruling: fix the defect now.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

### 2026-10-01 — Review pass
- verdicts: 22 findings — high 0, medium 0, low 15, false 7, maybe-false 0
- findings:
  - `[low]` `[patch]` Blind Hunter: the `wave is None` branch of `wave_held_stories` and the `held_story in refused_stories` dedupe never run in the new tests — verified by coverage and by deleting the `continue` (all tests stayed green); added `test_wave_held_stories_is_empty_without_a_wave` and `test_a_wave_that_refuses_its_only_story_reports_held_and_names_it_once`, and re-ran the mutation: the new test now fails.
  - `[low]` `[patch]` Blind Hunter: the Design Notes' mixed-fleet claim (a held station does not stop a campaign another station is working) is untested — added `test_a_held_station_does_not_stop_a_campaign_another_station_is_still_working` for `dispatched` and `in-flight`.
  - `[false]` `[reject]` Blind Hunter: a held `dispatch --stories` run exits 0 and a script cannot tell it from success — Acceptance Criterion 2 requires "its normal verdict"; a WARN never changes the exit, `drain --plan` reports the same state with exit 0, and the held story is in `data.stations[].status` and `data.unresolved`.
  - `[false]` `[reject]` Blind Hunter: the first idle site now yields a silent `held` if `DISPATCH` arrives without a story — `plan_station_queue` constructs `DISPATCH` only with `next_story` set (`core/dispatch_fleet.py`, the `outcome=DISPATCH, next_story=story` return), so the `next_story is None` site cannot see it; the totality test pins every outcome.
  - `[low]` `[reject]` Blind Hunter: a production `assert held_wave is not None` in a never-crash fix — it matches the neighbouring `assert wave is not None` / `assert plan is not None` idiom and is unreachable (serial always dispatches its head; parallel either sets the wave or returns through `live_stories`); a guard would add a branch for a state that cannot occur.
  - `[false]` `[reject]` Blind Hunter: `cycle.deps_graph or {}` could hide the unmet-Deps cause — `plan_station_cycle` sets `deps_graph` in the same `replace()` that sets the wave, so in the empty-wave branch it is never `None`.
  - `[low]` `[patch]` Blind Hunter: stale text — the `unresolved` comment in `execute_fleet_cycle`, the `campaign_complete` docstring, and the playbook line saying "for unmet Deps" while a wave refusal also reads `held` — all three updated.
  - `[low]` `[patch]` Blind Hunter: edits outside the epics.md Surface line with no memlog entry or reconcile — appended a reconcile entry naming every governed path to `spec-pyforge-marshal` and its co-governor `spec-pyforge-core`; `spec-surface-check` and `spec_surface_reconcile.py` exit 0. The epics.md Surface line stays as minted; the memlog entry and the Code Map record the actual files.
  - `[low]` `[patch]` Blind Hunter: `DW-marshal-65-1-3`, the defect's own row, stays open — set `status: resolved` with a `resolution:` line naming this story; `deferred-work-check` exits 0.
  - `[low]` `[patch]` Blind Hunter: shared helpers split across layers and `_held_reason`'s `head` parameter is misleading — renamed the parameter to `story`; the one-line wrapper stays because existing tests pin `drain_plan._held_reason`, and `wave_held_stories` stays in `cli/dispatch.py` because `StationCyclePlan` lives there (moving the dataclass is beyond this fix).
  - `[low]` `[patch]` Blind Hunter: the text-mode report for a held station is untested (`render_cycle_summary` drops `detail`) — added `test_dispatch_stories_on_a_held_wave_says_why_in_text_mode`; the reason is on the WARN finding the text report prints.
  - `[low]` `[reject]` Edge Case Hunter: `held` is terminal, so the campaign ends and the held story is not auto-dispatched once its Dep lands — real, and by design: `BLOCKED` is terminal for the same reason ("marshal cannot fix it by ticking again"), a non-terminal `held` would poll an unbounded campaign for a Dep nothing in it can land, and a rerun picks the story up; a liveness-aware Dep check is beyond a direct correction. Recorded as a residual risk and a judgement call for the operator.
  - `[low]` `[reject]` Edge Case Hunter: backlog stories outside the ready set (73.2 behind a held 73.1) get no finding — `held` is `drain --plan`'s own set (the head plus wave refusals); widening it would diverge from `drain --plan` (Boundary: its output is unchanged) and emit a finding per backlog story, while the head's unmet Deps are the actionable fact.
  - `[low]` `[patch]` Edge Case Hunter: the refused-head empty wave has no test — carried with the first row (same root cause), fixed there.
  - `[false]` `[reject]` Edge Case Hunter: held-with-nothing-launched exits 0 on an explicit `--stories` run — same claim and refutation as the exit-0 row above.
  - `[low]` `[patch]` Edge Case Hunter: governed files change with no owning-spec memlog entry — carried with the surface-reconcile row above, fixed there.
  - `[low]` `[patch]` Verification Gap: an empty wave whose head the wave itself refused is never exercised through `execute_fleet_cycle` (pre-verified, mutation shown) — carried with the first row, fixed there.
  - `[false]` `[reject]` Intent Alignment: a wave-refused story keeps the older refusal-loop wording rather than the new "holds … out" — a refused story has no unmet Deps to name; the existing `MRS-DRAIN-016` names it and its reason once, and the held `detail` carries `drain --plan`'s own wording for it.
  - `[low]` `[patch]` Intent Alignment: the tests exercise `run_dispatch` with the JSON envelope, not the operator's text surface — added the text-mode test (see above); the entrypoint's argparse wiring is unchanged and `run_dispatch` is the handler it reaches.
  - `[low]` `[reject]` Intent Alignment: the intent is silent on whether `held` stops the campaign — carried with the terminal-`held` row above (same decision, same residual risk).
  - `[false]` `[reject]` Intent Alignment: the mutation criterion is only pinned by the table-level test — the cycle-level tests fail with the original `ValueError` when the call site is reverted (run: 2 failed), and the parametrized test pins the table.
  - `[false]` `[reject]` Intent Alignment: "held" could mean unmet Deps only, or also a wave refusal — the diff handles both (Deps-held head and wave-refused head), each with its own test.
