"""Story 30.2 (CAP-63): the Vizro producer job, the flag and the task -- no vizro needed.

AC8 reads ``.github/workflows/kedro-viz-publish.yml`` as YAML: the second job, ``vizro``, runs
``vizro-static-export`` in ``-e pyforge-atlas`` (orchestrator ruling 2026-10-15) and uploads ``docs/dashboard/vizro`` as the
``vizro-static-export`` artifact (90 days), never commits, and runs only on its own paths
through the ``changes`` job. The export itself is proven in
``tests/integration/dashboard/test_vizro_static_export.py``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

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
    assert pixi["with"]["environments"].split() == ["pyforge-atlas"]

    uploads = [step for step in steps if str(step.get("uses", "")).startswith("actions/upload-artifact")]
    assert len(uploads) == 1
    (upload,) = uploads
    assert upload["with"] == {"name": "vizro-static-export", "path": "docs/dashboard/vizro", "retention-days": 90}
    assert upload["if"] == "${{ steps.vizro_flag.outputs.enabled == 'true' }}"

    flag_step = next(step for step in steps if step.get("id") == "vizro_flag")
    assert "vizro_static_export.py --print-flag" in flag_step["run"].replace("\\\n", " ").replace("  ", " ")
    export = next(step for step in steps if "vizro-static-export" in step.get("run", ""))
    assert export["run"].strip() == "pixi run --frozen -e pyforge-atlas vizro-static-export --clock now"
    checkout = next(step for step in steps if str(step.get("uses", "")).startswith("actions/checkout"))
    assert checkout["with"]["persist-credentials"] is False  # Story 37.2: the token never stays in .git/config
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
    # A `git diff` error runs the producer: --quiet's exit code is read, never empty output.
    assert "git diff --quiet" in paths_step["run"] and "rc=$?" in paths_step["run"]
    assert "--name-only" not in paths_step["run"]
    # Every pathspec either producer filters on is in the workflow trigger.
    for spec in [*paths_step["env"]["VIZRO_PATHS"].split(), *paths_step["env"]["KEDRO_VIZ_PATHS"].split()]:
        assert spec in trigger or f"{spec}/**" in trigger, spec


# --- Story 37.2 (CAP-63 amended 2026-10-19): the public data build, weekly -----------------------------


def test_the_vizro_job_builds_the_public_data_before_it_exports() -> None:
    steps = _steps(_workflow()["jobs"]["vizro"])
    names = [step.get("name", "") for step in steps]
    build = next(step for step in steps if step.get("name") == "Build the public atlas data")
    export = next(step for step in steps if "vizro-static-export" in step.get("run", ""))
    flag = next(step for step in steps if step.get("id") == "vizro_flag")

    room = next(step for step in steps if step.get("name") == "Free disk space for the data build")
    assert (
        names.index(flag["name"]) < names.index(room["name"]) < names.index(build["name"]) < names.index(export["name"])
    )
    assert build["if"] == export["if"] == room["if"]  # flag off: no build and no export
    (removal,) = [line for line in room["run"].splitlines() if "rm -rf" in line]
    targets = removal.split("rm -rf", 1)[1].split()
    assert "/usr/share/dotnet" in targets
    assert all(
        t.startswith(("/usr/", "/opt/")) and len(t.rstrip("/").split("/")) >= 3 for t in targets
    )  # never /usr or /opt
    assert _workflow()["jobs"]["vizro"]["timeout-minutes"] == 240  # three times the measured build
    # Story 38.1: semantic_packages builds inside the bootstrap's one DAG, never as a step after it
    assert build["run"].split("\n")[0] == "pixi run --frozen -e pyforge-atlas pyforge-atlas-bootstrap"
    assert "--pipelines semantic_packages" not in build["run"]
    assert "continue-on-error" not in build  # a failed build fails the job; Pages keeps its last export


def test_the_vizro_job_runs_public_sources_only() -> None:
    job = _workflow()["jobs"]["vizro"]
    text = yaml.safe_dump(job)  # the parsed job: comments are not in it
    assert "secrets." not in text and "PYFORGE_ATLAS_CREDENTIALED" not in text
    assert "GITHUB_TOKEN" not in text and "GH_TOKEN" not in text and "PHASE_P" not in text
    assert all("env" not in step for step in _steps(job) if step.get("name") == "Build the public atlas data")


def test_the_bootstrap_task_runs_the_fetch_pipelines_with_the_semantic_store_and_never_the_estate_cache() -> None:
    task = tomllib.loads(PIXI.read_text(encoding="utf-8"))["feature"]["pyforge-atlas"]["tasks"][
        "pyforge-atlas-bootstrap"
    ]
    pipelines = task["cmd"].split("--pipelines ", 1)[1].split()[0].split(",")
    assert pipelines == [
        "core",
        "pypi_intelligence",
        "vulnerability",
        "vcs_health",
        "upstream_discovery",
        "derived_artifacts",
        "seed_gaps",
        "artifactory_downloads",
        "semantic_packages",  # Story 38.1: it and derived_artifacts read each other's outputs
    ]
    assert task["cwd"] == "src/shared/packages/pyforge-atlas"


def test_the_workflow_rebuilds_weekly_and_still_on_push_and_dispatch() -> None:
    document = _workflow()
    on_block = document.get("on", document.get(True))
    assert set(on_block) == {"push", "schedule", "workflow_dispatch"}
    (entry,) = on_block["schedule"]
    minute, hour, day_of_month, month, day_of_week = entry["cron"].split()
    assert (day_of_month, month) == ("*", "*") and day_of_week.isdigit()  # once a week
    assert minute.isdigit() and hour.isdigit()


# --- Story 37.12 (CAP-63, CAP-64): the last-good copies persist between Pages runs ----------------------------

MEMBER = "src/shared/packages/pyforge-atlas"
DATA_ROOT = f"{MEMBER}/data"
# `stores/*` beside `!stores/vdb`, never `stores`: actions/cache globs with implicitDescendants false and tar
# recurses into a listed directory, so an exclusion under a listed `stores` would archive the 9.6 GB vdb store.
LAST_GOOD_PATHS = [f"{DATA_ROOT}/raw", f"{DATA_ROOT}/stores/*", f"!{DATA_ROOT}/stores/vdb"]
CACHE_KEY = "pyforge-atlas-last-good-${{ github.run_id }}"
CACHE_PREFIX = "pyforge-atlas-last-good-"
GLOBALS = REPO_ROOT / MEMBER / "conf" / "base" / "globals.yml"
CATALOG = REPO_ROOT / MEMBER / "conf" / "base" / "catalog.yml"


def _cache_step(kind: str) -> dict:
    (step,) = [
        step
        for step in _steps(_workflow()["jobs"]["vizro"])
        if str(step.get("uses", "")).startswith(f"actions/cache/{kind}@")
    ]
    return step


def _data_root_paths() -> dict[str, str]:
    """``globals.yml``'s ``paths``, each resolved with no env override, as the job runs them."""
    paths = yaml.safe_load(GLOBALS.read_text(encoding="utf-8"))["paths"]
    data_root = paths["data_root"]
    assert data_root == "${env_or:PYFORGE_ATLAS_DATA_ROOT,data}"  # the member's data/, the root the build writes
    return {key: str(value).replace("${paths.data_root}", "data") for key, value in paths.items()} | {
        "data_root": "data"
    }


def _resolved_filepath(entry: dict, paths: dict[str, str]) -> str:
    filepath = str(entry.get("filepath", ""))
    for key, value in paths.items():
        filepath = filepath.replace(f"${{globals:paths.{key}}}", value)
    if filepath.startswith("${runtime_params:"):
        filepath = filepath.split(",", 1)[1].rstrip("}")  # the default a run without the param writes
    return filepath


def test_the_vizro_job_restores_the_last_good_copies_before_the_build_and_saves_them_after() -> None:
    steps = _steps(_workflow()["jobs"]["vizro"])
    names = [step.get("name", "") for step in steps]
    restore, save = _cache_step("restore"), _cache_step("save")
    build = next(step for step in steps if step.get("name") == "Build the public atlas data")
    export = next(step for step in steps if "vizro-static-export" in step.get("run", ""))
    room = next(step for step in steps if step.get("name") == "Free disk space for the data build")
    flag = next(step for step in steps if step.get("id") == "vizro_flag")
    order = [names.index(step["name"]) for step in (flag, room, restore, build, save, export)]
    assert order == sorted(order), names  # restored before the build reads it, saved before the export can fail
    assert restore["uses"] == "actions/cache/restore@v6" and save["uses"] == "actions/cache/save@v6"
    # The build's own gate: flag off, nothing restored or saved; no always()/failure(), so a failed build saves
    # nothing and still fails the job.
    assert restore["if"] == save["if"] == build["if"] == "${{ steps.vizro_flag.outputs.enabled == 'true' }}"
    assert "continue-on-error" not in build and "continue-on-error" not in save
    assert [s for s in steps if "actions/cache" in str(s.get("uses", ""))] == [restore, save]


def test_the_restore_and_the_save_name_the_same_paths_and_key() -> None:
    restore, save = _cache_step("restore")["with"], _cache_step("save")["with"]
    # actions/cache hashes the path list into the entry's version: a save under other paths is never restored.
    assert restore["path"].splitlines() == save["path"].splitlines() == LAST_GOOD_PATHS
    assert restore["key"] == save["key"] == CACHE_KEY  # one entry per run
    assert restore["restore-keys"].split() == [CACHE_PREFIX]  # the newest entry a run before this one saved
    assert CACHE_KEY.startswith(CACHE_PREFIX)
    assert set(restore) == {"path", "key", "restore-keys"}  # no fail-on-cache-miss: a miss is the fresh root
    assert set(save) == {"path", "key"}


def test_only_last_good_copies_persist_never_the_vdb_store_or_a_pipeline_output() -> None:
    includes = [path for path in LAST_GOOD_PATHS if not path.startswith("!")]
    excludes = [path[1:] for path in LAST_GOOD_PATHS if path.startswith("!")]
    assert excludes == [f"{DATA_ROOT}/stores/vdb"]
    assert _data_root_paths()["vdb_store"] == "data/stores/vdb"
    # Each exclusion's parent is listed by its children (`<parent>/*`), never as itself, or tar would recurse into it.
    for excluded in excludes:
        parent = excluded.rsplit("/", 1)[0]
        assert f"{parent}/*" in includes and parent not in includes and DATA_ROOT not in includes
    for layer in ("intermediate", "primary", "derived", "cache"):
        assert not any(path.startswith(f"{DATA_ROOT}/{layer}") for path in includes), layer


def test_the_cached_paths_are_the_data_root_the_build_writes() -> None:
    task = tomllib.loads(PIXI.read_text(encoding="utf-8"))["feature"]["pyforge-atlas"]["tasks"][
        "pyforge-atlas-bootstrap"
    ]
    assert task["cwd"] == MEMBER  # Kedro resolves `data` against the member directory
    assert _data_root_paths()["data_root"] == "data"
    job = _workflow()["jobs"]["vizro"]
    assert "PYFORGE_ATLAS_DATA_ROOT" not in yaml.safe_dump(job)  # an override would move the data off the cache


def test_every_last_good_store_under_the_data_root_is_cached() -> None:
    """A raw-layer entry keeps its last-good copy (and AD-13 marker) under its own path: every one under the data
    root lies under a cached path, the vdb store the one exclusion, and no output layer lies under one."""
    paths = _data_root_paths()
    catalog = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
    cached, excluded = ("data/raw/", "data/stores/"), "data/stores/vdb"
    raw_under_root: list[str] = []
    for name, entry in catalog.items():
        if not isinstance(entry, dict):
            continue
        filepath = _resolved_filepath(entry, paths)
        if not filepath.startswith("data/"):
            continue  # seeds, conf files and the recipes tree are tracked, not run state
        layer = (entry.get("metadata") or {}).get("layer")
        if layer == "raw":
            raw_under_root.append(name)
            if filepath == excluded:
                assert name == "vulnerability_vdb_store"
            else:
                assert filepath.startswith(cached), (name, filepath)
        else:
            assert not filepath.startswith(cached), (name, filepath)  # an output never persists
    assert {"vulnerability_cisa_kev_raw", "core_s3_download_stats_raw", "pypi_conda_map_store"} <= set(raw_under_root)


def test_no_pull_request_can_write_a_cache_main_restores() -> None:
    on_block = _workflow().get("on", _workflow().get(True))
    assert not {"pull_request", "pull_request_target"} & set(on_block)


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


def test_boards_enabled_reads_the_tree(tmp_path: Path) -> None:
    on = flagd_tree(tmp_path, {FLAG: "on"}, name="on.json")
    off = flagd_tree(tmp_path, {FLAG: "off"}, name="off.json")
    assert vizro_static_boards.boards_enabled(flags_path=str(on)) is True
    assert vizro_static_boards.boards_enabled(flags_path=str(off)) is False


def test_the_task_flag_off_refuses_before_importing_the_dashboard(tmp_path: Path, capsys) -> None:
    out = tmp_path / "vizro"
    tree = flagd_tree(tmp_path, {FLAG: "off"})
    assert cli.main(["--out", str(out), "--flags-path", str(tree)]) == 2
    assert f"flag {FLAG} is off" in capsys.readouterr().err
    assert not out.exists()


def test_flag_off_never_imports_the_dashboard_or_vizro(tmp_path: Path) -> None:
    """In a fresh interpreter: with the flag off, the task returns before ``dashboard.static_export``
    (and so vizro) is ever imported."""
    tree = flagd_tree(tmp_path, {FLAG: "off"})
    probe = (
        "import sys\n"
        f"sys.path.insert(0, {str(TOOLS)!r})\n"
        "import vizro_static_export as cli\n"
        f"code = cli.main(['--out', {str(tmp_path / 'vizro')!r}, '--flags-path', {str(tree)!r}])\n"
        "loaded = sorted(m for m in sys.modules if m == 'vizro' or m.startswith(('vizro.', 'pyforge.atlas.dashboard')))\n"
        "print(code, loaded)\n"
    )
    env = {k: v for k, v in os.environ.items() if k != "PYTEST_ADDOPTS"}
    proc = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, env=env, check=False)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "2 []"


def test_the_pixi_task_runs_the_tool_in_pyforge_atlas() -> None:
    """Orchestrator ruling 2026-10-15: the export runs in pyforge-atlas (vizro + plotly), not local-recipes."""
    features = tomllib.loads(PIXI.read_text(encoding="utf-8"))["feature"]
    task = features["pyforge-atlas"]["tasks"]["vizro-static-export"]
    assert task["cmd"] == "python src/shared/packages/pyforge-atlas/tools/vizro_static_export.py"
    assert "vizro-static-export" not in features["local-recipes"]["tasks"]


def test_every_producer_job_carries_its_own_render_marker() -> None:
    """``ci_surface_gates --render`` finds a job's ``if:`` by its marker; ``publish`` once carried the
    workflow row's id and would have gained a second ``if:`` when the row went live."""
    text = WORKFLOW.read_text(encoding="utf-8")
    for job in ("changes", "publish", "vizro"):
        assert f"  {job}:\n    # ci-surfaces: kedro-viz-publish.{job}\n" in text, job
