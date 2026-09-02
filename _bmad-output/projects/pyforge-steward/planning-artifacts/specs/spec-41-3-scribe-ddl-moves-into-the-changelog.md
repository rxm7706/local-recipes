---
title: "Scribe DDL moves into the changelog"
type: "fix"
created: "2026-09-02"
status: "ready-for-dev"
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

- [ ] Changeset + map entry
- [ ] Driver assert-only path + tests
- [ ] Rollback policy doc
- [ ] CI `sqlmigrate` gate still green
- [ ] Ledger `41-3-scribe-ddl-moves-into-the-changelog` → `review` then `done` via `sprint-ledger-sync`.

## Verification

`pixi run -e pyforge-scribe pyforge-scribe-test -k pg`; `src/platform` policy suite + sqlmigrate extraction.

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 41.3). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
