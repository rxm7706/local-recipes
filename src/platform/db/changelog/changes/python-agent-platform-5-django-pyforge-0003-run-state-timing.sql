--liquibase formatted sql
--changeset python-agent-platform:5
--comment sqlmigrate django_pyforge.0003_run_state_timing
--
-- Add field station to runstate
--
ALTER TABLE "run_state" ADD COLUMN "station" varchar(64) DEFAULT '' NOT NULL;
ALTER TABLE "run_state" ALTER COLUMN "station" DROP DEFAULT;
--
-- Add field started_at to runstate
--
ALTER TABLE "run_state" ADD COLUMN "started_at" timestamp with time zone NULL;
--
-- Add field heartbeat_at to runstate
--
ALTER TABLE "run_state" ADD COLUMN "heartbeat_at" timestamp with time zone NULL;
--
-- Add field completed_at to runstate
--
ALTER TABLE "run_state" ADD COLUMN "completed_at" timestamp with time zone NULL;
--
-- Add field duration_ms to runstate
--
ALTER TABLE "run_state" ADD COLUMN "duration_ms" integer NULL CHECK ("duration_ms" >= 0);
