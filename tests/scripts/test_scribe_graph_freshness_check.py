"""Acceptance tests for scripts/scribe_graph_freshness_check.py (Story 8.1).

Matrix:
  MISSING   — no graph.json on disk → advisory finding, exit 1
  FRESH     — graph.json newer than the schedule's own period → clean, exit 0
  STALE     — graph.json older than the schedule's own period → advisory
              finding, exit 1

Harness style matches missing_preserve_check's own meta-tests: importlib-load
the script, monkeypatch its module-level GRAPH_STORE_PATH, seed a real file.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = REPO_ROOT / "scripts" / "scribe_graph_freshness_check.py"


def _load_detector():
    spec = importlib.util.spec_from_file_location(
        "scribe_graph_freshness_check_under_test", DETECTOR_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["scribe_graph_freshness_check_under_test"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_missing_store_is_advisory_finding(tmp_path, monkeypatch, capsys):
    mod = _load_detector()
    graph_path = tmp_path / "graph.json"
    monkeypatch.setattr(mod, "GRAPH_STORE_PATH", graph_path)

    assert mod.main() == 1
    out = capsys.readouterr().out
    assert "SCRIBE-GRAPHFRESH-001" in out
    assert "advisory only, never a PR gate" in out


def test_fresh_store_is_clean(tmp_path, monkeypatch, capsys):
    mod = _load_detector()
    graph_path = tmp_path / "graph.json"
    graph_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(mod, "GRAPH_STORE_PATH", graph_path)

    assert mod.main() == 0
    out = capsys.readouterr().out
    assert "fresh" in out
    assert "SCRIBE-GRAPHFRESH" not in out


def test_stale_store_is_advisory_finding(tmp_path, monkeypatch, capsys):
    mod = _load_detector()
    graph_path = tmp_path / "graph.json"
    graph_path.write_text("{}", encoding="utf-8")
    stale_seconds = (mod.SCHEDULE_PERIOD_HOURS + 2) * 3600
    old_mtime = time.time() - stale_seconds
    import os

    os.utime(graph_path, (old_mtime, old_mtime))
    monkeypatch.setattr(mod, "GRAPH_STORE_PATH", graph_path)

    assert mod.main() == 1
    out = capsys.readouterr().out
    assert "SCRIBE-GRAPHFRESH-002" in out


def test_json_mode_reports_status(tmp_path, monkeypatch, capsys):
    mod = _load_detector()
    graph_path = tmp_path / "graph.json"
    graph_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(mod, "GRAPH_STORE_PATH", graph_path)

    assert mod.main(["--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["_findings"] == []


def test_future_mtime_clamps_age_to_zero_not_negative(tmp_path, monkeypatch, capsys):
    """A future mtime (clock skew, a restored snapshot) must never report a
    nonsensical negative-hour age -- clamp to 0.0 and still count as fresh."""
    mod = _load_detector()
    graph_path = tmp_path / "graph.json"
    graph_path.write_text("{}", encoding="utf-8")
    future_mtime = time.time() + 3600
    import os

    os.utime(graph_path, (future_mtime, future_mtime))
    monkeypatch.setattr(mod, "GRAPH_STORE_PATH", graph_path)

    status, reason, age_hours = mod.check_freshness(graph_path)

    assert status == "ok"
    assert age_hours == 0.0
    assert "-" not in f"{age_hours:.1f}"


def test_check_freshness_pure_function_boundary():
    mod = _load_detector()
    graph_path = REPO_ROOT / "does-not-exist" / "graph.json"
    status, reason, age_hours = mod.check_freshness(graph_path, now=1_000_000.0)
    assert status == "missing"
    assert age_hours is None
    assert str(graph_path) in reason


def test_placement_is_scripts_runtime_not_doctor():
    """Placement decision: scripts/*_check.py + scope=runtime (mirrors
    index_freshness_check.py's own precedent for a gitignored, host-local
    derived artifact a CI runner never populates)."""
    source = DETECTOR_PATH.read_text(encoding="utf-8")
    assert 'DETECTOR = {"scope": "runtime"}' in source
