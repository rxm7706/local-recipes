#!/usr/bin/env python3
"""spdx-schema-gap — propose spdx.schema.json enum additions by diffing the
vendored SPDX license enum against the upstream SPDX license list, prioritized
by the licenses real conda-forge packages actually carry (a mapping-gap
sibling for the SPDX schema).

The vendored enum (data/spdx.schema.json, ~811 IDs at v3.28.0) is used by
`_sbom.normalize_license` + `conda_forge_atlas._normalize_license_to_spdx`;
it drifts behind the upstream SPDX license list, and real package licenses
can fall outside it unnoticed. This CLI closes the DISCOVERY gap only — it
takes each distinct `conda_license` on `v_actionable_packages` that the
vendored enum does NOT cover and classifies it:

  add-to-schema   the string IS a current upstream SPDX ID → genuine
                  staleness; add it to the vendored enum (ranked by how many
                  packages use it)
  non-standard    not upstream either → a normalization candidate, NOT a
                  schema add (report-only)

Compound SPDX *expressions* (containing AND/OR/WITH or parens) are skipped —
the enum holds single IDs only. `--drift` lists upstream IDs absent from the
vendored enum regardless of atlas usage.

Accept/reject stays with git review — this tool NEVER writes the schema.
Upstream list: spdx/license-list-data json/licenses.json via
_http.resolve_github_raw_urls (GITHUB_RAW_BASE_URL-routable), TTL-7d cache
`spdx_license_list.json` with offline-stale fallback. Exit code 0 always.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from conda_forge_atlas import open_db  # noqa: E402
from _sbom import _spdx_id_enum  # noqa: E402


def _get_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent / "data" / "conda-forge-expert"


UPSTREAM_CACHE_PATH = _get_data_dir() / "spdx_license_list.json"   # runtime, gitignored
_EXPRESSION_RE = re.compile(r"[()]|(?:^|\s)(?:AND|OR|WITH)(?:\s|$)")


# ── upstream SPDX license list ───────────────────────────────────────────────

def _http_spdx_fetcher() -> list[str] | None:
    """Fetch the upstream SPDX license IDs via _http (mirror-routable,
    skip_auth — public host). None on any failure."""
    try:
        from _http import make_request, open_url, resolve_github_raw_urls
    except Exception:
        return None
    for url in resolve_github_raw_urls(
            "spdx/license-list-data", "main", "json/licenses.json"):
        try:
            req = make_request(url, skip_auth=True)
            with open_url(req, timeout=30) as resp:
                doc = json.loads(resp.read().decode("utf-8"))
            lics = doc.get("licenses") if isinstance(doc, dict) else None
            if isinstance(lics, list):
                return [str(x["licenseId"]) for x in lics
                        if isinstance(x, dict) and x.get("licenseId")]
        except Exception:
            continue
    return None


def load_upstream_spdx(
    fetcher: Callable[[], list[str] | None] | None = None,
    cache_path: Path = UPSTREAM_CACHE_PATH,
    ttl_days: int = 7,
    now: int | None = None,
) -> tuple[list[str], str, bool]:
    """(ids, source, stale). Fresh cache → cache; else fetch + store; fetch
    fail → stale cache fallback; nothing → ([], 'unavailable', False).
    Mirrors the lts-registry-gap products-cache contract (never raises)."""
    fetcher = fetcher if fetcher is not None else _http_spdx_fetcher
    ref = now if now is not None else int(time.time())
    cached: dict[str, Any] = {}
    try:
        doc = json.loads(cache_path.read_text(encoding="utf-8"))
        if isinstance(doc, dict):
            cached = doc
    except (OSError, ValueError):
        cached = {}
    # A hand-edited / corrupt cache (non-list ids, non-numeric fetched_at)
    # must not break the "never raises" contract — type-guard both fields.
    ids = cached.get("ids")
    fetched_at = cached.get("fetched_at", 0)
    if (isinstance(ids, list) and isinstance(fetched_at, (int, float))
            and (ref - fetched_at) < ttl_days * 86400):
        return list(ids), "cache", False
    fetched = None
    try:
        fetched = fetcher()
    except Exception:
        fetched = None
    if fetched:
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(
                json.dumps({"fetched_at": ref, "ids": fetched}, indent=2),
                encoding="utf-8")
        except OSError:
            pass
        return fetched, "spdx", False
    if isinstance(cached.get("ids"), list):
        return list(cached["ids"]), "cache", True   # stale fallback
    return [], "unavailable", False


# ── atlas license usage ──────────────────────────────────────────────────────

def _atlas_license_counts(conn) -> dict[str, int]:
    """{conda_license: package_count} across the canonical persona view."""
    counts: dict[str, int] = {}
    for lic, n in conn.execute(
            "SELECT conda_license, COUNT(*) FROM v_actionable_packages "
            "WHERE conda_license IS NOT NULL AND conda_license != '' "
            "GROUP BY conda_license"):
        counts[str(lic)] = int(n)
    return counts


def _is_expression(s: str) -> bool:
    return bool(_EXPRESSION_RE.search(s))


def classify(
    atlas_counts: dict[str, int],
    vendored: set[str],
    upstream: set[str],
) -> dict[str, list[dict[str, Any]]]:
    """Partition the atlas license strings the vendored enum misses into
    add-to-schema (a real upstream SPDX ID) vs non-standard (everything
    else). Expressions are skipped. Both lists are package-count-ranked."""
    vendored_lower = {v.lower() for v in vendored}
    upstream_by_lower = {u.lower(): u for u in upstream}
    add: list[dict[str, Any]] = []
    nonstd: list[dict[str, Any]] = []
    for lic, count in atlas_counts.items():
        if lic in vendored or lic.lower() in vendored_lower:
            continue
        if _is_expression(lic):
            continue
        up = upstream_by_lower.get(lic.lower())
        if up is not None:
            add.append({"license": lic, "spdx_id": up, "packages": count})
        else:
            nonstd.append({"license": lic, "packages": count})
    add.sort(key=lambda r: (-r["packages"], r["spdx_id"]))
    nonstd.sort(key=lambda r: (-r["packages"], r["license"]))
    return {"add_to_schema": add, "non_standard": nonstd}


def render_enum_lines(add: list[dict[str, Any]]) -> str:
    """Ready-to-paste enum-ID additions (the add-to-schema tier). The
    operator inserts these into spdx.schema.json's `enum` in sorted order."""
    if not add:
        return ""
    lines = ["  // add to spdx.schema.json `enum` (real SPDX IDs on packages, "
             "missing from the vendored copy):"]
    for r in add:
        lines.append(f'  "{r["spdx_id"]}",   // {r["packages"]} package(s)')
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Propose spdx.schema.json enum additions by diffing the "
                    "vendored enum against upstream SPDX, ranked by atlas "
                    "license usage. READ-ONLY: never writes the schema.")
    from conda_forge_atlas import DB_PATH
    ap.add_argument("--db", type=Path, default=DB_PATH,
                    help=f"Path to atlas DB (default: {DB_PATH})")
    ap.add_argument("--source-file", type=Path, default=None,
                    help="JSON array of upstream SPDX IDs, OR the upstream "
                         "licenses.json object (offline/test; skips net+cache)")
    ap.add_argument("--drift", action="store_true",
                    help="Also list upstream IDs absent from the vendored enum "
                         "regardless of atlas usage (pure staleness count)")
    ap.add_argument("--limit", type=int, default=0,
                    help="Cap each output list (0 = no cap)")
    ap.add_argument("--out", type=Path, default=None,
                    help="Write the enum-addition snippets to FILE")
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="Machine-readable summary on stdout")
    args = ap.parse_args(argv)

    if args.source_file is not None:
        try:
            doc = json.loads(args.source_file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"error: cannot read --source-file: {exc}", file=sys.stderr)
            return 1
        if isinstance(doc, dict):
            lics = doc.get("licenses")
            doc = ([str(x["licenseId"]) for x in lics
                    if isinstance(x, dict) and x.get("licenseId")]
                   if isinstance(lics, list) else [])
        upstream_ids = [str(s) for s in doc] if isinstance(doc, list) else []
        source, stale = "file", False
    else:
        upstream_ids, source, stale = load_upstream_spdx()
    if not upstream_ids:
        print("error: no upstream SPDX license list available "
              "(offline with an empty cache?)", file=sys.stderr)
        return 1

    vendored = set(_spdx_id_enum())
    upstream = set(upstream_ids)
    conn = open_db(path=args.db)
    try:
        atlas_counts = _atlas_license_counts(conn)
    finally:
        conn.close()

    result = classify(atlas_counts, vendored, upstream)
    if args.limit > 0:
        result["add_to_schema"] = result["add_to_schema"][:args.limit]
        result["non_standard"] = result["non_standard"][:args.limit]

    drift = sorted(upstream - vendored) if args.drift else []
    if args.limit > 0:
        drift = drift[:args.limit]

    summary = {
        "vendored_enum": len(vendored),
        "upstream_ids": len(upstream),
        "upstream_source": source,
        "upstream_stale": stale,
        "distinct_atlas_licenses": len(atlas_counts),
        "add_to_schema": result["add_to_schema"],
        "non_standard": result["non_standard"],
        "counts": {
            "add_to_schema": len(result["add_to_schema"]),
            "non_standard": len(result["non_standard"]),
            "upstream_drift": len(upstream - vendored),
        },
    }
    if args.drift:
        summary["upstream_drift_ids"] = drift

    snippets = render_enum_lines(result["add_to_schema"])
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(snippets, encoding="utf-8")
    if args.as_json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"spdx-schema-gap: {summary['counts']['add_to_schema']} "
              f"add-to-schema / {summary['counts']['non_standard']} "
              f"non-standard — vendored {len(vendored)} vs upstream "
              f"{len(upstream)} [{source}{', STALE' if stale else ''}], "
              f"{summary['counts']['upstream_drift']} upstream IDs not vendored")
        if snippets and args.out is None:
            print(snippets, end="")
        elif args.out is not None:
            print(f"snippets written to {args.out}")
        if result["non_standard"]:
            top = ", ".join(f"{r['license']} ({r['packages']})"
                            for r in result["non_standard"][:8])
            print(f"  non-standard (normalize, not schema): {top}"
                  f"{' …' if len(result['non_standard']) > 8 else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
