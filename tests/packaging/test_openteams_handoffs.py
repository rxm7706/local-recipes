"""Offline unit tests for Story 17.2 ("handoffs are execution-ready"):

1. `create_missing_issues` in
   `conda-forge-packaging-inventory-operations_openteams_identity.py` -- one
   `gh issue create` (+ `gh project item-add`) per record missing
   `OpenTeams_Issue_URL`, disabled by default (dry-run) behind `--create-issues`.
2. `write_aoss_free_queue` in `conda-forge-packaging-inventory-operations_metrics.py`
   -- the dated AOSS-Free extra Mason queue, which must never expand the
   OpenTeams universe (CDO-ENT-JFROG union CDO-ENT-CONDA).
3. `write_ops_canvas` / `write_workbook_canvas` in
   `openteams_identity_dashboards.py` -- the two missing dashboard-canvas
   generators (catalog already existed via
   conda-forge-packaging-inventory-operations_priority.py::write_canvas).

Per this project's Testing Contract, this file never touches real GitHub
credentials or the network: every `gh` call is mocked
(`subprocess.check_output` / `subprocess.check_call`).

`pytest.importorskip("openpyxl")` at module scope keeps this file collectible
under the deliberately lean `pyforge-ci` environment that
`pixi run -e pyforge-ci pyforge-deps-test` runs the rest of `tests/packaging`
in (see test_dependency_completeness.py's module docstring) -- the three
target scripts import `openpyxl` at module load time and only run under
`-e local-recipes`, where the real quartet lives. Without this guard, adding
this file to `tests/packaging/` would break that unrelated, pre-existing gate
with a `ModuleNotFoundError` at collection time.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

pytest.importorskip(
    "openpyxl",
    reason="target scripts import openpyxl at module load; only present under -e local-recipes",
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _load_module(filename: str):
    """Import a (possibly hyphenated-filename) script under `scripts/` as a
    module. Mirrors `.claude/skills/conda-forge-expert/tests/conftest.py`'s
    `load_module` fixture -- this tree has no shared conftest for
    `tests/packaging`, so it is inlined here rather than adding one just for
    this file.
    """
    script_path = SCRIPTS_DIR / filename
    assert script_path.is_file(), f"script not found: {script_path}"
    module_name = script_path.stem.replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


identity = _load_module("conda-forge-packaging-inventory-operations_openteams_identity.py")
metrics = _load_module("conda-forge-packaging-inventory-operations_metrics.py")
dashboards = _load_module("openteams_identity_dashboards.py")
priority = _load_module("conda-forge-packaging-inventory-operations_priority.py")


def test_discovery_is_not_vacuous():
    """If any of these stopped existing (typo, rename), every test below would
    fail on AttributeError with a confusing traceback -- this fails loudly
    and specifically instead."""
    assert callable(identity.create_missing_issues)
    assert callable(metrics.write_aoss_free_queue)
    assert callable(dashboards.write_ops_canvas)
    assert callable(dashboards.write_workbook_canvas)


# ---------------------------------------------------------------------------
# create_missing_issues (conda-forge-packaging-inventory-operations_openteams_identity.py)
# ---------------------------------------------------------------------------


def _row(name: str, issue_url: str = "") -> dict[str, str]:
    return {
        "Core_Python_Package_Name": name,
        "OpenTeams_Title": f"[Conda-Forge Packaging] {name}",
        "OpenTeams_Issue_URL": issue_url,
    }


def test_dry_run_default_makes_no_gh_call(monkeypatch):
    calls: list[tuple[str, tuple, dict]] = []
    monkeypatch.setattr(
        subprocess, "check_output", lambda *a, **k: calls.append(("check_output", a, k)) or ""
    )
    monkeypatch.setattr(
        subprocess, "check_call", lambda *a, **k: calls.append(("check_call", a, k)) or 0
    )

    row = _row("some-pkg")
    result = identity.create_missing_issues("gh", [row], board={}, dry_run=True)

    assert calls == [], "dry-run must never call the gh subprocess"
    assert result == [("some-pkg", "[Conda-Forge Packaging] some-pkg")]
    assert row["OpenTeams_Issue_URL"] == ""


def test_dry_run_is_the_default_parameter_value(monkeypatch):
    """`--create-issues` is opt-in: calling without `dry_run` at all must also
    make no gh call (mirrors main()'s `dry_run=not args.create_issues` wiring
    when the flag is absent)."""
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: (_ for _ in ()).throw(AssertionError("gh called")))
    monkeypatch.setattr(subprocess, "check_call", lambda *a, **k: (_ for _ in ()).throw(AssertionError("gh called")))

    result = identity.create_missing_issues(None, [_row("some-pkg")], board={})
    assert result == [("some-pkg", "[Conda-Forge Packaging] some-pkg")]


def test_create_issues_flag_invokes_gh_and_merges_url(monkeypatch):
    calls: list[tuple[str, list]] = []

    def fake_check_output(args, **kwargs):
        calls.append(("check_output", args))
        return "https://github.com/OpenTeams-WFT-CDO/mgmt-wf-python-modernization/issues/123\n"

    def fake_check_call(args, **kwargs):
        calls.append(("check_call", args))
        return 0

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)
    monkeypatch.setattr(subprocess, "check_call", fake_check_call)

    row = _row("some-pkg")
    board: dict[str, str] = {}
    result = identity.create_missing_issues("gh", [row], board=board, dry_run=False)

    issue_calls = [c[1] for c in calls if c[0] == "check_output"]
    assert len(issue_calls) == 1, "exactly one gh issue create call"
    assert issue_calls[0] == [
        "gh",
        "issue",
        "create",
        "--repo",
        "OpenTeams-WFT-CDO/mgmt-wf-python-modernization",
        "--title",
        "[Conda-Forge Packaging] some-pkg",
    ]
    assert identity.ISSUE_CREATE_REPO == "OpenTeams-WFT-CDO/mgmt-wf-python-modernization"

    project_calls = [c[1] for c in calls if c[0] == "check_call"]
    assert len(project_calls) == 1, "the created issue is added to OpenTeams project 1"
    assert project_calls[0] == [
        "gh",
        "project",
        "item-add",
        "--owner",
        "OpenTeams-WFT-CDO",
        "--number",
        "1",
        "--url",
        "https://github.com/OpenTeams-WFT-CDO/mgmt-wf-python-modernization/issues/123",
    ]

    assert (
        row["OpenTeams_Issue_URL"]
        == "https://github.com/OpenTeams-WFT-CDO/mgmt-wf-python-modernization/issues/123"
    )
    assert board.get("some-pkg") == row["OpenTeams_Issue_URL"]
    assert result == [("some-pkg", "[Conda-Forge Packaging] some-pkg")]


def test_existing_issue_is_skipped_regardless_of_flag(monkeypatch):
    calls: list = []
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: calls.append(a) or "unexpected")
    monkeypatch.setattr(subprocess, "check_call", lambda *a, **k: calls.append(a) or 0)

    row = _row("already-tracked-pkg", issue_url="https://github.com/x/y/issues/1")
    result_dry = identity.create_missing_issues("gh", [dict(row)], board={}, dry_run=True)
    result_live = identity.create_missing_issues("gh", [dict(row)], board={}, dry_run=False)

    assert result_dry == []
    assert result_live == []
    assert calls == [], "an existing OpenTeams_Issue_URL must never trigger a creation call"


def test_gh_failure_for_one_name_does_not_abort_the_run(monkeypatch):
    calls: list = []

    def fake_check_output(args, **kwargs):
        calls.append(args)
        if "bad-pkg" in args[args.index("--title") + 1]:
            raise subprocess.CalledProcessError(1, args)
        return "https://github.com/OpenTeams-WFT-CDO/mgmt-wf-python-modernization/issues/999\n"

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)
    monkeypatch.setattr(subprocess, "check_call", lambda *a, **k: 0)

    rows = [_row("bad-pkg"), _row("good-pkg")]
    result = identity.create_missing_issues("gh", rows, board={}, dry_run=False)

    assert len(calls) == 2, "both names are attempted -- the failure does not abort the loop"
    assert [name for name, _title in result] == ["good-pkg"]
    assert rows[0]["OpenTeams_Issue_URL"] == "", "unchanged on gh failure"
    assert rows[1]["OpenTeams_Issue_URL"].endswith("/999")


def test_create_issues_flag_is_wired_into_argparse():
    """Real argparse, no mocks: `--help` exits inside argparse before any
    network/gh call is ever reached."""
    script_path = SCRIPTS_DIR / "conda-forge-packaging-inventory-operations_openteams_identity.py"
    proc = subprocess.run(
        [sys.executable, str(script_path), "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0
    assert "--create-issues" in proc.stdout


# ---------------------------------------------------------------------------
# write_aoss_free_queue (conda-forge-packaging-inventory-operations_metrics.py)
# ---------------------------------------------------------------------------


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_write_aoss_free_queue_excludes_the_openteams_universe(tmp_path):
    path = tmp_path / "aoss-free-queue-2026-08-22.csv"
    ts = "2026-08-22T00:00:00Z"

    written = metrics.write_aoss_free_queue(
        path,
        aoss_free_names={"pkg-a", "pkg-b"},
        universe_names={"pkg-b"},  # pkg-b is in CDO-ENT-JFROG or CDO-ENT-CONDA
        timestamp=ts,
    )

    assert written == ["pkg-a"]
    rows = _read_csv_rows(path)
    assert [r["Package_Name"] for r in rows] == ["pkg-a"]
    assert rows[0]["Verification_Timestamp_UTC"] == ts
    assert rows[0]["Reason"]


def test_write_aoss_free_queue_never_mutates_its_universe_argument(tmp_path):
    """The queue is `aoss_free_names - universe_names`; the function must
    never add names to (or otherwise expand) the universe set it was given."""
    path = tmp_path / "aoss-free-queue-2026-08-22.csv"
    universe = {"already-there"}
    metrics.write_aoss_free_queue(
        path,
        aoss_free_names={"new-name"},
        universe_names=universe,
        timestamp="2026-08-22T00:00:00Z",
    )
    assert universe == {"already-there"}


def test_write_aoss_free_queue_empty_input_writes_header_only(tmp_path):
    path = tmp_path / "aoss-free-queue-2026-08-22.csv"
    written = metrics.write_aoss_free_queue(path, set(), set(), "2026-08-22T00:00:00Z")

    assert written == []
    assert _read_csv_rows(path) == []
    header = path.read_text(encoding="utf-8").splitlines()[0]
    assert header == "Package_Name,Reason,Verification_Timestamp_UTC"


# ---------------------------------------------------------------------------
# write_ops_canvas / write_workbook_canvas (openteams_identity_dashboards.py)
# ---------------------------------------------------------------------------


def _decode_data_blob(text: str, prefix: str) -> dict:
    assert text.startswith(prefix)
    remainder = text[len(prefix) :]
    data, _end = json.JSONDecoder().raw_decode(remainder)
    return data


def test_write_ops_canvas_empty_records_is_valid_and_schema_shaped(tmp_path):
    path = tmp_path / "identity-ops.canvas.tsx"
    helpers = types.SimpleNamespace(**vars(identity))

    dashboards.write_ops_canvas(path, [], "identity-2026-08-20", helpers)

    text = path.read_text(encoding="utf-8")
    # Byte-identical to write_canvas's own import block, not just this
    # module's copy of it.
    assert text.startswith(priority._CANVAS_PREFIX)
    data = _decode_data_blob(text, dashboards._CANVAS_PREFIX)
    assert data["n"] == 0
    assert data["rows"] == []
    assert data["leaders"] == []
    # Bucket scaffolding (like write_canvas's bucketDefs) stays fully
    # populated at zero counts -- only the per-package arrays go empty.
    assert len(data["priorityDefs"]) == len(identity.P_ORDER)
    assert all(count == 0 for _p, _desc, count in data["priorityDefs"])


def test_write_workbook_canvas_empty_records_is_valid_and_schema_shaped(tmp_path):
    path = tmp_path / "jfrog-workbook.canvas.tsx"
    helpers = types.SimpleNamespace(**vars(identity))
    missing_xlsx = tmp_path / "missing-workbook.xlsx"

    dashboards.write_workbook_canvas(path, [], missing_xlsx, "identity-2026-08-20", helpers)

    text = path.read_text(encoding="utf-8")
    assert text.startswith(priority._CANVAS_PREFIX)
    data = _decode_data_blob(text, dashboards._CANVAS_PREFIX)
    assert data["neitherRows"] == []
    assert data["needPr"] == []
    assert data["boardGap"] == []
    assert data["workbookTabs"] == []
    assert data["jfrogMap"] == {
        "parseable": 0,
        "skip": 0,
        "both": 0,
        "pypiOnly": 0,
        "cfOnly": 0,
        "neither": 0,
    }
    # Static reference data (not per-package) stays populated.
    assert len(data["externalCounts"]) == len(dashboards.EXTERNAL_LIVE)
