--liquibase formatted sql
--changeset python-agent-platform:20
--comment sqlmigrate django_pyforge.0004_run_bounds — Story 42.2 run bounds. The rollback normalises 'cancelled' back to 'failed' before narrowing the constraint: the pre-42.2 schema has no vocabulary for a revoked run, so a rollback that skipped this step would simply fail against any estate that had used `steward revoke`.
--
-- Add field subject to runstate
--
ALTER TABLE "run_state" ADD COLUMN "subject" varchar(255) DEFAULT '' NOT NULL;
ALTER TABLE "run_state" ALTER COLUMN "subject" DROP DEFAULT;
--
-- Add field celery_task_id to runstate
--
ALTER TABLE "run_state" ADD COLUMN "celery_task_id" varchar(255) DEFAULT '' NOT NULL;
ALTER TABLE "run_state" ALTER COLUMN "celery_task_id" DROP DEFAULT;
--
-- Alter field status on runstate
--
-- (no-op)
--
-- Remove constraint run_state_status_valid from model runstate
--
ALTER TABLE "run_state" DROP CONSTRAINT "run_state_status_valid";
--
-- Create constraint run_state_status_valid on model runstate
--
ALTER TABLE "run_state" ADD CONSTRAINT "run_state_status_valid" CHECK ("status" IN ('pending', 'running', 'succeeded', 'failed', 'cancelled'));
--
-- Create index run_state_subject_status on field(s) subject, status of model runstate
--
CREATE INDEX "run_state_subject_status" ON "run_state" ("subject", "status");
--
-- Create index run_state_station_status on field(s) station, status of model runstate
--
CREATE INDEX "run_state_station_status" ON "run_state" ("station", "status");
--rollback DROP INDEX "run_state_station_status";
--rollback DROP INDEX "run_state_subject_status";
--rollback UPDATE "run_state" SET "status" = 'failed' WHERE "status" = 'cancelled';
--rollback ALTER TABLE "run_state" DROP CONSTRAINT "run_state_status_valid";
--rollback ALTER TABLE "run_state" ADD CONSTRAINT "run_state_status_valid" CHECK ("status" IN ('pending', 'running', 'succeeded', 'failed'));
--rollback ALTER TABLE "run_state" DROP COLUMN "celery_task_id";
--rollback ALTER TABLE "run_state" DROP COLUMN "subject";
