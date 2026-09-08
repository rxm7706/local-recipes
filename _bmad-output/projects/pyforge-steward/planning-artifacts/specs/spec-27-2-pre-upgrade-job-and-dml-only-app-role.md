---
title: 'Pre-upgrade Job and DML-only app role'
type: 'feature'
created: '2026-08-25'
status: 'done'
baseline_revision: '526da9eb661b8cf2087ba1c71deff0b44239799c'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md
warnings:
  - oversized
deferred: []
---

<intent-contract>

## Intent

**Problem:** Production schema change still runs as `manage.py migrate` on the hook-weight 0 Job, so the application role can ALTER the database and there is no Liquibase audit trail.

**Approach:** Add a Helm Job at hook-weight −1 on the same platform image that runs `liquibase update`, flip the shipped Job to `migrate --fake`, and make the app role DML-only at PostgreSQL (migration role holds DDL).

## Boundaries & Constraints

**Always:** Hook weights: Liquibase −1 then migrate 0; both `post-install,pre-upgrade`. Same image as web. `preserveSchemaCase` off; schema names lowercase; Job JDBC URL carries `currentSchema` and the host is the chart's PostgreSQL Service, not a pooling proxy. Schemas are exactly `public`, `langflow_schema`, `dbgpt_schema`, `liquibase` (`liquibaseSchemaName=liquibase`). `run_state` and `mcp_handles` stay tables in `public`. Changeset ids are `distribution:seq`. App role `CREATE`/`ALTER`/`DROP` refused by PostgreSQL. No init container. Spec lives at `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward`. Prefer helm render + SQL/policy tests; do not run 12-7 CRC.

**Block If:** Liquibase 5.0.4+ is missing from the platform env (27.1 must stay done).

**Never:** 27-3 `sqlmigrate` CI gate. 27-4 test-runner rewrite (`manage.py test` still Django `migrate`). Fifth schema or promoting `run_state`/`mcp_handles` to schemas. Bare changeset id `001-initial`. Second image. Init container. Recipe authoring. `import pyforge` under `src/platform/`. `scripts/bmad-switch`. Start 27-3, 27-4, or 12-7.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Chart render | `helm template` core chart | Two Jobs: liquibase weight −1 args `liquibase update` path; migrate weight 0 args include `migrate --fake`; same image as web; no initContainers on those Jobs | Render failure fails the test |
| Schema case | Changelog + liquibase.properties | `preserveSchemaCase` false; CREATE SCHEMA names lowercase only | Mixed-case name fails the check |
| Four schemas | Changelog CREATE SCHEMA + properties | Only `langflow_schema`, `dbgpt_schema` created in SQL; tracking schema `liquibase`; `public` implied | Fifth schema name fails the check |
| Changeset ids | `--changeset` lines | Shape `distribution:seq` (e.g. `python-agent-platform:1`) | Bare `001-initial` fails |
| Direct PG | JDBC builder input host `release-postgres` | URL contains `currentSchema=public`; pooling hostnames rejected | `pgbouncer`/`pgpool` host fails |
| App role DDL | PostgreSQL role with CREATE revoked | `CREATE`/`ALTER`/`DROP` raise insufficient_privilege | App guard instead of PG error fails |

</intent-contract>

## Code Map

- `src/platform/deploy/charts/platform/templates/migrate-job.yaml` -- today weight `"0"` and `migrate --noinput`; become `migrate --fake`
- `src/platform/deploy/charts/platform/templates/liquibase-job.yaml` -- NEW hook Job weight −1, component `liquibase`, same `platform.imageRef` as web
- `src/platform/deploy/charts/platform/templates/_helpers.tpl` -- `platform.liquibase.fullname`; `platform.liquibaseEnv` (`MIGRATION_DATABASE_URL` secretKeyRef); existingSecret key list
- `src/platform/deploy/charts/platform/values.yaml` -- `liquibase.backoffLimit`; `postgres.auth.appUsername`; secret key comments
- `src/platform/db/liquibase_update.py` -- parse `MIGRATION_DATABASE_URL` → JDBC `currentSchema=public`; exec `liquibase update`; reject pooler hosts
- `src/platform/db/liquibase.properties` -- `preserveSchemaCase: false`, `liquibaseSchemaName: liquibase`
- `src/platform/db/changelog/db.changelog-master.yaml` -- includeAll of `changes/`
- `src/platform/db/changelog/changes/python-agent-platform-1-schemas.sql` -- formatted SQL changeset `python-agent-platform:1`
- `src/platform/db/create_app_role.sql` -- operator SQL: DML-only `platform_app`
- `src/platform/tests/test_chart_invariants.py` -- two Jobs, weights, image, no initContainer, `--fake`
- `src/platform/tests/policy/test_liquibase_ddl_governance.py` -- schema names, ids, preserveSchemaCase, JDBC helper, app-role PG proof
- `src/platform/deploy/README.md` + `NOTES.txt` + overlay bring-up -- `MIGRATION_DATABASE_URL` vs `DATABASE_URL`
- Read-only: `src/platform/tests/policy/test_liquibase_channel_policy.py` (27.1); Django test runner; `recipes/`

## Tasks & Acceptance

**Execution:**
- `src/platform/deploy/charts/platform/templates/liquibase-job.yaml` -- Job weight −1, `python db/liquibase_update.py`, no initContainers
- `src/platform/deploy/charts/platform/templates/migrate-job.yaml` -- args `migrate --fake --noinput`
- `src/platform/db/**` -- properties, changelog, update helper, app-role SQL
- Helpers + values + NOTES/README -- migration URL secret key, app username
- Tests -- helm invariants + policy + postgres privilege (skip if not postgresql)

**Acceptance Criteria:**
- Given a chart upgrade, when hooks run, then Job weight −1 runs `liquibase update` on the platform image, then the shipped Job runs `migrate --fake`
- Given `preserveSchemaCase`, when checked, then it is off; schema names are lowercase; the Job connects directly with `currentSchema`
- Given this instance, when schemas are listed, then they are exactly `public`, `langflow_schema`, `dbgpt_schema`, `liquibase`
- Given the app role, when it issues `CREATE`/`ALTER`/`DROP`, then PostgreSQL refuses; no init container
- Given changeset ids, when scanned, then they are `distribution:seq`

## Spec Change Log

## Review Triage Log

### 2026-08-25 — Implementation self-review (dispatch; no nested reviewers)

- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none. Confirmed: two hook Jobs (weight −1 `liquibase update` via `db/liquibase_update.py`, weight 0 `migrate --fake`); no initContainers; same image as web; four lowercase schemas; changeset ids `python-agent-platform:1`/`2`; preserveSchemaCase false; JDBC `currentSchema` and pooler-host rejection; app-role CREATE/ALTER/DROP refused by PostgreSQL. Did not start 27-3, 27-4, or 12-7. No `import pyforge` under `src/platform/`. No recipes.

## Auto Run Result

Status: done

Helm render invariants + changelog/JDBC policy + DML-only role proof (local PostgreSQL). Compose still uses Django `migrate` for local/test DBs (27.4). `sqlmigrate` CI gate not added (27.3).


## Design Notes

`POSTGRES_USER` (`platform`) remains the migration/owner role. `DATABASE_URL` is the app role (`platform_app`) in production; `MIGRATION_DATABASE_URL` is the owner URL used only by the Liquibase Job. The chart still never renders a Secret. Compose `manage.py migrate` for local/test DBs stays 27.4. Fresh-install table DDL beyond CREATE SCHEMA is 27.3's sqlmigrate extraction; this story ships the governed Job path and the four-schema changelog.

Liquibase formatted SQL:

```sql
--changeset python-agent-platform:1
CREATE SCHEMA IF NOT EXISTS langflow_schema;
CREATE SCHEMA IF NOT EXISTS dbgpt_schema;
```

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
