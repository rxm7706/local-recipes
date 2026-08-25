#!/usr/bin/env python3
"""Read-only deferred-work twin check — thin CLI over Doctor's chain source.

Story 6.9 retired this script's logic into ``pyforge.doctor.sources.chain``;
Story 25.6 restores the familiar entrypoint so operators and docs can keep
calling ``python scripts/deferred_work_check.py``. The implementation is
delegated to ``python -m pyforge.doctor.sources deferred-work``.

Exit 0 when every Tier-3 deferral AND every spec-frontmatter deferral has a
tracked twin; non-zero otherwise.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

DETECTOR = None  # Story 6.9 residual CLI; verdicts live in pyforge.doctor.sources


def main() -> int:
    cmd = [sys.executable, "-m", "pyforge.doctor.sources", "deferred-work"]
    return subprocess.call(cmd, cwd=str(REPO_ROOT))


if __name__ == "__main__":
    sys.exit(main())
