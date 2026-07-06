#!/usr/bin/env python3
"""
inventory-match — user-inventory gap / version-lag matcher against the
conda-forge atlas (cyclonedx-universe-inventory Wave C / S5).

Reads a user inventory (manifests, lock files, SBOMs, `pip list` /
`conda list` text — all via `scan_project`'s shared parsers, S5a), resolves
every dep to a conda-forge package (mapping → inverse-G10 bare fold → the
decision-4 LIVE channeldata cross-check of every would-be-missing row,
implemented in the local wave; --offline/--no-live-cf revert to atlas-only),
then buckets each row on the three-way version comparison (decision 3:
inventory-pinned vs cf-latest vs upstream-of-record):

  ADD              Python, not on conda-forge (readiness/template attached)
  ADD-NONPYPI      non-Python ecosystem, not on conda-forge
  UPDATE-FEEDSTOCK conda-forge behind upstream (lag in releases/days where
                   `upstream_versions_history` allows)
  UPDATE-PIN       inventory pin behind conda-forge
  CURRENT          nothing to do
  UNKNOWN          not decidable (no cf version, name absent everywhere, …).
                   A matched package with no `upstream_versions` row still
                   buckets on the inv-vs-cf comparison where decidable and
                   carries `signals_absent: upstream_freshness` (the spec's
                   "UNKNOWN-leaning" soft reading — see § Risks).

Every row carries `match_confidence` verbatim from the mapping tier
(`unattributed`/`name_coincidence` rows are NEVER presented as verified) and
a `version_comparison` reliability flag (packaging-parse → reliable;
string-inequality fallback → unreliable).

Freshness policy check (Python Dependency Policy defaults, dated 2026-07-05,
overridable via --policy): per pinned dep, the ELIGIBLE version set comes
from an injectable provider — the DEFAULT (local wave) is the live PyPI
provider (pypi.org JSON per pypi-mapped package, yanked + requires-python
filtered, history fallback); --offline reverts to the
`upstream_versions_history` provider. Dense history (≥ 10 eligible) → pin
must sit in the top 20th percentile; sparse → last eligible − 1 suffices.

Policy gate (CI): --policy <json|toml> + deterministic exit codes —
0 = pass, 2 = policy violations, 1 = error (incl. usage errors — exit 2 is
RESERVED for the policy verdict). Missing data blocks when the policy says
so (`block_on_missing_data`, default true whenever a freshness threshold
is set); malformed/unknown policy keys are themselves a violation
(fail-closed — a typo'd gate must not silently pass). --weights <csv|json>
attaches the user-estate criticality multiplier per package (conda-forge
blast radius is not the user's blast radius).

Transitive resolution of bare manifests (policy § 3, local wave): direct
rows resolve via pip's `--dry-run --report` (PyPI track) / a py-rattler
conda-forge solve (conda track) and upgrade to `resolution: resolved`
(+ depth/fan-out for S7); resolver-discovered packages join as
`via: transitive` rows. `locked` rows are used as-given. Resolver failure
warns and leaves rows `direct` (--no-resolve/--offline skip deliberately).

Freshness contract (decision 6): refuses an atlas older than 14 days or
with no parseable built_at (--allow-stale overrides).

Live-env intake: --conda-env / --venv read installed metadata offline via
scan_project's existing walkers. Container-image intake stays via
scan-project (`scan-project --image ... --sbom cyclonedx` → --sbom-in);
verified end-to-end in the Wave C local gates.

CLI:
  inventory-match [INPUT ...] [--format FMT] [--sbom-in BOM]
                  [--conda-env DIR] [--venv DIR]
                  [--policy FILE] [--weights FILE]
                  [--report PATH] [--json] [--sbom-out PATH]
                  [--allow-stale] [--offline] [--no-resolve]
                  [--no-live-cf] [--python-version X.Y]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import functools
import json
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Callable

from export_purls import CHANNEL_QUALIFIER, RECIPES_DIR, fold_name
from universe_sbom import StaleAtlasError, check_freshness
import scan_project as sp


def _get_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent / "data" / "conda-forge-expert"


DB_PATH = _get_data_dir() / "cf_atlas.db"
DEFAULT_REPORT_PATH = _get_data_dir() / "inventory-match-report.md"

BUCKETS = ("ADD", "ADD-NONPYPI", "UPDATE-FEEDSTOCK", "UPDATE-PIN",
           "CURRENT", "UNKNOWN")

# Upstream-of-record preference: pypi first (registry of record for the
# python track), then the Wave B order (github dominates the tracker).
_UPSTREAM_SOURCE_ORDER = ("pypi", "github", "npm", "crates", "rubygems",
                          "maven", "gitlab", "codeberg")

# Python Dependency Policy freshness defaults (dated 2026-07-05).
FRESHNESS_DENSE_N = 10
FRESHNESS_TOP_PCT = 0.20


# ── input intake ─────────────────────────────────────────────────────────────

FORMAT_PARSERS: dict[str, Callable[[Path], list[Any]]] = {
    "pip": sp.parse_pip_text,
    "conda-list": sp.parse_conda_list_text,
    "requirements": sp.parse_requirements_txt,
    "pyproject": sp.parse_pyproject_toml,
    "environment-yml": sp.parse_environment_yml,
    "pixi-lock": sp.parse_pixi_lock,
    "pixi-toml": sp.parse_pixi_toml,
    "conda-lock": sp.parse_conda_lock,
    "uv-lock": sp.parse_uv_lock,
    "poetry-lock": sp.parse_poetry_lock,
    "pdm-lock": sp.parse_pdm_lock,
    "pylock": sp.parse_pylock_toml,
    "pipfile": sp.parse_pipfile,
    "pipfile-lock": sp.parse_pipfile_lock,
    "meta-yaml": sp.parse_meta_yaml,
    "recipe-yaml": sp.parse_recipe_yaml,
    "cyclonedx": sp.parse_sbom_cyclonedx,
    "spdx": sp.parse_sbom_spdx,
}

_FILENAME_FORMATS: dict[str, str] = {
    "requirements.txt": "requirements",
    "requirements.in": "requirements",
    "pyproject.toml": "pyproject",
    "environment.yml": "environment-yml",
    "environment.yaml": "environment-yml",
    "pixi.lock": "pixi-lock",
    "pixi.toml": "pixi-toml",
    "conda-lock.yml": "conda-lock",
    "conda-lock.yaml": "conda-lock",
    "uv.lock": "uv-lock",
    "poetry.lock": "poetry-lock",
    "pdm.lock": "pdm-lock",
    "pylock.toml": "pylock",
    "Pipfile": "pipfile",
    "Pipfile.lock": "pipfile-lock",
    "meta.yaml": "meta-yaml",
    "recipe.yaml": "recipe-yaml",
}

# Formats whose rows are complete/resolved as-given (policy § 3: lockfiles,
# SBOMs and live-env captures are used verbatim; bare manifests are flagged
# `resolution: direct` until the local-wave resolver integration).
_LOCKED_FORMATS = frozenset({
    "pip", "conda-list", "pixi-lock", "conda-lock", "uv-lock", "poetry-lock",
    "pdm-lock", "pylock", "pipfile-lock", "cyclonedx", "spdx",
})

# Policy tier per intake format (spec § Wave C S5 input contract). Rows from
# future-tier sources are flagged `policy_tier: future` in every output.
_POLICY_TIERS: dict[str, str] = {
    # policy-supported — the Dependency Policy's CI formats
    "requirements": "policy", "pyproject": "policy", "environment-yml": "policy",
    "conda-lock": "policy", "pixi-toml": "policy", "pixi-lock": "policy",
    "meta-yaml": "policy", "recipe-yaml": "policy",
    # tool-supported beyond policy (the tool runs ahead of the policy)
    "pip": "tool", "conda-list": "tool", "cyclonedx": "tool", "spdx": "tool",
    "pipfile": "tool", "pipfile-lock": "tool",
    # future tier
    "uv-lock": "future", "poetry-lock": "future", "pdm-lock": "future",
    "pylock": "future",
}
_TIER_RANK = {"policy": 0, "tool": 1, "future": 2}


def detect_format(path: Path) -> str | None:
    """Filename first; content sniff for text/JSON without canonical names."""
    if path.name in _FILENAME_FORMATS:
        return _FILENAME_FORMATS[path.name]
    try:
        head = path.read_text(errors="replace")[:4096]
    except OSError:
        return None
    stripped = head.lstrip()
    if stripped.startswith("{"):
        if '"bomFormat"' in head or "CycloneDX" in head:
            return "cyclonedx"
        if '"spdxVersion"' in head:
            return "spdx"
        return None
    if stripped.startswith("["):
        # conda list --json rows carry base_url/dist_name; pip list --format=json
        # rows are bare {name, version}
        if '"base_url"' in head or '"dist_name"' in head:
            return "conda-list"
        return "pip"
    if ("# packages in environment" in head or "@EXPLICIT" in head
            or re.search(r"(?m)^[A-Za-z0-9._-]+=[^=\s]+=\S+$", head)):
        return "conda-list"
    if re.search(r"(?m)^[A-Za-z0-9._-]+==\S+", head) \
            or re.search(r"(?im)^Package\s+Version", head):
        return "pip"
    return None


def load_inventory(
    inputs: list[Path], fmt: str | None,
) -> tuple[list[Any], list[str], list[str]]:
    """Parse every input into Deps. Returns (deps, labels, warnings).
    Directories are scanned (recursively, skipping vendored trees) for the
    canonical filenames in _FILENAME_FORMATS."""
    deps: list[Any] = []
    labels: list[str] = []
    warnings: list[str] = []
    for inp in inputs:
        if inp.is_dir():
            for fname, dir_fmt in _FILENAME_FORMATS.items():
                for path in sorted(inp.glob(f"**/{fname}")):
                    if any(p in sp._SKIP_PATH_PARTS for p in path.parts):
                        continue
                    # lock-over-manifest rule (same as scan-project)
                    if dir_fmt == "pixi-toml" and (path.parent / "pixi.lock").exists():
                        continue
                    if dir_fmt == "pipfile" and (path.parent / "Pipfile.lock").exists():
                        continue
                    found = FORMAT_PARSERS[dir_fmt](path)
                    if found:
                        deps.extend(_stamp_resolution(found, dir_fmt))
                        labels.append(str(path))
            continue
        use_fmt = fmt or detect_format(inp)
        if use_fmt is None or use_fmt not in FORMAT_PARSERS:
            warnings.append(f"unrecognized input format: {inp} (use --format)")
            continue
        found = FORMAT_PARSERS[use_fmt](inp)
        if not found:
            warnings.append(f"no deps parsed from {inp} (format {use_fmt})")
        deps.extend(_stamp_resolution(found, use_fmt))
        labels.append(str(inp))
    return deps, labels, warnings


def _stamp_resolution(deps: list[Any], fmt: str) -> list[Any]:
    resolution = "locked" if fmt in _LOCKED_FORMATS else "direct"
    return _stamp(deps, resolution, _POLICY_TIERS.get(fmt, "tool"))


def _stamp(deps: list[Any], resolution: str, tier: str) -> list[Any]:
    for d in deps:
        d.extras.setdefault("resolution", resolution)
        d.extras.setdefault("policy_tier", tier)
    return deps


def _effective_pin(d: Any) -> tuple[str | None, str | None]:
    """(exact_pin | None, constraint | None) for one Dep. Range bounds are
    NEVER pins: a recorded non-== operator (`>=`/`~=`/`!=` — parsers stash
    it in extras['op']) or operator/wildcard characters inside the version
    string (pixi.toml-style raw specs) demote to constraint."""
    ver = d.version
    constraint = d.extras.get("constraint")
    op = d.extras.get("op")
    if not ver:
        return None, constraint
    if op and op not in ("==", "==="):
        return None, f"{op}{ver}"
    if re.search(r"[<>=!~^*\s]", ver):
        v = ver.strip()
        if v.startswith("=="):
            exact = v.lstrip("=").strip()
            if re.fullmatch(r"[0-9][\w.!+-]*", exact):
                return exact, None
        return None, ver
    return ver, constraint


def dedupe_deps(deps: list[Any]) -> list[dict[str, Any]]:
    """Collapse to one row per (ecosystem, identity). Identity is the
    PEP-503 fold for pypi (and other registries) but the EXACT lowercase
    name for conda — `ruamel.yaml` and `ruamel_yaml` are two different
    conda-forge packages and must never merge. A pinned occurrence beats an
    unpinned one; two DIFFERENT pins are kept first-wins and recorded in
    `pin_conflict`; manifests are unioned."""
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for d in deps:
        if not d.name:
            continue
        eco = d.ecosystem
        ident = d.name.lower() if eco == "conda" else fold_name(d.name)
        key = (eco, ident)
        pinned, constraint = _effective_pin(d)
        tier = d.extras.get("policy_tier", "tool")
        row = merged.get(key)
        if row is None:
            merged[key] = {
                "name": d.name,
                "ecosystem": eco,
                "pinned": pinned,
                "constraint": constraint,
                "manifests": [d.manifest],
                "resolution": d.extras.get("resolution", "locked"),
                "policy_tier": tier,
                **({"depth": d.extras["depth"]}
                   if d.extras.get("depth") is not None else {}),
                **({"fanout": d.extras["fanout"]}
                   if d.extras.get("fanout") is not None else {}),
            }
            continue
        if d.manifest not in row["manifests"]:
            row["manifests"].append(d.manifest)
        if pinned:
            if row["pinned"] is None:
                row["pinned"] = pinned
                row["name"] = d.name
            elif pinned != row["pinned"] and pinned not in row.get("pin_conflict", []):
                row.setdefault("pin_conflict", []).append(pinned)
        # a constraint never attaches to an exact-pinned row (a `<1.20`
        # bound from another manifest must not masquerade as its metadata)
        if row["pinned"] is None and row["constraint"] is None:
            row["constraint"] = constraint
        # resolution rank: locked (as-given complete) > resolved > direct
        res = d.extras.get("resolution")
        if res == "locked" or (res == "resolved" and row["resolution"] == "direct"):
            row["resolution"] = res
        for graph_key in ("depth", "fanout"):
            v = d.extras.get(graph_key)
            if v is not None:
                cur = row.get(graph_key)
                row[graph_key] = v if cur is None else (
                    min(cur, v) if graph_key == "depth" else max(cur, v))
        if _TIER_RANK.get(tier, 1) < _TIER_RANK.get(row["policy_tier"], 1):
            row["policy_tier"] = tier
    for row in merged.values():
        row["pin_kind"] = ("exact" if row["pinned"]
                           else ("range" if row["constraint"] else "unpinned"))
    return sorted(merged.values(), key=lambda r: (r["ecosystem"], r["name"]))


# ── version comparison ───────────────────────────────────────────────────────

_NUMERIC_RE = re.compile(r"^\d+(\.\d+)*$")


def cmp_versions(a: str | None, b: str | None) -> tuple[int | None, bool]:
    """Three-way compare → (-1/0/1 | None, reliable). Ladder: packaging
    parse → pure dotted-numeric tuples → string equality; string INEQUALITY
    is the only unreliable verdict (decision 3)."""
    if not a or not b:
        return None, True
    # conda epochs ("1!2.0") parse under packaging
    try:
        from packaging.version import InvalidVersion, Version
        try:
            va, vb = Version(a), Version(b)
            return (va > vb) - (va < vb), True
        except InvalidVersion:
            pass
    except ImportError:
        pass
    if _NUMERIC_RE.match(a) and _NUMERIC_RE.match(b):
        ta = tuple(int(x) for x in a.split("."))
        tb = tuple(int(x) for x in b.split("."))
        return (ta > tb) - (ta < tb), True
    if a == b:
        return 0, True
    return (a > b) - (a < b), False


def _sort_versions(versions: list[str]) -> tuple[list[str], bool]:
    """Ascending sort; reliable=False when any pairwise fallback was
    lexicographic-on-unequal-strings."""
    reliable = True

    def _cmp(x: str, y: str) -> int:
        nonlocal reliable
        c, ok = cmp_versions(x, y)
        if not ok:
            reliable = False
        return c or 0

    return sorted(versions, key=functools.cmp_to_key(_cmp)), reliable


# ── freshness policy (Python Dependency Policy § freshness) ──────────────────

def freshness_check(
    pinned: str | None,
    eligible: list[str] | None,
    dense_n: int = FRESHNESS_DENSE_N,
    top_pct: float = FRESHNESS_TOP_PCT,
) -> dict[str, Any]:
    """Dense history (≥ dense_n eligible versions): the pin must sit in the
    top `top_pct` percentile of the ascending eligible set. Sparse: last
    eligible − 1 or newer suffices. Returns verdict pass/fail/warn/unknown
    + the percentile on every row (warn = comparison unreliable)."""
    if not pinned or not eligible:
        return {"verdict": "unknown", "percentile": None}
    ordered, sort_reliable = _sort_versions(list(dict.fromkeys(eligible)))
    count_le = 0
    cmp_reliable = True
    for v in ordered:
        c, ok = cmp_versions(v, pinned)
        if not ok:
            cmp_reliable = False
        if c is not None and c <= 0:
            count_le += 1
    percentile = round(count_le / len(ordered), 4)
    if len(ordered) >= dense_n:
        passed = percentile >= 1 - top_pct
    else:
        floor_version = ordered[-2] if len(ordered) >= 2 else ordered[-1]
        c, ok = cmp_versions(pinned, floor_version)
        cmp_reliable = cmp_reliable and ok
        passed = c is not None and c >= 0
    if not (sort_reliable and cmp_reliable):
        return {"verdict": "warn", "percentile": percentile}
    return {"verdict": "pass" if passed else "fail", "percentile": percentile}


def history_version_provider(conn: sqlite3.Connection) -> Callable[[str], list[str] | None]:
    """Default OFFLINE eligible-set provider: distinct versions seen for a
    conda package across `upstream_versions_history` + the current
    `upstream_versions` rows. No yanked/requires-python filtering is
    possible offline — the live PyPI provider is the LOCAL wave."""
    def provider(conda_name: str) -> list[str] | None:
        versions = {
            r[0] for r in conn.execute(
                "SELECT DISTINCT version FROM upstream_versions_history "
                "WHERE conda_name = ? AND version IS NOT NULL", (conda_name,))
        }
        versions |= {
            r[0] for r in conn.execute(
                "SELECT version FROM upstream_versions "
                "WHERE conda_name = ? AND version IS NOT NULL", (conda_name,))
        }
        return sorted(versions) if len(versions) >= 2 else None

    provider.basis = "upstream_versions_history (offline)"  # type: ignore[attr-defined]
    return provider


# ── local wave (Wave C): live providers + transitive resolver ────────────────
# Everything in this section needs network and/or tooling the web container
# lacks (pip's resolver, py-rattler, pypi.org JSON, live channeldata, the
# vdb-derived vuln rollups). Each surface degrades gracefully — any failure
# warns and falls back to the web-slice (offline) behavior, never a hard
# match failure. `--offline` disables the lot explicitly.

CACHE_DIR = _get_data_dir() / "cache"
CHANNELDATA_CACHE = CACHE_DIR / "channeldata-inventory-match.json"
CHANNELDATA_TTL_S = 24 * 3600
_LIVE_TIMEOUT_S = 30
_RESOLVE_TIMEOUT_S = 900


def _fetch_url_bytes(urls: list[str], timeout: int = _LIVE_TIMEOUT_S) -> bytes | None:
    """First-success fetch over an ordered URL chain via _http (enterprise
    routing + truststore). None when every URL fails."""
    import _http
    for url in urls:
        try:
            with _http.open_url(_http.make_request(url), timeout=timeout) as resp:
                return resp.read()
        except Exception:  # noqa: BLE001 — any transport failure → next URL
            continue
    return None


def fetch_live_channeldata(ttl_s: int = CHANNELDATA_TTL_S) -> dict[str, Any] | None:
    """TTL-cached live conda-forge `channeldata.json` packages map — the
    decision-4 / G74 cross-check source (the atlas can lag freshly-created
    feedstocks). Returns None when unreachable (caller warns + rows keep the
    atlas-only verdict, stamped `live_cf_check: unavailable`)."""
    try:
        if (CHANNELDATA_CACHE.exists()
                and time.time() - CHANNELDATA_CACHE.stat().st_mtime < ttl_s):
            return json.loads(
                CHANNELDATA_CACHE.read_text(encoding="utf-8")).get("packages")
    except (OSError, json.JSONDecodeError):
        pass
    import _http
    data = _fetch_url_bytes(
        [f"{b.rstrip('/')}/channeldata.json"
         for b in _http.resolve_conda_forge_urls()])
    if data is None:
        return None
    try:
        packages = json.loads(data).get("packages")
    except json.JSONDecodeError:
        return None
    if not isinstance(packages, dict) or not packages:
        return None
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _http.atomic_write_bytes(CHANNELDATA_CACHE, data)
    except OSError:
        pass
    return packages


def _needs_live_cf_check(row: dict[str, Any]) -> bool:
    """Rows about to be REPORTED as missing from conda-forge (decision 4:
    a 'missing' declaration is destructive/report-final)."""
    if row["bucket"] in ("ADD", "ADD-NONPYPI"):
        return True
    return (row["bucket"] == "UNKNOWN" and row["ecosystem"] == "conda"
            and "conda_forge_presence" in row["signals_absent"])


def apply_live_cf_check(rows: list[dict[str, Any]],
                        channeldata: dict[str, Any]) -> dict[str, int]:
    """Decision-4 post-pass: cross-check every would-be-missing row against
    LIVE channeldata. A hit means the atlas is stale for that package — the
    row is re-bucketed against the channeldata version and stamped
    `atlas_stale`; a miss is stamped `live_cf_check: absent-confirmed`."""
    stats = {"checked": 0, "recovered": 0, "confirmed_absent": 0}
    fold_idx: dict[str, str] = {}
    for k in channeldata:
        fold_idx.setdefault(fold_name(k), k)
    for row in rows:
        if not _needs_live_cf_check(row):
            continue
        stats["checked"] += 1
        name = row["name"]
        if name in channeldata:
            hit_name = name
        elif name.lower() in channeldata:
            hit_name = name.lower()
        else:
            hit_name = fold_idx.get(fold_name(name))
        if hit_name is None:
            row["live_cf_check"] = "absent-confirmed"
            stats["confirmed_absent"] += 1
            continue
        cd_version = (channeldata.get(hit_name) or {}).get("version")
        row["conda_name"] = hit_name
        row["cf_latest"] = cd_version
        row["match_via"] = "channeldata_live"
        row["match_confidence"] = ("exact" if row["ecosystem"] == "conda"
                                   and hit_name == name.lower() else "likely")
        row["atlas_stale"] = True
        row["live_cf_check"] = "present"
        row["conda_purl"] = (
            f"pkg:conda/{hit_name}@{cd_version}{CHANNEL_QUALIFIER}"
            if cd_version else f"pkg:conda/{hit_name}{CHANNEL_QUALIFIER}")
        if "upstream_freshness" not in row["signals_absent"]:
            row["signals_absent"].append("upstream_freshness")
        if cd_version is None:
            row["bucket"] = "UNKNOWN"
            row["signals_absent"].append("cf_version")
        else:
            c, ok = cmp_versions(row.get("pinned"), cd_version)
            row["bucket"] = ("UPDATE-PIN" if c is not None and c < 0
                             else "CURRENT")
            row["version_comparison"] = "reliable" if ok else "unreliable"
        stats["recovered"] += 1
    return stats


def _py_admits(requires_python: str, pyv: str) -> bool:
    """Does a requires-python spec admit runtime `pyv`? Unparseable specs
    never exclude (fail-open per-version; the eligible set stays useful)."""
    try:
        from packaging.specifiers import SpecifierSet
        return pyv in SpecifierSet(requires_python)
    except Exception:  # noqa: BLE001 — malformed upstream spec
        return True


def _fetch_pypi_release_map(pypi_name: str) -> dict[str, Any] | None:
    import _http
    data = _fetch_url_bytes(_http.resolve_pypi_json_urls(pypi_name))
    if data is None:
        return None
    try:
        releases = json.loads(data).get("releases")
    except json.JSONDecodeError:
        return None
    return releases if isinstance(releases, dict) else None


def live_pypi_version_provider(
    conn: sqlite3.Connection,
    *,
    py_version: str | None = None,
    fetch: Callable[[str], dict[str, Any] | None] = _fetch_pypi_release_map,
) -> Callable[[str], list[str] | None]:
    """LOCAL-wave eligible-set provider (policy: runtime-Python-compatible,
    non-yanked). One pypi.org JSON fetch per pypi-mapped matched package
    (bounded to the inventory slice, memoized per run); releases that are
    fully yanked or whose requires-python excludes the runtime are dropped.
    Falls back to the offline history provider per name on any failure or
    for packages with no PyPI identity."""
    fallback = history_version_provider(conn)
    pypi_by_conda = {
        r[0]: r[1] for r in conn.execute(
            "SELECT conda_name, pypi_name FROM packages "
            "WHERE conda_name IS NOT NULL AND pypi_name IS NOT NULL "
            "AND pypi_name != ''")
    }
    pyv = py_version or ".".join(str(v) for v in sys.version_info[:3])
    stats = {"live": 0, "fallback": 0}

    @functools.lru_cache(maxsize=4096)
    def _eligible(pypi_name: str) -> tuple[str, ...] | None:
        releases = fetch(pypi_name)
        if releases is None:
            return None
        eligible = []
        for ver, files in releases.items():
            if not files or not isinstance(files, list):
                continue  # no artifacts → not installable
            if all(f.get("yanked") for f in files):
                continue
            rp = next((f.get("requires_python") for f in files
                       if f.get("requires_python")), None)
            if rp and not _py_admits(rp, pyv):
                continue
            eligible.append(ver)
        return tuple(eligible)

    def provider(conda_name: str) -> list[str] | None:
        pypi_name = pypi_by_conda.get(conda_name)
        if pypi_name:
            e = _eligible(pypi_name)
            if e is not None and len(e) >= 2:
                stats["live"] += 1
                return sorted(e)
        stats["fallback"] += 1
        return fallback(conda_name)

    provider.basis = (  # type: ignore[attr-defined]
        f"pypi.org JSON (live; yanked + requires-python[{pyv}] filtered), "
        "upstream_versions_history fallback")
    provider.stats = stats  # type: ignore[attr-defined]
    return provider


# ── transitive resolver (policy § 3) ─────────────────────────────────────────

def _spec_string(d: Any, *, conda: bool = False) -> str:
    pinned, constraint = _effective_pin(d)
    if pinned:
        return f"{d.name} =={pinned}" if conda else f"{d.name}=={pinned}"
    if constraint:
        return f"{d.name} {constraint}" if conda else f"{d.name}{constraint}"
    return d.name


def _pip_report(specs: list[str], warnings: list[str]) -> dict[str, Any] | None:
    """`pip install --dry-run --report` (installation report, pip ≥ 23) —
    the policy-named PyPI resolver. None on failure."""
    import subprocess
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        report_path = Path(tmp.name)
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--dry-run",
             "--ignore-installed", "--quiet", "--report", str(report_path),
             *specs],
            capture_output=True, text=True, timeout=_RESOLVE_TIMEOUT_S)
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or "").strip().splitlines()
            warnings.append("pip resolver failed — pypi rows stay direct"
                            + (f": {tail[-1]}" if tail else ""))
            return None
        return json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        warnings.append(f"pip resolver unavailable ({exc}) — pypi rows stay direct")
        return None
    finally:
        report_path.unlink(missing_ok=True)


def derive_pip_graph(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """fold → {name, version, requested, depth, fanout} from a pip
    installation report. Edges come from each package's requires_dist with
    markers evaluated against the report's environment (extra unset); depth
    is BFS from the requested roots; fanout is the resolved out-degree.
    Marker-hidden reachability leaves depth None (still a resolved row)."""
    env = report.get("environment") or {}
    nodes: dict[str, dict[str, Any]] = {}
    requires: dict[str, list[str]] = {}
    for item in report.get("install", []):
        meta = item.get("metadata") or {}
        name = meta.get("name")
        if not name:
            continue
        f = fold_name(name)
        nodes[f] = {"name": name, "version": meta.get("version"),
                    "requested": bool(item.get("requested"))}
        requires[f] = meta.get("requires_dist") or []
    edges: dict[str, set[str]] = {f: set() for f in nodes}
    try:
        from packaging.markers import default_environment
        from packaging.requirements import Requirement
        menv = {**default_environment(), **env, "extra": ""}
    except ImportError:
        Requirement = None  # type: ignore[assignment]
        menv = {}
    if Requirement is not None:
        for f, reqs in requires.items():
            for spec in reqs:
                try:
                    r = Requirement(spec)
                    if r.marker is not None and not r.marker.evaluate(menv):
                        continue
                except Exception:  # noqa: BLE001 — malformed/extra-only marker
                    continue
                tf = fold_name(r.name)
                if tf in nodes:
                    edges[f].add(tf)
    depth = {f: 0 for f, n in nodes.items() if n["requested"]}
    queue = list(depth)
    while queue:
        cur = queue.pop(0)
        for nxt in sorted(edges.get(cur, ())):
            if nxt not in depth:
                depth[nxt] = depth[cur] + 1
                queue.append(nxt)
    for f, n in nodes.items():
        n["depth"] = depth.get(f)
        n["fanout"] = len(edges.get(f, ()))
    return nodes


def _conda_solve_records(specs: list[str],
                         warnings: list[str]) -> list[Any] | None:
    """py-rattler conda-forge solve for the conda track. None on failure."""
    try:
        import asyncio
        import datetime as _dt
        import rattler

        async def _solve() -> list[Any]:
            vps = None
            for attr in ("detect", "current"):
                try:
                    vps = getattr(rattler.VirtualPackage, attr)()
                    break
                except Exception:  # noqa: BLE001
                    continue
            return await rattler.solve(
                ["conda-forge"], specs,
                platforms=[rattler.Platform.current(), rattler.Platform("noarch")],
                virtual_packages=vps,
                timeout=_dt.timedelta(seconds=_RESOLVE_TIMEOUT_S))

        return asyncio.run(_solve())
    except Exception as exc:  # noqa: BLE001 — solver missing/unsolvable/offline
        warnings.append(f"conda solve failed ({type(exc).__name__}: {exc}) "
                        "— conda rows stay direct")
        return None


def derive_conda_graph(records: list[Any],
                       requested: set[str]) -> dict[str, dict[str, Any]]:
    """lowercase-name → {name, version, requested, depth, fanout} from
    solved RepoDataRecords (edges from each record's `depends` specs)."""
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, set[str]] = {}
    for rec in records:
        name = getattr(rec.name, "normalized", None) or str(rec.name)
        key = name.lower()
        nodes[key] = {"name": name, "version": str(rec.version),
                      "requested": key in requested}
        edges[key] = {d.split()[0].lower() for d in (rec.depends or []) if d}
    for key in edges:
        edges[key] = {d for d in edges[key] if d in nodes}
    depth = {k: 0 for k, n in nodes.items() if n["requested"]}
    queue = list(depth)
    while queue:
        cur = queue.pop(0)
        for nxt in sorted(edges.get(cur, ())):
            if nxt not in depth:
                depth[nxt] = depth[cur] + 1
                queue.append(nxt)
    for key, n in nodes.items():
        n["depth"] = depth.get(key)
        n["fanout"] = len(edges.get(key, ()))
    return nodes


def resolve_transitive(deps: list[Any], warnings: list[str]) -> dict[str, int]:
    """Policy § 3: bare-manifest (`resolution: direct`) rows are resolved to
    the full graph before matching — PyPI track via pip's resolver, conda
    track via a py-rattler conda-forge solve. Direct rows upgrade to
    `resolution: resolved` (+ depth/fanout for S7); resolver-discovered
    transitive packages append as new rows (`via: transitive`). Any resolver
    failure warns and leaves the affected rows `direct`."""
    stats = {"pypi_upgraded": 0, "conda_upgraded": 0, "added": 0}
    direct = [d for d in deps if d.name and d.extras.get("resolution") == "direct"]
    pypi_direct = [d for d in direct if d.ecosystem == "pypi"]
    conda_direct = [d for d in direct if d.ecosystem == "conda"]

    def _tier(group: list[Any]) -> str:
        tiers = [d.extras.get("policy_tier", "tool") for d in group]
        return min(tiers, key=lambda t: _TIER_RANK.get(t, 1)) if tiers else "tool"

    if pypi_direct:
        report = _pip_report([_spec_string(d) for d in pypi_direct], warnings)
        if report is not None:
            nodes = derive_pip_graph(report)
            covered = set()
            for d in pypi_direct:
                node = nodes.get(fold_name(d.name))
                if node is None:
                    continue
                covered.add(fold_name(d.name))
                d.extras.update(
                    resolution="resolved",
                    depth=node["depth"] if node["depth"] is not None else 0,
                    fanout=node["fanout"])
                if not d.version:
                    d.version = node["version"]
                stats["pypi_upgraded"] += 1
            tier = _tier(pypi_direct)
            label = f"resolved:{pypi_direct[0].manifest}"
            for f, node in sorted(nodes.items()):
                if f in covered or node["requested"]:
                    continue
                deps.append(sp.Dep(
                    name=node["name"], version=node["version"],
                    ecosystem="pypi", manifest=label,
                    extras={"resolution": "resolved", "policy_tier": tier,
                            "depth": node["depth"], "fanout": node["fanout"],
                            "via": "transitive"}))
                stats["added"] += 1

    if conda_direct:
        records = _conda_solve_records(
            [_spec_string(d, conda=True) for d in conda_direct], warnings)
        if records is not None:
            requested = {d.name.lower() for d in conda_direct}
            nodes = derive_conda_graph(records, requested)
            covered = set()
            for d in conda_direct:
                node = nodes.get(d.name.lower())
                if node is None:
                    continue
                covered.add(d.name.lower())
                d.extras.update(
                    resolution="resolved",
                    depth=node["depth"] if node["depth"] is not None else 0,
                    fanout=node["fanout"])
                if not d.version:
                    d.version = node["version"]
                stats["conda_upgraded"] += 1
            tier = _tier(conda_direct)
            label = f"resolved:{conda_direct[0].manifest}"
            for key, node in sorted(nodes.items()):
                if key in covered or node["requested"]:
                    continue
                deps.append(sp.Dep(
                    name=node["name"], version=node["version"],
                    ecosystem="conda", manifest=label,
                    extras={"resolution": "resolved", "policy_tier": tier,
                            "depth": node["depth"], "fanout": node["fanout"],
                            "via": "transitive"}))
                stats["added"] += 1
    return stats


# ── vuln rollups (vdb-derived Phase G posture, read from the atlas) ──────────

_VULN_COLS = ("vuln_critical_affecting_current", "vuln_high_affecting_current",
              "vuln_kev_affecting_current", "vuln_max_epss_score")

# policy `vulns.*` threshold key → the attached rollup field it gates
_VULN_THRESHOLDS = {"max_critical": "critical", "max_high": "high",
                    "max_kev": "kev"}


def attach_vuln_rollups(conn: sqlite3.Connection,
                        rows: list[dict[str, Any]]) -> None:
    """Attach the atlas's Phase G vuln rollups (CURRENT-cf-version posture —
    stamped as such) to atlas-matched rows; matched rows with no rollup data
    gain `signals_absent: vuln_rollups` so fail-closed policies see the gap."""
    names = sorted({r["conda_name"] for r in rows if r.get("conda_name")})
    if not names:
        return
    got: dict[str, dict[str, Any]] = {}
    for i in range(0, len(names), 500):
        chunk = names[i:i + 500]
        marks = ",".join("?" for _ in chunk)
        for row in conn.execute(
            f"SELECT conda_name, {', '.join(_VULN_COLS)} FROM packages "
            f"WHERE conda_name IN ({marks})", chunk,
        ):
            if any(v is not None for v in row[1:]):
                got[row[0]] = {
                    "critical": row[1] or 0, "high": row[2] or 0,
                    "kev": row[3] or 0, "max_epss": row[4],
                    "basis": "atlas Phase G rollups (current cf version)",
                }
    for r in rows:
        cn = r.get("conda_name")
        if not cn:
            continue
        if cn in got:
            r["vulns"] = got[cn]
        elif "vuln_rollups" not in r["signals_absent"]:
            r["signals_absent"].append("vuln_rollups")


# ── atlas indexes ────────────────────────────────────────────────────────────

def load_atlas_indexes(conn: sqlite3.Connection) -> dict[str, Any]:
    conda_by_name: dict[str, dict[str, Any]] = {}
    conda_by_fold: dict[str, dict[str, Any]] = {}
    mapping_by_fold: dict[str, list[dict[str, Any]]] = {}
    # scope: the matcher must see EVERY conda row — archived/inactive
    # packages are reported (flagged), not misreported as "not on cf".
    for row in conn.execute(
        "SELECT conda_name, pypi_name, latest_conda_version, latest_status, "
        "feedstock_archived, conda_license, feedstock_name, match_source, "
        "match_confidence FROM packages WHERE conda_name IS NOT NULL "
        "ORDER BY conda_name"
    ):
        rec = {
            "conda_name": row[0], "pypi_name": row[1], "cf_latest": row[2],
            "latest_status": row[3] or "active", "feedstock_archived": row[4] or 0,
            "conda_license": row[5], "feedstock_name": row[6],
            "match_source": row[7], "match_confidence": row[8],
        }
        # conda names are exact identifiers; the fold index exists only for
        # the flagged g10_bare / conda_fold fallbacks (fold collisions like
        # ruamel.yaml vs ruamel_yaml keep the first name — never `exact`).
        conda_by_name[row[0].lower()] = rec
        conda_by_fold.setdefault(fold_name(row[0]), rec)
        if row[1]:
            mapping_by_fold.setdefault(fold_name(row[1]), []).append(rec)

    upstream: dict[str, dict[str, Any]] = {}
    order = {s: i for i, s in enumerate(_UPSTREAM_SOURCE_ORDER)}
    for name, source, version, fetched_at in conn.execute(
        "SELECT conda_name, source, version, fetched_at FROM upstream_versions "
        "WHERE version IS NOT NULL ORDER BY conda_name, source"
    ):
        rank = order.get(source, len(order))
        cur = upstream.get(name)
        if cur is None or rank < cur["rank"]:
            upstream[name] = {"source": source, "version": version,
                              "fetched_at": fetched_at, "rank": rank}
    return {"conda_by_name": conda_by_name, "conda_by_fold": conda_by_fold,
            "mapping_by_fold": mapping_by_fold, "upstream": upstream}


def universe_lookup(conn: sqlite3.Connection, wanted_folds: set[str]) -> dict[str, str]:
    """fold → stored universe spelling, restricted to the folds we need
    (single pass; no full fold-index kept in memory)."""
    hits: dict[str, str] = {}
    if not wanted_folds:
        return hits
    for (name,) in conn.execute("SELECT pypi_name FROM pypi_universe"):
        f = fold_name(name)
        if f in wanted_folds and f not in hits:
            hits[f] = name
    return hits


_ENRICH_COLS = ("pypi_name", "latest_version", "latest_yanked", "requires_python",
                "license_spdx", "conda_forge_readiness", "recommended_template",
                "staged_recipes_pr_url")


def enrichment_lookup(conn: sqlite3.Connection, names: list[str]) -> dict[str, dict[str, Any]]:
    """Exact stored-spelling reads via the v29 ORPHAN_RULE view (orphan
    pypi_intelligence rows are never version truth)."""
    out: dict[str, dict[str, Any]] = {}
    for i in range(0, len(names), 500):
        chunk = names[i:i + 500]
        marks = ",".join("?" for _ in chunk)
        for row in conn.execute(
            f"SELECT {', '.join(_ENRICH_COLS)} FROM v_pypi_intelligence_valid "
            f"WHERE pypi_name IN ({marks}) AND json_fetched_at IS NOT NULL",
            chunk,
        ):
            out[row[0]] = dict(zip(_ENRICH_COLS, row))
    return out


# ── matcher core ─────────────────────────────────────────────────────────────

def _upstream_lag(
    conn: sqlite3.Connection, conda_name: str, cf_latest: str | None,
    up_version: str | None, up_source: str | None,
) -> tuple[int | None, int | None]:
    """(lag_releases, lag_days): distinct known upstream versions — the
    current `upstream_versions` row plus source-filtered history — strictly
    newer than cf-latest, and days since the earliest history snapshot that
    carried one. (None, None) when nothing lands reliably newer (history
    may not have snapshotted the drift yet); lag_days None when only the
    current row proves the lag (no dated snapshot)."""
    if not cf_latest:
        return None, None
    rows: list[tuple[str, int | None]] = list(conn.execute(
        "SELECT version, MIN(snapshot_at) FROM upstream_versions_history "
        "WHERE conda_name = ? AND source = ? AND version IS NOT NULL "
        "GROUP BY version",
        (conda_name, up_source),
    ))
    if up_version:
        rows.append((up_version, None))
    newer_versions: set[str] = set()
    snaps: list[int] = []
    for version, first_seen in rows:
        c, ok = cmp_versions(version, cf_latest)
        if ok and c is not None and c > 0:
            newer_versions.add(version)
            if first_seen is not None:
                snaps.append(first_seen)
    if not newer_versions:
        return None, None
    lag_days = int((time.time() - min(snaps)) / 86400) if snaps else None
    return len(newer_versions), lag_days


def match_inventory(
    conn: sqlite3.Connection,
    inv_rows: list[dict[str, Any]],
    weights: dict[str, float] | None = None,
    version_provider: Callable[[str], list[str] | None] | None = None,
) -> list[dict[str, Any]]:
    """The S5 matcher: resolve → three-way compare → bucket, one output row
    per deduped inventory row."""
    idx = load_atlas_indexes(conn)
    conda_by_name = idx["conda_by_name"]
    conda_by_fold = idx["conda_by_fold"]
    mapping_by_fold = idx["mapping_by_fold"]
    upstream = idx["upstream"]
    provider = version_provider or history_version_provider(conn)
    weights = weights or {}

    # Pre-resolve universe membership + enrichment for the pypi-side names
    # we may need (unmatched pypi deps → ADD path).
    pypi_folds = {fold_name(r["name"]) for r in inv_rows if r["ecosystem"] == "pypi"}
    universe = universe_lookup(conn, pypi_folds)
    enrich = enrichment_lookup(conn, sorted(universe.values()))

    out: list[dict[str, Any]] = []
    for inv in inv_rows:
        fold = fold_name(inv["name"])
        row: dict[str, Any] = {
            **{k: inv[k] for k in ("name", "ecosystem", "pinned", "pin_kind",
                                   "constraint", "manifests", "resolution",
                                   "policy_tier")},
            **({"pin_conflict": inv["pin_conflict"]} if inv.get("pin_conflict") else {}),
            **({"depth": inv["depth"]} if inv.get("depth") is not None else {}),
            **({"fanout": inv["fanout"]} if inv.get("fanout") is not None else {}),
            "conda_name": None, "cf_latest": None, "match_via": None,
            "match_source": None, "match_confidence": None,
            "upstream_version": None, "upstream_source": None,
            "lag_releases": None, "lag_days": None,
            "bucket": "UNKNOWN", "version_comparison": None,
            "freshness": {"verdict": "unknown", "percentile": None},
            "weight": weights.get(fold),
            "signals_absent": [],
        }

        # ── resolve to a conda package ──
        rec: dict[str, Any] | None = None
        if inv["ecosystem"] == "conda":
            # conda names are exact identifiers — exact lookup first; the
            # fold fallback is a flagged guess (ruamel.yaml ≠ ruamel_yaml).
            rec = conda_by_name.get(inv["name"].lower())
            if rec:
                row["match_via"] = "conda_name"
                row["match_confidence"] = "exact"
            else:
                rec = conda_by_fold.get(fold)
                if rec:
                    row["match_via"] = "conda_fold"
                    row["match_confidence"] = "likely"
        elif inv["ecosystem"] == "pypi":
            mapped = mapping_by_fold.get(fold)
            if mapped:
                rec = mapped[0]
                if len(mapped) > 1:
                    row["mapping_alternates"] = [m["conda_name"] for m in mapped[1:]]
                row["match_via"] = "mapping"
                row["match_source"] = rec["match_source"]
                # verbatim tier — 'none'-provenance ('n/a') and
                # name_coincidence rows are never upgraded to verified.
                row["match_confidence"] = rec["match_confidence"]
            else:
                rec = conda_by_fold.get(fold)
                if rec and rec["pypi_name"] and fold_name(rec["pypi_name"]) != fold:
                    # the conda package is already mapped to a DIFFERENT
                    # PyPI project — a bare-name match here would re-open
                    # the wasmtime-vs-wasmtime-py trap (mapping_gap G10);
                    # fall through to the ADD/universe path instead.
                    rec = None
                if rec:
                    row["match_via"] = "g10_bare"
                    row["match_confidence"] = "likely"
        else:
            rec = conda_by_fold.get(fold)
            if rec:
                row["match_via"] = "g10_bare"
                # a conda package mapped to a PyPI project is a Python
                # package — a same-named cargo/npm dep is probably a
                # different artifact (name coincidence), not the same one.
                row["match_confidence"] = ("name_coincidence"
                                           if rec["pypi_name"] else "likely")

        # ── unmatched → ADD / ADD-NONPYPI / UNKNOWN ──
        if rec is None:
            if inv["ecosystem"] == "pypi":
                stored = universe.get(fold)
                if stored is None:
                    row["bucket"] = "UNKNOWN"
                    row["signals_absent"].append("pypi_universe")
                else:
                    row["bucket"] = "ADD"
                    row["pypi_name"] = stored
                    e = enrich.get(stored)
                    if e:
                        row["conda_forge_readiness"] = e["conda_forge_readiness"]
                        row["recommended_template"] = e["recommended_template"]
                        row["staged_recipes_pr_url"] = e["staged_recipes_pr_url"]
                        row["license_spdx"] = e["license_spdx"]
                        row["upstream_version"] = e["latest_version"]
                        row["upstream_source"] = "pypi"
                        if e["latest_yanked"]:
                            # a yanked latest is not a clean upstream-of-record
                            row["upstream_yanked"] = True
                    else:
                        row["signals_absent"].append("pypi_enrichment")
                    local = RECIPES_DIR / fold
                    row["local_recipe"] = local.is_dir() or (RECIPES_DIR / inv["name"]).is_dir()
            elif inv["ecosystem"] == "conda":
                # a conda identifier we can't find on conda-forge — another
                # channel or a rename; never guessed into ADD.
                row["bucket"] = "UNKNOWN"
                row["signals_absent"].append("conda_forge_presence")
            else:
                row["bucket"] = "ADD-NONPYPI"
                row["signals_absent"].append("conda_forge_presence")
            out.append(row)
            continue

        # ── matched: three-way comparison ──
        conda_name = rec["conda_name"]
        row["conda_name"] = conda_name
        row["cf_latest"] = rec["cf_latest"]
        row["latest_status"] = rec["latest_status"]
        row["feedstock_archived"] = bool(rec["feedstock_archived"])
        row["conda_license"] = rec["conda_license"]
        row["conda_purl"] = (
            f"pkg:conda/{conda_name}@{rec['cf_latest']}{CHANNEL_QUALIFIER}"
            if rec["cf_latest"] else f"pkg:conda/{conda_name}{CHANNEL_QUALIFIER}"
        )

        up = upstream.get(conda_name)
        if up:
            row["upstream_version"] = up["version"]
            row["upstream_source"] = up["source"]
        else:
            row["signals_absent"].append("upstream_freshness")

        unreliable = False
        cmp_cf_up, ok1 = cmp_versions(rec["cf_latest"], row["upstream_version"])
        cmp_inv_cf, ok2 = cmp_versions(inv["pinned"], rec["cf_latest"])
        unreliable = (not ok1) or (not ok2)

        if rec["cf_latest"] is None:
            row["bucket"] = "UNKNOWN"
            row["signals_absent"].append("cf_version")
        elif cmp_cf_up is not None and cmp_cf_up < 0:
            row["bucket"] = "UPDATE-FEEDSTOCK"
            row["pin_behind_cf"] = bool(cmp_inv_cf is not None and cmp_inv_cf < 0)
            lag_rel, lag_days = _upstream_lag(
                conn, conda_name, rec["cf_latest"],
                row["upstream_version"], row["upstream_source"])
            row["lag_releases"], row["lag_days"] = lag_rel, lag_days
        elif cmp_inv_cf is not None and cmp_inv_cf < 0:
            row["bucket"] = "UPDATE-PIN"
        else:
            row["bucket"] = "CURRENT"
        row["version_comparison"] = "unreliable" if unreliable else "reliable"

        row["freshness"] = freshness_check(inv["pinned"], provider(conda_name))
        out.append(row)
    attach_vuln_rollups(conn, out)
    return out


# ── weights sidecar ──────────────────────────────────────────────────────────

def load_weights(path: Path) -> dict[str, float]:
    """--weights <csv|json>: per-package criticality multiplier, keyed by
    folded name. CSV: `name,weight` rows (header optional); JSON: object."""
    text = path.read_text(encoding="utf-8")
    weights: dict[str, float] = {}
    if path.suffix.lower() == ".json":
        raw = json.loads(text)
        if not isinstance(raw, dict):
            raise ValueError("weights JSON must be an object {name: weight}")
        for name, w in raw.items():
            weights[fold_name(str(name))] = float(w)
        return weights
    for row in csv.reader(text.splitlines()):
        if len(row) < 2:
            continue
        name, w = row[0].strip(), row[1].strip()
        if not name or name.lower() == "name":
            continue
        weights[fold_name(name)] = float(w)
    return weights


# ── policy gate ──────────────────────────────────────────────────────────────

def load_policy(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".toml":
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[import-not-found,no-redef]
        return tomllib.loads(text)
    return json.loads(text)


def evaluate_policy(rows: list[dict[str, Any]], policy: dict[str, Any]) -> dict[str, Any]:
    """Deterministic CI gate. Supported thresholds (all optional):

      freshness.max_fail (int)          rows with verdict 'fail'
      freshness.count_warn_as_fail      treat 'warn' rows as failures
      buckets.max.<BUCKET> (int)        per-bucket row ceilings
      license.require_present (bool)    matched rows must carry a license
      license.deny ([spdx ids])         denylisted licenses (matched rows)
      metadata.max_signals_absent_rows  rows with ANY signals_absent
      vulns.max_critical (int)          rows whose matched package carries
                                        >0 critical vulns affecting its
                                        CURRENT cf version (Phase G rollups)
      vulns.max_high (int)              same, high severity
      vulns.max_kev (int)               same, CISA-KEV-listed
      block_on_missing_data (bool)      freshness 'unknown' rows count as
                                        failures, and rows missing vuln
                                        rollup data count against every
                                        vulns threshold (fail-closed;
                                        default true when the corresponding
                                        threshold is set)

    Unknown top-level keys, unknown bucket names, and malformed threshold
    shapes are `policy.schema` VIOLATIONS (fail-closed — a typo'd gate must
    never silently pass CI).
    Returns {"pass": bool, "violations": [...]} — weighted rows listed first.
    """
    violations: list[dict[str, Any]] = []

    # ── schema validation (fail-closed on typos) ──
    known_keys = {"freshness", "buckets", "license", "metadata", "vulns",
                  "block_on_missing_data"}
    schema_errors: list[str] = []
    for key in sorted(set(policy) - known_keys):
        schema_errors.append(f"unknown policy key {key!r}")
    if "freshness" in policy and (
            not isinstance(policy["freshness"], dict)
            or "max_fail" not in policy["freshness"]):
        schema_errors.append("freshness must be a table with max_fail")
    if "buckets" in policy:
        bmax = policy["buckets"].get("max") if isinstance(policy["buckets"], dict) else None
        if not isinstance(bmax, dict):
            schema_errors.append("buckets must be a table with a max table")
        else:
            for bucket in sorted(set(bmax) - set(BUCKETS)):
                schema_errors.append(f"unknown bucket {bucket!r} in buckets.max")
    if "license" in policy and (
            not isinstance(policy["license"], dict)
            or not isinstance(policy["license"].get("deny", []), list)):
        schema_errors.append("license must be a table; license.deny must be a list")
    if "metadata" in policy and not isinstance(policy["metadata"], dict):
        schema_errors.append("metadata must be a table")
    if "vulns" in policy:
        vp = policy["vulns"]
        if not isinstance(vp, dict):
            schema_errors.append("vulns must be a table")
        else:
            for key in sorted(set(vp) - set(_VULN_THRESHOLDS)):
                schema_errors.append(f"unknown vulns key {key!r}")
    if schema_errors:
        violations.append({
            "check": "policy.schema",
            "limit": 0, "actual": len(schema_errors), "rows": [],
            "note": "; ".join(schema_errors),
        })
        return {"pass": False, "violations": violations}

    def _named(rs: list[dict[str, Any]]) -> list[str]:
        ordered = sorted(rs, key=lambda r: (-(r.get("weight") or 0), r["name"]))
        return [r["name"] for r in ordered]

    fresh_pol = policy.get("freshness")
    if isinstance(fresh_pol, dict) and "max_fail" in fresh_pol:
        bad_verdicts = {"fail"}
        if fresh_pol.get("count_warn_as_fail"):
            bad_verdicts.add("warn")
        if policy.get("block_on_missing_data", True):
            bad_verdicts.add("unknown")
        failing = [r for r in rows if r["pin_kind"] == "exact"
                   and r["freshness"]["verdict"] in bad_verdicts]
        if len(failing) > int(fresh_pol["max_fail"]):
            violations.append({
                "check": "freshness",
                "limit": int(fresh_pol["max_fail"]),
                "actual": len(failing),
                "rows": _named(failing),
            })

    bucket_max = (policy.get("buckets") or {}).get("max") or {}
    for bucket, limit in bucket_max.items():
        hits = [r for r in rows if r["bucket"] == bucket]
        if limit is not None and len(hits) > int(limit):
            violations.append({
                "check": f"buckets.max.{bucket}",
                "limit": int(limit),
                "actual": len(hits),
                "rows": _named(hits),
            })

    lic_pol = policy.get("license")
    if isinstance(lic_pol, dict):
        matched = [r for r in rows if r.get("conda_name")]
        if lic_pol.get("require_present"):
            missing = [r for r in matched
                       if not (r.get("conda_license") or r.get("license_spdx"))]
            if missing:
                violations.append({
                    "check": "license.require_present",
                    "limit": 0, "actual": len(missing), "rows": _named(missing),
                })
        deny = {str(x).lower() for x in lic_pol.get("deny") or []}
        if deny:
            def _lic_tokens(r: dict[str, Any]) -> set[str]:
                # token-level so compound expressions ("GPL-3.0-only OR
                # MIT") still trip the denylist (conservative CI reading)
                s = str(r.get("conda_license") or r.get("license_spdx") or "")
                return {t.lower() for t in re.findall(r"[A-Za-z0-9.+-]+", s)}
            denied = [r for r in matched if deny & _lic_tokens(r)]
            if denied:
                violations.append({
                    "check": "license.deny",
                    "limit": 0, "actual": len(denied), "rows": _named(denied),
                })

    meta_pol = policy.get("metadata")
    if isinstance(meta_pol, dict) and "max_signals_absent_rows" in meta_pol:
        gaps = [r for r in rows if r["signals_absent"]]
        if len(gaps) > int(meta_pol["max_signals_absent_rows"]):
            violations.append({
                "check": "metadata.max_signals_absent_rows",
                "limit": int(meta_pol["max_signals_absent_rows"]),
                "actual": len(gaps),
                "rows": _named(gaps),
            })

    vuln_pol = policy.get("vulns")
    if isinstance(vuln_pol, dict):
        block_missing = policy.get("block_on_missing_data", True)
        matched = [r for r in rows if r.get("conda_name")]
        missing = ([r for r in matched
                    if "vuln_rollups" in r["signals_absent"]]
                   if block_missing else [])
        for key, field in _VULN_THRESHOLDS.items():
            if key not in vuln_pol:
                continue
            hits = [r for r in matched
                    if (r.get("vulns") or {}).get(field, 0) > 0]
            offending = hits + [r for r in missing if r not in hits]
            if len(offending) > int(vuln_pol[key]):
                violations.append({
                    "check": f"vulns.{key}",
                    "limit": int(vuln_pol[key]),
                    "actual": len(offending),
                    "rows": _named(offending),
                    **({"note": f"{len(missing)} row(s) counted for missing "
                                "vuln rollup data (fail-closed)"}
                       if missing else {}),
                })

    return {"pass": not violations, "violations": violations}


# ── outputs ──────────────────────────────────────────────────────────────────

def render_report(result: dict[str, Any]) -> str:
    rows = result["rows"]
    by_bucket: dict[str, list[dict[str, Any]]] = {b: [] for b in BUCKETS}
    for r in rows:
        by_bucket[r["bucket"]].append(r)
    lines = [
        "# inventory-match report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- atlas built_at: {result['built_at']}",
        f"- inputs: {', '.join(result['inputs']) or '(none)'}",
        f"- deps (deduped): {len(rows):,}",
        f"- freshness eligible-set basis: {result['freshness_basis']}",
    ]
    rc = result.get("resolution_counts")
    if rc:
        lines.append("- resolution: "
                     + " · ".join(f"{rc[k]} {k}" for k in ("locked", "resolved", "direct")))
    lc = result.get("live_cf_check")
    if lc:
        detail = (f" — checked {lc['checked']}, recovered {lc['recovered']}, "
                  f"absent-confirmed {lc['confirmed_absent']}"
                  if "checked" in lc else "")
        lines.append(f"- live cf cross-check (decision 4): {lc['basis']}{detail}")
    lines += [
        "",
        "## Buckets",
        "",
    ]
    for b in BUCKETS:
        lines.append(f"- {b}: {len(by_bucket[b]):,}")
    for b in BUCKETS:
        if not by_bucket[b]:
            continue
        lines += ["", f"## {b}", ""]
        ordered = sorted(by_bucket[b],
                         key=lambda r: (-(r.get("weight") or 0), r["name"]))
        for r in ordered:
            bits = [f"pinned {r['pinned'] or '(none)'}"]
            if r.get("conda_name"):
                bits.append(f"cf {r['conda_name']}@{r.get('cf_latest') or '?'}")
            if r.get("upstream_version"):
                bits.append(f"upstream {r['upstream_version']} ({r.get('upstream_source')})")
            if r.get("lag_releases"):
                lag_d = f", {r['lag_days']} d" if r.get("lag_days") is not None else ""
                bits.append(f"lag {r['lag_releases']} releases{lag_d}")
            if r.get("conda_forge_readiness") is not None:
                bits.append(f"readiness {r['conda_forge_readiness']}")
            if r.get("staged_recipes_pr_url"):
                bits.append(f"PR {r['staged_recipes_pr_url']}")
            if r.get("local_recipe"):
                bits.append("local recipe present")
            if r["pin_kind"] == "exact":
                f = r["freshness"]
                pct = f" p{f['percentile']:.2f}" if f["percentile"] is not None else ""
                bits.append(f"freshness {f['verdict']}{pct}")
            if r.get("match_confidence") and r["match_confidence"] not in ("exact", "verified"):
                bits.append(f"confidence {r['match_confidence']}")
            if r.get("version_comparison") == "unreliable":
                bits.append("version_comparison UNRELIABLE")
            if r.get("pin_conflict"):
                bits.append(f"PIN CONFLICT (also seen: {', '.join(r['pin_conflict'])})")
            if r.get("policy_tier") == "future":
                bits.append("policy: future")
            if r.get("upstream_yanked"):
                bits.append("upstream latest YANKED")
            if r.get("feedstock_archived"):
                bits.append("ARCHIVED feedstock")
            if r.get("atlas_stale"):
                bits.append("ATLAS STALE (live channeldata hit)")
            if r.get("live_cf_check") == "absent-confirmed":
                bits.append("absence live-confirmed")
            v = r.get("vulns")
            if v and (v["critical"] or v["high"] or v["kev"]):
                bits.append(f"vulns: {v['critical']}C/{v['high']}H/{v['kev']}KEV")
            if r.get("depth") is not None and r["depth"] > 0:
                bits.append(f"depth {r['depth']}")
            if r["signals_absent"]:
                bits.append(f"signals_absent: {', '.join(r['signals_absent'])}")
            if r.get("weight") is not None:
                bits.append(f"weight {r['weight']}")
            lines.append(f"- **{r['name']}** — {'; '.join(bits)}")
    pol = result.get("policy")
    if pol is not None:
        lines += ["", "## Policy gate", "",
                  f"- verdict: {'PASS' if pol['pass'] else 'FAIL'}"]
        for v in pol["violations"]:
            head = f"- {v['check']}: {v['actual']} > {v['limit']}"
            if v.get("note"):
                head += f" — {v['note']}"
            lines.append(head)
            if v["rows"]:
                lines.append(f"  - rows: {', '.join(v['rows'][:20])}"
                             + (" …" if len(v["rows"]) > 20 else ""))
    return "\n".join(lines) + "\n"


def annotate_sbom(
    sbom_path: Path, rows: list[dict[str, Any]], built_at: Any,
) -> dict[str, Any]:
    """--sbom-out: the INPUT CycloneDX BOM with `cfe:gap_status` /
    `cfe:conda_purl` per matched component + `cfe:atlas_built_at` stamped
    in metadata."""
    doc = json.loads(sbom_path.read_text(encoding="utf-8"))
    if doc.get("bomFormat") != "CycloneDX":
        raise ValueError("--sbom-out annotation requires a CycloneDX JSON --sbom-in")
    by_fold: dict[tuple[str, str], dict[str, Any]] = {}
    for r in rows:
        by_fold.setdefault((r["ecosystem"], fold_name(r["name"])), r)
    # purl-type → matcher ecosystem, mirroring parse_sbom_cyclonedx's
    # classification so ADD-NONPYPI rows (npm/cargo/…) annotate too and a
    # pkg:npm/redis never inherits the PyPI redis row's verdict.
    purl_eco = {"pypi": "pypi", "conda": "conda", "npm": "npm", "deb": "apt",
                "rpm": "dnf", "apk": "apk", "cargo": "cargo",
                "maven": "maven", "gem": "gem"}
    purl_type_re = re.compile(r"^pkg:([A-Za-z0-9.+-]+)/")
    for comp in doc.get("components") or []:
        name = comp.get("name") or ""
        purl = comp.get("purl") or ""
        m = purl_type_re.match(purl)
        row = None
        if m:
            eco = purl_eco.get(m.group(1).lower(), "generic")
            row = by_fold.get((eco, fold_name(name)))
        elif name:
            # purl-less components only: name-based fallback
            row = by_fold.get(("pypi", fold_name(name))) \
                or by_fold.get(("conda", fold_name(name)))
        if row is None:
            continue
        props = comp.setdefault("properties", [])
        props.append({"name": "cfe:gap_status", "value": row["bucket"]})
        if row.get("conda_purl"):
            props.append({"name": "cfe:conda_purl", "value": row["conda_purl"]})
    # an explicit `"metadata": null` makes setdefault return None — guard
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
        doc["metadata"] = metadata
    meta_props = metadata.setdefault("properties", [])
    meta_props.append({"name": "cfe:atlas_built_at", "value": str(built_at)})
    return doc


# ── main ─────────────────────────────────────────────────────────────────────

def run(
    conn: sqlite3.Connection,
    deps: list[Any],
    inputs: list[str],
    weights: dict[str, float] | None = None,
    policy: dict[str, Any] | None = None,
    version_provider: Callable[[str], list[str] | None] | None = None,
    live_cf: dict[str, Any] | None = None,
    live_cf_mode: str = "disabled",
) -> dict[str, Any]:
    """`live_cf` is the live channeldata packages map (decision-4 post-pass)
    or None; `live_cf_mode` records why it is absent ('disabled' — the web /
    --offline behavior — or 'unavailable' — fetch failed, G74 residual)."""
    inv_rows = dedupe_deps(deps)
    provider = version_provider or history_version_provider(conn)
    rows = match_inventory(conn, inv_rows, weights=weights,
                           version_provider=provider)
    live_cf_result: dict[str, Any] = {"basis": live_cf_mode}
    if live_cf is not None:
        live_cf_result = {"basis": "channeldata.json (live)",
                          **apply_live_cf_check(rows, live_cf)}
    built = None
    try:
        built = conn.execute("SELECT value FROM meta WHERE key='built_at'").fetchone()
        built = built[0] if built else None
    except sqlite3.Error:
        pass
    result: dict[str, Any] = {
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "built_at": built,
        "inputs": inputs,
        "freshness_basis": getattr(provider, "basis", "injected"),
        "live_cf_check": live_cf_result,
        "resolution_counts": {
            res: sum(1 for r in rows if r["resolution"] == res)
            for res in ("locked", "resolved", "direct")},
        "counts": {b: sum(1 for r in rows if r["bucket"] == b) for b in BUCKETS},
        "rows": rows,
    }
    if policy is not None:
        result["policy"] = evaluate_policy(rows, policy)
    return result


class _ExitOneArgumentParser(argparse.ArgumentParser):
    """argparse exits 2 on usage errors — but exit 2 is RESERVED for the
    policy-gate FAIL verdict here, so usage errors must exit 1."""

    def error(self, message: str):  # type: ignore[override]
        self.print_usage(sys.stderr)
        sys.stderr.write(f"error: {message}\n")
        sys.exit(1)


def main() -> int:
    parser = _ExitOneArgumentParser(
        description="Match a user inventory against the conda-forge atlas "
                    "(gap + version-lag buckets; optional CI policy gate).")
    parser.add_argument("inputs", nargs="*", type=Path,
                        help="Manifest/lock/text files or project directories")
    parser.add_argument("--format", choices=sorted(FORMAT_PARSERS),
                        help="Force the parser for FILE inputs (needed for "
                             "pip/conda list text with non-canonical names)")
    parser.add_argument("--sbom-in", type=Path, default=None,
                        help="CycloneDX/SPDX JSON SBOM input (annotation source "
                             "for --sbom-out)")
    parser.add_argument("--conda-env", type=Path, default=None,
                        help="Live conda env prefix (reads conda-meta/ offline)")
    parser.add_argument("--venv", type=Path, default=None,
                        help="Python venv path (reads site-packages dist-info)")
    parser.add_argument("--policy", type=Path, default=None,
                        help="Policy thresholds (JSON or TOML); violations → exit 2")
    parser.add_argument("--weights", type=Path, default=None,
                        help="Criticality sidecar (csv `name,weight` or JSON object)")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH,
                        help=f"Markdown report path (default {DEFAULT_REPORT_PATH})")
    parser.add_argument("--json", action="store_true",
                        help="Emit the full result as JSON on stdout")
    parser.add_argument("--sbom-out", type=Path, default=None,
                        help="Write the --sbom-in BOM annotated with "
                             "cfe:gap_status / cfe:conda_purl")
    parser.add_argument("--allow-stale", action="store_true",
                        help="Bypass the 14-day atlas freshness gate (decision 6)")
    parser.add_argument("--offline", action="store_true",
                        help="Web-slice behavior: no transitive resolver, no "
                             "live channeldata cross-check, offline "
                             "(history-based) freshness eligible sets")
    parser.add_argument("--no-resolve", action="store_true",
                        help="Keep bare-manifest rows `resolution: direct` "
                             "(skip the pip / conda transitive resolver)")
    parser.add_argument("--no-live-cf", action="store_true",
                        help="Skip the decision-4 live channeldata "
                             "cross-check of missing-from-cf declarations")
    parser.add_argument("--python-version", default=None,
                        help="Runtime Python X.Y[.Z] for the live "
                             "eligible-set requires-python filter "
                             "(default: this interpreter)")
    args = parser.parse_args()

    if not (args.inputs or args.sbom_in or args.conda_env or args.venv):
        parser.error("no inputs given (files, directories, --sbom-in, "
                     "--conda-env, or --venv)")
    if args.sbom_out and not args.sbom_in:
        parser.error("--sbom-out requires --sbom-in (it annotates the input BOM)")

    if not DB_PATH.exists():
        sys.stderr.write(
            f"cf_atlas.db not found at {DB_PATH}. "
            "Run `pixi run -e local-recipes build-cf-atlas` first.\n")
        return 1

    deps: list[Any] = []
    labels: list[str] = []
    warnings: list[str] = []
    if args.inputs:
        deps, labels, warnings = load_inventory(args.inputs, args.format)
    if args.sbom_in:
        fmt = detect_format(args.sbom_in)
        if fmt not in ("cyclonedx", "spdx"):
            sys.stderr.write(f"--sbom-in {args.sbom_in}: not a recognizable "
                             "CycloneDX/SPDX JSON SBOM\n")
            return 1
        if args.sbom_out and fmt != "cyclonedx":
            sys.stderr.write("--sbom-out annotation requires a CycloneDX "
                             "--sbom-in (SPDX input cannot be annotated)\n")
            return 1
        deps.extend(_stamp_resolution(FORMAT_PARSERS[fmt](args.sbom_in), fmt))
        labels.append(str(args.sbom_in))
    if args.conda_env:
        deps.extend(_stamp(sp.parse_conda_meta_dir(args.conda_env), "locked", "tool"))
        labels.append(f"conda-env:{args.conda_env}")
    if args.venv:
        deps.extend(_stamp(sp.parse_python_venv(args.venv), "locked", "tool"))
        labels.append(f"venv:{args.venv}")
    if not deps:
        for w in warnings:
            sys.stderr.write(f"  warn: {w}\n")
        sys.stderr.write("no dependencies parsed from any input\n")
        return 1

    resolve_on = not (args.offline or args.no_resolve)
    live_cf_on = not (args.offline or args.no_live_cf)
    if resolve_on and any(d.extras.get("resolution") == "direct" for d in deps):
        resolve_transitive(deps, warnings)
    for w in warnings:
        sys.stderr.write(f"  warn: {w}\n")

    try:
        weights = load_weights(args.weights) if args.weights else None
        policy = load_policy(args.policy) if args.policy else None
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"could not load policy/weights: {exc}\n")
        return 1

    conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    try:
        check_freshness(conn, args.allow_stale)
        provider = (None if args.offline
                    else live_pypi_version_provider(
                        conn, py_version=args.python_version))
        channeldata = fetch_live_channeldata() if live_cf_on else None
        live_cf_mode = "disabled"
        if live_cf_on and channeldata is None:
            live_cf_mode = "unavailable"
            sys.stderr.write(
                "  warn: live channeldata unreachable — missing-from-cf "
                "declarations are atlas-only (G74 residual risk)\n")
        result = run(conn, deps, labels, weights=weights, policy=policy,
                     version_provider=provider, live_cf=channeldata,
                     live_cf_mode=live_cf_mode)
        if args.sbom_out:
            annotated = annotate_sbom(args.sbom_in, result["rows"],
                                      result["built_at"])
            args.sbom_out.parent.mkdir(parents=True, exist_ok=True)
            args.sbom_out.write_text(
                json.dumps(annotated, indent=2, sort_keys=False) + "\n",
                encoding="utf-8")
    except StaleAtlasError as exc:
        sys.stderr.write(f"REFUSED: {exc}\n")
        return 1
    except (sqlite3.OperationalError, ValueError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1
    finally:
        conn.close()

    report_text = render_report(result)
    try:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report_text, encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"  warn: could not write report to {args.report}: {exc}\n")

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        sys.stdout.write(report_text)

    if result.get("policy") is not None and not result["policy"]["pass"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
