--liquibase formatted sql
--changeset pyforge-mybmad:2
--preconditions onFail:CONTINUE
--precondition-sql-check expectedResult:1 SELECT count(*) FROM pg_roles WHERE rolname = 'platform_app'
--comment DML-only grants on schema mybmad when the operator has created the app role. Never CREATE: Prisma owns tables in mybmad; Django public is untouched.
GRANT USAGE ON SCHEMA mybmad TO platform_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA mybmad TO platform_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA mybmad GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO platform_app;
--rollback ALTER DEFAULT PRIVILEGES IN SCHEMA mybmad REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM platform_app;
--rollback REVOKE SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA mybmad FROM platform_app;
--rollback REVOKE USAGE ON SCHEMA mybmad FROM platform_app;
