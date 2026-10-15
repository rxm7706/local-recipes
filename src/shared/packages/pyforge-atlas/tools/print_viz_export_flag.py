#!/usr/bin/env python3
"""Print GitHub Actions outputs for ``pyforge.atlas.viz_export_artifact``."""

from __future__ import annotations

from pyforge.atlas.viz_export_artifact import export_artifact_enabled


def main() -> int:
    enabled = export_artifact_enabled()
    # GITHUB_OUTPUT key consumed by kedro-viz-publish.yml upload step `if:`.
    print(f"enabled={'true' if enabled else 'false'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
