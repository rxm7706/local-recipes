#!/usr/bin/env python3
"""Detector: every tracked file is governed by a spec surface or explicitly allowlisted.

The regenerable-factory contract (spec-regenerable-factory CAP-3): specs declare
the code they govern via `surface:` globs in SPEC.md frontmatter; this checker
enforces two properties over `git ls-files`:

  coverage — every tracked file matches >=1 spec surface OR an allowlist entry
             (scripts/spec_surface_allowlist.txt, every entry reason-tagged and
             printed — no silent exemptions).
  drift    — a governed file's content changed (vs the committed baseline
             scripts/.spec-surface-baseline.json) while its spec's .memlog.md
             did NOT move: code drifted out from under its contract. Reconcile
             by updating the spec (bmad-spec re-derive) then --write-baseline.

Exit non-zero on any finding (never false-green). Glob dialect: `**` spans
path separators, `*`/`?` do not; a pattern with no glob chars matches exactly.

Usage:  python scripts/spec_surface_check.py [--write-baseline] [--json]
Pixi:   pixi run -e local-recipes spec-surface-check
"""
from __future__ import annotations

# Registry declaration — see scripts/detectors.py. `repo`: reads tracked files only.
DETECTOR = {"scope": "repo"}

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_GLOB = "_bmad-output/projects/*/planning-artifacts/specs/spec-*/SPEC.md"
ALLOWLIST = REPO_ROOT / "scripts" / "spec_surface_allowlist.txt"
BASELINE = REPO_ROOT / "scripts" / ".spec-surface-baseline.json"


def glob_to_re(pattern: str) -> re.Pattern:
    out, i = [], 0
    while i < len(pattern):
        c = pattern[i]
        if pattern[i:i + 2] == "**":
            out.append(".*")
            i += 2
        elif c == "*":
            out.append("[^/]*")
            i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def parse_surface(spec_md: Path) -> tuple[list[str], str]:
    """(`surface:` globs, drift mode) from SPEC.md frontmatter.

    Drift modes (`surface-drift:`): "memlog" (default — governed change must
    move .memlog.md), "sentinel:<path>" (…or the named repo file, e.g. a
    CHANGELOG the surface's own process maintains), "exempt" (coverage-only;
    for product-churn surfaces — always printed, never silent).
    """
    globs, excludes, drift = [], [], "memlog"
    in_fm, section = False, None
    for line in spec_md.read_text(encoding="utf-8").splitlines():
        if line.strip() == "---":
            if in_fm:
                break
            in_fm = True
            continue
        if not in_fm:
            continue
        if section and line.startswith("  - "):
            (globs if section == "surface" else excludes).append(
                line[4:].split("#", 1)[0].strip())
            continue
        # A comment or blank line INSIDE a block sequence is valid YAML and must not
        # end the section. Before 2026-07-28 any such line reset `section`, silently
        # dropping every glob after it — so adding an explanatory comment under
        # `surface:` UN-GOVERNED the whole spec, and the checker reported the files as
        # "removed" rather than erroring. Silent governance loss, caught only because
        # the removal looked impossible (the file was plainly still there).
        if section and (not line.strip() or line.lstrip().startswith("#")):
            continue
        section = None
        if line.startswith("surface:"):
            section = "surface"
        elif line.startswith("surface-drift-exclude:"):
            # generated artifacts inside a governed surface: still covered,
            # but excluded from the drift hash (regenerate-at-will).
            section = "exclude"
        elif line.startswith("surface-drift:"):
            drift = line.split(":", 1)[1].split("#", 1)[0].strip()
    return globs, excludes, drift


def load_allowlist() -> list[tuple[str, str]]:
    entries = []
    for raw in ALLOWLIST.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        pattern, _, reason = line.partition("#")
        entries.append((pattern.strip(), reason.strip() or "(no reason given)"))
    return entries


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "-C", str(REPO_ROOT), "ls-files"],
                         capture_output=True, text=True, check=True).stdout
    return [l for l in out.splitlines() if l]


def sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write-baseline", action="store_true",
                    help="stamp the drift baseline after a spec reconciliation")
    ap.add_argument("--json", action="store_true", help="machine output")
    args = ap.parse_args()

    specs: dict[str, dict] = {}
    for spec_md in sorted(REPO_ROOT.glob(SPEC_GLOB)):
        # Key by <project>/<spec-dir>, never the bare dir name: the same slug can
        # legitimately exist in two projects (e.g. the marshal governance Spec in
        # local-recipes vs. the marshal CLI product Spec), and a bare-name key
        # silently DROPS one surface — a governance hole with no finding emitted.
        project = spec_md.relative_to(REPO_ROOT).parts[2]
        name = f"{project}/{spec_md.parent.name}"
        globs, excludes, drift = parse_surface(spec_md)
        specs[name] = {
            "spec": spec_md,
            "globs": globs,
            "drift": drift,
            "exclude": set(excludes),
            "res": [glob_to_re(g) for g in globs],
            "memlog": spec_md.parent / ".memlog.md",
        }

    allow = load_allowlist()
    allow_res = [(glob_to_re(p), p, r) for p, r, in allow]

    files = tracked_files()
    governed: dict[str, list[str]] = {}  # spec -> files
    ungoverned: list[str] = []
    allow_hits: dict[str, int] = {p: 0 for p, _ in allow}
    for f in files:
        owners = [n for n, s in specs.items() if any(r.match(f) for r in s["res"])]
        if owners:
            for n in owners:
                governed.setdefault(n, []).append(f)
            continue
        for rx, pat, _ in allow_res:
            if rx.match(f):
                allow_hits[pat] += 1
                break
        else:
            ungoverned.append(f)

    findings: list[str] = []
    for f in ungoverned:
        findings.append(f"[ungoverned] {f}: no spec surface and no allowlist entry")
    for pat, n in allow_hits.items():
        if n == 0:
            findings.append(f"[stale-allowlist] {pat!r} matches nothing — remove or fix")

    # drift: governed content moved while the spec's contract did not.
    # The contract hash is the memlog, plus any sentinel file (a repo file
    # whose movement counts as the contract moving — e.g. a CHANGELOG the
    # surface's own process maintains). Exempt specs record no file hashes.
    def contract_hash(s: dict) -> str:
        h = sha1(s["memlog"]) if s["memlog"].exists() else ""
        if s["drift"].startswith("sentinel:"):
            sentinel = REPO_ROOT / s["drift"].split(":", 1)[1].strip()
            h += "+" + (sha1(sentinel) if sentinel.is_file() else "missing")
        return h

    current = {
        name: {
            "memlog": contract_hash(s),
            "files": {} if s["drift"] == "exempt" else
                     {f: sha1(REPO_ROOT / f) for f in sorted(governed.get(name, []))
                      if f not in s["exclude"] and (REPO_ROOT / f).is_file()},
        }
        for name, s in specs.items()
    }
    if args.write_baseline:
        BASELINE.write_text(json.dumps(current, indent=1, sort_keys=True) + "\n",
                            encoding="utf-8")
        print(f"baseline stamped: {BASELINE.relative_to(REPO_ROOT)} "
              f"({len(specs)} specs)")
    elif BASELINE.exists():
        base = json.loads(BASELINE.read_text(encoding="utf-8"))
        for name, cur in current.items():
            b = base.get(name)
            if b is None:
                findings.append(f"[no-baseline] {name}: run --write-baseline")
                continue
            if b["memlog"] != cur["memlog"]:
                continue  # spec moved — code changes are presumed reconciled
            for f in sorted(set(b["files"]) | set(cur["files"])):
                old, new = b["files"].get(f), cur["files"].get(f)
                if old != new:
                    what = "changed" if old and new else ("added" if new else "removed")
                    findings.append(f"[drift] {name}: {f} {what} but the spec's "
                                    f"memlog did not move — reconcile the spec, "
                                    f"then --write-baseline")
    else:
        findings.append("[no-baseline] baseline missing: run --write-baseline")

    if args.json:
        print(json.dumps({
            "specs": {n: s["globs"] for n, s in specs.items()},
            "governed": {n: len(v) for n, v in governed.items()},
            "allowlisted": allow_hits, "findings": findings,
        }, indent=1))
        return 1 if findings else 0

    print(f"specs: {len(specs)}  ·  tracked files: {len(files)}  ·  "
          f"governed: {sum(len(v) for v in governed.values())}  ·  "
          f"allowlisted: {sum(allow_hits.values())}")
    for name, s in sorted(specs.items()):
        mode = "" if s["drift"] == "memlog" else f"  [drift: {s['drift']}]"
        print(f"  {name}: {len(governed.get(name, []))} file(s) "
              f"via {len(s['globs'])} surface glob(s){mode}")
    print("  allowlist (explicit, reason-tagged):")
    for pat, reason in allow:
        print(f"    {allow_hits[pat]:>5}  {pat}  # {reason}")
    if findings:
        print(f"\nFINDINGS ({len(findings)}):")
        for f in findings:
            print(f"  ✗ {f}")
        return 1
    print("\nOK: every tracked file governed or allowlisted; no drift.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
