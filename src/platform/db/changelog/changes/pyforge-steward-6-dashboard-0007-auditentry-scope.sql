--liquibase formatted sql
--changeset pyforge-steward:6
--comment sqlmigrate pyforge_steward_dashboard.0007_auditentry_scope
--
-- Add field scope to auditentry
--
ALTER TABLE "pyforge_steward_dashboard_auditentry" ADD COLUMN "scope" jsonb DEFAULT '{}'::jsonb NOT NULL;
ALTER TABLE "pyforge_steward_dashboard_auditentry" ALTER COLUMN "scope" DROP DEFAULT;
--rollback ALTER TABLE "pyforge_steward_dashboard_auditentry" DROP COLUMN "scope" CASCADE;
