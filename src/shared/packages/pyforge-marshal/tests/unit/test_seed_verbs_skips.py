"""Unit tests for ``pyforge.marshal.seed.verbs.skips`` (Story 10.4) --
covers every skip row of the spec's I/O & Edge-Case Matrix: ``apply_skips``
matching one / all / none, its idempotence, first-pattern-wins, the
fingerprint hash-pair removal that keeps the plan internally consistent,
``record_skip``'s append / dedupe / blank-rejection, and an AGREEMENT test
pinning ``first_match``'s glob semantics to ``fs._matches``'s.

A review pass adds the regressions for six defects this file did not
previously reach: validation that only ran when there was data to validate,
a pattern argument consumed twice, a whitespace-only pattern surviving the
strip, skip matching and never-write matching disagreeing about ``./``-
prefixed paths, the field-by-field rebuilds that would drop a future
``Plan``/``RepoFingerprint`` field, and the missing ``managed_after_skips``
seam that left ``--skip`` unable to protect a hand-edit.

Plan values are built with the same override-dict builder convention
``test_seed_plan_types.py`` establishes, so a future field addition to
``Action``/``RepoFingerprint`` needs one edit per file rather than one per
test.
"""

from __future__ import annotations

import dataclasses
import json

import pytest

from pyforge.marshal.seed.detect.inventory import ArtifactState
from pyforge.marshal.seed.errors import UsageError
from pyforge.marshal.seed.fs import NeverWrite, _matches
from pyforge.marshal.seed.model.manifest import ArtifactClass
from pyforge.marshal.seed.plan.types import Action, Plan, RepoFingerprint, SkippedArtifact
from pyforge.marshal.seed.verbs.preconditions import ManagedRecord
from pyforge.marshal.seed.verbs.skips import (
    apply_skips,
    first_match,
    managed_after_skips,
    record_skip,
)


def _action(**overrides) -> Action:
    fields = {
        "artifact_id": "agents-md",
        "artifact_class": ArtifactClass.COPIED_MANAGED,
        "current_state": ArtifactState.ABSENT,
        "target_state": ArtifactState.PRESENT_CONFORMANT,
        "target_path": "AGENTS.md",
        "chosen_anchor": (),
        "rationale": "test",
    }
    fields.update(overrides)
    return Action(**fields)


def _fingerprint(**overrides) -> RepoFingerprint:
    fields = {
        "git_head": "abc123",
        "dirty": False,
        "artifact_hashes": (("a", "aaaaaaaa"), ("b", "bbbbbbbb"), ("c", "cccccccc")),
    }
    fields.update(overrides)
    return RepoFingerprint(**fields)


def _three_action_plan() -> Plan:
    """Three actions with ids a/b/c, matching ``_fingerprint``'s three hash
    pairs -- the plan-internal consistency an apply runner's bidirectional
    drift check requires, and the invariant ``apply_skips`` must preserve."""
    return Plan(
        actions=(
            _action(artifact_id="a", target_path="docs/a.md"),
            _action(artifact_id="b", target_path="docs/nested/b.md"),
            _action(artifact_id="c", target_path="CLAUDE.md"),
        ),
        repo_fingerprint=_fingerprint(),
    )


# --- first_match -----------------------------------------------------------


def test_first_match_returns_the_matching_pattern():
    assert first_match(("docs/*",), "docs/a.md") == "docs/*"


def test_first_match_returns_none_when_no_pattern_matches():
    assert first_match(("docs/*", "*.toml"), "CLAUDE.md") is None


def test_first_match_over_an_empty_pattern_list_is_none():
    assert first_match((), "anything.md") is None


def test_first_match_returns_the_first_of_several_matching_patterns():
    """Which pattern wins is not a correctness question for the DECISION
    (binary either way) but it is for the MESSAGE -- ``SkippedArtifact.
    pattern`` names it, so a reviewer can tell which ``--skip`` argument is
    responsible."""
    assert first_match(("docs/*", "docs/a.md", "*"), "docs/a.md") == "docs/*"


def test_first_match_star_crosses_a_path_separator():
    """``fnmatch``'s ``*`` matches ``/`` -- the OVER-matching direction, the
    safe one for a rule whose job is to withhold a write."""
    assert first_match(("docs/*",), "docs/nested/deep/b.md") == "docs/*"


def test_first_match_is_case_sensitive_on_every_platform():
    """``fnmatchcase``, never ``fnmatch``: the latter folds case through
    ``os.path.normcase`` (a no-op on POSIX, lowercasing on Windows), which
    would make the same pattern mean different things per platform."""
    assert first_match(("CLAUDE.md",), "claude.md") is None


def test_first_match_strips_a_padded_pattern_before_matching():
    """A padded glob is non-blank yet matches no real path -- so without a
    strip it silently withholds NOTHING, which for a skip means writing a
    file the operator asked to leave alone."""
    assert first_match((" docs/* ",), "docs/a.md") == "docs/*"


def test_first_match_rejects_a_bare_string_of_patterns():
    """``str`` is a valid ``Sequence[str]``, so iterating one yields single
    CHARACTERS -- one of which is very often ``*``, which matches
    everything. Silently skipping every artifact is the worst possible
    reading of a caller's typo."""
    with pytest.raises(UsageError) as excinfo:
        first_match("docs/*", "CLAUDE.md")  # type: ignore[arg-type]
    assert excinfo.value.exit_code == 2
    assert excinfo.value.remedy.strip()


def test_first_match_rejects_a_non_string_pattern_entry():
    with pytest.raises(UsageError):
        first_match((123,), "CLAUDE.md")  # type: ignore[list-item]


# --- first_match / fs._matches agreement -----------------------------------

_AGREEMENT_PATTERNS = (
    "docs/*",
    "docs/**",
    "docs/dreams/*.md",
    "*.md",
    "*",
    "CLAUDE.md",
    "claude.md",
    "_bmad-output/projects/*/planning-artifacts/**",
    "no-match-for-anything-here",
    # Padded, deliberately: `NeverWrite` strips at construction, so this is
    # the one input class where a non-stripping `first_match` would silently
    # disagree with `fs._matches` -- and disagree by matching NOTHING.
    "  docs/*  ",
    " CLAUDE.md",
)

_AGREEMENT_PATHS = (
    "docs/a.md",
    "docs/nested/deep/b.md",
    "docs/dreams/x.md",
    "CLAUDE.md",
    "claude.md",
    "src/pyforge/marshal/seed/fs.py",
    "_bmad-output/projects/p/planning-artifacts/specs/s.md",
    "",
)


@pytest.mark.parametrize("pattern", _AGREEMENT_PATTERNS)
@pytest.mark.parametrize("path", _AGREEMENT_PATHS)
def test_first_match_agrees_with_fs_matches_on_every_pattern_and_path(pattern: str, path: str):
    """A skip glob and a never-write glob are the same KIND of rule, so
    they must not answer the same ``(pattern, path)`` question two different
    ways. ``fs._matches`` lives in a module this story may not edit and is
    module-private, so the two implementations are duplicated deliberately
    and pinned here instead -- the same guard-an-intentional-duplication
    pattern ``tests/meta/test_supervisor_run_path_agreement.py`` already
    uses."""
    assert first_match((pattern,), path) == _matches(NeverWrite(patterns=(pattern,)), path)


def test_the_agreement_table_is_not_vacuous():
    """Non-vacuous proof: the shared table must produce BOTH matches and
    non-matches, or the parametrized agreement above would pass by never
    exercising a real hit."""
    results = [first_match((pattern,), path) for pattern in _AGREEMENT_PATTERNS for path in _AGREEMENT_PATHS]
    assert any(result is not None for result in results)
    assert any(result is None for result in results)


# --- record_skip -----------------------------------------------------------


def test_record_skip_appends_a_new_pattern_preserving_order():
    assert record_skip(("a/*",), "b/*") == ("a/*", "b/*")


def test_record_skip_onto_an_empty_tuple_returns_a_single_entry():
    assert record_skip((), "a/*") == ("a/*",)


def test_record_skip_does_not_record_a_duplicate():
    assert record_skip(("a/*",), "a/*") == ("a/*",)


def test_record_skip_strips_before_comparing_so_a_padded_duplicate_is_still_a_duplicate():
    assert record_skip(("a/*",), "  a/*  ") == ("a/*",)


def test_record_skip_treats_an_already_stored_padded_entry_as_the_same_rule():
    """Both sides are compared stripped -- otherwise a padded entry from a
    hand-edited state file would let the same rule be recorded again on
    every run, growing the list by one dead entry each time."""
    assert record_skip((" a/* ",), "a/*") == (" a/* ",)


def test_record_skip_rejects_a_bare_string_of_existing_patterns():
    with pytest.raises(UsageError):
        record_skip("a/*", "b/*")  # type: ignore[arg-type]


def test_record_skip_stores_the_stripped_pattern():
    """A padded pattern is non-blank yet matches no real path -- it would
    look like an active rule while protecting nothing (the same failure
    ``NeverWrite.__post_init__``'s own strip closes)."""
    assert record_skip((), "  docs/*  ") == ("docs/*",)


def test_record_skip_never_mutates_its_argument():
    original = ("a/*",)
    record_skip(original, "b/*")
    assert original == ("a/*",)


@pytest.mark.parametrize("blank", ["", "   ", "\t", "\n"])
def test_record_skip_rejects_a_blank_pattern_with_usage_error(blank: str):
    with pytest.raises(UsageError) as excinfo:
        record_skip((), blank)
    assert excinfo.value.exit_code == 2
    assert excinfo.value.remedy.strip()


def test_record_skip_rejects_a_non_string_pattern_with_usage_error():
    with pytest.raises(UsageError):
        record_skip((), 42)  # type: ignore[arg-type]


# --- apply_skips -----------------------------------------------------------


def test_apply_skips_matching_one_action_moves_exactly_that_one():
    result = apply_skips(_three_action_plan(), ("CLAUDE.md",))

    assert [action.artifact_id for action in result.actions] == ["a", "b"]
    assert result.skipped == (SkippedArtifact(artifact_id="c", target_path="CLAUDE.md", pattern="CLAUDE.md"),)


def test_apply_skips_drops_the_skipped_artifacts_hash_pair_from_the_fingerprint():
    """An apply runner cross-checks ``artifact_hashes`` against ``actions``
    in BOTH directions -- a hashed id carrying no action is an integrity
    failure that refuses the whole plan -- so filtering only one side would
    produce a plan every subsequent apply rejects as corrupt."""
    result = apply_skips(_three_action_plan(), ("CLAUDE.md",))

    assert result.repo_fingerprint.artifact_hashes == (("a", "aaaaaaaa"), ("b", "bbbbbbbb"))
    assert {pair[0] for pair in result.repo_fingerprint.artifact_hashes} == {
        action.artifact_id for action in result.actions
    }


def test_apply_skips_carries_the_rest_of_the_fingerprint_through_unchanged():
    plan = _three_action_plan()
    result = apply_skips(plan, ("CLAUDE.md",))

    assert result.repo_fingerprint.git_head == plan.repo_fingerprint.git_head
    assert result.repo_fingerprint.dirty == plan.repo_fingerprint.dirty


def test_apply_skips_matching_every_action_empties_actions_and_names_them_all():
    """A plan whose every action was skipped is a legitimate no-op run
    (AD-60 defines idempotence as plan-emptiness), never a failure."""
    result = apply_skips(_three_action_plan(), ("*",))

    assert result.actions == ()
    assert [entry.artifact_id for entry in result.skipped] == ["a", "b", "c"]
    assert result.repo_fingerprint.artifact_hashes == ()


def test_apply_skips_matching_nothing_returns_a_plan_equal_to_the_input():
    plan = _three_action_plan()
    assert apply_skips(plan, ("nothing/matches/this",)) == plan


def test_apply_skips_with_no_patterns_at_all_returns_a_plan_equal_to_the_input():
    plan = _three_action_plan()
    assert apply_skips(plan, ()) == plan


def test_apply_skips_is_idempotent():
    """The second pass finds nothing left in ``actions`` to match, so a
    rebuild-from-actions-only would silently empty ``skipped`` again --
    quietly un-skipping what the first pass skipped."""
    plan = _three_action_plan()
    once = apply_skips(plan, ("docs/*",))
    twice = apply_skips(once, ("docs/*",))

    assert twice == once
    assert twice.skipped == once.skipped
    assert twice.repo_fingerprint == once.repo_fingerprint


def test_apply_skips_records_the_first_matching_pattern_when_two_patterns_match():
    result = apply_skips(_three_action_plan(), ("docs/*", "docs/a.md"))

    matched = {entry.artifact_id: entry.pattern for entry in result.skipped}
    assert matched == {"a": "docs/*", "b": "docs/*"}


def test_apply_skips_preserves_the_relative_order_of_surviving_actions():
    plan = _three_action_plan()
    result = apply_skips(plan, ("docs/nested/*",))

    assert [action.artifact_id for action in result.actions] == ["a", "c"]


def test_apply_skips_sorts_skipped_by_artifact_id():
    result = apply_skips(_three_action_plan(), ("CLAUDE.md", "docs/*"))

    assert [entry.artifact_id for entry in result.skipped] == ["a", "b", "c"]


def test_apply_skips_merges_a_second_disjoint_skip_into_the_existing_skipped_tuple():
    plan = _three_action_plan()
    once = apply_skips(plan, ("CLAUDE.md",))
    twice = apply_skips(once, ("docs/a.md",))

    assert [entry.artifact_id for entry in twice.skipped] == ["a", "c"]
    assert [action.artifact_id for action in twice.actions] == ["b"]
    assert twice.repo_fingerprint.artifact_hashes == (("b", "bbbbbbbb"),)


def test_apply_skips_never_mutates_the_input_plan():
    plan = _three_action_plan()
    apply_skips(plan, ("*",))

    assert [action.artifact_id for action in plan.actions] == ["a", "b", "c"]
    assert plan.skipped == ()
    assert len(plan.repo_fingerprint.artifact_hashes) == 3


def test_apply_skips_on_an_empty_plan_is_a_no_op():
    plan = Plan(actions=(), repo_fingerprint=_fingerprint(artifact_hashes=()))
    assert apply_skips(plan, ("*",)) == plan


def test_apply_skips_honours_a_padded_pattern_rather_than_silently_skipping_nothing():
    result = apply_skips(_three_action_plan(), (" docs/* ",))

    assert [action.artifact_id for action in result.actions] == ["c"]
    assert [entry.pattern for entry in result.skipped] == ["docs/*", "docs/*"]


def test_apply_skips_rejects_a_bare_string_of_patterns():
    """The catastrophic typo: iterating a bare ``str`` yields characters,
    one of which is ``*`` -- so this would otherwise empty ``actions``
    entirely and produce a plan that applies as a successful no-op."""
    with pytest.raises(UsageError):
        apply_skips(_three_action_plan(), "docs/*")  # type: ignore[arg-type]


def test_apply_skips_rejects_a_non_string_pattern_entry():
    """``state.skips[]`` is YAML, where a bare ``- 123`` decodes as an
    ``int`` -- which ``fnmatch`` would report as an opaque ``TypeError``
    naming neither skips nor patterns."""
    with pytest.raises(UsageError):
        apply_skips(_three_action_plan(), (123,))  # type: ignore[list-item]


def test_apply_skips_validates_its_patterns_even_when_there_is_nothing_to_match():
    """Validation reached only through ``first_match`` was DATA-dependent:
    with no actions the loop never ran, so the bare-``str`` typo the
    validator exists to catch returned cleanly and the caller learned
    nothing (review finding). An empty plan is exactly the shape a
    previous ``--skip`` leaves behind."""
    plan = Plan(actions=(), repo_fingerprint=_fingerprint(artifact_hashes=()))

    with pytest.raises(UsageError) as excinfo:
        apply_skips(plan, "docs/*")  # type: ignore[arg-type]
    assert excinfo.value.exit_code == 2
    assert excinfo.value.remedy.strip()


def test_apply_skips_reads_a_one_shot_iterable_of_patterns_exactly_once():
    """``patterns`` used to be consumed by the validator and then
    re-consumed per action, so with a generator only the first action saw a
    non-empty pattern list -- every later one was silently matched against
    nothing."""
    result = apply_skips(_three_action_plan(), (pattern for pattern in ("docs/*",)))

    assert [action.artifact_id for action in result.actions] == ["c"]
    assert [entry.artifact_id for entry in result.skipped] == ["a", "b"]


def test_record_skip_reads_a_one_shot_iterable_of_patterns_exactly_once():
    """``record_skip((p for p in ("a/*", "b/*")), "c/*")`` returned
    ``("c/*",)`` -- both existing skips silently discarded, because the
    generator was exhausted by the validation pass before the result was
    built from it (review finding)."""
    patterns = (pattern for pattern in ("a/*", "b/*"))

    assert record_skip(patterns, "c/*") == ("a/*", "b/*", "c/*")  # type: ignore[arg-type]


@pytest.mark.parametrize("blank", ["", "   ", "\t", "\n"])
def test_first_match_rejects_a_whitespace_only_pattern(blank: str):
    """A pattern that is blank once stripped matches NOTHING -- the precise
    "silently protects nothing while looking like a rule" failure the strip
    itself exists to prevent. Both siblings already reject this shape
    (``NeverWrite.__post_init__``, and ``record_skip`` for its own new
    pattern), so accepting it here was the odd one out."""
    with pytest.raises(UsageError) as excinfo:
        first_match((blank,), "docs/a.md")
    assert excinfo.value.exit_code == 2
    assert excinfo.value.remedy.strip()


def test_first_match_never_returns_a_falsy_non_none_value():
    """``first_match(("",), "")`` returned ``""`` -- a FALSY non-``None``
    sentinel that any ``if first_match(...)`` caller would read as a miss,
    turning a matched skip into an unskipped write."""
    with pytest.raises(UsageError):
        first_match(("",), "")


def test_record_skip_rejects_a_whitespace_only_stored_pattern():
    with pytest.raises(UsageError):
        record_skip(("   ",), "docs/*")


def test_apply_skips_rejects_a_whitespace_only_pattern():
    with pytest.raises(UsageError):
        apply_skips(_three_action_plan(), ("docs/*", "  "))


# --- lexical path normalization (skip vs never-write agreement) -------------


def _one_action_plan(target_path: str) -> Plan:
    return Plan(
        actions=(_action(artifact_id="a", target_path=target_path),),
        repo_fingerprint=_fingerprint(artifact_hashes=(("a", "aaaaaaaa"),)),
    )


def test_apply_skips_matches_a_dot_slash_prefixed_target_path():
    """The never-write rung matches the RESOLVED repo-relative string, so it
    refuses ``./AGENTS.md`` naming ``resolved: 'AGENTS.md'`` -- an operator
    who copies that pattern into ``--skip`` must not get silence (review
    finding). Skip matching is lexical, so the normalization closes exactly
    the cosmetic difference."""
    result = apply_skips(_one_action_plan("./AGENTS.md"), ("AGENTS.md",))

    assert result.actions == ()
    assert result.skipped == (SkippedArtifact(artifact_id="a", target_path="./AGENTS.md", pattern="AGENTS.md"),)


def test_apply_skips_matches_a_target_path_with_duplicate_separators():
    result = apply_skips(_one_action_plan("docs//a.md"), ("docs/a.md",))

    assert [entry.artifact_id for entry in result.skipped] == ["a"]


def test_apply_skips_records_the_declared_target_path_not_the_normalized_one():
    """Normalization decides the MATCH only -- ``plan.json`` must still show
    the path the manifest actually declares."""
    result = apply_skips(_one_action_plan(".//docs/a.md"), ("docs/a.md",))

    assert result.skipped[0].target_path == ".//docs/a.md"


def test_apply_skips_leaves_a_dot_dot_segment_alone():
    """Collapsing ``..`` lexically is a claim about the filesystem
    (``a/../b`` is ``b`` only when ``a`` is not a symlink) and this module
    has no disk access to check it -- that is the resolution-based rung's
    job, not this one's."""
    result = apply_skips(_one_action_plan("docs/../AGENTS.md"), ("AGENTS.md",))

    assert result.skipped == ()
    assert [action.artifact_id for action in result.actions] == ["a"]


# --- future-field survival (dataclasses.replace) ---------------------------


def test_apply_skips_carries_an_unknown_repo_fingerprint_field_through():
    """A field-by-field rebuild silently DROPS any field a future story adds
    -- data loss with no error and no failing test at the moment it lands.
    A subclass stands in for that future field here."""

    @dataclasses.dataclass(frozen=True)
    class _FutureFingerprint(RepoFingerprint):
        provenance: str = "recorded-by-a-later-story"

    plan = Plan(
        actions=_three_action_plan().actions,
        repo_fingerprint=_FutureFingerprint(
            git_head="abc123",
            dirty=False,
            artifact_hashes=(("a", "aaaaaaaa"), ("b", "bbbbbbbb"), ("c", "cccccccc")),
        ),
    )

    result = apply_skips(plan, ("CLAUDE.md",))

    assert isinstance(result.repo_fingerprint, _FutureFingerprint)
    assert result.repo_fingerprint.provenance == "recorded-by-a-later-story"
    assert result.repo_fingerprint.artifact_hashes == (("a", "aaaaaaaa"), ("b", "bbbbbbbb"))


def test_apply_skips_carries_an_unknown_plan_field_through():
    @dataclasses.dataclass(frozen=True)
    class _FuturePlan(Plan):
        rendered_at: str = "2026-08-14T00:00:00Z"

    plan = _FuturePlan(
        actions=_three_action_plan().actions,
        repo_fingerprint=_fingerprint(),
    )

    result = apply_skips(plan, ("CLAUDE.md",))

    assert isinstance(result, _FuturePlan)
    assert result.rendered_at == "2026-08-14T00:00:00Z"
    assert [action.artifact_id for action in result.actions] == ["a", "b"]


# --- managed_after_skips (the skip <-> rung-6 seam) -------------------------


def _record(artifact_id: str) -> ManagedRecord:
    return ManagedRecord(artifact_id=artifact_id, path=f"{artifact_id}.md", body_sha="deadbeef")


def test_managed_after_skips_drops_the_records_for_skipped_artifacts():
    """Without this filter ``--skip`` cannot protect a hand-edit at all:
    rung 6 checks every record it is handed, so the skipped artifact stays
    refused and the refusal's only offered remedy is ``--force``, which
    discards every hand-edit including the one being protected."""
    plan = apply_skips(_three_action_plan(), ("docs/a.md",))
    records = (_record("a"), _record("b"), _record("c"))

    assert managed_after_skips(records, plan) == (_record("b"), _record("c"))


def test_managed_after_skips_preserves_the_callers_record_order():
    plan = apply_skips(_three_action_plan(), ("CLAUDE.md",))
    records = (_record("c"), _record("b"), _record("a"))

    assert [record.artifact_id for record in managed_after_skips(records, plan)] == ["b", "a"]


def test_managed_after_skips_keeps_every_record_when_nothing_was_skipped():
    plan = _three_action_plan()
    records = (_record("a"), _record("b"))

    assert managed_after_skips(records, plan) == records


def test_managed_after_skips_keeps_a_record_the_plan_never_mentions():
    """State legitimately records artifacts this plan has no action for --
    that is the whole reason rung 6 iterates records rather than actions."""
    plan = apply_skips(_three_action_plan(), ("docs/a.md",))

    assert managed_after_skips((_record("unmentioned"),), plan) == (_record("unmentioned"),)


def test_managed_after_skips_never_mutates_its_arguments():
    plan = apply_skips(_three_action_plan(), ("*",))
    records = (_record("a"), _record("b"), _record("c"))

    managed_after_skips(records, plan)

    assert [record.artifact_id for record in records] == ["a", "b", "c"]
    assert [entry.artifact_id for entry in plan.skipped] == ["a", "b", "c"]


def test_a_skipped_plan_round_trips_through_json():
    """The whole point of putting skips in the `Plan` rather than in a
    rendering: they must survive into the serialized artifact a human
    reviews as a diff."""
    result = apply_skips(_three_action_plan(), ("docs/*",))
    restored = Plan.from_json_dict(json.loads(json.dumps(result.to_json_dict())))

    assert restored == result
    assert isinstance(restored.skipped, tuple)
    assert all(isinstance(entry, SkippedArtifact) for entry in restored.skipped)
