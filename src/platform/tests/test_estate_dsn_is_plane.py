"""Steward 34.4: estate reads target the query plane (FR-49)."""

from __future__ import annotations

import pytest

from config.estate_dsn import EstateOltpForbidden
from config.estate_dsn import assert_estate_read_is_plane
from config.estate_dsn import estate_datasource_payload


def test_default_settings_estate_dsn_is_plane() -> None:
    pytest.importorskip("django")
    from django.conf import settings

    if not settings.configured:
        pytest.skip("Django settings not configured")
    try:
        dsn = settings.QUERY_PLANE_ESTATE_DSN
    except Exception:
        pytest.skip("QUERY_PLANE_ESTATE_DSN not on this settings module")
    assert_estate_read_is_plane(dsn)
    assert "postgres" not in dsn.lower()


def test_oltp_dsn_fails_the_gate() -> None:
    with pytest.raises(EstateOltpForbidden):
        assert_estate_read_is_plane(
            "postgresql://platform:platform@postgres:5432/platform",
        )


def test_langflow_schema_url_fails_the_gate() -> None:
    with pytest.raises(EstateOltpForbidden):
        assert_estate_read_is_plane(
            "postgresql://lf:lf@localhost:5432/platform?options=-c%20search_path=langflow_schema",
        )


def test_dbgpt_payload_is_duckdb_not_postgres() -> None:
    payload = estate_datasource_payload("platform", "duckdb:atlas.duckdb")
    assert payload["db_type"] == "duckdb"
    assert payload["file_path"] == "atlas.duckdb"
    assert payload["db_pwd"] == ""


def test_oltp_payload_is_refused() -> None:
    with pytest.raises(EstateOltpForbidden):
        estate_datasource_payload(
            "platform",
            "postgresql://platform:secret@oltp:5432/platform",
        )
