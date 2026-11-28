"""The station-tests run starts no more test jobs than fit beside the other workflows' (steward Story 117.41).

Steward Story 117.41 (spec-pyforge-steward CAP-175): the ``changes`` job's filter step holds one table of every sharded
suite's shard count, normal and crowded, sums the normal job count of the jobs the run will start, and writes each
suite's group list as an output its job's matrix reads. These tests run that section of the step as the runner does,
against stated outputs, and hold every sharded job to the output and to ``--splits ${{ strategy.job-total }}``.
Story 117.42 is held here too: ``kedro-catalog-check`` runs once, on a live-half shard that exists in both modes.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pyforge-station-tests.yml"
BUDGET = 29
_GROUPS_EXPR = re.compile(r"^\$\{\{ fromJSON\(needs\.changes\.outputs\.([a-z_]+)_groups\) \}\}$")


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _filter_script() -> str:
    steps = _workflow()["jobs"]["changes"]["steps"]
    (step,) = [step for step in steps if step.get("id") == "filter"]
    return step["run"]


def _shard_section() -> str:
    """The filter step's lines from the shard table to its end: what runs after every other output is written."""
    lines = _filter_script().splitlines()
    (start,) = [index for index, line in enumerate(lines) if line.strip().startswith("job_budget=")]
    return "\n".join(lines[start:]) + "\n"


def _start_outputs() -> list[str]:
    """Every ``changes`` output that starts a job (the group lists excluded)."""
    outputs = _workflow()["jobs"]["changes"]["outputs"]
    return sorted(name for name in outputs if not name.endswith("_groups"))


def _sharded_jobs() -> dict[str, str]:
    """Each job whose matrix reads a group list, keyed by the suite the list is named for."""
    found: dict[str, str] = {}
    for job_id, job in _workflow()["jobs"].items():
        group = (((job.get("strategy") or {}).get("matrix")) or {}).get("group")
        if isinstance(group, str):
            match = _GROUPS_EXPR.match(group)
            assert match, f"{job_id}: matrix.group {group!r} is not a changes group list"
            found[match.group(1)] = job_id
    return found


def run_section(outputs: dict[str, bool], tmp_path: Path) -> dict[str, list[int]]:
    """Run the shard section after the stated outputs, as the filter step does, and read back the group lists."""
    if shutil.which("bash") is None or shutil.which("seq") is None:
        pytest.skip("bash and seq are needed to run the filter step's shard section")
    output = tmp_path / "github-output"
    output.write_text("".join(f"{name}={'true' if value else 'false'}\n" for name, value in outputs.items()))
    script = "set -euo pipefail\n" + _shard_section()
    subprocess.run(
        ["bash", "--noprofile", "--norc", "-c", script],
        env={"GITHUB_OUTPUT": str(output), "PATH": "/usr/bin:/bin"},
        check=True,
        capture_output=True,
        text=True,
    )
    groups: dict[str, list[int]] = {}
    for line in output.read_text().splitlines():
        name, _, value = line.partition("=")
        if name.endswith("_groups"):
            groups[name.removesuffix("_groups")] = json.loads(value)
    return groups


def _jobs_started(outputs: dict[str, bool], groups: dict[str, list[int]]) -> int:
    return sum(len(groups[name]) if name in groups else 1 for name, fired in outputs.items() if fired)


def test_every_sharded_job_reads_its_group_list_and_splits_by_its_matrix() -> None:
    workflow = _workflow()
    declared = workflow["jobs"]["changes"]["outputs"]
    for suite, job_id in _sharded_jobs().items():
        assert declared[f"{suite}_groups"] == f"${{{{ steps.filter.outputs.{suite}_groups }}}}"
        addopts = workflow["jobs"][job_id]["env"]["PYTEST_ADDOPTS"]
        assert "--splits ${{ strategy.job-total }} --group ${{ matrix.group }}" in addopts, job_id
        assert suite in _start_outputs(), f"{suite} starts no job"


def test_a_run_of_every_station_starts_the_budget(tmp_path: Path) -> None:
    outputs = dict.fromkeys(_start_outputs(), True)
    groups = run_section(outputs, tmp_path)
    assert set(groups) == set(_sharded_jobs())
    assert _jobs_started(outputs, groups) == BUDGET
    assert {suite: len(lists) for suite, lists in groups.items()} == {
        "atlas": 3,
        "atlas_live": 2,
        "doctor_live": 1,
        "herald": 1,
        "herald_live": 3,
        "marshal": 3,
        "marshal_live": 1,
        "steward": 1,
        "steward_live": 3,
        "warden": 1,
    }


def test_a_run_of_one_station_keeps_the_normal_counts(tmp_path: Path) -> None:
    outputs = {name: name in {"core", "steward", "steward_live"} for name in _start_outputs()}
    groups = run_section(outputs, tmp_path)
    assert groups["steward"] == [1, 2]
    assert groups["steward_live"] == [1, 2, 3, 4]
    assert groups["marshal"] == [1, 2, 3, 4]


def test_the_budget_is_inclusive(tmp_path: Path) -> None:
    """At the normal counts, every sharded suite is 27 jobs: two more fit (29), three do not (30)."""
    sharded = set(_sharded_jobs())
    single = [name for name in _start_outputs() if name not in sharded]
    fits = {name: name in sharded or name in single[:2] for name in _start_outputs()}
    over = {name: name in sharded or name in single[:3] for name in _start_outputs()}
    normal = run_section(fits, tmp_path)
    assert _jobs_started(fits, normal) == BUDGET
    assert normal["marshal"] == [1, 2, 3, 4]
    crowded = run_section(over, tmp_path)
    assert crowded["marshal"] == [1, 2, 3]
    assert _jobs_started(over, crowded) <= BUDGET


def test_the_kedro_catalog_check_runs_once_on_a_live_shard_both_modes_start(tmp_path: Path) -> None:
    workflow = _workflow()
    sites = [
        (job_id, step)
        for job_id, job in workflow["jobs"].items()
        for step in job.get("steps") or []
        if "kedro-catalog-check" in str(step.get("run", ""))
    ]
    assert [(job_id, step.get("if")) for job_id, step in sites] == [("atlas-live-test", "matrix.group == '2'")]
    for outputs in (dict.fromkeys(_start_outputs(), True), {name: name.startswith("atlas") for name in _start_outputs()}):
        assert 2 in run_section(outputs, tmp_path)["atlas_live"]
