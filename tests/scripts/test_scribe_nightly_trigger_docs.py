"""Boundary + reviewability coverage for Story 8.1's I/O & Edge-Case Matrix
rows that scripts/test_scribe_nightly_trigger.py and
scripts/test_scribe_graph_freshness_check.py don't reach: the GitHub Actions
boundary documentation, and the trigger definition being checked into git.

Matrix rows covered here:
  "GitHub Actions considered as the trigger mechanism" — the runbook's Scope
    note explains why not, and no workflow file exists for this trigger.
  "Trigger fires on schedule" (partial) — "the trigger's definition is
    reviewable in git": the pixi tasks and the systemd unit files exist as
    checked-in, non-empty repo content. (The "four consecutive scheduled
    runs" half of that row is only observable on an operator's own machine
    over real elapsed time — not something a repo-local test can assert.)
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNBOOK = (
    REPO_ROOT
    / "src"
    / "shared"
    / "packages"
    / "pyforge-scribe"
    / "docs"
    / "cli-runbooks.md"
)
OPS_DIR = (
    REPO_ROOT / "src" / "shared" / "packages" / "pyforge-scribe" / "ops" / "systemd"
)
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


def test_runbook_documents_why_not_github_actions():
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "Scope note: why not a GitHub Actions workflow" in text
    assert "HARD boundary for Epic 8" in text


def test_no_github_actions_workflow_added_for_the_nightly_trigger():
    # Reject both the literal CLI invocation and the two pixi task names
    # that also reach it (`pyforge-scribe-nightly-compile` runs the trigger
    # body; `scribe-install-nightly-trigger` installs it) -- a workflow
    # invoking either would bypass this same HARD boundary just as surely
    # as calling `scribe graph compile` directly.
    forbidden = (
        "scribe graph compile",
        "pyforge-scribe-nightly-compile",
        "scribe-install-nightly-trigger",
    )
    for workflow in WORKFLOWS_DIR.glob("*.y*ml"):
        content = workflow.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in content, (
                f"{workflow} appears to trigger the nightly compile (found "
                f"{needle!r}) — Epic 8's HARD boundary forbids a GitHub "
                "Actions workflow for this"
            )


def test_trigger_definition_is_checked_in_and_reviewable():
    service_tmpl = OPS_DIR / "pyforge-scribe-nightly-compile.service.tmpl"
    timer_unit = OPS_DIR / "pyforge-scribe-nightly-compile.timer"
    assert service_tmpl.is_file() and service_tmpl.stat().st_size > 0
    assert timer_unit.is_file() and timer_unit.stat().st_size > 0

    pixi_toml = (REPO_ROOT / "pixi.toml").read_text(encoding="utf-8")
    assert "[feature.pyforge-scribe.tasks.pyforge-scribe-nightly-compile]" in pixi_toml
    assert "[feature.pyforge-scribe.tasks.scribe-install-nightly-trigger]" in pixi_toml
