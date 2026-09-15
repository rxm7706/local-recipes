#!/usr/bin/env python3
"""Derive a deck's Infographic head from its standalone poster.

``presentations/<slug>/project/<Persona> Infographic standalone.html`` is the
trio source (contract: ``spec-deck-family-lockstep`` CAP-1, herald Story 21.1).
``--head`` wraps that standalone's body in ``<x-dc>``, moves every ``<link>``
and the one ``<style>`` block into ``<helmet>``, and writes

    presentations/<slug>/project/<Persona> - Infographic.dc.html

with the outer dc.html shell (``./support.js``) and a ``$preview`` script.
The standalone is never written. A second run on unchanged bytes prints
``unchanged``.

Usage (the ``scripts/deck_export.py`` precedent: one script, one pixi task)::

    pixi run -e local-recipes deck-trio <slug> --head

This is NOT a detector (never in ``detectors`` / ``detectors-ci``). The only
non-zero exit is a usage error -- exit 2, no write. Do not pass ``--deck``
(Story 21.2).
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

POSTER_SUFFIX = " Infographic standalone.html"
DEFAULT_WIDTH = 1240
DEFAULT_HEIGHT = 2200

_HEAD = re.compile(r"<head\b[^>]*>(.*?)</head>", re.DOTALL | re.IGNORECASE)
_BODY = re.compile(r"<body\b[^>]*>(.*)</body>", re.DOTALL | re.IGNORECASE)
_STYLE = re.compile(r"<style\b[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)
_LINK = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
# Property form, not the tail of max-width / min-height.
_WIDTH = re.compile(r"(?<![\w-])width:(\d+)px")
_HEIGHT = re.compile(r"(?<![\w-])height:(\d+)px")


class MissingStyleError(ValueError):
    """Standalone ``<head>`` has no locatable ``<style>`` block."""


def standalone_hits(root: Path, slug: str) -> list[Path]:
    return sorted((root / "presentations" / slug / "project").glob(f"*{POSTER_SUFFIX}"))


def persona_and_paths(root: Path, slug: str) -> tuple[Path, Path]:
    hits = standalone_hits(root, slug)
    standalone = hits[0]
    persona = standalone.name[: -len(POSTER_SUFFIX)]
    head = standalone.parent / f"{persona} - Infographic.dc.html"
    return standalone, head


def derive_head(standalone_text: str) -> str:
    head_m = _HEAD.search(standalone_text)
    head_html = head_m.group(1) if head_m else ""
    style_m = _STYLE.search(head_html)
    if style_m is None:
        raise MissingStyleError("standalone <head> has no locatable <style> block")
    links = _LINK.findall(head_html)
    body_m = _BODY.search(standalone_text)
    body_inner = body_m.group(1) if body_m else ""
    width_m = _WIDTH.search(body_inner)
    height_m = _HEIGHT.search(body_inner)
    width = int(width_m.group(1)) if width_m else DEFAULT_WIDTH
    height = int(height_m.group(1)) if height_m else DEFAULT_HEIGHT
    props = json.dumps(
        {"$preview": {"width": width, "height": height}},
        separators=(",", ":"),
    )
    escaped = html.escape(props, quote=True)
    helmet = "\n".join([*links, style_m.group(0)])
    return (
        "<!DOCTYPE html>\n"
        "<html>\n"
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<script src="./support.js"></script>\n'
        "</head>\n"
        "<body>\n"
        "<x-dc>\n"
        "<helmet>\n"
        f"{helmet}\n"
        "</helmet>"
        f"{body_inner}"
        "</x-dc>\n"
        f'<script type="text/x-dc" data-dc-script data-props="{escaped}"></script>\n'
        "</body>\n"
        "</html>\n"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("slug", help="deck directory under presentations/")
    ap.add_argument(
        "--head",
        action="store_true",
        help="derive project/<Persona> - Infographic.dc.html from the standalone",
    )
    args = ap.parse_args(argv)
    if not args.head:
        ap.error("--head is required")

    root = ROOT
    deck_dir = root / "presentations" / args.slug
    if not deck_dir.is_dir():
        ap.error(f"presentations/{args.slug} not found")
    hits = standalone_hits(root, args.slug)
    if not hits:
        ap.error(f"no standalone: presentations/{args.slug}/project/*{POSTER_SUFFIX}")
    if len(hits) > 1:
        ap.error(
            f"ambiguous standalone: {len(hits)} files match "
            f"presentations/{args.slug}/project/*{POSTER_SUFFIX}"
        )

    standalone, head = persona_and_paths(root, args.slug)
    try:
        derived = derive_head(standalone.read_text(encoding="utf-8"))
    except MissingStyleError as exc:
        ap.error(str(exc))

    existing = head.read_text(encoding="utf-8") if head.is_file() else None
    if existing == derived:
        print("unchanged")
    else:
        head.write_text(derived, encoding="utf-8")
        print("wrote")
    return 0


if __name__ == "__main__":
    sys.exit(main())
