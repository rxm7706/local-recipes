--liquibase formatted sql
--changeset python-agent-platform:24
--comment sqlmigrate warden_fabric.0004_fleet_run_repo_counts — Story 16.7 fleet run failed and skipped repo counts.

--
-- Add field failed_repo_count to fleetrun
--
ALTER TABLE "warden_fabric_fleetrun" ADD COLUMN "failed_repo_count" integer DEFAULT 0 NOT NULL CHECK ("failed_repo_count" >= 0);
ALTER TABLE "warden_fabric_fleetrun" ALTER COLUMN "failed_repo_count" DROP DEFAULT;
--
-- Add field skipped_repo_count to fleetrun
--
ALTER TABLE "warden_fabric_fleetrun" ADD COLUMN "skipped_repo_count" integer DEFAULT 0 NOT NULL CHECK ("skipped_repo_count" >= 0);
ALTER TABLE "warden_fabric_fleetrun" ALTER COLUMN "skipped_repo_count" DROP DEFAULT;
--rollback ALTER TABLE "warden_fabric_fleetrun" DROP COLUMN "skipped_repo_count";
--rollback ALTER TABLE "warden_fabric_fleetrun" DROP COLUMN "failed_repo_count";
