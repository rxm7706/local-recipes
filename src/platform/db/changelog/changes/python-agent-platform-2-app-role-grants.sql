--liquibase formatted sql
--changeset python-agent-platform:2
--preconditions onFail:CONTINUE
--precondition-sql-check expectedResult:1 SELECT count(*) FROM pg_roles WHERE rolname = 'platform_app'
--comment DML grants for the app role when the operator has created it.
GRANT USAGE ON SCHEMA public TO platform_app;
GRANT USAGE ON SCHEMA langflow_schema TO platform_app;
GRANT USAGE ON SCHEMA dbgpt_schema TO platform_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO platform_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO platform_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA langflow_schema GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO platform_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA dbgpt_schema GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO platform_app;
