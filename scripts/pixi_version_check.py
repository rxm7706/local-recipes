#!/usr/bin/env python3
"""pixi-version-check — every pixi-version pin site agrees with pixi.toml's
own `requires-pixi` floor, and no pixi dependency spec carries a ceiling.

`pixi.toml`'s `requires-pixi` comment enumerates every place a pixi version
is duplicated (CI workflows, both Containerfiles, environment.yaml) and
says, in its own words, "NOTHING ENFORCES ANY OF THIS." It has drifted three
times, most recently 2026-08-21 when a `pixi upgrade` raised the floor to
0.77.0 but 10 external sites stayed at 0.76.2 -- one of them
(`src/platform/compose/dbgpt/Containerfile`) was never even registered in
the comment, and broke `container-dbgpt` CI the very next push. This is the
detector that comment always said was the durable fix; the registry it
checks lives in `scripts/pixi_version_registry.py`, not here.

The second pass (mason Story 20.1, spec-pyforge-mason CAP-30; operator ruling
2026-09-28: "we should loosen pyforge-mason to be >=0.80.0 with no cap -- we
don't need to cap pixi in any station / environment") reads the root
`pixi.toml` and every `src/shared/packages/*/pixi.toml` and `pyproject.toml`
with `tomllib`, walks every dependency table (conda, PyPI, host, build, run;
every feature, target and package table) and every PEP 508 list, plus
`requires-pixi`, and fails on any pixi spec with a clause that is not a floor
(`>`, `>=`), an exclusion (`!=`) or `*`. Mason's `pixi >=0.80.0,<0.81` was the
one pixi ceiling in the repo: it held every environment carrying
pyforge-mason at pixi 0.80.0 while the workspace resolved 0.81.0.

Findings:
  version-mismatch     a site's pinned version differs from pixi.toml's floor
  hit-count-drift      a site's expected occurrence count no longer matches
                       (a pin was added, removed, or the registry itself is stale)
  missing-file         a registered site's file no longer exists
  pixi-upper-bound     a pixi dependency spec carries a ceiling (`<`, `<=`,
                       `==`, `~=`, a bare or wildcard pin, a pinned source)
  manifest-unreadable  a scanned manifest is not valid TOML

Reconciler: `pixi run -e local-recipes bump-pixi-version -- <version>` for
the first three; a `pixi-upper-bound` is fixed by hand (floor only).

Exit codes: 0 clean, 1 drift found, 2 pixi.toml itself unreadable.
"""
from __future__ import annotations

# Registry declaration — see scripts/detectors.py. `repo`: reads tracked files only.
DETECTOR = {"scope": "repo"}

import argparse
import json
import re
import sys
import tomllib
from collections.abc import Iterable, Iterator
from pathlib import Path

from pixi_version_registry import REPO_ROOT, SITES, master_version, read_versions

# The tree the upper-bound pass reads; tests point it at a planted tree.
CAP_SCAN_ROOT = REPO_ROOT

_PEP508_NAME = re.compile(r"^\s*([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)\s*(?:\[[^\]]*\])?\s*(.*)$")


def scanned_manifests(root: Path) -> list[Path]:
    """The manifests no pixi spec may cap: the workspace manifest and every
    station / portal package's own `pixi.toml` and `pyproject.toml`."""
    return [
        root / "pixi.toml",
        *sorted(root.glob("src/shared/packages/*/pixi.toml")),
        *sorted(root.glob("src/shared/packages/*/pyproject.toml")),
    ]


def _is_pixi(name: object) -> bool:
    return isinstance(name, str) and re.sub(r"[-_.]+", "-", name).strip().lower() == "pixi"


def _is_dependency_table(key: str) -> bool:
    # conda/PyPI/host/build/run `*dependencies`, [project.optional-dependencies],
    # [dependency-groups], [build-system] requires.
    return key.endswith("dependencies") or key in {"dependency-groups", "requires"}


def _pep508_pixi_spec(requirement: str) -> str | None:
    """The version part of a PEP 508 requirement naming pixi, else None."""
    m = _PEP508_NAME.match(requirement)
    if not m or not _is_pixi(m.group(1)):
        return None
    spec = m.group(2).split(";", 1)[0].strip()
    if spec.startswith("(") and spec.endswith(")"):
        spec = spec[1:-1].strip()
    return spec


def _pixi_specs_in_deps(value: object, where: tuple[str, ...]) -> Iterator[tuple[tuple[str, ...], object]]:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                spec = _pep508_pixi_spec(item)
                if spec is not None:
                    yield where, spec
    elif isinstance(value, dict):
        for name, spec in value.items():
            if isinstance(spec, list):  # a named group of PEP 508 strings
                yield from _pixi_specs_in_deps(spec, (*where, str(name)))
            elif _is_pixi(name):
                yield (*where, str(name)), spec


def pixi_specs(document: object, where: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], object]]:
    """Every (table path, spec) naming pixi in a parsed manifest, at any depth."""
    if not isinstance(document, dict):
        return
    for key, value in document.items():
        here = (*where, str(key))
        if key == "requires-pixi":
            yield here, value
        elif _is_dependency_table(str(key)):
            yield from _pixi_specs_in_deps(value, here)
        else:
            yield from pixi_specs(value, here)


def capping_clauses(spec: object) -> list[str]:
    """The clauses of a pixi spec that put an upper bound on it (empty = uncapped).

    Allowed: a floor (`>`, `>=`), an exclusion (`!=`, which never caps), `*` or
    nothing. Everything else caps: `<`, `<=`, `==`, `===`, `~=`, conda's `=`,
    a bare or wildcard version (`0.80.0`, `0.80.*`), a PEP 508 direct reference,
    and anything unrecognized (fail closed)."""
    if isinstance(spec, dict):
        if "version" in spec:
            return capping_clauses(spec["version"])
        pinned = [k for k in ("path", "git", "url") if k in spec]
        return [f"{pinned[0]} source"] if pinned else []
    if not isinstance(spec, str):
        return []
    caps = []
    for clause in re.split(r"[,|]", spec):
        compact = re.sub(r"\s+", "", clause)
        if not compact or compact == "*" or compact.startswith((">", "!=")):
            continue
        caps.append(clause.strip())
    return caps


def upper_bound_findings(manifests: Iterable[Path], root: Path) -> list[dict]:
    findings: list[dict] = []
    for path in manifests:
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
        try:
            document = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            findings.append({"kind": "manifest-unreadable", "site": rel, "detail": f"{rel}: {exc}"})
            continue
        for where, spec in pixi_specs(document):
            caps = capping_clauses(spec)
            if caps:
                findings.append({
                    "kind": "pixi-upper-bound", "site": f"{rel} [{'.'.join(where)}]",
                    "detail": f"pixi spec {spec!r} is capped by {', '.join(repr(c) for c in caps)} -- no station "
                              f"or environment caps pixi (spec-pyforge-mason CAP-30); pin a floor only",
                })
    return findings


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

    manifests = scanned_manifests(CAP_SCAN_ROOT)
    findings.extend(upper_bound_findings(manifests, CAP_SCAN_ROOT))

    return findings, {"master_version": master, "sites_checked": len(SITES),
                      "manifests_scanned": sum(1 for m in manifests if m.is_file())}


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pixi-version-check",
        description="Detect drift between pixi.toml's requires-pixi floor and every "
                    "other pixi-version pin site in the repo, and any pixi dependency "
                    "spec with an upper bound. Exits 1 on drift.")
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
          f"(pixi.toml requires-pixi) | {stats['sites_checked']} site(s) checked | "
          f"{stats['manifests_scanned']} manifest(s) scanned for pixi ceilings\n")
    if not findings:
        print("  clean — every pin site matches the floor, and no pixi spec is capped.")
        return 0
    for f in findings:
        print(f"  {f['kind']}: {f['site']} — {f['detail']}")
    print(f"\nDRIFT: {len(findings)} finding(s).")
    if any(f["kind"] in {"version-mismatch", "hit-count-drift", "missing-file"} for f in findings):
        print(f"Reconcile pin sites with `pixi run -e local-recipes bump-pixi-version -- "
              f"{stats['master_version']}`.")
    if any(f["kind"] in {"pixi-upper-bound", "manifest-unreadable"} for f in findings):
        print("Remove each pixi ceiling by hand: a floor (>=X.Y.Z) only.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
