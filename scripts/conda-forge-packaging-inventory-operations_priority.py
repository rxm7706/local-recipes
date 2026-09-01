#!/usr/bin/env python3
"""Thin CLI shim over Atlas ``inventory_priority_assignments`` (Story 23.9).

Ranking rules live in Kedro ``assign_inventory_priority`` (Story 23.3). This
script reads ``inventory_priority_assignments.parquet``, optionally joins
``enterprise_jfrog_consumption.parquet`` for Artifactory telemetry columns, and
writes:

1. ``identity_ranked_export.parquet`` (Story 22.1 / Vizro Epic 22 shape)
2. Legacy ranked CSV when ``--ranked-csv`` is passed (replaces the retired
   workbook ranked tab)

Passing ``--xlsx`` or ``--tab`` exits 2 with a retirement pointer.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
PYFORGE_ATLAS_DATA_ROOT_ENV = "PYFORGE_ATLAS_DATA_ROOT"
PYFORGE_ATLAS_PROJECT_DIR = REPO_ROOT / "src/shared/packages/pyforge-atlas"
PRIORITY_ASSIGNMENTS_RELPATH = Path(
    "derived/inventory_priority_assignments/inventory_priority_assignments.parquet"
)
ENTERPRISE_JFROG_RELPATH = Path(
    "derived/enterprise_jfrog_consumption/enterprise_jfrog_consumption.parquet"
)
IDENTITY_RANKED_EXPORT_RELPATH = Path(
    "derived/identity_ranked_export/identity_ranked_export.parquet"
)
RANKED_EXPORT_COLUMNS = [
    "Core_Python_Package_Name",
    "P",
    "Rank",
    "Score",
    "Work",
    "Platforms",
    "Apps",
    "Downloads",
    "Versions",
    "Vuln",
    "Priority_Bucket_Description",
    "Priority_Source",
    "Priority_Reason",
    "JFROG_risk_level",
    "JFROG_latest_vuln_count",
    "internal_component_count",
    "internal_lob_count",
    "Verification_Timestamp_UTC",
]
RANK_COLS = [
    "P",
    "Rank",
    "Score",
    "Package",
    "Work",
    "Platforms",
    "Apps",
    "Downloads",
    "Versions",
    "Vuln",
]
DETAIL_COLS = [
    "Priority_Bucket_Description",
    "Priority_Source",
    "Priority_Reason",
    "JFROG_risk_level",
    "JFROG_latest_vuln_count",
    "internal_component_count",
    "internal_lob_count",
]
LEGACY_RANKED_CSV_COLUMNS = RANK_COLS + DETAIL_COLS
BUCKET_ORDER = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10"]
WORK_ORDER = [
    "Fix vulnerability",
    "Create recipe",
    "File OpenTeams tracking issue [Conda-Forge Packaging]",
    "Already tracked",
]
_RETIRED_WORKBOOK_MSG = (
    "retired by Story 23.9 — use inventory_priority_assignments.parquet under "
    "PYFORGE_ATLAS_DATA_ROOT (and --ranked-export for Vizro)"
)


def _resolve_data_root() -> Path:
    data_root = Path(os.environ.get(PYFORGE_ATLAS_DATA_ROOT_ENV, "data"))
    if not data_root.is_absolute():
        data_root = PYFORGE_ATLAS_PROJECT_DIR / data_root
    return data_root


def default_priority_assignments_path() -> Path:
    return _resolve_data_root() / PRIORITY_ASSIGNMENTS_RELPATH


def default_jfrog_consumption_path() -> Path:
    return _resolve_data_root() / ENTERPRISE_JFROG_RELPATH


def default_ranked_export_path() -> Path:
    return _resolve_data_root() / IDENTITY_RANKED_EXPORT_RELPATH


def _blank(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _num(value) -> float:
    try:
        return float(value) if value not in (None, "") else 0.0
    except (TypeError, ValueError):
        return 0.0


def load_priority_assignments(path: Path) -> pd.DataFrame:
    if not path.is_file():
        print(
            f"inventory_priority_assignments not found at {path} -- run "
            "`pixi run -e pyforge-atlas pyforge-atlas-bootstrap` first",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return pd.read_parquet(path)


def load_jfrog_consumption(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame()
    try:
        return pd.read_parquet(path)
    except Exception as exc:
        print(f"Warning: could not read enterprise_jfrog_consumption at {path}: {exc}", file=sys.stderr)
        return pd.DataFrame()


def _jfrog_lookup(jfrog_df: pd.DataFrame) -> dict[str, dict]:
    if jfrog_df.empty or "core_python_package_name" not in jfrog_df.columns:
        return {}
    return {
        _blank(row.get("core_python_package_name")).lower(): row
        for row in jfrog_df.to_dict(orient="records")
        if _blank(row.get("core_python_package_name"))
    }


def assignments_to_records(assignments: pd.DataFrame, jfrog_by: dict[str, dict]) -> list[dict]:
    """Build canvas/export record dicts from Kedro priority assignments + JFROG join."""
    records: list[dict] = []
    for row in assignments.to_dict(orient="records"):
        name = _blank(row.get("core_python_package_name"))
        j = jfrog_by.get(name.lower(), {})
        plat = int(_num(j.get("platform_env_count")))
        apps = int(_num(j.get("internal_app_count")))
        ic = int(_num(j.get("internal_component_count")))
        lob = int(_num(j.get("internal_lob_count")))
        dl = int(_num(j.get("artifactory_downloads")))
        ver = int(_num(j.get("artifactory_version_count")))
        bucket = _blank(row.get("P"))
        records.append(
            {
                "name": name,
                "bucket": bucket,
                "rank": int(_num(row.get("Rank"))),
                "score100": int(_num(row.get("Score"))),
                "work": _blank(row.get("Work")),
                "plat": plat,
                "apps": apps,
                "ic": ic,
                "lob": lob,
                "dl": dl,
                "ver": ver,
                "vuln": _blank(row.get("vuln_status")),
                "src": _blank(row.get("Priority_Source")),
                "why": _blank(row.get("Priority_Reason")),
                "risk": _blank(row.get("risk_level")),
                "latest": int(_num(row.get("jfrog_latest_vuln_count"))),
                "priority_desc": _blank(row.get("Priority_Bucket_Description")),
            }
        )
    return records


def write_ranked_export(path: Path, records: list[dict]) -> None:
    """Serialize ranking rows for Vizro Epic 22 (Story 22.1)."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for rec in records:
        rows.append(
            {
                "Core_Python_Package_Name": rec["name"],
                "P": rec["bucket"],
                "Rank": rec["rank"],
                "Score": rec["score100"],
                "Work": rec["work"],
                "Platforms": rec["plat"],
                "Apps": rec["apps"],
                "Downloads": rec["dl"],
                "Versions": rec["ver"],
                "Vuln": rec["vuln"],
                "Priority_Bucket_Description": rec["priority_desc"],
                "Priority_Source": rec["src"],
                "Priority_Reason": rec["why"],
                "JFROG_risk_level": rec["risk"],
                "JFROG_latest_vuln_count": rec["latest"],
                "internal_component_count": rec["ic"],
                "internal_lob_count": rec["lob"],
                "Verification_Timestamp_UTC": stamp,
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=RANKED_EXPORT_COLUMNS).to_parquet(path, engine="pyarrow")


def write_ranked_csv(path: Path, records: list[dict]) -> None:
    """Legacy ranked tab shape as CSV (RANK_COLS + DETAIL_COLS)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LEGACY_RANKED_CSV_COLUMNS)
        writer.writeheader()
        for rec in records:
            writer.writerow(
                {
                    "P": rec["bucket"],
                    "Rank": rec["rank"],
                    "Score": rec["score100"],
                    "Package": rec["name"],
                    "Work": rec["work"],
                    "Platforms": rec["plat"],
                    "Apps": rec["apps"],
                    "Downloads": rec["dl"],
                    "Versions": rec["ver"],
                    "Vuln": rec["vuln"],
                    "Priority_Bucket_Description": rec["priority_desc"],
                    "Priority_Source": rec["src"],
                    "Priority_Reason": rec["why"],
                    "JFROG_risk_level": rec["risk"],
                    "JFROG_latest_vuln_count": rec["latest"],
                    "internal_component_count": rec["ic"],
                    "internal_lob_count": rec["lob"],
                }
            )


def write_canvas(path: Path, records: list[dict], counts: dict[str, int], tab: str) -> None:
    canvas_rows = [
        [
            r["name"],
            r["bucket"],
            r["src"],
            r["why"],
            r["plat"],
            r["apps"],
            r["ic"],
            r["lob"],
            r["dl"],
            r["ver"],
            r["vuln"],
            r["rank"],
            r["score100"],
            r["work"],
        ]
        for r in records
    ]
    leaders = []
    for b in BUCKET_ORDER:
        for r in (x for x in records if x["bucket"] == b):
            if sum(1 for row in leaders if row[0] == b) >= 6:
                break
            leaders.append(
                [
                    b,
                    r["name"],
                    r["rank"],
                    r["score100"],
                    r["plat"],
                    r["apps"],
                    r["ic"],
                    r["lob"],
                    r["dl"],
                    r["ver"],
                    r["vuln"] or "",
                    r["src"],
                    r["work"],
                ]
            )
    work_counts = {w: sum(1 for r in records if r["work"] == w) for w in WORK_ORDER}
    bucket_defs = [
        [b, next((r["priority_desc"] for r in records if r["bucket"] == b), ""), counts.get(b, 0)]
        for b in BUCKET_ORDER
    ]
    data = json.dumps(
        {
            "counts": counts,
            "workCounts": work_counts,
            "workOrder": WORK_ORDER,
            "bucketDefs": bucket_defs,
            "rows": canvas_rows,
            "leaders": leaders,
        },
        separators=(",", ":"),
    )
    path.write_text(
        _CANVAS_PREFIX
        + data
        + _CANVAS_SUFFIX.replace("identity-TAB", tab).replace("N_ROWS", f"{len(records):,}"),
        encoding="utf-8",
    )


_CANVAS_PREFIX = r"""import {
  BarChart,
  Button,
  Callout,
  Grid,
  H1,
  H2,
  Row,
  Select,
  Stack,
  Stat,
  Table,
  Text,
  TextInput,
  useCanvasState,
} from "cursor/canvas";

const DATA = """

_CANVAS_SUFFIX = r""" as {
  counts: Record<string, number>;
  workCounts: Record<string, number>;
  workOrder: string[];
  bucketDefs: Array<[string, string, number]>;
  rows: Array<[string, string, string, string, number, number, number, number, number, number, string, number, number, string]>;
  leaders: Array<[string, string, number, number, number, number, number, number, number, number, string, string, string]>;
};

const PAGE = 80;
const BUCKETS = ["All", "P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10"];
const ORDER = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10"];

function fmt(n: number): string {
  return n.toLocaleString("en-US");
}

export default function IdentityPriorityAll() {
  const [bucket, setBucket] = useCanvasState("identity-pri-bucket", "All");
  const [work, setWork] = useCanvasState("identity-pri-work", "All");
  const [q, setQ] = useCanvasState("identity-pri-q", "");
  const [page, setPage] = useCanvasState("identity-pri-page", 0);
  const query = q.trim().toLowerCase();
  const filtered = DATA.rows.filter((r) => {
    if (bucket !== "All" && r[1] !== bucket) return false;
    if (work !== "All" && r[13] !== work) return false;
    if (
      query &&
      !r[0].includes(query) &&
      !r[2].includes(query) &&
      !r[3].toLowerCase().includes(query) &&
      !r[13].toLowerCase().includes(query)
    ) {
      return false;
    }
    return true;
  });
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE));
  const safePage = Math.min(page, pages - 1);
  const slice = filtered.slice(safePage * PAGE, safePage * PAGE + PAGE);

  return (
    <Stack gap={20}>
      <Stack gap={6}>
        <H1>Priority for every identity-TAB package</H1>
        <Text tone="secondary" size="small">
          N_ROWS rows. Fix vulnerability is its own work bucket and P1.
          Board P2–P3 locked. P4 platforms, P5 apps, P6 100+ downloads or
          versions, P7 10+. Leftover: P8 Create recipe, P9 File OpenTeams
          tracking issue [Conda-Forge Packaging] (JFROG on conda-forge), P10
          same tracking issue (CDO-ENT-CONDA) + already-tracked remainder.
          Score is 1–100 use only. Source: inventory_priority_assignments.parquet.
        </Text>
      </Stack>

      <Grid columns={4} gap={12}>
        <Stat value={fmt(DATA.workCounts["Fix vulnerability"] || 0)} label="Fix vulnerability" tone="danger" />
        <Stat value={fmt(DATA.workCounts["Create recipe"] || 0)} label="Create recipe" tone="warning" />
        <Stat value={fmt(DATA.counts.P8)} label="P8 leftover new packages" />
        <Stat value={fmt(DATA.counts.P10)} label="P10 conda-only / already tracked" />
      </Grid>

      <Callout tone="info">
        Work labels: Fix vulnerability (current-version HIGH / affected_latest),
        Create recipe (JFROG, not on conda-forge), File OpenTeams tracking
        issue [Conda-Forge Packaging] (already on conda-forge, missing the
        board issue), Already tracked. Score stays
        100×platforms + 10×apps + 3×components + 2×LOBs + log10(1+downloads) +
        log10(1+versions), percentile 1–100.
      </Callout>

      <H2>Priority buckets</H2>
      <Table
        striped
        stickyHeader
        headers={["Bucket", "Packages", "Description"]}
        columnAlign={["left", "right", "left"]}
        rows={DATA.bucketDefs.map((d) => [d[0], fmt(d[2]), d[1]])}
      />
      <Text tone="secondary" size="small">
        Proposed_Priority on identity-TAB, with Priority_Bucket_Description on each row.
      </Text>

      <H2>Bucket counts</H2>
      <BarChart
        horizontal
        height={280}
        categories={ORDER}
        series={[
          {
            name: "packages",
            data: ORDER.map((b) => DATA.counts[b] || 0),
            tone: "info",
          },
        ]}
        showValues
      />
      <Text tone="secondary" size="small">
        Package counts by Proposed_Priority.
      </Text>

      <H2>Work type</H2>
      <BarChart
        horizontal
        height={160}
        categories={DATA.workOrder}
        series={[
          {
            name: "packages",
            data: DATA.workOrder.map((w) => DATA.workCounts[w] || 0),
            tone: "warning",
          },
        ]}
        showValues
      />
      <Text tone="secondary" size="small">
        What Mason does. Fix vulnerability first; Create recipe is packaging;
        the issue rows are board coverage.
      </Text>

      <H2>Top of each bucket</H2>
      <Table
        striped
        stickyHeader
        headers={[
          "P",
          "Rank",
          "Score",
          "Package",
          "Work",
          "Platforms",
          "Apps",
          "Downloads",
          "Versions",
          "Vuln",
        ]}
        columnAlign={["left", "right", "right", "left", "left", "right", "right", "right", "right", "left"]}
        rows={DATA.leaders.map((r) => [
          r[0],
          fmt(r[2]),
          fmt(r[3]),
          r[1],
          r[12],
          fmt(r[4]),
          fmt(r[5]),
          fmt(r[8]),
          fmt(r[9]),
          r[10] || "—",
        ])}
      />

      <H2>All packages</H2>
      <Row gap={8} align="center" wrap>
        <Select
          value={bucket}
          onChange={(v) => {
            setBucket(v);
            setPage(0);
          }}
          options={BUCKETS.map((b) => ({
            value: b,
            label:
              b === "All"
                ? `All (${fmt(DATA.rows.length)})`
                : `${b} (${fmt(DATA.counts[b] || 0)})`,
          }))}
        />
        <Select
          value={work}
          onChange={(v) => {
            setWork(v);
            setPage(0);
          }}
          options={[
            { value: "All", label: "All work" },
            ...DATA.workOrder.map((w) => ({
              value: w,
              label: `${w} (${fmt(DATA.workCounts[w] || 0)})`,
            })),
          ]}
        />
        <TextInput
          value={q}
          onChange={(v) => {
            setQ(v);
            setPage(0);
          }}
          placeholder="Filter by package, source, or reason"
        />
        <Text tone="secondary" size="small">
          {fmt(filtered.length)} rows · page {safePage + 1}/{pages}
        </Text>
      </Row>
      <Row gap={8}>
        <Button onClick={() => setPage(Math.max(0, safePage - 1))}>Previous</Button>
        <Button onClick={() => setPage(Math.min(pages - 1, safePage + 1))}>Next</Button>
      </Row>
      <Table
        striped
        stickyHeader
        headers={[
          "Rank",
          "P",
          "Score",
          "Package",
          "Work",
          "Platforms",
          "Apps",
          "Components",
          "LOBs",
          "Downloads",
          "Versions",
          "Reason",
        ]}
        columnAlign={[
          "right",
          "left",
          "right",
          "left",
          "left",
          "right",
          "right",
          "right",
          "right",
          "right",
          "right",
          "left",
        ]}
        rows={slice.map((r) => [
          fmt(r[11]),
          r[1],
          fmt(r[12]),
          r[0],
          r[13],
          fmt(r[4]),
          fmt(r[5]),
          fmt(r[6]),
          fmt(r[7]),
          fmt(r[8]),
          fmt(r[9]),
          r[3],
        ])}
      />
    </Stack>
  );
}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--xlsx",
        type=Path,
        default=None,
        help="Retired by Story 23.9 — exits 2 with a pointer to the Atlas export.",
    )
    parser.add_argument(
        "--tab",
        default=None,
        help="Retired by Story 23.9 — exits 2 with a pointer to the Atlas export.",
    )
    parser.add_argument(
        "--priority-assignments",
        type=Path,
        default=None,
        help=(
            "Atlas inventory_priority_assignments input (Story 23.3). "
            f"Default: ${{PYFORGE_ATLAS_DATA_ROOT}}/{PRIORITY_ASSIGNMENTS_RELPATH}"
        ),
    )
    parser.add_argument(
        "--jfrog-parquet",
        type=Path,
        default=None,
        help=(
            "Optional enterprise_jfrog_consumption join for telemetry columns. "
            f"Default: ${{PYFORGE_ATLAS_DATA_ROOT}}/{ENTERPRISE_JFROG_RELPATH}"
        ),
    )
    parser.add_argument(
        "--ranked-export",
        type=Path,
        default=None,
        help=(
            "Parquet output for Vizro Epic 22. "
            f"Default: ${{PYFORGE_ATLAS_DATA_ROOT}}/{IDENTITY_RANKED_EXPORT_RELPATH}"
        ),
    )
    parser.add_argument(
        "--ranked-csv",
        type=Path,
        default=None,
        help="Optional legacy ranked CSV (replaces the retired workbook ranked tab).",
    )
    parser.add_argument(
        "--canvas",
        type=Path,
        default=Path(
            "/home/rxm7706/.cursor/projects/home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/canvases/identity-2026-08-20.canvas.tsx"
        ),
    )
    parser.add_argument(
        "--canvas-tab-label",
        default="identity-2026-08-12",
        help="Label substituted into the catalog canvas title (display only).",
    )
    args = parser.parse_args()

    if args.xlsx is not None or args.tab is not None:
        print(_RETIRED_WORKBOOK_MSG, file=sys.stderr)
        return 2

    priority_path = args.priority_assignments or default_priority_assignments_path()
    jfrog_path = args.jfrog_parquet or default_jfrog_consumption_path()
    ranked_export = args.ranked_export or default_ranked_export_path()

    assignments = load_priority_assignments(priority_path)
    jfrog_df = load_jfrog_consumption(jfrog_path)
    jfrog_by = _jfrog_lookup(jfrog_df)
    records = assignments_to_records(assignments, jfrog_by)

    counts = {b: sum(1 for r in records if r["bucket"] == b) for b in BUCKET_ORDER}
    print("TOTAL", len(records))
    print("bucket", counts)
    print("work", dict(Counter(r["work"] for r in records)))
    print("source", dict(Counter(r["src"] for r in records)))
    if records:
        scores = [r["score100"] for r in records]
        print("score 1-100 min/max", min(scores), max(scores))

    write_ranked_export(ranked_export, records)
    print("wrote", ranked_export)

    if args.ranked_csv:
        write_ranked_csv(args.ranked_csv, records)
        print("wrote", args.ranked_csv)

    if args.canvas:
        args.canvas.parent.mkdir(parents=True, exist_ok=True)
        write_canvas(args.canvas, records, counts, args.canvas_tab_label)
        print("wrote", args.canvas)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
