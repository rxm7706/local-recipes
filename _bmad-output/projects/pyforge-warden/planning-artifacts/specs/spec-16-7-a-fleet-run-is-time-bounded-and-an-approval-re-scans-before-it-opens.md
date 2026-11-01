---
title: "16.7: A fleet run is time-bounded, and an approval re-scans before it opens"
type: 'fix'
created: '2026-11-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/.memlog.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-16-2-a-fleet-run-scans-each-inventoried-repo-one-verdict-per-repo.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-16-3-each-fleet-fix-waits-in-a-proposal-queue-for-operator-approval.md
  - src/shared/packages/django-warden/src/django_warden_fabric/tasks.py
  - src/shared/packages/django-warden/src/django_warden_fabric/fleet.py
  - src/shared/packages/django-warden/src/django_warden_fabric/models.py
  - src/shared/packages/django-warden/src/django_warden_fabric/proposals.py
deferred: []
---

<intent-contract>

## Intent

**Problem:** CAP-26 states no failure modes, and the fleet code has no time bounds and no stale-approval guard (line
numbers at `03a7aff5d9`; WAR-M-D4):
- `scan_fleet_repo` and `open_fix_proposal` (`src/shared/packages/django-warden/src/django_warden_fabric/tasks.py`) declare no `soft_time_limit` or `time_limit`, unlike
  `run_fleet_inventory` (about :135-140), and `shallow_clone` (`src/shared/packages/django-warden/src/django_warden_fabric/fleet.py` about :41-79) runs `git clone` with no
  timeout, so one hung clone leaves a run `RUNNING` forever.
- A failed repo does get `FleetRepoScan` `FAILED`, but the run row records no failed or skipped repo counts, so a run
  that ends `SUCCEEDED` as a job (Story 16.2's decision, `spec-16-2-…md` I/O matrix) says nothing about its misses.
- The approve re-clones without re-scanning, so it can open a fix for a finding the repo no longer has; no approval
  expires.
- Dropped as already handled: double-approve and dismiss (`src/shared/packages/django-warden/src/django_warden_fabric/proposals.py` about :83-128). The read/write token split
  waits on the open credential ruling.

EGM audit 2026-11-01, cluster WAR-CL-8; finding WAR-M-D4, accepted by the operator on 2026-11-01; residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.

**Approach:**
- `scan_fleet_repo` and `open_fix_proposal` take soft and hard time limits, reusing the values `run_fleet_inventory`
  uses (the general pool's 300 s hard limit, Story 16.1's spec Change Log); `shallow_clone` passes a timeout to its
  `git` calls, and a timeout is that repo's `FAILED` row with the reason.
- `FleetRun` gains failed and skipped repo counts, filled when the run finalizes; a `0004` migration ships with its
  covering Liquibase changeset under `src/platform/db/changelog/changes/` and a `src/platform/db/sqlmigrate-map.yaml`
  entry.
- The approve re-scans the fresh clone with `warden scan` before acting, and refuses with a `failed` actuation when the
  proposal's finding id is absent from the fresh report. A configurable approval expiry (a setting with a default,
  named in this spec at implementation) refuses an older proposal the same way.
- A memlog decision on `spec-pyforge-warden` names the bounds and the approve-time re-scan; CAP-26 success names them
  through a `bmad-spec` re-derive.

Ledger key: `16-7-a-fleet-run-is-time-bounded-and-an-approval-re-scans-before-it-opens`.
Type / Effort / Deps: fix / L / S-16.6 (both change the approve path in `tasks.py` and `proposals.py`).

### Living CAP citations

- `spec-pyforge-warden` CAP-26 (FR-43) — Warden scans the fleet, one verdict per repo, and each fix waits for the
  operator. A `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- **AC1 — Tasks are bounded.** Given the Celery task registry, When `scan_fleet_repo` and `open_fix_proposal` are
  inspected, Then each declares a `soft_time_limit` below its `time_limit`, at the values `run_fleet_inventory` uses.
- **AC2 — A hung clone ends.** Given a `git clone` stub that never returns before the clone timeout, When the fleet run
  scans that repo, Then its `FleetRepoScan` row ends `FAILED` naming the timeout, the other repos proceed, and the run
  ends `SUCCEEDED` as a job.
- **AC3 — The run counts its misses.** Given a three-repo run with one failed clone and one archived repo, When the run
  finalizes, Then the run row records 1 failed and 1 skipped; no status outside the job vocabulary appears.
- **AC4 — A vanished finding is refused.** Given a queued proposal whose finding a fresh scan of the clone no longer
  reports, When the operator approves it, Then the proposal records a `failed` actuation naming the vanished finding
  and the fake forge client records zero writes.
- **AC5 — An old approval is refused.** Given a proposal older than the configured approval expiry, When it is approved,
  Then it is refused the same way, and the expiry can be changed through its setting.
- **AC6 — The migration is whole.** `makemigrations --check` reports no change for `warden_fabric`; the `0004`
  migration has its covering changeset and its `sqlmigrate-map.yaml` entry, and `sqlmigrate-extraction` passes.
- **AC7 — The contract follows.** A memlog decision records the bounds and the approve-time re-scan; CAP-26 success
  names them through a `bmad-spec` re-derive.
- **AC8 — Green.** `pixi run -e pyforge-guild platform-ci-local -- --test` and
  `pixi run --frozen -e pyforge-warden pyforge-warden-test` pass.

## Boundaries & Constraints

**Always:** a job status is never a verdict; a run stays `SUCCEEDED` as a job when some repos fail; the Celery message
carries ids only (keys-not-blobs); every throwaway clone is removed after a success, a failure and a timeout.

**Never:** add a fleet-level verdict; change double-approve or dismiss behaviour; run a live fleet write (the credential for a live fleet write is not ruled (`spec-pyforge-warden/.memlog.md`, the 2026-10-11 decision, item 9));
hand-edit `SPEC.md`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-warden` CAP-26 (FR-43) — Warden scans the fleet, one verdict per repo; a fix, no new
  CAP.

Parent: CAP-26

- EGM audit finding carried: WAR-M-D4 (cluster WAR-CL-8; accepted 2026-11-01; one memlog event on
  `spec-pyforge-warden/.memlog.md`); residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Epic: Epic 16 — a fix story joins its done epic (operator rule 2026-10-04; doctor Story 41.5 lets the epic key roll up
  to `in-progress`).
- Ledger key: `16-7-a-fleet-run-is-time-bounded-and-an-approval-re-scans-before-it-opens`.
- Ledger status at mint: `backlog`.
- Deps: S-16.6.
- Surface: `src/shared/packages/django-warden/src/django_warden_fabric/tasks.py`, `src/shared/packages/django-warden/src/django_warden_fabric/fleet.py`, `src/shared/packages/django-warden/src/django_warden_fabric/models.py`, `src/shared/packages/django-warden/src/django_warden_fabric/migrations/` (a new `0004` migration),
  `src/shared/packages/django-warden/src/django_warden_fabric/proposals.py`, `src/platform/db/changelog/changes/`, `src/platform/db/sqlmigrate-map.yaml`,
  `src/platform/tests/test_warden_fleet_run.py`, `src/platform/tests/test_warden_fleet_proposals.py`.
- Dream: `docs/dreams/pyforge-warden.md` § *Realization log*, the 2026-11-01 (the EGM fleet audit) entry.
- Minted 2026-11-01 by the EGM audit landing (marshal Story 113.7, spec-pyforge-marshal:CAP-302); mode in-PR: built in the audit's landing PR.

## Verification

**Commands:**
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: pass (the `django-warden` tests under
  `src/platform/tests/`, including `src/platform/tests/test_warden_fleet_run.py` and
  `src/platform/tests/test_warden_fleet_proposals.py`; the covering changeset under `sqlmigrate-extraction`).
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Auto Run Result

Status: backlog

Summary: not yet dispatched.

## Spec Change Log

- 2026-11-01: minted `backlog` from the EGM fleet audit (marshal Story 113.7): cluster WAR-CL-8, finding WAR-M-D4,
  accepted by the operator; the double-approve and dismiss sub-claims dropped as handled; mode in-PR.

## Review Triage Log

- (none yet)
