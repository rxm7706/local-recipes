"""Story 31.1 — pin foundry-full mypy in CI and pr-preflight (AC8–AC10)."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[6]


def test_lint_types_workflow_runs_foundry_full_mypy() -> None:
    workflow = (_REPO_ROOT / ".github/workflows/lint-types.yml").read_text(encoding="utf-8")
    assert "pyforge-foundry-full" in workflow
    assert re.search(
        r"pixi run --frozen -e pyforge-foundry-full mypy",
        workflow,
    ), "lint-types job must run the mypy task in pyforge-foundry-full"


def test_pr_preflight_lanes_include_foundry_full_mypy() -> None:
    pixi = tomllib.loads((_REPO_ROOT / "pixi.toml").read_text(encoding="utf-8"))
    task = pixi["feature"]["guild-tasks"]["tasks"]["pr-preflight-lanes"]
    depends_on = task["depends-on"]
    assert {"task": "mypy", "environment": "pyforge-foundry-full"} in depends_on
