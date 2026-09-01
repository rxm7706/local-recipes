"""GFM dashboards published beside the identity gist row catalog.

Rendered by conda-forge-packaging-inventory-operations_openteams_identity.py
--gist-only. Matches the identity-ops and jfrog-workbook canvases.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

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
    "P10": "Lowest leftover: CDO-ENT-CONDA name missing an OpenTeams tracking issue, or already tracked with little Artifactory use.",
}
WORK_DESC = {
    "Fix vulnerability": "Latest release has confirmed advisories (HIGH / affected_latest). Always P1.",
    "Create recipe": "Not on conda-forge. Needs a feedstock (usually a staged-recipes PR).",
    "File OpenTeams tracking issue [Conda-Forge Packaging]": "Already on conda-forge. Still missing the OpenTeams issue titled `[Conda-Forge Packaging] {name}`.",
    "Already tracked": "Already has that OpenTeams packaging issue. No new tracker work.",
}
PRIORITY_HOW = [
    "First-match top-down. There is no P0. Floor is P10.",
    "P1: current-version HIGH / affected_latest, plus leftover board P1.",
    "P2 and P3: existing OpenTeams packaging-issue Priority. Not overwritten unless the name is P1.",
    "P4: platform_env_count > 0.",
    "P5: internal_app_count > 0 and not already P1–P4.",
    "P6: 100+ Artifactory downloads or 100+ versions, not already P1–P5.",
    "P7: 10+ downloads or 10+ versions, below the P6 floor.",
    "P8: leftover Create recipe (JFROG consumed, not on conda-forge).",
    "P9: leftover File OpenTeams tracking issue for JFROG names already on conda-forge.",
    "P10: leftover File OpenTeams tracking issue for CDO-ENT-CONDA names, plus already-tracked remainder.",
    "Score (1–100) is use-only (platforms, apps, components, LOBs, downloads, versions). It ranks inside a P; it does not pick the P.",
    "Work is independent of leftover P: Fix vulnerability / Create recipe / File OpenTeams tracking issue [Conda-Forge Packaging] / Already tracked.",
]

EXTERNAL_LIVE = [
    ("Anaconda Dist 2026.x", "639", "HTML 2026.x table", "639 (Anaaconda-Dist)"),
    ("Anaconda main", "5461", "pkgs/main channeldata.json", "5,458 (Anaconda-Main)"),
    ("conda-forge", "33875", "conda-forge channeldata.json", "33,875 (Conda-Forge)"),
    ("Basilisk /v1/packages", "33853", "api.basilisk.prefix.dev", "33,853 (Basilisk)"),
    ("AOSS free Python", "1466", "docs #python list", "1,474 (GAOSS-Free)"),
    ("AOSS premium Python", "2114", "Wayback Python <ul>", "2,114 (GAOSS-Premium)"),
    ("about maintainers", "559", "README As Maintainer", "n/a"),
    ("about co-maintainers", "255", "README As Co-Maintainer", "n/a"),
]

ENTERPRISE_JFROG_RELPATH = Path(
    "derived/enterprise_jfrog_consumption/enterprise_jfrog_consumption.parquet"
)
INVENTORY_UNIVERSE_RELPATH = Path("derived/inventory_universe/inventory_universe.parquet")

CATALOG_SOURCE_FLAGS: tuple[tuple[str, str], ...] = (
    ("tab:CDO-ENT-JFROG", "in_cdo_ent_jfrog"),
    ("tab:CDO-ENT-CONDA", "in_cdo_ent_conda"),
    ("tab:OpenTeams", "in_openteams"),
    ("tab:Conda-Forge", "in_conda_forge"),
    ("tab:Basilisk", "in_basilisk"),
    ("tab:Anaconda-Main", "in_anaconda_main"),
    ("tab:Anaaconda-Dist", "in_anaconda_dist"),
    ("tab:GAOSS-Free", "in_aoss_free"),
    ("tab:GAOSS-Premium", "in_aoss_premium"),
)


def data_root_from_export(export_path: Path) -> Path:
    """Resolve ``PYFORGE_ATLAS_DATA_ROOT`` from an export Parquet path."""
    return export_path.parent.parent.parent


def jfrog_parquet_path(export_path: Path) -> Path:
    return data_root_from_export(export_path) / ENTERPRISE_JFROG_RELPATH


def inventory_universe_parquet_path(export_path: Path) -> Path:
    return data_root_from_export(export_path) / INVENTORY_UNIVERSE_RELPATH


def _flag_true(row: dict, flag: str) -> bool:
    val = row.get(flag)
    if isinstance(val, bool):
        return val
    return str(val or "").strip().lower() in {"true", "1", "yes"}


def _input_names(row: dict) -> list[str]:
    raw = row.get("package_input_names") or row.get("Package_Input_Names") or ""
    if isinstance(raw, (list, tuple)):
        return [str(v).strip() for v in raw if str(v).strip()]
    text = str(raw).strip()
    if not text:
        return []
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = json.loads(text.replace("'", '"'))
            if isinstance(parsed, list):
                return [str(v).strip() for v in parsed if str(v).strip()]
        except json.JSONDecodeError:
            pass
    if "; " in text:
        return [part.strip() for part in text.split("; ") if part.strip()]
    return [text]


def read_parquet_records(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    try:
        df = pd.read_parquet(path)
    except Exception:
        return []
    out: list[dict[str, str]] = []
    for row in df.to_dict(orient="records"):
        rec: dict[str, str] = {}
        for key, val in row.items():
            k = str(key)
            if val is None or (isinstance(val, float) and pd.isna(val)):
                rec[k] = ""
            elif isinstance(val, bool):
                rec[k] = "true" if val else ""
            elif isinstance(val, (list, tuple)):
                rec[k] = "; ".join(str(v) for v in val)
            else:
                rec[k] = str(val).strip()
        out.append(rec)
    return out


def load_jfrog_by(
    export_path: Path, pep503_name
) -> tuple[dict[str, dict[str, str]], int]:
    """Load CDO-ENT-JFROG rows from ``enterprise_jfrog_consumption.parquet``."""
    path = jfrog_parquet_path(export_path)
    jfrog_by: dict[str, dict[str, str]] = {}
    skip = 0
    if not path.is_file():
        return jfrog_by, skip
    try:
        df = pd.read_parquet(path)
    except Exception:
        return jfrog_by, skip
    if "repository_source" in df.columns:
        df = df[df["repository_source"] == "CDO-ENT-JFROG"]
    for row in df.to_dict(orient="records"):
        raw = str(row.get("core_python_package_name") or row.get("name") or "").strip()
        k = pep503_name(raw) if raw else ""
        if not k or len(k) == 1:
            skip += 1
            continue
        jfrog_by.setdefault(
            k,
            {
                "name": raw,
                "artifactory_downloads": str(row.get("artifactory_downloads") or "0"),
                "platform_env_count": str(row.get("platform_env_count") or "0"),
                "internal_component_count": str(row.get("internal_component_count") or "0"),
                "internal_app_count": str(row.get("internal_app_count") or "0"),
                "packaging_tier": str(row.get("packaging_tier") or ""),
            },
        )
    return jfrog_by, skip


def catalog_source_stats(
    export_path: Path, packaging_name_from_title
) -> list[tuple[str, int, int, int, int, int]]:
    """Per-source row counts from ``inventory_universe.parquet`` (Story 23.8/23.9)."""
    rows = read_parquet_records(inventory_universe_parquet_path(export_path))
    if not rows:
        return []
    stats: list[tuple[str, int, int, int, int, int]] = []
    for label, flag in CATALOG_SOURCE_FLAGS:
        members = [r for r in rows if _flag_true(r, flag)]
        data_rows = len(members)
        names = {
            (r.get("core_python_package_name") or r.get("Core_Python_Package_Name") or "").strip()
            for r in members
        }
        unique_names = len({n for n in names if n})
        a = b = c = 0
        if label == "tab:OpenTeams":
            for row in members:
                titles = _input_names(row)
                if not titles:
                    c += 1
                    continue
                for title in titles:
                    if packaging_name_from_title(title):
                        a += 1
                    elif title.strip():
                        b += 1
                    else:
                        c += 1
        stats.append((label, data_rows, unique_names, a, b, c))
    return stats


def render(
    records: list[dict[str, str]],
    export_path: Path,
    gist_id: str,
    tab: str,
    helpers,
) -> str:
    overlay_live_local = helpers.overlay_live_local
    load_local_recipe_type = helpers.load_local_recipe_type
    row_recipe_type = helpers.row_recipe_type
    pep503_name = helpers.pep503_name
    packaging_name_from_title = helpers.packaging_name_from_title
    file_sha256 = helpers.file_sha256
    md_table = helpers.md_table
    as_int = helpers._as_int
    p_order = helpers.P_ORDER
    recipe_type_order = helpers.RECIPE_TYPE_ORDER
    gist_filename = helpers.GIST_FILENAME
    repo_root = helpers.REPO_ROOT
    work_order = helpers.WORK_DASH_ORDER

    overlay_live_local(records, repo_root / "recipes")
    dir_types = load_local_recipe_type(repo_root / "recipes")
    ts = (records[0].get("Verification_Timestamp_UTC") if records else "") or (
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    sha = file_sha256(export_path) if export_path.is_file() else ""
    n = len(records)
    ident = {
        pep503_name(r.get("Core_Python_Package_Name") or ""): r for r in records
    }

    def status_of(row: dict[str, str]) -> str:
        return row.get("Local_Build_Status") or "blank"

    def pct(num: int, den: int) -> str:
        return f"{(100 * num / den):.1f}%" if den else "—"

    p_counts = Counter(r.get("P") or "?" for r in records)
    work_counts = Counter(r.get("Work") or "?" for r in records)
    have_issue = sum(1 for r in records if r.get("OpenTeams_Issue_URL"))
    miss_issue = n - have_issue
    miss_by_p: Counter[str] = Counter()
    have_by_p: Counter[str] = Counter()
    miss_by_work: Counter[str] = Counter()
    for r in records:
        p = r.get("P") or "?"
        if r.get("OpenTeams_Issue_URL"):
            have_by_p[p] += 1
        else:
            miss_by_p[p] += 1
            miss_by_work[r.get("Work") or "?"] += 1

    noarch_types = {"noarch-python", "noarch-generic"}
    type_status: dict[str, Counter] = defaultdict(Counter)
    by_p_kind: dict[str, dict[str, Counter]] = defaultdict(
        lambda: {"noarch": Counter(), "other": Counter()}
    )
    for r in records:
        rtype = row_recipe_type(r, dir_types)
        st = status_of(r)
        type_status[rtype][st] += 1
        kind = "noarch" if rtype in noarch_types else "other"
        by_p_kind[r.get("P") or "?"][kind][st] += 1

    fs_n = sum(1 for r in records if r.get("Conda-Forge_FeedStock_URL"))
    needs = sum(1 for r in records if not r.get("Conda-Forge_FeedStock_URL"))
    local_n = sum(1 for r in records if r.get("Local_Recipes_URL"))
    green = sum(1 for r in records if status_of(r) == "success")
    skipped = sum(
        1
        for r in records
        if status_of(r) in {"build-clean-test-blocked", "blocked-missing-ortools"}
    )
    failed = sum(1 for r in records if status_of(r) == "failed")
    staged = sum(1 for r in records if r.get("Staged_Recipes_PR_URL"))
    no_pr = sum(
        1
        for r in records
        if not r.get("Conda-Forge_FeedStock_URL") and not r.get("Staged_Recipes_PR_URL")
    )

    census_rows = []
    for p in p_order:
        bucket = [r for r in records if r.get("P") == p]
        if not bucket:
            continue
        census_rows.append(
            [
                p,
                f"{len(bucket):,}",
                f"{sum(1 for r in bucket if r.get('Conda-Forge_FeedStock_URL')):,}",
                f"{sum(1 for r in bucket if not r.get('Conda-Forge_FeedStock_URL')):,}",
                f"{sum(1 for r in bucket if not r.get('Conda-Forge_FeedStock_URL') and not r.get('Staged_Recipes_PR_URL')):,}",
                f"{sum(1 for r in bucket if r.get('Local_Recipes_URL')):,}",
                f"{sum(1 for r in bucket if status_of(r) == 'success'):,}",
                f"{sum(1 for r in bucket if status_of(r) in {'build-clean-test-blocked', 'blocked-missing-ortools'}):,}",
                f"{sum(1 for r in bucket if status_of(r) == 'failed'):,}",
                f"{sum(1 for r in bucket if status_of(r) in {'not-attempted', 'blank'}):,}",
            ]
        )

    cube_agg: dict[tuple, list[int]] = {}
    for r in records:
        key = (
            r.get("P") or "?",
            r.get("Work") or "?",
            "yes" if r.get("Conda-Forge_FeedStock_URL") else "no",
            "yes" if not r.get("Conda-Forge_FeedStock_URL") else "no",
        )
        agg = cube_agg.setdefault(key, [0, 0, 0, 0, 0, 0])
        agg[0] += 1
        if r.get("Local_Recipes_URL"):
            agg[1] += 1
        st = status_of(r)
        if st == "success":
            agg[2] += 1
        elif st in {"build-clean-test-blocked", "blocked-missing-ortools"}:
            agg[3] += 1
        elif st == "failed":
            agg[4] += 1
        else:
            agg[5] += 1
    cube_rows = []
    for key in sorted(
        cube_agg,
        key=lambda k: (p_order.index(k[0]) if k[0] in p_order else 99, k[1], k[2], k[3]),
    ):
        a = cube_agg[key]
        cube_rows.append([key[0], key[1], key[2], key[3], *[f"{x:,}" for x in a]])

    jfrog_by, skip = load_jfrog_by(export_path, pep503_name)

    def is_pypi(row: dict[str, str] | None) -> bool:
        if not row:
            return False
        return (row.get("primary_type") or "") == "pypi" or (
            row.get("primary_purl") or ""
        ).startswith("pkg:pypi/")

    def is_cf(row: dict[str, str] | None) -> bool:
        if not row:
            return False
        return bool(row.get("conda_purl") or row.get("Conda-Forge_FeedStock_URL"))

    both = pypi_only = cf_only = neither = 0
    neither_rows: list[list[str]] = []
    need_pr = []
    for k, jr in jfrog_by.items():
        ident_row = ident.get(k)
        pypi = is_pypi(ident_row)
        cf = is_cf(ident_row)
        if pypi and cf:
            both += 1
        elif pypi:
            pypi_only += 1
        elif cf:
            cf_only += 1
        else:
            neither += 1
            neither_rows.append(
                [
                    jr.get("name") or k,
                    f"{as_int(jr.get('artifactory_downloads') or '0')}",
                    jr.get("packaging_tier") or "",
                ]
            )
        on_cf = bool(
            ident_row
            and (ident_row.get("Conda-Forge_FeedStock_URL") or ident_row.get("conda_purl"))
        )
        has_pr = bool(ident_row and ident_row.get("Staged_Recipes_PR_URL"))
        if ident_row and not on_cf and not has_pr:
            need_pr.append((jr, ident_row))
    neither_rows.sort(key=lambda r: (-as_int(r[1]), r[0].lower()))
    parseable = len(jfrog_by)
    pick = []
    any_sig = 0
    for jr, ident_row in need_pr:
        plat = as_int(jr.get("platform_env_count") or "0")
        ic = as_int(jr.get("internal_component_count") or "0")
        apps = as_int(jr.get("internal_app_count") or "0")
        if plat > 0 or ic > 0 or apps > 0:
            any_sig += 1
        if plat > 0 and ic > 0:
            pick.append((jr, ident_row, plat, ic, apps))
    pick.sort(key=lambda t: -as_int(t[0].get("artifactory_downloads") or "0"))
    top_dl = sorted(
        need_pr,
        key=lambda t: -as_int(t[0].get("artifactory_downloads") or "0"),
    )[:12]
    board_gap = []
    for k, jr in jfrog_by.items():
        ident_row = ident.get(k)
        if is_pypi(ident_row) and not is_cf(ident_row) and ident_row and not ident_row.get(
            "OpenTeams_Issue_URL"
        ):
            board_gap.append(
                [
                    jr.get("name") or k,
                    f"{as_int(jr.get('artifactory_downloads') or '0')}",
                ]
            )
    board_gap.sort(key=lambda r: (-as_int(r[1]), r[0].lower()))

    catalog_stats = catalog_source_stats(export_path, packaging_name_from_title)

    build_kind_rows = []
    for p in p_order:
        for kind in ("noarch", "other"):
            counts = by_p_kind[p][kind]
            if not sum(counts.values()):
                continue
            build_kind_rows.append(
                [
                    p if kind == "noarch" else "",
                    kind,
                    f"{sum(counts.values()):,}",
                    f"{counts.get('success', 0):,}",
                    f"{counts.get('build-clean-test-blocked', 0):,}",
                    f"{counts.get('failed', 0):,}",
                    f"{counts.get('not-attempted', 0):,}",
                    f"{counts.get('blank', 0):,}",
                ]
            )

    lines: list[str] = [
        "---",
        "id: mgmt-wf-python-modernization-dashboards",
        "title: OpenTeams identity dashboards (canvas companion)",
        "format: gfm-table",
        f"rows_identity: {n}",
        f"generated: {ts}",
        f"source_export: {export_path}",
        f"export_sha256: {sha}",
        "generator: scripts/conda-forge-packaging-inventory-operations_openteams_identity.py --gist-only",
        f"gist_id: {gist_id}",
        f"companion: {gist_filename}",
        "priority_rule: first-match top-down; no P0; floor P10; Score ranks inside P and does not pick P",
        "priority_buckets:",
    ]
    for p in p_order:
        lines.append(f"  {p}:")
        lines.append(f"    n: {p_counts.get(p, 0)}")
        lines.append(f"    rule: {json.dumps(PRIORITY_DESC[p])}")
    lines.append("work_labels:")
    for w in work_order:
        lines.append(f"  {json.dumps(w)}:")
        lines.append(f"    n: {work_counts.get(w, 0)}")
        lines.append(f"    meaning: {json.dumps(WORK_DESC[w])}")
    lines.extend(
        [
        "parse:",
        "  - Narrative GFM. Machine identity rows stay in the companion file at heading ## Identity rows",
        "  - How libraries were prioritized: YAML priority_buckets / work_labels, then heading ## Priority and work",
        "---",
        "",
        "# Identity dashboards",
        "",
        "Companion to the identity row catalog in this gist. Same snapshot as",
        "the three canvases: searchable catalog, identity ops (Priority / Issues /",
        "Builds / Census), Artifactory + workbook (Map / Staged gap / Board gap /",
        "Catalog sources / External).",
        "",
        f"- Identity export: `{export_path}` · **{n:,}** rows · floor P10",
        f"- Generated: `{ts}`",
        f"- Export sha256: `{sha}`",
        f"- Gist id (edit in place; not stored in git): `{gist_id}`",
        "",
        "## Priority and work",
        "",
        "How P is assigned (first match wins; YAML priority_buckets / work_labels is the machine copy):",
        "",
    ]
    )
    for i, how in enumerate(PRIORITY_HOW, start=1):
        lines.append(f"{i}. {how}")
    lines.extend(
        [
        "",
        *md_table(
            ["P", "n", "Rule"],
            [
                [p, f"{p_counts.get(p, 0):,}", PRIORITY_DESC[p]]
                for p in p_order
            ]
            + [["Total", f"{n:,}", "All identity rows. Floor is P10."]],
        ),
        "",
        *md_table(
            ["Work", "n", "Meaning"],
            [
                [w, f"{work_counts.get(w, 0):,}", WORK_DESC[w]]
                for w in work_order
            ],
        ),
        "",
        "## Packaging-issue gap",
        "",
        f"{have_issue:,} of {n:,} have an OpenTeams `[Conda-Forge Packaging]` issue URL.",
        f"**{miss_issue:,}** missing ({pct(miss_issue, n)}).",
        "",
        *md_table(
            ["P", "Identity rows", "Have issue", "Missing", "Missing rate"],
            [
                [
                    p,
                    f"{p_counts.get(p, 0):,}",
                    f"{have_by_p.get(p, 0):,}",
                    f"{miss_by_p.get(p, 0):,}",
                    pct(miss_by_p.get(p, 0), p_counts.get(p, 0)),
                ]
                for p in p_order
            ]
            + [["All", f"{n:,}", f"{have_issue:,}", f"{miss_issue:,}", pct(miss_issue, n)]],
        ),
        "",
        *md_table(
            ["Work", "Missing packaging issue"],
            [
                [w, f"{miss_by_work.get(w, 0):,}"]
                for w in work_order
                if miss_by_work.get(w, 0)
            ],
        ),
        "",
        "## Local build (CFE stamp)",
        "",
        *md_table(
            ["Type", "Rows", "Success", "Test-blocked", "Failed", "Not attempted", "Blank"],
            [
                [
                    rtype,
                    f"{sum(type_status[rtype].values()):,}",
                    f"{type_status[rtype].get('success', 0):,}",
                    f"{type_status[rtype].get('build-clean-test-blocked', 0):,}",
                    f"{type_status[rtype].get('failed', 0):,}",
                    f"{type_status[rtype].get('not-attempted', 0):,}",
                    f"{type_status[rtype].get('blank', 0):,}",
                ]
                for rtype in recipe_type_order
                if rtype in type_status
            ],
        ),
        "",
        *md_table(
            ["P", "Kind", "Rows", "Success", "Test-blocked", "Failed", "Not attempted", "Blank"],
            build_kind_rows,
        ),
        "",
        "## Census: feedstock, staged-recipes, local build",
        "",
        f"Feedstock exists **{fs_n:,}**. Needs staged-recipes **{needs:,}**",
        f"(no staged PR yet **{no_pr:,}**). Local recipe URL **{local_n:,}**.",
        f"CFE success **{green:,}** · skipped **{skipped:,}** · failed **{failed:,}**.",
        f"Staged_Recipes_PR_URL filled **{staged:,}**.",
        "",
        *md_table(
            [
                "P",
                "n",
                "Feedstock",
                "Needs staged",
                "No staged PR yet",
                "Local recipe URL",
                "Green",
                "Skipped",
                "Failed",
                "Not native-built",
            ],
            census_rows
            + [
                [
                    "Total",
                    f"{n:,}",
                    f"{fs_n:,}",
                    f"{needs:,}",
                    f"{no_pr:,}",
                    f"{local_n:,}",
                    f"{green:,}",
                    f"{skipped:,}",
                    f"{failed:,}",
                    f"{n - green - skipped - failed:,}",
                ]
            ],
        ),
        "",
        "### Full cube (P × work × feedstock × needs staged)",
        "",
        *md_table(
            [
                "P",
                "Work",
                "Feedstock",
                "Needs staged",
                "n",
                "Local recipe URL",
                "Green",
                "Skipped",
                "Failed",
                "Not native-built",
            ],
            cube_rows,
        ),
        "",
        "## CDO-ENT-JFROG → PyPI / conda-forge",
        "",
        f"Parseable unique JFROG names **{parseable:,}** (skipped empty {skip}).",
        f"Both **{both:,}** ({pct(both, parseable)}) · PyPI only **{pypi_only:,}**",
        f"({pct(pypi_only, parseable)}) · conda-forge only **{cf_only:,}**",
        f"({pct(cf_only, parseable)}) · neither **{neither:,}** ({pct(neither, parseable)}).",
        "",
        *md_table(
            ["Bucket", "Rows", "Share"],
            [
                ["PyPI URL verified", f"{both + pypi_only:,}", pct(both + pypi_only, parseable)],
                ["conda-forge URL verified", f"{both + cf_only:,}", pct(both + cf_only, parseable)],
                ["Both", f"{both:,}", pct(both, parseable)],
                ["PyPI only", f"{pypi_only:,}", pct(pypi_only, parseable)],
                ["conda-forge only", f"{cf_only:,}", pct(cf_only, parseable)],
                ["Neither", f"{neither:,}", pct(neither, parseable)],
            ],
        ),
        "",
        "### No verified PyPI or conda-forge URL",
        "",
        *md_table(
            ["Package", "Artifactory downloads", "Packaging tier"],
            neither_rows,
        ),
        "",
        "## JFROG names needing a staged-recipes PR",
        "",
        f"Not on conda-forge and no staged-recipes PR: **{len(need_pr):,}**.",
        f"Platform envs and internal components both > 0: **{len(pick)}**.",
        f"Any platform or internal signal: **{any_sig:,}**.",
        "",
        *md_table(
            [
                "Package",
                "Downloads",
                "Platform envs",
                "Internal components",
                "Apps",
                "Work",
                "Tracker",
            ],
            [
                [
                    t[0].get("name") or "",
                    f"{as_int(t[0].get('artifactory_downloads') or '0'):,}",
                    str(t[2]),
                    str(t[3]),
                    str(t[4]),
                    t[1].get("Work") or "",
                    "issue" if t[1].get("OpenTeams_Issue_URL") else "no issue",
                ]
                for t in pick
            ],
        ),
        "",
        "### Most downloaded (not on conda-forge, no staged PR)",
        "",
        *md_table(
            ["Package", "Downloads", "Platform envs", "Internal components", "Work"],
            [
                [
                    t[0].get("name") or "",
                    f"{as_int(t[0].get('artifactory_downloads') or '0'):,}",
                    str(as_int(t[0].get("platform_env_count") or "0")),
                    str(as_int(t[0].get("internal_component_count") or "0")),
                    t[1].get("Work") or "",
                ]
                for t in top_dl
            ],
        ),
        "",
        "## Artifactory PyPI-only names with no packaging issue",
        "",
        f"**{len(board_gap)}** remaining after the full-board join.",
        "",
        *md_table(["Package", "Artifactory downloads"], board_gap),
        "",
        "## Catalog sources",
        "",
        *md_table(
            ["Source", "Data rows", "Unique names", "Packaging titles", "Other titles", "Empty titles"],
            [
                [
                    s[0],
                    f"{s[1]:,}",
                    f"{s[2]:,}",
                    f"{s[3]:,}" if s[0] == "tab:OpenTeams" else "—",
                    f"{s[4]:,}" if s[0] == "tab:OpenTeams" else "—",
                    f"{s[5]:,}" if s[0] == "tab:OpenTeams" else "—",
                ]
                for s in catalog_stats
            ],
        ),
        "",
        "## External source counts",
        "",
        "Live index fetches dated 2026-08-15 (not re-run at gist publish).",
        "Catalog source counts come from ``inventory_universe.parquet`` (Story 23.8).",
        "",
        *md_table(
            ["Source", "Count", "How counted", "Workbook tab (legacy reference)"],
            [list(row) for row in EXTERNAL_LIVE],
        ),
        "",
    ]
    )
    return "\n".join(lines)


# Two of the three dashboard views for the live identity tab (catalog, ops,
# Artifactory/workbook -- see docs/dreams/conda-forge-packaging-inventory-
# operations.md). Catalog already exists (identity-2026-08-20.canvas.tsx via
# conda-forge-packaging-inventory-operations_priority.py::write_canvas).
# These two restructure the same already-computed values `render()` uses for
# its markdown mirror into a `cursor/canvas` TSX file. Same import block and
# DATA-blob structural pattern as write_canvas -- see its `_CANVAS_PREFIX` /
# `_CANVAS_SUFFIX` in conda-forge-packaging-inventory-operations_priority.py.
CANVAS_DIR = Path(
    "/home/rxm7706/.cursor/projects/"
    "home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/canvases"
)
DEFAULT_OPS_CANVAS_PATH = CANVAS_DIR / "identity-ops.canvas.tsx"
DEFAULT_WORKBOOK_CANVAS_PATH = CANVAS_DIR / "jfrog-workbook.canvas.tsx"

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

_OPS_CANVAS_SUFFIX = r""" as {
  tab: string;
  n: number;
  priorityCounts: Record<string, number>;
  workCounts: Record<string, number>;
  priorityDefs: Array<[string, string, number]>;
  workDefs: Array<[string, string, number]>;
  issues: { have: number; miss: number; byP: Array<[string, number, number, number]> };
  buildByType: Array<[string, number, number, number, number, number, number]>;
  rows: Array<[string, string, string, string, string]>;
  leaders: Array<[string, string, string]>;
};

function fmt(n: number): string {
  return n.toLocaleString("en-US");
}

export default function IdentityOps() {
  const [q, setQ] = useCanvasState("identity-ops-q", "");
  const query = q.trim().toLowerCase();
  const filtered = DATA.rows.filter(
    (r) => !query || r[0].includes(query) || r[2].toLowerCase().includes(query)
  );

  return (
    <Stack gap={20}>
      <Stack gap={6}>
        <H1>Identity ops -- Priority, Work, Issues, Builds</H1>
        <Text tone="secondary" size="small">
          {fmt(DATA.n)} rows on tab {DATA.tab}.
        </Text>
      </Stack>

      <Grid columns={4} gap={12}>
        <Stat value={fmt(DATA.issues.have)} label="Have OpenTeams issue" />
        <Stat value={fmt(DATA.issues.miss)} label="Missing OpenTeams issue" tone="warning" />
        <Stat value={fmt(DATA.workCounts["Create recipe"] || 0)} label="Create recipe" />
        <Stat value={fmt(DATA.workCounts["Fix vulnerability"] || 0)} label="Fix vulnerability" tone="danger" />
      </Grid>

      <Callout tone="info">
        Priority is first-match top-down (P1 highest, P10 floor). Work is
        independent of priority: Fix vulnerability / Create recipe / File
        OpenTeams tracking issue [Conda-Forge Packaging] / Already tracked.
      </Callout>

      <H2>Priority buckets</H2>
      <Table
        striped
        stickyHeader
        headers={["P", "Packages", "Description"]}
        columnAlign={["left", "right", "left"]}
        rows={DATA.priorityDefs.map((d) => [d[0], fmt(d[2]), d[1]])}
      />

      <H2>Work type</H2>
      <BarChart
        horizontal
        height={160}
        categories={DATA.workDefs.map((d) => d[0])}
        series={[{ name: "packages", data: DATA.workDefs.map((d) => d[2]), tone: "warning" }]}
        showValues
      />

      <H2>Packaging-issue gap by priority</H2>
      <Table
        striped
        stickyHeader
        headers={["P", "Have issue", "Missing", "Missing rate"]}
        columnAlign={["left", "right", "right", "right"]}
        rows={DATA.issues.byP.map((r) => [r[0], fmt(r[1]), fmt(r[2]), `${r[3]}%`])}
      />

      <H2>Local build by recipe type</H2>
      <Table
        striped
        stickyHeader
        headers={["Type", "Rows", "Success", "Test-blocked", "Failed", "Not attempted", "Blank"]}
        columnAlign={["left", "right", "right", "right", "right", "right", "right"]}
        rows={DATA.buildByType.map((r) => [r[0], fmt(r[1]), fmt(r[2]), fmt(r[3]), fmt(r[4]), fmt(r[5]), fmt(r[6])])}
      />

      <H2>All packages</H2>
      <Row gap={8} align="center" wrap>
        <TextInput value={q} onChange={setQ} placeholder="Filter by package or work" />
        <Text tone="secondary" size="small">
          {fmt(filtered.length)} of {fmt(DATA.rows.length)} rows
        </Text>
      </Row>
      <Table
        striped
        stickyHeader
        headers={["Package", "P", "Work", "Build status", "Has issue"]}
        columnAlign={["left", "left", "left", "left", "left"]}
        rows={filtered}
      />
    </Stack>
  );
}
"""

_WORKBOOK_CANVAS_SUFFIX = r""" as {
  tab: string;
  jfrogMap: {
    parseable: number;
    skip: number;
    both: number;
    pypiOnly: number;
    cfOnly: number;
    neither: number;
  };
  neitherRows: Array<[string, number, string]>;
  needPr: Array<[string, number]>;
  boardGap: Array<[string, number]>;
  catalogSources: Array<[string, number, number]>;
  externalCounts: Array<[string, string, string, string]>;
};

function fmt(n: number): string {
  return n.toLocaleString("en-US");
}

export default function JfrogWorkbook() {
  return (
    <Stack gap={20}>
      <Stack gap={6}>
        <H1>Artifactory / workbook -- CDO-ENT-JFROG to PyPI / conda-forge</H1>
        <Text tone="secondary" size="small">
          {fmt(DATA.jfrogMap.parseable)} parseable JFROG names on tab {DATA.tab}
          ({fmt(DATA.jfrogMap.skip)} skipped).
        </Text>
      </Stack>

      <Grid columns={4} gap={12}>
        <Stat value={fmt(DATA.jfrogMap.both)} label="PyPI + conda-forge" />
        <Stat value={fmt(DATA.jfrogMap.pypiOnly)} label="PyPI only" tone="warning" />
        <Stat value={fmt(DATA.jfrogMap.cfOnly)} label="conda-forge only" />
        <Stat value={fmt(DATA.jfrogMap.neither)} label="Neither" tone="danger" />
      </Grid>

      <H2>No verified PyPI or conda-forge URL</H2>
      <Table
        striped
        stickyHeader
        headers={["Package", "Artifactory downloads", "Packaging tier"]}
        columnAlign={["left", "right", "left"]}
        rows={DATA.neitherRows.map((r) => [r[0], fmt(r[1]), r[2]])}
      />

      <H2>Needs a staged-recipes PR</H2>
      <Table
        striped
        stickyHeader
        headers={["Package", "Artifactory downloads"]}
        columnAlign={["left", "right"]}
        rows={DATA.needPr.map((r) => [r[0], fmt(r[1])])}
      />

      <H2>PyPI-only names with no packaging issue</H2>
      <Table
        striped
        stickyHeader
        headers={["Package", "Artifactory downloads"]}
        columnAlign={["left", "right"]}
        rows={DATA.boardGap.map((r) => [r[0], fmt(r[1])])}
      />

      <H2>Catalog sources</H2>
      <Table
        striped
        stickyHeader
        headers={["Source", "Data rows", "Unique names"]}
        columnAlign={["left", "right", "right"]}
        rows={DATA.catalogSources.map((r) => [r[0], fmt(r[1]), fmt(r[2])])}
      />

      <H2>External source counts</H2>
      <Table
        striped
        stickyHeader
        headers={["Source", "Count", "How counted", "Workbook tab (legacy reference)"]}
        columnAlign={["left", "right", "left", "left"]}
        rows={DATA.externalCounts}
      />
    </Stack>
  );
}
"""


def _pct(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 1) if denominator else 0.0


def write_ops_canvas(
    path: Path,
    records: list[dict[str, str]],
    tab: str,
    helpers,
) -> None:
    """Ops dashboard canvas: Priority/Work, Issues gap, Builds/Census --
    restructures the same values `render()` computes for its markdown mirror
    (Priority and work / Packaging-issue gap / Local build sections) into a
    `cursor/canvas` TSX file. Structural sibling of
    conda-forge-packaging-inventory-operations_priority.py::write_canvas;
    this canvas renders inside Cursor, not this repo's test suite -- a zero
    input still produces a valid, schema-shaped file with empty rows/leaders.
    """
    p_order = helpers.P_ORDER
    recipe_type_order = helpers.RECIPE_TYPE_ORDER
    work_order = helpers.WORK_DASH_ORDER
    row_recipe_type = helpers.row_recipe_type
    load_local_recipe_type = helpers.load_local_recipe_type
    overlay_live_local = helpers.overlay_live_local
    repo_root = helpers.REPO_ROOT

    dir_types: dict[str, str] = {}
    if records:
        overlay_live_local(records, repo_root / "recipes")
        dir_types = load_local_recipe_type(repo_root / "recipes")

    p_counts = Counter(r.get("P") or "?" for r in records)
    work_counts = Counter(r.get("Work") or "?" for r in records)

    have_by_p: Counter = Counter()
    miss_by_p: Counter = Counter()
    have_issue = 0
    for r in records:
        p = r.get("P") or "?"
        if r.get("OpenTeams_Issue_URL"):
            have_issue += 1
            have_by_p[p] += 1
        else:
            miss_by_p[p] += 1
    miss_issue = len(records) - have_issue

    type_status: dict[str, Counter] = defaultdict(Counter)
    for r in records:
        rtype = row_recipe_type(r, dir_types)
        status = r.get("Local_Build_Status") or "blank"
        type_status[rtype][status] += 1

    priority_defs = [[p, PRIORITY_DESC[p], p_counts.get(p, 0)] for p in p_order]
    work_defs = [[w, WORK_DESC[w], work_counts.get(w, 0)] for w in work_order]
    issues_by_p = [
        [p, have_by_p.get(p, 0), miss_by_p.get(p, 0), _pct(miss_by_p.get(p, 0), p_counts.get(p, 0))]
        for p in p_order
    ]
    build_by_type = [
        [
            rtype,
            sum(type_status[rtype].values()),
            type_status[rtype].get("success", 0),
            type_status[rtype].get("build-clean-test-blocked", 0),
            type_status[rtype].get("failed", 0),
            type_status[rtype].get("not-attempted", 0),
            type_status[rtype].get("blank", 0),
        ]
        for rtype in recipe_type_order
        if rtype in type_status
    ]
    rows = [
        [
            r.get("Core_Python_Package_Name") or "",
            r.get("P") or "",
            r.get("Work") or "",
            r.get("Local_Build_Status") or "",
            "yes" if r.get("OpenTeams_Issue_URL") else "no",
        ]
        for r in records
    ]
    leaders: list[list] = []
    for p in p_order:
        n = 0
        for r in records:
            if (r.get("P") or "?") != p:
                continue
            if n >= 6:
                break
            leaders.append([p, r.get("Core_Python_Package_Name") or "", r.get("Work") or ""])
            n += 1

    data = json.dumps(
        {
            "tab": tab,
            "n": len(records),
            "priorityCounts": dict(p_counts),
            "workCounts": dict(work_counts),
            "priorityDefs": priority_defs,
            "workDefs": work_defs,
            "issues": {"have": have_issue, "miss": miss_issue, "byP": issues_by_p},
            "buildByType": build_by_type,
            "rows": rows,
            "leaders": leaders,
        },
        separators=(",", ":"),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_CANVAS_PREFIX + data + _OPS_CANVAS_SUFFIX, encoding="utf-8")


def write_workbook_canvas(
    path: Path,
    records: list[dict[str, str]],
    export_path: Path,
    tab: str,
    helpers,
) -> None:
    """Artifactory / catalog dashboard canvas: CDO-ENT-JFROG -> PyPI /
    conda-forge map, staged-recipes gap, board gap, catalog sources, external
    source counts -- restructures the same values `render()` computes for its
    markdown mirror into a `cursor/canvas` TSX file. A missing/nonexistent
    export Parquet (as in a zero-records test) still produces a valid,
    schema-shaped file with empty array fields; this canvas renders inside
    Cursor, not this repo's test suite.
    """
    pep503_name = helpers.pep503_name
    packaging_name_from_title = helpers.packaging_name_from_title
    as_int = helpers._as_int

    ident = {pep503_name(r.get("Core_Python_Package_Name") or ""): r for r in records}

    def is_pypi(row: dict[str, str] | None) -> bool:
        if not row:
            return False
        return (row.get("primary_type") or "") == "pypi" or (
            row.get("primary_purl") or ""
        ).startswith("pkg:pypi/")

    def is_cf(row: dict[str, str] | None) -> bool:
        if not row:
            return False
        return bool(row.get("conda_purl") or row.get("Conda-Forge_FeedStock_URL"))

    jfrog_by, skip = load_jfrog_by(export_path, pep503_name)

    both = pypi_only = cf_only = neither = 0
    neither_rows: list[list] = []
    need_pr: list[list] = []
    for k, jr in jfrog_by.items():
        ident_row = ident.get(k)
        pypi = is_pypi(ident_row)
        cf = is_cf(ident_row)
        if pypi and cf:
            both += 1
        elif pypi:
            pypi_only += 1
        elif cf:
            cf_only += 1
        else:
            neither += 1
            neither_rows.append(
                [
                    jr.get("name") or k,
                    as_int(jr.get("artifactory_downloads") or "0"),
                    jr.get("packaging_tier") or "",
                ]
            )
        on_cf = bool(
            ident_row
            and (ident_row.get("Conda-Forge_FeedStock_URL") or ident_row.get("conda_purl"))
        )
        has_pr = bool(ident_row and ident_row.get("Staged_Recipes_PR_URL"))
        if ident_row and not on_cf and not has_pr:
            need_pr.append([jr.get("name") or k, as_int(jr.get("artifactory_downloads") or "0")])
    neither_rows.sort(key=lambda r: (-r[1], str(r[0]).lower()))
    need_pr.sort(key=lambda r: -r[1])
    parseable = len(jfrog_by)

    board_gap: list[list] = []
    for k, jr in jfrog_by.items():
        ident_row = ident.get(k)
        if (
            is_pypi(ident_row)
            and not is_cf(ident_row)
            and ident_row
            and not ident_row.get("OpenTeams_Issue_URL")
        ):
            board_gap.append([jr.get("name") or k, as_int(jr.get("artifactory_downloads") or "0")])
    board_gap.sort(key=lambda r: (-r[1], str(r[0]).lower()))

    catalog_sources = [
        [label, data_rows, unique_names]
        for label, data_rows, unique_names, _a, _b, _c in catalog_source_stats(
            export_path, packaging_name_from_title
        )
    ]

    data = json.dumps(
        {
            "tab": tab,
            "jfrogMap": {
                "parseable": parseable,
                "skip": skip,
                "both": both,
                "pypiOnly": pypi_only,
                "cfOnly": cf_only,
                "neither": neither,
            },
            "neitherRows": neither_rows,
            "needPr": need_pr,
            "boardGap": board_gap,
            "catalogSources": catalog_sources,
            "externalCounts": [list(row) for row in EXTERNAL_LIVE],
        },
        separators=(",", ":"),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_CANVAS_PREFIX + data + _WORKBOOK_CANVAS_SUFFIX, encoding="utf-8")
