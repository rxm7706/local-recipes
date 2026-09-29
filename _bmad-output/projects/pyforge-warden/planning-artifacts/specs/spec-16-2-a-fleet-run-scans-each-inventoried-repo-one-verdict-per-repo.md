---
title: "16.2: A fleet run scans each inventoried repo, one verdict per repo"
type: 'feature'
created: '2026-09-28'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - docs/dreams/pyforge-warden.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - src/shared/packages/django-warden/src/django_warden_fabric/tasks.py
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-16-1-warden-inventories-a-ghe-organisation-s-repos.md
flag:
  key: pyforge.warden.fleet_scan
  provider: openfeature-file
  default: {production: off, staging: on, dev: on}
  scope: global
  fallback: "no fleet run can start; the fleet-run action is listed as disabled and refuses"
  cleanup: 90 days after ON in every environment (Q4)
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** With Story 16.1's inventory, nothing scans the fleet. The intake proposed a `scan_jobs` table whose
`status` is CLEAN or VULNERABLE; the operator rejected that on 2026-09-28 because it would compete with `warden scan`'s
exit code. A fleet run must be N ordinary `warden scan` verdicts, persisted, with no verdict of its own.

**Approach:** In `django_warden_fabric`, on the `ComplianceJob` shape: a `FleetRun` row (id, organisation, job status
`pending`/`running`/`succeeded`/`failed`, phase, error, timestamps) and one `FleetRepoScan` row per inventoried repo
(the repo, the commit SHA scanned, `report_json`, the scan's own exit code, a per-repo job status and error). A
keys-not-blobs Celery task fans out one sub-task per repo: shallow-clone the default branch into a `mkdtemp` (`0700`)
directory with a `git` subprocess (argv list, the Steward-provided credential through the environment, never in the URL
or a log), run the existing `warden scan` call (`tasks.py::_run_warden_engines`'s path, `--format json`, with
`--fix-prs-dry-run` so the actuator only plans), persist, and remove the clone in a `finally`. The run's status says
whether the job ran; each repo's verdict is its own report's `status` and exit code, and nothing composes them. Models
ship a migration and its covering Liquibase changeset. The action reads the flag through `django_pyforge.flags`; OFF,
it is listed as disabled and refuses.

Ledger key: `16-2-a-fleet-run-scans-each-inventoried-repo-one-verdict-per-repo`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / L / S-16.1.

### Living CAP citations

- `spec-pyforge-warden` CAP-26 (FR-43); CAP-1 (one command, one exit); CAP-10 (no residue); CAP-17 (derived progress).
- `spec-feature-flag-governance:CAP-1`.

## Acceptance Criteria

- Given an inventory of three fixture repos (local bare repositories), When a fleet run completes, Then one `FleetRun` and three `FleetRepoScan` rows exist, each carrying that repo's own `warden scan` report and exit code
- Given any row, When its fields are read, Then no status value exists outside the job vocabulary (`pending`, `running`, `succeeded`, `failed`) and the report's own frozen verdict lattice — no CLEAN, no VULNERABLE, no fleet verdict
- Given a success and a forced failure mid-scan, When each run ends, Then every throwaway clone directory is gone
- Given the Celery messages, When they are inspected, Then they carry only ids (keys-not-blobs)
- Given a fleet run, When the scans run, Then the actuator runs dry-run only and no forge write is made
- Given the flag OFF, When the operator starts a fleet run, Then the action is listed as disabled and refuses (the management command exits 2)

## Boundaries & Constraints

**Always:**
- Reuse the existing `warden scan` call; never reimplement an analyzer.
- Clone into system temp at `0700`; remove on success and on failure; never write a scanned repo.
- Keep the credential out of URLs, argv values that are logged, model fields and error text.
- Ship the migration with its covering Liquibase changeset; `platform-ci-local -- --test` green.
- Read the flag through `django_pyforge.flags`; add the key to `src/platform/config/flags.json` (default OFF).
- Reconcile every Spec `spec-surface-check` names for the touched paths; scoped stamps only.

**Never:**
- Compose, store or display a fleet-level pass/fail, score or roll-up verdict.
- Open a PR or call the forge's write endpoints (Story 16.3 owns approval).
- Add a webhook trigger, a FastAPI or SQLAlchemy service, or a gitgres store.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| three repos | fixture inventory | one run row, three repo rows, three reports | — |
| a repo fails to clone | clone error | that repo's row `failed` with the error; others proceed | run `succeeded` as a job |
| scan exits 2 | engine error | the report and exit 2 stored as that repo's verdict | — |
| forced failure | exception mid-scan | clone removed | row `failed` |
| archived repo | inventory flag | skipped, recorded as skipped | — |
| flag OFF | key off | action disabled | refuses, exit 2 |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-warden` CAP-26 (FR-43).
Dream: `docs/dreams/pyforge-warden.md` § Realization log → *2026-09-28 (night) — Proposed: the fix-PR actuator finishes the fix, SAST joins as a plugin, and Warden scans the enterprise fleet*.
Ledger key: `16-2-a-fleet-run-scans-each-inventoried-repo-one-verdict-per-repo`.
Ledger status at mint: `backlog`.
Deps: S-16.1.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: pass (the `django-warden` tests under `src/platform/tests/`, the covering changeset under `sqlmigrate-extraction`).
- Flag ON/OFF: a test writes two flagd trees (`pyforge.warden.fleet_scan` on, then off; the `src/platform/tests/test_openfeature_file_flags.py` shape until the `spec-feature-flag-governance:CAP-4` fixture lands): ON runs the fleet, OFF lists the action as disabled and refuses with exit 2.
- `pixi run -e pyforge-guild spec-surface-check` exits 0 after the scoped stamps.

## Review Triage Log

- No review yet (minted 2026-09-28). Implementation and review stay separate.
