"""Whole-file managed-region discovery (Story 8.2, architecture FR-113 /
AD-53 / P-06).

Story 8.1's ``markers.py`` owns ONE line at a time; this module owns the
scan across a whole file: where each managed region's bytes actually are,
and which files are structurally unsafe to touch at all. The span it
returns is what S-8.3 substitutes against, so AR-1 (region corruption) is
contained here -- in a pure function that can be exhaustively unit-tested
-- rather than in the writer.

Spans are BYTE offsets into ``text.encode("utf-8")`` (P-06: substitution is
byte-span replacement, never a semantic markdown edit), accumulated
line-by-line while walking ``splitlines(keepends=True)`` -- never by
re-encoding a growing prefix per line, which would make a scan quadratic in
file size.

Nesting and overlap are ONE rule (FR-113 names them as one), so the tracker
here is a single ``open region | None``, not a stack: an interleaved
``begin a, begin b, end a, end b`` cannot be reached without first passing
through the exact state a properly-nested ``begin a, begin b, end b, end a``
reaches -- "a ``begin`` arrived while a region is still open". Rejecting
that state as a category therefore needs no lookahead and no stack, and
rejecting it (rather than supporting well-formed nesting) is the point: a
nested region has no unambiguous body span to substitute.

CRLF, LF, and a lone CR parse identically because BOTH the line split and
the terminator strip go through ``str.splitlines()``, whose universal
line-boundary handling collapses all three into one boundary -- so the
content handed to ``markers.parse_marker_line`` is always terminator-free
without a manual ``.rstrip("\\r")`` special case (which would recover CRLF
only, and silently mis-handle every other boundary ``splitlines`` splits
on). Byte offsets are still measured against the ORIGINAL bytes, each
line's real terminator included, so a CRLF file's spans address the CRLF
file.

Fence awareness exists because a managed region's own content may DOCUMENT
the marker grammar inside a fenced code block; honoring such a line would
let a doc example open, close, or corrupt real parser state. It applies
only to the ``html`` format (the one AD-53 registers for ``.md``) --
``hash`` files have no fenced-code-block concept, and inventing one for
them would let a shell script's ``~~~`` banner comment silently swallow
real markers.

This module never compares a region's declared ``sha`` against its actual
body (P-07: hash guards belong to detect, never to a parser), never writes,
never reads a file (the caller passes ``text`` in, P-03), and never
re-implements line-level grammar -- a ``MarkerError`` from
``parse_marker_line`` propagates unchanged.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass

from pyforge.core.errors import PyforgeError

from ..model.version import ModelVersion
from .markers import BeginMarker, RegionFormat, parse_marker_line

# A CommonMark-shaped fence opener/closer: up to 3 leading spaces (4 would
# make it an indented code block, not a fence), then a run of at least 3
# backticks or tildes. Matched with `.match()`, not `.fullmatch()` -- an
# opening fence may carry an info string (```python), and this module needs
# only the run itself to decide fence state.
_FENCE_PATTERN = re.compile(r" {0,3}(`{3,}|~{3,})")


class RegionParseError(PyforgeError, ValueError):
    """Raised for a region-STRUCTURE violation across a file: nested or
    overlapping regions, a ``begin`` never closed before end of text, two
    regions sharing one name, or an ``end`` that does not match the region
    currently open (including a stray ``end`` with nothing open).

    Never raised for a line-level grammar violation -- that stays
    ``MarkerError``, raised by ``markers.parse_marker_line`` and propagated
    unchanged, so the two failure classes remain separately catchable.

    Story 14.3, SPEC-pyforge-core CAP-5: ``PyforgeError`` is an additional
    base -- ``ValueError`` stays in the MRO.
    """


@dataclass(frozen=True)
class RegionSpan:
    """One fully-parsed managed region's identity and byte extents.

    ``begin_span``/``end_span`` cover exactly their marker LINE's bytes,
    excluding that line's own terminator. ``body_span`` covers every byte
    strictly between the two marker lines -- it starts immediately after the
    ``begin`` line's terminator and ends exactly where the ``end`` line's
    bytes start -- so interior newlines are included, both marker lines are
    excluded, and a region whose markers sit on adjacent lines yields an
    empty (start == end) body span. The resulting substitution contract, the
    one S-8.3 depends on, is
    ``text_bytes[:body_span[0]] + new_body + text_bytes[body_span[1]:]``.

    ``sha`` is the value DECLARED by the ``begin`` marker, reported as-is
    and never recomputed against ``body_span``'s actual content: comparing
    them is a detect-stage guard (P-07), not a parser's job.
    """

    name: str
    model_version: ModelVersion
    sha: str
    body_span: tuple[int, int]
    begin_span: tuple[int, int]
    end_span: tuple[int, int]


@dataclass(frozen=True)
class _OpenRegion:
    """The at-most-one region awaiting its ``end`` marker."""

    marker: BeginMarker
    lineno: int
    begin_span: tuple[int, int]
    body_start: int


def _fence_delimiter(content: str) -> tuple[str, int] | None:
    """The (fence character, run length) of a line that OPENS a fenced code
    block, or ``None`` for any other line. An opener may carry trailing
    content (an info string, e.g. ```python) -- only a closer is
    constrained, which is why closing is a separate check (``_closes_fence``)
    rather than reusing this function's result directly."""
    match = _FENCE_PATTERN.match(content)
    if match is None:
        return None
    run = match.group(1)
    return run[0], len(run)


def _closes_fence(content: str, open_fence: tuple[str, int]) -> bool:
    """Whether ``content`` closes a fence opened with ``open_fence`` (its
    character and run length). CommonMark: a closing fence must use the same
    character, a run at least as long as the opener's, AND have nothing but
    whitespace after the run -- unlike an opener, which may carry an info
    string. Without the trailing-whitespace check, a line like
    ` ``` still open ` would end the fence early, exposing whatever real
    marker text follows it (still logically inside the fence) to the live
    parser -- the exact AR-1 corruption fence-awareness exists to prevent,
    triggered from the opposite direction."""
    match = _FENCE_PATTERN.match(content)
    if match is None:
        return False
    run = match.group(1)
    if run[0] != open_fence[0] or len(run) < open_fence[1]:
        return False
    return content[match.end() :].strip() == ""


def _iter_lines(text: str) -> Iterator[tuple[str, int, int, int]]:
    """Yield ``(content, line_start, content_end, line_end)`` per line:
    ``content`` is terminator-free (what the marker grammar sees), while the
    three offsets are byte positions in ``text.encode("utf-8")`` --
    ``line_start`` and ``content_end`` bound the line's own bytes without its
    terminator, and ``line_end`` is where the NEXT line starts.

    Owning the offset advance here (rather than in the caller's loop) is
    what lets ``parse_regions`` ``continue`` past a fenced or non-marker line
    without ever risking a skipped increment -- the one bookkeeping slip that
    would silently misplace every subsequent span.
    """
    offset = 0
    for line in text.splitlines(keepends=True):
        # `splitlines()` on a single kept-ends line yields exactly one
        # element: the same line, minus whatever boundary it ended with.
        content = line.splitlines()[0]
        content_end = offset + len(content.encode("utf-8"))
        line_end = offset + len(line.encode("utf-8"))
        yield content, offset, content_end, line_end
        offset = line_end


def parse_regions(text: str, fmt: RegionFormat) -> tuple[RegionSpan, ...]:
    """Locate every managed region in ``text``, in file order.

    Pure (P-03): no I/O, no subprocess, no clock -- the caller reads the
    file and passes its text in. ``fmt`` is the artifact's DECLARED format
    (AD-53), used exactly as given and never sniffed from ``text``.

    Raises ``RegionParseError`` for a structure violation (see that class),
    and propagates ``MarkerError``/``NotImplementedError`` unchanged from
    ``markers.parse_marker_line`` -- for a malformed line, or for a reserved
    (``slashstar``) or unregistered ``fmt``, respectively.
    """
    # Force `fmt` validation eagerly, even for empty/marker-free text: the
    # loop below only ever reaches `parse_marker_line` on a line that looks
    # like a marker, so a reserved/unregistered `fmt` used to scan text with
    # no such line would otherwise never be checked at all. Probing with an
    # empty line is side-effect-free for every registered format (its
    # delimiter prefix never matches "") and triggers the exact same guard
    # `parse_marker_line` already runs unconditionally for `slashstar`.
    parse_marker_line(fmt, "")

    # Value equality, not identity: `parse_marker_line` coerces a bare
    # `"html"` string to the canonical member and would happily parse its
    # markers, so an `is` check here would silently drop fence-awareness for
    # exactly that caller -- the one narrow path where a documented marker
    # inside a fence could corrupt a real scan.
    fence_aware = fmt == RegionFormat.HTML

    spans: list[RegionSpan] = []
    closed_names: set[str] = set()
    open_fence: tuple[str, int] | None = None
    fence_lineno = 0
    open_region: _OpenRegion | None = None

    for lineno, (content, line_start, content_end, line_end) in enumerate(_iter_lines(text), start=1):
        if fence_aware:
            if open_fence is not None:
                if _closes_fence(content, open_fence):
                    open_fence = None
                continue
            delimiter = _fence_delimiter(content)
            if delimiter is not None:
                open_fence = delimiter
                fence_lineno = lineno
                continue

        marker = parse_marker_line(fmt, content)
        if marker is None:
            continue

        if isinstance(marker, BeginMarker):
            if open_region is not None:
                raise RegionParseError(
                    f"line {lineno}: region {marker.region!r} begins while region"
                    f" {open_region.marker.region!r} (line {open_region.lineno}) is still"
                    " open -- nested or overlapping managed regions are a hard error"
                )
            if marker.region in closed_names:
                raise RegionParseError(
                    f"line {lineno}: duplicate region {marker.region!r} -- a region name"
                    " may appear at most once per file"
                )
            open_region = _OpenRegion(
                marker=marker,
                lineno=lineno,
                begin_span=(line_start, content_end),
                body_start=line_end,
            )
            continue

        if open_region is None:
            raise RegionParseError(f"line {lineno}: end marker for region {marker.region!r} with no region open")
        if marker.region != open_region.marker.region:
            raise RegionParseError(
                f"line {lineno}: end marker for region {marker.region!r} does not match the"
                f" open region {open_region.marker.region!r} (line {open_region.lineno})"
            )
        spans.append(
            RegionSpan(
                name=open_region.marker.region,
                model_version=open_region.marker.model_version,
                sha=open_region.marker.sha,
                body_span=(open_region.body_start, line_start),
                begin_span=open_region.begin_span,
                end_span=(line_start, content_end),
            )
        )
        closed_names.add(marker.region)
        open_region = None

    if open_fence is not None:
        # Checked BEFORE the unterminated-begin case below: an unclosed
        # fence silently swallows every line after it (fenced content is
        # never scanned for markers at all), so a region that looks
        # unterminated -- or simply missing -- from here on is very often a
        # symptom of THIS root cause, not a separate mistake. But a region
        # opened and left unclosed BEFORE the fence ever appeared is a
        # genuinely separate problem -- name it too, rather than silently
        # dropping it behind the fence error.
        char, run_length = open_fence
        detail = ""
        if open_region is not None:
            detail = f" (region {open_region.marker.region!r}, begun at line {open_region.lineno}, is also still open)"
        raise RegionParseError(
            f"line {fence_lineno}: a {char * run_length!r} fenced code block is never closed before end of text{detail}"
        )
    if open_region is not None:
        raise RegionParseError(
            f"region {open_region.marker.region!r} begins at line {open_region.lineno}"
            " but is never closed before end of text"
        )
    return tuple(spans)


# The literal anchor sentinel that never searches file content -- it always
# resolves, to the byte offset right after a YAML frontmatter block (or 0
# when there is none). See ``_frontmatter_end`` and ``resolve_anchor``.
_TOP_SENTINEL = "<top>"

# `core/spec_surface.py`'s own frontmatter delimiter -- `<top>`'s detection
# mirrors that module's established `---`/`---` convention (first line
# exactly `---`, the next line THAT IS `---` closes it), reimplemented
# locally rather than imported: importing `core/spec_surface.py` would give
# `regions/` its first dependency on `pyforge.marshal.core`, for ~10 lines of
# well-established, easily-mirrored logic (this story's own Design Notes).
_FRONTMATTER_DELIMITER = "---"


@dataclass(frozen=True)
class AnchorResolution:
    """Where a region belongs, and which anchor (if any) put it there.

    ``offset`` is a BYTE offset into ``text.encode("utf-8")`` (P-06, the same
    convention every ``RegionSpan`` offset already follows), always a valid
    insertion point: immediately after the matched anchor line's own
    terminator, immediately after a YAML frontmatter block (or byte 0) for
    ``<top>``, or ``len(text.encode())`` for the EOF append fallback.

    ``matched`` is the literal anchor string from ``anchor`` that resolved
    (including ``"<top>"`` itself), or ``None`` for the EOF fallback -- named
    here so a future plan layer can surface which anchor was chosen (AD-57's
    own surface, not this story's; see the module's Never bullets).
    """

    offset: int
    matched: str | None


def _frontmatter_end(text: str) -> int:
    """The byte offset right after a leading YAML frontmatter block in
    ``text``, or ``0`` when ``text`` carries no such block.

    Mirrors ``core/spec_surface.py::parse_declared_surface``'s own detection
    exactly (see that module's docstring): the first line must be exactly
    ``---`` (whitespace-stripped), and the block closes at the next line
    that is exactly ``---`` -- NOT necessarily the second line -- scanning
    forward from there. An unclosed block (no closing ``---`` before end of
    text) is "no such block", per that same established convention, and
    returns ``0`` exactly like a text with no leading ``---`` at all.
    """
    lines = list(_iter_lines(text))
    if not lines or lines[0][0].strip() != _FRONTMATTER_DELIMITER:
        return 0
    for content, _line_start, _content_end, line_end in lines[1:]:
        if content.strip() == _FRONTMATTER_DELIMITER:
            return line_end
    return 0


def resolve_anchor(text: str, fmt: RegionFormat, anchor: tuple[str, ...]) -> AnchorResolution:
    """Resolve ``anchor`` -- an ORDERED preference list, not a file-position
    search (see the module's Design Notes) -- against ``text`` to a single
    byte offset a new region may be inserted at.

    Tries each literal in ``anchor`` IN ORDER. For an ordinary anchor
    string, the FIRST anchor with ANY matching line anywhere in the file
    (``content.startswith(anchor_text)``, fence-skipped exactly like
    ``parse_regions``'s own ``fence_aware`` gate -- so a line that only
    LOOKS like an anchor from inside a fenced code block is never treated as
    one) wins, and ``offset`` is that line's own ``line_end`` (right after
    its terminator) -- the first such line encountered in file order, when
    more than one line matches the same anchor text. The literal sentinel
    ``"<top>"`` never searches file content at all: the moment it is reached
    in ``anchor``'s own order, it always resolves, via ``_frontmatter_end``.

    When nothing in ``anchor`` matches (including when ``"<top>"`` is not
    present in ``anchor`` at all), returns ``matched=None`` and
    ``offset=len(text.encode())`` -- the EOF append fallback.

    Raises ``NotImplementedError`` for ``RegionFormat.SLASHSTAR`` (reserved,
    unimplemented in V1) -- symmetric with ``parse_regions``'s own eager
    ``parse_marker_line(fmt, "")`` validation (review finding: without this,
    ``resolve_anchor`` silently ran ordinary, non-fence-aware matching for a
    reserved format instead of raising -- currently masked in
    ``insert_region`` only because it always calls ``parse_regions`` first,
    which already raises for this same ``fmt``, but this function is
    independently public).

    Raises ``RegionParseError`` if a fenced code block is never closed
    before end of text -- symmetric with ``parse_regions``'s own identical
    hard error for the identical condition (review finding: without this,
    an unterminated fence made every remaining line, including any real
    anchor candidate after it, silently unmatchable with no error at all --
    currently masked in ``insert_region`` only because it always calls
    ``parse_regions`` first, which already raises for this same file, but
    this function is independently public).

    Pure (P-03): no I/O, exactly like ``parse_regions``, which this function
    shares its fence-tracking and line-iteration machinery with rather than
    duplicating it.
    """
    # Force `fmt` validation eagerly, exactly like `parse_regions` -- see
    # that function's own comment on why probing with an empty line is
    # side-effect-free for every registered format.
    parse_marker_line(fmt, "")

    fence_aware = fmt == RegionFormat.HTML
    first_match_end: dict[str, int] = {}
    open_fence: tuple[str, int] | None = None
    fence_lineno = 0

    for lineno, (content, _line_start, _content_end, line_end) in enumerate(_iter_lines(text), start=1):
        if fence_aware:
            if open_fence is not None:
                if _closes_fence(content, open_fence):
                    open_fence = None
                continue
            delimiter = _fence_delimiter(content)
            if delimiter is not None:
                open_fence = delimiter
                fence_lineno = lineno
                continue

        for anchor_text in anchor:
            if anchor_text == _TOP_SENTINEL or anchor_text in first_match_end:
                continue
            if content.startswith(anchor_text):
                first_match_end[anchor_text] = line_end

    if open_fence is not None:
        char, run_length = open_fence
        raise RegionParseError(
            f"line {fence_lineno}: a {char * run_length!r} fenced code block is never closed before end of text"
        )

    for anchor_text in anchor:
        if anchor_text == _TOP_SENTINEL:
            return AnchorResolution(offset=_frontmatter_end(text), matched=_TOP_SENTINEL)
        if anchor_text in first_match_end:
            return AnchorResolution(offset=first_match_end[anchor_text], matched=anchor_text)

    return AnchorResolution(offset=len(text.encode("utf-8")), matched=None)
