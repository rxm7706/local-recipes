---
title: 'Station-scoped drain and an explicit story sequence (Story 22.11, Epic 22)'
type: 'feature'
created: '2026-08-31'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: medium
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-single-story-dispatch/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-22-7-fleet-wide-drain-is-a-marshal-orchestrated-mode.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-22-10-branch-merged-requires-real-divergence-not-just-ancestry.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** `drain --mode <mode>` (CAP-7) chains automatically — preflight, launch, wait
for merge-through-finalize, launch the next — but only fleet-wide: none of its six flags
(`--mode`, `--leave-remaining`, `--once`, `--max-cycles`, `--tick-seconds`, `--campaign`)
carry a station filter, so it always reads all eight stations' ordered backlogs and
launches one story per station in parallel. `dispatch <slug> <story>` (CAP-1) launches
exactly one story and returns — no chaining at all. There is no way to drain a single
station to zero without touching every other station's backlog, and no way to hand
marshal an explicit ordered list of stories to run, overriding the tracked ledger's own
order, for a one-off targeted push.

**Problem, evidenced live (2026-08-31):** wanted to complete just `pyforge-scribe`'s 2
remaining backlog stories — the fleet's only story with a declared cross-station `Deps:`
link in the entire remaining backlog — without disturbing atlas's or marshal's own
in-flight backlogs. The only paths available were fleet-wide `drain` (wrong scope, would
also fire atlas's and marshal's next stories) or two manual `dispatch` calls with an
operator polling for landing between them, forfeiting `drain`'s
chaining/preflight/campaign-journal machinery for no reason but scope.

**Approach:** extend the dispatch surface, don't fork it. CAP-7's chaining, preflight, and
campaign-journal machinery already does what a station-scoped drain needs; the only
missing dimension is *which stories, on which stations* — handed as an override to the
same per-station ordered-backlog reader (`dispatch_fleet.station_backlog`) CAP-7 already
owns.

1. `drain --mode <mode> --station <slug>` restricts one campaign cycle to exactly one
   station's own tracked backlog — same chaining/preflight/journal, one station instead of
   eight.
2. `dispatch <slug> --stories <key1>,<key2>,...` chains a caller-supplied ordered list
   instead of the ledger's own backlog order, one dispatch at a time (not one agent handed
   the whole list — the epic's "not backlog orchestration" non-goal is unchanged).

## Acceptance Criteria

- Given `drain --mode <mode> --station <slug>`, when a cycle runs, then the campaign's
  chaining/preflight/journal apply to exactly that station's own tracked backlog, and
  every other station's backlog is provably untouched by the same invocation.
- Given `dispatch <slug> --stories <key1>,<key2>,...`, when it runs, then the named
  stories launch in that order via the same chaining `drain` already uses, one dispatch at
  a time.
- Given a `--stories` key that is unknown or already done on that station's tracked
  backlog, when the command runs, then it refuses before any worktree is provisioned —
  the same zombie-refusal discipline fleet-wide `drain` already applies.
- Given either new flag, when a dispatch launches, then it reuses Story 22.2's preflight,
  Story 22.4's landing, and Story 22.10's divergence guard unchanged — no second preflight
  or landing path is introduced.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger
key `22-11-station-scoped-drain-and-an-explicit-story-sequence`. `--station` and
`--stories` change only which stories/order the campaign reads — never a lighter-weight
preflight or landing path (CAP-2/CAP-4/CAP-9 stay exactly as shipped).

**Block If:** A change would build a second preflight, landing, or campaign-journal
implementation instead of reusing CAP-7's own (`dispatch_fleet.station_backlog`,
`run_fleet_drain`'s chaining loop).

**Never:** Handing one dispatched agent a whole backlog or story list to work through in
one session — the unit of dispatch stays exactly one story per launch, chained by marshal
between launches (the epic's own "not backlog orchestration" non-goal, unchanged). A
second branch-name or preflight derivation site.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` —
  `add_factory_drain_subparser` (new `--station` argument), `add_factory_dispatch_subparser`
  (new `--stories` argument), `run_fleet_drain` (station-scoping the backlog read),
  `dispatch_fleet.station_backlog` (the existing per-station ordered-backlog reader both
  new flags key off).
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch.py` /
  `test_dispatch_fleet.py` — new coverage: `--station` touches only the named station's
  backlog; `--stories` chains in the given order; an unknown/already-done key refuses
  before any worktree provisioning.

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are
violated (station-scope isolation, sequence ordering, pre-launch key validation, no
second preflight/landing path). Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 22.11 and `spec-marshal-single-story-dispatch` CAP-10. Both new
flags are pure read-scope/read-order changes over the same `station_backlog` reader CAP-7
already calls — no new campaign-journal shape, no new preflight function, no new landing
path. `--stories` validates every key against the station's *tracked* backlog (the same
source `station_backlog` reads) before launching anything, matching `drain`'s own
zombie-refusal discipline rather than a partial run that fails mid-sequence.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, including this story's own new/updated test coverage.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (no undeclared dependency surface).

## Spec Change Log

- 2026-08-31: drafted from `spec-marshal-single-story-dispatch` CAP-10 (minted the same day
  from a live incident — draining just `pyforge-scribe`'s 2 remaining stories had no CLI
  primitive that didn't also touch every other station's backlog).
