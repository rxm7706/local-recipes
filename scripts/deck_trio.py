#!/usr/bin/env python3
"""Derive a presentation deck's Infographic HEAD from its standalone poster.

Every PyForge deck's Infographic head (``project/<Persona> - Infographic.dc.html``)
is, per ``docs/specs/presentation-deck.md`` § *Artifact dependency tree*, the
standalone poster's body with exactly three mechanical differences:

1. the body content is wrapped in ``<x-dc>...</x-dc>``, with a ``<helmet>`` as
   its first child;
2. the standalone's ``<head><style>...</style>`` block moves into that
   ``<helmet>`` verbatim, alongside the standalone's own font/stylesheet
   ``<link>`` tags;
3. a ``<script src="./support.js"></script>`` tag is added to ``<head>``, and a
   ``<script type="text/x-dc" data-dc-script data-props='{"$preview":{...}}'>``
   tag is appended before ``</body>`` -- its ``$preview`` height an actual
   headless-browser measurement of the standalone (never a guess, never a
   render of the head itself -- see ``measure_height``'s docstring).

Nothing has derived this until now -- each deck's README hand-tracked the
resulting drift as "standalone ahead" (spec-21-1 Intent). This script is a
*pure* function of the standalone's current bytes: an unchanged standalone
produces byte-identical head output on rerun, and the write is skipped (no
rewrite, mtime untouched) when the derived bytes already match what's on disk.
It refuses rather than guesses on any malformed input (missing/ambiguous
poster, no locatable ``<style>`` block) and never writes to the standalone
under any code path.

Only ``--head`` is implemented here; ``--deck`` (Infographic Deck derivation)
is Story 21.2's.

Usage (the ``scripts/deck_facts.py`` / ``deck_export.py`` precedent -- one
script, one pixi task)::

    pixi run -e local-recipes deck-trio <slug> --head
"""
from __future__ import annotations

import argparse
import os
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTER_SUFFIX = " Infographic standalone.html"
PREVIEW_WIDTH = 1240


# ------------------------------------------------------------------ parsing

class _PosterStructure(HTMLParser):
    """Locates, by raw offset into the poster's decoded text, exactly what the
    three-way mechanical transform needs: every ``<link>`` tag and ``<style>``
    block inside ``<head>`` (moved into ``<helmet>`` verbatim), and the inner
    content of ``<body>`` (wrapped in ``<x-dc>``). Mirrors deck_facts.py's
    ``_MarkSpans`` offset-tracking technique (``getpos()`` +
    ``get_starttag_text()``), not its class -- this is a different, simpler
    shape (no splicing, only the spans this transform needs).
    """

    def __init__(self, text: str) -> None:
        super().__init__(convert_charrefs=True)
        self.text = text
        self._line_start = [0]
        i = text.find("\n")
        while i >= 0:
            self._line_start.append(i + 1)
            i = text.find("\n", i + 1)
        self.links: list[tuple[int, int]] = []
        self.style_spans: list[tuple[int, int]] = []
        self.body_inner: tuple[int, int] | None = None
        self._in_head = False
        self._style_start: int | None = None
        self._body_start: int | None = None

    def _at(self) -> int:
        """Absolute offset of the construct being handled (getpos() is
        1-based line + characters since the last \\n)."""
        line, col = self.getpos()
        return self._line_start[line - 1] + col

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        start = self._at()
        end = start + len(self.get_starttag_text() or "")
        if tag == "head":
            self._in_head = True
        elif tag == "link" and self._in_head:
            self.links.append((start, end))
        elif tag == "style" and self._in_head:
            self._style_start = start
        elif tag == "body" and self._body_start is None:
            self._body_start = end

    def handle_endtag(self, tag: str) -> None:
        start = self._at()
        if tag == "head":
            self._in_head = False
        elif tag == "style" and self._style_start is not None:
            close = self.text.find(">", start)
            end = len(self.text) if close < 0 else close + 1
            self.style_spans.append((self._style_start, end))
            self._style_start = None
        elif tag == "body" and self._body_start is not None and self.body_inner is None:
            self.body_inner = (self._body_start, start)


# ---------------------------------------------------------------- transform

def render_head(parser: _PosterStructure, poster_text: str, height: int) -> str:
    """The pure 3-way mechanical transform (Boundaries & Constraints, Always
    #1-#3): the derived head's full text, given a poster already parsed by
    ``_PosterStructure`` and a measured ``$preview`` height.

    Assumes ``parser.style_spans`` and ``parser.body_inner`` are non-empty --
    the caller (``main()``) checks and refuses before calling this.
    """
    spans = sorted(parser.links + parser.style_spans)
    helmet_content = "\n".join(poster_text[start:end] for start, end in spans)
    body_start, body_end = parser.body_inner  # type: ignore[misc]
    body_content = poster_text[body_start:body_end]
    props = (
        "{&quot;$preview&quot;:{&quot;width&quot;:" + str(PREVIEW_WIDTH)
        + ",&quot;height&quot;:" + str(height) + "}}"
    )
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
        f"{helmet_content}\n"
        "</helmet>"
        f"{body_content}"
        "</x-dc>\n"
        f'<script type="text/x-dc" data-dc-script data-props="{props}"></script>\n'
        "</body>\n"
        "</html>\n"
    )


# ------------------------------------------------------------------ measure

def measure_height(poster: Path) -> int:
    """Render ``poster`` (the standalone file, not the transformed head --
    see the module docstring and spec Design Notes) headless at width 1240
    and return ``document.documentElement.scrollHeight``, the ``$preview``
    height. Isolated as its own function so tests can monkeypatch it and run
    fully offline (no live browser).

    The standalone is rendered, never the head: the head's ``<x-dc>``/
    ``<helmet>`` are inert without the ``support.js`` runtime, which is
    frequently absent from a deck's ``project/`` directory on disk, while the
    standalone is guaranteed valid, runtime-independent HTML whose body is
    byte-equivalent to the head's.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # noqa: BLE001 -- an unimportable/broken install
        raise RuntimeError(f"playwright is not usable: {exc}") from exc

    with sync_playwright() as p:
        try:
            # Same channel="chrome"-with-fallback order as deck_qa.py's render_gate.
            browser = p.chromium.launch(channel="chrome", timeout=30_000)
        except (Exception, SystemExit):  # noqa: BLE001 -- fall back to bundled
            # chromium. SystemExit included: playwright's own internals have
            # raised it live (deck_qa.py's render_gate hit this exact failure
            # mode first; see its own comment at the identical fallback point).
            try:
                browser = p.chromium.launch(timeout=30_000)
            except (Exception, SystemExit) as exc:  # noqa: BLE001 -- no usable
                # browser at all
                raise RuntimeError(f"no usable chromium: {exc}") from exc
        try:
            try:
                page = browser.new_page(viewport={"width": PREVIEW_WIDTH, "height": 800})
            except (Exception, SystemExit) as exc:  # noqa: BLE001 -- page creation failure
                raise RuntimeError(f"page creation failed: {exc}") from exc
            try:
                try:
                    # wait_until="networkidle" + document.fonts.ready: the default
                    # "load" event fires before web fonts finish downloading, which
                    # let scrollHeight vary run-to-run against an unchanged poster.
                    page.goto(poster.resolve().as_uri(), wait_until="networkidle")
                    page.evaluate("document.fonts.ready")
                    return int(page.evaluate("document.documentElement.scrollHeight"))
                except (Exception, SystemExit) as exc:  # noqa: BLE001 -- navigation/measurement failure
                    raise RuntimeError(f"height measurement failed: {exc}") from exc
            finally:
                page.close()
        finally:
            browser.close()


# --------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("slug", help="deck directory under presentations/")
    ap.add_argument(
        "--head",
        action="store_true",
        required=True,
        help="derive the Infographic head (*.dc.html) from the standalone poster "
        "-- the only mode this story implements (--deck is Story 21.2's)",
    )
    args = ap.parse_args(argv)

    root = ROOT
    hits = sorted((root / "presentations" / args.slug / "project").glob(f"*{POSTER_SUFFIX}"))
    if not hits:
        ap.error(f"no poster: presentations/{args.slug}/project/*{POSTER_SUFFIX}")
    if len(hits) > 1:
        ap.error(
            f"ambiguous poster: presentations/{args.slug}/project/*{POSTER_SUFFIX} matches "
            f"{', '.join(p.name for p in hits)}"
        )
    poster = hits[0]
    rel_poster = poster.relative_to(root).as_posix()
    persona = poster.name[: -len(POSTER_SUFFIX)]
    head_path = poster.parent / f"{persona} - Infographic.dc.html"

    raw = poster.read_bytes()
    try:
        poster_text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        ap.error(f"{rel_poster} is not UTF-8: {exc}")

    parser = _PosterStructure(poster_text)
    parser.feed(poster_text)
    parser.close()
    if not parser.style_spans:
        ap.error(f"{rel_poster}: <head> has no <style> block")
    if parser.body_inner is None:
        ap.error(f"{rel_poster}: no <body> element found")

    try:
        height = measure_height(poster)
    except RuntimeError as exc:
        ap.error(str(exc))
    new_bytes = render_head(parser, poster_text, height).encode("utf-8")

    if head_path.is_file() and head_path.read_bytes() == new_bytes:
        print(f"{args.slug}: unchanged {head_path.relative_to(root).as_posix()}")
        return 0

    # Temp file + os.replace: an interrupted write never leaves a truncated
    # head, mirroring deck_facts.py's own poster-rewrite idiom.
    tmp = head_path.with_name(head_path.name + ".deck-trio.tmp")
    tmp.write_bytes(new_bytes)
    os.replace(tmp, head_path)
    print(f"{args.slug}: wrote {head_path.relative_to(root).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
