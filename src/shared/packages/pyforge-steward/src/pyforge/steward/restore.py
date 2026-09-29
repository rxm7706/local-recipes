"""Steward ``restore`` duty — PostgreSQL restore drill (Story 41.1).

``pyforge steward restore --drill`` restores a custom-format dump into a
scratch database, asserts ``run_state`` and ``wagtailcore_page`` counts
against the backup manifest, and returns frozen evidence (AD-8: never
``sys.exit()`` here).
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

from .bootstrap import repo_root
from .interfaces import DutyResult


def _load_postgres_backup_module():
    """Load platform/db/postgres_backup.py without importing pyforge.* from host."""
    module_path = repo_root() / "src" / "platform" / "db" / "postgres_backup.py"
    spec = importlib.util.spec_from_file_location(
        "platform_postgres_backup",
        module_path,
    )
    if spec is None or spec.loader is None:
        msg = f"could not load postgres backup module from {module_path}"
        raise RuntimeError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RestoreDuty:
    name = "restore"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        if not ns.drill:
            return DutyResult(
                ok=False,
                summary="restore: --drill is required (full operator restore is restore.md)",
            )
        backup_path = Path(ns.backup_path).resolve()
        try:
            backup_mod = _load_postgres_backup_module()
            result = backup_mod.run_restore_drill(backup_path=backup_path)
        except Exception as exc:  # noqa: BLE001 — duty boundary
            return DutyResult(
                ok=False,
                summary=f"restore drill failed: {exc}",
                details={"error": str(exc), "backup_path": str(backup_path)},
            )
        ok = bool(result["ok"])
        summary = "restore drill: counts match manifest" if ok else "restore drill: count mismatch"
        return DutyResult(
            ok=ok,
            summary=summary,
            details=result,
        )
