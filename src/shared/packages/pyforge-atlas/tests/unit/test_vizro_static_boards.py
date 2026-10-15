"""Story 30.2 (CAP-63): the Vizro producer job, the flag and the task -- no vizro needed.

AC8 reads ``.github/workflows/kedro-viz-publish.yml`` as YAML: the second job, ``vizro``, runs
``vizro-static-export`` in ``-e local-recipes`` and uploads ``docs/dashboard/vizro`` as the
``vizro-static-export`` artifact (90 days), never commits, and runs only on its own paths
through the ``changes`` job. The export itself is proven in
``tests/integration/dashboard/test_vizro_static_export.py``.
"""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

import pytest
import yaml
from pyforge.testing_kit.flags import flagd_tree

from pyforge.atlas import vizro_static_boards

REPO_ROOT = Path(__file__).resolve().parents[6]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "kedro-viz-publish.yml"
FLAGS = REPO_ROOT / "src" / "platform" / "config" / "flags.json"
OVERLAYS = REPO_ROOT / "src" / "platform" / "config" / "flag-overlays.json"
PIXI = REPO_ROOT / "pixi.toml"
TOOLS = REPO_ROOT / "src/shared/packages/pyforge-atlas/tools"
FLAG = "pyforge.atlas.vizro_static_boards"
VIZRO_PATHS = [
    "src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard",
    "src/shared/packages/pyforge-atlas/src/pyforge/atlas/semantic",
    "src/shared/packages/pyforge-atlas/conf/base/catalog.yml",
]

if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import vizro_static_export as cli  # noqa: E402


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _steps(job: dict) -> list[dict]:
    return [step for step in job["steps"] if isinstance(step, dict)]


def test_ac8_the_vizro_job_uploads_the_export_and_never_commits() -> None:
    document = _workflow()
    assert document["permissions"] == {"contents": "read"}
    job = document["jobs"]["vizro"]
    assert "PAUSE_KEDRO_VIZ_PUBLISH" in job["if"] and "PAUSE_ALL_CI" in job["if"]
    assert job["needs"] == "changes"
    assert "needs.changes.outputs.vizro == 'true'" in job["if"]

    steps = _steps(job)
    pixi = next(step for step in steps if "setup-pixi" in str(step.get("uses", "")))
    assert pixi["with"]["environments"].split() == ["local-recipes"]

    uploads = [step for step in steps if str(step.get("uses", "")).startswith("actions/upload-artifact")]
    assert len(uploads) == 1
    (upload,) = uploads
    assert upload["with"] == {"name": "vizro-static-export", "path": "docs/dashboard/vizro", "retention-days": 90}
    assert upload["if"] == "${{ steps.vizro_flag.outputs.enabled == 'true' }}"

    flag_step = next(step for step in steps if step.get("id") == "vizro_flag")
    assert "vizro_static_export.py --print-flag" in flag_step["run"].replace("\\\n", " ").replace("  ", " ")
    export = next(step for step in steps if "vizro-static-export" in step.get("run", ""))
    assert export["run"].strip() == "pixi run --frozen -e local-recipes vizro-static-export"
    assert export["if"] == upload["if"]


def test_ac8_no_job_commits_pushes_or_deploys() -> None:
    for name, job in _workflow()["jobs"].items():
        for step in _steps(job):
            run = step.get("run", "")
            for forbidden in ("git push", "git commit", "steward deploy", "deploy-pages"):
                assert forbidden not in run, f"{name}: {forbidden}"
            assert "deploy-pages" not in str(step.get("uses", ""))


def test_ac8_the_vizro_job_runs_on_its_own_paths() -> None:
    document = _workflow()
    on_block = document.get("on", document.get(True))
    trigger = on_block["push"]["paths"]
    for path in VIZRO_PATHS:
        assert path in trigger or f"{path}/**" in trigger, path
    changes = document["jobs"]["changes"]
    assert "PAUSE_KEDRO_VIZ_PUBLISH" in changes["if"]
    paths_step = next(step for step in _steps(changes) if step.get("id") == "paths")
    assert paths_step["env"]["VIZRO_PATHS"].split() == VIZRO_PATHS
    assert changes["outputs"]["vizro"] == "${{ steps.paths.outputs.vizro }}"
    # Every pathspec either producer filters on is in the workflow trigger.
    for spec in [*paths_step["env"]["VIZRO_PATHS"].split(), *paths_step["env"]["KEDRO_VIZ_PATHS"].split()]:
        assert spec in trigger or f"{spec}/**" in trigger, spec


def test_the_flag_is_in_the_tree_off_by_default_and_on_only_in_dev() -> None:
    entry = json.loads(FLAGS.read_text(encoding="utf-8"))["flags"][FLAG]
    assert entry["defaultVariant"] == "off"
    assert entry["variants"] == {"on": True, "off": False}
    assert entry["metadata"]["owner"] == "atlas"
    assert entry["metadata"]["story"] == "30-2-vizro-boards-publish-as-static-exports-under-dashboard-vizro"
    overlays = json.loads(OVERLAYS.read_text(encoding="utf-8"))
    assert {env: overlays[env][FLAG] for env in ("dev", "staging", "production")} == {
        "dev": "on",
        "staging": "off",
        "production": "off",
    }
    assert vizro_static_boards.FLAG_KEY == FLAG


@pytest.mark.parametrize(("variant", "expected"), [("on", True), ("off", False)])
def test_boards_enabled_reads_the_tree(tmp_path: Path, variant: str, expected: bool) -> None:
    tree = flagd_tree(tmp_path, {FLAG: variant})
    assert vizro_static_boards.boards_enabled(flags_path=str(tree)) is expected


def test_the_task_flag_off_refuses_before_importing_the_dashboard(tmp_path: Path, capsys) -> None:
    out = tmp_path / "vizro"
    tree = flagd_tree(tmp_path, {FLAG: "off"})
    assert cli.main(["--out", str(out), "--flags-path", str(tree)]) == 2
    assert f"flag {FLAG} is off" in capsys.readouterr().err
    assert not out.exists()


def test_the_pixi_task_runs_the_tool_in_local_recipes_with_the_serve_pythonpath() -> None:
    tasks = tomllib.loads(PIXI.read_text(encoding="utf-8"))["feature"]["local-recipes"]["tasks"]
    task = tasks["vizro-static-export"]
    assert task["cmd"] == "python src/shared/packages/pyforge-atlas/tools/vizro_static_export.py"
    assert task["env"]["PYTHONPATH"] == tasks["dashboard-serve"]["env"]["PYTHONPATH"]
