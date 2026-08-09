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
             by updating the spec (bmad-spec re-derive) then
             --write-baseline --spec <name>.

             A memlog reconciles the paths it NAMES (S-13.2). When the contract
             moved but never mentions a changed file, that file reports
             [drift-presumed] — informational, never gating: unproven rather
             than wrong. Before this, ANY memlog entry presumed every governed
             file in the surface reconciled, so unrelated activity silently
             laundered pending drift.

Exit non-zero on any finding (never false-green). Glob dialect: `**` spans
path separators, `*`/`?` do not; a pattern with no glob chars matches exactly.

Usage:  python scripts/spec_surface_check.py [--write-baseline [--spec NAME]] [--json]
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


def memlog_text(memlog: Path) -> str:
    """The memlog's raw text, for per-file reconciliation claims (S-13.2).

    A governed path counts as reconciled when the memlog NAMES it — a literal
    substring match on the repo-relative path, which is the form these entries
    already cite files in. Deliberately literal: inferring reconciliation intent
    from prose would rebuild the "presumed reconciled" blanket this replaces.
    """
    if not memlog.is_file():
        return ""
    return memlog.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write-baseline", action="store_true",
                    help="stamp the drift baseline after a spec reconciliation")
    ap.add_argument("--spec", action="append", metavar="NAME", default=None,
                    help=("limit --write-baseline to this spec (repeatable). "
                          "WITHOUT it the stamp covers EVERY spec, which accepts "
                          "every other spec's pending drift as correct."))
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
    # S-13.2: informational, NEVER gating — see the report block below.
    presumed: list[str] = []
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
        # S-13.1 — SCOPED stamping. Stamping every spec in one write made the
        # sanctioned fix for a single `[no-baseline]` unusable: it necessarily
        # accepted every OTHER spec's pending drift as correct, so the honest
        # move was to leave the finding standing. That is why this detector
        # carried a large red for weeks — a gate nobody can safely clear stops
        # being a gate. With --spec, one spec reconciles in isolation.
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
            scope = f"{len(specs)} spec(s) — ALL (accepts every spec's pending drift)"
        BASELINE.write_text(json.dumps(merged, indent=1, sort_keys=True) + "\n",
                            encoding="utf-8")
        print(f"baseline stamped: {BASELINE.relative_to(REPO_ROOT)} — {scope}")
    elif BASELINE.exists():
        base = json.loads(BASELINE.read_text(encoding="utf-8"))
        for name, cur in current.items():
            b = base.get(name)
            if b is None:
                findings.append(f"[no-baseline] {name}: run "
                                f"--write-baseline --spec {name}")
                continue
            # S-13.2 — the reconciliation claim is PER-FILE, not per-spec.
            # Short-circuiting the whole spec here meant appending ANY memlog
            # entry marked every governed file in that surface reconciled,
            # including files the author never touched: the drift half was
            # defeatable by unrelated activity, silently, and indistinguishably
            # from a real fix in the count the dashboard renders. Live: one
            # unrelated note took findings 63 -> 61, clearing two detectors
            # nobody had reconciled. A memlog reconciles the paths it NAMES.
            spec_moved = b["memlog"] != cur["memlog"]
            named = memlog_text(specs[name]["memlog"]) if spec_moved else ""
            for f in sorted(set(b["files"]) | set(cur["files"])):
                old, new = b["files"].get(f), cur["files"].get(f)
                if old == new:
                    continue
                what = "changed" if old and new else ("added" if new else "removed")
                if not spec_moved:
                    findings.append(f"[drift] {name}: {f} {what} but the spec's "
                                    f"memlog did not move — reconcile the spec, "
                                    f"then --write-baseline --spec {name}")
                elif f not in named:
                    # INFORMATIONAL, never gating (see `presumed` below): most
                    # existing memlog entries predate any naming convention, so a
                    # hard failure here would red the gate for every historical
                    # entry — the same unclearable red in a new shape.
                    presumed.append(f"[drift-presumed] {name}: {f} {what}; the "
                                    f"memlog moved but does not name this path — "
                                    f"confirm it was reconciled, then "
                                    f"--write-baseline --spec {name}")
    else:
        findings.append("[no-baseline] baseline missing: run --write-baseline")

    if args.json:
        print(json.dumps({
            "specs": {n: s["globs"] for n, s in specs.items()},
            "governed": {n: len(v) for n, v in governed.items()},
            "allowlisted": allow_hits, "findings": findings,
            "drift_presumed": presumed,
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
    if presumed:
        # Printed BEFORE findings and excluded from the exit code: this set is
        # "the memlog moved but never named this path", which is unproven rather
        # than wrong. Making it visible is the whole point — the alternative is
        # the silent per-spec clearing this replaces.
        #
        # SUMMARIZED per spec, not listed per file. The first run surfaced 995
        # entries (834 of them one station's whole surface), which would bury the
        # gating findings underneath them — a signal nobody reads is barely
        # better than the silence it replaced. `--json` carries the full set for
        # anything that wants to work through it.
        by_spec: dict[str, list[str]] = {}
        for line in presumed:
            spec_name, _, rest = line.partition(": ")
            by_spec.setdefault(spec_name.removeprefix("[drift-presumed] "),
                               []).append(rest.split(";")[0])
        print(f"\nDRIFT-PRESUMED ({len(presumed)} across {len(by_spec)} spec(s)) "
              f"— informational, not gating; full set in --json:")
        for spec_name, items in sorted(by_spec.items(),
                                       key=lambda kv: (-len(kv[1]), kv[0])):
            print(f"  ~ {spec_name}: {len(items)} governed file(s) changed while "
                  f"the memlog moved without naming them")
            for item in items[:2]:
                print(f"      e.g. {item}")
            if len(items) > 2:
                print(f"      … {len(items) - 2} more")
    if findings:
        print(f"\nFINDINGS ({len(findings)}):")
        for f in findings:
            print(f"  ✗ {f}")
        return 1
    print("\nOK: every tracked file governed or allowlisted; no drift.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
