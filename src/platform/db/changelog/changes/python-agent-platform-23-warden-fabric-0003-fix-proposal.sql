--liquibase formatted sql
--changeset python-agent-platform:23
--comment sqlmigrate warden_fabric.0003_fix_proposal — Story 16.3 fix proposal queue.

--
-- Create model FixProposal
--
CREATE TABLE "warden_fabric_fixproposal" ("id" uuid NOT NULL PRIMARY KEY, "repo_full_name" varchar(512) NOT NULL, "finding_id" varchar(512) NOT NULL, "action" varchar(32) NOT NULL, "target" varchar(512) NOT NULL, "planned_paths_json" text NOT NULL, "state" varchar(16) NOT NULL, "pr_url" text NOT NULL, "error" text NOT NULL, "approved_by" varchar(255) NOT NULL, "approved_at" timestamp with time zone NULL, "created_at" timestamp with time zone NOT NULL, "updated_at" timestamp with time zone NOT NULL, "fleet_repo_scan_id" uuid NOT NULL);
--
-- Create constraint warden_fabric_fixproposal_scan_finding_uniq on model fixproposal
--
ALTER TABLE "warden_fabric_fixproposal" ADD CONSTRAINT "warden_fabric_fixproposal_scan_finding_uniq" UNIQUE ("fleet_repo_scan_id", "finding_id");
ALTER TABLE "warden_fabric_fixproposal" ADD CONSTRAINT "warden_fabric_fixpro_fleet_repo_scan_id_c0fb26a7_fk_warden_fa" FOREIGN KEY ("fleet_repo_scan_id") REFERENCES "warden_fabric_fleetreposcan" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "warden_fabric_fixproposal_fleet_repo_scan_id_c0fb26a7" ON "warden_fabric_fixproposal" ("fleet_repo_scan_id");
--rollback DROP TABLE IF EXISTS "warden_fabric_fixproposal";
