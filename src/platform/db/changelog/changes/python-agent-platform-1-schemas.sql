--liquibase formatted sql
--changeset python-agent-platform:1
--comment Engine schemas. public already exists; liquibase tracking schema is liquibaseSchemaName=liquibase.
CREATE SCHEMA IF NOT EXISTS langflow_schema;
CREATE SCHEMA IF NOT EXISTS dbgpt_schema;
