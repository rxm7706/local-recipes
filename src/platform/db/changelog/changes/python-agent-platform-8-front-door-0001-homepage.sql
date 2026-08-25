--liquibase formatted sql
--changeset python-agent-platform:8
--comment sqlmigrate front_door.0001_homepage
--
-- Create model HomePage
--
CREATE TABLE "front_door_homepage" ("page_ptr_id" integer NOT NULL PRIMARY KEY, "body" text NOT NULL);
ALTER TABLE "front_door_homepage" ADD CONSTRAINT "front_door_homepage_page_ptr_id_8cb0f4c7_fk_wagtailcore_page_id" FOREIGN KEY ("page_ptr_id") REFERENCES "wagtailcore_page" ("id") DEFERRABLE INITIALLY DEFERRED;
