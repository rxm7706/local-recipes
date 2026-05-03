#!/usr/bin/env python3
"""
inventory-channel — Audit a channel/mirror inventory.

Auto-detects format from URL or file content:
  - conda repodata.json   (key 'packages.conda' or 'packages')
  - PyPI Simple v1 JSON   (key 'projects' with name/_last-serial)
  - npm registry CouchDB  (key 'rows' with id/value)
  - crates.io sparse index (local file/dir; bulk fetch deferred to v2)

For each detected format, fetches/parses the inventory, cross-references
against cf_atlas.db, optionally scans for CVEs via vdb, and renders a
sectioned report. Default --with-vulns is ON for conda channels (~60s for
20k pkgs), OFF for PyPI/npm/cargo (much larger universes).

JFrog auth: honors JFROG_API_KEY, JFROG_USERNAME+JFROG_PASSWORD env vars.
Cache: 24h TTL at .claude/data/conda-forge-expert/inventory_cache/.

CLI:
  inventory-channel <URL_OR_FILE>
                    [--with-vulns | --no-vulns]
                    [--diff]            # compare against upstream conda-forge
                    [--health]          # mirror health: yanked/orphaned/archived
                    [--brief]
                    [--no-cache]
                    [--cache-ttl SECONDS]
                    [--json]
                    [--csv]
                    [--sbom {cyclonedx,spdx}]
                    [--sbom-out PATH]
                    [--limit N]         # cap deps scanned (for testing)

Pixi:
  pixi run -e vuln-db inventory-channel -- https://conda.anaconda.org/conda-forge/noarch/repodata.json
  pixi run -e vuln-db inventory-channel -- https://your-jfrog/conda-forge/linux-64/repodata.json --diff --health
  pixi run -e vuln-db inventory-channel -- https://pypi.org/simple/ --with-vulns
"""
from __future__ import annotations

import argparse
import csv as csv_mod
import io
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from base64 import b64encode
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Enterprise HTTP helpers (truststore + .netrc auth)
sys.path.insert(0, str(Path(__file__).parent))
try:
    from _http import inject_ssl_truststore, make_request as _http_make_request  # type: ignore[import-not-found]
    inject_ssl_truststore()
    _HTTP_AVAILABLE = True
except ImportError:
    _HTTP_AVAILABLE = False


def _get_data_dir() -> Path:
    """Get skill-scoped data directory: .claude/data/conda-forge-expert/"""
    return Path(__file__).parent.parent.parent.parent / "data" / "conda-forge-expert"


DATA_DIR = _get_data_dir()
ATLAS_DB = DATA_DIR / "cf_atlas.db"
CACHE_DIR = DATA_DIR / "inventory_cache"
RULE = "─" * 74
DOUBLE_RULE = "═" * 74
DEFAULT_CACHE_TTL = 86400  # 24h


@dataclass
class Package:
    name: str
    version: str | None
    ecosystem: str  # conda / pypi / npm / cargo
    license: str | None = None
    license_family: str | None = None
    timestamp: int | None = None
    size: int | None = None
    extras: dict[str, Any] = field(default_factory=dict)
    # Aliases so SBOM emitter can treat us like Dep
    @property
    def manifest(self) -> str:
        return self.extras.get("source_url", "channel")

    def purl(self) -> str | None:
        if self.version:
            return f"pkg:{self.ecosystem}/{self.name}@{self.version}"
        return f"pkg:{self.ecosystem}/{self.name}"


# ── Fetcher with cache + JFrog auth + .netrc + truststore ───────────────────

def _make_request(url: str) -> urllib.request.Request:
    """Build a Request with JFrog/netrc/Bearer auth. Uses _http if available."""
    if _HTTP_AVAILABLE:
        return _http_make_request(url, user_agent="inventory-channel/1.0")
    # Fallback: env-var only auth (no .netrc)
    headers: dict[str, str] = {"User-Agent": "inventory-channel/1.0"}
    if os.environ.get("JFROG_API_KEY"):
        headers["X-JFrog-Art-Api"] = os.environ["JFROG_API_KEY"]
    elif os.environ.get("JFROG_USERNAME") and os.environ.get("JFROG_PASSWORD"):
        creds = f"{os.environ['JFROG_USERNAME']}:{os.environ['JFROG_PASSWORD']}"
        headers["Authorization"] = "Basic " + b64encode(creds.encode()).decode()
    return urllib.request.Request(url, headers=headers)


def fetch_source(url_or_path: str, no_cache: bool, cache_ttl: int) -> tuple[bytes | None, str | None]:
    """Fetch from URL (with caching) or read local file. Returns (bytes, error)."""
    is_url = url_or_path.startswith(("http://", "https://"))
    if not is_url:
        p = Path(url_or_path)
        if not p.exists():
            return (None, f"local file not found: {p}")
        try:
            return (p.read_bytes(), None)
        except OSError as e:
            return (None, f"local file read error: {e}")

    # URL fetch with cache
    cache_key = url_or_path.replace("/", "_").replace(":", "_")[:200]
    cache_path = CACHE_DIR / f"{cache_key}.cache"
    if not no_cache and cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < cache_ttl:
            return (cache_path.read_bytes(), None)

    try:
        req = _make_request(url_or_path)
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = resp.read()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(data)
        return (data, None)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return (None, "401 unauthorized (set JFROG_API_KEY or JFROG_USERNAME+PASSWORD)")
        return (None, f"HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        return (None, f"unreachable: {e.reason}")
    except (TimeoutError, OSError) as e:
        return (None, f"network error: {e}")


# ── Format detection + parsers ──────────────────────────────────────────────

def detect_format(url: str, content: bytes) -> str:
    """Returns 'conda' | 'pypi' | 'npm' | 'cargo' | 'unknown'."""
    if "repodata.json" in url.lower():
        return "conda"
    if url.endswith("/simple/") or "pypi.org/simple" in url:
        return "pypi"
    if "_all_docs" in url or "registry.npmjs.org" in url:
        return "npm"
    if "crates.io" in url or url.endswith(".crates-index"):
        return "cargo"
    # Sniff content
    try:
        sample = content[:4096].decode("utf-8", errors="ignore")
        if "packages.conda" in sample or '"info"' in sample and '"subdir"' in sample:
            return "conda"
        if '"projects"' in sample and "_last-serial" in sample:
            return "pypi"
        if '"rows"' in sample and '"id"' in sample:
            return "npm"
    except Exception:
        pass
    return "unknown"


def parse_conda_repodata(content: bytes) -> tuple[list[Package], dict[str, Any]]:
    """Parse a conda repodata.json. Returns (packages, info)."""
    data = json.loads(content)
    info = data.get("info", {}) or {}
    packages: dict[str, Package] = {}  # name → latest Package by timestamp

    for source_dict in (data.get("packages.conda", {}), data.get("packages", {})):
        for rec in (source_dict or {}).values():
            name = rec.get("name")
            if not name:
                continue
            ts = rec.get("timestamp", 0) or 0
            existing = packages.get(name)
            if existing is None or (ts and (existing.timestamp or 0) < ts):
                packages[name] = Package(
                    name=name,
                    version=rec.get("version"),
                    ecosystem="conda",
                    license=rec.get("license"),
                    license_family=rec.get("license_family"),
                    timestamp=int(ts / 1000) if ts else None,
                    size=rec.get("size"),
                    extras={
                        "subdir": info.get("subdir"),
                        "noarch": rec.get("noarch"),
                        "build": rec.get("build"),
                        "depends_count": len(rec.get("depends") or []),
                    },
                )
    return (list(packages.values()), info)


def parse_pypi_simple(content: bytes) -> list[Package]:
    data = json.loads(content)
    return [
        Package(
            name=p["name"].lower(), version=None, ecosystem="pypi",
            extras={"_last-serial": p.get("_last-serial")},
        )
        for p in (data.get("projects") or [])
        if p.get("name")
    ]


def parse_npm_registry(content: bytes) -> list[Package]:
    data = json.loads(content)
    return [
        Package(name=row["id"].lower(), version=None, ecosystem="npm")
        for row in (data.get("rows") or [])
        if row.get("id")
    ]


def parse_cargo_sparse(content: bytes) -> list[Package]:
    """crates.io sparse index — JSONL, one line per crate version."""
    pkgs: dict[str, Package] = {}
    for line in content.decode("utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        name = rec.get("name")
        if not name:
            continue
        # Keep latest version per crate
        ver = rec.get("vers")
        existing = pkgs.get(name)
        if existing is None or (ver and existing.version and ver > existing.version):
            pkgs[name] = Package(name=name.lower(), version=ver, ecosystem="cargo")
    return list(pkgs.values())


# ── Atlas cross-reference ───────────────────────────────────────────────────

def cross_reference_atlas(packages: list[Package], ecosystem: str) -> dict[str, dict[str, Any]]:
    if not ATLAS_DB.exists():
        return {}
    conn = sqlite3.connect(ATLAS_DB)
    conn.row_factory = sqlite3.Row
    col = "conda_name" if ecosystem == "conda" else \
          "pypi_name" if ecosystem == "pypi" else \
          "npm_name" if ecosystem == "npm" else None
    if not col:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for pkg in packages:
        row = conn.execute(
            f"SELECT conda_name, pypi_name, feedstock_archived, latest_status, "
            f"conda_license, latest_conda_version FROM packages WHERE {col} = ?",
            (pkg.name,),
        ).fetchone()
        if row:
            out[pkg.name] = dict(row)
    return out


# ── Vuln scan ───────────────────────────────────────────────────────────────

def scan_vulns(
    packages: list[Package],
    limit: int | None = None,
    atlas_xref: dict[str, dict[str, Any]] | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], str | None]:
    """Scan vdb. For conda packages, also probes the pypi-equivalent purl since vdb
    indexes upstream advisories by `pkg:pypi/...`. Atlas xref provides the pypi name
    when known; otherwise falls back to the conda name."""
    try:
        from vdb.lib import search as vdb_search  # type: ignore[import-untyped]
    except ImportError:
        return ({}, "vdb library not installed (run from `vuln-db` env)")
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from detail_cf_atlas import _extract_vuln_fields  # type: ignore[import-not-found]
    except ImportError:
        return ({}, "detail_cf_atlas._extract_vuln_fields missing")

    atlas_xref = atlas_xref or {}
    out: dict[str, list[dict[str, Any]]] = {}
    iter_pkgs = packages[:limit] if limit else packages
    for pkg in iter_pkgs:
        primary = pkg.purl()
        if not primary:
            continue
        purls = [primary]
        if pkg.ecosystem == "conda":
            atlas = atlas_xref.get(pkg.name) or {}
            pypi_name = atlas.get("pypi_name") or pkg.name
            pypi_purl = (
                f"pkg:pypi/{pypi_name}@{pkg.version}" if pkg.version else f"pkg:pypi/{pypi_name}"
            )
            if pypi_purl != primary:
                purls.append(pypi_purl)
        seen_ids: set[str] = set()
        extracted: list[dict[str, Any]] = []
        for purl in purls:
            try:
                results = list(vdb_search.search_by_purl_like(purl, with_data=True) or [])
            except Exception:
                continue
            for r in results:
                v = _extract_vuln_fields(r)
                vid = v.get("id")
                if vid and vid in seen_ids:
                    continue
                if vid:
                    seen_ids.add(vid)
                extracted.append(v)
        if extracted:
            key = f"{pkg.ecosystem}:{pkg.name}@{pkg.version}"
            out[key] = extracted
    return (out, None)


# ── Mirror health ───────────────────────────────────────────────────────────

def mirror_health(packages: list[Package], atlas_xref: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Compute health signals: archived feedstock count, stale-version count, etc."""
    archived = 0
    stale_version = 0  # mirror has older version than atlas
    inactive = 0
    no_atlas_match = 0
    for pkg in packages:
        atlas = atlas_xref.get(pkg.name)
        if not atlas:
            no_atlas_match += 1
            continue
        if atlas.get("feedstock_archived"):
            archived += 1
        if atlas.get("latest_status") == "inactive":
            inactive += 1
        atlas_v = atlas.get("latest_conda_version")
        if atlas_v and pkg.version and atlas_v != pkg.version:
            stale_version += 1
    return {
        "archived_feedstocks": archived,
        "stale_versions": stale_version,
        "inactive_packages": inactive,
        "no_atlas_match": no_atlas_match,
    }


# ── Diff against upstream ───────────────────────────────────────────────────

def fetch_upstream_diff(ecosystem: str, info: dict[str, Any], no_cache: bool, cache_ttl: int) -> tuple[set[str] | None, str | None]:
    """For conda channels, fetch upstream conda-forge equivalent and return its package name set."""
    if ecosystem != "conda":
        return (None, "diff only supported for conda channels in v1")
    subdir = info.get("subdir")
    if not subdir:
        return (None, "subdir missing from local channel info; cannot diff")
    upstream_url = f"https://conda.anaconda.org/conda-forge/{subdir}/repodata.json"
    content, err = fetch_source(upstream_url, no_cache, cache_ttl)
    if err or not content:
        return (None, f"upstream fetch failed: {err}")
    upstream_pkgs, _ = parse_conda_repodata(content)
    return ({p.name for p in upstream_pkgs}, None)


# ── Render ──────────────────────────────────────────────────────────────────

def render(
    source: str, fmt: str, info: dict[str, Any], packages: list[Package],
    atlas_xref: dict[str, dict[str, Any]], vulns_by_pkg: dict[str, list[dict[str, Any]]],
    health: dict[str, Any] | None, diff_upstream: set[str] | None,
    source_status: dict[str, str], brief: bool,
) -> str:
    out: list[str] = []
    p = out.append

    p(DOUBLE_RULE)
    p(f"  Channel inventory: {source}")
    p(DOUBLE_RULE)
    p("")
    p(f"  Format:           {fmt}")
    p(f"  Total packages:   {len(packages):,}")
    if fmt == "conda" and info:
        p(f"  Channel info:     subdir={info.get('subdir', '?')}  repodata_version={info.get('repodata_version', '?')}")
    if atlas_xref:
        p(f"  Atlas matches:    {len(atlas_xref):,} of {len(packages):,} ({100*len(atlas_xref)//max(1,len(packages))}%)")

    # Severity breakdown
    if vulns_by_pkg:
        p("")
        p(RULE)
        p("  Vulnerability overview")
        p(RULE)
        sev_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Unknown": 0}
        kev_count = 0
        pkg_with_vulns = 0
        pkg_risk: list[tuple[str, int, int, int, int, list[dict[str, Any]]]] = []
        for pkg_key, vlist in vulns_by_pkg.items():
            if not vlist:
                continue
            pkg_with_vulns += 1
            c = h = m = ll = 0
            for v in vlist:
                sev = v["severity"] if v["severity"] in sev_counts else "Unknown"
                sev_counts[sev] += 1
                if v["kev"]:
                    kev_count += 1
                if sev == "Critical": c += 1
                elif sev == "High": h += 1
                elif sev == "Medium": m += 1
                elif sev == "Low": ll += 1
            pkg_risk.append((pkg_key, c, h, m, ll, vlist))
        p(f"  Packages with any CVE:    {pkg_with_vulns:,} of {len(packages):,} ({100*pkg_with_vulns//max(1,len(packages))}%)")
        for s in ("Critical", "High", "Medium", "Low", "Unknown"):
            if sev_counts[s]:
                p(f"  {s:<25} {sev_counts[s]:,}")
        if kev_count:
            p(f"  KEV-listed:               {kev_count}")

        # Top N most-vulnerable
        if pkg_risk and not brief:
            pkg_risk.sort(key=lambda x: (-x[1], -x[2], -x[3], -x[4]))
            top_n = 10
            p("")
            p(f"  Top {min(top_n, len(pkg_risk))} most-vulnerable in this channel:")
            for pkg_key, c, h, m, ll, vlist in pkg_risk[:top_n]:
                counts = []
                if c: counts.append(f"{c} Crit")
                if h: counts.append(f"{h} High")
                if m: counts.append(f"{m} Med")
                if ll: counts.append(f"{ll} Low")
                p(f"    {pkg_key:<45} {', '.join(counts)}")

    # Mirror health
    if health:
        p("")
        p(RULE)
        p("  Mirror health signals")
        p(RULE)
        p(f"  Archived feedstocks:      {health['archived_feedstocks']:,}")
        p(f"  Stale versions vs atlas:  {health['stale_versions']:,}")
        p(f"  Inactive packages:        {health['inactive_packages']:,}")
        p(f"  No atlas match:           {health['no_atlas_match']:,}")

    # Diff against upstream
    if diff_upstream is not None:
        p("")
        p(RULE)
        p("  Diff vs upstream conda-forge")
        p(RULE)
        local_set = {pkg.name for pkg in packages}
        only_local = local_set - diff_upstream
        only_upstream = diff_upstream - local_set
        p(f"  In this channel ∩ upstream:  {len(local_set & diff_upstream):,}")
        p(f"  In this channel only:        {len(only_local):,}  (internal/private/forks)")
        p(f"  In upstream only:            {len(only_upstream):,}  (mirror gaps)")
        if only_local and not brief:
            p("")
            p("  First 10 channel-only packages (likely internal):")
            for n in sorted(only_local)[:10]:
                p(f"    {n}")

    # Source summary
    p("")
    p(DOUBLE_RULE)
    p("  Source summary")
    p(DOUBLE_RULE)
    sym = {"ok": "✓", "fail": "✗", "skip": "—"}
    for src, status in source_status.items():
        if src.endswith("_msg"):
            continue
        msg = source_status.get(f"{src}_msg", "")
        p(f"  {sym.get(status, '?')} {src:<35} {msg}")
    p(DOUBLE_RULE)
    return "\n".join(out)


# ── CSV emit ────────────────────────────────────────────────────────────────

def emit_csv(packages: list[Package], vulns_by_pkg: dict[str, list[dict[str, Any]]],
             atlas_xref: dict[str, dict[str, Any]]) -> str:
    buf = io.StringIO()
    w = csv_mod.writer(buf)
    w.writerow(["name", "version", "ecosystem", "license", "license_family",
                "vuln_count", "critical", "high", "medium", "low",
                "atlas_match", "feedstock_archived", "latest_status"])
    for pkg in packages:
        key = f"{pkg.ecosystem}:{pkg.name}@{pkg.version}"
        vulns = vulns_by_pkg.get(key, [])
        crit = sum(1 for v in vulns if v["severity"] == "Critical")
        high = sum(1 for v in vulns if v["severity"] == "High")
        med = sum(1 for v in vulns if v["severity"] == "Medium")
        low = sum(1 for v in vulns if v["severity"] == "Low")
        atlas = atlas_xref.get(pkg.name, {})
        w.writerow([
            pkg.name, pkg.version or "", pkg.ecosystem, pkg.license or "",
            pkg.license_family or "", len(vulns), crit, high, med, low,
            "yes" if atlas else "no",
            atlas.get("feedstock_archived", ""),
            atlas.get("latest_status", ""),
        ])
    return buf.getvalue()


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "inventory-channel").split("\n")[1])
    parser.add_argument("source", help="URL or local file path to channel index")
    parser.add_argument("--with-vulns", dest="vulns", action="store_const", const=True,
                        help="Force vulnerability scan ON")
    parser.add_argument("--no-vulns", dest="vulns", action="store_const", const=False,
                        help="Force vulnerability scan OFF")
    parser.add_argument("--diff", action="store_true", help="Compare against upstream conda-forge")
    parser.add_argument("--health", action="store_true", help="Mirror health signals")
    parser.add_argument("--brief", action="store_true", help="Summary only")
    parser.add_argument("--no-cache", dest="no_cache", action="store_true",
                        help="Always re-fetch, ignore cache")
    parser.add_argument("--cache-ttl", dest="cache_ttl", type=int, default=DEFAULT_CACHE_TTL,
                        help=f"Cache TTL in seconds (default: {DEFAULT_CACHE_TTL})")
    parser.add_argument("--limit", type=int, help="Cap deps scanned (for testing)")
    parser.add_argument("--json", dest="as_json", action="store_true",
                        help="Output raw JSON")
    parser.add_argument("--csv", dest="as_csv", action="store_true",
                        help="Output CSV (one row per package)")
    parser.add_argument("--sbom", choices=["cyclonedx", "spdx"],
                        help="Emit SBOM (CycloneDX 1.6 or SPDX 2.3 JSON)")
    parser.add_argument("--sbom-out", dest="sbom_out", help="Write SBOM to file")
    args = parser.parse_args()

    source_status: dict[str, str] = {}

    # 1. Fetch
    t0 = time.monotonic()
    content, err = fetch_source(args.source, args.no_cache, args.cache_ttl)
    if err or not content:
        print(f"ERROR: fetch failed: {err}", file=sys.stderr)
        return 1
    source_status["channel fetch"] = "ok"
    source_status["channel fetch_msg"] = f"— {len(content):,} bytes in {time.monotonic() - t0:.1f}s"

    # 2. Detect format
    fmt = detect_format(args.source, content)
    source_status["format detection"] = "ok" if fmt != "unknown" else "fail"
    source_status["format detection_msg"] = f"— {fmt}"
    if fmt == "unknown":
        print(f"ERROR: unknown channel format for {args.source}", file=sys.stderr)
        return 2

    # 3. Parse
    info: dict[str, Any] = {}
    if fmt == "conda":
        packages, info = parse_conda_repodata(content)
    elif fmt == "pypi":
        packages = parse_pypi_simple(content)
    elif fmt == "npm":
        packages = parse_npm_registry(content)
    elif fmt == "cargo":
        packages = parse_cargo_sparse(content)
    else:
        packages = []
    source_status["parse"] = "ok"
    source_status["parse_msg"] = f"— {len(packages):,} packages"

    # 4. Atlas xref
    atlas_xref = cross_reference_atlas(packages, fmt)
    if ATLAS_DB.exists():
        source_status["atlas cross-reference"] = "ok"
        source_status["atlas cross-reference_msg"] = f"— matched {len(atlas_xref):,} of {len(packages):,}"
    else:
        source_status["atlas cross-reference"] = "fail"
        source_status["atlas cross-reference_msg"] = "— atlas DB missing; run `build-cf-atlas`"

    # 5. Vuln scan (default ON for conda, OFF for others)
    do_vulns = args.vulns if args.vulns is not None else (fmt == "conda")
    vulns_by_pkg: dict[str, list[dict[str, Any]]] = {}
    if do_vulns:
        t1 = time.monotonic()
        if len(packages) > 50000:
            print(f"WARNING: scanning {len(packages):,} packages — may take many minutes",
                  file=sys.stderr)
        vulns_by_pkg, vdb_err = scan_vulns(packages, args.limit, atlas_xref)
        if vdb_err:
            source_status["vdb scan"] = "fail"
            source_status["vdb scan_msg"] = f"— {vdb_err}"
        else:
            source_status["vdb scan"] = "ok"
            source_status["vdb scan_msg"] = (
                f"— scanned {len(packages):,}, {sum(1 for v in vulns_by_pkg.values() if v):,} with vulns "
                f"in {time.monotonic() - t1:.1f}s"
            )
    else:
        source_status["vdb scan"] = "skip"
        if args.vulns is False:
            reason = "explicitly disabled with --no-vulns"
        else:
            reason = "default OFF for non-conda (use --with-vulns to enable)"
        source_status["vdb scan_msg"] = f"— {reason}"

    # 6. Mirror health (atlas-derived)
    health = None
    if args.health:
        if atlas_xref:
            health = mirror_health(packages, atlas_xref)
            source_status["mirror health"] = "ok"
            source_status["mirror health_msg"] = "— computed from atlas cross-reference"
        else:
            source_status["mirror health"] = "fail"
            source_status["mirror health_msg"] = "— requires atlas DB"

    # 7. Diff against upstream
    diff_upstream = None
    if args.diff:
        t2 = time.monotonic()
        diff_upstream, derr = fetch_upstream_diff(fmt, info, args.no_cache, args.cache_ttl)
        if derr or diff_upstream is None:
            source_status["upstream diff"] = "fail"
            source_status["upstream diff_msg"] = f"— {derr or 'no data'}"
        else:
            source_status["upstream diff"] = "ok"
            source_status["upstream diff_msg"] = (
                f"— upstream has {len(diff_upstream):,} packages "
                f"(fetched in {time.monotonic() - t2:.1f}s)"
            )

    # Output
    if args.sbom:
        sys.path.insert(0, str(Path(__file__).parent))
        from _sbom import emit_cyclonedx, emit_spdx  # type: ignore[import-not-found]
        emitter = emit_cyclonedx if args.sbom == "cyclonedx" else emit_spdx
        # Adapt atlas_xref keys for SBOM (it expects ecosystem:name)
        atlas_for_sbom = {f"{fmt}:{name}": rec for name, rec in atlas_xref.items()}
        sbom = emitter(packages, vulns_by_pkg,
                       project_name=Path(args.source).stem or "channel",
                       atlas_records=atlas_for_sbom)
        sbom_json = json.dumps(sbom, indent=2, default=str)
        if args.sbom_out:
            Path(args.sbom_out).write_text(sbom_json)
            print(f"SBOM ({args.sbom}) written to {args.sbom_out}", file=sys.stderr)
        else:
            print(sbom_json)
    elif args.as_csv:
        print(emit_csv(packages, vulns_by_pkg, atlas_xref))
    elif args.as_json:
        print(json.dumps({
            "source": args.source, "format": fmt, "info": info,
            "packages": [p.__dict__ for p in packages],
            "atlas_xref": atlas_xref,
            "vulns_by_pkg": vulns_by_pkg,
            "health": health,
            "diff_upstream": sorted(diff_upstream) if diff_upstream else None,
            "source_status": {k: v for k, v in source_status.items() if not k.endswith("_msg")},
        }, indent=2, default=str))
    else:
        print(render(args.source, fmt, info, packages, atlas_xref,
                     vulns_by_pkg, health, diff_upstream, source_status, args.brief))
    return 0


if __name__ == "__main__":
    sys.exit(main())
