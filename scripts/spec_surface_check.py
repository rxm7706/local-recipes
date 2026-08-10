#!/usr/bin/env python3
"""Mutation-only residual: stamp the spec-surface drift baseline.

Story 6.9 ("the `scripts/` shims retire") ported this script's own
read-only VERDICT — coverage (every tracked file governed by a spec
surface or explicitly allowlisted) and drift (a governed file changed
without its spec's `.memlog.md` moving) — into
`pyforge.doctor.sources.chain::gather_spec_surface`
(`python -m pyforge.doctor.sources spec-surface`). That port is the one
place the verdict lives now; this file is NOT a detector any more (no
`DETECTOR = {...}` marker, and `scripts/detectors.py`'s AST scan correctly
no longer discovers it).

What survives here, and why it could not simply move with the rest: Doctor
sources are deliberately READ-ONLY gathers (Charter §6 — the producing
station keeps the operational guard; only Doctor holds the verdict), so
`gather_spec_surface` never got a `--write-baseline`/`--spec NAME`
mutation path, and nothing else in the repo has one either. That capability
is live and depended on today — `_bmad-output/projects/pyforge-marshal/
SYNC-RUNBOOK.md` Step 3, `CLAUDE.md`'s own Sync-loop section, and
`spec-surface-drift-reconciliation` (an ACTIVE, `in-progress` Marshal
spec) all instruct or require `--write-baseline --spec NAME` as a real,
working command. So it stays here, reduced to exactly that: compute the
same live "what does every governed spec's contract + file set look like
right now" state the read-only port also computes internally, and (only
when asked) merge it into the committed `scripts/.spec-surface-baseline.json`.

Usage (plain `python`, no pixi task -- the `spec-surface-check` pixi task
invokes the dispatcher below instead, which does not understand this flag):
        python scripts/spec_surface_check.py --write-baseline [--spec NAME ...]
Verdict (coverage/drift/blindness, unchanged behavior):
        pixi run -e local-recipes spec-surface-check
        python -m pyforge.doctor.sources spec-surface
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

# Explicit opt-out: this file still matches detectors.py's `*_check.py` glob
# by name (kept for doc/CLI continuity), but Story 6.9 reduced it to a
# mutation-only residual -- it is not a detector and must not trip the
# registry's "looks like one but declares nothing" gap.
DETECTOR = None

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_GLOB = "_bmad-output/projects/*/planning-artifacts/specs/spec-*/SPEC.md"
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


def parse_surface(spec_md: Path) -> tuple[list[str], list[str], str]:
    """(`surface:` globs, `surface-drift-exclude:` globs, drift mode) from
    SPEC.md frontmatter -- verbatim from the pre-reduction script (still the
    ground truth `--write-baseline` stamps against, so it must read the
    contract identically to the read-only port)."""
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
        if section and (not line.strip() or line.lstrip().startswith("#")):
            continue
        section = None
        if line.startswith("surface:"):
            section = "surface"
        elif line.startswith("surface-drift-exclude:"):
            section = "exclude"
        elif line.startswith("surface-drift:"):
            drift = line.split(":", 1)[1].split("#", 1)[0].strip()
    return globs, excludes, drift


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "-C", str(REPO_ROOT), "ls-files"],
                         capture_output=True, text=True, check=True).stdout
    return [l for l in out.splitlines() if l]


def sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def contract_hash(s: dict) -> str:
    h = sha1(s["memlog"]) if s["memlog"].exists() else ""
    if s["drift"].startswith("sentinel:"):
        sentinel = REPO_ROOT / s["drift"].split(":", 1)[1].strip()
        h += "+" + (sha1(sentinel) if sentinel.is_file() else "missing")
    return h


def _live_state() -> dict[str, dict]:
    """Every spec's CURRENT `{memlog, files}` baseline entry -- the ground
    truth `--write-baseline` merges into the committed file. Mirrors
    `gather_spec_surface`'s own internal computation (Doctor's read-only
    port), which is a deliberate, unavoidable duplication: the verdict and
    the stamp must agree on what "current" means, and Doctor's own gather
    cannot write, so this is not one function two ways -- it is the one
    remaining mutation caller of the same read."""
    specs: dict[str, dict] = {}
    for spec_md in sorted(REPO_ROOT.glob(SPEC_GLOB)):
        # Key by <project>/<spec-dir>, never the bare dir name -- the same
        # slug can legitimately exist in two projects, and a bare-name key
        # would silently drop one surface.
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

    files = tracked_files()
    governed: dict[str, list[str]] = {}
    for f in files:
        for n, s in specs.items():
            if any(r.match(f) for r in s["res"]):
                governed.setdefault(n, []).append(f)

    return {
        name: {
            "memlog": contract_hash(s),
            "files": {} if s["drift"] == "exempt" else
                     {f: sha1(REPO_ROOT / f) for f in sorted(governed.get(name, []))
                      if f not in s["exclude"] and (REPO_ROOT / f).is_file()},
        }
        for name, s in specs.items()
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write-baseline", action="store_true",
                    help="stamp the drift baseline after a spec reconciliation")
    ap.add_argument("--spec", action="append", metavar="NAME", default=None,
                    help=("limit --write-baseline to this spec (repeatable). "
                          "WITHOUT it the stamp covers EVERY spec, which accepts "
                          "every other spec's pending drift as correct."))
    args = ap.parse_args()

    if args.spec and not args.write_baseline:
        ap.error("--spec only makes sense with --write-baseline")

    if not args.write_baseline:
        print(
            "this script no longer computes the coverage/drift verdict -- run "
            "`python -m pyforge.doctor.sources spec-surface` for that. Pass "
            "--write-baseline [--spec NAME ...] to stamp the baseline after a "
            "spec reconciliation.",
            file=sys.stderr,
        )
        return 2

    current = _live_state()

    # S-13.1 -- SCOPED stamping. Stamping every spec in one write made the
    # sanctioned fix for a single `[no-baseline]` unusable: it necessarily
    # accepted every OTHER spec's pending drift as correct, so the honest
    # move was to leave the finding standing. With --spec, one spec
    # reconciles in isolation.
    if args.spec:
        unknown = sorted(set(args.spec) - set(current))
        if unknown:
            print(f"unknown spec(s): {', '.join(unknown)}\n"
                  f"known: {', '.join(sorted(current))}", file=sys.stderr)
            return 2
        # MERGE, never rewrite: building from `current` alone would silently
        # drop every spec this invocation did not name.
        merged = (json.loads(BASELINE.read_text(encoding="utf-8"))
                  if BASELINE.exists() else {})
        for name in args.spec:
            merged[name] = current[name]
        scope = f"{len(set(args.spec))} spec(s): {', '.join(sorted(set(args.spec)))}"
    else:
        merged = current
        scope = f"{len(current)} spec(s) — ALL (accepts every spec's pending drift)"
    BASELINE.write_text(json.dumps(merged, indent=1, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(f"baseline stamped: {BASELINE.relative_to(REPO_ROOT)} — {scope}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
