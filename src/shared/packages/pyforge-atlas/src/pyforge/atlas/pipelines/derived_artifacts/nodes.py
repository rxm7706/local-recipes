"""``derived_artifacts`` pipeline nodes (Story B7, AC-3; Story 23.8; Story 23.3).

``build_universe_sbom`` — the full-universe CycloneDX BOM (§ 5.2 item 7): one conda
component per package (``?channel=conda-forge`` purl, ``cfe:pypi_name`` on mapped rows
for the matcher's universe membership), with ``cfe:atlas_built_at`` stamped in
metadata so consumers can enforce the AD-15 14-day freshness contract (refuse-stale,
exactly as the legacy ``universe_sbom`` gate).

``build_inventory_universe`` (Story 23.8, spec-23-8-workbook-free-metrics-universe.md)
— the ~38k-row full-inventory package universe that replaces
``docs/Analysis_Dataset-2026-08-12.xlsx`` as the source of the legacy
``conda-forge-packaging-inventory-operations_metrics.py`` script's package universe.
Unions 9 already-cataloged Parquet sources (the ones the story's Intent table maps
1:1 to the retired workbook's package-bearing sheets) into one row per PEP-503
``core_python_package_name``.

``derive_basilisk_vuln_rollup`` + ``assign_inventory_priority`` (Story 23.3) — port
``scripts/conda-forge-packaging-inventory-operations_priority.py``'s P1–P10 hierarchy
to Kedro-native Parquet over ``identity_packages_primary`` and enterprise inputs.

PURE nodes: pandas + stdlib only; no inline IO; ``dagster``/``kedro_mcp`` never imported
(AD-1). Reuses the ported purl primitives from the ``universal_sbom`` nodes.
"""

from __future__ import annotations

import math
import re
import time
from typing import Any

import pandas as pd

from ..universal_sbom.nodes import conda_purl


def build_universe_sbom(
    core_packages_enumerated: pd.DataFrame,
    pypi_conda_mapping: pd.DataFrame,
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Emit the full-universe CycloneDX BOM (one conda component per package). Stamps
    ``cfe:atlas_built_at`` (from ``params:universe_sbom.now`` if given, else now) so the
    matcher can refuse a stale atlas (AD-15). A mapped conda component carries a
    ``cfe:pypi_name`` property (the universe-membership signal, DW-B7-3)."""
    params = parameters or {}
    now = params.get("universe_sbom", {}).get("now")
    built_at = int(time.time() if now is None else now)

    # conda_name -> pypi_name (one component per mapped pair; legacy universe-sbom rule)
    pypi_by_conda: dict[str, str] = {}
    for _, r in pypi_conda_mapping.iterrows():
        cname, pname = r.get("conda_name"), r.get("pypi_name")
        if cname and not pd.isna(cname) and pname and not pd.isna(pname):
            pypi_by_conda.setdefault(str(cname), str(pname))

    components: list[dict[str, Any]] = []
    for _, r in core_packages_enumerated.iterrows():
        cname = r.get("conda_name")
        if not cname or pd.isna(cname):
            continue
        cname = str(cname)
        version = None if pd.isna(r.get("latest_version")) else r.get("latest_version")
        comp: dict[str, Any] = {
            "type": "library",
            "bom-ref": f"conda-{cname}-{version or 'unknown'}",
            "name": cname,
            "version": version or "",
            "purl": conda_purl(cname, version),
        }
        mapped = pypi_by_conda.get(cname)
        if mapped:
            comp["properties"] = [{"name": "cfe:pypi_name", "value": mapped}]
        components.append(comp)

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "metadata": {
            "component": {"type": "application", "name": "conda-forge-universe", "bom-ref": "conda-forge-universe"},
            "properties": [{"name": "cfe:atlas_built_at", "value": str(built_at)}],
        },
        "components": components,
    }


# ---------------------------------------------------------------------------
# Story 23.8 — inventory_universe (workbook-free metrics universe)
# ---------------------------------------------------------------------------
#
# The four helpers below (``_pep503``/``_clean_pkg_token``/``norm_pkg``/
# ``looks_like_pkg``) and ``parse_openteams_title`` are a VERBATIM port of
# ``scripts/conda-forge-packaging-inventory-operations_metrics.py``'s own
# same-named functions (spec Boundaries: "Name normalization is
# metrics.py::norm_pkg semantics ... port the two helpers verbatim into the
# node"). Duplicated, not shared, because metrics.py is a standalone stdlib-only
# script (no dependency on this package) and this node is pandas+stdlib-only
# (AD-1, no dagster/kedro_mcp import) — a shared util would require a new
# cross-boundary import either script would have to take on. Keep both copies
# in sync by hand if the parsing rules ever change.

_PKG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
_OPEN_TEAMS_BRACKET_RE = re.compile(r"^\[Conda-Forge Packaging\]\s+(.+?)\s*$", re.IGNORECASE)
_INVALID_PACKAGE_TOKENS = {
    "new",
    "ready",
    "done",
    "backlog",
    "blocked",
    "yes",
    "no",
    "n/a",
    "na",
}


def _pep503(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value.strip().lower()).strip("-")


def _clean_pkg_token(raw: str) -> str:
    s = (raw or "").strip()
    s = re.sub(r"\[.*?\]", "", s)
    s = re.sub(r"#\d+\b", "", s)
    s = re.sub(r"\s*(>=|==|~=|<=|!=|>|<).*$", "", s)
    return s.strip().strip("\"'")


def norm_pkg(value: str) -> str:
    return _pep503(_clean_pkg_token(value))


def looks_like_pkg(value: str) -> bool:
    raw = (value or "").strip()
    if not raw or _DATE_RE.match(raw) or re.fullmatch(r"\d+(\.0+)?", raw):
        return False
    v = norm_pkg(raw)
    if v in _INVALID_PACKAGE_TOKENS:
        return False
    if len(v) < 2:
        return False
    return bool(_PKG_RE.fullmatch(v))


def _split_package_list(value: str) -> list[str]:
    parts = re.split(r"[,;\n/]", value)
    return [norm_pkg(x) for x in parts if x and x.strip()]


def parse_openteams_title(title: str) -> tuple[str, list[str]]:
    """Rules a/b/c — verbatim port of metrics.py's own function of the same name."""
    t = (title or "").strip()
    if not t:
        return "c", []
    if "|" in t:
        rhs = t.split("|", 1)[1]
        pkgs = [x for x in _split_package_list(rhs) if looks_like_pkg(x)]
        return ("a", pkgs) if pkgs else ("c", [])
    m = _OPEN_TEAMS_BRACKET_RE.match(t)
    if m:
        pkgs = [x for x in _split_package_list(m.group(1)) if looks_like_pkg(x)]
        return ("b", pkgs) if pkgs else ("c", [])
    return "c", []


# core_python_package_name output column order.
_INVENTORY_UNIVERSE_COLUMNS: tuple[str, ...] = (
    "core_python_package_name",
    "package_input_names",
    "sources",
    "in_cdo_ent_jfrog",
    "in_cdo_ent_conda",
    "in_openteams",
    "in_conda_forge",
    "in_basilisk",
    "in_anaconda_main",
    "in_anaconda_dist",
    "in_aoss_free",
    "in_aoss_premium",
    "role",
    "openteams_universe_member",
)

# provenance label -> in_<source> flag column (spec Boundaries: these are STABLE
# strings inherited from the retired workbook's sheet names, byte-identical to
# today's Repository_Source values on the same package -- not live sheet names).
_TAB_CONDA_FORGE = "tab:Conda-Forge"
_TAB_ANACONDA_MAIN = "tab:Anaconda-Main"
_TAB_ANACONDA_DIST = "tab:Anaaconda-Dist"
_TAB_BASILISK = "tab:Basilisk"
_TAB_AOSS_FREE = "tab:GAOSS-Free"
_TAB_AOSS_PREMIUM = "tab:GAOSS-Premium"
_TAB_CDO_ENT_JFROG = "tab:CDO-ENT-JFROG"
_TAB_CDO_ENT_CONDA = "tab:CDO-ENT-CONDA"
_TAB_OPENTEAMS = "tab:OpenTeams"


def build_inventory_universe(
    core_packages_enumerated: pd.DataFrame,
    core_anaconda_main_packages: pd.DataFrame,
    discovery_anaconda_dist_2026x_raw: pd.DataFrame,
    discovery_basilisk_packages_raw: pd.DataFrame,
    discovery_aoss_free_python_raw: pd.DataFrame,
    discovery_aoss_premium_python_raw: pd.DataFrame,
    enterprise_jfrog_names: pd.DataFrame,
    enterprise_conda_maintainers: pd.DataFrame,
    openteams_project_1_board_raw: pd.DataFrame,
) -> pd.DataFrame:
    """Union the 9 Parquet sources that replace
    ``docs/Analysis_Dataset-2026-08-12.xlsx``'s package-bearing sheets into
    ``inventory_universe`` -- one row per PEP-503 ``core_python_package_name``
    (Story 23.8's Intent table has the full sheet -> source mapping).

    Never raises: an empty/malformed/missing-column input contributes zero rows
    for that source and is otherwise ignored (mirrors every other
    never-raise-degrade-to-empty node in this package). ``10kOpen`` (a stale
    ``CDO-ENT-JFROG`` clone) and ``10kClosed`` (no catalog source) are NOT
    reproduced by construction -- neither is one of the 9 inputs here (spec
    Design Notes: the known, accepted delta)."""
    acc: dict[str, dict[str, Any]] = {}

    def _touch(raw_value: str, label: str, flag: str, *, input_name: str | None = None) -> None:
        pkg = norm_pkg(str(raw_value))
        if not looks_like_pkg(pkg):
            return
        entry = acc.setdefault(pkg, {"input_names": set(), "sources": set(), "flags": set()})
        # metrics.py's parse_sheet_sources() falls back through Package_Name /
        # name / raw_names / Item / Title (in that order) for the RAW input
        # name it records -- an OpenTeams-sourced row has none of the first
        # four, so its raw input name is the FULL title text, not the
        # extracted package name. Callers pass `input_name` for that case;
        # every other source's raw value already IS the package name.
        raw_str = str(input_name if input_name is not None else raw_value).strip()
        if raw_str:
            entry["input_names"].add(raw_str)
        entry["sources"].add(label)
        entry["flags"].add(flag)

    def _from_name_column(df: pd.DataFrame, column: str, label: str, flag: str) -> None:
        if df is None or getattr(df, "empty", True) or column not in getattr(df, "columns", []):
            return
        for raw_value in df[column].dropna():
            _touch(raw_value, label, flag)

    _from_name_column(core_packages_enumerated, "conda_name", _TAB_CONDA_FORGE, "in_conda_forge")
    _from_name_column(core_anaconda_main_packages, "conda_name", _TAB_ANACONDA_MAIN, "in_anaconda_main")
    _from_name_column(discovery_anaconda_dist_2026x_raw, "conda_name", _TAB_ANACONDA_DIST, "in_anaconda_dist")
    _from_name_column(discovery_basilisk_packages_raw, "conda_name", _TAB_BASILISK, "in_basilisk")
    _from_name_column(discovery_aoss_free_python_raw, "pypi_name", _TAB_AOSS_FREE, "in_aoss_free")
    _from_name_column(discovery_aoss_premium_python_raw, "pypi_name", _TAB_AOSS_PREMIUM, "in_aoss_premium")

    # enterprise_jfrog_names: a pypi_name and/or a conda_name per row (Story 21.5's
    # names-only projection) -- either column, when present, counts as CDO-ENT-JFROG
    # membership for that name.
    if enterprise_jfrog_names is not None and not getattr(enterprise_jfrog_names, "empty", True):
        cols = set(enterprise_jfrog_names.columns)
        for name_col in ("pypi_name", "conda_name"):
            if name_col not in cols:
                continue
            for raw_value in enterprise_jfrog_names[name_col].dropna():
                _touch(raw_value, _TAB_CDO_ENT_JFROG, "in_cdo_ent_jfrog")

    # enterprise_conda_maintainers: core_python_package_name + role (Story 21.5).
    roles: dict[str, str] = {}
    if enterprise_conda_maintainers is not None and not getattr(enterprise_conda_maintainers, "empty", True):
        cols = set(enterprise_conda_maintainers.columns)
        if {"core_python_package_name", "role"} <= cols:
            for row in enterprise_conda_maintainers.itertuples(index=False):
                raw_name = getattr(row, "core_python_package_name", None)
                if raw_name is None or (not isinstance(raw_name, str) and pd.isna(raw_name)):
                    continue
                _touch(raw_name, _TAB_CDO_ENT_CONDA, "in_cdo_ent_conda")
                role = getattr(row, "role", None)
                if role in ("Maintainer", "Co-Maintainer"):
                    pkg = norm_pkg(str(raw_name))
                    if roles.get(pkg) != "Maintainer":
                        roles[pkg] = role

    # openteams_project_1_board_raw: parse_openteams_title over the `title` column
    # (rules a/b/c) -- rule "c" (no parseable package) contributes nothing.
    if openteams_project_1_board_raw is not None and not getattr(openteams_project_1_board_raw, "empty", True):
        if "title" in openteams_project_1_board_raw.columns:
            for raw_title in openteams_project_1_board_raw["title"].dropna():
                title_str = str(raw_title)
                rule, pkgs = parse_openteams_title(title_str)
                if rule == "c":
                    continue
                for pkg in pkgs:
                    _touch(pkg, _TAB_OPENTEAMS, "in_openteams", input_name=title_str)

    if not acc:
        return pd.DataFrame(columns=list(_INVENTORY_UNIVERSE_COLUMNS))

    rows: list[dict[str, Any]] = []
    for pkg, entry in acc.items():
        flags = entry["flags"]
        in_jfrog = "in_cdo_ent_jfrog" in flags
        in_conda_ent = "in_cdo_ent_conda" in flags
        rows.append(
            {
                "core_python_package_name": pkg,
                "package_input_names": sorted(entry["input_names"]),
                "sources": sorted(entry["sources"]),
                "in_cdo_ent_jfrog": in_jfrog,
                "in_cdo_ent_conda": in_conda_ent,
                "in_openteams": "in_openteams" in flags,
                "in_conda_forge": "in_conda_forge" in flags,
                "in_basilisk": "in_basilisk" in flags,
                "in_anaconda_main": "in_anaconda_main" in flags,
                "in_anaconda_dist": "in_anaconda_dist" in flags,
                "in_aoss_free": "in_aoss_free" in flags,
                "in_aoss_premium": "in_aoss_premium" in flags,
                "role": roles.get(pkg, "N/A"),
                "openteams_universe_member": in_jfrog or in_conda_ent,
            }
        )
    return (
        pd.DataFrame(rows, columns=list(_INVENTORY_UNIVERSE_COLUMNS))
        .sort_values("core_python_package_name")
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Story 23.3 — inventory_priority_assignments (priority.py port)
# ---------------------------------------------------------------------------
#
# Verbatim port of ``scripts/conda-forge-packaging-inventory-operations_priority.py``
# rule hierarchy (spec Boundaries). Duplicated here — not imported from ``scripts/`` —
# because that script is openpyxl-bound and this node is pandas+stdlib-only (AD-1).

_PACK = re.compile(r"^\[Conda-Forge Packaging\]\s+(.+?)\s*$", re.I)
_BUCKET_ORDER = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10"]
_PRI_N = {b: i for i, b in enumerate(_BUCKET_ORDER, start=1)}
_WORK_FIX_VULN = "Fix vulnerability"
_WORK_CREATE = "Create recipe"
_WORK_ISSUE_CF = "File OpenTeams tracking issue [Conda-Forge Packaging]"
_WORK_ISSUE_CF_LEGACY = "File issue (on conda-forge)"
_WORK_ISSUE_MAINT_LEGACY = "File issue (maintained feedstock)"
_WORK_TRACKED = "Already tracked"
_WORK_ORDER = [_WORK_FIX_VULN, _WORK_CREATE, _WORK_ISSUE_CF, _WORK_TRACKED]
_WORK_RANK = {w: i for i, w in enumerate(_WORK_ORDER)}
_BATCH_TO_WORK = {
    "A": _WORK_CREATE,
    "B": _WORK_ISSUE_CF,
    "C": _WORK_ISSUE_CF,
    "TRACKED": _WORK_TRACKED,
    _WORK_FIX_VULN: _WORK_FIX_VULN,
    _WORK_CREATE: _WORK_CREATE,
    _WORK_ISSUE_CF: _WORK_ISSUE_CF,
    _WORK_ISSUE_CF_LEGACY: _WORK_ISSUE_CF,
    _WORK_ISSUE_MAINT_LEGACY: _WORK_ISSUE_CF,
    _WORK_TRACKED: _WORK_TRACKED,
}
_PRIORITY_DESC = {
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

_INVENTORY_PRIORITY_COLUMNS: tuple[str, ...] = (
    "core_python_package_name",
    "P",
    "Rank",
    "Score",
    "Work",
    "Priority_Bucket_Description",
    "Priority_Source",
    "Priority_Reason",
    "Proposed_Priority",
    "Packaging_Work",
    "Priority_Rank",
    "Priority_Score",
    "risk_level",
    "vuln_status",
    "jfrog_latest_vuln_count",
)

_BASILISK_ROLLUP_COLUMNS: tuple[str, ...] = (
    "conda_name",
    "risk_level",
    "vuln_status",
    "jfrog_latest_vuln_count",
)


def _priority_pep503(raw) -> str | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).strip().lower().replace("_", "-").replace(".", "-")
    s = re.sub(r"-+", "-", s).strip("-")
    return s if len(s) >= 2 else None


def _priority_num(v) -> float:
    try:
        return float(v) if v not in (None, "") else 0.0
    except (TypeError, ValueError):
        return 0.0


def _priority_filled(raw) -> bool:
    s = str(raw or "").strip()
    return bool(s) and s.upper() not in {"N/A", "NA", "NONE", "-"}


def _priority_use_score(plat: int, apps: int, ic: int, lob: int, downloads: int, versions: int) -> float:
    return (
        100.0 * plat
        + 10.0 * apps
        + 3.0 * ic
        + 2.0 * lob
        + math.log10(1.0 + downloads)
        + math.log10(1.0 + versions)
    )


def _priority_percentile_1_100(raws: list[float]) -> list[int]:
    n = len(raws)
    if n == 1:
        return [100]
    order = sorted(range(n), key=lambda i: (raws[i], i))
    out = [1] * n
    for rank, i in enumerate(order):
        out[i] = 1 + int(round(99.0 * rank / (n - 1)))
    return out


def _board_priority_from_row(row: Any) -> str:
    for key in ("priority", "Priority"):
        val = row.get(key) if isinstance(row, dict) else getattr(row, key, None)
        if val is not None and str(val).strip():
            return str(val).strip()
    milestone = row.get("milestone") if isinstance(row, dict) else getattr(row, "milestone", None)
    if milestone is not None and str(milestone).strip():
        m = str(milestone).strip()
        for prefix in ("P1", "P2", "P3"):
            if m.startswith(prefix):
                return prefix
    return ""


def _priority_board_maps(ot_rows: list[dict]) -> tuple[dict, dict]:
    by_url, by_name = {}, {}
    for r in ot_rows:
        title = r.get("title") or r.get("Title") or ""
        m = _PACK.match(str(title))
        if not m:
            continue
        rec = {
            "priority": _board_priority_from_row(r),
            "url": str(r.get("url") or r.get("URL") or "").strip(),
        }
        if rec["url"]:
            by_url[rec["url"]] = rec
        n = _priority_pep503(m.group(1))
        if n:
            by_name[n] = rec
    return by_url, by_name


def _priority_board_lock(ident: dict, name: str | None, by_url: dict, by_name: dict) -> str | None:
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


def _priority_is_current_vuln(j: dict | None) -> bool:
    if not j:
        return False
    return str(j.get("risk_level") or "") == "HIGH" or str(j.get("vuln_status") or "") == "affected_latest"


def _priority_work_label(ident: dict, inv: dict | None, j: dict | None) -> str:
    if _priority_is_current_vuln(j):
        return _WORK_FIX_VULN
    if inv:
        mapped = _BATCH_TO_WORK.get(str(inv.get("OpenTeams_Batch") or "").strip())
        if mapped and mapped != _WORK_FIX_VULN:
            return mapped
        cohort = str(inv.get("OpenTeams_Cohort") or "").strip()
        coverage = str(inv.get("OpenTeams_Coverage") or "").strip()
        if coverage == "Have_Issue":
            return _WORK_TRACKED
        if cohort == "JFROG_NEW":
            return _WORK_CREATE
        if cohort == "JFROG_ON_CF" or cohort == "CONDA_ONLY":
            return _WORK_ISSUE_CF
    if _priority_filled(ident.get("OpenTeams_Issue_URL")):
        return _WORK_TRACKED
    if _priority_filled(ident.get("conda_purl")) or _priority_filled(ident.get("Conda-Forge_FeedStock_URL")):
        return _WORK_ISSUE_CF
    return _WORK_CREATE


def _priority_assign_lane(
    ident: dict, name: str | None, j: dict | None, by_url: dict, by_name: dict
) -> tuple[str | None, str, str]:
    plat = int(_priority_num(j.get("platform_env_count")) if j else 0)
    apps = int(_priority_num(j.get("internal_app_count")) if j else 0)
    dl = int(_priority_num(j.get("artifactory_downloads")) if j else 0)
    ver = int(_priority_num(j.get("artifactory_version_count")) if j else 0)
    risk = str(j.get("risk_level") or "") if j else ""
    vuln = str(j.get("vuln_status") or "") if j else ""
    if risk == "HIGH" or vuln == "affected_latest":
        return "P1", "current-version-vuln", "latest version has confirmed advisories"
    locked = _priority_board_lock(ident, name, by_url, by_name)
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


def _parse_cvss_from_severity(severity: Any) -> float | None:
    if severity is None or (isinstance(severity, float) and pd.isna(severity)):
        return None
    if isinstance(severity, (int, float)):
        return float(severity)
    if isinstance(severity, str):
        try:
            return float(severity)
        except ValueError:
            return None
    if isinstance(severity, list):
        scores = [_parse_cvss_from_severity(item) for item in severity]
        scores = [s for s in scores if s is not None]
        return max(scores) if scores else None
    if isinstance(severity, dict):
        if "score" in severity:
            return _parse_cvss_from_severity(severity["score"])
        for key in ("baseScore", "base_score"):
            if key in severity:
                return _parse_cvss_from_severity(severity[key])
    return None


def _cvss_to_risk_level(cvss: float | None) -> str:
    if cvss is None:
        return "NO_DATA"
    if cvss >= 7.0:
        return "HIGH"
    if cvss >= 4.0:
        return "MEDIUM"
    if cvss > 0.0:
        return "LOW"
    return "NO_DATA"


def derive_basilisk_vuln_rollup(
    vulnerability_basilisk_advisories: pd.DataFrame,
    vulnerability_basilisk_details: pd.DataFrame,
) -> pd.DataFrame:
    """Per-package Basilisk rollup: one row per ``conda_name`` with advisory count,
    ``vuln_status``, and ``risk_level``. Names with zero advisories are absent."""
    if (
        vulnerability_basilisk_advisories is None
        or getattr(vulnerability_basilisk_advisories, "empty", True)
        or not {"conda_name", "advisory_id"} <= set(getattr(vulnerability_basilisk_advisories, "columns", []))
    ):
        return pd.DataFrame(columns=list(_BASILISK_ROLLUP_COLUMNS))

    adv = vulnerability_basilisk_advisories.copy()
    adv["conda_name"] = adv["conda_name"].map(lambda x: _priority_pep503(x) or str(x).strip().lower())
    adv = adv[adv["conda_name"].notna() & (adv["conda_name"] != "")]

    severity_by_id: dict[str, Any] = {}
    if (
        vulnerability_basilisk_details is not None
        and not getattr(vulnerability_basilisk_details, "empty", True)
        and "advisory_id" in getattr(vulnerability_basilisk_details, "columns", [])
    ):
        for row in vulnerability_basilisk_details.itertuples(index=False):
            aid = str(getattr(row, "advisory_id", "") or "")
            if aid:
                severity_by_id[aid] = getattr(row, "severity", None) if hasattr(row, "severity") else None

    rows: list[dict[str, Any]] = []
    for conda_name, grp in adv.groupby("conda_name", sort=True):
        advisory_ids = grp["advisory_id"].dropna().astype(str).unique()
        count = len(advisory_ids)
        if count == 0:
            continue
        cvss_scores = [_parse_cvss_from_severity(severity_by_id.get(aid)) for aid in advisory_ids]
        cvss_scores = [s for s in cvss_scores if s is not None]
        max_cvss = max(cvss_scores) if cvss_scores else None
        rows.append(
            {
                "conda_name": conda_name,
                "risk_level": _cvss_to_risk_level(max_cvss),
                "vuln_status": "affected_latest",
                "jfrog_latest_vuln_count": count,
            }
        )
    if not rows:
        return pd.DataFrame(columns=list(_BASILISK_ROLLUP_COLUMNS))
    return pd.DataFrame(rows, columns=list(_BASILISK_ROLLUP_COLUMNS)).reset_index(drop=True)


def _priority_str_field(raw) -> str:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return ""
    return str(raw).strip()


def _explicit_inv_from_identity(ident: dict) -> dict | None:
    inv = {
        "OpenTeams_Batch": _priority_str_field(ident.get("OpenTeams_Batch")),
        "OpenTeams_Cohort": _priority_str_field(ident.get("OpenTeams_Cohort")),
        "OpenTeams_Coverage": _priority_str_field(ident.get("OpenTeams_Coverage")),
    }
    return inv if any(inv.values()) else None


def _priority_inv_from_identity(
    ident: dict, in_jfrog: bool, on_cf: bool, in_conda_ent: bool
) -> dict[str, str]:
    derived_cohort = _derive_openteams_cohort(in_jfrog, on_cf, in_conda_ent)
    cohort = _priority_str_field(ident.get("OpenTeams_Cohort")) or derived_cohort
    return {
        "OpenTeams_Batch": _priority_str_field(ident.get("OpenTeams_Batch")),
        "OpenTeams_Cohort": cohort,
        "OpenTeams_Coverage": _priority_str_field(ident.get("OpenTeams_Coverage")),
    }


def _derive_openteams_cohort(in_jfrog: bool, on_conda_forge: bool, in_conda_ent: bool) -> str:
    if in_jfrog and not on_conda_forge:
        return "JFROG_NEW"
    if in_jfrog and on_conda_forge:
        return "JFROG_ON_CF"
    if in_conda_ent and not in_jfrog:
        return "CONDA_ONLY"
    return ""


def _on_conda_forge(ident: dict) -> bool:
    return _priority_filled(ident.get("conda_purl")) or _priority_filled(ident.get("Conda-Forge_FeedStock_URL"))


def assign_inventory_priority(
    identity_packages_primary: pd.DataFrame,
    enterprise_jfrog_consumption: pd.DataFrame,
    enterprise_conda_maintainers: pd.DataFrame,
    openteams_project_1_board_raw: pd.DataFrame,
    vulnerability_basilisk_rollup: pd.DataFrame,
    parameters: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Port ``priority.py``'s P1–P10 / Rank / Score / Work hierarchy over Kedro Parquet
    inputs (Story 23.3). Never raises; empty identity yields an empty typed frame."""
    _ = parameters  # reserved — no TTL/cadence gating for this pure derive node

    if identity_packages_primary is None or getattr(identity_packages_primary, "empty", True):
        return pd.DataFrame(columns=list(_INVENTORY_PRIORITY_COLUMNS))

    ident_cols = set(getattr(identity_packages_primary, "columns", []))
    if "Core_Python_Package_Name" not in ident_cols:
        return pd.DataFrame(columns=list(_INVENTORY_PRIORITY_COLUMNS))

    jfrog_by: dict[str, dict] = {}
    if (
        enterprise_jfrog_consumption is not None
        and not getattr(enterprise_jfrog_consumption, "empty", True)
        and "core_python_package_name" in getattr(enterprise_jfrog_consumption, "columns", [])
    ):
        for row in enterprise_jfrog_consumption.itertuples(index=False):
            key = _priority_pep503(getattr(row, "core_python_package_name", None))
            if key:
                jfrog_by[key] = row._asdict()

    conda_ent_names: set[str] = set()
    if (
        enterprise_conda_maintainers is not None
        and not getattr(enterprise_conda_maintainers, "empty", True)
        and "core_python_package_name" in getattr(enterprise_conda_maintainers, "columns", [])
    ):
        for row in enterprise_conda_maintainers.itertuples(index=False):
            key = _priority_pep503(getattr(row, "core_python_package_name", None))
            if key:
                conda_ent_names.add(key)

    vuln_by: dict[str, dict] = {}
    if (
        vulnerability_basilisk_rollup is not None
        and not getattr(vulnerability_basilisk_rollup, "empty", True)
        and "conda_name" in getattr(vulnerability_basilisk_rollup, "columns", [])
    ):
        for row in vulnerability_basilisk_rollup.itertuples(index=False):
            key = _priority_pep503(getattr(row, "conda_name", None))
            if key:
                vuln_by[key] = row._asdict()

    ot_rows: list[dict] = []
    if openteams_project_1_board_raw is not None and not getattr(openteams_project_1_board_raw, "empty", True):
        ot_rows = openteams_project_1_board_raw.to_dict(orient="records")
    by_url, by_name = _priority_board_maps(ot_rows)

    records: list[dict[str, Any]] = []
    for ident in identity_packages_primary.to_dict(orient="records"):
        name = _priority_pep503(ident.get("Core_Python_Package_Name")) or str(
            ident.get("Core_Python_Package_Name") or ""
        )
        key = _priority_pep503(ident.get("Core_Python_Package_Name"))
        j_raw = jfrog_by.get(key or "")
        v_raw = vuln_by.get(key or "")
        j: dict[str, Any] = {}
        if j_raw:
            j.update(j_raw)
        if v_raw:
            j["risk_level"] = v_raw.get("risk_level", "")
            j["vuln_status"] = v_raw.get("vuln_status", "")
            j["jfrog_latest_vuln_count"] = v_raw.get("jfrog_latest_vuln_count", 0)

        plat = int(_priority_num(j.get("platform_env_count")) if j else 0)
        apps = int(_priority_num(j.get("internal_app_count")) if j else 0)
        ic = int(_priority_num(j.get("internal_component_count")) if j else 0)
        lob = int(_priority_num(j.get("internal_lob_count")) if j else 0)
        dl = int(_priority_num(j.get("artifactory_downloads")) if j else 0)
        ver = int(_priority_num(j.get("artifactory_version_count")) if j else 0)
        raw = _priority_use_score(plat, apps, ic, lob, dl, ver)

        in_jfrog = key in jfrog_by if key else False
        on_cf = _on_conda_forge(ident)
        in_conda_ent = key in conda_ent_names if key else False
        inv = _priority_inv_from_identity(ident, in_jfrog, on_cf, in_conda_ent)
        cohort = inv["OpenTeams_Cohort"]

        work = _priority_work_label(ident, _explicit_inv_from_identity(ident), j or None)
        bucket, src, why = _priority_assign_lane(ident, key, j or None, by_url, by_name)
        records.append(
            {
                "core_python_package_name": name,
                "name": name,
                "ident": ident,
                "work": work,
                "cohort": cohort,
                "bucket": bucket,
                "src": src,
                "why": why,
                "raw": raw,
                "risk_level": str(j.get("risk_level") or "") if j else "",
                "vuln_status": str(j.get("vuln_status") or "") if j else "",
                "jfrog_latest_vuln_count": int(_priority_num(j.get("jfrog_latest_vuln_count")) if j else 0),
            }
        )

    if not records:
        return pd.DataFrame(columns=list(_INVENTORY_PRIORITY_COLUMNS))

    scores = _priority_percentile_1_100([r["raw"] for r in records])
    for r, s in zip(records, scores):
        r["score100"] = s

    remainder = [r for r in records if r["bucket"] is None]
    for r in remainder:
        if r["work"] == _WORK_CREATE:
            tier, src = "P8", "work-create-recipe"
            why = "leftover Create recipe: JFROG consumed, not on conda-forge"
        elif r["work"] == _WORK_ISSUE_CF:
            if r.get("cohort") == "CONDA_ONLY":
                tier, src = "P10", "work-file-issue-conda-only"
                why = "leftover File OpenTeams tracking issue [Conda-Forge Packaging] (CDO-ENT-CONDA)"
            else:
                tier, src = "P9", "work-file-issue-on-cf"
                why = "leftover File OpenTeams tracking issue [Conda-Forge Packaging]"
        else:
            tier, src = "P10", "work-already-tracked-remainder"
            why = "leftover Already tracked"
        r["bucket"] = tier
        r["src"] = src
        r["why"] = f"{why} (score {r['score100']})"

    def _sort_key(r: dict):
        return (
            _PRI_N[r["bucket"]],
            _WORK_RANK.get(r["work"], 9),
            -r["score100"],
            -r["raw"],
            -int(_priority_num(r.get("dl", 0))),
            -int(_priority_num(r.get("ver", 0))),
            r["name"],
        )

    # attach dl/ver for sort_key (parity with priority.py sort_key)
    for r in records:
        key = _priority_pep503(r["ident"].get("Core_Python_Package_Name"))
        j = jfrog_by.get(key or "")
        r["dl"] = int(_priority_num(j.get("artifactory_downloads")) if j else 0)
        r["ver"] = int(_priority_num(j.get("artifactory_version_count")) if j else 0)

    records.sort(key=_sort_key)
    for i, r in enumerate(records, start=1):
        r["rank"] = i

    out_rows: list[dict[str, Any]] = []
    for r in records:
        bucket = r["bucket"]
        out_rows.append(
            {
                "core_python_package_name": r["core_python_package_name"],
                "P": bucket,
                "Rank": r["rank"],
                "Score": r["score100"],
                "Work": r["work"],
                "Priority_Bucket_Description": _PRIORITY_DESC.get(bucket, ""),
                "Priority_Source": r["src"],
                "Priority_Reason": r["why"],
                "Proposed_Priority": bucket,
                "Packaging_Work": r["work"],
                "Priority_Rank": r["rank"],
                "Priority_Score": r["score100"],
                "risk_level": r["risk_level"],
                "vuln_status": r["vuln_status"],
                "jfrog_latest_vuln_count": r["jfrog_latest_vuln_count"],
            }
        )
    return pd.DataFrame(out_rows, columns=list(_INVENTORY_PRIORITY_COLUMNS))
