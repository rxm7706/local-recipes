#!/usr/bin/env python3
"""Detector: enforce the Dream-to-Code operating model (_bmad-output/EXEMPLAR-STANDARD.md).

Four invariants. INV-1..3 decided 2026-07-28 by the operator; INV-0 was discovered
while validating this detector against pyforge-atlas — see its comment in check().

  INV-0  every Spec declares `owner-dream:` (without it the chain is untraversable
         and INV-1/INV-2 silently mis-measure)
  INV-1  every Dream in docs/dreams/*.md has a Spec (no status exempt)
  INV-2  the CHAIN follows the owner — a Dream's planning artifacts live in the owning
         Smith's project (Charter §5 as amended 2026-07-28, "owning is becoming — at the
         planning tier"). It does NOT rename the package: `surface:` is independent.
         owner: <station> -> pyforge-<station>;  owner: guild -> pyforge-genesis
  INV-3  every project's planning-artifacts uses the 6.10 sharded build tree
         (prds/<run>/, architecture/<run>/, epics.md) — flat prd.md/architecture.md
         is the deprecated bmad-create-* shape and is non-conformant

Exits non-zero on findings. `--json` for machine output; the findings ARE the migration
backlog, which is why they are derived here rather than hand-listed in a doc.

Deliberately stdlib + PyYAML only, so it runs in bare CI like the other detectors.
"""
from __future__ import annotations

# Registry declaration — see scripts/detectors.py. `repo`: reads tracked files only.
DETECTOR = {"scope": "repo"}

import argparse
import json
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
DREAMS = ROOT / "docs" / "dreams"
PROJECTS = ROOT / "_bmad-output" / "projects"


def frontmatter(path: pathlib.Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            return {}
        return yaml.safe_load(text.split("---")[1]) or {}
    except Exception:
        return {}


# The placeholder: where a Dream lands before it has a station. INTAKE ONLY — in the target
# state it holds nothing and is RETIRED. Applying INV-2 today moves all 8 of its Specs out.
PLACEHOLDER = "local-recipes"

# The two constitutive Dreams (Charter §5): they PRECEDE the stations, so they are owned by
# `guild` rather than a Smith, and their chains live in `pyforge-genesis` — the one project
# not named for a Smith. `guild` IS terminal for these two and only these two; a third is an
# unassigned Dream hiding behind a collective noun.
# Genesis's *installer* (`genesis init`/`adopt`) is NOT constitutive — it is buildable work
# owned by the Marshal, and its Spec belongs under pyforge-marshal.
CONSTITUTIVE = {"pyforge-charter", "pyforge-genesis"}


def expected_project(owner: str) -> str:
    """Project for an owner. `guild` -> pyforge-genesis, the constitutive project
    (origin Dream + Charter/Lexicon/membership records) — never the placeholder.
    A *buildable* Dream owned by `guild` still means "station not yet chosen" (INV-2a)."""
    return "pyforge-genesis" if owner == "guild" else f"pyforge-{owner}"


def collect() -> tuple[dict, list]:
    dreams = {}
    for p in sorted(DREAMS.glob("*.md")):
        if p.name == "README.md":
            continue
        fm = frontmatter(p)
        dreams[p.stem] = {"owner": fm.get("owner", ""), "status": fm.get("status", "")}

    specs = []
    for sp in sorted(PROJECTS.glob("*/planning-artifacts/specs/*/SPEC.md")):
        fm = frontmatter(sp)
        specs.append({
            "project": sp.parts[len(PROJECTS.parts)],
            "spec": sp.parent.name,
            "dream": (fm.get("owner-dream") or "").split("/")[-1].removesuffix(".md"),
            "path": str(sp.relative_to(ROOT)),
        })
    return dreams, specs


def check() -> list[dict]:
    dreams, specs = collect()
    findings: list[dict] = []

    # INV-0 — every Spec declares owner-dream. Without it the chain is not
    # traversable and INV-1/INV-2 cannot be measured. Found the hard way: the
    # first cut of this detector reported 21 dreams-without-specs, but 10 of
    # those Specs existed and simply did not declare the link, and 1 more
    # (spec-upstream-discovery) had frontmatter that would not parse at all —
    # so `except: return {}` silently turned a real Spec into a missing one.
    for s in specs:
        if not s["dream"]:
            slug = s["spec"].removeprefix("spec-")
            implied = slug if slug in dreams else ""
            findings.append({
                "inv": "INV-0", "kind": "spec-without-dream-link", "subject": s["spec"],
                "owner": dreams.get(implied, {}).get("owner", "") if implied else "",
                "status": f"in {s['project']}",
                "remedy": (f"add `owner-dream: docs/dreams/{implied}.md`"
                           if implied else "add an owner-dream: key"),
            })

    # A Spec covers a Dream if it DECLARES the link, or (fallback) its slug matches.
    # The fallback keeps INV-1 honest while INV-0 is being closed — otherwise every
    # unlinked Spec would be double-counted as a missing one.
    covered = {s["dream"] for s in specs if s["dream"]}
    covered |= {s["spec"].removeprefix("spec-") for s in specs
                if not s["dream"] and s["spec"].removeprefix("spec-") in dreams}

    # INV-1 — every Dream has a Spec
    for slug, d in sorted(dreams.items()):
        if slug not in covered:
            findings.append({
                "inv": "INV-1", "kind": "dream-without-spec", "subject": slug,
                "owner": d["owner"] or "(none)", "status": d["status"] or "(none)",
                "remedy": f"author a Spec under {expected_project(d['owner'] or 'guild')}"
                          f"/planning-artifacts/specs/spec-{slug}/",
            })

    # INV-2a — a buildable Dream owned by `guild` has no station yet. Resolving it to the
    # placeholder would make an unassigned chain look settled, so it is flagged instead.
    for slug, d in sorted(dreams.items()):
        if d.get("owner") == "guild" and slug not in CONSTITUTIVE:  # a third `guild`
            findings.append({
                "inv": "INV-2", "kind": "owner-unassigned", "subject": slug,
                "owner": "guild", "status": d.get("status", ""),
                "remedy": "assign a station (guild is intake, not a terminal owner)",
            })

    # INV-2 — the chain lives where its owner lives
    for s in specs:
        owner = dreams.get(s["dream"], {}).get("owner", "")
        if not owner:
            continue
        want = expected_project(owner)
        if s["project"] != want:
            findings.append({
                "inv": "INV-2", "kind": "spec-location-mismatch", "subject": s["spec"],
                "owner": owner, "status": f"in {s['project']}",
                "remedy": f"move to {want}/planning-artifacts/specs/{s['spec']}/",
            })

    # INV-3 — sharded build tree
    for pdir in sorted(PROJECTS.glob("*/planning-artifacts")):
        project = pdir.parts[len(PROJECTS.parts)]
        names = {p.name for p in pdir.iterdir()}
        if not (pdir / "prds").is_dir():
            flat = "prd.md" in {n.lower() for n in names}
            findings.append({
                "inv": "INV-3", "kind": "prd-not-sharded", "subject": project,
                "owner": "", "status": "flat prd.md" if flat else "absent",
                "remedy": "regenerate via bmad-prd into prds/prd-<slug>-<date>/",
            })
        if not (pdir / "architecture").is_dir():
            flat = any(n.startswith("architecture") for n in names)
            findings.append({
                "inv": "INV-3", "kind": "architecture-not-sharded", "subject": project,
                "owner": "", "status": "flat architecture.md" if flat else "absent",
                "remedy": "regenerate via bmad-architecture into "
                          "architecture/architecture-<slug>-<date>/",
            })
        if "epics.md" not in names:
            findings.append({
                "inv": "INV-3", "kind": "epics-missing", "subject": project,
                "owner": "", "status": "absent",
                "remedy": "run bmad-create-epics-and-stories",
            })
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--inv", help="filter to one invariant (INV-1|INV-2|INV-3)")
    args = ap.parse_args()

    findings = check()
    if args.inv:
        findings = [f for f in findings if f["inv"] == args.inv]

    if args.json:
        print(json.dumps({"findings": findings, "count": len(findings)}, indent=2))
        return 1 if findings else 0

    dreams, specs = collect()
    print(f"Dream-to-Code chain — {len(dreams)} dreams, {len(specs)} specs, "
          f"{len(list(PROJECTS.glob('*/planning-artifacts')))} projects\n")
    if not findings:
        print("OK: all three invariants hold.")
        return 0

    for inv in ("INV-0", "INV-1", "INV-2", "INV-3"):
        group = [f for f in findings if f["inv"] == inv]
        if not group:
            continue
        print(f"  {inv} — {len(group)} finding(s)")
        for f in group:
            extra = f" owner={f['owner']}" if f["owner"] else ""
            print(f"     {f['subject']:<38} {f['status']:<22}{extra}")
        print()
    # Scoreboard by OWNER — the only conformance scope (EXEMPLAR-STANDARD.md).
    # A station is answerable for every Dream carrying its `owner:`, wherever the
    # artifacts sit. Rolling up by project instead would let a station park debt in
    # satellite projects and still show clean.
    dream_owner = {k: v["owner"] for k, v in dreams.items()}
    spec_owner = {s["spec"]: dream_owner.get(s["dream"], "") for s in specs}
    proj_owner: dict[str, str] = {}
    for s in specs:
        o = spec_owner.get(s["spec"], "")
        if o and s["project"] not in proj_owner:
            proj_owner[s["project"]] = o

    tally: dict[str, int] = {}
    for f in findings:
        subj = f["subject"]
        owner = (dream_owner.get(subj)
                 or spec_owner.get(subj)
                 or proj_owner.get(subj)
                 or f.get("owner") or "(unattributed)")
        tally[owner] = tally.get(owner, 0) + 1

    print("  by owner (the accountability unit):")
    for owner, n in sorted(tally.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"     {owner:<18} {n}")
    print()
    print(f"FINDINGS: {len(findings)}. These are the migration backlog "
          f"(see _bmad-output/EXEMPLAR-STANDARD.md).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
