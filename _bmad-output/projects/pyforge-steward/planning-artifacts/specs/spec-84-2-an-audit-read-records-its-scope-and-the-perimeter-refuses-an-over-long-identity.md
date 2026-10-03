---
title: "84.2: An audit read records its scope, and the perimeter refuses an over-long identity"
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

**Problem:** Audit-read gaps the operator ruled to fix: every AUDIT_READ row records the same constant 'of what', so reads are indistinguishable; an identity or role longer than the audit columns reaches the database. The same read path carries the open rows DW-9-3-2 and DW-9-3-4.

**Approach:** Add a JSON `scope` field to AuditEntry (with a migration) holding the read's validated filters as sorted lookups; refuse at DashboardIdentityMiddleware any identity or role longer than one shared constant in declarations.py that the columns use; fix DW-9-3-2 and DW-9-3-4 on the same path.

Ledger key: `84-2-an-audit-read-records-its-scope-and-the-perimeter-refuses-an-over-long-identity`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- The steward capabilities that shipped each behaviour (Epic 9's audit trail, Story 9.1's ingress); a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given two different reads When they are audited Then two rows record two different scopes
- Given an identity longer than the shared limit When it reaches the middleware Then the request is refused naming the limit, before any write
- Given this story lands When its deferred-work rows are read Then each of `DW-9-3-10`, `DW-9-3-9`, `DW-9-3-2`, `DW-9-3-4` is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed

## Boundaries & Constraints

**Always:** Generate the migration; keep `makemigrations --check` green. Fix each defect where the shipped behaviour lives and pin it with a test that fails without the fix.

**Never:** Never truncate an identity silently.

</intent-contract>

## Deferred-work rows this story closes (operator rulings 2026-10-03, deferral burn-down Phase 3)

- `DW-9-3-10` — Record each read's scope: add a JSONField `scope` to AuditEntry (with a migration); query_audit_entries stores its validated **filters as sorted lookups with string values; a test shows two different reads write two different rows.
- `DW-9-3-9` — Reject over-long identities at the perimeter: DashboardIdentityMiddleware refuses, before the response starts and naming the limit, any identity or role longer than one shared constant in declarations.py that AuditEntry.actor and .role also use as max_length (still 255, so no migration).
- `DW-9-3-2` — Open sibling on the same code path (not a ruling); fixed in this bundle under the fix-now default.
- `DW-9-3-4` — Open sibling on the same code path (not a ruling); fixed in this bundle under the fix-now default.

## Binding

Parent: The steward capabilities that shipped each behaviour (Epic 9's audit trail, Story 9.1's ingress)
Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-03 (Phase 3) entry.
Ledger key: `84-2-an-audit-read-records-its-scope-and-the-perimeter-refuses-an-over-long-identity`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 from the operator's Phase 3 rulings (rulings page `rulings` collection; "group them by module, as Phase 2 did").

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
