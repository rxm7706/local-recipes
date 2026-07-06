#!/usr/bin/env python3
"""
library-futures — 2027–2030 survival scoring for conda-forge packages
(cyclonedx-universe-inventory Wave D / S7).

Per matched conda-forge package IN ANY ECOSYSTEM, computes a transparent
WEIGHTED COMPOSITE (not ML): a `futures_score` (0-100) and a `futures_tier`
(keep / watch / plan-migration / replace). Each signal is a named,
documented sub-score; the weights + dated thresholds live in ONE auditable
dict (`DEFAULT_WEIGHTS`); the per-signal breakdown rides on every row so a
human can audit any verdict.

Composite (decision 5, "no silent zeros"): each signal scorer returns
`(subscore|None, present)`. The score renormalizes over PRESENT weights
only — a missing signal shrinks the denominator, never contributes a zero.
Signals that don't APPLY (Python-only signals on a Rust CLI) are excluded
from the denominator entirely and reported once as
`python-enrichment (n/a: non-python)`; signals that apply but are NULL land
in `signals_absent`.

Tier = a lattice meet over `replace > plan-migration > watch > keep`:
    tier = reduce(worse, [base_band] + caps + floors)
The most-severe candidate always wins, so ordering is irrelevant. Caps:
py314-not-ready (Python), 18-month silence. Floors: archived feedstock,
yanked latest, product fully EOL, pinned line EOL before the 2027 window.
`replace` (bottom band, or plan-migration escalated when archived AND a
healthier alternative exists) auto-attaches `find-alternative` suggestions.

Horizon signals (decision 5, both hard bounds on the tier):
  • Python 3.14 readiness — offline from python_tags + classifiers +
    requires_python (PyPI side) corroborated by
    package_python_downloads.pkg_python (conda side).
  • LTS + EOL — endoflife.date API v1 → lts-registry.yaml → lts-like
    heuristic. The live fetch is the LOCAL wave; this module uses an
    injectable EolClient (fake fetcher in tests, cached JSON offline).

Read-only + offline (reads cf_atlas.db, the git-tracked lts-registry.yaml,
and a TTL'd eol_cache.json). NOT an MCP tool — consumed by recommend-2027
(S8) and available as a standalone CLI. The spec's annotated-BOM properties
(`cfe:py314_readiness` / `cfe:lts_status`) are S8's `--sbom-out` job — S7
exposes both as explicit row columns for S8 to annotate. EPSS/CWE ride each
row's `vuln_enrichment` REPORT-ONLY (stale rollup; never scored).

CLI:
  library-futures [--package NAME ...] [INVENTORY ...] [--json] [--allow-stale]
"""
from __future__ import annotations

import argparse
import datetime as dt
import functools
import json
import math
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Callable

from conda_forge_atlas import _OSI_APPROVED_SPDX, _normalize_license_to_spdx
from universe_sbom import StaleAtlasError, check_freshness
import find_alternative


def _get_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent / "data" / "conda-forge-expert"


DB_PATH = _get_data_dir() / "cf_atlas.db"
EOL_CACHE_PATH = _get_data_dir() / "eol_cache.json"           # runtime, gitignored
REGISTRY_PATH = Path(__file__).resolve().parent.parent / "data" / "lts-registry.yaml"

# Tier severity chain (worst → best). worse(a,b) = the more-severe tier.
TIERS = ("replace", "plan-migration", "watch", "keep")
_SEVERITY = {t: i for i, t in enumerate(TIERS)}   # replace=0 (worst)


def worse(a: str, b: str) -> str:
    return a if _SEVERITY[a] <= _SEVERITY[b] else b


# ── the single auditable weights + thresholds dict ──────────────────────────

DEFAULT_WEIGHTS: dict[str, Any] = {
    "as_of": "2026-07-06",
    "window": (2027, 2030),
    # signal → {weight, applies: "all" | "python"}. subscore is always
    # normalized to [0,100] (higher = healthier / more keep-worthy).
    "signals": {
        # ecosystem-agnostic backbone (present for ~all cf packages)
        "upstream_freshness":   {"weight": 12, "applies": "all"},
        "release_cadence":      {"weight": 8,  "applies": "all"},
        "adoption_stage":       {"weight": 6,  "applies": "all"},
        "conda_downloads":      {"weight": 8,  "applies": "all"},   # PORTABLE
        "vuln_posture":         {"weight": 14, "applies": "all"},
        "feedstock_health":     {"weight": 10, "applies": "all"},
        "license_quality":      {"weight": 8,  "applies": "all"},
        "blast_radius":         {"weight": 6,  "applies": "all"},
        "user_weight":          {"weight": 4,  "applies": "all"},   # S5 sidecar
        "freshness_policy":     {"weight": 6,  "applies": "all"},   # S5 percentile
        "graph_depth_fanout":   {"weight": 4,  "applies": "all"},   # S5 resolver
        # Python-only enrichment layer
        "py_activity_band":     {"weight": 4,  "applies": "python"},
        "packaging_health":     {"weight": 4,  "applies": "python"},
        "metadata_complete":    {"weight": 3,  "applies": "python"},
        "cross_channel_redund": {"weight": 2,  "applies": "python"},
        # NEVER SCORED: PyPI downloads (non-portable — a credential-less
        # rebuild loses them), bus_factor_proxy / dependency_blast_radius
        # (NULL placeholders). EPSS + CWE exist only on the STALE packages
        # rollup (not the query-time-correct view) — surfaced REPORT-ONLY
        # via each row's `vuln_enrichment`, excluded from the composite.
    },
    "horizon": {
        "py314_not_ready_cap": "watch",
        "silence_cap": "watch",
        "silence_cap_days": 547,          # 18 months, dated
        "archived_floor": "plan-migration",
        "yanked_latest_floor": "plan-migration",
        "product_eol_floor": "plan-migration",
        "eol_before_window_floor": "plan-migration",
        "window_start_year": 2027,
    },
    "tier_bands": {"keep": 70, "watch": 45, "plan-migration": 25},  # else replace
    "min_present_weight_frac": 0.35,
    # decision 5(a): `py314-likely` requires a release WITHIN the 3.14 cycle
    "py314_cycle_start": "2025-10-07",
}

_PY314_CYCLE_START_TS = int(dt.datetime(2025, 10, 7,
                                        tzinfo=dt.timezone.utc).timestamp())


# ── LTS registry + endoflife.date client ────────────────────────────────────

def load_lts_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    """Parse lts-registry.yaml → {alias_lower: entry}. Missing/unparseable
    file → empty map (the client falls back to bare-name slugs)."""
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return {}
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(doc, dict):
        return {}
    index: dict[str, Any] = {}
    for name, entry in (doc.get("products") or {}).items():
        if not isinstance(entry, dict):
            continue
        entry = {**entry, "_name": name}
        for key in [name, *(entry.get("aliases") or [])]:
            index[str(key).lower()] = entry
    return index


def _parse_iso_date(v: Any) -> dt.date | None:
    # YAML auto-parses `2028-12-31` into a date; endoflife JSON gives strings.
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    if not isinstance(v, str):
        return None
    try:
        return dt.date.fromisoformat(v[:10])
    except ValueError:
        return None


class EolClient:
    """endoflife.date lookups with a TTL'd file cache + injectable fetcher.

    `fetcher(slug) -> list[cycle] | None` — the default is _http-backed
    (LOCAL wave); tests inject a fake. Offline / fetch failure → newest
    stale cache entry (stale=True + a report age-warning), else `unknown`.
    Never raises on a lookup — a missing product is `unknown`, not a crash.
    """

    def __init__(
        self,
        cache_path: Path = EOL_CACHE_PATH,
        fetcher: Callable[[str], list | None] | None = None,
        registry: dict[str, Any] | None = None,
        ttl_days: int = 7,
        now: int | None = None,
    ) -> None:
        self.cache_path = cache_path
        self.fetcher = fetcher if fetcher is not None else _http_eol_fetcher
        self.registry = registry if registry is not None else load_lts_registry()
        self.ttl_seconds = ttl_days * 86400
        self.now = now if now is not None else int(time.time())
        self._cache = self._load_cache()

    def _load_cache(self) -> dict[str, Any]:
        try:
            doc = json.loads(self.cache_path.read_text(encoding="utf-8"))
            return doc if isinstance(doc, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save_cache(self) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(
                json.dumps(self._cache, indent=2), encoding="utf-8")
        except OSError:
            pass

    def resolve_slug(self, name: str) -> tuple[str | None, dict[str, Any] | None]:
        """(slug, registry_entry). Registry alias/slug first, then the bare
        lowercase name as a slug (endoflife covers many by bare name)."""
        entry = self.registry.get(name.lower())
        if entry is not None:
            return entry.get("slug"), entry
        return name.lower(), None

    def _cycles(self, slug: str) -> tuple[list | None, str, bool]:
        """(cycles, source, stale). Fresh cache → cache; else fetch + store;
        fetch fail → stale cache; nothing → (None, 'cache-miss-offline')."""
        cached = self._cache.get(slug)
        if cached and (self.now - cached.get("fetched_at", 0)) < self.ttl_seconds:
            return cached.get("cycles"), "endoflife", False
        fetched = None
        try:
            fetched = self.fetcher(slug)
        except Exception:
            fetched = None
        if fetched is not None:
            self._cache[slug] = {"fetched_at": self.now, "cycles": fetched}
            self._save_cache()
            return fetched, "endoflife", False
        if cached and cached.get("cycles") is not None:
            return cached["cycles"], "endoflife", True   # stale fallback
        return None, "cache-miss-offline", False

    def lts_status(self, name: str, pinned_line: str | None = None) -> dict[str, Any]:
        result: dict[str, Any] = {
            "lts_status": "unknown", "eol_date": None,
            "product_fully_eol": False, "pinned_line_eol_before_window": False,
            "source": None, "stale": False,
        }
        slug, entry = self.resolve_slug(name)
        window_start = DEFAULT_WEIGHTS["horizon"]["window_start_year"]

        # Manual / heuristic-seed registry entries (endoflife lacks the product)
        if entry is not None and entry.get("source") in ("manual", "heuristic-seed"):
            result["source"] = entry["source"]
            if entry.get("source") == "heuristic-seed":
                result["lts_status"] = "lts-like"
                return result
            return self._from_manual_lines(entry, pinned_line, window_start, result)

        if not slug:
            result["source"] = "registry"
            return result

        cycles, source, stale = self._cycles(slug)
        result["source"], result["stale"] = source, stale
        if not cycles:
            return result       # unknown — no cap/floor, treated as absent
        return self._from_cycles(cycles, pinned_line, window_start, result)

    def _is_eol(self, v: Any) -> bool:
        """endoflife `eol` is a bool OR a date; True / a date past the
        client's `now` → EOL (deterministic — uses self.now, not wall-clock)."""
        if v is True:
            return True
        if v is False or v is None:
            return False
        d = _parse_iso_date(v)
        return _past(d, self.now) if d else False

    def _from_cycles(self, cycles, pinned_line, window_start, result):
        any_lts = False
        all_eol = True
        pinned = None
        for c in cycles:
            if not isinstance(c, dict):
                continue
            if _lts_truthy(c.get("lts")):
                any_lts = True
            if not self._is_eol(c.get("eol")):
                all_eol = False
            if pinned_line and str(c.get("cycle")) == str(pinned_line):
                pinned = c
        result["product_fully_eol"] = all_eol
        if pinned is not None:
            eol_date = _parse_iso_date(pinned.get("eol"))
            result["eol_date"] = eol_date.isoformat() if eol_date else None
            if eol_date and eol_date.year < window_start:
                result["pinned_line_eol_before_window"] = True
            if _lts_truthy(pinned.get("lts")) and not self._is_eol(pinned.get("eol")):
                result["lts_status"] = "lts-supported"
            elif any_lts:
                result["lts_status"] = "lts-available"
            else:
                result["lts_status"] = "none"
        else:
            result["lts_status"] = "lts-available" if any_lts else "none"
        return result

    def _from_manual_lines(self, entry, pinned_line, window_start, result):
        lines = entry.get("lts_lines") or []
        any_lts = any(ln.get("lts") for ln in lines if isinstance(ln, dict))
        all_eol = True
        for ln in lines:
            if isinstance(ln, dict) and not _past(_parse_iso_date(ln.get("eol")), self.now):
                all_eol = False
        result["product_fully_eol"] = all_eol and bool(lines)
        pinned = next((ln for ln in lines if isinstance(ln, dict)
                       and str(ln.get("line")) == str(pinned_line)), None)
        if pinned is not None:
            eol = _parse_iso_date(pinned.get("eol"))
            result["eol_date"] = eol.isoformat() if eol else None
            if eol and eol.year < window_start:
                result["pinned_line_eol_before_window"] = True
            result["lts_status"] = ("lts-supported"
                                    if pinned.get("lts") and not _past(eol, self.now)
                                    else ("lts-available" if any_lts else "none"))
        else:
            result["lts_status"] = "lts-available" if any_lts else "none"
        return result


def _lts_truthy(v: Any) -> bool:
    return v is True or (isinstance(v, str) and v not in ("", "false", "False"))


def _past(d: dt.date | None, now_ts: int) -> bool:
    if d is None:
        return False
    return d < dt.datetime.fromtimestamp(now_ts, dt.timezone.utc).date()


def _http_eol_fetcher(slug: str) -> list | None:
    """Default LOCAL-wave fetcher: endoflife.date /api/<slug>.json via _http
    (mirror-routable, truststore-injected, skip_auth — public host)."""
    try:
        from _http import make_request, open_url, resolve_endoflife_urls
    except Exception:
        return None
    for url in resolve_endoflife_urls(slug):
        try:
            with open_url(make_request(url, skip_auth=True)) as resp:
                doc = json.load(resp)
            if isinstance(doc, list):
                return doc
        except Exception:
            continue
    return None


# ── Python 3.14 readiness (pure) ────────────────────────────────────────────

def py314_readiness(
    python_tags: Any, classifiers: Any, requires_python: str | None,
    pkg_pythons: list[str] | None, packaging_shape: str | None, is_py: bool,
    latest_upload_at: int | None = None,
) -> str:
    """`py314-ready` / `py314-likely` / `py314-not-ready` / `unknown`;
    non-Python → `unknown` (absent). Pure over already-extracted values.
    Per decision 5(a), `py314-likely` requires pure-python AND
    requires_python not excluding 3.14 AND a release within the 3.14 cycle
    (latest_upload_at >= 2025-10-07); an unknown/older upload stays
    `unknown` — recency is a claim, not a default."""
    if not is_py:
        return "unknown"
    tags = _as_list(python_tags)
    clsf = _as_list(classifiers)
    has_314_tag = any("314" in str(t) for t in tags)
    has_314_clsf = any(":: 3.14" in str(c) for c in clsf)
    has_314_conda = any(str(p) == "3.14" for p in (pkg_pythons or []))
    if has_314_tag or has_314_clsf or has_314_conda:
        return "py314-ready"
    # explicit upper cap below 3.14 → not ready
    rp = requires_python or ""
    if _requires_python_excludes_314(rp):
        return "py314-not-ready"
    is_pure = packaging_shape == "pure-python"
    compiled = packaging_shape in ("cython", "c-extension", "rust-pyo3", "fortran")
    if is_pure:
        if latest_upload_at is not None and latest_upload_at >= _PY314_CYCLE_START_TS:
            return "py314-likely"
        return "unknown"
    if compiled:
        # compiled with no cp314 wheel/build evidence → not ready
        return "py314-not-ready"
    return "unknown"


def _requires_python_excludes_314(rp: str) -> bool:
    """True when requires_python has an upper bound below 3.14
    (e.g. `>=3.8,<3.14`, `<3.13`) or an explicit `!=3.14` exclusion.
    Best-effort string parse."""
    import re
    if re.search(r"!=\s*3\.14(\.\*)?", rp):
        return True
    for m in re.finditer(r"<=?\s*3\.(\d+)", rp):
        minor = int(m.group(1))
        # `<3.14` excludes; `<=3.13` excludes; `<3.15` does not
        if "<=" in rp[max(0, m.start() - 1):m.end()]:
            if minor < 14:
                return True
        elif minor <= 14:
            return True
    return False


def _as_list(v: Any) -> list:
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            parsed = json.loads(v)
            return parsed if isinstance(parsed, list) else [v]
        except json.JSONDecodeError:
            return [v]
    return []


# ── per-signal scorers: (conn, conda_name, row) → (subscore|None, present) ───

def _pkg_row(conn: sqlite3.Connection, conda_name: str) -> dict[str, Any] | None:
    cur = conn.execute(
        "SELECT pypi_name, latest_conda_version, latest_conda_upload, "
        "total_downloads, downloads_90d, downloads_source, downloads_fetched_at, "
        "conda_license, feedstock_archived, feedstock_bad, "
        "bot_version_errors_count, gh_default_branch_status "
        "FROM packages WHERE conda_name = ?", (conda_name,))
    r = cur.fetchone()
    if r is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, r))


def is_python(pkg: dict[str, Any] | None, row: dict[str, Any]) -> bool:
    if row.get("ecosystem") == "pypi":
        return True
    return bool(pkg and pkg.get("pypi_name"))


def _score_upstream_freshness(conn, conda_name, row, pkg):
    up = row.get("upstream_version")
    lag = row.get("lag_releases")
    if up is None and lag is None:
        return None, False
    base = 100.0 if not lag else max(0.0, 100.0 - lag * 15.0)
    if (row.get("lag_days") or 0) > 365:
        base = min(base, 40.0)
    if pkg and pkg.get("gh_default_branch_status") in ("failure", "error"):
        base = max(0.0, base - 20.0)
    return base, True


def _score_release_cadence(conn, conda_name, row, pkg):
    import release_cadence as rc
    now = int(time.time())
    rows = conn.execute(
        "SELECT upload_unix FROM package_version_downloads "
        "WHERE conda_name = ? AND upload_unix IS NOT NULL", (conda_name,)).fetchall()
    if not rows:
        return None, False
    uploads = [r[0] for r in rows]
    r30 = sum(1 for u in uploads if u >= now - 30 * 86400)
    r90 = sum(1 for u in uploads if u >= now - 90 * 86400)
    r365 = sum(1 for u in uploads if u >= now - 365 * 86400)
    cls = rc._classify(r30, r90, r365)
    return {"accelerating": 100, "stable": 80, "decelerating": 45,
            "one-version": 40, "silent": 15}.get(cls, 40), True


def _score_adoption(conn, conda_name, row, pkg):
    import adoption_stage as ad
    now = int(time.time())
    total = conn.execute(
        "SELECT COUNT(DISTINCT version) FROM package_version_downloads "
        "WHERE conda_name = ?", (conda_name,)).fetchone()[0]
    upload = pkg.get("latest_conda_upload") if pkg else None
    if not upload:
        return None, False
    age_days = (now - upload) / 86400
    r30 = conn.execute(
        "SELECT COUNT(*) FROM package_version_downloads WHERE conda_name = ? "
        "AND upload_unix >= ?", (conda_name, now - 30 * 86400)).fetchone()[0]
    cls = ad._classify(age_days, r30, total)
    return {"bleeding-edge": 90, "stable": 100, "mature": 75,
            "declining": 40, "silent": 15}.get(cls), cls != "unknown"


def _score_conda_downloads(conn, conda_name, row, pkg):
    if not pkg or pkg.get("downloads_90d") is None:
        return None, False
    dl = pkg["downloads_90d"] or 0
    return min(100.0, 20.0 + 12.0 * math.log10(1 + dl)), True


def _score_vuln_posture(conn, conda_name, row, pkg):
    r = conn.execute(
        "SELECT vuln_critical_current, vuln_high_current, vuln_kev_current, "
        "vuln_scanned_at FROM v_current_version_vulns WHERE conda_name = ?",
        (conda_name,)).fetchone()
    if r is None or r[3] is None:
        return None, False
    crit, high, kev = r[0] or 0, r[1] or 0, r[2] or 0
    return max(0.0, 100.0 - crit * 30.0 - high * 10.0 - kev * 25.0), True


def _score_feedstock_health(conn, conda_name, row, pkg):
    # feedstock_archived is a FLOOR, not scored here (no double-count).
    if pkg is None:
        return None, False
    base = 100.0
    if pkg.get("feedstock_bad"):
        base -= 40.0
    if (pkg.get("bot_version_errors_count") or 0) > 0:
        base -= 20.0
    return max(0.0, base), True


def _score_license_quality(conn, conda_name, row, pkg):
    raw = (pkg.get("conda_license") if pkg else None) or row.get("conda_license")
    if not raw:
        return None, False
    spdx = _normalize_license_to_spdx(raw)
    if spdx and spdx in _OSI_APPROVED_SPDX:
        return 100.0, True
    if spdx:
        return 60.0, True
    return 40.0, True   # present but unparseable


def _score_blast_radius(conn, conda_name, row, pkg):
    n = conn.execute(
        "SELECT COUNT(*) FROM dependencies WHERE target_conda_name = ? "
        "AND requirement_type IN ('run', 'host')", (conda_name,)).fetchone()[0]
    return min(100.0, 20.0 + 15.0 * math.log10(1 + n)), True


def _score_user_weight(conn, conda_name, row, pkg):
    w = row.get("weight")
    if w is None:
        return None, False
    # clamp BOTH ends — a negative sidecar weight must not drag the
    # composite below zero
    return max(0.0, min(100.0, 40.0 + float(w) * 12.0)), True


def _score_freshness_policy(conn, conda_name, row, pkg):
    fr = row.get("freshness") or {}
    verdict = fr.get("verdict")
    score = {"pass": 100.0, "warn": 60.0, "fail": 25.0}.get(verdict) if verdict else None
    return score, score is not None


def _score_graph_depth_fanout(conn, conda_name, row, pkg):
    depth, fanout = row.get("depth"), row.get("fanout")
    if depth is None and fanout is None:
        return None, False
    base = 30.0
    if depth == 0:
        base += 30.0      # a direct dependency of the user's roots
    base += min(40.0, (fanout or 0) * 8.0)
    return min(100.0, base), True


def _intel_row(conn, pypi_name):
    cur = conn.execute(
        "SELECT activity_band, has_wheel, has_sdist, packaging_shape, "
        "latest_yanked, latest_upload_at, repo_url, docs_url, classifiers, "
        "requires_python, python_tags, json_fetched_at, cross_channel_at, "
        "in_bioconda, in_pytorch, in_nvidia, in_robostack, in_homebrew, "
        "in_nixpkgs, in_spack, in_debian, in_fedora "
        "FROM v_pypi_intelligence_valid WHERE pypi_name = ?", (pypi_name,))
    r = cur.fetchone()
    if r is None:
        return None
    return dict(zip([d[0] for d in cur.description], r))


def _score_py_activity_band(intel):
    # serial deltas are the Phase-O inputs that COMPUTE activity_band —
    # scoring the band scores the deltas; they are not a second signal.
    if not intel or not intel.get("activity_band"):
        return None, False
    score = {"hot": 100.0, "warm": 75.0, "cold": 45.0,
             "dormant": 15.0}.get(intel["activity_band"])
    return score, score is not None


def _score_packaging_health(intel):
    if not intel or intel.get("json_fetched_at") is None:
        return None, False
    if intel.get("latest_yanked"):
        return 10.0, True
    score = 0.0
    if intel.get("has_sdist"):
        score += 40.0
    if intel.get("has_wheel"):
        score += 30.0
    shape = intel.get("packaging_shape")
    score += 30.0 if shape == "pure-python" else (15.0 if shape else 0.0)
    return min(100.0, score), True


def _score_metadata_complete(intel):
    if not intel or intel.get("json_fetched_at") is None:
        return None, False
    present = sum(1 for k in ("repo_url", "docs_url", "classifiers",
                              "requires_python") if intel.get(k))
    return present / 4.0 * 100.0, True


def _score_cross_channel_redund(intel):
    if not intel or intel.get("cross_channel_at") is None:
        return None, False
    n = sum(1 for k in ("in_bioconda", "in_pytorch", "in_nvidia", "in_robostack",
                        "in_homebrew", "in_nixpkgs", "in_spack", "in_debian",
                        "in_fedora") if intel.get(k))
    return min(100.0, 30.0 + n * 15.0), True


_BACKBONE_SCORERS = {
    "upstream_freshness": _score_upstream_freshness,
    "release_cadence": _score_release_cadence,
    "adoption_stage": _score_adoption,
    "conda_downloads": _score_conda_downloads,
    "vuln_posture": _score_vuln_posture,
    "feedstock_health": _score_feedstock_health,
    "license_quality": _score_license_quality,
    "blast_radius": _score_blast_radius,
    "user_weight": _score_user_weight,
    "freshness_policy": _score_freshness_policy,
    "graph_depth_fanout": _score_graph_depth_fanout,
}
_PYTHON_SCORERS = {
    "py_activity_band": _score_py_activity_band,
    "packaging_health": _score_packaging_health,
    "metadata_complete": _score_metadata_complete,
    "cross_channel_redund": _score_cross_channel_redund,
}


# ── composite + tier ────────────────────────────────────────────────────────

def compute_composite(subscores, weights, is_py):
    """subscores: {signal: (value|None, present)}. Returns
    (score|None, breakdown, absent, confidence)."""
    sigs = weights["signals"]
    applicable = [s for s, meta in sigs.items()
                  if meta["applies"] == "all" or (meta["applies"] == "python" and is_py)]
    num = denom = 0.0
    breakdown: dict[str, Any] = {}
    absent: list[str] = []
    for s in applicable:
        w = sigs[s]["weight"]
        val, present = subscores.get(s, (None, False))
        breakdown[s] = {"subscore": round(val, 1) if val is not None else None,
                        "weight": w, "present": present}
        if present and val is not None:
            num += w * val
            denom += w
        else:
            absent.append(s)
    score = round(num / denom, 1) if denom else None
    total_applicable_w = sum(sigs[s]["weight"] for s in applicable)
    frac = denom / total_applicable_w if total_applicable_w else 0.0
    confidence = "low" if frac < weights["min_present_weight_frac"] else "ok"
    return score, breakdown, absent, confidence


def band_from_score(score, weights):
    if score is None:
        return "watch"      # no score at all → cautious middle, not keep
    b = weights["tier_bands"]
    if score >= b["keep"]:
        return "keep"
    if score >= b["watch"]:
        return "watch"
    if score >= b["plan-migration"]:
        return "plan-migration"
    return "replace"


def derive_tier(conn, score, row, pkg, py314, lts, weights):
    """The lattice meet: most-severe of the base band + all caps + all
    floors. Returns (tier, reasons, alternatives)."""
    h = weights["horizon"]
    base = band_from_score(score, weights)
    candidates: list[tuple[str, str]] = [(base, f"score band {base} ({score})")]
    is_py = is_python(pkg, row)

    if is_py and py314 == "py314-not-ready":
        candidates.append((h["py314_not_ready_cap"], "py314-not-ready caps at watch"))
    if _silent_18mo(conn, row, pkg, weights):
        candidates.append((h["silence_cap"], ">18mo silence caps at watch"))
    if pkg and pkg.get("feedstock_archived"):
        candidates.append((h["archived_floor"], "archived feedstock"))
    if row.get("upstream_yanked") or (pkg and _latest_yanked(conn, pkg)):
        candidates.append((h["yanked_latest_floor"], "latest release yanked"))
    if lts.get("product_fully_eol"):
        candidates.append((h["product_eol_floor"], "product fully EOL"))
    if lts.get("pinned_line_eol_before_window"):
        candidates.append((h["eol_before_window_floor"],
                           f"pinned line EOL before {h['window_start_year']}"))

    tier = functools.reduce(worse, [c[0] for c in candidates])
    reasons = [why for t, why in candidates if t == tier]

    alternatives: list[dict[str, Any]] = []
    # escalate plan-migration → replace only when archived AND a healthier
    # alternative exists (somewhere to go); attach suggestions on any replace.
    if tier == "plan-migration" and pkg and pkg.get("feedstock_archived") \
            and row.get("conda_name"):
        alts = find_alternative.find_alternatives(row["conda_name"], limit=3, conn=conn)
        if alts:
            tier = "replace"
            reasons.append("archived with healthier alternatives → replace")
            alternatives = alts
    elif tier == "replace" and row.get("conda_name"):
        alternatives = find_alternative.find_alternatives(row["conda_name"], limit=3, conn=conn)
    return tier, reasons, alternatives


def _silent_18mo(conn, row, pkg, weights):
    days = weights["horizon"]["silence_cap_days"]
    upload = pkg.get("latest_conda_upload") if pkg else None
    if not upload:
        return False
    age = (int(time.time()) - upload) / 86400
    if age <= days:
        return False
    # AND no upstream movement: no positive lag and no failing CI churn signal
    upstream_moving = bool(row.get("lag_releases"))
    return not upstream_moving


def _latest_yanked(conn, pkg):
    if not pkg or not pkg.get("pypi_name"):
        return False
    r = conn.execute(
        "SELECT latest_yanked FROM v_pypi_intelligence_valid WHERE pypi_name = ?",
        (pkg["pypi_name"],)).fetchone()
    return bool(r and r[0])


# ── row scoring ──────────────────────────────────────────────────────────────

_SCOREABLE_BUCKETS = {"CURRENT", "UPDATE-FEEDSTOCK", "UPDATE-PIN", "UNKNOWN"}


def score_row(conn, row, weights, eol_client, now):
    conda_name = row.get("conda_name")
    pkg = _pkg_row(conn, conda_name) if conda_name else None
    is_py = is_python(pkg, row)

    subscores: dict[str, Any] = {}
    for name, fn in _BACKBONE_SCORERS.items():
        subscores[name] = fn(conn, conda_name, row, pkg) if conda_name else (None, False)
    intel = _intel_row(conn, pkg["pypi_name"]) if (pkg and pkg.get("pypi_name")) else None
    for name, fn in _PYTHON_SCORERS.items():
        subscores[name] = fn(intel)

    score, breakdown, absent, confidence = compute_composite(subscores, weights, is_py)

    # ── horizon signals ──
    pinned_line = _minor_line(row.get("pinned"))
    lts = eol_client.lts_status(conda_name or row.get("name", ""), pinned_line) \
        if eol_client else {"lts_status": "unknown", "eol_date": None,
                            "product_fully_eol": False,
                            "pinned_line_eol_before_window": False, "stale": False}
    py314 = "unknown"
    if is_py:
        pkg_pythons = _pkg_pythons(conn, conda_name) if conda_name else []
        py314 = py314_readiness(
            intel.get("python_tags") if intel else None,
            intel.get("classifiers") if intel else None,
            intel.get("requires_python") if intel else None,
            pkg_pythons,
            intel.get("packaging_shape") if intel else None, is_py,
            latest_upload_at=intel.get("latest_upload_at") if intel else None)

    tier, reasons, alternatives = derive_tier(
        conn, score, row, pkg, py314, lts, weights)

    signals_absent = list(row.get("signals_absent") or [])
    signals_absent += [a for a in absent if a not in signals_absent]
    if not is_py:
        signals_absent.append("python-enrichment (n/a: non-python)")
    if lts.get("lts_status") in (None, "unknown"):
        signals_absent.append("lts_status")

    out = {
        "name": row.get("name"), "conda_name": conda_name,
        "ecosystem": row.get("ecosystem"), "pinned": row.get("pinned"),
        "bucket": row.get("bucket"),
        "futures_score": score, "futures_tier": tier, "tier_reasons": reasons,
        "confidence": confidence, "breakdown": breakdown,
        "signals_absent": signals_absent,
        "py314_readiness": py314,
        "lts_status": lts.get("lts_status"), "eol_date": lts.get("eol_date"),
        "eol_stale": lts.get("stale", False),
        "weight": row.get("weight"),
    }
    enrich = _vuln_enrichment(conn, conda_name) if conda_name else None
    if enrich:
        out["vuln_enrichment"] = enrich
    if alternatives:
        out["alternatives"] = [
            {"conda_name": a["conda_name"], "score": a.get("composite_score")}
            for a in alternatives]
    return out


def _minor_line(version: str | None) -> str | None:
    if not version:
        return None
    parts = str(version).split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else parts[0]


def _pkg_pythons(conn, conda_name) -> list[str]:
    return [r[0] for r in conn.execute(
        "SELECT pkg_python FROM package_python_downloads WHERE conda_name = ?",
        (conda_name,))]


def _vuln_enrichment(conn, conda_name) -> dict[str, Any] | None:
    """EPSS / CWE, REPORT-ONLY (never in the composite): these columns exist
    only on the stale `packages.vuln_*` rollup, not the query-time-correct
    view — surfacing them with their scan stamp keeps the spec's 'max EPSS,
    CWE categories' visible without importing stale data into the score."""
    r = conn.execute(
        "SELECT vuln_max_epss_score, vuln_cwe_top, vdb_scanned_at "
        "FROM packages WHERE conda_name = ?", (conda_name,)).fetchone()
    if r is None or (r[0] is None and r[1] is None):
        return None
    return {"max_epss": r[0], "cwe_top": r[1], "rollup_scanned_at": r[2],
            "note": "stale rollup — report-only, never scored"}


def score_packages(conn, rows, weights=None, eol_client=None, now=None):
    """Score the matched (on-conda-forge) rows of an inventory. ADD /
    ADD-NONPYPI / rows without a conda_name are skipped (not on cf — S6's
    domain). Returns a list of futures_row dicts, tier then score sorted."""
    weights = weights or DEFAULT_WEIGHTS
    now = now if now is not None else int(time.time())
    if eol_client is None:
        eol_client = EolClient(now=now)
    out = []
    for row in rows:
        if not row.get("conda_name"):
            continue
        if row.get("bucket") and row["bucket"] not in _SCOREABLE_BUCKETS:
            continue
        out.append(score_row(conn, row, weights, eol_client, now))
    out.sort(key=lambda r: (_SEVERITY[r["futures_tier"]],
                            -(r["futures_score"] if r["futures_score"] is not None else -1),
                            r["conda_name"] or ""))
    return out


# ── standalone CLI ───────────────────────────────────────────────────────────

def _rows_from_packages(conn, names):
    """Build minimal match-style rows for `--package NAME` standalone use."""
    rows = []
    for name in names:
        r = conn.execute(
            "SELECT conda_name, pypi_name, latest_conda_version FROM packages "
            "WHERE conda_name = ?", (name,)).fetchone()
        if r is None:
            sys.stderr.write(f"  warn: {name} not found on conda-forge\n")
            continue
        rows.append({"name": name, "conda_name": r[0],
                     "ecosystem": "pypi" if r[1] else "conda",
                     "cf_latest": r[2], "bucket": "CURRENT",
                     "pinned": r[2], "signals_absent": []})
    return rows


def render_report(rows: list[dict[str, Any]]) -> str:
    lines = ["# library-futures — 2027–2030 survival scoring", ""]
    by_tier: dict[str, int] = {}
    for r in rows:
        by_tier[r["futures_tier"]] = by_tier.get(r["futures_tier"], 0) + 1
    lines.append("- tiers: " + ", ".join(
        f"{t}={by_tier.get(t, 0)}" for t in TIERS) + "")
    lines.append("")
    for r in rows:
        bits = [f"score {r['futures_score']}", f"py314 {r['py314_readiness']}",
                f"lts {r['lts_status']}"]
        if r.get("eol_date"):
            bits.append(f"eol {r['eol_date']}")
        if r["confidence"] == "low":
            bits.append("confidence LOW")
        if r.get("eol_stale"):
            bits.append("eol-cache STALE")
        if r.get("alternatives"):
            bits.append("alts: " + ", ".join(a["conda_name"] for a in r["alternatives"]))
        lines.append(f"- **{r['conda_name']}** → **{r['futures_tier']}** "
                     f"({'; '.join(bits)})")
        if r["tier_reasons"]:
            lines.append(f"    reasons: {'; '.join(r['tier_reasons'])}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Score conda-forge packages for 2027–2030 survival "
                    "(keep/watch/plan-migration/replace).")
    parser.add_argument("inputs", nargs="*",
                        help="Inventory inputs (forwarded to inventory-match)")
    parser.add_argument("--package", action="append", default=[],
                        help="Score a single conda package by name (repeatable)")
    parser.add_argument("--weights", type=Path, default=None,
                        help="Criticality sidecar (csv name,weight or JSON "
                             "object) — feeds the user_weight signal")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--allow-stale", action="store_true",
                        help="Bypass the 14-day atlas freshness gate")
    args = parser.parse_args()

    if not args.package and not args.inputs:
        parser.error("give --package NAME and/or inventory inputs")
    if not DB_PATH.exists():
        sys.stderr.write(f"cf_atlas.db not found at {DB_PATH}.\n")
        return 1

    conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    try:
        check_freshness(conn, args.allow_stale)
        rows = _rows_from_packages(conn, args.package)
        if args.inputs:
            import inventory_match as im
            sidecar = im.load_weights(args.weights) if args.weights else None
            deps, labels, warnings = im.load_inventory([Path(p) for p in args.inputs], None)
            for w in warnings:
                sys.stderr.write(f"  warn: {w}\n")
            rows += im.run(conn, deps, labels, weights=sidecar)["rows"]
        result = score_packages(conn, rows)
    except StaleAtlasError as exc:
        sys.stderr.write(f"REFUSED: {exc}\n")
        return 1
    except sqlite3.OperationalError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1
    finally:
        conn.close()

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        sys.stdout.write(render_report(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
