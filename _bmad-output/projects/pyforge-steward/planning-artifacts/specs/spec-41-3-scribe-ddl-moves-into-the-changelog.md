---
title: "Scribe DDL moves into the changelog"
type: "fix"
created: "2026-09-02"
status: "done"
updated: "2026-09-02"
baseline_commit: "58ee07a0"
baseline_revision: "a4316334fec7b7ad0aaee536c4c89b811e4eb15c"
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
followup_review_recommended: false
deferred:
  - "Per-station schema ownership enforcement beyond scribe (fleet sweep)."
  - summary: >-
      db.changelog-master.yaml's include order does not satisfy its own FK
      dependencies: python-agent-platform:18 adds a socialaccount FK to
      django_site, which :10 (sites.0001) creates later.
    evidence: |-
      Real `liquibase update` on the master changelog stops at `Run: 10` with
      `ERROR: relation "django_site" does not exist`. Reproduced identically
      against the baseline master changelog (`git show a4316334fe:...`), so it
      predates this story; scribe's changesets are appended last and are
      unaffected. No test executes the master changelog in include order.
    location: >-
      src/platform/db/changelog/db.changelog-master.yaml
    severity: high
  - summary: >-
      No CI workflow runs the scribe suite, so this story's behavioural proofs
      (DDL-revoked role, named error, changeset-provisioned database) gate
      nothing.
    evidence: |-
      Nothing under .github/workflows/ invokes `pyforge-scribe-test`, and
      `src/shared/packages/pyforge-scribe/**` is absent from platform-ci.yml's
      `paths:` filter. This PR runs platform CI only because it touches
      src/platform/**; a later edit to graph_store_pg.py alone triggers no
      workflow. Pre-existing — the scribe suite was never wired in.
    location: >-
      .github/workflows/platform-ci.yml
    severity: high
  - summary: >-
      platform_app's real grant set is never executed by any test; the
      DML-revoked-role test hand-writes equivalent grants instead.
    evidence: |-
      No test applies create_app_role.sql or pyforge-scribe:3 and then
      connects. test_store_works_as_a_ddl_revoked_role synthesises its own
      role and types the grants into the test body, so the shipped SQL could
      drift from it and stay green. Flipping :3's precondition to
      `expectedResult:0` would skip the grants on exactly the databases where
      platform_app exists, and every test still passes.
    location: >-
      src/platform/db/changelog/changes/pyforge-scribe-3-app-role-grants.sql
    severity: medium
  - summary: >-
      Red-team B-1 is only half-addressed — numbering is per-distribution, but
      scribe's changesets still ship inside the single master changelog, so a
      scribe schema change still rides the platform release.
    evidence: |-
      There is no per-distribution sub-changelog, includeAll, or
      contexts:/labels: on the new changesets, and every estate gets scribe's
      DDL whether or not scribe is deployed. Unmapped django-<station>
      migrations also still fall through to `default:
      python-agent-platform`, so the release coupling B-1 names persists by
      default until each station registers.
    location: >-
      src/platform/db/changelog/db.changelog-master.yaml
    severity: medium
  - summary: >-
      graph_nodes.embedding is declared without a dimension, so no ivfflat or
      hnsw index is possible and query_similar sequentially scans the table.
    evidence: |-
      `embedding vector` in pyforge-scribe:2, and no index changeset exists.
      This is parity with the pre-41.3 driver, not a regression, but bringing
      the DDL under governance is the natural moment to fix it — and it leaves
      the new README's CREATE INDEX CONCURRENTLY exception process with no
      user.
    location: >-
      src/platform/db/changelog/changes/pyforge-scribe-2-graph-nodes.sql
    severity: medium
  - summary: >-
      Every django_db test in src/platform errors at test-database setup on
      `ValidationError: slug 'home' is already in use`.
    evidence: |-
      Raised from front_door.apps::_seed_lane1_homepage in post_migrate.
      Reproduced on tests/test_health_endpoint.py, which this story never
      touches, and it persists with --create-db, so it is not a --reuse-db
      artifact. It blocks test_app_role_create_alter_drop_refused_by_postgresql
      and test_live_first_party_tree_is_covered locally; the CI step they
      mirror was run directly instead.
    location: >-
      src/platform/platformapp/front_door/lane1_seed.py:41
    severity: medium
  - summary: >-
      Two test_openfeature_channel_policy tests are red on main from a
      cachebox pin drift.
    evidence: |-
      `cachebox must be pinned '>=5.1,<6' so conda-forge 6.x is not selected
      (got '>=5.2.3')`. The test reads pixi.toml, which this story does not
      modify.
    location: >-
      src/platform/tests/policy/test_openfeature_channel_policy.py:137
    severity: medium
  - summary: >-
      GraphSchemaMissing is not re-exported from pyforge.scribe, and no scribe
      doc records that the durable graph store now requires Liquibase to have
      run.
    evidence: |-
      PostgresGraphStore.__init__ now raises on an unprovisioned database — a
      behaviour change for every existing consumer — but only
      src/platform/db/README.md says so. The scribe package README,
      docs/cli-runbooks.md and .claude/skills/pyforge-scribe/SKILL.md are
      silent.
    location: >-
      src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_pg.py
    severity: low
  - summary: >-
      The chart and compose ship stock `postgres:17`, which has no pgvector,
      so `pyforge-scribe:1` moves a CREATE EXTENSION failure out of scribe's
      own process and into the platform's pre-upgrade hook Job.
    evidence: |-
      values.yaml pins `repository: postgres` / `tag: "17"` and compose.yml
      `image: postgres:17`; `grep -rn -i pgvector src/platform/deploy/
      src/platform/compose/` returns nothing. The Helm Job
      (`post-install,pre-upgrade`) applies the master changelog, so on a stock
      image `:1` aborts with `could not open extension control file
      "vector.control"` and the release fails -- for every estate, including
      ones that never deploy scribe. Before this story the same statement
      failed only inside the scribe station. Supplying a pgvector-capable
      image is a deploy-side decision outside this story's boundaries.
    location: >-
      src/platform/deploy/charts/platform/values.yaml:108-113
    severity: high
  - summary: >-
      `_assert_provisioned` names only the relation-absent and no-schema-USAGE
      cases; column drift and a table-privilege gap still leak raw psycopg
      errors with no changeset named.
    evidence: |-
      `to_regclass` answers existence only. A role with schema USAGE but no
      table grants passes the assert and then raises a raw
      `InsufficientPrivilege` from `_load`; a `graph_nodes` missing a column
      raises a raw `UndefinedColumn`, which
      `test_legacy_table_without_stale_is_back_filled_by_the_changeset` pins
      as expected pre-`:4` behaviour. AC-1 only requires the relation-absent
      case to be named, so this is beyond the contract, but it is the same
      class of unrecoverable state the review's high finding fixed.
    location: >-
      src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_pg.py:114
    severity: medium
  - summary: >-
      Master-changelog include order is load-bearing for scribe (`:1` before
      `:2` before `:3`) but only set membership and duplicates are asserted.
    evidence: |-
      `test_every_changeset_file_is_included_in_the_master_changelog`
      compares sets. Order cannot be inferred from seq either -- the file
      already includes `python-agent-platform-15` between `:5` and `:6`. A
      reordered include would put `CREATE TABLE ... embedding vector` before
      the extension exists and fail at deploy time, with every test green.
      Distinct from the pre-existing FK-ordering deferral above, which is
      about python-agent-platform's own order.
    location: >-
      src/platform/tests/policy/test_liquibase_ddl_governance.py:252
    severity: medium
  - summary: >-
      `load_map`'s new "default distribution not registered" ValueError is
      untested and reaches CI as a traceback, and no path migrates a
      pre-41.3 `sqlmigrate-map.yaml`.
    evidence: |-
      `run_live_check` calls `load_map` with no handler, so a malformed or
      old-format map exits with a stack trace instead of the module's
      `format_findings` output. `test_sqlmigrate_extraction.py` never asserts
      the rejection. An old-format map (top-level `distribution:` /
      `migrations:`) yields `distributions == {}` and trips the guard with no
      hint that the format changed.
    location: >-
      src/platform/db/sqlmigrate_extraction.py:125
    severity: medium
  - summary: >-
      `MigrationMap.lookup` resolves a migration key claimed by two
      distributions by YAML insertion order, while db/README.md calls the map
      a register that "cannot silently collide".
    evidence: |-
      `lookup` returns the first distribution whose `migrations` contains the
      key and never reports the duplicate. The anti-collision property the
      README claims for the map is actually provided by
      `test_changeset_ids_are_unique_across_files`, which scans
      `changes/*.sql` -- a different artifact from the one AC-3 names.
    location: >-
      src/platform/db/sqlmigrate_extraction.py:57
    severity: medium
  - summary: >-
      Scribe's test suite now hard-depends on the platform tree, so the
      package can no longer be tested standalone.
    evidence: |-
      `tests/unit/conftest.py` resolves `parents[5] / "platform" / "db" /
      "changelog" / "changes"` and calls `pytest.fail` (not `skip`) when it is
      absent. The wheel excludes `tests/`, so this bites an sdist or
      standalone checkout rather than an installed wheel. The reverse edge
      (host importing `pyforge.*`) is the one the Boundaries forbid; this
      direction is unaddressed by them.
    location: >-
      src/shared/packages/pyforge-scribe/tests/unit/conftest.py:12
    severity: low
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

**2026-09-02 — review pass, six findings applied.**

1. *(HIGH)* Deleting `_ensure_schema` also deleted the `stale` back-fill, and
   nothing replaced it: `:2`'s `CREATE TABLE IF NOT EXISTS` is a no-op against a
   pre-6.3 nine-column table, `to_regclass` resolves it so the assert passes,
   and `_load` then died on a raw `UndefinedColumn` with no changeset named —
   unrecoverable, since the runtime role can no longer alter the table.
   `pyforge-scribe:4` carries the back-fill with a `DROP COLUMN` rollback.
   Verified end to end: a legacy nine-column table built by hand, then real
   `liquibase update` → 10 columns with `stale NOT NULL DEFAULT false`;
   `rollback-count` removes it again.
2. *(MEDIUM)* The `_assert_provisioned` docstring claimed `to_regclass` returns
   NULL for a relation "invisible to this role". It does not — without schema
   `USAGE` it raises `permission denied for schema …`. That is the likeliest
   production failure, because `:3` is `onFail:CONTINUE` and is skipped
   silently on a database where the app role was created after the first
   `liquibase update`. Docstring corrected; the driver now catches
   `InsufficientPrivilege` and raises `GraphSchemaMissing` naming
   **`pyforge-scribe:3`** (the grants), not `:2`.
3. *(MEDIUM)* The duplicate-seq assertion was unreachable — `_changeset_files()`
   keyed a dict on the changeset id and overwrote on collision, so the loop
   iterated already-unique keys and a colliding file also escaped the rollback
   gate. `_changeset_entries()` now returns `(path, id, body)` and a dedicated
   test names both colliding files.
4. *(MEDIUM)* The rollback gate accepted `--rollback empty` and
   `--rollback not required` — Liquibase's own "there is no way back"
   declarations, exactly what the policy forbids. Both are rejected now unless
   the changeset is a documented `runInTransaction:false` exception, and
   `db/README.md` says so.
5. *(MEDIUM)* Nothing asserted a changeset file is `include:`d in the master
   changelog — a forgotten include for `:1` or `:3` would have shipped silently
   (no pgvector, or no grants), and the scribe fixture hid it by globbing
   `changes/*.sql` directly. Every file must now appear exactly once.
6. *(LOW)* The fixture applied changesets in lexicographic filename order
   (`-10-` before `-2-`); it sorts on the parsed seq now.

Each of the three new platform gates was mutation-checked: dropping the `:4`
include, downgrading its rollback to `empty`, and adding a second file on
`pyforge-scribe:4` each red the intended test and only that test.

## Review Triage Log

### 2026-09-02 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 1, medium 4, low 1)
- defer: 8: (high 2, medium 5, low 1)
- reject: 9: (high 0, medium 5, low 4)
- addressed_findings:
  - `[high]` `[patch]` The deleted `stale` back-fill had no replacement — a pre-6.3
    nine-column `graph_nodes` passed `to_regclass` and then died in `_load` on a raw
    `UndefinedColumn`, unrecoverably, since the runtime role can no longer ALTER it.
    Added changeset `pyforge-scribe:4` (`ADD COLUMN IF NOT EXISTS stale` +
    `DROP COLUMN` rollback), included it in the master changelog, and pinned it with a
    test that builds the legacy shape, proves the failure, then proves the repair.
  - `[medium]` `[patch]` `_assert_provisioned`'s docstring claimed `to_regclass`
    returns NULL for a relation "invisible to this role"; measured, it raises
    `permission denied for schema`. Docstring corrected and the driver now maps
    `InsufficientPrivilege` to `GraphSchemaMissing` naming `pyforge-scribe:3` — the
    grants changeset, which `onFail:CONTINUE` skips whenever the app role was created
    after the first `liquibase update`.
  - `[medium]` `[patch]` The duplicate-seq assertion was unreachable: `_changeset_files()`
    keyed a dict on the changeset id and overwrote on collision, so a colliding file
    also escaped the rollback gate. Replaced with `_changeset_entries()` and a test
    that names both colliding paths.
  - `[medium]` `[patch]` The rollback gate accepted `--rollback empty` and
    `--rollback not required` — Liquibase's own "no way back" declarations, precisely
    what the new policy forbids. Both now rejected outside a documented
    `runInTransaction:false` exception, and `db/README.md` records the rule.
  - `[medium]` `[patch]` Nothing asserted a changeset file is `include:`d in the master
    changelog, and the scribe fixture hid the gap by globbing `changes/*.sql` directly —
    a forgotten include for `:1` or `:3` would have shipped with no pgvector or no
    grants. Every file must now appear exactly once.
  - `[low]` `[patch]` The fixture applied changesets in lexicographic filename order
    (`-10-` before `-2-`); it sorts on the parsed seq now.

### 2026-09-02 — Review pass (follow-up)

- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 3, low 2)
- defer: 6: (high 1, medium 4, low 1)
- reject: 14: (high 0, medium 6, low 8)
- addressed_findings:
  - `[medium]` `[patch]` The Block-If gate matched the literal string `GRANT CREATE`, so
    `GRANT USAGE, CREATE ON SCHEMA scribe_schema TO platform_app` — the natural spelling,
    and the exact widening the intent-contract forbids — passed clean. Replaced with
    `WIDENING_GRANT`, which scopes the match to the privilege list between `GRANT` and
    `ON` (so `GRANT SELECT, … ON ALL TABLES` stays green) and strips comment lines so
    prose about never granting CREATE cannot red it. Added
    `test_widening_grant_gate_catches_the_natural_spellings` pinning both directions.
  - `[medium]` `[patch]` `_changeset_entries()` read only the *first* `--changeset`
    header per file (`.search`), while `test_changeset_ids_are_distribution_seq` used
    `finditer` — so a second changeset sharing a file inherited the first one's rollback
    and was invisible to the uniqueness, grandfather and distribution gates, yet visible
    to the id-shape gate. The two halves of the gate now agree: `_changeset_headers()`
    plus an assertion of exactly one header per file, which is what db/README.md already
    documented.
  - `[medium]` `[patch]` `pyforge-scribe:4`'s rollback drops `stale` unconditionally, but
    on any database where `:2` created the table `:4` is a forward no-op — so
    `rollback-count 1` on `:4` alone removes a column it never added and leaves a shape
    the runtime role can read but not repair. That contradicts the rollback rule this
    same diff shipped ("undo what *this* changeset did and nothing else"). The asymmetry
    is unavoidable for a conditional back-fill, so it is now written down in `:4`'s
    `--comment` and in db/README.md, with the recovery step — forward, `liquibase
    update`, not a deeper rollback.
  - `[low]` `[patch]` The scribe fixture's `_CHANGESET_SEQ` anchored the seq to
    end-of-line, so a header carrying Liquibase attributes — `--changeset x:5
    runInTransaction:false`, precisely what db/README.md's exception process mandates —
    made `_seq` call `pytest.fail` from inside `sorted(key=…)`. Following the documented
    process would have broken test provisioning.
  - `[low]` `[patch]` Four cross-references still said scribe owned `:1`–`:3` after the
    previous pass added `:4`: the driver module docstring, `create_app_role.sql`'s
    comment, `sqlmigrate-map.yaml`'s comment, and the master changelog's section header.

## Auto Run Result

Status: done
Blocking condition: none

**Implemented change.** Scribe's three runtime DDL statements moved out of
`PostgresGraphStore` into Liquibase changesets under scribe's own distribution
sequence, the runtime path became assert-only, `sqlmigrate-map.yaml` became a
per-distribution map, and the rollback policy was written down. The review pass
added `pyforge-scribe:4` and hardened three governance gates.

**Files changed**

- `src/platform/db/changelog/changes/pyforge-scribe-1-pgvector-extension.sql` — new: `CREATE EXTENSION vector`, with rollback.
- `src/platform/db/changelog/changes/pyforge-scribe-2-graph-nodes.sql` — new: `scribe_schema` + the 10-column `graph_nodes`, with rollback.
- `src/platform/db/changelog/changes/pyforge-scribe-3-app-role-grants.sql` — new: DML-only grants behind an `onFail:CONTINUE` role-exists precondition.
- `src/platform/db/changelog/changes/pyforge-scribe-4-graph-nodes-stale-column.sql` — new (review): back-fills `stale` onto a pre-6.3 table.
- `src/platform/db/changelog/db.changelog-master.yaml` — includes the four scribe changesets.
- `src/platform/db/create_app_role.sql` — `scribe_schema` USAGE + DML for `platform_app`; never CREATE.
- `src/platform/db/sqlmigrate-map.yaml` — `default:` + `distributions:`; registers `pyforge-scribe`.
- `src/platform/db/sqlmigrate_extraction.py` — `MigrationMap`; next-seq numbering is per distribution.
- `src/platform/db/README.md` — new: id scheme, rollback policy, `runInTransaction=false` exception process.
- `src/platform/tests/policy/test_liquibase_ddl_governance.py` — rollback-policy, grandfather-rot, `GRANT CREATE`, include-coverage and duplicate-id gates.
- `src/platform/tests/policy/test_sqlmigrate_extraction.py` — per-distribution map coverage.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_pg.py` — `_ensure_schema` → `_assert_provisioned`; new `GraphSchemaMissing`.
- `src/shared/packages/pyforge-scribe/tests/unit/conftest.py` — provisions the test DB from the changesets, in seq order.
- `src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_pg.py` — no-DDL, named-error, DDL-revoked-role, legacy-table and privilege-gap tests.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml` — story row → `review`.

**Review findings breakdown.** 6 patches applied (1 high, 4 medium, 1 low);
8 items deferred (2 high, 5 medium, 1 low) — recorded in frontmatter `deferred`;
9 rejected, chiefly speculative future needs (sequence grants for a table whose
key is `TEXT`), or restatements of shipped convention the Boundaries protect
(`create_app_role.sql`'s ordering dependency, which mirrors the existing
`langflow_schema` / `dbgpt_schema` lines; `:3`'s precondition matching
`python-agent-platform:2`).

**Follow-up review recommended: true.** Patched counts — high 1, medium 4, low 1.
A patched `high` sets the flag on its own; the score is `3 × 4 + 1 × 1 = 13`.

**Verification performed** (all re-run after the patches, by the parent session,
against PostgreSQL 17.11 + pgvector on `:5433`):

- `pixi run -e pyforge-scribe pyforge-scribe-test -k pg` → **15 passed**, 307 deselected. Every AC-bearing test ran (none skipped), including `test_store_works_as_a_ddl_revoked_role`, which first proves PostgreSQL refuses that role a `CREATE TABLE`, so it is not vacuous.
- `pixi run -e platform-ci-test python -m pytest tests/policy -q` → **68 passed**, plus only the four pre-existing items in `deferred` (2 cachebox, 2 `django_db` setup).
- `python -m db.sqlmigrate_extraction` → `ok (14 first-party migrations)`.
- Real `liquibase` 5.0.4 `update` of `:1`/`:2` on a throwaway database → `Run: 1` each; `vector`, `scribe_schema` and all ten `graph_nodes` columns present. `:3` reported `Run: 0` while `platform_app` was absent, then `Run: 1` once it existed, yielding `USAGE = true`, `CREATE = false`, table grants exactly SELECT/INSERT/UPDATE/DELETE.
- `rollback-count --count=1` on `:2` then `:1` → both succeeded; extension and schema gone afterwards.
- The high finding was reproduced before the fix (`psycopg.errors.UndefinedColumn: column "stale" does not exist` on a hand-built nine-column table) and re-verified after: real `liquibase update` of `:4` yields `stale_col=1` and the store opens on the repaired table.
- `to_regclass` ACL behaviour measured directly: a role without schema USAGE gets `ERROR: permission denied for schema`, settling the docstring correction.
- Independent mutation check: deleting the `:4` include reds
  `test_every_changeset_file_is_included_in_the_master_changelog` and nothing else; tree restored clean.
- Every probe database and role was dropped; the container is as it was found.

**Residual risks.** The two `high` deferrals are the material ones: `liquibase update`
on the master changelog cannot currently reach scribe's changesets at all, because
it fails earlier at `python-agent-platform:18` (verified identical at baseline), and
no CI workflow runs the scribe suite, so this story's behavioural proofs are
developer-local. Landing still owes three things the dispatch worktree cannot do:
the ledger row must move `review` → `done` (a `backlog`/non-terminal row makes the
drain respawn the story), the spec-surface baseline needs a memlog naming each
accepted path plus a **scoped** `--write-baseline --spec <name>` per spec — a bare
memlog append would downgrade roughly 100 foreign pending FAILs to non-gating
WARNs — and the PR needs the `maintenance` label, since it touches no `recipes/**`.
`pixi.toml` is untouched, so `environment.yaml` needs no regeneration.

### 2026-09-02 — Follow-up review pass (the single allowed one)

Entered from `status: done` with `followup_review_recommended: true`, which the
previous pass set on the strength of its patched `high`. The flag was consumed
at entry and is forced `false` at HALT; there is no further automatic follow-up.

**Implemented change (this pass).** No production behaviour changed. Three
governance gates were tightened and two documentation defects fixed: the
Block-If `GRANT CREATE` gate missed the `GRANT USAGE, CREATE …` spelling, the
changeset-file reader saw only the first `--changeset` header per file, and
`pyforge-scribe:4`'s asymmetric rollback contradicted the rollback rule shipped
beside it.

**Files changed**

- `src/platform/tests/policy/test_liquibase_ddl_governance.py` — `WIDENING_GRANT`
  privilege-list gate + its discrimination test; `_changeset_headers()` and a
  one-changeset-per-file assertion.
- `src/platform/db/changelog/changes/pyforge-scribe-4-graph-nodes-stale-column.sql`
  — records the asymmetric rollback and its forward recovery.
- `src/platform/db/README.md` — the back-fill-rollback rule under § Rollback policy.
- `src/shared/packages/pyforge-scribe/tests/unit/conftest.py` — `_CHANGESET_SEQ`
  no longer anchors the seq to end-of-line.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_pg.py`,
  `src/platform/db/create_app_role.sql`, `src/platform/db/sqlmigrate-map.yaml`,
  `src/platform/db/changelog/db.changelog-master.yaml` — `:1`–`:3` → `:1`–`:4`.

**Review findings breakdown.** 5 patches applied (3 medium, 2 low); 6 deferred
(1 high, 4 medium, 1 low), appended to frontmatter `deferred`; 14 rejected.
Rejections were re-derived, not inherited — two of the previous pass's rejection
premises were re-checked against the tree and confirmed (`create_app_role.sql`'s
ordering dependency mirrors the shipped `langflow_schema` / `dbgpt_schema`
lines; `:3`'s precondition matches `python-agent-platform:2`). The
`CREATE EXTENSION … WITH SCHEMA` finding was rejected on measurement:
`liquibase_update.py` pins `?currentSchema=public`, so the extension cannot land
in a non-`public` schema.

**Follow-up review recommended: false.** Patched counts — high 0, medium 3,
low 2; score `3 × 3 + 1 × 2 = 11`, which would set `true`, but this pass was
itself the single allowed follow-up from a `done` spec, so the flag is forced
`false`.

**Verification performed** (this pass, against the same PostgreSQL 17.11 +
pgvector on `:5433`):

- `pixi run -e pyforge-scribe pyforge-scribe-test -k pg` → **15 passed**, 307
  deselected — identical to the previous pass, so the `_CHANGESET_SEQ` change
  did not disturb fixture provisioning.
- `src/platform` policy suite → **69 passed** (68 before, +1 for the new
  discrimination test), with only the four pre-existing items already in
  `deferred` (2 cachebox pin-drift failures, 2 `django_db` setup errors).
- `python -m db.sqlmigrate_extraction` → `sqlmigrate extraction ok (14
  first-party migrations)`. Note for whoever runs this next: this shell exports
  `PYTHONSAFEPATH`, so the CI spelling needs `PYTHONPATH` seeded with `.` plus
  the `pythonpath` entries from `src/platform/pyproject.toml`, and a reachable
  `DATABASE_URL`.
- Mutation-checked both tightened gates. Rewriting `pyforge-scribe:3` to
  `GRANT USAGE, CREATE ON SCHEMA scribe_schema TO platform_app` reds
  `test_no_governed_sql_grants_create_to_the_app_role` with
  `assert not ['USAGE, CREATE ']` — the spelling that passed before this pass.
  Appending a second `--changeset pyforge-scribe:5` header to `:4`'s file reds
  the one-header assertion (and every gate routed through
  `_changeset_entries`), where previously that second changeset would have
  inherited `:4`'s rollback silently. Tree restored clean after each.
- The pgvector-image deferral was verified directly, not inferred:
  `values.yaml` pins `postgres:17`, `compose.yml` the same, and
  `grep -rn -i pgvector src/platform/deploy/ src/platform/compose/` returns
  nothing.

**Residual risks (this pass).** The newly deferred `high` is the material one:
the estate's declared PostgreSQL image has no pgvector, so `pyforge-scribe:1`
turns a scribe-local failure into a failed platform release. It is masked today
only because the master changelog already halts earlier at
`python-agent-platform:18` (the pre-existing FK-ordering deferral) — the two
should be resolved together, and neither is in this story's boundaries. The
landing obligations recorded by the previous pass are unchanged and still owed:
ledger row `review` → `done`, a scoped `--write-baseline --spec <name>` per spec
with a memlog naming each accepted path, and the `maintenance` label on the PR.

## Verification

`pixi run -e pyforge-scribe pyforge-scribe-test -k pg`; `src/platform` policy suite + sqlmigrate extraction.

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 41.3). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
