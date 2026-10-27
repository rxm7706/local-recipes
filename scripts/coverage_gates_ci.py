#!/usr/bin/env python3
"""CI driver for Story 19.3 / FR-131 named-module coverage gates.

For each touched ``pyforge-<station>`` package:

1. Run the station's unit (and, when present, integration) tests under
   ``pytest --cov`` producing a coverage.py JSON report.
2. Evaluate the report with ``coverage_gate`` (a scripts/ sibling, outside
   every pyforge.<station> package -- spec-coverage-gate-independence CAP-1),
   gating only the *touched source modules* so the failure names those
   modules.
3. Exit non-zero when any suite fails.

Full package-wide evaluate (every module) remains available via the pixi
``pyforge-*-test-coverage`` tasks — this driver is the PR path filter.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# coverage_gate.py is a scripts/ sibling (spec-coverage-gate-independence
# CAP-1, doctor Story 24.1: the evaluator moved out of pyforge.marshal so no
# station governs its own CI gate). Insert this file's own directory
# explicitly so the import resolves whether this driver is executed directly
# (`python scripts/coverage_gates_ci.py`, which Python already prepends) or
# loaded via importlib (test harnesses, which do not).
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from coverage_gate import (
    STATIONS,
    evaluate_coverage_payload,
    format_only_paths,
    package_root,
    package_src,
    thresholds_for,
    touched_source_modules,
    touched_stations,
)


def _normalize_base(base: str) -> str:
    """``refs/remotes/origin/<name>`` for a bare branch name (GITHUB_BASE_REF is
    the name only) and for ``origin/<name>`` (what the pixi tasks pass); a sha,
    a full ref and any revision expression are returned as-is. The push-event
    workflow passes ``git rev-parse HEAD~1``; prefixing that made every
    push-to-main run die with "unknown revision 'origin/<sha>'"
    (2026-08-24 -> 2026-09-04).

    Full refname, never the short ``origin/<name>`` (spec-coverage-gate-
    independence CAP-4, doctor Story 32.1): git resolves a short name to a
    local branch or tag of that name before ``refs/remotes/<name>``, so a
    stray local ``origin/main`` at HEAD made the diff empty and the gate pass
    having judged nothing. An ``origin/<name>`` revision expression
    (``origin/main~1``) is qualified the same way: its prefix is the part a
    shadow wears."""
    if not base or base.startswith("refs/"):
        return base
    if base.startswith("origin/"):
        return f"refs/remotes/{base}"
    if base.startswith("@") or "@{" in base or any(ch in base for ch in "~^:"):
        return base
    if re.fullmatch(r"[0-9a-f]{7,40}", base):
        return base
    if "/" in base:
        return base  # another remote's branch or a local branch with a slash: not ours to guess
    return f"refs/remotes/origin/{base}"


def _git_diff_names(base: str, head: str) -> list[str]:
    proc = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        # Shallow / missing base — fall back to listing files vs merge-base tip.
        proc = subprocess.run(
            ["git", "diff", "--name-only", base, head],
            cwd=REPO,
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            print(proc.stderr or proc.stdout or "git diff failed", flush=True)
            raise SystemExit(1)
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _git_show(rev: str, path: str) -> str | None:
    proc = subprocess.run(
        ["git", "show", f"{rev}:{path}"],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    return proc.stdout if proc.returncode == 0 else None


def _drop_format_only(
    paths: list[str], base: str, head: str, *, quiet: bool = False
) -> list[str]:
    """Remove station source files whose AST did not change between ``base``
    and ``head`` (steward Story 66.1, 2026-09-20): a formatting-only edit is
    not a touched module, so the floor measures code changes, not the
    formatter. Diffs against the merge-base, the same three-dot semantics as
    ``_git_diff_names``. Added / deleted / unparseable files stay touched.
    """
    proc = subprocess.run(
        ["git", "merge-base", base, head],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    merge_base = (
        proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else base
    )
    candidates = [
        p for p in paths if p.endswith(".py") and "/src/shared/packages/" in f"/{p}"
    ]
    pairs = {p: (_git_show(merge_base, p), _git_show(head, p)) for p in candidates}
    skipped = format_only_paths(pairs)
    if skipped and not quiet:
        print(
            f"format-only (AST unchanged), not counted as touched: {len(skipped)} file(s)",
            flush=True,
        )
    return [p for p in paths if p not in skipped]


def _suite_test_paths(root: Path, suite: str) -> list[Path]:
    """Map a gate suite to the test directories that feed it.

    ``unit`` covers unit + meta — the fast non-integration surface.
    ``integration`` is tests/integration only.

    Story 32.5 (spec-fleet-consistency-standard CAP-2) collapsed eight suite
    names to three, so this needs no per-station special case. It previously
    named ``contract`` (marshal-only, a one-file placeholder) and recognised
    neither spelling of ``conformance`` — the reason steward's 32 CLI-contract
    tests and warden's 19 oracle gates were measured by nothing.
    """
    if suite == "unit":
        names = ("unit", "meta")
    elif suite == "integration":
        names = ("integration",)
    else:
        names = (suite,)
    return [root / "tests" / name for name in names if (root / "tests" / name).is_dir()]


def _run_pytest_cov(
    *,
    station: str,
    suite: str,
    report: Path,
) -> tuple[str, int]:
    """Run pytest with coverage for one suite; write coverage JSON to ``report``.

    Returns ``(status, pytest_rc)`` where ``status`` is ``\"skipped\"`` (no
    matching tests — do **not** evaluate) or ``\"ran\"`` (pytest was invoked).
    """
    root = package_root(REPO, station)
    src = package_src(REPO, station)
    test_paths = _suite_test_paths(root, suite)
    if not test_paths:
        print(f"skip {station} {suite}: no matching tests/ directories", flush=True)
        return "skipped", 0
    if not src.is_dir():
        print(f"skip {station} {suite}: missing package src at {src}", flush=True)
        return "skipped", 0

    cov_mod = f"pyforge.{station}"
    task_argv, alone_runs = _station_test_task_argv(station)
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        *[str(p) for p in test_paths],
        "-q",
        "-m",
        GATE_MARKER_EXPR,
        f"--cov={cov_mod}",
        "--cov-branch",
        f"--cov-report=json:{report}",
        "--cov-report=term-missing:skip-covered",
        *task_argv,
    ]
    print("+", " ".join(cmd), flush=True)
    env = os.environ.copy()
    station_src = root / "src"
    env["PYTHONPATH"] = os.pathsep.join(
        [str(station_src), str(_SCRIPTS_DIR), env.get("PYTHONPATH", "")]
    )
    rc = subprocess.run(cmd, cwd=REPO, env=env, check=False).returncode
    # The tests the station task sets aside run alone after the coverage run, as
    # they do there: doctor's 5 s speed budget fails under xdist workers and --cov.
    for argv in alone_runs:
        if rc != 0 or not _under_any(argv, test_paths):
            continue
        alone = [sys.executable, "-m", "pytest", *argv, "-m", GATE_MARKER_EXPR]
        print("+", " ".join(alone), flush=True)
        rc = subprocess.run(alone, cwd=REPO, env=env, check=False).returncode
    return "ran", rc


def _existing_touched_modules(modules: list[str], station: str) -> list[str]:
    """Drop deleted/renamed-away modules so they are not zero-filled as failures."""
    src_root = package_src(REPO, station)
    kept: list[str] = []
    prefix = f"pyforge.{station}."
    root_name = f"pyforge.{station}"
    for name in modules:
        if name != root_name and not name.startswith(prefix):
            continue
        if name == root_name:
            init = src_root / "__init__.py"
            if init.is_file():
                kept.append(name)
            continue
        # dotted pyforge.<station>.… → …/src/pyforge/<station>/….py
        rel = name.replace(".", "/")
        py_file = (
            REPO
            / "src"
            / "shared"
            / "packages"
            / f"pyforge-{station}"
            / "src"
            / f"{rel}.py"
        )
        pkg_init = (
            REPO
            / "src"
            / "shared"
            / "packages"
            / f"pyforge-{station}"
            / "src"
            / rel
            / "__init__.py"
        )
        if py_file.is_file() or pkg_init.is_file():
            kept.append(name)
        else:
            print(
                f"coverage gate: ignoring deleted/missing module {name}",
                flush=True,
            )
    return kept


def _evaluate(
    *,
    station: str,
    suite: str,
    report: Path,
    modules: list[str],
) -> int:
    try:
        payload = json.loads(report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(
            f"coverage gate: unreadable coverage JSON for pyforge-{station} "
            f"{suite}: {exc}",
            flush=True,
        )
        return 1
    station_modules = _existing_touched_modules(modules, station)
    if not station_modules:
        print(
            f"coverage gate: no touched source modules for pyforge-{station} "
            f"{suite}; skipping evaluate",
            flush=True,
        )
        return 0
    ok, message = evaluate_coverage_payload(
        payload,
        station=station,
        suite=suite,  # type: ignore[arg-type]
        only_modules=station_modules,
    )
    print(message, flush=True)
    return 0 if ok else 1


GATE_MARKER_EXPR = "not slow"


def _pixi_task_cmd(task_name: str) -> str | None:
    pixi_path = REPO / "pixi.toml"
    if not pixi_path.is_file():
        return None
    data = tomllib.loads(pixi_path.read_text(encoding="utf-8"))
    for feature in data.get("feature", {}).values():
        if not isinstance(feature, dict):
            continue
        tasks = feature.get("tasks")
        if not isinstance(tasks, dict):
            continue
        task = tasks.get(task_name)
        if isinstance(task, dict):
            cmd = task.get("cmd")
            if isinstance(cmd, str):
                return cmd
    return None


_TASK_FLAGS = ("-n", "--dist", "--ignore")


def _pytest_runs_from_task_cmd(cmd: str) -> list[list[str]]:
    """The argv after ``pytest`` in each ``&&`` segment of a station test task cmd."""
    runs: list[list[str]] = []
    for segment in cmd.split("&&"):
        parts = shlex.split(segment)
        if "pytest" in parts:
            runs.append(parts[parts.index("pytest") + 1 :])
    return runs


def _pytest_first_run_flags(cmd: str) -> list[str]:
    """Mirror Story 71.6: ``-n`` / ``--dist`` / ``--ignore`` of the task's first pytest run
    (``--flag=value`` is split into two tokens)."""
    runs = _pytest_runs_from_task_cmd(cmd)
    rest = runs[0] if runs else []
    out: list[str] = []
    i = 0
    while i < len(rest):
        name, eq, value = rest[i].partition("=")
        if eq and name in _TASK_FLAGS:
            out.extend([name, value])
        elif rest[i] in _TASK_FLAGS and i + 1 < len(rest):
            out.extend([rest[i], rest[i + 1]])
            i += 1
        i += 1
    return out


def _pytest_alone_runs_from_task_cmd(cmd: str) -> list[list[str]]:
    """The task's later pytest runs whose every path its first run ``--ignore``s: the
    tests it sets aside to run alone (doctor's speed budget). Other later runs (mason's
    CFE parity test, atlas's packaging tests) test no station module and stay out."""
    flags = _pytest_first_run_flags(cmd)
    ignored = {flags[i + 1] for i in range(0, len(flags), 2) if flags[i] == "--ignore"}
    alone: list[list[str]] = []
    for argv in _pytest_runs_from_task_cmd(cmd)[1:]:
        paths = {tok for tok in argv if not tok.startswith("-")}
        if paths and paths <= ignored:
            alone.append(argv)
    return alone


def _station_test_task_argv(station: str) -> tuple[list[str], list[list[str]]]:
    cmd = _pixi_task_cmd(f"pyforge-{station}-test")
    if not cmd:
        return [], []
    return _pytest_first_run_flags(cmd), _pytest_alone_runs_from_task_cmd(cmd)


def _under_any(argv: list[str], test_paths: list[Path]) -> bool:
    """True when every path in ``argv`` lies under one of this suite's test directories."""
    roots = [tp.resolve() for tp in test_paths]
    paths = [(REPO / tok).resolve() for tok in argv if not tok.startswith("-")]
    return bool(paths) and all(
        any(p == r or r in p.parents for r in roots) for p in paths
    )


def _resolve_changed_paths(
    base: str, head: str, paths_file: str | None, *, quiet_format_only: bool = False
) -> list[str]:
    if paths_file:
        return [
            line.strip()
            for line in Path(paths_file).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    normalized = _normalize_base(base)
    paths = _git_diff_names(normalized, head)
    return _drop_format_only(paths, normalized, head, quiet=quiet_format_only)


def build_coverage_plan(
    *,
    base: str,
    head: str,
    paths_file: str | None,
    suites: Sequence[str],
    coverage_gates_stations: str | None = None,
) -> dict[str, object]:
    """JSON-serializable plan of pytest runs the driver would make (Story 71.4)."""
    paths = _resolve_changed_paths(base, head, paths_file, quiet_format_only=True)
    stations = sorted(touched_stations(paths))
    allow_raw = (
        coverage_gates_stations or os.environ.get("COVERAGE_GATES_STATIONS", "")
    ).strip()
    allow = (
        {s.strip() for s in allow_raw.split(",") if s.strip()} if allow_raw else None
    )
    runs: list[dict[str, object]] = []
    for station in stations:
        if station not in STATIONS:
            continue
        if allow is not None and station not in allow:
            continue
        root = package_root(REPO, station)
        src = package_src(REPO, station)
        if not src.is_dir():
            continue
        for suite in suites:
            if suite not in ("unit", "integration"):
                continue
            test_paths = _suite_test_paths(root, suite)
            if not test_paths:
                continue
            runs.append(
                {
                    "station": station,
                    "suite": suite,
                    "test_paths": [str(p.relative_to(REPO)) for p in test_paths],
                    "marker_expr": GATE_MARKER_EXPR,
                }
            )
    return {
        "touched_stations": stations,
        "runs": runs,
    }


def merge_coverage_reports(paths: Sequence[Path]) -> dict[str, object]:
    """The union of several coverage.py JSON reports over the same source (Story 117.4).

    Per file, executed lines and branches are unioned and the missing sets are what no report executed; the summary
    percent is coverage.py's own formula, ``(covered_lines + covered_branches) / (num_statements + num_branches)``.
    Files present in one report only keep that report's data. Totals are recomputed the same way.
    """
    merged: dict[str, dict[str, object]] = {}
    meta: dict[str, object] = {}
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        meta = meta or dict(payload.get("meta") or {})
        for name, data in (payload.get("files") or {}).items():
            if not isinstance(data, Mapping):
                continue
            slot = merged.setdefault(
                name,
                {
                    "executed_lines": set(),
                    "missing_lines": set(),
                    "executed_branches": set(),
                    "missing_branches": set(),
                    "excluded_lines": set(),
                },
            )
            slot["executed_lines"] |= set(data.get("executed_lines") or [])
            slot["missing_lines"] |= set(data.get("missing_lines") or [])
            slot["excluded_lines"] |= set(data.get("excluded_lines") or [])
            slot["executed_branches"] |= {
                tuple(b) for b in data.get("executed_branches") or []
            }
            slot["missing_branches"] |= {
                tuple(b) for b in data.get("missing_branches") or []
            }
    files: dict[str, object] = {}
    tot_lines = tot_missing = tot_br = tot_br_missing = 0
    for name, slot in sorted(merged.items()):
        executed = slot["executed_lines"]
        missing = slot["missing_lines"] - executed
        exec_br = slot["executed_branches"]
        missing_br = slot["missing_branches"] - exec_br
        statements = len(executed) + len(missing)
        branches = len(exec_br) + len(missing_br)
        denominator = statements + branches
        percent = (
            100.0
            if denominator == 0
            else 100.0 * (len(executed) + len(exec_br)) / denominator
        )
        files[name] = {
            "executed_lines": sorted(executed),
            "missing_lines": sorted(missing),
            "excluded_lines": sorted(slot["excluded_lines"]),
            "executed_branches": [list(b) for b in sorted(exec_br)],
            "missing_branches": [list(b) for b in sorted(missing_br)],
            "summary": {
                "covered_lines": len(executed),
                "num_statements": statements,
                "percent_covered": percent,
                "percent_covered_display": f"{percent:.0f}",
                "missing_lines": len(missing),
                "excluded_lines": len(slot["excluded_lines"]),
                "num_branches": branches,
                "covered_branches": len(exec_br),
                "missing_branches": len(missing_br),
            },
        }
        tot_lines += len(executed)
        tot_missing += len(missing)
        tot_br += len(exec_br)
        tot_br_missing += len(missing_br)
    denominator = tot_lines + tot_missing + tot_br + tot_br_missing
    totals = {
        "covered_lines": tot_lines,
        "num_statements": tot_lines + tot_missing,
        "missing_lines": tot_missing,
        "num_branches": tot_br + tot_br_missing,
        "covered_branches": tot_br,
        "missing_branches": tot_br_missing,
        "percent_covered": 100.0
        if denominator == 0
        else 100.0 * (tot_lines + tot_br) / denominator,
    }
    return {
        "meta": {**meta, "merged_from": [str(p) for p in paths]},
        "files": files,
        "totals": totals,
    }


def allow_for_report(environ: Mapping[str, str]) -> set[str]:
    """The stations ``COVERAGE_GATES_STATIONS`` names (Story 117.2: ``--report`` wants exactly one)."""
    raw = environ.get("COVERAGE_GATES_STATIONS", "").strip()
    return {s.strip() for s in raw.split(",") if s.strip()} if raw else set()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        default=os.environ.get("GITHUB_BASE_REF", "origin/main"),
        help=(
            "git diff base (default: GITHUB_BASE_REF, else origin/main); a branch name "
            "or origin/<name> is read as refs/remotes/origin/<name>"
        ),
    )
    parser.add_argument(
        "--head",
        default="HEAD",
        help="git diff head (default: HEAD)",
    )
    parser.add_argument(
        "--paths-file",
        default=None,
        help="Optional precomputed changed-paths list (skips git diff)",
    )
    parser.add_argument(
        "--suites",
        default="unit,integration",
        help="Comma-separated suites to gate (default: unit,integration)",
    )
    parser.add_argument(
        "--report",
        action="append",
        default=None,
        help=(
            "Story 117.2: the coverage JSON the station suite's own run wrote; judge it instead of "
            "running pytest-cov again. Repeatable (Story 117.4): the package-local and live-tree halves "
            "each write one, and the gate judges their union (executed lines and branches merged per "
            "file). When none of the files exists, run the coverage pass as before and write the first "
            "path. One station (COVERAGE_GATES_STATIONS) and --suites unit only."
        ),
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Print the stations and suites that would run as JSON; do not invoke pytest",
    )
    args = parser.parse_args(argv)

    paths = _resolve_changed_paths(args.base, args.head, args.paths_file)
    stations = sorted(touched_stations(paths))
    modules = sorted(touched_source_modules(paths))

    suites = [s.strip() for s in args.suites.split(",") if s.strip()]
    for suite in suites:
        if suite not in ("unit", "integration"):
            print(f"unknown suite {suite!r}; expected unit|integration", flush=True)
            return 2
    if args.report and (suites != ["unit"] or len(allow_for_report(os.environ)) != 1):
        print(
            "--report takes --suites unit and exactly one COVERAGE_GATES_STATIONS station",
            flush=True,
        )
        return 2

    if args.plan:
        plan = build_coverage_plan(
            base=args.base,
            head=args.head,
            paths_file=args.paths_file,
            suites=suites,
        )
        print(json.dumps(plan, sort_keys=True), flush=True)
        return 0

    print(f"touched stations: {stations or '(none)'}", flush=True)
    print(f"touched source modules: {modules or '(none)'}", flush=True)

    if not stations:
        print("coverage gates: no pyforge station packages touched; OK", flush=True)
        return 0

    # Optional allow-list (CI home env often only installs one station).
    allow_raw = os.environ.get("COVERAGE_GATES_STATIONS", "").strip()
    allow = (
        {s.strip() for s in allow_raw.split(",") if s.strip()} if allow_raw else None
    )
    rc = 0
    with tempfile.TemporaryDirectory(prefix="coverage-gates-") as tmp:
        tmp_path = Path(tmp)
        for station in stations:
            if station not in STATIONS:
                continue
            if allow is not None and station not in allow:
                print(
                    f"coverage gates: skipping pyforge-{station} "
                    f"(not in COVERAGE_GATES_STATIONS={allow_raw})",
                    flush=True,
                )
                continue
            for suite in suites:
                if suite not in ("unit", "integration"):
                    print(
                        f"unknown suite {suite!r}; expected unit|integration",
                        flush=True,
                    )
                    return 2
                report = tmp_path / f"{station}-{suite}.json"
                present = [Path(r) for r in (args.report or []) if Path(r).is_file()]
                if present:
                    # Story 117.2 / 117.4: the suite's own run(s) wrote these reports; judge their union, never re-run.
                    print(
                        f"coverage gate: judging pyforge-{station} {suite} from "
                        + ", ".join(str(r) for r in present),
                        flush=True,
                    )
                    if len(present) == 1:
                        report = present[0]
                    else:
                        report = tmp_path / f"{station}-{suite}-merged.json"
                        report.write_text(
                            json.dumps(merge_coverage_reports(present), sort_keys=True),
                            encoding="utf-8",
                        )
                    status, pytest_rc = "ran", 0
                else:
                    if args.report:
                        report = Path(args.report[0])
                        report.parent.mkdir(parents=True, exist_ok=True)
                    status, pytest_rc = _run_pytest_cov(
                        station=station, suite=suite, report=report
                    )
                if status == "skipped":
                    # N/A suite (e.g. no tests/integration) — never zero-fill.
                    continue
                if pytest_rc != 0:
                    print(
                        f"pytest failed for pyforge-{station} {suite} "
                        f"(exit {pytest_rc})",
                        flush=True,
                    )
                    rc = 1
                    # Still evaluate when a report exists so under-threshold
                    # modules are named alongside the red suite.
                    if not report.is_file():
                        continue
                gate_rc = _evaluate(
                    station=station,
                    suite=suite,
                    report=report,
                    modules=modules,
                )
                if gate_rc != 0:
                    rc = 1
                thr = thresholds_for(station).for_suite(suite)  # type: ignore[arg-type]
                print(
                    f"pyforge-{station} {suite} floor: {thr:.0f}%",
                    flush=True,
                )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
