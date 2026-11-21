--liquibase formatted sql
--changeset pyforge-steward:7
--comment sqlmigrate pyforge_steward_dashboard.0008_quarantineshelfrow
--
-- Create model QuarantineShelfRow
--
CREATE TABLE "pyforge_steward_dashboard_quarantineshelfrow" ("row_id" varchar(64) NOT NULL PRIMARY KEY, "vendor_id" varchar(64) NOT NULL, "jira_key" varchar(64) NULL, "github_item_id" varchar(64) NULL, "title" varchar(512) NOT NULL, "passport_id" varchar(64) NULL, "arrived_at" timestamp with time zone NOT NULL, "linked_at" timestamp with time zone NULL);
CREATE INDEX "pyforge_steward_dashboar_row_id_a24d7c99_like" ON "pyforge_steward_dashboard_quarantineshelfrow" ("row_id" varchar_pattern_ops);
CREATE INDEX "pyforge_steward_dashboard_quarantineshelfrow_vendor_id_ac548d5e" ON "pyforge_steward_dashboard_quarantineshelfrow" ("vendor_id");
CREATE INDEX "pyforge_steward_dashboar_vendor_id_ac548d5e_like" ON "pyforge_steward_dashboard_quarantineshelfrow" ("vendor_id" varchar_pattern_ops);
CREATE INDEX "pyforge_steward_dashboard_quarantineshelfrow_jira_key_17fbd30a" ON "pyforge_steward_dashboard_quarantineshelfrow" ("jira_key");
CREATE INDEX "pyforge_steward_dashboar_jira_key_17fbd30a_like" ON "pyforge_steward_dashboard_quarantineshelfrow" ("jira_key" varchar_pattern_ops);
CREATE INDEX "pyforge_steward_dashboard__github_item_id_e0857a20" ON "pyforge_steward_dashboard_quarantineshelfrow" ("github_item_id");
CREATE INDEX "pyforge_steward_dashboar_github_item_id_e0857a20_like" ON "pyforge_steward_dashboard_quarantineshelfrow" ("github_item_id" varchar_pattern_ops);
CREATE INDEX "pyforge_steward_dashboard__passport_id_da0f1724" ON "pyforge_steward_dashboard_quarantineshelfrow" ("passport_id");
CREATE INDEX "pyforge_steward_dashboar_passport_id_da0f1724_like" ON "pyforge_steward_dashboard_quarantineshelfrow" ("passport_id" varchar_pattern_ops);
CREATE INDEX "pyforge_steward_dashboard__arrived_at_e39a2643" ON "pyforge_steward_dashboard_quarantineshelfrow" ("arrived_at");
--rollback DROP TABLE IF EXISTS "pyforge_steward_dashboard_quarantineshelfrow" CASCADE;
