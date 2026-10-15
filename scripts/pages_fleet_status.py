#!/usr/bin/env python3
"""Write the fleet board's build input for the Pages workflow (steward Story 102.3, CAP-168).

Reads the JSON ``sprint-ledger-query --format json --output PATH`` wrote and writes
``docsite/content/fleet-status.json`` in the shape herald's board reads (herald Story 42.1), through
``pyforge.steward.pages.fleet_status_document``. Exit 0 wrote the file, 1 the ledger JSON was missing
or unusable (named on stderr); nothing else is written.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for _pkg in ("pyforge-core", "pyforge-steward"):
    _src = REPO_ROOT / "src" / "shared" / "packages" / _pkg / "src"
    if str(_src) not in sys.path:
        sys.path.insert(0, str(_src))

from pyforge.steward.pages import FLEET_STATUS_REL, fleet_status_document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reshape sprint-ledger-query JSON into the fleet board's input."
    )
    parser.add_argument(
        "--ledger",
        type=Path,
        required=True,
        help="sprint-ledger-query --format json output",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / FLEET_STATUS_REL,
        help=f"default: {FLEET_STATUS_REL}",
    )
    parser.add_argument(
        "--generated-at",
        default=None,
        help="the snapshot time the board names (default: the ledger payload's generated_at)",
    )
    args = parser.parse_args(argv)

    try:
        payload = json.loads(args.ledger.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(
            f"pages_fleet_status: {args.ledger}: unreadable ledger JSON ({exc})",
            file=sys.stderr,
        )
        return 1
    if not isinstance(payload, dict):
        print(f"pages_fleet_status: {args.ledger}: not a JSON object", file=sys.stderr)
        return 1
    try:
        document = fleet_status_document(payload, generated_at=args.generated_at)
    except ValueError as exc:
        print(f"pages_fleet_status: {args.ledger}: {exc}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    stations = len(document["stations"])
    print(
        f"pages_fleet_status: wrote {args.out} ({stations} stations, {len(document['stories'])} stories)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
