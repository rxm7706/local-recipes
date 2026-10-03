---
title: "84.1: An audit purge records itself, and the audit table is append-only by privilege"
type: 'fix'
created: '2026-10-03'
status: 'ready-for-dev'
baseline_revision: '514b6982d55a7e9ff34a3579fd3bda0fc15bceb4'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Two audit-trail gaps the operator ruled to fix: `purge_expired_entries` deletes audit rows without recording the purge, and nothing makes the audit trail append-only, so one ORM call can rewrite history.

**Approach:** Add `AuditAction.PURGE` and a required `actor` (the retention job's identity) to `purge_expired_entries`, writing one purge row in the same transaction as the delete; have `steward deploy` render grants giving the app role only SELECT and INSERT on the audit table and a separate retention role DELETE.

Ledger key: `84-1-an-audit-purge-records-itself-and-the-audit-table-is-append-only-by-privilege`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- The steward capabilities that shipped each behaviour (Epic 9's audit trail, Story 9.1's ingress); a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a purge When it runs Then one purge row records the actor, the cutoff and the row count, in the same transaction
- Given the rendered grants When the app role tries UPDATE or DELETE on the audit table Then the database refuses
- Given the retention role When it purges Then it succeeds and records the purge
- Given this story lands When its deferred-work rows are read Then each of `DW-9-3-3`, `DW-9-3-8` is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed

**Added 2026-10-03 (landing review):**
- Given the rendered grants When the retention role runs the purge's DELETE with its WHERE clause and inserts the purge row Then both succeed, and an UPDATE by the retention role is refused. Test the rendered SQL for SELECT, INSERT and DELETE to the retention role and no UPDATE to either role.
- Given `app_role` and `retention_role` name the same role (in any letter case) When the grants render Then they refuse with a `ValueError`.

## Boundaries & Constraints

**Always:** Generate the Django migration and keep `makemigrations --check` green (AGENTS.md pre-PR item 3). Fix each defect where the shipped behaviour lives and pin it with a test that fails without the fix.

**Never:** Never let the app role delete audit rows.

</intent-contract>

## Deferred-work rows this story closes (operator rulings 2026-10-03, deferral burn-down Phase 3)

- `DW-9-3-3` — Record purges: add AuditAction.PURGE and a required keyword `actor` (the retention job's identity) to purge_expired_entries, and write one purge row (row_count = rows deleted, target = cutoff) in the same transaction as the delete, with a migration and tests.
- `DW-9-3-8` — Make the audit trail append-only by privilege: `steward deploy` (Story 9.5 perimeter) renders SQL granting the app role only SELECT and INSERT on the audit table, with DELETE granted to a separate retention role that runs purge_expired_entries; test the rendered SQL.

## Binding

Parent: The steward capabilities that shipped each behaviour (Epic 9's audit trail, Story 9.1's ingress)
Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-03 (Phase 3) entry.
Ledger key: `84-1-an-audit-purge-records-itself-and-the-audit-table-is-append-only-by-privilege`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 from the operator's Phase 3 rulings (rulings page `rulings` collection; "group them by module, as Phase 2 did").

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Spec Change Log

- 2026-10-03 — sent back by the operator session after the landing review (findings below). Two acceptance criteria added. Status back to `ready-for-dev`.

## Review Triage Log

### 2026-10-03 — Landing review (operator session) — sent back
The rendered grants were applied to a real PostgreSQL 17 cluster: a table shaped like `pyforge_steward_dashboard_auditentry` (identity `id`), owned by a migration role, with roles `app` and `retention`.
- The app role works as intended: INSERT succeeds; UPDATE and DELETE are refused.
- `high` `patch` **The retention role cannot purge.** `render_audit_table_grants` grants it DELETE only.
  - Its `DELETE ... WHERE occurred_at < ...` (what `purge_expired_entries` runs) fails with `permission denied for table pyforge_steward_dashboard_auditentry`, because PostgreSQL needs SELECT on the columns a WHERE clause reads.
  - The purge row `purge_expired_entries` writes in the same transaction also fails: the retention role has no INSERT.
  - So the third acceptance criterion fails on a real database. Fix: grant the retention role SELECT, INSERT and DELETE, and never UPDATE.
- `medium` `patch` **The same role can be named twice.** `render_audit_table_grants(app_role="app", retention_role="app")` renders `GRANT DELETE ... TO app`. That breaks the Never rule: never let the app role delete audit rows. Fix: refuse equal roles (compare case-insensitively, since unquoted PostgreSQL identifiers fold to lower case).

### 2026-10-03 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (orchestrator self-review after implementation; no subagent layer this run)

## Auto Run Result

- Summary: Added `AuditAction.PURGE`, required `actor` on `purge_expired_entries` with a transactional purge audit row; `steward deploy perimeter` now renders append-only PostgreSQL grants for the audit table.
- Files: `dashboard/audit.py`, `dashboard/models.py`, migration `0006_auditaction_purge.py`, `deploy.py`, `cli.py`, `test_dashboard_audit.py`, `test_deploy_perimeter.py`, `deferred-work-ledger.md` (closed DW-9-3-3, DW-9-3-8).
- Verification: `pyforge-steward-test` 1979 passed; `lint-types` exit 0; `python scripts/spec_surface_reconcile.py` OK.
- Follow-up review recommended: false
- Residual risks: In-process ORM can still bypass DB grants until adopters apply the rendered SQL; purge recording uses the same DB alias as delete but `record_audit_entry` does not pass `using=`.
