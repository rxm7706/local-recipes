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
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from _sbom import TOOL_NAME, TOOL_VENDOR, TOOL_VERSION, _purl, normalize_license
from export_purls import fold_name, g98_pypi_name, upstream_purl


def _get_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent / "data" / "conda-forge-expert"


DB_PATH = _get_data_dir() / "cf_atlas.db"
DEFAULT_OUT_DIR = _get_data_dir() / "universe-sbom"
DEFAULT_OUT = {
    "cyclonedx": DEFAULT_OUT_DIR / "universe-sbom.cdx.json",
    "spdx": DEFAULT_OUT_DIR / "universe-sbom.spdx.json",
}

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
        return int(float(row[0])) if row else None
    except (sqlite3.Error, ValueError, TypeError):
        return None


def check_freshness(conn: sqlite3.Connection, allow_stale: bool) -> int | None:
    """Decision 6, FAIL-CLOSED: an atlas whose age cannot be verified
    (missing/unparseable built_at — precisely the atlases most likely to be
    ancient) is REFUSED like a stale one; --allow-stale overrides both."""
    built = atlas_built_at(conn)
    if built is None:
        if not allow_stale:
            raise StaleAtlasError(
                "atlas has no parseable built_at stamp — freshness cannot be "
                "verified; rebuild it or pass --allow-stale"
            )
        sys.stderr.write("  warn: no parseable built_at — emitting on --allow-stale\n")
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
    """PEP-503-FOLDED pypi names mapped by ANY conda package — computed from
    the full table regardless of slice flags: decision 1's sibling-suppression
    is about identity (the name IS mapped), not about whether the conda side
    of the pair made it into the current slice. Folding uses Wave A's
    `fold_name` (membership-lookup-only, D1) so dot/dash/underscore spelling
    variance between `packages.pypi_name` and the universe cannot resurrect
    a mapped name as a standalone sibling; `g98_pypi_name` stays emission-only."""
    # scope: mapping-identity lookup over every row — a slice-narrowed scan
    # would resurrect mapped names as standalone pkg:pypi components.
    return {
        fold_name(row[0]) for row in conn.execute(
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
        "SELECT conda_name, source, url FROM upstream_versions "
        "WHERE source <> 'pypi' ORDER BY conda_name, source, url"
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
    seen_refs: set[str] = set()
    for (name, last_serial) in conn.execute(
        "SELECT pypi_name, last_serial FROM pypi_universe ORDER BY pypi_name"
    ):
        if fold_name(name) in mapped_fold:
            continue
        g98 = g98_pypi_name(name)
        version, license_str = enrich.get(name, (None, None))
        purl = _purl("pypi", g98, version)
        if purl in seen_refs:
            # Two stored spellings can G98-normalize identically (Phase D
            # never prunes renamed rows); bom-ref uniqueness is a CycloneDX
            # requirement the JSON schema cannot express.
            continue
        seen_refs.add(purl)
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


def signal_ages(conn: sqlite3.Connection, with_vulns: bool) -> list[dict[str, str]]:
    """Decision 6: per-signal `*_fetched_at` age stamps for BOM metadata."""
    props: list[dict[str, str]] = []
    # scope: aggregate freshness stamps over full tables — metadata, not
    # version truth.
    row = conn.execute("SELECT MAX(fetched_at) FROM pypi_universe").fetchone()
    if row and row[0]:
        props.append(_prop("cfe:pypi_universe_max_fetched_at", row[0]))
    row = conn.execute(
        "SELECT MAX(fetched_at) FROM upstream_versions"
    ).fetchone()
    if row and row[0]:
        props.append(_prop("cfe:upstream_versions_max_fetched_at", row[0]))
    if with_vulns:
        row = conn.execute(
            "SELECT MAX(vuln_scanned_at) FROM v_current_version_vulns"
        ).fetchone()
        if row and row[0]:
            props.append(_prop("cfe:vulns_max_scanned_at", row[0]))
    return props


def emit_universe_cyclonedx(
    components: list[dict[str, Any]],
    built_at: int | None,
    extra_metadata_props: list[dict[str, str]] | None = None,
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
    props = ([_prop("cfe:atlas_built_at", built_at)] if built_at is not None else [])
    props += extra_metadata_props or []
    if props:
        metadata["properties"] = props
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
    seen_ids: dict[str, int] = {}
    extracted: dict[str, str] = {}  # license text -> LicenseRef id
    for comp in components:
        licenses = comp.get("licenses") or []
        declared = "NOASSERTION"
        if licenses:
            lic = licenses[0]
            declared = (lic.get("expression")
                        or lic.get("license", {}).get("id")
                        or "")
            if not declared:
                # name-form (non-SPDX junk): preserve the text via a
                # LicenseRef + hasExtractedLicensingInfos instead of
                # dropping it to NOASSERTION.
                text = lic.get("license", {}).get("name", "")
                if text:
                    ref = extracted.setdefault(
                        text, f"LicenseRef-cfe-{len(extracted) + 1}")
                    declared = ref
                else:
                    declared = "NOASSERTION"
        base_id = "SPDXRef-" + "".join(
            c if c.isalnum() or c in ".-" else "-" for c in comp["bom-ref"]
        )
        # The sanitizer is many-to-one (`_`/`@`/`?` all collapse to `-`);
        # SPDXIDs must be unique per document — dedupe with a counter.
        n = seen_ids.get(base_id, 0)
        seen_ids[base_id] = n + 1
        spdx_id = base_id if n == 0 else f"{base_id}-{n}"
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
        "documentDescribes": [p["SPDXID"] for p in packages],
    }
    if extracted:
        doc["hasExtractedLicensingInfos"] = [
            {"licenseId": ref, "extractedText": text}
            for text, ref in sorted(extracted.items(), key=lambda kv: kv[1])
        ]
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
    """Returns (document, summary). Raises StaleAtlasError per decision 6,
    ValueError on contradictory slice combinations (guarded HERE, not only in
    main(), so the MCP/library path cannot emit a silently-empty BOM)."""
    if conda_only and pypi_only:
        raise ValueError("--conda-only and --pypi-only are mutually exclusive")
    if mapped_only and pypi_only:
        raise ValueError(
            "--mapped-only and --pypi-only are contradictory: mapped pairs "
            "are conda components (decision 1) and the pypi side would be empty"
        )
    if actionable_only and pypi_only:
        sys.stderr.write(
            "  warn: --actionable-only has no effect with --pypi-only\n"
        )
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

    doc = (emit_universe_cyclonedx(components, built,
                                   signal_ages(conn, with_vulns))
           if fmt == "cyclonedx"
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
    parser.add_argument("--out", type=Path, default=None,
                        help="Output path (default: per-format file under "
                             f"{DEFAULT_OUT_DIR})")
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

    if not DB_PATH.exists():
        sys.stderr.write(
            f"cf_atlas.db not found at {DB_PATH}. "
            "Run `pixi run -e local-recipes build-cf-atlas` first.\n"
        )
        return 1

    t0 = time.monotonic()
    try:
        # as_uri(): canonical cross-platform file-URI — handles drive
        # letters and percent-encodes ?/# so sqlite can't mis-split the path.
        conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        sys.stderr.write(f"cannot open {DB_PATH}: {exc}\n")
        return 1
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
    except (StaleAtlasError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    except sqlite3.OperationalError as exc:
        sys.stderr.write(
            f"atlas query failed: {exc}. If the schema predates v20/v29 "
            "(pypi_universe / v_pypi_intelligence_valid), re-run "
            "`pixi run -e local-recipes build-cf-atlas`; otherwise inspect "
            "the error before rebuilding.\n"
        )
        return 1
    finally:
        conn.close()

    out = args.out if args.out is not None else DEFAULT_OUT[args.format]
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        # Unique temp per run: a shared fixed .tmp would let two concurrent
        # emits interleave and defeat the atomic-replace guarantee. Compact
        # separators: pretty-printing would inflate the full-universe file
        # ~1/3 and skew the measured size/time the layout decision rests on.
        tmp: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=out.parent,
                prefix=out.name + ".", suffix=".tmp", delete=False,
            ) as fh:
                tmp = Path(fh.name)
                json.dump(doc, fh, separators=(",", ":"))
            tmp.replace(out)
            tmp = None
        finally:
            # A write failure must not leak the delete=False temp file.
            if tmp is not None:
                try:
                    tmp.unlink()
                except OSError:
                    pass
    except OSError as exc:
        sys.stderr.write(f"cannot write {out}: {exc}\n")
        return 1

    summary["out"] = str(out)
    summary["bytes"] = out.stat().st_size
    summary["wall_seconds"] = round(time.monotonic() - t0, 2)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        sys.stdout.write(
            f"  {summary['format']} universe SBOM → {out}\n"
            f"  conda components: {summary['conda_components']:,} · "
            f"pypi components: {summary['pypi_components']:,} · "
            f"{summary['bytes']:,} bytes in {summary['wall_seconds']}s\n"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
