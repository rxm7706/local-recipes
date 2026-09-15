#!/usr/bin/env python3
"""Derive a presentation deck's Infographic HEAD and Infographic Deck from its
standalone poster.

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

The Infographic Deck (``project/<Persona> - Infographic Deck.dc.html``) is the
same standalone's sections re-laid as 1920x1080 slides, in document order:
one masthead slide (``data-label="Cover"``, when the standalone carries
content before its first act/section), one ``<section data-label>`` per act
band (``<div class="act">``, never split), one-or-more per numbered section
(``<section class="sec">``, split only when its own rendered content
overflows a slide's content budget, packed at its own direct-child
boundaries), and one closing-band slide (``data-label="Close"``, when the
standalone carries content after its last act/section) -- each wrapped in the
family's own ``width:1240px`` page frame so content renders unchanged from
the standalone. A non-numbered full-bleed banner sitting BETWEEN act/section
elements (e.g. a mid-deck "doctrine" band) is neither a masthead, a closing
band, nor a numbered section, and produces no slide.

Both modes are pure functions of the standalone's current bytes: an unchanged
standalone produces byte-identical output on rerun, and the write is skipped
(no rewrite, mtime untouched) when the derived bytes already match what's on
disk. Both refuse rather than guess on any malformed input (missing/ambiguous
poster, no locatable ``<style>`` block, no act bands, no numbered sections, an
empty act/section label, a section with zero direct children, a
measured-vs-parsed section-count mismatch) and never write to the standalone
under any code path. When both ``--head`` and ``--deck`` are
requested together, both modes' preconditions are validated (and their output
rendered) before either file is written, so a ``--deck`` failure can never
leave a ``--head`` write behind.

Usage (the ``scripts/deck_facts.py`` / ``deck_export.py`` precedent -- one
script, one pixi task)::

    pixi run -e local-recipes deck-trio <slug> --head
    pixi run -e local-recipes deck-trio <slug> --deck
    pixi run -e local-recipes deck-trio <slug> --head --deck
"""
from __future__ import annotations

import argparse
import os
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTER_SUFFIX = " Infographic standalone.html"
DECK_SUFFIX = " - Infographic Deck.dc.html"
PREVIEW_WIDTH = 1240

# The family's own documented page frame (infographic-standard.md's Authoring
# template): content renders at the same width as the standalone, no reflow.
PAGE_FRAME_STYLE = "width:1240px; margin:0 auto; padding:56px 56px 0; box-sizing:border-box"
PAGE_FRAME_PADDING_TOP = 56
PAGE_FRAME_PADDING_BOTTOM = 0

SLIDE_WIDTH = 1920
SLIDE_HEIGHT = 1080
# The vertical space actually available for a slide's content once the page
# frame's own top+bottom padding is subtracted (Design Notes § Overflow split).
SLIDE_CONTENT_BUDGET = SLIDE_HEIGHT - PAGE_FRAME_PADDING_TOP - PAGE_FRAME_PADDING_BOTTOM

_MEASURE_CONTAINER_ID = "__deck_trio_frame__"
# Reads back, in one round-trip, the container's own total content height
# (``scrollHeight``, compared against SLIDE_CONTENT_BUDGET after subtracting
# the frame's own padding) plus each DIRECT child's own effective height,
# measured as the delta between consecutive children's own
# ``getBoundingClientRect().top`` -- or to the container's own bottom edge
# for the last child -- rather than an isolated
# ``getBoundingClientRect().height``. The isolated-rect *height* measurement
# excludes inter-sibling margins that CSS margin-collapse makes real, so a
# "fitting" packed group's true height once isolated could exceed the
# budget; this position-delta technique captures the real gap instead
# (Design Notes § Overflow split). A same-page ``offsetTop`` delta would
# capture the identical gap, but ``offsetTop`` is unreliable on ``<svg>``
# root elements (verified live against the Warden poster's own inline
# diagrams: some Chromium builds return ``undefined`` for an SVG's
# ``offsetTop``, poisoning the delta with ``NaN``) -- every real poster in
# this family carries inline SVGs (infographic-standard.md's own floor is
# >= 3), so ``getBoundingClientRect().top`` (defined on every ``Element``,
# SVG included) is used instead. Both children's rects and the container's
# own bottom are read in the same synchronous pass, so no scroll can occur
# between them and no positioned-ancestor requirement applies.
_MEASURE_SCRIPT = (
    "(() => { "
    "const el = document.getElementById(" + repr(_MEASURE_CONTAINER_ID) + "); "
    "const kids = Array.from(el.children); "
    "const containerBottom = el.getBoundingClientRect().top + el.scrollHeight; "
    "const tops = kids.map(c => c.getBoundingClientRect().top); "
    "const children = kids.map((c, i) => "
    "(i + 1 < kids.length ? tops[i + 1] : containerBottom) - tops[i]); "
    "return {total: el.scrollHeight, children}; })()"
)

# HTML5 void elements: never have a closing tag, so a generic open/close
# depth-tracking stack must never push (and never expect a pop for) one.
_VOID_ELEMENTS = frozenset(
    {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }
)


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


class _Act:
    """One ``<div class="act">`` band: its own full outer source span (wrapped
    verbatim, never split -- Boundaries & Constraints, Always #4) plus its
    nested ``.lbl``/``.ttl`` text (the ``.lbl`` text is the slide's
    ``data-label``, Always #5)."""

    __slots__ = ("lbl", "span", "ttl")

    def __init__(self, span: tuple[int, int], lbl: str, ttl: str) -> None:
        self.span = span
        self.lbl = lbl
        self.ttl = ttl


class _Section:
    """One ``<section class="sec">``: its own full outer source span (``span``
    -- used only to bound the masthead/closing-band search, never as slide
    content), its first ``<h2>`` text (the slide's ``data-label``), and the
    raw source spans of its own DIRECT children -- not the section's inner
    content as one span, but sliced per child so the overflow-split path
    (Design Notes § Overflow split) can pack them onto consecutive slides
    without ever splitting inside an element."""

    __slots__ = ("children", "heading", "span")

    def __init__(
        self, heading: str, children: list[tuple[int, int]], span: tuple[int, int]
    ) -> None:
        self.heading = heading
        self.children = children
        self.span = span


class _DeckStructure(HTMLParser):
    """Locates, by raw offset into the poster's decoded text, every act band
    (``<div class="act">``) and numbered section (``<section class="sec">``)
    inside the poster, in document order -- exactly what the deck-derivation
    transform needs. Mirrors ``_PosterStructure``'s offset-tracking technique
    (``getpos()`` + ``get_starttag_text()``), not its class -- a new,
    purpose-built subclass for an unrelated shape (spec-21-1's own Code Map
    note: reuse the PATTERN, not the class).

    A small open-tag depth stack (mirroring a real DOM stack, HTML5 void
    elements excluded per ``_VOID_ELEMENTS``) identifies: the tag that closes
    an open act/section at its own opening depth (so nested markup inside
    either construct never confuses the boundary), and every tag that opens
    at exactly depth+1 relative to an open section's own depth -- its DIRECT
    children, sliced by their own start/end offsets for the overflow-split
    path.

    The masthead (content before the first act/section) and closing band
    (content after the last) are NOT captured by this parser directly -- the
    caller (``main()``) derives their spans from ``items[0]``/``items[-1]``'s
    own ``span``, the poster's shared ``_PosterStructure.body_inner``, and
    (Design Notes § Ambient wrapper exclusion) this parser's own
    ``first_item_outer_chain``/``last_item_outer_chain``/``close_starts`` --
    the open-tag ancestry (excluding ``<body>``) at the first item's own open
    and the last item's own close, used to detect and strip the family's
    standard whole-body wrapper div rather than slice straight through its
    own tag pair.
    """

    def __init__(self, text: str) -> None:
        super().__init__(convert_charrefs=True)
        self.text = text
        self._line_start = [0]
        i = text.find("\n")
        while i >= 0:
            self._line_start.append(i + 1)
            i = text.find("\n", i + 1)

        self.acts: list[_Act] = []
        self.sections: list[_Section] = []
        # Combined, in document order -- acts and sections never nest or
        # overlap, so appending each at its own close preserves source order.
        self.items: list[tuple[str, object]] = []

        self._stack: list[str] = []
        self._open_act: dict | None = None
        self._open_section: dict | None = None
        # Stack of [str] accumulators; handle_data appends to the innermost
        # active one (a .lbl/.ttl span or a section's first <h2>).
        self._text_targets: list[list[str]] = []

        # Ambient wrapper exclusion (Design Notes): a parallel (tag, start,
        # open_tag_end) stack, tracked in lockstep with ``_stack``, for
        # every tag still open once inside ``<body>`` (``_body_depth`` marks
        # where inside-body entries begin) -- plus a start-offset -> own
        # close-tag-start map so a wrapper identified via
        # first/last_item_outer_chain can be resolved to its own closing
        # tag's own start offset.
        self._tag_spans: list[tuple[str, int, int]] = []
        self._body_depth: int | None = None
        self.close_starts: dict[tuple[str, int], int] = {}
        self.first_item_outer_chain: list[tuple[str, int, int]] | None = None
        self.last_item_outer_chain: list[tuple[str, int, int]] | None = None

    def _at(self) -> int:
        line, col = self.getpos()
        return self._line_start[line - 1] + col

    @staticmethod
    def _class_of(attrs) -> str:  # noqa: ANN001
        for name, value in attrs:
            if name == "class":
                return value or ""
        return ""

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        start = self._at()
        cls = self._class_of(attrs)
        depth = len(self._stack)

        is_new_item = (tag == "div" and cls == "act" and self._open_act is None) or (
            tag == "section" and cls == "sec" and self._open_section is None
        )
        if is_new_item and self.first_item_outer_chain is None:
            self.first_item_outer_chain = list(self._tag_spans[self._body_depth or 0 :])

        if tag == "div" and cls == "act" and self._open_act is None:
            self._open_act = {"start": start, "depth": depth, "lbl": None, "ttl": None}
        elif tag == "section" and cls == "sec" and self._open_section is None:
            self._open_section = {"start": start, "depth": depth, "h2": None, "children": []}
        elif self._open_section is not None and depth == self._open_section["depth"] + 1:
            # A direct child of the open section's own content.
            self._open_section["children"].append([start, None])

        if self._open_act is not None:
            if tag == "span" and cls == "lbl" and self._open_act["lbl"] is None:
                self._open_act["lbl"] = []
                self._text_targets.append(self._open_act["lbl"])
            elif tag == "span" and cls == "ttl" and self._open_act["ttl"] is None:
                self._open_act["ttl"] = []
                self._text_targets.append(self._open_act["ttl"])
        if self._open_section is not None and tag == "h2" and self._open_section["h2"] is None:
            self._open_section["h2"] = []
            self._text_targets.append(self._open_section["h2"])

        if tag not in _VOID_ELEMENTS:
            close = self.text.find(">", start)
            tag_open_end = len(self.text) if close < 0 else close + 1
            self._tag_spans.append((tag, start, tag_open_end))
            self._stack.append(tag)
            if tag == "body" and self._body_depth is None:
                self._body_depth = len(self._stack)

    def handle_data(self, data: str) -> None:
        if self._text_targets:
            self._text_targets[-1].append(data)

    def handle_endtag(self, tag: str) -> None:
        start = self._at()
        close = self.text.find(">", start)
        end = len(self.text) if close < 0 else close + 1

        if tag not in _VOID_ELEMENTS and self._stack:
            self._stack.pop()
            if self._tag_spans:
                popped_tag, popped_start, _popped_open_end = self._tag_spans.pop()
                self.close_starts[(popped_tag, popped_start)] = start
        depth = len(self._stack)

        # Close whichever text capture this tag's own end belongs to, before
        # any boundary bookkeeping below.
        if self._open_act is not None and self._text_targets and tag == "span":
            top = self._text_targets[-1]
            # Identity, not equality: two still-empty accumulators are `==`
            # (both `[]`) but must never be confused for one another.
            if top is self._open_act.get("lbl") or top is self._open_act.get("ttl"):
                self._text_targets.pop()
        if (
            self._open_section is not None
            and tag == "h2"
            and self._text_targets
            and self._text_targets[-1] is self._open_section.get("h2")
        ):
            self._text_targets.pop()

        if (
            self._open_section is not None
            and self._open_section["children"]
            and depth == self._open_section["depth"] + 1
            and self._open_section["children"][-1][1] is None
        ):
            self._open_section["children"][-1][1] = end

        if self._open_act is not None and tag == "div" and depth == self._open_act["depth"]:
            lbl = "".join(self._open_act["lbl"] or []).strip()
            ttl = "".join(self._open_act["ttl"] or []).strip()
            act = _Act(span=(self._open_act["start"], end), lbl=lbl, ttl=ttl)
            self.acts.append(act)
            self.items.append(("act", act))
            self._open_act = None
            self.last_item_outer_chain = list(self._tag_spans[self._body_depth or 0 :])
        elif self._open_section is not None and tag == "section" and depth == self._open_section["depth"]:
            heading = "".join(self._open_section["h2"] or []).strip()
            children = [(s, e) for s, e in self._open_section["children"] if e is not None]
            section = _Section(
                heading=heading, children=children, span=(self._open_section["start"], end)
            )
            self.sections.append(section)
            self.items.append(("sec", section))
            self._open_section = None
            self.last_item_outer_chain = list(self._tag_spans[self._body_depth or 0 :])


# ---------------------------------------------------------------- transform

def _helmet_content(parser: _PosterStructure, poster_text: str) -> str:
    """The verbatim font/stylesheet ``<link>`` + ``<style>`` relocation both
    ``--head`` and ``--deck`` perform (Boundaries & Constraints, Always #3):
    every ``<link>``/``<style>`` span the parser found inside ``<head>``,
    joined in source order."""
    spans = sorted(parser.links + parser.style_spans)
    return "\n".join(poster_text[start:end] for start, end in spans)


def render_head(parser: _PosterStructure, poster_text: str, helmet_content: str, height: int) -> str:
    """The pure 3-way mechanical transform (Boundaries & Constraints, Always
    #1-#3): the derived head's full text, given a poster already parsed by
    ``_PosterStructure``, its already-collected helmet content, and a
    measured ``$preview`` height.

    Assumes ``parser.body_inner`` is non-empty -- the caller (``main()``)
    checks and refuses before calling this.
    """
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


def _escape_attr(text: str) -> str:
    """Re-escape a label pulled from decoded ``handle_data`` text (entities
    already resolved) back into a well-formed HTML attribute value."""
    return text.replace("&", "&amp;").replace('"', "&quot;")


def _pack_children(heights: list[int], budget: int) -> list[list[int]]:
    """Greedily packs child indices, in source order, into as few consecutive
    groups as needed so no group's cumulative height exceeds ``budget`` --
    closing the current group and opening a new one exactly when the next
    child would overflow it. A single child that alone exceeds the budget
    still becomes its own best-effort group; no deeper split is attempted
    (Design Notes § Overflow split)."""
    groups: list[list[int]] = []
    current: list[int] = []
    current_height = 0
    for i, h in enumerate(heights):
        if current and current_height + h > budget:
            groups.append(current)
            current = []
            current_height = 0
        current.append(i)
        current_height += h
    if current:
        groups.append(current)
    return groups


def _build_deck_slides(
    parser: _DeckStructure,
    poster_text: str,
    measurements: list[tuple[int, list[int]]],
    masthead: str | None,
    closing: str | None,
) -> list[tuple[str, str]]:
    """Assembles the full, in-order slide list (Boundaries & Constraints,
    Always #1-#2, #30-#31): an optional masthead bookend, one slide per act
    band (never split), one-or-more per numbered section (split only when its
    own rendered content overflows the slide's content budget -- Design
    Notes § Overflow split), and an optional closing-band bookend.
    ``measurements`` is aligned index-for-index with ``parser.sections``.
    ``masthead``/``closing`` are the already-decided (``None`` when absent)
    raw source spans -- never split, matching an act band's treatment, not a
    section's overflow-split one."""
    slides: list[tuple[str, str]] = []
    if masthead is not None:
        slides.append(("Cover", masthead))

    section_i = 0
    for kind, obj in parser.items:
        if kind == "act":
            act: _Act = obj  # type: ignore[assignment]
            slides.append((act.lbl, poster_text[act.span[0] : act.span[1]]))
            continue

        section: _Section = obj  # type: ignore[assignment]
        total, child_heights = measurements[section_i]
        section_i += 1
        child_htmls = [poster_text[s:e] for s, e in section.children]

        if total <= SLIDE_CONTENT_BUDGET:
            slides.append((section.heading, "\n".join(child_htmls)))
            continue

        groups = _pack_children(child_heights, SLIDE_CONTENT_BUDGET)
        n = len(groups)
        for i, group in enumerate(groups, start=1):
            label = section.heading if i == 1 else f"{section.heading} (cont. {i}/{n})"
            content = "\n".join(child_htmls[j] for j in group)
            slides.append((label, content))

    if closing is not None:
        slides.append(("Close", closing))
    return slides


_SLIDE_STYLE = (
    "box-sizing:border-box; width:100%; height:100%; background:var(--color-bg); "
    "color:var(--color-text); font-family:var(--font-body); overflow:hidden;"
)


def render_deck(helmet_content: str, slides: list[tuple[str, str]]) -> str:
    """The pure transform (Boundaries & Constraints, Always #4-#7, #34): given
    the already-collected ``<helmet>`` content and an ordered list of
    ``(label, content_html)`` slide tuples, the derived deck's full text --
    matching the family's own established 14-file skeleton (``<x-import
    component-from-global-scope="deck-stage" ...>`` inside ``<x-dc>``) and
    laying every slide out at the family's own page frame so content renders
    exactly as it did in the standalone -- no reflow, no redesign. Never
    fabricates ``data-speaker-notes`` (Never #4): the attribute is simply
    never emitted.
    """
    slide_markup = "\n\n".join(
        f'  <section data-label="{_escape_attr(label)}" style="{_SLIDE_STYLE}">\n'
        f'    <div style="{PAGE_FRAME_STYLE}">\n{content}\n    </div>\n  </section>'
        for label, content in slides
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
        "</helmet>\n"
        '<x-import component-from-global-scope="deck-stage" from="./deck-stage.js" '
        f'width="{SLIDE_WIDTH}" height="{SLIDE_HEIGHT}" hint-size="100%,100%" data-uneditable="">\n\n'
        f"{slide_markup}\n\n"
        "</x-import>\n"
        "</x-dc>\n"
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


def measure_section(page, helmet_content: str, child_htmls: list[str]) -> tuple[int, list[int]]:
    """Renders one section's (or, in principle, any) direct-child source
    spans inside the family's own 1240px page frame (``PAGE_FRAME_STYLE``)
    and reads back, in one round-trip, the container's total content height
    (frame padding subtracted, so it compares directly against
    ``SLIDE_CONTENT_BUDGET``) and each child's own effective height via the
    margin-collapse-safe ``getBoundingClientRect().top``-delta technique
    (``_MEASURE_SCRIPT``) -- ``_build_deck_slides``'s greedy packer turns
    these into a slide count.

    Applies the same ``wait_until="networkidle"`` + ``document.fonts.ready``
    fix ``measure_height`` needed (spec-21-1 Review pass, 2026-09-14) from the
    start: an unfixed font-load race wouldn't just jitter a cosmetic height
    number here, it could change which children land on which slide between
    runs, breaking the "second run changes nothing" AC outright. Takes an
    already-open ``page`` so ``measure_all_sections`` can reuse a single one
    across every section in a ``--deck`` run instead of launching Chromium
    per section.
    """
    html = (
        "<!DOCTYPE html>\n<html>\n<head>\n"
        '<meta charset="utf-8">\n'
        f"{helmet_content}\n"
        "</head>\n<body>\n"
        f'<div id="{_MEASURE_CONTAINER_ID}" style="{PAGE_FRAME_STYLE}">\n'
        + "\n".join(child_htmls)
        + "\n</div>\n</body>\n</html>\n"
    )
    try:
        page.set_content(html, wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        result = page.evaluate(_MEASURE_SCRIPT)
    except (Exception, SystemExit) as exc:  # noqa: BLE001 -- render/measurement failure
        raise RuntimeError(f"section measurement failed: {exc}") from exc

    total = round(result["total"]) - PAGE_FRAME_PADDING_TOP - PAGE_FRAME_PADDING_BOTTOM
    children = [round(h) for h in result["children"]]
    return total, children


def measure_all_sections(
    sections: list[_Section], poster_text: str, helmet_content: str
) -> list[tuple[int, list[int]]]:
    """Launches Chromium ONCE (the same launch-fallback/timeout/
    ``SystemExit``-tolerant order ``measure_height`` uses) and reuses a
    single page across every section's measurement, mirroring
    ``deck_qa.py``'s ``render_gate`` (one browser, reused across many units
    of work) -- a ``--deck`` run may measure ~20-30 sections, so a
    per-section launch/teardown would be needlessly slow. Isolated as its
    own function so tests can monkeypatch it wholesale and run fully offline
    (no live browser), mirroring ``measure_height``'s own docstring
    rationale for ``--head``. Returns one ``(total, child_heights)`` tuple
    per section, aligned index-for-index with ``sections`` -- the caller
    (``main()``) guards against a monkeypatch (or future bug) returning a
    mismatched length rather than assuming the alignment holds.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # noqa: BLE001 -- an unimportable/broken install
        raise RuntimeError(f"playwright is not usable: {exc}") from exc

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", timeout=30_000)
        except (Exception, SystemExit):  # noqa: BLE001 -- fall back to bundled chromium
            try:
                browser = p.chromium.launch(timeout=30_000)
            except (Exception, SystemExit) as exc:  # noqa: BLE001 -- no usable browser at all
                raise RuntimeError(f"no usable chromium: {exc}") from exc
        try:
            try:
                page = browser.new_page(viewport={"width": PREVIEW_WIDTH, "height": 800})
            except (Exception, SystemExit) as exc:  # noqa: BLE001 -- page creation failure
                raise RuntimeError(f"page creation failed: {exc}") from exc
            try:
                return [
                    measure_section(
                        page, helmet_content, [poster_text[s:e] for s, e in section.children]
                    )
                    for section in sections
                ]
            finally:
                page.close()
        finally:
            browser.close()


# --------------------------------------------------------------------- main

def _write_if_changed(slug: str, root: Path, path: Path, new_bytes: bytes) -> None:
    """Compare-before-write idempotency shared by ``--head`` and ``--deck``:
    skip the write (mtime untouched) when the derived bytes already match
    what's on disk. Temp file + ``os.replace``: an interrupted write never
    leaves a truncated artifact, mirroring ``deck_facts.py``'s own
    poster-rewrite idiom."""
    if path.is_file() and path.read_bytes() == new_bytes:
        print(f"{slug}: unchanged {path.relative_to(root).as_posix()}")
        return
    tmp = path.with_name(path.name + ".deck-trio.tmp")
    tmp.write_bytes(new_bytes)
    os.replace(tmp, path)
    print(f"{slug}: wrote {path.relative_to(root).as_posix()}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("slug", help="deck directory under presentations/")
    ap.add_argument(
        "--head",
        action="store_true",
        help="derive the Infographic head (*.dc.html) from the standalone poster",
    )
    ap.add_argument(
        "--deck",
        action="store_true",
        help="derive the Infographic Deck (*.dc.html, slides re-laid from the "
        "standalone poster's masthead/acts/sections/closing band)",
    )
    args = ap.parse_args(argv)
    if not args.head and not args.deck:
        ap.error("specify --head and/or --deck")

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

    helmet_content = _helmet_content(parser, poster_text)

    # Both requested modes are fully validated AND rendered here, before
    # either is written below -- so a --deck precondition failure can never
    # leave a --head write behind, or vice versa (Boundaries & Constraints,
    # Always #8).
    head_path: Path | None = None
    head_bytes: bytes | None = None
    if args.head:
        try:
            height = measure_height(poster)
        except RuntimeError as exc:
            ap.error(str(exc))
        head_bytes = render_head(parser, poster_text, helmet_content, height).encode("utf-8")
        head_path = poster.parent / f"{persona} - Infographic.dc.html"

    deck_path: Path | None = None
    deck_bytes: bytes | None = None
    if args.deck:
        deck_parser = _DeckStructure(poster_text)
        deck_parser.feed(poster_text)
        deck_parser.close()
        if not deck_parser.acts:
            ap.error(f'{rel_poster}: no <div class="act"> bands found')
        if not deck_parser.sections:
            ap.error(f'{rel_poster}: no <section class="sec"> elements found')
        for i, act in enumerate(deck_parser.acts, start=1):
            if not act.lbl:
                ap.error(f"{rel_poster}: act band {i} has an empty .lbl label")
        for i, section in enumerate(deck_parser.sections, start=1):
            if not section.children:
                ap.error(f"{rel_poster}: numbered section {i} has zero direct children")
            if not section.heading:
                ap.error(f"{rel_poster}: numbered section {i} has an empty <h2> label")

        try:
            measurements = measure_all_sections(deck_parser.sections, poster_text, helmet_content)
        except RuntimeError as exc:
            ap.error(str(exc))
        if len(measurements) != len(deck_parser.sections):
            ap.error(
                f"{rel_poster}: measured {len(measurements)} section(s) but parsed "
                f"{len(deck_parser.sections)} section(s) -- refusing rather than "
                "guessing which measurement belongs to which section"
            )

        # Masthead/closing band: the body's leading/trailing spans outside
        # any act/section, bounded by document position rather than a class
        # match (Design Notes § Masthead and closing band). Reuses the
        # shared _PosterStructure's own body_inner -- the same span --head
        # wraps in <x-dc> -- rather than re-deriving body bounds here.
        body_start, body_end = parser.body_inner  # type: ignore[misc]
        first_item = deck_parser.items[0][1]
        last_item = deck_parser.items[-1][1]
        first_start = first_item.span[0]  # type: ignore[attr-defined]
        last_end = last_item.span[1]  # type: ignore[attr-defined]

        # Ambient wrapper exclusion (Design Notes): the family's own
        # standard authoring template wraps the ENTIRE body -- masthead
        # through closing band -- in one page-frame div. A raw
        # body_start/body_end slice would cut straight through that div's
        # own tag pair (unclosed opening tag in the masthead, orphaned
        # closing tag in the closing band). When the same open-tag chain
        # (excluding <body>) is still open both at the first item's own
        # open and at the last item's own close, it is one unbroken
        # wrapper spanning both bookends -- slice from ITS OWN
        # inner-content bounds instead. Any other shape (no such wrapper,
        # or a different chain at each end) falls back to the unchanged
        # body_start/body_end slice.
        wrap_start, wrap_end = body_start, body_end
        first_chain = deck_parser.first_item_outer_chain or []
        last_chain = deck_parser.last_item_outer_chain or []
        if first_chain and last_chain and first_chain == last_chain:
            wrapper_tag, wrapper_start, wrapper_open_end = first_chain[0]
            wrapper_close_start = deck_parser.close_starts.get((wrapper_tag, wrapper_start))
            if wrapper_close_start is not None:
                wrap_start, wrap_end = wrapper_open_end, wrapper_close_start

        masthead_raw = poster_text[wrap_start:first_start]
        closing_raw = poster_text[last_end:wrap_end]
        masthead = masthead_raw if masthead_raw.strip() else None
        closing = closing_raw if closing_raw.strip() else None

        slides = _build_deck_slides(deck_parser, poster_text, measurements, masthead, closing)
        deck_bytes = render_deck(helmet_content, slides).encode("utf-8")
        deck_path = poster.parent / f"{persona}{DECK_SUFFIX}"

    if head_path is not None and head_bytes is not None:
        _write_if_changed(args.slug, root, head_path, head_bytes)
    if deck_path is not None and deck_bytes is not None:
        _write_if_changed(args.slug, root, deck_path, deck_bytes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
