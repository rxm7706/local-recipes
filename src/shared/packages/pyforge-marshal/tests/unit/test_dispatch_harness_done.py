"""Story 29.2 — harness-done is CAP-4 only (pure gate)."""

from __future__ import annotations

from pyforge.marshal.core.dispatch_harness_done import (
    FollowupReview,
    blocks_harness_relaunch,
    followup_review_recommended,
    has_auto_run_result,
    is_followup_review_spec,
    land_fail_operator_message,
    parse_baseline_revision,
    parse_spec_status,
)


def test_parse_status_done_and_followup_false() -> None:
    text = "---\nstatus: done\nfollowup_review_recommended: false\n---\n# spec\n"
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


# --- leading banner (mirrors test_spec_low_risk.py's identical suite) --------


def test_blank_line_before_banner_reads_status() -> None:
    """Story 51.8 (CAP-256, review pass 1): a promoted, banner-topped
    tracked spec's ``status: done`` must not be misread as absent -- a
    leading blank line before the banner's opening marker must not fall
    through to "no frontmatter" either."""
    text = "\n<!-- Promoted ... -->\n---\nstatus: done\n---\n"
    assert parse_spec_status(text) == "done"


def test_spaces_before_banner_reads_status() -> None:
    text = "  <!-- Promoted ... -->\n---\nstatus: done\n---\n"
    assert parse_spec_status(text) == "done"


def test_bom_before_banner_reads_status() -> None:
    text = "\ufeff<!-- Promoted ... -->\n---\nstatus: done\n---\n"
    assert parse_spec_status(text) == "done"


def test_banner_below_frontmatter_unaffected() -> None:
    """The banner-BELOW-frontmatter shape never starts with ``<!--``, so it
    is untouched by the banner-skip and must keep parsing exactly as
    before."""
    text = "---\nstatus: done\n---\n<!-- Promoted ... -->\n"
    assert parse_spec_status(text) == "done"


def test_unclosed_banner_above_frontmatter_returns_none() -> None:
    """An unclosed ``<!--`` is not a banner this parser recognizes -- the
    text still doesn't start with ``---``, so it stays absent."""
    text = "<!-- never closed\n---\nstatus: done\n---\n"
    assert parse_spec_status(text) is None


def test_blank_line_with_no_banner_still_returns_none() -> None:
    """A leading blank line/BOM tolerance must not widen into reading
    frontmatter that isn't at the start once the (non-existent) banner is
    skipped."""
    text = "\n---\nstatus: done\n---\n"
    assert parse_spec_status(text) is None


# --- Story 51.11 (CAP-258): baseline_revision + Auto Run Result heading -----


def test_parse_baseline_revision_reads_frontmatter_scalar() -> None:
    text = "---\nstatus: blocked\nbaseline_revision: 'c8277c03c117ff4779d54a2ff9d900f519415971'\n---\n"
    assert parse_baseline_revision(text) == "c8277c03c117ff4779d54a2ff9d900f519415971"


def test_parse_baseline_revision_missing_is_none() -> None:
    text = "---\nstatus: blocked\n---\n"
    assert parse_baseline_revision(text) is None


def test_has_auto_run_result_true_when_heading_present() -> None:
    text = "---\nstatus: blocked\n---\n\n## Auto Run Result\n\nStatus: escalated\n"
    assert has_auto_run_result(text) is True


def test_has_auto_run_result_false_when_absent() -> None:
    text = "---\nstatus: blocked\n---\n\nNo such section here.\n"
    assert has_auto_run_result(text) is False


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


# --- the follow-up review marker (Story 73.1, CAP-281) ----------------------


def test_is_followup_review_spec_needs_done_and_an_explicit_truthy_flag() -> None:
    assert is_followup_review_spec("---\nstatus: done\nfollowup_review_recommended: true\n---\n") is True
    assert is_followup_review_spec("---\nstatus: done  # landed\nfollowup_review_recommended: yes\n---\n") is True
    assert is_followup_review_spec("---\nstatus: done\nfollowup_review_recommended: false\n---\n") is False
    assert is_followup_review_spec("---\nstatus: done\n---\n") is False
    assert is_followup_review_spec("---\nstatus: in-progress\nfollowup_review_recommended: true\n---\n") is False
    assert is_followup_review_spec("no frontmatter at all") is False


def test_is_followup_review_spec_is_the_pairing_the_relaunch_gate_lets_through() -> None:
    """Story 29.2's gate and the marker read the same two facts: a `done` spec the gate does NOT block is
    exactly one the marker marks."""
    text = "---\nstatus: done\nfollowup_review_recommended: true\n---\n"
    assert blocks_harness_relaunch(parse_spec_status(text), followup_review_recommended(text)) is False
    assert is_followup_review_spec(text) is True


def test_followup_review_round_trips_through_the_launch_intent_payload() -> None:
    marker = FollowupReview(dw_id="DW-FRR-51-2")
    assert marker.to_intent_payload() == {"followup_review": {"dw_id": "DW-FRR-51-2"}}
    assert FollowupReview.from_intent_payload({"story_key": "51.2", **marker.to_intent_payload()}) == marker


def test_followup_review_without_a_row_round_trips_a_null_id() -> None:
    marker = FollowupReview(dw_id=None)
    assert marker.to_intent_payload() == {"followup_review": {"dw_id": None}}
    assert FollowupReview.from_intent_payload(marker.to_intent_payload()) == FollowupReview(dw_id=None)
    assert FollowupReview() == FollowupReview(dw_id=None)


def test_a_launch_payload_without_the_marker_is_a_normal_run() -> None:
    assert FollowupReview.from_intent_payload({"story_key": "51.2", "model": "x"}) is None
    assert FollowupReview.from_intent_payload({}) is None


def test_a_malformed_marker_never_reads_a_row_id_out_of_a_non_string() -> None:
    assert FollowupReview.from_intent_payload({"followup_review": True}) is None
    assert FollowupReview.from_intent_payload({"followup_review": "DW-FRR-51-2"}) is None
    assert FollowupReview.from_intent_payload({"followup_review": {"dw_id": 7}}) == FollowupReview(dw_id=None)
    assert FollowupReview.from_intent_payload({"followup_review": {"dw_id": ""}}) == FollowupReview(dw_id=None)
    assert FollowupReview.from_intent_payload({"followup_review": {}}) == FollowupReview(dw_id=None)
