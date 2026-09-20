"""Unit tests for ``pyforge.marshal.seed.detect.hashes`` (Story 9.3) --
covers the spec's I/O & Edge-Case Matrix: file/region hash match and
mismatch, the ``recorded_sha is None`` "adopted out-of-band" case for both,
CRLF/LF hash parity (no false positive), region hashing unaffected by
content outside the region, an empty region body, and multi-byte UTF-8 in a
region body -- plus ``normalize_line_endings``/``hash_content`` unit
coverage and the design-notes cross-check against
``regions.markers.region_sha``'s own output shape.

Region-bearing tests build real ``RegionSpan``s via ``regions.parse.
parse_regions`` rather than hand-constructing one, mirroring
``test_seed_regions_parse.py``'s own ``_begin``/``_end``/``_doc`` helpers
and its multi-byte-UTF-8 body technique.
"""

from __future__ import annotations

from pyforge.marshal.seed.detect.findings import Finding, FindingType, Severity
from pyforge.marshal.seed.detect.hashes import (
    check_managed_file,
    check_managed_region,
    hash_content,
    normalize_line_endings,
    region_body_text,
)
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.regions.markers import (
    RegionFormat,
    region_sha,
    render_begin,
    render_end,
)
from pyforge.marshal.seed.regions.parse import parse_regions

_VERSION = ModelVersion.parse("1.0.0")
_SHA = "a1b2c3d4"


def _begin(name: str, sha: str = _SHA, fmt: RegionFormat = RegionFormat.HTML) -> str:
    return render_begin(fmt, name, _VERSION, sha)


def _end(name: str, fmt: RegionFormat = RegionFormat.HTML) -> str:
    return render_end(fmt, name)


def _doc(*lines: str, newline: str = "\n") -> str:
    return "".join(f"{line}{newline}" for line in lines)


# --- normalize_line_endings -------------------------------------------------


def test_normalize_line_endings_collapses_crlf_to_lf():
    assert normalize_line_endings("a\r\nb\r\n") == "a\nb\n"


def test_normalize_line_endings_collapses_lone_cr_to_lf():
    assert normalize_line_endings("a\rb\r") == "a\nb\n"


def test_normalize_line_endings_leaves_lf_unchanged():
    assert normalize_line_endings("a\nb\n") == "a\nb\n"


def test_normalize_line_endings_handles_mixed_terminators_in_one_document():
    assert normalize_line_endings("a\r\nb\rc\n") == "a\nb\nc\n"


def test_normalize_line_endings_of_empty_string_is_empty_string():
    assert normalize_line_endings("") == ""


# --- hash_content ------------------------------------------------------------


def test_hash_content_is_8_lowercase_hex_characters():
    result = hash_content("hello world\n")
    assert len(result) == 8
    assert result == result.lower()
    assert all(char in "0123456789abcdef" for char in result)


def test_hash_content_matches_region_shas_own_output_shape_over_normalized_text():
    """The design notes' own cross-check: ``hash_content`` is
    ``region_sha`` applied to already-normalized text, never a differently-
    shaped algorithm (the spec's own "no re-implementation at a different
    truncation length or digest" Never bullet). Covers both normalized
    terminators ``hash_content`` collapses: CRLF and a lone CR."""
    crlf_text = "some content\r\n"
    assert hash_content(crlf_text) == region_sha(normalize_line_endings(crlf_text))
    cr_text = "some content\rmore\r"
    assert hash_content(cr_text) == region_sha(normalize_line_endings(cr_text))


def test_hash_content_differs_for_different_content():
    assert hash_content("a\n") != hash_content("b\n")


def test_hash_content_is_deterministic():
    assert hash_content("same\n") == hash_content("same\n")


def test_hash_content_of_empty_string_does_not_crash():
    result = hash_content("")
    assert len(result) == 8


def test_hash_content_agrees_for_crlf_and_lf_checkouts_of_identical_content():
    """I/O Matrix: CRLF checkout, same content -- no false positive at the
    hash-function level, beneath ``check_managed_file``'s own version of
    this same row below."""
    lf_text = "line one\nline two\n"
    crlf_text = "line one\r\nline two\r\n"
    assert hash_content(lf_text) == hash_content(crlf_text)


# --- region_body_text ---------------------------------------------------------


def test_region_body_text_extracts_exactly_the_body_span():
    text = _doc("intro", _begin("tiers"), "line1", _end("tiers"), "outro")
    (span,) = parse_regions(text, RegionFormat.HTML)

    assert region_body_text(text, span) == "line1\n"


def test_region_body_text_handles_multi_byte_utf8_near_marker_boundaries():
    """I/O Matrix: multi-byte UTF-8 in body -- both the preamble (before the
    region) and the body itself carry non-ASCII content near the marker
    boundaries, mirroring ``test_seed_regions_parse.py``'s own byte-offset
    proof technique."""
    preamble = "héllo — ünicode ✓ prelude"
    body = "naïve café — ✓\nsecond ligne\n"
    text = _doc(preamble, _begin("a"), *body.splitlines(), _end("a"))
    (span,) = parse_regions(text, RegionFormat.HTML)

    assert region_body_text(text, span) == body


def test_region_body_text_of_an_empty_body_is_the_empty_string():
    """I/O Matrix: empty region body (adjacent markers) -- hashes the empty
    string deterministically, no crash."""
    text = _doc("intro", _begin("a", region_sha("")), _end("a"), "outro")
    (span,) = parse_regions(text, RegionFormat.HTML)

    assert span.body_span[0] == span.body_span[1]
    assert region_body_text(text, span) == ""


# --- check_managed_file -------------------------------------------------------


def test_check_managed_file_returns_none_when_hash_matches():
    text = "hello\n"
    recorded = hash_content(text)

    assert check_managed_file("AGENTS.md", text, recorded) is None


def test_check_managed_file_returns_hard_finding_on_mismatch():
    finding = check_managed_file("AGENTS.md", "current content\n", "deadbeef")

    assert isinstance(finding, Finding)
    assert finding.severity is Severity.HARD
    assert finding.type is FindingType.MANAGED_FILE_MODIFIED
    assert finding.path == "AGENTS.md"


def test_check_managed_file_returns_hard_finding_when_recorded_sha_is_none():
    """I/O Matrix: file adopted out-of-band -- ``recorded_sha=None``, file
    present, is a HARD finding, never a silent pass-through."""
    finding = check_managed_file("AGENTS.md", "current content\n", None)

    assert finding is not None
    assert finding.severity is Severity.HARD
    assert finding.type is FindingType.MANAGED_FILE_MODIFIED
    assert finding.path == "AGENTS.md"


def test_check_managed_file_on_empty_content_does_not_crash():
    """End-to-end counterpart of ``test_hash_content_of_empty_string_does_not_crash``
    -- a managed file legitimately reduced to zero bytes still round-trips
    through the public comparison function, not just the bare hash helper."""
    recorded = hash_content("")

    assert check_managed_file("EMPTY.md", "", recorded) is None


def test_check_managed_file_no_false_positive_across_a_crlf_checkout():
    """I/O Matrix: CRLF checkout, same content -- ``recorded_sha`` computed
    from the LF-authored original still matches the CRLF checkout."""
    lf_text = "line one\nline two\n"
    crlf_text = "line one\r\nline two\r\n"
    recorded = hash_content(lf_text)

    assert check_managed_file("AGENTS.md", crlf_text, recorded) is None


# --- check_managed_region ------------------------------------------------------


def test_check_managed_region_returns_none_when_hash_matches():
    text = _doc("intro", _begin("tiers"), "line1", _end("tiers"), "outro")
    (span,) = parse_regions(text, RegionFormat.HTML)
    recorded = hash_content(region_body_text(text, span))

    assert check_managed_region("AGENTS.md", text, span, recorded) is None


def test_check_managed_region_returns_hard_finding_on_mismatch():
    text = _doc("intro", _begin("tiers"), "line1", _end("tiers"), "outro")
    (span,) = parse_regions(text, RegionFormat.HTML)

    finding = check_managed_region("AGENTS.md", text, span, "deadbeef")

    assert isinstance(finding, Finding)
    assert finding.severity is Severity.HARD
    assert finding.type is FindingType.MANAGED_REGION_MODIFIED
    assert finding.path == "AGENTS.md"
    # Names the region too (the AC's "naming the artifact's path and region
    # name, for the region case"), even though `Finding.path` itself only
    # ever carries the bare artifact path.
    assert finding.message.startswith("AGENTS.md#tiers: ")


def test_check_managed_region_returns_hard_finding_when_recorded_sha_is_none():
    """I/O Matrix: region adopted out-of-band -- ``recorded_sha=None``,
    region present, is a HARD finding."""
    text = _doc("intro", _begin("tiers"), "line1", _end("tiers"), "outro")
    (span,) = parse_regions(text, RegionFormat.HTML)

    finding = check_managed_region("AGENTS.md", text, span, None)

    assert finding is not None
    assert finding.severity is Severity.HARD
    assert finding.type is FindingType.MANAGED_REGION_MODIFIED


def test_check_managed_region_is_unaffected_by_content_outside_the_region():
    """I/O Matrix: content outside the region changed, body unchanged --
    ``check_managed_region`` still returns ``None`` (body-only hashing)."""
    body_line = "line1"
    text_before = _doc("intro v1", _begin("tiers"), body_line, _end("tiers"), "outro v1")
    text_after = _doc("intro v2, heavily edited", _begin("tiers"), body_line, _end("tiers"), "outro v2, edited")
    (span_before,) = parse_regions(text_before, RegionFormat.HTML)
    (span_after,) = parse_regions(text_after, RegionFormat.HTML)
    recorded = hash_content(region_body_text(text_before, span_before))

    assert check_managed_region("AGENTS.md", text_after, span_after, recorded) is None


def test_check_managed_region_on_an_empty_body_does_not_crash():
    text = _doc("intro", _begin("a", region_sha("")), _end("a"), "outro")
    (span,) = parse_regions(text, RegionFormat.HTML)
    recorded = hash_content("")

    assert check_managed_region("a.md", text, span, recorded) is None


def test_check_managed_region_handles_multi_byte_utf8_in_body():
    preamble = "héllo — ünicode ✓ prelude"
    body = "naïve café — ✓\nsecond ligne\n"
    text = _doc(preamble, _begin("a"), *body.splitlines(), _end("a"))
    (span,) = parse_regions(text, RegionFormat.HTML)
    recorded = hash_content(body)

    assert check_managed_region("doc.md", text, span, recorded) is None
