#!/usr/bin/env python3
"""
add-handoff — ADD-bucket packaging worklist with on-demand enrichment
(cyclonedx-universe-inventory Wave C / S6).

Consumes `inventory-match` results (inline run, or a saved `--json` file
via --matches) and emits the ready-to-consume packaging worklist for the
ADD bucket: name, readiness score, recommended template, blockers (e.g.
non-OSI license), `signals_absent` per row — sorted readiness-desc.
ADD-NONPYPI entries are appended unscored with their upstream identity
(ecosystem purl). No recipes are generated in this story.

Enrichment (bounded, BEFORE scoring): readiness/license coverage in
`pypi_intelligence` is sparse, so ADD names lacking `json_fetched_at` get
a Phase-R-style single-package `pypi.org/pypi/<name>/json` fetch — capped
at the inventory slice (--limit caps harder; dropped names are REPORTED,
never silently truncated), written back idempotently through the SAME
upsert Phase R uses (`conda_forge_atlas.phase_r_upsert_one` — the effort's
write-path discipline), then re-scored with the canonical Phase S formula
scoped to the slice (`apply_readiness_scores(conn, names)`).

FAIL-CLOSED license rule (spec S6): a NULL `license_spdx` NEVER silently
passes the OSI-eligibility check — it is the `license-unknown` blocker.
--no-enrich (offline mode) therefore leaves un-enriched rows BLOCKED, not
clean.

Freshness contract (decision 6): refuses an atlas older than 14 days or
with no parseable built_at (--allow-stale overrides).

CLI:
  add-handoff [INPUT ...] [--matches RESULT.json] [--format FMT]
              [--no-enrich] [--limit N]
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
from typing import Any, Callable

from conda_forge_atlas import (
    _OSI_APPROVED_SPDX,
    apply_readiness_scores,
    phase_r_upsert_one,
)
from universe_sbom import StaleAtlasError, check_freshness


def _get_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent / "data" / "conda-forge-expert"


DB_PATH = _get_data_dir() / "cf_atlas.db"
DEFAULT_REPORT_PATH = _get_data_dir() / "add-handoff-worklist.md"

# Fetcher signature — matches conda_forge_atlas._phase_r_fetch_one.
Fetcher = Callable[[str], tuple[str, dict | None, str | None]]


def _default_fetcher() -> Fetcher:
    """The real Phase R fetch worker (retries, Retry-After, jitter).
    Resolved lazily so fixture tests never touch the network path."""
    from conda_forge_atlas import _phase_r_fetch_one
    return _phase_r_fetch_one


# ── enrichment (the S6 write path) ──────────────────────────────────────────

def enrich_add_rows(
    conn: sqlite3.Connection,
    names: list[str],
    fetcher: Fetcher,
    limit: int | None = None,
) -> dict[str, Any]:
    """Bounded single-package enrichment for ADD names whose
    `pypi_intelligence` row lacks `json_fetched_at`. Idempotent by
    construction: already-enriched names are skipped up front, and the
    upsert is Phase R's own. Returns counters + the enriched name list.

    Names are de-duplicated (a name appearing in two manifests must not
    burn two live fetches / two --limit slots), and names absent from
    `pypi_universe` are NOT fetched — enriching them would mint exactly the
    orphan `pypi_intelligence` rows the schema-v29 ORPHAN_RULE excludes."""
    universe = {
        r[0] for r in conn.execute("SELECT pypi_name FROM pypi_universe")
    }
    needing: list[str] = []
    not_in_universe: list[str] = []
    seen: set[str] = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        if name not in universe:
            not_in_universe.append(name)
            continue
        # scope: eligibility probe, not version truth — mirrors Phase R's
        # own TTL query; NULL/missing json_fetched_at is exactly the signal.
        row = conn.execute(
            "SELECT json_fetched_at FROM pypi_intelligence WHERE pypi_name = ?",
            (name,),
        ).fetchone()
        if row is None or row[0] is None:
            needing.append(name)

    dropped: list[str] = []
    if limit is not None and len(needing) > limit:
        needing, dropped = needing[:limit], needing[limit:]

    now = int(time.time())
    fetched = failed = not_found = 0
    enriched_names: list[str] = []
    for name in needing:
        _, payload, err = fetcher(name)
        outcome = phase_r_upsert_one(conn, name, payload, err, now)
        if outcome == "fetched":
            fetched += 1
            enriched_names.append(name)
        elif outcome == "not_found":
            not_found += 1
            enriched_names.append(name)  # 404 IS an answer (project gone)
        else:
            failed += 1
    conn.commit()
    if enriched_names:
        apply_readiness_scores(conn, enriched_names)
    return {
        "eligible": len(needing) + len(dropped),
        "fetched": fetched,
        "not_found": not_found,
        "failed": failed,
        "dropped_by_limit": dropped,
        "not_in_universe": not_in_universe,
        "enriched_names": enriched_names,
    }


# ── worklist build ───────────────────────────────────────────────────────────

_INTEL_COLS = ("pypi_name", "latest_version", "latest_yanked", "license_spdx",
               "license_raw", "conda_forge_readiness", "recommended_template",
               "staged_recipes_pr_url", "has_sdist", "packaging_shape",
               "requires_python", "summary", "repo_url", "json_fetched_at",
               "json_last_error")


def _intel_for(conn: sqlite3.Connection, names: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for i in range(0, len(names), 500):
        chunk = names[i:i + 500]
        marks = ",".join("?" for _ in chunk)
        for row in conn.execute(
            f"SELECT {', '.join(_INTEL_COLS)} FROM v_pypi_intelligence_valid "
            f"WHERE pypi_name IN ({marks})", chunk,
        ):
            out[row[0]] = dict(zip(_INTEL_COLS, row))
    return out


def _row_name(r: dict[str, Any]) -> str | None:
    """The PyPI name of a match row: `pypi_name` (S5 always sets it for ADD)
    then `name`. None for a malformed row (hand-edited --matches) — callers
    skip those rather than KeyError."""
    n = r.get("pypi_name") or r.get("name")
    return n if isinstance(n, str) and n else None


def build_worklist(
    conn: sqlite3.Connection, add_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """One worklist entry per ADD row, blockers fail-closed on license."""
    paired = [(r, _row_name(r)) for r in add_rows]
    paired = [(r, n) for r, n in paired if n is not None]
    intel = _intel_for(conn, [n for _, n in paired])
    entries: list[dict[str, Any]] = []
    for match_row, name in paired:
        e = intel.get(name)
        blockers: list[str] = []
        signals_absent: list[str] = []
        entry: dict[str, Any] = {
            "pypi_name": name,
            "readiness": None,
            "template": None,
            "blockers": blockers,
            "signals_absent": signals_absent,
            "latest_version": None,
            "staged_recipes_pr_url": None,
            "local_recipe": bool(match_row.get("local_recipe")),
        }
        if e is None or e["json_fetched_at"] is None:
            # never enriched (skipped, failed, or not in the valid view) —
            # the OSI check CANNOT pass on absent data (fail-closed)
            signals_absent.append("pypi_enrichment")
            blockers.append("license-unknown")
            signals_absent.append("readiness_score")
            entries.append(entry)
            continue
        entry["latest_version"] = e["latest_version"]
        entry["readiness"] = e["conda_forge_readiness"]
        entry["template"] = e["recommended_template"]
        entry["staged_recipes_pr_url"] = e["staged_recipes_pr_url"]
        entry["summary"] = e["summary"]
        entry["packaging_shape"] = e["packaging_shape"]
        if e["json_last_error"] == "HTTP 404":
            blockers.append("pypi-project-gone")
        if e["license_spdx"] is None:
            blockers.append("license-unknown")  # enriched, still unresolvable
        elif e["license_spdx"] not in _OSI_APPROVED_SPDX:
            blockers.append(f"license-non-osi ({e['license_spdx']})")
        if e["latest_yanked"]:
            blockers.append("latest-yanked")
        if e["conda_forge_readiness"] is None:
            signals_absent.append("readiness_score")
        entries.append(entry)
    # readiness-desc, unscored last, name as tiebreak
    entries.sort(key=lambda x: (-(x["readiness"] if x["readiness"] is not None
                                  else -1), x["pypi_name"]))
    return entries


def nonpypi_entries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """ADD-NONPYPI rows appended unscored — upstream identity as a purl.
    Malformed rows (no name; hand-edited --matches) are skipped."""
    out = []
    valid = [r for r in rows if isinstance(r.get("name"), str) and r["name"]]
    for r in sorted(valid, key=lambda x: x["name"]):
        eco = r.get("ecosystem") or "generic"
        ver = f"@{r['pinned']}" if r.get("pinned") else ""
        out.append({
            "name": r["name"],
            "ecosystem": eco,
            "upstream_purl": f"pkg:{eco}/{r['name']}{ver}",
        })
    return out


def run_handoff(
    conn: sqlite3.Connection,
    match_rows: list[dict[str, Any]],
    fetcher: Fetcher | None = None,
    enrich: bool = True,
    limit: int | None = None,
) -> dict[str, Any]:
    add_rows = [r for r in match_rows if r.get("bucket") == "ADD"]
    nonpypi_rows = [r for r in match_rows if r.get("bucket") == "ADD-NONPYPI"]

    enrichment: dict[str, Any] = {"skipped": True}
    if enrich and add_rows:
        names = [n for n in (_row_name(r) for r in add_rows) if n]
        enrichment = enrich_add_rows(conn, names, fetcher or _default_fetcher(),
                                     limit=limit)

    built = None
    try:
        row = conn.execute("SELECT value FROM meta WHERE key='built_at'").fetchone()
        if row:
            # stored as a UNIX-epoch string — render ISO for the human report;
            # fall back to the raw value if it isn't a parseable timestamp.
            try:
                built = dt.datetime.fromtimestamp(
                    int(float(row[0])), dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            except (ValueError, TypeError):
                built = row[0]
    except sqlite3.Error:
        pass
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "built_at": built,
        "add_count": len(add_rows),
        "nonpypi_count": len(nonpypi_rows),
        "enrichment": enrichment,
        "worklist": build_worklist(conn, add_rows),
        "nonpypi": nonpypi_entries(nonpypi_rows),
    }


# ── report ───────────────────────────────────────────────────────────────────

def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# add-handoff packaging worklist",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- atlas built_at: {result['built_at']}",
        f"- ADD rows: {result['add_count']:,} · ADD-NONPYPI: {result['nonpypi_count']:,}",
    ]
    enr = result["enrichment"]
    if enr.get("skipped"):
        lines.append("- enrichment: SKIPPED (--no-enrich) — un-enriched rows "
                     "stay BLOCKED (license-unknown), never clean")
    else:
        lines.append(
            f"- enrichment: {enr['fetched']} fetched, {enr['not_found']} gone "
            f"(404), {enr['failed']} failed (stay eligible) of "
            f"{enr['eligible']} needing")
        if enr["dropped_by_limit"]:
            lines.append(
                f"- **--limit dropped {len(enr['dropped_by_limit'])} names "
                f"(still un-enriched, still blocked):** "
                + ", ".join(enr["dropped_by_limit"]))
        if enr.get("not_in_universe"):
            lines.append(
                f"- **{len(enr['not_in_universe'])} ADD names not in "
                f"pypi_universe (not fetched — would orphan; stale --matches?):** "
                + ", ".join(enr["not_in_universe"]))
    lines += ["", "## Worklist (readiness-desc)", ""]
    for e in result["worklist"]:
        bits = [f"readiness {e['readiness'] if e['readiness'] is not None else '?'}"]
        if e.get("latest_version"):
            bits.append(f"v{e['latest_version']}")
        if e.get("template"):
            bits.append(e["template"])
        if e["blockers"]:
            bits.append("BLOCKERS: " + ", ".join(e["blockers"]))
        if e.get("staged_recipes_pr_url"):
            bits.append(f"PR in flight: {e['staged_recipes_pr_url']}")
        if e.get("local_recipe"):
            bits.append("local recipe present")
        if e["signals_absent"]:
            bits.append("signals_absent: " + ", ".join(e["signals_absent"]))
        lines.append(f"- **{e['pypi_name']}** — {'; '.join(bits)}")
    if not result["worklist"]:
        lines.append("- (none)")
    lines += ["", "## ADD-NONPYPI (unscored, upstream identity only)", ""]
    for n in result["nonpypi"]:
        lines.append(f"- **{n['name']}** ({n['ecosystem']}) — {n['upstream_purl']}")
    if not result["nonpypi"]:
        lines.append("- (none)")
    return "\n".join(lines) + "\n"


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit the ADD-bucket packaging worklist from "
                    "inventory-match results (bounded enrichment first).")
    parser.add_argument("inputs", nargs="*", type=Path,
                        help="Inventory inputs (run inventory-match inline)")
    parser.add_argument("--matches", type=Path, default=None,
                        help="Saved `inventory-match --json` result to consume "
                             "instead of running the matcher")
    parser.add_argument("--format", dest="format_", metavar="FMT", default=None,
                        help="Forwarded to inventory-match for text inputs")
    parser.add_argument("--no-enrich", dest="enrich", action="store_false",
                        help="Offline: skip the bounded PyPI fetch (rows stay "
                             "BLOCKED license-unknown — fail-closed)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Cap live fetches (dropped names are reported)")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH,
                        help=f"Markdown worklist path (default {DEFAULT_REPORT_PATH})")
    parser.add_argument("--json", action="store_true",
                        help="Emit the full result as JSON on stdout")
    parser.add_argument("--allow-stale", action="store_true",
                        help="Bypass the 14-day atlas freshness gate (decision 6)")
    args = parser.parse_args()

    if bool(args.inputs) == bool(args.matches):
        sys.stderr.write("give either INPUT files/dirs or --matches, not both/neither\n")
        return 1
    if args.limit is not None and args.limit < 0:
        sys.stderr.write("--limit must be >= 0\n")
        return 1
    if not DB_PATH.exists():
        sys.stderr.write(
            f"cf_atlas.db not found at {DB_PATH}. "
            "Run `pixi run -e local-recipes build-cf-atlas` first.\n")
        return 1

    # RW connection: enrichment writes ride the S2 discipline (idempotent
    # upsert; --no-enrich never writes).
    conn = sqlite3.connect(DB_PATH)
    try:
        check_freshness(conn, args.allow_stale)
        if args.matches:
            doc = json.loads(args.matches.read_text(encoding="utf-8"))
            # a bare JSON list (or any non-object) has no `rows` — guard the
            # .get() so a hand-made/wrong file gets the friendly message,
            # not an AttributeError traceback.
            match_rows = doc.get("rows") if isinstance(doc, dict) else None
            if not isinstance(match_rows, list):
                sys.stderr.write(f"--matches {args.matches}: no `rows` list "
                                 "(is this `inventory-match --json` output?)\n")
                return 1
        else:
            import inventory_match as im
            deps, labels, warnings = im.load_inventory(args.inputs, args.format_)
            for w in warnings:
                sys.stderr.write(f"  warn: {w}\n")
            if not deps:
                sys.stderr.write("no dependencies parsed from any input\n")
                return 1
            match_rows = im.run(conn, deps, labels)["rows"]

        result = run_handoff(conn, match_rows, enrich=args.enrich,
                             limit=args.limit)
    except StaleAtlasError as exc:
        sys.stderr.write(f"REFUSED: {exc}\n")
        return 1
    except (sqlite3.OperationalError, json.JSONDecodeError, OSError) as exc:
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
