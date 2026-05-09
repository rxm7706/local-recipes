#!/usr/bin/env python3
"""
detail-cf-atlas — Render a comprehensive package detail card.

Pulls together four sources, gracefully degrading when any source fails:

  1. Local cf_atlas.db (offline-safe, primary)               -- always tried
  2a. anaconda.org files API (per-build artifact info)       -- network, primary
  2b. conda-forge channel current_repodata.json (fallback)   -- network, kicks in
                                                                when 2a fails
  3. conda_forge_metadata.ArtifactData (full per-build)      -- needs --deep flag

The 2a→2b fallback exists for air-gapped enterprise networks where
api.anaconda.org is blocked but a conda channel mirror (JFrog Artifactory,
prefix.dev) is reachable. The fallback uses the same URL chain as
`_http.resolve_conda_forge_urls()`: CONDA_FORGE_BASE_URL → pixi mirrors →
pixi default-channels → repo.prefix.dev → conda.anaconda.org.

Outputs a sectioned terminal card with Source Summary at the bottom listing
which sources contributed data and which failed.

CLI:
  detail-cf-atlas <package_name> [--deep] [--files] [--subdir SUBDIR] [--json]

Pixi:
  pixi run -e local-recipes detail-cf-atlas -- bmad-method
  pixi run -e local-recipes detail-cf-atlas -- bmad-method --deep
  pixi run -e local-recipes detail-cf-atlas -- bmad-method --deep --files
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _get_data_dir() -> Path:
    """Get skill-scoped data directory: .claude/data/conda-forge-expert/"""
    return Path(__file__).parent.parent.parent.parent / "data" / "conda-forge-expert"


DATA_DIR = _get_data_dir()
DB_PATH = DATA_DIR / "cf_atlas.db"
ANACONDA_BASE = os.environ.get("ANACONDA_API_BASE", "https://api.anaconda.org")
NETWORK_TIMEOUT = 10  # seconds

# Probed when atlas has no `conda_subdirs` for a package. Order matches the
# conda-forge canonical set; win-32 is intentionally omitted (deprecated).
_STANDARD_CONDA_FORGE_SUBDIRS: tuple[str, ...] = (
    "linux-64", "linux-aarch64", "linux-ppc64le",
    "noarch",
    "osx-64", "osx-arm64",
    "win-64",
)

# ANSI sectioning helpers
RULE = "─" * 74
DOUBLE_RULE = "═" * 74

# Enterprise HTTP helpers (truststore + .netrc auth)
sys.path.insert(0, str(Path(__file__).parent))
try:
    from _http import inject_ssl_truststore, make_request as _http_make_request  # type: ignore[import-not-found]
    inject_ssl_truststore()
except ImportError:
    _http_make_request = None  # type: ignore[assignment]


def _humanize_timestamp(ts: int | None) -> str:
    if not ts:
        return "—"
    t = dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc)
    delta_days = (dt.datetime.now(dt.timezone.utc) - t).days
    suffix = (
        f"({delta_days} days ago)" if delta_days > 1
        else "(yesterday)" if delta_days == 1
        else "(today)"
    )
    return f"{t.strftime('%Y-%m-%d %H:%M UTC')} {suffix}"


def _humanize_size(n: int | float | None) -> str:
    if not n:
        return "—"
    size: float = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.2f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def fetch_atlas(name: str) -> tuple[dict[str, Any] | None, list[str], str | None]:
    """Source #1: local cf_atlas.db. Returns (record, maintainers, error_msg)."""
    if not DB_PATH.exists():
        return (None, [], f"atlas DB missing at {DB_PATH} — run `build-cf-atlas` first")
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM v_packages_enriched WHERE conda_name = ? OR pypi_name = ? LIMIT 1",
            (name, name),
        ).fetchone()
        if row is None:
            return (None, [], f"no atlas record found for `{name}`")
        record = dict(row)
        maintainers: list[str] = []
        if record.get("conda_name"):
            maintainers = [
                r[0] for r in conn.execute(
                    "SELECT m.handle FROM maintainers m "
                    "JOIN package_maintainers pm ON pm.maintainer_id = m.id "
                    "WHERE pm.conda_name = ? ORDER BY m.handle",
                    (record["conda_name"],),
                )
            ]
        return (record, maintainers, None)
    except sqlite3.Error as e:
        return (None, [], f"atlas SQLite error: {e}")


def fetch_anaconda_files(name: str, subdir_filter: str | None = None) -> tuple[list[dict[str, Any]], str | None]:
    """Source #2: anaconda.org per-package files API. Returns (latest_per_subdir, error_msg)."""
    url = f"{ANACONDA_BASE}/package/conda-forge/{name}/files"
    try:
        if _http_make_request is not None:
            req = _http_make_request(url, user_agent="detail-cf-atlas/1.0")
        else:
            req = urllib.request.Request(url, headers={"User-Agent": "detail-cf-atlas/1.0"})
        with urllib.request.urlopen(req, timeout=NETWORK_TIMEOUT) as resp:
            files = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return ([], f"package `{name}` not found on anaconda.org/conda-forge")
        return ([], f"anaconda.org HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        return ([], f"anaconda.org unreachable: {e.reason}")
    except (TimeoutError, OSError) as e:
        return ([], f"anaconda.org timeout/network error: {e}")
    except Exception as e:
        return ([], f"anaconda.org unexpected error: {e}")

    # Reduce to latest build per subdir
    by_subdir: dict[str, dict[str, Any]] = {}
    for f in files:
        attrs = f.get("attrs", {}) or {}
        sd = attrs.get("subdir")
        if not sd or (subdir_filter and sd != subdir_filter):
            continue
        ts = f.get("upload_time", "")
        if sd not in by_subdir or ts > by_subdir[sd].get("upload_time", ""):
            by_subdir[sd] = f
    return (sorted(by_subdir.values(), key=lambda f: f["attrs"]["subdir"]), None)


def fetch_repodata_build_matrix(
    name: str,
    subdir_filter: str | None,
    atlas_subdirs: list[str],
) -> tuple[list[dict[str, Any]], str | None, str | None]:
    """Source #2 fallback: per-subdir current_repodata.json from a conda channel.

    Used when api.anaconda.org is unreachable (common in air-gapped enterprise
    networks). Resolves base URLs through `_http.resolve_conda_forge_urls()`,
    which honors CONDA_FORGE_BASE_URL → pixi mirrors → pixi default-channels →
    repo.prefix.dev/conda-forge → conda.anaconda.org/conda-forge in priority
    order. JFrog auth (X-JFrog-Art-Api / Basic) is injected by `_http_make_request`
    when the relevant env vars are set.

    For each subdir, fetches `<base>/<sd>/current_repodata.json` and selects
    the latest matching package (highest `timestamp`, falling back to first-seen
    when timestamps are absent). Reshapes to the same dict shape
    `fetch_anaconda_files` returns so the renderer is source-agnostic.

    `current_repodata.json` contains only the latest builds per package — same
    granularity as the files API for "latest per subdir". Drops `upload_time`
    (repodata's `timestamp` is build time, not upload time, and is in millis);
    the renderer prints that field as empty cleanly.

    Returns (records, base_url_used, error_msg). `base_url_used` is which
    candidate the first successful fetch came from; surfaced in source_status
    so the user sees whether it was prefix.dev, JFrog, or anaconda.org.
    """
    if _http_make_request is None:
        return ([], None, "_http helper not importable; cannot resolve fallback URLs")
    try:
        from _http import resolve_conda_forge_urls  # type: ignore[import-not-found]
    except ImportError:
        return ([], None, "_http.resolve_conda_forge_urls unavailable")

    candidates = resolve_conda_forge_urls()
    if not candidates:
        return ([], None, "no conda-forge base URLs resolved (env, pixi config, or fallbacks)")

    subdirs = list(atlas_subdirs) if atlas_subdirs else list(_STANDARD_CONDA_FORGE_SUBDIRS)
    if subdir_filter:
        subdirs = [s for s in subdirs if s == subdir_filter]
    if not subdirs:
        return ([], None, f"no subdirs to query (filter={subdir_filter!r})")

    base_used: str | None = None
    by_subdir: dict[str, dict[str, Any]] = {}
    last_err: str | None = None
    for sd in subdirs:
        for base in candidates:
            url = f"{base.rstrip('/')}/{sd}/current_repodata.json"
            try:
                req = _http_make_request(url, user_agent="detail-cf-atlas/1.0")
                with urllib.request.urlopen(req, timeout=NETWORK_TIMEOUT) as resp:
                    data = json.load(resp)
            except (urllib.error.HTTPError, urllib.error.URLError,
                    TimeoutError, OSError, json.JSONDecodeError) as e:
                last_err = f"{type(e).__name__}: {e}"
                continue
            base_used = base_used or base
            best: dict[str, Any] | None = None
            best_ts = -1
            for section in ("packages", "packages.conda"):
                pkgs = data.get(section) or {}
                if not isinstance(pkgs, dict):
                    continue
                for fname, meta in pkgs.items():
                    if not isinstance(meta, dict) or meta.get("name") != name:
                        continue
                    ts = int(meta.get("timestamp") or 0)
                    if ts > best_ts:
                        best_ts = ts
                        best = {
                            "basename": f"{sd}/{fname}",
                            "version": meta.get("version"),
                            "size": meta.get("size"),
                            "md5": meta.get("md5"),
                            "upload_time": "",
                            "attrs": {
                                "subdir": sd,
                                "version": meta.get("version"),
                                "build": meta.get("build"),
                                "depends": meta.get("depends") or [],
                            },
                        }
            if best is not None:
                by_subdir[sd] = best
            break  # got valid JSON for this subdir; don't probe further bases

    if not by_subdir:
        msg = (f"`{name}` not found in repodata across {len(subdirs)} subdir(s) "
               f"× {len(candidates)} candidate base(s)")
        if last_err:
            msg += f"; last network error: {last_err}"
        return ([], base_used, msg)
    return (sorted(by_subdir.values(), key=lambda f: f["attrs"]["subdir"]), base_used, None)


def fetch_artifact_data(subdir: str, basename: str) -> tuple[dict[str, Any] | None, str | None]:
    """Source #3 (--deep): full per-build metadata via conda_forge_metadata.

    Returns (info_dict, error_msg). info_dict mirrors info/index.json + about.json.
    """
    try:
        from conda_forge_metadata.types import ArtifactData  # type: ignore[import-untyped]
        from conda_forge_metadata.artifact_info import get_artifact_info_as_json  # type: ignore[import-untyped]
    except ImportError as e:
        return (None, f"conda_forge_metadata not importable: {e}")

    # basename can include 'subdir/' prefix from anaconda.org responses
    fname = basename.rsplit("/", 1)[-1]
    try:
        info: ArtifactData | dict | None = get_artifact_info_as_json(
            "conda-forge", subdir, fname,
        )
        if not info:
            return (None, f"no artifact metadata returned for {subdir}/{fname}")
        return (dict(info), None)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return (None, f"artifact fetch unreachable: {e}")
    except Exception as e:
        return (None, f"artifact fetch unexpected error: {type(e).__name__}: {e}")


_CVSS_KEYS_TO_VERSION = {
    "cvssV4_0": "v4", "cvssV4": "v4",
    "cvssV3_1": "v3.1", "cvssV3_0": "v3.0", "cvssV3": "v3",
    "cvssV2_0": "v2", "cvssV2": "v2",
}


def _walk_for_cvss(obj: Any, depth: int = 0) -> dict[str, Any] | None:
    """Recursively walk a dict/list looking for CVSS metric blocks.

    MITRE 5.0 spec puts metrics under containers.cna.metrics[], but ADP
    (Authorized Data Publishers like CISA, NVD) attach metrics under
    containers.adp[].metrics — different paths. Walk it all.
    """
    if depth > 8:  # safety: don't recurse too deep
        return None
    if isinstance(obj, dict):
        for vkey, ver in _CVSS_KEYS_TO_VERSION.items():
            cvss = obj.get(vkey)
            if cvss and isinstance(cvss, dict):
                score = cvss.get("baseScore")
                sev = cvss.get("baseSeverity")
                if score is not None:
                    sev_val = sev.get("root") if isinstance(sev, dict) else sev
                    # Pydantic enums stringify as "Severitytype.Critical"; strip the prefix
                    sev_str: str | None = None
                    if sev_val:
                        sev_str = str(sev_val).rsplit(".", 1)[-1].title()
                    return {
                        "score": score,
                        "severity": sev_str,
                        "version": ver,
                        "vector": cvss.get("vectorString"),
                    }
        for v in obj.values():
            result = _walk_for_cvss(v, depth + 1)
            if result:
                return result
    elif isinstance(obj, list):
        for item in obj:
            result = _walk_for_cvss(item, depth + 1)
            if result:
                return result
    return None


def _walk_for_descriptions(obj: Any, depth: int = 0) -> str:
    """Find the first English description anywhere in the model dump."""
    if depth > 6:
        return ""
    if isinstance(obj, dict):
        # Direct description
        if "value" in obj and "lang" in obj:
            lang = obj.get("lang")
            lang_val = lang.get("root") if isinstance(lang, dict) else lang
            if lang_val == "en":
                return (obj.get("value") or "").strip().split("\n")[0][:200]
        for v in obj.values():
            r = _walk_for_descriptions(v, depth + 1)
            if r:
                return r
    elif isinstance(obj, list):
        for item in obj:
            r = _walk_for_descriptions(item, depth + 1)
            if r:
                return r
    return ""


def _walk_for_kev(obj: Any, depth: int = 0) -> bool:
    """Look for KEV (Known Exploited Vulnerabilities) tags anywhere in the model."""
    if depth > 6:
        return False
    if isinstance(obj, dict):
        # Check tags / cisaActionDue / kev flags
        for k, v in obj.items():
            kl = str(k).lower()
            if kl in ("kev", "kev_catalog", "exploited") and v:
                return True
            if kl == "tags" and isinstance(v, list):
                for tag in v:
                    if "kev" in str(tag).lower() or "exploited" in str(tag).lower():
                        return True
            if kl in ("cisaexploitadd", "cisaactiondue", "cisarequiredaction") and v:
                return True
            if isinstance(v, (dict, list)):
                if _walk_for_kev(v, depth + 1):
                    return True
    elif isinstance(obj, list):
        for item in obj:
            if _walk_for_kev(item, depth + 1):
                return True
    return False


def _walk_for_cwe(obj: Any, depth: int = 0) -> str | None:
    """Find first CWE id anywhere in the model."""
    if depth > 6:
        return None
    if isinstance(obj, dict):
        cwe = obj.get("cweId")
        if cwe and str(cwe).startswith("CWE-"):
            return cwe
        for v in obj.values():
            r = _walk_for_cwe(v, depth + 1)
            if r:
                return r
    elif isinstance(obj, list):
        for item in obj:
            r = _walk_for_cwe(item, depth + 1)
            if r:
                return r
    return None


def _extract_vuln_fields(record: dict[str, Any]) -> dict[str, Any]:
    """Extract display-friendly fields from a raw vdb search result.

    vdb returns dicts with top-level keys: cve_id, name, type, matching_vers,
    matched_by, source_data. source_data is a Pydantic CVE model in MITRE 5.0
    format; .model_dump() exposes containers.cna AND containers.adp[] with
    descriptions, metrics, affected products. We walk the entire dump
    recursively because metric/CWE locations vary by data source (NVD puts
    them under adp, GHSA puts them under cna).
    """
    out: dict[str, Any] = {
        "id": record.get("cve_id", "?"),
        "severity": "Unknown",
        "cvss_score": None,
        "cvss_version": None,
        "cvss_vector": None,
        "description": "",
        "matching_vers": record.get("matching_vers", ""),
        "matched_by": record.get("matched_by", ""),
        "fix_version": None,
        "kev": False,
        "cwe": None,
    }
    sd = record.get("source_data")
    if not sd or not hasattr(sd, "model_dump"):
        return out
    try:
        d = sd.model_dump(exclude_none=True)
    except Exception:
        return out

    cvss = _walk_for_cvss(d)
    if cvss:
        out["cvss_score"] = cvss["score"]
        out["cvss_version"] = cvss["version"]
        out["cvss_vector"] = cvss.get("vector")
        if cvss["severity"]:
            out["severity"] = cvss["severity"]

    out["description"] = _walk_for_descriptions(d)
    out["cwe"] = _walk_for_cwe(d)
    out["kev"] = _walk_for_kev(d)

    return out


def fetch_vdb_data(record: dict[str, Any],
                   version_override: str | None = None) -> tuple[dict[str, Any] | None, str | None]:
    """Source #4 (--vdb): query AppThreat multi-source vulnerability DB.

    Derives 1-3 purls from the atlas record (pypi, conda, github, npm) and
    aggregates vuln matches across all configured sources.

    When ``version_override`` is set, version-pinned purls are built against
    that version instead of ``record["latest_conda_version"]`` — used by
    ``--version`` to query CVEs affecting an arbitrary release.

    Returns (data_dict, error_msg). data_dict is None when no purls are
    derivable or when the library is unavailable.
    """
    try:
        from vdb.lib import search as vdb_search  # type: ignore[import-untyped]
    except ImportError:
        return (None, "vdb library not installed (run from `vuln-db` env: `pixi run -e vuln-db ...`)")

    # Always query BOTH version-pinned (for "affecting current" check) AND
    # un-pinned (for "total vulns across all versions" baseline). Dedup by CVE id.
    purls: list[str] = []
    pypi_name = record.get("pypi_name")
    conda_name = record.get("conda_name")
    npm_name = record.get("npm_name")
    repo_url = record.get("conda_repo_url") or record.get("conda_dev_url") or ""
    version = version_override or record.get("latest_conda_version")
    if pypi_name:
        purls.append(f"pkg:pypi/{pypi_name}")
        if version:
            purls.append(f"pkg:pypi/{pypi_name}@{version}")
    if conda_name:
        purls.append(f"pkg:conda/{conda_name}")
        if version:
            purls.append(f"pkg:conda/{conda_name}@{version}")
    if npm_name:
        purls.append(f"pkg:npm/{npm_name}")
        if version:
            purls.append(f"pkg:npm/{npm_name}@{version}")
    import re as _re
    gh_match = _re.search(r"github\.com/([^/]+)/([^/?#.]+)", repo_url)
    if gh_match:
        purls.append(f"pkg:github/{gh_match.group(1)}/{gh_match.group(2)}")

    if not purls:
        return (None, "no purls derivable (no pypi/conda/npm name + version)")

    purl_results: list[dict[str, Any]] = []
    all_vulns: list[dict[str, Any]] = []
    affecting_ids: set[str] = set()  # CVE IDs hit by a version-pinned query
    all_seen: dict[str, dict[str, Any]] = {}  # CVE ID → extracted record
    for purl in purls:
        try:
            results = list(vdb_search.search_by_purl_like(purl, with_data=True) or [])
        except Exception as e:  # noqa: BLE001
            return (None, f"vdb search failed for {purl}: {type(e).__name__}: {e}")
        purl_results.append({"purl": purl, "matches": len(results)})
        is_version_pinned = "@" in purl
        for raw in results:
            extracted = _extract_vuln_fields(raw)
            vid = extracted["id"]
            if vid not in all_seen:
                all_seen[vid] = extracted
                all_vulns.append(extracted)
            if is_version_pinned:
                affecting_ids.add(vid)
    affecting_latest: list[dict[str, Any]] = [all_seen[vid] for vid in affecting_ids if vid in all_seen]

    by_severity: dict[str, int] = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Unknown": 0}
    kev_count = 0
    for v in all_vulns:
        sev = v["severity"] if v["severity"] in by_severity else "Unknown"
        by_severity[sev] += 1
        if v["kev"]:
            kev_count += 1

    return (
        {
            "purls": purl_results,
            "all_vulns": all_vulns,
            "by_severity": by_severity,
            "kev_count": kev_count,
            "affecting_latest_version": affecting_latest,
        },
        None,
    )


def render(record: dict[str, Any] | None,
           maintainers: list[str],
           anaconda_files: list[dict[str, Any]],
           artifact_data: dict[str, Any] | None,
           vdb_data: dict[str, Any] | None,
           source_status: dict[str, str],
           include_files: bool,
           vdb_all: bool,
           vdb_deep: bool,
           queried_version: str | None = None) -> str:
    """Render the terminal card."""
    if record is None:
        return ""  # caller already printed an error

    name = record.get("conda_name") or record.get("pypi_name") or "?"
    out: list[str] = []
    p = out.append

    # ── Header ────────────────────────────────────────────────────────────
    p(DOUBLE_RULE)
    p(f"  {name}  (conda-forge atlas)")
    p(DOUBLE_RULE)
    p("")
    if record.get("conda_summary"):
        p(f"  {record['conda_summary']}")
        p("")
    p(f"  Latest version: {record.get('latest_conda_version') or '—':<14} "
      f"Status: {record.get('latest_status') or '—':<8} "
      f"License: {record.get('conda_license') or '—'}")
    p(f"  Uploaded:       {_humanize_timestamp(record.get('latest_conda_upload'))}")
    p(f"  Recipe format:  {record.get('recipe_format') or '—':<10} "
      f"Source registry: {record.get('conda_source_registry') or '—'}")

    # ── Cross-channel relationship ─────────────────────────────────────────
    p("")
    p(RULE)
    p("  Cross-channel relationship")
    p(RULE)
    p(f"  PyPI:           {record.get('pypi_name') or '—'}")
    p(f"  npm:            {record.get('npm_name') or '—'}")
    p(f"  CRAN:           {record.get('cran_name') or '—'}")
    p(f"  CPAN:           {record.get('cpan_name') or '—'}")
    p(f"  LuaRocks:       {record.get('luarocks_name') or '—'}")
    p(f"  match_source:   {record.get('match_source')} / "
      f"{record.get('match_confidence')} confidence "
      f"({record.get('relationship')})")

    # ── Feedstock ──────────────────────────────────────────────────────────
    p("")
    p(RULE)
    p("  Feedstock")
    p(RULE)
    p(f"  Name:           {record.get('feedstock_name') or '—'}")
    archived = record.get("feedstock_archived")
    p(f"  Archived:       {'yes' if archived == 1 else 'no' if archived == 0 else '—'}")
    p(f"  GitHub:         {record.get('feedstock_url') or '—'}")
    p(f"  Maintainers:    {', '.join(maintainers) if maintainers else '— (none in atlas)'}")

    # ── Downloads (atlas v2+) ──────────────────────────────────────────────
    fetched_at = record.get("downloads_fetched_at")
    if fetched_at is not None or record.get("total_downloads") is not None:
        p("")
        p(RULE)
        p("  Downloads (anaconda.org, cached in atlas)")
        p(RULE)
        total = record.get("total_downloads")
        latest = record.get("latest_version_downloads")
        latest_ver = record.get("latest_conda_version") or "?"
        latest_label = f"Latest (v{latest_ver}):"
        p(f"  Lifetime:        {total:,}" if total is not None else "  Lifetime:        —")
        p(f"  {latest_label:<16} {latest:,}" if latest is not None
          else f"  {latest_label:<16} —")
        p(f"  Fetched:         {_humanize_timestamp(fetched_at)}")

    # ── Build matrix ───────────────────────────────────────────────────────
    p("")
    p(RULE)
    if anaconda_files:
        bm_label = source_status.get("_build_matrix_label", "anaconda.org")
        p(f"  Build matrix ({len(anaconda_files)} subdirs, latest per subdir from {bm_label})")
        p(RULE)
        for f in anaconda_files:
            attrs = f.get("attrs", {}) or {}
            ts = f.get("upload_time", "")[:10]
            version = f.get("version") or attrs.get("version") or "?"
            p(f"  {attrs.get('subdir', '?'):<14} "
              f"{version:<12} "
              f"{attrs.get('build', '?'):<20} "
              f"{_humanize_size(f.get('size')):<10} {ts}")
            p(f"                md5: {f.get('md5', '—')}")
            depends = attrs.get('depends', [])
            if depends:
                p(f"                depends: {', '.join(depends[:6])}"
                  f"{' …' if len(depends) > 6 else ''}")
    else:
        sd_atlas = record.get("conda_subdirs", "[]")
        try:
            atlas_subdirs = json.loads(sd_atlas) if sd_atlas else []
        except (json.JSONDecodeError, TypeError):
            atlas_subdirs = []
        p(f"  Build matrix ({len(atlas_subdirs)} subdir(s) per atlas; per-build details unavailable)")
        p(RULE)
        for sd in atlas_subdirs:
            p(f"  {sd:<14} {record.get('latest_conda_version', '?')}    "
              "(atlas only — build_string + size + md5 not fetched)")
        if "anaconda" in source_status and source_status["anaconda"] == "fail":
            p("")
            p("  ⚠  anaconda.org/api unreachable — could not fetch per-build artifact")
            p("     metadata (build_string, file size, md5/sha256, depends list).")
            p("     Showing atlas-cached version only.")

    # ── Project links ──────────────────────────────────────────────────────
    p("")
    p(RULE)
    p("  Project links")
    p(RULE)
    p(f"  Homepage:        {record.get('conda_homepage') or '—'}")
    p(f"  Repository:      {record.get('conda_repo_url') or '—'}")
    p(f"  Dev URL:         {record.get('conda_dev_url') or '—'}")
    p(f"  Documentation:   {record.get('conda_doc_url') or '—'}")

    # ── Maintenance signals (Phase J/M/N joined) ──────────────────────────
    if record is not None and (
        record.get("bot_status_fetched_at")
        or record.get("gh_status_fetched_at")
    ):
        p("")
        p(RULE)
        p("  Maintenance signals")
        p(RULE)
        bot_errs = record.get("bot_version_errors_count")
        bot_open = record.get("bot_open_pr_count")
        bot_state = record.get("bot_last_pr_state")
        bot_ver = record.get("bot_last_pr_version")
        if record.get("bot_status_fetched_at"):
            p(f"  Bot version-update PRs:")
            p(f"    last attempted version: {bot_ver or '—'}, "
              f"last PR state: {bot_state or '—'}")
            p(f"    open count: {bot_open if bot_open is not None else '—'}, "
              f"failed-attempt count: {bot_errs if bot_errs is not None else '—'}")
            if record.get("feedstock_bad") == 1:
                p(f"    ⚠ cf-graph flagged this feedstock as 'bad'")
        gh_ci = record.get("gh_default_branch_status")
        gh_iss = record.get("gh_open_issues_count")
        gh_pr = record.get("gh_open_prs_count")
        if record.get("gh_status_fetched_at"):
            p(f"  GitHub default branch CI: {gh_ci or '—'}")
            p(f"  GitHub open issues:       "
              f"{gh_iss if gh_iss is not None else '—'}")
            p(f"  GitHub open PRs (any):    "
              f"{gh_pr if gh_pr is not None else '—'}")

    # ── Upstream versions across registries (Phase H/K/L) ─────────────────
    if record is not None and record.get("conda_name"):
        upstream_rows = []
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            for r in conn.execute(
                "SELECT source, version, last_error FROM upstream_versions "
                "WHERE conda_name = ? ORDER BY source",
                (record["conda_name"],),
            ):
                upstream_rows.append(dict(r))
        except sqlite3.Error:
            upstream_rows = []
        if upstream_rows:
            p("")
            p(RULE)
            p("  Upstream versions (Phase H/K/L unified side table)")
            p(RULE)
            conda_v = record.get("latest_conda_version") or "?"
            p(f"  conda-forge: v{conda_v}")
            for ur in upstream_rows:
                ver = ur.get("version")
                err = ur.get("last_error")
                tag = "✓" if ver and ver != conda_v else (" " if ver else "✗")
                source = ur.get("source") or "?"
                if ver:
                    behind = " (matches)" if ver == conda_v else " (BEHIND)"
                    p(f"  {tag} {source:<10}: v{ver}{behind}")
                else:
                    p(f"  {tag} {source:<10}: — ({err or 'no data'})")

    # ── Dependency reach (Phase J) ────────────────────────────────────────
    if record is not None and record.get("conda_name"):
        try:
            conn = sqlite3.connect(DB_PATH)
            n_deps_to = list(conn.execute(
                "SELECT COUNT(DISTINCT target_conda_name) FROM dependencies "
                "WHERE source_conda_name = ?", (record["conda_name"],)
            ))[0][0]
            n_deps_from = list(conn.execute(
                "SELECT COUNT(DISTINCT source_conda_name) FROM dependencies "
                "WHERE target_conda_name = ?", (record["conda_name"],)
            ))[0][0]
        except sqlite3.Error:
            n_deps_to = n_deps_from = 0
        if n_deps_to or n_deps_from:
            p("")
            p(RULE)
            p("  Dependency graph (Phase J)")
            p(RULE)
            p(f"  Direct deps (this → ?):     {n_deps_to:>5}  "
              f"(use `whodepends {record['conda_name']}`)")
            p(f"  Direct dependents (? → this): {n_deps_from:>5}  "
              f"(use `whodepends {record['conda_name']} --reverse`)")

    # ── Channel storefronts ────────────────────────────────────────────────
    p("")
    p(RULE)
    p("  Channel storefronts")
    p(RULE)
    p(f"  anaconda.org:    {record.get('conda_anaconda_url') or '—'}")
    p(f"  prefix.dev:      {record.get('prefix_dev_url') or '—'}")
    p("  conda-metadata-app (deep inspect):")
    if anaconda_files:
        first = anaconda_files[0]
        bn = first["basename"].rsplit("/", 1)[-1]
        sd = first["attrs"]["subdir"]
        p(f"    https://conda-metadata-app.streamlit.app/?q=conda-forge/{sd}/{bn}")
    else:
        p("    ⚠  cannot build URL — needs exact build filename from anaconda.org API")
        p("       Manual workaround: visit anaconda.org link above and click any file.")

    # ── --deep section ─────────────────────────────────────────────────────
    if "artifact" in source_status:
        p("")
        p(RULE)
        if artifact_data:
            sd = artifact_data.get("subdir", "?")
            fn = artifact_data.get("name", "?")
            p(f"  Per-build artifact deep-inspect ({sd}/{fn})")
            p(RULE)
            about = artifact_data.get("about") or {}
            description = about.get("description")
            if description:
                p("  Description (full long-form from info/about.json):")
                for line in (description or "").strip().splitlines()[:30]:
                    p(f"    {line}")
                if len((description or "").splitlines()) > 30:
                    p("    [...truncated; full description in info/about.json]")
                p("")
            index = artifact_data.get("index") or {}
            depends = index.get("depends") or []
            constrains = index.get("constrains") or []
            if depends:
                p("  Full dependencies (run):")
                for d in depends:
                    p(f"    {d}")
            if constrains:
                p("  Constraints:")
                for c in constrains:
                    p(f"    {c}")
            run_exports = artifact_data.get("rendered_recipe", {}).get("build", {}).get("run_exports") if artifact_data.get("rendered_recipe") else None
            if run_exports:
                p(f"  Run-exports: {run_exports}")
            p(f"  Built with:    conda-build {about.get('conda_build_version', '?')} / conda {about.get('conda_version', '?')}")
            files_list = artifact_data.get("files") or []
            if files_list:
                total_size = sum(f.get("size_in_bytes", 0) or 0 for f in files_list if isinstance(f, dict))
                p(f"  Files:         count={len(files_list):,}  total_size={_humanize_size(total_size)}")
                if include_files:
                    p("  Files (sample):")
                    for f in files_list[:50]:
                        path = f.get("_path") if isinstance(f, dict) else str(f)
                        p(f"    {path}")
                    if len(files_list) > 50:
                        p(f"    [...truncated, {len(files_list) - 50} more files]")
        else:
            p("  Per-build artifact deep-inspect (--deep)")
            p(RULE)
            p(f"  ⚠  {source_status.get('artifact_msg', 'unavailable')}")

    # ── Cached VDB risk (atlas v6+) ────────────────────────────────────────
    # Renders only when live vdb data is NOT shown (no --vdb, or --no-vdb,
    # or vdb library unavailable) AND the atlas has a cached scan. Lets
    # local-recipes-env callers see the risk signal without spinning up
    # the heavy vuln-db env. Phase G populates these columns.
    cached_scan_ts = record.get("vdb_scanned_at") if record else None
    show_cached_vdb = (
        not ("vdb" in source_status and vdb_data)
        and cached_scan_ts is not None
        and record is not None
    )
    if show_cached_vdb and record is not None:
        p("")
        p(RULE)
        p("  VDB Risk (cached, from cf_atlas Phase G)")
        p(RULE)
        c_total = record.get("vuln_total")
        c_crit = record.get("vuln_critical_affecting_current") or 0
        c_high = record.get("vuln_high_affecting_current") or 0
        c_kev  = record.get("vuln_kev_affecting_current") or 0
        c_err  = record.get("vdb_last_error")
        if c_crit or c_kev:
            risk = "CRITICAL" if c_crit else "HIGH"
        elif c_high:
            risk = "HIGH"
        elif (c_total or 0) > 0:
            risk = "MEDIUM"
        else:
            risk = "LOW (no vulns indexed)"
        latest_v = record.get("latest_conda_version") or "?"
        p(f"  RISK: {risk}")
        p(f"  Affecting v{latest_v}: {c_crit} Critical, {c_high} High, {c_kev} KEV")
        p(f"  Total vulns indexed across all versions: {c_total if c_total is not None else '—'}")
        p(f"  Scanned: {_humanize_timestamp(cached_scan_ts)}")
        if c_err:
            p(f"  Last scan error: {c_err}")
        p("  (For full CVE list, run: pixi run -e vuln-db detail-cf-atlas-vdb <name>)")

    # ── --vdb section ──────────────────────────────────────────────────────
    if "vdb" in source_status and vdb_data:
        p("")
        p(RULE)
        p("  VDB Security (multi-source: NVD + GHSA + OSV + Snyk + npm + ...)")
        p(RULE)
        latest_v = queried_version or record.get("latest_conda_version") or "?"
        version_label = "queried_version" if queried_version else "latest_conda_version"
        affecting = vdb_data.get("affecting_latest_version", [])
        sev = vdb_data.get("by_severity", {})
        kev = vdb_data.get("kev_count", 0)
        total = len(vdb_data.get("all_vulns", []))
        # Section 1: Risk header
        crit_aff = sum(1 for v in affecting if v["severity"] == "Critical")
        high_aff = sum(1 for v in affecting if v["severity"] == "High")
        if crit_aff or kev:
            risk = "CRITICAL" if crit_aff else "HIGH"
        elif high_aff:
            risk = "HIGH"
        elif total:
            risk = "MEDIUM"
        else:
            risk = "LOW (no vulns indexed)"
        p(f"  RISK: {risk} — {crit_aff} Critical-affecting-current, {high_aff} High-affecting-current, "
          f"{kev} KEV-listed")
        p(f"        {version_label} {latest_v} → {len(affecting)} of {total} vulns affect it")
        p("")
        # Section 2: Severity counts
        p("  Severity     Total   Affecting current")
        for s in ("Critical", "High", "Medium", "Low", "Unknown"):
            n = sev.get(s, 0)
            n_aff = sum(1 for v in affecting if v["severity"] == s)
            if n or n_aff:
                p(f"  {s:<12} {n:<7} {n_aff}")
        if kev:
            p(f"  KEV catalog:  {kev} vuln(s) on the active-exploit list")
        # Section 3: Top actionable CVEs (or fallback to historical when 0 affecting)
        sev_rank = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Unknown": 4}
        if affecting:
            p("")
            limit = len(affecting) if vdb_all else 5
            sorted_list = sorted(
                affecting,
                key=lambda v: (sev_rank.get(v["severity"], 4),
                               -(float(v["cvss_score"]) if v["cvss_score"] else 0)),
            )
            p(f"  Top {min(limit, len(sorted_list))} actionable (by severity then CVSS):")
        elif vdb_data.get("all_vulns"):
            # Fallback: show historical CVEs (none affect current — just for context)
            all_v = vdb_data["all_vulns"]
            p("")
            p(f"  ✓ No vulns affect current version. Showing top historical (across all versions):")
            limit = len(all_v) if vdb_all else 5
            sorted_list = sorted(
                all_v,
                key=lambda v: (sev_rank.get(v["severity"], 4),
                               -(float(v["cvss_score"]) if v["cvss_score"] else 0)),
            )
        else:
            sorted_list = []
            limit = 0

        for v in sorted_list[:limit]:
            score_str = f"{v['cvss_score']:>4}" if v["cvss_score"] else "  — "
            cwe_str = v["cwe"] or ""
            kev_marker = " KEV" if v["kev"] else ""
            cvss_ver = f" ({v['cvss_version']})" if v.get("cvss_version") else ""
            p(f"    {v['id']:<22} {score_str}{cvss_ver:<7} {v['severity']:<9} {cwe_str:<10}{kev_marker}")
            if v["description"]:
                p(f"      {v['description'][:88]}")
            if v["matching_vers"]:
                p(f"      affected: {v['matching_vers'][:80]}")
        # Section 5+6 (only with --vdb-deep)
        if vdb_deep:
            p("")
            p("  Purl coverage:")
            for pr in vdb_data.get("purls", []):
                p(f"    {pr['purl']:<50} {pr['matches']} match(es)")

    # ── Source summary ─────────────────────────────────────────────────────
    p("")
    p(DOUBLE_RULE)
    p("  Source summary")
    p(DOUBLE_RULE)
    sym = {"ok": "✓", "fail": "✗", "skip": "—"}
    # internal-only keys (single-word) used as flags by the renderer; hide them
    INTERNAL_KEYS = {"anaconda", "artifact", "vdb", "_build_matrix_label"}
    for src, status in source_status.items():
        if src.endswith("_msg") or src in INTERNAL_KEYS:
            continue
        msg = source_status.get(f"{src}_msg", "")
        p(f"  {sym.get(status, '?')} {src:<35} {msg}")
    p("")
    p("  Hints:")
    p("  • Most fields above came from your local cf_atlas.db (offline-safe).")
    if any(s == "fail" for k, s in source_status.items() if not k.endswith("_msg")):
        p("  • Re-run when network is available to populate per-build details.")
        p("  • For air-gapped / JFrog mirrors, set CONDA_FORGE_BASE_URL and")
        p("    ANACONDA_API_BASE env vars to redirect.")
    p(DOUBLE_RULE)

    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1] if __doc__ else "")
    parser.add_argument("name", help="Package name (conda_name or pypi_name)")
    parser.add_argument("--deep", action="store_true",
                        help="Fetch per-build deep metadata via conda_forge_metadata (~2s)")
    parser.add_argument("--files", action="store_true",
                        help="With --deep, list file paths from paths.json (verbose)")
    parser.add_argument("--subdir", help="Filter to a single subdir (e.g., linux-64)")
    parser.add_argument("--vdb", action=argparse.BooleanOptionalAction, default=False,
                        help="Query AppThreat multi-source vulnerability DB (requires `vuln-db` env). "
                             "Pass --no-vdb to skip the vuln pass when invoked from a task that "
                             "enables it by default (e.g., the vuln-db env's detail-cf-atlas).")
    parser.add_argument("--vdb-deep", dest="vdb_deep", action="store_true",
                        help="With --vdb, also show purl coverage and source attribution")
    parser.add_argument("--vdb-all", dest="vdb_all", action="store_true",
                        help="With --vdb, list ALL affecting vulns (not just top 5)")
    parser.add_argument("--version", dest="queried_version", metavar="VERSION",
                        help="With --vdb, override the version used in version-pinned purls "
                             "(default: latest_conda_version from atlas)")
    parser.add_argument("--json", dest="as_json", action="store_true",
                        help="Output raw JSON instead of formatted card")
    args = parser.parse_args()

    source_status: dict[str, str] = {}

    # Source #1: atlas (always)
    record, maintainers, atlas_err = fetch_atlas(args.name)
    if record is None:
        print(f"ERROR: {atlas_err}", file=sys.stderr)
        if "atlas DB missing" in (atlas_err or ""):
            return 1
        return 2
    source_status["atlas (local SQLite)"] = "ok"
    source_status["atlas (local SQLite)_msg"] = "— fields populated from local DB"
    source_status["atlas: maintainers junction"] = "ok" if maintainers else "skip"
    source_status["atlas: maintainers junction_msg"] = (
        f"— {len(maintainers)} maintainer(s)" if maintainers else "— none in atlas"
    )

    # Source #2: build matrix (anaconda.org files API → repodata.json fallback)
    # Try the cheap per-package files API first. If it fails (air-gapped network
    # where api.anaconda.org is blocked), fall back to per-subdir
    # current_repodata.json from a conda channel mirror (prefix.dev / JFrog /
    # whatever the resolver chain points at).
    anaconda_files: list[dict[str, Any]] = []
    build_matrix_label = "anaconda.org"
    if record.get("conda_name"):
        t0 = time.monotonic()
        anaconda_files, anaconda_err = fetch_anaconda_files(record["conda_name"], args.subdir)
        if anaconda_err:
            source_status["anaconda.org files API"] = "fail"
            source_status["anaconda.org files API_msg"] = f"— {anaconda_err}"
            # Fall back to current_repodata.json via the _http URL chain.
            atlas_subdirs_raw = record.get("conda_subdirs") or "[]"
            try:
                atlas_subdirs = json.loads(atlas_subdirs_raw)
                if not isinstance(atlas_subdirs, list):
                    atlas_subdirs = []
            except (json.JSONDecodeError, TypeError):
                atlas_subdirs = []
            t1 = time.monotonic()
            anaconda_files, base_used, repodata_err = fetch_repodata_build_matrix(
                record["conda_name"], args.subdir, atlas_subdirs,
            )
            if repodata_err:
                source_status["conda-forge channel (repodata)"] = "fail"
                source_status["conda-forge channel (repodata)_msg"] = f"— {repodata_err}"
                source_status["anaconda"] = "fail"
            else:
                source_status["conda-forge channel (repodata)"] = "ok"
                source_status["conda-forge channel (repodata)_msg"] = (
                    f"— {len(anaconda_files)} subdir(s) in {time.monotonic() - t1:.1f}s "
                    f"via {base_used or '?'}"
                )
                source_status["anaconda"] = "ok"
                build_matrix_label = base_used or "conda channel mirror"
        else:
            source_status["anaconda.org files API"] = "ok"
            source_status["anaconda.org files API_msg"] = (
                f"— {len(anaconda_files)} subdir(s) in {time.monotonic() - t0:.1f}s"
            )
            source_status["anaconda"] = "ok"
    else:
        source_status["anaconda.org files API"] = "skip"
        source_status["anaconda.org files API_msg"] = "— skipped (no conda_name; PyPI-only row)"
    source_status["_build_matrix_label"] = build_matrix_label

    # Source #3: deep artifact metadata
    artifact_data: dict[str, Any] | None = None
    if args.deep:
        if anaconda_files:
            target = anaconda_files[0]
            sd = target["attrs"]["subdir"]
            bn = target["basename"]
            t0 = time.monotonic()
            artifact_data, artifact_err = fetch_artifact_data(sd, bn)
            if artifact_err:
                source_status["artifact"] = "fail"
                source_status["conda_forge_metadata.ArtifactData"] = "fail"
                source_status["conda_forge_metadata.ArtifactData_msg"] = f"— {artifact_err}"
                source_status["artifact_msg"] = artifact_err
            else:
                source_status["artifact"] = "ok"
                source_status["conda_forge_metadata.ArtifactData"] = "ok"
                source_status["conda_forge_metadata.ArtifactData_msg"] = (
                    f"— fetched {sd}/{bn.rsplit('/', 1)[-1]} in {time.monotonic() - t0:.1f}s"
                )
        else:
            source_status["artifact"] = "fail"
            source_status["conda_forge_metadata.ArtifactData"] = "fail"
            source_status["conda_forge_metadata.ArtifactData_msg"] = (
                "— skipped (depends on anaconda.org files API which failed)"
            )
            source_status["artifact_msg"] = "depends on anaconda.org which failed"
    else:
        source_status["conda_forge_metadata.ArtifactData"] = "skip"
        source_status["conda_forge_metadata.ArtifactData_msg"] = "— --deep not requested"

    # Source #4: vdb (--vdb)
    vdb_data: dict[str, Any] | None = None
    if args.vdb:
        t0 = time.monotonic()
        vdb_data, vdb_err = fetch_vdb_data(record, args.queried_version)
        if vdb_err:
            source_status["vdb (appthreat-vulnerability-db)"] = "fail"
            source_status["vdb (appthreat-vulnerability-db)_msg"] = f"— {vdb_err}"
        elif vdb_data is None:
            source_status["vdb (appthreat-vulnerability-db)"] = "skip"
            source_status["vdb (appthreat-vulnerability-db)_msg"] = "— no purls derivable"
        else:
            n_total = len(vdb_data.get("all_vulns", []))
            n_aff = len(vdb_data.get("affecting_latest_version", []))
            n_purls = len(vdb_data.get("purls", []))
            source_status["vdb (appthreat-vulnerability-db)"] = "ok"
            source_status["vdb (appthreat-vulnerability-db)_msg"] = (
                f"— {n_total} vuln(s) across {n_purls} purl(s), {n_aff} affecting current version "
                f"in {time.monotonic() - t0:.1f}s"
            )
            source_status["vdb"] = "ok"  # internal flag for renderer
    else:
        source_status["vdb (appthreat-vulnerability-db)"] = "skip"
        source_status["vdb (appthreat-vulnerability-db)_msg"] = "— --vdb not requested"

    if args.as_json:
        # Convert vdb objects to dicts for JSON serialization
        def _vuln_to_dict(v: Any) -> dict[str, Any]:
            return {a: getattr(v, a, None) for a in dir(v) if not a.startswith("_") and not callable(getattr(v, a, None))}
        vdb_serialized = None
        if vdb_data:
            vdb_serialized = {
                "purls": vdb_data["purls"],
                "by_severity": vdb_data["by_severity"],
                "kev_count": vdb_data["kev_count"],
                "all_vulns": [_vuln_to_dict(v) for v in vdb_data["all_vulns"]],
                "affecting_latest_version": [_vuln_to_dict(v) for v in vdb_data["affecting_latest_version"]],
            }
        print(json.dumps({
            "atlas": record,
            "maintainers": maintainers,
            "anaconda_files": anaconda_files,
            "artifact": artifact_data,
            "vdb": vdb_serialized,
            "source_status": {k: v for k, v in source_status.items() if not k.endswith("_msg")},
        }, indent=2, sort_keys=True, default=str))
    else:
        print(render(record, maintainers, anaconda_files, artifact_data, vdb_data,
                     source_status, args.files, args.vdb_all, args.vdb_deep,
                     args.queried_version))
    return 0


if __name__ == "__main__":
    sys.exit(main())
