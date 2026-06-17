#!/usr/bin/env python
"""
Rewrite pyproject.toml's [project].version field to the value passed via
$PKG_VERSION. Idempotent — safe to run on a pyproject.toml that already has
the correct version.

Upstream alex-pinkus/tree-sitter-swift hardcodes pyproject.toml `version = "0.0.1"`
across all releases. This script is the cross-platform conda-side workaround that
keeps the wheel's bundled dist-info version in sync with the conda recipe.
Becomes a no-op the day upstream resumes bumping the version field properly.
"""
from __future__ import annotations

import os
import pathlib
import re
import sys


def main() -> int:
    version = os.environ.get("PKG_VERSION")
    if not version:
        print("ERROR: PKG_VERSION not set in environment", file=sys.stderr)
        return 1

    target = pathlib.Path("pyproject.toml")
    content = target.read_text(encoding="utf-8")

    # Replace the FIRST `version = "..."` line — that's the [project].version one.
    # (build-system block uses `requires = [...]`, not `version`.)
    new_content, n = re.subn(
        r'^version = ".*?"$',
        f'version = "{version}"',
        content,
        count=1,
        flags=re.MULTILINE,
    )

    if n == 0:
        print("ERROR: no `version = \"...\"` line found in pyproject.toml", file=sys.stderr)
        return 2

    target.write_text(new_content, encoding="utf-8")
    print(f"pyproject.toml version rewritten to {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
