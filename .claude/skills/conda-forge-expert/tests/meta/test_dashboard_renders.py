"""Meta: the Guildhall's JavaScript must actually run.

The three standing doc detectors and the rest of this suite never execute the
dashboard's inline script, so on 2026-07-26 a partial derived object blanked
In Build / Realized / Archived while everything reported green. This test runs
the render and fails on any throw.
"""
from __future__ import annotations

import shutil
import subprocess

import pytest

from pathlib import Path

# .claude/skills/<skill>/tests/meta/<file> -> repo root. Anchored on the skill
# dir like test_skill_md_consistency.py, rather than counting parents, which is
# how this first landed on .claude/ instead of the root.
SKILL_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = SKILL_DIR.parents[2]
CHECK = REPO_ROOT / "docs" / "dashboard" / "check_render.js"


@pytest.mark.meta
def test_dashboard_script_runs_clean():
    if not CHECK.is_file():
        pytest.fail(f"missing render check: {CHECK.relative_to(REPO_ROOT)}")
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not on PATH (provisioned by the local-recipes env)")
    r = subprocess.run([node, str(CHECK)], capture_output=True, text=True,
                       cwd=REPO_ROOT, timeout=120)
    assert r.returncode == 0, (
        "the Guildhall's inline script threw — every section BELOW the error "
        f"renders empty:\n{r.stdout}\n{r.stderr}"
    )
