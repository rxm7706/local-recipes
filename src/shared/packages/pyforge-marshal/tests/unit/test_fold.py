"""Unit tests for ``pyforge.marshal.core.journal.fold`` (Story 3.2,
AD-26/AD-28/AD-30) -- the full I/O & Edge-Case Matrix, ``intent``/
``outcome`` pairing (including the self-referencing-outcome case that
closes Story 3.1's deferred-work gap), quarantine scoping, and synthetic
coverage of the 9 illustrative "accumulating run state" domains the epic
names (story transitions, gate verdicts, escalations, deferrals,
consumption, supervisor actions, frozen surfaces, attempt counts, gate
mode) proving the generic ``by_kind``/``for_story``/``is_evaluable``
mechanism handles all of them structurally -- none has a real writer yet.
"""

from __future__ import annotations

import json

import pytest

from pyforge.marshal.core import verdict
from pyforge.marshal.core.identity import StoryKey
from pyforge.marshal.core.journal import (
    FoldResult,
    JournalEntry,
    JournalEntryId,
    Phase,
    QuarantinedRecord,
    build_entry,
    fold,
    prepare_for_write,
)
from pyforge.marshal.core.model import Finding, Severity, Verdict


def _valid_id(counter: int = 0, writer_id: str = "cli-1") -> JournalEntryId:
    return JournalEntryId(writer_id=writer_id, counter=counter)


def _ts(n: int = 0) -> str:
    return f"2026-08-03T05:45:{12 + n:02d}.123Z"


def _line(entry: JournalEntry) -> str:
    return json.dumps(entry.to_json_dict())


# --- fold(): the bare-str guard -------------------------------------------


def test_fold_rejects_bare_str_for_lines():
    with pytest.raises(TypeError, match="lines"):
        fold("not-a-list")  # type: ignore[arg-type]


def test_fold_rejects_a_non_mapping_sidecars():
    """Review finding, verified live: `fold(lines, sidecars=None)` used to
    raise an unguarded AttributeError the instant any line needed sidecar
    resolution, aborting the whole fold -- mirrors `core.policy.compose`'s
    own contract-violation guard on its Mapping-typed parameters."""
    with pytest.raises(TypeError, match="sidecars"):
        fold([], sidecars=None)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="sidecars"):
        fold([], sidecars="not-a-mapping")  # type: ignore[arg-type]


def test_deeply_nested_json_line_is_quarantined_not_a_crash():
    """Review finding, verified live: `json.loads` on an adversarially deep
    line raises RecursionError, a RuntimeError subclass a bare
    (ValueError, TypeError) catch does not see -- the exact "one bad line
    must never abort the whole fold" guarantee this module promises."""
    deeply_nested = "[" * 200_000 + "]" * 200_000
    result = fold([deeply_nested])
    assert result.entries == ()
    assert len(result.quarantined) == 1
    assert result.quarantined[0].finding.code == "MRS-JOURNAL-001"


def test_fold_of_empty_lines_returns_an_empty_result():
    result = fold([])
    assert result == FoldResult(
        entries=(), open_intents=(), orphaned_outcomes=(), quarantined=()
    )
    assert result.is_evaluable(None, None) is True


# --- intent/outcome pairing: the I/O & Edge-Case Matrix --------------------


def test_matched_intent_and_outcome_both_appear_in_entries_intent_not_open():
    intent = build_entry(
        id=_valid_id(counter=0),
        ts=_ts(0),
        run_id="run-1",
        kind="gate-verdict",
        phase=Phase.INTENT,
        payload={},
    )
    outcome = build_entry(
        id=_valid_id(counter=1),
        ts=_ts(1),
        run_id="run-1",
        kind="gate-verdict",
        phase=Phase.OUTCOME,
        intent_id=_valid_id(counter=0),
        payload={"verdict": "clean"},
    )
    result = fold([_line(intent), _line(outcome)])
    assert intent in result.entries
    assert outcome in result.entries
    assert intent not in result.open_intents
    assert outcome not in result.orphaned_outcomes


def test_lone_unmatched_intent_appears_in_open_intents():
    intent = build_entry(
        id=_valid_id(),
        ts=_ts(0),
        run_id="run-1",
        kind="run-started",
        phase=Phase.INTENT,
        payload={},
    )
    result = fold([_line(intent)])
    assert result.entries == (intent,)
    assert result.open_intents == (intent,)
    assert result.orphaned_outcomes == ()


def test_orphaned_outcome_with_no_matching_intent_appears_in_orphaned_outcomes():
    outcome = build_entry(
        id=_valid_id(counter=1),
        ts=_ts(0),
        run_id="run-1",
        kind="gate-verdict",
        phase=Phase.OUTCOME,
        intent_id=_valid_id(counter=99),
        payload={},
    )
    result = fold([_line(outcome)])
    assert result.entries == (outcome,)
    assert result.orphaned_outcomes == (outcome,)
    assert result.open_intents == ()


def test_self_referencing_outcome_appears_in_orphaned_outcomes():
    """Closes the Story 3.1 review's deferred self-reference gap
    (deferred-work.md, ``intent_id == id``): ``build_entry`` constructs it
    without error, but ``fold``'s id-keyed pairing never finds a matching
    ``intent``-phase entry for it -- an intent's own id is never looked up
    among ``outcome``-phase entries, so a self-reference can never
    accidentally match itself."""
    self_id = _valid_id(counter=5)
    outcome = build_entry(
        id=self_id,
        ts=_ts(0),
        run_id="run-1",
        kind="gate-verdict",
        phase=Phase.OUTCOME,
        intent_id=self_id,
        payload={},
    )
    result = fold([_line(outcome)])
    assert result.orphaned_outcomes == (outcome,)
    assert result.open_intents == ()


def test_pairing_is_by_id_alone_not_position_or_adjacency():
    """Two intents, one outcome referencing the SECOND intent's id even
    though it appears first in the line order -- proves pairing reads
    ``intent_id`` exclusively, never positional/ordinal adjacency."""
    first_intent = build_entry(
        id=_valid_id(counter=0), ts=_ts(0), run_id="run-1", kind="k", phase=Phase.INTENT, payload={}
    )
    second_intent = build_entry(
        id=_valid_id(counter=1), ts=_ts(1), run_id="run-1", kind="k", phase=Phase.INTENT, payload={}
    )
    outcome = build_entry(
        id=_valid_id(counter=2),
        ts=_ts(2),
        run_id="run-1",
        kind="k",
        phase=Phase.OUTCOME,
        intent_id=_valid_id(counter=1),
        payload={},
    )
    result = fold([_line(outcome), _line(first_intent), _line(second_intent)])
    assert result.open_intents == (first_intent,)
    assert result.orphaned_outcomes == ()


# --- AD-28 total order ------------------------------------------------------


def test_entries_are_sorted_by_ad28_total_order_regardless_of_input_order():
    early = build_entry(
        id=_valid_id(writer_id="cli-1", counter=0),
        ts=_ts(0),
        run_id="run-1",
        kind="run-started",
        phase=Phase.INTENT,
        payload={},
    )
    late = build_entry(
        id=_valid_id(writer_id="cli-1", counter=1),
        ts=_ts(1),
        run_id="run-1",
        kind="story-transition",
        phase=Phase.OBSERVATION,
        payload={},
    )
    result = fold([_line(late), _line(early)])
    assert result.entries == (early, late)


def test_entries_tie_break_by_writer_id_then_counter_at_equal_ts():
    a = build_entry(
        id=_valid_id(writer_id="cli-1", counter=5),
        ts=_ts(0),
        run_id="run-1",
        kind="k",
        phase=Phase.OBSERVATION,
        payload={},
    )
    b = build_entry(
        id=_valid_id(writer_id="cli-2", counter=0),
        ts=_ts(0),
        run_id="run-1",
        kind="k",
        phase=Phase.OBSERVATION,
        payload={},
    )
    result = fold([_line(b), _line(a)])
    assert result.entries == (a, b)


# --- malformed JSON: the I/O & Edge-Case Matrix ----------------------------


def test_malformed_json_line_is_quarantined_scoped_to_whole_run():
    result = fold(["not-json{"])
    assert result.entries == ()
    assert len(result.quarantined) == 1
    record = result.quarantined[0]
    assert record.story is None
    assert record.kind is None
    assert record.finding.code == "MRS-JOURNAL-001"
    assert result.is_evaluable(None, None) is False


def test_quarantined_finding_carries_path_back_to_the_raw_line():
    """Review finding, verified live: mirrors core.identity's own
    MRS-IDENT-001/002 convention of threading the offending raw input into
    Finding.path, so a Finding pulled out of QuarantinedRecord.finding in
    isolation still names what failed."""
    result = fold(["not-json{"])
    assert result.quarantined[0].finding.path == "not-json{"


def test_fold_quarantines_a_non_str_element_without_aborting_the_fold():
    good = build_entry(
        id=_valid_id(), ts=_ts(0), run_id="run-1", kind="run-started", phase=Phase.INTENT, payload={}
    )
    result = fold([123, _line(good)])  # type: ignore[list-item]
    assert good in result.entries
    assert len(result.quarantined) == 1
    assert result.quarantined[0].finding.code == "MRS-JOURNAL-001"


# --- valid JSON, invalid shape: the I/O & Edge-Case Matrix -----------------


def test_invalid_shape_with_recoverable_story_and_kind_scopes_narrowly():
    document = {
        "id": {"writer_id": "cli-1", "counter": 0},
        "ts": _ts(0),
        "kind": "gate-verdict",
        "story": "3.1",
        "phase": "observation",
        "payload": {},
        # run_id deliberately omitted -- an otherwise-valid shape failure.
    }
    result = fold([json.dumps(document)])
    assert result.entries == ()
    assert len(result.quarantined) == 1
    record = result.quarantined[0]
    assert record.story == StoryKey(epic=3, seq=1)
    assert record.kind == "gate-verdict"
    assert record.finding.code == "MRS-JOURNAL-001"


def test_other_stories_and_kinds_stay_evaluable_when_one_line_quarantines():
    bad_document = {
        "id": {"writer_id": "cli-1", "counter": 0},
        "ts": _ts(0),
        "kind": "gate-verdict",
        "story": "3.1",
        "phase": "observation",
        "payload": {},
    }
    good = build_entry(
        id=_valid_id(counter=1),
        ts=_ts(1),
        run_id="run-1",
        kind="story-transition",
        phase=Phase.OBSERVATION,
        story=StoryKey(epic=4, seq=1),
        payload={},
    )
    result = fold([json.dumps(bad_document), _line(good)])
    assert good in result.entries
    assert result.is_evaluable(StoryKey(epic=4, seq=1), "story-transition") is True
    assert result.is_evaluable(StoryKey(epic=3, seq=1), "gate-verdict") is False


def test_shape_failure_with_only_kind_recoverable_widens_to_whole_run():
    """AD-30's Design Notes: a line recovering ONE of story/kind but not
    the other still cannot be narrowly scoped -- no meaningful partial
    key -- so it widens to (None, None) exactly like recovering neither."""
    document = {
        "id": {"writer_id": "cli-1", "counter": 0},
        "ts": _ts(0),
        "kind": "run-started",
        "phase": "intent",
        "payload": {},
        # run_id missing (shape failure) AND no story field at all.
    }
    result = fold([json.dumps(document)])
    assert len(result.quarantined) == 1
    record = result.quarantined[0]
    assert record.story is None
    assert record.kind is None
    assert result.is_evaluable(None, None) is False


# --- sidecar resolution: the I/O & Edge-Case Matrix ------------------------


@pytest.mark.parametrize("blob_is_none", [False, True], ids=["absent", "none-valued"])
def test_missing_or_none_sidecar_blob_is_quarantined(blob_is_none):
    """Both unresolvable-blob spellings quarantine MRS-JOURNAL-002: the path
    absent from `sidecars` entirely, and the path present but mapped to
    `None` (the caller could not read it).

    The None-valued case derives its key from `prepared.sidecar_relative_path`
    rather than hardcoding `blobs/cli-1-9.json` (review finding): a hardcoded
    path silently degenerates into a duplicate of the absent case if
    `prepare_for_write`'s naming convention ever changes, leaving this branch
    untested with no failing test to signal it."""
    entry = build_entry(
        id=_valid_id(counter=9),
        ts=_ts(0),
        run_id="run-1",
        kind="run-started",
        phase=Phase.INTENT,
        story=StoryKey(epic=3, seq=1),
        payload={"data": "x" * 5000},
    )
    prepared = prepare_for_write(entry)
    sidecars = {prepared.sidecar_relative_path: None} if blob_is_none else {}
    result = fold([prepared.line], sidecars=sidecars)
    assert result.entries == ()
    assert len(result.quarantined) == 1
    record = result.quarantined[0]
    assert record.finding.code == "MRS-JOURNAL-002"
    assert record.story == StoryKey(epic=3, seq=1)
    assert record.kind == "run-started"


def test_sidecar_blob_that_is_not_valid_json_is_quarantined():
    entry = build_entry(
        id=_valid_id(counter=9),
        ts=_ts(0),
        run_id="run-1",
        kind="run-started",
        phase=Phase.INTENT,
        payload={"data": "x" * 5000},
    )
    prepared = prepare_for_write(entry)
    result = fold(
        [prepared.line], sidecars={prepared.sidecar_relative_path: "not-json{"}
    )
    assert result.entries == ()
    assert result.quarantined[0].finding.code == "MRS-JOURNAL-002"


def test_sidecar_blob_that_decodes_to_a_non_object_is_quarantined():
    """The third documented `_SidecarUnresolved` failure mode: the blob text
    IS valid JSON but decodes to something other than a JSON object (here, a
    list) -- `replace(entry, payload=...)` then fails `JournalEntry`'s own
    `payload must be a Mapping` check, which must surface as MRS-JOURNAL-002,
    not an uncaught ValueError escaping the fold."""
    entry = build_entry(
        id=_valid_id(counter=9),
        ts=_ts(0),
        run_id="run-1",
        kind="run-started",
        phase=Phase.INTENT,
        payload={"data": "x" * 5000},
    )
    prepared = prepare_for_write(entry)
    result = fold(
        [prepared.line], sidecars={prepared.sidecar_relative_path: "[1, 2, 3]"}
    )
    assert result.entries == ()
    assert result.quarantined[0].finding.code == "MRS-JOURNAL-002"


def test_sidecar_present_and_valid_restores_the_original_payload():
    payload = {"data": "x" * 5000}
    entry = build_entry(
        id=_valid_id(counter=9),
        ts=_ts(0),
        run_id="run-1",
        kind="run-started",
        phase=Phase.INTENT,
        payload=payload,
    )
    prepared = prepare_for_write(entry)
    result = fold(
        [prepared.line],
        sidecars={prepared.sidecar_relative_path: prepared.sidecar_content},
    )
    assert result.quarantined == ()
    assert len(result.entries) == 1
    assert result.entries[0].payload == payload


def test_inline_payload_with_only_a_sidecar_ref_key_but_no_sidecar_needed_is_untouched():
    """A payload naturally small enough to inline never goes through
    sidecar resolution at all -- only the exact ``{"sidecar_ref": <str>}``
    shape ``prepare_for_write`` emits triggers it."""
    entry = build_entry(
        id=_valid_id(),
        ts=_ts(0),
        run_id="run-1",
        kind="run-started",
        phase=Phase.INTENT,
        payload={"a": 1},
    )
    result = fold([_line(entry)])
    assert result.entries == (entry,)
    assert result.quarantined == ()


# --- by_kind/for_story/is_evaluable: the generic query surface -------------


def test_by_kind_and_for_story_return_empty_tuple_when_nothing_matches():
    entry = build_entry(
        id=_valid_id(), ts=_ts(0), run_id="run-1", kind="run-started", phase=Phase.INTENT, payload={}
    )
    result = fold([_line(entry)])
    assert result.by_kind("nope") == ()
    assert result.for_story(StoryKey(epic=9, seq=9)) == ()


def test_is_evaluable_is_false_for_everything_once_the_whole_run_quarantines():
    result = fold(["not-json"])
    assert result.is_evaluable(None, None) is False
    assert result.is_evaluable(StoryKey(epic=1, seq=1), "anything") is False


def test_is_evaluable_rejects_an_asymmetric_story_kind_pair():
    """Review finding, verified live: no QuarantinedRecord ever scopes
    asymmetrically (its own invariant forbids it), so a caller asking
    `is_evaluable(story, None)` got a silent, always-True answer that could
    never actually match a real per-(story, kind) quarantine."""
    result = fold([])
    with pytest.raises(ValueError, match="both None or both set"):
        result.is_evaluable(StoryKey(epic=1, seq=1), None)
    with pytest.raises(ValueError, match="both None or both set"):
        result.is_evaluable(None, "some-kind")


# --- synthetic coverage of the 9 illustrative run-state domains ------------
#
# None of these kinds has a real writer yet (the epic's own Never clause) --
# these are SYNTHETIC fixtures proving the generic by_kind/for_story/
# is_evaluable mechanism handles every domain structurally, mirroring
# core/policy.py's own "mechanism proven synthetically" precedent.


@pytest.mark.parametrize(
    "kind",
    [
        "story-transition",  # story transitions
        "gate-verdict",  # gate verdicts
        "escalation-raised",  # escalations
        "deferral-recorded",  # deferrals
        "consumption-sample",  # consumption
        "supervisor-action",  # supervisor actions
        "freeze-declared",  # frozen surfaces
        "attempt-count",  # attempt counts
        "gate-mode-changed",  # effective gate mode
    ],
)
def test_by_kind_and_for_story_handle_every_illustrative_run_state_domain(kind):
    story = StoryKey(epic=3, seq=2)
    entry = build_entry(
        id=_valid_id(),
        ts=_ts(0),
        run_id="run-1",
        kind=kind,
        phase=Phase.OBSERVATION,
        story=story,
        payload={"kind": kind},
    )
    result = fold([_line(entry)])
    assert result.by_kind(kind) == (entry,)
    assert result.for_story(story) == (entry,)
    assert result.is_evaluable(story, kind) is True


# --- QuarantinedRecord/FoldResult: construction invariants -----------------


def test_quarantined_record_rejects_only_one_of_story_kind_set():
    with pytest.raises(ValueError, match="both None or both set together"):
        QuarantinedRecord(
            raw="{}",
            story=StoryKey(epic=1, seq=1),
            kind=None,
            finding=Finding(code="MRS-JOURNAL-001", severity=Severity.ERROR, message="x"),
        )


def test_quarantined_record_rejects_non_str_raw():
    with pytest.raises(ValueError, match="raw"):
        QuarantinedRecord(
            raw=123,  # type: ignore[arg-type]
            story=None,
            kind=None,
            finding=Finding(code="MRS-JOURNAL-001", severity=Severity.ERROR, message="x"),
        )


def test_quarantined_record_rejects_non_finding():
    with pytest.raises(ValueError, match="finding"):
        QuarantinedRecord(raw="{}", story=None, kind=None, finding="not-a-finding")  # type: ignore[arg-type]


def test_fold_result_rejects_non_journal_entry_in_entries():
    with pytest.raises(ValueError, match="entries"):
        FoldResult(
            entries=("not-an-entry",),  # type: ignore[arg-type]
            open_intents=(),
            orphaned_outcomes=(),
            quarantined=(),
        )


def test_fold_result_rejects_non_quarantined_record_in_quarantined():
    with pytest.raises(ValueError, match="quarantined"):
        FoldResult(
            entries=(),
            open_intents=(),
            orphaned_outcomes=(),
            quarantined=("not-a-record",),  # type: ignore[arg-type]
        )


def test_fold_result_rejects_a_non_intent_entry_in_open_intents():
    """Review finding, verified live: type-checking alone let a
    Phase.OUTCOME entry construct cleanly inside open_intents."""
    outcome = build_entry(
        id=_valid_id(counter=1),
        ts=_ts(0),
        run_id="run-1",
        kind="k",
        phase=Phase.OUTCOME,
        intent_id=_valid_id(counter=0),
        payload={},
    )
    with pytest.raises(ValueError, match="open_intents"):
        FoldResult(entries=(outcome,), open_intents=(outcome,), orphaned_outcomes=(), quarantined=())


def test_fold_result_rejects_a_non_outcome_entry_in_orphaned_outcomes():
    intent = build_entry(
        id=_valid_id(), ts=_ts(0), run_id="run-1", kind="k", phase=Phase.INTENT, payload={}
    )
    with pytest.raises(ValueError, match="orphaned_outcomes"):
        FoldResult(entries=(intent,), open_intents=(), orphaned_outcomes=(intent,), quarantined=())


# --- registry/verdict integration ------------------------------------------


def test_mrs_journal_001_is_registered_and_classifies_unevaluable():
    assert verdict.classify("MRS-JOURNAL-001") is Verdict.UNEVALUABLE


def test_mrs_journal_002_is_registered_and_classifies_unevaluable():
    assert verdict.classify("MRS-JOURNAL-002") is Verdict.UNEVALUABLE


# --- review-pass regressions: input guards, blank lines, sidecar binding ----


def test_fold_skips_blank_and_whitespace_only_lines():
    """Review finding, verified live: `FsPort.append_line` owns each line's
    trailing newline, so a journal file always ends in one and the obvious
    caller (`text.split("\n")`) always yields a final `""`. Quarantining that
    terminator artifact recovered no (story, kind), widened to (None, None),
    and made an otherwise perfectly intact run WHOLLY unevaluable."""
    entry = build_entry(
        id=_valid_id(),
        ts=_ts(0),
        run_id="run-1",
        kind="run-started",
        phase=Phase.INTENT,
        story=StoryKey(epic=3, seq=1),
        payload={},
    )
    result = fold([_line(entry), "", "   ", "\t"])
    assert len(result.entries) == 1
    assert result.quarantined == ()
    assert result.is_evaluable(StoryKey(epic=3, seq=1), "run-started") is True
    assert result.is_evaluable(None, None) is True


@pytest.mark.parametrize(
    "bad_lines",
    [b'{"a": 1}', bytearray(b'{"a": 1}'), {"line-a": "line-b"}, None, 42],
    ids=["bytes", "bytearray", "mapping", "none", "int"],
)
def test_fold_rejects_non_sequence_lines(bad_lines):
    """Review finding, verified live: the guard covered only a bare `str`.
    `bytes`/`bytearray` shredded into one quarantine record PER BYTE, a
    Mapping silently folded its KEYS as journal lines with zero signal, and
    `fold(None)`/`fold(42)` died with a bare "'NoneType' object is not
    iterable" naming no contract -- asymmetric with the `sidecars` guard
    added three lines away in the previous review pass."""
    with pytest.raises(TypeError, match="lines"):
        fold(bad_lines)  # type: ignore[arg-type]


def test_sidecar_ref_naming_another_entrys_blob_is_quarantined():
    """Review finding, verified live: `prepare_for_write` derives the blob
    path SOLELY from the entry's own (writer_id, counter), but resolution
    used to honour whatever path the line named -- so entry `cli-1/2` could
    reference `cli-1/1`'s blob and silently adopt that entry's payload, with
    zero quarantine and zero signal, in an append-only artifact whose whole
    value is being tamper-evident."""
    owner = build_entry(
        id=_valid_id(counter=1),
        ts=_ts(0),
        run_id="run-1",
        kind="run-started",
        phase=Phase.INTENT,
        payload={"secret": "x" * 5000},
    )
    prepared = prepare_for_write(owner)
    forged = json.dumps(
        {
            "id": {"writer_id": "cli-1", "counter": 2},
            "ts": _ts(1),
            "run_id": "run-1",
            "kind": "run-started",
            "phase": "observation",
            "payload": {"sidecar_ref": prepared.sidecar_relative_path},
        }
    )
    result = fold(
        [forged], sidecars={prepared.sidecar_relative_path: prepared.sidecar_content}
    )
    assert result.entries == ()
    assert len(result.quarantined) == 1
    assert result.quarantined[0].finding.code == "MRS-JOURNAL-002"


def test_sidecar_ref_using_path_traversal_is_quarantined():
    """Falls out of the same own-blob binding: a ref that is not this
    entry's derived path never resolves, so traversal and absolute refs are
    rejected without a separate path-sanitizing rule."""
    line = json.dumps(
        {
            "id": {"writer_id": "cli-1", "counter": 0},
            "ts": _ts(0),
            "run_id": "run-1",
            "kind": "run-started",
            "phase": "observation",
            "payload": {"sidecar_ref": "../../etc/passwd"},
        }
    )
    result = fold([line], sidecars={"../../etc/passwd": '{"pwned": true}'})
    assert result.entries == ()
    assert result.quarantined[0].finding.code == "MRS-JOURNAL-002"


def test_deeply_nested_sidecar_blob_is_quarantined_as_a_sidecar_failure():
    """Review finding, verified live: a blob nested deeply enough still
    DECODES via `json.loads`, then fails inside `JournalEntry.__post_init__`'s
    own copy.deepcopy/json.dumps with RecursionError. Caught only as
    ValueError, that escaped to `fold`'s outer catch and was reported as
    MRS-JOURNAL-001 -- a LINE parse failure -- defeating the exact
    discrimination the two codes exist to make."""
    entry = build_entry(
        id=_valid_id(counter=9),
        ts=_ts(0),
        run_id="run-1",
        kind="run-started",
        phase=Phase.INTENT,
        payload={"data": "x" * 5000},
    )
    prepared = prepare_for_write(entry)
    deep_blob = '{"d": ' + "[" * 600 + "]" * 600 + "}"
    result = fold([prepared.line], sidecars={prepared.sidecar_relative_path: deep_blob})
    assert result.entries == ()
    assert len(result.quarantined) == 1
    assert result.quarantined[0].finding.code == "MRS-JOURNAL-002"


# --- review-pass regressions: the query surface ----------------------------


def test_is_evaluable_run_scope_is_unaffected_by_a_narrowly_scoped_quarantine():
    """Review finding: this method's docstring used to claim `False` "the
    instant ANY line quarantines". The code has never behaved that way, and
    behaving that way would defeat AD-30's narrow scoping and this story's
    own AC ("records provably unaffected stay evaluable")."""
    good = build_entry(
        id=_valid_id(),
        ts=_ts(0),
        run_id="run-1",
        kind="run-started",
        phase=Phase.INTENT,
        story=StoryKey(epic=3, seq=1),
        payload={},
    )
    narrow = json.dumps(
        {"story": "3.1", "kind": "gate-verdict", "ts": _ts(1)}  # run_id/id missing
    )
    result = fold([_line(good), narrow])
    assert result.quarantined[0].story == StoryKey(epic=3, seq=1)
    assert result.is_evaluable(StoryKey(epic=3, seq=1), "gate-verdict") is False
    assert result.is_evaluable(None, None) is True


@pytest.mark.parametrize("bad_story", ["3.1", None, 31], ids=["str", "none", "int"])
def test_for_story_rejects_a_non_story_key(bad_story):
    """Review finding, verified live: `for_story("3.1")` silently returned
    `()` for a caller passing a raw key string, and `for_story(None)`
    silently returned every run-scoped entry -- both indistinguishable from
    "this story has no entries", and asymmetric with the strict guard
    `is_evaluable` grew three methods away."""
    result = fold([])
    with pytest.raises(TypeError, match="story"):
        result.for_story(bad_story)  # type: ignore[arg-type]


def test_by_kind_rejects_a_non_str_kind():
    result = fold([])
    with pytest.raises(TypeError, match="kind"):
        result.by_kind(None)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("story", "kind"), [("3.1", "k"), (31, "k"), (StoryKey(epic=3, seq=1), 7)]
)
def test_is_evaluable_rejects_wrong_types(story, kind):
    result = fold([])
    with pytest.raises(TypeError):
        result.is_evaluable(story, kind)  # type: ignore[arg-type]
