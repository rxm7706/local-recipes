---
title: 'The JDBC driver ships under its own name'
type: 'chore'
created: '2026-09-26'
status: 'done'
baseline_revision: '88fc0218759906310b38ed32b64a4a1f6b190757'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-27-1-liquibase-on-the-channel-operator-gate.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** Story 27.1 pinned `liquibase-postgresql >=42.7.13`, which on SelfExplainML was the pgjdbc JDBC driver (`postgresql.jar`) published under a name conda-forge uses for a different artifact: Liquibase's PostgreSQL dialect extension (5.0.4, no driver). The driver is now its own recipe, `pgjdbc` (on SelfExplainML; submitted to conda-forge as staged-recipes #34956), and the local `liquibase-postgresql` recipe mirrors the conda-forge feedstock. The operator wants liquibase, liquibase-postgresql and pgjdbc all from conda-forge.

**Approach:** Pin `pgjdbc >=42.7.13` for the driver and `liquibase-postgresql = { version = ">=5.0.4,<42", channel = "conda-forge" }` for the extension. `<42` is needed because `pixi lock` keeps an already-locked record that satisfies the version even when its channel no longer matches; it also excludes the retired build in any fresh solve. Flip the 27.1 policy test to assert the three pins and the locked channels.

## Boundaries & Constraints

**Always:** Pins stay on `[feature.python-agent-platform.dependencies]`. `liquibase` stays `>=5.0.4`. The driver keeps installing `share/liquibase/lib/postgresql.jar`, the path `db/liquibase_update.py` relies on (no `--classpath`). Cite canopy:FR-21 / canopy:AD-16.

**Never:** Change the Helm Job, the changelog, or the DML-only role (Story 27.2). Channel-pin `pgjdbc` to SelfExplainML: with the feature's flexible channel priority, it moves to conda-forge on the lock refresh after #34956 publishes. Delete the SelfExplainML `liquibase-postgresql` 42.7.13 artifact (an operator decision).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Pins | Live `pixi.toml` python-agent-platform deps | `liquibase >=5.0.4`, `pgjdbc >=42.7.13`, `liquibase-postgresql` `>=5.0.4,<42` on conda-forge | Any other spec fails |
| Pre-27.5 spec | `liquibase-postgresql = ">=42.7.13"` | Assertion fails | Names liquibase-postgresql |
| Lock | `pixi.lock` python-agent-platform URLs | liquibase >=5.0.4; pgjdbc >=42.7.13; every liquibase-postgresql URL is conda-forge and <42 | Missing or wrong channel fails |
| Retired build locked | SelfExplainML `liquibase-postgresql-42.7.13` URL | Assertion fails | Names 42.7.13 |

</intent-contract>

## Code Map

- `pixi.toml` -- `[feature.python-agent-platform.dependencies]`: `pgjdbc = ">=42.7.13"`, `liquibase-postgresql = { version = ">=5.0.4,<42", channel = "conda-forge" }`
- `pixi.lock` -- `python-agent-platform` / `platform-dev`: SelfExplainML `liquibase-postgresql` 42.7.13 replaced by SelfExplainML `pgjdbc` 42.7.13 and conda-forge `liquibase-postgresql` 5.0.4
- `src/platform/tests/policy/test_liquibase_channel_policy.py` -- pgjdbc pin and lock floor; extension spec and conda-forge lock channel; drift tests for the pre-27.5 spec and the retired build
- `docs/reference/library-llms-full.md` -- `liquibase-postgresql` and `pgjdbc` entries

## Tasks & Acceptance

**Execution:**
- Pins, lock and policy test updated as above.

**Acceptance:**
- `pixi run -e pyforge-guild platform-ci-local --test`: the Policy suite passes.
- `pixi lock` solves every environment; the lock diff is limited to the three Liquibase-family records.
- Liquibase 5.0.4 with conda-forge `liquibase-postgresql` 5.0.4 and `pgjdbc` 42.7.13 loads both jars and applies the platform changelog to PostgreSQL 17 through `python -m db.liquibase_update`.

## Outcome

Verified locally 2026-09-26 in a scratch env built from exactly those three packages plus PostgreSQL 17.11 and pgvector. `liquibase --version` lists `lib/liquibase-postgresql-5.0.4.jar` and `lib/postgresql.jar` (PostgreSQL JDBC Driver 42.7.13). The driver carried the changelog into PostgreSQL. On an empty database the run stopped at changeset 18 (`third-party-0001`: FK to `django_site`), which the master changelog includes before `sites-0001` (changeset 10). That ordering defect predates this story. With the sites includes moved ahead of changeset 18 in a scratch copy, all 27 changesets applied and the four schemas matched Story 27.2.
