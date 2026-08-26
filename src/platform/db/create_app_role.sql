-- Operator-applied as the migration role (POSTGRES_USER / platform).
-- FR-22: the app role must be refused CREATE/ALTER/DROP by PostgreSQL.
-- Password is supplied by the operator; do not commit credentials.
--
--   CREATE ROLE platform_app LOGIN PASSWORD '...';
-- then run the REVOKE/GRANT block below.

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM platform_app;
GRANT CONNECT ON DATABASE platform TO platform_app;
GRANT USAGE ON SCHEMA public TO platform_app;
GRANT USAGE ON SCHEMA langflow_schema TO platform_app;
GRANT USAGE ON SCHEMA dbgpt_schema TO platform_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO platform_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO platform_app;
-- Default privileges do not cover tables already in public / engine schemas.
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO platform_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO platform_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA langflow_schema TO platform_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA langflow_schema TO platform_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA dbgpt_schema TO platform_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA dbgpt_schema TO platform_app;
