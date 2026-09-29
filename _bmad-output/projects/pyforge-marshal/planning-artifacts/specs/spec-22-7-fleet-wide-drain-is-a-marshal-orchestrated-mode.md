---
title: 'Story 22.7: Fleet-wide drain is a marshal-orchestrated mode'
type: feature
created: '2026-08-27'
status: done
updated: '2026-08-27'
baseline_revision: fecee52191fd42d6554e1cf012615d61e2ef3188
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-single-story-dispatch/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-single-story-dispatch/fleet-drain-playbook.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The eight-station fleet-drain campaign (2026-08-22/23) that landed dozens of
stories exists only as `.cursor/pyforge-fleet-drain/` — a session-local, hand-driven
coordinator (`COORDINATOR.md`'s singleton STATUS.md lock, `PLAN.md`'s Phase 0-5 hand ritual,
`SEQUENCING.md`'s one-off wave ordering, `queues.yaml`/`generate-queues.py`'s ledger-derived
backlog). It is manual, non-marshal, and is the one capability
(`spec-marshal-single-story-dispatch` CAP-7) the 2026-08-21 decomposition of Epic 22 left
uncovered while CAP-1..CAP-6 shipped as marshal verbs.

**Approach:** Add a fleet-wide drain mode to `marshal factory dispatch` (verb naming
provisional per PRD Q-15: `marshal factory dispatch --fleet` or `marshal drain`) that reads
each of the eight pyforge stations' ordered backlog from its tracked
`sprint-status-ledger.yaml` (plus optional order overrides — the in-repo analog of
`queues.yaml`'s `order_overrides`), applies a campaign policy (`drain_to_zero`, `leave_one`,
`skip_on_blocked`), and for each cycle: preflights every station's next queued story through
CAP-2's zombie-refusal facts, launches one story per station in parallel by composing
`run_dispatch` under CAP-5's per-station in-flight guard (never duplicating
`station_in_flight_conflict`), and — when a launched story's merge-through-finalize completes
(CAP-4: merge on CI green, scoped `sprint-ledger-sync --project <station>`, spec promotion) —
chains that station's next backlog story. Deps: 22.1, 22.2, 22.4, 22.5 (all done).

## Acceptance Criteria

Lifted verbatim from `epics.md` Story 22.7 (the epic's exact Given/When/Then):

- Given the eight pyforge stations with per-station ordered backlogs (tracked ledgers +
  optional overrides) when the operator runs the one documented fleet-drain command then
  marshal applies the campaign mode (`drain_to_zero`, `leave_one`, `skip_on_blocked`
  policies), preflights each dispatch (S-22.2's zombie refusal), launches one story per
  station in parallel (S-22.5's per-station guard and untouched FR-184 clamp posture), and
  chains each station's next story when merge-through-finalize completes (S-22.4 with
  merge-in-agent: merge when CI green, scoped `sprint-ledger-sync --project <station>`, spec
  promotion, queue regen) — the eight-station 2026-08-22/23 hand ritual replays without
  session discipline.

Decomposed for traceability (same contract, restated as discrete checks):

- The command reads all eight stations' ordered backlog from tracked
  `sprint-status-ledger.yaml` files (+ optional order overrides), never from
  `.cursor/pyforge-fleet-drain/queues.yaml`.
- Campaign mode is one of `drain_to_zero` / `leave_one` / `skip_on_blocked` and is applied,
  not ignored.
- Every dispatch this mode issues is preflighted through CAP-2's zombie/liveness facts before
  launch.
- One story in flight per station; stations dispatch in parallel; FR-184's in-loop
  `max_parallel` clamp is untouched.
- Merge-through-finalize (CAP-4: CI-green merge, scoped `sprint-ledger-sync --project
  <station>`, spec promotion, queue-state regen) triggers the next queued story for that
  station.
- Replaying the eight-station 2026-08-22/23 campaign through this mode produces the same
  landed-story outcomes the hand ritual produced, without an operator maintaining session
  discipline.

## Boundaries & Constraints

**Always:**
- Compose over the already-shipped dispatch primitives — `run_dispatch`
  (`cli/dispatch.py`), `station_in_flight_conflict` (CAP-5), and
  `cross_station_surface_overlap_advisories` (CAP-5) — never duplicate Story 22.5's
  in-flight or overlap logic inside the fleet mode.
- Compose over CAP-4's landing/finalize primitives (`core/dispatch_landing.py`,
  Story 4.1/Epic 15 promotion, `sprint-ledger-sync --project <station>`) — zero new
  landing or promotion code paths.
- Store campaign/queue state in-repo under `pyforge-marshal` (journal + tracked ledgers),
  never session-local `.cursor/` state — this is the Spec's named Success-signal
  subsumption target.
- `BMAD_ACTIVE_PROJECT=pyforge-<station>` per dispatched session with physical artifact
  paths; never `scripts/bmad-switch` (standing HARD rule, CLAUDE.md).
- Ledger key for this story: `22-7-fleet-wide-drain-is-a-marshal-orchestrated-mode`.

**Never:**
- Dispatch onto a station that already has a live in-flight story (CAP-5's
  `MRS-DISP-011`/`MRS-DISP-021` refusal codes apply unchanged inside fleet mode).
- Modify FR-184's in-loop `max_parallel` clamp — the fleet mode's concurrency lives only on
  the cross-project plane (`spec-horizontal-run-concurrency`).
- Reimplement CAP-2's git/process completion-judgment logic, CAP-3's verification gate, or
  CAP-4's landing logic inside the fleet driver.
- Silently force a blocked/failed station past `skip_on_blocked` — a HALTed or blocked
  station's story stays in backlog, is reported to the operator by name, and is never
  auto-retried or force-continued.
- Leave `.cursor/pyforge-fleet-drain/` as the only implementation of this capability — this
  story ships the marshal-native mode that supersedes it.

## I/O & Edge-Case Matrix

| Input / Scenario | Expected Behavior |
|---|---|
| A station's tracked ledger has zero non-`done` story keys | Station reported `drained`; fleet mode skips it, no dispatch attempted |
| All eight stations already have a live in-flight story (CAP-2 facts) | Every station's dispatch this cycle is refused, naming each in-flight story (CAP-5 `MRS-DISP-021`); no redispatch attempted |
| A queued story's dispatch is refused as a zombie redispatch | CAP-2's `MRS-DISP-011` applies unchanged; story is not retried this cycle |
| A station's next story HALTs / is blocked mid-drain | `skip_on_blocked` policy: skip to that station's next queued story, report the skip and reason to the operator, leave the blocked story in backlog |
| A queued story has no tracked spec under `planning-artifacts/specs/` | Preflight refuses that dispatch naming `MRS-DISP-005` (existing CAP-1 behavior); fleet mode does not auto-draft specs — spec authoring is out of scope for this verb |
| A dispatched story's merge-through-finalize completes (CI green) | CAP-4 composition runs (merge, scoped `sprint-ledger-sync --project <station>`, spec promotion, queue-state regen), then that station's next backlog story is dispatched (`drain_to_zero`) or the campaign stops at the configured `leave_remaining` (`leave_one`) |
| Two different stations both have a story ready to dispatch | Both dispatch concurrently (CAP-5 cross-station parallel permitted); FR-184 untouched |
| Overlapping declared frozen surfaces between two concurrently in-flight stations | Loud advisory only (CAP-5 `MRS-DISP-022`), dispatch is never blocked by it |
| Campaign mode argument is missing or not one of the three named modes | Refuse loudly naming the invalid/missing mode; never silently default to `drain_to_zero` |
| Every station's tracked ledger shows zero non-`done` keys | Fleet mode reports the campaign complete and exits cleanly; no dispatch attempted |

</intent-contract>

## Code Map

**Composes (never duplicates):**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py::run_dispatch`
  (line 525) — the single-story dispatch primitive the fleet mode calls once per station per
  cycle; owns spec resolution, policy composition, worktree provisioning, and the CAP-5
  preflight this story must reuse rather than re-check.
- `cli/dispatch.py::station_in_flight_conflict` (line 373) — CAP-5's one-per-station guard;
  `run_dispatch` already calls this at line 624, so the fleet driver inherits it for free by
  calling `run_dispatch` rather than reimplementing the check.
- `cli/dispatch.py::cross_station_surface_overlap_advisories` (line 430) — CAP-5's loud
  cross-station overlap advisory, likewise inherited through `run_dispatch`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py::list_station_slugs`
  (line 173) — the existing eight-station enumeration primitive; this is the marshal-native
  replacement for the hardcoded `STATIONS` tuple in
  `.cursor/pyforge-fleet-drain/generate-queues.py` (lines 26-35).
- `core/dispatch.py::resolve_story_spec_path` / `story_spec_candidates` (lines 87-105) — the
  spec-lookup `run_dispatch` already uses (line 590) to surface `MRS-DISP-005`; the fleet
  mode's per-station backlog walk reuses this, it does not re-derive spec presence itself.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_landing.py`
  (`may_attempt_dispatch_landing`, `refuse_unverified_landing`,
  `merge_subject_is_marshal_native`) — CAP-4's landing primitives; the "chain when
  merge-through-finalize completes" step composes over these, never a parallel landing path.
- `core/status.py::build_fleet_row` (line 1068) / `_apply_dispatch_overlay` (line 995) —
  existing per-station dispatch-overlay status facts (`marshal status` / `fleet-picture`);
  the fleet   mode's per-station backlog/in-flight read should be groundable in the same
  journal + git/process facts these already assemble, not a second status path.

**2026-09-01 hotfix extensions (SCP `sprint-change-proposal-2026-09-01-dispatch-autonomy-hotfixes.md`):**
- `core/dispatch_retry.py` — transient vs terminal block for `MRS-DRAIN-005`; campaign
  blocked-map reconciliation via `prune_blocked_stories_merged_on_main`.
- `cli/dispatch.py` — `--harness` override; `--stories` spec preflight batch.
- `dispatch_fleet_supervisor` — forwards `--harness` on supervised ticks.

**Supersedes (the interim runner this story replaces — read to know what to absorb, not
reimplement):**
- `.cursor/pyforge-fleet-drain/COORDINATOR.md` — hand-maintained singleton-lock discipline
  (a `STATUS.md` owner/state table an operator reads before every launch); this story makes
  "one coordinator" structural (the marshal process itself owns sequencing), not a documented
  convention a human must remember to honor.
- `.cursor/pyforge-fleet-drain/PLAN.md` — the Phase 0-5 hand ritual (preflight, spec
  readiness, launch, merge+finalize, chain-next-story) this story's fleet-drain mode
  productizes end to end.
- `.cursor/pyforge-fleet-drain/SEQUENCING.md` — one campaign's hand-authored wave/unlock
  ordering; the marshal-native mode's "optional overrides" on top of ledger order is the
  general form of this one-off file.
- `.cursor/pyforge-fleet-drain/queues.yaml` + `generate-queues.py` — the per-station ordered
  backlog + skip-policy state this story moves in-repo under `pyforge-marshal` (journal +
  tracked ledgers), never regenerated as session-local `.cursor/` YAML.
- `.cursor/pyforge-fleet-drain/STATUS.md` — the hand-maintained coordinator-lock and
  in-flight snapshot; superseded by `marshal status` / journal facts, which CAP-1/CAP-2/CAP-6
  already produce.

**Acceptance oracle (interim, until this story ships):**
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-single-story-dispatch/fleet-drain-playbook.md`
  — validated 2026-08-22/23; its "What marshal must productize" table maps each playbook
  phase to the Epic 22 story that productizes it, with CAP-7 (this story) mapped to the
  `--fleet` / `drain` queue-and-modes row.

## Verification

- `pixi run -e pyforge-marshal pyforge-marshal-test` green
- Fleet-drain fixture(s) replaying the eight-station 2026-08-22/23 campaign's outcomes
  (skip/HALT/parallel/chain scenarios from the I/O & Edge-Case Matrix above) against the new
  mode, per `fleet-drain-playbook.md`'s acceptance-oracle role.

## Dispatcher verification — 2026-08-27

Session's review pass was interrupted by the account spend limit (twice); the dispatcher
completed verification independently per Story 22.3: full `pyforge-marshal-test` in this
worktree = 6491 passed / 1 failed, the failure being the pre-existing
`test_skf_domain_skill::test_context_files_not_hand_edited` red on origin/main itself
(outside this story's surface); scoped drain/dispatch subset 203/203. Landed by the
dispatcher, marshal-native.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `741603efd8` (2026-08-27, "docs(marshal): 22.7 spec done + ledger -- dispatcher verification (review interrupted by spend limit)"); also `02d7f0bb1e` (2026-08-27, "feat(marshal): fleet-wide drain is a marshal-orchestrated mode (Story 22.7)"); also `5569f79b90` (2026-08-27, "docs(marshal): mint story 22.9 -- dispatch branch names its station (cross-station worktre"). Ledger row `22-7-fleet-wide-drain-is-a-marshal-orchestrated-mode: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-22-7-fleet-wide-drain-is-a-marshal-orchestrated-mode.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
