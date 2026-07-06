#!/usr/bin/env python3
"""lts-registry-gap — propose lts-registry.yaml entries by diffing the
endoflife.date product list against atlas packages (a mapping-gap sibling).

The LTS registry (data/lts-registry.yaml) is hand-curated by design: every
entry is a verified conda-name → endoflife.date-slug decision, so no tool
ever writes it. This CLI closes the DISCOVERY gap only — it diffs the
endoflife.date all-products list against `v_actionable_packages`, skips
names the registry already covers (aliases included), and emits
ready-to-paste YAML entry proposals with conservative confidence tiers:

  exact   conda_name or pypi_name lowercase-equals a product slug
  likely  equality after `_`->`-` normalization, or after stripping a
          `python-` / `py-` conda-name prefix

Accept/reject stays with git review — this tool NEVER writes the registry.
Products list: /api/all.json via _http.resolve_endoflife_urls("all")
(ENDOFLIFE_BASE_URL mirror-routable), TTL-7d cache `eol_products.json` in
the runtime data dir with offline-stale fallback (the EolClient pattern).
Exit code 0 always (report tool).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from conda_forge_atlas import open_db  # noqa: E402
from library_futures import load_lts_registry  # noqa: E402


def _get_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent / "data" / "conda-forge-expert"


DB_PATH = _get_data_dir() / "cf_atlas.db"
PRODUCTS_CACHE_PATH = _get_data_dir() / "eol_products.json"   # runtime, gitignored


# ── products list (all.json) ─────────────────────────────────────────────────

def _http_products_fetcher() -> list[str] | None:
    """Fetch the endoflife.date all-products list via _http (mirror-routable,
    truststore-injected, skip_auth — public host). None on any failure."""
    try:
        from _http import make_request, open_url, resolve_endoflife_urls
    except Exception:
        return None
    for url in resolve_endoflife_urls("all"):
        try:
            req = make_request(url, skip_auth=True)
            with open_url(req, timeout=30) as resp:
                doc = json.loads(resp.read().decode("utf-8"))
            if isinstance(doc, list):
                return [str(s) for s in doc]
        except Exception:
            continue
    return None


def load_products(
    fetcher: Callable[[], list[str] | None] | None = None,
    cache_path: Path = PRODUCTS_CACHE_PATH,
    ttl_days: int = 7,
    now: int | None = None,
) -> tuple[list[str], str, bool]:
    """(slugs, source, stale). Fresh cache → cache; else fetch + store;
    fetch fail → stale cache fallback; nothing → ([], 'unavailable', False).
    Mirrors the EolClient cache contract (never raises)."""
    fetcher = fetcher if fetcher is not None else _http_products_fetcher
    ref = now if now is not None else int(time.time())
    cached: dict[str, Any] = {}
    try:
        doc = json.loads(cache_path.read_text(encoding="utf-8"))
        if isinstance(doc, dict):
            cached = doc
    except (OSError, ValueError):
        cached = {}
    if cached.get("products") and (ref - cached.get("fetched_at", 0)) < ttl_days * 86400:
        return list(cached["products"]), "cache", False
    fetched = None
    try:
        fetched = fetcher()
    except Exception:
        fetched = None
    if fetched:
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(
                json.dumps({"fetched_at": ref, "products": fetched}, indent=2),
                encoding="utf-8")
        except OSError:
            pass
        return fetched, "endoflife", False
    if cached.get("products"):
        return list(cached["products"]), "cache", True    # stale fallback
    return [], "unavailable", False


# ── matching ─────────────────────────────────────────────────────────────────

def _norm(name: str) -> str:
    return name.lower().replace("_", "-")


def _candidates(conn) -> list[tuple[str, str | None]]:
    # v_actionable_packages IS the canonical persona-filter scope.
    rows = conn.execute(
        "SELECT conda_name, pypi_name FROM v_actionable_packages "
        "ORDER BY conda_name").fetchall()
    return [(r[0], r[1]) for r in rows]


def classify(
    candidates: list[tuple[str, str | None]],
    slugs: list[str],
    registry: dict[str, Any],
) -> list[dict[str, Any]]:
    """One proposal per conda name, highest tier wins. Registry-covered
    names (incl. aliases — the load_lts_registry index carries both) are
    excluded: they're decided, not gaps."""
    slug_set = {s.lower() for s in slugs}
    proposals: list[dict[str, Any]] = []
    for conda_name, pypi_name in candidates:
        if not conda_name or conda_name.lower() in registry:
            continue
        if pypi_name and pypi_name.lower() in registry:
            continue
        hit: tuple[str, str, str] | None = None   # (slug, confidence, via)
        for label, value in (("conda_name", conda_name),
                             ("pypi_name", pypi_name or "")):
            if value and value.lower() in slug_set:
                hit = (value.lower(), "exact", f"{label} == slug")
                break
        if hit is None:
            for label, value in (("conda_name", conda_name),
                                 ("pypi_name", pypi_name or "")):
                if not value:
                    continue
                norm = _norm(value)
                if norm != value.lower() and norm in slug_set:
                    hit = (norm, "likely", f"{label} normalized (_ -> -)")
                    break
                for prefix in ("python-", "py-"):
                    if norm.startswith(prefix) and norm[len(prefix):] in slug_set:
                        hit = (norm[len(prefix):], "likely",
                               f"{label} sans '{prefix}' prefix")
                        break
                if hit:
                    break
        if hit:
            proposals.append({
                "conda_name": conda_name,
                "pypi_name": pypi_name,
                "slug": hit[0],
                "confidence": hit[1],
                "matched_via": hit[2],
            })
    return proposals


# ── rendering ────────────────────────────────────────────────────────────────

def render_yaml_snippets(proposals: list[dict[str, Any]], today: str) -> str:
    """Ready-to-paste `products:` entries, grouped exact-first. The operator
    still verifies slug identity + lts_policy on the product page before
    committing — that human step is the point of the registry."""
    lines: list[str] = []
    for tier in ("exact", "likely"):
        rows = [p for p in proposals if p["confidence"] == tier]
        if not rows:
            continue
        lines.append(f"# ── proposed ({tier}) — verify each product page before committing ──")
        for p in rows:
            lines.append(f"  {p['conda_name']}:")
            lines.append(f"    slug: {p['slug']}")
            lines.append("    aliases: []")
            lines.append("    source: endoflife")
            lines.append("    lts_policy: false   # verify against the product page")
            lines.append(f"    added: {today}")
            lines.append(f"    note: \"proposed by lts-registry-gap ({tier}: {p['matched_via']})\"")
    return "\n".join(lines) + ("\n" if lines else "")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Propose lts-registry.yaml entries by diffing the "
                    "endoflife.date product list against atlas packages. "
                    "READ-ONLY: never writes the registry.")
    ap.add_argument("--db", type=Path, default=DB_PATH,
                    help=f"Path to atlas DB (default: {DB_PATH})")
    ap.add_argument("--products-file", type=Path, default=None,
                    help="JSON array of product slugs (offline/test injection; "
                         "skips the network + cache)")
    ap.add_argument("--limit", type=int, default=0,
                    help="Cap proposals per tier (0 = no cap)")
    ap.add_argument("--out", type=Path, default=None,
                    help="Write the YAML snippets to FILE instead of stdout")
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="Machine-readable summary on stdout")
    args = ap.parse_args(argv)

    if args.products_file is not None:
        try:
            doc = json.loads(args.products_file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"error: cannot read --products-file: {exc}", file=sys.stderr)
            return 1
        slugs = [str(s) for s in doc] if isinstance(doc, list) else []
        source, stale = "file", False
    else:
        slugs, source, stale = load_products()
    if not slugs:
        print("error: no endoflife.date product list available "
              "(offline with an empty cache?)", file=sys.stderr)
        return 1

    registry = load_lts_registry()
    conn = open_db(path=args.db)
    try:
        proposals = classify(_candidates(conn), slugs, registry)
    finally:
        conn.close()

    if args.limit > 0:
        capped: list[dict[str, Any]] = []
        for tier in ("exact", "likely"):
            capped.extend(
                [p for p in proposals if p["confidence"] == tier][:args.limit])
        proposals = capped

    today = time.strftime("%Y-%m-%d", time.gmtime())
    summary = {
        "products": len(slugs),
        "products_source": source,
        "products_stale": stale,
        "registry_entries": len(registry),
        "proposals": proposals,
        "counts": {
            "exact": sum(1 for p in proposals if p["confidence"] == "exact"),
            "likely": sum(1 for p in proposals if p["confidence"] == "likely"),
        },
    }
    snippets = render_yaml_snippets(proposals, today)
    if args.out is not None:
        args.out.write_text(snippets, encoding="utf-8")
    if args.as_json:
        print(json.dumps(summary, indent=2))
    else:
        header = (f"lts-registry-gap: {len(proposals)} proposal(s) "
                  f"({summary['counts']['exact']} exact / "
                  f"{summary['counts']['likely']} likely) — "
                  f"{len(slugs)} products [{source}"
                  f"{', STALE' if stale else ''}], "
                  f"{len(registry)} registry keys covered")
        print(header)
        if snippets and args.out is None:
            print(snippets, end="")
        elif args.out is not None:
            print(f"snippets written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
