#!/usr/bin/env python3
"""Regenerate a presentation deck's derived export artifacts from its Marp sources.

The Marp ``.md`` files under ``presentations/<slug>/src/marp/`` are the source of
truth for the non-React exports (see ``docs/specs/presentation-deck.md`` §
*Standard export set*). This tool re-derives the companions with ``marp`` so they
never drift from their source and stay reproducible:

    html              src/marp/<slug>-infographic-standalone-<date>.html   (marp --html)
    infographic-pptx  src/pptx/<slug>_infographic_deck-<date>.pptx         (marp --pptx)
    deck-pptx         src/pptx/<slug>-deck-<date>.pptx                     (marp --pptx)

Story 21.5 (spec-deck-family-lockstep CAP-3) also stamps the exec summary and
the three marp sources with a small marked-fact band from ``facts.yaml``, then
dates the marp sources to the rebuild day so the Standard export set is current.

Usage (run inside the local-recipes pixi env, which carries marp + Chrome)::

    pixi run -e local-recipes deck-export <slug> [html|deck-pptx|infographic-pptx ...]
    pixi run -e local-recipes deck-export <slug> --format all|pptx|summary|html

With no targets and no ``--format`` it regenerates all three marp exports after
stamping. ``--pptx`` needs Chrome at ``/usr/bin/google-chrome`` (auto-wired
here); ``html`` is pure Node. ``DECK_EXPORT_DATE=YYYY-MM-DD`` pins the rebuild
day (tests).
"""
from __future__ import annotations

import argparse
import glob
import html
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

from pyforge.herald import stamps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALID_TARGETS = {"html", "deck-pptx", "infographic-pptx"}
FORMATS = {"all", "pptx", "summary", "html"}
CHROME = "/usr/bin/google-chrome"
LEDGER_FACT_IDS = (
    "tree_commit_date",
    "cfe_skill_version",
    "bmad_core_version",
    "fleet_epics_done_total",
    "fleet_stories_done_total",
)
BAND_ATTR = "data-herald-ledger-band"
MARP_BAND = "<!-- herald-ledger-band -->"
MARP_KINDS = ("deck", "executive-summary", "infographic")


def find_source(marp_dir: str, slug: str, kind: str):
    """Return (path, date) for the newest ``<slug>-<kind>-<YYYY-MM-DD>.md``.

    Exact kind+date only. A looser ``{slug}-{kind}-*.md`` glob would prefer
    ``<slug>-infographic-deck-narration-2026-07-31.md`` over
    ``<slug>-infographic-2026-09-15.md`` because ``deck`` sorts after ``2``.
    """
    dated = re.compile(
        rf"^{re.escape(slug)}-{re.escape(kind)}-(\d{{4}}-\d{{2}}-\d{{2}})\.md$"
    )
    scored: list[tuple[str, str]] = []
    for p in glob.glob(os.path.join(marp_dir, f"{slug}-{kind}-*.md")):
        m = dated.match(os.path.basename(p))
        if m:
            scored.append((m.group(1), p))
    if not scored:
        return None, None
    day, src = max(scored, key=lambda item: item[0])
    return src, day


def chrome_available() -> bool:
    """Whether a Chrome/Chromium binary the ``--pptx`` targets need
    (``marp --pptx`` shells a headless render) can actually be found --
    checked before those targets run so a missing browser skips them
    instead of crashing mid-``marp`` (Story 23.3).

    Checks the hardcoded ``CHROME`` path, a handful of common binary names
    on ``PATH``, and an already-set ``CHROME_PATH`` env var (``marp``'s own
    override, per its docs) -- a machine with a real but differently
    named/located Chrome must not silently report "no chrome". A stale or
    mistyped ``CHROME_PATH`` must not report "available" either (Story
    23.5 follow-up review) -- it is only trusted when it actually points
    at a file."""
    chrome_path_env = os.environ.get("CHROME_PATH")
    return bool(
        os.path.exists(CHROME)
        or shutil.which("chromium")
        or shutil.which("chromium-browser")
        or shutil.which("google-chrome")
        or shutil.which("google-chrome-stable")
        or (chrome_path_env and os.path.exists(chrome_path_env))
    )


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


def rebuild_day() -> str:
    pinned = os.environ.get("DECK_EXPORT_DATE", "").strip()
    if pinned:
        return pinned
    return date.today().isoformat()


def load_fact_values(facts_path: Path) -> dict[str, str]:
    """Tiny facts.yaml reader — id/value pairs only (no PyYAML required)."""
    out: dict[str, str] = {}
    current: str | None = None
    if not facts_path.is_file():
        return out
    for raw in facts_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("- id:"):
            current = line.split(":", 1)[1].strip().strip("\"'")
        elif current and line.startswith("value:"):
            out[current] = line.split(":", 1)[1].strip().strip("\"'")
            current = None
    return out


def ledger_cells(facts: dict[str, str]) -> list[tuple[str, str]]:
    return [(fid, facts[fid]) for fid in LEDGER_FACT_IDS if fid in facts]


def html_ledger_band(facts: dict[str, str]) -> str:
    cells = []
    for fid, value in ledger_cells(facts):
        cells.append(
            f'<span data-fact="{html.escape(fid, quote=True)}">'
            f"{html.escape(value)}</span>"
        )
    inner = " · ".join(cells) if cells else ""
    return (
        f'<div {BAND_ATTR}="1" style="font-size:14px;opacity:0.85;margin-top:16px;">'
        f"Ledger {inner}</div>"
    )


def stamp_exec_summary(path: Path, facts: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8")
    band = html_ledger_band(facts)
    pattern = re.compile(
        rf"<div {re.escape(BAND_ATTR)}=\"1\"[^>]*>.*?</div>",
        re.DOTALL,
    )
    if pattern.search(text):
        text = pattern.sub(band, text, count=1)
    else:
        for end in ("</x-dc>", "</body>"):
            if end in text:
                text = text.replace(end, band + "\n" + end, 1)
                break
        else:
            text = text.rstrip() + "\n" + band + "\n"
    path.write_text(text, encoding="utf-8")


def marp_ledger_slide(facts: dict[str, str]) -> str:
    bits = []
    for fid, value in ledger_cells(facts):
        bits.append(f'<span data-fact="{html.escape(fid, quote=True)}">{html.escape(value)}</span>')
    body = " · ".join(bits)
    return f"\n\n{MARP_BAND}\n\n---\n\n## Ledger\n\n{body}\n"


def stamp_marp_source(src: Path, dest: Path, facts: dict[str, str]) -> None:
    text = src.read_text(encoding="utf-8")
    slide = marp_ledger_slide(facts)
    if MARP_BAND in text:
        text = text.split(MARP_BAND, 1)[0].rstrip() + slide
    else:
        text = text.rstrip() + slide
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")


def find_exec_summary(deck_dir: Path) -> Path | None:
    hits = sorted(deck_dir.joinpath("project").glob("*Executive Summary.dc.html"))
    return hits[0] if hits else None


def stamp_marp_kinds(marp_dir: Path, slug: str, facts: dict[str, str], day: str) -> None:
    for kind in MARP_KINDS:
        src, _ = find_source(str(marp_dir), slug, kind)
        if not src:
            continue
        dest = marp_dir / f"{slug}-{kind}-{day}.md"
        stamp_marp_source(Path(src), dest, facts)


def format_to_targets(fmt: str | None, positional: list[str]) -> set[str]:
    if fmt == "summary":
        return set()
    if fmt == "pptx":
        return {"deck-pptx", "infographic-pptx"}
    if fmt == "html":
        return {"html"}
    if fmt == "all" or (fmt is None and not positional):
        return set(VALID_TARGETS)
    return set(positional)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("slug", help="deck directory under presentations/")
    ap.add_argument(
        "targets",
        nargs="*",
        help="any of: html deck-pptx infographic-pptx (default: all three after stamp)",
    )
    ap.add_argument(
        "--format",
        dest="fmt",
        choices=sorted(FORMATS),
        help="Story 21.5: summary stamps the exec; pptx/html/all also stamp marp then export",
    )
    args = ap.parse_args()

    if args.targets and args.fmt:
        sys.exit("error: pass positional targets or --format, not both")

    targets = format_to_targets(args.fmt, args.targets)
    bad = targets - VALID_TARGETS
    if bad:
        sys.exit(
            f"error: unknown target(s): {', '.join(sorted(bad))}; "
            f"valid: {', '.join(sorted(VALID_TARGETS))}"
        )

    deck_dir = Path(ROOT) / "presentations" / args.slug
    marp_dir = deck_dir / "src" / "marp"
    pptx_dir = deck_dir / "src" / "pptx"
    if not marp_dir.is_dir():
        sys.exit(f"error: {marp_dir.relative_to(ROOT)} not found")
    pptx_dir.mkdir(parents=True, exist_ok=True)

    facts = load_fact_values(deck_dir / "facts.yaml")
    day = rebuild_day()
    stamp_summary = args.fmt in ("all", "summary")
    stamp_marp = args.fmt in ("all", "pptx", "html")

    if stamp_summary:
        exec_path = find_exec_summary(deck_dir)
        if exec_path is None:
            sys.exit(f"error: no Executive Summary.dc.html under {deck_dir / 'project'}")
        stamp_exec_summary(exec_path, facts)
        print(f"  stamped {exec_path.relative_to(ROOT)}")

    if stamp_marp:
        stamp_marp_kinds(marp_dir, args.slug, facts, day)

    if not targets:
        print(f"\n{args.slug}: stamped summary (no marp export requested)")
        return

    deck_md, deck_date = find_source(str(marp_dir), args.slug, "deck")
    info_md, info_date = find_source(str(marp_dir), args.slug, "infographic")

    if os.path.exists(CHROME):
        os.environ.setdefault("CHROME_PATH", CHROME)

    chrome_ok = chrome_available()
    produced: list[str] = []
    if "html" in targets:
        if not info_md:
            sys.exit("error: no infographic .md source for the 'html' target")
        out = os.path.join(
            str(marp_dir), f"{args.slug}-infographic-standalone-{info_date}.html"
        )
        run_marp([info_md, "-o", out])
        produced.append(out)
        stamps.write_stamp(Path(out), repo_root=Path(ROOT), slug=args.slug)
    if "infographic-pptx" in targets:
        if not info_md:
            sys.exit("error: no infographic .md source for 'infographic-pptx'")
        if not chrome_ok:
            print(f"{args.slug}: derive-skipped: no chrome (infographic-pptx)")
        else:
            out = os.path.join(pptx_dir, f"{args.slug}_infographic_deck-{info_date}.pptx")
            run_marp(["--pptx", info_md, "-o", out])
            produced.append(out)
            stamps.write_stamp(Path(out), repo_root=Path(ROOT), slug=args.slug)
    if "deck-pptx" in targets:
        if not deck_md:
            sys.exit("error: no deck .md source for the 'deck-pptx' target")
        if not chrome_ok:
            print(f"{args.slug}: derive-skipped: no chrome (deck-pptx)")
        else:
            out = os.path.join(pptx_dir, f"{args.slug}-deck-{deck_date}.pptx")
            run_marp(["--pptx", deck_md, "-o", out])
            produced.append(out)
            stamps.write_stamp(Path(out), repo_root=Path(ROOT), slug=args.slug)

    print(f"\n{args.slug}: regenerated {len(produced)} artifact(s):")
    for p in produced:
        print("  ", os.path.relpath(p, ROOT))


if __name__ == "__main__":
    main()
