"""Story 30.1 (CAP-62): Kedro-Viz export as workflow artifact and manifest."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml
from pyforge.testing_kit.flags import flag_states

from pyforge.atlas.viz_export_artifact import FLAG_KEY

REPO_ROOT = Path(__file__).resolve().parents[6]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "kedro-viz-publish.yml"
STAGED_RELATIVE = Path("docs/dashboard/kedro-viz")
# AC4 compares the workflow with its shape at the story's baseline_revision (e134549afc). The baseline
# is pinned here, not read with `git show`: CI checks out one commit (`fetch-depth: 1`), so the old
# revision is not there to read and the test died with CalledProcessError on PR #2236.
BASELINE_ON_BLOCK = {
    "push": {
        "branches": ["main"],
        "paths": [
            "src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/**",
            "src/shared/packages/pyforge-atlas/conf/base/catalog.yml",
            "src/shared/packages/pyforge-atlas/conf/base/globals.yml",
            "src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/**",
        ],
    },
    "workflow_dispatch": None,
}
# Story 30.2 (CAP-63) adds the Vizro producer to this workflow. GitHub filters paths per
# workflow, not per job, so `on.push.paths` grows by the Vizro paths, and the `changes` job
# keeps the publish job on exactly the baseline paths above (asserted below).
VIZRO_TRIGGER_PATHS = [
    "src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/**",
    "src/shared/packages/pyforge-atlas/src/pyforge/atlas/semantic/**",
]
CI_SURFACES = REPO_ROOT / "docs/governance/ci-surfaces.yaml"
README = REPO_ROOT / "docs/dashboard/README.md"

_TOOLS = REPO_ROOT / "src/shared/packages/pyforge-atlas/tools"
if str(_TOOLS) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_TOOLS))
import viz_manifest  # noqa: E402


def _load_workflow() -> dict:
    assert WORKFLOW.is_file()
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _workflow_on(document: dict) -> dict:
    block = document.get("on")
    if block is None:
        block = document.get(True)
    assert isinstance(block, dict)
    return block


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
    widened = {
        "push": {
            "branches": BASELINE_ON_BLOCK["push"]["branches"],
            "paths": [*BASELINE_ON_BLOCK["push"]["paths"], *VIZRO_TRIGGER_PATHS],
        },
        "workflow_dispatch": None,
        # Story 37.2: the weekly public data build (operator ruling 2026-10-19, "Weekly + on push")
        "schedule": [{"cron": "17 5 * * 1"}],
    }
    assert on_block == widened
    assert "workflow_dispatch" in on_block

    job = document["jobs"]["publish"]
    assert "PAUSE_KEDRO_VIZ_PUBLISH" in job["if"]
    # The publish job still runs on the baseline paths alone (Story 30.2's `changes` job).
    assert job["needs"] == "changes"
    assert "needs.changes.outputs.kedro_viz == 'true'" in job["if"]
    paths_step = next(s for s in document["jobs"]["changes"]["steps"] if s.get("id") == "paths")
    kedro_viz_pathspecs = paths_step["env"]["KEDRO_VIZ_PATHS"].split()
    assert kedro_viz_pathspecs == [path.removesuffix("/**") for path in BASELINE_ON_BLOCK["push"]["paths"]]

    steps = job["steps"]
    run_text = "\n".join(step.get("run", "") for step in steps if isinstance(step, dict))
    for forbidden in (
        "steward deploy dashboard",
        "git checkout -B main",
        "git config user.name",
        "git push",
    ):
        assert forbidden not in run_text

    # The stub-credentials step stays. Story 32.1 (fix under CAP-62) replaced the two-key heredoc this test pinned
    # by digest since Story 30.1, which had drifted from the catalog's eight keys, with tools/bootstrap.py's one
    # list; test_viz_publish_build.py pins that source and the absence of a list here.
    stub = next(s for s in steps if isinstance(s, dict) and "Materialize stub credentials" in s.get("name", ""))
    assert "tools/bootstrap.py --credentials-only" in stub["run"]

    pixi = next(s for s in steps if isinstance(s, dict) and "setup-pixi" in str(s.get("uses", "")))
    envs = pixi["with"]["environments"]
    assert "pyforge-atlas" in envs
    assert "pyforge-steward" not in envs

    uploads = [s for s in steps if isinstance(s, dict) and str(s.get("uses", "")).startswith("actions/upload-artifact")]
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
    # AC5 left the state as the story found it; moving it from paused-manually to live is the operator's step the
    # spec names (done 2026-10-16, with the workflow re-enabled), so either state is valid, and nothing else is.
    assert row["state"] in {"paused-manually", "live"}


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
