"""Unit tests for Story 28.12/28.16 dependency graph helpers."""

from __future__ import annotations

from pyforge.marshal.core.identity import normalize, render_feed_key
from pyforge.marshal.core.spec_deps import (
    parse_deps_text,
    ready_backlog,
    story_deps_from_epics,
    story_transitively_depends_on,
)


def test_parse_deps_text_reads_bare_story_keys() -> None:
    assert parse_deps_text("28.12") == (normalize("28.12"),)
    assert parse_deps_text("S-28.12, 22.1") == (
        normalize("28.12"),
        normalize("22.1"),
    )
    assert parse_deps_text("—") == ()
    assert parse_deps_text("") == ()


def test_story_deps_from_epics_extracts_per_story_deps() -> None:
    epics = """
### Story 28.16: Parallel fan-out
**Type:** feature • **Effort:** M • **Deps:** 28.12

### Story 28.12: Ordering
**Type:** feature • **Effort:** M • **Deps:** —
"""
    graph = story_deps_from_epics(epics)
    key_28_16 = render_feed_key(normalize("28.16"))
    key_28_12 = render_feed_key(normalize("28.12"))
    assert graph[key_28_16] == (normalize("28.12"),)
    assert graph[key_28_12] == ()


def test_ready_backlog_filters_unmet_dependencies() -> None:
    graph = {
        render_feed_key(normalize("28.16")): (normalize("28.12"),),
        render_feed_key(normalize("28.12")): (),
    }
    statuses = (
        ("28-12-ordering", "backlog"),
        ("28-16-fanout", "backlog"),
    )
    assert ready_backlog(("28-16-fanout", "28-12-ordering"), statuses, graph) == ("28-12-ordering",)
    done_statuses = (
        ("28-12-ordering", "done"),
        ("28-16-fanout", "backlog"),
    )
    assert ready_backlog(("28-16-fanout", "28-12-ordering"), done_statuses, graph) == ("28-16-fanout", "28-12-ordering")


def test_story_transitively_depends_on() -> None:
    a = render_feed_key(normalize("28.12"))
    b = render_feed_key(normalize("28.16"))
    graph = {b: (normalize("28.12"),), a: ()}
    assert story_transitively_depends_on(b, a, graph)
    assert not story_transitively_depends_on(a, b, graph)
