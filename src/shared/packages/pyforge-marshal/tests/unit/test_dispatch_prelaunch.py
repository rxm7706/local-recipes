"""Unit tests for ``core/dispatch_prelaunch.py`` (Story 65.1, CAP-274).

The pure predicates ``marshal factory drain --plan`` reports through and Story
65.2 reuses: the spec-binding predicate, the prose-park detector, the
inert-override check, the epics block splitter and Deps readiness. No fakes --
every function here takes text and returns a value.
"""

from __future__ import annotations

import pytest

from pyforge.marshal.core import dispatch_prelaunch as prelaunch
from pyforge.marshal.core.identity import StoryKey, normalize

_SPEC_WITH_COMMANDS = """\
---
title: 'a story'
---

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: pass
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- expected: pass
"""

_POLICY = ("pixi run --frozen -e pyforge-marshal pyforge-marshal-test",)


# --- spec_binding_findings -----------------------------------------------------


def test_a_spec_without_a_verification_section_is_gate_010() -> None:
    findings = prelaunch.spec_binding_findings("---\nstatus: backlog\n---\n\n## Intent\n", _POLICY)
    assert [f.code for f in findings] == ["MRS-GATE-010"]


def test_an_unreadable_spec_binds_against_nothing() -> None:
    assert [f.code for f in prelaunch.spec_binding_findings(None, _POLICY)] == ["MRS-GATE-010"]


def test_a_declared_command_outside_policy_is_gate_011_naming_it() -> None:
    findings = prelaunch.spec_binding_findings(_SPEC_WITH_COMMANDS, _POLICY)
    assert [f.code for f in findings] == ["MRS-GATE-011"]
    assert "pyforge-deps-test" in findings[0].message


def test_a_spec_whose_commands_all_bind_reports_nothing() -> None:
    policy = _POLICY + ("pixi run --frozen -e pyforge-ci pyforge-deps-test",)
    assert prelaunch.spec_binding_findings(_SPEC_WITH_COMMANDS, policy) == ()


def test_binding_is_the_post_session_gates_own_verdict() -> None:
    """The predicate is `gate.check_spec_binding` over `parse_success_signal`, not a copy of it."""
    from pyforge.marshal.core import gate, spec_binding

    for text in ("no verification here", _SPEC_WITH_COMMANDS, "## Verification\n\nprose only\n"):
        expected = gate.check_spec_binding(spec_binding.parse_success_signal(text), _POLICY)
        assert prelaunch.spec_binding_findings(text, _POLICY) == expected


# --- find_prose_park -----------------------------------------------------------

_STEWARD_BLOCK = (
    "### Story 44.4: Fold the packages\n\n"
    "**Parked 2026-09-13 (regenerate-not-fold):** do **not** dispatch. Ledger stays `backlog`.\n"
)


def test_the_real_steward_wording_is_a_prose_park_in_the_epics_block() -> None:
    park = prelaunch.find_prose_park(story="44-4-x", station_skips={}, epics_block=_STEWARD_BLOCK, spec_text=None)
    assert park is not None
    assert park.source == "epics.md"
    assert "Parked 2026-09-13" in park.excerpt


@pytest.mark.parametrize(
    "text",
    [
        "This story is PARKED until the kernel is verified.",
        "do not dispatch",
        "Do NOT Dispatch this one",
        "do _not_ dispatch",
        "do **not**\tdispatch",
    ],
)
def test_parked_and_do_not_dispatch_match_case_insensitively(text: str) -> None:
    assert prelaunch.find_prose_park(story="1-1-x", station_skips={}, epics_block=text, spec_text=None) is not None


@pytest.mark.parametrize(
    "text",
    [
        "the story is unparked now",
        "the story is un-parked now",
        "Un-Parked 2026-09-20",
        "a sparked idea",
        "the is_parked flag",
        "do dispatch it",
        "",
    ],
)
def test_the_opposite_claim_and_lookalikes_are_not_a_park(text: str) -> None:
    assert prelaunch.find_prose_park(story="1-1-x", station_skips={}, epics_block=text, spec_text=None) is None


def test_a_park_in_the_tracked_spec_is_found_when_the_epics_block_is_clean() -> None:
    park = prelaunch.find_prose_park(
        story="1-1-x",
        station_skips={},
        epics_block="### Story 1.1: fine\n\nNothing to see.",
        spec_text="---\nstatus: backlog\n---\n\nParked 2026-09-13: do not dispatch.\n",
    )
    assert park is not None
    assert park.source == "tracked spec"


def test_a_skip_policies_entry_mirrors_the_park_so_it_is_not_a_finding() -> None:
    park = prelaunch.find_prose_park(
        story="44-4-fold-the-packages",
        station_skips={"44-4-fold-the-packages": "declared"},
        epics_block=_STEWARD_BLOCK,
        spec_text=None,
    )
    assert park is None


def test_a_park_on_another_story_is_not_mirrored_by_this_ones_skip() -> None:
    park = prelaunch.find_prose_park(
        story="44-5-move-the-estate",
        station_skips={"44-4-fold-the-packages": "declared"},
        epics_block=_STEWARD_BLOCK,
        spec_text=None,
    )
    assert park is not None


# --- story_epics_blocks --------------------------------------------------------

_EPICS = """\
## Epic 44: Launch

Epic preamble: parked stories are listed below.

### Story 44.3: Kernel

**Deps:** —

### Story 44.4: Fold the packages

**Parked 2026-09-13:** do **not** dispatch.

## Epic 45: Something else

Epic 45 preamble that also says parked.

### Story 45.1: Fine

Nothing here.
"""


def test_blocks_split_on_story_headings_and_carry_the_heading_line() -> None:
    blocks = prelaunch.story_epics_blocks(_EPICS)
    assert set(blocks) == {normalize("44.3"), normalize("44.4"), normalize("45.1")}
    assert blocks[normalize("44.3")].startswith("### Story 44.3: Kernel")
    assert "44.4" not in blocks[normalize("44.3")]


def test_the_last_story_of_an_epic_stops_at_the_next_epic_heading() -> None:
    blocks = prelaunch.story_epics_blocks(_EPICS)
    assert "do **not** dispatch" in blocks[normalize("44.4")]
    assert "Epic 45 preamble" not in blocks[normalize("44.4")]
    assert (
        prelaunch.find_prose_park(
            story="45-1-x", station_skips={}, epics_block=blocks[normalize("45.1")], spec_text=None
        )
        is None
    )
    assert (
        prelaunch.find_prose_park(
            story="44-3-x", station_skips={}, epics_block=blocks[normalize("44.3")], spec_text=None
        )
        is None
    )


def test_a_document_with_no_story_headings_has_no_blocks() -> None:
    assert prelaunch.story_epics_blocks("# Title\n\nJust prose.\n") == {}


# --- inert_override_keys -------------------------------------------------------

_LEDGER = (
    ("44-3-kernel", "done"),
    ("44-4-fold-the-packages", "backlog"),
    ("44-12-launch", "done"),
)


def test_a_list_of_only_done_keys_is_inert() -> None:
    assert prelaunch.inert_override_keys(["44-3-kernel", "44-12-launch"], _LEDGER) == ("44-3-kernel", "44-12-launch")


def test_a_list_of_only_absent_keys_is_inert() -> None:
    assert prelaunch.inert_override_keys(["renamed-away", "gone-1"], _LEDGER) == ("renamed-away", "gone-1")


def test_done_and_absent_keys_together_are_inert() -> None:
    assert prelaunch.inert_override_keys(["44-3-kernel", "renamed-away"], _LEDGER) == ("44-3-kernel", "renamed-away")


def test_one_live_key_makes_the_whole_list_live() -> None:
    assert prelaunch.inert_override_keys(["44-3-kernel", "44-4-fold-the-packages"], _LEDGER) == ()


def test_an_empty_or_missing_list_is_not_an_inert_override() -> None:
    assert prelaunch.inert_override_keys([], _LEDGER) == ()
    assert prelaunch.inert_override_keys(None, _LEDGER) == ()


def test_a_repeated_key_is_reported_once() -> None:
    assert prelaunch.inert_override_keys(["44-3-kernel", "44-3-kernel"], _LEDGER) == ("44-3-kernel",)


# --- unmet_deps ----------------------------------------------------------------


def test_unmet_deps_names_the_declared_deps_that_are_not_done() -> None:
    graph = {"44.4": (normalize("44.3"), normalize("44.12"), normalize("44.9"))}
    statuses = (("44-3-kernel", "done"), ("44-12-launch", "done"), ("44-9-late", "backlog"))
    unmet = prelaunch.unmet_deps("44-4-fold-the-packages", statuses, graph)
    assert unmet == (normalize("44.9"),)
    assert isinstance(unmet[0], StoryKey)


def test_a_story_with_every_dep_done_or_no_deps_has_none_unmet() -> None:
    graph = {"44.4": (normalize("44.3"),)}
    statuses = (("44-3-kernel", "done"),)
    assert prelaunch.unmet_deps("44-4-fold-the-packages", statuses, graph) == ()
    assert prelaunch.unmet_deps("44-7-undeclared", statuses, graph) == ()


def test_a_dep_absent_from_the_ledger_is_unmet() -> None:
    graph = {"44.4": (normalize("44.3"),)}
    assert prelaunch.unmet_deps("44-4-x", (), graph) == (normalize("44.3"),)


def test_a_malformed_story_key_has_no_readable_deps() -> None:
    assert prelaunch.unmet_deps("not-a-key", (), {"44.4": (normalize("44.3"),)}) == ()
