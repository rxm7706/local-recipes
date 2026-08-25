"""Story 27.2 — Liquibase changelog shape, JDBC targeting, DML-only app role."""

from __future__ import annotations

import re
import secrets
from pathlib import Path

import pytest
from django.db import connection
from django.db import transaction
from django.db.utils import ProgrammingError

from db.liquibase_update import jdbc_url_from_migration_database_url
from db.liquibase_update import liquibase_update_argv

PLATFORM_ROOT = Path(__file__).resolve().parents[2]
DB_ROOT = PLATFORM_ROOT / "db"
CHANGELOG_DIR = DB_ROOT / "changelog" / "changes"
PROPERTIES = DB_ROOT / "liquibase.properties"
APP_ROLE_SQL = DB_ROOT / "create_app_role.sql"
ALLOWED_SCHEMAS = frozenset(
    {"public", "langflow_schema", "dbgpt_schema", "liquibase"},
)
CHANGESET_ID = re.compile(r"^[a-z0-9][a-z0-9.-]*:[1-9][0-9]*$")
CREATE_SCHEMA = re.compile(
    r"CREATE\s+SCHEMA(?:\s+IF\s+NOT\s+EXISTS)?\s+([^\s;]+)",
    re.IGNORECASE,
)
CHANGESET_LINE = re.compile(r"^--changeset\s+(\S+)", re.MULTILINE)


def _changelog_sql() -> str:
    parts = [
        path.read_text(encoding="utf-8")
        for path in sorted(CHANGELOG_DIR.glob("*.sql"))
    ]
    assert parts, "no Liquibase SQL changesets -- this check would pass vacuously"
    return "\n".join(parts)


def test_preserve_schema_case_is_disabled() -> None:
    text = PROPERTIES.read_text(encoding="utf-8")
    assert re.search(r"(?i)^preserveSchemaCase:\s*false\s*$", text, re.MULTILINE), text
    argv = liquibase_update_argv("postgres://platform:x@platform-postgres:5432/platform")
    assert "--preserve-schema-case=false" in argv
    assert "--liquibase-schema-name=liquibase" in argv


def test_schema_names_are_lowercase_and_exactly_four() -> None:
    sql = _changelog_sql()
    created = {match.group(1).strip('"') for match in CREATE_SCHEMA.finditer(sql)}
    unexpected = created - ALLOWED_SCHEMAS
    assert not unexpected, f"fifth or unknown schema in changelog: {unexpected}"
    mixed = {name for name in created if name != name.lower()}
    assert not mixed, f"mixed-case schema names fail FR-21a: {mixed}"
    assert "langflow_schema" in created
    assert "dbgpt_schema" in created
    assert "liquibase" in PROPERTIES.read_text(encoding="utf-8")


def test_changeset_ids_are_distribution_seq() -> None:
    sql = _changelog_sql()
    ids = CHANGESET_LINE.findall(sql)
    assert ids, "no --changeset lines"
    for changeset_id in ids:
        assert CHANGESET_ID.match(changeset_id), (
            f"changeset id {changeset_id!r} must be distribution:seq "
            f"(bare 001-initial is review-blocking)"
        )
        assert changeset_id != "001-initial"


def test_jdbc_url_sets_current_schema_and_rejects_pooling_proxy() -> None:
    jdbc, user, password = jdbc_url_from_migration_database_url(
        "postgres://platform:s3cret@test-release-postgres:5432/platform",
    )
    assert user == "platform"
    assert password == "s3cret"  # noqa: S105 -- fixture
    assert "currentSchema=public" in jdbc
    assert "jdbc:postgresql://test-release-postgres:5432/platform" in jdbc
    with pytest.raises(ValueError, match="pooling"):
        jdbc_url_from_migration_database_url(
            "postgres://platform:x@platform-pgbouncer:5432/platform",
        )
    with pytest.raises(ValueError, match="pooling"):
        jdbc_url_from_migration_database_url(
            "postgres://platform:x@pgpool.internal:5432/platform",
        )


def test_operator_sql_revokes_create_from_app_role() -> None:
    sql = APP_ROLE_SQL.read_text(encoding="utf-8").upper()
    assert "REVOKE CREATE ON SCHEMA PUBLIC FROM PLATFORM_APP" in sql
    assert "REVOKE CREATE ON SCHEMA PUBLIC FROM PUBLIC" in sql


@pytest.mark.django_db(transaction=True)
def test_app_role_create_alter_drop_refused_by_postgresql() -> None:
    if connection.vendor != "postgresql":
        pytest.skip("postgresql required for FR-22 privilege proof")

    role = f"dml_only_{secrets.token_hex(4)}"
    table = f"dml_probe_{secrets.token_hex(4)}"
    with connection.cursor() as cursor:
        try:
            cursor.execute(f'CREATE ROLE "{role}" NOINHERIT')
        except ProgrammingError as exc:
            pytest.skip(f"cannot CREATE ROLE in this database: {exc}")
        try:
            cursor.execute(f'REVOKE CREATE ON SCHEMA public FROM "{role}"')
            with transaction.atomic():
                cursor.execute(f'SET ROLE "{role}"')
                with pytest.raises(ProgrammingError) as create_error:
                    cursor.execute(f'CREATE TABLE "{table}" (id integer)')
                err = str(create_error.value).lower()
                assert "permission denied" in err or "42501" in err
            cursor.execute("RESET ROLE")
            cursor.execute(f'CREATE TABLE "{table}" (id integer)')
            try:
                with transaction.atomic():
                    cursor.execute(f'SET ROLE "{role}"')
                    with pytest.raises(ProgrammingError) as alter_error:
                        cursor.execute(
                            f'ALTER TABLE "{table}" ADD COLUMN extra integer',
                        )
                    alter = str(alter_error.value).lower()
                    assert "must be owner" in alter or "permission denied" in alter
                with transaction.atomic():
                    cursor.execute(f'SET ROLE "{role}"')
                    with pytest.raises(ProgrammingError) as drop_error:
                        cursor.execute(f'DROP TABLE "{table}"')
                    drop = str(drop_error.value).lower()
                    assert "must be owner" in drop or "permission denied" in drop
            finally:
                cursor.execute("RESET ROLE")
                cursor.execute(f'DROP TABLE IF EXISTS "{table}"')
        finally:
            cursor.execute("RESET ROLE")
            cursor.execute(f'DROP ROLE IF EXISTS "{role}"')


def test_values_app_username_matches_changelog_grants() -> None:
    values = (PLATFORM_ROOT / "deploy/charts/platform/values.yaml").read_text(
        encoding="utf-8",
    )
    grants = (CHANGELOG_DIR / "python-agent-platform-2-app-role-grants.sql").read_text(
        encoding="utf-8",
    )
    assert "appUsername: platform_app" in values
    assert "platform_app" in grants
