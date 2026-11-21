--liquibase formatted sql
--changeset pyforge-steward:5
--comment sqlmigrate pyforge_steward_dashboard.0005_corridorload_signer_corridorload_slice_name
--
-- Add field signer to corridorload
--
ALTER TABLE "pyforge_steward_dashboard_corridorload" ADD COLUMN "signer" varchar(255) DEFAULT '' NOT NULL;
ALTER TABLE "pyforge_steward_dashboard_corridorload" ALTER COLUMN "signer" DROP DEFAULT;
--
-- Add field slice_name to corridorload
--
ALTER TABLE "pyforge_steward_dashboard_corridorload" ADD COLUMN "slice_name" varchar(128) DEFAULT '' NOT NULL;
ALTER TABLE "pyforge_steward_dashboard_corridorload" ALTER COLUMN "slice_name" DROP DEFAULT;
--rollback ALTER TABLE IF EXISTS "pyforge_steward_dashboard_corridorload" DROP COLUMN IF EXISTS "slice_name" CASCADE;
--rollback ALTER TABLE IF EXISTS "pyforge_steward_dashboard_corridorload" DROP COLUMN IF EXISTS "signer" CASCADE;
