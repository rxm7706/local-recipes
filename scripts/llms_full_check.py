#!/usr/bin/env python3
"""llms-full-check — detect drift between pixi.toml and docs/reference/library-llms-full.md.

The catalog (docs/reference/library-llms-full.md) is an LLM-authored derivative of
pixi.toml. This detector is the cheap, deterministic half of the
detector/reconciler loop (same pattern as bmad_drift_check.py):

  undocumented-dep  active dependency in pixi.toml never mentioned in the catalog
  ghost-entry       versioned catalog entry whose package left pixi.toml
  floor-drift       catalog version floor incompatible with the manifest spec

Reconciler: the regeneration prompt in the catalog's header (an LLM rewrite);
this script never edits either file.

Deliberately unchecked (regeneration territory, not detection): commented-out
deps vs the catalog's "explicitly NOT available" section, env-membership prose,
capability text.

Exit codes: 0 clean, 1 drift found, 2 missing input file.
"""
from __future__ import annotations

# Registry declaration — see scripts/detectors.py. `repo`: reads tracked files only.
DETECTOR = {"scope": "repo"}

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / "pixi.toml"
CATALOG = REPO_ROOT / "docs" / "reference" / "library-llms-full.md"

# A catalog entry is "- **name** (spec)" on a bullet line; "a / b" name lists
# share one spec. Prose bolds like "**pandera** (schemas)" are excluded by
# requiring the spec to start version-ish (digit, comparison op, or *).
ENTRY_RE = re.compile(r"\*\*([A-Za-z0-9_.@ /-]+?)\*\* \(([^)]*)\)")
SPEC_OK_RE = re.compile(r"^\s*[><=~^*\d]")
NAME_RE = re.compile(r"[a-z0-9][a-z0-9_.-]*$")
VERSION_RE = re.compile(r"\d+(?:\.\d+)*")


def manifest_deps(manifest: dict) -> dict[str, set[str]]:
    """name -> set of version-spec strings, from every *dependencies table
    ([dependencies], feature deps, pypi-dependencies, target tables)."""
    deps: dict[str, set[str]] = {}

    def walk(node: object) -> None:
        if not isinstance(node, dict):
            return
        for key, value in node.items():
            if key.endswith("dependencies") and isinstance(value, dict):
                for name, spec in value.items():
                    if isinstance(spec, dict):  # {version = "...", extras = [...]}
                        spec = str(spec.get("version", "*"))
                    deps.setdefault(name, set()).add(str(spec))
            elif isinstance(value, dict):
                walk(value)

    walk(manifest)
    return deps


def first_version(spec: str) -> str | None:
    m = VERSION_RE.search(spec or "")
    return m.group(0) if m else None


def versions_compatible(doc: str | None, live: str | None) -> bool:
    """Component-wise prefix match in either direction, so an abbreviated doc
    floor stays valid ('5.2' ~ '5.2.15', '21' ~ '21.0.0') but a real bump
    trips ('0.76.0' !~ '0.77.0')."""
    if doc is None or live is None:
        return True
    a, b = doc.split("."), live.split(".")
    n = min(len(a), len(b))
    return a[:n] == b[:n]


def catalog_entries(text: str) -> set[tuple[str, str]]:
    """(name, spec) for every well-formed versioned entry on bullet lines."""
    entries: set[tuple[str, str]] = set()
    for line in text.splitlines():
        if not line.lstrip().startswith("- "):
            continue
        for match in ENTRY_RE.finditer(line):
            spec = match.group(2)
            if not SPEC_OK_RE.match(spec):
                continue
            for name in match.group(1).split("/"):
                name = name.strip()
                if NAME_RE.match(name):
                    entries.add((name, spec))
    return entries


def mentioned(name: str, text: str) -> bool:
    return re.search(
        rf"(?<![A-Za-z0-9_-]){re.escape(name)}(?![A-Za-z0-9_-])", text, re.IGNORECASE
    ) is not None


def run() -> tuple[list[dict], dict]:
    deps = manifest_deps(tomllib.loads(MANIFEST.read_text()))
    text = CATALOG.read_text()

    findings: list[dict] = []
    for name in sorted(deps):
        if not mentioned(name, text):
            findings.append({
                "kind": "undocumented-dep", "name": name,
                "detail": f"active in pixi.toml ({', '.join(sorted(deps[name]))}) "
                          "but never mentioned in the catalog"})

    entries = sorted(catalog_entries(text))
    for name, spec in entries:
        if name not in deps:
            findings.append({
                "kind": "ghost-entry", "name": name,
                "detail": f"catalog documents it ({spec}) but it is not an "
                          "active pixi.toml dependency"})
            continue
        doc_v = first_version(spec)
        if doc_v is None:
            continue
        if not any(versions_compatible(doc_v, first_version(s)) for s in deps[name]):
            findings.append({
                "kind": "floor-drift", "name": name,
                "detail": f"catalog says ({spec}) but pixi.toml pins "
                          f"{', '.join(sorted(deps[name]))}"})

    return findings, {"manifest_deps": len(deps), "catalog_entries": len(entries)}


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="llms-full-check",
        description="Detect drift between pixi.toml and docs/reference/library-llms-full.md "
                    "(the library catalog). Exits 1 on drift.")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    for path in (MANIFEST, CATALOG):
        if not path.exists():
            print(f"missing {path}", file=sys.stderr)
            return 2

    findings, stats = run()
    if args.json:
        print(json.dumps({"stats": stats, "findings": findings}, indent=2))
        return 1 if findings else 0

    print(f"llms-full-check: {stats['manifest_deps']} active deps in pixi.toml | "
          f"{stats['catalog_entries']} versioned entries in {CATALOG.name}\n")
    if not findings:
        print("  clean — catalog covers every active dependency; no ghost entries "
              "or floor drift.")
        return 0
    by_kind: dict[str, list[dict]] = {}
    for f in findings:
        by_kind.setdefault(f["kind"], []).append(f)
    for kind, items in sorted(by_kind.items()):
        print(f"  {kind} ({len(items)}):")
        for f in items:
            print(f"    - {f['name']}: {f['detail']}")
    print(f"\nDRIFT: {len(findings)} finding(s). Reconcile by regenerating the "
          "catalog (prompt in its header), then re-run.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
