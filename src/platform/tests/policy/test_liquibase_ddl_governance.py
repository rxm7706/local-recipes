"""Liquibase changelog shape, JDBC targeting, DML-only app role.

Story 27.2 shipped the shape; Story 41.3 added the rollback policy and
scribe's own distribution sequence (red-team S-4 / B-1 / R-12).
"""

from __future__ import annotations

import re
import secrets
from pathlib import Path

import pytest
import yaml
from django.db import connection
from django.db import transaction
from django.db.utils import ProgrammingError

from db.liquibase_update import jdbc_url_from_migration_database_url
from db.liquibase_update import liquibase_update_argv

PLATFORM_ROOT = Path(__file__).resolve().parents[2]
DB_ROOT = PLATFORM_ROOT / "db"
CHANGELOG_DIR = DB_ROOT / "changelog" / "changes"
MASTER_CHANGELOG = DB_ROOT / "changelog" / "db.changelog-master.yaml"
PROPERTIES = DB_ROOT / "liquibase.properties"
APP_ROLE_SQL = DB_ROOT / "create_app_role.sql"
DB_README = DB_ROOT / "README.md"
ALLOWED_SCHEMAS = frozenset(
    # Story 41.3 added scribe_schema: scribe's graph relations are governed
    # DDL now, not something its runtime driver creates for itself.
    {"public", "langflow_schema", "dbgpt_schema", "liquibase", "scribe_schema"},
)
CHANGESET_ID = re.compile(r"^[a-z0-9][a-z0-9.-]*:[1-9][0-9]*$")
CREATE_SCHEMA = re.compile(
    r"CREATE\s+SCHEMA(?:\s+IF\s+NOT\s+EXISTS)?\s+([^\s;]+)",
    re.IGNORECASE,
)
CHANGESET_LINE = re.compile(r"^--changeset\s+(\S+)(?P<attributes>.*)$", re.MULTILINE)
ROLLBACK_LINE = re.compile(r"^--rollback\s+(?P<body>\S.*?)\s*$", re.MULTILINE)
# Liquibase's own two escape hatches. `--rollback empty` / `--rollback not
# required` satisfy the parser while declaring there is no way back -- exactly
# what the policy exists to forbid outside a documented exception.
EMPTY_ROLLBACK = re.compile(r"^(empty|not\s+required)\s*;?$", re.IGNORECASE)
COMMENT_LINE = re.compile(r"^--comment\s+\S", re.MULTILINE)
RUN_IN_TRANSACTION_FALSE = re.compile(r"runInTransaction:\s*false", re.IGNORECASE)
SCRIBE_CHANGESETS = (
    "pyforge-scribe:1",
    "pyforge-scribe:2",
    "pyforge-scribe:3",
    "pyforge-scribe:4",
)
# Story 41.3 wrote the rollback policy; these changesets predate it and CAP-9
# shipped them. The list is closed and literal -- a new changeset cannot join
# it without showing up in review.
GRANDFATHERED_WITHOUT_ROLLBACK = frozenset(
    f"python-agent-platform:{seq}" for seq in range(1, 20)
)


def _changeset_entries() -> list[tuple[Path, str, str]]:
    """``(path, distribution:seq, body)`` for every changeset file.

    A list, not a dict: two files declaring the same id must be visible as a
    collision rather than collapsing into one key (which also let the loser
    slip past the rollback gate).
    """
    entries: list[tuple[Path, str, str]] = []
    for path in sorted(CHANGELOG_DIR.glob("*.sql")):
        text = path.read_text(encoding="utf-8")
        match = CHANGESET_LINE.search(text)
        assert match is not None, f"{path.name} has no --changeset header"
        entries.append((path, match.group(1), text))
    assert entries, "no Liquibase SQL changesets -- this check would pass vacuously"
    return entries


def _changeset_files() -> dict[str, str]:
    """``distribution:seq`` → file body (ids are unique; see the collision test)."""
    return {changeset_id: body for _path, changeset_id, body in _changeset_entries()}


def _has_real_rollback(body: str) -> bool:
    """True when at least one ``--rollback`` line is an actual statement."""
    return any(
        not EMPTY_ROLLBACK.match(match.group("body"))
        for match in ROLLBACK_LINE.finditer(body)
    )


def _master_includes() -> list[str]:
    """Every ``include: file:`` in the master changelog, in document order."""
    document = yaml.safe_load(MASTER_CHANGELOG.read_text(encoding="utf-8")) or {}
    return [
        entry["include"]["file"]
        for entry in document.get("databaseChangeLog", [])
        if isinstance(entry, dict) and "include" in entry
    ]


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


def test_schema_names_are_lowercase_and_known() -> None:
    sql = _changelog_sql()
    created = {match.group(1).strip('"') for match in CREATE_SCHEMA.finditer(sql)}
    unexpected = created - ALLOWED_SCHEMAS
    assert not unexpected, f"unknown schema in changelog: {unexpected}"
    mixed = {name for name in created if name != name.lower()}
    assert not mixed, f"mixed-case schema names fail FR-21a: {mixed}"
    assert "langflow_schema" in created
    assert "dbgpt_schema" in created
    assert "scribe_schema" in created
    assert "liquibase" in PROPERTIES.read_text(encoding="utf-8")
    source = (DB_ROOT / "liquibase_update.py").read_text(encoding="utf-8")
    assert "CREATE SCHEMA IF NOT EXISTS liquibase" in source


def test_changeset_ids_are_distribution_seq() -> None:
    sql = _changelog_sql()
    ids = [match.group(1) for match in CHANGESET_LINE.finditer(sql)]
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


def test_every_changeset_carries_rollback_or_a_documented_exception() -> None:
    """Story 41.3: no new changeset lands without a way back.

    ``--rollback empty`` and ``--rollback not required`` do not count: they are
    a declaration that there is none, which is the case the policy forbids.
    """
    offenders: list[str] = []
    for _path, changeset_id, body in _changeset_entries():
        if changeset_id in GRANDFATHERED_WITHOUT_ROLLBACK:
            continue
        if _has_real_rollback(body):
            continue
        header = CHANGESET_LINE.search(body)
        assert header is not None
        exception = RUN_IN_TRANSACTION_FALSE.search(header.group("attributes"))
        if exception and COMMENT_LINE.search(body):
            continue
        offenders.append(changeset_id)
    assert not offenders, (
        "changesets without a real --rollback (`empty` / `not required` do not "
        "count) and without a documented runInTransaction:false exception "
        f"(db/README.md): {sorted(offenders)}"
    )


def test_empty_rollback_forms_do_not_satisfy_the_gate() -> None:
    """The gate's own escape-hatch discrimination, proven on both spellings."""
    for hatch in ("empty", "not required", "NOT   REQUIRED", "empty;"):
        assert not _has_real_rollback(
            f"--changeset x:1\nSELECT 1;\n--rollback {hatch}\n",
        ), hatch
    assert _has_real_rollback("--changeset x:1\nSELECT 1;\n--rollback DROP TABLE x;\n")
    # A real rollback beside an escape hatch still counts as a way back.
    assert _has_real_rollback(
        "--changeset x:1\nSELECT 1;\n--rollback empty\n--rollback DROP TABLE x;\n",
    )


def test_every_changeset_file_is_included_in_the_master_changelog() -> None:
    """An un-included changeset file is inert: no extension, or no grants."""
    includes = _master_includes()
    on_disk = {f"changes/{path.name}" for path, _id, _body in _changeset_entries()}
    missing = sorted(on_disk - set(includes))
    assert not missing, (
        f"changeset files absent from db.changelog-master.yaml: {missing}"
    )
    dangling = sorted(set(includes) - on_disk)
    assert not dangling, f"master changelog includes non-existent files: {dangling}"
    duplicated = sorted({name for name in includes if includes.count(name) > 1})
    assert not duplicated, f"included more than once: {duplicated}"


def test_rollback_grandfather_list_still_names_live_changesets() -> None:
    """The exemption cannot rot into a blanket pass for ids that are gone."""
    present = set(_changeset_files())
    missing = GRANDFATHERED_WITHOUT_ROLLBACK - present
    assert not missing, (
        f"grandfathered changeset ids no longer in the changelog: {sorted(missing)}"
    )
    assert not any(
        changeset_id.startswith("pyforge-scribe:")
        for changeset_id in GRANDFATHERED_WITHOUT_ROLLBACK
    ), "Story 41.3's own changesets are not grandfathered"


def test_rollback_policy_and_exception_process_are_written_down() -> None:
    text = DB_README.read_text(encoding="utf-8")
    assert "## Rollback policy" in text
    assert "--rollback" in text
    assert "runInTransaction" in text
    assert "recovery" in text.lower(), "the exception process must say how to recover"


def test_scribe_owns_its_own_distribution_sequence() -> None:
    """Red-team B-1 / R-12: per-distribution ids, scribe's DDL in the changelog."""
    data = yaml.safe_load((DB_ROOT / "sqlmigrate-map.yaml").read_text(encoding="utf-8"))
    distributions = data["distributions"]
    assert "python-agent-platform" in distributions
    assert "pyforge-scribe" in distributions
    assert data["default"] in distributions

    bodies = _changeset_files()
    for changeset_id in SCRIBE_CHANGESETS:
        assert changeset_id in bodies, f"{changeset_id} missing from the changelog"

    scribe_sql = "\n".join(bodies[cid] for cid in SCRIBE_CHANGESETS).upper()
    assert "CREATE EXTENSION IF NOT EXISTS VECTOR" in scribe_sql
    assert "CREATE SCHEMA IF NOT EXISTS SCRIBE_SCHEMA" in scribe_sql
    assert "SCRIBE_SCHEMA.GRAPH_NODES" in scribe_sql
    assert "ADD COLUMN IF NOT EXISTS STALE" in scribe_sql

    # Every changeset's distribution is registered in the map.
    for changeset_id in bodies:
        distribution = changeset_id.split(":", 1)[0]
        assert distribution in distributions, (
            f"{changeset_id} uses an unregistered distribution; add it to "
            f"sqlmigrate-map.yaml"
        )


def test_changeset_ids_are_unique_across_files() -> None:
    """Two files on one id collapse silently and one escapes the rollback gate."""
    by_id: dict[str, list[str]] = {}
    for path, changeset_id, _body in _changeset_entries():
        by_id.setdefault(changeset_id, []).append(path.name)
    collisions = {
        changeset_id: names for changeset_id, names in by_id.items() if len(names) > 1
    }
    assert not collisions, f"changeset id declared by more than one file: {collisions}"


def test_no_governed_sql_grants_create_to_the_app_role() -> None:
    """Block-If: widening platform_app defeats the control CAP-9 buys."""
    for text in (_changelog_sql(), APP_ROLE_SQL.read_text(encoding="utf-8")):
        upper = re.sub(r"\s+", " ", text.upper())
        assert "GRANT CREATE" not in upper
        assert "GRANT ALL" not in upper


def test_values_app_username_matches_changelog_grants() -> None:
    values = (PLATFORM_ROOT / "deploy/charts/platform/values.yaml").read_text(
        encoding="utf-8",
    )
    grants = (CHANGELOG_DIR / "python-agent-platform-2-app-role-grants.sql").read_text(
        encoding="utf-8",
    )
    assert "appUsername: platform_app" in values
    assert "platform_app" in grants
