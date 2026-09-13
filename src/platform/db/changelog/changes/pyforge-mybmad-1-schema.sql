--liquibase formatted sql
--changeset pyforge-mybmad:1
--comment Story 52.1: Prisma schema mybmad only. Django/Liquibase objects in public stay unchanged. The mybmad sidecar never owns public.
CREATE SCHEMA IF NOT EXISTS mybmad;
--rollback DROP SCHEMA IF EXISTS mybmad;
