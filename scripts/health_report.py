#!/usr/bin/env python3
"""Recipe health dashboard generator.

Scans all recipes and produces a CSV report plus a console summary.

Usage:
    python scripts/health_report.py [options]

Options:
    --recipes-dir PATH   Path to recipes directory (default: recipes/)
    --output PATH        Output CSV path (default: health_report.csv)
    --workers N          Parallel workers for local checks (default: 8)
    --limit N            Process only first N recipes (useful for testing)
    --check-versions     Query PyPI for version updates (network)
    --check-cves         Scan dependencies via OSV.dev (network)
    --validate           Run rattler-build lint per recipe (slow, ~30s each)
    --offline            Force offline mode for CVE scanning
"""

import argparse
import csv
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Path setup — add the skills scripts dir so we can import the tools directly
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_SCRIPTS = REPO_ROOT / ".claude" / "skills" / "conda-forge-expert" / "scripts"
sys.path.insert(0, str(SKILLS_SCRIPTS))

try:
    from recipe_optimizer import optimize_recipe
    HAS_OPTIMIZER = True
except ImportError:
    HAS_OPTIMIZER = False
    print("[warn] recipe_optimizer not available — optimize checks skipped", file=sys.stderr)

try:
    from validate_recipe import validate_recipe
    HAS_VALIDATOR = True
except ImportError:
    HAS_VALIDATOR = False
    print("[warn] validate_recipe not available — validation checks skipped", file=sys.stderr)

try:
    from vulnerability_scanner import run_scan
    HAS_SCANNER = True
except ImportError:
    HAS_SCANNER = False
    print("[warn] vulnerability_scanner not available — CVE checks skipped", file=sys.stderr)

try:
    from recipe_updater import update_recipe
    HAS_UPDATER = True
except ImportError:
    HAS_UPDATER = False
    print("[warn] recipe_updater not available — version checks skipped", file=sys.stderr)


# ---------------------------------------------------------------------------
# Format detection + recipe metadata extraction
# ---------------------------------------------------------------------------

def detect_format(recipe_dir: Path) -> str:
    has_v1 = (recipe_dir / "recipe.yaml").exists()
    has_v0 = (recipe_dir / "meta.yaml").exists()
    if has_v1 and has_v0:
        return "both"
    if has_v1:
        return "v1"
    if has_v0:
        return "v0"
    return "empty"


def is_recipe_dir(recipe_dir: Path) -> bool:
    """Return True only if the directory contains at least one recipe file."""
    return (recipe_dir / "recipe.yaml").exists() or (recipe_dir / "meta.yaml").exists()


def extract_recipe_meta(recipe_dir: Path) -> dict:
    """Read version and python_min directly from the recipe file (fast, no deps)."""
    meta = {"version_current": "", "python_min": "", "outdated_python_min": False}

    recipe_file = recipe_dir / "recipe.yaml"
    is_v1 = recipe_file.exists()
    if not is_v1:
        recipe_file = recipe_dir / "meta.yaml"
    if not recipe_file.exists():
        return meta

    try:
        text = recipe_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return meta

    if is_v1:
        # context:
        #   version: "1.2.3"
        #   python_min: "3.9"
        m = re.search(r"^\s+version:\s+['\"]?([^\s'\"#]+)", text, re.MULTILINE)
        if m:
            meta["version_current"] = m.group(1)
        m = re.search(r"^\s+python_min:\s+['\"]?([^\s'\"#]+)", text, re.MULTILINE)
        if m:
            meta["python_min"] = m.group(1)
    else:
        # {% set version = "1.2.3" %}
        m = re.search(r'{%[-\s]*set\s+version\s*=\s*["\']([^"\']+)["\']', text)
        if m:
            meta["version_current"] = m.group(1)
        # {% set python_min = "3.9" %}
        m = re.search(r'{%[-\s]*set\s+python_min\s*=\s*["\']([^"\']+)["\']', text)
        if m:
            meta["python_min"] = m.group(1)

    if meta["python_min"]:
        try:
            parts = [int(x) for x in meta["python_min"].split(".")[:2]]
            meta["outdated_python_min"] = parts < [3, 10]
        except ValueError:
            pass

    return meta


# ---------------------------------------------------------------------------
# Per-recipe health check
# ---------------------------------------------------------------------------

def check_recipe(
    recipe_dir: Path,
    *,
    run_validate: bool,
    run_versions: bool,
    run_cves: bool,
    offline: bool,
) -> dict:
    name = recipe_dir.name
    recipe_meta = extract_recipe_meta(recipe_dir)
    result = {
        "name": name,
        "format": detect_format(recipe_dir),
        "python_min": recipe_meta["python_min"],
        "outdated_python_min": "True" if recipe_meta["outdated_python_min"] else "",
        "optimize_codes": "",
        "optimize_count": 0,
        "validate_passed": "",
        "validate_errors": "",
        "validate_warnings": "",
        "version_current": recipe_meta["version_current"],
        "version_latest": "",
        "is_outdated": "",
        "cve_count": "",
        "cve_ids": "",
        "error": "",
    }

    # Determine recipe path for tools that want the recipe file directly
    recipe_file = recipe_dir / "recipe.yaml"
    if not recipe_file.exists():
        recipe_file = recipe_dir / "meta.yaml"

    # -- Optimize (always, fast) --
    if HAS_OPTIMIZER and recipe_file.exists():
        try:
            suggestions = optimize_recipe(recipe_dir)
            codes = [s.code for s in suggestions]
            result["optimize_codes"] = "|".join(codes)
            result["optimize_count"] = len(codes)
        except Exception as exc:
            result["error"] += f"optimize:{exc}; "

    # -- Validate (optional, spawns rattler-build) --
    if run_validate and HAS_VALIDATOR and recipe_file.exists():
        try:
            vr = validate_recipe(recipe_dir)
            result["validate_passed"] = str(vr.passed)
            result["validate_errors"] = "|".join(vr.errors)
            result["validate_warnings"] = "|".join(vr.warnings)
        except Exception as exc:
            result["error"] += f"validate:{exc}; "

    # -- Version check (optional, hits PyPI) --
    if run_versions and HAS_UPDATER and recipe_file.exists():
        try:
            upd = update_recipe(recipe_file, dry_run=True)
            if upd.get("success"):
                result["version_latest"] = upd.get("new_version") or result["version_current"]
                result["is_outdated"] = str(bool(upd.get("updated")))
        except Exception as exc:
            result["error"] += f"version:{exc}; "

    # -- CVE scan (optional, hits OSV.dev) --
    if run_cves and HAS_SCANNER and recipe_file.exists():
        try:
            scan = run_scan(recipe_dir, offline=offline)
            if scan.get("success"):
                result["cve_count"] = scan.get("total_vulnerabilities", 0)
                vuln_ids = [
                    v["id"]
                    for pkg in scan.get("results", [])
                    for v in pkg.get("vulns", [])
                ]
                result["cve_ids"] = "|".join(vuln_ids)
        except Exception as exc:
            result["error"] += f"cve:{exc}; "

    return result


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

def _counter(rows: list[dict], field: str) -> dict:
    counts: dict = {}
    for row in rows:
        for code in row[field].split("|"):
            if code:
                counts[code] = counts.get(code, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))


def print_summary(rows: list[dict], elapsed: float, args: argparse.Namespace) -> None:
    total = len(rows)
    fmt_counts: dict = {}
    for r in rows:
        fmt_counts[r["format"]] = fmt_counts.get(r["format"], 0) + 1

    print("\n" + "=" * 60)
    print(f"  Recipe Health Report  ({total} recipes, {elapsed:.1f}s)")
    print("=" * 60)

    print("\nFormat breakdown:")
    for fmt, count in sorted(fmt_counts.items()):
        bar = "#" * (count * 30 // total)
        print(f"  {fmt:<6}  {count:>5}  {bar}")

    # python_min stats
    outdated_pm = [r["name"] for r in rows if r.get("outdated_python_min") == "True"]
    if outdated_pm:
        print(f"\nOutdated python_min (<3.10):  {len(outdated_pm)} recipes")
        # Group by value
        pm_vals: dict = {}
        for r in rows:
            if r.get("outdated_python_min") == "True":
                v = r["python_min"]
                pm_vals[v] = pm_vals.get(v, 0) + 1
        for val, cnt in sorted(pm_vals.items()):
            print(f"  python_min={val:<6}  {cnt:>5} recipes")

    if any(r["optimize_count"] for r in rows):
        code_counts = _counter(rows, "optimize_codes")
        print(f"\nTop optimize issues (recipes affected):")
        for code, count in list(code_counts.items())[:10]:
            print(f"  {code:<12}  {count:>5}")

    if args.validate:
        failed = sum(1 for r in rows if r["validate_passed"] == "False")
        print(f"\nValidation:  {failed} failed / {total} total")

    if args.check_versions:
        outdated = sum(1 for r in rows if r["is_outdated"] == "True")
        print(f"\nOutdated:    {outdated} / {total}")

    if args.check_cves:
        with_cves = sum(1 for r in rows if r["cve_count"] not in ("", "0", 0))
        total_cves = sum(int(r["cve_count"]) for r in rows if str(r["cve_count"]).isdigit())
        print(f"\nCVEs:        {total_cves} total across {with_cves} recipes")

    errors = [r["name"] for r in rows if r["error"]]
    if errors:
        print(f"\nCheck errors: {len(errors)} recipes (see CSV 'error' column)")

    print(f"\nReport written to: {args.output}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--recipes-dir", default="recipes", help="Path to recipes directory")
    parser.add_argument("--output", default="health_report.csv", help="Output CSV path")
    parser.add_argument("--workers", type=int, default=8, help="Parallel workers")
    parser.add_argument("--limit", type=int, default=0, help="Process only first N recipes (0 = all)")
    parser.add_argument("--check-versions", action="store_true", help="Query PyPI for version updates")
    parser.add_argument("--check-cves", action="store_true", help="Scan via OSV.dev")
    parser.add_argument("--validate", action="store_true", help="Run rattler-build lint (slow)")
    parser.add_argument("--offline", action="store_true", help="Force offline CVE scanning")
    args = parser.parse_args()

    recipes_dir = Path(args.recipes_dir)
    if not recipes_dir.is_absolute():
        recipes_dir = REPO_ROOT / recipes_dir

    if not recipes_dir.exists():
        print(f"error: recipes directory not found: {recipes_dir}", file=sys.stderr)
        sys.exit(1)

    recipe_dirs = sorted(d for d in recipes_dir.iterdir() if d.is_dir() and is_recipe_dir(d))
    if args.limit:
        recipe_dirs = recipe_dirs[: args.limit]

    total = len(recipe_dirs)
    print(f"Scanning {total} recipes", end="", flush=True)
    if args.validate:
        print(" [+validate]", end="", flush=True)
    if args.check_versions:
        print(" [+versions]", end="", flush=True)
    if args.check_cves:
        print(" [+cves]", end="", flush=True)
    print(" ...")

    # Local-only checks (optimize, format) are parallelized freely.
    # Network/subprocess checks run in the same worker pool but with a
    # smaller degree of parallelism to respect rate limits.
    workers = args.workers
    if args.check_cves or args.check_versions:
        workers = min(workers, 4)

    results: list[dict] = []
    done = 0
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                check_recipe,
                d,
                run_validate=args.validate,
                run_versions=args.check_versions,
                run_cves=args.check_cves,
                offline=args.offline,
            ): d.name
            for d in recipe_dirs
        }
        for future in as_completed(futures):
            done += 1
            if done % 50 == 0 or done == total:
                pct = done * 100 // total
                elapsed = time.time() - t0
                eta = (elapsed / done) * (total - done) if done < total else 0
                print(f"  {done}/{total} ({pct}%)  {elapsed:.0f}s elapsed  ETA {eta:.0f}s", flush=True)
            try:
                results.append(future.result())
            except Exception as exc:
                results.append({"name": futures[future], "error": str(exc)})

    # Sort alphabetically
    results.sort(key=lambda r: r["name"].lower())

    # Write CSV
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = REPO_ROOT / output_path

    fieldnames = [
        "name", "format",
        "version_current", "python_min", "outdated_python_min",
        "optimize_count", "optimize_codes",
        "validate_passed", "validate_errors", "validate_warnings",
        "version_latest", "is_outdated",
        "cve_count", "cve_ids",
        "error",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    print_summary(results, time.time() - t0, args)


if __name__ == "__main__":
    main()
