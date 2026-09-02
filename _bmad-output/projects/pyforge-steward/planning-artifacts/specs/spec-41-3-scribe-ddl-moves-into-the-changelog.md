---
title: "Scribe DDL moves into the changelog"
type: "fix"
created: "2026-09-02"
status: "in-review"
updated: "2026-09-02"
baseline_commit: "58ee07a0"
severity: "HIGH"
context:
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/resilience-invariants.md"
  - "src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_pg.py"
  - "src/platform/db/changelog/"
  - "src/platform/db/sqlmigrate-map.yaml"
warnings: []
deferred:
  - "Per-station schema ownership enforcement beyond scribe (fleet sweep)."
---

<intent-contract>

## Intent

**Problem:** `graph_store_pg.py` executes `CREATE EXTENSION IF NOT EXISTS vector`, `CREATE
SCHEMA` and `CREATE TABLE IF NOT EXISTS` at runtime. CAP-9 revokes DDL from the
app role (`platform_app`), so in production this fails with `permission denied`
or tempts a `GRANT` that defeats the auditor control; `CREATE EXTENSION`
additionally needs superuser or a trusted-extension grant. `sqlmigrate-map.yaml`
has no scribe entry and is a single global sequence for one distribution.
Red-team **S-4**, **B-1**, directive **R-12**.

**Approach:** Move the three statements into a Liquibase changeset owned by scribe under a
per-distribution id (`pyforge-scribe:N`), make the runtime path assert-only
(fail loudly if the relation is absent), and extend `sqlmigrate-map.yaml` to a
per-distribution map so a station owns its own sequence. Write the rollback
policy: every changeset carries `rollback:` or a documented
`runInTransaction=false` exception.

## Acceptance Criteria

- Given `platform_app`, when Scribe's PostgreSQL driver initialises, then it executes no DDL; a test with a DDL-revoked role passes and the relation-absent case raises a named error.
- Given the changelog, when `liquibase update` runs, then `scribe_schema`, the `vector` extension and the graph table exist; the changeset has a `rollback:` block.
- Given `sqlmigrate-map.yaml`, when read, then ids are `<distribution>:<seq>` with at least `python-agent-platform` and `pyforge-scribe` distributions, and the sqlmigrate extraction gate still passes.
- Given `db/README` (or the changelog header), when read, then the rollback policy and the `runInTransaction=false` exception process are written down.

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-steward/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`.
Ledger key `41-3-scribe-ddl-moves-into-the-changelog`. Host never imports `pyforge.*`. Contrib and engine tables stay as CAP-9 shipped them. Liquibase from the conda feedstock on the platform image.

**Block If:** Implementation would grant `CREATE` to `platform_app`, run DDL from an initContainer, or fold the map back into one sequence.

**Never:** Runtime `CREATE EXTENSION` from any station. A changeset without rollback or a documented exception.

</intent-contract>

## Tasks

- [x] Changeset + map entry
- [x] Driver assert-only path + tests
- [x] Rollback policy doc
- [x] CI `sqlmigrate` gate still green
- [x] Ledger `41-3-scribe-ddl-moves-into-the-changelog` → `review`; **`done` is the landing step's** (the Tier-3 feed `sprint-ledger-sync` promotes from does not exist in a dispatch worktree, so the tracked twin carries the row directly).

## Dev Notes

**2026-09-02 — implemented.** Three changesets, not one, because Liquibase
applies preconditions per changeset: folding the guarded `platform_app` grants
in with the DDL would have skipped the DDL too on a database where the app role
does not exist. `pyforge-scribe:1` is the extension, `:2` the schema + table,
`:3` the grants behind the same `onFail:CONTINUE` role-exists precondition
`python-agent-platform:2` already uses.

`sqlmigrate-map.yaml` grew a `default:` key alongside `distributions:`;
`load_map` now returns a `MigrationMap` and `expected_changeset_id` numbers the
next id **within** a distribution, so a station sitting at `:40` no longer
pushes the platform's next id past `:7`. `pyforge-scribe` registers with an
empty `migrations: {}` — its schema is hand-authored, not a Django migration —
which keeps the id space declared in one place.

The rollback policy is forward-looking: `python-agent-platform:1`–`:19` shipped
before it existed and are grandfathered by a closed literal list in
`test_liquibase_ddl_governance.py`, so a new changeset cannot join them
silently. Backfilling rollbacks onto shipped contrib/engine DDL was out of
bounds (Boundaries).

The scribe test fixture now provisions its database *from the changesets*
(`tests/unit/conftest.py`), so the DDL has exactly one source and a drifted
changeset reds the driver suite. Guarded changesets are skipped there, matching
what Liquibase itself does when `platform_app` is absent.

**Live verification against PostgreSQL 17.11 + pgvector (:5433).**

- Real `liquibase` 5.0.4 `update` of all three changesets: `Run: 1` each, then
  `vector` extension, `scribe_schema`, and `scribe_schema.graph_nodes` with all
  ten columns present; `has_schema_privilege('platform_app','scribe_schema',…)`
  = USAGE **true**, CREATE **false**; table grants exactly
  SELECT/INSERT/UPDATE/DELETE.
- `rollback-count --count=1` on each, in reverse: all three succeeded and the
  extension, schema and table were gone afterwards — the `--rollback` blocks are
  real, not decorative.
- Whole scribe suite against a **freshly created** database provisioned only by
  those changesets: 316 passed, 4 skipped. The driver never creates anything.
- `test_store_works_as_a_ddl_revoked_role` builds a login role, revokes CREATE
  on `public` and `scribe_schema`, proves PostgreSQL refuses it a `CREATE TABLE`
  (so the test is not vacuous), then drives a full upsert → commit → reopen
  through `PostgresGraphStore` as that role.

**Pre-existing, not touched.** (a) `liquibase update` on the *master* changelog
fails at `python-agent-platform:18` — `socialaccount_socialapp_sites` adds an FK
to `django_site`, but `sites.0001` is `:10`, included after `:18`. The include
order in `db.changelog-master.yaml` does not satisfy that dependency; scribe's
three changesets are last and unaffected. (b) Any `django_db` test in
`src/platform` errors at test-DB setup here on
`ValidationError: slug 'home' is already in use` from
`front_door.apps::_seed_lane1_homepage` in `post_migrate`, which is why
`test_live_first_party_tree_is_covered` and
`test_app_role_create_alter_drop_refused_by_postgresql` could not be run
locally; the CI step they mirror, `python -m db.sqlmigrate_extraction`, was run
directly and reports `ok (14 first-party migrations)`. (c) Two
`test_openfeature_channel_policy` failures (a `cachebox` pin drift) are red on
`main`.

## Verification

`pixi run -e pyforge-scribe pyforge-scribe-test -k pg`; `src/platform` policy suite + sqlmigrate extraction.

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 41.3). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
