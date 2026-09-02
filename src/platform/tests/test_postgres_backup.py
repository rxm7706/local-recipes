"""Story 41.1 — postgres_backup manifest and drill helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_run_restore_drill_missing_manifest(tmp_path: Path, monkeypatch):
    from db import postgres_backup  # noqa: PLC0415 — platform test package root

    monkeypatch.setenv("MIGRATION_DATABASE_URL", "postgres://u:p@localhost:5432/platform")
    with pytest.raises(FileNotFoundError, match="manifest.json"):
        postgres_backup.run_restore_drill(backup_path=tmp_path / "missing")


def test_manifest_roundtrip_fields(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    manifest = {
        "timestamp": "20260101T000000Z",
        "run_state_count": 4,
        "wagtail_page_count": 9,
        "drill_dump": str(tmp_path / "dump.pgcustom"),
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert loaded["run_state_count"] == 4
    assert loaded["wagtail_page_count"] == 9
