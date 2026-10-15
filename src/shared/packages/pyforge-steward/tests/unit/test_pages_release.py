"""Story 102.5 (CAP-168): configure-pages is authoritative on every host, and the deployed site ships
as the ``pages-site.zip`` asset of the rolling ``pages-site`` pre-release.

AC1 and AC2 read ``.github/workflows/pages.yml`` as YAML; AC6 reads the protected-refs rulesets.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from pyforge.steward import pages

REPO_ROOT = Path(__file__).resolve().parents[6]
PAGES_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pages.yml"
PROTECTED_REFS = REPO_ROOT / "docs" / "governance" / "rulesets" / "protected-refs.json"


def _workflow() -> dict:
    return yaml.safe_load(PAGES_WORKFLOW.read_text(encoding="utf-8"))


def _steps(job: str) -> list[dict]:
    return [step for step in _workflow()["jobs"][job]["steps"] if isinstance(step, dict)]


# --- AC1: the host env -------------------------------------------------------------------------


def test_ac1_no_step_runs_the_retired_host_env_exporter() -> None:
    for job in ("build", "deploy"):
        for step in _steps(job):
            assert "export_pages_host_env.py" not in str(step.get("run", "")), step.get("name")
    assert "export_pages_host_env" not in PAGES_WORKFLOW.read_text(encoding="utf-8")


def test_ac1_pages_check_reads_the_deploying_hosts_values() -> None:
    build = next(step for step in _steps("build") if "pages-check" in str(step.get("run", "")))
    assert build["env"] == {
        "SITE_URL": "${{ steps.pages.outputs.base_url }}",
        "PAGES_HOST_BASE_URL": "${{ steps.pages.outputs.base_url }}",
        "PAGES_HOST_BASE_PATH": "${{ steps.pages.outputs.base_path }}",
    }
    configure = next(step for step in _steps("build") if step.get("id") == "pages")
    assert str(configure["uses"]).startswith("actions/configure-pages@")


def test_ac1_the_flag_exports_stay_in_the_renamed_step() -> None:
    step = next(step for step in _steps("build") if step.get("name") == "Resolve build env (flags)")
    run = step["run"]
    assert 'docsite/tools/export_ci_surfaces_tile_env.py >> "$GITHUB_ENV"' in run
    assert 'scripts/pages_artifact_download.py --flag-env >> "$GITHUB_ENV"' in run
    assert "env" not in step  # no host value reaches a flag export
    names = [s.get("name") for s in _steps("build")]
    assert not [name for name in names if name and "Resolve Pages host env" in name]


# --- AC2: the asset step ----------------------------------------------------------------------


def test_ac2_contents_write_is_the_deploy_jobs_alone() -> None:
    jobs = _workflow()["jobs"]
    assert jobs["deploy"]["permissions"] == {"pages": "write", "id-token": "write", "contents": "write"}
    assert jobs["build"]["permissions"]["contents"] == "read"
    assert _workflow()["permissions"]["contents"] == "read"


def test_ac2_the_asset_steps_follow_the_deploy_and_carry_the_gate() -> None:
    steps = _steps("deploy")
    deploy_at = next(i for i, step in enumerate(steps) if str(step.get("uses", "")).startswith("actions/deploy-pages@"))
    download_at = next(
        i for i, step in enumerate(steps) if str(step.get("uses", "")).startswith("actions/download-artifact@")
    )
    publish_at = next(i for i, step in enumerate(steps) if pages.RELEASE_ASSET in str(step.get("run", "")))
    assert deploy_at < download_at < publish_at
    for index in (download_at, publish_at):
        assert steps[index]["if"] == pages.RELEASE_ASSET_IF
    assert steps[download_at]["with"] == {"name": "pages-site", "path": "pages-site"}
    run = steps[publish_at]["run"]
    assert "pages-site.zip" in run
    assert re.search(r"gh release (create|upload) pages-site\b", run)
    assert "--clobber" in run
    assert "--prerelease" in run and '--target "$GITHUB_SHA"' in run
    assert "test -f pages-site/build.json" in run


def test_ac2_the_gate_reads_the_build_jobs_exported_duty_flag() -> None:
    build = _workflow()["jobs"]["build"]
    assert build["outputs"]["pages_duty"] == "${{ steps.duty.outputs.pages_duty }}"
    duty = next(step for step in _steps("build") if step.get("id") == "duty")
    assert duty["run"] == 'echo "pages_duty=${PYFORGE_PAGES_DUTY:-0}" >> "$GITHUB_OUTPUT"'
    names = [step.get("name") or step.get("id") for step in _steps("build")]
    assert names.index("Resolve build env (flags)") < names.index("Carry the duty flag to the deploy job")
    assert "github.event_name != 'pull_request'" in pages.RELEASE_ASSET_IF


def test_ac2_the_site_artifact_uploads_on_every_event() -> None:
    upload = next(step for step in _steps("build") if str(step.get("uses", "")).startswith("actions/upload-artifact@"))
    assert upload["with"]["name"] == "pages-site"
    assert upload["with"]["path"] == "docs-site/build/site"
    assert "if" not in upload


@pytest.mark.parametrize(
    ("pages_duty", "event_name", "runs"),
    [
        ("1", "push", True),
        ("1", "workflow_dispatch", True),
        ("1", "schedule", True),
        ("1", "pull_request", False),
        ("0", "push", False),
        ("", "push", False),
    ],
)
def test_release_asset_runs_evaluates_the_gate(pages_duty: str, event_name: str, runs: bool) -> None:
    assert pages.release_asset_runs(pages_duty=pages_duty, event_name=event_name) is runs


# --- AC6: protected refs ----------------------------------------------------------------------


def _pattern(glob: str) -> re.Pattern[str]:
    """GitHub ruleset ``ref_name`` globs: ``**`` spans slashes, ``*`` does not."""
    parts = re.split(r"(\*\*|\*)", glob)
    body = "".join(".*" if part == "**" else "[^/]*" if part == "*" else re.escape(part) for part in parts)
    return re.compile(f"^{body}$")


def test_ac6_the_rolling_tag_matches_no_protected_pattern() -> None:
    document = json.loads(PROTECTED_REFS.read_text(encoding="utf-8"))
    patterns = [
        glob
        for ruleset in document["rulesets"]
        for glob in ruleset.get("conditions", {}).get("ref_name", {}).get("include", [])
    ]
    assert "refs/tags/archive/**" in patterns  # the read is real
    tag_ref = f"refs/tags/{pages.RELEASE_TAG}"
    assert not [glob for glob in patterns if _pattern(glob).match(tag_ref)]
    assert _pattern("refs/tags/archive/**").match("refs/tags/archive/x")  # the matcher is alive


def test_ac6_the_rolling_tag_is_not_a_version() -> None:
    assert pages.RELEASE_TAG == "pages-site"
    assert not re.fullmatch(r"v?\d{4}\.\d{1,2}\.\d{1,2}(\.\d+)?", pages.RELEASE_TAG)
