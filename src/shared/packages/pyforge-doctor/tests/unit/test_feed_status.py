"""Shared sprint-feed status parsing (Story 41.2)."""

from __future__ import annotations

from pyforge.doctor.sources.feed_status import (
    TERMINAL,
    is_epic_aggregate_key,
    normalize_status_value,
    parse_development_statuses,
)


def test_parse_skips_column_zero_comment_inside_development_status() -> None:
    text = """development_status:
  1-1-a: done
# column-zero comment must not truncate the block
  1-2-b: done
"""
    assert set(parse_development_statuses(text)) == {"1-1-a", "1-2-b"}


def test_parse_strips_quotes_and_inline_comments_for_terminal() -> None:
    text = """development_status:
  1-1-a: 'done'
  1-2-b: done  # landed
"""
    parsed = parse_development_statuses(text)
    assert parsed["1-1-a"] in TERMINAL
    assert parsed["1-2-b"] in TERMINAL


def test_epic_aggregate_keys_are_not_story_keys() -> None:
    assert is_epic_aggregate_key("epic-9")
    assert is_epic_aggregate_key("epic-9-retrospective")
    assert not is_epic_aggregate_key("9-1-a-story")


def test_normalize_status_value() -> None:
    assert normalize_status_value("'done'") == "done"
    assert normalize_status_value("done  # note") == "done"
