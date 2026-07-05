#!/usr/bin/env python3
"""
universe-sbom — Full-universe CycloneDX/SPDX inventory of conda-forge + PyPI
(cyclonedx-universe-inventory Wave B / S3).

Emits the complete inventory per the intake spec's design decisions 1–2:

  • ALL conda packages (archived/inactive INCLUDED, flagged via
    `cfe:latest_status` / `cfe:feedstock_archived` — a consumer may run one).
    A mapped conda↔pypi pair is ONE component (the conda one) carrying
    `cfe:pypi_purl` / `cfe:match_source` / `cfe:match_confidence` properties —
    never two sibling components (SBOM consumers would double-count).
    Non-Python conda components carry `cfe:upstream_purl` +
    `cfe:upstream_source` where the atlas knows the upstream.
  • ALL PyPI projects — standalone `pkg:pypi/` components ONLY for names
    unmapped to conda; version/license attached where `pypi_intelligence`
    is enriched (read via `v_pypi_intelligence_valid` — the v29 ORPHAN_RULE
    view; orphan rows are never version truth).

Freshness contract (decision 6): the BOM stamps `cfe:atlas_built_at`; the
CLI REFUSES to run when the atlas is older than 14 days (`--allow-stale`
overrides) — cached records decay (G74/G78).

Offline-safe: reads only cf_atlas.db. Full-universe size/emit time are
RECORDED BY THE LOCAL RUN into Dev Notes (live-verification principle);
the single-file-vs-split layout decision is made from those numbers.

CLI:
  universe-sbom [--out PATH] [--format cyclonedx|spdx]
                [--actionable-only] [--mapped-only] [--conda-only]
                [--pypi-only] [--with-vulns] [--allow-stale] [--json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from _sbom import TOOL_NAME, TOOL_VENDOR, TOOL_VERSION, _purl, normalize_license
from export_purls import g98_pypi_name, upstream_purl


def _get_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent / "data" / "conda-forge-expert"


DB_PATH = _get_data_dir() / "cf_atlas.db"
DEFAULT_OUT = _get_data_dir() / "universe-sbom" / "universe-sbom.cdx.json"

STALE_AFTER_DAYS = 14

# Preference order when a package has several non-pypi upstream identities —
# github is the dominant tracker (47k rows; see intake-spec Grounding).
_UPSTREAM_SOURCE_ORDER = ("github", "npm", "crates", "rubygems", "maven",
                          "gitlab", "codeberg")


class StaleAtlasError(RuntimeError):
    pass


def atlas_built_at(conn: sqlite3.Connection) -> int | None:
    try:
        row = conn.execute("SELECT value FROM meta WHERE key='built_at'").fetchone()
        return int(row[0]) if row else None
    except (sqlite3.Error, ValueError, TypeError):
        return None


def check_freshness(conn: sqlite3.Connection, allow_stale: bool) -> int | None:
    built = atlas_built_at(conn)
    if built is None:
        sys.stderr.write("  warn: atlas has no built_at stamp — emitting anyway\n")
        return None
    age_days = (time.time() - built) / 86400
    if age_days > STALE_AFTER_DAYS and not allow_stale:
        raise StaleAtlasError(
            f"atlas is {age_days:.1f} days old (> {STALE_AFTER_DAYS}); "
            "rebuild it or pass --allow-stale"
        )
    return built


# --- component builders ------------------------------------------------------


def _prop(name: str, value: Any) -> dict[str, str]:
    return {"name": name, "value": str(value)}


def mapped_pypi_folds(conn: sqlite3.Connection) -> set[str]:
    """G98-folded pypi names mapped by ANY conda package — computed from the
    full table regardless of slice flags: decision 1's sibling-suppression is
    about identity (the name IS mapped), not about whether the conda side of
    the pair made it into the current slice."""
    # scope: mapping-identity lookup over every row — a slice-narrowed scan
    # would resurrect mapped names as standalone pkg:pypi components.
    return {
        g98_pypi_name(row[0]) for row in conn.execute(
            "SELECT pypi_name FROM packages "
            "WHERE pypi_name IS NOT NULL AND pypi_name <> ''"
        )
    }


def conda_components(
    conn: sqlite3.Connection,
    actionable_only: bool,
    mapped_only: bool,
    with_vulns: bool,
) -> list[dict[str, Any]]:
    """All conda components per the slice flags."""
    table = "v_actionable_packages" if actionable_only else "packages"
    # scope: BOM scope decision 2 — the FULL conda universe by default,
    # archived/inactive INCLUDED and flagged (consumers may run them);
    # --actionable-only narrows to the view.
    rows = conn.execute(
        f"""
        SELECT conda_name, latest_conda_version, conda_license, pypi_name,
               match_source, match_confidence, latest_status, feedstock_archived
        FROM {table}
        WHERE conda_name IS NOT NULL
        ORDER BY conda_name
        """
    ).fetchall()

    upstreams: dict[str, list[tuple[str, str | None]]] = {}
    for name, source, url in conn.execute(
        "SELECT conda_name, source, url FROM upstream_versions WHERE source <> 'pypi'"
    ):
        upstreams.setdefault(name, []).append((source, url))

    vuln_counts: dict[str, tuple[int, int, int]] = {}
    if with_vulns:
        for name, crit, high, kev in conn.execute(
            "SELECT conda_name, vuln_critical_current, vuln_high_current, "
            "vuln_kev_current FROM v_current_version_vulns "
            "WHERE vuln_critical_current > 0 OR vuln_high_current > 0 "
            "   OR vuln_kev_current > 0"
        ):
            vuln_counts[name] = (crit, high, kev)

    components: list[dict[str, Any]] = []
    for (conda_name, version, license_str, pypi_name, match_source,
         match_confidence, latest_status, archived) in rows:
        if mapped_only and not pypi_name:
            continue
        purl = _purl("conda", conda_name, version, {"channel": "conda-forge"})
        comp: dict[str, Any] = {
            "type": "library",
            "bom-ref": purl,
            "name": conda_name,
            "purl": purl,
        }
        if version:
            comp["version"] = version
        entry = normalize_license(license_str)
        if entry:
            comp["licenses"] = [entry]
        props: list[dict[str, str]] = []
        if latest_status:
            props.append(_prop("cfe:latest_status", latest_status))
        if archived:
            props.append(_prop("cfe:feedstock_archived", "true"))
        if pypi_name:
            g98 = g98_pypi_name(pypi_name)
            props.append(_prop("cfe:pypi_purl", f"pkg:pypi/{g98}"))
            props.append(_prop("cfe:match_source", match_source or ""))
            props.append(_prop("cfe:match_confidence", match_confidence or ""))
        else:
            candidates = sorted(
                upstreams.get(conda_name, ()),
                key=lambda su: (_UPSTREAM_SOURCE_ORDER.index(su[0])
                                if su[0] in _UPSTREAM_SOURCE_ORDER else 99, su[0]),
            )
            for source, url in candidates:
                up = upstream_purl(source, url)
                if up:
                    props.append(_prop("cfe:upstream_purl", up))
                    props.append(_prop("cfe:upstream_source", source))
                    break
        if conda_name in vuln_counts:
            crit, high, kev = vuln_counts[conda_name]
            props.append(_prop("cfe:vuln_critical_current", crit))
            props.append(_prop("cfe:vuln_high_current", high))
            props.append(_prop("cfe:vuln_kev_current", kev))
        if props:
            comp["properties"] = props
        components.append(comp)
    return components


def pypi_components(
    conn: sqlite3.Connection,
    mapped_fold: set[str],
) -> list[dict[str, Any]]:
    """Standalone pkg:pypi components for UNMAPPED universe names only
    (decision 1). Enrichment (version/license) comes from the v29 view —
    orphan pypi_intelligence rows are never version truth."""
    enrich: dict[str, tuple[str | None, str | None]] = {
        name: (ver, lic)
        for name, ver, lic in conn.execute(
            "SELECT pypi_name, latest_version, license_spdx "
            "FROM v_pypi_intelligence_valid WHERE json_fetched_at IS NOT NULL"
        )
    }
    components: list[dict[str, Any]] = []
    for (name, last_serial) in conn.execute(
        "SELECT pypi_name, last_serial FROM pypi_universe ORDER BY pypi_name"
    ):
        g98 = g98_pypi_name(name)
        if g98 in mapped_fold:
            continue
        version, license_str = enrich.get(name, (None, None))
        purl = _purl("pypi", g98, version)
        comp: dict[str, Any] = {
            "type": "library",
            "bom-ref": purl,
            "name": g98,
            "purl": purl,
        }
        if version:
            comp["version"] = version
        entry = normalize_license(license_str)
        if entry:
            comp["licenses"] = [entry]
        if last_serial is not None:
            comp["properties"] = [_prop("cfe:pypi_last_serial", last_serial)]
        components.append(comp)
    return components


# --- document emitters ---------------------------------------------------------


def emit_universe_cyclonedx(
    components: list[dict[str, Any]], built_at: int | None
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "timestamp": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tools": {
            "components": [{
                "type": "application",
                "name": TOOL_NAME,
                "version": TOOL_VERSION,
                "publisher": TOOL_VENDOR,
            }],
        },
        "component": {
            "type": "data",
            "name": "conda-forge-pypi-universe",
            "bom-ref": "conda-forge-pypi-universe",
        },
    }
    if built_at is not None:
        metadata["properties"] = [_prop("cfe:atlas_built_at", built_at)]
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": metadata,
        "components": components,
    }


def emit_universe_spdx(
    components: list[dict[str, Any]], built_at: int | None
) -> dict[str, Any]:
    """Minimal SPDX 2.3 rendering of the same component set."""
    packages = []
    for comp in components:
        licenses = comp.get("licenses") or []
        declared = "NOASSERTION"
        if licenses:
            lic = licenses[0]
            declared = (lic.get("expression")
                        or lic.get("license", {}).get("id")
                        or "NOASSERTION")
        spdx_id = "SPDXRef-" + "".join(
            c if c.isalnum() or c in ".-" else "-" for c in comp["bom-ref"]
        )
        packages.append({
            "SPDXID": spdx_id,
            "name": comp["name"],
            "versionInfo": comp.get("version", "NOASSERTION"),
            "downloadLocation": "NOASSERTION",
            "licenseConcluded": "NOASSERTION",
            "licenseDeclared": declared,
            "externalRefs": [{
                "referenceCategory": "PACKAGE-MANAGER",
                "referenceType": "purl",
                "referenceLocator": comp["purl"],
            }],
        })
    doc = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "conda-forge-pypi-universe",
        "documentNamespace": f"https://rxm7706.github.io/local-recipes/spdx/{uuid.uuid4()}",
        "creationInfo": {
            "created": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "creators": [f"Tool: {TOOL_NAME}-{TOOL_VERSION}"],
        },
        "packages": packages,
    }
    if built_at is not None:
        doc["comment"] = f"cfe:atlas_built_at={built_at}"
    return doc


# --- orchestration ---------------------------------------------------------------


def build_universe_bom(
    conn: sqlite3.Connection,
    fmt: str = "cyclonedx",
    actionable_only: bool = False,
    mapped_only: bool = False,
    conda_only: bool = False,
    pypi_only: bool = False,
    with_vulns: bool = False,
    allow_stale: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Returns (document, summary). Raises StaleAtlasError per decision 6."""
    built = check_freshness(conn, allow_stale)
    components: list[dict[str, Any]] = []
    n_conda = n_pypi = 0
    if not pypi_only:
        components += conda_components(
            conn, actionable_only, mapped_only, with_vulns)
        n_conda = len(components)
    if not conda_only and not mapped_only:
        mapped_fold = mapped_pypi_folds(conn)
        pypi_comps = pypi_components(conn, mapped_fold)
        components += pypi_comps
        n_pypi = len(pypi_comps)

    doc = (emit_universe_cyclonedx(components, built) if fmt == "cyclonedx"
           else emit_universe_spdx(components, built))
    summary = {
        "format": fmt,
        "conda_components": n_conda,
        "pypi_components": n_pypi,
        "total_components": len(components),
        "atlas_built_at": built,
    }
    return doc, summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit the full conda-forge + PyPI universe inventory as an SBOM."
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help=f"Output path (default {DEFAULT_OUT})")
    parser.add_argument("--format", choices=("cyclonedx", "spdx"),
                        default="cyclonedx")
    parser.add_argument("--actionable-only", action="store_true",
                        help="Restrict conda side to v_actionable_packages")
    parser.add_argument("--mapped-only", action="store_true",
                        help="Only conda components with a PyPI mapping")
    parser.add_argument("--conda-only", action="store_true",
                        help="Skip the PyPI universe side")
    parser.add_argument("--pypi-only", action="store_true",
                        help="Skip the conda side (unmapped PyPI names only)")
    parser.add_argument("--with-vulns", action="store_true",
                        help="Attach current-version vuln-count properties "
                             "(off by default at universe scale)")
    parser.add_argument("--allow-stale", action="store_true",
                        help="Emit even when the atlas is older than "
                             f"{STALE_AFTER_DAYS} days")
    parser.add_argument("--json", action="store_true",
                        help="Print the run summary as JSON")
    args = parser.parse_args()

    if args.conda_only and args.pypi_only:
        sys.stderr.write("--conda-only and --pypi-only are mutually exclusive\n")
        return 1
    if not DB_PATH.exists():
        sys.stderr.write(
            f"cf_atlas.db not found at {DB_PATH}. "
            "Run `pixi run -e local-recipes build-cf-atlas` first.\n"
        )
        return 1

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    t0 = time.monotonic()
    try:
        doc, summary = build_universe_bom(
            conn, fmt=args.format,
            actionable_only=args.actionable_only,
            mapped_only=args.mapped_only,
            conda_only=args.conda_only,
            pypi_only=args.pypi_only,
            with_vulns=args.with_vulns,
            allow_stale=args.allow_stale,
        )
    except StaleAtlasError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    except sqlite3.OperationalError as exc:
        sys.stderr.write(
            f"atlas schema too old or incomplete ({exc}). "
            "Re-run `pixi run -e local-recipes build-cf-atlas` "
            "(schema v29+ adds v_pypi_intelligence_valid).\n"
        )
        return 1
    finally:
        conn.close()

    try:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        tmp = args.out.with_suffix(args.out.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1)
        tmp.replace(args.out)
    except OSError as exc:
        sys.stderr.write(f"cannot write {args.out}: {exc}\n")
        return 1

    summary["out"] = str(args.out)
    summary["bytes"] = args.out.stat().st_size
    summary["wall_seconds"] = round(time.monotonic() - t0, 2)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        sys.stdout.write(
            f"  {summary['format']} universe SBOM → {args.out}\n"
            f"  conda components: {summary['conda_components']:,} · "
            f"pypi components: {summary['pypi_components']:,} · "
            f"{summary['bytes']:,} bytes in {summary['wall_seconds']}s\n"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
