"""Every durations file the sharded station-tests matrix names exists and holds timings.

Steward Story 136.7 (spec-pyforge-steward:CAP-175, DW-steward-cutover-2026-11-10-11): ``pytest-split``
falls back to splitting by test count, without failing, when its ``--durations-path`` is missing, so a
sharded job that names a file nobody wrote stays green and unbalanced. This test is what reds instead.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pyforge-station-tests.yml"
#: Steward Story 117.23: Platform CI's test job is sharded too. Its path runs from src/platform, its working directory,
#: and is written with ``=``: pytest takes a bare option value that names an existing path for a test path, and would
#: then read its rootdir and configuration from the repository root, not src/platform.
PLATFORM_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "platform-ci.yml"
DURATIONS_DIR = REPO_ROOT / "tests" / "durations"
_DURATIONS_PATH = re.compile(r"--durations-path(?:\s+|=)(?:\.\./)*(tests/durations/[\w.-]+\.json)")


def named_durations_files(workflow_text: str) -> list[str]:
    """The durations files the workflow's sharded jobs name, each once, sorted."""
    return sorted(set(_DURATIONS_PATH.findall(workflow_text)))


def durations_problems(names: list[str], root: Path) -> list[str]:
    """One line per named file that is missing, unreadable, or holds no positive timing."""
    problems: list[str] = []
    for name in names:
        path = root / name
        if not path.is_file():
            problems.append(f"{name}: missing")
            continue
        try:
            timings = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            problems.append(f"{name}: not JSON ({exc})")
            continue
        if not isinstance(timings, dict) or not timings:
            problems.append(f"{name}: holds no timings")
        elif not all(
            isinstance(value, (int, float)) and value >= 0 for value in timings.values()
        ):
            problems.append(f"{name}: a timing is not a non-negative number")
    return problems


def _sharded_workflows() -> str:
    """The text of every workflow whose jobs shard with pytest-split."""
    return "\n".join(path.read_text(encoding="utf-8") for path in (WORKFLOW, PLATFORM_WORKFLOW))


def test_the_workflow_names_at_least_one_durations_file() -> None:
    assert named_durations_files(WORKFLOW.read_text(encoding="utf-8")), (
        "no sharded job names a durations file"
    )
    # Story 117.23: Platform CI's test job names its own.
    assert "tests/durations/platform.json" in named_durations_files(PLATFORM_WORKFLOW.read_text(encoding="utf-8"))


def test_every_durations_file_the_workflow_names_exists_and_holds_timings() -> None:
    names = named_durations_files(_sharded_workflows())
    assert durations_problems(names, REPO_ROOT) == []


def test_no_durations_file_is_left_that_no_job_names() -> None:
    names = {
        Path(name).name
        for name in named_durations_files(_sharded_workflows())
    }
    on_disk = {path.name for path in DURATIONS_DIR.glob("*.json")}
    assert on_disk - names == set()


def test_a_missing_empty_or_malformed_file_is_named(tmp_path: Path) -> None:
    durations = tmp_path / "tests" / "durations"
    durations.mkdir(parents=True)
    (durations / "empty.json").write_text("{}", encoding="utf-8")
    (durations / "broken.json").write_text("{", encoding="utf-8")
    (durations / "wrong.json").write_text('{"a::b": "slow"}', encoding="utf-8")
    (durations / "good.json").write_text('{"a::b": 0.5}', encoding="utf-8")
    text = "\n".join(
        f"PYTEST_ADDOPTS: --splits 2 --group 1 --durations-path tests/durations/{name}.json"
        for name in ("missing", "empty", "broken", "wrong", "good")
    )
    problems = durations_problems(named_durations_files(text), tmp_path)
    assert [line.split(":")[0] for line in problems] == [
        "tests/durations/broken.json",
        "tests/durations/empty.json",
        "tests/durations/missing.json",
        "tests/durations/wrong.json",
    ]


def test_a_path_from_a_job_s_working_directory_is_read() -> None:
    """Story 117.23: a job that runs from a subdirectory names the file with a ``../`` prefix, after ``=``."""
    text = "PYTEST_ADDOPTS: --splits 3 --group 1 --durations-path=../../tests/durations/platform.json"
    assert named_durations_files(text) == ["tests/durations/platform.json"]
    assert named_durations_files("--durations-path tests/durations/x.json") == ["tests/durations/x.json"]

