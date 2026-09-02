--liquibase formatted sql
--changeset pyforge-scribe:4
--comment Story 41.3: a graph_nodes created by a pre-6.3 driver has no `stale` column, and pyforge-scribe:2's CREATE TABLE IF NOT EXISTS is a no-op against it. Scribe's runtime role can no longer add the column itself, so the back-fill is a changeset.
ALTER TABLE scribe_schema.graph_nodes ADD COLUMN IF NOT EXISTS stale BOOLEAN NOT NULL DEFAULT FALSE;
--rollback ALTER TABLE scribe_schema.graph_nodes DROP COLUMN IF EXISTS stale;
