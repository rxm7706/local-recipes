---
title: "16.8: The fleet worker scans non-Python lockfiles against provisioned offline DBs"
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
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-16-4-non-python-lockfiles-scan-through-osv-scanner-s-own-parsers.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-12-4-the-offline-osv-database-is-provisioned-in-ci.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/osv-db-offline-provisioning-decision.md
  - scripts/platform-provision-osv-offline-db.sh
  - src/shared/packages/django-warden/src/django_warden_fabric/tasks.py
  - src/shared/packages/django-warden/src/django_warden_fabric/proposals.py
deferred: []
---

<intent-contract>

## Intent

**Problem:** CAP-26's npm clause assumes offline OSV databases nothing provisions, and leaves the outcome of a
non-Python proposal unstated (line numbers at `03a7aff5d9`; WAR-M-Z2):
- `scripts/platform-provision-osv-offline-db.sh` provisions only `osv-scanner/PyPI/all.zip` (:12), and only CI runs it
  (`.github/workflows/platform-ci.yml` about :864). The fleet worker sets no offline-database cache, so a real npm, Go
  or Cargo scan routes to `indeterminate` with `offline-db-unavailable-ecosystem` (`src/shared/packages/pyforge-warden/src/pyforge/warden/native_lockfiles.py` about
  :220-221). That is not egress: osv-scanner runs `--offline`.
- `src/shared/packages/django-warden/src/django_warden_fabric/proposals.py` (about :58) queues a proposal for any planned `vuln:` outcome, including an npm one that CAP-24's
  edit set (`pixi.toml`, `pyproject.toml`, recipes) cannot fix.
- Rejected as taste: the claim that CAP-26 bundles three capabilities (the Dream split the npm clause into Story 16.4).

**Operator ruling 2026-11-01** (the `spec-pyforge-warden` memlog's decision of that date): a non-PyPI or conda
vulnerability proposal is never queued — only a `vuln:` finding on a PyPI or conda component queues one.

EGM audit 2026-11-01, cluster WAR-CL-6; finding WAR-M-Z2, accepted by the operator on 2026-11-01; residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.

**Approach:**
- Extend `scripts/platform-provision-osv-offline-db.sh` to provision the npm, Go and crates.io databases beside PyPI,
  idempotently, keeping its already-provisioned short-circuit per ecosystem.
- Point the fleet worker's scan environment at the provisioned cache (`OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY`, read from
  a setting); a missing database for an ecosystem stays `indeterminate`, never `clean`.
- `proposals.py` queues only `vuln:` outcomes whose component is PyPI or conda; any other ecosystem's finding is
  recorded in the run's report and queues nothing.
- CAP-26 success names the per-ecosystem offline database as a precondition and the ruled non-Python proposal outcome,
  through the `spec-pyforge-warden` `bmad-spec` re-derive (with WAR-CL-3's).

Ledger key: `16-8-the-fleet-worker-scans-non-python-lockfiles-against-provisioned-offline-dbs`.
Type / Effort / Deps: fix / M / S-16.6 (both change the queue in `proposals.py`).

### Living CAP citations

- `spec-pyforge-warden` CAP-26 (FR-43) — the security axis for the lockfile ecosystems osv-scanner parses natively. A
  `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag
  (`pyforge.warden.non_python_ecosystems` keeps gating discovery).

## Acceptance Criteria

- **AC1 — The databases are provisioned.** Given an empty cache directory and a connected runner, When
  `scripts/platform-provision-osv-offline-db.sh` runs, Then the cache holds `PyPI`, `npm`, `Go` and `crates.io`
  databases; a second run is a no-op for each one already present.
- **AC2 — The worker reads them.** Given a fleet repo whose `package-lock.json` pins a known-vulnerable npm version and
  a fixture cache that holds the npm database, When `scan_fleet_repo` runs, Then the stored report carries the `vuln:`
  finding for it and no `offline-db-unavailable-ecosystem` finding.
- **AC3 — A missing database stays honest.** Given the same repo and a cache without the npm database, When it is
  scanned, Then the security axis is `indeterminate`, never `clean`.
- **AC4 — No non-Python proposal.** Given the AC2 run, When it finalizes, Then no `FixProposal` exists for the npm
  finding, while a PyPI or conda `vuln:` outcome in the same run still queues one.
- **AC5 — Offline.** The scan runs osv-scanner with `--offline`; the suite opens no socket (fixture databases only).
- **AC6 — The contract follows.** CAP-26 success names the per-ecosystem offline database and the ruled non-Python
  proposal outcome through a `bmad-spec` re-derive; no `SPEC.md` hand edit.
- **AC7 — Green.** `pixi run -e pyforge-guild platform-ci-local -- --test` and
  `pixi run --frozen -e pyforge-warden pyforge-warden-test` pass.

## Boundaries & Constraints

**Always:** the scan stays `--offline`; provisioning runs only on a connected runner or an operator's machine, never
inside the scan; container and artifact scanning stay out of scope.

**Never:** queue a proposal for an npm, Go or Cargo finding; download a database from inside a test; hand-edit
`SPEC.md`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-warden` CAP-26 (FR-43) — the fleet's security axis over non-Python lockfiles; a fix,
  no new CAP.

Parent: CAP-26

- EGM audit finding carried: WAR-M-Z2 (cluster WAR-CL-6; accepted 2026-11-01; one memlog event on
  `spec-pyforge-warden/.memlog.md`); operator ruling 2026-11-01 (the memlog decision of that date); residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Epic: Epic 16 — a fix story joins its done epic (operator rule 2026-10-04; doctor Story 41.5 lets the epic key roll up
  to `in-progress`).
- Ledger key: `16-8-the-fleet-worker-scans-non-python-lockfiles-against-provisioned-offline-dbs`.
- Ledger status at mint: `backlog`.
- Deps: S-16.6.
- Surface: `scripts/platform-provision-osv-offline-db.sh`, `src/shared/packages/django-warden/src/django_warden_fabric/tasks.py`, `src/shared/packages/django-warden/src/django_warden_fabric/proposals.py`,
  `.github/workflows/platform-ci.yml`, `src/platform/tests/test_warden_fleet_run.py`,
  `src/platform/tests/test_warden_fleet_proposals.py`.
- Dream: `docs/dreams/pyforge-warden.md` § *Realization log*, the 2026-11-01 (the EGM fleet audit) entry.
- Minted 2026-11-01 by the EGM audit landing (marshal Story 113.7, spec-pyforge-marshal:CAP-302); mode in-PR: built in the audit's landing PR.

## Verification

**Commands:**
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: pass (the `django-warden` tests under
  `src/platform/tests/`, including `src/platform/tests/test_warden_fleet_run.py` and
  `src/platform/tests/test_warden_fleet_proposals.py`).
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).
- `bash -n scripts/platform-provision-osv-offline-db.sh` — expected: exit 0.

**Run before the push:**
- On a connected machine: `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY=<scratch dir> pixi run -e pyforge-warden bash scripts/platform-provision-osv-offline-db.sh`
  — expected: the four databases present, and a second run reports each as already provisioned.

## Auto Run Result

Status: backlog

Summary: not yet dispatched.

## Spec Change Log

- 2026-11-01: minted `backlog` from the EGM fleet audit (marshal Story 113.7): cluster WAR-CL-6, finding WAR-M-Z2,
  accepted by the operator; operator ruling 2026-11-01 (a non-PyPI or conda vulnerability proposal is never queued);
  mode in-PR.

## Review Triage Log

- (none yet)
