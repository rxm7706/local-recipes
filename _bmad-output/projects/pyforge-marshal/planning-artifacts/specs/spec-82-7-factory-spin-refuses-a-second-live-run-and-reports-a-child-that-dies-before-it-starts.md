---
title: '82.7: Factory spin refuses a second live run and reports a child that dies before it starts'
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

**Problem:** `marshal factory spin` launches without asking two questions. Re-verified at HEAD a7cdb91fe4:

- `cli/spin.py::run_spin` (`:1335`) has no precondition for an already-live run: none of its gates, and none of
  `MRS-SPIN-001` through `MRS-SPIN-017`, checks the loop home for one before minting a run id (`:1673`) and spawning
  another detached `bmad-loop run`. bmad-loop's own `cmd_run` checks only `worktree_clean` and its base skills, so two
  engines can drive one project's feed, journal and working tree at once (DW-FU-3-3-2; the team memory note that
  `factory spin` does not serialize says the same).
- `adapters/harness_bmadloop.py::spin` spawns the child (`:1564`) and then polls the log for its starting line with
  `_poll_for_harness_run_id(self, log_path)` (`:1514-1535`), which never asks whether the child is still alive. A child
  that exits at once (most often `cmd_run`'s `worktree_clean` refusal, before its starting line) burns the whole poll window
  and is reported as a launch: `MRS-SPIN-004` WARN, exit 0, the dead pid in the `outcome` entry, the real error unread in
  `harness.log` (DW-FU-3-3-4).

**Approach:**

- Before minting a run id, `run_spin` reads the home's run facts (the `cli/status.py::_gather_home_facts` facts `marshal
  land` already reuses) and refuses with a new `MRS-SPIN-*` ERROR when `core.status.is_run_live` reports a live run, naming
  the run and the remedy (`marshal factory attach`, stop it, or wait). The refusal mints nothing and spawns nothing.
- The poll takes the spawned child's liveness: each step asks whether the pid is still running (an exited child that has
  not been reaped counts as exited). A child that exits before its starting line ends the poll at once and raises the
  adapter's launch error with the tail of `harness.log`, so `spin` reports a failed launch (the existing `MRS-SPIN-003`
  class) with a non-zero exit and an `outcome` entry that says the process exited. A slow but live child keeps today's
  `MRS-SPIN-004` WARN.

Ledger key: `82-7-factory-spin-refuses-a-second-live-run-and-reports-a-child-that-dies-before-it-starts`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-2 (launch returns a run identifier promptly; the run completes, escalates or stops with a
  named reason) with Story 3.3 (FR-9, FR-10, FR-52; AD-3, AD-22). Story 3.3's I/O row that counted an unconfirmed launch as
  a success "pid known" is the defect corrected here. No new CAP; no flag.

## Acceptance Criteria

- Given a loop home whose latest run is unfinished with a live supervisor or engine pid When `marshal factory spin <slug>` runs Then it exits non-zero with the new `MRS-SPIN-*` ERROR naming that run, and no run directory is created and nothing is spawned
- Given a home whose latest run is finished or whose pids are both dead When spin runs Then it launches as today
- Given a spawned child that exits with status 1 before printing its starting line When spin runs Then the poll ends without waiting out its window and spin reports a failed launch quoting the log tail, with a non-zero exit
- Given a child still alive when the poll window ends without a starting line When spin runs Then it reports `MRS-SPIN-004` WARN and exit 0 as today
- Given either check removed When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Refuse before any write. Register the new code in `core/findings.py` and `core/verdict.py`. Close DW-FU-3-3-2
and DW-FU-3-3-4 in `deferred-work-ledger.md` when the story lands (status `closed`, a `resolved:` line naming this story).

**Never:** Do not add a lock file or a second liveness model; reuse `is_run_live`. Do not change `marshal factory resume`.
Do not touch retry escalation or the policy writes (Story 82.6's surface).

</intent-contract>

## Binding

Parent: Story 3.3, `spec-pyforge-marshal` CAP-2; a defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 entry.
Ledger key: `82-7-factory-spin-refuses-a-second-live-run-and-reports-a-child-that-dies-before-it-starts`.
Ledger status at mint: `backlog`.
Deps: —.
Closes: DW-FU-3-3-2, DW-FU-3-3-4.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

## Review Triage Log

- No review has run yet.
