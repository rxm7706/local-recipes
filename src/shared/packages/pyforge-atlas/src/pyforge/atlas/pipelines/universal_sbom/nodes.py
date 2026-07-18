"""``universal_sbom`` pipeline nodes (Story B7).

Two PURE nodes over the entry-scoped SBOM datasets, plus the pure SBOM primitives
ported VERBATIM from the shipped ``cyclonedx-universe-inventory`` CLIs (HARD read-only
``.claude/**``; not imported from there):

- ``normalize_intake_to_cyclonedx`` — merge the § 4.10 base inventory + the transitive
  resolution into a CycloneDX BOM, PRESERVING every ``cfe:*`` property and the
  ``?channel=conda-forge`` purl qualifier (AD-10, never stripped), and recording the
  resolution depth + fan-out as ``cfe:*`` metadata (FR-17 / AC-1).
- ``match_against_universe`` — the six-bucket matcher (AD-10): freshness-gate the
  universe BOM (14-day refuse-stale, AD-15), then bucket each component against the
  atlas indexes. Emits a security **input** (a match report), NEVER a
  ``ComplianceReport`` (AD-12 — that is F4's single-producer job).

No inline IO (A2 gate): pandas + stdlib only; ``dagster``/``kedro_mcp`` never imported
(AD-1). Data arrives via catalog datasets by name (AD-3).
"""

from __future__ import annotations

import re
import time
from typing import Any

import pandas as pd

# ── ported primitives (VERBATIM from export_purls.py / inventory_match.py) ────

CHANNEL_QUALIFIER = "?channel=conda-forge"  # export_purls.CHANNEL_QUALIFIER
CFE_PREFIX = "cfe:"
BUCKETS = ("ADD", "ADD-NONPYPI", "UPDATE-FEEDSTOCK", "UPDATE-PIN", "CURRENT", "UNKNOWN")
STALE_AFTER_DAYS_DEFAULT = 14  # universe_sbom.STALE_AFTER_DAYS

_NUMERIC_RE = re.compile(r"^\d+(\.\d+)*$")


class StaleUniverseError(RuntimeError):
    """Raised when the universe BOM is older than the freshness contract and
    ``allow_stale`` is not set — the consumer refuses a stale atlas exactly as the
    legacy ``universe_sbom.check_freshness`` gate (AD-15)."""


def fold_name(name: str) -> str:
    """PEP-503 fold for MEMBERSHIP LOOKUP ONLY (export_purls.fold_name)."""
    return re.sub(r"[-_.]+", "-", (name or "").lower())


def conda_purl(conda_name: str, version: str | None) -> str:
    """``pkg:conda/<name>@<ver>?channel=conda-forge`` — the qualifier is never dropped."""
    if version:
        return f"pkg:conda/{conda_name}@{version}{CHANNEL_QUALIFIER}"
    return f"pkg:conda/{conda_name}{CHANNEL_QUALIFIER}"


def cmp_versions(a: str | None, b: str | None) -> tuple[int | None, bool]:
    """Three-way compare → (-1/0/1 | None, reliable). VERBATIM from
    inventory_match.cmp_versions (packaging → dotted-numeric → string ladder)."""
    if not a or not b:
        return None, True
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


def classify_bucket(
    inv: dict[str, Any],
    conda_rec: dict[str, Any] | None,
    upstream_version: str | None,
    in_universe: bool,
) -> str:
    """The six-bucket decision tree, ported VERBATIM from
    inventory_match.match_inventory (lines 1110–1184).

    ``inv`` = {name, ecosystem, pinned}; ``conda_rec`` = the resolved conda record
    (None if unmatched); ``upstream_version`` = the upstream-of-record (None until
    DW-B7-1 wires the column); ``in_universe`` = pypi fold ∈ the universe (ADD path).
    """
    eco = inv.get("ecosystem")
    if conda_rec is None:
        # ── unmatched → ADD / ADD-NONPYPI / UNKNOWN ──
        if eco == "pypi":
            return "ADD" if in_universe else "UNKNOWN"
        if eco == "conda":
            return "UNKNOWN"  # a conda id not on cf — never guessed into ADD
        return "ADD-NONPYPI"
    # ── matched: three-way comparison ──
    cf_latest = conda_rec.get("cf_latest")
    if cf_latest is None:
        return "UNKNOWN"
    cmp_cf_up, _ = cmp_versions(cf_latest, upstream_version)
    cmp_inv_cf, _ = cmp_versions(inv.get("pinned"), cf_latest)
    if cmp_cf_up is not None and cmp_cf_up < 0:
        return "UPDATE-FEEDSTOCK"
    if cmp_inv_cf is not None and cmp_inv_cf < 0:
        return "UPDATE-PIN"
    return "CURRENT"


# ── freshness gate (VERBATIM contract from universe_sbom.check_freshness) ──────


def _atlas_built_at(bom: dict[str, Any]) -> int | None:
    """Read ``cfe:atlas_built_at`` from a BOM's ``metadata.properties`` (int epoch)."""
    props = ((bom or {}).get("metadata") or {}).get("properties") or []
    for p in props:
        if p.get("name") == "cfe:atlas_built_at":
            try:
                return int(float(p.get("value")))
            except (TypeError, ValueError):
                return None
    return None


def check_universe_freshness(
    bom: dict[str, Any],
    stale_after_days: int = STALE_AFTER_DAYS_DEFAULT,
    now: float | None = None,
    allow_stale: bool = False,
) -> int | None:
    """FAIL-CLOSED freshness gate (AD-15): a BOM whose ``built_at`` cannot be
    verified is REFUSED like a stale one; ``allow_stale`` overrides both. Ported
    from universe_sbom.check_freshness (decision 6)."""
    built = _atlas_built_at(bom)
    now = time.time() if now is None else now
    if built is None:
        if not allow_stale:
            raise StaleUniverseError(
                "universe BOM has no parseable cfe:atlas_built_at stamp — freshness "
                "cannot be verified; rebuild it or pass allow_stale"
            )
        return None
    age_days = (now - built) / 86400
    if age_days > stale_after_days and not allow_stale:
        raise StaleUniverseError(
            f"universe BOM is {age_days:.1f} days old (> {stale_after_days}); "
            "rebuild it or pass allow_stale"
        )
    return built


# ── CycloneDX emit (plain-dict shape, matching _sbom.emit_cyclonedx) ──────────


def _component(dep: dict[str, Any]) -> dict[str, Any]:
    """One CycloneDX component from a normalized inventory row. Conda deps get the
    ``?channel=conda-forge`` qualifier; a passthrough row's ``purl`` + ``cfe:*``
    properties are PRESERVED VERBATIM (AD-10)."""
    name = dep["name"]
    version = dep.get("version") or ""
    eco = dep.get("ecosystem", "pypi")
    if dep.get("purl"):
        purl = dep["purl"]  # passthrough — never re-derive / strip the qualifier
    elif eco == "conda":
        purl = conda_purl(name, dep.get("version"))
    else:
        purl = f"pkg:{eco}/{name}@{version}" if version else f"pkg:{eco}/{name}"
    comp: dict[str, Any] = {
        "type": "library",
        "bom-ref": f"{eco}-{name}-{version or 'unknown'}",
        "name": name,
        "version": version,
        "purl": purl,
    }
    props = list(dep.get("properties") or [])  # preserve incoming cfe:* verbatim
    manifest = dep.get("manifest")
    if manifest and not any(p.get("name") == "manifest" for p in props):
        props.append({"name": "manifest", "value": str(manifest)})
    if props:
        comp["properties"] = props
    return comp


def _cyclonedx_envelope(
    components: list[dict[str, Any]],
    project_name: str,
    metadata_props: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {"component": {"type": "application", "name": project_name, "bom-ref": project_name}}
    if metadata_props:
        meta["properties"] = metadata_props
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "metadata": meta,
        "components": components,
    }


# ── node 1: normalize (AC-1, AC-2) ───────────────────────────────────────────


def normalize_intake_to_cyclonedx(
    sbom_intake_entry: dict[str, Any],
    sbom_resolution_entry: dict[str, Any],
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge the § 4.10 base inventory + the transitive resolution into a CycloneDX
    BOM, preserving ``cfe:*`` + ``?channel`` (AD-10) and recording resolution
    depth/fan-out as ``cfe:*`` metadata (FR-17 / AC-1)."""
    base_deps = list((sbom_intake_entry or {}).get("deps") or [])
    resolution = sbom_resolution_entry or {"resolution": "unresolved"}

    deps = list(base_deps)
    seen = {(d.get("ecosystem"), fold_name(d.get("name", ""))) for d in deps}
    meta_props: list[dict[str, str]] = [{"name": "cfe:resolution", "value": str(resolution.get("resolution", "unresolved"))}]

    if resolution.get("resolution") == "resolved":
        for td in resolution.get("deps") or []:
            if not td.get("name"):  # a malformed injected resolution dep never crashes the run (AD-13)
                continue
            key = (td.get("ecosystem"), fold_name(td.get("name", "")))
            if key in seen:
                continue
            seen.add(key)
            deps.append(td)
        if resolution.get("depth") is not None:
            meta_props.append({"name": "cfe:resolution_depth", "value": str(resolution["depth"])})
        if resolution.get("fanout") is not None:
            meta_props.append({"name": "cfe:resolution_fanout", "value": str(resolution["fanout"])})
    elif resolution.get("reason"):
        meta_props.append({"name": "cfe:resolution_reason", "value": str(resolution["reason"])})

    # A malformed row (base OR injected transitive) missing a name never crashes the
    # run (AD-13) — _component would KeyError on dep["name"] (Edge-MEDIUM).
    components = [_component(d) for d in deps if d.get("name")]
    project = (parameters or {}).get("sbom", {}).get("project_name", "user-inventory")
    return _cyclonedx_envelope(components, project, meta_props)


# ── node 2: match (AC-3, AC-4, AD-12) ─────────────────────────────────────────


def _build_indexes(
    core_packages_enumerated: pd.DataFrame,
    pypi_conda_mapping: pd.DataFrame,
    derived_universe_sbom: dict[str, Any],
    pypi_universe: pd.DataFrame | None = None,
) -> dict[str, Any]:
    conda_by_name: dict[str, dict[str, Any]] = {}
    conda_by_fold: dict[str, dict[str, Any]] = {}
    for _, r in core_packages_enumerated.iterrows():
        cname = r.get("conda_name")
        if not cname or pd.isna(cname):
            continue
        rec = {
            "conda_name": cname,
            "cf_latest": (None if pd.isna(r.get("latest_version")) else r.get("latest_version")),
            # DW-B7-1: upstream_version is graceful — missing column → None
            "upstream_version": (None if pd.isna(r.get("upstream_version")) else r.get("upstream_version"))
            if "upstream_version" in core_packages_enumerated.columns
            else None,
        }
        conda_by_name[str(cname).lower()] = rec
        conda_by_fold.setdefault(fold_name(str(cname)), rec)

    mapping_by_fold: dict[str, dict[str, Any]] = {}
    # conda_name(lower) -> the pypi fold it is mapped to — the G10 guard input
    # (a same-named conda pkg mapped to a DIFFERENT pypi project must NOT bare-match).
    conda_to_pypifold: dict[str, str] = {}
    for _, r in pypi_conda_mapping.iterrows():
        pname, cname = r.get("pypi_name"), r.get("conda_name")
        if not pname or pd.isna(pname) or not cname or pd.isna(cname):
            continue
        rec = conda_by_name.get(str(cname).lower()) or {"conda_name": cname, "cf_latest": None, "upstream_version": None}
        mapping_by_fold.setdefault(fold_name(str(pname)), rec)
        conda_to_pypifold.setdefault(str(cname).lower(), fold_name(str(pname)))

    # Universe membership for the ADD path (VERBATIM legacy universe_lookup): the FULL
    # PyPI universe (pypi_universe.pypi_name) is authoritative — a pypi name present
    # there but unmatched to conda is ADD (not UNKNOWN). Unioned with the mapped folds
    # + any standalone pkg:pypi/ components the universe BOM carries (DW-B7-3).
    universe_folds: set[str] = set()
    if pypi_universe is not None and "pypi_name" in getattr(pypi_universe, "columns", []):
        for v in pypi_universe["pypi_name"].dropna():
            universe_folds.add(fold_name(str(v)))
    for comp in (derived_universe_sbom or {}).get("components") or []:
        purl = comp.get("purl") or ""
        m = re.match(r"^pkg:pypi/([^@?]+)", purl)
        if m:
            universe_folds.add(fold_name(m.group(1)))
        for p in comp.get("properties") or []:
            if p.get("name") == "cfe:pypi_name" and p.get("value"):
                universe_folds.add(fold_name(str(p["value"])))
    universe_folds |= set(mapping_by_fold.keys())

    return {
        "conda_by_name": conda_by_name,
        "conda_by_fold": conda_by_fold,
        "mapping_by_fold": mapping_by_fold,
        "conda_to_pypifold": conda_to_pypifold,
        "universe_folds": universe_folds,
    }


def match_against_universe(
    sbom_normalized_bom_entry: dict[str, Any],
    core_packages_enumerated: pd.DataFrame,
    pypi_conda_mapping: pd.DataFrame,
    derived_universe_sbom: dict[str, Any],
    pypi_universe: pd.DataFrame | None = None,
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The six-bucket matcher (AD-10). Refuse-stale gate on the universe BOM (AD-15),
    then bucket each component against the atlas indexes. Emits a security INPUT —
    a match report — NEVER a ComplianceReport (AD-12)."""
    params = parameters or {}
    stale_after = int(params.get("freshness", {}).get("stale_after_days", STALE_AFTER_DAYS_DEFAULT))
    allow_stale = bool(params.get("sbom", {}).get("allow_stale", False))
    now = params.get("sbom", {}).get("now")

    built_at = check_universe_freshness(  # RAISES StaleUniverseError when stale (AC-3)
        derived_universe_sbom, stale_after_days=stale_after, now=now, allow_stale=allow_stale
    )
    # MEDIUM-2: report the TRUE staleness even when allow_stale bypassed the gate —
    # never tell a downstream consumer the atlas is fresh when it is not.
    now_epoch = time.time() if now is None else now
    stale = built_at is None or ((now_epoch - built_at) / 86400 > stale_after)

    idx = _build_indexes(core_packages_enumerated, pypi_conda_mapping, derived_universe_sbom, pypi_universe)

    rows: list[dict[str, Any]] = []
    for comp in (sbom_normalized_bom_entry or {}).get("components") or []:
        name = comp.get("name") or ""
        version = comp.get("version") or None
        purl = comp.get("purl") or ""
        m = re.match(r"^pkg:([A-Za-z0-9.+-]+)/", purl)
        eco = {"pypi": "pypi", "conda": "conda"}.get(m.group(1).lower() if m else "", "generic")
        inv = {"name": name, "ecosystem": eco, "pinned": version}
        fold = fold_name(name)

        conda_rec: dict[str, Any] | None = None
        if eco == "conda":
            conda_rec = idx["conda_by_name"].get(name.lower()) or idx["conda_by_fold"].get(fold)
        elif eco == "pypi":
            conda_rec = idx["mapping_by_fold"].get(fold)
            if conda_rec is None:
                cand = idx["conda_by_fold"].get(fold)
                # G10 guard (MEDIUM-3, VERBATIM from legacy inventory_match:1090-1096):
                # a same-named conda pkg mapped to a DIFFERENT pypi project is a name
                # coincidence — reject the bare match, fall through to ADD/universe.
                if cand is not None:
                    mapped_fold = idx["conda_to_pypifold"].get(str(cand.get("conda_name", "")).lower())
                    if mapped_fold is not None and mapped_fold != fold:
                        cand = None
                conda_rec = cand
        else:
            conda_rec = idx["conda_by_fold"].get(fold)

        upstream = conda_rec.get("upstream_version") if conda_rec else None
        bucket = classify_bucket(inv, conda_rec, upstream, fold in idx["universe_folds"])
        row: dict[str, Any] = {
            "name": name,
            "ecosystem": eco,
            "pinned": version,
            "bucket": bucket,
            "conda_name": (conda_rec or {}).get("conda_name"),
            "cf_latest": (conda_rec or {}).get("cf_latest"),
        }
        if conda_rec and conda_rec.get("conda_name"):
            row["conda_purl"] = conda_purl(str(conda_rec["conda_name"]), conda_rec.get("cf_latest"))
            # Surface the legacy version_comparison reliability flag (Edge-MEDIUM) —
            # the bucketing itself stays verbatim (legacy acts on the verdict either way).
            cf_latest = conda_rec.get("cf_latest")
            if cf_latest is not None:
                _, ok1 = cmp_versions(cf_latest, upstream)
                _, ok2 = cmp_versions(version, cf_latest)
                row["version_comparison"] = "unreliable" if (not ok1 or not ok2) else "reliable"
        rows.append(row)

    counts = {b: sum(1 for r in rows if r["bucket"] == b) for b in BUCKETS}
    # AD-12: this is a security INPUT (six-bucket match report), NOT a ComplianceReport.
    return {
        "kind": "sbom-match-report",
        "atlas_built_at": built_at,
        "stale": stale,
        "components": rows,
        "buckets": counts,
    }
