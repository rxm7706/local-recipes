# Governed schema change (`src/platform/db/`)

Canopy AD-9 / CAP-9 / FR-21a–FR-23. Production DDL flows through Liquibase,
applied by the migration role from a Helm `pre-upgrade` hook Job — never from
an init container, never from an application process at boot.

| Path | What it is |
|---|---|
| `changelog/db.changelog-master.yaml` | Include order for every changeset. |
| `changelog/changes/*.sql` | Liquibase formatted-SQL changesets, one file per changeset. |
| `sqlmigrate-map.yaml` | First-party Django migration → changeset id, per distribution. |
| `sqlmigrate_extraction.py` | CI gate: a production migration without a covering changeset fails the build. |
| `liquibase_update.py` | The Job entrypoint (`liquibase update`) — JDBC targeting, `currentSchema`, `liquibase` schema creation. |
| `create_app_role.sql` | Operator-applied: the DML-only `platform_app` role. |

## Changeset ids are `<distribution>:<seq>`

Each **distribution** owns its own sequence. `python-agent-platform:14` and
`pyforge-scribe:2` are independent numbers, so a station's schema change does
not have to be squeezed into another distribution's numbering or wait on its
release (Story 41.3, red-team B-1).

`sqlmigrate-map.yaml` is the register:

```yaml
default: python-agent-platform      # where an unmapped Django migration lands
distributions:
  python-agent-platform:
    migrations:
      users.0001_initial: 6
  pyforge-scribe:
    migrations: {}                  # hand-authored DDL, no Django app
```

A distribution whose schema is *not* authored as Django migrations (scribe's
graph store) still declares itself here with an empty `migrations:` map, so the
id space is registered in one place and cannot silently collide.

**Adding a changeset**

1. Pick the owning distribution; take the next free seq in *that* distribution.
2. Name the file `<distribution>-<seq>-<slug>.sql` and give it a
   `--changeset <distribution>:<seq>` header.
3. Add a rollback (below).
4. `include:` it in `db.changelog-master.yaml`.
5. If it came from a Django migration, add the map entry; CI's
   `python -m db.sqlmigrate_extraction` names the id it expected when you don't.

## Rollback policy

**Every changeset carries a rollback, or a documented exception.** Liquibase
cannot infer rollback for formatted SQL, so an unrolled-back changeset makes
`liquibase rollback` fail at exactly the moment it is needed.

- **Formatted SQL** (`changelog/changes/*.sql`) declares it with `--rollback`
  lines — one per statement, in reverse order of the forward statements. This is
  the formatted-SQL spelling of a YAML changeset's `rollback:` block; the policy
  is the same in either syntax.
- **`--rollback empty` and `--rollback not required` are rejected.** Liquibase
  accepts both, but they declare that there *is* no way back — the case this
  policy exists to forbid. A changeset that genuinely cannot be reversed takes
  the `runInTransaction=false` exception below, which is reviewed; it does not
  get there by satisfying the parser. The policy test discriminates the two
  forms explicitly.
- The rollback must undo what *this* changeset did and nothing else. Guard with
  `IF EXISTS` so rolling back a partially-applied changeset does not itself fail.
- Grants roll back as the matching `REVOKE`s, including
  `ALTER DEFAULT PRIVILEGES … REVOKE`.
- A changeset must be `include:`d in `db.changelog-master.yaml` — an
  un-included file is inert and ships nothing. The policy test asserts every
  `changes/*.sql` appears there exactly once.

```sql
--liquibase formatted sql
--changeset pyforge-scribe:2
--comment scribe's graph schema and node table
CREATE SCHEMA IF NOT EXISTS scribe_schema;
CREATE TABLE IF NOT EXISTS scribe_schema.graph_nodes (id TEXT PRIMARY KEY);
--rollback DROP TABLE IF EXISTS scribe_schema.graph_nodes;
--rollback DROP SCHEMA IF EXISTS scribe_schema;
```

Enforced by `tests/policy/test_liquibase_ddl_governance.py`. The
`python-agent-platform:1`–`:19` changesets shipped by CAP-9 before this policy
existed are grandfathered by an explicit list in that test: the list is closed,
so a new changeset cannot join it.

### `runInTransaction=false` — the exception process

A few statements cannot run inside a transaction (`CREATE INDEX CONCURRENTLY`,
`ALTER TYPE … ADD VALUE`, `VACUUM`). Those changesets are marked
`--changeset <distribution>:<seq> runInTransaction:false`, and PostgreSQL will
not roll them back for you — a failure leaves the change half-applied.

To take the exception:

1. **Isolate it.** One statement per `runInTransaction:false` changeset, and
   nothing else in that changeset. A failed non-transactional changeset is
   recovered by hand; keep the blast radius to one statement.
2. **Write the exception down in the changeset itself** — a `--comment` line
   naming the statement, why it cannot run in a transaction, and the manual
   recovery step (for `CREATE INDEX CONCURRENTLY`: drop the resulting
   `INVALID` index and re-run).
3. Still supply `--rollback` where one exists (a concurrently-built index is
   dropped normally). Only when no rollback statement exists at all does the
   documented `--comment` stand in its place — and the policy test accepts it
   only on a `runInTransaction:false` changeset.

Liquibase **5.0.4 or later** is required for this: 5.0.2/5.0.3 carry the issue
7791 `SEARCH_PATH` defect, which affects `runInTransaction="false"` changesets
specifically. `preserveSchemaCase` stays off (issue 7624) and schema names stay
lowercase.

## Runtime processes never emit DDL

The application role (`platform_app`) holds DML only; `CREATE`/`ALTER`/`DROP`
are refused by PostgreSQL, which is the control an auditor can verify. A driver
that needs a relation **asserts** it and fails with a named error pointing at
the changeset — it does not create it, and the fix is never a `GRANT`.

`pyforge.scribe.graph_store_pg` is the worked example (Story 41.3, red-team
S-4): `pyforge-scribe:1` creates the pgvector extension (superuser / trusted
extension — a runtime role cannot), `:2` creates `scribe_schema.graph_nodes`,
`:3` grants DML to `platform_app` behind a role-exists precondition, and `:4`
back-fills the `stale` column onto a table created by a pre-6.3 driver — `:2`'s
`CREATE TABLE IF NOT EXISTS` is a no-op against such a table, and the runtime
role can no longer add the column itself.

Two failure modes the driver names rather than leaking: the relation absent
(`pyforge-scribe:2` has not run) and the schema unreadable. The second is the
subtle one — `:3` is `onFail:CONTINUE`, so on a database where the app role was
created *after* the first `liquibase update` the grants were skipped silently,
and the driver points at `pyforge-scribe:3` instead of surfacing a raw
`permission denied`.

Django is exempt from *authoring* only: migrations remain the authoring surface,
extracted with `sqlmigrate` into changesets, and the deploy runs
`liquibase update` then `migrate --fake` so `post_migrate` still populates
content types, permissions and sites. Ephemeral `test_*` databases are outside
the governed estate.
