"""Story 102.1–102.3 and 102.5 (CAP-168): pages.yml trigger, build, and deploy shape."""

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
    "docs/dashboard/**",  # tracked `deploy static` boards publish from here (102.4's review kept it)
    "scripts/pages_*.py",
    "src/shared/packages/pyforge-steward/src/pyforge/steward/pages.py",
    "docs-site/**",
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


def test_a_dispatch_bypasses_only_the_pause_switches_of_the_deploy() -> None:
    """Story 102.3's review (AD-4 as amended 2026-10-14): an equal hash performs zero deploys, a
    dispatch included. The dispatch term guards only the pause switches; the job's own condition
    (not a PR, main, a changed tree) is conjoined outside it."""
    deploy_if = " ".join(_load()["jobs"]["deploy"]["if"].split())
    assert deploy_if == (
        "${{ (github.event_name == 'workflow_dispatch' || (vars.PAUSE_ALL_CI != 'true' && "
        "vars.PAUSE_PAGES != 'true')) && (github.event_name != 'pull_request' && "
        "github.ref == 'refs/heads/main' && needs.build.outputs.changed == 'true') }}"
    )


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
    """The Pages artifact uploads off pull requests; the ``pages-site`` copy uploads for a pull request
    or a changed tree (Story 102.5 and its review: a PR's review copy, and the deploy job's release
    asset; an unchanged tree deploys nothing)."""
    document = _load()
    steps = document["jobs"]["build"]["steps"]
    upload_pages = next(s for s in steps if isinstance(s, dict) and "upload-pages-artifact" in str(s.get("uses", "")))
    upload_site = next(
        s for s in steps if isinstance(s, dict) and s.get("uses", "").startswith("actions/upload-artifact@")
    )
    assert "pull_request" in upload_pages["if"]
    assert upload_pages["if"].strip() == "${{ github.event_name != 'pull_request' }}"
    assert upload_site["if"] == "${{ github.event_name == 'pull_request' || steps.stamp.outputs.changed == 'true' }}"
    assert upload_site["with"]["name"] == "pages-site"


def test_pages_yml_runs_docs_site_validate_in_build() -> None:
    text = PAGES_WORKFLOW.read_text(encoding="utf-8")
    assert "docs-site-validate" in text
    assert re.search(r"jobs:\s*\n\s*build:", text)


def test_pages_yml_writes_the_fleet_board_input_before_the_build() -> None:
    """Story 102.3 (closes the 102.2 gap herald 42.1's spec assigns to this workflow): a Guild step
    writes the fleet board's input (docs-site/src/content/fleet-status.json since herald Story 43.7) from
    sprint-ledger-query --format json before pages-check, and the build env carries herald's status-pages flag
    (``python -m pyforge.herald.pages_env``, herald Story 43.7)."""
    steps = [s for s in _load()["jobs"]["build"]["steps"] if isinstance(s, dict)]
    runs = [str(s.get("run", "")) for s in steps]
    writer = next(i for i, run in enumerate(runs) if "scripts/pages_fleet_status.py" in run)
    build = next(i for i, run in enumerate(runs) if "pages-check" in run)
    env = next(i for i, run in enumerate(runs) if "pyforge.herald.pages_env" in run)
    assert env < writer < build
    assert "sprint-ledger-query -- --format json --output" in runs[writer]
    assert "--out docs-site/src/content/fleet-status.json" in runs[writer]
    assert 'python -m pyforge.herald.pages_env >> "$GITHUB_ENV"' in runs[env]
