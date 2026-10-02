---
title: '82.2: Marshal land keeps a live run''s branch and home while its engine is alive, even when its supervisor is dead'
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

**Problem:** `core/status.py::is_run_live` (`:1255-1296`) is the one predicate `cli/land.py` checks (`:936`) before it
honours `landing_branch_retirement` and deletes a station branch. Its last line is
`return not facts.finished and facts.supervisor_alive is True`: it reads only the supervisor sidecar's pid. Story 5.8
added `FleetHomeFacts.engine_alive` (`ProcessPort.is_alive(launch_pid)`, gathered at `:849-852`) and `derive_home_state`
already lets it soften a dead sidecar (`:784`), but `is_run_live` never reads it. So a dead sidecar behind a live harness
(the 2026-08-11 incident Story 5.8 fixed for `status`) reads "not live" here, and `marshal land` retires a branch a running
harness is still using (DW-5-8-1, DW-FU-4-11). Separately, `_resync_home_branch` (`cli/land.py:1570`, called at `:533`,
`:616` and `:1060`) fetches and fast-forwards the loop home's checked-out branch from outside the run with no lock and no
liveness check: a live run's untouched tracked files can be rewritten on disk mid-turn (DW-FU-4-12). Re-verified at HEAD
a7cdb91fe4.

**Approach:**

- `is_run_live` also returns live when the run is unfinished and `engine_alive is True`, whatever `supervisor_alive`
  reads. Its existing conservative arms (`journal_unreadable`, `run_state_retired`) are unchanged.
- `run_land` gathers the home's facts once and hands `_resync_home_branch` the liveness verdict; while the run is live the
  resync neither fetches nor fast-forwards and reports one `MRS-LAND-009` WARN naming the live run (the code's existing
  "resync did not happen" signal, so no new code).
- All three resync call sites take the same verdict.

Ledger key: `82-2-marshal-land-keeps-a-live-run-s-branch-and-home-while-its-engine-is-alive-even-when-its-supervisor-is-dead`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-9 (the last mile lands itself; branch retirement and resync), with Story 4.11 (FR-172),
  Story 5.8 (FR-181; AD-5) and Story 4.12 (FR-173). A defect of shipped behaviour, so no new CAP; no flag.

## Acceptance Criteria

- Given facts with `has_run`, not `finished`, `supervisor_alive is False` and `engine_alive is True` When `is_run_live` runs Then it returns `True`
- Given the same home When `marshal land` runs with `landing_branch_retirement` true Then branch deletion is downgraded with `MRS-LAND-008` and the branch survives
- Given a live run in the home When `marshal land` reaches any of its three resync exits Then no fetch or fast-forward runs against the home and one `MRS-LAND-009` WARN names the live run
- Given a finished run, or one whose supervisor and engine are both confirmed dead When `marshal land` runs Then retirement and resync behave exactly as today
- Given the `engine_alive` term removed from `is_run_live` When the new test runs Then it fails (mutation)
- Given the liveness check removed from the resync When the new live-run resync test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** `is_run_live` stays pure and reads `FleetHomeFacts` directly, never `derive_home_state`'s state string. A fact
that cannot be proven stays refused, never defaulted to "safe to delete". Close DW-5-8-1, DW-FU-4-11 and DW-FU-4-12 in
`deferred-work-ledger.md` when the story lands (status `closed`, a `resolved:` line naming this story).

**Never:** Do not change what `marshal status` displays for a home. Do not add a lock that can block a live run's own git
operations. Do not write back the on-disk `landing_branch_retirement` or `landing_resync` policy values.

</intent-contract>

## Binding

Parent: Stories 4.11, 4.12 and 5.8, `spec-pyforge-marshal` CAP-9; a defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 entry.
Ledger key: `82-2-marshal-land-keeps-a-live-run-s-branch-and-home-while-its-engine-is-alive-even-when-its-supervisor-is-dead`.
Ledger status at mint: `backlog`.
Deps: —.
Closes: DW-5-8-1, DW-FU-4-11, DW-FU-4-12.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

## Review Triage Log

- No review has run yet.
