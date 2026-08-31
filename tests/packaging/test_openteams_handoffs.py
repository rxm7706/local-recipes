"""Offline unit tests for Story 17.2 ("handoffs are execution-ready") and
Story 21.7 ("quartet thin-out and gist wrapper"):

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
4. `identity_export_parquet_path` / `read_identity_export_records` /
   `merge_ranking_columns` / `main()` / `publish_gist_from_tab` in
   `conda-forge-packaging-inventory-operations_openteams_identity.py`
   (Story 21.7) -- the identity script reads the Atlas Phase D
   `identity_export_parquet` instead of live-fetching ASSOCIATOR_URL/board/
   feedstock-outputs/staged-prs; `--gist-only` merges ranking columns from
   the ranked identity tab by name.

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

# pandas ships alongside openpyxl only under -e local-recipes (Story 21.7's
# identity_export_parquet read); the importorskip above already halts
# collection under the lean pyforge-ci env before this import is reached.
import pandas as pd  # noqa: E402

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
    assert "--ops-canvas" in proc.stdout
    assert "--workbook-canvas" in proc.stdout


def test_blank_package_name_is_skipped(monkeypatch):
    """A row with a blank/missing Core_Python_Package_Name must never reach
    `gh issue create` -- it would mint a garbage `[Conda-Forge Packaging] `
    title."""
    calls: list = []
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: calls.append(a) or "unexpected")
    monkeypatch.setattr(subprocess, "check_call", lambda *a, **k: calls.append(a) or 0)

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
    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("gh vanished")),
    )
    monkeypatch.setattr(subprocess, "check_call", lambda *a, **k: 0)

    result = identity.create_missing_issues("gh", [_row("some-pkg")], board={}, dry_run=False)
    assert result == []  # issue-create itself failed; nothing to report as created


def test_project_item_add_failure_does_not_mark_row_as_tracked(monkeypatch):
    """If `gh issue create` succeeds but `gh project item-add` fails, the row
    must NOT be marked tracked (OpenTeams_Issue_URL / board), so a future
    Atlas Phase D run's own board join (Story 21.7: this script no longer
    performs that join itself) still sees it as missing and retries the
    project-add step -- otherwise it is silently done forever."""
    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda *a, **k: "https://github.com/OpenTeams-WFT-CDO/mgmt-wf-python-modernization/issues/42\n",
    )
    monkeypatch.setattr(
        subprocess,
        "check_call",
        lambda *a, **k: (_ for _ in ()).throw(subprocess.CalledProcessError(1, a)),
    )

    row = _row("some-pkg")
    board: dict[str, str] = {}
    result = identity.create_missing_issues("gh", [row], board=board, dry_run=False)

    # Still reported as created (the issue really was created) ...
    assert result == [("some-pkg", "[Conda-Forge Packaging] some-pkg")]
    # ... but NOT merged into the row or the board, so it is retried next run.
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
    monkeypatch.setattr(dashboards, "render", lambda *a, **k: "# stub dashboard markdown\n")
    monkeypatch.setattr(
        dashboards, "write_ops_canvas", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("ops boom"))
    )
    monkeypatch.setattr(
        dashboards,
        "write_workbook_canvas",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("workbook boom")),
    )

    dash_path = tmp_path / "dashboards.md"
    identity.write_dashboard_markdown(
        dash_path, [], tmp_path / "missing.xlsx", "gist-id-123", "identity-2026-08-20"
    )

    assert dash_path.read_text(encoding="utf-8") == "# stub dashboard markdown\n"


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


# ---------------------------------------------------------------------------
# Story 21.7: identity_export_parquet_path / read_identity_export_records /
# merge_ranking_columns / main() / publish_gist_from_tab
# (conda-forge-packaging-inventory-operations_openteams_identity.py)
# ---------------------------------------------------------------------------


def test_identity_export_parquet_path_respects_data_root_env(monkeypatch, tmp_path):
    monkeypatch.setenv("PYFORGE_ATLAS_DATA_ROOT", str(tmp_path))

    path = identity.identity_export_parquet_path()

    assert path == tmp_path / "derived/identity_export_parquet/identity_export_parquet.parquet"


def test_identity_export_parquet_path_default_relative_to_atlas_project_dir(monkeypatch):
    monkeypatch.delenv("PYFORGE_ATLAS_DATA_ROOT", raising=False)

    path = identity.identity_export_parquet_path()

    assert path == (
        identity.PYFORGE_ATLAS_PROJECT_DIR
        / "data/derived/identity_export_parquet/identity_export_parquet.parquet"
    )


def test_read_identity_export_records_reads_parquet_and_stringifies_nulls(
    monkeypatch, tmp_path
):
    parquet_path = tmp_path / "identity_export_parquet.parquet"
    df = pd.DataFrame(
        [
            {"Core_Python_Package_Name": "pkg-a", "identity_source": "purl-associator", "P": pd.NA},
            {"Core_Python_Package_Name": "pkg-b", "identity_source": "inventory", "P": pd.NA},
        ]
    )
    df.to_parquet(parquet_path)
    monkeypatch.setattr(identity, "identity_export_parquet_path", lambda: parquet_path)

    records = identity.read_identity_export_records()

    assert records == [
        {"Core_Python_Package_Name": "pkg-a", "identity_source": "purl-associator", "P": ""},
        {"Core_Python_Package_Name": "pkg-b", "identity_source": "inventory", "P": ""},
    ]


def test_read_identity_export_records_missing_file_returns_none_and_names_it(
    monkeypatch, tmp_path, capsys
):
    missing = tmp_path / "no-bootstrap-yet" / "identity_export_parquet.parquet"
    monkeypatch.setattr(identity, "identity_export_parquet_path", lambda: missing)

    result = identity.read_identity_export_records()

    assert result is None
    captured = capsys.readouterr()
    assert str(missing) in captured.err
    assert "pyforge-atlas-bootstrap" in captured.err


def test_merge_ranking_columns_merges_by_name_and_warns_on_a_miss(capsys):
    identity_records = [
        {"Core_Python_Package_Name": "pkg-a", "identity_source": "inventory"},
        {"Core_Python_Package_Name": "pkg-b", "identity_source": "purl-associator"},
    ]
    ranked_records = [
        {
            "Core_Python_Package_Name": "pkg-a",
            "P": "P4",
            "Rank": "1",
            "Score": "80",
            "Work": "Create recipe",
        }
    ]

    merged = identity.merge_ranking_columns(identity_records, ranked_records)

    assert [r["Core_Python_Package_Name"] for r in merged] == ["pkg-a"]
    assert merged[0]["P"] == "P4"
    assert merged[0]["Work"] == "Create recipe"
    assert merged[0]["identity_source"] == "inventory"  # identity column untouched
    captured = capsys.readouterr()
    assert "pkg-b" in captured.err
    assert "No ranking match" in captured.err


def test_merge_ranking_columns_never_raises_on_a_total_miss():
    merged = identity.merge_ranking_columns(
        [{"Core_Python_Package_Name": "pkg-z"}],
        [
            {
                "Core_Python_Package_Name": "pkg-y",
                "P": "P1",
                "Rank": "1",
                "Score": "1",
                "Work": "Already tracked",
            }
        ],
    )
    assert merged == []


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


def test_main_reads_parquet_writes_tab_and_skips_gist(monkeypatch, tmp_path, capsys):
    from openpyxl import Workbook

    xlsx_path = tmp_path / "Analysis_Dataset.xlsx"
    Workbook().save(xlsx_path)

    parquet_path = tmp_path / "identity_export_parquet.parquet"
    df = pd.DataFrame(
        [
            {
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
            }
        ]
    )
    df.to_parquet(parquet_path)
    (tmp_path / "recipes").mkdir()
    monkeypatch.setattr(identity, "identity_export_parquet_path", lambda: parquet_path)
    # Hermetic: main() unconditionally calls overlay_live_local(records,
    # REPO_ROOT / "recipes"); without this, it would scan this actual
    # repository's real recipes/ tree instead of the empty fixture dir above.
    monkeypatch.setattr(identity, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog", "--xlsx", str(xlsx_path), "--skip-gist"])

    rc = identity.main()

    assert rc == 0
    rows = identity.read_xlsx_tab(xlsx_path, identity.TAB_OUT)
    assert [r["Core_Python_Package_Name"] for r in rows] == ["pkg-a"]
    assert rows[0]["identity_source"] == "inventory"
    assert "Skipped gist publish (--skip-gist)" in capsys.readouterr().out


def test_main_default_path_overlay_runs_before_tab_and_csv_write(
    monkeypatch, tmp_path, capsys
):
    """Story 21.7 review pass 1 regression: main()'s default (non-`--skip-gist`)
    path must overlay the live recipes/ tree ONCE, before the xlsx tab / CSV
    are persisted -- not only later, inside write_gist_markdown's own internal
    overlay_live_local call for the gist step. Plants a real
    recipes/pkg-a/recipe.yaml whose CFE build-status stamp differs from the
    Parquet fixture's Local_Build_Status/Local_Recipes_URL, then asserts the
    xlsx tab (and the CSV, and what the mocked gist publish would have sent)
    all already carry the live-scanned value -- not the stale Parquet one.
    Before the Code Map fix, the tab/CSV were written pre-overlay and only the
    later write_gist_markdown call mutated `records` in place, so the gist
    could silently disagree with what was already persisted to disk."""
    from openpyxl import Workbook

    xlsx_path = tmp_path / "Analysis_Dataset.xlsx"
    Workbook().save(xlsx_path)
    output_csv = tmp_path / "identity.csv"

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

    parquet_path = tmp_path / "identity_export_parquet.parquet"
    df = pd.DataFrame(
        [
            {
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
                # Deliberately stale/blank vs. the live recipes/ tree planted
                # above -- if main() forgot to overlay before persisting, these
                # are the values that would end up on disk.
                "Local_Recipes_URL": "",
                "Local_Build_Status": "not-attempted",
                "Verification_Timestamp_UTC": "2026-08-30T00:00:00Z",
            }
        ]
    )
    df.to_parquet(parquet_path)
    monkeypatch.setattr(identity, "identity_export_parquet_path", lambda: parquet_path)
    monkeypatch.setattr(identity, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(identity, "resolve_gist_id", lambda _cli: "fake-gist-id")
    monkeypatch.setattr(identity, "gh_bin", lambda: "gh")
    monkeypatch.setattr(dashboards, "render", lambda *a, **k: "# stub dashboard\n")
    monkeypatch.setattr(dashboards, "write_ops_canvas", lambda *a, **k: None)
    monkeypatch.setattr(dashboards, "write_workbook_canvas", lambda *a, **k: None)
    published: dict = {}

    def _fake_publish_gist_files(gh, gist_id, identity_path, dashboard_path):
        published["identity_md"] = identity_path.read_text(encoding="utf-8")

    monkeypatch.setattr(identity, "publish_gist_files", _fake_publish_gist_files)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--xlsx",
            str(xlsx_path),
            "--output-csv",
            str(output_csv),
            "--cache-dir",
            str(tmp_path / "cache"),
        ],
    )

    rc = identity.main()

    assert rc == 0
    # The persisted xlsx tab already reflects the live-scanned overlay -- not
    # the stale Parquet-fixture value -- by the time it was written.
    rows = identity.read_xlsx_tab(xlsx_path, identity.TAB_OUT)
    assert rows[0]["Local_Build_Status"] == "success"
    assert "recipes/pkg-a" in rows[0]["Local_Recipes_URL"]
    # The CSV agrees.
    csv_rows = _read_csv_rows(output_csv)
    assert csv_rows[0]["Local_Build_Status"] == "success"
    assert "recipes/pkg-a" in csv_rows[0]["Local_Recipes_URL"]
    # ... and so does what the (mocked) gist publish would have sent -- the
    # same live-scanned value, never the pre-overlay one.
    assert "success" in published["identity_md"]


def test_main_exits_nonzero_when_parquet_missing(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        identity, "identity_export_parquet_path", lambda: tmp_path / "missing.parquet"
    )
    monkeypatch.setattr(
        sys, "argv", ["prog", "--xlsx", str(tmp_path / "x.xlsx"), "--skip-gist"]
    )

    rc = identity.main()

    assert rc == 1
    assert "identity_export_parquet not found" in capsys.readouterr().err


def test_publish_gist_from_tab_merges_ranking_and_never_falls_back_to_a_live_fetch(
    monkeypatch, tmp_path
):
    """--gist-only reads the Parquet for identity/overlay columns and merges
    ranking columns from the ranked tab by name (I/O & Edge-Case Matrix
    "steady state" row) -- never a direct HTTP/GraphQL call."""
    from openpyxl import Workbook

    xlsx_path = tmp_path / "Analysis_Dataset.xlsx"
    wb = Workbook()
    wb.active.title = identity.TAB_OUT
    ws = wb[identity.TAB_OUT]
    ws.append(["Core_Python_Package_Name", "P", "Rank", "Score", "Work"])
    ws.append(["pkg-a", "P4", "1", "80", "Create recipe"])
    wb.save(xlsx_path)

    parquet_path = tmp_path / "identity_export_parquet.parquet"
    pd.DataFrame(
        [{"Core_Python_Package_Name": "pkg-a", "identity_source": "inventory"}]
    ).to_parquet(parquet_path)
    (tmp_path / "recipes").mkdir()
    monkeypatch.setattr(identity, "identity_export_parquet_path", lambda: parquet_path)
    # Hermetic: write_gist_markdown (called internally below) always calls
    # overlay_live_local(records, REPO_ROOT / "recipes"); without this, it
    # would scan this actual repository's real recipes/ tree instead of the
    # empty fixture dir above.
    monkeypatch.setattr(identity, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(identity, "resolve_gist_id", lambda _cli: "fake-gist-id")
    monkeypatch.setattr(identity, "gh_bin", lambda: "gh")
    monkeypatch.setattr(dashboards, "render", lambda *a, **k: "# stub dashboard\n")
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

    rc = identity.publish_gist_from_tab(xlsx_path, None)

    assert rc == 0
    assert published["gist_id"] == "fake-gist-id"
    md_text = published["identity_path"].read_text(encoding="utf-8")
    assert "pkg-a" in md_text
    assert "P4" in md_text


def test_publish_gist_from_tab_returns_1_when_tab_missing_ranking_columns(
    monkeypatch, tmp_path, capsys
):
    """I/O & Edge-Case Matrix: `--gist-only`, tab missing ranking columns
    (`priority.py` never ran) -- must return 1 with the existing error
    message, unchanged from before this story. The ranked tab carries only
    identity columns (no P/Rank/Score/Work), so `publish_gist_from_tab`
    must fail on the missing-columns check before ever touching the
    identity Parquet."""
    from openpyxl import Workbook

    xlsx_path = tmp_path / "Analysis_Dataset.xlsx"
    wb = Workbook()
    wb.active.title = identity.TAB_OUT
    ws = wb[identity.TAB_OUT]
    ws.append(["Core_Python_Package_Name", "identity_source"])
    ws.append(["pkg-a", "inventory"])
    wb.save(xlsx_path)

    monkeypatch.setattr(identity, "resolve_gist_id", lambda _cli: "fake-gist-id")
    monkeypatch.setattr(identity, "gh_bin", lambda: "gh")

    def _fail_if_called():
        raise AssertionError(
            "identity_export_parquet must not be read once the ranked-tab "
            "columns check has already failed"
        )

    monkeypatch.setattr(identity, "identity_export_parquet_path", _fail_if_called)

    rc = identity.publish_gist_from_tab(xlsx_path, None)

    assert rc == 1
    assert "Identity tab is missing ranking columns" in capsys.readouterr().err
