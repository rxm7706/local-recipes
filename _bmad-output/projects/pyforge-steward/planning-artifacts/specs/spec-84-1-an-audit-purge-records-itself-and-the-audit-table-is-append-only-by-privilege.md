---
title: "84.1: An audit purge records itself, and the audit table is append-only by privilege"
type: 'fix'
created: '2026-10-03'
status: 'ready-for-dev'
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

## Review Triage Log

- No review has run yet.
