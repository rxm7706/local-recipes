#!/usr/bin/env python3
"""Finish ``viz-publish-stage``: optional manifest from the viz export artifact flag."""

from __future__ import annotations

import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import viz_manifest  # noqa: E402

from pyforge.atlas.viz_export_artifact import export_artifact_enabled  # noqa: E402


def main() -> int:
    root = viz_manifest.repo_root()
    staged = root / "docs" / "dashboard" / "kedro-viz"
    return viz_manifest.write_manifest(staged, flag_on=export_artifact_enabled())


if __name__ == "__main__":
    raise SystemExit(main())
