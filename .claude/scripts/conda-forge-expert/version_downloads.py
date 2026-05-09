#!/usr/bin/env python3
"""Wrapper. Canonical: skills/conda-forge-expert/scripts/version_downloads.py"""
import subprocess
import sys
from pathlib import Path

_SKILL_SCRIPT = (
    Path(__file__).parent.parent.parent
    / "skills" / "conda-forge-expert" / "scripts" / "version_downloads.py"
)

if __name__ == "__main__":
    sys.exit(subprocess.run([sys.executable, str(_SKILL_SCRIPT)] + sys.argv[1:]).returncode)
