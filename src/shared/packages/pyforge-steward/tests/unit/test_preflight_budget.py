"""Unit tests for preflight journal budget check (Stories 71.7, 117.5)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.steward import preflight, preflight_budget


def _write_journal(path: Path, *records: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(record, sort_keys=True) for record in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_budgets(repo: Path, *, single: float = 90, full: float = 240, lanes: dict[str, float] | None = None) -> None:
    dest = repo / "docs/governance/preflight-budgets.toml"
    dest.parent.mkdir(parents=True, exist_ok=True)
    body = f"[defaults]\nsingle_station = {single:g}\nfull = {full:g}\n\n[lanes]\n"
    for key, value in (lanes or {}).items():
        body += f'"{key}" = {value:g}\n'
    dest.write_text(body, encoding="utf-8")


def _run_record(
    *,
    run_id: str = "run-1",
    total_seconds: float,
    selected: list[str],
    lanes: list[tuple[str, float]],
    logical_cores: int = 16,
    environment: str = "pyforge-guild",
) -> dict:
    return {
        "run_id": run_id,
        "started_at": "2026-10-08T00:00:00+00:00",
        "total_seconds": total_seconds,
        "logical_cores": logical_cores,
        "verdict": "ok",
        "selection": {
            "mode": "diff",
            "selected": [{"lane": lane, "environment": environment, "reason": "test"} for lane in selected],
            "skipped": [],
        },
        "lanes": [
            {"task": task, "environment": environment, "seconds": sec, "exit_code": 0, "status": "ok"}
            for task, sec in lanes
        ],
    }


def _median_history(
    task: str,
    seconds: float,
    *,
    runs: int = 5,
    environment: str = "pyforge-guild",
) -> list[dict]:
    return [
        _run_record(
            run_id=f"hist-{i}",
            total_seconds=seconds + 5,
            selected=[task],
            lanes=[(task, seconds)],
            environment=environment,
        )
        for i in range(runs)
    ]


def test_single_station_under_budget_exits_0(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIXI_PROJECT_ROOT", str(tmp_path))
    _write_budgets(tmp_path, lanes={"pyforge-marshal-test@pyforge-guild": 500})
    journal = tmp_path / preflight.JOURNAL_RELATIVE
    _write_journal(
        journal,
        *_median_history("pyforge-marshal-test", 40.0),
        _run_record(
            total_seconds=58.0,
            selected=["pyforge-marshal-test", "lint-types"],
            lanes=[("lint-types", 10.0), ("pyforge-marshal-test", 40.0)],
        ),
    )
    assert preflight_budget.main(["--budget"]) == preflight_budget.EXIT_OK


def test_lane_at_twice_budget_is_named_and_exits_0(tmp_path: Path) -> None:
    _write_budgets(tmp_path, lanes={"pyforge-steward-test@pyforge-guild": 50})
    journal = tmp_path / preflight.JOURNAL_RELATIVE
    _write_journal(
        journal,
        *_median_history("pyforge-steward-test", 100.0),
        _run_record(
            total_seconds=120.0,
            selected=["pyforge-steward-test"],
            lanes=[("pyforge-steward-test", 100.0)],
        ),
    )
    result = preflight_budget.evaluate_budget(tmp_path)
    assert result.exit_code == preflight_budget.EXIT_OK
    text = "\n".join(result.lines)
    assert "pyforge-steward-test@pyforge-guild" in text
    assert "median 100.0s" in text
    assert "budget 50s" in text
    assert "delta" in text


def test_all_lanes_under_budget_prints_totals_only(tmp_path: Path) -> None:
    _write_budgets(tmp_path, lanes={"pyforge-marshal-test@pyforge-guild": 500})
    journal = tmp_path / preflight.JOURNAL_RELATIVE
    _write_journal(
        journal,
        *_median_history("pyforge-marshal-test", 40.0),
        _run_record(
            total_seconds=58.0,
            selected=["pyforge-marshal-test"],
            lanes=[("pyforge-marshal-test", 40.0)],
        ),
    )
    result = preflight_budget.evaluate_budget(tmp_path)
    assert result.exit_code == preflight_budget.EXIT_OK
    assert len(result.lines) == 1
    assert "within budget" in result.lines[0]
    assert "over budget" not in result.lines[0]


def test_unknown_lane_uses_mode_default(tmp_path: Path) -> None:
    _write_budgets(tmp_path, single=40, full=240, lanes={})
    journal = tmp_path / preflight.JOURNAL_RELATIVE
    _write_journal(
        journal,
        *_median_history("pyforge-marshal-test", 100.0),
        _run_record(
            total_seconds=110.0,
            selected=["pyforge-marshal-test"],
            lanes=[("pyforge-marshal-test", 100.0)],
        ),
    )
    result = preflight_budget.evaluate_budget(tmp_path)
    text = "\n".join(result.lines)
    assert "budget 40s" in text


def test_shared_surface_long_run_exits_0(tmp_path: Path) -> None:
    _write_budgets(tmp_path, full=500, lanes={"test-ci@pyforge-guild": 900})
    journal = tmp_path / preflight.JOURNAL_RELATIVE
    _write_journal(
        journal,
        *_median_history("test-ci", 280.0),
        _run_record(
            total_seconds=300.0,
            selected=["test-ci", "lint-types"],
            lanes=[("test-ci", 280.0), ("lint-types", 15.0)],
        ),
    )
    result = preflight_budget.evaluate_budget(tmp_path)
    assert result.exit_code == preflight_budget.EXIT_OK
    assert "within budget" in result.lines[0]


def test_missing_journal_exits_2(tmp_path: Path) -> None:
    _write_budgets(tmp_path)
    result = preflight_budget.evaluate_budget(tmp_path)
    assert result.exit_code == preflight_budget.EXIT_CANNOT_EVALUATE


def test_empty_journal_exits_2(tmp_path: Path) -> None:
    _write_budgets(tmp_path)
    journal = tmp_path / preflight.JOURNAL_RELATIVE
    journal.parent.mkdir(parents=True)
    journal.write_text("", encoding="utf-8")
    result = preflight_budget.evaluate_budget(tmp_path)
    assert result.exit_code == preflight_budget.EXIT_CANNOT_EVALUATE


def test_malformed_line_warns_and_judges_valid_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_budgets(tmp_path, lanes={"pyforge-marshal-test@pyforge-guild": 500})
    journal = tmp_path / preflight.JOURNAL_RELATIVE
    journal.parent.mkdir(parents=True)
    good = json.dumps(
        _run_record(total_seconds=58.0, selected=["pyforge-marshal-test"], lanes=[("pyforge-marshal-test", 50.0)]),
        sort_keys=True,
    )
    journal.write_text("{ not json\n" + good + "\n", encoding="utf-8")
    result = preflight_budget.evaluate_budget(tmp_path)
    assert result.exit_code == preflight_budget.EXIT_OK
    err = capsys.readouterr().err
    assert "line 1" in err


def test_run_flag_selects_older_run(tmp_path: Path) -> None:
    _write_budgets(tmp_path, lanes={"pyforge-marshal-test@pyforge-guild": 30})
    journal = tmp_path / preflight.JOURNAL_RELATIVE
    _write_journal(
        journal,
        *_median_history("pyforge-marshal-test", 90.0, runs=5),
        _run_record(run_id="old", total_seconds=90.0, selected=["pyforge-marshal-test"], lanes=[("x", 1.0)]),
        _run_record(run_id="new", total_seconds=58.0, selected=["pyforge-marshal-test"], lanes=[("x", 1.0)]),
    )
    result = preflight_budget.evaluate_budget(tmp_path, run_id="old")
    assert result.exit_code == preflight_budget.EXIT_OK
    assert "old" in result.lines[0]


def test_unknown_run_id_exits_2(tmp_path: Path) -> None:
    _write_budgets(tmp_path)
    journal = tmp_path / preflight.JOURNAL_RELATIVE
    _write_journal(
        journal,
        _run_record(run_id="run-1", total_seconds=58.0, selected=["pyforge-marshal-test"], lanes=[("x", 1.0)]),
    )
    result = preflight_budget.evaluate_budget(tmp_path, run_id="missing")
    assert result.exit_code == preflight_budget.EXIT_CANNOT_EVALUATE


def test_preflight_main_budget_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIXI_PROJECT_ROOT", str(tmp_path))
    _write_budgets(tmp_path, lanes={"pyforge-marshal-test@pyforge-guild": 500})
    journal = tmp_path / preflight.JOURNAL_RELATIVE
    _write_journal(
        journal,
        *_median_history("pyforge-marshal-test", 40.0),
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


def test_load_budget_config_missing_lane_uses_defaults(tmp_path: Path) -> None:
    _write_budgets(tmp_path, single=90, full=240, lanes={"lint-types@pyforge-guild": 100})
    config = preflight_budget.load_budget_config(tmp_path)
    assert config.single_station_default == 90
    assert config.full_default == 240
    assert config.lanes["lint-types@pyforge-guild"] == 100
    assert preflight_budget._budget_seconds_for_label(config, "missing@pyforge-guild", single_station=True) == 90
    assert preflight_budget._budget_seconds_for_label(config, "missing@pyforge-guild", single_station=False) == 240
