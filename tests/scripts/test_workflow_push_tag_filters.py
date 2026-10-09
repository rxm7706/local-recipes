"""Story 87.15 (minor 13): tag pushes must not start workflows with branch-only path filters."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"


def _push_trigger(document: dict) -> object | None:
    triggers = document.get("on", document.get(True))
    if not isinstance(triggers, dict):
        return None
    return triggers.get("push")


def test_every_push_trigger_filters_branches_or_tags():
    violations: list[str] = []
    for path in sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        push = _push_trigger(doc)
        if push is None:
            continue
        if push is True:
            violations.append(f"{path.name}: bare push trigger")
            continue
        if isinstance(push, list):
            violations.append(f"{path.name}: push is a list without branch/tag filter")
            continue
        if not isinstance(push, dict):
            continue
        if "branches" not in push and "tags" not in push:
            violations.append(f"{path.name}: push lacks branches/tags filter (keys={sorted(push)})")
    assert not violations, "tag pushes could start workflows:\n  " + "\n  ".join(violations)
