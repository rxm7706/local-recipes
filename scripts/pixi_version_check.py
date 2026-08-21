#!/usr/bin/env python3
"""pixi-version-check — every pixi-version pin site agrees with pixi.toml's
own `requires-pixi` floor.

`pixi.toml`'s `requires-pixi` comment enumerates every place a pixi version
is duplicated (CI workflows, both Containerfiles, environment.yaml) and
says, in its own words, "NOTHING ENFORCES ANY OF THIS." It has drifted three
times, most recently 2026-08-21 when a `pixi upgrade` raised the floor to
0.77.0 but 10 external sites stayed at 0.76.2 -- one of them
(`src/platform/compose/dbgpt/Containerfile`) was never even registered in
the comment, and broke `container-dbgpt` CI the very next push. This is the
detector that comment always said was the durable fix; the registry it
checks lives in `scripts/pixi_version_registry.py`, not here.

Findings:
  version-mismatch  a site's pinned version differs from pixi.toml's floor
  hit-count-drift   a site's expected occurrence count no longer matches
                    (a pin was added, removed, or the registry itself is stale)
  missing-file      a registered site's file no longer exists

Reconciler: `pixi run -e local-recipes bump-pixi-version -- <version>`.

Exit codes: 0 clean, 1 drift found, 2 pixi.toml itself unreadable.
"""
from __future__ import annotations

# Registry declaration — see scripts/detectors.py. `repo`: reads tracked files only.
DETECTOR = {"scope": "repo"}

import argparse
import json
import sys

from pixi_version_registry import SITES, master_version, read_versions


def run() -> tuple[list[dict], dict]:
    master = master_version()
    findings: list[dict] = []

    for site in SITES:
        versions, existed = read_versions(site)
        if not existed:
            findings.append({
                "kind": "missing-file", "site": site.name,
                "detail": f"{site.path} no longer exists",
            })
            continue
        if len(versions) != site.expected_hits:
            findings.append({
                "kind": "hit-count-drift", "site": site.name,
                "detail": f"expected {site.expected_hits} pin(s) in {site.path}, "
                          f"found {len(versions)}",
            })
            continue
        for v in versions:
            if v != master:
                findings.append({
                    "kind": "version-mismatch", "site": site.name,
                    "detail": f"{site.path} pins {v}, pixi.toml requires-pixi is >={master}",
                })

    return findings, {"master_version": master, "sites_checked": len(SITES)}


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pixi-version-check",
        description="Detect drift between pixi.toml's requires-pixi floor and every "
                    "other pixi-version pin site in the repo. Exits 1 on drift.")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    try:
        findings, stats = run()
    except RuntimeError as exc:
        print(f"pixi-version-check: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"stats": stats, "findings": findings}, indent=2))
        return 1 if findings else 0

    print(f"pixi-version-check: master floor >={stats['master_version']} "
          f"(pixi.toml requires-pixi) | {stats['sites_checked']} site(s) checked\n")
    if not findings:
        print("  clean — every pin site matches the floor.")
        return 0
    for f in findings:
        print(f"  {f['kind']}: {f['site']} — {f['detail']}")
    print(f"\nDRIFT: {len(findings)} finding(s). Reconcile with "
          f"`pixi run -e local-recipes bump-pixi-version -- {stats['master_version']}`.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
