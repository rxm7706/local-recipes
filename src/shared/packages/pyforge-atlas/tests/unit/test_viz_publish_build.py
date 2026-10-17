"""Story 32.1 (fix under CAP-62): the DAG export builds in CI, and a failed build fails its task.

kedro-viz-publish.yml run 39002722593 failed because the workflow carried its own stub credentials list, two of
the eight keys conf/base/catalog.yml named at the time, and `viz-build` read green because `kedro viz build` exits 0
when its build fails. These tests keep the stub's one source (tools/bootstrap.py's CREDENTIAL_KEYS) equal to the
catalog, keep the workflow off a list of its own, keep every atlas tool the workflow runs in the env that carries
`pyforge.atlas`, and pin the check that fails `viz-build` on an incomplete build.
Offline, fixture-free reads of tracked files, plus tmp_path writes only (NFR-1).
"""

from __future__ import annotations

import inspect
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[6]
MEMBER_DIR = REPO_ROOT / "src" / "shared" / "packages" / "pyforge-atlas"
CONF_BASE = MEMBER_DIR / "conf" / "base"
# Kedro's default catalog patterns (`catalog*`, `catalog*/**`, `**/catalog*`; settings.py keeps them) load every
# catalog file under conf/base, so the key walk reads all of them, not only catalog.yml.
# `**/catalog*.y*ml` covers `catalog*` and `**/catalog*`; `**/catalog*/**/*.y*ml` covers files inside a `catalog*/` folder.
CATALOG_GLOBS = ("**/catalog*.y*ml", "**/catalog*/**/*.y*ml")
CATALOG_GLOB = " + ".join(CATALOG_GLOBS)
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "kedro-viz-publish.yml"
PIXI_TOML = REPO_ROOT / "pixi.toml"
TOOLS = MEMBER_DIR / "tools"
VIZ_BUILD_CHECK = TOOLS / "viz_build_check.py"
STUB_STEP_NAME = "Materialize stub credentials for offline catalog resolution"

if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import bootstrap  # noqa: E402
import viz_build_check  # noqa: E402

_RAW_CREDENTIALS_LINE = re.compile(r"^\s+credentials:\s*([A-Za-z_][A-Za-z0-9_-]*)\s*(?:#.*)?$", re.MULTILINE)


def _walk_credentials(node: Any, found: set[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "credentials" and isinstance(value, str):
                found.add(value)
            else:
                _walk_credentials(value, found)
    elif isinstance(node, list):
        for item in node:
            _walk_credentials(item, found)


def _catalog_files() -> list[Path]:
    files = sorted({path for pattern in CATALOG_GLOBS for path in CONF_BASE.glob(pattern) if path.is_file()})
    assert CONF_BASE / "catalog.yml" in files, f"{CATALOG_GLOB} under conf/base found no catalog.yml: {files}"
    return files


def _catalog_credential_keys() -> set[str]:
    found: set[str] = set()
    for catalog in _catalog_files():
        _walk_credentials(yaml.safe_load(catalog.read_text(encoding="utf-8")), found)
    return found


def _catalog_credential_keys_scanned() -> set[str]:
    found: set[str] = set()
    for catalog in _catalog_files():
        found |= set(_RAW_CREDENTIALS_LINE.findall(catalog.read_text(encoding="utf-8")))
    return found


def _workflow() -> dict[str, Any]:
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _all_run_texts(document: dict[str, Any]) -> list[tuple[str, str, str]]:
    runs = []
    for job_id, job in document["jobs"].items():
        for step in job.get("steps", []):
            if isinstance(step, dict) and "run" in step:
                runs.append((job_id, str(step.get("name", "")), str(step["run"])))
    return runs


def _all_strings(node: Any, where: str = "") -> list[tuple[str, str]]:
    """Every string key and value of the parsed workflow, with its path (comments are gone after safe_load)."""
    found: list[tuple[str, str]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{where}.{key}"
            if isinstance(key, str):
                found.append((here, key))
            found.extend(_all_strings(value, here))
    elif isinstance(node, list):
        for i, item in enumerate(node):
            found.extend(_all_strings(item, f"{where}[{i}]"))
    elif isinstance(node, str):
        found.append((where, node))
    return found


# ---------------------------------------------------------------------------------------------------------------------
# One source, complete (AC1, AC3)
# ---------------------------------------------------------------------------------------------------------------------


def test_catalog_reading_is_not_blind() -> None:
    """The YAML walk and a raw-text scan of the catalog agree, and both find keys."""
    walked = _catalog_credential_keys()
    scanned = _catalog_credential_keys_scanned()
    assert walked, f"found no `credentials:` key in conf/base/{CATALOG_GLOB}"
    assert walked == scanned


def test_stub_names_every_catalog_credential_key() -> None:
    catalog_keys = _catalog_credential_keys()
    stub_keys = set(bootstrap.CREDENTIAL_KEYS)
    missing = sorted(catalog_keys - stub_keys)
    extra = sorted(stub_keys - catalog_keys)
    assert not missing, (
        f"conf/base/{CATALOG_GLOB} names credential key(s) {missing} that tools/bootstrap.py's CREDENTIAL_KEYS lacks: "
        "kedro viz build and kedro run fail with 'Unable to find credentials' on a fresh clone and in CI"
    )
    assert not extra, f"tools/bootstrap.py's CREDENTIAL_KEYS names key(s) {extra} the catalog no longer names"


def test_stub_writes_every_key_as_an_empty_mapping() -> None:
    assert len(bootstrap.CREDENTIAL_KEYS) == len(set(bootstrap.CREDENTIAL_KEYS))
    assert yaml.safe_load(bootstrap._CREDENTIALS_STUB) == {key: {} for key in bootstrap.CREDENTIAL_KEYS}


def _point_bootstrap_at(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(bootstrap, "_MEMBER_ROOT", tmp_path)
    monkeypatch.delenv("PYFORGE_ATLAS_DATA_ROOT", raising=False)
    return tmp_path / "conf" / "local" / "credentials.yml"


def test_credentials_only_writes_the_stub_and_nothing_else(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    creds = _point_bootstrap_at(tmp_path, monkeypatch)
    assert bootstrap.main(["--credentials-only"]) == 0
    assert creds.read_text(encoding="utf-8") == bootstrap._CREDENTIALS_STUB
    created = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    assert created == ["conf", "conf/local", "conf/local/credentials.yml"], (
        f"--credentials-only must create the stub and its parents only, no store directory: {created}"
    )
    assert not (tmp_path / "data").exists()


def test_credentials_only_fills_a_zero_byte_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    creds = _point_bootstrap_at(tmp_path, monkeypatch)
    creds.parent.mkdir(parents=True)
    creds.write_bytes(b"")
    assert bootstrap.main(["--credentials-only"]) == 0
    assert creds.read_text(encoding="utf-8") == bootstrap._CREDENTIALS_STUB


def test_credentials_only_never_overwrites_a_non_empty_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    creds = _point_bootstrap_at(tmp_path, monkeypatch)
    creds.parent.mkdir(parents=True)
    original = b"github_token: an-operator-value\n"
    creds.write_bytes(original)
    assert bootstrap.main(["--credentials-only"]) == 0
    assert creds.read_bytes() == original


def test_bare_bootstrap_still_makes_the_store_dirs_and_the_stub(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    creds = _point_bootstrap_at(tmp_path, monkeypatch)
    assert bootstrap.main([]) == 0
    assert creds.read_text(encoding="utf-8") == bootstrap._CREDENTIALS_STUB
    assert (tmp_path / "data" / "stores" / "vdb").is_dir()
    assert (tmp_path / "data" / "stores" / "osv").is_dir()


# ---------------------------------------------------------------------------------------------------------------------
# The workflow reads the one source, carries no list, and runs atlas's tools in atlas's env (AC2, AC3, AC6)
# ---------------------------------------------------------------------------------------------------------------------


def test_workflow_writes_the_stub_through_bootstrap_before_the_build() -> None:
    steps = _workflow()["jobs"]["publish"]["steps"]
    names = [str(step.get("name", "")) for step in steps if isinstance(step, dict)]
    stub_index = names.index(STUB_STEP_NAME)
    stage_index = next(i for i, step in enumerate(steps) if "viz-publish-stage" in str(step.get("run", "")))
    assert stub_index < stage_index
    run = steps[stub_index]["run"]
    assert "src/shared/packages/pyforge-atlas/tools/bootstrap.py --credentials-only" in run
    assert "pixi run --frozen -e pyforge-atlas python" in run


def test_workflow_carries_no_credentials_list_of_its_own() -> None:
    """No string anywhere in the workflow (a `run:`, an `env:`, a `with:`, a key) names a credential key or the file."""
    keys = _catalog_credential_keys() | set(bootstrap.CREDENTIAL_KEYS)
    offenders = []
    for where, text in _all_strings(_workflow()):
        named = sorted(key for key in keys if re.search(rf"\b{re.escape(key)}\b", text))
        if named or "credentials.yml" in text:
            offenders.append(f"{where}: keys {named}, names credentials.yml: {'credentials.yml' in text}")
    assert not offenders, (
        "kedro-viz-publish.yml must write its stub only through tools/bootstrap.py --credentials-only, never from "
        f"a list of its own: {offenders}"
    )


_PIXI_PYTHON_TOOL = re.compile(
    r"pixi run\b(?P<flags>[^\n]*?)\bpython\s+(?P<tool>\S*src/shared/packages/pyforge-atlas/tools/[^\s/]+\.py)"
)
_ATLAS_ENV = re.compile(r"(?:^|\s)(?:-e|--environment)[ =]pyforge-atlas(?:\s|$)")


def test_every_atlas_tool_step_runs_in_the_atlas_env() -> None:
    """An atlas tool imports `pyforge.atlas`, which only `pyforge-atlas` carries (`pyforge-guild` deliberately not)."""
    calls = []
    for job_id, name, run in _all_run_texts(_workflow()):
        joined = re.sub(r"\\\n\s*", " ", run)  # fold shell line continuations
        for match in _PIXI_PYTHON_TOOL.finditer(joined):
            calls.append((job_id, name, Path(match.group("tool")).name, match.group("flags").strip()))
    found = {tool for _, _, tool, _ in calls}
    assert {"bootstrap.py", "print_viz_export_flag.py", "vizro_static_export.py"} <= found, found
    wrong = [
        f"{job} / {name!r}: {tool} runs with `{flags}`"
        for job, name, tool, flags in calls
        if not _ATLAS_ENV.search(flags)
    ]
    assert not wrong, f"every pixi-run atlas tool step must name -e pyforge-atlas: {wrong}"


# ---------------------------------------------------------------------------------------------------------------------
# viz-build fails when the build fails (AC4)
# ---------------------------------------------------------------------------------------------------------------------


def _atlas_tasks() -> dict[str, Any]:
    return tomllib.loads(PIXI_TOML.read_text(encoding="utf-8"))["feature"]["pyforge-atlas"]["tasks"]


def test_viz_build_task_checks_its_output_after_the_build() -> None:
    tasks = _atlas_tasks()
    viz_build = tasks["viz-build"]
    assert [part.strip() for part in viz_build["cmd"].split("&&")] == [
        "rm -rf build",
        "kedro viz build",
        "python tools/viz_build_check.py",
    ]
    assert viz_build["cwd"] == "src/shared/packages/pyforge-atlas"
    assert (REPO_ROOT / viz_build["cwd"] / "tools" / "viz_build_check.py").is_file()
    assert tasks["viz-publish-stage"]["depends-on"] == ["viz-build"]


def _complete_build(build_dir: Path) -> None:
    for rel in viz_build_check.REQUIRED_OUTPUTS:
        path = build_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")


def test_required_outputs_pin() -> None:
    """A pin: the three files, in the order the deployer writes them; the next test reads kedro-viz itself."""
    assert viz_build_check.REQUIRED_OUTPUTS == ("api/main", "index.html", "api/deploy-viz-metadata")


def test_required_outputs_match_the_kedro_viz_deployer() -> None:
    base_deployer = pytest.importorskip("kedro_viz.integrations.deployment.base_deployer")
    save_responses = pytest.importorskip("kedro_viz.api.rest.responses.save_responses")
    main, index, metadata = viz_build_check.REQUIRED_OUTPUTS
    assert base_deployer._METADATA_PATH == metadata
    assert (base_deployer._HTML_DIR / index).is_file(), "the deployer's static upload carries no index.html"
    assert "{path}/" + main in inspect.getsource(save_responses.save_api_responses_to_fs)
    deploy = inspect.getsource(base_deployer.BaseDeployer.deploy)
    calls = ("_upload_api_responses(", "_upload_static_files(", "_upload_deploy_viz_metadata_file(")
    positions = [deploy.index(call) for call in calls]
    assert positions == sorted(positions), "the deployer no longer writes the metadata file last"


def test_check_passes_on_a_complete_build(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _complete_build(tmp_path)
    assert viz_build_check.main(["--build-dir", str(tmp_path)]) == 0
    assert "build complete" in capsys.readouterr().out


@pytest.mark.parametrize("build_exists", [True, False], ids=["empty-build-dir", "no-build-dir"])
def test_check_fails_naming_every_missing_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], build_exists: bool
) -> None:
    build_dir = tmp_path / "build"
    if build_exists:
        build_dir.mkdir()
    assert viz_build_check.main(["--build-dir", str(build_dir)]) == 1
    err = capsys.readouterr().err
    for rel in viz_build_check.REQUIRED_OUTPUTS:
        assert rel in err
    assert "Unable to find credentials" in err and "`<key>: {}`" in err


@pytest.mark.parametrize("absent", ["api/main", "index.html", "api/deploy-viz-metadata"])
def test_check_fails_on_a_partial_build(tmp_path: Path, capsys: pytest.CaptureFixture[str], absent: str) -> None:
    _complete_build(tmp_path)
    (tmp_path / absent).unlink()
    assert viz_build_check.main(["--build-dir", str(tmp_path)]) == 1
    assert viz_build_check.missing_outputs(tmp_path) == [absent]
    assert f"missing: {absent}." in capsys.readouterr().err


def test_check_exits_non_zero_as_a_script(tmp_path: Path) -> None:
    """The task runs the file as a script: its process exit code, not just main()'s return, is the verdict."""
    proc = subprocess.run(
        [sys.executable, str(VIZ_BUILD_CHECK), "--build-dir", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1, proc.stderr
    _complete_build(tmp_path)
    proc = subprocess.run(
        [sys.executable, str(VIZ_BUILD_CHECK), "--build-dir", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
