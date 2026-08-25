--liquibase formatted sql
--changeset python-agent-platform:7
--comment sqlmigrate users.0002_user_idp_subject
--
-- Add field idp_subject to user
--
ALTER TABLE "users_user" ADD COLUMN "idp_subject" varchar(255) NULL UNIQUE;
CREATE INDEX "users_user_idp_subject_649fc044_like" ON "users_user" ("idp_subject" varchar_pattern_ops);
