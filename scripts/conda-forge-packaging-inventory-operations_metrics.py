#!/usr/bin/env python3
"""Conda-forge packaging inventory operations runner.

Story 23.9: thin actuator over Atlas Story 23.4 exports. Under ``--live-catalog
PATH`` (a ``PYFORGE_ATLAS_DATA_ROOT``), reads
``derived/inventory_verified_packages/inventory_verified_packages.parquet`` and
``derived/inventory_aoss_free_queue/inventory_aoss_free_queue.parquet`` and
only formats CSV / Markdown / the regenerated prompt. Verification, universe
union, ``packaging_status``, and row assembly live in Kedro — not here.

Prompt sync contract:
- Replay prompt doc: docs/reference/conda-forge-packaging-inventory-operations_replay.md
- Any behavior/source/rule/metric/output change must update both this script and
  the replay prompt doc in the same commit.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

_VERIFIED_PACKAGES_REL = (
    "derived/inventory_verified_packages/inventory_verified_packages.parquet"
)
_AOSS_QUEUE_REL = "derived/inventory_aoss_free_queue/inventory_aoss_free_queue.parquet"

CSV_COLS = [
    "Repository_Source",
    "Role",
    "Package_Input_Name",
    "Core_Python_Package_Name",
    "PyPI_Verified",
    "CondaForge_Verified",
    "Priority_Bucket",
    "Packaging_Candidate_Status",
    "PyPI_PURL",
    "PyPI_Package_URL",
    "Conda-forge_PURL",
    "Conda-Forge_Package_URL",
    "Conda-Forge_FeedStock_URL",
    "Verification_Timestamp_UTC",
]

_QUEUE_COLS = ["Package_Name", "Reason", "Verification_Timestamp_UTC"]

_STATUS_ORDER = (
    "Already Packaged",
    "High Priority Candidate",
    "Low Priority Candidate",
    "Conda-Forge Only",
    "Not on PyPI",
)

_NET_NEW_STATUSES = frozenset(
    {"High Priority Candidate", "Low Priority Candidate", "Not on PyPI"}
)

_RETIRED_WORKBOOK_FLAG = "--analysis-" "xlsx"
_RETIRED_WORKBOOK_MSG = (
    "retired by Story 23.9 — use --live-catalog and the Atlas exports at "
    f"{_VERIFIED_PACKAGES_REL} + {_AOSS_QUEUE_REL} under PYFORGE_ATLAS_DATA_ROOT"
)


@dataclass
class AtlasExports:
    """Result of ``load_atlas_exports()`` — the Story 23.9 loader."""

    verified_rows: list[dict[str, str]] = field(default_factory=list)
    queue_rows: list[dict[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    failed: bool = False


def load_atlas_exports(root: Path) -> AtlasExports:
    """Read Story 23.4 Parquet exports under ``root`` (``PYFORGE_ATLAS_DATA_ROOT``).

    Lazily imports pandas. A missing or unreadable export is fatal (``failed``)
    — the caller must exit 2 before writing anything.
    """
    import pandas as pd

    result = AtlasExports()
    specs = (
        (_VERIFIED_PACKAGES_REL, "inventory_verified_packages", CSV_COLS),
        (_AOSS_QUEUE_REL, "inventory_aoss_free_queue", _QUEUE_COLS),
    )
    frames: dict[str, pd.DataFrame] = {}
    for rel_path, key, required_cols in specs:
        path = root / rel_path
        try:
            if not path.exists():
                result.failed = True
                result.warnings.append(f"--live-catalog: {key} missing at {path}")
                return result
            df = pd.read_parquet(path)
        except Exception as exc:
            result.failed = True
            result.warnings.append(f"--live-catalog: {key} unreadable at {path}: {exc}")
            return result
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            result.failed = True
            result.warnings.append(
                f"--live-catalog: {key} at {path} is missing columns: {', '.join(missing)}"
            )
            return result
        frames[key] = df

    verified = frames["inventory_verified_packages"].loc[:, CSV_COLS]
    result.verified_rows = [
        {col: "" if pd.isna(val) else str(val) for col, val in row.items()}
        for row in verified.to_dict(orient="records")
    ]
    queue = frames["inventory_aoss_free_queue"].loc[:, _QUEUE_COLS]
    result.queue_rows = [
        {col: "" if pd.isna(val) else str(val) for col, val in row.items()}
        for row in queue.to_dict(orient="records")
    ]
    return result


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS)
        w.writeheader()
        w.writerows(rows)


def write_aoss_queue_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_QUEUE_COLS)
        w.writeheader()
        w.writerows(rows)


def write_markdown(
    path: Path,
    rows: list[dict[str, str]],
    queue_count: int,
) -> None:
    """Format a summary report from already-derived export columns only."""
    status_counts = Counter(row["Packaging_Candidate_Status"] for row in rows)
    source_attr_counts = Counter(row["Repository_Source"] for row in rows)
    net_new_counts = Counter(
        row["Packaging_Candidate_Status"]
        for row in rows
        if row.get("CondaForge_Verified") != "Yes"
        and row["Packaging_Candidate_Status"] in _NET_NEW_STATUSES
    )
    not_on_cf_count = sum(1 for row in rows if row.get("CondaForge_Verified") != "Yes")

    lines: list[str] = []
    lines.append("# Consolidated Verified Package Inventory Report")
    lines.append("")
    lines.append(f"- Total final unique package count: **{len(rows):,}**")
    lines.append(f"- Count not on conda-forge: **{not_on_cf_count:,}**")
    lines.append(f"- AOSS-Free Mason queue rows: **{queue_count:,}**")
    lines.append("")
    lines.append("## Packaging Candidate Status Breakdown")
    lines.append("")
    for status in _STATUS_ORDER:
        lines.append(f"- {status}: **{status_counts.get(status, 0):,}**")
    lines.append("")
    lines.append("## Primary Repository Source Attribution in Final Inventory")
    lines.append("")
    for src, cnt in source_attr_counts.most_common():
        lines.append(f"- {src}: **{cnt:,}**")
    lines.append("")
    lines.append("## Net-New Packages Breakdown")
    lines.append("")
    lines.append("- Net-new is defined as packages not verified on conda-forge.")
    for status in _STATUS_ORDER:
        if status in _NET_NEW_STATUSES:
            lines.append(f"- {status}: **{net_new_counts.get(status, 0):,}**")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_revised_prompt(path: Path, args: argparse.Namespace) -> None:
    lines = ["python3 scripts/conda-forge-packaging-inventory-operations_metrics.py"]
    lines.append(f'--live-catalog "{args.live_catalog}"')
    lines.append(f'--output-csv "{args.output_csv}"')
    lines.append(f'--output-md "{args.output_md}"')
    lines.append(f'--output-revised-prompt "{args.output_revised_prompt}"')
    command = " \\\n  ".join(lines)
    text = f"""# docs/reference/conda-forge-packaging-inventory-operations_prompt.md

Run consolidated verified package inventory generation from Atlas exports.

```bash
{command}
```
"""
    path.write_text(text, encoding="utf-8")


def _queue_output_path(output_csv: Path, queue_rows: list[dict[str, str]]) -> Path:
    stamp = "unknown-date"
    if queue_rows:
        stamp = str(queue_rows[0].get("Verification_Timestamp_UTC", ""))[:10] or stamp
    return output_csv.parent / f"aoss-free-queue-{stamp}.csv"


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="conda-forge-packaging-inventory-operations-metrics",
        description=(
            "Format consolidated verified package inventory outputs from Atlas "
            "Story 23.4 Parquet exports (inventory_verified_packages + "
            "inventory_aoss_free_queue)."
        ),
    )
    parser.add_argument(
        _RETIRED_WORKBOOK_FLAG,
        type=Path,
        default=None,
        dest="analysis_xlsx",
        help="Retired by Story 23.9 — exits 2 with a pointer to --live-catalog.",
    )
    parser.add_argument(
        "--live-catalog",
        type=Path,
        required=True,
        metavar="PATH",
        help=(
            "PYFORGE_ATLAS_DATA_ROOT containing the Story 23.4 Parquet exports "
            "under derived/inventory_verified_packages/ and "
            "derived/inventory_aoss_free_queue/."
        ),
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("cdao_consolidated_inventory_verified_all_packages.csv"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("cdao_consolidated_inventory_verified_all_packages.md"),
    )
    parser.add_argument(
        "--output-revised-prompt",
        type=Path,
        default=Path("docs/reference/conda-forge-packaging-inventory-operations_prompt.md"),
    )
    parser.add_argument(
        "--skip-revised-prompt",
        action="store_true",
        help="Do not overwrite docs/reference/conda-forge-packaging-inventory-operations_prompt.md.",
    )
    args = parser.parse_args()

    if args.analysis_xlsx is not None:
        print(_RETIRED_WORKBOOK_MSG, file=sys.stderr)
        return 2

    exports = load_atlas_exports(args.live_catalog)
    if exports.failed:
        for warning in exports.warnings:
            print(warning, file=sys.stderr)
        return 2

    write_csv(args.output_csv, exports.verified_rows)
    write_markdown(args.output_md, exports.verified_rows, len(exports.queue_rows))
    queue_path = _queue_output_path(args.output_csv, exports.queue_rows)
    write_aoss_queue_csv(queue_path, exports.queue_rows)
    if not args.skip_revised_prompt:
        write_revised_prompt(args.output_revised_prompt, args)

    not_on_cf_count = sum(
        1 for row in exports.verified_rows if row.get("CondaForge_Verified") != "Yes"
    )
    print("=== MASTER PROMPT V3.0 EXECUTION SUMMARY METRICS ===")
    print()
    print(f"Total final unique packages processed: {len(exports.verified_rows):,}")
    print(f"Count not on conda-forge: {not_on_cf_count:,}")
    print(f"Wrote CSV: {args.output_csv}")
    print(f"Wrote Markdown report: {args.output_md}")
    print(f"Wrote AOSS-Free queue: {queue_path} ({len(exports.queue_rows):,} rows)")
    if not args.skip_revised_prompt:
        print(f"Wrote revised prompt: {args.output_revised_prompt}")
    if exports.warnings:
        print("\nWarnings:")
        for warning in exports.warnings:
            print(f"  - {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
