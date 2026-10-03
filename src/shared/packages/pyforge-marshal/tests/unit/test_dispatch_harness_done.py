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
    should_take_harness_done_land_only,
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


# --- Story 83.7: refused landing journal extends the land-only gate -----------


def test_should_take_land_only_when_latest_landing_was_refused_even_if_spec_in_progress() -> None:
    assert (
        should_take_harness_done_land_only(
            "in-progress",
            False,
            latest_landing_verdict="refused",
        )
        is True
    )


def test_should_not_take_land_only_without_a_refused_landing_when_spec_not_done() -> None:
    assert (
        should_take_harness_done_land_only(
            "in-progress",
            False,
            latest_landing_verdict=None,
        )
        is False
    )
    assert (
        should_take_harness_done_land_only(
            "ready-for-dev",
            False,
            latest_landing_verdict=None,
        )
        is False
    )


def test_should_take_land_only_when_refused_and_spec_in_review() -> None:
    assert (
        should_take_harness_done_land_only(
            "in-review",
            False,
            latest_landing_verdict="refused",
        )
        is True
    )


def test_refused_landing_does_not_force_land_only_after_send_back_to_ready_for_dev() -> None:
    assert (
        should_take_harness_done_land_only(
            "ready-for-dev",
            False,
            latest_landing_verdict="refused",
        )
        is False
    )


def test_refused_landing_does_not_force_land_only_after_send_back_to_draft() -> None:
    assert (
        should_take_harness_done_land_only(
            "draft",
            False,
            latest_landing_verdict="refused",
        )
        is False
    )


def test_removing_the_send_back_guard_would_land_only_on_ready_for_dev_after_refusal() -> None:
    """Mutation guard (Story 83.7 AC): send-back statuses must never take land-only."""
    assert (
        should_take_harness_done_land_only(
            "ready-for-dev",
            False,
            latest_landing_verdict="refused",
        )
        is False
    )


def test_removing_the_refused_landing_journal_rule_leaves_in_progress_stories_launchable() -> None:
    """Mutation guard (Story 83.7 AC): land-only must not fire without the journal fact."""
    assert blocks_harness_relaunch("in-progress", False) is False


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


_TIP = "0123456789abcdef0123456789abcdef01234567"


def test_followup_review_round_trips_through_the_launch_intent_payload() -> None:
    marker = FollowupReview(dw_id="DW-FRR-51-2", launch_origin_main_sha=_TIP)
    assert marker.to_intent_payload() == {
        "followup_review": {"dw_id": "DW-FRR-51-2"},
        "launch_origin_main_sha": _TIP,
    }
    assert FollowupReview.from_intent_payload({"story_key": "51.2", **marker.to_intent_payload()}) == marker


def test_followup_review_without_a_row_round_trips_a_null_id() -> None:
    marker = FollowupReview(dw_id=None, launch_origin_main_sha=_TIP)
    assert marker.to_intent_payload() == {"followup_review": {"dw_id": None}, "launch_origin_main_sha": _TIP}
    assert FollowupReview.from_intent_payload(marker.to_intent_payload()) == marker
    assert FollowupReview() == FollowupReview(dw_id=None, launch_origin_main_sha=None)


def test_followup_review_records_the_launch_tip_beside_the_marker_not_inside_it() -> None:
    """The launch tip is its own INTENT key (the spec's wording), read back into the one marker type."""
    payload = FollowupReview(dw_id="DW-FRR-51-2", launch_origin_main_sha=_TIP).to_intent_payload()
    assert payload["followup_review"] == {"dw_id": "DW-FRR-51-2"}
    assert payload["launch_origin_main_sha"] == _TIP
    assert FollowupReview.from_intent_payload(payload) == FollowupReview("DW-FRR-51-2", _TIP)


def test_a_launch_payload_without_the_marker_is_a_normal_run() -> None:
    assert FollowupReview.from_intent_payload({"story_key": "51.2", "model": "x"}) is None
    assert FollowupReview.from_intent_payload({}) is None
    # A tip alone is not a marker: only a mapping under `followup_review` marks a follow-up run.
    assert FollowupReview.from_intent_payload({"launch_origin_main_sha": _TIP}) is None


def test_a_malformed_marker_never_reads_a_row_id_out_of_a_non_string() -> None:
    assert FollowupReview.from_intent_payload({"followup_review": True}) is None
    assert FollowupReview.from_intent_payload({"followup_review": "DW-FRR-51-2"}) is None
    assert FollowupReview.from_intent_payload({"followup_review": {"dw_id": 7}}) == FollowupReview(dw_id=None)
    assert FollowupReview.from_intent_payload({"followup_review": {"dw_id": ""}}) == FollowupReview(dw_id=None)
    assert FollowupReview.from_intent_payload({"followup_review": {}}) == FollowupReview(dw_id=None)


def test_a_malformed_launch_tip_reads_as_unrecorded() -> None:
    for tip in (7, "", None, ["x"]):
        marker = FollowupReview.from_intent_payload({"followup_review": {"dw_id": None}, "launch_origin_main_sha": tip})
        assert marker == FollowupReview(dw_id=None, launch_origin_main_sha=None)
