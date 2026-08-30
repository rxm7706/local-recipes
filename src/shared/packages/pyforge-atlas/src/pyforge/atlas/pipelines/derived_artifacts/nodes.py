"""``derived_artifacts`` pipeline nodes (Story B7, AC-3; Story 23.8).

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

PURE nodes: pandas + stdlib only; no inline IO; ``dagster``/``kedro_mcp`` never imported
(AD-1). Reuses the ported purl primitives from the ``universal_sbom`` nodes.
"""

from __future__ import annotations

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
