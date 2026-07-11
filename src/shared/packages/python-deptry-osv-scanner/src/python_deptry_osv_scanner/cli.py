"""CLI entry point (skeleton).

Story 4.1 (E4) implements the real argparse CLI, ``ComplianceReport``
assembly, ``report-schema.json`` validation, and the FR5 exit-code gate. This
stub only makes the ``python-deptry-osv-scanner`` console script resolvable so the package
builds and the pixi environment is verifiable end to end before the E1-E4
implementation lands.
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    """Placeholder entry point; returns 0 so the skeleton is CI-green."""
    print(
        "python-deptry-osv-scanner: Option B build skeleton wired. "
        "E1-E4 not yet implemented - see docs/specs/python-deptry-osv-scanner.md.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
