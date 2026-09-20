"""BSL-grounded gist markdown for the identity complete export (Story 23.6, CAP-8d).

Renders the two pinned gist documents (row catalog + dashboard companion) from
``identity_complete_export.parquet`` via declared BSL queries — the ONLY copy of
markdown-table-building logic post-port.
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from pyforge.core.errors import PyforgeError

from pyforge.atlas.semantic import models
from pyforge.atlas.semantic.query_helpers import bsl_query

GIST_FILENAME = "mgmt-wf-python-modernization-identity.md"
GIST_DASHBOARD_FILENAME = "mgmt-wf-python-modernization-dashboards.md"

GIST_COLUMNS: tuple[str, ...] = (
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
    "Core_Python_Package_Name",
    "OpenTeams_Title",
    "identity_source",
    "associator_key",
    "associator_status",
    "primary_purl",
    "primary_type",
    "alternative_purls",
    "cpes",
    "conda_purl",
    "source_repository_url",
    "OpenTeams_Issue_URL",
    "Conda-Forge_FeedStock_URL",
    "Conda-Forge_Metadata_URL",
    "Staged_Recipes_PR_URL",
    "Local_Recipes_URL",
    "Local_Build_Status",
    "Verification_Timestamp_UTC",
    "Priority_Bucket_Description",
    "Priority_Source",
    "Priority_Reason",
    "JFROG_risk_level",
    "JFROG_latest_vuln_count",
    "internal_component_count",
    "internal_lob_count",
)

GIST_SCHEMA: tuple[tuple[str, str, str, str], ...] = (
    ("P", "enum", "yes", "Proposed priority `P1`–`P10`."),
    ("Rank", "int", "yes", "1-based rank across the snapshot (P1 first)."),
    ("Score", "int", "yes", "Use-score percentile 1–100."),
    ("Package", "string", "yes", "Display name (same identity as Core_Python_Package_Name)."),
    (
        "Work",
        "enum",
        "yes",
        "`Fix vulnerability` | `Create recipe` | `File OpenTeams tracking issue [Conda-Forge Packaging]` | `Already tracked`.",
    ),
    ("Platforms", "int", "no", "JFROG `platform_env_count`."),
    ("Apps", "int", "no", "JFROG `internal_app_count`."),
    ("Downloads", "int", "no", "JFROG `artifactory_downloads`."),
    ("Versions", "int", "no", "JFROG `artifactory_version_count`."),
    ("Vuln", "enum", "no", "JFROG `vuln_status` (`affected_latest`, `clean`, …)."),
    (
        "Core_Python_Package_Name",
        "string",
        "yes",
        "Primary key. Conda/PyPI package identity as stored (unique).",
    ),
    ("OpenTeams_Title", "string", "yes", "Issue title `[Conda-Forge Packaging] {name}`."),
    (
        "identity_source",
        "enum",
        "yes",
        "`purl-associator` | `inventory` | `none` | `openteams-board`.",
    ),
    (
        "associator_key",
        "string",
        "no",
        "Key matched in prefix-dev/purl-associator mappings-index. Blank if unused.",
    ),
    (
        "associator_status",
        "string",
        "no",
        "Associator status, or `inventory-derived` / `unmapped`.",
    ),
    ("primary_purl", "purl", "no", "Upstream PURL (`pkg:pypi/…` or `pkg:github/…`). Not a conda PURL."),
    ("primary_type", "enum", "no", "`pypi` | `github` | `git` | blank."),
    ("alternative_purls", "purl[]", "no", "`; `-joined extra PURLs."),
    ("cpes", "string[]", "no", "`; `-joined CPEs from the associator."),
    ("conda_purl", "purl", "no", "`pkg:conda/{name}?channel=conda-forge` only when on conda-forge."),
    ("source_repository_url", "url", "no", "Upstream VCS URL. Not a feedstock and not PyPI/anaconda."),
    (
        "OpenTeams_Issue_URL",
        "url",
        "no",
        "GitHub issue on OpenTeams-WFT-CDO/mgmt-wf-python-modernization.",
    ),
    (
        "Conda-Forge_FeedStock_URL",
        "url[]",
        "no",
        "`; `-joined github.com/conda-forge/{repo}-feedstock from conda-forge.org/packages.",
    ),
    (
        "Conda-Forge_Metadata_URL",
        "url",
        "no",
        "Packages-page Browse link: conda-metadata-app.streamlit.app/?q=conda-forge/{pkg}.",
    ),
    (
        "Staged_Recipes_PR_URL",
        "url",
        "no",
        "Best conda-forge/staged-recipes PR (open file path, else title; prefer open then merged).",
    ),
    (
        "Local_Recipes_URL",
        "url[]",
        "no",
        "`; `-joined github.com/rxm7706/local-recipes/tree/main/recipes/{dir}.",
    ),
    (
        "Local_Build_Status",
        "enum",
        "no",
        "`success` | `failed` | `build-clean-test-blocked` | `not-attempted`. From the local `recipe.yaml` CFE stamp. Blank if no stamp.",
    ),
    ("Verification_Timestamp_UTC", "datetime", "yes", "ISO 8601 UTC generation time for this snapshot."),
    ("Priority_Bucket_Description", "string", "yes", "Human description of `P`."),
    (
        "Priority_Source",
        "string",
        "no",
        "Assignment source (`current-version-vuln`, `platform`, `work-create-recipe`, …).",
    ),
    ("Priority_Reason", "string", "no", "Short reason for this `P`."),
    ("JFROG_risk_level", "enum", "no", "`HIGH` | `MEDIUM` | `LOW` | `NO_DATA`."),
    ("JFROG_latest_vuln_count", "int", "no", "Basilisk latest-version known vulnerability count."),
    ("internal_component_count", "int", "no", "JFROG internal component count."),
    ("internal_lob_count", "int", "no", "JFROG internal LOB count."),
)

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

P_ORDER = ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10")
RECIPE_TYPE_ORDER = ("noarch-python", "noarch-generic", "compiled", "arch", "none")
BUILD_STATUS_ORDER = (
    "success",
    "build-clean-test-blocked",
    "failed",
    "blocked-missing-ortools",
    "not-attempted",
    "blank",
)
WORK_DASH_ORDER = (
    "Fix vulnerability",
    "Create recipe",
    "File OpenTeams tracking issue [Conda-Forge Packaging]",
    "Already tracked",
)

LOCAL_RECIPES_URL = "https://github.com/rxm7706/local-recipes/tree/main/recipes/{dir}"
CFE_BUILD_STATUS_RE = re.compile(r"(?m)^  cfe-local-build-status:\s*(\S+)")
LOCAL_DIR_FROM_URL_RE = re.compile(r"/recipes/([^/\s]+)\s*$")
NOARCH_LINE_RE = re.compile(r"(?m)^\s*noarch:\s*['\"]?([A-Za-z0-9_-]+)")
COMPILER_LINE_RE = re.compile(
    r"(?:\{\{\s*compiler\s*\(|\$\{\{\s*compiler\s*\(|"
    r"\{\{\s*stdlib\s*\(|\$\{\{\s*stdlib\s*\()"
)
RECIPE_NAME_RE = re.compile(r"(?m)^\s*name:\s*['\"]?([^'\"#\n]+)")
TITLE_STOP = {
    "recipe",
    "recipes",
    "package",
    "packages",
    "python",
    "conda",
    "forge",
    "meta",
    "yaml",
}

EXTERNAL_SOURCE_SPECS: tuple[tuple[str, str, str, str], ...] = (
    ("Anaconda Dist 2026.x", "raw/discovery_anaconda_dist_2026x_raw", "HTML 2026.x table", "639 (Anaaconda-Dist)"),
    (
        "Anaconda main",
        "primary/core_channeldata_raw/core_channeldata_raw.parquet",
        "pkgs/main channeldata.json",
        "5,458 (Anaconda-Main)",
    ),
    (
        "conda-forge",
        "primary/core_channeldata_raw/core_channeldata_raw.parquet",
        "conda-forge channeldata.json",
        "33,875 (Conda-Forge)",
    ),
    (
        "Basilisk /v1/packages",
        "raw/discovery_basilisk_packages_raw/discovery_basilisk_packages_raw.parquet",
        "api.basilisk.prefix.dev",
        "33,853 (Basilisk)",
    ),
    (
        "AOSS free Python",
        "conf/base/seeds/discovery_aoss_free_python_seed.json",
        "docs #python list",
        "1,474 (GAOSS-Free)",
    ),
    (
        "AOSS premium Python",
        "raw/discovery_aoss_premium_python_raw/discovery_aoss_premium_python_raw.parquet",
        "Wayback Python <ul>",
        "2,114 (GAOSS-Premium)",
    ),
)


class IdentityGistError(PyforgeError, Exception):
    """Raised when the export Parquet is absent or empty."""


def render_identity_gist_markdown(
    export_path: Path,
    *,
    gist_id: str = "",
    repo_root: Path | None = None,
) -> tuple[str, str]:
    """Render identity row catalog + dashboard markdown from the complete export."""
    export_path = Path(export_path)
    if not export_path.is_file():
        raise IdentityGistError(
            f"identity_complete_export not found at {export_path} — run "
            "`pixi run -e pyforge-atlas pyforge-atlas-bootstrap` first"
        )
    df = pd.read_parquet(export_path)
    if df.empty:
        raise IdentityGistError(f"identity_complete_export is empty at {export_path}")

    root = repo_root or _find_repo_root(export_path)
    records = _records_from_frame(df)
    _overlay_live_local(records, root / "recipes")
    overlay_df = pd.DataFrame(records)

    data_root = _data_root_from_export(export_path)
    jfrog_path = data_root / "derived/enterprise_jfrog_consumption/enterprise_jfrog_consumption.parquet"
    atlas_root = _pyforge_atlas_root(export_path)

    with tempfile.TemporaryDirectory() as tmpdir:
        overlay_path = Path(tmpdir) / "identity_complete_export_overlay.parquet"
        overlay_df.to_parquet(overlay_path, index=False)
        table = models.duckdb_table_from_parquet(str(overlay_path))
        model = models.build_identity_complete_export_model(table, gist_columns=GIST_COLUMNS)

        identity_md = _render_identity_catalog(
            records,
            export_path,
            gist_id=gist_id,
            model=model,
        )
        dashboards_md = _render_dashboards(
            records,
            export_path,
            gist_id=gist_id,
            model=model,
            jfrog_path=jfrog_path if jfrog_path.is_file() else None,
            data_root=data_root,
            atlas_root=atlas_root,
            repo_root=root,
        )
    return identity_md, dashboards_md


def _find_repo_root(start: Path) -> Path:
    for parent in [start, *start.parents]:
        if (parent / ".git").exists() or (parent / "_bmad-output").is_dir():
            return parent
    return start.parents[min(5, len(start.parents) - 1)]


def _pyforge_atlas_root(export_path: Path) -> Path:
    for parent in export_path.parents:
        if parent.name == "pyforge-atlas":
            return parent
    return _find_repo_root(export_path) / "src/shared/packages/pyforge-atlas"


def _data_root_from_export(export_path: Path) -> Path:
    return export_path.parent.parent.parent


def _records_from_frame(df: pd.DataFrame) -> list[dict[str, str]]:
    return [
        {str(k): ("" if pd.isna(v) else str(v).strip()) for k, v in row.items()} for row in df.to_dict(orient="records")
    ]


def _pep503_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", (value or "").strip().lower()).strip("-")


def _join_list(values: list[str]) -> str:
    return "; ".join(v for v in values if v)


def _name_keys(row: dict[str, str]) -> list[str]:
    keys: list[str] = []
    for raw in (row.get("Core_Python_Package_Name", ""), row.get("associator_key", "")):
        if not raw:
            continue
        for cand in (raw, raw.lower(), _pep503_name(raw), raw.replace("-", "_")):
            if cand and cand not in keys:
                keys.append(cand)
    return keys


def _first_map(mapping: dict[str, str], keys: list[str]) -> str:
    for key in keys:
        if key in mapping and mapping[key]:
            return mapping[key]
    return ""


def _load_local_recipes(recipes_dir: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not recipes_dir.is_dir():
        return out
    for d in sorted(p for p in recipes_dir.iterdir() if p.is_dir() and not p.name.startswith(".")):
        url = LOCAL_RECIPES_URL.format(dir=d.name)
        names = {_pep503_name(d.name)}
        for fname in ("recipe.yaml", "meta.yaml"):
            fpath = d / fname
            if not fpath.is_file():
                continue
            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for m in RECIPE_NAME_RE.finditer(text):
                token = _pep503_name(m.group(1))
                if token and token not in TITLE_STOP:
                    names.add(token)
        for name in names:
            if name and name not in out:
                out[name] = url
            elif name and out.get(name) and out[name] != url:
                if url not in out[name].split("; "):
                    out[name] = _join_list([out[name], url])
    return out


def _load_local_build_status(recipes_dir: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not recipes_dir.is_dir():
        return out
    for d in recipes_dir.iterdir():
        if not d.is_dir() or d.name.startswith("."):
            continue
        fpath = d / "recipe.yaml"
        if not fpath.is_file():
            continue
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = CFE_BUILD_STATUS_RE.search(text)
        if not m:
            continue
        status = m.group(1).strip().strip("'\"")
        if not status:
            continue
        names = {_pep503_name(d.name), d.name.lower()}
        for rm in RECIPE_NAME_RE.finditer(text):
            token = _pep503_name(rm.group(1))
            if token and token not in TITLE_STOP:
                names.add(token)
        for name in names:
            if name and name not in out:
                out[name] = status
    return out


def _overlay_live_local(records: list[dict[str, str]], recipes_dir: Path) -> None:
    local_map = _load_local_recipes(recipes_dir)
    status_map = _load_local_build_status(recipes_dir)
    for row in records:
        keys = _name_keys(row)
        pkg = row.get("Package") or ""
        if pkg:
            keys = list(keys)
            for cand in (pkg, pkg.lower(), _pep503_name(pkg)):
                if cand and cand not in keys:
                    keys.append(cand)
        url = _first_map(local_map, keys) or row.get("Local_Recipes_URL") or ""
        row["Local_Recipes_URL"] = url
        status = _first_map(status_map, keys)
        if not status and url:
            m = LOCAL_DIR_FROM_URL_RE.search(url.split(";")[0].strip())
            if m:
                slug = m.group(1)
                status = status_map.get(_pep503_name(slug)) or status_map.get(slug.lower()) or ""
        row["Local_Build_Status"] = status


def classify_recipe_text(text: str) -> str:
    m = NOARCH_LINE_RE.search(text)
    if m:
        kind = m.group(1).strip().lower()
        if kind == "python":
            return "noarch-python"
        if kind in {"generic", "true", "yes"}:
            return "noarch-generic"
        return "noarch-other"
    if COMPILER_LINE_RE.search(text):
        return "compiled"
    return "arch"


def load_local_recipe_type(recipes_dir: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not recipes_dir.is_dir():
        return out
    for d in recipes_dir.iterdir():
        if not d.is_dir() or d.name.startswith("."):
            continue
        text = ""
        for fname in ("recipe.yaml", "meta.yaml"):
            fpath = d / fname
            if not fpath.is_file():
                continue
            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
            if text:
                break
        out[d.name] = classify_recipe_text(text) if text else "none"
    return out


def row_recipe_type(row: dict[str, str], dir_types: dict[str, str]) -> str:
    url = row.get("Local_Recipes_URL") or ""
    if not url:
        return "none"
    m = LOCAL_DIR_FROM_URL_RE.search(url.split(";")[0].strip())
    if not m:
        return "none"
    return dir_types.get(m.group(1), "none")


def md_cell(value: str) -> str:
    return (
        (value or "")
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r", " ")
        .replace("\n", " ")
        .replace("<", "\\<")
    )


def md_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = [
        "| " + " | ".join(md_cell(h) for h in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(md_cell(str(c)) for c in row) + " |")
    return lines


def _as_int(value: str | int | float) -> int:
    try:
        return int(float(str(value).replace(",", "").strip() or 0))
    except ValueError:
        return 0


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _emit_status_block(lines: list[str], indent: str, counts: Counter) -> None:
    lines.append(f"{indent}rows: {sum(counts.values())}")
    for status in BUILD_STATUS_ORDER:
        n = counts.get(status, 0)
        if n:
            lines.append(f"{indent}{status}: {n}")
    extra = sorted(k for k in counts if k not in BUILD_STATUS_ORDER)
    for status in extra:
        lines.append(f"{indent}{status}: {counts[status]}")


def _filled_key(col: str) -> str:
    return f"filled_{col.replace('-', '_').replace(' ', '_')}"


def _query_counts(model: Any, dimensions: list[str], measure: str = "identity_row_count") -> pd.DataFrame:
    return bsl_query(model, dimensions=dimensions, measures=[measure])


def _scalar_measure(model: Any, measure: str) -> int:
    df = bsl_query(model, measures=[measure])
    if df.empty or measure not in df.columns:
        return 0
    return int(df[measure].iloc[0])


def _render_identity_catalog(
    records: list[dict[str, str]],
    export_path: Path,
    *,
    gist_id: str,
    model: Any,
) -> str:
    rows = sorted(records, key=lambda r: (r.get("Core_Python_Package_Name") or "").lower())
    src_counts = Counter(r.get("identity_source", "") for r in rows)
    build_counts = Counter((r.get("Local_Build_Status") or "blank") for r in rows)
    recipes_dir = _find_repo_root(export_path) / "recipes"
    dir_types = load_local_recipe_type(recipes_dir)
    by_p: dict[str, Counter] = defaultdict(Counter)
    by_type: dict[str, Counter] = defaultdict(Counter)
    success_by_p_type: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        p = row.get("P") or "?"
        status = row.get("Local_Build_Status") or "blank"
        rtype = row_recipe_type(row, dir_types)
        by_p[p][status] += 1
        by_type[rtype][status] += 1
        if status == "success":
            success_by_p_type[p][rtype] += 1

    fills = {}
    for col in GIST_COLUMNS:
        key = _filled_key(col)
        fills[col] = _scalar_measure(model, key)

    ts = (rows[0].get("Verification_Timestamp_UTC") if rows else "") or datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    for row in rows:
        row["Verification_Timestamp_UTC"] = ts
    sha = _file_sha256(export_path)
    cols = list(GIST_COLUMNS)

    lines: list[str] = [
        "---",
        "id: mgmt-wf-python-modernization-identity",
        "title: OpenTeams CDO Python modernization identity snapshot",
        "format: gfm-table",
        "primary_key: Core_Python_Package_Name",
        f"rows: {len(rows)}",
        f"columns: {len(cols)}",
        f"generated: {ts}",
        f"source_export: {export_path}",
        f"export_sha256: {sha}",
        "generator: scripts/conda-forge-packaging-inventory-operations_openteams_identity.py --gist-only",
        "blank_means: missing",
        'multi_value_separator: "; "',
        f"gist_id: {gist_id}",
        f"companion: {GIST_DASHBOARD_FILENAME}",
        "parse:",
        '  - GFM pipe table below heading "## Identity rows"',
        f"  - Dashboard tables live in companion file {GIST_DASHBOARD_FILENAME}",
        "  - Header row is the canonical column names; do not rename",
        "  - One package per row; Core_Python_Package_Name is unique",
        "  - Empty cell = missing / not applicable (never N/A in this snapshot)",
        "  - URLs are raw (not markdown links) so they copy as-is",
        "identity_source:",
    ]
    for key, count in sorted(src_counts.items()):
        lines.append(f"  {key}: {count}")
    lines.append("filled:")
    for col in cols:
        lines.append(f"  {col}: {fills[col]}")
    lines.append("local_build:")
    for key, count in sorted(build_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"  {key}: {count}")
    lines.append("local_build_by_p:")
    for p in list(P_ORDER) + sorted(k for k in by_p if k not in P_ORDER):
        if p not in by_p:
            continue
        lines.append(f"  {p}:")
        _emit_status_block(lines, "    ", by_p[p])
    lines.append("local_build_by_type:")
    type_keys = list(RECIPE_TYPE_ORDER) + sorted(k for k in by_type if k not in RECIPE_TYPE_ORDER)
    for rtype in type_keys:
        if rtype not in by_type:
            continue
        lines.append(f"  {rtype}:")
        _emit_status_block(lines, "    ", by_type[rtype])
    lines.append("local_build_success_by_p_type:")
    for p in list(P_ORDER) + sorted(k for k in success_by_p_type if k not in P_ORDER):
        if p not in success_by_p_type:
            continue
        lines.append(f"  {p}:")
        for rtype in list(RECIPE_TYPE_ORDER) + sorted(k for k in success_by_p_type[p] if k not in RECIPE_TYPE_ORDER):
            n = success_by_p_type[p].get(rtype, 0)
            if n:
                lines.append(f"    {rtype}: {n}")
    lines.extend(
        [
            "---",
            "",
            "# mgmt-wf-python-modernization identity",
            "",
            "Snapshot of the Atlas ``identity_complete_export.parquet``: one row per OpenTeams",
            "universe name (`CDO-ENT-JFROG` ∪ `CDO-ENT-CONDA`) plus board-only",
            "`[Conda-Forge Packaging]` extras from org project 1.",
            "",
            f"- Rows: **{len(rows):,}**",
            f"- Columns: **{len(cols)}** (ranking `P`/`Rank`/`Score`/`Work` plus identity URLs and local build status)",
            "- Primary key: `Core_Python_Package_Name` (unique)",
            f"- Generated: `{ts}`",
            f"- Source export: `{export_path}`",
            f"- Export sha256: `{sha}`",
            f"- Gist id (edit in place on every rerun; id is not stored in git): `{gist_id}`",
            f"- Dashboards (same snapshot as the three canvases): `{GIST_DASHBOARD_FILENAME}` in this gist",
            "",
            "## Parse contract",
            "",
            "1. Skip YAML frontmatter (`---` … `---`).",
            "2. The data table starts at `## Identity rows`.",
            "3. Split rows on `|`; trim cell whitespace; unescape `\\|` and `\\\\`.",
            "4. Multi-value cells (`alternative_purls`, `cpes`, `Conda-Forge_FeedStock_URL`, `Local_Recipes_URL`) split on `'; '`.",
            "5. Blank cell means missing. Do not invent URLs or PURLs.",
            "6. `Local_Build_Status` is the live CFE stamp (`success` / `failed` / `build-clean-test-blocked` / `not-attempted`).",
            "7. Frontmatter `local_build_by_p` / `local_build_by_type` / `local_build_success_by_p_type` split those stamps by priority and recipe type (`noarch-python` / `noarch-generic` / `compiled` / `arch` / `none`).",
            f"8. Canvas summaries (P/work, issue gap, census, Artifactory map) are `{GIST_DASHBOARD_FILENAME}` in this gist, not this table.",
            "",
            "## Column schema",
            "",
            "| column | type | required | meaning |",
            "| --- | --- | --- | --- |",
        ]
    )
    for name, typ, req, meaning in GIST_SCHEMA:
        lines.append(f"| `{name}` | {typ} | {req} | {meaning} |")
    lines.extend(
        [
            "",
            "## Identity rows",
            "",
            "| " + " | ".join(md_cell(h) for h in cols) + " |",
            "| " + " | ".join("---" for _ in cols) + " |",
        ]
    )
    for rec in rows:
        lines.append("| " + " | ".join(md_cell(rec.get(c, "")) for c in cols) + " |")
    lines.append("")
    return "\n".join(lines)


def _pct(num: int, den: int) -> str:
    return f"{(100 * num / den):.1f}%" if den else "—"


def _render_dashboards(
    records: list[dict[str, str]],
    export_path: Path,
    *,
    gist_id: str,
    model: Any,
    jfrog_path: Path | None,
    data_root: Path,
    atlas_root: Path,
    repo_root: Path,
) -> str:
    n = len(records)
    ts = (records[0].get("Verification_Timestamp_UTC") if records else "") or datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    sha = _file_sha256(export_path)

    p_df = _query_counts(model, ["P"])
    p_counts = {row["P"]: int(row["identity_row_count"]) for _, row in p_df.iterrows()}
    work_df = _query_counts(model, ["Work"])
    work_counts = {row["Work"]: int(row["identity_row_count"]) for _, row in work_df.iterrows()}

    have_issue = _scalar_measure(model, "has_issue_count")
    miss_issue = n - have_issue

    issue_df = _query_counts(model, ["P", "has_openteams_issue"])
    have_by_p: Counter[str] = Counter()
    miss_by_p: Counter[str] = Counter()
    for _, row in issue_df.iterrows():
        p = row["P"]
        if row["has_openteams_issue"] == "yes":
            have_by_p[p] += int(row["identity_row_count"])
        else:
            miss_by_p[p] += int(row["identity_row_count"])

    miss_work_df = _query_counts(model, ["Work", "has_openteams_issue"])
    miss_by_work: Counter[str] = Counter()
    for _, row in miss_work_df.iterrows():
        if row["has_openteams_issue"] == "no":
            miss_by_work[row["Work"]] += int(row["identity_row_count"])

    fs_n = _scalar_measure(model, "feedstock_count")
    local_n = _scalar_measure(model, "local_recipe_count")
    green = _scalar_measure(model, "build_success_count")
    skipped = _scalar_measure(model, "build_skipped_count")
    failed = _scalar_measure(model, "build_failed_count")
    staged = _scalar_measure(model, "staged_pr_count")
    needs = n - fs_n
    no_pr_df = _query_counts(model, ["has_feedstock", "has_staged_pr"])
    no_pr = sum(
        int(row["identity_row_count"])
        for _, row in no_pr_df.iterrows()
        if row["has_feedstock"] == "no" and row["has_staged_pr"] == "no"
    )

    dir_types = load_local_recipe_type(repo_root / "recipes")
    noarch_types = {"noarch-python", "noarch-generic"}
    type_status: dict[str, Counter] = defaultdict(Counter)
    by_p_kind: dict[str, dict[str, Counter]] = defaultdict(lambda: {"noarch": Counter(), "other": Counter()})
    for r in records:
        rtype = row_recipe_type(r, dir_types)
        st = r.get("Local_Build_Status") or "blank"
        type_status[rtype][st] += 1
        kind = "noarch" if rtype in noarch_types else "other"
        by_p_kind[r.get("P") or "?"][kind][st] += 1

    census_rows: list[list[str]] = []
    for p in P_ORDER:
        bucket_n = p_counts.get(p, 0)
        if not bucket_n:
            continue
        p_model_slice = _query_counts(
            model, ["P", "has_feedstock", "has_staged_pr", "has_local_recipe", "Local_Build_Status"]
        )
        bucket = p_model_slice[p_model_slice["P"] == p]
        fs = sum(int(r["identity_row_count"]) for _, r in bucket[bucket["has_feedstock"] == "yes"].iterrows())
        needs_p = bucket_n - fs
        no_staged = sum(
            int(r["identity_row_count"])
            for _, r in bucket.iterrows()
            if r["has_feedstock"] == "no" and r["has_staged_pr"] == "no"
        )
        local = sum(int(r["identity_row_count"]) for _, r in bucket[bucket["has_local_recipe"] == "yes"].iterrows())
        g = sum(int(r["identity_row_count"]) for _, r in bucket.iterrows() if r["Local_Build_Status"] == "success")
        sk = sum(
            int(r["identity_row_count"])
            for _, r in bucket.iterrows()
            if r["Local_Build_Status"] in {"build-clean-test-blocked", "blocked-missing-ortools"}
        )
        fl = sum(int(r["identity_row_count"]) for _, r in bucket.iterrows() if r["Local_Build_Status"] == "failed")
        not_native = bucket_n - g - sk - fl
        census_rows.append(
            [
                p,
                f"{bucket_n:,}",
                f"{fs:,}",
                f"{needs_p:,}",
                f"{no_staged:,}",
                f"{local:,}",
                f"{g:,}",
                f"{sk:,}",
                f"{fl:,}",
                f"{not_native:,}",
            ]
        )

    cube_df = _query_counts(
        model,
        ["P", "Work", "has_feedstock", "has_local_recipe", "Local_Build_Status"],
    )
    cube_agg: dict[tuple, list[int]] = {}
    for _, row in cube_df.iterrows():
        key = (
            row["P"],
            row["Work"],
            "yes" if row["has_feedstock"] == "yes" else "no",
            "no" if row["has_feedstock"] == "yes" else "yes",
        )
        agg = cube_agg.setdefault(key, [0, 0, 0, 0, 0, 0])
        cnt = int(row["identity_row_count"])
        agg[0] += cnt
        if row["has_local_recipe"] == "yes":
            agg[1] += cnt
        st = row["Local_Build_Status"]
        if st == "success":
            agg[2] += cnt
        elif st in {"build-clean-test-blocked", "blocked-missing-ortools"}:
            agg[3] += cnt
        elif st == "failed":
            agg[4] += cnt
        else:
            agg[5] += cnt
    cube_rows = []
    for key in sorted(
        cube_agg,
        key=lambda k: (P_ORDER.index(k[0]) if k[0] in P_ORDER else 99, k[1], k[2], k[3]),
    ):
        a = cube_agg[key]
        cube_rows.append([key[0], key[1], key[2], key[3], *[f"{x:,}" for x in a]])

    jfrog_section = _jfrog_map_section(records, jfrog_path)

    build_kind_rows = []
    for p in P_ORDER:
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

    external_rows = _external_source_rows(data_root, atlas_root)

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
        f"companion: {GIST_FILENAME}",
        "priority_rule: first-match top-down; no P0; floor P10; Score ranks inside P and does not pick P",
        "priority_buckets:",
    ]
    for p in P_ORDER:
        lines.append(f"  {p}:")
        lines.append(f"    n: {p_counts.get(p, 0)}")
        lines.append(f"    rule: {json.dumps(PRIORITY_DESC[p])}")
    lines.append("work_labels:")
    for w in WORK_DASH_ORDER:
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
            "External).",
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
                [[p, f"{p_counts.get(p, 0):,}", PRIORITY_DESC[p]] for p in P_ORDER]
                + [["Total", f"{n:,}", "All identity rows. Floor is P10."]],
            ),
            "",
            *md_table(
                ["Work", "n", "Meaning"],
                [[w, f"{work_counts.get(w, 0):,}", WORK_DESC[w]] for w in WORK_DASH_ORDER],
            ),
            "",
            "## Packaging-issue gap",
            "",
            f"{have_issue:,} of {n:,} have an OpenTeams `[Conda-Forge Packaging]` issue URL.",
            f"**{miss_issue:,}** missing ({_pct(miss_issue, n)}).",
            "",
            *md_table(
                ["P", "Identity rows", "Have issue", "Missing", "Missing rate"],
                [
                    [
                        p,
                        f"{p_counts.get(p, 0):,}",
                        f"{have_by_p.get(p, 0):,}",
                        f"{miss_by_p.get(p, 0):,}",
                        _pct(miss_by_p.get(p, 0), p_counts.get(p, 0)),
                    ]
                    for p in P_ORDER
                ]
                + [["All", f"{n:,}", f"{have_issue:,}", f"{miss_issue:,}", _pct(miss_issue, n)]],
            ),
            "",
            *md_table(
                ["Work", "Missing packaging issue"],
                [[w, f"{miss_by_work.get(w, 0):,}"] for w in WORK_DASH_ORDER if miss_by_work.get(w, 0)],
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
                    for rtype in RECIPE_TYPE_ORDER
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
        ]
    )
    lines.extend(jfrog_section)
    lines.extend(
        [
            "",
            "## External source counts",
            "",
            "Live row counts from materialized Atlas Parquet (Story 23.6).",
            "",
            *md_table(
                ["Source", "Count", "How counted", "Workbook tab (legacy reference)"],
                external_rows,
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _jfrog_map_section(records: list[dict[str, str]], jfrog_path: Path | None) -> list[str]:
    ident = {_pep503_name(r.get("Core_Python_Package_Name") or ""): r for r in records}
    jfrog_by: dict[str, dict[str, str]] = {}
    skip = 0
    if jfrog_path and jfrog_path.is_file():
        jdf = pd.read_parquet(jfrog_path)
        if "repository_source" in jdf.columns:
            jdf = jdf[jdf["repository_source"] == "CDO-ENT-JFROG"]
        for row in jdf.to_dict(orient="records"):
            raw = str(row.get("core_python_package_name") or row.get("name") or "").strip()
            k = _pep503_name(raw) if raw else ""
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

    def is_pypi(row: dict[str, str] | None) -> bool:
        if not row:
            return False
        return (row.get("primary_type") or "") == "pypi" or (row.get("primary_purl") or "").startswith("pkg:pypi/")

    def is_cf(row: dict[str, str] | None) -> bool:
        if not row:
            return False
        return bool(row.get("conda_purl") or row.get("Conda-Forge_FeedStock_URL"))

    both = pypi_only = cf_only = neither = 0
    neither_rows: list[list[str]] = []
    need_pr: list[tuple[dict[str, str], dict[str, str]]] = []
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
                    f"{_as_int(jr.get('artifactory_downloads') or '0')}",
                    jr.get("packaging_tier") or "",
                ]
            )
        on_cf = bool(ident_row and (ident_row.get("Conda-Forge_FeedStock_URL") or ident_row.get("conda_purl")))
        has_pr = bool(ident_row and ident_row.get("Staged_Recipes_PR_URL"))
        if ident_row and not on_cf and not has_pr:
            need_pr.append((jr, ident_row))
    neither_rows.sort(key=lambda r: (-_as_int(r[1]), r[0].lower()))
    parseable = len(jfrog_by)
    pick = []
    any_sig = 0
    for jr, ident_row in need_pr:
        plat = _as_int(jr.get("platform_env_count") or "0")
        ic = _as_int(jr.get("internal_component_count") or "0")
        apps = _as_int(jr.get("internal_app_count") or "0")
        if plat > 0 or ic > 0 or apps > 0:
            any_sig += 1
        if plat > 0 and ic > 0:
            pick.append((jr, ident_row, plat, ic, apps))
    pick.sort(key=lambda t: -_as_int(t[0].get("artifactory_downloads") or "0"))
    top_dl = sorted(need_pr, key=lambda t: -_as_int(t[0].get("artifactory_downloads") or "0"))[:12]
    board_gap = []
    for k, jr in jfrog_by.items():
        ident_row = ident.get(k)
        if is_pypi(ident_row) and not is_cf(ident_row) and ident_row and not ident_row.get("OpenTeams_Issue_URL"):
            board_gap.append([jr.get("name") or k, f"{_as_int(jr.get('artifactory_downloads') or '0')}"])
    board_gap.sort(key=lambda r: (-_as_int(r[1]), r[0].lower()))

    return [
        "## CDO-ENT-JFROG → PyPI / conda-forge",
        "",
        f"Parseable unique JFROG names **{parseable:,}** (skipped empty {skip}).",
        f"Both **{both:,}** ({_pct(both, parseable)}) · PyPI only **{pypi_only:,}**",
        f"({_pct(pypi_only, parseable)}) · conda-forge only **{cf_only:,}**",
        f"({_pct(cf_only, parseable)}) · neither **{neither:,}** ({_pct(neither, parseable)}).",
        "",
        *md_table(
            ["Bucket", "Rows", "Share"],
            [
                ["PyPI URL verified", f"{both + pypi_only:,}", _pct(both + pypi_only, parseable)],
                ["conda-forge URL verified", f"{both + cf_only:,}", _pct(both + cf_only, parseable)],
                ["Both", f"{both:,}", _pct(both, parseable)],
                ["PyPI only", f"{pypi_only:,}", _pct(pypi_only, parseable)],
                ["conda-forge only", f"{cf_only:,}", _pct(cf_only, parseable)],
                ["Neither", f"{neither:,}", _pct(neither, parseable)],
            ],
        ),
        "",
        "### No verified PyPI or conda-forge URL",
        "",
        *md_table(["Package", "Artifactory downloads", "Packaging tier"], neither_rows),
        "",
        "## JFROG names needing a staged-recipes PR",
        "",
        f"Not on conda-forge and no staged-recipes PR: **{len(need_pr):,}**.",
        f"Platform envs and internal components both > 0: **{len(pick)}**.",
        f"Any platform or internal signal: **{any_sig:,}**.",
        "",
        *md_table(
            ["Package", "Downloads", "Platform envs", "Internal components", "Apps", "Work", "Tracker"],
            [
                [
                    t[0].get("name") or "",
                    f"{_as_int(t[0].get('artifactory_downloads') or '0'):,}",
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
                    f"{_as_int(t[0].get('artifactory_downloads') or '0'):,}",
                    str(_as_int(t[0].get("platform_env_count") or "0")),
                    str(_as_int(t[0].get("internal_component_count") or "0")),
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
    ]


def _external_source_rows(data_root: Path, atlas_root: Path) -> list[list[str]]:
    rows: list[list[str]] = []
    for label, relpath, how, legacy_tab in EXTERNAL_SOURCE_SPECS:
        count = _count_source_path(data_root, atlas_root, relpath)
        rows.append([label, f"{count:,}" if count is not None else "—", how, legacy_tab])
    return rows


def _count_source_path(data_root: Path, atlas_root: Path, relpath: str) -> int | None:
    candidates = [data_root / relpath, atlas_root / relpath]
    for path in candidates:
        if path.is_file() and path.suffix == ".parquet":
            try:
                return len(pd.read_parquet(path))
            except Exception:
                return None
        if path.is_file() and path.suffix == ".json":
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, list):
                    return len(payload)
            except Exception:
                return None
    return None
