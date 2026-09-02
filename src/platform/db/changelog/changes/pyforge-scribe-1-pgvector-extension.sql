--liquibase formatted sql
--changeset pyforge-scribe:1
--comment Story 41.3 (red-team S-4 / R-12): pgvector for the scribe graph store. CREATE EXTENSION needs superuser or a trusted-extension grant, so it belongs to the migration role -- no station creates it at runtime.
CREATE EXTENSION IF NOT EXISTS vector;
--rollback DROP EXTENSION IF EXISTS vector;
