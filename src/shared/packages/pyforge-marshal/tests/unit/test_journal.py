"""Unit tests for ``pyforge.marshal.core.journal`` (Story 3.1,
AD-25/AD-28/AD-30) -- ``mint_run_id``, ``Phase``, ``JournalEntryId``,
``JournalEntry``/``build_entry``, and ``PreparedWrite``/``prepare_for_write``
across the spec's I/O & Edge-Case Matrix, plus ``jsonschema.validate`` round
trips against the packaged ``schemas/journal.json``.

The concurrency test (this story's headline AC) lives in
``tests/unit/test_fs_local.py`` instead -- it proves ``LocalFs.append_line``'s
own physical guarantee directly, independent of this module's entry-shaping.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from pyforge.marshal.core.identity import StoryKey
from pyforge.marshal.core.journal import (
    KIND_FREEZE_DECLARED,
    KIND_FREEZE_REMOVED,
    SIDECAR_THRESHOLD_BYTES,
    FoldResult,
    FrozenPath,
    JournalEntry,
    JournalEntryId,
    Phase,
    PreparedWrite,
    build_entry,
    intent_reconciles,
    mint_run_id,
    prepare_for_write,
)

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "pyforge"
    / "marshal"
    / "schemas"
    / "journal.json"
)


def _schema() -> dict[str, object]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def _valid_id(counter: int = 0, writer_id: str = "cli-1") -> JournalEntryId:
    return JournalEntryId(writer_id=writer_id, counter=counter)


# --- Phase --------------------------------------------------------------------


def test_phase_is_the_three_valued_ad28_vocabulary():
    assert {member.value for member in Phase} == {"intent", "outcome", "observation"}


# --- mint_run_id(): the I/O & Edge-Case Matrix ---------------------------------


def test_mint_run_id_valid():
    assert (
        mint_run_id("pyforge-marshal", "20260803T054512123Z", "a1b2c3")
        == "pyforge-marshal-20260803T054512123Z-a1b2c3"
    )


def test_mint_run_id_rejects_malformed_slug():
    with pytest.raises(ValueError, match="slug"):
        mint_run_id("Not_Valid!", "20260803T054512123Z", "a1b2c3")


@pytest.mark.parametrize(
    "utc_compact",
    [
        "2026-08-03T05:45:12.123Z",  # not compact
        "20260803T054512Z",  # missing milliseconds
        "20260803T0545121234Z",  # 4-digit milliseconds
        "20260803T054512123",  # missing trailing Z
        "",
    ],
)
def test_mint_run_id_rejects_malformed_utc_compact(utc_compact):
    with pytest.raises(ValueError, match="utc_compact"):
        mint_run_id("pyforge-marshal", utc_compact, "a1b2c3")


@pytest.mark.parametrize("random_token", ["", "A1B2C3", "a1-b2", "a1_b2", "a1 b2"])
def test_mint_run_id_rejects_malformed_random_token(random_token):
    with pytest.raises(ValueError, match="random_token"):
        mint_run_id("pyforge-marshal", "20260803T054512123Z", random_token)


def test_mint_run_id_rejects_non_str_slug():
    with pytest.raises(ValueError, match="slug"):
        mint_run_id(None, "20260803T054512123Z", "a1b2c3")  # type: ignore[arg-type]


# --- JournalEntryId -------------------------------------------------------------


def test_journal_entry_id_valid_construction():
    entry_id = JournalEntryId(writer_id="cli-1", counter=0)
    assert entry_id.writer_id == "cli-1"
    assert entry_id.counter == 0


@pytest.mark.parametrize(
    "writer_id", ["", "-cli", "CLI", "cli 1", "cli.1"]
)
def test_journal_entry_id_rejects_invalid_writer_id(writer_id):
    with pytest.raises(ValueError, match="writer_id"):
        JournalEntryId(writer_id=writer_id, counter=0)


def test_journal_entry_id_rejects_negative_counter():
    with pytest.raises(ValueError, match="counter"):
        JournalEntryId(writer_id="cli-1", counter=-1)


def test_journal_entry_id_rejects_bool_counter():
    """``bool`` excluded (``True == 1``), mirroring
    ``Envelope.schema_version``'s own bool-exclusion idiom."""
    with pytest.raises(ValueError, match="counter"):
        JournalEntryId(writer_id="cli-1", counter=True)  # type: ignore[arg-type]


def test_journal_entry_id_total_ordering():
    assert JournalEntryId("cli-1", 0) < JournalEntryId("cli-1", 1)
    assert JournalEntryId("cli-1", 5) < JournalEntryId("cli-2", 0)


def test_journal_entry_id_equal_ids_hash_equal():
    a = JournalEntryId(writer_id="cli-1", counter=1)
    b = JournalEntryId(writer_id="cli-1", counter=1)
    assert a == b
    assert hash(a) == hash(b)
    assert len({a, b}) == 1


# --- build_entry()/JournalEntry: the I/O & Edge-Case Matrix --------------------


def test_build_entry_returns_a_journal_entry():
    entry = build_entry(
        id=_valid_id(),
        ts="2026-08-03T05:45:12.123Z",
        run_id="run-1",
        kind="run-started",
        phase=Phase.INTENT,
        payload={},
    )
    assert isinstance(entry, JournalEntry)


def test_build_entry_intent_with_no_intent_id():
    entry = build_entry(
        id=_valid_id(),
        ts="2026-08-03T05:45:12.123Z",
        run_id="pyforge-marshal-20260803T054512123Z-a1b2c3",
        kind="run-started",
        phase=Phase.INTENT,
        payload={"a": 1},
    )
    assert entry.phase is Phase.INTENT
    assert entry.intent_id is None
    assert entry.story is None


def test_build_entry_observation_with_no_intent_id():
    entry = build_entry(
        id=_valid_id(),
        ts="2026-08-03T05:45:12.123Z",
        run_id="run-1",
        kind="freeze-declared",
        phase=Phase.OBSERVATION,
        payload={},
    )
    assert entry.phase is Phase.OBSERVATION
    assert entry.intent_id is None


def test_build_entry_outcome_requires_intent_id():
    entry = build_entry(
        id=_valid_id(counter=1),
        ts="2026-08-03T05:45:12.123Z",
        run_id="run-1",
        kind="gate-verdict",
        phase=Phase.OUTCOME,
        intent_id=_valid_id(counter=0),
        payload={"verdict": "clean"},
    )
    assert entry.phase is Phase.OUTCOME
    assert entry.intent_id == _valid_id(counter=0)


def test_build_entry_outcome_without_intent_id_raises():
    with pytest.raises(ValueError, match="intent_id is required"):
        build_entry(
            id=_valid_id(),
            ts="2026-08-03T05:45:12.123Z",
            run_id="run-1",
            kind="gate-verdict",
            phase=Phase.OUTCOME,
            intent_id=None,
            payload={},
        )


def test_build_entry_observation_with_intent_id_raises():
    with pytest.raises(ValueError, match="intent_id must be absent"):
        build_entry(
            id=_valid_id(),
            ts="2026-08-03T05:45:12.123Z",
            run_id="run-1",
            kind="freeze-declared",
            phase=Phase.OBSERVATION,
            intent_id=_valid_id(counter=0),
            payload={},
        )


def test_build_entry_intent_with_intent_id_raises():
    """AD-28's rule extended to ``intent`` -- an intent entry has nothing
    prior to reference."""
    with pytest.raises(ValueError, match="intent_id must be absent"):
        build_entry(
            id=_valid_id(),
            ts="2026-08-03T05:45:12.123Z",
            run_id="run-1",
            kind="run-started",
            phase=Phase.INTENT,
            intent_id=_valid_id(counter=0),
            payload={},
        )


def test_build_entry_accepts_a_story():
    entry = build_entry(
        id=_valid_id(),
        ts="2026-08-03T05:45:12.123Z",
        run_id="run-1",
        kind="story-transition",
        phase=Phase.OBSERVATION,
        story=StoryKey(epic=3, seq=1),
        payload={},
    )
    assert entry.story == StoryKey(epic=3, seq=1)


@pytest.mark.parametrize(
    "ts",
    [
        "2026-08-03 05:45:12.123Z",  # space, not T
        "2026-08-03T05:45:12Z",  # no fractional digits
        "2026-08-03T05:45:12.1234Z",  # 4 fractional digits
        "2026-08-03T05:45:12.123+00:00",  # offset, not Z
        "2026-13-01T05:45:12.123Z",  # month 13
        "2026-08-03T24:00:00.123Z",  # hour 24
        "2026-02-30T05:45:12.123Z",  # calendar-invalid (Feb 30)
        "not-a-date",
    ],
)
def test_journal_entry_rejects_malformed_ts(ts):
    with pytest.raises(ValueError):
        build_entry(
            id=_valid_id(),
            ts=ts,
            run_id="run-1",
            kind="run-started",
            phase=Phase.INTENT,
            payload={},
        )


def test_journal_entry_rejects_blank_run_id():
    with pytest.raises(ValueError, match="run_id"):
        build_entry(
            id=_valid_id(),
            ts="2026-08-03T05:45:12.123Z",
            run_id="   ",
            kind="run-started",
            phase=Phase.INTENT,
            payload={},
        )


def test_journal_entry_rejects_blank_kind():
    with pytest.raises(ValueError, match="kind"):
        build_entry(
            id=_valid_id(),
            ts="2026-08-03T05:45:12.123Z",
            run_id="run-1",
            kind="   ",
            phase=Phase.INTENT,
            payload={},
        )


def test_journal_entry_rejects_non_story_key_story():
    with pytest.raises(ValueError, match="story"):
        build_entry(
            id=_valid_id(),
            ts="2026-08-03T05:45:12.123Z",
            run_id="run-1",
            kind="run-started",
            phase=Phase.INTENT,
            story="3.1",  # type: ignore[arg-type]
            payload={},
        )


def test_journal_entry_rejects_non_journal_entry_id_for_id():
    with pytest.raises(ValueError, match="id must be a JournalEntryId"):
        build_entry(
            id="not-an-id",  # type: ignore[arg-type]
            ts="2026-08-03T05:45:12.123Z",
            run_id="run-1",
            kind="run-started",
            phase=Phase.INTENT,
            payload={},
        )


def test_journal_entry_rejects_non_mapping_payload():
    with pytest.raises(ValueError, match="payload"):
        build_entry(
            id=_valid_id(),
            ts="2026-08-03T05:45:12.123Z",
            run_id="run-1",
            kind="run-started",
            phase=Phase.INTENT,
            payload="not-a-mapping",  # type: ignore[arg-type]
        )


def test_journal_entry_rejects_non_serializable_payload():
    with pytest.raises(ValueError, match="JSON-serializable"):
        build_entry(
            id=_valid_id(),
            ts="2026-08-03T05:45:12.123Z",
            run_id="run-1",
            kind="run-started",
            phase=Phase.INTENT,
            payload={"x": object()},
        )


def test_journal_entry_rejects_non_str_payload_key():
    """Review finding: a bare json.dumps() silently coerces a non-str key
    (no error at construction), but prepare_for_write's sort_keys=True
    later crashes on the SAME payload with an unhandled TypeError (sorting
    mixed-type (key, value) tuples). Rejected here instead, at the one
    place every JournalEntry is constructed."""
    with pytest.raises(ValueError, match="payload keys must all be str"):
        build_entry(
            id=_valid_id(),
            ts="2026-08-03T05:45:12.123Z",
            run_id="run-1",
            kind="run-started",
            phase=Phase.INTENT,
            payload={1: "a", "b": 2},
        )


def test_build_entry_rejects_out_of_vocabulary_phase():
    with pytest.raises(ValueError):
        build_entry(
            id=_valid_id(),
            ts="2026-08-03T05:45:12.123Z",
            run_id="run-1",
            kind="run-started",
            phase="bogus",  # type: ignore[arg-type]
            payload={},
        )


def test_journal_entry_payload_is_deep_copied_not_aliased():
    source = {"nested": {"a": 1}}
    entry = build_entry(
        id=_valid_id(),
        ts="2026-08-03T05:45:12.123Z",
        run_id="run-1",
        kind="run-started",
        phase=Phase.INTENT,
        payload=source,
    )
    source["nested"]["a"] = 99
    assert entry.payload["nested"]["a"] == 1


# --- JournalEntry.to_json_dict() -----------------------------------------------


def test_to_json_dict_shape_omits_absent_optional_keys():
    entry = build_entry(
        id=_valid_id(writer_id="cli-1", counter=2),
        ts="2026-08-03T05:45:12.123Z",
        run_id="run-1",
        kind="run-started",
        phase=Phase.INTENT,
        payload={"a": 1},
    )
    document = entry.to_json_dict()
    assert document == {
        "id": {"writer_id": "cli-1", "counter": 2},
        "ts": "2026-08-03T05:45:12.123Z",
        "run_id": "run-1",
        "kind": "run-started",
        "phase": "intent",
        "payload": {"a": 1},
    }
    assert "story" not in document
    assert "intent_id" not in document


def test_to_json_dict_includes_story_and_intent_id_when_present():
    entry = build_entry(
        id=_valid_id(writer_id="cli-1", counter=2),
        ts="2026-08-03T05:45:12.123Z",
        run_id="run-1",
        kind="gate-verdict",
        phase=Phase.OUTCOME,
        story=StoryKey(epic=3, seq=1),
        intent_id=_valid_id(writer_id="cli-1", counter=1),
        payload={},
    )
    document = entry.to_json_dict()
    assert document["story"] == "3.1"
    assert document["intent_id"] == {"writer_id": "cli-1", "counter": 1}


def test_to_json_dict_payload_is_a_copy_not_an_alias():
    entry = build_entry(
        id=_valid_id(),
        ts="2026-08-03T05:45:12.123Z",
        run_id="run-1",
        kind="run-started",
        phase=Phase.INTENT,
        payload={"nested": {"a": 1}},
    )
    document = entry.to_json_dict()
    document["payload"]["nested"]["a"] = 99
    assert entry.payload["nested"]["a"] == 1


def test_to_json_dict_round_trips_through_json_dumps():
    entry = build_entry(
        id=_valid_id(),
        ts="2026-08-03T05:45:12.123Z",
        run_id="run-1",
        kind="run-started",
        phase=Phase.INTENT,
        payload={"a": 1},
    )
    assert json.loads(json.dumps(entry.to_json_dict())) == entry.to_json_dict()


# --- PreparedWrite/prepare_for_write(): the I/O & Edge-Case Matrix -------------


def test_sidecar_threshold_bytes_is_4096():
    assert SIDECAR_THRESHOLD_BYTES == 4096


def test_prepare_for_write_small_payload_inlines():
    entry = build_entry(
        id=_valid_id(writer_id="cli-1", counter=0),
        ts="2026-08-03T05:45:12.123Z",
        run_id="run-1",
        kind="run-started",
        phase=Phase.INTENT,
        payload={"a": 1},
    )
    prepared = prepare_for_write(entry)
    assert prepared.sidecar_relative_path is None
    assert prepared.sidecar_content is None
    document = json.loads(prepared.line)
    assert document["payload"] == {"a": 1}
    assert "\n" not in prepared.line


def test_prepare_for_write_oversized_payload_uses_sidecar():
    payload = {"data": "x" * 5000}
    assert len(json.dumps(payload, sort_keys=True).encode("utf-8")) > SIDECAR_THRESHOLD_BYTES
    entry = build_entry(
        id=_valid_id(writer_id="cli-1", counter=7),
        ts="2026-08-03T05:45:12.123Z",
        run_id="run-1",
        kind="run-started",
        phase=Phase.INTENT,
        payload=payload,
    )
    prepared = prepare_for_write(entry)
    assert prepared.sidecar_relative_path == "blobs/cli-1-7.json"
    assert prepared.sidecar_content == json.dumps(payload, sort_keys=True)
    document = json.loads(prepared.line)
    assert document["payload"] == {"sidecar_ref": "blobs/cli-1-7.json"}


def test_prepare_for_write_threshold_boundary_inlines_at_exactly_4096_bytes():
    overhead = len(json.dumps({"k": ""}, sort_keys=True).encode("utf-8"))
    payload = {"k": "x" * (SIDECAR_THRESHOLD_BYTES - overhead)}
    assert len(json.dumps(payload, sort_keys=True).encode("utf-8")) == SIDECAR_THRESHOLD_BYTES
    entry = build_entry(
        id=_valid_id(),
        ts="2026-08-03T05:45:12.123Z",
        run_id="run-1",
        kind="run-started",
        phase=Phase.INTENT,
        payload=payload,
    )
    prepared = prepare_for_write(entry)
    assert prepared.sidecar_relative_path is None


def test_prepare_for_write_threshold_boundary_sidecars_at_4097_bytes():
    overhead = len(json.dumps({"k": ""}, sort_keys=True).encode("utf-8"))
    payload = {"k": "x" * (SIDECAR_THRESHOLD_BYTES + 1 - overhead)}
    assert (
        len(json.dumps(payload, sort_keys=True).encode("utf-8"))
        == SIDECAR_THRESHOLD_BYTES + 1
    )
    entry = build_entry(
        id=_valid_id(),
        ts="2026-08-03T05:45:12.123Z",
        run_id="run-1",
        kind="run-started",
        phase=Phase.INTENT,
        payload=payload,
    )
    prepared = prepare_for_write(entry)
    assert prepared.sidecar_relative_path is not None


def test_prepare_for_write_rejects_non_journal_entry():
    with pytest.raises(TypeError, match="JournalEntry"):
        prepare_for_write("not-an-entry")  # type: ignore[arg-type]


def test_prepared_write_rejects_only_one_sidecar_field_set():
    with pytest.raises(ValueError, match="both None or both set together"):
        PreparedWrite(line="{}", sidecar_relative_path="blobs/x.json", sidecar_content=None)


def test_prepared_write_rejects_non_str_line():
    with pytest.raises(ValueError, match="line"):
        PreparedWrite(line=123, sidecar_relative_path=None, sidecar_content=None)  # type: ignore[arg-type]


# --- schema validation ---------------------------------------------------------


def test_small_entry_matches_the_packaged_schema():
    entry = build_entry(
        id=_valid_id(writer_id="cli-1", counter=0),
        ts="2026-08-03T05:45:12.123Z",
        run_id="run-1",
        kind="run-started",
        phase=Phase.INTENT,
        payload={"a": 1},
    )
    prepared = prepare_for_write(entry)
    jsonschema.validate(instance=json.loads(prepared.line), schema=_schema())


def test_outcome_entry_with_story_matches_the_packaged_schema():
    entry = build_entry(
        id=_valid_id(writer_id="cli-1", counter=1),
        ts="2026-08-03T05:45:12.123Z",
        run_id="run-1",
        kind="gate-verdict",
        phase=Phase.OUTCOME,
        story=StoryKey(epic=3, seq=1),
        intent_id=_valid_id(writer_id="cli-1", counter=0),
        payload={"verdict": "clean"},
    )
    prepared = prepare_for_write(entry)
    jsonschema.validate(instance=json.loads(prepared.line), schema=_schema())


def test_oversized_payload_prepared_line_matches_the_packaged_schema():
    entry = build_entry(
        id=_valid_id(writer_id="cli-1", counter=9),
        ts="2026-08-03T05:45:12.123Z",
        run_id="run-1",
        kind="run-started",
        phase=Phase.INTENT,
        payload={"data": "x" * 5000},
    )
    prepared = prepare_for_write(entry)
    jsonschema.validate(instance=json.loads(prepared.line), schema=_schema())


def test_schema_rejects_outcome_entry_missing_intent_id():
    instance = {
        "id": {"writer_id": "cli-1", "counter": 1},
        "ts": "2026-08-03T05:45:12.123Z",
        "run_id": "run-1",
        "kind": "gate-verdict",
        "phase": "outcome",
        "payload": {},
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=instance, schema=_schema())


def test_schema_rejects_observation_entry_carrying_intent_id():
    instance = {
        "id": {"writer_id": "cli-1", "counter": 1},
        "ts": "2026-08-03T05:45:12.123Z",
        "run_id": "run-1",
        "kind": "freeze-declared",
        "phase": "observation",
        "intent_id": {"writer_id": "cli-1", "counter": 0},
        "payload": {},
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=instance, schema=_schema())


def test_schema_rejects_unknown_top_level_property():
    entry = build_entry(
        id=_valid_id(),
        ts="2026-08-03T05:45:12.123Z",
        run_id="run-1",
        kind="run-started",
        phase=Phase.INTENT,
        payload={},
    )
    document = entry.to_json_dict()
    document["bogus"] = "nope"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=document, schema=_schema())


def test_schema_rejects_a_malformed_entry_id_missing_counter():
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            instance={"writer_id": "cli-1"},
            schema=_schema()["$defs"]["entryId"],
        )


def test_schema_rejects_a_document_missing_a_required_field():
    entry = build_entry(
        id=_valid_id(),
        ts="2026-08-03T05:45:12.123Z",
        run_id="run-1",
        kind="run-started",
        phase=Phase.INTENT,
        payload={},
    )
    document = entry.to_json_dict()
    del document["run_id"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=document, schema=_schema())


# --- FrozenPath (Story 2.3, AD-26/AD-27) --------------------------------------


def test_frozen_path_rejects_empty_path():
    with pytest.raises(ValueError):
        FrozenPath(path="", story_key=None)


def test_frozen_path_rejects_non_str_story_key():
    with pytest.raises(ValueError):
        FrozenPath(path="recipes/x/recipe.yaml", story_key=123)  # type: ignore[arg-type]


def test_frozen_path_accepts_none_story_key():
    fp = FrozenPath(path="recipes/x/recipe.yaml", story_key=None)
    assert fp.story_key is None


def test_frozen_path_accepts_str_story_key():
    fp = FrozenPath(path="recipes/x/recipe.yaml", story_key="2.3")
    assert fp.story_key == "2.3"


# --- FoldResult.live_frozen_surfaces (Story 2.3, AD-26/AD-27) ----------------


def _observation(
    *, kind: str, payload: dict[str, object], counter: int, ts_offset: int = 0
) -> JournalEntry:
    return build_entry(
        id=_valid_id(counter=counter),
        ts=_ts_frozen(ts_offset),
        run_id="run-1",
        kind=kind,
        phase=Phase.OBSERVATION,
        payload=payload,
    )


def _ts_frozen(n: int) -> str:
    return f"2026-08-06T05:45:{12 + n:02d}.123Z"


def _fold_of(*entries: JournalEntry) -> FoldResult:
    return FoldResult(entries=tuple(entries), open_intents=(), orphaned_outcomes=(), quarantined=())


def test_live_frozen_surfaces_empty_fold_returns_the_seed_alone_as_policy_owned():
    """AD-26/F-3's own standalone-evaluation case: an EMPTY synthetic
    FoldResult still routes the seed through this one accessor, never a
    direct read."""
    empty = FoldResult(entries=(), open_intents=(), orphaned_outcomes=(), quarantined=())
    result = empty.live_frozen_surfaces(("a.yaml", "b.yaml"))
    assert set(result) == {
        FrozenPath(path="a.yaml", story_key=None),
        FrozenPath(path="b.yaml", story_key=None),
    }


def test_live_frozen_surfaces_rejects_a_non_tuple_seed():
    empty = FoldResult(entries=(), open_intents=(), orphaned_outcomes=(), quarantined=())
    with pytest.raises(TypeError):
        empty.live_frozen_surfaces(["a.yaml"])  # type: ignore[arg-type]


def test_live_frozen_surfaces_freeze_declared_adds_a_story_owned_entry():
    entry = _observation(
        kind=KIND_FREEZE_DECLARED,
        payload={"path": "a.yaml", "story_key": "6.1"},
        counter=0,
    )
    result = _fold_of(entry).live_frozen_surfaces(())
    assert result == (FrozenPath(path="a.yaml", story_key="6.1"),)


def test_live_frozen_surfaces_freeze_declared_narrows_alongside_the_seed():
    entry = _observation(
        kind=KIND_FREEZE_DECLARED,
        payload={"path": "b.yaml", "story_key": "6.1"},
        counter=0,
    )
    result = _fold_of(entry).live_frozen_surfaces(("a.yaml",))
    assert set(result) == {
        FrozenPath(path="a.yaml", story_key=None),
        FrozenPath(path="b.yaml", story_key="6.1"),
    }


def test_live_frozen_surfaces_freeze_removed_lifts_a_seeded_freeze():
    entry = _observation(
        kind=KIND_FREEZE_REMOVED, payload={"path": "a.yaml"}, counter=0
    )
    result = _fold_of(entry).live_frozen_surfaces(("a.yaml", "b.yaml"))
    assert result == (FrozenPath(path="b.yaml", story_key=None),)


def test_live_frozen_surfaces_freeze_removed_lifts_a_declared_freeze():
    declared = _observation(
        kind=KIND_FREEZE_DECLARED,
        payload={"path": "a.yaml", "story_key": "6.1"},
        counter=0,
        ts_offset=0,
    )
    removed = _observation(
        kind=KIND_FREEZE_REMOVED, payload={"path": "a.yaml"}, counter=1, ts_offset=1
    )
    result = _fold_of(declared, removed).live_frozen_surfaces(())
    assert result == ()


def test_live_frozen_surfaces_processes_entries_in_chronological_order():
    """Declared, removed, then re-declared by a DIFFERENT story: the final
    live entry must reflect the LAST event, not an unordered batch
    application (declared-then-removed, batched by kind, would wrongly
    drop the re-declaration)."""
    declared_1 = _observation(
        kind=KIND_FREEZE_DECLARED,
        payload={"path": "a.yaml", "story_key": "6.1"},
        counter=0,
        ts_offset=0,
    )
    removed = _observation(
        kind=KIND_FREEZE_REMOVED, payload={"path": "a.yaml"}, counter=1, ts_offset=1
    )
    declared_2 = _observation(
        kind=KIND_FREEZE_DECLARED,
        payload={"path": "a.yaml", "story_key": "6.2"},
        counter=2,
        ts_offset=2,
    )
    result = _fold_of(declared_1, removed, declared_2).live_frozen_surfaces(())
    assert result == (FrozenPath(path="a.yaml", story_key="6.2"),)


def test_live_frozen_surfaces_skips_a_freeze_declared_entry_missing_story_key():
    """A malformed domain-specific payload for THIS kind is skipped, never
    raised -- the generic fold already validated the entry's own shape;
    this method's own additional shape requirement (story_key present, a
    str) is its own concern."""
    entry = _observation(
        kind=KIND_FREEZE_DECLARED, payload={"path": "a.yaml"}, counter=0
    )
    result = _fold_of(entry).live_frozen_surfaces(())
    assert result == ()


def test_live_frozen_surfaces_ignores_unrelated_kinds():
    entry = _observation(kind="gate-verdict", payload={"path": "a.yaml"}, counter=0)
    result = _fold_of(entry).live_frozen_surfaces(("seed.yaml",))
    assert result == (FrozenPath(path="seed.yaml", story_key=None),)


def test_live_frozen_surfaces_meta_never_reads_effective_policy_seed_directly():
    """AD-26: a live/run-scoped answer must be produced SOLELY by this
    method, never by reading `EffectivePolicy.seed_view()["frozen_surfaces"]`
    and treating it as the live value outside this fold. This is a
    behavioral proof (the accessor is the ONLY way this test ever reaches a
    live frozen set), complementing the static AD-26 seed-field-access
    guard in tests/meta/test_ad26_seed_field_access_guard.py."""
    from pyforge.marshal.core.policy import compose

    effective, _ = compose(
        project_slug="acme", project={"frozen_surfaces": ["a.yaml"]}, flags={}
    )
    seed_value = effective.seed_view()["frozen_surfaces"].value
    empty = FoldResult(entries=(), open_intents=(), orphaned_outcomes=(), quarantined=())
    live = empty.live_frozen_surfaces(seed_value)
    assert live == (FrozenPath(path="a.yaml", story_key=None),)


# ---------------------------------------------------------------------------
# Story 4.6 -- intent_reconciles: the pure reconciliation-evidence
# classification (AD-6 x AD-21 x AD-28). The I/O & Edge-Case Matrix from
# the story's own spec.
# ---------------------------------------------------------------------------


def test_intent_reconciles_true_when_every_key_is_confirmed():
    intent_payload = {"action": "commit_paths", "story_keys": ["4.1", "4.2"]}
    evidence = {"confirmed_story_keys": ["4.1", "4.2", "9.9"]}
    assert intent_reconciles(intent_payload, evidence) is True


def test_intent_reconciles_false_on_partial_match():
    """A batched action either fully happened or Marshal cannot positively
    say it did -- a partial match never reconciles."""
    intent_payload = {"action": "commit_paths", "story_keys": ["4.1", "4.2"]}
    evidence = {"confirmed_story_keys": ["4.1"]}
    assert intent_reconciles(intent_payload, evidence) is False


def test_intent_reconciles_false_when_evidence_is_empty():
    intent_payload = {"action": "merge_branch", "story_keys": ["4.3"]}
    evidence = {"confirmed_story_keys": []}
    assert intent_reconciles(intent_payload, evidence) is False


def test_intent_reconciles_false_on_missing_story_keys():
    assert intent_reconciles({"action": "merge_branch"}, {"confirmed_story_keys": ["4.3"]}) is False


def test_intent_reconciles_false_on_empty_story_keys():
    intent_payload = {"action": "merge_branch", "story_keys": []}
    evidence = {"confirmed_story_keys": ["4.3"]}
    assert intent_reconciles(intent_payload, evidence) is False


def test_intent_reconciles_false_on_non_list_story_keys():
    intent_payload = {"action": "merge_branch", "story_keys": "4.3"}
    evidence = {"confirmed_story_keys": ["4.3"]}
    assert intent_reconciles(intent_payload, evidence) is False


def test_intent_reconciles_false_on_non_str_element_in_story_keys():
    intent_payload = {"action": "merge_branch", "story_keys": ["4.3", 4]}
    evidence = {"confirmed_story_keys": ["4.3", 4]}
    assert intent_reconciles(intent_payload, evidence) is False


def test_intent_reconciles_false_on_missing_confirmed_story_keys():
    intent_payload = {"action": "merge_branch", "story_keys": ["4.3"]}
    assert intent_reconciles(intent_payload, {}) is False


def test_intent_reconciles_false_on_non_list_confirmed_story_keys():
    intent_payload = {"action": "merge_branch", "story_keys": ["4.3"]}
    evidence = {"confirmed_story_keys": "4.3"}
    assert intent_reconciles(intent_payload, evidence) is False


def test_intent_reconciles_false_on_non_str_element_in_confirmed_story_keys():
    intent_payload = {"action": "merge_branch", "story_keys": ["4.3"]}
    evidence = {"confirmed_story_keys": [4.3]}
    assert intent_reconciles(intent_payload, evidence) is False
