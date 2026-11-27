---
title: '69.1: The chain-currency sweep scans the fleet once'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 69-1-the-chain-currency-sweep-scans-the-fleet-once
spec: spec-pyforge-doctor
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py'
  - 'scripts/chain_currency_sweep_check.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_chain_layers_audit.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_board_chain_layers_audit.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_registry.py'
  - 'src/shared/packages/pyforge-doctor/tests/meta/test_package_half_is_the_oracle.py'
  - 'tests/scripts/test_chain_currency_sweep_check.py'
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - docs/dreams/pyforge-doctor.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `scripts/chain_currency_sweep_check.py` takes 86 s of the 132 s Detectors job on a PR, the longest job a PR waits on, and 43.4 s alone here. It calls `board.gather_chain_layers_audit` once per station. Each call loads `scripts/fleet_scan.py` again and runs `scan_fleet()` over every chain: 98 subprocesses in all (git log index builds and `git blame` runs), 29 s of the run. The fleet table depends only on the tree being judged, never on the station.

**Approach:** `board.gather_chain_layers_audits(target, projects)` audits several projects over one `_FleetScan`: one load of `fleet_scan.py`, one `scan_fleet()` and one Dream orphan index, each computed on first use and kept only when it succeeds. Each project still runs through `degrade_on_exception` on its own. `gather_chain_layers_audit` runs the same code with a fresh `_FleetScan`, so one project's audit is unchanged. The sweep makes one batch call and reads each station's answer; a station the batch leaves out is could-not-run.

Ledger key: `69-1-the-chain-currency-sweep-scans-the-fleet-once`.

### Living CAP citations

- spec-pyforge-steward:CAP-175 (the preflight and a PR's CI answer within a measured budget; realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Each project's findings equal what the one-project audit returns for it.
- A project whose audit raises degrades alone; a failed load or scan is retried by the next project, as the one-project audit always did.

**Never:**
- Never read a station as current when the audit did not answer for it.

## Acceptance Criteria

**Given** the eight stations
**When** the sweep runs
**Then** its findings equal the per-station audit's, in under a quarter of the time

- **AC1 — The batch, the audit and the sweep tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild python -m pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_chain_layers_audit.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_board_chain_layers_audit.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_registry.py tests/scripts/test_chain_currency_sweep_check.py -q
  ```

- **AC2 — The sweep is current.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild chain-currency-sweep-check
  ```

</intent-contract>

## Result (2026-11-27)

- The sweep takes 6.3 s alone, from 43.4 s, and its `--json` output is byte for byte the same.
- Against `origin/main`'s `board.py`, the batch returns the same findings for all eight stations and an unknown slug, every check and status included (42.5 s to 5.6 s).
- `test_batch_audit_equals_each_project_alone_and_scans_the_fleet_once` holds that the batch equals each project alone, a FAIL path included, and loads and scans once; it reds when each project gets its own scan.
- The package half now names `chain-audit-verdict`, so it leaves the oracle's gap list (`test_package_half_is_the_oracle.py`, 23 to 22 entries).
- AC1: 50 passed. AC2: exit 0.
