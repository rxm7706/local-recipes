#!/usr/bin/env python3
"""Emit the status pages env for GitHub Actions (run with ``-e pyforge-guild``; Story 42.1, CAP-60).

Prints ``PYFORGE_STATUS_PAGES=1|0`` from ``pyforge.herald.status_pages`` for the workflow to append to
``$GITHUB_ENV`` before the ``site`` build; the step that runs it is steward's (``pages.yml``)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from status_pages import export_env_for_ci  # noqa: E402


def main() -> None:
    for key, value in export_env_for_ci().items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
