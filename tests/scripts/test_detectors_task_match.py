"""``scripts/detectors.py`` gives a detector the task that runs its script (doctor Story 49.1, DW-doctor-103-3-1).

``discover()`` used to take the first pixi task whose ``cmd`` contained the detector's file name.
``test_flag_gate_check.py`` contains ``flag_gate_check.py``, so a task that listed the test file inline became the
detector's task: steward Story 103.3's review saw six detectors go to ``scripts-lib-test`` that way, and at
``ab38be642f`` the 36 files of ``tests/scripts/scripts-lib-test.txt`` inline take nine. The registry never runs the task
(``run_one`` runs the script), but ``--list``, ``--json`` and ``docs/reference/detectors.md`` name it, and a detector
with no task is the registry's own gap finding, which a wrong match hid. Now a task runs a detector when its ``cmd``
holds the detector's repo-relative path, optionally ``./``-prefixed, as one shell word.

Stdlib + pytest only: this file runs in ``pyforge-ci`` (``pyforge-doctor-scripts-test``).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import detectors  # noqa: E402  (scripts/ has no __init__.py; sys.path is set above)

FLAG_GATE = "scripts/flag_gate_check.py"

#: Every scanned detector and the task it maps to at ``ab38be642f``, before this story. The fix keeps each one; a
#: detector retired from the tree drops its row here.
LIVE_TASKS = {
    "ad_citation_check": "ad-citation-check",
    "bmad_cursor_mdc_check": "bmad-cursor-mdc-check",
    "bmad_estate_check": "bmad-estate-check",
    "bmad_loop_baseline_drift_check": "baseline-drift-check",
    "cfe_rebuild_guard_check": "cfe-rebuild-guard-check",
    "chain_currency_sweep_check": "chain-currency-sweep-check",
    "ci_surface_gates": "ci-surface-gates-check",
    "claude_instruction_mode_check": "claude-instruction-mode-check",
    "failure_catalog_check": "failure-catalog-check",
    "flag_gate_check": "flag-gate-check",
    "governance_currency_check": "governance-currency",
    "index_freshness_check": "index-freshness-check",
    "llms_full_check": "llms-full-check",
    "loop_stall_check": "loop-stall-check",
    "mason_cfe_surface_check": "mason-cfe-surface-check",
    "memlog_fidelity_check": "memlog-fidelity-check",
    "missing_preserve_check": "missing-preserve-check",
    "pin_policy_check": "pin-policy-check",
    "pixi_version_check": "pixi-version-check",
    "platform_ci_test_requirements_check": "platform-ci-test-requirements-check",
    "precommit_config_check": "precommit-config-check",
    "protected_refs_ruleset_check": "protected-refs-ruleset-check",
    "realization_register_check": "realization-register-check",
    "scribe_graph_freshness_check": "scribe-graph-freshness-check",
    "target_version_check": "target-version-check",
    "tea_playwright_check": "tea-playwright-check",
    "unpushed_work_check": "unpushed-work-check",
    "upstream_todos_check": "upstream-todos-check",
}


def _discover_with(
    monkeypatch: pytest.MonkeyPatch, tasks: dict[str, str]
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """``discover()`` over the live scripts with ``tasks`` as the pixi task table, rows keyed by detector name."""
    monkeypatch.setattr(detectors, "_pixi_tasks", lambda: dict(tasks))
    found, gaps = detectors.discover()
    return {row["name"]: row for row in found}, gaps


def _first(extra: dict[str, str], tasks: dict[str, str]) -> dict[str, str]:
    """``tasks`` with ``extra`` placed first in order, the way an earlier feature's task would sit in ``pixi.toml``."""
    return {**extra, **{name: cmd for name, cmd in tasks.items() if name not in extra}}


def _lib_test_files() -> list[str]:
    listing = (REPO_ROOT / "tests" / "scripts" / "scripts-lib-test.txt").read_text(encoding="utf-8")
    return [line.strip() for line in listing.splitlines() if line.strip()]


# --- AC2: a task that names a detector's test file does not take the detector -----------------------------------


def test_a_task_listing_the_library_tests_inline_takes_no_detector(monkeypatch: pytest.MonkeyPatch) -> None:
    """The review's reproduction (DW-doctor-103-3-1): ``scripts-lib-test``'s files inline, in a task ahead of the
    others. The inline ``cmd`` contains several detectors' file names (``test_<detector>.py``), which is what the old
    substring test matched; none of those detectors maps to it now."""
    live = detectors._pixi_tasks()
    inline_cmd = "python -m pytest " + " ".join(_lib_test_files()) + " -q"
    rows, gaps = _discover_with(monkeypatch, _first({"scripts-lib-test": inline_cmd}, live))

    named_by_file_name = sorted(name for name, row in rows.items() if Path(row["path"]).name in inline_cmd)
    assert "flag_gate_check" in named_by_file_name and len(named_by_file_name) >= 6, named_by_file_name
    assert [name for name, row in rows.items() if row["task"] == "scripts-lib-test"] == []
    assert {name: rows[name]["task"] for name in LIVE_TASKS} == LIVE_TASKS
    assert gaps == []


def test_a_task_running_only_the_detectors_test_does_not_take_it(monkeypatch: pytest.MonkeyPatch) -> None:
    live = detectors._pixi_tasks()
    first = {"lib": "python -m pytest tests/scripts/test_flag_gate_check.py -q"}
    rows, _gaps = _discover_with(monkeypatch, _first(first, live))

    assert rows["flag_gate_check"]["task"] == "flag-gate-check"


# --- AC3: a detector left with only a test listing is a registry gap ---------------------------------------------


def test_a_detector_whose_own_task_is_gone_reads_as_a_registry_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    """The gap a wrong match hid: ``flag-gate-check`` removed, a task naming its test file left."""
    live = {name: cmd for name, cmd in detectors._pixi_tasks().items() if name != "flag-gate-check"}
    rows, gaps = _discover_with(monkeypatch, _first({"lib": "pytest tests/scripts/test_flag_gate_check.py -q"}, live))

    assert rows["flag_gate_check"]["task"] is None
    assert [gap for gap in gaps if gap.startswith(f"{FLAG_GATE}:")] == [
        f"{FLAG_GATE}: declares scope=repo but has no pixi task — nothing can invoke it by name"
    ]


# --- AC4: the path is one shell word -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cmd",
    [
        "python scripts/flag_gate_check.py",
        "python ./scripts/flag_gate_check.py --check",
        'python "scripts/flag_gate_check.py"',
        "python 'scripts/flag_gate_check.py'",
        "python scripts/flag_gate_check.py && echo ok",
        "(python scripts/flag_gate_check.py)",
        "python scripts/flag_gate_check.py;echo ok",
        "python scripts/flag_gate_check.py|tee out.txt",
        "scripts/flag_gate_check.py",
        "python\tscripts/flag_gate_check.py",
    ],
)
def test_a_command_running_the_path_runs_the_detector(cmd: str) -> None:
    assert detectors._runs_detector(cmd, FLAG_GATE) is True


@pytest.mark.parametrize(
    "cmd",
    [
        "pytest tests/scripts/test_flag_gate_check.py",
        "python tests/scripts/flag_gate_check.py",
        "python vendor/scripts/flag_gate_check.py",
        "python xscripts/flag_gate_check.py",
        "python ../scripts/flag_gate_check.py",
        "python scripts/flag_gate_check.pyc",
        "python scripts/flag_gate_check.py.bak",
        "python scripts/flag_gate_check_v2.py",
        "python scripts/flag_gate_check.py:main",
        "python -m pytest --deselect=scripts/flag_gate_check.py",
        "python scripts/other_check.py",
        "",
    ],
)
def test_a_command_that_only_names_another_path_does_not(cmd: str) -> None:
    assert detectors._runs_detector(cmd, FLAG_GATE) is False


def test_the_path_is_matched_literally_not_as_a_pattern() -> None:
    """``.`` in the path is a dot, not any character."""
    assert detectors._runs_detector("python scripts/flag_gate_checkXpy", FLAG_GATE) is False


# --- AC5: a --json task is still skipped ---------------------------------------------------------------------------


def test_a_json_task_ahead_of_the_detectors_own_is_still_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    live = detectors._pixi_tasks()
    rows, _gaps = _discover_with(monkeypatch, _first({"j": f"python {FLAG_GATE} --json"}, live))

    assert rows["flag_gate_check"]["task"] == "flag-gate-check"


def test_a_same_named_file_elsewhere_ahead_of_the_detectors_task_is_not_it(monkeypatch: pytest.MonkeyPatch) -> None:
    live = detectors._pixi_tasks()
    rows, _gaps = _discover_with(monkeypatch, _first({"o": "python tests/scripts/flag_gate_check.py"}, live))

    assert rows["flag_gate_check"]["task"] == "flag-gate-check"


# --- AC6: the whole scan, over its own pixi.toml ---------------------------------------------------------------------


def test_a_fixture_tree_maps_each_detector_to_the_task_that_runs_its_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "docs" / "dashboard").mkdir(parents=True)
    (tmp_path / "scripts" / "alpha_check.py").write_text('DETECTOR = {"scope": "repo"}\n', encoding="utf-8")
    (tmp_path / "docs" / "dashboard" / "check_beta.py").write_text(
        'DETECTOR = {"scope": "runtime"}\n', encoding="utf-8"
    )
    (tmp_path / "pixi.toml").write_text(
        "[feature.first.tasks]\n"
        'alpha-tests = "pytest tests/scripts/test_alpha_check.py tests/docs/test_check_beta.py -q"\n'
        "[feature.second.tasks]\n"
        'alpha-check = { cmd = "python scripts/alpha_check.py" }\n'
        'beta-check = "python ./docs/dashboard/check_beta.py --strict"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(detectors, "ROOT", tmp_path)
    monkeypatch.setattr(
        detectors,
        "SEARCH",
        ((tmp_path / "scripts", "*_check.py"), (tmp_path / "docs" / "dashboard", "check_*.py")),
    )

    found, gaps = detectors.discover()

    assert [(row["path"], row["scope"], row["task"]) for row in found] == [
        ("scripts/alpha_check.py", "repo", "alpha-check"),
        ("docs/dashboard/check_beta.py", "runtime", "beta-check"),
    ]
    assert gaps == []


# --- AC7: the live tree --------------------------------------------------------------------------------------------


def test_every_live_detector_keeps_its_task_and_that_task_runs_its_path() -> None:
    found, gaps = detectors.discover()
    tasks = detectors._pixi_tasks()
    mapped = {row["name"]: row["task"] for row in found}

    assert gaps == []
    assert {name: mapped.get(name) for name in LIVE_TASKS} == LIVE_TASKS
    assert [
        row["path"]
        for row in found
        if row["task"] is None or not detectors._runs_detector(tasks[row["task"]], row["path"])
    ] == []
