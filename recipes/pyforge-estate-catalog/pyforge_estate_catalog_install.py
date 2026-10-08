#!/usr/bin/env python3
"""Print the vendored catalog path for ``bmad-method install --custom-source``."""
from __future__ import annotations

import argparse
import os
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Locate the pyforge-estate-catalog share tree for BMAD discovery mode.",
    )
    parser.parse_args()
    prefix = os.environ.get("CONDA_PREFIX") or sys.prefix
    root = os.path.join(prefix, "share", "pyforge-estate-catalog")
    if not os.path.isdir(root):
        print(f"Error: pyforge-estate-catalog not found at {root}", file=sys.stderr)
        sys.exit(1)
    manifest = os.path.join(root, ".claude-plugin", "marketplace.json")
    if not os.path.isfile(manifest):
        print(f"Error: missing marketplace manifest at {manifest}", file=sys.stderr)
        sys.exit(1)
    print(root)
    print("")
    print("Air-gapped install:")
    print(f"  bmad-method install --custom-source {root!r}")


if __name__ == "__main__":
    main()
