#!/usr/bin/env python3
"""Inspect a conda/pixi env from multiple angles.

Resolution order for the env prefix:
  1. --prefix <path>                    (explicit)
  2. --environment <name>               (resolved via `pixi info --json`)
  3. $CONDA_PREFIX                      (active env)

Modes
-----
Default
    List root packages (graph in-degree 0 — nothing else depends on them).
    The apex of the conda-meta dependency graph after solve.

--audit
    Classify manifest explicits as pure-intent / transitively-covered /
    drifted. Requires a pixi env.

--freshness
    For each installed package within the chosen --scope, report whether
    your env-pinned version is behind conda-forge and whether conda-forge
    is behind PyPI. Joins cf_atlas data (offline, may be stale; emits a
    warning if so) with a live per-package PyPI JSON fetch (default ON;
    pass --no-live to skip). Bot / autotick state comes from atlas only.

--security
    CVE counts (KEV / Critical / High / total) affecting the installed
    version of each scoped package, sorted by severity.

--bus-factor
    Maintainer count per scoped package; explicit list of bus_factor=1
    packages (single-maintainer SPoFs).

--licenses
    SPDX rollup with non-permissive (GPL/AGPL/LGPL family) callout +
    unknown-license list + top-N license counts.

--sbom cyclonedx|spdx
    Emit a standard SBOM for the scoped env packages (JSON to stdout).

--diff OTHER_ENV
    Set + version diff between this env and OTHER_ENV (pixi env name).

Common flags
------------
    --scope roots|explicits|all
        Filter the inspected set. Default: roots (smallest, fastest).
        Applies to --freshness/--security/--bus-factor/--licenses/--sbom.
    --no-live
        Skip the live PyPI fetch in --freshness; use atlas data only.
    --workers N
        Concurrency for the PyPI fetch (default 8).
    --cache-ttl SECONDS
        Refresh on-disk PyPI cache when older (default 21600 = 6 h).
    --include REGEX / --exclude REGEX
        Filter the inspected set by name.
    --json
        Emit machine-readable JSON instead of text.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Repo-root helpers
_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCRIPT_DIR = Path(__file__).parent


def _import_http():
    """Lazy import of the _http helper. Returns the module or None."""
    if str(_SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPT_DIR))
    try:
        import _http  # type: ignore[import-not-found]
        return _http
    except Exception:  # noqa: BLE001
        return None

_ATLAS_DB = _REPO_ROOT / ".claude" / "data" / "conda-forge-expert" / "cf_atlas.db"
_CACHE_DIR = _REPO_ROOT / ".claude" / "data" / "conda-forge-expert" / "env_freshness_cache"
_PYPI_CACHE_FILE = _CACHE_DIR / "pypi_versions.json"
_ATLAS_STALE_DAYS = 7


# ---------- prefix / env resolution ----------

def resolve_prefix(args: argparse.Namespace) -> Path:
    if args.prefix:
        return Path(args.prefix).expanduser().resolve()
    if args.environment:
        cmd = ["pixi", "info", "--json"]
        if args.manifest_path:
            cmd += ["--manifest-path", args.manifest_path]
        try:
            info = json.loads(subprocess.check_output(cmd, text=True))
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise SystemExit(f"failed to run `pixi info --json`: {e}")
        for env in info.get("environments_info", []):
            if env["name"] == args.environment:
                return Path(env["prefix"])
        names = ", ".join(e["name"] for e in info.get("environments_info", []))
        raise SystemExit(f"env '{args.environment}' not found. available: {names}")
    prefix = os.environ.get("CONDA_PREFIX")
    if not prefix:
        raise SystemExit(
            "No env specified and CONDA_PREFIX is not set. "
            "Pass --prefix PATH, --environment NAME, or activate an env."
        )
    return Path(prefix)


def resolve_env_name(args: argparse.Namespace) -> str | None:
    return args.environment or os.environ.get("PIXI_ENVIRONMENT_NAME")


# ---------- conda-meta scan ----------

def scan_conda_meta(prefix: Path) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Return ({name: [direct deps]}, {name: version})."""
    conda_meta = prefix / "conda-meta"
    if not conda_meta.is_dir():
        raise SystemExit(f"No conda-meta directory at {conda_meta}")
    depends_of: dict[str, list[str]] = {}
    versions: dict[str, str] = {}
    for meta in conda_meta.glob("*.json"):
        rec = json.loads(meta.read_text())
        name = rec["name"]
        versions[name] = rec["version"]
        depends_of[name] = [d.split()[0] for d in rec.get("depends", [])]
    return depends_of, versions


def compute_roots_from(depends_of: dict[str, list[str]]) -> list[str]:
    all_pkgs = set(depends_of)
    depended_on = {dep for deps in depends_of.values() for dep in deps}
    return sorted(all_pkgs - depended_on)


# ---------- explicits via pixi ----------

def list_explicits(environment: str | None, manifest_path: str | None) -> dict[str, dict]:
    cmd = ["pixi", "list", "--explicit", "--json"]
    if environment:
        cmd += ["--environment", environment]
    if manifest_path:
        cmd += ["--manifest-path", manifest_path]
    try:
        records = json.loads(subprocess.check_output(cmd, text=True))
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise SystemExit(f"failed to run `pixi list --explicit --json`: {e}")
    return {
        rec["name"]: {
            "version": rec["version"],
            "requested_spec": rec.get("requested_spec", "*"),
        }
        for rec in records
    }


# ---------- atlas ----------

def load_atlas(names: set[str]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Return ({conda_name: atlas_row}, meta_info).

    meta_info has keys: available, built_at (unix), age_days, db_path.
    """
    meta: dict[str, Any] = {"available": False, "db_path": str(_ATLAS_DB)}
    if not _ATLAS_DB.exists():
        return {}, meta
    try:
        con = sqlite3.connect(f"file:{_ATLAS_DB}?mode=ro", uri=True)
    except sqlite3.Error as e:
        meta["error"] = str(e)
        return {}, meta

    cur = con.cursor()
    built_at_row = cur.execute(
        "SELECT value FROM meta WHERE key='built_at'"
    ).fetchone()
    built_at = int(built_at_row[0]) if built_at_row else 0
    meta.update(
        available=True,
        built_at=built_at,
        age_days=(time.time() - built_at) / 86400 if built_at else None,
    )

    cols = [
        "conda_name",
        "pypi_name",
        "latest_conda_version",
        "pypi_current_version",
        "pypi_current_version_yanked",
        "bot_open_pr_count",
        "bot_last_pr_state",
        "bot_last_pr_version",
        "feedstock_archived",
        "feedstock_name",
    ]
    rows: dict[str, dict[str, Any]] = {}
    if names:
        # Chunk to keep IN clause sane
        names_list = list(names)
        chunk = 500
        for i in range(0, len(names_list), chunk):
            slug = ",".join("?" for _ in names_list[i : i + chunk])
            q = f"SELECT {','.join(cols)} FROM packages WHERE conda_name IN ({slug})"
            for r in cur.execute(q, names_list[i : i + chunk]):
                rows[r[0]] = dict(zip(cols, r))
    con.close()
    return rows, meta


# ---------- atlas: vulns + maintainers + licenses ----------

def atlas_vulns_for(names_versions: list[tuple[str, str]]) -> dict[tuple[str, str], dict[str, Any]]:
    """Return {(name, version): vuln_row} via `package_version_vulns` join."""
    if not _ATLAS_DB.exists() or not names_versions:
        return {}
    con = sqlite3.connect(f"file:{_ATLAS_DB}?mode=ro", uri=True)
    out: dict[tuple[str, str], dict[str, Any]] = {}
    chunk = 200
    cols = ["conda_name", "version", "vuln_total",
            "vuln_critical_affecting_version", "vuln_high_affecting_version",
            "vuln_kev_affecting_version", "scanned_at"]
    for i in range(0, len(names_versions), chunk):
        batch = names_versions[i : i + chunk]
        slug = " OR ".join("(conda_name=? AND version=?)" for _ in batch)
        params: list[str] = [v for pair in batch for v in pair]
        q = f"SELECT {','.join(cols)} FROM package_version_vulns WHERE {slug}"
        for r in con.execute(q, params):
            out[(r[0], r[1])] = dict(zip(cols, r))
    con.close()
    return out


def atlas_maintainers_for(names: set[str]) -> dict[str, list[str]]:
    """Return {conda_name: [maintainer_handles]}."""
    if not _ATLAS_DB.exists() or not names:
        return {}
    con = sqlite3.connect(f"file:{_ATLAS_DB}?mode=ro", uri=True)
    out: dict[str, list[str]] = {n: [] for n in names}
    names_list = list(names)
    chunk = 500
    for i in range(0, len(names_list), chunk):
        slug = ",".join("?" for _ in names_list[i : i + chunk])
        q = (
            f"SELECT pm.conda_name, m.handle FROM package_maintainers pm "
            f"JOIN maintainers m ON m.id = pm.maintainer_id "
            f"WHERE pm.conda_name IN ({slug})"
        )
        for r in con.execute(q, names_list[i : i + chunk]):
            out.setdefault(r[0], []).append(r[1])
    con.close()
    return out


def atlas_licenses_for(names: set[str]) -> dict[str, dict[str, str | None]]:
    """Return {conda_name: {conda_license, conda_license_family}} from atlas."""
    if not _ATLAS_DB.exists() or not names:
        return {}
    con = sqlite3.connect(f"file:{_ATLAS_DB}?mode=ro", uri=True)
    out: dict[str, dict[str, str | None]] = {}
    names_list = list(names)
    chunk = 500
    for i in range(0, len(names_list), chunk):
        slug = ",".join("?" for _ in names_list[i : i + chunk])
        q = f"SELECT conda_name, conda_license, conda_license_family FROM packages WHERE conda_name IN ({slug})"
        for r in con.execute(q, names_list[i : i + chunk]):
            out[r[0]] = {"conda_license": r[1], "conda_license_family": r[2]}
    con.close()
    return out


# ---------- pypi cache ----------

def cache_load() -> dict[str, dict[str, Any]]:
    if not _PYPI_CACHE_FILE.exists():
        return {}
    try:
        return json.loads(_PYPI_CACHE_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def cache_save(data: dict[str, dict[str, Any]]) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _PYPI_CACHE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    tmp.replace(_PYPI_CACHE_FILE)


def fetch_pypi_version(pypi_name: str, timeout: int = 5) -> tuple[str | None, str | None]:
    """Return (version, error). Uses _http with JFrog/truststore fallbacks."""
    http = _import_http()
    if http is None:
        return None, "_http helper not importable"
    urls = http.resolve_pypi_json_urls(pypi_name)
    try:
        data, _ = http.fetch_with_fallback(urls, timeout=timeout, decode_json=True)
    except Exception as e:  # noqa: BLE001
        return None, type(e).__name__
    if not isinstance(data, dict):
        return None, "non-json response"
    info = data.get("info") or {}
    v = info.get("version")
    return (v if isinstance(v, str) else None), None


def live_pypi_lookups(
    pypi_names: list[str],
    workers: int,
    cache: dict[str, dict[str, Any]],
    cache_ttl_s: int,
) -> None:
    """Populate cache in-place. Skips entries fresher than cache_ttl_s."""
    now = time.time()
    todo = [n for n in pypi_names if not (
        n in cache and (now - cache[n].get("fetched_at", 0)) < cache_ttl_s
    )]
    if not todo:
        return
    http = _import_http()
    if http is not None:
        http.inject_ssl_truststore()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(fetch_pypi_version, n): n for n in todo}
        for fut in concurrent.futures.as_completed(futures):
            n = futures[fut]
            v, err = fut.result()
            cache[n] = {"version": v, "error": err, "fetched_at": now}


# ---------- classification ----------

def version_lt(a: str, b: str) -> bool:
    """a < b under packaging.Version, falling back to string compare."""
    if not a or not b or a == b:
        return False
    try:
        from packaging.version import Version
        return Version(a) < Version(b)
    except Exception:  # noqa: BLE001
        return a < b


def classify(
    env_v: str,
    cf_v: str | None,
    pypi_v: str | None,
    bot_pr_count: int | None,
    bot_pr_state: str | None,
    bot_pr_version: str | None,
    archived: int | None,
    has_atlas: bool,
    has_pypi_name: bool,
) -> str:
    """Pick the most informative status for one row.

    Rules (first match wins):
      - atlas missing entirely         -> no_atlas_row
      - feedstock archived             -> feedstock_archived
      - env < cf  (regardless of pypi) -> env_behind_cf
      - pypi-mapped and cf < pypi      -> cf_behind_pypi_{pr_open|stale_pr|no_pr}
      - no pypi name and env == cf     -> in_sync (non-Python pkg, atlas current)
      - no pypi name and env > cf      -> in_sync (atlas stale for this row)
      - has pypi name and env > cf and env == pypi -> in_sync (atlas stale)
      - has pypi name and env == cf == pypi -> in_sync
      - fallback                       -> in_sync
    """
    if not has_atlas:
        return "no_atlas_row"
    if archived:
        return "feedstock_archived"
    if cf_v and env_v and version_lt(env_v, cf_v):
        return "env_behind_cf"
    if has_pypi_name and cf_v and pypi_v and version_lt(cf_v, pypi_v):
        if bot_pr_count and bot_pr_count > 0:
            return "cf_behind_pypi_pr_open"
        if bot_pr_version and bot_pr_version == pypi_v and bot_pr_state in {"closed", "merged"}:
            return "in_sync"  # PR merged; cf reindex pending
        if bot_pr_state == "closed" and bot_pr_version and version_lt(bot_pr_version, pypi_v):
            return "cf_behind_pypi_stale_pr"
        return "cf_behind_pypi_no_pr"
    return "in_sync"


# ---------- scope ----------

def apply_scope(
    scope: str,
    all_pkgs: set[str],
    roots: set[str],
    explicits: set[str],
) -> set[str]:
    if scope == "roots":
        return set(roots)
    if scope == "explicits":
        return set(explicits)
    if scope == "all":
        return set(all_pkgs)
    raise SystemExit(f"unknown scope: {scope}")


# ---------- renderers ----------

STATUS_ORDER = [
    "cf_behind_pypi_no_pr",
    "cf_behind_pypi_stale_pr",
    "cf_behind_pypi_pr_open",
    "env_behind_cf",
    "feedstock_archived",
    "no_atlas_row",
    "in_sync",
]

STATUS_LABEL = {
    "cf_behind_pypi_no_pr":   "conda-forge BEHIND pypi, no PR — feedstock action needed",
    "cf_behind_pypi_stale_pr":"conda-forge BEHIND pypi, PR closed but cf still old — stuck",
    "cf_behind_pypi_pr_open": "conda-forge BEHIND pypi, autotick PR open — wait",
    "env_behind_cf":          "env BEHIND conda-forge — re-lock to upgrade",
    "feedstock_archived":     "feedstock ARCHIVED — terminal; no future cf updates",
    "no_atlas_row":           "not in atlas (off-channel, local build, or new package)",
    "in_sync":                "in sync (no action needed)",
}


def render_freshness_text(
    rows: list[dict[str, Any]],
    atlas_meta: dict[str, Any],
    live: bool,
    scope: str,
    label: str,
) -> None:
    print(f"Freshness audit for env '{label}' (scope: {scope}, {len(rows)} packages):\n")

    # Header warnings
    if not atlas_meta.get("available"):
        print(f"⚠  atlas DB not available at {atlas_meta['db_path']} — name mapping, bot/PR state, and feedstock-archived status are unknown.\n")
    else:
        age = atlas_meta.get("age_days") or 0
        if age > _ATLAS_STALE_DAYS:
            print(f"⚠  atlas DB is {age:.1f} days old (threshold: {_ATLAS_STALE_DAYS} d) — `pixi run -e local-recipes build-cf-atlas` to refresh.\n")
    if not live:
        print("⚠  --no-live: PyPI versions are from atlas (subject to atlas staleness).\n")

    by_status: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_status.setdefault(r["status"], []).append(r)

    summary = ", ".join(
        f"{len(by_status[s])} {s}" for s in STATUS_ORDER if s in by_status
    )
    print(f"Summary: {summary}\n")

    for status in STATUS_ORDER:
        items = by_status.get(status)
        if not items:
            continue
        print(f"── {STATUS_LABEL[status]} ({len(items)}) ──")
        if status == "in_sync":
            print(f"   ({len(items)} packages omitted — pass --verbose to list)")
            print()
            continue
        for r in sorted(items, key=lambda x: x["name"]):
            extra = []
            if r.get("bot_pr_version"):
                extra.append(f"pr_version={r['bot_pr_version']} state={r.get('bot_pr_state')}")
            extra_s = "  " + ", ".join(extra) if extra else ""
            print(
                f"   {r['name']:<32} env={r['env_version']:<14} cf={r['cf_version'] or '-':<14} pypi={r['pypi_version'] or '-':<14}{extra_s}"
            )
        print()


def render_freshness_verbose_in_sync(rows: list[dict[str, Any]]) -> None:
    items = [r for r in rows if r["status"] == "in_sync"]
    if not items:
        return
    print(f"── in sync ({len(items)}) ──")
    for r in sorted(items, key=lambda x: x["name"]):
        print(f"   {r['name']:<32} {r['env_version']}")


# ---------- main ----------

# ---------- mode handlers (security / bus-factor / licenses / sbom / diff) ----------

# License classification: SPDX-style identifiers that conda-forge typically
# considers "non-permissive" (copyleft) or that require special attention.
_NON_PERMISSIVE_FAMILIES = {"GPL", "AGPL", "LGPL", "GPL2", "GPL3", "AGPL3"}
_NON_PERMISSIVE_IDS = {
    "GPL-2.0-only", "GPL-2.0-or-later", "GPL-3.0-only", "GPL-3.0-or-later",
    "AGPL-3.0-only", "AGPL-3.0-or-later", "LGPL-2.1-only", "LGPL-2.1-or-later",
    "LGPL-3.0-only", "LGPL-3.0-or-later", "GPL", "AGPL", "LGPL",
}


def _classify_license(lic: str | None, fam: str | None) -> str:
    if not lic:
        return "unknown"
    if (fam or "").upper().split("(")[0].strip() in _NON_PERMISSIVE_FAMILIES:
        return "non_permissive"
    if any(tok in lic for tok in _NON_PERMISSIVE_IDS):
        return "non_permissive"
    return "permissive"


def run_security(args, prefix: Path, versions: dict[str, str], scoped: set[str], label: str) -> int:
    name_ver = [(n, versions[n]) for n in sorted(scoped)]
    vulns = atlas_vulns_for(name_ver)
    _, atlas_meta = load_atlas(set())  # just for meta/age

    rows: list[dict[str, Any]] = []
    for n in sorted(scoped):
        row = vulns.get((n, versions[n]))
        if row and row.get("vuln_total"):
            rows.append({
                "name": n,
                "version": versions[n],
                "vuln_total": row["vuln_total"],
                "critical": row["vuln_critical_affecting_version"],
                "high": row["vuln_high_affecting_version"],
                "kev": row["vuln_kev_affecting_version"],
                "scanned_at": row["scanned_at"],
            })

    rows.sort(key=lambda r: (-(r["kev"] or 0), -(r["critical"] or 0), -(r["high"] or 0), -(r["vuln_total"] or 0), r["name"]))

    summary = {
        "scanned_packages": len(scoped),
        "vulnerable_packages": len(rows),
        "kev_total": sum(r["kev"] or 0 for r in rows),
        "critical_total": sum(r["critical"] or 0 for r in rows),
        "high_total": sum(r["high"] or 0 for r in rows),
        "vuln_total": sum(r["vuln_total"] or 0 for r in rows),
    }

    if args.json:
        print(json.dumps({
            "prefix": str(prefix), "environment": label, "scope": args.scope,
            "atlas": atlas_meta, "summary": summary, "rows": rows,
        }, indent=2))
        return 0

    print(f"Security audit for env '{label}' (scope: {args.scope}, {len(scoped)} packages scanned):\n")
    if not atlas_meta.get("available"):
        print(f"⚠  atlas DB not available at {atlas_meta['db_path']} — no CVE data.\n")
    elif (atlas_meta.get("age_days") or 0) > _ATLAS_STALE_DAYS:
        print(f"⚠  atlas DB is {atlas_meta['age_days']:.1f} days old (threshold: {_ATLAS_STALE_DAYS} d) — CVE coverage may be stale.\n")
    print(f"Summary: {summary['vulnerable_packages']} vulnerable, "
          f"{summary['kev_total']} KEV, {summary['critical_total']} Critical, "
          f"{summary['high_total']} High, {summary['vuln_total']} total CVE-version hits.\n")

    if not rows:
        print("✓ No CVEs affecting the installed versions in this scope.")
        return 0

    print(f"{'PACKAGE':<32} {'VERSION':<14} {'KEV':>4} {'CRIT':>4} {'HIGH':>4} {'TOTAL':>5}")
    for r in rows:
        print(f"  {r['name']:<30} {r['version']:<14} {r['kev'] or 0:>4} {r['critical'] or 0:>4} {r['high'] or 0:>4} {r['vuln_total'] or 0:>5}")
    return 0


def run_bus_factor(args, prefix: Path, versions: dict[str, str], scoped: set[str], label: str) -> int:
    maint = atlas_maintainers_for(scoped)
    _, atlas_meta = load_atlas(set())

    rows: list[dict[str, Any]] = []
    for n in sorted(scoped):
        handles = maint.get(n, [])
        rows.append({
            "name": n, "version": versions[n],
            "maintainer_count": len(handles), "maintainers": handles,
        })

    by_count: dict[int, list[dict[str, Any]]] = {}
    for r in rows:
        by_count.setdefault(r["maintainer_count"], []).append(r)

    if args.json:
        print(json.dumps({
            "prefix": str(prefix), "environment": label, "scope": args.scope,
            "atlas": atlas_meta,
            "summary": {str(k): len(v) for k, v in sorted(by_count.items())},
            "rows": rows,
        }, indent=2))
        return 0

    print(f"Bus-factor audit for env '{label}' (scope: {args.scope}, {len(scoped)} packages):\n")
    if not atlas_meta.get("available"):
        print(f"⚠  atlas DB not available — no maintainer data.\n")
    print(f"Distribution: " + ", ".join(
        f"{c} package{'s' if len(items) != 1 else ''} with bus_factor={c}" if c == 0
        else f"{len(items)} pkgs with {c} maintainer{'s' if c != 1 else ''}"
        for c, items in sorted(by_count.items())
    ) + "\n")

    bf1 = by_count.get(1, [])
    bf0 = by_count.get(0, [])
    if bf1:
        print(f"── bus_factor = 1 (single maintainer; SPoF risk) ({len(bf1)}) ──")
        for r in sorted(bf1, key=lambda x: x["name"]):
            print(f"   {r['name']:<32} {r['version']:<14} maintainer: {r['maintainers'][0]}")
        print()
    if bf0:
        print(f"── bus_factor = 0 (no maintainer in atlas; off-channel, archived, or unmapped) ({len(bf0)}) ──")
        for r in sorted(bf0, key=lambda x: x["name"])[:20]:
            print(f"   {r['name']:<32} {r['version']}")
        if len(bf0) > 20:
            print(f"   ... ({len(bf0) - 20} more — pass --verbose for full list or --json for all)")
        print()
    return 0


def run_licenses(args, prefix: Path, versions: dict[str, str], scoped: set[str], label: str) -> int:
    lic = atlas_licenses_for(scoped)
    _, atlas_meta = load_atlas(set())

    rows: list[dict[str, Any]] = []
    for n in sorted(scoped):
        info = lic.get(n) or {}
        c_lic = info.get("conda_license")
        c_fam = info.get("conda_license_family")
        rows.append({
            "name": n, "version": versions[n],
            "license": c_lic, "license_family": c_fam,
            "class": _classify_license(c_lic, c_fam),
        })

    by_license: dict[str, int] = {}
    for r in rows:
        key = r["license"] or "(unknown)"
        by_license[key] = by_license.get(key, 0) + 1

    by_class: dict[str, list[dict[str, Any]]] = {"non_permissive": [], "unknown": [], "permissive": []}
    for r in rows:
        by_class[r["class"]].append(r)

    if args.json:
        print(json.dumps({
            "prefix": str(prefix), "environment": label, "scope": args.scope,
            "atlas": atlas_meta,
            "summary": {
                "by_class": {k: len(v) for k, v in by_class.items()},
                "by_license": dict(sorted(by_license.items(), key=lambda kv: -kv[1])),
            },
            "rows": rows,
        }, indent=2))
        return 0

    print(f"License inventory for env '{label}' (scope: {args.scope}, {len(scoped)} packages):\n")
    print(f"Summary: {len(by_class['non_permissive'])} non-permissive, "
          f"{len(by_class['unknown'])} unknown, {len(by_class['permissive'])} permissive.\n")

    if by_class["non_permissive"]:
        print(f"── Non-permissive / copyleft ({len(by_class['non_permissive'])}) ──")
        for r in sorted(by_class["non_permissive"], key=lambda x: x["name"]):
            print(f"   {r['name']:<32} {r['version']:<14} {r['license']}")
        print()

    if by_class["unknown"]:
        print(f"── Unknown / missing license ({len(by_class['unknown'])}) ──")
        for r in sorted(by_class["unknown"], key=lambda x: x["name"])[:15]:
            print(f"   {r['name']:<32} {r['version']}")
        if len(by_class["unknown"]) > 15:
            print(f"   ... ({len(by_class['unknown']) - 15} more — use --json for full list)")
        print()

    print(f"── Top licenses by package count ──")
    for lic_id, count in sorted(by_license.items(), key=lambda kv: -kv[1])[:15]:
        print(f"   {lic_id:<40} {count}")
    return 0


def run_sbom(args, prefix: Path, versions: dict[str, str], scoped: set[str], label: str) -> int:
    """Emit a CycloneDX or SPDX SBOM for the scoped env packages."""
    sys.path.insert(0, str(_SCRIPT_DIR))
    try:
        from _sbom import emit_cyclonedx, emit_spdx  # type: ignore[import-not-found]
    except Exception as e:  # noqa: BLE001
        raise SystemExit(f"_sbom helper not importable: {e}")
    try:
        from scan_project import Dep  # type: ignore[import-not-found]
    except Exception as e:  # noqa: BLE001
        raise SystemExit(f"scan_project helper not importable: {e}")

    atlas_rows, _ = load_atlas(scoped)
    # Build Dep list. ecosystem=conda; manifest=conda-meta record path
    deps: list[Any] = []
    atlas_records: dict[str, dict[str, Any]] = {}
    for n in sorted(scoped):
        deps.append(Dep(
            name=n, version=versions[n], ecosystem="conda",
            manifest=f"conda-meta/{n}-{versions[n]}.json",
        ))
        if n in atlas_rows:
            atlas_records[f"conda:{n}"] = {
                "conda_license": (atlas_licenses_for({n}).get(n) or {}).get("conda_license"),
            }

    emitter = emit_cyclonedx if args.sbom == "cyclonedx" else emit_spdx
    bom = emitter(deps, vulns_by_dep={}, project_name=f"env-{label}", atlas_records=atlas_records)
    print(json.dumps(bom, indent=2))
    return 0


def run_diff(args, prefix: Path, versions: dict[str, str], label: str) -> int:
    """Diff two envs by package set and versions."""
    # Resolve the other env's prefix via pixi info
    cmd = ["pixi", "info", "--json"]
    if args.manifest_path:
        cmd += ["--manifest-path", args.manifest_path]
    try:
        info = json.loads(subprocess.check_output(cmd, text=True))
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise SystemExit(f"failed to run `pixi info --json`: {e}")

    other_prefix = None
    for env in info.get("environments_info", []):
        if env["name"] == args.diff:
            other_prefix = Path(env["prefix"])
            break
    if other_prefix is None:
        names = ", ".join(e["name"] for e in info.get("environments_info", []))
        raise SystemExit(f"env '{args.diff}' not found. available: {names}")

    _, other_versions = scan_conda_meta(other_prefix)

    a, b = set(versions), set(other_versions)
    only_a = sorted(a - b)
    only_b = sorted(b - a)
    common = a & b
    version_diff = sorted(n for n in common if versions[n] != other_versions[n])

    if args.json:
        print(json.dumps({
            "env_a": label, "env_b": args.diff,
            "prefix_a": str(prefix), "prefix_b": str(other_prefix),
            "summary": {
                "only_in_a": len(only_a),
                "only_in_b": len(only_b),
                "version_diff": len(version_diff),
                "in_sync": len(common) - len(version_diff),
            },
            "only_in_a": [{"name": n, "version": versions[n]} for n in only_a],
            "only_in_b": [{"name": n, "version": other_versions[n]} for n in only_b],
            "version_diff": [
                {"name": n, "version_a": versions[n], "version_b": other_versions[n]}
                for n in version_diff
            ],
        }, indent=2))
        return 0

    print(f"Env diff: '{label}' vs '{args.diff}'\n")
    print(f"Summary: {len(only_a)} only in '{label}', {len(only_b)} only in '{args.diff}', "
          f"{len(version_diff)} version-different, {len(common) - len(version_diff)} in sync.\n")

    if only_a:
        print(f"── Only in '{label}' ({len(only_a)}) ──")
        for n in only_a:
            print(f"   {n:<40} {versions[n]}")
        print()
    if only_b:
        print(f"── Only in '{args.diff}' ({len(only_b)}) ──")
        for n in only_b:
            print(f"   {n:<40} {other_versions[n]}")
        print()
    if version_diff:
        print(f"── Different versions ({len(version_diff)}) ──")
        for n in version_diff:
            print(f"   {n:<32} a={versions[n]:<14} b={other_versions[n]}")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="env-inspect",
        description="Inspect a conda/pixi env: roots, manifest audit, freshness, security, bus-factor, licenses, SBOM, env-diff.",
    )
    p.add_argument("--prefix", help="Explicit conda prefix (overrides --environment and $CONDA_PREFIX)")
    p.add_argument("-e", "--environment", help="Pixi environment name (resolved via `pixi info --json`)")
    p.add_argument("--manifest-path", help="Path to pixi.toml / pyproject.toml or workspace dir")
    p.add_argument("--audit", action="store_true",
                   help="Classify manifest explicits as pure-intent / transitively-covered / drifted (requires pixi env)")
    p.add_argument("--freshness", action="store_true",
                   help="Compare env vs conda-forge vs PyPI versions (live PyPI fetch by default)")
    p.add_argument("--security", action="store_true",
                   help="Report CVEs affecting installed versions (from atlas)")
    p.add_argument("--bus-factor", action="store_true",
                   help="Report maintainer count per package; flag bus_factor=1 packages")
    p.add_argument("--licenses", action="store_true",
                   help="Aggregate SPDX licenses across env; flag non-permissive / unknown")
    p.add_argument("--sbom", choices=("cyclonedx", "spdx"),
                   help="Emit a CycloneDX or SPDX SBOM for the env (JSON to stdout)")
    p.add_argument("--diff", metavar="OTHER_ENV",
                   help="Diff this env against OTHER_ENV (pixi env name)")
    p.add_argument("--scope", choices=("roots", "explicits", "all"), default="roots",
                   help="Which subset of installed packages to inspect for --freshness/--security/--bus-factor/--licenses (default: roots)")
    p.add_argument("--no-live", action="store_true", help="Skip live PyPI fetch; use atlas data only")
    p.add_argument("--workers", type=int, default=8, help="Parallel PyPI fetch workers (default 8)")
    p.add_argument("--cache-ttl", type=int, default=21600, help="PyPI cache TTL in seconds (default 21600 = 6 h)")
    p.add_argument("--include", help="Filter scope to names matching this regex")
    p.add_argument("--exclude", help="Drop names matching this regex from the scope")
    p.add_argument("--verbose", action="store_true", help="List in-sync packages (otherwise collapsed)")
    p.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    prefix = resolve_prefix(args)
    depends_of, versions = scan_conda_meta(prefix)
    roots = compute_roots_from(depends_of)
    label = args.environment or os.environ.get("PIXI_ENVIRONMENT_NAME") or prefix.name

    # ----- diff mode (handle first; doesn't use scope) -----
    if args.diff:
        return run_diff(args, prefix, versions, label)

    # ----- default mode (roots only) -----
    if (not args.audit and not args.freshness and not args.security
            and not args.bus_factor and not args.licenses and not args.sbom):
        if args.json:
            print(json.dumps({
                "prefix": str(prefix),
                "count": len(roots),
                "roots": [{"name": n, "version": versions[n]} for n in roots],
            }, indent=2))
            return 0
        print(f"{len(roots)} root packages in env '{label}' (nothing else in the env depends on them):\n")
        for n in roots:
            print(f"  {n:<40} {versions[n]}")
        return 0

    # ----- audit mode -----
    if args.audit:
        env_name = resolve_env_name(args)
        if not env_name:
            raise SystemExit("--audit requires a pixi env. Pass --environment NAME or run inside `pixi run -e <env>`.")
        explicits = list_explicits(env_name, args.manifest_path)
        roots_set = set(roots)
        explicits_set = set(explicits)
        pure = sorted(roots_set & explicits_set)
        covered = sorted(explicits_set - roots_set)
        drifted = sorted(roots_set - explicits_set)
        if args.json:
            print(json.dumps({
                "prefix": str(prefix),
                "environment": env_name,
                "summary": {
                    "roots": len(roots),
                    "explicits": len(explicits),
                    "pure_intent": len(pure),
                    "transitively_covered": len(covered),
                    "drifted_roots": len(drifted),
                },
                "pure_intent": [{"name": n, "version": versions[n], "requested_spec": explicits[n]["requested_spec"]} for n in pure],
                "transitively_covered": [{"name": n, "version": versions[n], "requested_spec": explicits[n]["requested_spec"]} for n in covered],
                "drifted_roots": [{"name": n, "version": versions[n]} for n in drifted],
            }, indent=2))
            return 0
        print(f"Manifest audit for env '{label}':\n")
        for title, items, descr in (
            ("Pure intent (declared & still a root)", pure, None),
            ("Transitively-covered explicits (declared but also pulled in by another explicit)", covered, "Candidates to drop from pixi.toml — verify your pin is no tighter than the transitive one."),
            ("Drifted roots (a root but NOT declared in the manifest)", drifted, None),
        ):
            print(f"{title} — {len(items)} packages:")
            if descr:
                print(f"  {descr}")
            if not items:
                if title.startswith("Drifted"):
                    print("  (none — env is consistent with the manifest)")
                else:
                    print("  (none)")
            for n in items:
                if title.startswith("Drifted"):
                    print(f"  {n:<40} {versions[n]}")
                else:
                    spec = explicits[n]["requested_spec"]
                    print(f"  {n:<40} {versions[n]:<20} (spec: {spec})")
            print()
        return 0

    # ----- compute scoped set (shared by freshness / security / bus-factor / licenses / sbom) -----
    explicits: dict[str, dict] = {}
    if args.scope == "explicits":
        env_name = resolve_env_name(args)
        if not env_name:
            raise SystemExit("--scope explicits requires a pixi env. Pass --environment NAME or run inside `pixi run -e <env>`.")
        explicits = list_explicits(env_name, args.manifest_path)

    all_pkgs = set(versions)
    scoped = apply_scope(args.scope, all_pkgs, set(roots), set(explicits))

    if args.include:
        rx = re.compile(args.include)
        scoped = {n for n in scoped if rx.search(n)}
    if args.exclude:
        rx = re.compile(args.exclude)
        scoped = {n for n in scoped if not rx.search(n)}

    # ----- security mode -----
    if args.security:
        return run_security(args, prefix, versions, scoped, label)

    # ----- bus-factor mode -----
    if args.bus_factor:
        return run_bus_factor(args, prefix, versions, scoped, label)

    # ----- licenses mode -----
    if args.licenses:
        return run_licenses(args, prefix, versions, scoped, label)

    # ----- sbom mode -----
    if args.sbom:
        return run_sbom(args, prefix, versions, scoped, label)

    # ----- freshness mode -----
    atlas_rows, atlas_meta = load_atlas(scoped)

    # Build list of (conda_name -> pypi_name) for live fetch
    pypi_names = sorted({
        atlas_rows[n]["pypi_name"]
        for n in scoped
        if n in atlas_rows and atlas_rows[n].get("pypi_name")
    })

    live = not args.no_live
    cache = cache_load()
    if live:
        live_pypi_lookups(pypi_names, args.workers, cache, args.cache_ttl)
        cache_save(cache)

    rows: list[dict[str, Any]] = []
    for n in sorted(scoped):
        atlas = atlas_rows.get(n) or {}
        pypi_name = atlas.get("pypi_name")
        cf_v = atlas.get("latest_conda_version")
        # Pick live pypi if available, else atlas pypi_current_version
        pypi_v = None
        if pypi_name and live and pypi_name in cache:
            pypi_v = cache[pypi_name].get("version")
        if pypi_v is None:
            pypi_v = atlas.get("pypi_current_version")
        status = classify(
            env_v=versions[n],
            cf_v=cf_v,
            pypi_v=pypi_v,
            bot_pr_count=atlas.get("bot_open_pr_count"),
            bot_pr_state=atlas.get("bot_last_pr_state"),
            bot_pr_version=atlas.get("bot_last_pr_version"),
            archived=atlas.get("feedstock_archived"),
            has_atlas=bool(atlas),
            has_pypi_name=bool(pypi_name),
        )
        rows.append({
            "name": n,
            "env_version": versions[n],
            "cf_version": cf_v,
            "pypi_version": pypi_v,
            "pypi_name": pypi_name,
            "bot_pr_count": atlas.get("bot_open_pr_count"),
            "bot_pr_state": atlas.get("bot_last_pr_state"),
            "bot_pr_version": atlas.get("bot_last_pr_version"),
            "feedstock_archived": bool(atlas.get("feedstock_archived")),
            "status": status,
        })

    if args.json:
        print(json.dumps({
            "prefix": str(prefix),
            "environment": label,
            "scope": args.scope,
            "live_pypi": live,
            "atlas": atlas_meta,
            "summary": {s: sum(1 for r in rows if r["status"] == s) for s in STATUS_ORDER},
            "rows": rows,
        }, indent=2))
        return 0

    render_freshness_text(rows, atlas_meta, live, args.scope, label)
    if args.verbose:
        render_freshness_verbose_in_sync(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
