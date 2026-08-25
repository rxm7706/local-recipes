"""Unit tests for the Liquibase Job URL helper (no helm, no postgres)."""

from __future__ import annotations

import pytest

from db.liquibase_update import jdbc_url_from_migration_database_url
from db.liquibase_update import liquibase_update_argv


def test_argv_starts_with_liquibase_update() -> None:
    argv = liquibase_update_argv(
        "postgresql://migrator:pw@platform-postgres:5432/platform",
    )
    assert argv[0] == "liquibase"
    assert argv[-1] == "update"
    assert any(
        part.startswith("--url=") and "currentSchema=public" in part for part in argv
    )


def test_missing_host_rejected() -> None:
    with pytest.raises(ValueError, match="hostname"):
        jdbc_url_from_migration_database_url("postgres://user:pw@/platform")
