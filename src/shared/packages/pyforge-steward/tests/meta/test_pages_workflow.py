"""Story 102.1 (CAP-168): pages.yml trigger and checkout shape."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[6]
PAGES_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pages.yml"

_EXPECTED_PUSH_PATHS = {
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


def test_pages_yml_trigger_shape() -> None:
    assert PAGES_WORKFLOW.is_file()
    assert not (REPO_ROOT / ".github" / "workflows" / "dashboard.yml").exists()
    document = yaml.safe_load(PAGES_WORKFLOW.read_text(encoding="utf-8"))
    assert document["name"] == "Pages"
    triggers = document.get("on", document.get(True))
    assert isinstance(triggers, dict)
    push = triggers["push"]
    assert push["branches"] == ["main"]
    assert set(push["paths"]) == _EXPECTED_PUSH_PATHS
    assert "workflow_dispatch" in triggers
    assert "pull_request" not in triggers
    schedule = triggers["schedule"]
    assert isinstance(schedule, list) and len(schedule) == 1
    assert schedule[0]["cron"] == "17 6 * * 1"


def test_pages_yml_build_checkout_is_shallow_and_sparse() -> None:
    document = yaml.safe_load(PAGES_WORKFLOW.read_text(encoding="utf-8"))
    checkout = next(
        step
        for step in document["jobs"]["build"]["steps"]
        if isinstance(step, dict) and step.get("uses", "").startswith("actions/checkout@")
    )
    with_block = checkout["with"]
    assert with_block["fetch-depth"] == 1
    sparse = with_block["sparse-checkout"]
    assert "!/presentations/" in sparse
    assert "/presentations/*/project/*.html" in sparse
    assert with_block.get("sparse-checkout-cone-mode") is False
