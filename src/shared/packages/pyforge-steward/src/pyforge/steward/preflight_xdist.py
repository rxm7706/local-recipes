"""pytest-xdist worker sharing for concurrent pr-preflight lanes (Story 71.6, CAP-159)."""

from __future__ import annotations

from typing import Any

from pyforge.steward import preflight_suite_reduction as psr


def _task_cmd(pixi_data: dict[str, Any], task_name: str) -> str | None:
    return psr._task_cmd(pixi_data, task_name)


def task_cmd_uses_xdist_auto(pixi_data: dict[str, Any], task_name: str) -> bool:
    """True when the pixi task's pytest invocation passes ``-n auto``."""
    cmd = _task_cmd(pixi_data, task_name)
    if not cmd:
        return False
    for segment in cmd.split("&&"):
        segment = segment.strip()
        if not segment:
            continue
        parsed = psr._parse_single_pytest(segment)
        if parsed is None:
            continue
        suffix = parsed.suffix
        for i, tok in enumerate(suffix):
            if tok == "-n" and i + 1 < len(suffix) and suffix[i + 1] == "auto":
                return True
    return False


def allocate_xdist_worker_counts(*, lane_count: int, logical_cores: int) -> list[int]:
    """Split ``logical_cores`` across ``lane_count`` concurrent xdist lanes (each ≥ 1)."""
    if lane_count <= 0:
        return []
    base = logical_cores // lane_count
    remainder = logical_cores % lane_count
    out: list[int] = []
    for i in range(lane_count):
        share = base + (1 if i < remainder else 0)
        out.append(max(1, share))
    return out


def lane_xdist_worker_map(
    *,
    lane_tasks: list[str],
    pixi_data: dict[str, Any],
    logical_cores: int,
    pool_jobs: int,
) -> dict[str, int]:
    """Map each selected lane task that uses ``-n auto`` to its worker share."""
    xdist_tasks = [t for t in lane_tasks if task_cmd_uses_xdist_auto(pixi_data, t)]
    if not xdist_tasks:
        return {}
    concurrent = min(max(1, pool_jobs), len(xdist_tasks))
    shares = allocate_xdist_worker_counts(lane_count=concurrent, logical_cores=logical_cores)
    # Every xdist lane gets the minimum slot so any ``concurrent``-wide batch sums ≤ cores.
    share = min(shares) if shares else 1
    return {task: share for task in xdist_tasks}


def pytest_xdist_argv_from_cmd(cmd: str) -> list[str]:
    """Extract ``-n`` / ``--dist`` tokens from the first pytest segment in a task cmd."""
    for segment in cmd.split("&&"):
        segment = segment.strip()
        if not segment:
            continue
        parsed = psr._parse_single_pytest(segment)
        if parsed is None:
            continue
        out: list[str] = []
        suffix = parsed.suffix
        i = 0
        while i < len(suffix):
            tok = suffix[i]
            if tok in ("-n", "--dist") and i + 1 < len(suffix):
                out.extend([tok, suffix[i + 1]])
                i += 2
                continue
            i += 1
        return out
    return []


def pytest_xdist_argv_for_station_test_task(pixi_data: dict[str, Any], station: str) -> list[str]:
    task = f"pyforge-{station}-test"
    cmd = _task_cmd(pixi_data, task)
    if not cmd:
        return []
    return pytest_xdist_argv_from_cmd(cmd)
