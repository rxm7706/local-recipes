#!/usr/bin/env python3
"""
Entrypoint wrapper for conda-forge-expert → cve_watcher.py
Stable public CLI surface for pixi tasks and external callers.
Canonical implementation: .claude/skills/conda-forge-expert/scripts/cve_watcher.py
Do NOT put logic here — delegate entirely to the canonical script.
"""
import subprocess
import sys
from pathlib import Path

_SKILL_SCRIPT = (
    Path(__file__).parent.parent.parent
    / "skills" / "conda-forge-expert" / "scripts" / "cve_watcher.py"
)

if __name__ == "__main__":
    sys.exit(subprocess.run([sys.executable, str(_SKILL_SCRIPT)] + sys.argv[1:]).returncode)
