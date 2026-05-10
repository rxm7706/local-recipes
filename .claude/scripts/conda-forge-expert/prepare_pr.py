#!/usr/bin/env python3
"""
Entrypoint wrapper for conda-forge-expert → submit_pr.py --prepare-only.

Pushes the recipe branch to the user's staged-recipes fork without opening
the PR. Stable public CLI surface for pixi tasks and external callers.

Canonical implementation:
    .claude/skills/conda-forge-expert/scripts/submit_pr.py

Do NOT put logic here — delegate entirely to the canonical script.
"""
import subprocess
import sys
from pathlib import Path

_SKILL_SCRIPT = (
    Path(__file__).parent.parent.parent
    / "skills" / "conda-forge-expert" / "scripts" / "submit_pr.py"
)

if __name__ == "__main__":
    args = [sys.executable, str(_SKILL_SCRIPT), "--prepare-only", *sys.argv[1:]]
    sys.exit(subprocess.run(args).returncode)
