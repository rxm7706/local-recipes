"""Span substitution and region insertion -- the two write primitives
(Stories 8.3/8.4, architecture FR-113 / AR-1 / P-06).

Story 8.2's ``parse.py`` locates a managed region's exact byte spans (and,
since Story 8.4, resolves an anchor to a byte offset via
``resolve_anchor``); Story 7.3's ``fs.replace_span``/``fs.write`` are the
guarded, atomic byte-span/whole-file writers. Nothing before this module
combined them into "replace a region's body with new content"
(``substitute_region``, S-8.3) or "put a region into a file that has never
had one" (``insert_region``, S-8.4) -- the two write paths the whole epic
exists to make safe. This module is that combination, and nothing more: it
does no I/O of its own to locate a region or an anchor (``text``/``region``/
``anchor`` are caller-supplied or resolved via a pure ``parse.py`` call),
and no I/O of its own to write one (every byte lands on disk via exactly one
``fs.replace_span``/``fs.write`` call).

**Why one combined ``fs.replace_span`` call, not two.** ``begin_span`` and
``body_span`` are two distinct, non-adjacent-in-content byte ranges (a
marker-line terminator sits between them), so a naive implementation might
replace each independently -- and since ``begin_span`` always precedes
``body_span`` in file order, replacing the body alone would never invalidate
the begin marker's own offsets, making TWO separate atomic writes
technically *possible*. It is still wrong: a crash (or any interruption)
between the two writes would leave a file with a NEW body but a STALE begin
marker (or vice versa) on disk -- a real, observable, on-disk half-merged
state, exactly what AR-1 exists to make structurally impossible. One
combined span, written through ``fs.replace_span``'s own single
temp-file-then-rename, means the file is either the old region or the new
one, in its entirety, never a hybrid of both.

**Why the terminator is sliced from ``text``, not re-derived.** ``parse.py``
establishes ``body_span`` as starting immediately after the begin line's
terminator. Rather than guessing the line-ending style (``\\n`` vs
``\\r\\n``) from context, slicing
``text.encode("utf-8")[begin_span[1]:body_span[0]]`` reads the ACTUAL 1-2
terminator bytes the file already has and reuses them verbatim -- the same
"never re-derive what you can read" discipline ``parse.py`` itself follows
for CRLF/LF parity.

This module imports ``fs`` (the module, not its individual functions) so a
caller can monkeypatch ``fs.replace_span`` and observe exactly how many
times ``substitute_region`` calls it -- mirroring ``test_seed_fs.py``'s own
precedent for ``fs.atomic_write_bytes``.

Never calls ``Path.write_text``, ``open(..., "w")``, or any write primitive
other than ``fs.replace_span``/``fs.write`` (P-01); never re-parses or
re-validates ``region`` against a fresh read of ``path`` (mirrors
``fs.replace_span``'s own accepted, documented TOCTOU limitation); never
handles marker deletion or opt-out (S-8.5's surface); and ``substitute_region``
never short-circuits as a no-op when ``new_body`` already matches (AD-60:
idempotence is a PLAN-layer concern for THAT primitive -- unlike
``insert_region``, whose own epics AC states the opposite for itself; see
its own docstring).

**Why ``insert_region`` imports ``model.manifest``'s types nowhere.**
``model/manifest.py`` already imports FROM ``regions.markers`` (Story 7.4),
so importing ``Region``/``ManifestEntry`` back into ``regions/`` here would
create a package import cycle. ``insert_region`` therefore takes plain
``name: str``/``anchor: tuple[str, ...]`` parameters, matching
``substitute_region``'s own dependence on ``model.version`` only, never
``model.manifest``.

**Substituting more than one region in the same file (review finding).**
Every ``RegionSpan``'s byte offsets are only valid against the EXACT
``text``/file bytes they were parsed from. A caller updating region A THEN
region B, both located by ONE ``parse_regions`` pass, must NOT reuse B's
now-stale offsets after A's write has changed the file's byte layout (a
different-length new body shifts every offset after it) -- doing so writes
into the wrong bytes of a file that has already moved out from under
`region`. This is not a new limitation this module introduces: it is the
same P-07 discipline the whole epic already establishes ("trusts the plan
that was already built from a fresh detect pass") applied one level down --
the correct pattern is detect (``parse_regions``) -> apply ONE region ->
re-detect -> apply the next, never parse-once-apply-many. `tests/unit/
test_seed_regions_apply.py` proves both the hazard (naive reuse of stale
offsets corrupts the file) and the safe pattern (re-parsing between calls
does not).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from pyforge.core.errors import PyforgeError

from .. import fs
from ..model.version import ModelVersion
from .markers import RegionFormat, region_sha, render_begin, render_end
from .parse import RegionSpan, parse_regions, resolve_anchor


class RegionShaMismatchError(PyforgeError, ValueError):
    """Raised by ``substitute_region`` when ``expected_sha`` does not match
    ``region.sha``, BEFORE any write is attempted -- the file is left
    completely untouched. Belt-and-braces defense-in-depth only: the
    primary guard is the caller's own fresh ``parse_regions`` detect pass
    (P-07); this is a second, cheap check against a stale ``region`` object
    a caller might otherwise substitute against.

    Story 14.3, SPEC-pyforge-core CAP-5: ``PyforgeError`` is an additional
    base -- ``ValueError`` stays in the MRO, matching
    ``MarkerError``/``RegionParseError``'s own shape.
    """


def substitute_region(
    text: str,
    path: Path,
    region: RegionSpan,
    new_body: str,
    *,
    model_version: ModelVersion,
    expected_sha: str,
    fmt: RegionFormat,
    repo_root: Path,
    never_write: fs.NeverWrite,
) -> None:
    """Replace ``region``'s begin marker line AND body with new content, in
    exactly one guarded write.

    ``text`` must be the SAME text the caller already parsed ``region`` out
    of via ``parse_regions`` -- read with ``path.read_text(encoding="utf-8",
    newline="")``, never plain ``read_text()``, whose universal-newline
    translation would silently convert ``\\r\\n`` to ``\\n`` on read and
    desync ``region``'s byte offsets from the file's real on-disk bytes.
    This function does no I/O of its own to verify that; it only trusts
    ``text``/``region`` as given, exactly like ``fs.replace_span``'s own
    offsets are trusted against whatever ``path`` currently holds.

    Raises ``RegionShaMismatchError`` before any write when
    ``region.sha != expected_sha``. Otherwise: computes the new sha via
    ``markers.region_sha(new_body)`` (never accepts a caller-supplied sha
    for the NEW marker -- only ``expected_sha``, for the OLD one, is caller
    input), renders the new begin marker line via
    ``markers.render_begin(fmt, region.name, model_version, new_sha)``,
    slices the original terminator bytes between the begin line and the
    body directly out of ``text`` (see the module docstring's second Design
    Note), and writes ``new_begin_line + terminator + new_body`` as ONE
    combined payload through exactly one
    ``fs.replace_span(path, region.begin_span[0], region.body_span[1], ...)``
    call (see the module docstring's first Design Note). Everything outside
    that combined span -- including the ``end`` marker line and any trailing
    content -- stays byte-identical, per ``fs.replace_span``'s own contract.

    ``new_body`` is written exactly as given, even if it literally contains
    conflict-marker-shaped text (``<<<<<<<``, ``=======``, ``>>>>>>>``) --
    pure byte concatenation has no notion of "special" text.

    Raises ``ValueError`` upfront if ``region.begin_span[1] >
    region.body_span[0]`` (review finding): every ``RegionSpan`` a real
    ``parse_regions`` call produces satisfies this by construction (the body
    always starts at or after the begin line's own end), so this can only
    fire against a hand-constructed, malformed ``region`` -- exactly the
    "error-prone" bypass this module's own docstring already discourages.
    Without this check, a negative-length slice silently returns ``b""``
    (Python slicing never raises on ``start > stop``), concatenating the new
    begin line directly onto the new body with no terminator between them --
    a corrupted, unterminated marker line written with no error at all.

    Raises ``TypeError`` upfront if ``new_body`` is not ``str`` (review
    finding, mirroring ``fs.replace_span``'s own identical upfront
    ``new_body`` check one layer down): without this, a caller accidentally
    passing ``bytes`` -- plausible, since ``fs.replace_span`` itself takes
    ``new_body: bytes`` -- previously fell through to a bare, contextless
    ``AttributeError: 'bytes' object has no attribute 'encode'`` instead of
    a named, attributable error.
    """
    if not isinstance(new_body, str):
        raise TypeError(f"new_body must be str, got {type(new_body).__name__}")
    if region.sha != expected_sha:
        raise RegionShaMismatchError(
            f"{path}: region {region.name!r} declared sha {region.sha!r} does not match"
            f" expected sha {expected_sha!r} -- refusing to write"
        )
    if region.begin_span[1] > region.body_span[0]:
        raise ValueError(
            f"{path}: region {region.name!r} has a malformed span -- begin_span ends at"
            f" {region.begin_span[1]} but body_span starts at {region.body_span[0]}"
            " (begin must end at or before body starts)"
        )

    new_sha = region_sha(new_body)
    new_begin_line = render_begin(fmt, region.name, model_version, new_sha)
    text_bytes = text.encode("utf-8")
    terminator = text_bytes[region.begin_span[1] : region.body_span[0]]
    combined = new_begin_line.encode("utf-8") + terminator + new_body.encode("utf-8")

    fs.replace_span(
        path,
        region.begin_span[0],
        region.body_span[1],
        combined,
        repo_root=repo_root,
        never_write=never_write,
    )


class InsertionOutcome(StrEnum):
    """``insert_region``'s own result: whether it actually wrote a new
    region, or found one already there and left the file untouched."""

    INSERTED = "inserted"
    ALREADY_PRESENT = "already-present"


@dataclass(frozen=True)
class InsertionResult:
    """``insert_region``'s full return value: the outcome, plus which anchor
    (if any) it acted on.

    ``matched`` mirrors ``AnchorResolution.matched`` exactly (the literal
    anchor string, or ``None`` for the EOF append fallback) for an
    anchor-resolved insertion, and is ``None`` for the two paths that never
    run anchor resolution at all -- ``ALREADY_PRESENT`` (no write, so no
    anchor was ever chosen) and an absent-file create (no anchor concept
    applies, the region is the file's entire content). Carrying this instead
    of discarding it is what lets a future plan layer surface "the chosen
    anchor... is named in the plan" (AD-56) without re-deriving it via a
    second ``resolve_anchor`` call.
    """

    outcome: InsertionOutcome
    matched: str | None


class AnchorInsideExistingRegionError(PyforgeError, ValueError):
    """Raised by ``insert_region`` when the anchor ``resolve_anchor`` chose
    falls strictly inside an ALREADY-EXISTING, DIFFERENT region's own
    begin/end span, BEFORE any write -- the file is left completely
    untouched (review finding).

    ``resolve_anchor`` has no notion of "already-parsed region spans" (it
    is a pure, anchor-text-only line search, matching this module's own
    established fence-only-awareness scope). If an anchor's literal text
    also happens to appear as ordinary content inside an UNRELATED existing
    region's body, the naive offset would splice a brand-new region's
    markers into the middle of that region -- producing exactly the
    nested/overlapping structure AR-1 and Story 8.2's own ``parse_regions``
    already reject as a hard error, just discovered one write later, on
    disk, instead of before ever touching the file. This check reuses
    ``existing`` -- the SAME ``parse_regions`` result ``insert_region``
    already computed for its own already-present check -- at no extra parse
    cost.

    Story 14.3, SPEC-pyforge-core CAP-5: ``PyforgeError`` is an additional
    base -- ``ValueError`` stays in the MRO, matching
    ``RegionShaMismatchError``'s own shape.
    """


def _eof_append_prefix(text: str) -> str:
    """The bytes to prepend to a payload being appended at end of file so
    it is separated from EXISTING content by exactly one blank line --
    never zero (review finding: a bare ``"\\n"`` prefix produces none when
    ``text`` has no trailing newline at all) and never two (review finding:
    a bare ``"\\n"`` prefix produces two when ``text`` already ends in a
    blank line) -- or by nothing at all when ``text`` is empty, since there
    is then no existing content to separate from, matching the absent-file
    create path's own "region alone, nothing else" contract."""
    if not text or text.endswith("\n\n"):
        return ""
    if text.endswith("\n"):
        return "\n"
    return "\n\n"


def _render_region(fmt: RegionFormat, name: str, model_version: ModelVersion, body: str) -> str:
    """Render a brand-new, freestanding region -- begin marker, body, end
    marker -- as one payload of newly-written bytes.

    Every rendered marker line ends in ``"\\n"`` regardless of the
    surrounding file's own line-ending convention: this is BRAND NEW text
    being inserted, not an existing line being substituted, so there is no
    ambient CRLF/LF to re-derive (unlike ``substitute_region``'s own
    terminator, sliced from ``text``). ``body``'s own trailing-newline
    responsibility mirrors ``substitute_region``'s ``new_body`` contract: if
    ``body`` does not itself end in ``"\\n"``, the end-marker line glues
    directly onto body's own last line -- this function does not append one
    on the caller's behalf.
    """
    sha = region_sha(body)
    begin_line = render_begin(fmt, name, model_version, sha)
    end_line = render_end(fmt, name)
    return f"{begin_line}\n{body}{end_line}\n"


def insert_region(
    text: str | None,
    path: Path,
    name: str,
    anchor: tuple[str, ...],
    body: str,
    *,
    model_version: ModelVersion,
    fmt: RegionFormat,
    repo_root: Path,
    never_write: fs.NeverWrite,
) -> InsertionResult:
    """Put a NEW region into ``path``, at the position ``anchor`` resolves
    to -- the primitive ``marshal seed adopt``'s "gain the model content"
    verb needs for the case S-8.2/S-8.3 never covered: a file that has never
    had the region at all.

    When ``text is not None`` (the file exists): runs ``parse_regions(text,
    fmt)`` first. If ``name`` is already among the returned spans, returns
    ``InsertionResult(InsertionOutcome.ALREADY_PRESENT, matched=None)``
    immediately -- untouched, no write at all (unlike ``substitute_region``,
    which defers idempotence to a future plan layer per AD-60, THIS
    primitive's own epics AC names "already-present is a no-op" as its own
    behavior; see the module docstring). Otherwise resolves ``anchor`` via
    ``resolve_anchor`` and writes the rendered region through exactly one
    ``fs.replace_span(path, offset, offset, payload, ...)`` call -- a
    zero-width span, satisfying ``fs.replace_span``'s own ``0 <= start <=
    end <= len(original)`` contract with ``start == end``, so insertion
    needs no new primitive in ``fs.py``. A matched-anchor insertion carries
    no leading blank line; the append-fallback (``resolve_anchor`` returns
    ``matched=None``) payload is preceded by exactly one blank line,
    computed by ``_eof_append_prefix`` (never a bare ``"\\n"`` -- see that
    function's own docstring), separating the appended region from whatever
    content precedes it. Returns ``InsertionResult(InsertionOutcome.INSERTED,
    matched=resolution.matched)`` -- the SAME ``matched`` ``resolve_anchor``
    itself produced, never re-derived.

    Raises ``AnchorInsideExistingRegionError`` BEFORE any write if the
    resolved offset falls strictly inside an already-existing, different
    region's own span (review finding -- see that class's own docstring).

    When ``text is None`` (the file is absent): skips detection and
    resolution entirely -- there is no existing span to splice into -- and
    writes the rendered region alone, nothing else, via ``fs.write(path,
    payload, ...)``. Returns ``InsertionResult(InsertionOutcome.INSERTED,
    matched=None)`` -- no anchor concept applies when there is no file to
    anchor against.

    Trusts the caller exactly like ``substitute_region`` trusts its own
    ``text``/``region``: performs no re-verification that ``text is None``
    truly means ``path`` is absent, or that a non-``None`` ``text`` is
    fresh.
    """
    payload = _render_region(fmt, name, model_version, body)

    if text is None:
        fs.write(path, payload.encode("utf-8"), repo_root=repo_root, never_write=never_write)
        return InsertionResult(outcome=InsertionOutcome.INSERTED, matched=None)

    existing = parse_regions(text, fmt)
    if any(span.name == name for span in existing):
        return InsertionResult(outcome=InsertionOutcome.ALREADY_PRESENT, matched=None)

    resolution = resolve_anchor(text, fmt, anchor)
    colliding = next(
        (span for span in existing if span.begin_span[0] < resolution.offset < span.end_span[1]),
        None,
    )
    if colliding is not None:
        raise AnchorInsideExistingRegionError(
            f"{path}: anchor {resolution.matched!r} resolves to byte {resolution.offset},"
            f" which falls inside the already-existing region {colliding.name!r} (span"
            f" {colliding.begin_span[0]}-{colliding.end_span[1]}) -- refusing to insert"
        )
    if resolution.matched is None:
        payload = f"{_eof_append_prefix(text)}{payload}"

    fs.replace_span(
        path,
        resolution.offset,
        resolution.offset,
        payload.encode("utf-8"),
        repo_root=repo_root,
        never_write=never_write,
    )
    return InsertionResult(outcome=InsertionOutcome.INSERTED, matched=resolution.matched)
