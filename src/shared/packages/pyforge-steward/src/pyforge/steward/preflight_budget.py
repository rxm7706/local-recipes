"""Read ``pr-preflight`` journal runs and report per-lane budget drift (Stories 71.7, 117.5).

Separate from ``run_preflight`` — never changes its verdict, not a detector or PR gate.
Story 117.5 (CAP-175): budgets live in ``docs/governance/preflight-budgets.toml``; each
lane's median over the last five green runs is compared to 1.5× its budget. Warn only (D3).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pyforge.steward.preflight import JOURNAL_RELATIVE, lane_label, lane_medians

CAP_CITATION = "CAP-175 (FR-49)"
LEGACY_CAP_CITATION = "CAP-159 (FR-32)"
OVER_BUDGET_RATIO = 1.5
BUDGETS_RELATIVE = Path("docs/governance/preflight-budgets.toml")

STATION_TOKENS: tuple[str, ...] = (
    "atlas",
    "doctor",
    "herald",
    "marshal",
    "mason",
    "scribe",
    "steward",
    "warden",
)
STATION_TEST_TASKS: frozenset[str] = frozenset(f"pyforge-{s}-test" for s in STATION_TOKENS)

EXIT_OK = 0
EXIT_OVER_BUDGET = 1
EXIT_CANNOT_EVALUATE = 2

_INSTALL_LANE = "install"


@dataclass(frozen=True)
class BudgetConfig:
    single_station_default: float
    full_default: float
    lanes: Mapping[str, float]


@dataclass(frozen=True)
class ParsedJournal:
    runs: tuple[dict[str, Any], ...]
    install_by_run: dict[str, list[float]]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class BudgetJudgement:
    exit_code: int
    lines: tuple[str, ...]


def _repo_root() -> Path:
    return Path(os.environ.get("PIXI_PROJECT_ROOT", ".")).resolve()


def budgets_toml_path(repo_root: Path) -> Path:
    return repo_root / BUDGETS_RELATIVE


def load_budget_config(repo_root: Path) -> BudgetConfig:
    path = budgets_toml_path(repo_root)
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    defaults = data.get("defaults") or {}
    single = float(defaults.get("single_station", 90))
    full = float(defaults.get("full", 240))
    raw_lanes = data.get("lanes") or {}
    lanes = {str(key): float(value) for key, value in raw_lanes.items()}
    return BudgetConfig(single_station_default=single, full_default=full, lanes=lanes)


def _read_journal(path: Path) -> ParsedJournal:
    if not path.is_file():
        return ParsedJournal(runs=(), install_by_run={}, warnings=())
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return ParsedJournal(runs=(), install_by_run={}, warnings=())

    runs: list[dict[str, Any]] = []
    install_by_run: dict[str, list[float]] = {}
    warnings: list[str] = []

    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError:
            warnings.append(f"preflight-budget: warning: skipping malformed JSON at line {line_no}")
            continue
        if not isinstance(record, dict):
            warnings.append(f"preflight-budget: warning: skipping malformed JSON at line {line_no}")
            continue
        if record.get("phase") == "install" and "run_id" in record:
            rid = str(record["run_id"])
            install_by_run.setdefault(rid, []).append(float(record.get("seconds", 0.0)))
        if "lanes" in record and "run_id" in record:
            runs.append(record)

    return ParsedJournal(runs=tuple(runs), install_by_run=install_by_run, warnings=tuple(warnings))


def _newest_run(runs: Sequence[dict[str, Any]]) -> dict[str, Any] | None:
    return runs[-1] if runs else None


def _run_by_id(runs: Sequence[dict[str, Any]], run_id: str) -> dict[str, Any] | None:
    for record in reversed(runs):
        if str(record.get("run_id")) == run_id:
            return record
    return None


def _selection_selected_lanes(selection: dict[str, Any]) -> set[tuple[str, str]]:
    """The selected lanes as ``(task, environment)`` pairs: one task may run in two environments."""
    selected = selection.get("selected")
    if not isinstance(selected, list):
        return set()
    lanes: set[tuple[str, str]] = set()
    for entry in selected:
        if isinstance(entry, dict) and "lane" in entry:
            lanes.add((str(entry["lane"]), str(entry.get("environment", ""))))
    return lanes


def is_single_station_budget(selection: dict[str, Any]) -> bool:
    """True when selection has at most one station test lane and no ``test-ci``."""
    selected = _selection_selected_lanes(selection)
    if any(task == "test-ci" for task, _environment in selected):
        return False
    station_tests = [(task, env) for task, env in selected if task in STATION_TEST_TASKS]
    return len(station_tests) <= 1


def _timing_label(entry: dict[str, Any]) -> str:
    """``<task>@<environment>``, the lane's scratch name; the task alone for an entry with no environment."""
    task = str(entry.get("task", "unknown"))
    environment = entry.get("environment")
    return lane_label(task, str(environment)) if environment else task


def _lane_timings(run: dict[str, Any], install_seconds: Sequence[float]) -> list[tuple[str, float]]:
    timings: list[tuple[str, float]] = []
    if install_seconds:
        timings.append((_INSTALL_LANE, float(sum(install_seconds))))
    lanes = run.get("lanes")
    if isinstance(lanes, list):
        for entry in lanes:
            if not isinstance(entry, dict):
                continue
            status = entry.get("status", "")
            if status in ("cancelled", "not-run"):
                continue
            timings.append((_timing_label(entry), float(entry.get("seconds", 0.0))))
    return timings


def _slowest_lanes(timings: Sequence[tuple[str, float]], count: int = 3) -> list[tuple[str, float]]:
    ordered = sorted(timings, key=lambda item: (-item[1], item[0]))
    return ordered[:count]


def _format_lane_list(lanes: Sequence[tuple[str, float]]) -> str:
    return ", ".join(f"{name} {seconds:.1f}s" for name, seconds in lanes)


def _budget_seconds_for_label(config: BudgetConfig, label: str, *, single_station: bool) -> float:
    if label in config.lanes:
        return config.lanes[label]
    return config.single_station_default if single_station else config.full_default


def _run_lane_keys(run: dict[str, Any]) -> list[tuple[str, str, str]]:
    """``(task, environment, label)`` for each ok lane in the run."""
    keys: list[tuple[str, str, str]] = []
    lanes = run.get("lanes")
    if not isinstance(lanes, list):
        return keys
    for entry in lanes:
        if not isinstance(entry, dict):
            continue
        if entry.get("status") not in ("ok",):
            continue
        task = str(entry.get("task", "unknown"))
        environment = str(entry.get("environment"))  # match lane_medians keying
        label = _timing_label(entry)
        keys.append((task, environment, label))
    return keys


def judge_run(
    run: dict[str, Any],
    *,
    budget_seconds: float,
    install_seconds: Sequence[float],
    medians: Mapping[tuple[str, str], float] | None = None,
    config: BudgetConfig | None = None,
) -> BudgetJudgement:
    """Per-lane budget report for one journaled run (Story 117.5).

    ``budget_seconds`` is kept for Story 71.7 call sites; per-lane budgets come from
    ``config`` when supplied. Exit code is always :data:`EXIT_OK` when the run is judged
    (operator ruling D3).
    """
    run_id = str(run.get("run_id", "unknown"))
    wall = float(run.get("total_seconds", 0.0))
    selection = run.get("selection")
    if not isinstance(selection, dict):
        selection = {}

    single = is_single_station_budget(selection)
    if config is None:
        config = BudgetConfig(
            single_station_default=budget_seconds,
            full_default=budget_seconds,
            lanes={},
        )

    medians = medians or {}
    over_rows: list[str] = []
    checked = 0
    for task, environment, label in _run_lane_keys(run):
        if label == _INSTALL_LANE:
            continue
        checked += 1
        median = medians.get((task, environment))
        if median is None:
            continue
        budget = _budget_seconds_for_label(config, label, single_station=single)
        threshold = OVER_BUDGET_RATIO * budget
        if median > threshold:
            delta = median - threshold
            over_rows.append(
                f"preflight-budget: lane {label} over budget: median {median:.1f}s > "
                f"{OVER_BUDGET_RATIO:g}× budget {budget:g}s ({CAP_CITATION}); delta +{delta:.1f}s"
            )

    if over_rows:
        header = (
            f"preflight-budget: run {run_id} wall {wall:.1f}s; "
            f"{len(over_rows)} lane(s) over {OVER_BUDGET_RATIO:g}× budget ({CAP_CITATION})"
        )
        return BudgetJudgement(EXIT_OK, (header, *over_rows))

    timings = _lane_timings(run, install_seconds)
    slowest = _slowest_lanes(timings, 1)
    slowest_name = slowest[0][0] if slowest else "unknown"
    slowest_sec = slowest[0][1] if slowest else 0.0
    msg = (
        f"preflight-budget: run {run_id} wall {wall:.1f}s; "
        f"{checked} lane(s) within budget ({CAP_CITATION}); "
        f"slowest lane {slowest_name} {slowest_sec:.1f}s"
    )
    return BudgetJudgement(EXIT_OK, (msg,))


def evaluate_budget(
    repo_root: Path,
    *,
    budget_seconds: float = 90,
    run_id: str | None = None,
    journal_path: Path | None = None,
) -> BudgetJudgement:
    path = journal_path or (repo_root / JOURNAL_RELATIVE)
    parsed = _read_journal(path)

    for warning in parsed.warnings:
        print(warning, file=sys.stderr)

    if run_id is not None:
        run = _run_by_id(parsed.runs, run_id)
        if run is None:
            return BudgetJudgement(
                EXIT_CANNOT_EVALUATE,
                (f"preflight-budget: cannot evaluate: run id {run_id!r} not in journal",),
            )
    else:
        run = _newest_run(parsed.runs)

    if run is None:
        return BudgetJudgement(
            EXIT_CANNOT_EVALUATE,
            ("preflight-budget: cannot evaluate: no valid run in journal",),
        )

    rid = str(run["run_id"])
    installs = parsed.install_by_run.get(rid, [])
    config = load_budget_config(repo_root)
    medians = lane_medians(path)
    return judge_run(
        run,
        budget_seconds=budget_seconds,
        install_seconds=installs,
        medians=medians,
        config=config,
    )


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="pyforge.steward.preflight --budget")
    parser.add_argument(
        "--budget",
        action="store_true",
        help=f"report lanes over {OVER_BUDGET_RATIO:g}× their journal-derived budget ({CAP_CITATION})",
    )
    parser.add_argument(
        "--seconds",
        type=float,
        default=None,
        help=(
            f"legacy single-station default when the budgets file is missing a lane "
            f"({LEGACY_CAP_CITATION}; ignored when [defaults] is present)"
        ),
    )
    parser.add_argument(
        "--run",
        dest="run_id",
        default=None,
        help="judge this run id instead of the newest journaled run",
    )
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv or [])
    if not args.budget:
        print("preflight-budget: pass --budget to judge the journal", file=sys.stderr)
        return EXIT_CANNOT_EVALUATE
    repo = _repo_root()
    config = load_budget_config(repo)
    fallback = args.seconds if args.seconds is not None else config.single_station_default
    result = evaluate_budget(
        repo,
        budget_seconds=fallback,
        run_id=args.run_id,
    )
    for line in result.lines:
        print(line)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
