--liquibase formatted sql
--changeset pyforge-scribe:3
--preconditions onFail:CONTINUE
--precondition-sql-check expectedResult:1 SELECT count(*) FROM pg_roles WHERE rolname = 'platform_app'
--comment DML-only grants on scribe_schema when the operator has created the app role. Never CREATE: the app role reads and writes graph rows, the migration role owns the shape.
GRANT USAGE ON SCHEMA scribe_schema TO platform_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA scribe_schema TO platform_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA scribe_schema GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO platform_app;
--rollback ALTER DEFAULT PRIVILEGES IN SCHEMA scribe_schema REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM platform_app;
--rollback REVOKE SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA scribe_schema FROM platform_app;
--rollback REVOKE USAGE ON SCHEMA scribe_schema FROM platform_app;
