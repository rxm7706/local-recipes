"""Story 13.3's static-JSON-snapshot exporter
(``scripts/export_progress_snapshot.py``), replacing
``web/scripts/sync-progress.mjs``.

Imported directly via ``importlib`` -- the script lives outside the
``pyforge.herald`` package (it is a build-time tool, not shipped runtime
code), so it is not reachable via a normal package import. Mirrors
``test_export_web_snapshot.py``'s own loader pattern."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "export_progress_snapshot.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("export_progress_snapshot", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


export_progress_snapshot = _load_module()

from pyforge.herald import progress


def test_export_progress_snapshot_writes_every_record(tmp_path):
    repo_root = tmp_path / "repo"
    progress_path = repo_root / progress.DEFAULT_PROGRESS_PATH
    progress.upsert(
        progress_path,
        station="warden",
        date="2026-08-08",
        shipped_capabilities=["hygiene gate"],
        compute_hours=1.5,
        token_spend=1000,
        wall_clock_hours=2.0,
        unblock_narrative="none",
    )

    out_dir = tmp_path / "out"
    out_path = export_progress_snapshot.export_progress_snapshot(repo_root=repo_root, out_dir=out_dir)

    assert out_path == out_dir / "progress.json"
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert len(payload) == 1
    assert payload[0]["station"] == "warden"
    assert payload[0]["shipped_capabilities"] == ["hygiene gate"]


def test_export_progress_snapshot_creates_out_dir(tmp_path):
    repo_root = tmp_path / "repo"
    out_dir = tmp_path / "does" / "not" / "exist" / "yet"
    out_path = export_progress_snapshot.export_progress_snapshot(repo_root=repo_root, out_dir=out_dir)
    assert out_path.exists()
    assert json.loads(out_path.read_text(encoding="utf-8")) == []


def test_main_writes_and_prints(tmp_path, capsys):
    repo_root = tmp_path / "repo"
    progress_path = repo_root / progress.DEFAULT_PROGRESS_PATH
    progress.upsert(
        progress_path,
        station="atlas",
        date="2026-08-08",
        shipped_capabilities=[],
        compute_hours=0,
        token_spend=0,
        wall_clock_hours=0,
        unblock_narrative="",
    )
    out_dir = tmp_path / "out"

    rc = export_progress_snapshot.main(["--repo-root", str(repo_root), "--out-dir", str(out_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert str(out_dir / "progress.json") in out
    assert (out_dir / "progress.json").exists()
