#!/usr/bin/env python3
"""Emit CI surfaces tile env for GitHub Actions (run with ``-e pyforge-guild``)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ci_surfaces_tile import export_tile_env_for_ci  # noqa: E402


def main() -> None:
    for key, value in export_tile_env_for_ci().items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
