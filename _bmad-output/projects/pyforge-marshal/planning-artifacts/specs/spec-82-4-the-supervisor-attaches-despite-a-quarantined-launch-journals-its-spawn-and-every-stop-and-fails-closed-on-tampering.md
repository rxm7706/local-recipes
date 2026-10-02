---
title: '82.4: The supervisor attaches despite a quarantined launch, journals its spawn and every stop, and fails closed on tampering'
type: 'fix'
created: '2026-10-02'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The supervisor's journal can read healthy while a live run goes unsupervised. Re-verified at HEAD a7cdb91fe4:

- `supervisor/__main__.py::run_supervisor` (`:754`) decides attach-or-inert from one `fold` (`:916`): `started_by_marshal`
  (`:928-932`) looks for a launch or resume entry in `fold_result.by_kind`. A quarantined `run-launch` line never appears
  there, so a run Marshal did start reads as "not ours" and the supervisor returns 0 inert (`:933-967`), with one stderr
  line and no journal write (DW-FU-3-4-3; `tests/unit/test_supervisor.py:5200` pins exactly this).
- No `signal` handler exists anywhere in the package. `supervisor-detach` is written only when the tick loop ends
  (`:2625-2629`), so SIGTERM, SIGHUP or an operator's `pkill` leave an open `supervisor-attach` that reads like a healthy
  supervisor (DW-FU-3-4-6).
- `cli/spin.py::_spawn_supervisor_sidecar` (`:1102`, called from launch at `:1831` and resume at `:2400`) spawns the
  sidecar at `:1280` and reports the outcome only as `data["supervisor_pid"]` (`:1332`) or an `MRS-SPIN-007` (`:1306`); the
  run journal never records that supervision was attempted, succeeded or failed (DW-FU-3-4-7). `_writer_id`'s docstring
  (`:855-863`) pins "never appends a third entry".
- The agent session can write the run's `journal.jsonl` through the Tier-3 backlink. Making it unwritable or replacing it
  sends every later append into the `(FsError, ValueError)` branch (`:2649-2667`), which prints one stderr line and returns
  1, leaving the live run unsupervised with a journal byte-identical to a healthy one mid-tick (DW-FU-3-4-8).

**Approach:**

- When `fold` finds no launch or resume entry but quarantined at least one line, the supervisor attaches and supervises;
  its `supervisor-attach` carries the quarantine count and a new MRS-SUPV WARN saying ownership could not be proven from the
  journal. A journal with neither a launch entry nor a quarantined line stays inert, as today.
- SIGTERM, SIGHUP and SIGINT handlers journal `supervisor-detach` with a reason naming the signal, then exit. SIGKILL and a
  host crash stay detectable by heartbeat absence, as the module docstring already says.
- `_spawn_supervisor_sidecar` journals one observation per spawn, the sidecar's pid or the spawn error, for launch and
  resume alike; `_writer_id`'s docstring is corrected.
- The supervisor opens the journal once for appending at attach and writes every later entry through that descriptor
  (an `FsPort` handle; `LocalFs` implements it). Each tick it compares the path's identity and size with what it last
  wrote. A replaced, truncated or removed journal, or an append that fails, makes it stop the watched run through
  `HarnessPort.stop` and record why on its own log and, when the held descriptor still accepts it, in a final
  `supervisor-detach`. With no harness run id to stop against it keeps watching and reports that it cannot act, the
  `MRS-SUPV-003` / `MRS-SUPV-005` precedent, rather than exiting.

Ledger key: `82-4-the-supervisor-attaches-despite-a-quarantined-launch-journals-its-spawn-and-every-stop-and-fails-closed-on-tampering`.
Type / Effort / Deps: fix / L / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-2 (a run is watched from outside by something the session cannot disable) with Story 3.4
  (FR-11; NFR-4, NFR-5; AD-9, AD-20). Defects of shipped behaviour, so no new CAP; no flag.

## Acceptance Criteria

- Given a run directory whose only `run-launch` line is unparseable and whose watched pid is alive When the supervisor starts Then it journals a `supervisor-attach` carrying the quarantine count and an MRS-SUPV WARN, and keeps heartbeating
- Given a journal with no launch entry and no quarantined line When the supervisor starts Then it stays inert with no journal write, as today
- Given a running supervisor When it receives SIGTERM, SIGHUP or SIGINT Then its last journal entry is a `supervisor-detach` whose reason names the signal
- Given `marshal factory spin` or `resume` When the sidecar spawn succeeds or raises Then the run journal holds one entry recording the sidecar pid or the error
- Given a supervised run When the journal is replaced, truncated, or made read-only between ticks Then the supervisor stops the watched run through `HarnessPort.stop` and records why, and never exits leaving the run alive and unwatched
- Given each fix removed in turn When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** The journal stays the supervisor's only durable write target besides its own log. Every new reason and code is
registered in `core/findings.py` and `core/verdict.py`. Close DW-FU-3-4-3, DW-FU-3-4-6, DW-FU-3-4-7 and DW-FU-3-4-8 in
`deferred-work-ledger.md` when the story lands (status `closed`, a `resolved:` line naming this story).

**Never:** Do not run the supervisor under a different uid or add IPC; AD-9's import and IPC bans stay. Do not attach to a
journal that proves the run is someone else's. Do not change the idle ladder or the budget ceilings (Story 82.5's surface).

</intent-contract>

## Binding

Parent: Story 3.4, `spec-pyforge-marshal` CAP-2; a defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 entry.
Ledger key: `82-4-the-supervisor-attaches-despite-a-quarantined-launch-journals-its-spawn-and-every-stop-and-fails-closed-on-tampering`.
Ledger status at mint: `backlog`.
Deps: —.
Closes: DW-FU-3-4-3, DW-FU-3-4-6, DW-FU-3-4-7, DW-FU-3-4-8.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

## Review Triage Log

- No review has run yet.
