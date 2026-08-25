--liquibase formatted sql
--changeset python-agent-platform:11
--comment sqlmigrate sites.0002_alter_domain_unique
--
-- Alter field domain on site
--
ALTER TABLE "django_site" ADD CONSTRAINT "django_site_domain_a2e37b91_uniq" UNIQUE ("domain");
CREATE INDEX "django_site_domain_a2e37b91_like" ON "django_site" ("domain" varchar_pattern_ops);
