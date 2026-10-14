"""Story 102.1–102.2 (CAP-168): pages.yml trigger, build, and deploy shape."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[6]
PAGES_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pages.yml"

_EXPECTED_PATHS = {
    "docs/tutorials/**",
    "docs/how-to/**",
    "docs/reference/**",
    "docs/explanation/**",
    "docs/index.md",
    "docs/404.md",
    "docs/map.yaml",
    "docs/dashboard/**",
    "docs-site/**",
    "docsite/**",
    "presentations/**",
    ".github/workflows/pages.yml",
}


def _load() -> dict:
    assert PAGES_WORKFLOW.is_file()
    assert not (REPO_ROOT / ".github" / "workflows" / "dashboard.yml").exists()
    assert not (REPO_ROOT / ".github" / "workflows" / "docsite-check.yml").exists()
    return yaml.safe_load(PAGES_WORKFLOW.read_text(encoding="utf-8"))


def test_pages_yml_trigger_shape() -> None:
    document = _load()
    assert document["name"] == "Pages"
    triggers = document.get("on", document.get(True))
    assert isinstance(triggers, dict)
    pr_paths = set(triggers["pull_request"]["paths"])
    push = triggers["push"]
    assert push["branches"] == ["main"]
    assert set(push["paths"]) == _EXPECTED_PATHS
    assert pr_paths == _EXPECTED_PATHS
    assert "workflow_dispatch" in triggers
    schedule = triggers["schedule"]
    assert isinstance(schedule, list) and len(schedule) == 1
    cron = schedule[0]["cron"]
    assert cron == "23 */6 * * *"
    assert "17 6 * * 1" not in cron


def test_pages_yml_build_checkout_is_shallow_and_keeps_the_deck_downloads() -> None:
    document = _load()
    checkout = next(
        step
        for step in document["jobs"]["build"]["steps"]
        if isinstance(step, dict) and step.get("uses", "").startswith("actions/checkout@")
    )
    with_block = checkout["with"]
    assert with_block["fetch-depth"] == 1
    assert "sparse-checkout" not in with_block


def test_pages_yml_build_job_has_no_extra_if_beyond_pause_fragment() -> None:
    document = _load()
    build_if = document["jobs"]["build"].get("if", "")
    assert "PAUSE_PAGES" in build_if
    assert "PAUSE_DASHBOARD" not in build_if
    assert "pull_request" not in build_if


def test_pages_yml_deploy_if_conjoins_skip_conditions() -> None:
    document = _load()
    deploy_if = document["jobs"]["deploy"]["if"]
    assert "PAUSE_PAGES" in deploy_if
    assert "pull_request" in deploy_if
    assert "needs.build.outputs.changed" in deploy_if


def test_pages_yml_concurrency_and_timeouts() -> None:
    document = _load()
    build = document["jobs"]["build"]
    deploy = document["jobs"]["deploy"]
    assert build["timeout-minutes"] == 20
    assert deploy["timeout-minutes"] == 15
    assert build["concurrency"]["cancel-in-progress"] is True
    assert deploy["concurrency"]["group"] == "pages"
    assert deploy["concurrency"]["cancel-in-progress"] is False


def test_pages_yml_pr_artifact_upload_shape() -> None:
    document = _load()
    steps = document["jobs"]["build"]["steps"]
    upload_pages = next(s for s in steps if isinstance(s, dict) and "upload-pages-artifact" in str(s.get("uses", "")))
    upload_pr = next(s for s in steps if isinstance(s, dict) and s.get("uses", "").startswith("actions/upload-artifact@"))
    assert "pull_request" in upload_pages["if"]
    assert upload_pages["if"].strip() == "${{ github.event_name != 'pull_request' }}"
    assert upload_pr["if"].strip() == "${{ github.event_name == 'pull_request' }}"
    assert upload_pr["with"]["name"] == "pages-site"


def test_pages_yml_runs_docs_site_validate_in_build() -> None:
    text = PAGES_WORKFLOW.read_text(encoding="utf-8")
    assert "docs-site-validate" in text
    assert re.search(r"jobs:\s*\n\s*build:", text)

