#!/usr/bin/env python3
"""Assign Proposed_Priority on identity-2026-08-12.

Hierarchy (board P2–P3 kept when they are not current-version vulns):
  P1     current-version vulnerability → work Fix vulnerability
         (plus existing board P1 that are not vulns)
  P2–P3  existing OpenTeams packaging-issue Priority
  P4     platform_env_count > 0
  P5     internal_app_count > 0 (no platform)
  P6     100+ Artifactory downloads or 100+ Artifactory versions
  P7     10+ downloads or 10+ versions (and not already P6)
  P8     leftover Create recipe (JFROG, not on conda-forge)
  P9     leftover File issue (on conda-forge)
  P0     leftover File issue (maintained feedstock) + Already tracked remainder

Packaging_Work replaces OpenTeams_Batch A/B/C/TRACKED with the work itself.
Priority_Score is 1..100 from the use formula; work type does not inflate it.
JFROG packaging_tier is ignored.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook

PACK = re.compile(r"^\[Conda-Forge Packaging\]\s+(.+?)\s*$", re.I)
TAB = "identity-2026-08-12"
BUCKET_ORDER = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P0"]
PRI_N = {b: i for i, b in enumerate(BUCKET_ORDER, start=1)}
WORK_FIX_VULN = "Fix vulnerability"
WORK_CREATE = "Create recipe"
WORK_ISSUE_CF = "File issue (on conda-forge)"
WORK_ISSUE_MAINT = "File issue (maintained feedstock)"
WORK_TRACKED = "Already tracked"
WORK_ORDER = [WORK_FIX_VULN, WORK_CREATE, WORK_TRACKED, WORK_ISSUE_CF, WORK_ISSUE_MAINT]
WORK_RANK = {w: i for i, w in enumerate(WORK_ORDER)}
BATCH_TO_WORK = {
    "A": WORK_CREATE,
    "B": WORK_ISSUE_CF,
    "C": WORK_ISSUE_MAINT,
    "TRACKED": WORK_TRACKED,
    WORK_FIX_VULN: WORK_FIX_VULN,
    WORK_CREATE: WORK_CREATE,
    WORK_ISSUE_CF: WORK_ISSUE_CF,
    WORK_ISSUE_MAINT: WORK_ISSUE_MAINT,
    WORK_TRACKED: WORK_TRACKED,
}
PRIORITY_DESC = {
    "P1": "Current-version vulnerability: the latest release has confirmed advisories (HIGH / affected_latest). Existing OpenTeams board P1 also stays here.",
    "P2": "Existing OpenTeams board P2. Not overwritten.",
    "P3": "Existing OpenTeams board P3. Not overwritten.",
    "P4": "Used in one or more platform environments (platform_env_count > 0).",
    "P5": "Used by internal applications, but not in a platform environment.",
    "P6": "Heavy Artifactory use: 100+ downloads or 100+ versions, and not already P1–P5.",
    "P7": "Moderate Artifactory use: 10+ downloads or 10+ versions, below the P6 floor.",
    "P8": "Leftover new packaging: consumed from JFROG, not on conda-forge, below the P7 floor (Create recipe).",
    "P9": "Leftover board coverage: already on conda-forge, missing an OpenTeams issue, below the P7 floor.",
    "P0": "Lowest leftover: maintained feedstock missing an issue, or already tracked with little Artifactory use.",
}
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
# Drop previous ranking headers so a rewrite does not duplicate them.
NEW_COLS = RANK_COLS + DETAIL_COLS + [
    "Proposed_Priority",
    "Packaging_Work",
    "Priority_Rank",
    "Priority_Score",
    "JFROG_vuln_status",
    "platform_env_count",
    "internal_app_count",
    "artifactory_downloads",
    "artifactory_version_count",
]


def pep503(raw) -> str | None:
    if raw is None or isinstance(raw, datetime):
        return None
    s = str(raw).strip().lower().replace("_", "-").replace(".", "-")
    s = re.sub(r"-+", "-", s).strip("-")
    return s if len(s) >= 2 else None


def num(v) -> float:
    try:
        return float(v) if v not in (None, "") else 0.0
    except (TypeError, ValueError):
        return 0.0


def load_tab(wb, name: str):
    ws = wb[name]
    it = ws.iter_rows(values_only=True)
    header = [str(h) if h is not None else "" for h in next(it)]
    rows = []
    for raw in it:
        rows.append({h: (raw[i] if i < len(raw) else None) for i, h in enumerate(header)})
    return header, rows


def use_score(plat: int, apps: int, ic: int, lob: int, downloads: int, versions: int) -> float:
    """Earlier use score + Artifactory version count. Not scaled to 1–100."""
    return (
        100.0 * plat
        + 10.0 * apps
        + 3.0 * ic
        + 2.0 * lob
        + math.log10(1.0 + downloads)
        + math.log10(1.0 + versions)
    )


def percentile_1_100(raws: list[float]) -> list[int]:
    n = len(raws)
    if n == 1:
        return [100]
    order = sorted(range(n), key=lambda i: (raws[i], i))
    out = [1] * n
    for rank, i in enumerate(order):
        out[i] = 1 + int(round(99.0 * rank / (n - 1)))
    return out


def board_maps(ot_rows: list[dict]) -> tuple[dict, dict]:
    by_url, by_name = {}, {}
    for r in ot_rows:
        m = PACK.match(str(r.get("Title") or ""))
        if not m:
            continue
        rec = {
            "priority": str(r.get("Priority") or "").strip(),
            "url": str(r.get("URL") or "").strip(),
        }
        if rec["url"]:
            by_url[rec["url"]] = rec
        n = pep503(m.group(1))
        if n:
            by_name[n] = rec
    return by_url, by_name


def board_lock(ident: dict, name: str | None, by_url: dict, by_name: dict) -> str | None:
    url = str(ident.get("OpenTeams_Issue_URL") or "").strip()
    rec = by_url.get(url) or by_name.get(name or "")
    if not rec:
        return None
    p = rec["priority"]
    if p.startswith("P1"):
        return "P1"
    if p.startswith("P2"):
        return "P2"
    if p.startswith("P3"):
        return "P3"
    return None


def _filled(raw) -> bool:
    s = str(raw or "").strip()
    return bool(s) and s.upper() not in {"N/A", "NA", "NONE", "-"}


def is_current_vuln(j: dict | None) -> bool:
    if not j:
        return False
    return str(j.get("risk_level") or "") == "HIGH" or str(j.get("vuln_status") or "") == "affected_latest"


def work_label(ident: dict, inv: dict | None, j: dict | None) -> str:
    """Work Mason actually does. Current-version vuln wins over recipe/issue/tracked."""
    if is_current_vuln(j):
        return WORK_FIX_VULN
    if inv:
        mapped = BATCH_TO_WORK.get(str(inv.get("OpenTeams_Batch") or "").strip())
        if mapped and mapped != WORK_FIX_VULN:
            return mapped
        cohort = str(inv.get("OpenTeams_Cohort") or "").strip()
        coverage = str(inv.get("OpenTeams_Coverage") or "").strip()
        if coverage == "Have_Issue":
            return WORK_TRACKED
        if cohort == "JFROG_NEW":
            return WORK_CREATE
        if cohort == "JFROG_ON_CF":
            return WORK_ISSUE_CF
        if cohort == "CONDA_ONLY":
            return WORK_ISSUE_MAINT
    if _filled(ident.get("OpenTeams_Issue_URL")):
        return WORK_TRACKED
    if _filled(ident.get("conda_purl")) or _filled(ident.get("Conda-Forge_FeedStock_URL")):
        return WORK_ISSUE_CF
    return WORK_CREATE


def assign_lane(ident, name, j, by_url, by_name) -> tuple[str | None, str, str]:
    plat = int(num(j.get("platform_env_count")) if j else 0)
    apps = int(num(j.get("internal_app_count")) if j else 0)
    dl = int(num(j.get("artifactory_downloads")) if j else 0)
    ver = int(num(j.get("artifactory_version_count")) if j else 0)
    risk = str(j.get("risk_level") or "") if j else ""
    vuln = str(j.get("vuln_status") or "") if j else ""
    if risk == "HIGH" or vuln == "affected_latest":
        return "P1", "current-version-vuln", "latest version has confirmed advisories"
    locked = board_lock(ident, name, by_url, by_name)
    if locked:
        return locked, "openteams-board", "existing board P1-P3, not overwritten"
    if plat > 0:
        return "P4", "platform", "platform_env_count > 0"
    if apps > 0:
        return "P5", "app", "internal_app_count > 0"
    if dl >= 100 or ver >= 100:
        return (
            "P6",
            "download-version-floor-100",
            "100+ Artifactory downloads or 100+ versions",
        )
    if dl >= 10 or ver >= 10:
        return (
            "P7",
            "download-version-floor-10",
            "10+ Artifactory downloads or 10+ versions",
        )
    return None, "remainder", "leftover split by packaging work"


def write_canvas(path: Path, records: list[dict], counts: dict[str, int]) -> None:
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
    data = json.dumps(
        {
            "counts": counts,
            "workCounts": work_counts,
            "workOrder": WORK_ORDER,
            "bucketDefs": [[b, PRIORITY_DESC[b], counts.get(b, 0)] for b in BUCKET_ORDER],
            "rows": canvas_rows,
            "leaders": leaders,
        },
        separators=(",", ":"),
    )
    path.write_text(
        _CANVAS_PREFIX + data + _CANVAS_SUFFIX,
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
const BUCKETS = ["All", "P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P0"];
const ORDER = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P0"];

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
        <H1>Priority for every identity-2026-08-12 package</H1>
        <Text tone="secondary" size="small">
          7,515 rows. Fix vulnerability is its own work bucket and P1.
          Board P2–P3 locked. P4 platforms, P5 apps, P6 100+ downloads or
          versions, P7 10+. Leftover: P8 Create recipe, P9 File issue (on
          conda-forge), P0 maintained feedstock + already-tracked remainder.
          Score is 1–100 use only. Source: identity tab on
          docs/Analysis_Dataset-2026-08-12.xlsx.
        </Text>
      </Stack>

      <Grid columns={4} gap={12}>
        <Stat value={fmt(DATA.workCounts["Fix vulnerability"] || 0)} label="Fix vulnerability" tone="danger" />
        <Stat value={fmt(DATA.workCounts["Create recipe"] || 0)} label="Create recipe" tone="warning" />
        <Stat value={fmt(DATA.counts.P8)} label="P8 leftover new packages" />
        <Stat value={fmt(DATA.counts.P0)} label="P0 maintained / already tracked" />
      </Grid>

      <Callout tone="info">
        Work labels: Fix vulnerability (current-version HIGH / affected_latest),
        Create recipe (JFROG, not on conda-forge), File issue (on conda-forge),
        File issue (maintained feedstock), Already tracked. Score stays
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
        Proposed_Priority on identity-2026-08-12, with Priority_Bucket_Description on each row.
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
    repo = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xlsx", type=Path, default=repo / "docs/Analysis_Dataset-2026-08-12.xlsx")
    parser.add_argument(
        "--canvas",
        type=Path,
        default=Path(
            "/home/rxm7706/.cursor/projects/home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/canvases/identity-priority-p4-p10.canvas.tsx"
        ),
    )
    args = parser.parse_args()

    wb = load_workbook(args.xlsx, data_only=True)
    ident_header, ident_rows = load_tab(wb, TAB)
    _, jfrog_rows = load_tab(wb, "CDO-ENT-JFROG")
    _, ot_rows = load_tab(wb, "OpenTeams")
    _, inv_rows = load_tab(wb, "inventory-2026-08-12")
    wb.close()

    jfrog: dict[str, dict] = {}
    for r in jfrog_rows:
        k = pep503(r.get("name"))
        if k:
            jfrog[k] = r
    inv_by = {
        pep503(r.get("Core_Python_Package_Name")): r
        for r in inv_rows
        if pep503(r.get("Core_Python_Package_Name"))
    }
    by_url, by_name = board_maps(ot_rows)

    records = []
    for idx, ident in enumerate(ident_rows):
        name = pep503(ident.get("Core_Python_Package_Name")) or str(
            ident.get("Core_Python_Package_Name") or ""
        )
        j = jfrog.get(pep503(ident.get("Core_Python_Package_Name")) or "")
        plat = int(num(j.get("platform_env_count")) if j else 0)
        apps = int(num(j.get("internal_app_count")) if j else 0)
        ic = int(num(j.get("internal_component_count")) if j else 0)
        lob = int(num(j.get("internal_lob_count")) if j else 0)
        dl = int(num(j.get("artifactory_downloads")) if j else 0)
        ver = int(num(j.get("artifactory_version_count")) if j else 0)
        risk = str(j.get("risk_level") or "") if j else ""
        vuln = str(j.get("vuln_status") or "") if j else ""
        latest = int(num(j.get("basilisk_latest_version_known_vulnerabilities_count")) if j else 0)
        raw = use_score(plat, apps, ic, lob, dl, ver)
        inv = inv_by.get(pep503(ident.get("Core_Python_Package_Name")) or "")
        work = work_label(ident, inv, j)
        bucket, src, why = assign_lane(ident, pep503(ident.get("Core_Python_Package_Name")), j, by_url, by_name)
        records.append(
            {
                "idx": idx,
                "name": name,
                "ident": ident,
                "work": work,
                "bucket": bucket,
                "src": src,
                "why": why,
                "plat": plat,
                "apps": apps,
                "ic": ic,
                "lob": lob,
                "dl": dl,
                "ver": ver,
                "risk": risk,
                "vuln": vuln,
                "latest": latest,
                "raw": raw,
            }
        )

    scores = percentile_1_100([r["raw"] for r in records])
    for r, s in zip(records, scores):
        r["score100"] = s

    remainder = [r for r in records if r["bucket"] is None]
    for r in remainder:
        if r["work"] == WORK_CREATE:
            tier, src = "P8", "work-create-recipe"
            why = "leftover Create recipe: JFROG consumed, not on conda-forge"
        elif r["work"] == WORK_ISSUE_CF:
            tier, src = "P9", "work-file-issue-on-cf"
            why = "leftover File issue (on conda-forge)"
        elif r["work"] == WORK_ISSUE_MAINT:
            tier, src = "P0", "work-file-issue-maintained"
            why = "leftover File issue (maintained feedstock)"
        else:
            tier, src = "P0", "work-already-tracked-remainder"
            why = "leftover Already tracked"
        r["bucket"] = tier
        r["src"] = src
        r["why"] = f"{why} (score {r['score100']})"

    def sort_key(r: dict):
        return (
            PRI_N[r["bucket"]],
            WORK_RANK.get(r["work"], 9),
            -r["score100"],
            -r["raw"],
            -r["dl"],
            -r["ver"],
            r["name"],
        )

    records.sort(key=sort_key)
    for i, r in enumerate(records, start=1):
        r["rank"] = i

    counts = {b: sum(1 for r in records if r["bucket"] == b) for b in BUCKET_ORDER}
    print("TOTAL", len(records))
    print("bucket", counts)
    print("work", dict(Counter(r["work"] for r in records)))
    print("source", dict(Counter(r["src"] for r in records)))
    print("score 1-100 min/max", min(r["score100"] for r in records), max(r["score100"] for r in records))
    print("work x priority")
    for w in WORK_ORDER:
        xs = [r for r in records if r["work"] == w]
        xt = Counter(r["bucket"] for r in xs)
        print(f"  {w}: n={len(xs)} " + " ".join(f"{b}={xt[b]}" for b in BUCKET_ORDER if xt[b]))
    for b in BUCKET_ORDER:
        xs = [r for r in records if r["bucket"] == b]
        print(f"{b} n={len(xs)}")
        if xs:
            print(
                f"  score {min(r['score100'] for r in xs)}-{max(r['score100'] for r in xs)} "
                f"dl {min(r['dl'] for r in xs)}-{max(r['dl'] for r in xs)} "
                f"ver {min(r['ver'] for r in xs)}-{max(r['ver'] for r in xs)} "
                f"work {dict(Counter(r['work'] for r in xs))}"
            )
        for r in xs[:5]:
            print(
                f"  #{r['rank']:<5} score={r['score100']:3} {r['name']:<40} "
                f"{r['work']:<36} dl={r['dl']:7} ver={r['ver']:4}"
            )

    orig_keep = [c for c in ident_header if c and c not in NEW_COLS]
    out_header = RANK_COLS + orig_keep + DETAIL_COLS
    by_idx = {r["idx"]: r for r in records}

    wb2 = load_workbook(args.xlsx)
    if TAB in wb2.sheetnames:
        del wb2[TAB]
    ws = wb2.create_sheet(TAB)
    ws.append(out_header)
    for idx, ident in enumerate(ident_rows):
        rec = by_idx[idx]
        pkg = ident.get("Core_Python_Package_Name") or rec["name"]
        row = [
            rec["bucket"],
            rec["rank"],
            rec["score100"],
            pkg,
            rec["work"],
            rec["plat"],
            rec["apps"],
            rec["dl"],
            rec["ver"],
            rec["vuln"] or "",
        ]
        row.extend("" if ident.get(c) is None else ident.get(c) for c in orig_keep)
        row.extend(
            [
                PRIORITY_DESC.get(rec["bucket"], ""),
                rec["src"],
                rec["why"],
                rec["risk"],
                rec["latest"],
                rec["ic"],
                rec["lob"],
            ]
        )
        ws.append(row)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    inv_ws = wb2["inventory-2026-08-12"]
    inv_header = [c.value for c in next(inv_ws.iter_rows(min_row=1, max_row=1))]
    batch_i = inv_header.index("OpenTeams_Batch")
    name_i = inv_header.index("Core_Python_Package_Name")
    pri_i = inv_header.index("Priority_Bucket") if "Priority_Bucket" in inv_header else None
    if "Priority_Bucket_Description" in inv_header:
        desc_col = inv_header.index("Priority_Bucket_Description") + 1
    else:
        desc_col = len(inv_header) + 1
        inv_ws.cell(1, desc_col, "Priority_Bucket_Description")
    bucket_by_name = {r["name"]: r["bucket"] for r in records}
    n_relabel = 0
    n_pri = 0
    for row in inv_ws.iter_rows(min_row=2):
        name = pep503(row[name_i].value)
        j = jfrog.get(name or "")
        if is_current_vuln(j):
            new = WORK_FIX_VULN
        else:
            old = str(row[batch_i].value or "").strip()
            new = BATCH_TO_WORK.get(old, old)
            if new == WORK_FIX_VULN:
                new = WORK_TRACKED if _filled(row[batch_i].value) else old
        if new and new != str(row[batch_i].value or "").strip():
            row[batch_i].value = new
            n_relabel += 1
        bucket = bucket_by_name.get(name or "")
        if bucket:
            if pri_i is not None and str(row[pri_i].value or "") != bucket:
                row[pri_i].value = bucket
                n_pri += 1
            inv_ws.cell(row[0].row, desc_col, PRIORITY_DESC[bucket])
    wb2.save(args.xlsx)
    wb2.close()
    print("identity header", out_header[:10], "... total", len(out_header))
    print("relabeled inventory OpenTeams_Batch", n_relabel)
    print("synced inventory Priority_Bucket", n_pri)

    if args.canvas:
        args.canvas.parent.mkdir(parents=True, exist_ok=True)
        write_canvas(args.canvas, records, counts)
        print("wrote", args.canvas)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
