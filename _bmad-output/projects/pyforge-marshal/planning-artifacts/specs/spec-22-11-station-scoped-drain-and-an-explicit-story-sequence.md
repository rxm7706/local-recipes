---
title: 'Station-scoped drain and an explicit story sequence (Story 22.11, Epic 22)'
type: 'feature'
created: '2026-08-31'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
difficulty: medium
baseline_revision: '1cc4a049063832c4c0368fedc63b1fdac3fdebb3'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-single-story-dispatch/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-22-7-fleet-wide-drain-is-a-marshal-orchestrated-mode.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-22-10-branch-merged-requires-real-divergence-not-just-ancestry.md
warnings: []
deferred:
  - summary: >-
      A station-scoped/sequenced campaign's scope is not persisted anywhere,
      so a manual `--campaign <id>` resume that omits `--station`/`--stories`
      silently widens the resumed cycle back to a full fleet-wide,
      ledger-order drain under the same run id and journal.
    evidence: |-
      `station`/`explicit_stories` are pure per-invocation CLI-argument
      inputs into `run_fleet_drain` -- nothing in `_journal_fleet_cycle`
      records that a given run id was scoped. The automated campaign
      supervisor always re-supplies both flags correctly (tested), so the
      risk is confined to a human manually typing `--campaign <id>` alone to
      inspect/recover a stalled campaign. The most likely trigger (the
      MRS-DRAIN-007 supervisor-spawn-failure recovery message) was patched
      in this review pass to always include `--station`/`--stories` when
      set, which closes the documented recovery path; an UNDOCUMENTED manual
      resume can still hit this. A full fix (persist scope into the run
      directory and read it back on resume) is a bigger design lift than a
      mechanical patch.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py:run_fleet_drain
    severity: medium
  - summary: >-
      `FleetCycleReport.complete` is vacuously `True` (`all()` over an empty
      `results` tuple) on the new `MRS-DRAIN-013` unknown-station early
      return, so the JSON envelope reports `"complete": true` alongside an
      ERROR finding for an outright refusal where nothing ran.
    evidence: |-
      Confirmed by reading `dispatch_fleet.campaign_complete` (`all(...)`
      over an empty iterable) and `FleetCycleReport.complete`'s delegation
      to it; `data["complete"] = report.complete` bakes this into the
      emitted JSON. This is NOT a regression introduced by this story: the
      pre-existing `MRS-DRAIN-012` ("no pyforge stations found") early
      return has the identical vacuous-truth shape and the file's own
      comment there already acknowledges it, relying on the accompanying
      ERROR finding (not `complete`) to signal the problem to callers. A
      caller/orchestrator that polls `data.complete` without also checking
      `findings` could still be misled. Fixing this properly means auditing
      every early-return `FleetCycleReport` construction fleet-wide, which
      is broader than this story's `--station`/`--stories` surface.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py:campaign_complete
    severity: medium
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
  `add_factory_drain_subparser` (new `--station`/`--stories` arguments),
  `add_factory_dispatch_subparser` (`story` positional made optional, new `--stories`
  argument), `run_dispatch` (routes `--stories` into `run_fleet_drain` as a synthetic
  `drain_to_zero` invocation), `execute_fleet_cycle` (new `station`/`explicit_stories`
  params; station-scoping + backlog-source override), `_spawn_campaign_supervisor` (threads
  `station`/`stories` into the detached supervisor's argv), `run_fleet_drain`
  (`--station`/`--stories` parsing, pre-launch key validation on a fresh campaign, the
  MRS-DRAIN-007 recovery message).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py` — three
  new pure functions: `parse_story_sequence`, `unresolved_story_sequence_keys`,
  `explicit_story_backlog` (the caller-ordered, not-yet-`done` effective backlog for a
  `--stories` campaign — deliberately not `apply_order_override`'s reorder-then-append-tail
  shape).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` /
  `core/verdict.py` — four new codes (`MRS-DISP-032`, `MRS-DRAIN-013/014/015`), registered
  and classified.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_fleet_supervisor/__main__.py`
  — `build_cycle_argv` / `run_fleet_campaign_supervisor` / `main` thread `station`/`stories`
  through every supervised re-tick.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch.py` /
  `test_dispatch_fleet.py` / `test_findings.py` — new coverage: `--station` touches only the
  named station's backlog (a `FakeHarness.read_slugs` audit trail proves it); `--stories`
  chains in the given order across cycles; an unknown/already-done key refuses before any
  worktree provisioning; the supervisor argv carries both flags on re-invocation.

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

## Implementation record — 2026-08-31

**Shape as built.** `--station` (accepts either `scribe` or `pyforge-scribe`) and `--stories`
land on `drain`'s own `argparse` parser — `dispatch <slug> --stories k1,k2,...` is a thin
translation layer (`run_dispatch`) that builds a synthetic `drain_to_zero` `Namespace` (with
`station=<slug>`, `stories=<raw comma string>`) and calls `run_fleet_drain` directly, so both
surfaces share one campaign implementation end to end (argparse validation, preflight,
journal, and the detached campaign supervisor). `execute_fleet_cycle` gained `station` (filters
`slugs` to exactly one — or refuses `MRS-DRAIN-013` if unknown — before any station's ledger is
even read, so every other station is provably untouched) and `explicit_stories` (when set, the
per-station backlog for that cycle is `dispatch_fleet.explicit_story_backlog` — the caller's
own ordered list re-filtered to not-yet-`done` every cycle — instead of
`station_backlog`/`order_override`, which reorders the full ledger and appends the untouched
tail). `run_fleet_drain` validates every `--stories` key against the station's tracked backlog
via the new `dispatch_fleet.unresolved_story_sequence_keys` ONLY on a fresh campaign's first
cycle (gated on `raw_campaign is None`, before `run_id`/`run_dir` are minted) — never on a
resumed/supervised tick, since a key legitimately flipping to `done` mid-campaign must not be
misread as invalid. The detached campaign supervisor (`dispatch_fleet_supervisor`) now threads
`station`/`stories` through `build_cycle_argv`/`_spawn_campaign_supervisor` so every re-tick
stays scoped/sequenced — the one thing that would otherwise silently widen a station-scoped or
explicit-sequence campaign back to fleet-wide/ledger-order on its very first re-tick.

Three new pure helpers landed in `core/dispatch_fleet.py`: `parse_story_sequence` (splits
`--stories`' comma list, drops blanks), `unresolved_story_sequence_keys` (normalized-identity
membership check against the tracked backlog — a malformed/unknown/already-`done` key is
"unresolved"), and `explicit_story_backlog` (the caller's own sequence, filtered to
not-yet-`done` every cycle — deliberately NOT `apply_order_override`'s reorder-then-append-tail
shape). Four new finding codes, each registered in `core/findings.py` AND classified in
`core/verdict.py`'s `_CLASSIFY_TABLE` (a `Finding` carrying `severity=ERROR` whose code
classifies to an "ok" verdict crashes `Envelope.__post_init__` — confirmed the hard way against
`test_registered_codes_contains_the_real_codes`' hand-mirrored literal set, which also needed
the same four codes): `MRS-DISP-032` (dispatch's story/`--stories` usage validation — neither/
both given, or an unresolved key), `MRS-DRAIN-013` (unknown `--station`), `MRS-DRAIN-014`
(`--stories` without `--station`), `MRS-DRAIN-015` (tracked ledger unreadable while validating
a fresh `--stories` sequence — deliberately a NEW code rather than reusing `MRS-DRAIN-003`,
whose classification is `WARN`/"ok" and would have crashed the envelope the same way).

**No second preflight/landing/campaign-journal path**: both new flags are pure read-scope/
read-order inputs into the SAME `execute_fleet_cycle` → `dispatch_once` →
`station_in_flight_conflict` (CAP-2/CAP-5) → `dispatch_land_finalize` (CAP-4, merge-in-agent) →
`gather_dispatch_git_facts` (CAP-9's divergence guard) chain Story 22.7 already built; nothing
in this diff touches those functions' own bodies.

**Verification performed:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` → 6555 passed, 12 deselected
  (network-opt-in, pre-existing pattern) — includes 17 new tests in `test_dispatch_fleet.py`
  (pure-function coverage for the three new helpers, per-station isolation via a
  `FakeHarness.read_slugs` audit trail, unknown-station/unresolved-key/missing-station
  refusals, a full multi-cycle chained-sequence replay proving order beats ledger order, and
  the campaign-supervisor argv-threading regression) and 4 new tests in `test_dispatch.py`
  (the `dispatch` verb's usage validation and delegation).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` → 118 passed, 1 skipped.
- `pixi run -e pyforge-marshal pytest tests/meta -q` → 1849 passed (no regression against the
  AD-7 verdict sole-ownership guard, the AD-15 finding-registry conventions, or any other
  structural guard).
- Live CLI smoke tests against the real `python -m pyforge.marshal.cli.main` entrypoint (not
  just hand-built `argparse.Namespace` fixtures): `factory drain --help` / `factory dispatch
  --help` render the new flags with their help text; `factory drain --mode drain_to_zero
  --stories a,b` (no `--station`) refuses `MRS-DRAIN-014`; `factory dispatch pyforge-marshal`
  (neither `story` nor `--stories`) and `factory dispatch pyforge-marshal 22-1-foo --stories
  a,b` (both) each refuse `MRS-DISP-032` with the right message variant.

**Residual risks / left incomplete:** None identified against this story's own Acceptance
Criteria. Landing (git commit beyond this session's working tree, ledger key
`22-11-station-scoped-drain-and-an-explicit-story-sequence` flip, and this file's own `status`
flip to `done`) is the dispatcher's, per the documented convention (Story 22.10's own review
finding: never let this file, `epics.md`, and the tracked ledger disagree on completion state
in the same uncommitted change) — `status` stays `in-review` here rather than jumping to
`done`.

## Spec Change Log

- 2026-08-31: drafted from `spec-marshal-single-story-dispatch` CAP-10 (minted the same day
  from a live incident — draining just `pyforge-scribe`'s 2 remaining stories had no CLI
  primitive that didn't also touch every other station's backlog).
- 2026-08-31: implemented (see Implementation record above); `status` moved to `in-review`
  pending the dispatcher's own landing pass.

## Review Triage Log

### 2026-08-31 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 8 (high 0, medium 4, low 4)
- defer: 2 (high 0, medium 2, low 0)
- reject: 6 (high 0, medium 1, low 5)
- addressed_findings:
  - `medium` `patch` Unknown `--station` combined with `--stories` on a fresh campaign read
    the ledger before checking station liveness, surfacing the confusing `MRS-DRAIN-015`
    ("cannot read the tracked ledger") instead of the actionable `MRS-DRAIN-013` ("unknown
    station... not among the live pyforge stations"). Reordered `run_fleet_drain`'s
    pre-validation to check station membership first (`dispatch.py`); live-verified.
  - `low` `patch` `MRS-DRAIN-015` (ledger unreadable for a known station) had no test.
    Added `test_stories_with_known_station_unreadable_ledger_refuses_mrs_drain_015`
    alongside a sibling test for the corrected `MRS-DRAIN-013` ordering above.
  - `medium` `patch` The `MRS-DRAIN-007` campaign-supervisor-spawn-failure recovery message
    told the operator to re-run `factory drain --mode <mode> --campaign <run_id>` without
    ever mentioning `--station`/`--stories` — following it literally on a scoped campaign
    would have silently widened the resumed cycle back to fleet-wide/ledger-order. The
    message now includes both flags when the cycle carried them (`dispatch.py`).
  - `low` `patch` `execute_fleet_cycle` relied only on its docstring, not code, for the
    invariant "`explicit_stories` requires `station`". Added an explicit `ValueError` guard
    plus `test_execute_fleet_cycle_rejects_explicit_stories_without_station`.
  - `low` `patch` The spec's own Code Map (this file) omitted the three new
    `core/dispatch_fleet.py` helpers, the `core/findings.py`/`core/verdict.py` registrations,
    and the `dispatch_fleet_supervisor/__main__.py` argv-threading — updated to match the
    real diff.
  - `low` `patch` `factory dispatch --help`'s top-level description never mentioned the
    `--stories` chaining mode, describing the command purely in singular-dispatch terms.
    Extended the description text; live-verified via `--help`.
  - `medium` `patch` No test drove the REAL `run_fleet_drain` → `_spawn_campaign_supervisor`
    call path to confirm `stories=explicit_stories` actually reaches the spawned supervisor
    subprocess's argv (the existing tests only checked the pure `build_cycle_argv` function
    in isolation, or a `--station`-only campaign). Added
    `test_stories_supervisor_reinvocation_via_run_fleet_drain_carries_stories` — in the
    process, confirmed the supervisor's own CLI is positional (station/stories appear as
    bare trailing args, not `--station`/`--stories` flags), so the test asserts the correct
    shape rather than the initially-assumed flagged one.
  - `medium` `patch` A `--campaign` id that never actually ran (an operator hand-typing an
    unused id together with `--stories`) bypassed the unknown/already-done-key pre-launch
    check, since the check was gated purely on `raw_campaign is None` rather than on whether
    the campaign actually exists — a literal violation of AC3's unconditional refusal
    promise under this narrow misuse. `run_fleet_drain` now treats `--campaign` as a genuine
    resume only when its run directory exists on disk (`fs.is_dir`), otherwise validating it
    like any fresh campaign. Added
    `test_stale_campaign_id_with_stories_still_validates_unresolved_keys`.

**Deferred (see frontmatter `deferred` list for full detail):** (1) campaign scope
(`--station`/`--stories`) is not persisted in the run directory, so an UNDOCUMENTED manual
`--campaign`-only resume (distinct from the now-patched `MRS-DRAIN-007` message) could still
silently widen scope — a bigger design lift than a mechanical patch; (2)
`FleetCycleReport.complete` is vacuously `True` on the new `MRS-DRAIN-013` early return,
mirroring a pre-existing `MRS-DRAIN-012` pattern this story did not introduce and whose
proper fix spans every early-return `FleetCycleReport` construction fleet-wide, not just this
story's surface.

**Rejected (noise — no action taken):** `dispatch --stories` skips the plain path's
`MRS-DISP-001` slug-format check (still safely refused via `MRS-DRAIN-013` downstream, just a
different code); `MRS-DISP-032` is raised from inside `run_fleet_drain` despite its
`MRS-DISP-`-prefixed name (by design — `dispatch --stories` is the user-facing surface that
surfaces these validations, even though `run_fleet_drain` is the shared implementation); the
fresh-`--stories`-campaign ledger read happening twice (pre-validation, then again inside
`execute_fleet_cycle`) is harmless, lock-protected redundancy; `--stories` accepting duplicate
keys is harmless and self-corrects (`explicit_story_backlog` drops a key once it lands `done`);
an empty-string `--stories` producing the "neither given" message is a rare self-inflicted
edge case whose message still points the operator at valid input; scheduling isolation
(concurrent campaigns across stations) is explicitly out of scope per the intent-contract's
own Boundaries & Constraints, which bar building a second campaign-journal/locking
implementation — the existing single fleet-wide lock is intentionally reused unchanged.

## Auto Run Result

**Summary:** Implemented Story 22.11 in full: `drain --mode <mode> --station <slug>`
restricts one campaign cycle to exactly one station's own tracked backlog (every other
station's ledger provably unread); `dispatch <slug> --stories k1,k2,...` chains a
caller-supplied ordered sequence on one station via the same `run_fleet_drain` machinery,
one dispatch at a time, refusing before any worktree is provisioned when a key is unknown
or already done. Both flags are pure read-scope/read-order overrides on CAP-7's existing
chaining/preflight/journal/campaign-supervisor implementation — no second implementation of
any of those was introduced. A subsequent adversarial review pass (4 parallel reviewers:
blind hunter, edge-case hunter, verification-gap, intent-alignment) found and fixed 8
real defects/gaps, deferred 2 narrower pre-existing/design-scope issues, and rejected 6 as
noise, out-of-scope, or self-correcting.

**Files changed** (final, including the review-pass patch):
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` — `--station`/
  `--stories` CLI surface, `run_dispatch`'s `--stories` translation into `run_fleet_drain`,
  `execute_fleet_cycle`'s station-scoping + backlog-source override (+ a new defensive
  guard), `_spawn_campaign_supervisor`'s argv threading, `run_fleet_drain`'s pre-launch
  validation (patched: station-liveness checked before the ledger read; a `--campaign` id
  is trusted as a resume only when its run directory actually exists), and the
  `MRS-DRAIN-007` recovery message (patched to include `--station`/`--stories`).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py` — three
  new pure functions (`parse_story_sequence`, `unresolved_story_sequence_keys`,
  `explicit_story_backlog`).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` /
  `core/verdict.py` — four new registered/classified codes (`MRS-DISP-032`,
  `MRS-DRAIN-013/014/015`).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_fleet_supervisor/__main__.py`
  — `station`/`stories` threaded through every supervised re-tick.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch.py` /
  `test_dispatch_fleet.py` / `test_findings.py` — original story coverage (21 tests) plus
  5 review-pass tests (unknown-station-with-stories ordering, `MRS-DRAIN-015` reachability,
  the `execute_fleet_cycle` guard, the real supervisor-argv threading, and the stale
  `--campaign`-id case).
- This spec file — Code Map corrected to match the real diff; `deferred` frontmatter list
  added; Review Triage Log appended.

**Review findings breakdown:** 8 patched (0 high, 4 medium, 4 low) — all applied and
re-verified; 2 deferred (both medium — recorded in frontmatter `deferred`); 6 rejected as
noise/out-of-scope/self-correcting (see Review Triage Log for detail on every finding).

**Follow-up review recommendation:** `true` (3 × medium(4) + 1 × low(4) = 16 ≥ 5, computed
over this pass's 8 patched findings only — 0 high, 4 medium, 4 low).

**Verification performed:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` → 6560 passed, 12 deselected
  (26 new tests total across the implementation and review passes).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` → 118 passed, 1 skipped.
- Live CLI smoke tests re-run post-patch: `factory dispatch --help` / `factory drain --help`
  render the updated description/flag text; `factory drain --mode drain_to_zero --station
  pyforge-totally-fake --stories 1-1-a,1-2-b --format json` now correctly returns
  `MRS-DRAIN-013` (unknown station, naming the live ones) instead of the pre-patch
  `MRS-DRAIN-015`.

**Residual risks:** The two deferred findings (frontmatter `deferred` list) — an
undocumented manual `--campaign`-only resume could still widen a station-scoped campaign's
effective scope beyond what the now-patched `MRS-DRAIN-007` message covers; and
`FleetCycleReport.complete` stays vacuously `True` on early-refusal returns with empty
`results`, a pre-existing pattern this story did not introduce. Neither blocks this story's
own Acceptance Criteria.
