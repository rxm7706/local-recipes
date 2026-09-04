--liquibase formatted sql
--changeset python-agent-platform:21
--comment sqlmigrate django_pyforge.0005_run_state_tenant — Story 42.5 tenant claim on run_state.

-- Add field tenant to runstate
ALTER TABLE "run_state" ADD COLUMN "tenant" varchar(64) DEFAULT '' NOT NULL;
ALTER TABLE "run_state" ALTER COLUMN "tenant" DROP DEFAULT;
--rollback ALTER TABLE "run_state" DROP COLUMN "tenant";
