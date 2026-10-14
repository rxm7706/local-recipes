#!/usr/bin/env python3
"""Weekly CI canary matrix from docs/governance/ci-surfaces.yaml (Story 99.6 / CAP-166)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ci_surface_gates_lib import REGISTRY_REL, load_registry  # noqa: E402

CANARY_PREFIX = "ci-canary."


def canary_token_for_row(row: dict[str, Any]) -> str:
    row_id = str(row.get("id") or "")
    return f"{CANARY_PREFIX}{row_id}"


def canary_job_name(surface_id: str) -> str:
    return f"canary ({surface_id})"


def surface_id_from_canary_token(token: str | None) -> str | None:
    if not token:
        return None
    text = str(token)
    if text.startswith(CANARY_PREFIX):
        return text[len(CANARY_PREFIX) :]
    return None


def paused_high_cost_matrix(registry: dict[str, Any]) -> list[dict[str, Any]]:
    """Rows the weekly canary builds: paused registry rows with cost: high."""
    out: list[dict[str, Any]] = []
    for row in registry.get("surfaces") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("cost") or "") != "high":
            continue
        if str(row.get("state") or "") != "paused":
            continue
        row_id = str(row.get("id") or "")
        if not row_id:
            continue
        twin = row.get("local_twin")
        entry: dict[str, Any] = {
            "id": row_id,
            "canary": canary_token_for_row(row),
        }
        if twin is not None:
            entry["local_twin"] = str(twin)
        out.append(entry)
    return out


def matrix_json(registry: dict[str, Any]) -> str:
    include = paused_high_cost_matrix(registry)
    return json.dumps({"include": include})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("matrix",),
        help="emit the GitHub Actions matrix payload",
    )
    parser.add_argument("--json", action="store_true", help="print JSON only (default for matrix)")
    parser.add_argument(
        "--registry",
        type=Path,
        default=ROOT / REGISTRY_REL,
        help="path to ci-surfaces.yaml",
    )
    args = parser.parse_args()
    if not args.registry.is_file():
        print(f"missing registry {args.registry}", file=sys.stderr)
        return 2
    registry = load_registry(args.registry)
    if args.command == "matrix":
        print(matrix_json(registry))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
