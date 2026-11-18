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
    assert len(DUTIES) == 31  # noqa: PLR2004 -- + ci (Story 99.3) after estate (Story 100.2), + preflight (Story 103.6), + pages (Story 102.3)


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


def test_restore_drill_reports_a_failure_of_the_drill_as_data(tmp_path: Path):
    """A drill that raises is refused as evidence, never as an exception (AD-8)."""

    class _Raises:
        @staticmethod
        def run_restore_drill(*, backup_path: Path):
            raise RuntimeError(f"pg_restore not on PATH for {backup_path.name}")

    ns = build_parser().parse_args(["restore", "--drill", "--backup-path", str(tmp_path / "backup")])
    with patch("pyforge.steward.restore._load_postgres_backup_module", return_value=_Raises):
        result = RestoreDuty().run(ns)
    assert result.ok is False
    assert result.summary.startswith("restore drill failed: pg_restore not on PATH")
    assert result.details["backup_path"] == str((tmp_path / "backup").resolve())
    assert "pg_restore" in result.details["error"]


def test_the_backup_module_is_loaded_from_the_checkout_by_file_path(tmp_path: Path):
    """The loader reads src/platform/db/postgres_backup.py under the repo root it is given, by path,
    so the duty never imports the host package."""
    import sys

    from pyforge.steward import restore

    module_dir = tmp_path / "src" / "platform" / "db"
    module_dir.mkdir(parents=True)
    (module_dir / "postgres_backup.py").write_text(
        "def run_restore_drill(*, backup_path):\n    return {'ok': True, 'backup_path': str(backup_path)}\n",
        encoding="utf-8",
    )
    sys.modules.pop("platform_postgres_backup", None)
    try:
        with patch("pyforge.steward.restore.repo_root", return_value=tmp_path):
            module = restore._load_postgres_backup_module()
            assert module.__file__ == str(module_dir / "postgres_backup.py")
            ns = build_parser().parse_args(["restore", "--drill", "--backup-path", str(tmp_path / "b")])
            result = RestoreDuty().run(ns)
    finally:
        sys.modules.pop("platform_postgres_backup", None)
    assert result.ok is True
    assert result.summary == "restore drill: counts match manifest"
    assert result.details["backup_path"] == str((tmp_path / "b").resolve())


def test_a_backup_module_with_no_loader_is_a_named_error(tmp_path: Path):
    from pyforge.steward import restore

    with (
        patch("pyforge.steward.restore.repo_root", return_value=tmp_path),
        patch("pyforge.steward.restore.importlib.util.spec_from_file_location", return_value=None),
    ):
        ns = build_parser().parse_args(["restore", "--drill", "--backup-path", str(tmp_path / "b")])
        result = RestoreDuty().run(ns)
        try:
            restore._load_postgres_backup_module()
        except RuntimeError as exc:
            assert "could not load postgres backup module" in str(exc)
        else:  # pragma: no cover - the assertion above is the point
            raise AssertionError("a missing loader must raise")
    assert result.ok is False
    assert "could not load postgres backup module" in result.summary
