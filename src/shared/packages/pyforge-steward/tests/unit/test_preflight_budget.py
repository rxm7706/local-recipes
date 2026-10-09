"""Unit tests for preflight journal budget check (Story 71.7, CAP-159)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.steward import preflight, preflight_budget


def _write_journal(path: Path, *records: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(record, sort_keys=True) for record in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_record(
    *,
    run_id: str = "run-1",
    total_seconds: float,
    selected: list[str],
    lanes: list[tuple[str, float]],
    logical_cores: int = 16,
) -> dict:
    return {
        "run_id": run_id,
        "started_at": "2026-10-08T00:00:00+00:00",
        "total_seconds": total_seconds,
        "logical_cores": logical_cores,
        "verdict": "ok",
        "selection": {
            "mode": "diff",
            "selected": [{"lane": lane, "environment": "pyforge-guild", "reason": "test"} for lane in selected],
            "skipped": [],
        },
        "lanes": [
            {"task": task, "environment": "pyforge-guild", "seconds": sec, "exit_code": 0, "status": "ok"}
            for task, sec in lanes
        ],
    }


def test_single_station_under_budget_exits_0(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    journal = tmp_path / preflight.JOURNAL_RELATIVE
    _write_journal(
        journal,
        {"phase": "install", "run_id": "run-1", "seconds": 5.0, "verdict": "ok"},
        _run_record(
            total_seconds=58.0,
            selected=["pyforge-marshal-test", "lint-types"],
            lanes=[("lint-types", 10.0), ("pyforge-marshal-test", 40.0)],
        ),
    )
    assert preflight_budget.main(["--budget"]) == preflight_budget.EXIT_OK


def test_single_station_over_budget_exits_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    journal = tmp_path / preflight.JOURNAL_RELATIVE
    _write_journal(
        journal,
        {"phase": "install", "run_id": "run-1", "seconds": 6.0, "verdict": "ok"},
        _run_record(
            total_seconds=61.0,
            selected=["pyforge-steward-test"],
            lanes=[("pyforge-steward-test", 50.0), ("detectors-ci", 5.0)],
        ),
    )
    result = preflight_budget.evaluate_budget(tmp_path, budget_seconds=60)
    assert result.exit_code == preflight_budget.EXIT_OVER_BUDGET
    text = "\n".join(result.lines)
    assert "run-1" in text
    assert "logical_cores 16" in text
    assert "install" in text
    assert "pyforge-steward-test" in text


def test_shared_surface_long_run_exits_0(tmp_path: Path) -> None:
    journal = tmp_path / preflight.JOURNAL_RELATIVE
    _write_journal(
        journal,
        _run_record(
            total_seconds=300.0,
            selected=["test-ci", "lint-types"],
            lanes=[("test-ci", 280.0), ("lint-types", 15.0)],
        ),
    )
    result = preflight_budget.evaluate_budget(tmp_path, budget_seconds=60)
    assert result.exit_code == preflight_budget.EXIT_OK
    assert "shared-surface" in result.lines[0]
    assert "test-ci" in result.lines[0]


def test_missing_journal_exits_2(tmp_path: Path) -> None:
    result = preflight_budget.evaluate_budget(tmp_path, budget_seconds=60)
    assert result.exit_code == preflight_budget.EXIT_CANNOT_EVALUATE


def test_empty_journal_exits_2(tmp_path: Path) -> None:
    journal = tmp_path / preflight.JOURNAL_RELATIVE
    journal.parent.mkdir(parents=True)
    journal.write_text("", encoding="utf-8")
    result = preflight_budget.evaluate_budget(tmp_path, budget_seconds=60)
    assert result.exit_code == preflight_budget.EXIT_CANNOT_EVALUATE


def test_malformed_line_warns_and_judges_valid_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    journal = tmp_path / preflight.JOURNAL_RELATIVE
    journal.parent.mkdir(parents=True)
    good = json.dumps(
        _run_record(total_seconds=58.0, selected=["pyforge-marshal-test"], lanes=[("pyforge-marshal-test", 50.0)]),
        sort_keys=True,
    )
    journal.write_text("{ not json\n" + good + "\n", encoding="utf-8")
    result = preflight_budget.evaluate_budget(tmp_path, budget_seconds=60)
    assert result.exit_code == preflight_budget.EXIT_OK
    err = capsys.readouterr().err
    assert "line 1" in err


def test_run_flag_selects_older_run(tmp_path: Path) -> None:
    journal = tmp_path / preflight.JOURNAL_RELATIVE
    _write_journal(
        journal,
        _run_record(run_id="old", total_seconds=90.0, selected=["pyforge-marshal-test"], lanes=[("x", 1.0)]),
        _run_record(run_id="new", total_seconds=58.0, selected=["pyforge-marshal-test"], lanes=[("x", 1.0)]),
    )
    result = preflight_budget.evaluate_budget(tmp_path, budget_seconds=60, run_id="old")
    assert result.exit_code == preflight_budget.EXIT_OVER_BUDGET
    assert "old" in result.lines[0]


def test_unknown_run_id_exits_2(tmp_path: Path) -> None:
    journal = tmp_path / preflight.JOURNAL_RELATIVE
    _write_journal(
        journal,
        _run_record(run_id="run-1", total_seconds=58.0, selected=["pyforge-marshal-test"], lanes=[("x", 1.0)]),
    )
    result = preflight_budget.evaluate_budget(tmp_path, run_id="missing")
    assert result.exit_code == preflight_budget.EXIT_CANNOT_EVALUATE


def test_preflight_main_budget_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    journal = tmp_path / preflight.JOURNAL_RELATIVE
    _write_journal(
        journal,
        _run_record(total_seconds=58.0, selected=["pyforge-marshal-test"], lanes=[("pyforge-marshal-test", 50.0)]),
    )
    assert preflight.main(["--budget"]) == preflight_budget.EXIT_OK


def test_pr_preflight_does_not_invoke_budget() -> None:
    source = (Path(__file__).resolve().parents[2] / "src" / "pyforge" / "steward" / "preflight.py").read_text(
        encoding="utf-8"
    )
    assert "preflight_budget" not in source.split("def run_preflight", 1)[0]
    run_body = source.split("def run_preflight", 1)[1].split("def _parse_args", 1)[0]
    assert "preflight_budget" not in run_body
    assert "budget" not in run_body
