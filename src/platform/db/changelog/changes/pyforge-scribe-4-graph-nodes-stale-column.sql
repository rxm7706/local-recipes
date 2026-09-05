--liquibase formatted sql
--changeset pyforge-scribe:4
--comment Story 41.3: a graph_nodes created by a pre-6.3 driver has no `stale` column, and pyforge-scribe:2's CREATE TABLE IF NOT EXISTS is a no-op against it. Scribe's runtime role can no longer add the column itself, so the back-fill is a changeset. Asymmetric rollback (db/README.md): on a database where :2 created the table, this changeset is a forward no-op but its rollback still drops `stale`, so a lone `rollback-count 1` here leaves a shape the runtime cannot read or repair. Recovery is forward -- re-run `liquibase update`, which re-applies :4. Roll :4 back only as part of a reverse-order rollback that also reaches :2.
ALTER TABLE scribe_schema.graph_nodes ADD COLUMN IF NOT EXISTS stale BOOLEAN NOT NULL DEFAULT FALSE;
--rollback ALTER TABLE scribe_schema.graph_nodes DROP COLUMN IF EXISTS stale;
