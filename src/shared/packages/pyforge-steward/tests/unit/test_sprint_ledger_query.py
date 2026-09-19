"""Unit tests for Sprint Ledger Query Module (`pyforge-steward`)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from pyforge.steward.sprint_ledger_query import (
    FormatterRegistry,
    HookRegistry,
    JSONFormatter,
    LedgerQueryDuty,
    LedgerQueryHook,
    MarkdownFormatter,
    SprintLedgerQueryEngine,
    SummaryFormatter,
    SyncMatrixFormatter,
    TableFormatter,
    eval_flag,
    get_runnable_backlog,
    sync_to_postgres,
)


def test_eval_flag_hierarchical_resolution(tmp_path: Path) -> None:
    # 1. Override
    assert eval_flag("test-flag", False, flag_overrides={"test-flag": True}) is True

    # 2. Env var
    import os
    os.environ["FLAGS_MY_FEATURE"] = "true"
    assert eval_flag("my-feature", False) is True
    del os.environ["FLAGS_MY_FEATURE"]

    # 3. File
    flags_file = tmp_path / "flags.json"
    flags_file.write_text(json.dumps({"file-flag": {"state": "ENABLED"}}), encoding="utf-8")
    assert eval_flag("file-flag", False, flags_file_path=flags_file) is True

    # 4. Default
    assert eval_flag("nonexistent-flag", "default_val") == "default_val"


def test_engine_query_and_formatters(tmp_path: Path) -> None:
    # Setup mock station planning-artifacts
    st_dir = tmp_path / "_bmad-output" / "projects" / "test-station" / "planning-artifacts"
    st_dir.mkdir(parents=True)

    ledger_yaml = st_dir / "sprint-status-ledger.yaml"
    ledger_yaml.write_text("development_status:\n  1-1-story-one: done\n  1-2-story-two: backlog\n", encoding="utf-8")

    epics_md = st_dir / "epics.md"
    epics_md.write_text("""## Epic 1: Test Epic

### Story 1.1: Story One
**FR/AD:** FR-1 • **Effort:** S • **Deps:** —
**Status:** done

### Story 1.2: Story Two
**FR/AD:** FR-2 • **Effort:** M • **Deps:** 1.1
**Status:** backlog
""", encoding="utf-8")

    engine = SprintLedgerQueryEngine(root_dir=tmp_path)
    res = engine.query(station="test-station")

    assert res.summary.total_stories == 2
    assert res.summary.total_done == 1
    assert res.summary.total_backlog == 1
    assert len(res.stories) == 2

    # Test formatters
    md = engine.export(res, "markdown")
    assert "Estate Sprint Ledger Query Report" in md
    assert "Story One" in md

    summary = engine.export(res, "summary")
    assert "Estate Sprint Ledger Summary: 2 stories" in summary

    json_str = engine.export(res, "json")
    json_data = json.loads(json_str)
    assert json_data["matching_stories_count"] == 2

    tbl = engine.export(res, "table")
    assert "STORY ONE" in tbl or "Story One" in tbl or "1.1" in tbl

    matrix = engine.export(res, "sync-matrix")
    assert "3-Way Alignment Sync Matrix" in matrix

    # Test runnable backlog
    runnable = get_runnable_backlog(engine, station="test-station")
    assert len(runnable) == 1
    assert runnable[0].story_id == "1.2"


def test_ledger_query_duty(tmp_path: Path) -> None:
    class DummyNS:
        duty = "ledger-query"
        unimplemented = False
        unlinked = False
        station = None
        status = None
        search = None
        format = "summary"
        output = None
        sync_postgres = False

    duty = LedgerQueryDuty()
    result = duty.run(DummyNS())
    assert result.ok is True
    assert "Estate Sprint Ledger Summary" in result.summary


def test_hook_registry() -> None:
    events = []

    class TestHook(LedgerQueryHook):
        def pre_query(self, filters: dict) -> None:
            events.append("pre_query")

        def post_query(self, result: any) -> None:
            events.append("post_query")

        def on_export(self, format_name: str, output: str) -> None:
            events.append(f"export_{format_name}")

    engine = SprintLedgerQueryEngine()
    engine.hooks.register(TestHook())
    res = engine.query()
    engine.export(res, "summary")

    assert events == ["pre_query", "post_query", "export_summary"]
