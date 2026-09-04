"""Unit tests for the Liquibase Job URL helper (no helm, no postgres)."""

from __future__ import annotations

from pathlib import Path

import pytest

from db.liquibase_update import jdbc_url_from_migration_database_url
from db.liquibase_update import liquibase_update_argv

PLATFORM_ROOT = Path(__file__).resolve().parents[1]
CHANGELOG_MASTER = PLATFORM_ROOT / "db" / "changelog" / "db.changelog-master.yaml"
CHANGESET_19 = (
    PLATFORM_ROOT
    / "db"
    / "changelog"
    / "changes"
    / "python-agent-platform-19-wagtail-7-4-catchup.sql"
)


def test_argv_starts_with_liquibase_update() -> None:
    argv = liquibase_update_argv(
        "postgresql://migrator:pw@platform-postgres:5432/platform",
    )
    assert argv[0] == "liquibase"
    assert argv[-1] == "update"
    assert any(
        part.startswith("--url=") and "currentSchema=public" in part for part in argv
    )


def test_changeset_19_adds_wagtail_site_name_and_is_included() -> None:
    body = CHANGESET_19.read_text(encoding="utf-8")
    assert "--changeset python-agent-platform:19" in body
    assert 'ADD COLUMN "site_name"' in body
    assert "ALTER COLUMN" in body and " TYPE " not in body
    master = CHANGELOG_MASTER.read_text(encoding="utf-8")
    assert "python-agent-platform-19-wagtail-7-4-catchup.sql" in master


def test_missing_host_rejected() -> None:
    with pytest.raises(ValueError, match="hostname"):
        jdbc_url_from_migration_database_url("postgres://user:pw@/platform")
