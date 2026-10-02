---
title: '82.7: Factory spin refuses a second live run and reports a child that dies before it starts'
type: 'fix'
created: '2026-10-02'
status: 'blocked'
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

**Problem:** `adapters/harness_bmadloop.py::spin` spawns the `bmad-loop run` child and then polls the log for its
starting line with `_poll_for_harness_run_id(self, log_path)` (`adapters/harness_bmadloop.py:1526`, called at `:1588`),
which never asks whether the child is still alive. A child that exits at once (most often `cmd_run`'s `worktree_clean`
refusal, before its starting line) burns the whole poll window and is reported as a launch: `MRS-SPIN-004` WARN, exit 0,
the dead pid in the `outcome` entry, the real error unread in `harness.log` (DW-FU-3-3-4).

**Scope ruling (operator, 2026-10-02):** the title's first half, refusing a second spin while the project's run is
live, already ships. `cli/spin.py::run_spin` calls `cli/dispatch.py::spin_loop_home_in_flight_conflict` before a run id
is minted (the "Story 34.1" block, from Story 28.24's 2026-09-10 fix) and refuses with `MRS-DISP-021`, naming the run and
its pids; `tests/unit/test_spin.py` covers it. This story keeps that guard unchanged and adds no second gate and no
second liveness model. DW-FU-3-3-2 is closed as resolved by Stories 28.24 and 34.1. The first dispatch of this story
(run `pyforge-marshal-20261002T130706347Z-dc65b4d3`) found the guard, blocked on the intent gap and changed no code.

**Approach:** the poll takes the spawned child's liveness: each step asks whether the pid is still running (an exited
child that has not been reaped counts as exited). A child that exits before its starting line ends the poll at once and
raises the adapter's launch error with the tail of `harness.log`, so `spin` reports a failed launch (the existing
`MRS-SPIN-003` class, "never launched, safe to retry") with a non-zero exit and an `outcome` entry that says the process
exited. A slow but live child keeps today's `MRS-SPIN-004` WARN.

Ledger key: `82-7-factory-spin-refuses-a-second-live-run-and-reports-a-child-that-dies-before-it-starts`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-2 (launch returns a run identifier promptly; the run completes, escalates or stops with a
  named reason) with Story 3.3 (FR-9, FR-10, FR-52; AD-3, AD-22). Story 3.3's I/O row that counted an unconfirmed launch as
  a success "pid known" is the defect corrected here. No new CAP; no flag.

## Acceptance Criteria

- Given a spawned child that exits with status 1 before printing its starting line When spin runs Then the poll ends without waiting out its window and spin reports a failed launch (`MRS-SPIN-003`) quoting the log tail, with a non-zero exit and an `outcome` entry that says the process exited
- Given a child still alive when the poll window ends without a starting line When spin runs Then it reports `MRS-SPIN-004` WARN and exit 0 as today
- Given a loop home whose run is live When a second spin runs Then it still refuses with `MRS-DISP-021` (Story 34.1's guard, unchanged)
- Given the liveness check removed from the poll When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Reuse the existing `MRS-SPIN-003` launch-failure path; no new finding code. Close DW-FU-3-3-4 in
`deferred-work-ledger.md` when the story lands (status `closed`, a `resolution:` line naming this story, a `verified:`
line citing `path:line` or a command with its exit code).

**Never:** Do not add a second spin-vs-spin gate, a lock file or a second liveness model; do not change Story 34.1's
guard or `MRS-DISP-021`. Do not change `marshal factory resume`. Do not touch retry escalation or the policy writes
(Story 82.6's surface).

</intent-contract>

## Binding

Parent: Story 3.3, `spec-pyforge-marshal` CAP-2; a defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 entry and the 2026-10-02 (later) ruling.
Ledger key: `82-7-factory-spin-refuses-a-second-live-run-and-reports-a-child-that-dies-before-it-starts`.
Ledger status at mint: `backlog`.
Deps: —.
Closes: DW-FU-3-3-4 (DW-FU-3-3-2 closed by the 2026-10-02 ruling).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

## Review Triage Log

- No review has run yet.

## Auto Run Result

Status: blocked
Blocking condition: intent gap -- the Problem's first premise is false at HEAD 80fb2fe128 (a spin-vs-spin guard already ships), and the Approach's `is_run_live` reuse contradicts AC2 on two edge arms. No code was changed.

**Evidence (read from the tree, not executed):**

- `cli/spin.py::run_spin` already refuses a second spin against a live loop home: the "Story 34.1" block (`cli/spin.py:1856-1878`) calls `spin_loop_home_in_flight_conflict` (`cli/dispatch.py:1774-1831`) before the run id is minted (`:1883`). It exits non-zero with `MRS-DISP-021`, names the run and its pids, creates no run directory and spawns nothing. Shipped in `c1c794797e9` (Story 28.24, 2026-09-10). Tests: `tests/unit/test_spin.py:4416-4528` (refuses while live, allows when the snapshot is finished, allows for another station, rapid second call).
- AC1's observable behaviour therefore exists today. What differs is (a) the code, `MRS-DISP-021` against the spec's new `MRS-SPIN-*`, and (b) the liveness model: 34.1 walks every run's launch and supervisor pid plus the harness snapshot; the spec requires `is_run_live`. Both the DW-FU-3-3-2 "STANDS 2026-10-01" verification and the team-memory note `factory spin does not serialize` (2026-08-15) miss or predate that guard. The spec's line anchors (`run_spin :1335`, mint `:1673`) are also stale (now `:1540`, `:1883`).
- `is_run_live` as written contradicts AC2 ("pids both dead -> launches as today"). Its conservative arms report live with no live pid: `journal_unreadable` and `run_state_retired` (`core/status.py:1288-1303`). `_gather_home_facts` (`cli/status.py:983-1011`) returns `journal_unreadable=True` for a latest run whose launch outcome carries `pid: None`, unless the harness reports that run terminal. A failed launch is exactly the run Part 2 now leaves behind. A gate on `is_run_live` alone would refuse every retry after a failed launch, and after a retired run, with no way out: the refusal mints no newer run directory. 34.1's pid walk refuses neither case.
- Part 2 is still valid and unambiguous: `adapters/harness_bmadloop.py:1526` `_poll_for_harness_run_id(self, log_path)` takes only the log path, and `spin` calls it at `:1588` with no child liveness.

**Unanswered questions (settle in this spec, then re-dispatch):**

1. Relation of the new `MRS-SPIN-*` gate to the shipped 34.1 spin-run guard. Replace it (the spin-run half of `spin_loop_home_in_flight_conflict` goes; `MRS-DISP-021` stops appearing for spin-vs-spin; `test_spin.py:4438`, `:4526` and the code lists in `test_findings.py` change), keep it and drop Part 1 (AC1 already holds under `MRS-DISP-021`; DW-FU-3-3-2 closes as resolved by Story 28.24/34.1), or layer the new gate behind it (fires only where 34.1 does not, so AC1's own scenario still reports `MRS-DISP-021`)? Each gives a different observable code for AC1 and a different mutation target for the last AC.
2. Should `journal_unreadable` and `run_state_retired` count as live for spin? Under `is_run_live` as it stands they do, and they deadlock a home after a failed or retired run; under AC2 they must not refuse.
3. Is Part 2 (child liveness in the poll, `MRS-SPIN-003` with the log tail, a non-zero exit) to ship alone as this story once Part 1 is settled?
