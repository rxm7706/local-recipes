"""Span substitution -- the update primitive (Story 8.3, architecture
FR-113 / AR-1 / P-06).

Story 8.2's ``parse.py`` locates a managed region's exact byte spans; Story
7.3's ``fs.replace_span`` is the guarded, atomic byte-span writer. Nothing
before this module combined them into "replace a region's body with new
content" -- the one write path the whole epic exists to make safe. This
module is that combination, and nothing more: it does no I/O of its own to
locate a region (``text``/``region`` are caller-supplied, already produced
by a single ``parse_regions`` pass), and no I/O of its own to write one
(every byte lands on disk via exactly one ``fs.replace_span`` call).

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
other than ``fs.replace_span`` (P-01); never re-parses or re-validates
``region`` against a fresh read of ``path`` (mirrors ``fs.replace_span``'s
own accepted, documented TOCTOU limitation); never resolves an anchor or
inserts a region that does not exist yet (S-8.4's surface); never handles
marker deletion or opt-out (S-8.5's surface); and never short-circuits as a
no-op when ``new_body`` already matches (AD-60: idempotence is a PLAN-layer
concern, a future story's surface, not this primitive's).

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

from pathlib import Path

from pyforge.core.errors import PyforgeError

from .. import fs
from ..model.version import ModelVersion
from .markers import RegionFormat, region_sha, render_begin
from .parse import RegionSpan


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
    """
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
