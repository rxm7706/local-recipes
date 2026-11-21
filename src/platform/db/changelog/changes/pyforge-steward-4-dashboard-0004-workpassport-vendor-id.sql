--liquibase formatted sql
--changeset pyforge-steward:4
--comment sqlmigrate pyforge_steward_dashboard.0004_workpassport_vendor_id
--
-- Add field vendor_id to workpassport
--
ALTER TABLE "pyforge_steward_dashboard_workpassport" ADD COLUMN "vendor_id" varchar(64) NULL;
CREATE INDEX "pyforge_steward_dashboard_workpassport_vendor_id_c9b85270" ON "pyforge_steward_dashboard_workpassport" ("vendor_id");
CREATE INDEX "pyforge_steward_dashboard_workpassport_vendor_id_c9b85270_like" ON "pyforge_steward_dashboard_workpassport" ("vendor_id" varchar_pattern_ops);
--rollback ALTER TABLE "pyforge_steward_dashboard_workpassport" DROP COLUMN "vendor_id" CASCADE;
