#!/usr/bin/env python3
"""Regenerate a presentation deck's derived export artifacts from its Marp sources.

The Marp ``.md`` files under ``presentations/<slug>/src/marp/`` are the source of
truth for the non-React exports (see ``docs/specs/presentation-deck.md`` §
*Standard export set*). This tool re-derives the companions with ``marp`` so they
never drift from their source and stay reproducible:

    html              src/marp/<slug>-infographic-standalone-<date>.html   (marp --html)
    infographic-pptx  src/pptx/<slug>_infographic_deck-<date>.pptx         (marp --pptx)
    deck-pptx         src/pptx/<slug>-deck-<date>.pptx                     (marp --pptx)

Each output's date is taken from its own source ``.md`` filename, so a deck whose
sources carry different dates stays internally consistent.

Usage (run inside the local-recipes pixi env, which carries marp + Chrome)::

    pixi run -e local-recipes deck-export <slug> [html|deck-pptx|infographic-pptx ...]

With no targets it regenerates all three. ``--pptx`` needs Chrome at
``/usr/bin/google-chrome`` (auto-wired here); ``html`` is pure Node.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATE_RE = re.compile(r"-(\d{4}-\d{2}-\d{2})\.md$")
VALID_TARGETS = {"html", "deck-pptx", "infographic-pptx"}
CHROME = "/usr/bin/google-chrome"


def find_source(marp_dir: str, slug: str, kind: str):
    """Return (path, date) for the newest ``<slug>-<kind>-<date>.md`` source."""
    cands = [
        p
        for p in glob.glob(os.path.join(marp_dir, f"{slug}-{kind}-*.md"))
        if "-standalone-" not in os.path.basename(p)
    ]
    if not cands:
        return None, None
    src = sorted(cands)[-1]  # newest by name == latest date
    m = DATE_RE.search(os.path.basename(src))
    return src, (m.group(1) if m else None)


def run_marp(extra: list[str]) -> None:
    marp_bin = shutil.which("marp")
    if not marp_bin:
        sys.exit(
            "error: 'marp' not on PATH — run via: "
            "pixi run -e local-recipes deck-export ..."
        )
    cmd = [marp_bin, "--allow-local-files", *extra]
    print("  $", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("slug", help="deck directory under presentations/")
    ap.add_argument(
        "targets",
        nargs="*",
        help="any of: html deck-pptx infographic-pptx (default: all)",
    )
    args = ap.parse_args()

    targets = set(args.targets) or set(VALID_TARGETS)
    bad = targets - VALID_TARGETS
    if bad:
        sys.exit(
            f"error: unknown target(s): {', '.join(sorted(bad))}; "
            f"valid: {', '.join(sorted(VALID_TARGETS))}"
        )

    deck_dir = os.path.join(ROOT, "presentations", args.slug)
    marp_dir = os.path.join(deck_dir, "src", "marp")
    pptx_dir = os.path.join(deck_dir, "src", "pptx")
    if not os.path.isdir(marp_dir):
        sys.exit(f"error: {os.path.relpath(marp_dir, ROOT)} not found")
    os.makedirs(pptx_dir, exist_ok=True)

    deck_md, deck_date = find_source(marp_dir, args.slug, "deck")
    info_md, info_date = find_source(marp_dir, args.slug, "infographic")

    if os.path.exists(CHROME):
        os.environ.setdefault("CHROME_PATH", CHROME)

    produced: list[str] = []
    if "html" in targets:
        if not info_md:
            sys.exit("error: no infographic .md source for the 'html' target")
        out = os.path.join(
            marp_dir, f"{args.slug}-infographic-standalone-{info_date}.html"
        )
        run_marp([info_md, "-o", out])
        produced.append(out)
    if "infographic-pptx" in targets:
        if not info_md:
            sys.exit("error: no infographic .md source for 'infographic-pptx'")
        out = os.path.join(pptx_dir, f"{args.slug}_infographic_deck-{info_date}.pptx")
        run_marp(["--pptx", info_md, "-o", out])
        produced.append(out)
    if "deck-pptx" in targets:
        if not deck_md:
            sys.exit("error: no deck .md source for the 'deck-pptx' target")
        out = os.path.join(pptx_dir, f"{args.slug}-deck-{deck_date}.pptx")
        run_marp(["--pptx", deck_md, "-o", out])
        produced.append(out)

    print(f"\n{args.slug}: regenerated {len(produced)} artifact(s):")
    for p in produced:
        print("  ", os.path.relpath(p, ROOT))


if __name__ == "__main__":
    main()
