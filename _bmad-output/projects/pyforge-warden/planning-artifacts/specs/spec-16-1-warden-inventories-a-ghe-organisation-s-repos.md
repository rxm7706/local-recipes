---
title: "16.1: Warden inventories a GHE organisation's repos"
type: 'feature'
created: '2026-09-28'
status: 'blocked'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - docs/dreams/pyforge-warden.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - src/shared/packages/django-warden/src/django_warden_fabric/models.py
  - src/shared/packages/django-warden/src/django_warden_fabric/tasks.py
  - src/platform/db/README.md
flag:
  key: pyforge.warden.fleet_inventory
  provider: openfeature-file
  default: {production: off, staging: on, dev: on}
  scope: global
  fallback: "no fleet inventory exists; the inventory action is listed as disabled and refuses"
  cleanup: 90 days after ON in every environment (Q4)
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Blocked (cross-station):** the inventory reads a GitHub Enterprise organisation with credentials Steward provides
(steward Story 75.1, the GHE host credentials). The Deps parser is station-local, so the ledger row is minted `blocked`;
the operator flips it once steward 75.1 is `done` and the worker's environment carries the GHE host, token and
organisation the way that story defines.

**Problem:** Warden scans one repo per invocation and has no notion of a fleet. The operator ruled on 2026-09-28 that
Warden scans the enterprise fleet on GitHub Enterprise, lifting the Non-goal "Fleet aggregation"; the first thing a
fleet run needs is the list of repos, and other stations need it too (Atlas's dependency history,
`spec-pyforge-atlas:CAP-61`).

**Approach:** In `django_warden_fabric` (spine § Currency reconciliation — 2026-09-28, Decision 2): a `FleetRepo` model
(organisation, full name, default branch, clone URL, archived, last-seen), a `fleet.py` that pages the GHE REST
organisation-repos listing through an injectable client (the actuator's `resolve_forge` shape: `GITHUB_API_URL` names
the GHE host), and a keys-not-blobs Celery task that upserts the rows idempotently and writes the inventory as one JSON
document at a configured path (`WARDEN_FLEET_INVENTORY_PATH`, beside the fabric's blob root). The export is the only
face other stations read; nobody imports `django_warden_fabric` or `pyforge.warden` for it. The model ships a Django
migration and its covering Liquibase changeset (`src/platform/db/`, the `sqlmigrate-extraction` gate). The inventory
action (portal button and management command, one code path) reads the flag through `pyforge.core.flags.read_boolean` (steward Story 75.1's contract); OFF, it is
listed as disabled and refuses.

Ledger key: `16-1-warden-inventories-a-ghe-organisation-s-repos`.
Ledger status (do not edit the ledger): `blocked`.
Type / Effort / Deps: feature / M / — (cross-station: steward Story 75.1).

### Living CAP citations

- `spec-pyforge-warden` CAP-26 (FR-43); CAP-16 (the service skeleton, keys-not-blobs).
- `spec-pyforge-atlas:CAP-61` (reads the export); `spec-feature-flag-governance:CAP-1`.

## Acceptance Criteria

- Given a fixture GHE organisation of three repos behind the injectable client, When the inventory task runs, Then three `FleetRepo` rows exist and the export lists the same three repos with full name, default branch and clone URL
- Given the same organisation listed twice, When the task runs again, Then the rows are updated in place, not duplicated
- Given a paginated listing, When it spans pages, Then every page is read
- Given the Celery message, When it is inspected, Then it carries only ids and the organisation name (keys-not-blobs), never a token
- Given a missing credential, When the task runs, Then it fails with a typed error naming the missing variable and writes no partial export
- Given the flag OFF, When the operator opens the portal or runs the management command, Then the action is listed as disabled and refuses (the command exits 2, warden's usage code)

## Boundaries & Constraints

**Always:**
- Live in `django-warden`; the `pyforge.warden` scan process gains no socket.
- Take credentials from the environment Steward provisions, never from a model field, a flag or a log line.
- Ship the migration with its covering Liquibase changeset; `platform-ci-local -- --test` green.
- Read the flag only through `pyforge.core.flags.read_boolean` (steward Story 75.1's contract) over the one tree (canopy:AD-11). If 75.1 has not landed when this story runs, add it in `pyforge.core` in exactly 75.1's shape (`read_boolean(key, default=False)`, `cutover_root.py`'s tree resolution, False with a named WARN for a missing tree, key or non-bool value; a `spec-pyforge-core` co-governor reconcile) — never a station-local reader or a second tree. Add the key to `src/platform/config/flags.json` (default OFF). The portal view runs inside the host, where `pyforge` may be absent; there, and only there, it evaluates the same key through `django_pyforge.flags`, the Guild's other sanctioned reader.
- Reconcile every Spec `spec-surface-check` names for the touched paths (`django-warden` and `src/platform/` are co-governed by steward's `spec-pyforge-unifying-strategy`); scoped stamps only.

**Never:**
- Clone or scan here (Story 16.2).
- Add a webhook, a FastAPI or SQLAlchemy service, or a gitgres store.
- Reach GHE from the test suite.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| three repos | fixture org | three rows, three-entry export | — |
| re-run | same org | rows updated, no duplicates | — |
| archived repo | `archived: true` | row kept, flagged archived | — |
| no token | env missing | no export | typed error naming the variable |
| GHE 5xx | listing fails | no partial export | job `failed` with the error |
| flag OFF | key off | action disabled | refuses, exit 2 |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-warden` CAP-26 (FR-43).
Dream: `docs/dreams/pyforge-warden.md` § Realization log → *2026-09-28 (night) — Proposed: the fix-PR actuator finishes the fix, SAST joins as a plugin, and Warden scans the enterprise fleet*.
Ledger key: `16-1-warden-inventories-a-ghe-organisation-s-repos`.
Ledger status at mint: `blocked` — until steward Story 75.1 (GHE host credentials) is `done`; the operator flips the row.
Deps: — (cross-station: steward Story 75.1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: pass (the `django-warden` tests live under `src/platform/tests/`, and the migration's covering changeset passes `sqlmigrate-extraction`).
- Flag ON/OFF: a test writes two flagd trees (`pyforge.warden.fleet_inventory` on, then off; the `src/platform/tests/test_openfeature_file_flags.py` shape until the `spec-feature-flag-governance:CAP-4` fixture lands): ON runs the inventory, OFF lists the action as disabled and refuses with exit 2.
- `pixi run -e pyforge-guild spec-surface-check` exits 0 after the scoped stamps.

## Review Triage Log

- No review yet (minted 2026-09-28, `blocked`). Implementation and review stay separate.
