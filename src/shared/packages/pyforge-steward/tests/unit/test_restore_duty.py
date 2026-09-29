"""Story 41.1 — restore duty drill behaviour."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from pyforge.steward.cli import DUTIES, build_parser, resolve_duty
from pyforge.steward.interfaces import DutyResult
from pyforge.steward.restore import RestoreDuty


def test_restore_is_fourteenth_duty():
    assert "restore" in DUTIES
    assert DUTIES.index("restore") == 13  # noqa: PLR2004 -- the fourteenth slot
    assert len(DUTIES) == 25  # noqa: PLR2004 -- + `cutover` (Story 44.12) + `ledger-query` (Story 65.1) + `catalog` (Story 60.1) + `load` (Story 61.1) + passport (Story 61.2) + glass (Story 61.3) + session (Story 63.4) + deck-drift (Story 59.4)


def test_restore_resolves_to_restore_duty():
    assert isinstance(resolve_duty("restore"), RestoreDuty)


def test_restore_drill_requires_drill_flag():
    duty = RestoreDuty()
    ns = build_parser().parse_args(
        ["restore", "--backup-path", "/tmp/backup"],
    )
    result = duty.run(ns)
    assert result.ok is False
    assert "--drill" in result.summary


def test_restore_drill_count_match(tmp_path: Path):
    backup_dir = tmp_path / "base" / "20260101T000000Z"
    backup_dir.mkdir(parents=True)
    dump_path = tmp_path / "drill" / "20260101T000000Z" / "dump.pgcustom"
    dump_path.parent.mkdir(parents=True)
    dump_path.write_text("placeholder", encoding="utf-8")
    manifest = {
        "timestamp": "20260101T000000Z",
        "run_state_count": 3,
        "wagtail_page_count": 7,
        "base_dir": str(backup_dir),
        "drill_dump": str(dump_path),
    }
    (backup_dir / "manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    duty = RestoreDuty()
    ns = build_parser().parse_args(
        ["restore", "--drill", "--backup-path", str(backup_dir)],
    )
    drill_result = {
        "ok": True,
        "manifest_path": str(backup_dir / "manifest.json"),
        "expected": {"run_state_count": 3, "wagtail_page_count": 7},
        "actual": {"run_state_count": 3, "wagtail_page_count": 7},
        "scratch_database": "platform_drill_test",
    }
    with patch(
        "pyforge.steward.restore._load_postgres_backup_module",
    ) as load_mod:
        load_mod.return_value.run_restore_drill.return_value = drill_result
        result = duty.run(ns)
    assert isinstance(result, DutyResult)
    assert result.ok is True
    assert result.details["actual"]["run_state_count"] == 3


def test_restore_drill_mismatch_exits_failed(tmp_path: Path):
    backup_dir = tmp_path / "latest"
    backup_dir.mkdir()
    (backup_dir / "manifest.json").write_text("{}", encoding="utf-8")
    duty = RestoreDuty()
    ns = build_parser().parse_args(
        ["restore", "--drill", "--backup-path", str(backup_dir)],
    )
    drill_result = {
        "ok": False,
        "expected": {"run_state_count": 1, "wagtail_page_count": 2},
        "actual": {"run_state_count": 0, "wagtail_page_count": 2},
    }
    with patch(
        "pyforge.steward.restore._load_postgres_backup_module",
    ) as load_mod:
        load_mod.return_value.run_restore_drill.return_value = drill_result
        result = duty.run(ns)
    assert result.ok is False
    assert "mismatch" in result.summary
