"""Read ``pr-preflight`` journal runs and judge CAP-159 wall-clock budget (Story 71.7).

Separate from ``run_preflight`` — never changes its verdict, not a detector or PR gate.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pyforge.steward.preflight import JOURNAL_RELATIVE

DEFAULT_BUDGET_SECONDS = 60
CAP_CITATION = "CAP-159 (FR-32)"

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


def _selection_selected_lanes(selection: dict[str, Any]) -> set[str]:
    selected = selection.get("selected")
    if not isinstance(selected, list):
        return set()
    lanes: set[str] = set()
    for entry in selected:
        if isinstance(entry, dict) and "lane" in entry:
            lanes.add(str(entry["lane"]))
    return lanes


def is_single_station_budget(selection: dict[str, Any]) -> bool:
    """True when selection has at most one station test lane and no ``test-ci``."""
    selected = _selection_selected_lanes(selection)
    if "test-ci" in selected:
        return False
    station_tests = [lane for lane in selected if lane in STATION_TEST_TASKS]
    return len(station_tests) <= 1


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
            task = str(entry.get("task", "unknown"))
            timings.append((task, float(entry.get("seconds", 0.0))))
    return timings


def _slowest_lanes(timings: Sequence[tuple[str, float]], count: int = 3) -> list[tuple[str, float]]:
    ordered = sorted(timings, key=lambda item: (-item[1], item[0]))
    return ordered[:count]


def _format_lane_list(lanes: Sequence[tuple[str, float]]) -> str:
    return ", ".join(f"{name} {seconds:.1f}s" for name, seconds in lanes)


def judge_run(
    run: dict[str, Any],
    *,
    budget_seconds: float,
    install_seconds: Sequence[float],
) -> BudgetJudgement:
    run_id = str(run.get("run_id", "unknown"))
    wall = float(run.get("total_seconds", 0.0))
    cores = run.get("logical_cores")
    selection = run.get("selection")
    if not isinstance(selection, dict):
        selection = {}

    timings = _lane_timings(run, install_seconds)
    slowest = _slowest_lanes(timings, 1)
    slowest_name = slowest[0][0] if slowest else "unknown"
    slowest_sec = slowest[0][1] if slowest else 0.0

    single = is_single_station_budget(selection)

    if single:
        if wall <= budget_seconds:
            msg = (
                f"preflight-budget: run {run_id} wall {wall:.1f}s "
                f"(budget {budget_seconds:g}s {CAP_CITATION}); slowest lane {slowest_name} {slowest_sec:.1f}s"
            )
            return BudgetJudgement(EXIT_OK, (msg,))
        top3 = _slowest_lanes(timings, 3)
        core_text = str(cores) if cores is not None else "unknown"
        msg = (
            f"preflight-budget: run {run_id} over budget: wall {wall:.1f}s > {budget_seconds:g}s "
            f"({CAP_CITATION}); logical_cores {core_text}; slowest lanes: {_format_lane_list(top3)}"
        )
        return BudgetJudgement(EXIT_OVER_BUDGET, (msg,))

    msg = (
        f"preflight-budget: run {run_id} shared-surface (not a single-station budget); "
        f"wall {wall:.1f}s bounded by slowest lane {slowest_name} {slowest_sec:.1f}s"
    )
    return BudgetJudgement(EXIT_OK, (msg,))


def evaluate_budget(
    repo_root: Path,
    *,
    budget_seconds: float = DEFAULT_BUDGET_SECONDS,
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
    return judge_run(run, budget_seconds=budget_seconds, install_seconds=installs)


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="pyforge.steward.preflight --budget")
    parser.add_argument(
        "--budget",
        action="store_true",
        help=f"judge journaled wall time against {DEFAULT_BUDGET_SECONDS}s ({CAP_CITATION})",
    )
    parser.add_argument(
        "--seconds",
        type=float,
        default=DEFAULT_BUDGET_SECONDS,
        help=f"budget in seconds (default: {DEFAULT_BUDGET_SECONDS:g}, {CAP_CITATION})",
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
    result = evaluate_budget(
        _repo_root(),
        budget_seconds=args.seconds,
        run_id=args.run_id,
    )
    for line in result.lines:
        print(line)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
