"""Unit tests for ``pyforge.marshal.core.deferred_work`` (Story 4.13,
FR-175) -- pure, no I/O, no fixtures touching disk or git; every input is a
plain string or value.
"""

from __future__ import annotations

import pytest

from pyforge.marshal.core import gate
from pyforge.marshal.core.deferred_work import (
    DeferralCandidate,
    FollowupReviewCandidate,
    append_ledger_entry,
    close_followup_review_row,
    deferrals_to_promote,
    followup_review_candidate,
    followup_review_id,
    followup_review_to_promote,
    open_followup_review_id,
    parse_followup_deferrals,
    promoted_id,
    render_followup_review_entry,
    render_ledger_entry,
)
from pyforge.marshal.core.identity import StoryKey, normalize

# --- parse_followup_deferrals -------------------------------------------

_CLEAN_BLOCK = """\
### DW-8: Follow-up review still recommended for 2-1-standalone-verify-command-runner-project-scoped after the damping cap was spent
origin: review-budget-followup
source_spec: `spec-2-1-standalone-verify-command-runner-project-scoped.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260802-183704-36df; this entry preserves the lingering recommendation for a deliberate later review.
status: open
"""

# Reproduces the live implementation-artifacts/deferred-work.md's own
# DW-6 shape (lines ~483-504 at the time this test was written): the
# heading's own five fields (origin/source_spec/severity/reason/status)
# are separated by SEVERAL interleaved, indented anonymous-bullet entries
# belonging to unrelated findings -- including one carrying its OWN
# indented `  status:` line -- that got appended into the same Tier-3 file
# in between. Only the column-0 field lines belong to DW-6 itself.
_DW6_SHAPED_BLOCK = """\
### DW-6: Follow-up review still recommended for 3-4-supervisor-process-lifecycle after the damping cap was spent
origin: review-budget-followup
source_spec: `spec-3-4-supervisor-process-lifecycle.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up.

- source_spec: `_bmad-output/implementation-artifacts/spec-3-5-idle-strand-detection.md`
  summary: An unrelated anonymous finding appended into the same Tier-3 file.
  evidence: Some other story's own review finding, interleaved here.
  status: **LIVE as of Story 3.5** -- an indented status line belonging to
    this anonymous bullet, not to DW-6.

- source_spec: `_bmad-output/implementation-artifacts/spec-3-5-idle-strand-detection.md`
  summary: A second unrelated anonymous finding, also interleaved.
  evidence: Another story's own review finding.
status: open

### DW-7: Follow-up review still recommended for 3-5-idle-strand-detection after the damping cap was spent
origin: review-budget-followup
source_spec: `spec-3-5-idle-strand-detection.md`
severity: low
reason: A second, unrelated block that must not be swallowed by DW-6's own scan.
status: open
"""

_NON_FOLLOWUP_ORIGIN_BLOCK = """\
### DW-9: Some other kind of tracked deferral entirely
origin: something-else
source_spec: `spec-5-1-unrelated.md`
severity: low
reason: Not a review-budget-followup entry at all.
status: open
"""


def test_parses_a_clean_block():
    candidates = parse_followup_deferrals(_CLEAN_BLOCK)
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.tier3_id == "DW-8"
    assert candidate.story_key == StoryKey(2, 1)
    assert candidate.title == (
        "Follow-up review still recommended for "
        "2-1-standalone-verify-command-runner-project-scoped after the "
        "damping cap was spent"
    )
    assert candidate.source_spec == "spec-2-1-standalone-verify-command-runner-project-scoped.md"
    assert candidate.severity == "low"
    assert candidate.status == "open"
    assert candidate.reason.startswith("The follow-up-review damping cap")


def test_parses_dw6_shaped_block_with_interleaved_anonymous_bullets():
    """The story's own named gotcha: a naive "read N lines after the
    heading" parser would collect the wrong ``status:`` (or the wrong
    ``reason:``) from the interleaved anonymous bullets. This must recover
    BOTH real blocks (DW-6 and the DW-7 that follows it) with their own
    correct fields, and must NOT fabricate a candidate from either
    anonymous bullet (neither carries an ``origin:`` field at all)."""
    candidates = parse_followup_deferrals(_DW6_SHAPED_BLOCK)
    assert [c.tier3_id for c in candidates] == ["DW-6", "DW-7"]

    dw6 = candidates[0]
    assert dw6.story_key == StoryKey(3, 4)
    assert dw6.severity == "low"
    assert dw6.status == "open"
    assert dw6.reason == (
        "The follow-up-review damping cap (limits.max_followup_reviews = 2) "
        "was spent with the story finalized (status: done, verify green) "
        "while the review pass still recommended an independent follow-up."
    )

    dw7 = candidates[1]
    assert dw7.story_key == StoryKey(3, 5)
    assert dw7.reason == ("A second, unrelated block that must not be swallowed by DW-6's own scan.")


def test_non_review_budget_followup_origin_is_ignored():
    assert parse_followup_deferrals(_NON_FOLLOWUP_ORIGIN_BLOCK) == ()


def test_missing_required_field_is_ignored_not_raised():
    truncated = """\
### DW-10: A heading with no fields following it at all

### DW-11: Follow-up review still recommended for 6-1-x after the damping cap was spent
origin: review-budget-followup
source_spec: `spec-6-1-x.md`
severity: low
reason: complete
status: open
"""
    candidates = parse_followup_deferrals(truncated)
    assert [c.tier3_id for c in candidates] == ["DW-11"]


def test_malformed_source_spec_drops_only_that_block():
    malformed = """\
### DW-12: Follow-up review still recommended for not-a-story-key after the damping cap was spent
origin: review-budget-followup
source_spec: `spec-not-a-story-key.md`
severity: low
reason: unparseable story key
status: open

### DW-13: Follow-up review still recommended for 7-2-y after the damping cap was spent
origin: review-budget-followup
source_spec: `spec-7-2-y.md`
severity: low
reason: fine
status: open
"""
    candidates = parse_followup_deferrals(malformed)
    assert [c.tier3_id for c in candidates] == ["DW-13"]


def test_no_headings_returns_empty_tuple():
    assert parse_followup_deferrals("# Deferred Work\n\nno headings here at all\n") == ()


# --- promoted_id ----------------------------------------------------------


def test_promoted_id_form():
    assert promoted_id(StoryKey(2, 1)) == "DW-FU-2-1"
    assert promoted_id(StoryKey(6, 1, "a")) == "DW-FU-6-1a"


# --- render_ledger_entry ----------------------------------------------------


def _candidate(**overrides) -> DeferralCandidate:
    base = dict(
        tier3_id="DW-8",
        story_key=StoryKey(2, 1),
        title=(
            "Follow-up review still recommended for "
            "2-1-standalone-verify-command-runner-project-scoped after the "
            "damping cap was spent"
        ),
        source_spec="spec-2-1-standalone-verify-command-runner-project-scoped.md",
        severity="low",
        reason="The follow-up-review damping cap was spent.",
        status="open",
    )
    base.update(overrides)
    return DeferralCandidate(**base)


def test_render_ledger_entry_matches_the_golden_shape():
    entry = render_ledger_entry(_candidate(), promoted_date="2026-08-10")
    assert entry == (
        "### DW-FU-2-1: Follow-up review still recommended for "
        "2-1-standalone-verify-command-runner-project-scoped after the "
        "damping cap was spent\n"
        "\n"
        "- source_spec: `spec-2-1-standalone-verify-command-runner-project-scoped.md`\n"
        "  summary: Follow-up review still recommended for "
        "2-1-standalone-verify-command-runner-project-scoped after the "
        "damping cap was spent\n"
        "  evidence: The follow-up-review damping cap was spent.\n"
        "  promoted: 2026-08-10 — promoted from Tier-3 "
        "`implementation-artifacts/deferred-work.md` (id `DW-8` there) "
        "under the ledger's `DW-FU-<story>` convention, so the next damped "
        "story cannot collide with a generic `DW-8`.\n"
        "  severity: low\n"
        "  status: open\n"
    )


def test_render_ledger_entry_names_the_bare_tier3_id_twice():
    """``scripts/deferred_work_check.py`` looks for the bare Tier-3 id
    (``DW-<n>``) ANYWHERE in the tracked ledger's text to decide it has a
    twin -- the rendered entry must carry it as a real substring."""
    entry = render_ledger_entry(_candidate(tier3_id="DW-42"), promoted_date="2026-08-10")
    assert entry.count("DW-42") == 2


# --- deferrals_to_promote ---------------------------------------------------


def test_deferrals_to_promote_filters_to_landing_keys_and_not_yet_promoted():
    in_scope_new = _candidate(tier3_id="DW-8", story_key=StoryKey(2, 1))
    in_scope_already_promoted = _candidate(tier3_id="DW-3", story_key=StoryKey(2, 6))
    not_in_landing_set = _candidate(tier3_id="DW-4", story_key=StoryKey(5, 1))

    candidates = (in_scope_new, in_scope_already_promoted, not_in_landing_set)
    landing_keys = frozenset({StoryKey(2, 1), StoryKey(2, 6)})
    tracked_text = "...\n### DW-FU-2-6: already promoted ...\n..."

    result = deferrals_to_promote(candidates, landing_keys, tracked_text)

    assert result == (in_scope_new,)


def test_deferrals_to_promote_empty_when_nothing_new():
    candidate = _candidate(tier3_id="DW-8", story_key=StoryKey(2, 1))
    landing_keys = frozenset({StoryKey(2, 1)})
    tracked_text = "already has DW-FU-2-1 in it somewhere"

    assert deferrals_to_promote((candidate,), landing_keys, tracked_text) == ()


def test_deferrals_to_promote_is_not_fooled_by_a_prefix_collision():
    """Review finding (2026-08-10): a bare ``promoted_id(...) in
    tracked_text`` substring test false-positives whenever one promoted id
    is a literal string-prefix of another. ``"DW-FU-1-1"`` is a substring
    of ``"DW-FU-1-10"`` -- and this repo already has both shapes live
    (story 1.10 alongside the already-promoted ``DW-FU-1-1``). A tracked
    ledger that carries ONLY ``DW-FU-1-10`` (story 1.10's own promotion)
    must NOT be read as story 1.1 already having a twin -- 1.1's own
    candidate must still come back as pending."""
    candidate_1_1 = _candidate(tier3_id="DW-8", story_key=StoryKey(1, 1), source_spec="spec-1-1-x.md")
    landing_keys = frozenset({StoryKey(1, 1)})
    tracked_text = "### DW-FU-1-10: some other, unrelated story's own promoted entry\n"

    result = deferrals_to_promote((candidate_1_1,), landing_keys, tracked_text)

    assert result == (candidate_1_1,)


def test_deferrals_to_promote_still_recognizes_an_exact_match_alongside_a_longer_sibling():
    """The companion case to the prefix-collision regression above: when
    the tracked text carries BOTH the longer sibling id AND the exact id
    being checked, the exact one is still correctly recognized as
    already-promoted."""
    candidate_1_1 = _candidate(tier3_id="DW-8", story_key=StoryKey(1, 1))
    landing_keys = frozenset({StoryKey(1, 1)})
    tracked_text = "### DW-FU-1-10: some other story\n\n### DW-FU-1-1: the exact match\n"

    assert deferrals_to_promote((candidate_1_1,), landing_keys, tracked_text) == ()


def test_deferrals_to_promote_dedupes_two_candidates_for_the_same_story_in_one_batch():
    """Review finding (2026-08-10): two Tier-3 blocks resolving to the SAME
    story key in one call must never both survive into the result -- that
    would mean two identical ``### DW-FU-<story>:`` headings written to the
    ledger in a single batch. The first, by input order, wins."""
    first = _candidate(tier3_id="DW-8", story_key=StoryKey(4, 4))
    second = _candidate(tier3_id="DW-20", story_key=StoryKey(4, 4))
    landing_keys = frozenset({StoryKey(4, 4)})

    result = deferrals_to_promote((first, second), landing_keys, tracked_text="")

    assert result == (first,)


# --- Story 2.8: review tier never changes deferred-work capture (AC4) ------
# Defense-in-depth proof for the by-construction guarantee: this story
# ships no CLI/journal wiring (see `core/gate.py`'s own module docstring
# addition), so nothing here is wired to vary by tier at all -- neither
# `parse_followup_deferrals` nor `deferrals_to_promote` imports, reads, or
# is otherwise aware `classify_review_tier`/`resolve_review_cycles` exist.
# This test reproduces the `review-budget-followup` Tier-3 block shape (the
# `DW-AD23-3` incident shape, per `_CLEAN_BLOCK`'s own fixture above) for a
# story classified into EACH defined tier -- the block's own `reason:` text
# is built FROM `classify_review_tier`'s real returned report (not just
# labeled to match it), so the tier value genuinely drives what gets parsed,
# and proves both are captured -- and promoted -- identically regardless.


def _review_budget_followup_block(*, tier3_id: str, story: str, story_key: StoryKey, report: dict[str, object]) -> str:
    return (
        f"### {tier3_id}: Follow-up review still recommended for {story} "
        "after the damping cap was spent\n"
        "origin: review-budget-followup\n"
        f"source_spec: `spec-{story}.md`\n"
        "severity: low\n"
        "reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) "
        f"was spent for a story classified into the {report['tier']!r} review tier "
        f"(declared_low_risk={report['declared_low_risk']!r}, "
        f"changed_files={report['changed_files']!r}) -- tier must never change "
        "deferred-work capture.\n"
        "status: open\n"
    )


def test_review_budget_followup_capture_is_identical_regardless_of_review_tier():
    low_tier_report = gate.classify_review_tier(declared_low_risk=True, changed_files=("a.py", "b.py"))
    standard_tier_report = gate.classify_review_tier(
        declared_low_risk=False, changed_files=("a.py", "b.py", "c.py", "d.py")
    )
    assert low_tier_report["tier"] == "low"
    assert standard_tier_report["tier"] == "standard"

    # The block text is built FROM each report above -- if `classify_review_
    # tier` ever produced a different tier for these inputs, the parsed
    # `reason` text below would change with it, so this is a real causal
    # link, not two facts asserted side by side.
    low_block = _review_budget_followup_block(
        tier3_id="DW-30",
        story="9-1-a-low-tier-story",
        story_key=StoryKey(9, 1),
        report=low_tier_report,
    )
    standard_block = _review_budget_followup_block(
        tier3_id="DW-31",
        story="9-2-a-standard-tier-story",
        story_key=StoryKey(9, 2),
        report=standard_tier_report,
    )

    low_candidates = parse_followup_deferrals(low_block)
    standard_candidates = parse_followup_deferrals(standard_block)

    assert len(low_candidates) == 1
    assert len(standard_candidates) == 1
    assert low_candidates[0].tier3_id == "DW-30"
    assert low_candidates[0].story_key == StoryKey(9, 1)
    assert f"classified into the {low_tier_report['tier']!r} review tier" in low_candidates[0].reason
    assert standard_candidates[0].tier3_id == "DW-31"
    assert standard_candidates[0].story_key == StoryKey(9, 2)
    assert f"classified into the {standard_tier_report['tier']!r} review tier" in standard_candidates[0].reason

    low_promoted = deferrals_to_promote(low_candidates, frozenset({low_candidates[0].story_key}), tracked_text="")
    standard_promoted = deferrals_to_promote(
        standard_candidates,
        frozenset({standard_candidates[0].story_key}),
        tracked_text="",
    )

    # Both tiers survive parsing AND promotion with the same completeness
    # guarantee -- never silently dropped for either.
    assert low_promoted == low_candidates
    assert standard_promoted == standard_candidates


# --- the dispatch twin: a recommended follow-up review (Story 66.1, CAP-275) --------

_FRR_SPEC_PATH = "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-51-2-the-landing-record.md"
_FRR_SPEC = "---\ntitle: '51.2: x'\nstatus: 'done'\nfollowup_review_recommended: true\n---\n\nbody\n"


def _frr_candidate() -> FollowupReviewCandidate:
    candidate = followup_review_candidate(_FRR_SPEC, normalize("51.2"), _FRR_SPEC_PATH)
    assert candidate is not None
    return candidate


def test_followup_review_id_form():
    assert followup_review_id(normalize("51.2")) == "DW-FRR-51-2"
    assert followup_review_id(normalize("6.1a")) == "DW-FRR-6-1a"


def test_followup_review_candidate_carries_both_path_forms():
    candidate = _frr_candidate()
    assert candidate.story_key == normalize("51.2")
    assert candidate.spec_path == _FRR_SPEC_PATH
    assert candidate.source_spec == "planning-artifacts/specs/spec-51-2-the-landing-record.md"


def test_followup_review_candidate_keeps_a_path_outside_planning_artifacts_whole():
    candidate = followup_review_candidate(_FRR_SPEC, normalize("51.2"), "specs/spec-51-2-x.md")
    assert candidate is not None and candidate.source_spec == "specs/spec-51-2-x.md"


@pytest.mark.parametrize("flag", ["true", "yes", "1", "True"])
def test_followup_review_candidate_accepts_every_explicit_truthy(flag: str):
    text = _FRR_SPEC.replace("followup_review_recommended: true", f"followup_review_recommended: {flag}")
    assert followup_review_candidate(text, normalize("51.2"), _FRR_SPEC_PATH) is not None


@pytest.mark.parametrize(
    "text",
    [
        _FRR_SPEC.replace("followup_review_recommended: true", "followup_review_recommended: false"),
        _FRR_SPEC.replace("followup_review_recommended: true", "followup_review_recommended: no"),
        _FRR_SPEC.replace("followup_review_recommended: true\n", ""),
        _FRR_SPEC.replace("status: 'done'", "status: 'in-review'"),
        _FRR_SPEC.replace("status: 'done'", "status: 'backlog'"),
        _FRR_SPEC.replace("status: 'done'\n", ""),
        "no frontmatter at all\nfollowup_review_recommended: true\n",
        "",
        None,
    ],
)
def test_followup_review_candidate_is_none_unless_done_and_explicitly_flagged(text):
    assert followup_review_candidate(text, normalize("51.2"), _FRR_SPEC_PATH) is None


@pytest.mark.parametrize(
    "status_line",
    [
        "status: done  # landed via dispatch",
        "status: Done",
        "status: DONE",
        "status: 'done'",
        'status: "done"',
        "status: done",
    ],
)
def test_followup_review_candidate_reads_status_through_the_harness_guards_reader(status_line: str):
    # The shapes the strict `promotion.read_spec_status` answers None for (a trailing comment, a capital)
    # are `done` to `dispatch_harness_done.parse_spec_status`, the reader the harness guard pairs with the flag.
    text = _FRR_SPEC.replace("status: 'done'", status_line)
    assert followup_review_candidate(text, normalize("51.2"), _FRR_SPEC_PATH) is not None


@pytest.mark.parametrize(
    "status_line",
    ["status: in-review", "status: backlog", "status: ready-for-dev", "status: blocked", "status: done-ish", "status:"],
)
def test_followup_review_candidate_is_none_for_a_status_other_than_done(status_line: str):
    text = _FRR_SPEC.replace("status: 'done'", status_line)
    assert followup_review_candidate(text, normalize("51.2"), _FRR_SPEC_PATH) is None


def test_followup_review_candidate_is_none_for_an_unterminated_frontmatter():
    text = "---\nstatus: done\nfollowup_review_recommended: true\n\nbody with no closing fence\n"
    assert followup_review_candidate(text, normalize("51.2"), _FRR_SPEC_PATH) is None


def test_followup_review_to_promote_passes_a_candidate_the_ledger_does_not_carry():
    candidate = _frr_candidate()
    # DW-FU-51-2-1 is the hand-filed row for the same story: a different prefix, never the dispatch twin.
    ledger = "### DW-FU-51-2-1: hand-filed\n\n- source_spec: `x`\n"
    assert followup_review_to_promote(candidate, ledger) is candidate
    assert followup_review_to_promote(candidate, "") is candidate


def test_followup_review_to_promote_is_idempotent():
    candidate = _frr_candidate()
    ledger = append_ledger_entry("# Ledger\n", render_followup_review_entry(candidate, promoted_date="2026-10-01"))
    assert followup_review_to_promote(candidate, ledger) is None


def test_followup_review_to_promote_is_not_fooled_by_a_prefix_collision():
    candidate = _frr_candidate()
    assert followup_review_to_promote(candidate, "### DW-FRR-51-20: later story\n") is candidate
    assert followup_review_to_promote(candidate, "### DW-FRR-51-2a: suffixed story\n") is candidate
    assert followup_review_to_promote(candidate, "### DW-FRR-51-20: a\n\n### DW-FRR-51-2: b\n") is None


def test_followup_review_to_promote_ignores_an_id_that_only_appears_in_prose():
    # Review pass 2: the live marshal ledger names `DW-FRR-51-2` in another row's `verified:` line. A prose mention
    # is not the row, so 51.2 -- the story this feature exists for -- is still carried.
    candidate = _frr_candidate()
    ledger = (
        "### DW-FU-51-2-1: Follow-up review still recommended for story 51.2\n"
        "\n"
        "- source_spec: `planning-artifacts/specs/spec-51-2-the-landing-record.md`\n"
        "  summary: hand-filed\n"
        "  verified: 2026-09-28 -- the carry for this story is `DW-FRR-51-2` (Story 66.1 mints it); see DW-FRR-51-2.\n"
        "  status: open\n"
    )
    assert followup_review_to_promote(candidate, ledger) is candidate
    assert followup_review_to_promote(candidate, "- verified: DW-FRR-51-2 is the carry\n") is candidate
    assert followup_review_to_promote(candidate, "mentions the placeholder `DW-FRR-<story>` only\n") is candidate


@pytest.mark.parametrize("level", ["##", "###", "####"])
def test_followup_review_to_promote_counts_a_row_heading_at_level_two_to_four(level: str):
    candidate = _frr_candidate()
    assert followup_review_to_promote(candidate, f"{level} DW-FRR-51-2: carried\n\n- status: open\n") is None
    assert followup_review_to_promote(candidate, f"{level} DW-FRR-51-2\n") is None
    # ... while a longer sibling heading at the same level is another row.
    assert followup_review_to_promote(candidate, f"{level} DW-FRR-51-20: later story\n") is candidate


def test_followup_review_to_promote_does_not_count_a_level_one_or_five_heading_or_an_indented_line():
    candidate = _frr_candidate()
    for text in ("# DW-FRR-51-2: x\n", "##### DW-FRR-51-2: x\n", "  ### DW-FRR-51-2: x\n", "text ### DW-FRR-51-2\n"):
        assert followup_review_to_promote(candidate, text) is candidate, text


def test_followup_review_to_promote_none_candidate_is_none():
    assert followup_review_to_promote(None, "") is None


def test_render_followup_review_entry_matches_the_golden_shape():
    assert render_followup_review_entry(_frr_candidate(), promoted_date="2026-10-01") == (
        "### DW-FRR-51-2: Follow-up review still recommended for story 51.2\n"
        "\n"
        "- source_spec: `planning-artifacts/specs/spec-51-2-the-landing-record.md`\n"
        "  summary: Story 51.2 landed with `followup_review_recommended: true`; the recommended independent "
        "follow-up review has not run and nothing else carries the recommendation.\n"
        "  evidence: Story 51.2 landed on origin/main with its tracked spec reading `status: done` and "
        "`followup_review_recommended: true`; dispatch-land finalize carried the recommendation.\n"
        f"  location: {_FRR_SPEC_PATH}\n"
        "  origin: dispatch-followup-review\n"
        "  severity: low\n"
        "  promoted: 2026-10-01 \u2014 dispatch-land finalize\n"
        "  status: open\n"
    )


def test_append_ledger_entry_separates_with_one_blank_line_and_ends_in_one_newline():
    assert append_ledger_entry("# Ledger\n\nold\n\n\n", "### new\n") == "# Ledger\n\nold\n\n### new\n"
    assert append_ledger_entry("", "### new\n") == "### new\n"


# --- the row, read open and closed (Story 73.1, CAP-281) ----------------------------


def _open_row_ledger(*, other_rows: str = "") -> str:
    """A ledger whose ``DW-FRR-51-2`` row was rendered by the carry (Story 66.1), plus ``other_rows``."""
    return (
        "# Ledger\n\nold\n\n" + render_followup_review_entry(_frr_candidate(), promoted_date="2026-10-01") + other_rows
    )


def test_open_followup_review_id_names_the_open_row():
    assert open_followup_review_id(_open_row_ledger(), normalize("51.2")) == "DW-FRR-51-2"


def test_open_followup_review_id_is_none_without_a_row():
    assert open_followup_review_id("# Ledger\n\nold\n", normalize("51.2")) is None
    assert open_followup_review_id("", normalize("51.2")) is None


def test_open_followup_review_id_is_none_for_a_closed_row():
    closed = close_followup_review_row(
        _open_row_ledger(), "DW-FRR-51-2", resolved_date="2026-10-02", landing="Merge pyforge-marshal/51-2 into main"
    )
    assert closed is not None
    assert open_followup_review_id(closed, normalize("51.2")) is None


def test_open_followup_review_id_is_not_fooled_by_a_prefix_collision():
    sibling = _open_row_ledger().replace("DW-FRR-51-2:", "DW-FRR-51-20:")
    assert open_followup_review_id(sibling, normalize("51.2")) is None
    assert open_followup_review_id(sibling, normalize("51.20")) == "DW-FRR-51-20"


def test_open_followup_review_id_ignores_an_id_that_only_appears_in_prose():
    prose = (
        "### DW-FU-51-2-1: a hand-filed row\n\n- source_spec: `x`\n  verified: DW-FRR-51-2 is the carry\n"
        "  status: open\n"
    )
    assert open_followup_review_id(prose, normalize("51.2")) is None


def test_open_followup_review_id_reads_the_status_of_its_own_row_only():
    """Another row's open ``status:`` after a closed ``DW-FRR`` row is not this row's status."""
    closed_row = _open_row_ledger().replace("  status: open", "  status: closed")
    next_row = "\n### DW-X-1: other\n\n- source_spec: `x`\n  status: open\n"
    assert open_followup_review_id(closed_row + next_row, normalize("51.2")) is None


def test_open_followup_review_id_tolerates_a_status_comment_and_a_bullet():
    bulleted = "### DW-FRR-51-2: x\n\n- status: open  # still to do\n"
    assert open_followup_review_id(bulleted, normalize("51.2")) == "DW-FRR-51-2"


def test_close_followup_review_row_renders_the_row_closed_in_place():
    ledger = _open_row_ledger(other_rows="\n### DW-X-1: other\n\n- source_spec: `x`\n  status: open\n")
    closed = close_followup_review_row(
        ledger, "DW-FRR-51-2", resolved_date="2026-10-02", landing="Merge pyforge-marshal/51-2 into main"
    )
    assert closed == ledger.replace(
        "  status: open\n\n### DW-X-1",
        "  resolved: 2026-10-02 (dispatch-land finalize: Merge pyforge-marshal/51-2 into main)\n"
        "  status: closed\n\n### DW-X-1",
    )
    # Only the FRR row moved: the neighbouring row is still open.
    assert closed is not None
    assert closed.endswith("  status: open\n")


def test_close_followup_review_row_is_a_no_op_for_a_closed_or_absent_row():
    ledger = _open_row_ledger()
    closed = close_followup_review_row(ledger, "DW-FRR-51-2", resolved_date="2026-10-02", landing="L")
    assert closed is not None
    assert close_followup_review_row(closed, "DW-FRR-51-2", resolved_date="2026-10-03", landing="L") is None
    assert close_followup_review_row(ledger, "DW-FRR-9-9", resolved_date="2026-10-02", landing="L") is None
    assert close_followup_review_row("", "DW-FRR-51-2", resolved_date="2026-10-02", landing="L") is None


def test_close_followup_review_row_is_not_fooled_by_a_prefix_collision():
    sibling = _open_row_ledger().replace("DW-FRR-51-2:", "DW-FRR-51-20:")
    assert close_followup_review_row(sibling, "DW-FRR-51-2", resolved_date="2026-10-02", landing="L") is None


def test_close_followup_review_row_leaves_prose_mentions_of_the_id_alone():
    prose = "### DW-FU-51-2-1: x\n\n  verified: DW-FRR-51-2\n  status: open\n"
    assert close_followup_review_row(prose, "DW-FRR-51-2", resolved_date="2026-10-02", landing="L") is None


def test_close_followup_review_row_closes_a_bulleted_status_at_its_own_indent():
    closed = close_followup_review_row(
        "### DW-FRR-51-2: x\n\n- status: open\n", "DW-FRR-51-2", resolved_date="2026-10-02", landing="L"
    )
    assert closed == ("### DW-FRR-51-2: x\n\n  resolved: 2026-10-02 (dispatch-land finalize: L)\n- status: closed\n")


def test_close_followup_review_row_collapses_a_multi_line_landing_onto_one_line():
    closed = close_followup_review_row(
        _open_row_ledger(), "DW-FRR-51-2", resolved_date="2026-10-02", landing="Merge a\n  into   main\n"
    )
    assert closed is not None
    assert "  resolved: 2026-10-02 (dispatch-land finalize: Merge a into main)\n  status: closed\n" in closed


def test_close_followup_review_row_names_a_blank_landing():
    closed = close_followup_review_row(_open_row_ledger(), "DW-FRR-51-2", resolved_date="2026-10-02", landing="  ")
    assert closed is not None
    assert "(dispatch-land finalize: the follow-up review landed)" in closed


def test_close_then_carry_adds_no_second_row():
    """A closed ``DW-FRR`` row still heads the ledger, so the carry (Story 66.1) never re-adds it."""
    closed = close_followup_review_row(_open_row_ledger(), "DW-FRR-51-2", resolved_date="2026-10-02", landing="L")
    assert closed is not None
    assert followup_review_to_promote(_frr_candidate(), closed) is None
