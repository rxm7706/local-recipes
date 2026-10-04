---
title: "86.3: Spin and the journal clean up a failed launch and record what they ran"
type: 'fix'
created: '2026-10-03'
status: 'in-progress'
baseline_revision: '94c1d081d733795f6e8235d12f8644072e8c8455'
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

**Problem:** Five spin and journal defects the operator ruled to fix: a failed launch-intent append leaves an empty run directory that becomes the newest run (resume refuses MRS-SPIN-011, retire skips the home); launch intents carry no marshal or harness version (FR-57); `LocalFs.read_text` can block on a FIFO in the supervisor's journal reads; spin swallows a project-policy read failure silently; and the fleet-drain campaign journal's pid-only writer id can repeat across cycles.

**Approach:** Remove the run directory on a failed intent append (best effort, still MRS-SPIN-003); write `marshal_version` and `harness_version` into spin's and dispatch's launch intents; open reads O_NONBLOCK and refuse a non-regular file; surface a policy read failure under MRS-SPIN-008; give the fleet-drain cycle writer id deploy's random token.

Ledger key: `86-3-spin-and-the-journal-clean-up-a-failed-launch-and-record-what-they-ran`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- The capabilities that shipped each behaviour (see each row); a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a failing intent append When spin launches Then no empty run directory remains and MRS-SPIN-003 is reported
- Given any launch When its intent is read Then it carries marshal_version and harness_version
- Given a FIFO at a journal path When the supervisor reads it Then FsError, never a hang
- Given an unreadable project policy When spin runs Then a WARN names it
- Given two cycles in one campaign When they journal Then their writer ids differ
- Given this story lands When its deferred-work rows are read Then each of `DW-FU-3-3-11`, `DW-FU-3-3-9`, `DW-FU-3-4-10`, `DW-FU-3-5-2`, `DW-FU-3-2` is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed

## Boundaries & Constraints

**Always:** Keep each change at its seam (cli/spin.py, adapters/fs_local.py, cli/dispatch.py). Fix each defect where the shipped behaviour lives and pin it with a test that fails without the fix.

**Never:** Never change journal entry ordering.

</intent-contract>

## Deferred-work rows this story closes (operator rulings 2026-10-03, deferral burn-down Phase 3)

- `DW-FU-3-3-11` — On a failed launch-intent append, run_spin removes the run directory it just created (fs.remove_empty_dir, best effort) and still reports MRS-SPIN-003; add a test using the failing-append fake.
- `DW-FU-3-3-9` — spin's launch intent and dispatch's dispatch-launch intent (cli/dispatch.py:2905-2911) payloads carry marshal_version and harness_version (from HarnessPort.harness_version()), closing DW-FU-3-3-9 and DW-1-9-2.
- `DW-FU-3-4-10` — LocalFs.read_text opens with O_RDONLY|O_NONBLOCK, fstat-checks S_ISREG and raises FsError for a non-regular file; add a FIFO test for the journal and sidecar reads.
- `DW-FU-3-5-2` — _compose_spin_policy appends the read failure (PolicyIOError.finding, or a generic MRS-POLICY-004 for other exceptions) to its returned findings, so run_spin reports it under the existing MRS-SPIN-008 WARN; add a unit test.
- `DW-FU-3-2` — The fleet-drain cycle writer id (cli/dispatch.py:5286) gains deploy's random token, like _deploy_writer_id, with a test that two cycles in one campaign mint distinct ids.

## Binding

Parent: The capabilities that shipped each behaviour (see each row)
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (Phase 3) entry.
Ledger key: `86-3-spin-and-the-journal-clean-up-a-failed-launch-and-record-what-they-ran`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 from the operator's Phase 3 rulings (rulings page `rulings` collection; "group them by module, as Phase 2 did").

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
