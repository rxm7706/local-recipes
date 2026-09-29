"""Unit tests for ``pyforge.marshal.seed.regions.markers`` (Story 8.1) --
covers the spec's I/O & Edge-Case Matrix: per-format rendering, the
html/hash round trip, ``slashstar``'s ``NotImplementedError`` on both
render and parse, name/sha validation errors, the body-only sha proof, and
``parse_marker_line``'s ``None``-for-ordinary-line contract.
"""

from __future__ import annotations

import re

import pytest
from pyforge.core.errors import PyforgeError

from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.regions.markers import (
    REGION_NAME_PATTERN,
    BeginMarker,
    EndMarker,
    MarkerError,
    RegionFormat,
    parse_marker_line,
    region_sha,
    render_begin,
    render_end,
)

# --- MarkerError shape --------------------------------------------------


def test_marker_error_is_a_pyforge_error_and_a_value_error():
    assert issubclass(MarkerError, PyforgeError)
    assert issubclass(MarkerError, ValueError)


# --- rendering: per-format comment style, never sniffed -----------------


def test_render_html_begin_matches_the_exact_grammar():
    line = render_begin(RegionFormat.HTML, "tiers", ModelVersion(1, 0, 0), "a1b2c3d4")
    assert line == "<!-- marshal-seed:begin region=tiers model-version=1.0.0 sha=a1b2c3d4 -->"


def test_render_html_end_matches_the_exact_grammar():
    line = render_end(RegionFormat.HTML, "tiers")
    assert line == "<!-- marshal-seed:end region=tiers -->"


def test_render_hash_begin_matches_the_exact_grammar_with_no_close_token():
    line = render_begin(RegionFormat.HASH, "tiers", ModelVersion(1, 0, 0), "a1b2c3d4")
    assert line == "# marshal-seed:begin region=tiers model-version=1.0.0 sha=a1b2c3d4"


def test_render_hash_end_matches_the_exact_grammar_with_no_close_token():
    line = render_end(RegionFormat.HASH, "tiers")
    assert line == "# marshal-seed:end region=tiers"


def test_render_uses_only_the_declared_format_not_content_or_extension():
    """AD-53's own Always bullet: the comment style comes from the
    registry entry the caller names, never from sniffing anything else --
    there is no file/extension argument to either renderer at all."""
    html_line = render_begin(RegionFormat.HTML, "tiers", ModelVersion(1, 0, 0), "a1b2c3d4")
    hash_line = render_begin(RegionFormat.HASH, "tiers", ModelVersion(1, 0, 0), "a1b2c3d4")
    assert html_line != hash_line
    assert html_line.startswith("<!--")
    assert hash_line.startswith("#")


# --- round trip: render -> parse -> render is byte-identical -------------


@pytest.mark.parametrize("fmt", [RegionFormat.HTML, RegionFormat.HASH])
def test_begin_round_trip_is_byte_identical(fmt):
    body = "some region body\nwith more than one line\n"
    begin = render_begin(fmt, "tiers", ModelVersion.parse("1.0.0"), region_sha(body))
    parsed = parse_marker_line(fmt, begin)
    assert isinstance(parsed, BeginMarker)
    assert render_begin(fmt, parsed.region, parsed.model_version, parsed.sha) == begin


@pytest.mark.parametrize("fmt", [RegionFormat.HTML, RegionFormat.HASH])
def test_end_round_trip_is_byte_identical(fmt):
    end = render_end(fmt, "tiers")
    parsed = parse_marker_line(fmt, end)
    assert isinstance(parsed, EndMarker)
    assert render_end(fmt, parsed.region) == end


def test_round_trip_preserves_field_values():
    begin = render_begin(RegionFormat.HTML, "dream-first-workflow", ModelVersion.parse("2.3.4-rc.1"), "deadbeef")
    parsed = parse_marker_line(RegionFormat.HTML, begin)
    assert isinstance(parsed, BeginMarker)
    assert parsed.region == "dream-first-workflow"
    assert parsed.model_version == ModelVersion.parse("2.3.4-rc.1")
    assert parsed.sha == "deadbeef"


# --- slashstar: registered enum member, unimplemented render/parse -------


def test_slashstar_is_a_registered_region_format_member():
    assert RegionFormat.SLASHSTAR == "slashstar"
    assert RegionFormat.SLASHSTAR in RegionFormat


def test_render_begin_slashstar_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        render_begin(RegionFormat.SLASHSTAR, "tiers", ModelVersion(1, 0, 0), "a1b2c3d4")


def test_render_end_slashstar_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        render_end(RegionFormat.SLASHSTAR, "tiers")


def test_parse_marker_line_slashstar_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        parse_marker_line(
            RegionFormat.SLASHSTAR, "/* marshal-seed:begin region=tiers model-version=1.0.0 sha=a1b2c3d4 */"
        )


def test_slashstar_produces_no_marker_text_on_render_failure():
    """ "no marker text is produced" -- the exception fires before any
    string is returned; there is nothing for a caller to accidentally use."""
    with pytest.raises(NotImplementedError):
        render_begin(RegionFormat.SLASHSTAR, "tiers", ModelVersion(1, 0, 0), "a1b2c3d4")
    with pytest.raises(NotImplementedError):
        render_end(RegionFormat.SLASHSTAR, "tiers")


def test_bare_string_slashstar_still_raises_not_implemented():
    """A caller that passes the bare string `"slashstar"` instead of the
    `RegionFormat.SLASHSTAR` member must not bypass the guard: StrEnum
    value-equality would let `"slashstar"` resolve in `_DELIMITERS` even
    though it fails an `is RegionFormat.SLASHSTAR` identity check, so
    `render_begin`/`render_end`/`parse_marker_line` coerce `fmt` to its
    canonical singleton first."""
    with pytest.raises(NotImplementedError):
        render_begin("slashstar", "tiers", ModelVersion(1, 0, 0), "a1b2c3d4")  # pyright: ignore[reportArgumentType]
    with pytest.raises(NotImplementedError):
        render_end("slashstar", "tiers")  # pyright: ignore[reportArgumentType]
    with pytest.raises(NotImplementedError):
        parse_marker_line("slashstar", "/* marshal-seed:end region=tiers */")  # pyright: ignore[reportArgumentType]


def test_unregistered_fmt_raises_marker_error_not_key_error():
    with pytest.raises(MarkerError, match="fmt must be a registered RegionFormat"):
        render_begin("xml", "tiers", ModelVersion(1, 0, 0), "a1b2c3d4")  # pyright: ignore[reportArgumentType]


# --- bad region name: BeginMarker/EndMarker/render_* all raise MarkerError


@pytest.mark.parametrize("bad_name", ["my region", "My_Region", "", "-tiers", "tiers/x"])
def test_begin_marker_rejects_marker_unsafe_region_name(bad_name):
    with pytest.raises(MarkerError):
        BeginMarker(region=bad_name, model_version=ModelVersion(1, 0, 0), sha="a1b2c3d4")


@pytest.mark.parametrize("bad_name", ["my region", "My_Region"])
def test_end_marker_rejects_marker_unsafe_region_name(bad_name):
    with pytest.raises(MarkerError):
        EndMarker(region=bad_name)


@pytest.mark.parametrize("bad_name", ["my region", "My_Region"])
def test_render_begin_rejects_marker_unsafe_region_name(bad_name):
    with pytest.raises(MarkerError):
        render_begin(RegionFormat.HTML, bad_name, ModelVersion(1, 0, 0), "a1b2c3d4")


@pytest.mark.parametrize("bad_name", ["my region", "My_Region"])
def test_render_end_rejects_marker_unsafe_region_name(bad_name):
    with pytest.raises(MarkerError):
        render_end(RegionFormat.HTML, bad_name)


def test_region_name_pattern_matches_every_name_in_the_manifest_template():
    """The exact charset `manifest.py`'s `Region` reuses -- every name
    already authored in `templates/manifest.yaml`."""
    for name in (
        "tiers",
        "portability-contract",
        "dream-first-workflow",
        "model-ignores",
        "model-badge",
        "bmad-multiproject",
    ):
        assert REGION_NAME_PATTERN.fullmatch(name) is not None


def test_region_name_pattern_rejects_space_and_equals():
    assert REGION_NAME_PATTERN.fullmatch("my region") is None
    assert REGION_NAME_PATTERN.fullmatch("region=x") is None


# --- bad sha ---------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_sha",
    [
        "a1b2c3d",  # 7 chars
        "a1b2c3d45",  # 9 chars
        "A1B2C3D4",  # uppercase
        "a1b2c3dg",  # non-hex char
        "",
        "        ",
    ],
)
def test_begin_marker_rejects_malformed_sha(bad_sha):
    with pytest.raises(MarkerError):
        BeginMarker(region="tiers", model_version=ModelVersion(1, 0, 0), sha=bad_sha)


def test_render_begin_rejects_malformed_sha():
    with pytest.raises(MarkerError):
        render_begin(RegionFormat.HTML, "tiers", ModelVersion(1, 0, 0), "not-hex-8")


def test_begin_marker_rejects_non_model_version():
    with pytest.raises(MarkerError):
        BeginMarker(region="tiers", model_version="1.0.0", sha="a1b2c3d4")  # pyright: ignore[reportArgumentType]


# --- body-only sha: renaming/model-version bump never changes it -----------


def test_region_sha_is_deterministic_for_the_same_body():
    body = "identical content\n"
    assert region_sha(body) == region_sha(body)


def test_region_sha_changes_when_the_body_changes():
    assert region_sha("body one\n") != region_sha("body two\n")


def test_region_sha_is_exactly_8_lowercase_hex_characters():
    sha = region_sha("some body\n")
    assert re.fullmatch(r"[0-9a-f]{8}", sha) is not None


def test_region_sha_unchanged_when_only_the_region_name_or_version_changes():
    """The AC itself: changing the region name or model-version alone
    (body unchanged) never changes the sha -- proven by rendering two
    marker lines that differ only in name/version but share one sha."""
    body = "the region's actual content\n"
    sha = region_sha(body)

    begin_a = render_begin(RegionFormat.HTML, "tiers", ModelVersion.parse("1.0.0"), sha)
    begin_b = render_begin(RegionFormat.HTML, "portability-contract", ModelVersion.parse("9.9.9"), sha)

    assert region_sha(body) == sha  # unchanged by anything above
    assert "sha=" + sha in begin_a
    assert "sha=" + sha in begin_b
    assert begin_a != begin_b  # the marker lines differ...
    # ...but never because the sha itself moved.
    parsed_a = parse_marker_line(RegionFormat.HTML, begin_a)
    parsed_b = parse_marker_line(RegionFormat.HTML, begin_b)
    assert isinstance(parsed_a, BeginMarker)
    assert isinstance(parsed_b, BeginMarker)
    assert parsed_a.sha == parsed_b.sha == sha


# --- unregistered format: not this module's concern (see manifest tests) --
# (I/O matrix's "Unregistered manifest format" row is covered end-to-end in
# tests/unit/test_seed_model_manifest.py, per the Code Map -- RegionFormat
# itself simply has no "xml" member, exercised indirectly by the parser
# tests above and directly by the manifest.py wiring.)


# --- non-marker line: parse_marker_line returns None ------------------------


@pytest.mark.parametrize("fmt", [RegionFormat.HTML, RegionFormat.HASH])
def test_ordinary_text_line_returns_none(fmt):
    assert parse_marker_line(fmt, "just some ordinary text") is None


def test_html_comment_that_is_not_a_marshal_seed_marker_returns_none():
    assert parse_marker_line(RegionFormat.HTML, "<!-- just a regular comment -->") is None


def test_hash_comment_that_is_not_a_marshal_seed_marker_returns_none():
    assert parse_marker_line(RegionFormat.HASH, "# just a regular comment") is None


def test_blank_line_returns_none():
    assert parse_marker_line(RegionFormat.HTML, "") is None
    assert parse_marker_line(RegionFormat.HASH, "") is None


def test_wrong_format_delimiter_returns_none_not_an_error():
    """A hash-style line handed to the HTML parser does not open with
    HTML's own delimiter, so it is simply not a candidate marker line in
    that format -- not a malformed one."""
    assert (
        parse_marker_line(RegionFormat.HTML, "# marshal-seed:begin region=tiers model-version=1.0.0 sha=a1b2c3d4")
        is None
    )


def test_extra_whitespace_after_open_delimiter_returns_none_not_an_error():
    """Only the EXACT canonical single-space grammar `render_begin` emits is
    recognized (this module's own documented boundary) -- two spaces after
    the open delimiter means the line does not even start with `"<!-- "`,
    so it never reaches tag detection at all and is ordinary content to
    this module, not a raised error. Recovering that variance is S-8.2's
    job, once it re-normalizes a file before consulting this grammar."""
    assert (
        parse_marker_line(
            RegionFormat.HTML,
            "<!--  marshal-seed:begin region=tiers model-version=1.0.0 sha=a1b2c3d4 -->",
        )
        is None
    )


def test_extra_whitespace_before_close_delimiter_raises_marker_error():
    """Unlike the open-delimiter case above, extra whitespace before the
    close delimiter still satisfies `line.endswith(" -->")` (the closing
    `" -->"` is still there, just with one more space ahead of it) -- so
    the line DOES reach tag detection, and the leftover leading space in
    the extracted body then fails the field grammar: a genuine malformed
    marker, not ordinary content."""
    with pytest.raises(MarkerError):
        parse_marker_line(
            RegionFormat.HTML,
            "<!-- marshal-seed:begin region=tiers model-version=1.0.0 sha=a1b2c3d4  -->",
        )


# --- malformed marker line: parse_marker_line raises MarkerError ------------


def test_malformed_begin_marker_line_raises_marker_error():
    with pytest.raises(MarkerError):
        parse_marker_line(RegionFormat.HTML, "<!-- marshal-seed:begin region=tiers -->")


def test_marker_line_with_unparseable_model_version_raises_marker_error():
    line = "<!-- marshal-seed:begin region=tiers model-version=not-a-version sha=a1b2c3d4 -->"
    with pytest.raises(MarkerError):
        parse_marker_line(RegionFormat.HTML, line)


def test_marker_tag_with_unknown_verb_raises_marker_error():
    with pytest.raises(MarkerError):
        parse_marker_line(RegionFormat.HTML, "<!-- marshal-seed:frobnicate region=tiers -->")


def test_hash_marker_line_with_a_stray_close_token_is_malformed():
    """A `hash` marker line has no closing token by grammar -- one that
    carries a stray trailing `-->` anyway still opens with `# ` and the
    `marshal-seed:` tag, so it is a recognized-but-malformed marker line
    (`MarkerError`), not ordinary content (`None`)."""
    with pytest.raises(MarkerError):
        parse_marker_line(RegionFormat.HASH, "# marshal-seed:end region=tiers -->")
