#!/usr/bin/env python3
"""Emit Pages host env for GitHub Actions (run with ``-e pyforge-guild``)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pages_second_host import export_host_env_for_ci  # noqa: E402


def main() -> None:
    for key, value in export_host_env_for_ci().items():
        # GitHub Actions workflow commands: append to GITHUB_ENV when redirected.
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
