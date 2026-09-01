#!/usr/bin/env python3
"""Build OpenTeams identity rows from the Atlas Phase D identity export.

Since Story 21.7, this script never fetches ASSOCIATOR_URL, the OpenTeams
board, feedstock-outputs, or staged-recipes PRs itself: `main()` reads
`identity_export_parquet` (pyforge-atlas Kedro catalog, Story 21.6's
`upstream_discovery` join -- PURL Associator + OpenTeams board + feedstock/
staged-PR/local-recipe overlays, one row per
CDO-ENT-JFROG/CDO-ENT-CONDA package plus board-only extras) via
`PYFORGE_ATLAS_DATA_ROOT`. Run `pixi run -e pyforge-atlas
pyforge-atlas-bootstrap` first; a missing Parquet is a hard error, never a
live-fetch fallback.

Packaging location URLs (same columns the conda-forge packages page and
the two recipe trees expose) -- Conda-Forge_FeedStock_URL/Metadata_URL,
Staged_Recipes_PR_URL -- come from that same Parquet. Local_Recipes_URL
and Local_Build_Status are the two exceptions: they are always freshly
re-derived from a live `recipes/` filesystem scan (`overlay_live_local`,
run unconditionally on every `main()`/`--gist-only` invocation) -- the
Parquet's own values for those two columns are never used downstream.

After writing the workbook tab, publish (edit in place, never create) the
pinned secret gist files mgmt-wf-python-modernization-identity.md (row
catalog) and mgmt-wf-python-modernization-dashboards.md (P/work, issue
gap, census, Artifactory map) unless --skip-gist. The gist id is not in
git: set OPENTEAMS_IDENTITY_GIST_ID,
conf/conda-forge-packaging-inventory-operations.local.env, or --gist-id.
`--gist-only` republishes from the identity Parquet merged with ranking
columns (P/Rank/Score/Work + JFROG) from the ranked identity tab
(`priority.py`'s output) by name, without regenerating identity rows.

Default output snapshot tab identity-2026-08-12 is not a source input.
Pass --tab-out to write a dated tab without overwriting an older snapshot.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

COLUMNS = [
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
]

TAB_OUT = "identity-2026-08-12"
OSS_MILESTONE = "OSS Enhancements (Conda Forge, Pixi, ect)"
PACKAGING_TITLE_RE = re.compile(r"^\[Conda-Forge Packaging\]\s+(.+?)\s*$", re.I)
DEFAULT_GH = Path(__file__).resolve().parent.parent / ".pixi/envs/local-recipes/bin/gh"
REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = Path("/tmp/openteams-identity")
# Story 21.7 (CAP-4, quartet thin-out): identity rows come from the Atlas Phase D
# join (Story 21.6's identity_export_parquet) -- never a direct fetch. Path mirrors
# the PYFORGE_ATLAS_DATA_ROOT / ${paths.data_root} convention globals.yml uses
# (Story 21.1), resolved the same way `kedro run` resolves a relative data_root:
# against the pyforge-atlas project directory (the documented bootstrap task's cwd).
PYFORGE_ATLAS_DATA_ROOT_ENV = "PYFORGE_ATLAS_DATA_ROOT"
PYFORGE_ATLAS_PROJECT_DIR = REPO_ROOT / "src/shared/packages/pyforge-atlas"
IDENTITY_EXPORT_PARQUET_RELPATH = Path(
    "derived/identity_export_parquet/identity_export_parquet.parquet"
)
IDENTITY_COMPLETE_EXPORT_RELPATH = Path(
    "derived/identity_complete_export/identity_complete_export.parquet"
)
GIST_FILENAME = "mgmt-wf-python-modernization-identity.md"
GIST_DASHBOARD_FILENAME = "mgmt-wf-python-modernization-dashboards.md"
GIST_ID_ENV = "OPENTEAMS_IDENTITY_GIST_ID"
LOCAL_ENV_PATH = REPO_ROOT / "conf/conda-forge-packaging-inventory-operations.local.env"
GIST_SCHEMA = [
    ("P", "enum", "yes", "Proposed priority `P1`–`P10`."),
    ("Rank", "int", "yes", "1-based rank across the snapshot (P1 first)."),
    ("Score", "int", "yes", "Use-score percentile 1–100."),
    ("Package", "string", "yes", "Display name (same identity as Core_Python_Package_Name)."),
    ("Work", "enum", "yes", "`Fix vulnerability` | `Create recipe` | `File OpenTeams tracking issue [Conda-Forge Packaging]` | `Already tracked`."),
    ("Platforms", "int", "no", "JFROG `platform_env_count`."),
    ("Apps", "int", "no", "JFROG `internal_app_count`."),
    ("Downloads", "int", "no", "JFROG `artifactory_downloads`."),
    ("Versions", "int", "no", "JFROG `artifactory_version_count`."),
    ("Vuln", "enum", "no", "JFROG `vuln_status` (`affected_latest`, `clean`, …)."),
    ("Core_Python_Package_Name", "string", "yes", "Primary key. Conda/PyPI package identity as stored (unique)."),
    ("OpenTeams_Title", "string", "yes", "Issue title `[Conda-Forge Packaging] {name}`."),
    ("identity_source", "enum", "yes", "`purl-associator` | `inventory` | `none` | `openteams-board`."),
    ("associator_key", "string", "no", "Key matched in prefix-dev/purl-associator mappings-index. Blank if unused."),
    ("associator_status", "string", "no", "Associator status, or `inventory-derived` / `unmapped`."),
    ("primary_purl", "purl", "no", "Upstream PURL (`pkg:pypi/…` or `pkg:github/…`). Not a conda PURL."),
    ("primary_type", "enum", "no", "`pypi` | `github` | `git` | blank."),
    ("alternative_purls", "purl[]", "no", "`; `-joined extra PURLs."),
    ("cpes", "string[]", "no", "`; `-joined CPEs from the associator."),
    ("conda_purl", "purl", "no", "`pkg:conda/{name}?channel=conda-forge` only when on conda-forge."),
    ("source_repository_url", "url", "no", "Upstream VCS URL. Not a feedstock and not PyPI/anaconda."),
    ("OpenTeams_Issue_URL", "url", "no", "GitHub issue on OpenTeams-WFT-CDO/mgmt-wf-python-modernization."),
    ("Conda-Forge_FeedStock_URL", "url[]", "no", "`; `-joined github.com/conda-forge/{repo}-feedstock from conda-forge.org/packages."),
    ("Conda-Forge_Metadata_URL", "url", "no", "Packages-page Browse link: conda-metadata-app.streamlit.app/?q=conda-forge/{pkg}."),
    ("Staged_Recipes_PR_URL", "url", "no", "Best conda-forge/staged-recipes PR (open file path, else title; prefer open then merged)."),
    ("Local_Recipes_URL", "url[]", "no", "`; `-joined github.com/rxm7706/local-recipes/tree/main/recipes/{dir}."),
    ("Local_Build_Status", "enum", "no", "`success` | `failed` | `build-clean-test-blocked` | `not-attempted`. From the local `recipe.yaml` CFE stamp. Blank if no stamp."),
    ("Verification_Timestamp_UTC", "datetime", "yes", "ISO 8601 UTC generation time for this snapshot."),
    ("Priority_Bucket_Description", "string", "yes", "Human description of `P`."),
    ("Priority_Source", "string", "no", "Assignment source (`current-version-vuln`, `platform`, `work-create-recipe`, …)."),
    ("Priority_Reason", "string", "no", "Short reason for this `P`."),
    ("JFROG_risk_level", "enum", "no", "`HIGH` | `MEDIUM` | `LOW` | `NO_DATA`."),
    ("JFROG_latest_vuln_count", "int", "no", "Basilisk latest-version known vulnerability count."),
    ("internal_component_count", "int", "no", "JFROG internal component count."),
    ("internal_lob_count", "int", "no", "JFROG internal LOB count."),
]
GIST_COLUMNS = [name for name, _typ, _req, _meaning in GIST_SCHEMA]
# Ranking + JFROG columns merged from the ranked identity tab at --gist-only
# publish time (Story 21.7; identity-contract.md "Ranking columns"). Derived,
# not hand-listed, so a future GIST_SCHEMA addition is picked up automatically.
RANKING_MERGE_COLUMNS = [c for c in GIST_COLUMNS if c not in COLUMNS and c != "Package"]
LOCAL_RECIPES_URL = "https://github.com/rxm7706/local-recipes/tree/main/recipes/{dir}"
CFE_BUILD_STATUS_RE = re.compile(r"(?m)^  cfe-local-build-status:\s*(\S+)")
LOCAL_DIR_FROM_URL_RE = re.compile(r"/recipes/([^/\s]+)\s*$")
NOARCH_LINE_RE = re.compile(r"(?m)^\s*noarch:\s*['\"]?([A-Za-z0-9_-]+)")
COMPILER_LINE_RE = re.compile(
    r"(?:\{\{\s*compiler\s*\(|\$\{\{\s*compiler\s*\(|"
    r"\{\{\s*stdlib\s*\(|\$\{\{\s*stdlib\s*\()"
)
P_ORDER = ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10")
RECIPE_TYPE_ORDER = (
    "noarch-python",
    "noarch-generic",
    "compiled",
    "arch",
    "none",
)
BUILD_STATUS_ORDER = (
    "success",
    "build-clean-test-blocked",
    "failed",
    "blocked-missing-ortools",
    "not-attempted",
    "blank",
)
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
    "example",
    "new",
    "the",
    "a",
    "an",
    "for",
    "and",
    "with",
    "using",
    "from",
    "initial",
    "commit",
    "support",
    "fix",
    "update",
    "bump",
    "r",
}
RECIPE_NAME_RE = re.compile(
    r"(?m)^(?:package:\s*\n(?:[ \t].*\n)*?[ \t]+name:\s*|"
    r"[ \t]+- name:\s*|"
    r"[ \t]+name:\s*)[\"']?([A-Za-z0-9][A-Za-z0-9._+-]*)"
)


def join_list(values: list[str]) -> str:
    return "; ".join(v for v in values if v)


def pep503_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", (value or "").strip().lower()).strip("-")


def packaging_name_from_title(title: str) -> str | None:
    m = PACKAGING_TITLE_RE.match((title or "").strip())
    if not m:
        return None
    name = pep503_name(m.group(1))
    return name or None


def gh_bin() -> str | None:
    if DEFAULT_GH.is_file():
        return str(DEFAULT_GH)
    return shutil.which("gh")


def load_local_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip("'").strip('"')
    return out


def resolve_gist_id(cli_value: str | None) -> str | None:
    for candidate in (
        (cli_value or "").strip(),
        os.environ.get(GIST_ID_ENV, "").strip(),
        load_local_env(LOCAL_ENV_PATH).get(GIST_ID_ENV, "").strip(),
    ):
        if candidate:
            return candidate
    return None


ISSUE_CREATE_REPO = "OpenTeams-WFT-CDO/mgmt-wf-python-modernization"
PROJECT_OWNER = "OpenTeams-WFT-CDO"
PROJECT_NUMBER = "1"


def create_missing_issues(
    gh: str | None,
    records: list[dict[str, str]],
    board: dict[str, str],
    dry_run: bool = True,
) -> list[tuple[str, str]]:
    """One GitHub issue per record missing ``OpenTeams_Issue_URL``.

    Additive-only and idempotent: this only ever creates issues for records
    that don't already carry an ``OpenTeams_Issue_URL`` (Story 21.7: that
    join now happens once, upstream, in Atlas's Phase D identity export) --
    it never edits, closes, or re-titles an existing issue. A row with a
    blank/missing ``Core_Python_Package_Name`` is skipped (never produces a
    garbage ``[Conda-Forge Packaging] `` title).

    A created issue is also added to OpenTeams project 1. ``board`` is a
    write-only bookkeeping sink here (never read back by this script since
    Story 21.7 -- a future Atlas pipeline run's own board join picks it up):
    ``row["OpenTeams_Issue_URL"]``/``board[...]`` are only updated once BOTH
    the issue-create and the project-item-add calls succeed -- if item-add
    fails after a successful create, the row is left unmarked (still
    reported via the return value) so a future run retries adding it to the
    project board instead of silently treating it as done forever.

    ``dry_run`` (the default, ``--create-issues`` absent) makes no ``gh``
    mutation call: it only prints and returns the ``(name, title)`` pairs
    that would be created. With ``dry_run=False`` a non-zero ``gh`` exit (or
    the ``gh`` binary vanishing mid-run) for one name is logged to stderr and
    does not abort the remaining names.
    """
    missing = [
        row
        for row in records
        if not (row.get("OpenTeams_Issue_URL") or "").strip()
        and (row.get("Core_Python_Package_Name") or "").strip()
    ]
    if not missing:
        return []
    if dry_run:
        result: list[tuple[str, str]] = []
        for row in missing:
            name = row.get("Core_Python_Package_Name", "")
            title = row.get("OpenTeams_Title") or f"[Conda-Forge Packaging] {name}"
            print(f"[dry-run] would create issue: {name} -- {title}", flush=True)
            result.append((name, title))
        return result
    if not gh:
        raise SystemExit("gh not found; cannot create issues with --create-issues")
    created: list[tuple[str, str]] = []
    for row in missing:
        name = row.get("Core_Python_Package_Name", "")
        title = row.get("OpenTeams_Title") or f"[Conda-Forge Packaging] {name}"
        try:
            url = subprocess.check_output(
                [gh, "issue", "create", "--repo", ISSUE_CREATE_REPO, "--title", title],
                text=True,
            ).strip()
        except (subprocess.CalledProcessError, OSError) as exc:
            print(f"gh issue create failed for {name}: {exc}", file=sys.stderr)
            continue
        try:
            subprocess.check_call(
                [
                    gh,
                    "project",
                    "item-add",
                    "--owner",
                    PROJECT_OWNER,
                    "--number",
                    PROJECT_NUMBER,
                    "--url",
                    url,
                ]
            )
        except (subprocess.CalledProcessError, OSError) as exc:
            print(
                f"gh project item-add failed for {name} ({url}): {exc}",
                file=sys.stderr,
            )
            created.append((name, title))
            continue
        row["OpenTeams_Issue_URL"] = url
        board[pep503_name(name)] = url
        created.append((name, title))
    return created


def name_keys(row: dict[str, str]) -> list[str]:
    keys: list[str] = []
    for raw in (
        row.get("Core_Python_Package_Name", ""),
        row.get("associator_key", ""),
    ):
        if not raw:
            continue
        for cand in (raw, raw.lower(), pep503_name(raw), raw.replace("-", "_")):
            if cand and cand not in keys:
                keys.append(cand)
    return keys


def first_map(mapping: dict[str, str], keys: list[str]) -> str:
    for key in keys:
        if key in mapping and mapping[key]:
            return mapping[key]
    return ""


def load_local_recipes(recipes_dir: Path) -> dict[str, str]:
    """PEP 503 package/dir name -> GitHub tree URL for this repo's recipes/."""
    out: dict[str, str] = {}
    if not recipes_dir.is_dir():
        return out
    for d in sorted(p for p in recipes_dir.iterdir() if p.is_dir() and not p.name.startswith(".")):
        url = LOCAL_RECIPES_URL.format(dir=d.name)
        names = {pep503_name(d.name)}
        for fname in ("recipe.yaml", "meta.yaml"):
            fpath = d / fname
            if not fpath.is_file():
                continue
            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for m in RECIPE_NAME_RE.finditer(text):
                token = pep503_name(m.group(1))
                if token and token not in TITLE_STOP:
                    names.add(token)
        for name in names:
            if name and name not in out:
                out[name] = url
            elif name and out.get(name) and out[name] != url:
                if url not in out[name].split("; "):
                    out[name] = join_list([out[name], url])
    return out


def load_local_build_status(recipes_dir: Path) -> dict[str, str]:
    """PEP 503 / dir name -> CFE ``cfe-local-build-status`` from recipe.yaml."""
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
        names = {pep503_name(d.name), d.name.lower()}
        for rm in RECIPE_NAME_RE.finditer(text):
            token = pep503_name(rm.group(1))
            if token and token not in TITLE_STOP:
                names.add(token)
        for name in names:
            if name and name not in out:
                out[name] = status
    return out


def overlay_live_local(records: list[dict[str, str]], recipes_dir: Path) -> None:
    """Fill Local_Recipes_URL + Local_Build_Status from the live recipes/ tree."""
    local_map = load_local_recipes(recipes_dir)
    status_map = load_local_build_status(recipes_dir)
    for row in records:
        keys = name_keys(row)
        pkg = row.get("Package") or ""
        if pkg:
            keys = list(keys)
            for cand in (pkg, pkg.lower(), pep503_name(pkg)):
                if cand and cand not in keys:
                    keys.append(cand)
        url = first_map(local_map, keys) or row.get("Local_Recipes_URL") or ""
        row["Local_Recipes_URL"] = url
        status = first_map(status_map, keys)
        if not status and url:
            m = LOCAL_DIR_FROM_URL_RE.search(url.split(";")[0].strip())
            if m:
                slug = m.group(1)
                status = (
                    status_map.get(pep503_name(slug))
                    or status_map.get(slug.lower())
                    or ""
                )
        row["Local_Build_Status"] = status


def classify_recipe_text(text: str) -> str:
    """noarch-python | noarch-generic | compiled | arch from recipe/meta body."""
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
    """Recipe directory name -> classify_recipe_text result (or ``none``)."""
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


def emit_status_block(lines: list[str], indent: str, counts: Counter) -> None:
    lines.append(f"{indent}rows: {sum(counts.values())}")
    for status in BUILD_STATUS_ORDER:
        n = counts.get(status, 0)
        if n:
            lines.append(f"{indent}{status}: {n}")
    extra = sorted(k for k in counts if k not in BUILD_STATUS_ORDER)
    for status in extra:
        lines.append(f"{indent}{status}: {counts[status]}")


def read_xlsx_tab(xlsx: Path, tab: str) -> list[dict[str, str]]:
    wb = load_workbook(xlsx, read_only=True, data_only=True)
    ws = wb[tab]
    rows_iter = ws.iter_rows(values_only=True)
    header = [str(h) if h is not None else "" for h in next(rows_iter)]
    rows = []
    for raw in rows_iter:
        rows.append({h: ("" if v is None else str(v).strip()) for h, v in zip(header, raw)})
    wb.close()
    return rows


def identity_export_parquet_path() -> Path:
    """Physical location of the Atlas Kedro catalog's ``identity_export_parquet``
    dataset (Story 21.6, CAP-3) -- the ONLY input to this script's identity rows
    since Story 21.7. Mirrors ``${paths.data_root}`` (default ``data``, override
    via ``PYFORGE_ATLAS_DATA_ROOT``), resolved against the pyforge-atlas project
    directory the same way the documented ``pyforge-atlas-bootstrap`` task's
    ``kedro run`` (cwd ``src/shared/packages/pyforge-atlas``) resolves it."""
    data_root = Path(os.environ.get(PYFORGE_ATLAS_DATA_ROOT_ENV, "data"))
    if not data_root.is_absolute():
        data_root = PYFORGE_ATLAS_PROJECT_DIR / data_root
    return data_root / IDENTITY_EXPORT_PARQUET_RELPATH


def identity_complete_export_parquet_path() -> Path:
    """Physical location of Story 23.5's ``identity_complete_export.parquet``."""
    data_root = Path(os.environ.get(PYFORGE_ATLAS_DATA_ROOT_ENV, "data"))
    if not data_root.is_absolute():
        data_root = PYFORGE_ATLAS_PROJECT_DIR / data_root
    return data_root / IDENTITY_COMPLETE_EXPORT_RELPATH


def read_identity_export_records() -> list[dict[str, str]] | None:
    """Read the Atlas Phase D identity export Parquet -- replaces the retired
    ASSOCIATOR_URL/board/feedstock-outputs/staged-prs fetch-and-join block
    (Story 21.7). Never falls back to a live fetch: a missing Parquet is a
    hard, named error (I/O & Edge-Case Matrix), reported here and signaled to
    the caller as ``None`` rather than raising."""
    path = identity_export_parquet_path()
    if not path.is_file():
        print(
            f"identity_export_parquet not found at {path} -- run "
            "`pixi run -e pyforge-atlas pyforge-atlas-bootstrap` first",
            file=sys.stderr,
        )
        return None
    df = pd.read_parquet(path)
    return [
        {str(k): ("" if pd.isna(v) else str(v).strip()) for k, v in row.items()}
        for row in df.to_dict(orient="records")
    ]


def merge_ranking_columns(
    identity_records: list[dict[str, str]], ranked_records: list[dict[str, str]]
) -> list[dict[str, str]]:
    """Merge ``RANKING_MERGE_COLUMNS`` (P/Rank/Score/Work + JFROG/priority
    fields) from ``ranked_records`` (the priority.py-ranked identity tab) onto
    ``identity_records`` (the Atlas Phase D Parquet export), matched by
    ``Core_Python_Package_Name``. A Parquet name with no match in the ranked
    tab is dropped -- P/Rank/Score/Work are GIST_SCHEMA-required, so a row
    that cannot carry them is never published -- and a stderr warning names
    it (I/O & Edge-Case Matrix "a name has no cross-source match": never
    silent-drop, never raise). ``Package`` (GIST_SCHEMA-required) is set on
    every merged row from ``Core_Python_Package_Name`` -- it is deliberately
    excluded from ``RANKING_MERGE_COLUMNS`` (the ranked tab is not its source
    of truth), so it must be set unconditionally here or every published gist
    row would carry a blank required column."""
    ranking_by_name = {
        pep503_name(row["Core_Python_Package_Name"]): row
        for row in ranked_records
        if (row.get("Core_Python_Package_Name") or "").strip()
    }
    merged: list[dict[str, str]] = []
    for row in identity_records:
        name = row.get("Core_Python_Package_Name", "")
        ranking_row = ranking_by_name.get(pep503_name(name))
        if ranking_row is None:
            print(
                f"No ranking match for {name!r} in the identity tab; skipping row",
                file=sys.stderr,
            )
            continue
        out = dict(row)
        out["Package"] = row.get("Core_Python_Package_Name", "")
        for col in RANKING_MERGE_COLUMNS:
            if col in ranking_row:
                out[col] = ranking_row[col]
        merged.append(out)
    return merged


def write_csv(path: Path, records: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for rec in records:
            w.writerow({c: rec.get(c, "") for c in COLUMNS})


def write_xlsx_tab(xlsx: Path, records: list[dict[str, str]], tab: str = TAB_OUT) -> None:
    wb = load_workbook(xlsx)
    if tab in wb.sheetnames:
        del wb[tab]
    ws = wb.create_sheet(tab)
    ws.append(COLUMNS)
    for rec in records:
        ws.append([rec.get(c, "") for c in COLUMNS])
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    wb.save(xlsx)
    wb.close()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _as_int(value: str) -> int:
    try:
        return int(float(str(value).replace(",", "").strip() or 0))
    except ValueError:
        return 0


WORK_DASH_ORDER = (
    "Fix vulnerability",
    "Create recipe",
    "File OpenTeams tracking issue [Conda-Forge Packaging]",
    "Already tracked",
)


def write_gist_markdown(
    path: Path,
    identity_md: str,
) -> None:
    path.write_text(identity_md, encoding="utf-8")


def write_dashboard_markdown(
    path: Path,
    dashboards_md: str,
    records: list[dict[str, str]],
    tab: str,
    ops_canvas: Path | None = None,
    workbook_canvas: Path | None = None,
    xlsx: Path | None = None,
) -> None:
    path.write_text(dashboards_md, encoding="utf-8")
    # Canvas writers stay on the legacy in-script computation path (Story 23.6
    # scope: markdown bodies only; canvas deprecation is Story 22.6).
    script_dir = str(Path(__file__).resolve().parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    import types
    from openteams_identity_dashboards import (
        DEFAULT_OPS_CANVAS_PATH,
        DEFAULT_WORKBOOK_CANVAS_PATH,
        write_ops_canvas,
        write_workbook_canvas,
    )

    helpers = types.SimpleNamespace(**globals())
    try:
        write_ops_canvas(ops_canvas or DEFAULT_OPS_CANVAS_PATH, records, tab, helpers=helpers)
    except Exception as exc:
        print(f"ops canvas write failed ({exc}); continuing", file=sys.stderr)
    if xlsx is not None:
        try:
            write_workbook_canvas(
                workbook_canvas or DEFAULT_WORKBOOK_CANVAS_PATH,
                records,
                xlsx,
                tab,
                helpers=helpers,
            )
        except Exception as exc:
            print(f"workbook canvas write failed ({exc}); continuing", file=sys.stderr)


def gist_file_names(gh: str, gist_id: str) -> set[str]:
    raw = subprocess.check_output(
        [gh, "api", f"gists/{gist_id}", "--jq", ".files | keys | .[]"],
        text=True,
    )
    return {line.strip().strip('"') for line in raw.splitlines() if line.strip()}


def publish_identity_gist(
    gh: str,
    gist_id: str,
    filename: str,
    md_path: Path,
    existing: set[str] | None = None,
) -> None:
    names = existing if existing is not None else gist_file_names(gh, gist_id)
    if filename in names:
        subprocess.check_call(
            [gh, "gist", "edit", gist_id, "--filename", filename, str(md_path)]
        )
    else:
        subprocess.check_call([gh, "gist", "edit", gist_id, "--add", str(md_path)])


def publish_gist_files(
    gh: str,
    gist_id: str,
    identity_path: Path,
    dashboard_path: Path,
) -> None:
    existing = gist_file_names(gh, gist_id)
    publish_identity_gist(gh, gist_id, GIST_FILENAME, identity_path, existing)
    publish_identity_gist(
        gh, gist_id, GIST_DASHBOARD_FILENAME, dashboard_path, existing
    )


def publish_gist_from_export(
    export_path: Path,
    gist_id_cli: str | None,
    tab: str = TAB_OUT,
    ops_canvas: Path | None = None,
    workbook_canvas: Path | None = None,
    xlsx: Path | None = None,
    skip_gist: bool = False,
) -> int:
    """Edit the pinned gist from ``identity_complete_export.parquet`` (Story 23.6)."""
    if not export_path.is_file():
        print(
            f"identity_complete_export not found at {export_path} -- run "
            "`pixi run -e pyforge-atlas pyforge-atlas-bootstrap` first",
            file=sys.stderr,
        )
        return 1
    try:
        import pandas as pd

        if pd.read_parquet(export_path).empty:
            print(
                f"identity_complete_export is empty at {export_path}; refusing gist publish",
                file=sys.stderr,
            )
            return 1
    except Exception as exc:
        print(f"Could not read identity_complete_export at {export_path}: {exc}", file=sys.stderr)
        return 1

    gist_id = resolve_gist_id(gist_id_cli)
    if skip_gist and not gist_id:
        gist_id = "offline-test"
    if not gist_id:
        print(
            "Skipped gist publish (set "
            f"{GIST_ID_ENV}, {LOCAL_ENV_PATH}, or --gist-id)",
            flush=True,
        )
        return 1

    atlas_src = REPO_ROOT / "src/shared/packages/pyforge-atlas/src"
    if str(atlas_src) not in sys.path:
        sys.path.insert(0, str(atlas_src))
    from pyforge.atlas.dashboard import identity_gist

    try:
        identity_md, dashboards_md = identity_gist.render_identity_gist_markdown(
            export_path,
            gist_id=gist_id,
            repo_root=REPO_ROOT,
        )
    except identity_gist.IdentityGistError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    records = [
        {str(k): ("" if pd.isna(v) else str(v).strip()) for k, v in row.items()}
        for row in pd.read_parquet(export_path).to_dict(orient="records")
    ]
    overlay_live_local(records, REPO_ROOT / "recipes")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    md_path = CACHE_DIR / GIST_FILENAME
    dash_path = CACHE_DIR / GIST_DASHBOARD_FILENAME
    write_gist_markdown(md_path, identity_md)
    write_dashboard_markdown(
        dash_path,
        dashboards_md,
        records,
        tab,
        ops_canvas,
        workbook_canvas,
        xlsx=xlsx,
    )
    if skip_gist:
        print(f"Wrote gist markdown offline ({len(records):,} rows) to {CACHE_DIR}", flush=True)
        return 0

    gh = gh_bin()
    if not gh:
        print("gh not found; cannot publish identity gist", file=sys.stderr)
        return 1
    print(f"Publishing {len(records):,} rows ({len(GIST_COLUMNS)} cols) ...", flush=True)
    publish_gist_files(gh, gist_id, md_path, dash_path)
    print("Updated pinned identity gist in place (catalog + dashboards)")
    return 0


def publish_gist_from_tab(
    xlsx: Path,
    gist_id_cli: str | None,
    tab: str = TAB_OUT,
    ops_canvas: Path | None = None,
    workbook_canvas: Path | None = None,
) -> int:
    """Legacy alias — Story 23.6 reads ``identity_complete_export.parquet`` only."""
    return publish_gist_from_export(
        identity_complete_export_parquet_path(),
        gist_id_cli,
        tab,
        ops_canvas,
        workbook_canvas,
        xlsx=xlsx,
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--xlsx",
        type=Path,
        default=Path("docs/Analysis_Dataset-2026-08-12.xlsx"),
    )
    p.add_argument(
        "--tab-out",
        default=TAB_OUT,
        help="Identity output tab. Default: identity-2026-08-12.",
    )
    p.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Optional CSV path. Default: skip CSV (workbook tab only).",
    )
    p.add_argument(
        "--cache-dir",
        type=Path,
        default=CACHE_DIR,
        help="Cache dir for the gist markdown/dashboard files written before publish.",
    )
    p.add_argument(
        "--skip-gist",
        action="store_true",
        help="Do not edit the pinned identity gist (offline tests only).",
    )
    p.add_argument(
        "--create-issues",
        action="store_true",
        help=(
            "Create a GitHub issue (gh issue create) and add it to OpenTeams "
            "project 1 for every record missing OpenTeams_Issue_URL. Default: "
            "dry-run only -- print what would be created, no gh mutation call."
        ),
    )
    p.add_argument(
        "--gist-only",
        action="store_true",
        help=(
            "Publish the current identity tab to the gist (row catalog + "
            "canvas dashboards) without regenerating identity rows."
        ),
    )
    p.add_argument(
        "--gist-id",
        default=None,
        help=(
            "Secret gist to edit in place. Default: "
            f"{GIST_ID_ENV} or {LOCAL_ENV_PATH.name}. Never commit the id."
        ),
    )
    p.add_argument(
        "--ops-canvas",
        type=Path,
        default=None,
        help=(
            "Ops dashboard canvas output path (Priority/Issues/Builds/Census). "
            "Default: the live identity-ops.canvas.tsx under the Cursor project "
            "canvases dir. Override for offline tests."
        ),
    )
    p.add_argument(
        "--workbook-canvas",
        type=Path,
        default=None,
        help=(
            "Artifactory/workbook dashboard canvas output path. Default: the "
            "live jfrog-workbook.canvas.tsx under the Cursor project canvases "
            "dir. Override for offline tests."
        ),
    )
    args = p.parse_args()
    if args.gist_only:
        export_path = identity_complete_export_parquet_path()
        return publish_gist_from_export(
            export_path,
            args.gist_id,
            args.tab_out,
            args.ops_canvas,
            args.workbook_canvas,
            xlsx=args.xlsx,
            skip_gist=args.skip_gist,
        )
    if args.create_issues and not gh_bin():
        print(
            "gh not found; cannot use --create-issues (omit --create-issues for "
            "a dry-run, or install gh)",
            file=sys.stderr,
        )
        return 1

    records = read_identity_export_records()
    if records is None:
        return 1

    # Single-live-snapshot guarantee: overlay the live recipes/ tree once, here,
    # before ANY output (tab, CSV, or gist) is written -- write_gist_markdown's
    # own internal overlay_live_local call (unchanged) then re-runs on this
    # already-overlaid data for the gist step, so the persisted xlsx tab,
    # --output-csv, and the published gist all agree on Local_Recipes_URL/
    # Local_Build_Status/Verification_Timestamp_UTC within one run (Story 21.7
    # review pass 1: this call was dropped along with the retired fetch+join
    # block in the first attempt, letting the tab/CSV and gist silently diverge).
    overlay_live_local(records, REPO_ROOT / "recipes")

    created = create_missing_issues(gh_bin(), records, {}, dry_run=not args.create_issues)
    if created:
        label = "Created" if args.create_issues else "Would create (dry-run)"
        print(f"{label} {len(created)} missing OpenTeams issue(s):")
        for name, title in created:
            print(f"  {name}: {title}")

    write_xlsx_tab(args.xlsx, records, args.tab_out)
    if args.output_csv:
        write_csv(args.output_csv, records)

    counts = Counter(r["identity_source"] for r in records)
    timestamp = records[0].get("Verification_Timestamp_UTC", "") if records else ""
    print(f"Wrote {len(records):,} rows to {args.xlsx} tab {args.tab_out}")
    if args.output_csv:
        print(f"Wrote CSV {args.output_csv}")
    print("identity_source:", dict(counts))
    print("has primary_purl:", sum(1 for r in records if r["primary_purl"]))
    print("has conda_purl:", sum(1 for r in records if r["conda_purl"]))
    print("has OpenTeams_Issue_URL:", sum(1 for r in records if r["OpenTeams_Issue_URL"]))
    print(
        "has Conda-Forge_FeedStock_URL:",
        sum(1 for r in records if r["Conda-Forge_FeedStock_URL"]),
    )
    print(
        "has Conda-Forge_Metadata_URL:",
        sum(1 for r in records if r["Conda-Forge_Metadata_URL"]),
    )
    print(
        "has Staged_Recipes_PR_URL:",
        sum(1 for r in records if r["Staged_Recipes_PR_URL"]),
    )
    print("has Local_Recipes_URL:", sum(1 for r in records if r.get("Local_Recipes_URL")))
    print(
        "has Local_Build_Status:",
        sum(1 for r in records if r.get("Local_Build_Status")),
    )
    print("Verification_Timestamp_UTC:", timestamp)

    if args.skip_gist:
        print("Skipped gist publish (--skip-gist)")
        return 0
    return publish_gist_from_export(
        identity_complete_export_parquet_path(),
        args.gist_id,
        args.tab_out,
        args.ops_canvas,
        args.workbook_canvas,
        xlsx=args.xlsx,
    )


if __name__ == "__main__":
    sys.exit(main())
