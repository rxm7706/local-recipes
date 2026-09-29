"""Unit tests for ``pyforge.marshal.seed.regions.parse`` (Stories 8.2/8.4) --
covers the spec's I/O & Edge-Case Matrix: zero/one/two regions, nesting and
overlap rejection, unterminated begin, duplicate region name, mismatched and
stray end markers, markdown fence awareness (html only), CRLF/LF parity, and
``MarkerError`` propagation from the line-level grammar -- plus the
body-span byte-offset proof over multi-byte UTF-8 content and the
zero-length-body case.

Story 8.4 adds ``resolve_anchor`` coverage: anchor-order-is-preference (not
file-position), the EOF append fallback, both ``<top>`` cases (with and
without frontmatter), and an anchor-shaped line shadowed inside a fence.
"""

from __future__ import annotations

import pytest
from pyforge.core.errors import PyforgeError

from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.regions.markers import (
    MarkerError,
    RegionFormat,
    region_sha,
    render_begin,
    render_end,
)
from pyforge.marshal.seed.regions.parse import (
    AnchorResolution,
    RegionParseError,
    RegionSpan,
    parse_regions,
    resolve_anchor,
)

_VERSION = ModelVersion.parse("1.0.0")
_SHA = "a1b2c3d4"


def _begin(name: str, sha: str = _SHA, fmt: RegionFormat = RegionFormat.HTML) -> str:
    return render_begin(fmt, name, _VERSION, sha)


def _end(name: str, fmt: RegionFormat = RegionFormat.HTML) -> str:
    return render_end(fmt, name)


def _doc(*lines: str, newline: str = "\n") -> str:
    return "".join(f"{line}{newline}" for line in lines)


def _slice(text: str, span: tuple[int, int]) -> str:
    """Read a span back out of the text's UTF-8 bytes -- the exact
    operation S-8.3's substitution performs."""
    start, end = span
    return text.encode("utf-8")[start:end].decode("utf-8")


# --- RegionParseError shape ------------------------------------------------


def test_region_parse_error_is_a_pyforge_error_and_a_value_error():
    assert issubclass(RegionParseError, PyforgeError)
    assert issubclass(RegionParseError, ValueError)


def test_region_parse_error_is_not_a_marker_error():
    """Structure violations and line-grammar violations stay separately
    catchable -- neither type is a subclass of the other."""
    assert not issubclass(RegionParseError, MarkerError)
    assert not issubclass(MarkerError, RegionParseError)


# --- no regions ------------------------------------------------------------


@pytest.mark.parametrize("fmt", [RegionFormat.HTML, RegionFormat.HASH])
def test_empty_text_returns_no_regions(fmt):
    assert parse_regions("", fmt) == ()


@pytest.mark.parametrize("fmt", [RegionFormat.HTML, RegionFormat.HASH])
def test_text_without_markers_returns_no_regions(fmt):
    text = _doc("# A heading", "", "Some ordinary prose.", "<!-- a plain comment -->")
    assert parse_regions(text, fmt) == ()


# --- one clean region ------------------------------------------------------


def test_one_clean_region_reports_name_model_version_and_declared_sha():
    body = "line1\n"
    sha = region_sha(body)
    text = _doc("intro", _begin("tiers", sha), "line1", _end("tiers"), "outro")

    (span,) = parse_regions(text, RegionFormat.HTML)

    assert isinstance(span, RegionSpan)
    assert span.name == "tiers"
    assert span.model_version == _VERSION
    assert span.sha == sha


def test_one_clean_region_spans_address_the_exact_marker_and_body_bytes():
    text = _doc("intro", _begin("tiers"), "line1", _end("tiers"), "outro")

    (span,) = parse_regions(text, RegionFormat.HTML)

    assert _slice(text, span.begin_span) == _begin("tiers")
    assert _slice(text, span.end_span) == _end("tiers")
    assert _slice(text, span.body_span) == "line1\n"


def test_body_span_is_the_substitution_contract():
    """The Design Notes' own reconstruction identity, which S-8.3 depends
    on: replacing exactly ``body_span`` leaves both marker lines and all
    surrounding content untouched."""
    text = _doc("intro", _begin("tiers"), "old body", _end("tiers"), "outro")
    raw = text.encode("utf-8")

    (span,) = parse_regions(text, RegionFormat.HTML)
    rebuilt = raw[: span.body_span[0]] + b"new body\n" + raw[span.body_span[1] :]

    assert rebuilt.decode("utf-8") == _doc("intro", _begin("tiers"), "new body", _end("tiers"), "outro")


def test_marker_spans_exclude_their_own_line_terminator():
    text = _doc(_begin("tiers"), "line1", _end("tiers"))

    (span,) = parse_regions(text, RegionFormat.HTML)

    assert "\n" not in _slice(text, span.begin_span)
    assert "\n" not in _slice(text, span.end_span)
    # ...and the body picks up exactly where the begin line's terminator ends.
    assert span.body_span[0] == span.begin_span[1] + len("\n")
    assert span.body_span[1] == span.end_span[0]


def test_final_line_without_a_trailing_newline_still_parses():
    text = _doc(_begin("tiers"), "line1") + _end("tiers")

    (span,) = parse_regions(text, RegionFormat.HTML)

    assert _slice(text, span.end_span) == _end("tiers")
    assert _slice(text, span.body_span) == "line1\n"


def test_hash_format_regions_parse_with_the_hash_comment_style():
    text = _doc(
        "# a plain comment",
        _begin("tiers", fmt=RegionFormat.HASH),
        "key = 1",
        _end("tiers", fmt=RegionFormat.HASH),
    )

    (span,) = parse_regions(text, RegionFormat.HASH)

    assert span.name == "tiers"
    assert _slice(text, span.body_span) == "key = 1\n"


# --- two sibling regions ---------------------------------------------------


def test_two_sibling_regions_are_returned_in_file_order():
    text = _doc(
        _begin("b-region"),
        "first body",
        _end("b-region"),
        "between",
        _begin("a-region"),
        "second body",
        _end("a-region"),
    )

    first, second = parse_regions(text, RegionFormat.HTML)

    # File order, NOT name order -- `b-region` opens first.
    assert (first.name, second.name) == ("b-region", "a-region")
    assert _slice(text, first.body_span) == "first body\n"
    assert _slice(text, second.body_span) == "second body\n"
    assert first.end_span[1] < second.begin_span[0]


# --- nesting / overlap -----------------------------------------------------


def test_nested_regions_raise_naming_both():
    text = _doc(_begin("a"), _begin("b"), "body", _end("b"), _end("a"))

    with pytest.raises(RegionParseError, match=r"region 'b' begins while region 'a'"):
        parse_regions(text, RegionFormat.HTML)


def test_overlapping_regions_raise_naming_both():
    """The interleaved shape is rejected by the SAME single check as the
    properly-nested one -- no stack, no lookahead."""
    text = _doc(_begin("a"), _begin("b"), "body", _end("a"), _end("b"))

    with pytest.raises(RegionParseError, match=r"region 'b' begins while region 'a'"):
        parse_regions(text, RegionFormat.HTML)


def test_a_region_reopening_itself_is_rejected_as_nesting():
    text = _doc(_begin("a"), _begin("a"), _end("a"))

    with pytest.raises(RegionParseError, match=r"region 'a' begins while region 'a'"):
        parse_regions(text, RegionFormat.HTML)


# --- unterminated begin ----------------------------------------------------


def test_unterminated_begin_raises_naming_the_region():
    text = _doc("intro", _begin("a"), "body", "more body")

    with pytest.raises(RegionParseError, match=r"'a' begins at line 2.*never closed"):
        parse_regions(text, RegionFormat.HTML)


def test_unterminated_begin_is_reported_even_after_an_earlier_clean_region():
    text = _doc(_begin("a"), "body", _end("a"), _begin("b"), "body")

    with pytest.raises(RegionParseError, match=r"'b' begins at line 4.*never closed"):
        parse_regions(text, RegionFormat.HTML)


# --- duplicate region name -------------------------------------------------


def test_duplicate_region_name_raises_naming_the_duplicate():
    text = _doc(_begin("a"), "first", _end("a"), _begin("a"), "second", _end("a"))

    with pytest.raises(RegionParseError, match=r"duplicate region 'a'"):
        parse_regions(text, RegionFormat.HTML)


# --- mismatched / stray end ------------------------------------------------


def test_end_marker_for_another_region_raises_naming_both():
    text = _doc(_begin("a"), "body", _end("b"))

    with pytest.raises(RegionParseError, match=r"region 'b' does not match the open region 'a'"):
        parse_regions(text, RegionFormat.HTML)


def test_stray_end_with_nothing_open_raises():
    text = _doc("intro", _end("a"))

    with pytest.raises(RegionParseError, match=r"region 'a' with no region open"):
        parse_regions(text, RegionFormat.HTML)


def test_second_end_after_a_closed_region_raises():
    text = _doc(_begin("a"), "body", _end("a"), _end("a"))

    with pytest.raises(RegionParseError, match=r"no region open"):
        parse_regions(text, RegionFormat.HTML)


# --- fence awareness (html only) -------------------------------------------


def test_marker_inside_a_backtick_fence_is_ignored():
    text = _doc("intro", "```markdown", _begin("a"), "body", _end("a"), "```", "outro")

    assert parse_regions(text, RegionFormat.HTML) == ()


def test_marker_inside_a_tilde_fence_is_ignored():
    text = _doc("~~~", _begin("a"), _end("a"), "~~~")

    assert parse_regions(text, RegionFormat.HTML) == ()


def test_malformed_marker_inside_a_fence_never_reaches_the_grammar():
    """Proof that a fenced line is never handed to ``parse_marker_line`` at
    all: a line that WOULD be a ``MarkerError`` outside the fence is inert
    inside it."""
    text = _doc("```", "<!-- marshal-seed:begin region=a -->", "```")

    assert parse_regions(text, RegionFormat.HTML) == ()


def test_a_fenced_end_marker_cannot_close_a_real_region():
    """The AR-1 case the fence rule exists for: a managed region whose body
    DOCUMENTS the marker grammar must still be closed only by its real end
    marker."""
    text = _doc(
        _begin("a"),
        "Regions are delimited like this:",
        "```",
        _end("a"),
        "```",
        _end("a"),
    )

    (span,) = parse_regions(text, RegionFormat.HTML)

    assert span.name == "a"
    assert _slice(text, span.body_span) == _doc("Regions are delimited like this:", "```", _end("a"), "```")


def test_a_real_region_after_a_closed_fence_still_parses():
    text = _doc("```", _begin("a"), "```", _begin("b"), "body", _end("b"))

    (span,) = parse_regions(text, RegionFormat.HTML)

    assert span.name == "b"


def test_a_shorter_or_different_run_does_not_close_a_fence():
    text = _doc(
        "~~~~",
        "```",  # different fence character -- does not close
        "~~~",  # same character, shorter run -- does not close
        _begin("a"),
        _end("a"),
        "~~~~~",  # same character, run >= the opener's -- closes
        _begin("b"),
        "body",
        _end("b"),
    )

    (span,) = parse_regions(text, RegionFormat.HTML)

    assert span.name == "b"


def test_up_to_three_leading_spaces_still_opens_a_fence():
    text = _doc("   ```", _begin("a"), _end("a"), "   ```")

    assert parse_regions(text, RegionFormat.HTML) == ()


def test_four_leading_spaces_is_not_a_fence():
    """Four spaces is an indented code block, not a fence -- treating it as
    one would silently swallow every marker after it."""
    text = _doc("    ```", _begin("a"), "body", _end("a"), "    ```")

    (span,) = parse_regions(text, RegionFormat.HTML)

    assert span.name == "a"


def test_a_closer_with_trailing_content_does_not_close_the_fence():
    """CommonMark: a closing fence may be followed only by whitespace. A
    line like `` ``` extra `` is still open -- the AR-1 case in the
    opposite direction from a marker-inside-a-fence: without this check, a
    closer with trailing content would end the fence early and expose real
    marker text (still logically inside it) to the live parser."""
    text = _doc("```", "``` still open", _begin("a"), _end("a"), "```")

    assert parse_regions(text, RegionFormat.HTML) == ()


def test_an_unclosed_fence_at_eof_raises_rather_than_silently_dropping_regions():
    """Fenced content is never scanned for markers, so an unclosed fence
    would otherwise silently swallow every region after it -- indistinguish-
    able from "this file legitimately has zero managed regions"."""
    text = _doc("intro", "```", _begin("a"), "body", _end("a"))

    with pytest.raises(RegionParseError, match=r"line 2:.*fenced code block is never closed"):
        parse_regions(text, RegionFormat.HTML)


def test_an_unclosed_fence_at_eof_also_names_an_unrelated_still_open_region():
    """Review finding: a region opened and never closed BEFORE the fence
    ever appears is a genuinely separate problem from the fence itself --
    the fence-priority error must still name it, not silently drop it."""
    text = _doc(_begin("a"), "body", "```")

    with pytest.raises(
        RegionParseError,
        match=r"fenced code block is never closed before end of text \(region 'a', begun at"
        r" line 1, is also still open\)",
    ):
        parse_regions(text, RegionFormat.HTML)


def test_an_unclosed_fence_at_eof_with_no_open_region_names_only_the_fence():
    text = _doc("intro", "```")

    with pytest.raises(RegionParseError, match=r"fenced code block is never closed"):
        try:
            parse_regions(text, RegionFormat.HTML)
        except RegionParseError as exc:
            assert "is also still open" not in str(exc)
            raise


def test_two_fences_in_one_file_reports_the_second_openers_line():
    """The first fence closes cleanly; only the second, later fence is
    left open -- `fence_lineno` must reflect the SECOND opening, not stale
    state left over from the first."""
    text = _doc("```", "```", "intro", "~~~", "unclosed")

    with pytest.raises(RegionParseError, match=r"line 4:.*fenced code block is never closed"):
        parse_regions(text, RegionFormat.HTML)


def test_fence_awareness_is_html_only():
    """A ``hash``-format artifact (``.toml``/``.yml``/shell) has no fenced
    code blocks -- a backtick banner line there must never make real markers
    inert."""
    text = _doc(
        "```",
        _begin("a", fmt=RegionFormat.HASH),
        "body",
        _end("a", fmt=RegionFormat.HASH),
        "```",
    )

    (span,) = parse_regions(text, RegionFormat.HASH)

    assert span.name == "a"


# --- CRLF / LF parity ------------------------------------------------------


def test_crlf_and_lf_agree_on_names_versions_and_shas():
    lf_text = _doc("intro", _begin("tiers"), "line1", _end("tiers"), "outro")
    crlf_text = _doc("intro", _begin("tiers"), "line1", _end("tiers"), "outro", newline="\r\n")

    (lf_span,) = parse_regions(lf_text, RegionFormat.HTML)
    (crlf_span,) = parse_regions(crlf_text, RegionFormat.HTML)

    assert (lf_span.name, lf_span.model_version, lf_span.sha) == (
        crlf_span.name,
        crlf_span.model_version,
        crlf_span.sha,
    )


def test_crlf_spans_address_the_crlf_bytes():
    """Byte offsets are measured against the ORIGINAL bytes, so a CRLF
    file's spans differ from the LF file's by one byte per preceding line --
    and still slice out exactly the right content."""
    crlf_text = _doc("intro", _begin("tiers"), "line1", _end("tiers"), "outro", newline="\r\n")

    (span,) = parse_regions(crlf_text, RegionFormat.HTML)

    assert _slice(crlf_text, span.begin_span) == _begin("tiers")
    assert _slice(crlf_text, span.end_span) == _end("tiers")
    assert _slice(crlf_text, span.body_span) == "line1\r\n"


def test_mixed_line_endings_in_one_document_still_parse_correctly():
    """A file edited across platforms may mix line-ending styles -- unlike
    the uniform-CRLF/uniform-LF cases above, this proves per-line byte
    accounting (each line's own terminator length, not a document-wide
    assumption) is what actually makes offsets correct."""
    text = f"intro\r\n{_begin('tiers')}\nline1\r\n{_end('tiers')}\noutro\r\n"

    (span,) = parse_regions(text, RegionFormat.HTML)

    assert _slice(text, span.begin_span) == _begin("tiers")
    assert _slice(text, span.end_span) == _end("tiers")
    assert _slice(text, span.body_span) == "line1\r\n"


# --- fmt validated even on text with nothing to scan ------------------------


def test_slashstar_propagates_not_implemented_even_for_empty_text():
    """Without an eager probe, the scan loop never reaches
    ``parse_marker_line`` at all on empty text, so a reserved ``fmt`` would
    silently report zero regions instead of refusing outright."""
    with pytest.raises(NotImplementedError):
        parse_regions("", RegionFormat.SLASHSTAR)


def test_unregistered_fmt_propagates_marker_error_even_for_empty_text():
    with pytest.raises(MarkerError):
        parse_regions("", "xml")  # pyright: ignore[reportArgumentType]


# --- byte offsets over multi-byte UTF-8 ------------------------------------


def test_body_span_is_byte_offsets_not_character_offsets():
    """The proof that these are BYTE offsets (P-06): with multi-byte content
    both before and inside the region, a character-offset span would slice
    out mangled text (or raise on a split code point)."""
    preamble = "héllo — ünicode ✓ prelude"
    body = "naïve café — ✓\nsecond ligne\n"
    text = _doc(preamble, _begin("a"), *body.splitlines(), _end("a"))

    (span,) = parse_regions(text, RegionFormat.HTML)

    character_offset = text.index(body)
    assert _slice(text, span.body_span) == body
    assert span.body_span[0] == len(text[:character_offset].encode("utf-8"))
    assert span.body_span[0] > character_offset  # ...i.e. NOT the character offset
    assert span.body_span[1] - span.body_span[0] == len(body.encode("utf-8"))


# --- zero-length body ------------------------------------------------------


def test_adjacent_markers_yield_an_empty_body_span():
    text = _doc("intro", _begin("a", region_sha("")), _end("a"), "outro")

    (span,) = parse_regions(text, RegionFormat.HTML)

    assert span.body_span[0] == span.body_span[1]
    assert _slice(text, span.body_span) == ""
    assert span.body_span[0] == span.end_span[0]


# --- line-grammar violations propagate unchanged ---------------------------


def test_malformed_marker_line_propagates_marker_error():
    text = _doc(
        "intro",
        "<!-- marshal-seed:begin region=a model-version=1.0.0 sha=zzzzzzzz -->",
        "body",
    )

    with pytest.raises(MarkerError):
        parse_regions(text, RegionFormat.HTML)


def test_unparseable_model_version_propagates_marker_error():
    text = _doc("<!-- marshal-seed:begin region=a model-version=nope sha=a1b2c3d4 -->")

    with pytest.raises(MarkerError):
        parse_regions(text, RegionFormat.HTML)


def test_slashstar_format_propagates_not_implemented():
    """S-8.1 already refuses the reserved format; this module neither
    catches nor special-cases that."""
    with pytest.raises(NotImplementedError):
        parse_regions(_doc("/* marshal-seed:end region=a */"), RegionFormat.SLASHSTAR)


# --- resolve_anchor (Story 8.4) ----------------------------------------------


def test_first_anchor_matches_resolves_immediately_after_its_line():
    text = _doc("intro", "## The tiers", "rest of the section", "outro")

    resolution = resolve_anchor(text, RegionFormat.HTML, ("## The tiers",))

    assert isinstance(resolution, AnchorResolution)
    assert resolution.matched == "## The tiers"
    # offset is the matched line's own line_end -- right after "## The
    # tiers\n", i.e. where "rest of the section" begins.
    assert text.encode("utf-8")[resolution.offset :].startswith(b"rest of the section")


def test_anchor_order_is_a_preference_not_a_file_position_search():
    """AD-56's own example: an earlier, absent anchor is ignored entirely --
    a LATER anchor in the list, even one further down in the file, still
    wins over a guaranteed-fallback anchor listed after it."""
    text = _doc("intro", "# CLAUDE.md", "more content")

    resolution = resolve_anchor(text, RegionFormat.HTML, ("## The tiers", "# CLAUDE.md", "<top>"))

    assert resolution.matched == "# CLAUDE.md"
    assert text.encode("utf-8")[resolution.offset :].startswith(b"more content")


def test_top_wins_only_when_every_earlier_anchor_is_absent():
    """The other half of the same AD-56 example: with NEITHER preferred
    anchor present, `<top>` (listed last) is the one that resolves."""
    text = _doc("intro", "unrelated content")

    resolution = resolve_anchor(text, RegionFormat.HTML, ("## The tiers", "# CLAUDE.md", "<top>"))

    assert resolution.matched == "<top>"
    assert resolution.offset == 0


def test_no_anchor_matches_and_no_top_appends_at_eof():
    text = _doc("intro", "some content", "more content")

    resolution = resolve_anchor(text, RegionFormat.HTML, ("## Nope", "### Also nope"))

    assert resolution.matched is None
    assert resolution.offset == len(text.encode("utf-8"))


def test_empty_anchor_tuple_also_falls_back_to_eof():
    text = _doc("intro")

    resolution = resolve_anchor(text, RegionFormat.HTML, ())

    assert resolution.matched is None
    assert resolution.offset == len(text.encode("utf-8"))


def test_top_with_frontmatter_resolves_immediately_after_the_closing_delimiter():
    text = _doc("---", "title: x", "---", "# Heading", "body")

    resolution = resolve_anchor(text, RegionFormat.HTML, ("<top>",))

    assert resolution.matched == "<top>"
    assert text.encode("utf-8")[resolution.offset :].startswith(b"# Heading")


def test_top_without_frontmatter_resolves_to_byte_zero():
    text = _doc("# Heading", "body")

    resolution = resolve_anchor(text, RegionFormat.HTML, ("<top>",))

    assert resolution.matched == "<top>"
    assert resolution.offset == 0


def test_top_with_an_unclosed_frontmatter_delimiter_falls_back_to_byte_zero():
    """No closing `---` before end of text -- per `core/spec_surface.py`'s
    own established convention, this is "no such block", not a malformed
    one; `<top>` still resolves, to byte 0."""
    text = _doc("---", "title: x", "no closing delimiter")

    resolution = resolve_anchor(text, RegionFormat.HTML, ("<top>",))

    assert resolution.matched == "<top>"
    assert resolution.offset == 0


def test_top_frontmatter_delimiter_may_be_far_from_the_second_line():
    """Mirrors `parse_declared_surface`'s own "next line THAT IS ---" (not
    literally line 2) convention -- multiple non-`---` frontmatter lines
    still close correctly at the first line that is exactly `---`."""
    text = _doc("---", "title: x", "tags: [a, b]", "extra: field", "---", "content")

    resolution = resolve_anchor(text, RegionFormat.HTML, ("<top>",))

    assert text.encode("utf-8")[resolution.offset :].startswith(b"content")


def test_anchor_text_only_inside_a_fence_is_skipped_and_falls_through():
    """The one line starting with the anchor text sits inside a fenced
    block (html fmt) -- fence-shadowed, so resolution falls through to the
    next anchor (here, the EOF fallback)."""
    text = _doc(
        "intro",
        "```markdown",
        "## The tiers",
        "```",
        "outro",
    )

    resolution = resolve_anchor(text, RegionFormat.HTML, ("## The tiers",))

    assert resolution.matched is None
    assert resolution.offset == len(text.encode("utf-8"))


def test_anchor_text_inside_a_fence_falls_through_to_a_later_real_match():
    text = _doc(
        "```markdown",
        "## The tiers",
        "```",
        "## The tiers",
        "real content",
    )

    resolution = resolve_anchor(text, RegionFormat.HTML, ("## The tiers",))

    assert resolution.matched == "## The tiers"
    assert text.encode("utf-8")[resolution.offset :].startswith(b"real content")


def test_fence_awareness_for_anchor_resolution_is_html_only():
    """A `hash`-format artifact has no fenced-code-block concept -- a
    backtick banner line there must never make a real anchor line inert."""
    text = _doc("```", "## The tiers", "rest")

    resolution = resolve_anchor(text, RegionFormat.HASH, ("## The tiers",))

    assert resolution.matched == "## The tiers"
    assert text.encode("utf-8")[resolution.offset :].startswith(b"rest")


def test_first_matching_line_in_file_order_wins_when_an_anchor_recurs():
    text = _doc("## The tiers", "first", "## The tiers", "second")

    resolution = resolve_anchor(text, RegionFormat.HTML, ("## The tiers",))

    assert text.encode("utf-8")[resolution.offset :].startswith(b"first")


def test_anchor_resolution_is_frozen():
    resolution = AnchorResolution(offset=0, matched=None)
    with pytest.raises(AttributeError):
        resolution.offset = 5  # pyright: ignore[reportAttributeAccessIssue]


def test_resolve_anchor_raises_on_an_unterminated_fence_symmetric_with_parse_regions():
    """Review finding: without this, an unterminated fence silently made
    every remaining line -- including any real anchor after it --
    unmatchable with no error at all, unlike `parse_regions`'s own hard
    error for the identical condition."""
    text = _doc("intro", "```markdown", "## The tiers", "no closing fence")

    with pytest.raises(RegionParseError, match="never closed"):
        resolve_anchor(text, RegionFormat.HTML, ("## The tiers",))


def test_resolve_anchor_raises_not_implemented_for_slashstar_symmetric_with_parse_regions():
    """Review finding: `parse_regions` raises `NotImplementedError` for the
    reserved `slashstar` format via an eager `parse_marker_line(fmt, "")`
    call even on marker-free text (see that function's own docstring);
    `resolve_anchor` had no equivalent call, so it silently ran ordinary,
    non-fence-aware matching for `slashstar` instead of raising -- masked
    in `insert_region` only because it always calls `parse_regions` first,
    which already raises for this same `fmt`, but this function is
    independently public."""
    text = _doc("## The tiers", "rest")

    with pytest.raises(NotImplementedError):
        resolve_anchor(text, RegionFormat.SLASHSTAR, ("## The tiers",))
