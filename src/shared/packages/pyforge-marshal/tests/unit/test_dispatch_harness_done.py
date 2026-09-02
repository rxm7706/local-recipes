"""Story 29.2 — harness-done is CAP-4 only (pure gate)."""

from __future__ import annotations

from pyforge.marshal.core.dispatch_harness_done import (
    blocks_harness_relaunch,
    followup_review_recommended,
    land_fail_operator_message,
    parse_spec_status,
)


def test_parse_status_done_and_followup_false() -> None:
    text = (
        "---\nstatus: done\nfollowup_review_recommended: false\n---\n# spec\n"
    )
    assert parse_spec_status(text) == "done"
    assert followup_review_recommended(text) is False
    assert blocks_harness_relaunch(parse_spec_status(text), False) is True


def test_missing_followup_is_not_a_relaunch() -> None:
    text = "---\nstatus: done\n---\n"
    assert followup_review_recommended(text) is False
    assert blocks_harness_relaunch("done", False) is True


def test_followup_true_allows_one_more_session() -> None:
    text = "---\nstatus: done\nfollowup_review_recommended: true\n---\n"
    assert followup_review_recommended(text) is True
    assert blocks_harness_relaunch("done", True) is False


def test_ready_for_dev_never_blocks() -> None:
    text = "---\nstatus: ready-for-dev\n---\n"
    assert parse_spec_status(text) == "ready-for-dev"
    assert blocks_harness_relaunch("ready-for-dev", False) is False


def test_operator_message_names_pr_and_chain() -> None:
    message = land_fail_operator_message(
        story_key="41-2-query-plane",
        named_target="https://github.com/rxm7706/local-recipes/pull/1017",
        land_verdict="refused",
    )
    assert "awaiting-operator" in message
    assert "CHAIN" in message
    assert "1017" in message
    assert "41-2-query-plane" in message
