#!/usr/bin/env python3
"""
Entrypoint wrapper for conda-forge-expert → build_bmad_suite.py
Canonical implementation: .claude/skills/conda-forge-expert/scripts/build_bmad_suite.py
"""
import subprocess
import sys
from pathlib import Path

_SKILL_SCRIPT = (
    Path(__file__).parent.parent.parent
    / "skills"
    / "conda-forge-expert"
    / "scripts"
    / "build_bmad_suite.py"
)
if __name__ == "__main__":
    sys.exit(
        subprocess.run([sys.executable, str(_SKILL_SCRIPT)] + sys.argv[1:]).returncode
    )
