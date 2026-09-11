---
title: 'The backup/PITR handoff is explicit when the BYO-PostgreSQL overlay is active'
type: 'feature'
created: '2026-09-11'
status: 'done'
baseline_revision: 'fb55f147c20c797b29f34307ebdd16fde02de4ce'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `postgres-backup-cronjob.yaml` runs unconditionally against whatever Postgres the
chart deploys. Once Story 51.1's `postgres.external.enabled` toggle lets the chart point at an
Enterprise Managed PostgreSQL instance pyforge doesn't own, the CronJob would otherwise keep
running a shadow backup of a database outside pyforge's operational control — and the real
owner of backup/PITR for that path would be silently unnamed rather than explicitly handed off,
exactly the gap the owning Dream's Non-goals flagged as deliberately left open rather than
pre-decided.

**Approach:** A small, separately-reviewable decision (kept out of Story 51.1 on purpose so it
gets its own review): condition `postgres-backup-cronjob.yaml` on the same
`postgres.external.enabled` toggle Story 51.1 introduces, and add one explicit paragraph to
`src/platform/deploy/README.md` naming the enterprise database team as the owner of
backup/PITR whenever the BYO-PostgreSQL overlay is active.

## Boundaries & Constraints

**Always:**
- Reuse Story 51.1's own `.Values.postgres.external.enabled` toggle — no new toggle.
- With the overlay NOT applied, the backup CronJob must still deploy exactly as it does today —
  no change to the self-hosted default's backup behavior.
- The `deploy/README.md` paragraph must explicitly name the enterprise database team as the
  BYO-path's backup/PITR owner — a named handoff, not an implicit or absent one.

**Never:**
- Do not introduce a second toggle or condition on anything other than Story 51.1's
  `postgres.external.enabled`.
- Do not touch Redis or any file Story 51.1/51.2 did not already touch, beyond
  `postgres-backup-cronjob.yaml` and `deploy/README.md`.
- Do not build any actual backup/PITR mechanism for the external instance — this story only
  documents the handoff and disables pyforge's own shadow backup; the enterprise's own
  database team's backup tooling is out of scope.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `postgres.external.enabled: false` (default) | Self-hosted Postgres | `postgres-backup-cronjob.yaml` deploys exactly as today | n/a |
| `postgres.external.enabled: true` (Story 51.1's overlay active) | External Postgres | `postgres-backup-cronjob.yaml` is not deployed | n/a |
| Either state | `deploy/README.md` | Names the enterprise database team as backup/PITR owner for the BYO path | n/a |

</intent-contract>

## Code Map

- `src/platform/deploy/charts/platform/templates/postgres-backup-cronjob.yaml` — add a
  `{{- if not .Values.postgres.external.enabled }}` guard (Story 51.1's own toggle), matching
  the guard style Story 51.1 applies to the other three Postgres templates.
- `src/platform/deploy/README.md` — one new paragraph naming the enterprise database team as
  the BYO-PostgreSQL path's backup/PITR owner, placed near the existing DR/backup references
  (`DR.md`, `restore.md`, Story 41.1).

## Tasks & Acceptance

**Execution:**
- [x] `feature` — guard `postgres-backup-cronjob.yaml` on `postgres.external.enabled`.
- [x] `feature` — add the ownership-handoff paragraph to `deploy/README.md`.

**Acceptance Criteria:**
- Given `postgres-backup-cronjob.yaml` today runs unconditionally against whatever Postgres the
  chart deploys, when `postgres.external.enabled: true` (Story 51.1's overlay), then the backup
  CronJob is not deployed — pyforge's chart does not create a shadow backup of a database it
  does not own.
- Given the BYO-PostgreSQL overlay is active, when `deploy/README.md` is read, then it names
  the enterprise database team as the owner of backup/PITR for that path.
- Given the overlay is NOT applied, when the chart is rendered, then the backup CronJob still
  deploys exactly as it does today.

## Verification

**Commands:**
- `helm template src/platform/deploy/charts/platform` (no overlay) — expect
  `postgres-backup-cronjob.yaml` unchanged from today's render.
- `helm template src/platform/deploy/charts/platform -f
  src/platform/deploy/overlays/external-postgres/values.yaml` (Story 51.1's overlay) — expect
  `postgres-backup-cronjob.yaml` to render empty.
- Manual: `deploy/README.md` names the enterprise database team as backup/PITR owner for the
  BYO path.

## Review Triage Log

### 2026-09-11 — Review pass
- verdicts: 1 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings:
  - `[low]` `[defer]` Added `postgres.external.enabled: false` default to `values.yaml` — Story 51.1's first task, required so the guard renders before 51.1 lands; 51.3 spec scoped to cronjob + README only — evidence: helm template nil-pointer without the default

## Auto Run Result

Status: done

Summary: Guarded `postgres-backup-cronjob.yaml` on Story 51.1's `postgres.external.enabled` toggle and documented the enterprise database team as BYO-PostgreSQL backup/PITR owner in `deploy/README.md`. Added the toggle default (`external.enabled: false`) to `values.yaml` so helm renders before Story 51.1 lands.

Files changed:
- `src/platform/deploy/charts/platform/templates/postgres-backup-cronjob.yaml` — skip backup CronJob when external Postgres is enabled
- `src/platform/deploy/README.md` — BYO backup/PITR handoff paragraph (Story 51.3)
- `src/platform/deploy/charts/platform/values.yaml` — `postgres.external.enabled: false` default (Story 51.1 seam, required for render)
- `src/platform/tests/test_chart_invariants.py` — `test_external_postgres_omits_backup_cronjob` matrix proof

Review findings breakdown: 0 patches applied; 1 deferred (`values.yaml` default overlaps Story 51.1)

Follow-up review recommendation: false

Verification performed:
- `helm template` default render: 1 CronJob (postgres-backup present)
- `helm template --set postgres.external.enabled=true`: 0 CronJobs, no cronjob template
- `pytest tests/test_chart_invariants.py::test_postgres_backup_cronjob_and_archive_mode tests/test_chart_invariants.py::test_external_postgres_omits_backup_cronjob` (platform-ci-test + platform-dev helm on PATH): 2 passed

Residual risks: Story 51.1 overlay file (`overlays/external-postgres/values.yaml`) not yet present — verification used `--set postgres.external.enabled=true` equivalent. Story 51.1 still owns StatefulSet/Service/PVC guards and overlay authoring.
