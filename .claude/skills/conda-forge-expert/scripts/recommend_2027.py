#!/usr/bin/env python3
"""
recommend-2027 — the 2027–2030 window scorecard for a user inventory
(cyclonedx-universe-inventory Wave D / S8).

Runs S5 (inventory-match) then S7 (library-futures) over a user inventory
and emits ONE scorecard: markdown + --json + an optional annotated
CycloneDX (--sbom-in/--sbom-out) whose matched components carry
`cfe:futures_tier`, `cfe:futures_score`, `cfe:py314_readiness`,
`cfe:lts_status` (+ `cfe:eol_date` where known), with `cfe:atlas_built_at`
stamped in metadata. The CLI name stays `recommend-2027`; the report
header states the 2027–2030 window explicitly.

Only matched (on-conda-forge) rows are scored; ADD / ADD-NONPYPI /
unmatched-UNKNOWN rows are listed as "not evaluated (not on conda-forge —
see add-handoff)". Per-signal freshness ages ride the report (decision 6),
and the atlas 14-day gate refuses stale data (--allow-stale overrides).

Operator overrides (decision 5): `pypi_intelligence.notes` containing
`cfe:futures_tier=<tier>` (Python side, read via the v29 view) and/or a
--overrides <yaml|json> sidecar `{name: {tier, reason}}` (non-Python).
An override REPLACES the tier but the report always shows
`overridden from <computed> (score N)` — never silently.

Phase-P downloads refresh (operator-gated): when the PyPI downloads
signal is older than ~90 d the report OFFERS the BigQuery refresh with
the § 13 cost-preflight instruction — it is never run implicitly (the
refresh itself is the LOCAL wave).

CLI:
  recommend-2027 [INPUT ...] [--matches RESULT.json] [--format FMT]
                 [--sbom-in BOM] [--sbom-out PATH]
                 [--weights FILE] [--overrides FILE]
                 [--report PATH] [--json] [--allow-stale]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

from export_purls import fold_name
from library_futures import DEFAULT_WEIGHTS, EolClient, score_packages
from universe_sbom import StaleAtlasError, check_freshness


def _get_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent / "data" / "conda-forge-expert"


DB_PATH = _get_data_dir() / "cf_atlas.db"
DEFAULT_REPORT_PATH = _get_data_dir() / "recommend-2027-report.md"

WINDOW = (2027, 2030)
DOWNLOADS_STALE_DAYS = 90
_NOTES_TIER_MARK = "cfe:futures_tier="
_VALID_TIERS = ("keep", "watch", "plan-migration", "replace")


# ── operator overrides ───────────────────────────────────────────────────────

def load_overrides_sidecar(path: Path) -> dict[str, dict[str, Any]]:
    """--overrides <yaml|json>: `{name: {tier, reason}}` (non-Python channel).
    Keys are folded so spelling variants match."""
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        import yaml  # type: ignore[import-untyped]
        raw = yaml.safe_load(text)
    else:
        raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError("overrides must be a mapping {name: {tier, reason}}")
    out: dict[str, dict[str, Any]] = {}
    for name, spec in raw.items():
        if isinstance(spec, str):
            spec = {"tier": spec}
        if not isinstance(spec, dict) or spec.get("tier") not in _VALID_TIERS:
            raise ValueError(f"override for {name!r}: tier must be one of {_VALID_TIERS}")
        out[fold_name(str(name))] = {"tier": spec["tier"],
                                     "reason": spec.get("reason")}
    return out


def _notes_overrides(conn: sqlite3.Connection,
                     scored: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """decision 5's Python channel: a `cfe:futures_tier=<tier>` marker in
    pypi_intelligence.notes (read via the v29 ORPHAN_RULE view)."""
    out: dict[str, dict[str, Any]] = {}
    names = [r["conda_name"] for r in scored if r.get("conda_name")]
    if not names:
        return out
    marks = ",".join("?" for _ in names)
    for conda_name, notes in conn.execute(
        f"SELECT p.conda_name, v.notes FROM packages p "
        f"JOIN v_pypi_intelligence_valid v ON v.pypi_name = p.pypi_name "
        f"WHERE p.conda_name IN ({marks}) AND v.notes IS NOT NULL", names,
    ):
        notes_str = str(notes)
        if _NOTES_TIER_MARK not in notes_str:
            continue
        tier = notes_str.split(_NOTES_TIER_MARK, 1)[1].split()[0].strip(",;")
        if tier in _VALID_TIERS:
            out[fold_name(conda_name)] = {"tier": tier,
                                          "reason": "pypi_intelligence.notes"}
    return out


def apply_overrides(scored: list[dict[str, Any]],
                    overrides: dict[str, dict[str, Any]]) -> None:
    """Override REPLACES futures_tier; the original stays visible."""
    for r in scored:
        key = fold_name(r.get("conda_name") or r.get("name") or "")
        ov = overrides.get(key)
        if not ov:
            continue
        r["override"] = {"tier": ov["tier"], "reason": ov.get("reason"),
                         "original_tier": r["futures_tier"],
                         "original_score": r["futures_score"]}
        r["futures_tier"] = ov["tier"]


# ── freshness ages + Phase-P staleness offer ────────────────────────────────

def signal_ages(conn: sqlite3.Connection, now: int) -> dict[str, Any]:
    """Per-signal MAX fetched-at ages in days (decision 6). NULL → absent."""
    def _age(sql: str) -> int | None:
        try:
            v = conn.execute(sql).fetchone()[0]
        except sqlite3.Error:
            return None
        if v is None:
            return None
        try:
            return int((now - int(float(v))) / 86400)
        except (TypeError, ValueError):
            return None
    return {
        "conda_downloads_age_days": _age(
            "SELECT MAX(downloads_fetched_at) FROM packages"),
        "vuln_scan_age_days": _age(
            "SELECT MAX(vuln_scanned_at) FROM v_current_version_vulns"),
        "pypi_json_age_days": _age(
            "SELECT MAX(json_fetched_at) FROM v_pypi_intelligence_valid"),
        "pypi_downloads_age_days": _age(
            "SELECT MAX(downloads_fetched_at) FROM v_pypi_intelligence_valid"),
    }


def detect_downloads_staleness(conn: sqlite3.Connection, now: int,
                               days: int = DOWNLOADS_STALE_DAYS) -> dict[str, Any] | None:
    """Operator-gated Phase-P offer: WARN when the PyPI downloads signal is
    older than ~90 d. NEVER runs the refresh — the report instructs the
    operator to run the § 13 dry-run cost preflight first (LOCAL wave)."""
    row = conn.execute(
        "SELECT MAX(downloads_fetched_at) FROM v_pypi_intelligence_valid"
    ).fetchone()
    if not row or row[0] is None:
        return None
    age_days = int((now - int(float(row[0]))) / 86400)
    if age_days <= days:
        return None
    return {
        "age_days": age_days,
        "threshold_days": days,
        "offer": ("PyPI downloads signal is stale — consider a Phase P "
                  "refresh (BigQuery): ALWAYS run the atlas-phase-engineering "
                  "§ 13 dry-run cost preflight first and approve the measured "
                  "estimate; never run implicitly."),
    }


# ── orchestration ────────────────────────────────────────────────────────────

def run_recommend(
    conn: sqlite3.Connection,
    match_rows: list[dict[str, Any]],
    eol_client: EolClient | None = None,
    weights: dict[str, Any] | None = None,
    overrides: dict[str, dict[str, Any]] | None = None,
    now: int | None = None,
) -> dict[str, Any]:
    now = now if now is not None else int(time.time())
    scored = score_packages(conn, match_rows, weights=weights or DEFAULT_WEIGHTS,
                            eol_client=eol_client, now=now)
    not_evaluated = [
        {"name": r.get("name"), "ecosystem": r.get("ecosystem"),
         "bucket": r.get("bucket")}
        for r in match_rows
        if not r.get("conda_name")
    ]
    all_overrides = _notes_overrides(conn, scored)
    all_overrides.update(overrides or {})   # sidecar beats notes
    apply_overrides(scored, all_overrides)

    built = None
    try:
        row = conn.execute("SELECT value FROM meta WHERE key='built_at'").fetchone()
        if row:
            try:
                built = dt.datetime.fromtimestamp(
                    int(float(row[0])), dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            except (ValueError, TypeError):
                built = row[0]
    except sqlite3.Error:
        pass

    tiers = {t: sum(1 for r in scored if r["futures_tier"] == t)
             for t in _VALID_TIERS}
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "built_at": built,
        "window": f"{WINDOW[0]}–{WINDOW[1]}",
        "weights_as_of": (weights or DEFAULT_WEIGHTS).get("as_of"),
        "tiers": tiers,
        "rows": scored,
        "not_evaluated": not_evaluated,
        "signal_ages": signal_ages(conn, now),
        "downloads_staleness": detect_downloads_staleness(conn, now),
    }


# ── outputs ──────────────────────────────────────────────────────────────────

def render_report(result: dict[str, Any]) -> str:
    lines = [
        f"# recommend-2027 — library survival scorecard for the "
        f"{result['window']} window",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- atlas built_at: {result['built_at']}",
        f"- weights as_of: {result['weights_as_of']}",
        "- tiers: " + ", ".join(f"{t}={n}" for t, n in result["tiers"].items()),
        "",
        "## Signal freshness (decision 6)",
        "",
    ]
    for k, v in result["signal_ages"].items():
        lines.append(f"- {k}: {v if v is not None else 'absent'}")
    stale = result.get("downloads_staleness")
    if stale:
        lines += ["", f"> **Phase P offer (operator-gated, {stale['age_days']} d "
                      f"> {stale['threshold_days']} d):** {stale['offer']}"]
    lines += ["", "## Scorecard", ""]
    for r in result["rows"]:
        bits = [f"score {r['futures_score']}",
                f"py314 {r['py314_readiness']}", f"lts {r['lts_status']}"]
        if r.get("eol_date"):
            bits.append(f"eol {r['eol_date']}")
        if r.get("confidence") == "low":
            bits.append("confidence LOW")
        if r.get("eol_stale"):
            bits.append("eol-cache STALE")
        ov = r.get("override")
        if ov:
            bits.append(f"OVERRIDDEN from {ov['original_tier']} "
                        f"(score {ov['original_score']})"
                        + (f" — {ov['reason']}" if ov.get("reason") else ""))
        enrich = r.get("vuln_enrichment")
        if enrich and enrich.get("max_epss") is not None:
            bits.append(f"max EPSS {enrich['max_epss']} (report-only)")
        lines.append(f"- **{r['conda_name']}** → **{r['futures_tier']}** "
                     f"({'; '.join(bits)})")
        if r.get("tier_reasons"):
            lines.append(f"    reasons: {'; '.join(r['tier_reasons'])}")
        if r.get("alternatives"):
            lines.append("    alternatives: "
                         + ", ".join(a["conda_name"] for a in r["alternatives"]))
        absent = r.get("signals_absent") or []
        if absent:
            lines.append(f"    signals_absent: {', '.join(absent)}")
    if not result["rows"]:
        lines.append("- (none scored)")
    lines += ["", "## Not evaluated (not on conda-forge — see add-handoff)", ""]
    for n in result["not_evaluated"]:
        lines.append(f"- {n['name']} ({n['ecosystem']}, bucket {n['bucket']})")
    if not result["not_evaluated"]:
        lines.append("- (none)")
    return "\n".join(lines) + "\n"


# purl-type → matcher ecosystem, mirroring inventory_match.annotate_sbom
_PURL_ECO = {"pypi": "pypi", "conda": "conda", "npm": "npm", "deb": "apt",
             "rpm": "dnf", "apk": "apk", "cargo": "cargo",
             "maven": "maven", "gem": "gem"}


def annotate_sbom(sbom_path: Path, scored: list[dict[str, Any]],
                  built_at: Any) -> dict[str, Any]:
    """The input CycloneDX BOM with the five S7/S8 `cfe:*` properties on
    every scored component + `cfe:atlas_built_at` stamped in metadata."""
    import re
    doc = json.loads(sbom_path.read_text(encoding="utf-8"))
    if doc.get("bomFormat") != "CycloneDX":
        raise ValueError("--sbom-out annotation requires a CycloneDX JSON --sbom-in")
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for r in scored:
        for name in (r.get("name"), r.get("conda_name")):
            if name:
                by_key.setdefault((r.get("ecosystem") or "", fold_name(name)), r)
    purl_type_re = re.compile(r"^pkg:([A-Za-z0-9.+-]+)/")
    for comp in doc.get("components") or []:
        name = comp.get("name") or ""
        purl = comp.get("purl") or ""
        m = purl_type_re.match(purl)
        row = None
        if m:
            eco = _PURL_ECO.get(m.group(1).lower(), "generic")
            row = by_key.get((eco, fold_name(name)))
        elif name:
            row = by_key.get(("pypi", fold_name(name))) \
                or by_key.get(("conda", fold_name(name)))
        if row is None:
            continue
        props = comp.setdefault("properties", [])
        props.append({"name": "cfe:futures_tier", "value": str(row["futures_tier"])})
        if row.get("futures_score") is not None:
            props.append({"name": "cfe:futures_score", "value": str(row["futures_score"])})
        props.append({"name": "cfe:py314_readiness", "value": str(row["py314_readiness"])})
        props.append({"name": "cfe:lts_status", "value": str(row["lts_status"])})
        if row.get("eol_date"):
            props.append({"name": "cfe:eol_date", "value": str(row["eol_date"])})
    meta_props = doc.setdefault("metadata", {}).setdefault("properties", [])
    meta_props.append({"name": "cfe:atlas_built_at", "value": str(built_at)})
    return doc


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description=f"Score a user inventory for the {WINDOW[0]}–{WINDOW[1]} "
                    "window (runs inventory-match then library-futures).")
    parser.add_argument("inputs", nargs="*", type=Path,
                        help="Manifest/lock/text files or project directories")
    parser.add_argument("--matches", type=Path, default=None,
                        help="Saved `inventory-match --json` result to consume "
                             "instead of running the matcher")
    parser.add_argument("--format", dest="format_", metavar="FMT", default=None,
                        help="Forwarded to inventory-match for text inputs")
    parser.add_argument("--sbom-in", type=Path, default=None,
                        help="CycloneDX/SPDX JSON SBOM input (annotation source "
                             "for --sbom-out)")
    parser.add_argument("--sbom-out", type=Path, default=None,
                        help="Write the --sbom-in BOM annotated with "
                             "cfe:futures_tier/score, cfe:py314_readiness, "
                             "cfe:lts_status")
    parser.add_argument("--weights", type=Path, default=None,
                        help="Criticality sidecar (csv/json) — the S5 "
                             "user_weight signal")
    parser.add_argument("--overrides", type=Path, default=None,
                        help="Operator override sidecar (yaml/json "
                             "{name: {tier, reason}})")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH,
                        help=f"Markdown report path (default {DEFAULT_REPORT_PATH})")
    parser.add_argument("--json", action="store_true",
                        help="Emit the full result as JSON on stdout")
    parser.add_argument("--allow-stale", action="store_true",
                        help="Bypass the 14-day atlas freshness gate (decision 6)")
    args = parser.parse_args()

    have_inline = bool(args.inputs or args.sbom_in)
    if have_inline == bool(args.matches):
        sys.stderr.write("give either INPUT files/--sbom-in or --matches, "
                         "not both/neither\n")
        return 1
    if args.sbom_out and not args.sbom_in:
        sys.stderr.write("--sbom-out requires --sbom-in (it annotates the input BOM)\n")
        return 1
    if not DB_PATH.exists():
        sys.stderr.write(
            f"cf_atlas.db not found at {DB_PATH}. "
            "Run `pixi run -e local-recipes build-cf-atlas` first.\n")
        return 1

    try:
        overrides = load_overrides_sidecar(args.overrides) if args.overrides else None
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"could not load --overrides: {exc}\n")
        return 1

    conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    try:
        check_freshness(conn, args.allow_stale)
        if args.matches:
            doc = json.loads(args.matches.read_text(encoding="utf-8"))
            match_rows = doc.get("rows") if isinstance(doc, dict) else None
            if not isinstance(match_rows, list):
                sys.stderr.write(f"--matches {args.matches}: no `rows` list "
                                 "(is this `inventory-match --json` output?)\n")
                return 1
        else:
            import inventory_match as im
            sidecar = im.load_weights(args.weights) if args.weights else None
            deps: list[Any] = []
            labels: list[str] = []
            if args.inputs:
                deps, labels, warnings = im.load_inventory(args.inputs, args.format_)
                for w in warnings:
                    sys.stderr.write(f"  warn: {w}\n")
            if args.sbom_in:
                fmt = im.detect_format(args.sbom_in)
                if fmt not in ("cyclonedx", "spdx"):
                    sys.stderr.write(f"--sbom-in {args.sbom_in}: not a "
                                     "recognizable CycloneDX/SPDX JSON SBOM\n")
                    return 1
                if args.sbom_out and fmt != "cyclonedx":
                    sys.stderr.write("--sbom-out annotation requires a "
                                     "CycloneDX --sbom-in\n")
                    return 1
                deps.extend(im._stamp_resolution(
                    im.FORMAT_PARSERS[fmt](args.sbom_in), fmt))
                labels.append(str(args.sbom_in))
            if not deps:
                sys.stderr.write("no dependencies parsed from any input\n")
                return 1
            match_rows = im.run(conn, deps, labels, weights=sidecar)["rows"]

        result = run_recommend(conn, match_rows, overrides=overrides)
        if args.sbom_out:
            annotated = annotate_sbom(args.sbom_in, result["rows"],
                                      result["built_at"])
            args.sbom_out.parent.mkdir(parents=True, exist_ok=True)
            args.sbom_out.write_text(
                json.dumps(annotated, indent=2) + "\n", encoding="utf-8")
    except StaleAtlasError as exc:
        sys.stderr.write(f"REFUSED: {exc}\n")
        return 1
    except (sqlite3.OperationalError, json.JSONDecodeError, OSError, ValueError) as exc:
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
