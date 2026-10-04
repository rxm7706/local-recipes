"""Offline unit tests for Story 17.2 ("handoffs are execution-ready") and
Story 21.7 / 23.9 ("quartet thin-out and workbook retirement"):

1. `create_missing_issues` in
   `conda-forge-packaging-inventory-operations_openteams_identity.py` -- one
   `gh issue create` (+ `gh project item-add`) per record missing
   `OpenTeams_Issue_URL`, disabled by default (dry-run) behind `--create-issues`.
2. `write_aoss_queue_csv` in `conda-forge-packaging-inventory-operations_metrics.py`
   -- formats the dated AOSS-Free extra Mason queue from Atlas exports.
3. `write_ops_canvas` / `write_workbook_canvas` in
   `openteams_identity_dashboards.py` -- the two missing dashboard-canvas
   generators (catalog already existed via
   conda-forge-packaging-inventory-operations_priority.py::write_canvas).
4. `identity_complete_export_parquet_path` / `read_identity_complete_export_records`
   / `main()` / `publish_gist_from_tab` in
   `conda-forge-packaging-inventory-operations_openteams_identity.py`
   (Story 23.9) -- the identity script reads ``identity_complete_export.parquet``
   and publishes gist markdown from that export (ranking columns already present).

Per this project's Testing Contract, this file never touches real GitHub
credentials or the network: every `gh` call a test makes goes through a fake
`subprocess.run`, and the autouse `_forbid_unmocked_gh` guard fails any test that
would start a real `gh` -- by bare name or absolute path, through `subprocess.run`
or any `subprocess.Popen` caller (`check_output`, `check_call`, `call`) -- and pins
`identity.gh_bin()` / `identity.DEFAULT_GH` to a sentinel path that cannot exist.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
import types
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

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
    # Reuse a copy another test module (e.g. pyforge-atlas's test_identity_parity.py)
    # already loaded from this same file, so the two never hold diverging copies.
    existing = sys.modules.get(module_name)
    existing_file = getattr(existing, "__file__", None)
    if existing is not None and existing_file and Path(existing_file).resolve() == script_path.resolve():
        return existing
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


_GH_SENTINEL = "/nonexistent-gh-sentinel/gh"


def _subprocess_argv0(args, kwargs) -> str:
    executable = kwargs.get("executable")
    if executable:
        return os.fsdecode(executable)
    if isinstance(args, (str, bytes, os.PathLike)):
        text = os.fsdecode(args)
        if kwargs.get("shell"):
            parts = shlex.split(text)
            return parts[0] if parts else ""
        return text
    try:
        return os.fsdecode(list(args)[0])
    except (IndexError, TypeError):
        return ""


def _is_gh(args, kwargs) -> bool:
    return Path(_subprocess_argv0(args, kwargs)).name in {"gh", "gh.exe"}


@pytest.fixture(autouse=True)
def _forbid_unmocked_gh(monkeypatch):
    """Never start a real ``gh`` from this module (Story 27.1 TEST SAFETY).

    ``subprocess.run``, ``check_output``, ``check_call`` and ``call`` all construct a
    ``subprocess.Popen``; guarding ``Popen`` on the basename of argv[0] catches a bare
    ``gh`` and an absolute path alike. ``gh_bin()`` / ``DEFAULT_GH`` point at a sentinel
    that cannot exist, so even an unguarded path could only fail to start."""
    real_popen = subprocess.Popen
    real_run = subprocess.run

    class _GuardedPopen(real_popen):
        def __init__(self, args, *a, **kw):
            if _is_gh(args, kw):
                raise AssertionError(f"unmocked gh subprocess: {args!r}")
            super().__init__(args, *a, **kw)

    def guarded_run(cmd, *args, **kwargs):
        if _is_gh(cmd, kwargs):
            raise AssertionError(f"unmocked gh subprocess.run: {cmd!r}")
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", _GuardedPopen)
    monkeypatch.setattr(subprocess, "run", guarded_run)
    monkeypatch.setattr(identity, "DEFAULT_GH", Path(_GH_SENTINEL))
    monkeypatch.setattr(identity, "gh_bin", lambda: _GH_SENTINEL)


@pytest.fixture(autouse=True)
def _pin_script_modules(monkeypatch):
    """``identity`` imports ``openteams_identity_dashboards`` by name at call time; pin the
    copies this module patches, whatever another test module left in ``sys.modules``."""
    for module in (identity, metrics, dashboards, priority):
        monkeypatch.setitem(sys.modules, module.__name__, module)


@pytest.mark.parametrize(
    "launch",
    [
        lambda: subprocess.check_call([_GH_SENTINEL, "issue", "list"]),
        lambda: subprocess.check_output(["/usr/bin/gh", "api", "user"]),
        lambda: subprocess.Popen(["gh", "auth", "status"]),
        lambda: subprocess.call("gh gist view x", shell=True),
        lambda: subprocess.run([identity.gh_bin(), "issue", "create"]),
    ],
)
def test_gh_guard_blocks_every_launch_path(launch):
    with pytest.raises(AssertionError, match="unmocked gh"):
        launch()


def test_gh_bin_and_default_gh_are_pinned_to_the_sentinel():
    assert identity.gh_bin() == _GH_SENTINEL
    assert identity.DEFAULT_GH == Path(_GH_SENTINEL)
    assert not Path(_GH_SENTINEL).exists()


def test_discovery_is_not_vacuous():
    """If any of these stopped existing (typo, rename), every test below would
    fail on AttributeError with a confusing traceback -- this fails loudly
    and specifically instead."""
    assert callable(identity.create_missing_issues)
    assert callable(metrics.write_aoss_queue_csv)
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
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    row = _row("some-pkg")
    result = identity.create_missing_issues("gh", [row], board={}, dry_run=True)

    assert calls == [], "dry-run must never call the gh subprocess"
    assert result == [("some-pkg", "[Conda-Forge Packaging] some-pkg")]
    assert row["OpenTeams_Issue_URL"] == ""


def test_dry_run_is_the_default_parameter_value(monkeypatch):
    """`--create-issues` is opt-in: calling without `dry_run` at all must also
    make no gh call (mirrors main()'s `dry_run=not args.create_issues` wiring
    when the flag is absent)."""
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("gh called")),
    )

    result = identity.create_missing_issues(None, [_row("some-pkg")], board={})
    assert result == [("some-pkg", "[Conda-Forge Packaging] some-pkg")]


def test_create_issues_flag_invokes_gh_and_merges_url(monkeypatch):
    calls: list[tuple[str, list]] = []

    def fake_run(cmd, **kwargs):
        calls.append(("run", cmd))
        stdout = (
            "https://github.com/OpenTeams-WFT-CDO/mgmt-wf-python-modernization/issues/123\n"
            if cmd[1] == "issue"
            else ""
        )
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(identity.time, "sleep", lambda _s: None)

    row = _row("some-pkg")
    board: dict[str, str] = {}
    result = identity.create_missing_issues("gh", [row], board=board, dry_run=False)

    issue_calls = [c[1] for c in calls if c[0] == "run" and c[1][1] == "issue"]
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

    project_calls = [c[1] for c in calls if c[0] == "run" and c[1][1] == "project"]
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
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    row = _row("already-tracked-pkg", issue_url="https://github.com/x/y/issues/1")
    result_dry = identity.create_missing_issues("gh", [dict(row)], board={}, dry_run=True)
    result_live = identity.create_missing_issues("gh", [dict(row)], board={}, dry_run=False)

    assert result_dry == []
    assert result_live == []
    assert calls == [], "an existing OpenTeams_Issue_URL must never trigger a creation call"


def test_gh_failure_for_one_name_does_not_abort_the_run(monkeypatch):
    calls: list = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[1] == "issue" and "bad-pkg" in cmd[cmd.index("--title") + 1]:
            raise subprocess.CalledProcessError(1, cmd, stderr="failed")
        stdout = (
            "https://github.com/OpenTeams-WFT-CDO/mgmt-wf-python-modernization/issues/999\n"
            if cmd[1] == "issue"
            else ""
        )
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(identity.time, "sleep", lambda _s: None)

    rows = [_row("bad-pkg"), _row("good-pkg")]
    result = identity.create_missing_issues("gh", rows, board={}, dry_run=False)

    issue_attempts = [c for c in calls if c[1] == "issue"]
    assert len(issue_attempts) == 2, "both names are attempted -- the failure does not abort the loop"
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
    assert "--ops-canvas" in proc.stdout
    assert "--workbook-canvas" in proc.stdout


def test_blank_package_name_is_skipped(monkeypatch):
    """A row with a blank/missing Core_Python_Package_Name must never reach
    `gh issue create` -- it would mint a garbage `[Conda-Forge Packaging] `
    title."""
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    blank_row = _row("")
    blank_row["Core_Python_Package_Name"] = "   "  # whitespace-only, still blank
    rows = [blank_row, _row("good-pkg")]

    dry_result = identity.create_missing_issues("gh", [dict(r) for r in rows], board={}, dry_run=True)
    assert [name for name, _title in dry_result] == ["good-pkg"]
    assert calls == []


def test_gh_binary_vanishing_mid_run_is_caught_not_fatal(monkeypatch):
    """A non-CalledProcessError OSError (e.g. FileNotFoundError if `gh`
    disappears mid-run) must be caught too, in both the issue-create and the
    project-item-add call, so the loop genuinely never aborts."""

    def fake_run(cmd, **kwargs):
        raise FileNotFoundError("gh vanished")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(identity.time, "sleep", lambda _s: None)

    result = identity.create_missing_issues("gh", [_row("some-pkg")], board={}, dry_run=False)
    assert result == []  # issue-create itself failed; nothing to report as created


def test_project_item_add_failure_does_not_mark_row_as_tracked(monkeypatch):
    """If `gh issue create` succeeds but `gh project item-add` fails, the row
    must NOT be marked tracked (OpenTeams_Issue_URL / board), so a future
    Atlas Phase D run's own board join (Story 21.7: this script no longer
    performs that join itself) still sees it as missing and retries the
    project-add step -- otherwise it is silently done forever."""
    issue_url = "https://github.com/OpenTeams-WFT-CDO/mgmt-wf-python-modernization/issues/42"

    def fake_run(cmd, **kwargs):
        if cmd[1] == "issue":
            return subprocess.CompletedProcess(
                cmd, 0, stdout=f"{issue_url}\n", stderr=""
            )
        raise subprocess.CalledProcessError(1, cmd, stderr="project add failed")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(identity.time, "sleep", lambda _s: None)

    row = _row("some-pkg")
    board: dict[str, str] = {}
    not_filed: list[tuple[str, str]] = []
    result = identity.create_missing_issues(
        "gh", [row], board=board, dry_run=False, not_filed=not_filed
    )

    assert result == []
    assert not_filed == [("some-pkg", f"filed-but-not-added: {issue_url}")]
    assert row["OpenTeams_Issue_URL"] == ""
    assert board == {}


# ---------------------------------------------------------------------------
# write_dashboard_markdown canvas-write guard
# ---------------------------------------------------------------------------


def test_write_dashboard_markdown_survives_a_canvas_write_failure(tmp_path, monkeypatch):
    """A raising write_ops_canvas/write_workbook_canvas must never block the
    gist-markdown write, nor propagate out of write_dashboard_markdown --
    which would otherwise abort the caller's subsequent publish_gist_files
    call even though the gist-markdown publish itself would have succeeded.
    `render` is stubbed here too so this test isolates the canvas guard from
    render()'s own (unrelated) real-xlsx requirement.
    """
    monkeypatch.setattr(dashboards, "render", lambda *a, **k: (_ for _ in ()).throw(AssertionError("render unused")))
    monkeypatch.setattr(
        dashboards, "write_ops_canvas", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("ops boom"))
    )
    monkeypatch.setattr(
        dashboards,
        "write_workbook_canvas",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("workbook boom")),
    )

    dash_path = tmp_path / "dashboards.md"
    export_path = tmp_path / "derived/identity_complete_export/identity_complete_export.parquet"
    export_path.parent.mkdir(parents=True)
    pd.DataFrame([{"Core_Python_Package_Name": "pkg-a"}]).to_parquet(export_path)
    identity.write_dashboard_markdown(
        dash_path,
        "# stub dashboard markdown\n",
        [],
        "identity_complete_export",
        export_path,
    )

    assert dash_path.read_text(encoding="utf-8") == "# stub dashboard markdown\n"


# ---------------------------------------------------------------------------
# INVENTORY_IDENTITY_UI mode gating (Story 22.6)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("env_value", "expected"),
    [
        (None, "both"),
        ("both", "both"),
        ("BOTH", "both"),
        (" canvas ", "canvas"),
        ("Vizro", "vizro"),
        ("vizr0", "both"),
        ("", "both"),
    ],
)
def test_identity_ui_mode(monkeypatch, env_value, expected):
    if env_value is None:
        monkeypatch.delenv(identity.INVENTORY_IDENTITY_UI_ENV, raising=False)
    else:
        monkeypatch.setenv(identity.INVENTORY_IDENTITY_UI_ENV, env_value)
    assert identity._identity_ui_mode() == expected


@pytest.mark.parametrize(
    ("env_value", "expected"),
    [
        (None, "both"),
        ("both", "both"),
        (" canvas ", "canvas"),
        ("Vizro", "vizro"),
        ("vizr0", "both"),
    ],
)
def test_priority_identity_ui_mode(monkeypatch, env_value, expected):
    if env_value is None:
        monkeypatch.delenv(priority.INVENTORY_IDENTITY_UI_ENV, raising=False)
    else:
        monkeypatch.setenv(priority.INVENTORY_IDENTITY_UI_ENV, env_value)
    assert priority._identity_ui_mode() == expected


def test_write_dashboard_markdown_skips_both_canvases_in_vizro_mode(tmp_path, monkeypatch):
    ops_calls: list[tuple] = []
    workbook_calls: list[tuple] = []

    monkeypatch.setenv(identity.INVENTORY_IDENTITY_UI_ENV, "vizro")
    monkeypatch.setattr(
        dashboards,
        "write_ops_canvas",
        lambda *a, **k: ops_calls.append((a, k)),
    )
    monkeypatch.setattr(
        dashboards,
        "write_workbook_canvas",
        lambda *a, **k: workbook_calls.append((a, k)),
    )

    dash_path = tmp_path / "dashboards.md"
    export_path = tmp_path / "derived/identity_complete_export/identity_complete_export.parquet"
    export_path.parent.mkdir(parents=True)
    pd.DataFrame([{"Core_Python_Package_Name": "pkg-a"}]).to_parquet(export_path)
    identity.write_dashboard_markdown(
        dash_path,
        "# gist markdown still written\n",
        [],
        "identity_complete_export",
        export_path,
    )

    assert dash_path.read_text(encoding="utf-8") == "# gist markdown still written\n"
    assert ops_calls == []
    assert workbook_calls == []


@pytest.mark.parametrize("env_value", [None, "both", "canvas", " vizr0 "])
def test_write_dashboard_markdown_writes_both_canvases_by_default(
    tmp_path, monkeypatch, env_value
):
    ops_calls: list[tuple] = []
    workbook_calls: list[tuple] = []

    if env_value is None:
        monkeypatch.delenv(identity.INVENTORY_IDENTITY_UI_ENV, raising=False)
    else:
        monkeypatch.setenv(identity.INVENTORY_IDENTITY_UI_ENV, env_value)
    monkeypatch.setattr(
        dashboards,
        "write_ops_canvas",
        lambda *a, **k: ops_calls.append((a, k)),
    )
    monkeypatch.setattr(
        dashboards,
        "write_workbook_canvas",
        lambda *a, **k: workbook_calls.append((a, k)),
    )
    monkeypatch.setattr(
        dashboards,
        "default_ops_canvas_path",
        lambda: tmp_path / "ops.canvas.tsx",
    )
    monkeypatch.setattr(
        dashboards,
        "default_workbook_canvas_path",
        lambda: tmp_path / "workbook.canvas.tsx",
    )

    dash_path = tmp_path / "dashboards.md"
    export_path = tmp_path / "derived/identity_complete_export/identity_complete_export.parquet"
    export_path.parent.mkdir(parents=True)
    pd.DataFrame([{"Core_Python_Package_Name": "pkg-a"}]).to_parquet(export_path)
    identity.write_dashboard_markdown(
        dash_path,
        "# dashboard markdown\n",
        [{"Core_Python_Package_Name": "pkg-a"}],
        "identity_complete_export",
        export_path,
    )

    assert dash_path.read_text(encoding="utf-8") == "# dashboard markdown\n"
    assert len(ops_calls) == 1
    assert len(workbook_calls) == 1


def test_priority_write_canvas_skipped_in_vizro_mode(monkeypatch):
    monkeypatch.setenv(priority.INVENTORY_IDENTITY_UI_ENV, "vizro")
    assert priority._identity_ui_mode() == "vizro"
    assert not (True and priority._identity_ui_mode() != "vizro")


# ---------------------------------------------------------------------------
# write_aoss_queue_csv (conda-forge-packaging-inventory-operations_metrics.py)
# ---------------------------------------------------------------------------


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_write_aoss_queue_csv_writes_export_rows(tmp_path):
    path = tmp_path / "aoss-free-queue-2026-08-22.csv"
    ts = "2026-08-22T00:00:00Z"
    rows = [
        {
            "Package_Name": "pkg-a",
            "Reason": "On PyPI, not on conda-forge, not in CDO consumption (GAOSS-Free)",
            "Verification_Timestamp_UTC": ts,
        }
    ]
    metrics.write_aoss_queue_csv(path, rows)

    written = _read_csv_rows(path)
    assert [r["Package_Name"] for r in written] == ["pkg-a"]
    assert written[0]["Verification_Timestamp_UTC"] == ts
    assert written[0]["Reason"]


def test_write_aoss_queue_csv_empty_input_writes_header_only(tmp_path):
    path = tmp_path / "aoss-free-queue-2026-08-22.csv"
    metrics.write_aoss_queue_csv(path, [])

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
    export_path = tmp_path / "derived/identity_complete_export/identity_complete_export.parquet"
    export_path.parent.mkdir(parents=True)
    pd.DataFrame([{"Core_Python_Package_Name": "pkg-a"}]).to_parquet(export_path)

    dashboards.write_workbook_canvas(path, [], export_path, "identity_complete_export", helpers)

    text = path.read_text(encoding="utf-8")
    assert text.startswith(priority._CANVAS_PREFIX)
    data = _decode_data_blob(text, dashboards._CANVAS_PREFIX)
    assert data["neitherRows"] == []
    assert data["needPr"] == []
    assert data["boardGap"] == []
    assert data["catalogSources"] == []
    assert data["jfrogMap"] == {
        "parseable": 0,
        "skip": 0,
        "both": 0,
        "pypiOnly": 0,
        "cfOnly": 0,
        "neither": 0,
    }
    assert len(data["externalCounts"]) == len(dashboards.EXTERNAL_LIVE)


# ---------------------------------------------------------------------------
# Story 23.9: identity_complete_export_parquet_path /
# read_identity_complete_export_records / main() / publish_gist_from_tab
# ---------------------------------------------------------------------------


def _complete_export_row(**overrides: str) -> dict[str, str]:
    row = {
        "Core_Python_Package_Name": "pkg-a",
        "OpenTeams_Title": "[Conda-Forge Packaging] pkg-a",
        "identity_source": "inventory",
        "associator_key": "",
        "associator_status": "inventory-derived",
        "primary_purl": "pkg:pypi/pkg-a",
        "primary_type": "pypi",
        "alternative_purls": "",
        "cpes": "",
        "conda_purl": "",
        "source_repository_url": "",
        "OpenTeams_Issue_URL": "https://github.com/x/y/issues/1",
        "Conda-Forge_FeedStock_URL": "",
        "Conda-Forge_Metadata_URL": "",
        "Staged_Recipes_PR_URL": "",
        "Local_Recipes_URL": "",
        "Local_Build_Status": "",
        "Verification_Timestamp_UTC": "2026-08-30T00:00:00Z",
        "P": "P4",
        "Rank": "1",
        "Score": "80",
        "Package": "pkg-a",
        "Work": "Create recipe",
    }
    row.update(overrides)
    return row


def test_identity_complete_export_parquet_path_respects_data_root_env(monkeypatch, tmp_path):
    monkeypatch.setenv("PYFORGE_ATLAS_DATA_ROOT", str(tmp_path))

    path = identity.identity_complete_export_parquet_path()

    assert path == tmp_path / "derived/identity_complete_export/identity_complete_export.parquet"


def test_identity_complete_export_parquet_path_default_relative_to_atlas_project_dir(monkeypatch):
    monkeypatch.delenv("PYFORGE_ATLAS_DATA_ROOT", raising=False)

    path = identity.identity_complete_export_parquet_path()

    assert path == (
        identity.PYFORGE_ATLAS_PROJECT_DIR
        / "data/derived/identity_complete_export/identity_complete_export.parquet"
    )


def test_read_identity_complete_export_records_reads_parquet_and_stringifies_nulls(
    monkeypatch, tmp_path
):
    parquet_path = tmp_path / "identity_complete_export.parquet"
    df = pd.DataFrame(
        [
            _complete_export_row(P=pd.NA),
            _complete_export_row(Core_Python_Package_Name="pkg-b", Package="pkg-b"),
        ]
    )
    df.to_parquet(parquet_path)
    monkeypatch.setattr(identity, "identity_complete_export_parquet_path", lambda: parquet_path)

    records = identity.read_identity_complete_export_records()

    assert records is not None
    assert records[0]["P"] == ""
    assert records[1]["Core_Python_Package_Name"] == "pkg-b"


def test_read_identity_complete_export_records_missing_file_returns_none_and_names_it(
    monkeypatch, tmp_path, capsys
):
    missing = tmp_path / "no-bootstrap-yet" / "identity_complete_export.parquet"
    monkeypatch.setattr(identity, "identity_complete_export_parquet_path", lambda: missing)

    result = identity.read_identity_complete_export_records()

    assert result is None
    captured = capsys.readouterr()
    assert str(missing) in captured.err
    assert "pyforge-atlas-bootstrap" in captured.err


def test_xlsx_flag_exits_2_with_pointer(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "--xlsx", str(tmp_path / "book.xlsx"), "--skip-gist"],
    )
    rc = identity.main()
    assert rc == 2
    assert "Story 23.9" in capsys.readouterr().err


def test_main_reads_parquet_writes_csv_and_skips_gist(monkeypatch, tmp_path, capsys):
    parquet_path = tmp_path / "derived/identity_complete_export/identity_complete_export.parquet"
    parquet_path.parent.mkdir(parents=True)
    pd.DataFrame([_complete_export_row()]).to_parquet(parquet_path)
    (tmp_path / "recipes").mkdir()
    monkeypatch.setattr(identity, "identity_complete_export_parquet_path", lambda: parquet_path)
    monkeypatch.setattr(identity, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog", "--skip-gist"])

    rc = identity.main()

    assert rc == 0
    assert "Skipped gist publish (--skip-gist)" in capsys.readouterr().out


def _mock_identity_gist_render(monkeypatch):
    # `pyforge-atlas` is NOT a dependency of the `local-recipes` feature this
    # file runs under, so a bare import here is a hard ModuleNotFoundError
    # rather than a skip. Same idiom as the module-level
    # `pytest.importorskip("pandas")` above -- the two tests that need the
    # atlas dashboard skip cleanly in envs that do not carry it.
    identity_gist = pytest.importorskip("pyforge.atlas.dashboard.identity_gist")

    def _render(export_path, **kwargs):
        root = kwargs.get("repo_root") or identity.REPO_ROOT
        records = pd.read_parquet(export_path).to_dict(orient="records")
        identity.overlay_live_local(records, Path(root) / "recipes")
        body = "\n".join(
            f"{r.get('Core_Python_Package_Name', '')} {r.get('P', '')} {r.get('Local_Build_Status', '')}"
            for r in records
        )
        return body, "# dash\n"

    monkeypatch.setattr(identity_gist, "render_identity_gist_markdown", _render)


def test_main_default_path_overlay_runs_before_csv_write(monkeypatch, tmp_path, capsys):
    recipes_dir = tmp_path / "recipes"
    pkg_dir = recipes_dir / "pkg-a"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "recipe.yaml").write_text(
        "package:\n"
        "  name: pkg-a\n"
        "  version: '1.0'\n"
        "extra:\n"
        "  cfe-local-build-status: success\n",
        encoding="utf-8",
    )

    parquet_path = tmp_path / "derived/identity_complete_export/identity_complete_export.parquet"
    parquet_path.parent.mkdir(parents=True)
    pd.DataFrame(
        [_complete_export_row(Local_Recipes_URL="", Local_Build_Status="not-attempted")]
    ).to_parquet(parquet_path)
    output_csv = tmp_path / "identity.csv"
    monkeypatch.setattr(identity, "identity_complete_export_parquet_path", lambda: parquet_path)
    monkeypatch.setattr(identity, "REPO_ROOT", tmp_path)
    _mock_identity_gist_render(monkeypatch)
    monkeypatch.setattr(identity, "resolve_gist_id", lambda _cli: "fake-gist-id")
    monkeypatch.setattr(identity, "gh_bin", lambda: "gh")
    monkeypatch.setattr(dashboards, "write_ops_canvas", lambda *a, **k: None)
    monkeypatch.setattr(dashboards, "write_workbook_canvas", lambda *a, **k: None)
    published: dict = {}

    def _fake_publish_gist_files(gh, gist_id, identity_path, dashboard_path):
        published["identity_md"] = identity_path.read_text(encoding="utf-8")

    monkeypatch.setattr(identity, "publish_gist_files", _fake_publish_gist_files)
    monkeypatch.setattr(identity, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--output-csv",
            str(output_csv),
            "--cache-dir",
            str(tmp_path / "cache"),
        ],
    )

    rc = identity.main()

    assert rc == 0
    csv_rows = _read_csv_rows(output_csv)
    assert csv_rows[0]["Local_Build_Status"] == "success"
    assert "recipes/pkg-a" in csv_rows[0]["Local_Recipes_URL"]
    assert "pkg-a" in published["identity_md"]
    assert "success" in published["identity_md"]


def test_main_exits_nonzero_when_parquet_missing(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        identity, "identity_complete_export_parquet_path", lambda: tmp_path / "missing.parquet"
    )
    monkeypatch.setattr(sys, "argv", ["prog", "--skip-gist"])

    rc = identity.main()

    assert rc == 1
    assert "identity_complete_export not found" in capsys.readouterr().err


def test_publish_gist_from_tab_reads_complete_export(monkeypatch, tmp_path):
    parquet_path = tmp_path / "derived/identity_complete_export/identity_complete_export.parquet"
    parquet_path.parent.mkdir(parents=True)
    pd.DataFrame([_complete_export_row()]).to_parquet(parquet_path)
    (tmp_path / "recipes").mkdir()
    monkeypatch.setattr(identity, "identity_complete_export_parquet_path", lambda: parquet_path)
    monkeypatch.setattr(identity, "REPO_ROOT", tmp_path)
    _mock_identity_gist_render(monkeypatch)
    monkeypatch.setattr(identity, "resolve_gist_id", lambda _cli: "fake-gist-id")
    monkeypatch.setattr(identity, "gh_bin", lambda: "gh")
    monkeypatch.setattr(dashboards, "write_ops_canvas", lambda *a, **k: None)
    monkeypatch.setattr(dashboards, "write_workbook_canvas", lambda *a, **k: None)
    published: dict = {}
    monkeypatch.setattr(
        identity,
        "publish_gist_files",
        lambda gh, gist_id, identity_path, dashboard_path: published.update(
            gist_id=gist_id, identity_path=identity_path, dashboard_path=dashboard_path
        ),
    )
    monkeypatch.setattr(identity, "CACHE_DIR", tmp_path / "cache")

    rc = identity.publish_gist_from_tab(None)

    assert rc == 0
    assert published["gist_id"] == "fake-gist-id"
    md_text = published["identity_path"].read_text(encoding="utf-8")
    assert "pkg-a" in md_text
    assert "P4" in md_text


def test_publish_gist_from_tab_returns_1_when_export_missing(monkeypatch, tmp_path, capsys):
    missing = tmp_path / "missing.parquet"
    monkeypatch.setattr(identity, "identity_complete_export_parquet_path", lambda: missing)
    monkeypatch.setattr(identity, "resolve_gist_id", lambda _cli: "fake-gist-id")
    monkeypatch.setattr(identity, "gh_bin", lambda: "gh")

    rc = identity.publish_gist_from_tab(None)

    assert rc == 1
    assert "identity_complete_export not found" in capsys.readouterr().err


def test_dead_flags_removed_from_argparse():
    """Story 21.7 retires the associator/board/feedstock-outputs/staged-prs/
    recipes-dir fetch surface -- none of the flags that fed it should still
    be wired into argparse."""
    script_path = SCRIPTS_DIR / "conda-forge-packaging-inventory-operations_openteams_identity.py"
    proc = subprocess.run(
        [sys.executable, str(script_path), "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0
    for dead_flag in (
        "--tab-in",
        "--associator",
        "--refresh-associator",
        "--project-items",
        "--feedstock-outputs",
        "--staged-prs",
        "--staged-open-prs",
        "--recipes-dir",
        "--refresh-staged-prs",
    ):
        assert dead_flag not in proc.stdout, dead_flag


# ---------------------------------------------------------------------------
# Story 27.1 — rate limits, export reader, schema parity
# ---------------------------------------------------------------------------


def test_create_missing_issues_retries_secondary_rate_limit(monkeypatch):
    calls: list[str] = []
    rate_calls = {"n": 0}

    def fake_run(cmd, **kwargs):
        calls.append(cmd[1])
        if cmd[1] == "issue" and rate_calls["n"] < 2:
            rate_calls["n"] += 1
            raise subprocess.CalledProcessError(
                403, cmd, stderr="secondary rate limit exceeded"
            )
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout="https://github.com/OpenTeams-WFT-CDO/mgmt-wf-python-modernization/issues/99\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    sleeps: list[float] = []
    monkeypatch.setattr(identity.time, "sleep", sleeps.append)

    not_filed: list[tuple[str, str]] = []
    result = identity.create_missing_issues(
        "gh",
        [_row("retry-pkg")],
        board={},
        dry_run=False,
        not_filed=not_filed,
    )
    assert result == [("retry-pkg", "[Conda-Forge Packaging] retry-pkg")]
    assert not_filed == []
    assert calls == ["issue", "issue", "issue", "project"]
    # Every gh call is paced 0.25 s; each rate-limited answer backs off 2 s, then 4 s.
    assert sleeps == [0.25, 2.0, 0.25, 4.0, 0.25, 0.25]


def test_create_missing_issues_gives_up_after_the_retry_budget(monkeypatch):
    """A rate limit that never clears: one attempt plus five retries, backoff doubling
    from 2 s (62 s in all), then the name is reported as not filed -- never retried forever."""
    calls: list[str] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd[1])
        raise subprocess.CalledProcessError(1, cmd, stderr="You have exceeded a secondary rate limit")

    monkeypatch.setattr(subprocess, "run", fake_run)
    sleeps: list[float] = []
    monkeypatch.setattr(identity.time, "sleep", sleeps.append)

    not_filed: list[tuple[str, str]] = []
    board: dict[str, str] = {}
    row = _row("stuck-pkg")
    result = identity.create_missing_issues("gh", [row], board=board, dry_run=False, not_filed=not_filed)

    assert identity._GH_MAX_RETRIES + 1 == 6
    assert calls == ["issue"] * 6
    assert sleeps == [0.25, 2.0, 0.25, 4.0, 0.25, 8.0, 0.25, 16.0, 0.25, 32.0, 0.25]
    assert result == []
    assert not_filed == [("stuck-pkg", "[Conda-Forge Packaging] stuck-pkg")]
    assert board == {}
    assert not row.get("OpenTeams_Issue_URL")


def test_read_identity_export_corrupt_parquet_named_error(monkeypatch, tmp_path, capsys):
    bad = tmp_path / "bad.parquet"
    bad.write_bytes(b"not-parquet")
    monkeypatch.setattr(identity, "identity_complete_export_parquet_path", lambda: bad)
    assert identity.read_identity_complete_export_records() is None
    err = capsys.readouterr().err
    assert "identity_complete_export not found" in err or "unreadable" in err


def test_read_identity_export_stringifies_list_cells(monkeypatch, tmp_path):
    path = tmp_path / "identity_complete_export.parquet"
    pd.DataFrame(
        [{"Core_Python_Package_Name": "pkg-a", "alternative_purls": ["a", "b"], "P": "P4"}]
    ).to_parquet(path)
    monkeypatch.setattr(identity, "identity_complete_export_parquet_path", lambda: path)
    records = identity.read_identity_complete_export_records()
    assert records is not None
    assert records[0]["alternative_purls"] == "a; b"


def test_empty_pyforge_atlas_data_root_refused(monkeypatch, capsys):
    monkeypatch.setenv(identity.PYFORGE_ATLAS_DATA_ROOT_ENV, "")
    assert identity.identity_complete_export_parquet_path() is None
    assert "empty" in capsys.readouterr().err.lower()


def test_gist_only_refuses_empty_pyforge_atlas_data_root(monkeypatch, capsys):
    monkeypatch.setenv(identity.PYFORGE_ATLAS_DATA_ROOT_ENV, "")
    monkeypatch.setattr(sys, "argv", ["prog", "--gist-only", "--skip-gist"])
    rc = identity.main()
    err = capsys.readouterr().err.lower()
    assert rc == 1
    assert "unresolved" in err or "empty" in err


def test_create_missing_issues_retries_rate_limit_text_on_exit_code_one(monkeypatch):
    calls: list[str] = []
    rate_calls = {"n": 0}

    def fake_run(cmd, **kwargs):
        assert kwargs.get("capture_output") is True, "gh rate-limit detection needs stderr captured"
        calls.append(cmd[1])
        if cmd[1] == "issue" and rate_calls["n"] < 1:
            rate_calls["n"] += 1
            raise subprocess.CalledProcessError(
                1,
                cmd,
                stderr="You have exceeded a secondary rate limit",
            )
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout="https://github.com/OpenTeams-WFT-CDO/mgmt-wf-python-modernization/issues/42\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(identity.time, "sleep", lambda _s: None)

    result = identity.create_missing_issues(
        "gh",
        [_row("stderr-limit-pkg")],
        board={},
        dry_run=False,
    )
    assert result
    assert calls.count("issue") >= 2


def test_gist_columns_match_identity_export_contract():
    atlas_src = REPO_ROOT / "src/shared/packages/pyforge-atlas/src"
    if str(atlas_src) not in sys.path:
        sys.path.insert(0, str(atlas_src))
    from pyforge.atlas.pipelines.derived_artifacts.identity_export_contract import (
        GIST_COLUMNS as contract_cols,
    )

    assert list(contract_cols) == identity.GIST_COLUMNS


_EXPORT_TS = "2026-08-30T12:00:00Z"
_CORPUS_PATH = (
    REPO_ROOT / "src/shared/packages/pyforge-atlas/tests/fixtures/inventory_identity/complete_export_expected.json"
)


def _pipeline_export(tmp_path: Path, *, ts: str = _EXPORT_TS, **identity_overrides) -> Path:
    """Run Atlas's real ``build_identity_complete_export`` node over the frozen corpus and
    write its output where the export lives under a data root (DW-FU-21-7-4)."""
    atlas_src = REPO_ROOT / "src/shared/packages/pyforge-atlas/src"
    if str(atlas_src) not in sys.path:
        sys.path.insert(0, str(atlas_src))
    from pyforge.atlas.pipelines.derived_artifacts.nodes import (
        build_identity_complete_export,
    )

    corpus = json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))
    identity_rows = [dict(row, **identity_overrides) for row in corpus["identity_packages_primary"]]
    df = build_identity_complete_export(
        pd.DataFrame(identity_rows),
        pd.DataFrame(corpus["inventory_priority_assignments"]),
        pd.DataFrame(corpus.get("enterprise_jfrog_consumption") or []),
        pd.DataFrame([]),
        pd.DataFrame(corpus.get("inventory_verified_packages") or []),
        pd.DataFrame([]),
        pd.DataFrame([]),
        pd.DataFrame(corpus.get("inventory_universe") or []),
        {"identity_complete_export": {"verification_timestamp_utc": ts}},
    )
    export_path = tmp_path / "data/derived/identity_complete_export/identity_complete_export.parquet"
    export_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(export_path, index=False)
    return export_path


def test_pipeline_export_readable_by_quartet_reader(monkeypatch, tmp_path, capsys):
    export_path = _pipeline_export(tmp_path)
    monkeypatch.setattr(identity, "identity_complete_export_parquet_path", lambda: export_path)
    records = identity.read_identity_complete_export_records()
    assert records is not None
    assert records[0]["Verification_Timestamp_UTC"] == _EXPORT_TS
    assert records[0]["P"] == "P5"
    assert records[0]["Core_Python_Package_Name"] == "fixture-pkg"
    assert set(identity.GIST_COLUMNS) <= set(records[0])
    assert identity.IDENTITY_EXPORT_READ_WARNINGS == []
    assert "warning:" not in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Story 27.1 third review -- reader warnings (DW-FU-21-7-5 / DW-FU-21-7-7)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("column", ["Score", "Priority_Source", "JFROG_risk_level", "internal_lob_count"])
def test_reader_warns_on_absent_ranking_or_jfrog_column(monkeypatch, tmp_path, capsys, column):
    df = pd.read_parquet(_pipeline_export(tmp_path)).drop(columns=[column])
    path = tmp_path / "trimmed.parquet"
    df.to_parquet(path, index=False)
    monkeypatch.setattr(identity, "identity_complete_export_parquet_path", lambda: path)

    records = identity.read_identity_complete_export_records()

    assert records is not None
    msg = f"identity_complete_export: ranking column {column} absent from export"
    assert identity.IDENTITY_EXPORT_READ_WARNINGS == [msg]
    assert f"warning: {msg}" in capsys.readouterr().err


def test_reader_warns_on_rows_sharing_a_pep503_key_counting_every_row(monkeypatch, tmp_path, capsys):
    path = tmp_path / "dups.parquet"
    pd.DataFrame(
        [
            _complete_export_row(Core_Python_Package_Name="Foo_Bar", Package="Foo_Bar"),
            _complete_export_row(Core_Python_Package_Name="foo-bar", Package="foo-bar"),
            _complete_export_row(Core_Python_Package_Name="dup", Package="dup"),
            _complete_export_row(Core_Python_Package_Name="dup", Package="dup"),
            _complete_export_row(Core_Python_Package_Name="solo", Package="solo"),
        ]
    ).to_parquet(path, index=False)
    monkeypatch.setattr(identity, "identity_complete_export_parquet_path", lambda: path)

    records = identity.read_identity_complete_export_records()

    assert records is not None and len(records) == 5
    dup_warnings = [w for w in identity.IDENTITY_EXPORT_READ_WARNINGS if "duplicate" in w]
    assert dup_warnings == [
        "identity_complete_export: duplicate ranked rows normalize to foo-bar (2 rows): Foo_Bar, foo-bar",
        "identity_complete_export: duplicate ranked rows normalize to dup (2 rows): dup, dup",
    ]
    assert "solo" not in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Story 27.1 third review -- canvas directory resolution (DW-FU-17-2-2)
# ---------------------------------------------------------------------------


@pytest.fixture
def _no_canvas_dir(monkeypatch, tmp_path):
    monkeypatch.delenv(priority.INVENTORY_CANVAS_DIR_ENV, raising=False)
    missing_env_file = tmp_path / "absent.local.env"
    monkeypatch.setattr(priority, "LOCAL_ENV_PATH", missing_env_file)
    monkeypatch.setattr(dashboards._priority_mod, "LOCAL_ENV_PATH", missing_env_file)
    return missing_env_file


def test_resolve_canvas_dir_reads_env_then_local_env_then_unset(monkeypatch, tmp_path, _no_canvas_dir):
    assert priority.INVENTORY_CANVAS_DIR_ENV == "PYFORGE_INVENTORY_CANVAS_DIR"
    assert priority.resolve_canvas_dir() is None
    assert priority.default_ops_canvas_path() is None
    assert priority.default_workbook_canvas_path() is None

    env_file = tmp_path / "ops.local.env"
    env_file.write_text("# local\nPYFORGE_INVENTORY_CANVAS_DIR='/srv/canvases/from-file'\n", encoding="utf-8")
    monkeypatch.setattr(priority, "LOCAL_ENV_PATH", env_file)
    assert priority.resolve_canvas_dir() == Path("/srv/canvases/from-file")

    monkeypatch.setenv(priority.INVENTORY_CANVAS_DIR_ENV, "   ")
    assert priority.resolve_canvas_dir() == Path("/srv/canvases/from-file"), "blank env falls through"

    monkeypatch.setenv(priority.INVENTORY_CANVAS_DIR_ENV, str(tmp_path / "from-env"))
    assert priority.resolve_canvas_dir() == tmp_path / "from-env"
    assert priority.default_ops_canvas_path() == tmp_path / "from-env/identity-ops.canvas.tsx"
    assert priority.default_workbook_canvas_path() == tmp_path / "from-env/jfrog-workbook.canvas.tsx"


def test_no_canvas_default_points_under_a_home_directory():
    for script in (
        "conda-forge-packaging-inventory-operations_priority.py",
        "openteams_identity_dashboards.py",
        "conda-forge-packaging-inventory-operations_openteams_identity.py",
    ):
        text = (SCRIPTS_DIR / script).read_text(encoding="utf-8")
        assert "/home/" not in text and ".cursor/projects" not in text, script


def _canvas_spies(monkeypatch) -> tuple[list, list]:
    ops_calls: list = []
    workbook_calls: list = []
    monkeypatch.setattr(dashboards, "write_ops_canvas", lambda path, *a, **k: ops_calls.append(path))
    monkeypatch.setattr(dashboards, "write_workbook_canvas", lambda path, *a, **k: workbook_calls.append(path))
    return ops_calls, workbook_calls


def _export_stub(tmp_path: Path) -> Path:
    export_path = tmp_path / "derived/identity_complete_export/identity_complete_export.parquet"
    export_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"Core_Python_Package_Name": "pkg-a"}]).to_parquet(export_path)
    return export_path


def test_unset_canvas_dir_skips_both_canvas_writes_with_a_message(monkeypatch, tmp_path, capsys, _no_canvas_dir):
    monkeypatch.delenv(identity.INVENTORY_IDENTITY_UI_ENV, raising=False)
    ops_calls, workbook_calls = _canvas_spies(monkeypatch)

    identity.write_dashboard_markdown(
        tmp_path / "dash.md", "# dash\n", [{"Core_Python_Package_Name": "pkg-a"}], "tab", _export_stub(tmp_path)
    )

    out = capsys.readouterr().out
    assert "Skipped ops canvas write (PYFORGE_INVENTORY_CANVAS_DIR unset)" in out
    assert "Skipped workbook canvas write (PYFORGE_INVENTORY_CANVAS_DIR unset)" in out
    assert ops_calls == [] and workbook_calls == []
    assert (tmp_path / "dash.md").read_text(encoding="utf-8") == "# dash\n"


def test_canvas_dir_from_env_targets_both_canvases(monkeypatch, tmp_path, capsys, _no_canvas_dir):
    monkeypatch.delenv(identity.INVENTORY_IDENTITY_UI_ENV, raising=False)
    monkeypatch.setenv(priority.INVENTORY_CANVAS_DIR_ENV, str(tmp_path / "canvases"))
    ops_calls, workbook_calls = _canvas_spies(monkeypatch)

    identity.write_dashboard_markdown(
        tmp_path / "dash.md", "# dash\n", [{"Core_Python_Package_Name": "pkg-a"}], "tab", _export_stub(tmp_path)
    )

    assert ops_calls == [tmp_path / "canvases/identity-ops.canvas.tsx"]
    assert workbook_calls == [tmp_path / "canvases/jfrog-workbook.canvas.tsx"]
    assert "Skipped" not in capsys.readouterr().out


def _priority_main(monkeypatch, tmp_path: Path) -> int:
    assignments = tmp_path / "inventory_priority_assignments.parquet"
    pd.DataFrame(
        [{"core_python_package_name": "pkg-a", "P": "P4", "Rank": 1, "Score": 80, "Work": "Create recipe"}]
    ).to_parquet(assignments, index=False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "priority",
            "--priority-assignments",
            str(assignments),
            "--jfrog-parquet",
            str(tmp_path / "no-jfrog.parquet"),
            "--ranked-export",
            str(tmp_path / "ranked.parquet"),
        ],
    )
    return priority.main()


def test_priority_canvas_unset_skips_with_a_message(monkeypatch, tmp_path, capsys, _no_canvas_dir):
    monkeypatch.delenv(priority.INVENTORY_IDENTITY_UI_ENV, raising=False)
    assert _priority_main(monkeypatch, tmp_path) == 0
    assert "Skipped canvas write (PYFORGE_INVENTORY_CANVAS_DIR unset" in capsys.readouterr().out
    assert not list(tmp_path.rglob("*.canvas.tsx"))


def test_priority_canvas_defaults_under_the_env_canvas_dir(monkeypatch, tmp_path, _no_canvas_dir):
    monkeypatch.delenv(priority.INVENTORY_IDENTITY_UI_ENV, raising=False)
    monkeypatch.setenv(priority.INVENTORY_CANVAS_DIR_ENV, str(tmp_path / "canvases"))
    assert _priority_main(monkeypatch, tmp_path) == 0
    canvas = tmp_path / "canvases/identity-2026-08-20.canvas.tsx"
    assert canvas.read_text(encoding="utf-8").startswith(priority._CANVAS_PREFIX)


def test_identity_canvas_help_names_the_real_setting():
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "conda-forge-packaging-inventory-operations_openteams_identity.py"), "--help"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    help_text = "".join(proc.stdout.split())  # argparse wraps on spaces and hyphens
    assert "PYFORGE_INVENTORY_CANVAS_DIR" in help_text
    assert "conf/conda-forge-packaging-inventory-operations.local.env" in help_text
    assert "PYFORGE_ATLAS_CANVAS_DIR" not in help_text
    assert ".env.local" not in help_text


# ---------------------------------------------------------------------------
# Story 27.1 third review -- `?` buckets and unknown recipe types (DW-FU-17-2-3)
# ---------------------------------------------------------------------------


def test_ops_canvas_shows_unset_buckets_and_keeps_unknown_recipe_types(tmp_path):
    recipes_url = "https://github.com/rxm7706/local-recipes/tree/main/recipes/{}"
    records = [
        {
            "Core_Python_Package_Name": "known",
            "P": "P4",
            "Work": "Create recipe",
            "Local_Build_Status": "success",
            "Local_Recipes_URL": recipes_url.format("known"),
        },
        {"Core_Python_Package_Name": "unset", "P": "", "Work": "", "Local_Build_Status": ""},
        {
            "Core_Python_Package_Name": "oddtype",
            "P": "P9",
            "Work": "Already tracked",
            "Local_Build_Status": "failed",
            "Local_Recipes_URL": recipes_url.format("oddtype"),
        },
    ]
    helpers = types.SimpleNamespace(**vars(identity))
    helpers.overlay_live_local = lambda _records, _dir: None
    helpers.load_local_recipe_type = lambda _dir: {"known": "noarch-python", "oddtype": "rust-binary"}
    helpers.REPO_ROOT = tmp_path
    path = tmp_path / "identity-ops.canvas.tsx"

    dashboards.write_ops_canvas(path, records, "identity-fixture", helpers)

    data = _decode_data_blob(path.read_text(encoding="utf-8"), dashboards._CANVAS_PREFIX)
    assert data["priorityDefs"][-1] == ["?", "Unknown / unset priority", 1]
    assert data["workDefs"][-1] == ["?", "Unknown / unset work type", 1]
    assert [row[0] for row in data["priorityDefs"]] == [*identity.P_ORDER, "?"]
    assert [row[0] for row in data["buildByType"]] == ["noarch-python", "none", "rust-binary"]
    assert data["buildByType"][-1] == ["rust-binary", 1, 0, 0, 1, 0, 0]
    assert sum(row[1] for row in data["buildByType"]) == data["n"] == 3


# ---------------------------------------------------------------------------
# Story 27.1 third review -- one export timestamp (DW-FU-21-7) and AC 3(b)/(c)
# ---------------------------------------------------------------------------


def _gist_run_setup(monkeypatch, tmp_path: Path, export_path: Path) -> dict:
    (tmp_path / "recipes").mkdir(exist_ok=True)
    monkeypatch.setattr(identity, "identity_complete_export_parquet_path", lambda: export_path)
    monkeypatch.setattr(identity, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(identity, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(identity, "resolve_gist_id", lambda _cli: "fake-gist-id")
    monkeypatch.setattr(dashboards, "write_ops_canvas", lambda *a, **k: None)
    monkeypatch.setattr(dashboards, "write_workbook_canvas", lambda *a, **k: None)
    published: dict = {}

    def _fake_publish(gh, gist_id, identity_path, dashboard_path):
        published["gh"] = gh
        published["identity_md"] = identity_path.read_text(encoding="utf-8")
        published["dashboards_md"] = dashboard_path.read_text(encoding="utf-8")

    monkeypatch.setattr(identity, "publish_gist_files", _fake_publish)
    return published


def _gist_table_column(identity_md: str, column: str) -> list[str]:
    lines = identity_md.rsplit("\n## Identity rows\n", 1)[1].strip().splitlines()
    header = [c.strip() for c in lines[0].strip("|").split("|")]
    idx = header.index(column)
    return [re.split(r"(?<!\\)\|", line.strip().strip("|"))[idx].strip() for line in lines[2:] if line.strip()]


def test_gist_csv_and_tab_carry_the_one_export_timestamp(monkeypatch, tmp_path, capsys):
    pytest.importorskip("pyforge.atlas.dashboard.identity_gist")
    export_path = _pipeline_export(tmp_path)
    published = _gist_run_setup(monkeypatch, tmp_path, export_path)
    output_csv = tmp_path / "identity.csv"
    monkeypatch.setattr(sys, "argv", ["prog", "--output-csv", str(output_csv)])

    assert identity.main() == 0

    export_ts = set(pd.read_parquet(export_path)["Verification_Timestamp_UTC"])
    assert export_ts == {_EXPORT_TS}
    csv_ts = {row["Verification_Timestamp_UTC"] for row in _read_csv_rows(output_csv)}
    assert csv_ts == export_ts
    assert f"Verification_Timestamp_UTC: {_EXPORT_TS}" in capsys.readouterr().out
    identity_md = published["identity_md"]
    assert f"generated: {_EXPORT_TS}" in identity_md
    assert f"- Generated: `{_EXPORT_TS}`" in identity_md
    assert set(_gist_table_column(identity_md, "Verification_Timestamp_UTC")) == export_ts
    stamps = set(re.findall(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", published["dashboards_md"]))
    assert stamps == export_ts, "the dashboards companion carries only the export's timestamp"
    assert published["gh"] == _GH_SENTINEL


def test_blank_export_timestamp_raises_identity_gist_error(tmp_path):
    identity_gist = pytest.importorskip("pyforge.atlas.dashboard.identity_gist")
    export_path = _pipeline_export(tmp_path, ts="")
    with pytest.raises(identity_gist.IdentityGistError, match="refusing to publish gist with a synthetic timestamp"):
        identity_gist.render_identity_gist_markdown(export_path, gist_id="x", repo_root=tmp_path)


def test_blank_export_timestamp_refuses_the_dashboards_companion_too(monkeypatch, tmp_path):
    identity_gist = pytest.importorskip("pyforge.atlas.dashboard.identity_gist")
    export_path = _pipeline_export(tmp_path, ts="")
    monkeypatch.setattr(identity_gist, "_render_identity_catalog", lambda *a, **k: "")
    with pytest.raises(identity_gist.IdentityGistError, match="refusing dashboard companion with a synthetic timestamp"):
        identity_gist.render_identity_gist_markdown(export_path, gist_id="x", repo_root=tmp_path)


def test_blank_export_timestamp_makes_the_script_exit_1(monkeypatch, tmp_path, capsys):
    pytest.importorskip("pyforge.atlas.dashboard.identity_gist")
    export_path = _pipeline_export(tmp_path, ts="")
    published = _gist_run_setup(monkeypatch, tmp_path, export_path)
    monkeypatch.setattr(sys, "argv", ["prog", "--gist-only", "--skip-gist"])

    assert identity.main() == 1

    assert "missing Verification_Timestamp_UTC" in capsys.readouterr().err
    assert published == {}
    assert not (tmp_path / "cache" / identity.GIST_FILENAME).exists()


def test_list_valued_cell_renders_through_the_gist(monkeypatch, tmp_path):
    pytest.importorskip("pyforge.atlas.dashboard.identity_gist")
    export_path = _pipeline_export(tmp_path, alternative_purls=["pkg:pypi/fixture-pkg", "pkg:github/org/fixture-pkg"])
    assert list(pd.read_parquet(export_path)["alternative_purls"].iloc[0]) == [
        "pkg:pypi/fixture-pkg",
        "pkg:github/org/fixture-pkg",
    ]
    _gist_run_setup(monkeypatch, tmp_path, export_path)
    monkeypatch.setattr(sys, "argv", ["prog", "--gist-only", "--skip-gist"])

    assert identity.main() == 0

    identity_md = (tmp_path / "cache" / identity.GIST_FILENAME).read_text(encoding="utf-8")
    assert _gist_table_column(identity_md, "alternative_purls") == ["pkg:pypi/fixture-pkg; pkg:github/org/fixture-pkg"]


# ---------------------------------------------------------------------------
# Story 27.1 third review -- filed-but-not-added is labelled apart from not filed
# ---------------------------------------------------------------------------


def test_main_labels_filed_but_not_added_apart_from_could_not_file(monkeypatch, tmp_path, capsys):
    path = tmp_path / "identity_complete_export.parquet"
    pd.DataFrame(
        [
            _complete_export_row(
                Core_Python_Package_Name=name,
                Package=name,
                OpenTeams_Title=f"[Conda-Forge Packaging] {name}",
                OpenTeams_Issue_URL="",
            )
            for name in ("pkg-ok", "pkg-noadd", "pkg-fail")
        ]
    ).to_parquet(path, index=False)
    (tmp_path / "recipes").mkdir()
    monkeypatch.setattr(identity, "identity_complete_export_parquet_path", lambda: path)
    monkeypatch.setattr(identity, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(identity.time, "sleep", lambda _s: None)
    issue_base = "https://github.com/OpenTeams-WFT-CDO/mgmt-wf-python-modernization/issues/"
    numbers = {"pkg-ok": 1, "pkg-noadd": 2}

    def fake_run(cmd, **kwargs):
        assert cmd[0] == _GH_SENTINEL
        if cmd[1] == "issue":
            name = cmd[cmd.index("--title") + 1].rsplit(" ", 1)[-1]
            if name == "pkg-fail":
                raise subprocess.CalledProcessError(1, cmd, stderr="validation failed")
            return subprocess.CompletedProcess(cmd, 0, stdout=f"{issue_base}{numbers[name]}\n", stderr="")
        if cmd[cmd.index("--url") + 1].endswith("/2"):
            raise subprocess.CalledProcessError(1, cmd, stderr="project add failed")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["prog", "--create-issues", "--skip-gist"])

    assert identity.main() == 0

    captured = capsys.readouterr()
    assert "Created 1 missing OpenTeams issue(s):" in captured.out
    err = captured.err
    could_not = err.split("Could not file 1 OpenTeams issue(s):", 1)[1].split("Filed but not added", 1)[0]
    assert "pkg-fail: [Conda-Forge Packaging] pkg-fail" in could_not
    assert "pkg-noadd" not in could_not
    filed = err.split("Filed but not added to OpenTeams project 1 (1)", 1)[1]
    assert f"pkg-noadd: {issue_base}2" in filed
    assert "filed-but-not-added" not in err
