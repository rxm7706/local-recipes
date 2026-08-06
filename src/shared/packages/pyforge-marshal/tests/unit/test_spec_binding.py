"""Unit tests for ``pyforge.marshal.core.spec_binding`` (Story 2.7,
AD-4/AD-49) -- ``parse_success_signal``'s parsing matrix over the EXACT
``## Verification`` -> ``**Commands:**`` shape verified live against
``spec-3-7-escalation-deferral-and-resume.md``/``spec-3-8-stage-bound-
durability-and-fleet-launch-wiring.md``.
"""

from __future__ import annotations

from pyforge.marshal.core.spec_binding import parse_success_signal

_REAL_SHAPE = """\
---
title: "example"
---

<intent-contract>

## Intent

Some intent text.

</intent-contract>

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: all green.
- `pixi run --frozen -e pyforge-marshal lint-imports --config foo.toml --no-cache` -- expected: contracts hold.

**Manual checks (if no CLI):**
- Do a thing manually.
"""


def test_parse_success_signal_extracts_both_commands_in_order():
    assert parse_success_signal(_REAL_SHAPE) == (
        "pixi run --frozen -e pyforge-marshal pyforge-marshal-test",
        "pixi run --frozen -e pyforge-marshal lint-imports --config foo.toml --no-cache",
    )


def test_parse_success_signal_stops_at_manual_checks_sub_heading():
    text = (
        "## Verification\n\n**Commands:**\n"
        "- `cmd-a` -- expected: ok.\n\n"
        "**Manual checks (if no CLI):**\n"
        "- `not-a-real-command` -- this must never be parsed as a Commands bullet.\n"
    )
    assert parse_success_signal(text) == ("cmd-a",)


def test_parse_success_signal_trailing_prose_after_closing_backtick_is_ignored():
    # Review finding (P5): this test used to be named
    # `..._em_dash_variant_also_parses` and claimed to cover em-dash
    # handling, but `_BULLET_COMMAND` has no dash-specific logic at all --
    # it only ever captures text strictly between the two backticks, so an
    # ordinary `-- expected: ...` bullet already exercises the identical
    # code path. What this test actually verifies: trailing prose after the
    # closing backtick, regardless of what punctuation it opens with (here
    # an em dash, `—`), never leaks into the captured command.
    text = "## Verification\n\n**Commands:**\n- `cmd-a` — expected: ok.\n"
    assert parse_success_signal(text) == ("cmd-a",)


def test_parse_success_signal_no_verification_heading_returns_none():
    assert parse_success_signal("# Title\n\nJust some prose, no heading.\n") is None


def test_parse_success_signal_empty_string_returns_none():
    assert parse_success_signal("") is None


def test_parse_success_signal_verification_heading_with_no_commands_subheading_returns_empty_tuple():
    text = "## Verification\n\nSome prose, no **Commands:** sub-list at all.\n"
    assert parse_success_signal(text) == ()


def test_parse_success_signal_commands_subheading_with_no_bullets_returns_empty_tuple():
    text = "## Verification\n\n**Commands:**\n\n**Manual checks:**\n- do something\n"
    assert parse_success_signal(text) == ()


def test_parse_success_signal_malformed_bullet_is_skipped_not_a_parse_failure():
    text = (
        "## Verification\n\n**Commands:**\n"
        "- this bullet has no backtick-quoted command at all\n"
        "- `cmd-a` -- expected: ok.\n"
    )
    assert parse_success_signal(text) == ("cmd-a",)


def test_parse_success_signal_stops_at_next_atx_heading_with_no_commands_subheading():
    text = "## Verification\n\nsome prose\n\n### Review Triage Log\n\n**Commands:**\n- `should-not-be-seen`\n"
    assert parse_success_signal(text) == ()


def test_parse_success_signal_none_is_distinct_from_empty_tuple():
    # AD-27's own None-vs-empty-tuple discipline, mirrored here (Design
    # Notes): None means "nothing to bind against" (no tracked spec /
    # section), () means "the spec explicitly declares zero commands".
    missing_section = parse_success_signal("no heading here\n")
    empty_commands = parse_success_signal("## Verification\n\n**Commands:**\n")
    assert missing_section is None
    assert empty_commands == ()
    assert missing_section != empty_commands


def test_parse_success_signal_ignores_a_verification_heading_inside_a_deeper_section():
    # A line that merely CONTAINS "## Verification" as a substring, not as
    # its own whole heading line, must not match.
    text = "some prose mentioning ## Verification in passing, not as a heading\n"
    assert parse_success_signal(text) is None


def test_parse_success_signal_only_the_first_verification_section_is_used():
    text = (
        "## Verification\n\n**Commands:**\n- `first`\n\n"
        "## Verification\n\n**Commands:**\n- `second`\n"
    )
    assert parse_success_signal(text) == ("first",)


def test_parse_success_signal_crlf_terminated_spec_still_parses():
    # Review finding (P4): `re.MULTILINE`'s `$` matches before `\n` but NOT
    # before a trailing `\r`, so every heading regex in this module
    # (anchored on `$`) failed to match a CRLF-terminated file at all --
    # a genuinely present `## Verification` section fell through to `None`
    # purely because of how the file's line endings were saved.
    text = "## Verification\r\n\r\n**Commands:**\r\n- `cmd-a` -- expected: ok.\r\n"
    assert parse_success_signal(text) == ("cmd-a",)
