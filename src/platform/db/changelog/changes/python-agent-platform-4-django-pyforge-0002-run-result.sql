--liquibase formatted sql
--changeset python-agent-platform:4
--comment sqlmigrate django_pyforge.0002_run_result_and_handle_subject
--
-- Add field result to runstate
--
ALTER TABLE "run_state" ADD COLUMN "result" jsonb NULL;
--
-- Add field subject to mcphandle
--
ALTER TABLE "mcp_handles" ADD COLUMN "subject" varchar(255) DEFAULT '' NOT NULL;
ALTER TABLE "mcp_handles" ALTER COLUMN "subject" DROP DEFAULT;
