"""Story 30.1 (CAP-62): Kedro-Viz export as workflow artifact and manifest."""

from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml

from pyforge.atlas.viz_export_artifact import FLAG_KEY
from pyforge.testing_kit.flags import flag_states

REPO_ROOT = Path(__file__).resolve().parents[6]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "kedro-viz-publish.yml"
BASELINE_REVISION = "e134549afcbdcc5b55b35f291464ac60d6685243"
STAGED_RELATIVE = Path("docs/dashboard/kedro-viz")
CI_SURFACES = REPO_ROOT / "docs/governance/ci-surfaces.yaml"
README = REPO_ROOT / "docs/dashboard/README.md"

_TOOLS = REPO_ROOT / "src/shared/packages/pyforge-atlas/tools"
if str(_TOOLS) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_TOOLS))
import viz_manifest  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _ensure_kedro_viz_untracked_from_index() -> None:
    """Re-apply index removals; other tests may refresh the index from HEAD."""
    subprocess.run(
        ["git", "rm", "-r", "--cached", "docs/dashboard/kedro-viz"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )


def _load_workflow() -> dict:
    assert WORKFLOW.is_file()
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _workflow_on(document: dict) -> dict:
    block = document.get("on")
    if block is None:
        block = document.get(True)
    assert isinstance(block, dict)
    return block


def _baseline_on_block() -> dict:
    proc = subprocess.run(
        ["git", "show", f"{BASELINE_REVISION}:.github/workflows/kedro-viz-publish.yml"],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO_ROOT,
    )
    baseline = yaml.safe_load(proc.stdout)
    return _workflow_on(baseline)


def test_ac1_kedro_viz_export_not_tracked_and_gitignored() -> None:
    proc = subprocess.run(
        ["git", "ls-files", "docs/dashboard/kedro-viz"],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO_ROOT,
    )
    assert proc.stdout.strip() == ""
    ignore = subprocess.run(
        ["git", "check-ignore", "docs/dashboard/kedro-viz/index.html"],
        cwd=REPO_ROOT,
    )
    assert ignore.returncode == 0


def test_ac4_kedro_viz_publish_workflow_shape() -> None:
    document = _load_workflow()
    assert document["permissions"]["contents"] == "read"
    assert "write" not in document.get("permissions", {})
    on_block = _workflow_on(document)
    assert on_block == _baseline_on_block()
    assert "workflow_dispatch" in on_block

    job = document["jobs"]["publish"]
    assert "PAUSE_KEDRO_VIZ_PUBLISH" in job["if"]

    steps = job["steps"]
    run_text = "\n".join(step.get("run", "") for step in steps if isinstance(step, dict))
    for forbidden in (
        "steward deploy dashboard",
        "git checkout -B main",
        "git config user.name",
        "git push",
    ):
        assert forbidden not in run_text

    stub = next(
        s
        for s in steps
        if isinstance(s, dict) and "Materialize stub credentials" in s.get("name", "")
    )
    assert "credentials.yml" in stub["run"]
    assert "bigquery_adc" in stub["run"] and "github_token" in stub["run"]

    pixi = next(s for s in steps if isinstance(s, dict) and "setup-pixi" in str(s.get("uses", "")))
    envs = pixi["with"]["environments"]
    assert "pyforge-atlas" in envs
    assert "pyforge-steward" not in envs

    uploads = [
        s
        for s in steps
        if isinstance(s, dict) and str(s.get("uses", "")).startswith("actions/upload-artifact")
    ]
    assert len(uploads) == 1
    upload = uploads[0]
    assert upload["with"]["name"] == "kedro-viz-export"
    assert upload["with"]["retention-days"] == 90
    assert upload["with"]["path"] == "docs/dashboard/kedro-viz/"
    assert "viz_export_flag.outputs.enabled" in upload["if"]


def test_ac5_ci_surfaces_kedro_viz_publish_switch() -> None:
    document = yaml.safe_load(CI_SURFACES.read_text(encoding="utf-8"))
    rows = document["surfaces"] if isinstance(document, dict) else document
    row = next(r for r in rows if r["id"] == "kedro-viz-publish")
    assert row["switch"] == "PAUSE_KEDRO_VIZ_PUBLISH"
    assert row["switch_class"] == "pause"
    assert row["state"] == "paused-manually"


def test_ac6_readme_names_artifact_and_manifest() -> None:
    text = README.read_text(encoding="utf-8")
    assert "kedro-viz-export" in text
    assert "manifest.json" in text
    assert "steward deploy dashboard" not in text


def _fixture_staged(tmp_path: Path) -> Path:
    staged = tmp_path / "build"
    metadata = staged / "api"
    metadata.mkdir(parents=True)
    (metadata / "deploy-viz-metadata").write_text(
        json.dumps({"timestamp": "unset", "version": "12.1.0"}) + "\n",
        encoding="utf-8",
    )
    (staged / "index.html").write_text("<html></html>\n", encoding="utf-8")
    return staged


@flag_states(FLAG_KEY)
def test_ac7_manifest_tool_respects_flag(
    tmp_path: Path, flag_provider: dict[str, bool], monkeypatch: pytest.MonkeyPatch
) -> None:
    staged = _fixture_staged(tmp_path)
    sha = "a" * 40
    monkeypatch.setenv("GITHUB_SHA", sha)

    def fake_committer_date(commit: str) -> str:
        assert commit == sha
        return "2026-10-14T12:00:00Z"

    monkeypatch.setattr(viz_manifest, "_committer_date_iso_utc", fake_committer_date)

    flag_on = flag_provider[FLAG_KEY]
    before = {p.relative_to(staged) for p in staged.rglob("*") if p.is_file()}
    assert viz_manifest.write_manifest(staged, flag_on=flag_on, export_commit=sha) == 0
    manifest = staged / "manifest.json"
    if not flag_on:
        assert not manifest.exists()
        after = {p.relative_to(staged) for p in staged.rglob("*") if p.is_file()}
        assert before == after
        return
    assert manifest.is_file()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert set(payload) == {"export_commit", "export_date", "kedro_viz_version"}
    assert payload["export_commit"] == sha
    assert payload["export_date"] == "2026-10-14T12:00:00Z"
    assert payload["kedro_viz_version"] == "12.1.0"


def test_matrix_invalid_sha_exits(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    staged = _fixture_staged(tmp_path)
    with pytest.raises(SystemExit) as exc:
        viz_manifest.write_manifest(staged, flag_on=True, export_commit="abc")
    assert exc.value.code == 1
    assert "40-hex" in capsys.readouterr().err


def test_matrix_missing_metadata_exits(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    staged = tmp_path / "empty"
    staged.mkdir()
    with pytest.raises(SystemExit) as exc:
        viz_manifest.write_manifest(staged, flag_on=True, export_commit="b" * 40)
    assert exc.value.code == 1
    assert "deploy-viz-metadata" in capsys.readouterr().err
