--liquibase formatted sql
--changeset pyforge-scribe:2
--comment Story 41.3: scribe's graph schema and node table. The runtime driver asserts these exist and fails loudly when they do not (CAP-9); it never creates them.
CREATE SCHEMA IF NOT EXISTS scribe_schema;
CREATE TABLE IF NOT EXISTS scribe_schema.graph_nodes (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    text TEXT NOT NULL,
    citation TEXT NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ,
    superseded_by TEXT,
    embedding vector,
    stale BOOLEAN NOT NULL DEFAULT FALSE
);
--rollback DROP TABLE IF EXISTS scribe_schema.graph_nodes;
--rollback DROP SCHEMA IF EXISTS scribe_schema;
