#!/usr/bin/env python3
"""
Check the dossier's numeric claims against the source tree.

The dossier states concrete figures — lines of source, file counts, Python
floors, test ratios. Those are exactly the claims that rot silently as the code
grows, which is the failure mode the dossier itself names as a fleet-wide
pattern ("every station's own docs undercount its own surface"). This script
makes the dossier subject to its own finding.

It is advisory by design: it reports drift and never rewrites content. Deciding
what a number should say is an editorial act, not a mechanical one.

    python docsite/tools/verify_claims.py               # human-readable
    python docsite/tools/verify_claims.py --format github   # CI annotations
    python docsite/tools/verify_claims.py --json        # machine-readable

Exit status is 1 when any claim has drifted, 0 when all are current.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
PACKAGES = ROOT / "src" / "shared" / "packages"

#: dossier section id -> package directory name
STATION_PACKAGE = {
    "atlas": "pyforge-atlas",
    "doctor": "pyforge-doctor",
    "herald": "pyforge-herald",
    "marshal": "pyforge-marshal",
    "mason": "pyforge-mason",
    "scribe": "pyforge-scribe",
    "steward": "pyforge-steward",
    "warden": "pyforge-warden",
}

#: how much a figure may drift before it is worth reporting
TOLERANCE = 0.05

_NUM = re.compile(r"(\d[\d,]*)")


def measure(pkg_dir: Path) -> dict:
    """Count what the dossier claims to count, the way it counts it."""
    src = pkg_dir / "src"
    tests = pkg_dir / "tests"

    def lines(root: Path) -> int:
        if not root.exists():
            return 0
        total = 0
        for p in root.rglob("*.py"):
            try:
                total += len(p.read_bytes().splitlines())
            except OSError:
                pass
        return total

    src_files = len(list(src.rglob("*.py"))) if src.exists() else 0
    requires = ""
    pyproject = pkg_dir / "pyproject.toml"
    if pyproject.exists():
        m = re.search(r'requires-python\s*=\s*"([^"]+)"', pyproject.read_text(encoding="utf-8"))
        requires = m.group(1) if m else ""

    src_lines = lines(src)
    test_lines = lines(tests)
    return {
        "src_lines": src_lines,
        "src_files": src_files,
        "test_lines": test_lines,
        "test_ratio": round(test_lines / src_lines, 2) if src_lines else 0.0,
        "requires_python": requires,
    }


def claimed_number(text: str) -> int | None:
    m = _NUM.search(str(text))
    return int(m.group(1).replace(",", "")) if m else None


def drifted(claim: int, actual: int) -> bool:
    if claim == actual:
        return False
    if actual == 0:
        return True
    return abs(claim - actual) / actual > TOLERANCE


def check(doc: dict) -> list[dict]:
    findings: list[dict] = []
    measured: dict[str, dict] = {}

    for section in doc["sections"]:
        pkg_name = STATION_PACKAGE.get(section["id"])
        if not pkg_name:
            continue
        pkg_dir = PACKAGES / pkg_name
        if not pkg_dir.exists():
            findings.append(
                {"station": section["id"], "claim": "package exists", "stated": pkg_name,
                 "actual": "not found", "kind": "missing"}
            )
            continue
        facts = measure(pkg_dir)
        measured[section["id"]] = facts

        for block in section["blocks"]:
            if block.get("type") != "stats":
                continue
            for stat in block["stats"]:
                # A stat is checked only when it says so. Guessing from the
                # label was tried and got it wrong in both directions:
                # "Pipelines wired to MCP" contains "line", and
                # "Lines added since last pass" is a delta, not a total.
                kind = stat.get("check")
                if not kind:
                    continue

                value = str(stat["value"])
                num = claimed_number(value)

                if kind == "src_lines" and num is not None:
                    if drifted(num, facts["src_lines"]):
                        findings.append(
                            {"station": section["id"], "claim": stat["label"], "stated": value,
                             "actual": f"{facts['src_lines']:,}", "kind": "stale-number"}
                        )
                    file_claim = re.search(r"(\d+)\s*files", str(stat["label"]))
                    if file_claim and drifted(int(file_claim.group(1)), facts["src_files"]):
                        findings.append(
                            {"station": section["id"], "claim": "file count", "stated": file_claim.group(1),
                             "actual": str(facts["src_files"]), "kind": "stale-number"}
                        )
                elif kind == "test_lines" and num is not None:
                    if drifted(num, facts["test_lines"]):
                        findings.append(
                            {"station": section["id"], "claim": stat["label"], "stated": value,
                             "actual": f"{facts['test_lines']:,}", "kind": "stale-number"}
                        )
                elif kind == "python_floor":
                    want = value.replace("py", "")
                    if want not in facts["requires_python"]:
                        findings.append(
                            {"station": section["id"], "claim": "Python floor", "stated": value,
                             "actual": facts["requires_python"], "kind": "stale-fact"}
                        )
                elif kind not in ("src_lines", "test_lines", "python_floor"):
                    findings.append(
                        {"station": section["id"], "claim": f"unknown check {kind!r}",
                         "stated": value, "actual": "—", "kind": "bad-config"}
                    )

    # fleet-wide: the hero's total-source figure
    total = sum(f["src_lines"] for f in measured.values())
    for stat in doc.get("stats", []):
        if "lines of source" in str(stat["label"]).lower():
            claim = claimed_number(stat["value"])
            scale = 1000 if "k" in str(stat["value"]).lower() else 1
            if claim is not None and drifted(claim * scale, total):
                findings.append(
                    {"station": "(fleet)", "claim": "total lines of source", "stated": stat["value"],
                     "actual": f"~{round(total / 1000)}K", "kind": "stale-number"}
                )

    # fleet-wide: do the stations still disagree on their Python floor, and
    # does the convention-gap table still describe them as disagreeing?
    floors = {s: m["requires_python"] for s, m in measured.items() if m["requires_python"]}
    if floors and len(set(floors.values())) == 1 and not _floor_gap_marked_closed(doc):
        findings.append(
            {"station": "(fleet)", "claim": "Python-floor convention gap",
             "stated": "the gap table still lists stations as disagreeing",
             "actual": f"all stations now agree on {next(iter(set(floors.values())))}",
             "kind": "gap-closed"}
        )

    return findings


def _floor_gap_marked_closed(doc: dict) -> bool:
    """True once the convention-gap table records the floor gap as resolved."""
    for section in doc["sections"]:
        for block in section["blocks"]:
            if block.get("type") != "table":
                continue
            for row in block.get("rows", []):
                cells = row.get("cells", [])
                if cells and "Python floor" in cells[0]:
                    return any("closed" in c.lower() for c in cells[1:])
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--format", choices=["text", "github"], default="text")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--content", default=str(ROOT / "docsite" / "content" / "dossier.yml"))
    args = ap.parse_args()

    doc = yaml.safe_load(Path(args.content).read_text(encoding="utf-8"))
    findings = check(doc)

    if args.json:
        print(json.dumps(findings, indent=2))
    elif args.format == "github":
        for f in findings:
            level = "notice" if f["kind"] == "gap-closed" else "warning"
            print(
                f"::{level} file=docdocsite/content/dossier.yml::"
                f"{f['station']}: {f['claim']} — dossier says {f['stated']}, source says {f['actual']}"
            )
        print(f"\n{len(findings)} claim(s) drifted from the source tree.")
    else:
        if not findings:
            print("All checked claims match the source tree.")
        else:
            width = max(len(f["station"]) for f in findings)
            print(f"{len(findings)} claim(s) drifted:\n")
            for f in findings:
                print(f"  {f['station']:<{width}}  {f['claim']}")
                print(f"  {'':<{width}}    dossier: {f['stated']}")
                print(f"  {'':<{width}}    source : {f['actual']}\n")

    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
