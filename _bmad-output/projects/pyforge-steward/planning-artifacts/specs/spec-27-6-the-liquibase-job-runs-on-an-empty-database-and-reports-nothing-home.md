---
title: 'The Liquibase Job runs on an empty database and reports nothing home'
type: 'fix'
created: '2026-09-26'
status: 'done'
baseline_revision: '27c8f1869103835bedc996170a6436a1774b18e4'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-27-2-pre-upgrade-job-and-dml-only-app-role.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-27-5-the-jdbc-driver-ships-under-its-own-name.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** Two defects, both found while verifying Story 27.5 end to end against PostgreSQL 17.
1. On an empty database the Story 27.2 pre-upgrade Job fails at `python-agent-platform:18` (`third-party-0001`): allauth's `socialaccount_socialapp_sites` takes a foreign key to `django_site`, but the master changelog includes `:10`-`:13` (`django.contrib.sites`) after `:18`. Every Liquibase test was static, so nothing applied the changelog to an empty database.
2. Liquibase 5 ships a usage-data clause and reports usage analytics (commands, timestamps, version, database type). With `liquibase.analytics.enabled` unset it first fetches `https://config.liquibase.com/analytics.yaml`. Nothing in the platform turned it off. In the cluster, the Job's NetworkPolicy (Postgres + DNS only) stops the data leaving but not the DNS lookup and timeout; `platform-dev` and CI have no such fence.

**Approach:** Move the four `sites` includes ahead of `:18`, and add a policy test that fails on any foreign key whose target table a later include creates. Set `LIQUIBASE_ANALYTICS_ENABLED = "false"` in `[feature.python-agent-platform.activation.env]`. The image sources that env's `pixi shell-hook` and `platform-dev` composes the feature, so one setting covers the Job, every pod, and local runs. Add a policy test for the switch.

## Boundaries & Constraints

**Always:** Changeset ids, authors and file paths stay unchanged, so already-migrated databases skip every applied changeset and see no difference. Cite canopy:FR-21a / canopy:FR-24 / canopy:AD-9.

**Never:** Edit a changeset's SQL. Add a Liquibase-specific egress rule. Disable analytics per invocation only (argv or properties file): an ad hoc `liquibase` run in a pod would miss it.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Live changelog | `db.changelog-master.yaml` + `changes/*.sql` | No include references a table a later include creates | Names the include, the table and the later creator |
| Forward reference | `a.sql` references `site`, `b.sql` (later) creates it | One finding | Reversed order: none |
| Analytics switch | `pixi.toml` python-agent-platform activation env | `LIQUIBASE_ANALYTICS_ENABLED == "false"` | Missing or `"true"` fails |
| Existing database | Changesets already in `databasechangelog` | Skipped by id; no re-run | n/a |

</intent-contract>

## Code Map

- `src/platform/db/changelog/db.changelog-master.yaml` -- `:10`-`:13` (sites) moved ahead of `:18`, with a comment
- `src/platform/tests/policy/test_liquibase_ddl_governance.py` -- `_foreign_keys_ahead_of_their_table`; live-tree test and a drift test
- `pixi.toml` -- `[feature.python-agent-platform.activation.env]` `LIQUIBASE_ANALYTICS_ENABLED = "false"`
- `src/platform/tests/policy/test_liquibase_channel_policy.py` -- analytics switch asserted, with a drift test
- `src/platform/Containerfile` -- shell-hook scan note names the new variable

## Tasks & Acceptance

**Execution:**
- Reorder, switch and tests as above.

**Acceptance:**
- `pixi run -e pyforge-guild platform-ci-local --test`: the Policy suite passes.
- The ordering test fails on the pre-27.6 changelog (one finding: `:18` references `django_site`, created later by `:10`).
- `pixi lock` and `environment.yaml` are unchanged (activation env is not solver input).
- Liquibase 5.0.4 applies all 27 changesets to an empty PostgreSQL 17 through `python -m db.liquibase_update`, inside pixi activation, and logs `liquibase.analytics.enabled` = `false` from the environment without loading the remote analytics configuration.

## Outcome

Verified locally 2026-09-26.
- Before the reorder, the ordering test reported exactly one finding (`:18` -> `django_site`, created by `:10`); after it, none.
- `pixi shell-hook` renders `export LIQUIBASE_ANALYTICS_ENABLED=false`.
- In a scratch env of liquibase + liquibase-postgresql 5.0.4 (conda-forge) and pgjdbc 42.7.13, with PostgreSQL 17.11 + pgvector, the reordered changelog applied 27 of 27 changesets to an empty database. The schemas were `public`, `langflow_schema`, `dbgpt_schema`, `liquibase`.
- At FINE log level, Liquibase read the switch from the environment; `LiquibaseRemoteAnalyticsConfiguration` never loaded. Without the switch it loads and consults `config.liquibase.com` (1500 ms timeout).
