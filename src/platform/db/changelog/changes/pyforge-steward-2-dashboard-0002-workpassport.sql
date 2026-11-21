--liquibase formatted sql
--changeset pyforge-steward:2
--comment sqlmigrate pyforge_steward_dashboard.0002_workpassport
--
-- Create model WorkPassport
--
CREATE TABLE "pyforge_steward_dashboard_workpassport" ("passport_id" varchar(64) NOT NULL PRIMARY KEY, "story_id" varchar(64) NOT NULL, "station" varchar(64) NOT NULL, "epic_id" varchar(64) NOT NULL, "title" varchar(512) NOT NULL, "status" varchar(32) NOT NULL, "jira_key" varchar(64) NULL, "github_item_id" varchar(64) NULL, "effort" varchar(32) NULL, "created_at" timestamp with time zone NOT NULL, "updated_at" timestamp with time zone NOT NULL);
CREATE INDEX "pyforge_steward_dashboar_passport_id_2095df1a_like" ON "pyforge_steward_dashboard_workpassport" ("passport_id" varchar_pattern_ops);
CREATE INDEX "pyforge_steward_dashboard_workpassport_story_id_e98b2e17" ON "pyforge_steward_dashboard_workpassport" ("story_id");
CREATE INDEX "pyforge_steward_dashboard_workpassport_story_id_e98b2e17_like" ON "pyforge_steward_dashboard_workpassport" ("story_id" varchar_pattern_ops);
CREATE INDEX "pyforge_steward_dashboard_workpassport_station_b4a71714" ON "pyforge_steward_dashboard_workpassport" ("station");
CREATE INDEX "pyforge_steward_dashboard_workpassport_station_b4a71714_like" ON "pyforge_steward_dashboard_workpassport" ("station" varchar_pattern_ops);
CREATE INDEX "pyforge_steward_dashboard_workpassport_status_da2d2e2a" ON "pyforge_steward_dashboard_workpassport" ("status");
CREATE INDEX "pyforge_steward_dashboard_workpassport_status_da2d2e2a_like" ON "pyforge_steward_dashboard_workpassport" ("status" varchar_pattern_ops);
CREATE INDEX "pyforge_steward_dashboard_workpassport_jira_key_09439edb" ON "pyforge_steward_dashboard_workpassport" ("jira_key");
CREATE INDEX "pyforge_steward_dashboard_workpassport_jira_key_09439edb_like" ON "pyforge_steward_dashboard_workpassport" ("jira_key" varchar_pattern_ops);
CREATE INDEX "pyforge_steward_dashboard_workpassport_github_item_id_ded5227c" ON "pyforge_steward_dashboard_workpassport" ("github_item_id");
CREATE INDEX "pyforge_steward_dashboar_github_item_id_ded5227c_like" ON "pyforge_steward_dashboard_workpassport" ("github_item_id" varchar_pattern_ops);
--rollback DROP TABLE "pyforge_steward_dashboard_workpassport" CASCADE;
