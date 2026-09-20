---
title: 'Stale extraction fails CI'
type: 'feature'
created: '2026-08-25'
status: 'done'
baseline_revision: '23f8562970fa83083ab4fac93f43c4adf56693a4'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-27-2-pre-upgrade-job-and-dml-only-app-role.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** A developer can change a first-party Django model and ship a migration without a Liquibase changeset, so production DDL (Job weight −1) drifts from what CI reviewed.

**Approach:** Add a `sqlmigrate` extraction check that every first-party production migration maps to an existing `distribution:seq` changeset (`python-agent-platform:N` on this tree) whose SQL covers the extracted statements; CI fails and names the missing changeset. Invention, not a third-party Django/Liquibase plugin.

## Boundaries & Constraints

**Always:** Reuse the 27.2 changelog tree (`src/platform/db/changelog/`, ids `python-agent-platform:N`). Gate first-party production migration modules (platform local apps + `django-*` packs in INSTALLED_APPS), not Django/Wagtail/allauth contrib. Wire through Platform CI pytest/policy lane (`tests/policy`) plus a named `sqlmigrate` step; no CRC/live cluster. Spec at `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward`.

**Block If:** A change would rewrite the 27.2 Helm Job contract or `manage.py test`.

**Never:** 27-4 test-runner rewrite. Helm `liquibase-job.yaml` / `migrate --fake` edits. Fifth schema. Bare id `001-initial`. Second changelog tree. `import pyforge` under `src/platform/`. Recipes. `scripts/bmad-switch`. Story 12-7.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Missing changeset | First-party migration with no map/changelog id | Check fails; message names the missing `python-agent-platform:N` | Exit 1 |
| Matching changeset | Migration + changeset whose SQL covers `sqlmigrate` statements | Check green | No error |
| SQL stale | Mapped id exists but extracted DDL not in changeset body | Check fails; names that changeset id | Exit 1 |
| Shared schema id | langflow/dbgpt `0001` → `python-agent-platform:1` | CREATE SCHEMA statements covered by existing :1 | Do not invent a second schemas file |

</intent-contract>

## Code Map

- `src/platform/db/changelog/db.changelog-master.yaml` -- 27.2 master; append includes only
- `src/platform/db/changelog/changes/python-agent-platform-1-schemas.sql` -- keep; covers schema RunSQL
- `src/platform/db/changelog/changes/python-agent-platform-2-app-role-grants.sql` -- keep; no Django migration
- `src/platform/db/sqlmigrate-map.yaml` -- NEW app_label.name → seq
- `src/platform/db/sqlmigrate_extraction.py` -- NEW loader + `sqlmigrate` + diff + CLI
- `src/platform/tests/policy/test_sqlmigrate_extraction.py` -- synthetic red/green + live tree
- `src/platform/tests/policy/test_typing_policy.py` -- add `db` to mypy targets if CI mypy lists it
- `.github/workflows/platform-ci.yml` -- named sqlmigrate step beside Policy suite
- Read-only: `db/liquibase_update.py`, Helm Jobs, `manage.py`, `recipes/`

## Tasks & Acceptance

**Execution:**
- `src/platform/db/sqlmigrate_extraction.py` -- implement gate + `python -m db.sqlmigrate_extraction`
- `src/platform/db/sqlmigrate-map.yaml` + changelog includes -- map every first-party production migration; extract uncovered DDL into new `python-agent-platform:N` files (do not replace :1/:2)
- `src/platform/tests/policy/test_sqlmigrate_extraction.py` -- matrix rows
- `.github/workflows/platform-ci.yml` -- named step; keep Policy suite collecting `tests/policy`

**Acceptance Criteria:**
- Given a model/migration change with no matching Liquibase changeset, when CI runs sqlmigrate extraction, then the check fails and names the missing changeset
- Given a matching changeset, when the same check runs, then it passes
- Given the 27.2 Job templates, when this PR is reviewed, then they are unchanged

## Spec Change Log

## Review Triage Log

### 2026-08-25 — Implementation self-review (dispatch; no nested reviewers)

- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none. Confirmed: `python -m db.sqlmigrate_extraction` and `tests/policy/test_sqlmigrate_extraction.py` fail naming `python-agent-platform:N` when a first-party migration has no changeset; matching SQL is green; 14 live first-party migrations mapped onto the 27.2 changelog tree (`python-agent-platform:1` shared for schema RunSQL). Helm Jobs unchanged. Did not start 27-4 or 12-7.

## Auto Run Result

Status: done
Reconciled 2026-09-20: the `in-review` verdict below is the session's own record at halt time; the story was landed afterwards and the ledger row promoted to `done` by `598f40d026 2026-08-25 chore(steward): 27-3 ledger finalize` — that promotion is the ruling this record now reflects.
Tests: `pytest tests/policy` → 53 passed (cwd src/platform); `python -m db.sqlmigrate_extraction` → ok (14 migrations)


## Design Notes

First-party = migration modules whose path sits under `src/platform/` or `src/shared/packages/django-*`. Test-only `django_pyforge.probe_portal` / `workclass_probe` are excluded. Framework apps stay Django-authored; canopy:FR-23 is the authoring gate for *our* models. Coverage is statement-subset (normalized), so langflow and dbgpt `0001` share `:1`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Status reconcile 2026-09-20

- frontmatter `status` `in-review` → `done` (ledger row `27-3-stale-extraction-fails-ci: done`).
- Auto Run Result `Status: in-review` → `done` (see the reconcile line under it).
