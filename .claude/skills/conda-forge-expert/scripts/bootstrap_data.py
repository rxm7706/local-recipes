#!/usr/bin/env python3
"""
bootstrap_data.py — Single command to download / refresh ALL data the
conda-forge-expert skill (and the atlas) needs to operate. Runs the
full chain in dependency order, surfaces progress, and accepts a
`--fresh` flag for a hard reset.

What it does (in order):
  1. mapping cache       — PyPI ↔ conda name mapping (parselmouth → pypi_conda_map.json)
  2. CVE DB              — OSV.dev legacy DB (used by scan_for_vulnerabilities)
  3. vdb (multi-source)  — AppThreat vdb (~2.5 GB; used by Phase G + scan-project --vdb)
  4. cf_atlas            — conda repodata + feedstock-outputs + parselmouth + PyPI Simple
  5. cf_atlas Phase E    — cf-graph-countyfair node_attrs (~150 MB tarball)
  6. cf_atlas Phase J/K/L/M — dep graph + VCS upstream + extra registries + bot health
  7. cf_atlas Phase G/G' — vdb risk summary (latest version + per-version with PHASE_GP_ENABLED)
  8. cf_atlas Phase H    — PyPI current version (with yanked detection)
  9. cf_atlas Phase N    — live GitHub data (CI / issues / PRs) — only if --gh and gh auth present

CLI:
  bootstrap-data [--fresh] [--no-vdb] [--no-cf-atlas]
                 [--gh] [--maintainer HANDLE] [--dry-run]

  --fresh       : wipe `.claude/data/conda-forge-expert/` first (hard reset).
  --no-vdb      : skip the 2.5 GB vdb refresh (saves ~5–10 min).
  --no-cf-atlas : skip the atlas rebuild (saves ~30 min cold + Phase F downloads).
  --gh          : run Phase N (live GitHub data); requires `gh auth login` first.
  --maintainer  : with --gh, scope Phase N to one maintainer (recommended).
  --dry-run     : print the steps without executing.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

DATA_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data" / "conda-forge-expert"
)
REPO_ROOT = Path(__file__).resolve().parents[5]


def _run(label: str, cmd: list[str], env_overrides: dict | None = None,
         dry_run: bool = False, timeout: int = 1800) -> bool:
    """Run a step with banner output. Returns True on success."""
    bar = "─" * 70
    print(f"\n{bar}")
    print(f"  → {label}")
    print(f"  $ {' '.join(cmd)}")
    if env_overrides:
        for k, v in env_overrides.items():
            print(f"    env {k}={v}")
    print(bar)
    if dry_run:
        print(f"  [dry-run] would execute the above")
        return True
    import os
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    t0 = time.monotonic()
    try:
        rc = subprocess.run(cmd, env=env, timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        print(f"  ⚠ {label} timed out after {timeout}s — continuing")
        return False
    elapsed = time.monotonic() - t0
    ok = rc == 0
    print(f"  {'✓' if ok else '✗'} {label} ({elapsed:.1f}s, rc={rc})")
    return ok


def hard_reset(dry_run: bool = False) -> None:
    """Delete the entire data dir and recreate it."""
    if not DATA_DIR.exists():
        print(f"  Data dir does not exist; nothing to reset: {DATA_DIR}")
        return
    print(f"  ⚠  HARD RESET: deleting {DATA_DIR}")
    if dry_run:
        size_mb = sum(
            f.stat().st_size for f in DATA_DIR.rglob("*") if f.is_file()
        ) / 1e6
        print(f"  [dry-run] would delete ~{size_mb:.1f} MB")
        return
    shutil.rmtree(DATA_DIR)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  ✓ Data dir reset.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap / refresh all conda-forge-expert data in one command."
    )
    parser.add_argument("--fresh", action="store_true",
                        help="Wipe .claude/data/conda-forge-expert/ first")
    parser.add_argument("--no-vdb", action="store_true", dest="no_vdb",
                        help="Skip the vdb refresh (saves 5-10 min + 2.5 GB on disk)")
    parser.add_argument("--no-cf-atlas", action="store_true", dest="no_cf_atlas",
                        help="Skip the cf_atlas rebuild")
    parser.add_argument("--no-cve-db", action="store_true", dest="no_cve_db",
                        help="Skip the legacy OSV.dev CVE DB refresh")
    parser.add_argument("--no-mapping", action="store_true", dest="no_mapping",
                        help="Skip the parselmouth name-mapping refresh")
    parser.add_argument("--gh", action="store_true",
                        help="Run Phase N (live GitHub data); requires gh auth")
    parser.add_argument("--maintainer", default=None,
                        help="With --gh, scope Phase N to one maintainer "
                             "(recommended unless you want a 6-hour run)")
    parser.add_argument("--with-per-version-vulns", action="store_true",
                        dest="with_pgp",
                        help="Run Phase G' (per-version vuln scoring; needs vuln-db env)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print steps without executing")
    args = parser.parse_args()

    print("═" * 70)
    print("  conda-forge-expert · bootstrap-data")
    print(f"  Data dir:  {DATA_DIR}")
    print(f"  Repo:      {REPO_ROOT}")
    print(f"  Mode:      {'dry-run' if args.dry_run else 'live'}")
    print("═" * 70)

    if args.fresh:
        hard_reset(args.dry_run)
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    results: list[tuple[str, bool]] = []

    # Step 1 — mapping cache (parselmouth)
    if not args.no_mapping:
        ok = _run("Refresh PyPI↔conda mapping cache",
                  ["pixi", "run", "-e", "local-recipes",
                   "update-mapping-cache"],
                  dry_run=args.dry_run, timeout=300)
        results.append(("mapping-cache", ok))

    # Step 2 — legacy OSV CVE DB
    if not args.no_cve_db:
        ok = _run("Refresh OSV.dev CVE DB (legacy, used by scan_for_vulnerabilities)",
                  ["pixi", "run", "-e", "local-recipes", "update-cve-db"],
                  dry_run=args.dry_run, timeout=600)
        results.append(("cve-db", ok))

    # Step 3 — vdb (heavy)
    if not args.no_vdb:
        ok = _run("Refresh vdb (AppThreat multi-source vulnerability DB; ~2.5 GB)",
                  ["pixi", "run", "-e", "vuln-db", "vdb-refresh"],
                  dry_run=args.dry_run, timeout=1800)
        results.append(("vdb-refresh", ok))

    # Step 4 — cf_atlas full build with all default + cf-graph + Phase L
    if not args.no_cf_atlas:
        cmd = ["pixi", "run", "-e", "local-recipes", "build-cf-atlas"]
        env = {"PHASE_E_ENABLED": "1"}  # pull cf-graph
        ok = _run("Build cf_atlas (B/B.5/B.6/C/C.5/D/E/E.5/F/G/H/J/K/L/M)",
                  cmd, env_overrides=env, dry_run=args.dry_run, timeout=2400)
        results.append(("cf-atlas-build", ok))

    # Step 5 — Phase G' per-version vuln scoring (opt-in)
    if args.with_pgp and not args.no_vdb:
        cmd = ["pixi", "run", "-e", "vuln-db", "build-cf-atlas"]
        env = {"PHASE_GP_ENABLED": "1"}
        ok = _run("Phase G' — per-version vuln scoring (vuln-db env)",
                  cmd, env_overrides=env, dry_run=args.dry_run, timeout=1800)
        results.append(("phase-gp", ok))

    # Step 6 — Phase N (live GitHub data) — opt-in via --gh
    if args.gh:
        cmd = ["pixi", "run", "-e", "local-recipes", "build-cf-atlas"]
        env = {"PHASE_N_ENABLED": "1"}
        if args.maintainer:
            env["PHASE_N_MAINTAINER"] = args.maintainer
        ok = _run("Phase N — live GitHub data (CI / issues / PRs)",
                  cmd, env_overrides=env, dry_run=args.dry_run, timeout=1800)
        results.append(("phase-n", ok))

    print("\n" + "═" * 70)
    print("  Bootstrap summary")
    print("═" * 70)
    for label, ok in results:
        marker = "✓" if ok else "✗"
        print(f"  {marker} {label}")
    failed = [l for l, ok in results if not ok]
    if failed:
        print(f"\n  {len(failed)} step(s) failed: {failed}")
        return 1
    print(f"\n  All {len(results)} step(s) completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
