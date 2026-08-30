#!/usr/bin/env python3
"""Conda-forge packaging inventory operations runner.

Prompt sync contract:
- Replay prompt doc: docs/reference/conda-forge-packaging-inventory-operations_replay.md
- Any behavior/source/rule/metric/output change must update both this script and
  the replay prompt doc in the same commit.

Story 21.3 (--live-catalog): when set, the acquisition of exactly three
verification sets (cf_packages / pypi_index / parselmouth_pypi) is replaced by
direct pandas.read_parquet reads of the pyforge-atlas Kedro data plane's Tier 0
outputs instead of live HTTP fetches or local snapshot files. See
load_live_catalog() below. pandas/pyarrow are imported lazily inside that
function only -- the default (no --live-catalog) path stays stdlib-only.
"""

from __future__ import annotations

import argparse
import csv
import html as html_lib
import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from zipfile import ZipFile

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
PKG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
PRIORITY_RE = re.compile(r"\bP\s*([0-9]{1,2})\b", re.IGNORECASE)
OPEN_TEAMS_BRACKET_RE = re.compile(r"^\[Conda-Forge Packaging\]\s+(.+?)\s*$", re.IGNORECASE)
CLONE_TABS = {"10kOpen"}  # stale clone of CDO-ENT-JFROG — do not double-count
# Output snapshots copied into the workbook for viewing — never ingest as sources.
OUTPUT_TABS = {"verified-all-packages", "inventory-2026-08-12", "identity-2026-08-12"}

PACKAGE_COLUMNS = {
    "name",
    "package_name",
    "raw_names",
    "item",
    "pypi_name",
    "conda_forge_name",
    "import_name",
}
INVALID_PACKAGE_TOKENS = {
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


def pep503(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value.strip().lower()).strip("-")


def clean_pkg_token(raw: str) -> str:
    s = (raw or "").strip()
    s = re.sub(r"\[.*?\]", "", s)
    s = re.sub(r"#\d+\b", "", s)
    s = re.sub(r"\s*(>=|==|~=|<=|!=|>|<).*$", "", s)
    return s.strip().strip("\"'")


def norm_pkg(value: str) -> str:
    return pep503(clean_pkg_token(value))


def looks_like_pkg(value: str) -> bool:
    raw = (value or "").strip()
    if not raw or DATE_RE.match(raw) or re.fullmatch(r"\d+(\.0+)?", raw):
        return False
    v = norm_pkg(raw)
    if v in INVALID_PACKAGE_TOKENS:
        return False
    if len(v) < 2:
        return False
    return bool(PKG_RE.fullmatch(v))


def split_package_list(value: str) -> list[str]:
    parts = re.split(r"[,;\n/]", value)
    return [norm_pkg(x) for x in parts if x and x.strip()]


def parse_bool_hint(value: str) -> bool | None:
    v = value.strip().lower()
    if v in {"1", "true", "yes", "y"}:
        return True
    if v in {"0", "false", "no", "n"}:
        return False
    return None


def parse_priority(value: str) -> int | None:
    m = PRIORITY_RE.search(value or "")
    if not m:
        return None
    n = int(m.group(1))
    if 1 <= n <= 10:
        return n
    return None


def fetch_text(url: str, timeout: int) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "local-recipes-conda-forge-packaging-inventory-operations-metrics/2.0",
            "Accept": "text/plain, text/html, application/json;q=0.9, */*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return res.read().decode("utf-8", errors="replace")


def fetch_json(url: str, timeout: int) -> dict:
    return json.loads(fetch_text(url, timeout))


@dataclass
class PackageRecord:
    core_name: str
    input_names: set[str] = field(default_factory=set)
    tabs: set[str] = field(default_factory=set)
    sources: set[str] = field(default_factory=set)
    priorities: set[int] = field(default_factory=set)
    pypi_hints: set[bool] = field(default_factory=set)
    cf_hints: set[bool] = field(default_factory=set)


@dataclass
class OpenTeamsSummary:
    rows_used_a: int = 0
    rows_used_b: int = 0
    rows_ignored_c: int = 0
    unique_packages: set[str] = field(default_factory=set)


@dataclass
class LiveCatalogResult:
    """Result of load_live_catalog() -- the --live-catalog Story 21.3 loader."""

    cf_packages: set[str] = field(default_factory=set)
    pypi_index: set[str] = field(default_factory=set)
    parselmouth_pypi: set[str] = field(default_factory=set)
    warnings: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


class XlsxReader:
    def __init__(self, path: Path):
        self.zip = ZipFile(path)
        self.shared_strings = self._load_shared_strings()
        self.sheet_targets = self._load_sheet_targets()

    def close(self) -> None:
        self.zip.close()

    def _load_shared_strings(self) -> list[str]:
        if "xl/sharedStrings.xml" not in self.zip.namelist():
            return []
        root = ET.fromstring(self.zip.read("xl/sharedStrings.xml"))
        out: list[str] = []
        for si in root.findall(f"{NS}si"):
            out.append("".join((t.text or "") for t in si.iter(f"{NS}t")))
        return out

    def _load_sheet_targets(self) -> dict[str, str]:
        wb = ET.fromstring(self.zip.read("xl/workbook.xml"))
        rels = ET.fromstring(self.zip.read("xl/_rels/workbook.xml.rels"))
        id_to_target = {r.attrib["Id"]: r.attrib["Target"] for r in rels}
        sheets = wb.find(f"{NS}sheets")
        out: dict[str, str] = {}
        if sheets is None:
            return out
        for sh in sheets:
            name = sh.attrib.get("name", "")
            rid = sh.attrib.get(REL_NS, "")
            target = id_to_target.get(rid, "").lstrip("/")
            if target and not target.startswith("xl/"):
                target = f"xl/{target}"
            if name and target:
                out[name] = target
        return out

    def sheet_names(self) -> list[str]:
        return list(self.sheet_targets.keys())

    def iter_rows(self, sheet_name: str) -> Iterable[dict[str, str]]:
        target = self.sheet_targets.get(sheet_name)
        if not target:
            return
        root = ET.fromstring(self.zip.read(target))
        rows = root.findall(f".//{NS}sheetData/{NS}row")
        if not rows:
            return

        headers = self._decode_row(rows[0])
        col_to_header = {col: (v or "").strip() for col, v in headers.items() if (v or "").strip()}
        for row in rows[1:]:
            decoded = self._decode_row(row)
            out: dict[str, str] = {}
            for col, header in col_to_header.items():
                out[header] = (decoded.get(col) or "").strip()
            yield out

    def _decode_row(self, row: ET.Element) -> dict[str, str]:
        values: dict[str, str] = {}
        for cell in row.findall(f"{NS}c"):
            ref = cell.attrib.get("r", "")
            col = "".join(ch for ch in ref if ch.isalpha())
            if not col:
                continue
            ctype = cell.attrib.get("t")
            v = cell.find(f"{NS}v")
            isv = cell.find(f"{NS}is")
            text = ""
            if ctype == "s" and v is not None and v.text:
                idx = int(v.text)
                if idx < len(self.shared_strings):
                    text = self.shared_strings[idx]
            elif ctype == "inlineStr" and isv is not None:
                t = isv.find(f"{NS}t")
                text = (t.text or "") if t is not None else ""
            elif v is not None and v.text:
                text = v.text
            values[col] = text
        return values


def parse_openteams_title(title: str) -> tuple[str, list[str]]:
    t = (title or "").strip()
    if not t:
        return "c", []
    if "|" in t:
        rhs = t.split("|", 1)[1]
        pkgs = [x for x in split_package_list(rhs) if looks_like_pkg(x)]
        return ("a", pkgs) if pkgs else ("c", [])
    m = OPEN_TEAMS_BRACKET_RE.match(t)
    if m:
        pkgs = [x for x in split_package_list(m.group(1)) if looks_like_pkg(x)]
        return ("b", pkgs) if pkgs else ("c", [])
    return "c", []


def parse_sheet_sources(xlsx: XlsxReader) -> tuple[dict[str, PackageRecord], dict[str, set[str]], dict[str, bool], set[str]]:
    records: dict[str, PackageRecord] = {}
    tab_packages: dict[str, set[str]] = defaultdict(set)
    analysis_cf_availability: dict[str, bool] = {}
    analysis_not_on_cf: set[str] = set()

    for sheet in xlsx.sheet_names():
        if sheet in OUTPUT_TABS:
            continue
        source_tag = f"tab:{sheet}"
        skip_source = sheet in CLONE_TABS
        derive_only = sheet in {"10kOpen", "10kClosed"}
        for row in xlsx.iter_rows(sheet):
            row_priority = None
            pypi_hint = None
            cf_hint = None
            if not derive_only:
                row_priority = parse_priority(row.get("Priority_Bucket", "") or row.get("Priority", ""))
                for k in ("Available_on_PyPI", "seen_pypi_source", "PyPI_Verified"):
                    if k in row:
                        pypi_hint = parse_bool_hint(row[k])
                        if pypi_hint is not None:
                            break
                for k in ("Available_on_Conda_Forge", "conda_forge_available", "CondaForge_Verified"):
                    if k in row:
                        cf_hint = parse_bool_hint(row[k])
                        if cf_hint is not None:
                            break
                status = row.get("Packaging_Candidate_Status", "")
                if status.lower().strip() == "already packaged":
                    pypi_hint = True if pypi_hint is None else pypi_hint
                    cf_hint = True if cf_hint is None else cf_hint

            row_packages: set[str] = set()
            if "Title" in row:
                _, title_pkgs = parse_openteams_title(row.get("Title", ""))
                row_packages.update(title_pkgs)

            for key, val in row.items():
                k = key.strip().lower()
                if k not in PACKAGE_COLUMNS:
                    continue
                if not val:
                    continue
                candidates = split_package_list(val) if k in {"raw_names"} or "," in val else [norm_pkg(val)]
                for c in candidates:
                    if looks_like_pkg(c):
                        row_packages.add(c)

            for pkg in row_packages:
                tab_packages[sheet].add(pkg)
                if skip_source:
                    continue
                rec = records.setdefault(pkg, PackageRecord(core_name=pkg))
                raw_name = (
                    row.get("Package_Name")
                    or row.get("name")
                    or row.get("raw_names")
                    or row.get("Item")
                    or row.get("Title")
                    or pkg
                )
                rec.input_names.add(raw_name.strip())
                rec.tabs.add(sheet)
                rec.sources.add(source_tag)
                if row_priority is not None:
                    rec.priorities.add(row_priority)
                if pypi_hint is not None:
                    rec.pypi_hints.add(pypi_hint)
                if cf_hint is not None:
                    rec.cf_hints.add(cf_hint)

            if sheet.startswith("Analysis_Dataset-") or sheet == "CDO-ENT-JFROG":
                pkg = norm_pkg(row.get("name", ""))
                if looks_like_pkg(pkg):
                    hint = parse_bool_hint(row.get("conda_forge_available", ""))
                    if hint is not None:
                        analysis_cf_availability[pkg] = hint
                        if not hint:
                            analysis_not_on_cf.add(pkg)

    return records, tab_packages, analysis_cf_availability, analysis_not_on_cf


def parse_openteams_tsv(path: Path) -> tuple[list[dict[str, str]], OpenTeamsSummary]:
    rows: list[dict[str, str]] = []
    summary = OpenTeamsSummary()
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for raw in reader:
            row = {k: (v or "").strip() for k, v in raw.items()}
            rows.append(row)
            rule, pkgs = parse_openteams_title(row.get("Title", ""))
            if rule == "a":
                summary.rows_used_a += 1
                summary.unique_packages.update(pkgs)
            elif rule == "b":
                summary.rows_used_b += 1
                summary.unique_packages.update(pkgs)
            else:
                summary.rows_ignored_c += 1
    return rows, summary


def integrate_openteams_rows(records: dict[str, PackageRecord], rows: list[dict[str, str]]) -> None:
    source_tag = "tsv:openteams"
    for row in rows:
        rule, pkgs = parse_openteams_title(row.get("Title", ""))
        if rule == "c":
            continue
        pr = parse_priority(row.get("Priority", ""))
        for pkg in pkgs:
            rec = records.setdefault(pkg, PackageRecord(core_name=pkg))
            rec.input_names.add(row.get("Title", pkg))
            rec.sources.add(source_tag)
            if pr is not None:
                rec.priorities.add(pr)


def parse_feedstocks_from_about(timeout: int) -> tuple[set[str], set[str]]:
    text = fetch_text("https://raw.githubusercontent.com/rxm7706/about/main/README.md", timeout)
    maint, co = set(), set()
    current: set[str] | None = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("List Of FeedStocks - As Maintainer"):
            current = maint
            continue
        if line.startswith("List Of FeedStocks - As Co-Maintainer"):
            current = co
            continue
        if current is None:
            continue
        m = re.match(r"^\d+\.\s+conda-forge/([a-zA-Z0-9._-]+)-feedstock\s*$", line)
        if m:
            current.add(norm_pkg(m.group(1)))
            continue
        if line and not line[0].isdigit():
            current = None
    return maint, co


GIT_HOST_RE = re.compile(
    r"https?://(?:www\.)?(github\.com|gitlab\.com|bitbucket\.org|codeberg\.org|"
    r"opendev\.org|gitee\.com|pagure\.io|sourceforge\.net|launchpad\.net|"
    r"gitlab\.freedesktop\.org|gitlab\.gnome\.org|foss\.heptapod\.net|"
    r"code\.qt\.io|git\.sr\.ht)/",
    re.I,
)
GH_ARCHIVE_RE = re.compile(r"https?://(?:www\.)?github\.com/([^/]+)/([^/]+)/", re.I)
TENK_TABS = ("10kClosed", "10kOpen")


def _as_url(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        for item in value:
            s = _as_url(item)
            if s:
                return s
        return ""
    return str(value).strip()


def git_url_from_channeldata_meta(meta: dict) -> str:
    for key in ("dev_url", "home", "source_url"):
        u = _as_url(meta.get(key))
        if not u:
            continue
        m = GH_ARCHIVE_RE.match(u)
        if m:
            owner, repo = m.group(1), m.group(2).removesuffix(".git")
            if owner.lower() == "conda-forge" and repo.endswith("-feedstock"):
                continue
            return f"https://github.com/{owner}/{repo}"
        if GIT_HOST_RE.search(u):
            return u.rstrip("/")
    return ""


def load_channeldata_packages(path: Path | None) -> dict[str, dict]:
    if path is None or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for k, meta in (data.get("packages") or {}).items():
        if not k:
            continue
        out.setdefault(norm_pkg(k), meta or {})
    return out


def load_channeldata_names(path: Path | None) -> set[str]:
    return set(load_channeldata_packages(path))


def load_pypi_simple_names(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    text = path.read_text(encoding="utf-8", errors="replace")
    out: set[str] = set()
    for m in re.finditer(r"<a\b[^>]*>([^<]+)</a>", text, re.I):
        n = norm_pkg(html_lib.unescape(m.group(1)))
        if n:
            out.add(n)
    return out


def load_parselmouth_pypi_names(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return set()
    out: set[str] = set()
    for pypi_val in data.values():
        if pypi_val:
            n = norm_pkg(str(pypi_val))
            if n:
                out.add(n)
    return out


_LIVE_CATALOG_FLOORS: dict[str, tuple[str, str, int | None]] = {
    # key -> (relative Parquet path under PYFORGE_ATLAS_DATA_ROOT, column, floor)
    "core_packages_enumerated": (
        "intermediate/core_packages_enumerated/core_packages_enumerated.parquet",
        "conda_name",
        30_000,
    ),
    "pypi_universe": (
        "intermediate/pypi_universe/pypi_universe.parquet",
        "pypi_name",
        1,
    ),
    # No documented scale floor (catalog-sources.md) -- existence/readability only.
    "pypi_conda_mapping": (
        "primary/pypi_conda_mapping/pypi_conda_mapping.parquet",
        "pypi_name",
        None,
    ),
}


def load_live_catalog(root: Path) -> LiveCatalogResult:
    """Read the three --live-catalog verification sets directly from the
    pyforge-atlas Kedro data plane's already-populated Tier 0 Parquet outputs
    under ``root`` (a ``PYFORGE_ATLAS_DATA_ROOT``), instead of live HTTP
    fetches or --cf-channeldata/--pypi-simple/--parselmouth snapshot files
    (Story 21.3, verification-matrix.md).

    Lazily imports pandas -- the default (no --live-catalog) path stays
    stdlib-only. Per dataset: a missing file, an unreadable/corrupt Parquet
    file, or (for the two floored datasets) a sub-floor distinct-value count
    degrades ONLY that one set to an empty set, records the dataset key in
    ``.failed``, and appends a one-line message to ``.warnings`` -- never
    raises.
    """
    import pandas as pd

    result = LiveCatalogResult()

    for key, (rel_path, column, floor) in _LIVE_CATALOG_FLOORS.items():
        path = root / rel_path
        try:
            # path.exists() itself can raise (e.g. PermissionError on a parent
            # dir) -- keep it inside the same try/except as the Parquet read
            # so any such failure also degrades this dataset instead of
            # propagating uncaught, per this loader's "never raises" contract.
            if not path.exists():
                result.failed.append(key)
                result.warnings.append(f"--live-catalog: {key} missing at {path}")
                continue
            df = pd.read_parquet(path, columns=[column])
            non_null = df[column].dropna()
            distinct = non_null.nunique()
        except Exception as exc:
            result.failed.append(key)
            result.warnings.append(f"--live-catalog: {key} unreadable at {path}: {exc}")
            continue
        if floor is not None and distinct < floor:
            result.failed.append(key)
            result.warnings.append(
                f"--live-catalog: {key} below floor ({distinct:,} distinct "
                f"{column} < {floor:,} required)"
            )
            continue
        values = {norm_pkg(str(v)) for v in non_null}
        values.discard("")
        if key == "core_packages_enumerated":
            result.cf_packages = values
        elif key == "pypi_universe":
            result.pypi_index = values
        else:
            result.parselmouth_pypi = values

    return result


def parse_channeldata_url(url: str, timeout: int) -> set[str]:
    data = fetch_json(url, timeout)
    pkgs = data.get("packages") or {}
    return {norm_pkg(k) for k in pkgs if k and looks_like_pkg(k)}


def openteams_summary_from_xlsx(xlsx: XlsxReader) -> OpenTeamsSummary:
    summary = OpenTeamsSummary()
    if "OpenTeams" not in xlsx.sheet_names():
        return summary
    for row in xlsx.iter_rows("OpenTeams"):
        rule, pkgs = parse_openteams_title(row.get("Title", ""))
        if rule == "a":
            summary.rows_used_a += 1
            summary.unique_packages.update(pkgs)
        elif rule == "b":
            summary.rows_used_b += 1
            summary.unique_packages.update(pkgs)
        else:
            summary.rows_ignored_c += 1
    return summary


def parse_aoss_page(url: str, timeout: int) -> set[str]:
    text = fetch_text(url, timeout)
    out: set[str] = set()
    # Avoid broad HTML token scraping noise: keep explicit python-* / pypi-like tokens.
    for token in re.findall(r"\b(?:python-[A-Za-z0-9._-]+|[A-Za-z0-9][A-Za-z0-9._-]{1,})\b", text):
        n = norm_pkg(token)
        if looks_like_pkg(n) and not n.startswith(("devsite-", "goog-", "gstatic", "google-cloud-documentation")):
            out.add(n)
    return out


def parse_basilisk_page(timeout: int) -> set[str]:
    text = fetch_text("https://basilisk.prefix.dev/?view=all", timeout)
    out: set[str] = set()
    # Only accept package-like names from explicit conda-forge package-url-like fragments.
    for token in re.findall(r"conda-forge/([A-Za-z0-9][A-Za-z0-9._-]{1,})", text):
        n = norm_pkg(token)
        if looks_like_pkg(n):
            out.add(n)
    return out


def parse_sheet_pkg_set(xlsx: XlsxReader, sheet: str, col: str) -> set[str]:
    out: set[str] = set()
    for row in xlsx.iter_rows(sheet):
        v = norm_pkg(row.get(col, ""))
        if looks_like_pkg(v):
            out.add(v)
    return out


def parse_cdo_ent_conda_roles(xlsx: XlsxReader) -> tuple[set[str], set[str]]:
    maint, co = set(), set()
    if "CDO-ENT-CONDA" not in xlsx.sheet_names():
        return maint, co
    for row in xlsx.iter_rows("CDO-ENT-CONDA"):
        pkg = norm_pkg(row.get("Package_Name") or row.get("name") or "")
        if not looks_like_pkg(pkg):
            continue
        role = (row.get("Role") or "").strip().lower().replace("_", "-")
        if role == "maintainer":
            maint.add(pkg)
        elif role == "co-maintainer":
            co.add(pkg)
    return maint, co


def load_curated_groups(path: Path) -> dict[str, set[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    groups = data.get("groups", [])
    out: dict[str, set[str]] = {}
    for entry in groups:
        name = str(entry.get("name", "")).strip()
        if not name:
            continue
        pkgs: set[str] = set()
        for raw in entry.get("packages", []):
            p = norm_pkg(str(raw))
            if looks_like_pkg(p):
                pkgs.add(p)
        out[name] = pkgs
    return out


def add_source_set(records: dict[str, PackageRecord], source_key: str, packages: set[str]) -> None:
    for pkg in packages:
        rec = records.setdefault(pkg, PackageRecord(core_name=pkg))
        rec.input_names.add(pkg)
        rec.sources.add(source_key)


def pypi_exists(pkg: str, timeout: int, cache: dict[str, bool]) -> bool:
    if pkg in cache:
        return cache[pkg]
    url = f"https://pypi.org/pypi/{pkg}/json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "local-recipes-conda-forge-packaging-inventory-operations-metrics/2.0"})
        with urllib.request.urlopen(req, timeout=timeout):
            cache[pkg] = True
            return True
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            cache[pkg] = False
            return False
        raise


def primary_source(sources: set[str]) -> str:
    def score(s: str) -> tuple[int, str]:
        if s == "about:maintainer":
            return (1, s)
        if s == "about:co-maintainer":
            return (2, s)
        if s.startswith("curated:"):
            return (3, s)
        if s.startswith("tsv:"):
            return (4, s)
        if s.startswith("tab:"):
            return (5, s)
        if s.startswith("external:"):
            return (6, s)
        return (9, s)

    return sorted(sources, key=score)[0] if sources else "N/A"


def priority_bucket(rec: PackageRecord) -> str:
    if rec.priorities:
        return f"P{min(rec.priorities)}"
    if any(
        s.startswith("curated:") or s.startswith("about:") or s == "tab:CDO-ENT-CONDA"
        for s in rec.sources
    ):
        return "P4"
    return "P9"


def packaging_status(pypi_ok: bool, cf_ok: bool, pbucket: str) -> str:
    pnum = int(pbucket[1:]) if pbucket.startswith("P") and pbucket[1:].isdigit() else 9
    if pypi_ok and cf_ok:
        return "Already Packaged"
    if pypi_ok and not cf_ok:
        return "High Priority Candidate" if pnum <= 8 else "Low Priority Candidate"
    if not pypi_ok and cf_ok:
        return "Conda-Forge Only"
    return "Not on PyPI"


def role_for_package(pkg: str, maint: set[str], co: set[str]) -> str:
    if pkg in maint:
        return "Maintainer"
    if pkg in co:
        return "Co-Maintainer"
    return "N/A"


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    cols = [
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
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def write_aoss_free_queue(
    path: Path,
    aoss_free_names: set[str],
    universe_names: set[str],
    timestamp: str,
) -> list[str]:
    """Dated AOSS-Free extra Mason queue.

    ``aoss_free_names`` (already filtered to on-PyPI, not-on-conda-forge by
    the caller) minus ``universe_names`` (the OpenTeams universe: CDO-ENT-JFROG
    union CDO-ENT-CONDA). Never merges into or expands that universe -- per
    the Dream, this is a separate, Mason-facing supplementary artifact: "Google
    AOSS Free names ... are an extra Mason queue. They do not expand the
    OpenTeams universe."
    """
    queue = sorted(aoss_free_names - universe_names)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=["Package_Name", "Reason", "Verification_Timestamp_UTC"]
        )
        w.writeheader()
        for pkg in queue:
            w.writerow(
                {
                    "Package_Name": pkg,
                    "Reason": "On PyPI, not on conda-forge, not in CDO consumption (GAOSS-Free)",
                    "Verification_Timestamp_UTC": timestamp,
                }
            )
    return queue


def write_markdown(
    path: Path,
    total: int,
    status_counts: Counter[str],
    tab_packages: dict[str, set[str]],
    source_sets: dict[str, set[str]],
    included: set[str],
    source_attr_counts: Counter[str],
    openteams: OpenTeamsSummary,
    net_new_counts: Counter[str],
) -> None:
    lines: list[str] = []
    lines.append("# Consolidated Verified Package Inventory Report")
    lines.append("")
    lines.append(f"- Total final unique package count: **{total:,}**")
    lines.append("")
    lines.append("## Packaging Candidate Status Breakdown")
    lines.append("")
    for k in ("Already Packaged", "High Priority Candidate", "Low Priority Candidate", "Conda-Forge Only", "Not on PyPI"):
        lines.append(f"- {k}: **{status_counts.get(k, 0):,}**")
    lines.append("")
    lines.append("## Per-Worksheet Tab Package Inclusion & Verification Matrix")
    lines.append("")
    lines.append("| Worksheet Tab | Raw Supplied Packages | Included Packages | Inclusion % |")
    lines.append("|---|---:|---:|---:|")
    for tab in sorted(tab_packages):
        raw = tab_packages[tab]
        inc = raw & included
        pct = (len(inc) / len(raw) * 100.0) if raw else 0.0
        lines.append(f"| {tab} | {len(raw):,} | {len(inc):,} | {pct:.1f}% |")
    lines.append("")
    lines.append("## Per-Source Package Inclusion & Verification Matrix")
    lines.append("")
    lines.append("| Source | Raw Supplied Packages | Included Packages | Inclusion % |")
    lines.append("|---|---:|---:|---:|")
    for src in sorted(source_sets):
        raw = source_sets[src]
        inc = raw & included
        pct = (len(inc) / len(raw) * 100.0) if raw else 0.0
        lines.append(f"| {src} | {len(raw):,} | {len(inc):,} | {pct:.1f}% |")
    lines.append("")
    lines.append("## Primary Repository Source Attribution in Final Inventory")
    lines.append("")
    for src, cnt in source_attr_counts.most_common():
        lines.append(f"- {src}: **{cnt:,}**")
    lines.append("")
    lines.append("## OpenTeams-Style Portion Parsing Summary")
    lines.append("")
    lines.append(f"- rows used by rule (a): **{openteams.rows_used_a:,}**")
    lines.append(f"- rows used by rule (b): **{openteams.rows_used_b:,}**")
    lines.append(f"- rows ignored by rule (c): **{openteams.rows_ignored_c:,}**")
    lines.append(f"- unique packages extracted from that portion: **{len(openteams.unique_packages):,}**")
    lines.append("")
    lines.append("## Net-New Packages Breakdown")
    lines.append("")
    lines.append("- Net-new is defined as packages not verified on conda-forge.")
    for k in ("High Priority Candidate", "Low Priority Candidate", "Conda-Forge Only", "Not on PyPI"):
        lines.append(f"- {k}: **{net_new_counts.get(k, 0):,}**")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_revised_prompt(path: Path, args: argparse.Namespace) -> None:
    # Story 21.3: this is a hardcoded f-string template over a fixed, explicit
    # list of args.* fields -- it does not dynamically echo every parsed
    # argument, so --live-catalog/--live-catalog-only must be appended
    # explicitly or a --live-catalog run's regenerated prompt silently omits
    # the flags actually used.
    extra_lines = ""
    if args.live_catalog is not None:
        extra_lines += f' \\\n  --live-catalog "{args.live_catalog}"'
    if args.live_catalog_only:
        extra_lines += " \\\n  --live-catalog-only"
    text = f"""# docs/reference/conda-forge-packaging-inventory-operations_prompt.md

Run consolidated verified package inventory generation from local exports.

```bash
python3 scripts/conda-forge-packaging-inventory-operations_metrics.py \\
  --analysis-xlsx "{args.analysis_xlsx}" \\
  --openteams-tsv "{args.openteams_tsv}" \\
  --curated-config "{args.curated_config}" \\
  --output-csv "{args.output_csv}" \\
  --output-md "{args.output_md}" \\
  --output-revised-prompt "{args.output_revised_prompt}" \\
  --verify-mode {args.verify_mode} \\
  --strict-max-live-checks {args.strict_max_live_checks}{extra_lines}
```
"""
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="conda-forge-packaging-inventory-operations-metrics",
        description=(
            "Build consolidated verified package inventory + metrics output. "
            "--live-catalog reads PyPI/conda-forge verification from the "
            "pyforge-atlas Kedro Parquet data plane instead of live HTTP "
            "fetches or --cf-channeldata/--pypi-simple/--parselmouth snapshot "
            "files."
        ),
    )
    parser.add_argument("--analysis-xlsx", type=Path, required=True)
    parser.add_argument("--openteams-tsv", type=Path, default=None)
    parser.add_argument("--curated-config", type=Path, default=Path("conf/conda-forge-packaging-inventory-operations_curated_groups.json"))
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
        help="Do not overwrite docs/reference/conda-forge-packaging-inventory-operations_prompt.md (use when regenerating inventory only).",
    )
    parser.add_argument("--pypi-simple", type=Path, default=Path("/tmp/ext-src/pypi-simple.html"))
    parser.add_argument("--cf-channeldata", type=Path, default=Path("/tmp/ext-src/cf-channeldata.json"))
    parser.add_argument("--main-channeldata", type=Path, default=Path("/tmp/ext-src/main-channeldata.json"))
    parser.add_argument("--parselmouth", type=Path, default=Path("/tmp/ext-src/compressed_mapping.json"))
    parser.add_argument("--verify-mode", choices=("fast", "strict"), default="fast")
    parser.add_argument("--max-fast-live-checks", type=int, default=400)
    parser.add_argument("--strict-max-live-checks", type=int, default=5000)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--strict-fetch", action="store_true")
    parser.add_argument(
        "--use-live-html-sources",
        action="store_true",
        help="Use live HTML scraping for AOSS/Basilisk/Anaconda-release pages (default uses workbook snapshots).",
    )
    parser.add_argument("--repodata-subdirs", default="noarch,linux-64,osx-64,osx-arm64,win-64")
    parser.add_argument(
        "--live-catalog",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Read conda-forge package names, PyPI package names, and the "
            "Parselmouth conda<->PyPI name mapping from the pyforge-atlas "
            "Kedro Parquet data plane under PATH (a PYFORGE_ATLAS_DATA_ROOT) "
            "instead of live HTTP fetches or --pypi-simple/--parselmouth "
            "snapshot files (fully unused when this is set). --cf-channeldata "
            "stays accepted and is NOT replaced by this flag -- it is still "
            "read independently for has_src/the 10k-tab drop filter."
        ),
    )
    parser.add_argument(
        "--live-catalog-only",
        action="store_true",
        help=(
            "Require --live-catalog and all three of its required datasets "
            "present, readable, and above their scale floors (no floor for "
            "the Parselmouth mapping); exit 2 before writing any output "
            "otherwise."
        ),
    )
    args = parser.parse_args()

    if args.live_catalog_only and args.live_catalog is None:
        print("--live-catalog-only requires --live-catalog", file=sys.stderr)
        return 2

    if not args.analysis_xlsx.exists():
        print(f"missing analysis workbook: {args.analysis_xlsx}", file=sys.stderr)
        return 2
    if args.openteams_tsv is not None and not args.openteams_tsv.exists():
        print(f"missing OpenTeams TSV: {args.openteams_tsv}", file=sys.stderr)
        return 2
    if not args.curated_config.exists():
        print(f"missing curated config: {args.curated_config}", file=sys.stderr)
        return 2

    warnings: list[str] = []
    live_catalog: LiveCatalogResult | None = None
    if args.live_catalog is not None:
        live_catalog = load_live_catalog(args.live_catalog)
        if args.live_catalog_only and live_catalog.failed:
            for w in live_catalog.warnings:
                print(w, file=sys.stderr)
            return 2
        warnings.extend(live_catalog.warnings)

    subdirs = [s.strip() for s in args.repodata_subdirs.split(",") if s.strip()]
    xlsx = XlsxReader(args.analysis_xlsx)
    try:
        records, tab_packages, analysis_cf_availability, analysis_not_on_cf = parse_sheet_sources(xlsx)
        if args.openteams_tsv is not None:
            tsv_rows, openteams_summary = parse_openteams_tsv(args.openteams_tsv)
            integrate_openteams_rows(records, tsv_rows)
        else:
            openteams_summary = openteams_summary_from_xlsx(xlsx)

        source_sets: dict[str, set[str]] = {}

        def try_source(
            key: str,
            live_fn,
            fallback_fn,
        ) -> set[str]:
            try:
                s = live_fn()
                if not s:
                    raise RuntimeError("empty live set")
            except Exception as exc:
                if args.strict_fetch:
                    raise
                warnings.append(f"{key} live fetch failed: {exc}")
                s = fallback_fn()
            source_sets[key] = s
            return s

        if args.live_catalog is not None:
            cf_packages = live_catalog.cf_packages
            source_sets["external:conda-forge-channel"] = cf_packages
        else:
            cf_packages = try_source(
                "external:conda-forge-channel",
                lambda: load_channeldata_names(args.cf_channeldata)
                or parse_channeldata_url("https://conda.anaconda.org/conda-forge/channeldata.json", args.timeout),
                lambda: parse_sheet_pkg_set(xlsx, "Conda-Forge", "Package_Name"),
            )
        anaconda_main = try_source(
            "external:anaconda-main-channel",
            lambda: load_channeldata_names(args.main_channeldata)
            or parse_channeldata_url("https://repo.anaconda.com/pkgs/main/channeldata.json", args.timeout),
            lambda: parse_sheet_pkg_set(xlsx, "Anaconda-Main", "Package_Name"),
        )
        if args.use_live_html_sources:
            anaconda_dist = try_source(
                "external:anaconda-2026x",
                lambda: parse_aoss_page("https://www.anaconda.com/docs/getting-started/anaconda/release/2026.x", args.timeout),
                lambda: parse_sheet_pkg_set(xlsx, "Anaaconda-Dist", "Package_Name"),
            )
            aoss_free = try_source(
                "external:aoss-free",
                lambda: parse_aoss_page("https://docs.cloud.google.com/assured-open-source-software/docs/supported-packages#python", args.timeout),
                lambda: parse_sheet_pkg_set(xlsx, "GAOSS-Free", "Package_Name"),
            )
            aoss_premium = try_source(
                "external:aoss-premium",
                lambda: parse_aoss_page("https://web.archive.org/web/20260419090548/https://docs.cloud.google.com/security-command-center/docs/aoss-supported-packages-premium#python", args.timeout),
                lambda: parse_sheet_pkg_set(xlsx, "GAOSS-Premium", "Package_Name"),
            )
            basilisk = try_source(
                "external:basilisk",
                lambda: parse_basilisk_page(args.timeout),
                lambda: parse_sheet_pkg_set(xlsx, "Basilisk", "Package_Name"),
            )
        else:
            anaconda_dist = parse_sheet_pkg_set(xlsx, "Anaaconda-Dist", "Package_Name")
            aoss_free = parse_sheet_pkg_set(xlsx, "GAOSS-Free", "Package_Name")
            aoss_premium = parse_sheet_pkg_set(xlsx, "GAOSS-Premium", "Package_Name")
            basilisk = parse_sheet_pkg_set(xlsx, "Basilisk", "Package_Name")
            source_sets["external:anaconda-2026x"] = anaconda_dist
            source_sets["external:aoss-free"] = aoss_free
            source_sets["external:aoss-premium"] = aoss_premium
            source_sets["external:basilisk"] = basilisk
        maint = set()
        co = set()
        try:
            maint, co = parse_feedstocks_from_about(args.timeout)
        except Exception as exc:
            if args.strict_fetch:
                raise
            warnings.append(f"external:about-readme live fetch failed: {exc}")
            maint, co = parse_cdo_ent_conda_roles(xlsx)
        source_sets["about:maintainer"] = maint
        source_sets["about:co-maintainer"] = co

        curated = load_curated_groups(args.curated_config)
        for group_name, packages in curated.items():
            source_sets[f"curated:{group_name}"] = packages

        for key, pkgs in source_sets.items():
            add_source_set(records, key, pkgs)

        if args.live_catalog is not None:
            parselmouth_pypi = live_catalog.parselmouth_pypi
            pypi_index = live_catalog.pypi_index
        else:
            parselmouth_pypi = load_parselmouth_pypi_names(args.parselmouth)
            pypi_index = load_pypi_simple_names(args.pypi_simple)
            if not pypi_index:
                warnings.append("pypi simple index missing; falling back to live JSON for unresolved names")
        cf_or_pm = cf_packages | parselmouth_pypi

        timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        pypi_cache: dict[str, bool] = {}
        pypi_verified: dict[str, bool] = {}
        strict_checked = 0
        strict_skipped = 0
        for pkg, rec in records.items():
            if pypi_index:
                pypi_verified[pkg] = pkg in pypi_index
                continue
            if args.verify_mode == "strict":
                if strict_checked < args.strict_max_live_checks:
                    try:
                        pypi_verified[pkg] = pypi_exists(pkg, args.timeout, pypi_cache)
                    except Exception:
                        pypi_verified[pkg] = any(rec.pypi_hints) if rec.pypi_hints else False
                    strict_checked += 1
                else:
                    pypi_verified[pkg] = any(rec.pypi_hints) if rec.pypi_hints else False
                    strict_skipped += 1
                continue
            if rec.pypi_hints:
                pypi_verified[pkg] = any(rec.pypi_hints)
            else:
                pypi_verified[pkg] = False

        rows: list[dict[str, str]] = []
        status_counts: Counter[str] = Counter()
        source_attr_counts: Counter[str] = Counter()
        net_new_counts: Counter[str] = Counter()
        tenk_names = set()
        for tab in TENK_TABS:
            tenk_names |= tab_packages.get(tab, set())
        must_keep = tab_packages.get("CDO-ENT-JFROG", set()) | tab_packages.get("CDO-ENT-CONDA", set())
        aoss_free_candidates = {
            pkg
            for pkg in aoss_free
            if pypi_verified.get(pkg, False) and pkg not in cf_or_pm
        }
        aoss_free_queue_path = args.output_csv.parent / f"aoss-free-queue-{timestamp[:10]}.csv"
        aoss_free_queue = write_aoss_free_queue(
            aoss_free_queue_path, aoss_free_candidates, must_keep, timestamp
        )
        cf_meta = load_channeldata_packages(args.cf_channeldata)
        dropped_tenk = 0
        keep: list[str] = []
        for pkg in sorted(records):
            pypi_ok = bool(pypi_verified.get(pkg, False))
            cf_ok = pkg in cf_or_pm
            has_src = bool(cf_ok and git_url_from_channeldata_meta(cf_meta.get(pkg) or {}))
            if pkg in tenk_names and pkg not in must_keep and not pypi_ok and not has_src:
                dropped_tenk += 1
                continue
            keep.append(pkg)

        included = set(keep)
        not_on_cf_count = 0
        for pkg in keep:
            rec = records[pkg]
            pypi_ok = bool(pypi_verified.get(pkg, False))
            cf_ok = pkg in cf_or_pm
            if not cf_ok:
                not_on_cf_count += 1
            pbucket = priority_bucket(rec)
            status = packaging_status(pypi_ok, cf_ok, pbucket)

            src = primary_source(rec.sources)
            source_attr_counts[src] += 1
            status_counts[status] += 1
            if not cf_ok and status in {
                "High Priority Candidate",
                "Low Priority Candidate",
                "Not on PyPI",
            }:
                net_new_counts[status] += 1

            first_input = sorted(rec.input_names)[0] if rec.input_names else pkg
            rows.append(
                {
                    "Repository_Source": src,
                    "Role": role_for_package(pkg, maint, co),
                    "Package_Input_Name": first_input,
                    "Core_Python_Package_Name": pkg,
                    "PyPI_Verified": "Yes" if pypi_ok else "No",
                    "CondaForge_Verified": "Yes" if cf_ok else "No",
                    "Priority_Bucket": pbucket,
                    "Packaging_Candidate_Status": status,
                    "PyPI_PURL": f"pkg:pypi/{pkg}" if pypi_ok else "N/A",
                    "PyPI_Package_URL": f"https://pypi.org/project/{pkg}/" if pypi_ok else "N/A",
                    "Conda-forge_PURL": f"pkg:conda/{pkg}?channel=conda-forge" if cf_ok else "N/A",
                    "Conda-Forge_Package_URL": f"https://anaconda.org/conda-forge/{pkg}/" if cf_ok else "N/A",
                    "Conda-Forge_FeedStock_URL": f"https://github.com/conda-forge/{pkg}-feedstock" if cf_ok else "N/A",
                    "Verification_Timestamp_UTC": timestamp,
                }
            )

        write_csv(args.output_csv, rows)
        write_markdown(
            args.output_md,
            total=len(rows),
            status_counts=status_counts,
            tab_packages=tab_packages,
            source_sets=source_sets,
            included=included,
            source_attr_counts=source_attr_counts,
            openteams=openteams_summary,
            net_new_counts=net_new_counts,
        )
        if not args.skip_revised_prompt:
            write_revised_prompt(args.output_revised_prompt, args)

        print("=== MASTER PROMPT V3.0 EXECUTION SUMMARY METRICS ===")
        print()
        print(f"Total final unique packages processed: {len(rows):,}")
        print(f"Count not on conda-forge: {not_on_cf_count:,}")
        print(f"Count from analysis-dataset portion not on conda-forge: {len(analysis_not_on_cf):,}")
        print("Count parsed from OpenTeams-style portion:")
        print(f"  - rows used by rule (a): {openteams_summary.rows_used_a:,}")
        print(f"  - rows used by rule (b): {openteams_summary.rows_used_b:,}")
        print(f"  - rows ignored by rule (c): {openteams_summary.rows_ignored_c:,}")
        print(f"  - unique packages extracted from that portion: {len(openteams_summary.unique_packages):,}")
        print()
        print(f"Dropped 10kClosed/10kOpen with no PyPI and no derived source repo: {dropped_tenk:,}")
        print(f"Wrote CSV: {args.output_csv}")
        print(f"Wrote Markdown report: {args.output_md}")
        print(
            f"Wrote AOSS-Free queue: {aoss_free_queue_path} "
            f"({len(aoss_free_queue):,} rows)"
        )
        if not args.skip_revised_prompt:
            print(f"Wrote revised prompt: {args.output_revised_prompt}")
        if warnings:
            print("\nWarnings (fallbacks used):")
            for w in warnings:
                print(f"  - {w}")
        if args.verify_mode == "strict" and strict_skipped:
            print(
                f"\nStrict mode note: skipped live PyPI checks for {strict_skipped:,} package(s) "
                f"after reaching --strict-max-live-checks={args.strict_max_live_checks:,}."
            )
        return 0
    finally:
        xlsx.close()


if __name__ == "__main__":
    sys.exit(main())
